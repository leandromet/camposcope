"""Burned area from MODIS MCD64A1, over a parcel's zones.

The Canadian stand-in for MapBiomas Fire Collection 5. The two are not
equivalent and the UI must not pretend they are — see
``canada/config/datasets.py::MODIS_BURN`` for why this product rather than
NBAC, and what its 463 m pixels cost.

**The masking trap, and how it differs here.** The Brazil module's central
warning is that MapBiomas Fire *masks* unburned pixels rather than storing 0, so
a mean over the raw band always comes out to 100 %. MCD64A1 has the same shape
for the same reason — ``BurnDate`` is masked where nothing burned — so the same
``unmask(0)`` discipline applies, and every reduction below does it. The
difference is what the band carries: MapBiomas' annual band is a 0/1 flag, while
``BurnDate`` is the **day of year** the pixel burned (1–366). So a burned pixel
must be reduced to a flag with ``.gt(0)`` *before* averaging, or the "burned
fraction" comes out as a mean day-of-year — a number in the hundreds that looks
like nothing in particular and is silently meaningless.

**Monthly images, annual answers.** MCD64A1 publishes one image per month. A
year's burned area is the per-pixel ``max`` over that year's twelve images
(a pixel burned in July is burned for the year), not a sum — summing would
double-count a pixel that appears in two months' composites.

**Whole years only.** The newest image is partway through the current year, and
a partial year on a bar chart reads as a quiet fire season rather than an
incomplete one. The range stops at the last complete year.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence, Tuple

import pandas as pd

from ...config.settings import EE_MAX_PIXELS, EE_TILE_SCALE
from ...services.ee_client import get_ee
from ...services.provenance import Provenance
from ...services.zones import Zone
from ..config import aafc as _aafc
from ..config.datasets import FIRE_MIN_MEANINGFUL_HA, MODIS_BURN, MODIS_BURN_YEARS
from .ee_zones import zone_feature_collection

logger = logging.getLogger(__name__)

FIRE_DATASET_ID = MODIS_BURN["asset"]
FIRE_BAND = MODIS_BURN["band"]
FIRE_SCALE_M = MODIS_BURN["scale_m"]
FIRE_YEARS: List[int] = list(MODIS_BURN_YEARS)
FIRE_YEAR_START = FIRE_YEARS[0]
FIRE_YEAR_END = FIRE_YEARS[-1]

#: The frequency layer's colour-ramp ceiling — calibrated against the observed
#: national distribution, not a theoretical one. See the note on
#: ``config/datasets.py::MODIS_BURN["max_frequency"]`` for the sampled numbers.
FIRE_FREQUENCY_MAX = MODIS_BURN["max_frequency"]


def _annual_band(year: int) -> str:
    return f"burned_{year}"


def annual_burn_image(years: Sequence[int] | None = None):
    """One multi-band image, one 0/1 band per year.

    This is what turns "25 years × N zones" into a single ``reduceRegions``
    round trip, the same shape every other analysis on this page uses. See the
    module docstring for why ``.gt(0)`` comes before the reduction and why the
    within-year combiner is ``max`` rather than ``sum``.
    """
    import ee

    years = list(years or FIRE_YEARS)
    col = ee.ImageCollection(FIRE_DATASET_ID).select(FIRE_BAND)
    bands = [
        col.filterDate(f"{y}-01-01", f"{y}-12-31")
        .max()                 # a pixel burned in any month is burned for the year
        .gt(0)                 # day-of-year → burned flag, BEFORE any averaging
        .unmask(0)             # unburned is masked, not 0 — see module docstring
        .rename(_annual_band(y))
        for y in years
    ]
    return ee.Image.cat(bands)


def fire_frequency_image(years: Sequence[int] | None = None):
    """Per-pixel count of years with any burn — the Fogo tab's map layer.

    Derived from the annual stack rather than fetched from a published
    frequency product, because MODIS has no equivalent of MapBiomas' pre-computed
    ``fire_frequency`` band. Summing the annual 0/1 bands is exactly the same
    quantity.
    """
    import ee

    years = list(years or FIRE_YEARS)
    stack = annual_burn_image(years)
    return (stack.select([_annual_band(y) for y in years])
            .reduce(ee.Reducer.sum()).rename("fire_frequency"))


def fire_analysis(
    zones: Sequence[Zone], *, years: Sequence[int] | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Provenance]:
    """Burn history, frequency and year of last burn, per zone.

    Returns ``(summary_df, annual_df, provenance)``:

    - ``summary_df``: one row per zone — ``fire_history_pct`` (share of the
      record's years with any burn in the zone), ``fire_frequency`` (mean
      per-pixel year-count), ``fire_last_year``, ``area_ha``, and
      ``below_resolution`` (see below).
    - ``annual_df``: long format, one row per zone per year — ``fire_pct``, the
      share of the zone burned that year, 0 for years with no burn.

    ``below_resolution`` is the honesty flag this page needs and the Brazil page
    does not: at 463 m a pixel is ~21 ha, so on a parcel of a few hundred
    hectares the burned fraction is dominated by pixel-edge effects. The tab
    reports the numbers either way — suppressing them would be its own kind of
    lie — but marks them as being below the product's useful resolution.
    """
    if not zones:
        raise ValueError("No zones to analyse.")

    get_ee()
    import ee

    years = list(years or FIRE_YEARS)
    fc = zone_feature_collection(zones)
    zone_labels = {z.key: z.label for z in zones}
    zone_areas = {z.key: z.area_ha for z in zones}

    stack = annual_burn_image(years)
    freq = fire_frequency_image(years)
    combined = stack.addBands(freq)

    try:
        stats = combined.reduceRegions(
            collection=fc, reducer=ee.Reducer.mean(),
            scale=FIRE_SCALE_M, tileScale=EE_TILE_SCALE,
        ).getInfo()
    except Exception as exc:                       # noqa: BLE001
        logger.warning("MODIS burned-area reduce failed: %s", exc)
        stats = {"features": []}

    summary_records: List[Dict[str, Any]] = []
    annual_records: List[Dict[str, Any]] = []

    for feat in stats.get("features", []):
        props = feat["properties"]
        zone_key = props["zone_key"]
        area_ha = zone_areas.get(zone_key, 0.0)

        per_year_frac = [float(props.get(_annual_band(y), 0.0) or 0.0)
                         for y in years]
        for year, frac in zip(years, per_year_frac):
            annual_records.append({
                "zone_key": zone_key,
                "zone_label": zone_labels.get(zone_key, zone_key),
                "year": year,
                "fire_pct": round(frac * 100.0, 2),
            })

        burned_years = [y for y, f in zip(years, per_year_frac) if f > 0]
        history_pct = (len(burned_years) / len(years)) * 100.0 if years else 0.0

        summary_records.append({
            "zone_key": zone_key,
            "zone_label": zone_labels.get(zone_key, zone_key),
            "fire_history_pct": round(history_pct, 1),
            "fire_frequency": round(float(props.get("fire_frequency") or 0.0), 2),
            # The most recent year with any burn, read off the annual series
            # rather than from a separate "year of last fire" asset — MODIS
            # publishes none, and deriving it here costs nothing extra.
            "fire_last_year": max(burned_years) if burned_years else None,
            "area_ha": area_ha,
            "below_resolution": area_ha < FIRE_MIN_MEANINGFUL_HA,
        })

    summary_df = pd.DataFrame.from_records(
        summary_records,
        columns=["zone_key", "zone_label", "fire_history_pct", "fire_frequency",
                 "fire_last_year", "area_ha", "below_resolution"],
    )
    annual_df = pd.DataFrame.from_records(
        annual_records,
        columns=["zone_key", "zone_label", "year", "fire_pct"],
    )
    # None beside real values becomes NaN, which is not legal JSON and this
    # frame reaches Reflex state as JSON.
    summary_df = summary_df.where(pd.notnull(summary_df), None)

    order = {z.key: i for i, z in enumerate(zones)}
    for frame, sort_cols in ((summary_df, ["_zone_order"]),
                             (annual_df, ["_zone_order", "year"])):
        if frame.empty:
            continue
        frame["_zone_order"] = frame["zone_key"].map(order)
        frame.sort_values(sort_cols, inplace=True)
        frame.drop(columns="_zone_order", inplace=True)
        frame.reset_index(drop=True, inplace=True)

    prov = Provenance(
        name="modis_burned_area",
        dataset_id=FIRE_DATASET_ID,
        bands=[FIRE_BAND],
        scale_m=FIRE_SCALE_M,
        reducer="mean of per-year max(BurnDate>0), unmasked to 0",
        pixel_area_basis="zone geometry area (canada/services/zones.py, BC Albers)",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={
            "zones": [z.key for z in zones],
            "years": years,
            "attribution": MODIS_BURN["attribution"],
            "resolution_note": (
                f"MCD64A1 pixels are {FIRE_SCALE_M} m (~21 ha). A fire smaller "
                "than roughly 20 ha does not register at all, and a burn edge is "
                "placed to within about half a kilometre. Zones under "
                f"{FIRE_MIN_MEANINGFUL_HA:,.0f} ha are flagged "
                "'below_resolution'."
            ),
            "why_not_nbac": (
                "Canada's National Burned Area Composite is better resolved but "
                "is not published in Earth Engine (checked 2026-08-27)."
            ),
        },
    )
    return summary_df, annual_df, prov


# --------------------------------------------------------------------------- #
# AAFC ACI class 60 — "Forest Fire and Burnt Area", the finer-resolution
# complement, not a replacement
# --------------------------------------------------------------------------- #
# The Annual Crop Inventory carries its own burnt-area class (see
# ``config/aafc.py::BURNT``) at 30 m — seven times finer than MCD64A1's 500 m
# and, unlike MODIS, a class already being fetched for the Cobertura tab's
# yearly trajectory, so the per-zone-per-year burnt area comes out of
# ``history_rows`` for free: no second Earth Engine round trip.
#
# **Complement, not a better MODIS.** Three real differences the UI has to
# carry, not paper over:
#
# 1. **Shorter record.** 2009–2025 (national from 2011), against MODIS'
#    2001–2025 — six fewer years, eight outside the Prairies.
# 2. **A land-cover class, not a burn product.** The AAFC classifier looks for
#    what a burn scar looks like from space *during that year's growing
#    season*; a fire whose scar has already regreened by the satellite's pass,
#    or that falls outside the classifier's training distribution, will not be
#    flagged even though it happened. MCD64A1 is a purpose-built daily-burn
#    product and will catch fires this class misses.
# 3. **National coverage gap is the same one Cobertura already has** — no
#    signal at all north of the inventory's roughly 54–58°N limit, where MODIS
#    (global) still answers.
#
# So the two are shown side by side, never merged into one number: a "total
# burnt years" that silently drew from whichever product had data for a given
# year would misrepresent both.

def aci_burn_rows(history_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The burnt-class rows already sitting in a Cobertura fetch's
    ``history_rows`` — one row per zone per year where class 60 appeared.

    Takes the already-fetched rows rather than querying Earth Engine again:
    ``run_aci_history`` (``canada/state/_cover.py``) already asked for every
    class in every year across every zone, and burnt area is just one more
    class in that same table. A caller with no Cobertura data yet (state row
    list empty) gets an empty list back, not an error — the Fogo tab's AAFC
    view says "run Cobertura first" rather than failing.
    """
    burnt_ids = _aafc.BURNT
    return [r for r in history_rows if int(r.get("class_id", -1)) in burnt_ids]


def aci_burn_mask(year: int):
    """AAFC ACI class 60 for one year, masked to just that class.

    30 m against MODIS' 500 m: a burn scar reads as a shape here, not a blob a
    couple of pixels wide. Superseded on the map by
    :func:`aci_burn_frequency_image` (below) for the same reason the MODIS
    layer went from single-year to multi-year — see that function's
    docstring — but kept as the per-year building block it is built from.
    """
    from .aci_history import aci_year_image

    codes = sorted(_aafc.BURNT)
    image = aci_year_image(year).rename("class")
    return image.remap(codes, [1] * len(codes)).selfMask().rename("burnt")


#: The ACI frequency ramp's ceiling. Sampled nationally at 500 m
#: (``ee.Reducer.frequencyHistogram()`` over -141..-52, 41..70) on
#: 2026-08-28: 312,512 burnt-pixel-years at frequency 1, 1,430 at 2, and
#: exactly 6 pixels ever reaching 3. A land-cover classifier's burnt-area
#: call is a one-off far more often than MODIS' purpose-built daily product
#: is (see the module docstring's point 2) — this is not a MODIS-style
#: multi-decade fire-return signal, it is "how many separate times did the
#: classifier call this pixel burnt," and that is almost always once.
ACI_BURN_FREQUENCY_MAX = 3


def aci_annual_burn_image(years: Sequence[int] | None = None):
    """One multi-band image, one 0/1 band per ACI year — the AAFC analogue
    of :func:`annual_burn_image`, class 60 in place of MCD64A1's ``BurnDate``.
    """
    import ee
    from .aci_history import aci_year_image

    years = list(years or _aafc.ACI_YEARS)
    codes = sorted(_aafc.BURNT)
    bands = [
        aci_year_image(y).rename("class")
        .remap(codes, [1] * len(codes), 0)
        .rename(_annual_band(y))
        for y in years
    ]
    return ee.Image.cat(bands)


def aci_burn_frequency_image(years: Sequence[int] | None = None):
    """Per-pixel count of ACI years classed burnt — the Fogo tab's AAFC map
    layer.

    The single-year layer this replaced (``aci_burn_mask``) only ever showed
    whatever one year the picker happened to be on, so a parcel burnt in
    (say) 2023 alone was invisible on the map every year except that one —
    while the analysis chart, which already reads every year out of
    ``history_rows``, showed the burn correctly. Compositing across the full
    record like the MODIS layer already does removes that mismatch: the map
    now shows the same "any year on record" answer the stats panel does.
    """
    import ee

    years = list(years or _aafc.ACI_YEARS)
    stack = aci_annual_burn_image(years)
    return (stack.select([_annual_band(y) for y in years])
            .reduce(ee.Reducer.sum()).rename("aci_fire_frequency"))


__all__ = [
    "fire_analysis", "annual_burn_image", "fire_frequency_image",
    "aci_burn_rows", "aci_burn_mask",
    "aci_annual_burn_image", "aci_burn_frequency_image",
    "FIRE_DATASET_ID", "FIRE_BAND", "FIRE_SCALE_M", "FIRE_YEARS",
    "FIRE_YEAR_START", "FIRE_YEAR_END", "FIRE_FREQUENCY_MAX",
    "ACI_BURN_FREQUENCY_MAX",
]
