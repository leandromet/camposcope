"""Tile-URL specs for the map: XYZ basemaps, Earth Engine basemaps, and the
per-tab analysis overlays (MapBiomas year, Hansen, biomass).

Ported from Naturametrics' ``services/layers.py``, trimmed and reshaped to
Camposcope's needs. Every ``*_spec`` function here is blocking (a ``getMapId``
round trip on a cache miss) and must be run off the event loop — see
``state/_layers.py`` for the background-handler pattern every caller uses.
Plain XYZ basemaps are the one exception: no Earth Engine involved, so
:func:`basemap_spec` never fails slowly.

**Why a tile layer per tab, not one static overlay.** The active results tab
names a specific question — land cover this year, forest loss, biomass — and
the map should show exactly that layer, not everything at once. Each `*_spec`
function is independent and cached by ``services/tiles.py``, so switching tabs
back and forth costs one round trip in total, the same guarantee the SPOT
basemap already gives.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..config import datasets as ds
from ..config import mapbiomas as mb
from ..config.settings import HANSEN_TREECOVER_THRESHOLD
from .tiles import get_tile_url

logger = logging.getLogger(__name__)


def basemap_spec(key: str, *, z_index: int = 0) -> Optional[Dict[str, Any]]:
    """Plain XYZ basemap — infallible, synchronous."""
    conf = ds.BASEMAPS.get(key)
    if conf is None:
        logger.warning("Unknown XYZ basemap %r", key)
        return None
    return {
        "id": f"basemap:{key}",
        "url": conf["url"],
        "opacity": 1.0,
        "attribution": conf["attribution"],
        "z_index": z_index,
        "max_native_zoom": conf.get("max_native_zoom", 19),
    }


def ee_basemap_spec(key: str, *, z_index: int = 1) -> Optional[Dict[str, Any]]:
    """Mint an Earth Engine basemap (the SPOT 2008 mosaics).

    Blocking, so callers run it off the event loop. Cached like every other
    tile URL (services/tiles.py), so switching back and forth costs one round
    trip in total. Returns ``None`` on any failure — including the licence
    gate — so the caller can fail closed rather than show a broken layer.
    """
    conf = ds.EE_BASEMAPS.get(key)
    if conf is None:
        logger.warning("Unknown Earth Engine basemap %r", key)
        return None

    def build():
        import ee
        return ee.Image(conf["asset"])

    try:
        url = get_tile_url(f"basemap:{key}", build, conf["vis"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("EE basemap %s failed: %s", key, exc)
        return None
    if url is None:
        return None

    return {
        "id": f"basemap:{key}",
        "url": url,
        "opacity": 1.0,
        "attribution": conf["attribution"],
        "z_index": z_index,
        "max_native_zoom": conf.get("max_native_zoom", 16),
    }


def mapbiomas_year_spec(
    year: int, *, opacity: float = 0.75, z_index: int = 10,
) -> Optional[Dict[str, Any]]:
    """MapBiomas land cover for one year — the Cobertura tab's map layer."""
    if year not in mb.MAPBIOMAS_YEARS:
        logger.warning("MapBiomas year %s outside %s–%s", year,
                       mb.MAPBIOMAS_YEAR_START, mb.MAPBIOMAS_YEAR_END)
        return None

    asset = mb.MAPBIOMAS_COLLECTIONS[mb.MAPBIOMAS_DEFAULT_COLLECTION]
    cache_key = f"mapbiomas:{mb.MAPBIOMAS_DEFAULT_COLLECTION}:{year}"

    def build():
        import ee
        return ee.Image(asset).select(mb.band_for_year(year))

    try:
        url = get_tile_url(cache_key, build, mb.MAPBIOMAS_VIS)
    except Exception as exc:                       # noqa: BLE001
        logger.warning("MapBiomas layer %s failed: %s", year, exc)
        return None
    if url is None:
        return None

    return {
        "id": cache_key, "url": url, "opacity": opacity, "z_index": z_index,
        "attribution": "MapBiomas Coleção 10.1", "max_native_zoom": 15,
    }


def hansen_treecover_spec(
    *, threshold: int = HANSEN_TREECOVER_THRESHOLD, opacity: float = 0.6,
    z_index: int = 15,
) -> Optional[Dict[str, Any]]:
    """Tree cover in 2000, masked at the canopy-cover threshold — the base
    layer under the Floresta tab, showing what there was to lose."""
    cache_key = f"hansen_tc:{threshold}"

    def build():
        import ee
        gfc = ee.Image(ds.HANSEN_GFC["asset"])
        treecover = gfc.select("treecover2000")
        return treecover.updateMask(treecover.gte(threshold))

    try:
        url = get_tile_url(cache_key, build, ds.HANSEN_GFC["treecover_vis"])
    except Exception as exc:                       # noqa: BLE001
        logger.warning("Hansen treecover layer failed: %s", exc)
        return None
    if url is None:
        return None

    return {
        "id": cache_key, "url": url, "opacity": opacity, "z_index": z_index,
        "attribution": ds.HANSEN_GFC["attribution"], "max_native_zoom": 13,
    }


def hansen_change_spec(
    from_year: int, *, threshold: int = HANSEN_TREECOVER_THRESHOLD,
    opacity: float = 0.85, z_index: int = 16,
) -> Optional[Dict[str, Any]]:
    """Loss since ``from_year`` (red) and gain (green, undated), one
    categorical band — the Floresta tab's map layer.

    Loss is gated by the same canopy threshold as the tree-cover layer (a
    pixel that was never forest cannot lose it); gain is not — Hansen
    publishes it as one undated flag with no canopy percentage to threshold
    against (doc/04-data-sources.md §3).
    """
    year_start = ds.HANSEN_GFC["loss_year_start"]
    year_end = ds.HANSEN_GFC["loss_year_end"]
    if not (year_start <= from_year <= year_end):
        logger.warning("Hansen loss year %s outside %s–%s",
                       from_year, year_start, year_end)
        return None

    cache_key = f"hansen_change:{from_year}:{threshold}"

    def build():
        import ee
        gfc = ee.Image(ds.HANSEN_GFC["asset"])
        forest2000 = gfc.select("treecover2000").gte(threshold)
        code = from_year - year_start + 1
        loss = (gfc.select("loss").eq(1).And(forest2000)
               .And(gfc.select("lossyear").gte(code)))
        gain = gfc.select("gain").eq(1)
        return ee.Image(0).where(gain, 2).where(loss, 1).selfMask().rename("change")

    vis = {"min": 1, "max": 2,
          "palette": [ds.HANSEN_GFC["loss_color"].lstrip("#"),
                     ds.HANSEN_GFC["gain_color"].lstrip("#")]}
    try:
        url = get_tile_url(cache_key, build, vis)
    except Exception as exc:                       # noqa: BLE001
        logger.warning("Hansen change layer failed: %s", exc)
        return None
    if url is None:
        return None

    return {
        "id": cache_key, "url": url, "opacity": opacity, "z_index": z_index,
        "attribution": (f"{ds.HANSEN_GFC['attribution']} — perda "
                        f"{from_year}–{year_end}, ganho (não datado)"),
        "max_native_zoom": 13,
    }


def biomass_year_spec(
    year: int, *, opacity: float = 0.75, z_index: int = 14,
) -> Optional[Dict[str, Any]]:
    """ESA CCI above-ground biomass for one year — the Biomassa tab's map
    layer. Ten non-contiguous years (config.datasets.AGB_YEARS), so unlike
    MapBiomas this is never worth a prefetch sweep."""
    from ..config.datasets import AGB, AGB_YEARS

    if year not in AGB_YEARS:
        logger.warning("Biomass year %s not in %s", year, AGB_YEARS)
        return None

    cache_key = f"biomass:{year}"

    def build():
        import ee
        return ee.Image(AGB["asset_template"].format(year=year)).select([0])

    try:
        url = get_tile_url(cache_key, build, AGB["vis"])
    except Exception as exc:                       # noqa: BLE001
        logger.warning("Biomass layer %s failed: %s", year, exc)
        return None
    if url is None:
        return None

    return {
        "id": cache_key, "url": url, "opacity": opacity, "z_index": z_index,
        "attribution": AGB["attribution"], "max_native_zoom": 12,
    }


def ibge_vegetation_spec(
    *, opacity: float = 1.0, z_index: int = 20,
) -> Optional[Dict[str, Any]]:
    """IBGE Vegetação 2022, rasterized once (services/ibge_vegetation.py) —
    the SPOT/IBGE comparison tab's left-hand layer for the "ibge_2022" mode.
    A single snapshot, so the cache key carries no year."""
    from .ibge_vegetation import classified_image

    cache_key = "ibge_vegetation:leg2"

    def build():
        return classified_image()

    from ..config.ibge_vegetation import IBGE_VEG_ATTRIBUTION, IBGE_VEG_VIS

    try:
        url = get_tile_url(cache_key, build, IBGE_VEG_VIS)
    except Exception as exc:                       # noqa: BLE001
        logger.warning("IBGE vegetation layer failed: %s", exc)
        return None
    if url is None:
        return None

    return {
        "id": cache_key, "url": url, "opacity": opacity, "z_index": z_index,
        "attribution": IBGE_VEG_ATTRIBUTION, "max_native_zoom": 13,
    }


def fire_frequency_spec(
    *, opacity: float = 0.75, z_index: int = 12,
) -> Optional[Dict[str, Any]]:
    """Fire frequency from MapBiomas Fire Collection 5 (1985-2025) — count of fire
    occurrences with an orange-red-darkred gradient (0-41 range). The Fogo tab's map
    layer. The source asset carries 81 bands (one per partial window MapBiomas
    publishes); only the full-period band is drawn here (services/fire.py)."""
    from .fire import FIRE_FREQUENCY_DATASET_ID, _FIRE_FREQUENCY_BAND, _FIRE_FREQUENCY_MAX

    cache_key = "fire_frequency"

    def build():
        import ee
        return ee.Image(FIRE_FREQUENCY_DATASET_ID).select(_FIRE_FREQUENCY_BAND)

    # Matches components/map_legend.py's gradient bar exactly, so the
    # on-map colours and the legend swatch never drift apart.
    vis = {
        "min": 0, "max": _FIRE_FREQUENCY_MAX,
        "palette": ["ffffff", "ffffb2", "fecc5c", "fd8d3c", "f03b20", "bd0026"],
    }

    try:
        url = get_tile_url(cache_key, build, vis)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fire frequency layer failed: %s", exc)
        return None
    if url is None:
        return None

    return {
        "id": cache_key, "url": url, "opacity": opacity, "z_index": z_index,
        "attribution": "MapBiomas Fogo Coleção 5 (CC BY-SA 4.0) · escala 30 m",
        "max_native_zoom": 13,
    }


__all__ = [
    "basemap_spec", "ee_basemap_spec", "ibge_vegetation_spec",
    "mapbiomas_year_spec", "hansen_treecover_spec", "hansen_change_spec",
    "biomass_year_spec", "fire_frequency_spec",
]
