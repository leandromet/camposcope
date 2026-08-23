"""Above-ground biomass from ESA CCI Biomass_cci v6.0 (doc/04-data-sources.md §4).

Ten snapshots, not a continuous series — 2007, 2010, then annual 2015–2022,
each its own Earth Engine asset. The first thing this module does is stitch
them into one multi-band image (one band per year), which turns "ten years ×
N zones" back into the single ``reduceRegions`` round trip everything else in
this app relies on.

Ported from Naturametrics with the same reasoning; reshaped from buffers to
zones. The gap in the series (2011–2014 missing, and only two points before
2015) is real — charts must draw it as a gap, never interpolate.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Sequence, Tuple

import pandas as pd

from ..config.datasets import AGB, AGB_YEARS
from ..config.settings import EE_MAX_PIXELS, EE_TILE_SCALE
from .ee_client import get_ee
from .mapbiomas_history import _zone_feature_collection
from .provenance import Provenance
from .zones import Zone

logger = logging.getLogger(__name__)

AGB_SCALE_M = AGB["scale_m"]           # 100 m — the product's native resolution
AGB_DATASET_ID = AGB["dataset_id"]


def _band_name(year: int) -> str:
    return f"agb_{year}"


def _stitched_image():
    """One image, one band per snapshot year — costs ten cheap asset opens
    locally, not ten reduceRegions calls."""
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

    Returns a long-format frame — ``zone_key, zone_label, year, agb_mean_mgha,
    area_ha, total_biomass_mg`` — plus provenance. Reduced at 100 m, the
    product's native resolution: reducing at MapBiomas' 30 m would not add
    real detail, only cost.
    """
    if not zones:
        raise ValueError("Nenhuma zona para analisar.")

    get_ee()
    import ee

    img = _stitched_image()
    fc = _zone_feature_collection(zones)
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
        pixel_area_basis="zone geometry area (services/zones.py)",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={
            "zones": [z.key for z in zones],
            "years": AGB_YEARS,
            "gap_note": (
                "série com lacuna: 2007 e 2010 são pontos isolados; anual "
                "apenas a partir de 2015. Não interpolar."
            ),
            "attribution": AGB["attribution"],
        },
    )
    return df, prov


__all__ = ["above_ground_biomass", "AGB_SCALE_M", "AGB_DATASET_ID"]
