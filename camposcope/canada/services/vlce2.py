"""ACI vs. NTEMS VLCE2 — the Validação tab's cross-check.

Where the Brazil page validates MapBiomas against imagery from a specific legal
date, this compares the AAFC crop inventory against an **independent national
land-cover product over the same year**. See ``canada/config/vlce2.py`` for what
the comparison can and cannot say; the short version is that it is made at a
coarse group level both legends genuinely encode, and it never declares a
winner.

**The reducer.** Both rasters are remapped to a group index (0–7) and packed as
``aci_group * 10 + vlce2_group``, then run through one ``frequencyHistogram``
over every zone — the same batched shape ``transitions.py`` uses, and for the
same reason: one round trip covers the whole matrix.

**Two products, two grids.** The ACI and VLCE2 are both nominally 30 m but are
published on different projections, so Earth Engine reprojects one onto the
other for the comparison. That is unavoidable and it means a small share of the
disagreement is registration error at class boundaries rather than genuine
disagreement about what is there — a real effect, concentrated exactly at
edges. It is recorded in provenance, and it is one more reason this tab reports
a disagreement *rate* rather than adjudicating individual pixels.

**Two things bound which years can be compared at all**, both enforced here
rather than left to the caller:

* VLCE2 ends in 2022 and the ACI's national coverage starts in 2011, so only
  2011–2022 exists on both sides.
* VLCE2's images are addressed by ``system:index``, not by date. ``filterDate``
  on that collection silently returns nothing — the trap that would make a naive
  port produce an empty image and an all-zero matrix that looks like total
  disagreement.
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
from ..config import vlce2 as cfg
from .aci_history import aci_year_image
from .ee_zones import mean_pixel_area, px_area_by_zone, zone_feature_collection

logger = logging.getLogger(__name__)

#: Group name → its index in the packed integer. Index, not the name itself,
#: because Earth Engine remaps numbers.
GROUP_INDEX: Dict[str, int] = {g: i for i, g in enumerate(cfg.GROUP_ORDER)}
INDEX_GROUP: Dict[int, str] = {i: g for g, i in GROUP_INDEX.items()}

#: The packing multiplier. Ten is enough for eight groups and keeps the packed
#: values small enough to read in a debugger, unlike the transitions module's
#: 1000 — there the operands are raw class codes up to 230.
_PACK = 10
assert len(cfg.GROUP_ORDER) < _PACK, (
    "More comparison groups than the packing multiplier allows; "
    "aci*%d+vlce2 would collide." % _PACK
)


class YearNotComparable(ValueError):
    """Raised for a year only one of the two products covers."""


def vlce2_year_image(year: int):
    """One year of VLCE2, addressed by ``system:index``.

    **Not** ``filterDate`` — see the module docstring. Verified 2026-08-27:
    the collection's images carry ids of the form ``CA_forest_VLCE2_2022`` and
    a date filter matches none of them.
    """
    import ee

    col = ee.ImageCollection(cfg.VLCE2_DATASET)
    return ee.Image(
        col.filter(ee.Filter.eq("system:index", cfg.image_id(year))).first()
    ).select([cfg.VLCE2_BAND]).rename("vlce2")


def _grouped(image, mapping: Dict[int, str], name: str):
    """Remap a classified image onto the comparison group indices.

    Codes absent from ``mapping`` fall to the ``other`` group rather than being
    masked away: a pixel the two products disagree about because one of them has
    no class for it is exactly the case this tab exists to show, and masking it
    would delete the finding.
    """
    import ee

    codes = sorted(mapping)
    targets = [GROUP_INDEX[mapping[c]] for c in codes]
    return image.remap(codes, targets, GROUP_INDEX["other"]).rename(name)


def agreement(
    zones: Sequence[Zone], year: int,
) -> Tuple[pd.DataFrame, pd.DataFrame, Provenance]:
    """Group-level agreement between the ACI and VLCE2, per zone.

    Returns ``(summary_df, matrix_df, provenance)``:

    - ``summary_df``: one row per zone — ``agreement_pct`` (share of the zone
      where the two products place the same group), ``area_ha``,
      ``n_disagreeing_groups``.
    - ``matrix_df``: long format, one row per zone × ACI group × VLCE2 group —
      ``zone_key, aci_group, vlce2_group, area_ha, is_agreement``. Every
      non-zero cell of the confusion matrix, which is what the table renders: a
      literal 8×8 grid would be unreadable at drawer width.
    """
    if year not in cfg.COMPARABLE_YEARS:
        raise YearNotComparable(
            f"{year} cannot be compared: the crop inventory and VLCE2 overlap "
            f"only over {cfg.COMPARABLE_YEAR_START}–{cfg.COMPARABLE_YEAR_END}."
        )
    if not zones:
        raise ValueError("No zones to analyse.")

    get_ee()
    import ee

    from concurrent.futures import ThreadPoolExecutor

    aci = _grouped(aci_year_image(year), cfg.ACI_TO_GROUP, "aci")
    vlce = _grouped(vlce2_year_image(year), cfg.VLCE2_TO_GROUP, "vlce2")
    combined = aci.multiply(_PACK).add(vlce).rename("combined")
    fc = zone_feature_collection(zones)

    def hist_call():
        return combined.reduceRegions(
            collection=fc, reducer=ee.Reducer.frequencyHistogram(),
            scale=EE_DEFAULT_SCALE_M, tileScale=EE_TILE_SCALE,
        ).getInfo()

    with ThreadPoolExecutor(max_workers=2) as ex:
        f_hist = ex.submit(hist_call)
        f_area = ex.submit(mean_pixel_area, fc, EE_DEFAULT_SCALE_M, EE_TILE_SCALE)
        hist, areas = f_hist.result(), f_area.result()

    px_area = px_area_by_zone(areas)
    zone_labels = {z.key: z.label for z in zones}

    matrix_records: List[Dict[str, Any]] = []
    summary_records: List[Dict[str, Any]] = []

    for feat in hist["features"]:
        props = feat["properties"]
        zone_key = props["zone_key"]
        zone_label = zone_labels.get(zone_key, zone_key)
        area_per_px_ha = px_area.get(zone_key, 900.0) / 10_000.0
        # Single selected band → the reducer's own name, not the band's. Same
        # quirk documented in aci_history.py and transitions.py.
        raw: Dict[str, float] = props.get("histogram") or {}

        agreed_ha = 0.0
        total_ha = 0.0
        disagreeing: set = set()

        for packed_str, count in raw.items():
            packed = int(float(packed_str))
            aci_i, vlce_i = packed // _PACK, packed % _PACK
            aci_group = INDEX_GROUP.get(aci_i, "other")
            vlce_group = INDEX_GROUP.get(vlce_i, "other")
            area_ha = float(count) * area_per_px_ha
            if area_ha <= 0:
                continue
            is_agreement = aci_group == vlce_group
            total_ha += area_ha
            if is_agreement:
                agreed_ha += area_ha
            else:
                disagreeing.add((aci_group, vlce_group))
            matrix_records.append({
                "zone_key": zone_key,
                "zone_label": zone_label,
                "aci_group": aci_group,
                "vlce2_group": vlce_group,
                "area_ha": area_ha,
                "is_agreement": is_agreement,
            })

        summary_records.append({
            "zone_key": zone_key,
            "zone_label": zone_label,
            "agreement_pct": (round(100.0 * agreed_ha / total_ha, 1)
                              if total_ha else 0.0),
            "area_ha": round(total_ha, 2),
            "n_disagreeing_groups": len(disagreeing),
        })

    matrix_df = pd.DataFrame.from_records(
        matrix_records,
        columns=["zone_key", "zone_label", "aci_group", "vlce2_group",
                 "area_ha", "is_agreement"],
    )
    summary_df = pd.DataFrame.from_records(
        summary_records,
        columns=["zone_key", "zone_label", "agreement_pct", "area_ha",
                 "n_disagreeing_groups"],
    )

    order = {z.key: i for i, z in enumerate(zones)}
    if not matrix_df.empty:
        matrix_df["_zone_order"] = matrix_df["zone_key"].map(order)
        matrix_df = matrix_df.sort_values(
            ["_zone_order", "area_ha"], ascending=[True, False]
        ).drop(columns="_zone_order").reset_index(drop=True)
    if not summary_df.empty:
        summary_df["_zone_order"] = summary_df["zone_key"].map(order)
        summary_df = summary_df.sort_values("_zone_order").drop(
            columns="_zone_order").reset_index(drop=True)

    prov = Provenance(
        name="aci_vlce2_agreement",
        dataset_id=f"{aafc.AACI_DATASET} | {cfg.VLCE2_DATASET}",
        bands=[aafc.band_for_year(year), cfg.VLCE2_BAND],
        scale_m=EE_DEFAULT_SCALE_M,
        reducer=f"frequencyHistogram(aci_group*{_PACK}+vlce2_group)",
        pixel_area_basis="mean ee.Image.pixelArea() per zone",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={
            "year": year,
            "zones": [z.key for z in zones],
            "groups": list(cfg.GROUP_ORDER),
            "comparable_years": [cfg.COMPARABLE_YEAR_START,
                                 cfg.COMPARABLE_YEAR_END],
            "no_verdict_note": (
                "Disagreement between two independent products is not error in "
                "either. This reports where they differ and says nothing about "
                "which is right."
            ),
            "grid_note": (
                "The two products are published on different projections, so "
                "one is reprojected onto the other. A share of the "
                "disagreement — concentrated at class boundaries — is "
                "registration error rather than genuine disagreement."
            ),
            "legend_note": (
                "Compared at group level, not class level: the ACI resolves "
                "crops and has no forest-type detail, VLCE2 the reverse. A "
                "class-level agreement rate between them would be meaningless."
            ),
        },
    )
    logger.info("ACI/VLCE2 agreement %s: %s zones, %s matrix cells",
                year, len(summary_df), len(matrix_df))
    return summary_df, matrix_df, prov


def default_year() -> int:
    """The year the tab opens on — the last both products cover."""
    return cfg.COMPARABLE_YEAR_END


__all__ = ["agreement", "vlce2_year_image", "default_year", "YearNotComparable",
           "GROUP_INDEX", "INDEX_GROUP"]
