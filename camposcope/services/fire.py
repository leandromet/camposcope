"""Fire analysis using MapBiomas Fire Collection 5 (1985-2025).

Three assets, each with a different band layout (confirmed against the live
Earth Engine assets — none of this can be inferred from the dataset docs
alone; see ``doc/earthengine/mapbiomas_*.sh`` for MapBiomas' own reference
scripts against the same assets):

  * ``mapbiomas_fire_collection5_annual_burned_v1`` — one band per year,
    ``burned_area_{year}`` (1985..2025, 41 bands). **Not** a dense 0/1 raster:
    an unburned pixel is MASKED (no value at all), only a burned pixel carries
    the literal value 1 (the reference scripts' own ``.selfMask()`` call after
    selecting the band is the tell). ``reduceRegion``/``reduceRegions`` skip
    masked pixels entirely, so taking the mean of the raw band always comes
    out to 1.0 (100%) — verified directly against a MT sample region: raw
    mean/min/max were all 1, and only ``.unmask(0)`` first drops the true
    burned fraction (here ~1.2%). Every read of this asset must unmask(0)
    before reducing, or the "fraction burned" is nonsense.
  * ``mapbiomas_fire_collection5_fire_frequency_v1`` — 81 bands, one per
    every (start_year, end_year) window MapBiomas publishes; the full-period
    count is the single band ``fire_frequency_1985_2025`` (the other 80 are
    partial windows this app has no use for). Same masking trap as the
    annual asset — a never-burned pixel is masked, not 0 — so this also
    needs ``.unmask(0)`` before any zone-level mean.
  * ``mapbiomas_fire_collection5_year_last_fire_v1`` — one band per year,
    ``classification_{year}``, pixel value = the most recent fire year as of
    that year's mosaic; masked wherever no fire has ever occurred (masking is
    the CORRECT semantics here — there is no year to report). The current
    answer is the LAST band (2025 here), and the sensible zone-level reducer
    is ``max`` — a mean across pixels with different fire years is not a
    year, and unmasking to 0 would corrupt a max with a fake "year 0".
"""

from __future__ import annotations

import logging
from typing import Dict, List, Sequence, Tuple

import pandas as pd

from ..config.settings import EE_MAX_PIXELS, EE_TILE_SCALE
from .ee_client import get_ee
from .mapbiomas_history import _zone_feature_collection
from .provenance import Provenance
from .zones import Zone

logger = logging.getLogger(__name__)

FIRE_ANNUAL_DATASET_ID = (
    "projects/mapbiomas-public/assets/brazil/fire/collection5/"
    "mapbiomas_fire_collection5_annual_burned_v1"
)
FIRE_FREQUENCY_DATASET_ID = (
    "projects/mapbiomas-public/assets/brazil/fire/collection5/"
    "mapbiomas_fire_collection5_fire_frequency_v1"
)
FIRE_LAST_YEAR_DATASET_ID = (
    "projects/mapbiomas-public/assets/brazil/fire/collection5/"
    "mapbiomas_fire_collection5_year_last_fire_v1"
)
FIRE_SCALE_M = 30  # Same resolution as MapBiomas

FIRE_YEAR_START = 1985
FIRE_YEAR_END = 2025
FIRE_YEARS = list(range(FIRE_YEAR_START, FIRE_YEAR_END + 1))

#: The full-period band inside the 81-band frequency asset (see module
#: docstring — the other 80 bands are partial windows, unused here).
_FIRE_FREQUENCY_BAND = f"fire_frequency_{FIRE_YEAR_START}_{FIRE_YEAR_END}"

#: The map layer's colour-ramp ceiling — calibrated against the *observed*
#: national distribution, not the theoretical "one fire per year across 41
#: years" reading the old value of 41 came from. Sampled nationally
#: (``ee.Reducer.frequencyHistogram()`` over Brazil's bbox, 1 km) on
#: 2026-08-27: 39.4% of burnt pixels sit at frequency 1 alone, 70% by
#: frequency 3, 97.5% by frequency 15 — a ceiling of 41 compresses that
#: entire real range into the bottom third of the palette, which is exactly
#: what produced this layer's reported bug: real fire signal reading as a
#: pale, near-invisible wash instead of a red gradient (the same root cause
#: fixed on the Canada page's MODIS layer — see
#: ``canada/services/fire.py::FIRE_FREQUENCY_MAX``). 15 keeps the palette
#: legible for the vast majority of burnt ground; the rare pixel above it
#: (2.5%, up to 74 real pixels at the true max of 41) simply clips to the
#: top colour rather than reading as "no fire."
_FIRE_FREQUENCY_MAX = 15
_FIRE_LAST_YEAR_BAND = f"classification_{FIRE_YEAR_END}"


def _annual_band(year: int) -> str:
    return f"burned_area_{year}"


def fire_analysis(zones: Sequence[Zone]) -> Tuple[pd.DataFrame, pd.DataFrame, Provenance]:
    """Fire history, frequency, and year of last fire from MapBiomas Fire Coll. 5.

    Returns ``(summary_df, annual_df, provenance)``:

    - ``summary_df``: one row per zone — ``fire_history_pct`` (share of the
      41-year period with any fire in the zone), ``fire_frequency`` (mean
      per-pixel occurrence count, 0–41), ``fire_last_year`` (most recent fire
      year anywhere in the zone), ``area_ha``.
    - ``annual_df``: long format, one row per zone per year —
      ``zone_key, year, fire_pct`` (share of the zone burned that year,
      0 for years with no fire) — the Cobertura-style per-year chart.
    """
    if not zones:
        raise ValueError("Nenhuma zona para analisar.")

    get_ee()
    import ee

    fc = _zone_feature_collection(zones)
    zone_labels = {z.key: z.label for z in zones}
    zone_areas = {z.key: z.area_ha for z in zones}

    # ---- annual burned fraction, one band per year, one round trip ----
    # unmask(0): both source assets mask the "no fire" case instead of
    # storing 0 (see module docstring) — skip this and every mean() below
    # silently averages only over already-burned pixels, i.e. always 100%.
    annual_img = ee.Image(FIRE_ANNUAL_DATASET_ID).select(
        [_annual_band(y) for y in FIRE_YEARS]
    ).unmask(0)
    freq_band = ee.Image(FIRE_FREQUENCY_DATASET_ID).select(
        [_FIRE_FREQUENCY_BAND], ["fire_frequency"]
    ).unmask(0)
    annual_with_freq = annual_img.addBands(freq_band)

    try:
        annual_stats = (
            annual_with_freq
            .reduceRegions(
                collection=fc, reducer=ee.Reducer.mean(),
                scale=FIRE_SCALE_M, tileScale=EE_TILE_SCALE,
            )
            .getInfo()
        )
    except Exception as exc:                       # noqa: BLE001
        logger.warning("MapBiomas Fire annual/frequency reduce failed: %s", exc)
        annual_stats = {"features": []}

    # ---- year of last fire — max, not mean, and NOT unmasked (see module
    # docstring: masking is the correct semantics for this one asset) ----
    last_year_band = ee.Image(FIRE_LAST_YEAR_DATASET_ID).select(
        [_FIRE_LAST_YEAR_BAND], ["fire_last_year"]
    )
    try:
        last_year_stats = (
            last_year_band.reduceRegions(
                collection=fc, reducer=ee.Reducer.max(),
                scale=FIRE_SCALE_M, tileScale=EE_TILE_SCALE,
            )
            .getInfo()
        )
    except Exception as exc:                       # noqa: BLE001
        logger.warning("MapBiomas Fire last-year reduce failed: %s", exc)
        last_year_stats = {"features": []}

    last_year_by_zone: Dict[str, float] = {
        f["properties"]["zone_key"]: f["properties"].get("fire_last_year")
        for f in last_year_stats.get("features", [])
    }

    summary_records = []
    annual_records = []
    for feat in annual_stats.get("features", []):
        props = feat["properties"]
        zone_key = props["zone_key"]
        area_ha = zone_areas.get(zone_key, 0.0)

        per_year_frac = [float(props.get(_annual_band(y), 0.0) or 0.0)
                         for y in FIRE_YEARS]
        for year, frac in zip(FIRE_YEARS, per_year_frac):
            annual_records.append({
                "zone_key": zone_key,
                "zone_label": zone_labels.get(zone_key, zone_key),
                "year": year,
                "fire_pct": round(frac * 100.0, 2),
            })

        history_pct = (sum(1 for f in per_year_frac if f > 0) / len(FIRE_YEARS)) * 100.0
        fire_freq = props.get("fire_frequency", 0.0) or 0.0
        last_year = last_year_by_zone.get(zone_key)

        summary_records.append({
            "zone_key": zone_key,
            "zone_label": zone_labels.get(zone_key, zone_key),
            "fire_history_pct": round(history_pct, 1),
            "fire_frequency": round(float(fire_freq), 1),
            "fire_last_year": int(last_year) if last_year else None,
            "area_ha": area_ha,
        })

    summary_df = pd.DataFrame.from_records(
        summary_records,
        columns=["zone_key", "zone_label", "fire_history_pct", "fire_frequency",
                "fire_last_year", "area_ha"],
    )
    annual_df = pd.DataFrame.from_records(
        annual_records,
        columns=["zone_key", "zone_label", "year", "fire_pct"],
    )

    if not summary_df.empty:
        order = {z.key: i for i, z in enumerate(zones)}
        summary_df["_zone_order"] = summary_df["zone_key"].map(order)
        summary_df = summary_df.sort_values("_zone_order").drop(columns="_zone_order")
        summary_df = summary_df.reset_index(drop=True)
    if not annual_df.empty:
        order = {z.key: i for i, z in enumerate(zones)}
        annual_df["_zone_order"] = annual_df["zone_key"].map(order)
        annual_df = annual_df.sort_values(["_zone_order", "year"]).drop(columns="_zone_order")
        annual_df = annual_df.reset_index(drop=True)

    prov = Provenance(
        name="mapbiomas_fire",
        dataset_id=FIRE_ANNUAL_DATASET_ID,
        bands=[_annual_band(y) for y in FIRE_YEARS] + ["fire_frequency", "fire_last_year"],
        scale_m=FIRE_SCALE_M,
        reducer="mean (annual/frequency) · max (last year)",
        pixel_area_basis="zone geometry area (services/zones.py)",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={
            "zones": [z.key for z in zones],
            "years": FIRE_YEARS,
            "attribution": "MapBiomas Fogo Coleção 5 (CC BY-SA 4.0) · escala 30 m",
            "methodology": (
                "Classificação por aprendizado profundo de mosaicos anuais "
                "Landsat via menor NBR (Normalized Burn Ratio) por pixel."
            ),
        },
    )
    return summary_df, annual_df, prov


__all__ = [
    "fire_analysis", "FIRE_SCALE_M", "FIRE_ANNUAL_DATASET_ID",
    "FIRE_FREQUENCY_DATASET_ID", "FIRE_LAST_YEAR_DATASET_ID",
    "FIRE_YEARS", "FIRE_YEAR_START", "FIRE_YEAR_END", "_FIRE_FREQUENCY_MAX",
]
