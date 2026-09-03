"""Species recorded in GBIF within each zone — the GBIF tab's "Calcular"
analysis, run on the property's own zone geometries rather than a synthetic
circle around a point.

**Why real zone polygons, not a buffer disc.** Naturametrics' equivalent
(``services/gbif_buffers.py``) queries a circle around a clicked point, which
is the right shape there — a point has no boundary of its own. A property
does: this app already draws its neighbourhood as true rings grown OUTWARD
FROM THE BOUNDARY (``services/zones.py``, decision D3), and those same rings
are what is drawn on the map (``state/_zones.py::map_overlays``). A circle
centred on the property's centroid would silently disagree with those
dashed rings for anything but a circular property, so the species count for
"0–2 km" has to come from the SAME 0–2 km geometry the map shows, not a
lookalike.

**Cumulative, not per-ring.** Presence is not additive — "the species in the
2–5 km ring" would read as a list that excludes the ones also present
nearer in, which a subtraction of counts does not give you. So each zone's
count is the union of itself and every zone inside it (property, then
property+ring1, then property+ring1+ring2, …), the same "cumulative disc"
convention Naturametrics documents for the same reason.

**Aggregates, not records.** ``limit=0`` with ``facet=`` returns counts
without paging any occurrence at all — one request per zone, fanned out
concurrently, the same shape ``services/gbif_buffers.py`` uses.

**GBIF's own geometry limit governs the simplification below.** A
self-declared CAR polygon can carry thousands of vertices; GBIF's
``geometry`` filter does not accept an arbitrarily complex one. The zone
polygon is therefore simplified before it is sent, backing off in coarser
steps until it is small enough, rather than guessing one tolerance that
might still be rejected for an unusually detailed property.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Optional

import requests
from shapely.geometry import Polygon, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from ..config import gbif as gc
from ..config.settings import (
    GBIF_FACET_LIMIT,
    GBIF_TIMEOUT_CONNECT,
    GBIF_TIMEOUT_READ,
)
from .gbif import get_session

logger = logging.getLogger(__name__)

_TIMEOUT = (GBIF_TIMEOUT_CONNECT, GBIF_TIMEOUT_READ)

#: GBIF has no documented hard cap, but a WKT filter past a few hundred
#: vertices routinely comes back ``HTTP 400``, measured. Kept well under that.
_MAX_GEOMETRY_VERTICES = 100

_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=4, thread_name_prefix="cs-gbif"
                )
    return _executor


@dataclass
class ZoneSpecies:
    """One zone's biodiversity summary — the cumulative area out to it."""

    zone_key: str
    zone_label: str
    total: int = 0
    #: ``(scientific name, occurrence count)``, most-recorded first.
    species: list[tuple[str, int]] = field(default_factory=list)
    #: ``(kingdom name, count)`` — the same taxonomy the map colouring uses.
    kingdoms: list[tuple[str, int]] = field(default_factory=list)
    richness: int = 0
    richness_truncated: bool = False
    error: str = ""


_KINGDOM_BY_KEY = {str(key): name for key, name in gc.KINGDOMS}


def _facet_rows(payload: dict, field_name: str) -> list[tuple[str, int]]:
    for facet in payload.get("facets", []):
        if facet.get("field") == field_name:
            return [(c["name"], c["count"]) for c in facet.get("counts", [])]
    return []


def _simplify_for_gbif(geom, max_vertices: int = _MAX_GEOMETRY_VERTICES):
    """Back the polygon off in coarser steps until GBIF can take it.

    Degrees, not metres — the geometry here is still in EPSG:4326, and GBIF's
    own coordinate precision is coarse enough that a simplification measured
    in the low hundreds of metres costs nothing a species-presence query would
    notice. Falls back to the convex hull (always a single, simple polygon)
    if six widening passes still are not enough, which only a very
    convoluted boundary would ever reach.
    """
    tolerance = 0.0001  # ~11 m
    candidate = geom
    for _ in range(6):
        candidate = geom.simplify(tolerance, preserve_topology=True)
        if candidate.geom_type == "MultiPolygon":
            candidate = candidate.convex_hull
        if (candidate.geom_type == "Polygon"
                and len(candidate.exterior.coords) <= max_vertices):
            return candidate
        tolerance *= 2.5

    hull = geom.convex_hull
    if hull.geom_type != "Polygon":
        return None
    return hull.simplify(tolerance, preserve_topology=True)


def _zone_wkt(geom) -> Optional[str]:
    """A zone polygon as the WKT GBIF's ``geometry`` filter takes.

    **Wound counter-clockwise.** GBIF rejects a clockwise exterior ring
    outright (``HTTP 400``), the same trap Naturametrics' own WKT builder
    documents.
    """
    simplified = _simplify_for_gbif(geom)
    if simplified is None or simplified.is_empty:
        return None
    if simplified.geom_type != "Polygon":
        return None
    # The exterior ring only — a hole here could only be a simplification
    # artefact (cumulative zones are simply connected by construction), and a
    # hole GBIF has to parse for no reason is one more way to hit its limits.
    exterior_only = Polygon(simplified.exterior)
    return orient(exterior_only, sign=1.0).wkt


def cumulative_zone_geometries(
    features: list[dict[str, Any]],
) -> list[tuple[str, str, Any]]:
    """``(zone_key, zone_label, cumulative_geometry)`` per zone, in the order
    ``features`` already comes in (property first, then rings by increasing
    radius — see ``services/zones.py::build_zones``).

    Each entry's geometry is the union of every feature up to and including
    it, so the smallest is the property alone and the largest is the full
    disc out to the outermost ring — exactly the area the outermost ring's
    own dashed circle on the map encloses.
    """
    out: list[tuple[str, str, Any]] = []
    accumulated: list[Any] = []
    for f in features:
        accumulated.append(shape(f["geometry"]))
        union = accumulated[0] if len(accumulated) == 1 else unary_union(accumulated)
        props = f.get("properties", {})
        out.append((props.get("zone_key", ""), props.get("label", ""), union))
    return out


def _one_zone(zone_key: str, zone_label: str, geom) -> ZoneSpecies:
    out = ZoneSpecies(zone_key=zone_key, zone_label=zone_label)
    wkt = _zone_wkt(geom)
    if wkt is None:
        out.error = "geometria da zona não pôde ser simplificada"
        return out

    params: list[tuple[str, str]] = [
        ("country", gc.COUNTRY),
        ("has_coordinate", "true"),
        ("has_geospatial_issue", "false"),
        ("geometry", wkt),
        ("limit", "0"),
        ("facet", "scientificName"),
        ("facet", "kingdomKey"),
        ("facetLimit", str(GBIF_FACET_LIMIT)),
    ]

    try:
        r = get_session().get(gc.OCCURRENCE_SEARCH, params=params, timeout=_TIMEOUT)
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}")
        payload = r.json()
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        logger.warning("GBIF zone facet failed (%s): %s", zone_key, exc)
        out.error = str(exc)
        return out

    out.total = payload.get("count", 0)
    names = _facet_rows(payload, "SCIENTIFIC_NAME")
    out.species = names
    out.richness = len(names)
    out.richness_truncated = len(names) >= GBIF_FACET_LIMIT
    out.kingdoms = [
        (_KINGDOM_BY_KEY.get(key, key), count)
        for key, count in _facet_rows(payload, "KINGDOM_KEY")
    ]
    return out


def species_by_zone(
    zones_geojson: dict[str, Any],
) -> list[ZoneSpecies]:
    """One :class:`ZoneSpecies` per zone, property first. Never raises.

    The zones go out concurrently: independent queries against a third
    party, so the run costs one round trip in wall clock rather than four.
    """
    features = (zones_geojson or {}).get("features") or []
    if not features:
        return []

    zones = cumulative_zone_geometries(features)
    futures = [
        _get_executor().submit(_one_zone, key, label, geom)
        for key, label, geom in zones
    ]
    results: list[ZoneSpecies] = []
    for (key, label, _geom), future in zip(zones, futures):
        try:
            results.append(future.result())
        except Exception as exc:  # noqa: BLE001
            logger.warning("GBIF zone task crashed (%s): %s", key, exc)
            results.append(ZoneSpecies(zone_key=key, zone_label=label, error=str(exc)))
    return results


__all__ = ["ZoneSpecies", "species_by_zone", "cumulative_zone_geometries"]
