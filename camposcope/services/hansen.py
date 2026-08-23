"""Hansen Global Forest Change — dated loss, split into three periods anchored
on the two dates that actually govern a CAR property; undated gain, kept
separate (doc/04-data-sources.md §3).

**Three periods, not two.** The Código Florestal (Lei 12.651/2012) uses
**22 July 2008** as its reference date for *área rural consolidada*; the
property's own **CAR registration date** is a second, independent turning
point. Loss is bucketed against both:

======================  =========================================
``ate_2008``            loss year ≤ 2008 (Hansen has no month field,
                        so the cutoff falls on the year boundary —
                        see ``config.datasets.FOREST_CODE_CUTOFF_YEAR``)
``2008_ate_registro``   2008 < loss year < registration year
``apos_registro``       loss year ≥ registration year
======================  =========================================

If a property was registered before or during 2008, the middle bucket is
simply empty — the split degrades gracefully rather than producing an
inverted range.

One batched call covers every zone: ``lossyear`` and ``gain`` are two bands of
the same image, so ``reduceRegions`` with ``frequencyHistogram`` returns both
histograms per zone in a single round trip — the same trick documented in
``mapbiomas_history.py`` for multi-band selections.

**Gain is never summed with loss.** It is a single undated 2000–2012 layer
(doc/04 §3); putting it on the same timeline as dated loss would misrepresent
both.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence, Tuple

import pandas as pd

from ..config.datasets import FOREST_CODE_CUTOFF_YEAR, HANSEN_GFC
from ..config.settings import EE_MAX_PIXELS, EE_TILE_SCALE
from .ee_client import get_ee
from .mapbiomas_history import _zone_feature_collection
from .provenance import Provenance
from .zones import Zone

logger = logging.getLogger(__name__)

HANSEN_ASSET = HANSEN_GFC["asset"]
LOSS_YEAR_START = HANSEN_GFC["loss_year_start"]
LOSS_YEAR_END = HANSEN_GFC["loss_year_end"]
#: `treecover2000` scale — Hansen's own native resolution.
HANSEN_SCALE_M = 30

PERIOD_UP_TO_2008 = "ate_2008"
PERIOD_TO_REGISTRATION = "2008_ate_registro"
PERIOD_AFTER_REGISTRATION = "apos_registro"


def _period(year: int, registration_year: "int | None") -> str:
    if year <= FOREST_CODE_CUTOFF_YEAR:
        return PERIOD_UP_TO_2008
    if registration_year and year < registration_year:
        return PERIOD_TO_REGISTRATION
    return PERIOD_AFTER_REGISTRATION


def forest_change(
    zones: Sequence[Zone], *, registration_year: "int | None" = None,
) -> Tuple[pd.DataFrame, float, Provenance]:
    """Loss by year, bucketed into three periods, and gain, per zone.

    Returns ``(loss_df, gain_total_ha, provenance)``. ``loss_df`` columns:
    ``zone_key, zone_label, year, area_ha, period`` — long format, one row per
    zone per loss year, so the chart can colour by period without a second
    query. ``period`` is one of ``PERIOD_UP_TO_2008``,
    ``PERIOD_TO_REGISTRATION``, ``PERIOD_AFTER_REGISTRATION``.
    """
    if not zones:
        raise ValueError("Nenhuma zona para analisar.")

    get_ee()
    import ee

    from concurrent.futures import ThreadPoolExecutor

    img = ee.Image(HANSEN_ASSET)
    fc = _zone_feature_collection(zones)

    def hist_call():
        return (
            img.select(["lossyear", "gain"])
            .reduceRegions(collection=fc, reducer=ee.Reducer.frequencyHistogram(),
                           scale=HANSEN_SCALE_M, tileScale=EE_TILE_SCALE)
            .getInfo()
        )

    def area_call():
        return (
            ee.Image.pixelArea()
            .reduceRegions(collection=fc, reducer=ee.Reducer.mean(),
                           scale=HANSEN_SCALE_M, tileScale=EE_TILE_SCALE)
            .getInfo()
        )

    with ThreadPoolExecutor(max_workers=2) as ex:
        f_hist, f_area = ex.submit(hist_call), ex.submit(area_call)
        hist, areas = f_hist.result(), f_area.result()

    px_area = {
        f["properties"]["zone_key"]: float(f["properties"].get("mean") or 900.0)
        for f in areas["features"]
    }
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
                "period": _period(year, registration_year),
            })

        gain_hist: Dict[str, float] = props.get("gain") or {}
        gain_count = float(gain_hist.get("1", 0.0))
        if zone_key == "imovel":            # gain total reported for the property only
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
            "forest_code_cutoff_year": FOREST_CODE_CUTOFF_YEAR,
            "registration_year": registration_year,
            "gain_note": (
                "gain é uma camada única e SEM DATA (2000-2012); nunca somada "
                "à perda datada."
            ),
        },
    )
    return loss_df, gain_total_ha, prov


__all__ = [
    "forest_change", "HANSEN_ASSET",
    "PERIOD_UP_TO_2008", "PERIOD_TO_REGISTRATION", "PERIOD_AFTER_REGISTRATION",
]
