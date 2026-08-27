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

CACHE_DIR = REPO_ROOT / "data" / "cache"

#: Kept for callers written against the single-level version of this module
#: (and as the default level's own path) — identical to ``LEVELS["ecozone"]
#: .geojson_path``.
GEOJSON_PATH = cfg.LEVELS["ecozone"].geojson_path

#: One memo slot and one disk-cache path per level — a level is a completely
#: separate FeatureCollection, not a filtered view of another, so nothing is
#: shared between them.
_memo: Dict[str, bytes] = {}
_memo_lock = threading.Lock()

#: The ecoregion id → (name_en, name_fr) lookup an ecodistrict borrows for its
#: tooltip, since the ecodistrict service itself publishes no name at all —
#: see ``config/ecozones.py``'s module docstring. Small (218 rows, no
#: geometry) and cheap enough to hold in memory for the process lifetime
#: rather than round-tripping it on every ecodistrict build.
_region_name_memo: Optional[Dict[int, tuple]] = None
_region_name_lock = threading.Lock()


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


def _fetch_from_featureserver(featureserver: str, out_fields: List[str],
                              *, geometry_precision: int) -> Dict[str, Any]:
    """Query one ArcGIS FeatureServer layer, paging until it stops returning
    more.

    ``maxRecordCount`` is 2000 on all three of this framework's layers, and
    the largest (ecodistrict, 1,025 rows) still fits in one page — the paging
    exists because ArcGIS silently truncates rather than erroring, and a
    silently truncated map would just be missing a region with nothing to say
    so.
    """
    session = _session()
    features: List[dict] = []
    offset = 0
    page_size = 1000

    while True:
        params = {
            "where": "1=1",
            "outFields": ",".join(out_fields),
            "returnGeometry": "true",
            "outSR": "4326",
            # Ask the server to generalise before sending. It is far cheaper to
            # have ArcGIS drop vertices than to transfer full-resolution
            # coastline and drop them here — and the tolerance is in degrees at
            # outSR, so this is roughly the same order as the level's own
            # SIMPLIFY_M.
            "geometryPrecision": str(geometry_precision),
            "f": "geojson",
            "resultOffset": str(offset),
            "resultRecordCount": str(page_size),
        }
        r = session.get(featureserver + "/query", params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        payload = r.json()
        page = payload.get("features") or []
        features.extend(page)
        if len(page) < page_size or not payload.get("properties", {}).get(
                "exceededTransferLimit", False):
            break
        offset += page_size

    return {"type": "FeatureCollection", "features": features}


def _ecoregion_name_lookup() -> Dict[int, tuple]:
    """``{ECOREGION_ID: (name_en, name_fr)}`` — geometry-free, ~218 rows,
    fetched once and held for the process lifetime.

    The one piece of cross-level data ecodistrict needs and cannot get from
    its own service: the framework gives ecodistricts no name of their own
    (see ``config/ecozones.py``'s module docstring), so its tooltip borrows
    the ecoregion it nests inside — which means actually knowing that
    ecoregion's name, not just its numeric id.
    """
    global _region_name_memo

    with _region_name_lock:
        if _region_name_memo is not None:
            return _region_name_memo

    ecoregion_cfg = cfg.LEVELS["ecoregion"]
    # Ecoregion is the one level guaranteed to publish both name fields (see
    # config/ecozones.py) — asserted rather than silently filtered, so a
    # future edit that drops one is a loud crash here, not a blank lookup.
    assert ecoregion_cfg.name_en_field and ecoregion_cfg.name_fr_field
    session = _session()
    r = session.get(ecoregion_cfg.featureserver + "/query", params={
        "where": "1=1",
        "outFields": ",".join([ecoregion_cfg.id_field,
                               ecoregion_cfg.name_en_field,
                               ecoregion_cfg.name_fr_field]),
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": "2000",
    }, timeout=_TIMEOUT)
    r.raise_for_status()
    payload = r.json()

    lookup: Dict[int, tuple] = {}
    for feature in payload.get("features", []):
        attrs = feature.get("attributes") or {}
        rid = attrs.get(ecoregion_cfg.id_field)
        if rid is None:
            continue
        lookup[int(rid)] = (
            (attrs.get(ecoregion_cfg.name_en_field) or "").strip(),
            # The source service embeds a stray \r\n in at least one French
            # name ("Bassin de Géorgie-Puget\r\n", verified 2026-08-28) —
            # stripped here rather than trusted, since a raw newline inside a
            # GeoJSON string property is exactly the kind of thing that reads
            # fine in a Python repr and breaks a tooltip.
            (attrs.get(ecoregion_cfg.name_fr_field) or "").strip(),
        )

    with _region_name_lock:
        _region_name_memo = lookup
    logger.info("Ecoregion name lookup ready: %s rows", len(lookup))
    return lookup


def build_geojson(level: str = "ecozone") -> dict:
    """Fetch, simplify and normalise one level's polygons.

    Blocking, a few seconds against the source service. The output carries
    only the fields the tooltip and the colour lookup need — every extra
    string field costs bytes across a few hundred (ecozone/ecoregion) to a
    couple thousand (ecodistrict) features for nothing.

    Every level's features carry ``zone_name_en``/``zone_name_pt`` — the
    *parent ecozone's* name, always, even for the ecozone level itself
    (there it is simply the feature's own name). That is what lets
    :func:`vector_spec` colour all three levels the same way, off the same
    fifteen-entry palette, with no per-level branch: 218 ecoregions or 1,025
    ecodistricts in their own distinct hues would be noise, not a legend.
    """
    if level not in cfg.LEVELS:
        raise ValueError(f"Unknown ecological-framework level: {level!r}")
    level_cfg = cfg.LEVELS[level]
    started = time.time()

    out_fields = [level_cfg.id_field, level_cfg.ecozone_id_field]
    if level_cfg.name_en_field:
        out_fields.append(level_cfg.name_en_field)
    if level_cfg.name_fr_field:
        out_fields.append(level_cfg.name_fr_field)
    if level == "ecodistrict":
        out_fields.append(cfg.ECODISTRICT_ECOREGION_ID_FIELD)

    raw = _fetch_from_featureserver(
        level_cfg.featureserver, out_fields,
        geometry_precision=level_cfg.coord_decimals)

    region_lookup = _ecoregion_name_lookup() if level == "ecodistrict" else {}

    try:
        from shapely.geometry import mapping, shape
        _shapely = True
    except ImportError:                                   # pragma: no cover
        _shapely = False

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
                tolerance_deg = level_cfg.simplify_m / 111_000.0
                geom = mapping(shape(geom).simplify(tolerance_deg,
                                                    preserve_topology=True))
            except Exception:                             # noqa: BLE001
                pass          # keep the unsimplified geometry rather than none

        cleaned = _clean_geometry(geom, level_cfg.coord_decimals)
        if cleaned is None:
            continue

        unit_id = props.get(level_cfg.id_field)
        ecozone_id = props.get(level_cfg.ecozone_id_field)
        zone_name_en = cfg.name(ecozone_id or 0, "en")
        zone_name_pt = cfg.name(ecozone_id or 0, "pt")

        if level_cfg.name_en_field:
            name_en = (props.get(level_cfg.name_en_field) or "").strip() \
                or zone_name_en
            name_fr = (props.get(level_cfg.name_fr_field) or "").strip()
            name_pt = zone_name_pt if level == "ecozone" else name_en
            parent_name_en = parent_name_fr = ""
        else:
            # Ecodistrict: no name field on the service at all. Its own
            # label is just its number; the ecoregion it nests inside — read
            # from the geometry-free lookup above — carries the meaning.
            region_id = props.get(cfg.ECODISTRICT_ECOREGION_ID_FIELD)
            parent_name_en, parent_name_fr = region_lookup.get(
                int(region_id) if region_id is not None else -1, ("", ""))
            name_en = f"{level_cfg.label_en} {unit_id}"
            name_fr = name_en
            name_pt = name_en

        features.append({
            "type": "Feature",
            "properties": {
                "unit_id": unit_id,
                "name_en": name_en,
                "name_fr": name_fr,
                "name_pt": name_pt,
                "ecozone_id": ecozone_id,
                "zone_name_en": zone_name_en,
                "zone_name_pt": zone_name_pt,
                "parent_name_en": parent_name_en,
                "parent_name_fr": parent_name_fr,
            },
            "geometry": cleaned,
        })

    logger.info("Built %s GeoJSON: %s/%s features in %.1f s",
                level, len(features), len(raw.get("features", [])),
                time.time() - started)
    return {"type": "FeatureCollection", "features": features}


def geojson_gzipped(level: str = "ecozone") -> bytes:
    """One level's simplified GeoJSON, gzip-compressed, memoised and
    disk-cached.

    Three tiers, each removing a different cost: the memo removes the disk
    read, the disk cache removes the network round trip, and the gzip is
    stored rather than recomputed because it is the same bytes every time —
    all three keyed by level, since each is an independent FeatureCollection.
    """
    if level not in cfg.LEVELS:
        raise ValueError(f"Unknown ecological-framework level: {level!r}")
    level_cfg = cfg.LEVELS[level]
    cache_path = CACHE_DIR / level_cfg.cache_filename

    with _memo_lock:
        cached = _memo.get(level)
    if cached is not None:
        return cached

    if cache_path.exists():
        try:
            payload = cache_path.read_bytes()
            with _memo_lock:
                _memo[level] = payload
            logger.info("%s GeoJSON from disk cache (%s KiB)",
                        level, len(payload) // 1024)
            return payload
        except OSError as exc:
            logger.warning("%s cache unreadable (%s) — rebuilding", level, exc)

    body = json.dumps(build_geojson(level), separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")
    payload = gzip.compress(body, 9)

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        # Written via a temporary file: two workers building this at once would
        # otherwise interleave into a corrupt gzip that then fails forever.
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_bytes(payload)
        tmp.replace(cache_path)
    except OSError as exc:
        logger.warning("Could not cache %s GeoJSON (%s) — serving from "
                       "memory", level, exc)

    with _memo_lock:
        _memo[level] = payload
    logger.info("%s GeoJSON ready: %s KiB gzipped", level, len(payload) // 1024)
    return payload


# --------------------------------------------------------------------------- #
# Layer spec
# --------------------------------------------------------------------------- #
_LEVEL_LABEL = {
    "ecozone": ("Ecozone", "Ecozona"),
    "ecoregion": ("Ecoregion", "Ecorregião"),
    "ecodistrict": ("Ecodistrict", "Ecodistrito"),
}


def vector_spec(level: str = "ecozone", *, opacity: float = 0.45,
                z_index: int = 5, show_labels: bool = True,
                lang: str = "en") -> dict:
    """Spec for the browser-side ecological-framework layer, at whichever of
    the three levels the caller picked.

    Purely declarative and involves no round trip of its own, so unlike every
    tile spec it cannot fail — the fetch happens in the browser.

    **Coloured by ``zone_name_en`` at every level**, never by the feature's
    own identity: 218 ecoregions or 1,025 ecodistricts each in their own hue
    would be a different colour every few kilometres, which is noise, not a
    legend. At the ecozone level itself this is simply its own name — see
    ``build_geojson``'s docstring.
    """
    if level not in cfg.LEVELS:
        raise ValueError(f"Unknown ecological-framework level: {level!r}")
    level_cfg = cfg.LEVELS[level]
    label_en, label_pt = _LEVEL_LABEL[level]
    name_prop = "name_pt" if lang == "pt" else "name_en"
    zone_prop = "zone_name_pt" if lang == "pt" else "zone_name_en"

    tooltip = [{"label": label_pt if lang == "pt" else label_en,
               "property": name_prop}]
    if level in ("ecoregion", "ecodistrict"):
        # A finer unit's own name says little without the ecozone it sits
        # in — the ecozone layer alone doesn't need this line, it *is* that
        # name.
        zone_label_en, zone_label_pt = _LEVEL_LABEL["ecozone"]
        tooltip.append({"label": zone_label_pt if lang == "pt" else zone_label_en,
                        "property": zone_prop})
    if level == "ecodistrict":
        # No PT gloss is maintained for 218 ecoregion names the way there is
        # for the fifteen ecozones — the English name is shown regardless of
        # UI language rather than silently going blank in Portuguese.
        region_label_en, region_label_pt = _LEVEL_LABEL["ecoregion"]
        tooltip.append({"label": region_label_pt if lang == "pt" else region_label_en,
                        "property": "parent_name_en"})
    if level == "ecozone":
        tooltip.append({"label": "Français", "property": "name_fr"})

    return {
        # The level, label and language suffixes make all three part of the
        # layer's identity, so switching any of them forces leaflet_map.js's
        # diff to rebuild rather than patch in place. Label markers are only
        # ever created at build time, so a same-id "cheap property update"
        # would silently do nothing — the note in services/biomes.py has the
        # full trace.
        "id": f"ecoframework:{level}:{lang}:{'lbl' if show_labels else 'nolbl'}",
        "path": level_cfg.geojson_path,
        "opacity": opacity,
        "z_index": z_index,
        "attribution": f"{cfg.ATTRIBUTION} — {label_en.lower()}s",
        "color_property": "zone_name_en",
        "palette": cfg.PALETTE,
        "default_color": cfg.DEFAULT_COLOR,
        "weight": cfg.OUTLINE_WIDTH,
        "label_property": name_prop if show_labels else None,
        "label_min_zoom": level_cfg.label_min_zoom,
        "tooltip": tooltip,
    }


__all__ = ["build_geojson", "geojson_gzipped", "vector_spec", "GEOJSON_PATH",
           "CACHE_DIR"]
