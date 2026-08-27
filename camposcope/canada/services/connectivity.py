"""Fragment-to-fragment connectivity, per zone — the costly proxy.

A port of :mod:`camposcope.services.connectivity` onto the AAFC legend, with the
same split of responsibilities: ``landscape_metrics`` always computes
``meff_ha`` because it falls out of a connected-components image it already
builds, while the true mean Euclidean nearest-neighbour distance (FRAGSTATS'
ENN_MN) costs an extra Earth Engine round trip per zone plus a local geometry
search, and therefore sits behind its own button.

**What counts as a fragment is a legend decision, and here it is an easy one.**
The Brazil module has to reach into a provisional, unvalidated MapBiomas class
grouping (``LEGEND_VALIDATED = False``) to decide what "forest" means. The ACI
encodes its hierarchy in its numbering, so ``aafc.FOREST`` — coniferous,
broadleaf, mixedwood and the undifferentiated class — is read straight off the
published legend rather than inferred.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence, Tuple

import pandas as pd

from ...config.settings import EE_DEFAULT_SCALE_M, EE_MAX_PIXELS, EE_TILE_SCALE
from ...services.ee_client import get_ee
from ...services.provenance import Provenance
from ...services.zones import Zone
from ..config import aafc
from .aci_history import ACI_ASSET, aci_year_image

logger = logging.getLogger(__name__)

CONNECTIVITY_COLUMNS = ["zone_key", "zone_label", "n_fragments", "enn_mean_m",
                        "enn_median_m"]

#: Fragments smaller than this are classification slivers, not fragments anyone
#: means by "connectivity between fragments".
MIN_FRAGMENT_PIXELS = 9

#: Hard ceiling on fragments per zone. A 5 km ring around a parcel in the BC
#: interior can hold thousands of forest patches, and an unbounded fetch turns
#: "slower" into "the request never returns". The result still reports what it
#: saw, marked degraded.
MAX_FRAGMENTS_PER_ZONE = 600


def _forest_mask(image):
    codes = sorted(aafc.FOREST_FORMATIONS)
    return image.remap(codes, [1] * len(codes), 0).selfMask().rename("forest")


def fragment_connectivity(
    zones: Sequence[Zone],
    year: int = aafc.ACI_YEAR_END,
    max_fragments: int = MAX_FRAGMENTS_PER_ZONE,
) -> Tuple[pd.DataFrame, Provenance]:
    """Mean/median Euclidean nearest-neighbour distance between forest
    fragments, one row per zone.

    Distance is edge-to-edge between fragment *polygons* (not centroids), on a
    single local azimuthal-equidistant projection centred on the parcel's own
    centroid — shared across every zone so a fragment straddling a ring boundary
    is measured consistently either side of it.
    """
    import ee
    from pyproj import Transformer
    from shapely.geometry import shape as shp_shape
    from shapely.ops import transform as shp_transform
    from shapely.strtree import STRtree

    if not zones:
        raise ValueError("No zones to analyse.")

    get_ee()

    image = aci_year_image(year).rename("class")
    forest = _forest_mask(image)

    parcel_centroid = shp_shape(zones[0].geojson).centroid
    aeqd = (f"+proj=aeqd +lat_0={parcel_centroid.y} +lon_0={parcel_centroid.x} "
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
                            "n_fragments": n, "enn_mean_m": None,
                            "enn_median_m": None})
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
                            "n_fragments": n, "enn_mean_m": None,
                            "enn_median_m": None})
            continue

        series = pd.Series(distances)
        records.append({
            "zone_key": zone.key, "zone_label": zone.label, "n_fragments": n,
            "enn_mean_m": float(series.mean()),
            "enn_median_m": float(series.median()),
        })

    # A None next to real floats becomes pandas NaN when built column by column
    # — and this frame reaches Reflex state as JSON, where NaN is not legal.
    df = pd.DataFrame.from_records(records, columns=CONNECTIVITY_COLUMNS)
    df = df.where(pd.notnull(df), None)

    prov = Provenance(
        name="fragment_connectivity",
        dataset_id=ACI_ASSET,
        bands=[aafc.band_for_year(year)],
        scale_m=EE_DEFAULT_SCALE_M,
        reducer="reduceToVectors + local nearest-neighbour (shapely STRtree)",
        pixel_area_basis="n/a — vector polygons, planar AEQD metres",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={
            "year": year, "zones": [z.key for z in zones],
            "forest_classes": sorted(aafc.FOREST_FORMATIONS),
            "min_fragment_pixels": MIN_FRAGMENT_PIXELS,
            "max_fragments_per_zone": max_fragments,
        },
    )
    if degraded_zones:
        prov.degrade(
            f"Zone(s) {', '.join(degraded_zones)} held more than "
            f"{max_fragments} forest fragments; the nearest-neighbour distance "
            f"considered only the first {max_fragments} Earth Engine returned, "
            "not all of them."
        )
    logger.info("Fragment connectivity: %s zones (%s degraded)",
                len(df), len(degraded_zones))
    return df, prov


__all__ = ["fragment_connectivity", "CONNECTIVITY_COLUMNS",
           "MIN_FRAGMENT_PIXELS", "MAX_FRAGMENTS_PER_ZONE"]
