"""Fragment-to-fragment connectivity, per zone — the costly proxy.

``services.landscape_metrics`` always computes ``meff_ha`` (effective mesh
size), a connectivity/fragmentation proxy that is essentially free: it reuses
the connected-components image already built for ``largest_patch_ha``.

The metric people usually mean by "connectivity between fragments" —
FRAGSTATS' mean Euclidean nearest-neighbour distance (ENN_MN) — is a
different, pricier computation, ported here from Naturametrics'
``services/connectivity.py`` and reshaped from buffers to zones the same way
``services/mapbiomas_history.py`` was:

1. Vectorises each zone's forest pixels into patch polygons with one
   ``reduceToVectors`` call per zone (an Earth Engine round trip
   ``landscape_metrics`` does not need at all).
2. Brings those polygons home and finds each one's nearest same-zone
   neighbour **locally**, with a shapely ``STRtree`` — reprojected to a local
   planar (AEQD) CRS centred on the property, so that "metres" means metres.

That is one Earth Engine call plus a local geometry search per zone, against
``landscape_metrics``' single shared call across every zone at once — costly
enough that this sits behind its own button (``state.run_connectivity``),
never folded into the automatic fetch.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence, Tuple

import pandas as pd

from ..config import mapbiomas as mb
from ..config.settings import EE_DEFAULT_SCALE_M, EE_MAX_PIXELS, EE_TILE_SCALE
from .ee_client import get_ee
from .provenance import Provenance
from .zones import Zone

logger = logging.getLogger(__name__)

#: One row per zone.
CONNECTIVITY_COLUMNS = ["zone_key", "zone_label", "n_fragments", "enn_mean_m",
                        "enn_median_m"]

#: Fragments smaller than this are classification slivers, not fragments
#: anyone means by "connectivity between fragments" — ported unchanged from
#: Naturametrics' equivalent judgement call.
MIN_FRAGMENT_PIXELS = 9

#: Hard ceiling on how many fragments the nearest-neighbour search runs over,
#: per zone — same reasoning as Naturametrics' ``MAX_FRAGMENTS_PER_RADIUS``:
#: a heavily fragmented ring can hold thousands of forest patches, and an
#: unbounded fetch can turn "slower" into "the request never returns". The
#: result still reports what it saw, marked degraded
#: (``Provenance.degrade``), same posture as ``services/exports.py``.
MAX_FRAGMENTS_PER_ZONE = 600


def _forest_mask(image):
    codes = sorted(mb.FOREST_FORMATIONS)
    return image.remap(codes, [1] * len(codes), 0).selfMask().rename("forest")


def fragment_connectivity(
    zones: Sequence[Zone],
    year: int = mb.MAPBIOMAS_YEAR_END,
    max_fragments: int = MAX_FRAGMENTS_PER_ZONE,
) -> Tuple[pd.DataFrame, Provenance]:
    """Mean/median Euclidean nearest-neighbour distance between forest
    fragments (:data:`mb.FOREST_FORMATIONS`), one row per zone.

    Distance is edge-to-edge between fragment *polygons* (not centroids), on
    a single local azimuthal-equidistant projection centred on the
    property's own centroid — shared across every zone (rings included) so
    that a fragment straddling a ring boundary is measured consistently
    either side of it.
    """
    import ee
    from pyproj import Transformer
    from shapely.geometry import shape as shp_shape
    from shapely.ops import transform as shp_transform
    from shapely.strtree import STRtree

    if not zones:
        raise ValueError("Nenhuma zona para analisar.")

    get_ee()

    image = ee.Image(mb.MAPBIOMAS_COLLECTIONS[mb.MAPBIOMAS_DEFAULT_COLLECTION]).select(
        mb.band_for_year(year)).rename("class")
    forest = _forest_mask(image)

    property_centroid = shp_shape(zones[0].geojson).centroid
    aeqd = (f"+proj=aeqd +lat_0={property_centroid.y} +lon_0={property_centroid.x} "
           f"+units=m +datum=WGS84 +no_defs")
    to_aeqd = Transformer.from_crs("EPSG:4326", aeqd, always_xy=True).transform
    min_area_m2 = MIN_FRAGMENT_PIXELS * (EE_DEFAULT_SCALE_M ** 2)

    records: List[Dict[str, Any]] = []
    degraded_zones: List[str] = []

    for zone in zones:
        geom = ee.Geometry(zone.geojson)
        vectors = forest.reduceToVectors(
            geometry=geom, scale=EE_DEFAULT_SCALE_M, geometryType="polygon",
            eightConnected=True, maxPixels=EE_MAX_PIXELS, tileScale=EE_TILE_SCALE,
        )
        # +1 so a count of exactly max_fragments+1 still reads as "capped"
        # rather than silently passing as "all of them".
        info = vectors.limit(max_fragments + 1).getInfo()
        features = info.get("features", [])
        capped = len(features) > max_fragments
        if capped:
            features = features[:max_fragments]
            degraded_zones.append(zone.label)

        polys_m = []
        for feat in features:
            geom_m = shp_transform(to_aeqd, shp_shape(feat["geometry"]))
            if geom_m.area >= min_area_m2:
                polys_m.append(geom_m)

        n = len(polys_m)
        if n < 2:
            records.append({"zone_key": zone.key, "zone_label": zone.label,
                            "n_fragments": n, "enn_mean_m": None, "enn_median_m": None})
            continue

        tree = STRtree(polys_m)
        distances = []
        for geom_m in polys_m:
            idx, dist = tree.query_nearest(
                geom_m, exclusive=True, return_distance=True, all_matches=False)
            if len(idx):
                distances.append(float(dist[0]))
        if not distances:
            records.append({"zone_key": zone.key, "zone_label": zone.label,
                            "n_fragments": n, "enn_mean_m": None, "enn_median_m": None})
            continue

        series = pd.Series(distances)
        records.append({
            "zone_key": zone.key, "zone_label": zone.label, "n_fragments": n,
            "enn_mean_m": float(series.mean()), "enn_median_m": float(series.median()),
        })

    # A None next to real floats in the same column becomes pandas NaN when
    # built column-by-column — and this frame reaches Reflex state as JSON,
    # where NaN is not legal. Swap it back to None (see the identical note in
    # Naturametrics' connectivity.py).
    df = pd.DataFrame.from_records(records, columns=CONNECTIVITY_COLUMNS)
    df = df.where(pd.notnull(df), None)

    prov = Provenance(
        name="fragment_connectivity",
        dataset_id=mb.MAPBIOMAS_COLLECTIONS[mb.MAPBIOMAS_DEFAULT_COLLECTION],
        bands=[mb.band_for_year(year)],
        scale_m=EE_DEFAULT_SCALE_M,
        reducer="reduceToVectors + local nearest-neighbour (shapely STRtree)",
        pixel_area_basis="n/a — vector polygons, planar AEQD metres",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={
            "year": year, "zones": [z.key for z in zones],
            "forest_classes": sorted(mb.FOREST_FORMATIONS),
            "min_fragment_pixels": MIN_FRAGMENT_PIXELS,
            "max_fragments_per_zone": max_fragments,
        },
    )
    if degraded_zones:
        prov.degrade(
            f"Zona(s) {', '.join(degraded_zones)} tinham mais de {max_fragments} "
            f"fragmentos de floresta; a distância ao vizinho mais próximo "
            f"considerou só os primeiros {max_fragments} retornados pelo Earth "
            f"Engine, não a totalidade."
        )
    logger.info("Fragment connectivity: %s zones (%s degraded)", len(df),
               len(degraded_zones))
    return df, prov


__all__ = ["fragment_connectivity", "CONNECTIVITY_COLUMNS", "MIN_FRAGMENT_PIXELS",
          "MAX_FRAGMENTS_PER_ZONE"]
