"""GBIF occurrences as a live, browser-driven vector layer — the GBIF tab's
map layer.

Ported from Naturametrics' ``services/gbif.py``, trimmed to what the GBIF tab
actually needs (decision D2): a bounding box and nothing else, the same
simpler shape ``services/biomes.py`` and the CAR WMS layer already use in this
app — no taxonomy cascade, no basis-of-record/year/UF accordion, no
species-in-buffer analysis. See Naturametrics' fuller module for why those
exist there and why they were left out here: this app answers "what lives
around this property", not "run a faceted biodiversity survey".

**The response is still slimmed here, not in the browser.** One page of 300
occurrences is over 2 MB of verbatim Darwin Core off the wire; the tooltip and
the kingdom colouring between them read a dozen fields, about 200 bytes per
record.

**This function must never raise**, same convention as ``services/biomes.py``
and the SICAR WMS spec: it can be called on every map pan, with nowhere to
surface an exception, so failures come back as ``properties.error`` on an
empty FeatureCollection.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Optional

import requests

from ..config import gbif as gc
from ..config.settings import (
    GBIF_CACHE_TTL_S,
    GBIF_MAX_PAGES,
    GBIF_MIN_ZOOM,
    GBIF_PAGE_SIZE,
    GBIF_TIMEOUT_CONNECT,
    GBIF_TIMEOUT_READ,
)

logger = logging.getLogger(__name__)

_TIMEOUT = (GBIF_TIMEOUT_CONNECT, GBIF_TIMEOUT_READ)

#: Path served by the backend (see camposcope/api). Relative — the map
#: component resolves it against the backend origin.
GEOJSON_PATH = "/_gbif.geojson"

_session: Optional[requests.Session] = None
_session_lock = threading.Lock()


def get_session() -> requests.Session:
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                s = requests.Session()
                s.headers.update({
                    "User-Agent": gc.USER_AGENT,
                    "Accept": "application/json",
                })
                _session = s
    return _session


# --------------------------------------------------------------------------- #
# Short-lived cache — de-duplicates the debounced refetch bursts a pan/zoom
# produces (leaflet_map.js's "settle" handler), not a long-term store.
# --------------------------------------------------------------------------- #
@dataclass
class _Entry:
    value: Any
    stored_at: float

    def fresh(self) -> bool:
        return (time.time() - self.stored_at) < GBIF_CACHE_TTL_S


_cache: dict[str, _Entry] = {}
_cache_lock = threading.Lock()


def _bbox_key(west: float, south: float, east: float, north: float) -> str:
    # Rounded to 3dp (~100 m), matching the client's own rounding in
    # leaflet_map.js's specUrl — a finer key would never hit the cache at all.
    return f"gbif:{west:.3f}:{south:.3f}:{east:.3f}:{north:.3f}"


# --------------------------------------------------------------------------- #
# Fetch
# --------------------------------------------------------------------------- #
def _clean(field: str, value: Any) -> Any:
    """Normalise one field value, or return ``None`` to drop it.

    Some publishers ship records with unrelated content packed into every
    field — a sync error between the collection and GBIF. Left alone these
    break the layer in two ways: the tooltip stops being readable, and a
    corrupt "kingdom" silently becomes its own slice of the map legend.
    """
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        return value

    text = " ".join(value.split())
    if not text:
        return None

    if field in gc.CONTROLLED_FIELDS:
        return None if len(text) > gc.CONTROLLED_MAX_CHARS else text
    if len(text) > gc.FREETEXT_MAX_CHARS:
        return text[:gc.FREETEXT_MAX_CHARS].rstrip() + "…"
    return text


def _slim(record: dict) -> dict | None:
    """One GBIF record → one GeoJSON feature, keeping only what is drawn.

    Returns ``None`` for a record with no usable coordinate — the upstream
    ``has_coordinate`` filter already excludes those, but a null slipping
    through would become a feature Leaflet renders as an exception.
    """
    lat = record.get(gc.LAT_FIELD)
    lon = record.get(gc.LON_FIELD)
    if lat is None or lon is None:
        return None

    props: dict[str, Any] = {}
    for source, target in gc.SLIM_FIELDS.items():
        value = _clean(target, record.get(source))
        if value is not None:
            props[target] = value

    props["lat"] = lat
    props["lon"] = lon
    # The canonical page for this exact record — "key" is GBIF's own
    # occurrence id, stable across the API and the website, so this is the
    # one link that reliably lands on the record itself rather than a search
    # for it.
    gbif_id = props.get("gbif_id")
    if gbif_id is not None:
        props["gbif_url"] = f"{gc.PORTAL_URL}/occurrence/{gbif_id}"

    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": props,
    }


def _fetch_page(west: float, south: float, east: float, north: float,
                offset: int) -> dict:
    params: list[tuple[str, str]] = [
        ("country", gc.COUNTRY),
        ("has_coordinate", "true"),
        # Records GBIF itself flagged as geospatially wrong (sea coordinate
        # for a terrestrial taxon, country mismatch, zero/zero) — excluded
        # rather than drawn, since this layer's whole purpose is telling
        # someone what was recorded *at a place*.
        ("has_geospatial_issue", "false"),
        ("decimalLatitude", f"{south},{north}"),
        ("decimalLongitude", f"{west},{east}"),
        ("limit", str(GBIF_PAGE_SIZE)),
        ("offset", str(offset)),
    ]

    session = get_session()
    last: Optional[Exception] = None
    for attempt in (1, 2):
        try:
            r = session.get(gc.OCCURRENCE_SEARCH, params=params, timeout=_TIMEOUT)
        except requests.RequestException as exc:
            last = exc
            logger.warning("GBIF occurrence request failed (attempt %d): %s",
                           attempt, exc)
            continue
        if r.status_code != 200:
            last = RuntimeError(f"HTTP {r.status_code}")
            continue
        try:
            return r.json()
        except ValueError as exc:
            last = exc
            continue
    raise RuntimeError(f"GBIF occurrence service unreachable: {last}")


def _fetch(west: float, south: float, east: float, north: float) -> dict:
    """Page 1 first and alone — it is the only page that tells us ``count``,
    the true match total. Any further pages needed to reach it (up to
    GBIF_MAX_PAGES) are then fired at GBIF concurrently rather than in a
    sequential loop: each page is its own ~1.5-2 s round trip (measured), so
    a 4-page fetch done one at a time would add 4-6 s to a single pan/zoom.
    Fetched in parallel it costs roughly what one page does. Ported from
    Naturametrics' ``services/gbif.py``, same reasoning.

    This also means the extra cost is adaptive, not a flat multiplier: a
    viewport with 250 matching records still does exactly one request, the
    same as before GBIF_MAX_PAGES was raised.
    """
    first = _fetch_page(west, south, east, north, 0)
    # GBIF reports the true match count independently of what this page
    # returned — the number the panel needs to admit how much is hidden.
    total = first.get("count", 0)
    first_results = first.get("results", [])
    features = [f for f in (_slim(r) for r in first_results) if f is not None]

    more_to_fetch = (
        len(first_results) == GBIF_PAGE_SIZE and not first.get("endOfRecords")
    )
    if more_to_fetch:
        capped_total = min(total, GBIF_MAX_PAGES * GBIF_PAGE_SIZE)
        pages_wanted = -(-capped_total // GBIF_PAGE_SIZE)  # ceil
        offsets = [p * GBIF_PAGE_SIZE for p in range(1, pages_wanted)]
        if offsets:
            with ThreadPoolExecutor(max_workers=len(offsets)) as pool:
                future_offset = {
                    pool.submit(_fetch_page, west, south, east, north,
                               offset): offset
                    for offset in offsets
                }
                for future in as_completed(future_offset):
                    try:
                        payload = future.result()
                    except Exception as exc:  # noqa: BLE001
                        # One page failing should not blank out the rest —
                        # the map still shows what came back, just short of
                        # the cap, same as any other truncation.
                        logger.warning(
                            "GBIF page at offset %d failed: %s",
                            future_offset[future], exc)
                        continue
                    features.extend(
                        f for f in (_slim(r) for r in payload.get("results", []))
                        if f is not None
                    )

    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "count": total,
            "shown": len(features),
            "truncated": total > len(features),
        },
    }


def points_in_bbox(west: float, south: float, east: float,
                   north: float) -> dict:
    """GBIF occurrences inside a viewport, as slim GeoJSON. Never raises."""
    key = _bbox_key(west, south, east, north)
    with _cache_lock:
        hit = _cache.get(key)
        if hit is not None and hit.fresh():
            return hit.value

    try:
        value = _fetch(west, south, east, north)
    except Exception as exc:  # noqa: BLE001
        logger.warning("GBIF occurrence query failed for %s: %s", key, exc)
        value = {
            "type": "FeatureCollection",
            "features": [],
            "properties": {"error": str(exc), "count": 0, "shown": 0,
                           "truncated": False},
        }

    with _cache_lock:
        _cache[key] = _Entry(value, time.time())
    return value


# --------------------------------------------------------------------------- #
# Layer spec
# --------------------------------------------------------------------------- #
def vector_spec(opacity: float = 0.85, min_zoom: int | None = None,
                z_index: int = 25) -> dict:
    """Spec for the dynamic, browser-fetched GBIF layer.

    Highest z_index of any layer in this app: the biodiversity dots are the
    newest and most specific reading of a place, and the one thing a user
    turned this tab on to see.

    Purely declarative — the fetch happens in the browser via
    leaflet_map.js's generic dynamic-layer pipeline (the same one
    ``services/biomes.py``'s ecozone-style layers already use, extended here
    with ``dynamic: True`` so it refetches per viewport instead of once).
    """
    return {
        "id": "gbif_occurrences",
        "path": GEOJSON_PATH,
        "dynamic": True,
        "min_zoom": GBIF_MIN_ZOOM if min_zoom is None else min_zoom,
        "z_index": z_index,
        "opacity": opacity,
        "attribution": gc.ATTRIBUTION,
        "color_property": "kingdom",
        "palette": gc.KINGDOM_COLORS,
        "default_color": gc.DEFAULT_COLOR,
        "point_style": {
            "radius": 4,
            "color": "#ffffff",
            "weight": 1,
            "fillOpacity": opacity,
        },
        "hover_style": {
            "radius": 7,
            "color": "#ffffff",
            "weight": 1.5,
            "fillOpacity": 1.0,
        },
        "tooltip": [
            {"label": "Nome científico", "property": "scientific_name"},
            {"label": "Reino", "property": "kingdom"},
            {"label": "Classe", "property": "class_name"},
            {"label": "Família", "property": "family"},
            {"label": "Data", "property": "event_date"},
            {"label": "Base do registro", "property": "basis_of_record"},
            {"label": "Registrado por", "property": "recorded_by"},
            {"label": "Instituição", "property": "institution_code"},
            {"label": "Conjunto de dados", "property": "dataset_name"},
            {"label": "Incerteza (m)", "property": "coordinate_uncertainty_m"},
            {"label": "Registro", "property": "gbif_url", "link": True,
             "link_text": "Ver no GBIF ↗"},
        ],
    }


__all__ = ["GEOJSON_PATH", "points_in_bbox", "vector_spec", "get_session"]
