"""Hansen Global Forest Change over a parcel's zones — dated loss, split at the
parcel's own start date; undated gain, kept separate.

A port of :mod:`camposcope.services.hansen` with the anchor replaced. The Brazil
version buckets loss against **two** dates: the Código Florestal's 22 July 2008
reference date, and the property's CAR registration. Canada has neither.

**What replaces them, and what happens when it is missing.** ``PARCEL_START_DATE``
from the parcel fabric is the one date specific to this parcel rather than to a
dataset, so it plays the role the CAR registration date plays in Brazil. But it
is **null for most BC parcels** (see ``pmbc.Parcel.start_year``), so this module
produces one of two shapes, and always says which:

``PERIOD_BEFORE_PARCEL`` / ``PERIOD_AFTER_PARCEL``
    When the parcel has a start year inside Hansen's own 2001–2025 record. Loss
    is split at it, exactly as the Brazil chart splits at registration.

``PERIOD_UNDIVIDED``
    When there is no start date, or it falls outside the Hansen record (a parcel
    created in 1974 is "before" the whole series and splitting at it would put
    every row in one bucket while implying a division existed). Every loss year
    lands in this single bucket and the tab shows a plain annual series with a
    note saying the cadastre carries no date to split on.

The alternative — substituting a plausible default year — was rejected: it would
put real forest loss in the wrong bucket with nothing on screen to say so.

**Gain is never summed with loss.** It is a single undated 2000–2012 layer, the
same trap the Brazil module documents; putting it on the same timeline as dated
loss would misrepresent both.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from ...config.datasets import HANSEN_GFC
from ...config.settings import EE_MAX_PIXELS, EE_TILE_SCALE
from ...services.ee_client import get_ee
from ...services.provenance import Provenance
from ...services.zones import Zone
from ..config.datasets import NTEMS_AGE
from .ee_zones import mean_pixel_area, px_area_by_zone, zone_feature_collection
from .zones import PARCEL_ZONE_KEY

logger = logging.getLogger(__name__)

HANSEN_ASSET = HANSEN_GFC["asset"]
LOSS_YEAR_START = HANSEN_GFC["loss_year_start"]
LOSS_YEAR_END = HANSEN_GFC["loss_year_end"]
#: Hansen's own native resolution.
HANSEN_SCALE_M = 30

PERIOD_BEFORE_PARCEL = "antes_da_parcela"
PERIOD_AFTER_PARCEL = "apos_a_parcela"
PERIOD_UNDIVIDED = "sem_divisao"


def splits_at(parcel_year: Optional[int]) -> Optional[int]:
    """The year loss is actually split at, or ``None`` for an undivided series.

    A start year outside Hansen's record cannot divide it — see the module
    docstring. Kept as a function rather than inlined so the UI can ask the same
    question the analysis asks, and the note it shows can never disagree with
    the buckets the chart draws.
    """
    if not parcel_year:
        return None
    if not (LOSS_YEAR_START < int(parcel_year) <= LOSS_YEAR_END):
        return None
    return int(parcel_year)


def _period(year: int, split_year: Optional[int]) -> str:
    if split_year is None:
        return PERIOD_UNDIVIDED
    return PERIOD_BEFORE_PARCEL if year < split_year else PERIOD_AFTER_PARCEL


def forest_change(
    zones: Sequence[Zone], *, parcel_year: Optional[int] = None,
) -> Tuple[pd.DataFrame, float, Provenance]:
    """Loss by year, bucketed against the parcel's start date, and gain, per zone.

    Returns ``(loss_df, gain_total_ha, provenance)``. ``loss_df`` columns:
    ``zone_key, zone_label, year, area_ha, period`` — long format, one row per
    zone per loss year, so the chart can colour by period without a second
    query.
    """
    if not zones:
        raise ValueError("No zones to analyse.")

    get_ee()
    import ee

    from concurrent.futures import ThreadPoolExecutor

    split_year = splits_at(parcel_year)
    img = ee.Image(HANSEN_ASSET)
    fc = zone_feature_collection(zones)

    def hist_call():
        return (
            img.select(["lossyear", "gain"])
            .reduceRegions(collection=fc,
                           reducer=ee.Reducer.frequencyHistogram(),
                           scale=HANSEN_SCALE_M, tileScale=EE_TILE_SCALE)
            .getInfo()
        )

    with ThreadPoolExecutor(max_workers=2) as ex:
        f_hist = ex.submit(hist_call)
        f_area = ex.submit(mean_pixel_area, fc, HANSEN_SCALE_M, EE_TILE_SCALE)
        hist, areas = f_hist.result(), f_area.result()

    px_area = px_area_by_zone(areas)
    zone_labels = {z.key: z.label for z in zones}

    loss_records: List[Dict[str, Any]] = []
    gain_total_ha = 0.0

    for feat in hist["features"]:
        props = feat["properties"]
        zone_key = props["zone_key"]
        area_per_px_ha = px_area.get(zone_key, 900.0) / 10_000.0

        loss_hist: Dict[str, float] = props.get("lossyear") or {}
        for code, count in loss_hist.items():
            code_i = int(float(code))
            if code_i <= 0:                       # 0 = no loss recorded
                continue
            year = 2000 + code_i
            area_ha = float(count) * area_per_px_ha
            if area_ha <= 0:
                continue
            loss_records.append({
                "zone_key": zone_key,
                "zone_label": zone_labels.get(zone_key, zone_key),
                "year": year,
                "area_ha": area_ha,
                "period": _period(year, split_year),
            })

        gain_hist: Dict[str, float] = props.get("gain") or {}
        gain_count = float(gain_hist.get("1", 0.0))
        # Gain total is reported for the parcel only — a ring's gain is context
        # the chart has no room for and the number would read as the parcel's.
        if zone_key == PARCEL_ZONE_KEY:
            gain_total_ha = gain_count * area_per_px_ha

    loss_df = pd.DataFrame.from_records(
        loss_records,
        columns=["zone_key", "zone_label", "year", "area_ha", "period"],
    )
    if not loss_df.empty:
        order = {z.key: i for i, z in enumerate(zones)}
        loss_df["_zone_order"] = loss_df["zone_key"].map(order)
        loss_df = loss_df.sort_values(["_zone_order", "year"]).drop(
            columns="_zone_order"
        ).reset_index(drop=True)

    prov = Provenance(
        name="hansen_forest_change",
        dataset_id=HANSEN_ASSET,
        bands=["lossyear", "gain"],
        scale_m=HANSEN_SCALE_M,
        reducer="frequencyHistogram",
        pixel_area_basis="mean ee.Image.pixelArea() per zone",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={
            "zones": [z.key for z in zones],
            "loss_year_range": [LOSS_YEAR_START, LOSS_YEAR_END],
            "parcel_start_year": parcel_year,
            "split_year": split_year,
            "split_note": (
                "Loss is split at the parcel's own start date."
                if split_year else
                "The parcel fabric carries no start date inside the Hansen "
                "record, so the loss series is not divided. No default anchor "
                "year was substituted."
            ),
            "gain_note": (
                "gain is a single UNDATED layer (2000-2012) and is never summed "
                "with dated loss."
            ),
        },
    )
    return loss_df, gain_total_ha, prov


# --------------------------------------------------------------------------- #
# NTEMS stand age — the Canadian bonus panel
# --------------------------------------------------------------------------- #
def stand_age(zones: Sequence[Zone]) -> Tuple[pd.DataFrame, Provenance]:
    """Mean/median NTEMS forest age per zone, and the forested share.

    Something the Brazil page cannot do: NTEMS publishes a **measured** stand
    age, where MapBiomas-derived age has to be counted forward from 1985 and
    carries a censoring ceiling at the start of the series.

    Two properties of the asset drive the implementation, both verified
    2026-08-27:

    * It must be read through ``.mosaic()``. Sampling ``.first()`` returns null
      everywhere — the single-image collection does not resolve to a plain Image
      the way ``ee.Image(asset)`` would. This is the trap that makes a naive
      version return an empty result with no error.
    * It is **masked to forested pixels**, so a null means "not forest here",
      not "no data". The mean is therefore the mean age *of the forest*, and the
      forested share is reported beside it so a 120-year mean over 3 % of a
      parcel cannot be mistaken for a statement about the parcel.
    """
    if not zones:
        raise ValueError("No zones to analyse.")

    get_ee()
    import ee

    from concurrent.futures import ThreadPoolExecutor

    age = (ee.ImageCollection(NTEMS_AGE["asset"]).mosaic()
           .select(NTEMS_AGE["band"]).rename("age"))
    fc = zone_feature_collection(zones)
    scale = NTEMS_AGE["scale_m"]

    def stats_call():
        reducer = (ee.Reducer.mean()
                   .combine(ee.Reducer.median(), sharedInputs=True)
                   .combine(ee.Reducer.count(), sharedInputs=True))
        return age.reduceRegions(
            collection=fc, reducer=reducer, scale=scale,
            tileScale=EE_TILE_SCALE,
        ).getInfo()

    def total_call():
        # unmask(0) turns the forest mask into a dense 0/1 band, so `sum` counts
        # EVERY pixel in the zone rather than only the forested ones the masked
        # image exposes. Without it there is nothing to divide the forested
        # count by, and the forested share cannot be computed at all.
        return age.mask().unmask(0).rename("any").reduceRegions(
            collection=fc, reducer=ee.Reducer.count(), scale=scale,
            tileScale=EE_TILE_SCALE,
        ).getInfo()

    with ThreadPoolExecutor(max_workers=2) as ex:
        f_stats, f_total = ex.submit(stats_call), ex.submit(total_call)
        stats, totals = f_stats.result(), f_total.result()

    total_by_zone = {
        f["properties"]["zone_key"]: float(f["properties"].get("count") or 0.0)
        for f in totals.get("features", [])
    }
    zone_labels = {z.key: z.label for z in zones}

    records = []
    for feat in stats.get("features", []):
        props = feat["properties"]
        zone_key = props["zone_key"]
        forested = float(props.get("count") or 0.0)
        total = total_by_zone.get(zone_key, 0.0)
        records.append({
            "zone_key": zone_key,
            "zone_label": zone_labels.get(zone_key, zone_key),
            "age_mean_y": (round(float(props["mean"]), 1)
                           if props.get("mean") is not None else None),
            "age_median_y": (round(float(props["median"]), 1)
                             if props.get("median") is not None else None),
            "forested_pct": round(100.0 * forested / total, 1) if total else 0.0,
            "reference_year": NTEMS_AGE["reference_year"],
        })

    df = pd.DataFrame.from_records(
        records,
        columns=["zone_key", "zone_label", "age_mean_y", "age_median_y",
                 "forested_pct", "reference_year"],
    )
    # A None beside real floats becomes pandas NaN, which is not legal JSON and
    # this frame reaches Reflex state as JSON. Swap it back.
    df = df.where(pd.notnull(df), None)

    if not df.empty:
        order = {z.key: i for i, z in enumerate(zones)}
        df["_zone_order"] = df["zone_key"].map(order)
        df = df.sort_values("_zone_order").drop(columns="_zone_order")
        df = df.reset_index(drop=True)

    prov = Provenance(
        name="ntems_stand_age",
        dataset_id=NTEMS_AGE["asset"],
        bands=[NTEMS_AGE["band"]],
        scale_m=scale,
        reducer="mean + median + count over the forest mask",
        pixel_area_basis="n/a — ages, not areas",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={
            "zones": [z.key for z in zones],
            "reference_year": NTEMS_AGE["reference_year"],
            "age_note": (
                f"Ages are as published, as of {NTEMS_AGE['reference_year']}. "
                "They are not aged forward to the present — doing so would be "
                "inventing precision the raster does not carry."
            ),
            "mask_note": (
                "The raster is masked to forested pixels; a null is 'not "
                "forest', not 'no data'. The mean is the mean age of the "
                "forest, which is why the forested share is reported beside it."
            ),
        },
    )
    return df, prov


__all__ = [
    "forest_change", "stand_age", "splits_at", "HANSEN_ASSET",
    "PERIOD_BEFORE_PARCEL", "PERIOD_AFTER_PARCEL", "PERIOD_UNDIVIDED",
    "LOSS_YEAR_START", "LOSS_YEAR_END",
]
