"""Tile-URL specs for the map: XYZ basemaps and Earth Engine basemaps.

Ported from Naturametrics' ``services/layers.py``, trimmed to what Camposcope
uses. Plain XYZ basemaps never fail slowly — no Earth Engine involved, so the
very first paint never waits on a network call. Earth-Engine-backed basemaps
(the SPOT 2008 mosaics, doc/12-spot-2008.md) go through
:func:`ee_basemap_spec`, which is blocking and must be run off the event loop.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..config import datasets as ds
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


__all__ = ["basemap_spec", "ee_basemap_spec"]
