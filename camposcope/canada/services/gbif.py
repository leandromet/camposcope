"""GBIF occurrences as a live, browser-driven vector layer — the Canada page's
GBIF tab.

Same shape as ``camposcope/services/gbif.py`` (see that module's docstring for
the full rationale); duplicated rather than imported because the country code
and the cache-key/route-path namespace are baked into this module's functions,
the same reason ``canada/services/sicar``-equivalents elsewhere in this app
carry their own copies rather than parameterising the Brazil one. The GBIF
endpoint, field mapping and palette themselves are NOT duplicated — see
``canada/config/gbif.py``.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Optional

import requests

from ...config.settings import (
    GBIF_CACHE_TTL_S,
    GBIF_MAX_PAGES,
    GBIF_MIN_ZOOM,
    GBIF_PAGE_SIZE,
    GBIF_TIMEOUT_CONNECT,
    GBIF_TIMEOUT_READ,
)
from ..config import gbif as gc

logger = logging.getLogger(__name__)

_TIMEOUT = (GBIF_TIMEOUT_CONNECT, GBIF_TIMEOUT_READ)

#: Distinct from the Brazil page's "/_gbif.geojson" — both pages share one
#: Starlette app (camposcope/api/__init__.py), so route paths are global.
GEOJSON_PATH = "/_gbif_ca.geojson"

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


@dataclass
class _Entry:
    value: Any
    stored_at: float

    def fresh(self) -> bool:
        return (time.time() - self.stored_at) < GBIF_CACHE_TTL_S


_cache: dict[str, _Entry] = {}
_cache_lock = threading.Lock()


def _bbox_key(west: float, south: float, east: float, north: float) -> str:
    return f"gbif_ca:{west:.3f}:{south:.3f}:{east:.3f}:{north:.3f}"


def _clean(field: str, value: Any) -> Any:
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
    sequential loop — see ``camposcope/services/gbif.py``'s ``_fetch()``,
    same reasoning, duplicated here for the same reason the rest of this
    module is duplicated rather than imported.
    """
    first = _fetch_page(west, south, east, north, 0)
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


def vector_spec(opacity: float = 0.85, min_zoom: int | None = None,
                z_index: int = 25) -> dict:
    """Spec for the dynamic, browser-fetched GBIF layer — see the Brazil
    page's own ``services/gbif.py::vector_spec`` for the full rationale."""
    return {
        "id": "gbif_occurrences_ca",
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
            {"label": "Scientific name", "property": "scientific_name"},
            {"label": "Kingdom", "property": "kingdom"},
            {"label": "Class", "property": "class_name"},
            {"label": "Family", "property": "family"},
            {"label": "Date", "property": "event_date"},
            {"label": "Basis of record", "property": "basis_of_record"},
            {"label": "Recorded by", "property": "recorded_by"},
            {"label": "Institution", "property": "institution_code"},
            {"label": "Dataset", "property": "dataset_name"},
            {"label": "Uncertainty (m)", "property": "coordinate_uncertainty_m"},
            {"label": "Record", "property": "gbif_url", "link": True,
             "link_text": "View on GBIF ↗"},
        ],
    }


__all__ = ["GEOJSON_PATH", "points_in_bbox", "vector_spec", "get_session"]
