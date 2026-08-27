"""Zones as an Earth Engine ``FeatureCollection``.

One helper, shared by every analysis service on this page — the Canadian
equivalent of ``camposcope.services.mapbiomas_history::_zone_feature_collection``,
lifted out into its own module rather than imported from there.

**Why not just import the Brazil one.** It is a five-line function and the
duplication is real, but importing it would make every Canadian analysis service
depend on the MapBiomas history module: its import of
``config/mapbiomas.py`` and ``config/datasets.py`` would be pulled in to build a
FeatureCollection that has nothing to do with either. A module that imports
Brazil's land-cover legend to analyse a BC parcel is the kind of coupling that
looks harmless until someone changes the legend.

Geometries travel to Earth Engine **inline**, as GeoJSON already computed
locally by :mod:`canada.services.zones` — never as an uploaded asset. Same
reasoning as the Brazil page: a cadastral boundary fetched at request time and
uploaded as an EE asset is immediately a stale private copy of official data.
"""

from __future__ import annotations

from typing import Sequence

from ...services.zones import Zone


def zone_feature_collection(zones: Sequence[Zone]):
    """One feature per zone, carrying the keys every parser downstream reads."""
    import ee

    return ee.FeatureCollection([
        ee.Feature(ee.Geometry(z.geojson), {
            "zone_key": z.key,
            "zone_label": z.label,
            "zone_kind": z.kind,
        })
        for z in zones
    ])


def mean_pixel_area(fc, scale: int, tile_scale: int):
    """Mean true pixel area (m²) inside each zone.

    The area basis every service on this page uses, and the reason none of them
    assumes a flat 0.09 ha per pixel: Canada spans 41°N to 83°N and true pixel
    area falls off sharply with latitude. Within a single zone the variation is
    far smaller than the classification error, so ``count × mean_pixel_area`` is
    exact for practical purposes — and it costs one cheap round trip that is
    always issued in parallel with the histogram it accompanies.
    """
    import ee

    return ee.Image.pixelArea().reduceRegions(
        collection=fc,
        reducer=ee.Reducer.mean(),
        scale=scale,
        tileScale=tile_scale,
    ).getInfo()


def px_area_by_zone(areas: dict, default_m2: float = 900.0) -> dict:
    """``{zone_key: mean_pixel_area_m2}`` from a :func:`mean_pixel_area` result."""
    return {
        f["properties"]["zone_key"]: float(f["properties"].get("mean") or default_m2)
        for f in (areas or {}).get("features", [])
    }


__all__ = ["zone_feature_collection", "mean_pixel_area", "px_area_by_zone"]
