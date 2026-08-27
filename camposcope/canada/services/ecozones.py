"""Ecozone polygons: the navigation overlay, Canada's answer to IBGE biomes.

Same job and same delivery mechanism as :mod:`camposcope.services.biomes` — the
polygons are fetched once, simplified, cached on disk as gzipped GeoJSON, and
served to the browser over ordinary HTTP rather than pushed through the Reflex
WebSocket. See ``camposcope/api/__init__.py`` for why a static,
identical-for-everyone FeatureCollection has no business being a state var.

**One difference, and it is the whole reason this is a separate module.** The
Brazil layer's polygons live in an Earth Engine asset, so that module's
``build_geojson`` is an EE call. There is no published EE asset for the Canadian
ecozones, and uploading one would mean this app maintaining a private copy of
federal data that AAFC can revise without telling us. So the polygons come from
the source service — the ArcGIS FeatureServer, with the pre-packaged GeoJSON as
a fallback — and this module needs no Earth Engine at all. A pleasant side
effect: the ecozone layer works on a machine with no EE credentials, which the
biome layer does not.

**Orientation only.** The delivered polygons are simplified to 2 km and rounded
to two decimals. Nothing this app reports is derived from which ecozone a parcel
falls in, and boundaries drawn from this layer must not decide anything.
"""

from __future__ import annotations

import gzip
import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional

import requests

from ...config.settings import REPO_ROOT
from ..config import ecozones as cfg
from ..config.settings import PMBC_TIMEOUT_CONNECT, PMBC_TIMEOUT_READ, PMBC_USER_AGENT

logger = logging.getLogger(__name__)

_TIMEOUT = (PMBC_TIMEOUT_CONNECT, PMBC_TIMEOUT_READ)

CACHE_PATH = REPO_ROOT / "data" / "cache" / "canada_ecozones.json.gz"

#: Path served by the backend (see ``camposcope/api/__init__.py``). Relative —
#: the map component resolves it against the backend origin, which differs
#: between the split dev ports and single-port production.
GEOJSON_PATH = "/_ecozones.geojson"

_memo: Optional[bytes] = None
_memo_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# Geometry cleaning — ported verbatim in behaviour from services/biomes.py
# --------------------------------------------------------------------------- #
def _clean_ring(ring: list, dp: int) -> Optional[list]:
    """Round a ring and drop the duplicate vertices rounding creates.

    Without the dedup, rounding *adds* bytes: long stretches of coastline
    collapse onto the same rounded coordinate and each repeat still costs its
    characters. Canada's Pacific and Arctic coasts make this worth more here
    than it is in Brazil.
    """
    out: List[List[float]] = []
    for x, y in ring:
        pos = [round(x, dp), round(y, dp)]
        if not out or out[-1] != pos:
            out.append(pos)
    if len(out) < 4:
        return None
    if out[0] != out[-1]:
        out.append(list(out[0]))
    return out


def _clean_geometry(geom: dict, dp: int) -> Optional[dict]:
    """Reduce any geometry to a Polygon/MultiPolygon, or drop it.

    Simplification turns the smallest islands into LineStrings and Points.
    Leaflet renders the degenerate ones as invisible zero-area shapes that still
    sit in the hit-test path and steal hovers from the polygon underneath, so
    they are removed here rather than filtered in the browser. The Arctic
    archipelago produces a great many of these.
    """
    kind = geom.get("type")

    if kind == "Polygon":
        rings = [r for r in (_clean_ring(r, dp) for r in geom["coordinates"]) if r]
        return {"type": "Polygon", "coordinates": rings} if rings else None

    if kind == "MultiPolygon":
        polys = []
        for poly in geom["coordinates"]:
            rings = [r for r in (_clean_ring(r, dp) for r in poly) if r]
            if rings:
                polys.append(rings)
        return {"type": "MultiPolygon", "coordinates": polys} if polys else None

    if kind == "GeometryCollection":
        parts = [g for g in (_clean_geometry(g, dp)
                             for g in geom.get("geometries", [])) if g]
        if not parts:
            return None
        polys: list = []
        for part in parts:
            if part["type"] == "MultiPolygon":
                polys.extend(part["coordinates"])
            else:
                polys.append(part["coordinates"])
        return {"type": "MultiPolygon", "coordinates": polys}

    return None      # Point, LineString — degenerate remains of simplification


# --------------------------------------------------------------------------- #
# Fetch
# --------------------------------------------------------------------------- #
def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": PMBC_USER_AGENT, "Accept": "application/json"})
    return s


def _fetch_from_featureserver() -> Dict[str, Any]:
    """Query the ArcGIS FeatureServer, paging until it stops returning more.

    ``maxRecordCount`` is 2000 and the layer holds a few hundred polygon parts,
    so this normally completes in one page — the paging exists because ArcGIS
    silently truncates rather than erroring, and a silently truncated ecozone
    map would just be missing a region with nothing to say so.
    """
    session = _session()
    features: List[dict] = []
    offset = 0
    page_size = 1000

    while True:
        params = {
            "where": "1=1",
            "outFields": ",".join(cfg.FIELDS.values()),
            "returnGeometry": "true",
            "outSR": "4326",
            # Ask the server to generalise before sending. It is far cheaper to
            # have ArcGIS drop vertices than to transfer full-resolution
            # coastline and drop them here — and the tolerance is in degrees at
            # outSR, so this is roughly the same order as SIMPLIFY_M.
            "geometryPrecision": str(cfg.COORD_DECIMALS),
            "f": "geojson",
            "resultOffset": str(offset),
            "resultRecordCount": str(page_size),
        }
        r = session.get(cfg.ECOZONE_FEATURESERVER + "/query",
                        params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        payload = r.json()
        page = payload.get("features") or []
        features.extend(page)
        if len(page) < page_size or not payload.get("properties", {}).get(
                "exceededTransferLimit", False):
            break
        offset += page_size

    return {"type": "FeatureCollection", "features": features}


def build_geojson() -> dict:
    """Fetch, simplify and normalise the ecozone polygons.

    Blocking, a few seconds against the source service. The output carries only
    the three fields the tooltip and the colour lookup need — every extra string
    field costs bytes across a few hundred features for nothing.
    """
    started = time.time()
    raw = _fetch_from_featureserver()

    try:
        from shapely.geometry import mapping, shape
        _shapely = True
    except ImportError:                                   # pragma: no cover
        _shapely = False

    id_field = cfg.FIELDS["id"]
    en_field = cfg.FIELDS["name_en"]
    fr_field = cfg.FIELDS["name_fr"]

    features = []
    for feature in raw.get("features", []):
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}

        if _shapely and geom:
            # The server's geometryPrecision only rounds coordinates; it does
            # not remove vertices. Simplifying here is what actually shrinks the
            # payload. Done in degrees — an approximation of SIMPLIFY_M that is
            # entirely adequate for a layer explicitly not used for decisions.
            try:
                tolerance_deg = cfg.SIMPLIFY_M / 111_000.0
                geom = mapping(shape(geom).simplify(tolerance_deg,
                                                    preserve_topology=True))
            except Exception:                             # noqa: BLE001
                pass          # keep the unsimplified geometry rather than none

        cleaned = _clean_geometry(geom, cfg.COORD_DECIMALS)
        if cleaned is None:
            continue

        ecozone_id = props.get(id_field)
        name_en = props.get(en_field) or cfg.name(ecozone_id or 0, "en")
        features.append({
            "type": "Feature",
            "properties": {
                "ecozone_id": ecozone_id,
                "name_en": name_en,
                "name_fr": props.get(fr_field) or "",
                "name_pt": cfg.name(ecozone_id or 0, "pt"),
            },
            "geometry": cleaned,
        })

    logger.info("Built ecozone GeoJSON: %s/%s features in %.1f s",
                len(features), len(raw.get("features", [])), time.time() - started)
    return {"type": "FeatureCollection", "features": features}


def geojson_gzipped() -> bytes:
    """The simplified ecozone GeoJSON, gzip-compressed, memoised and disk-cached.

    Three tiers, each removing a different cost: the memo removes the disk read,
    the disk cache removes the network round trip, and the gzip is stored rather
    than recomputed because it is the same bytes every time.
    """
    global _memo

    with _memo_lock:
        if _memo is not None:
            return _memo

    if CACHE_PATH.exists():
        try:
            payload = CACHE_PATH.read_bytes()
            with _memo_lock:
                _memo = payload
            logger.info("Ecozone GeoJSON from disk cache (%s KiB)",
                        len(payload) // 1024)
            return payload
        except OSError as exc:
            logger.warning("Ecozone cache unreadable (%s) — rebuilding", exc)

    body = json.dumps(build_geojson(), separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")
    payload = gzip.compress(body, 9)

    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Written via a temporary file: two workers building this at once would
        # otherwise interleave into a corrupt gzip that then fails forever.
        tmp = CACHE_PATH.with_suffix(".tmp")
        tmp.write_bytes(payload)
        tmp.replace(CACHE_PATH)
    except OSError as exc:
        logger.warning("Could not cache ecozone GeoJSON (%s) — serving from "
                       "memory", exc)

    with _memo_lock:
        _memo = payload
    logger.info("Ecozone GeoJSON ready: %s KiB gzipped", len(payload) // 1024)
    return payload


# --------------------------------------------------------------------------- #
# Layer spec
# --------------------------------------------------------------------------- #
def vector_spec(opacity: float = 0.45, z_index: int = 5,
                show_labels: bool = True, lang: str = "en") -> dict:
    """Spec for the browser-side ecozone layer.

    Purely declarative and involves no round trip of its own, so unlike every
    tile spec it cannot fail — the fetch happens in the browser.
    """
    name_prop = "name_pt" if lang == "pt" else "name_en"
    return {
        # The label and language suffixes make both part of the layer's
        # identity, so toggling either forces leaflet_map.js's diff to rebuild
        # rather than patch in place. Label markers are only ever created at
        # build time, so a same-id "cheap property update" would silently do
        # nothing — the note in services/biomes.py has the full trace.
        "id": f"ecozones:{lang}:{'lbl' if show_labels else 'nolbl'}",
        "path": GEOJSON_PATH,
        "opacity": opacity,
        "z_index": z_index,
        "attribution": cfg.ATTRIBUTION,
        # Coloured on the English name always, whatever language is displayed:
        # the palette is keyed by it, and a colour that changed with the UI
        # language would be a different map for no reason.
        "color_property": "name_en",
        "palette": cfg.PALETTE,
        "default_color": cfg.DEFAULT_COLOR,
        "weight": cfg.OUTLINE_WIDTH,
        "label_property": name_prop if show_labels else None,
        "label_min_zoom": cfg.LABEL_MIN_ZOOM,
        "tooltip": [
            {"label": "Ecozone" if lang != "pt" else "Ecozona",
             "property": name_prop},
            {"label": "Français", "property": "name_fr"},
        ],
    }


__all__ = ["build_geojson", "geojson_gzipped", "vector_spec", "GEOJSON_PATH",
           "CACHE_PATH"]
