"""Species recorded in GBIF within each zone — the Canada page's GBIF tab.

Same shape as ``camposcope/services/gbif_species.py`` (see that module for the
full rationale — real zone polygons rather than a synthetic circle, cumulative
counts, and the simplification GBIF's own geometry limit forces); duplicated
rather than imported for the same reason ``canada/services/gbif.py`` is: the
country code and which country's ``services/gbif.py`` session/session module
to use are baked into this module's functions.
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

from ...config.settings import GBIF_FACET_LIMIT, GBIF_TIMEOUT_CONNECT, GBIF_TIMEOUT_READ
from ..config import gbif as gc
from .gbif import get_session

logger = logging.getLogger(__name__)

_TIMEOUT = (GBIF_TIMEOUT_CONNECT, GBIF_TIMEOUT_READ)
_MAX_GEOMETRY_VERTICES = 100

_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=4, thread_name_prefix="ca-gbif"
                )
    return _executor


@dataclass
class ZoneSpecies:
    zone_key: str
    zone_label: str
    total: int = 0
    species: list[tuple[str, int]] = field(default_factory=list)
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
    tolerance = 0.0001
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
    simplified = _simplify_for_gbif(geom)
    if simplified is None or simplified.is_empty:
        return None
    if simplified.geom_type != "Polygon":
        return None
    exterior_only = Polygon(simplified.exterior)
    return orient(exterior_only, sign=1.0).wkt


def cumulative_zone_geometries(
    features: list[dict[str, Any]],
) -> list[tuple[str, str, Any]]:
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
        out.error = "zone geometry could not be simplified"
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


def species_by_zone(zones_geojson: dict[str, Any]) -> list[ZoneSpecies]:
    """One :class:`ZoneSpecies` per zone. Never raises."""
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
