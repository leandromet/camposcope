"""Above-ground biomass from ESA CCI Biomass_cci v6.0, over a parcel's zones.

A near-verbatim port of :mod:`camposcope.services.biomass` — the product is
global, so nothing about it is Canadian and nothing here re-decides anything the
Brazil module already decided. Only the zone plumbing differs (this page's own
``zone_feature_collection``, so the module does not drag Brazil's MapBiomas
config in behind it).

The series has a real gap — 2007 and 2010 are isolated snapshots and it only
becomes annual in 2015 — and charts draw it as a gap. Never interpolated.

**One Canadian caveat the Brazil page does not need.** ESA CCI Biomass is a
forest above-ground biomass product, and its retrieval degrades over terrain
with persistent snow cover and over sparse northern woodland. A number returned
for a parcel in the BC interior mountains is weaker evidence than the same
number over the Amazon, and the tab's attribution line says so rather than
presenting Mg/ha with uniform confidence across a country that spans temperate
rainforest to tundra.
"""

from __future__ import annotations

import logging
from typing import Sequence, Tuple

import pandas as pd

from ...config.datasets import AGB, AGB_YEARS
from ...config.settings import EE_MAX_PIXELS, EE_TILE_SCALE
from ...services.ee_client import get_ee
from ...services.provenance import Provenance
from ...services.zones import Zone
from .ee_zones import zone_feature_collection

logger = logging.getLogger(__name__)

AGB_SCALE_M = AGB["scale_m"]           # 100 m — the product's native resolution
AGB_DATASET_ID = AGB["dataset_id"]


def _band_name(year: int) -> str:
    return f"agb_{year}"


def _stitched_image():
    """One image, one band per snapshot year — ten cheap asset opens locally,
    not ten ``reduceRegions`` calls."""
    import ee

    bands = []
    for year in AGB_YEARS:
        asset = AGB["asset_template"].format(year=year)
        # Band 0 of each asset is the AGB estimate itself (Mg/ha); the other
        # bands (SD, quality flags) are not needed here.
        bands.append(ee.Image(asset).select([0], [_band_name(year)]))
    return ee.Image.cat(bands)


def above_ground_biomass(
    zones: Sequence[Zone],
) -> Tuple[pd.DataFrame, Provenance]:
    """Mean AGB (Mg/ha) and total biomass (Mg) per zone per snapshot year.

    Reduced at 100 m, the product's native resolution: reducing at the ACI's
    30 m would not add real detail, only cost.
    """
    if not zones:
        raise ValueError("No zones to analyse.")

    get_ee()
    import ee

    img = _stitched_image()
    fc = zone_feature_collection(zones)
    bands = [_band_name(y) for y in AGB_YEARS]

    stats = (
        img.select(bands)
        .reduceRegions(collection=fc, reducer=ee.Reducer.mean(),
                       scale=AGB_SCALE_M, tileScale=EE_TILE_SCALE)
        .getInfo()
    )

    zone_labels = {z.key: z.label for z in zones}
    zone_areas = {z.key: z.area_ha for z in zones}

    records = []
    for feat in stats["features"]:
        props = feat["properties"]
        zone_key = props["zone_key"]
        area_ha = zone_areas.get(zone_key, 0.0)
        for year in AGB_YEARS:
            mean_val = props.get(_band_name(year))
            if mean_val is None:
                continue                       # no coverage for this zone/year
            records.append({
                "zone_key": zone_key,
                "zone_label": zone_labels.get(zone_key, zone_key),
                "year": year,
                "agb_mean_mgha": float(mean_val),
                "area_ha": area_ha,
                "total_biomass_mg": float(mean_val) * area_ha,
            })

    df = pd.DataFrame.from_records(
        records,
        columns=["zone_key", "zone_label", "year", "agb_mean_mgha", "area_ha",
                 "total_biomass_mg"],
    )
    if not df.empty:
        order = {z.key: i for i, z in enumerate(zones)}
        df["_zone_order"] = df["zone_key"].map(order)
        df = df.sort_values(["_zone_order", "year"]).drop(columns="_zone_order")
        df = df.reset_index(drop=True)

    prov = Provenance(
        name="esa_cci_biomass",
        dataset_id=AGB_DATASET_ID,
        bands=bands,
        scale_m=AGB_SCALE_M,
        reducer="mean",
        pixel_area_basis="zone geometry area (canada/services/zones.py, BC Albers)",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={
            "zones": [z.key for z in zones],
            "years": AGB_YEARS,
            "gap_note": (
                "The series has a real gap: 2007 and 2010 are isolated "
                "snapshots and it is annual only from 2015. Do not interpolate."
            ),
            "canada_note": (
                "Retrieval degrades over terrain with persistent snow cover and "
                "over sparse northern woodland — a value from the BC interior "
                "mountains carries less confidence than the same value over "
                "closed temperate forest."
            ),
            "attribution": AGB["attribution"],
        },
    )
    return df, prov


__all__ = ["above_ground_biomass", "AGB_SCALE_M", "AGB_DATASET_ID"]
