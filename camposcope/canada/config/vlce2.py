"""NTEMS VLCE2 — the independent land-cover product the Validação tab checks
the ACI against.

Where the Brazil page validates MapBiomas against imagery from a specific legal
date (the SPOT 2008 mosaic, because the Código Florestal turns on 22 July 2008),
Canada has no comparable date and no comparable one-off mosaic. What it has
instead is something the Brazil page does not: **a second, independent,
national, annual land-cover product over the same years**.

``projects/sat-io/open-datasets/CA_FOREST_LC_VLCE2`` — Virtual Land Cover
Engine v2, from the Canadian Forest Service's NTEMS programme. Verified against
the asset on 2026-08-27: 39 images, one per year **1984–2022**, single band
``b1``, 30 m, national coverage including well north of the ACI limit.

**Why this is the right pairing, and what it can and cannot say.** The two
products are built for different purposes from overlapping inputs — the ACI is
an agricultural inventory tuned to distinguish crops, VLCE2 is a forest-oriented
land-cover map with no crop classes at all. So they will *never* agree at class
level, and a raw pixel-agreement percentage between their native legends would
be a meaningless number. The comparison is therefore made at the level of
:data:`GROUP_ORDER` below — coarse classes both legends genuinely encode — and
what it reports is *where the two products disagree about the coarse thing*,
which is a real signal about classification confidence over a parcel.

**No verdict.** Disagreement is not error, and this tab never says which product
is right. Same posture as the Brazil page's SPOT tab (decision D9): reporting
that two maps differ over 12 % of a parcel is an observation; deciding which one
is wrong is a judgement neither raster contains.

Two further facts the UI must carry, or it will mislead:

* **VLCE2 ends in 2022, the ACI runs to 2025.** Only 2011–2022 is comparable at
  all, and the year picker is bounded to that window rather than silently
  pairing a year against nothing.
* **VLCE2 covers the whole country, the ACI does not.** North of ~58°N the
  comparison degrades to "VLCE2 only" — which is itself worth showing, since it
  is the honest picture of what is known about that parcel.
"""

from __future__ import annotations

from typing import Dict, List

from . import aafc

# --------------------------------------------------------------------------- #
# Dataset
# --------------------------------------------------------------------------- #
VLCE2_DATASET = "projects/sat-io/open-datasets/CA_FOREST_LC_VLCE2"
VLCE2_BAND = "b1"
VLCE2_SCALE_M = 30

VLCE2_YEAR_START = 1984
VLCE2_YEAR_END = 2022
VLCE2_YEARS: List[int] = list(range(VLCE2_YEAR_START, VLCE2_YEAR_END + 1))

#: The collection's images are addressed by ``system:index``, not by date —
#: ``filterDate`` on this asset returns nothing. Verified 2026-08-27; this is
#: the trap that makes a naive port of the ACI loader silently produce an empty
#: image.
def image_id(year: int) -> str:
    return f"CA_forest_VLCE2_{year}"


#: The overlap with the ACI's own national coverage — the only years the two
#: products can honestly be compared over.
COMPARABLE_YEAR_START = max(VLCE2_YEAR_START, aafc.ACI_NATIONAL_FROM)
COMPARABLE_YEAR_END = min(VLCE2_YEAR_END, aafc.ACI_YEAR_END)
COMPARABLE_YEARS: List[int] = list(
    range(COMPARABLE_YEAR_START, COMPARABLE_YEAR_END + 1)
)

VLCE2_ATTRIBUTION = (
    "NTEMS VLCE2 — Canadian Forest Service / Hermosilla et al., "
    "Canada land cover 1984–2022, 30 m"
)

# --------------------------------------------------------------------------- #
# Class labels
# --------------------------------------------------------------------------- #
VLCE2_LABELS_EN: Dict[int, str] = {
    0: "Unclassified",
    20: "Water",
    31: "Snow and ice",
    32: "Rock and rubble",
    33: "Exposed and barren land",
    40: "Bryoids",
    50: "Shrubs",
    80: "Wetland",
    81: "Wetland — treed",
    100: "Herbs",
    210: "Coniferous",
    220: "Broadleaf",
    230: "Mixedwood",
}

VLCE2_LABELS_PT: Dict[int, str] = {
    0: "Não classificado",
    20: "Água",
    31: "Neve e gelo",
    32: "Rocha e detritos",
    33: "Solo exposto e estéril",
    40: "Briófitas e liquens",
    50: "Arbustos",
    80: "Área úmida",
    81: "Área úmida arbórea",
    100: "Herbáceas",
    210: "Conífera",
    220: "Folhosa",
    230: "Floresta mista",
}

VLCE2_LABELS: Dict[str, Dict[int, str]] = {
    "en": VLCE2_LABELS_EN,
    "pt": VLCE2_LABELS_PT,
}


def label(class_id: int, lang: str = "en") -> str:
    table = VLCE2_LABELS.get(lang, VLCE2_LABELS_EN)
    return table.get(
        class_id, f"Classe {class_id}" if lang == "pt" else f"Class {class_id}"
    )


# --------------------------------------------------------------------------- #
# Colours
# --------------------------------------------------------------------------- #
#: The published VLCE2 palette. Like the ACI's and MapBiomas', it is prescribed
#: and not colour-blind safe, so the legend always pairs swatch with label.
VLCE2_COLOR_MAP: Dict[int, str] = {
    0: "#686868", 20: "#3333ff", 31: "#ccffff", 32: "#cccccc", 33: "#996633",
    40: "#ffccff", 50: "#ffff00", 80: "#993399", 81: "#9933cc", 100: "#ccff33",
    210: "#006600", 220: "#00cc00", 230: "#cc9900",
}

VLCE2_GAP_COLOR = "cccccc"

#: Dense 0..230 palette for ``getMapId`` — Earth Engine needs one entry per
#: index across the whole min..max range, and VLCE2's codes are sparse.
VLCE2_PALETTE: List[str] = [
    VLCE2_COLOR_MAP[i].lstrip("#") if i in VLCE2_COLOR_MAP else VLCE2_GAP_COLOR
    for i in range(231)
]

VLCE2_VIS = {"min": 0, "max": 230, "palette": VLCE2_PALETTE}


def color(class_id: int) -> str:
    return VLCE2_COLOR_MAP.get(class_id, f"#{VLCE2_GAP_COLOR}")


# --------------------------------------------------------------------------- #
# The comparison vocabulary
# --------------------------------------------------------------------------- #
# The coarse classes BOTH legends genuinely encode. Everything below is a
# judgement call about equivalence, made once, here, in the open — see the
# module docstring for why a class-level comparison would be meaningless
# instead.
#
# ``cropland`` and ``urban`` appear in the ACI and have no VLCE2 counterpart at
# all: VLCE2 buries both in ``herbs`` / ``exposed and barren``. They are kept as
# their own groups rather than folded away, because "the ACI calls this cropland
# and VLCE2 calls it herbs" is exactly the kind of disagreement this tab exists
# to surface — collapsing them would hide the single most common one.

GROUP_ORDER: List[str] = [
    "forest", "wetland", "shrub_herb", "cropland", "water",
    "barren", "urban", "other",
]

GROUP_LABELS_EN: Dict[str, str] = {
    "forest": "Forest",
    "wetland": "Wetland",
    "shrub_herb": "Shrub and herb",
    "cropland": "Cropland and pasture",
    "water": "Water",
    "barren": "Barren, rock, snow",
    "urban": "Urban and developed",
    "other": "Other / no data",
}

GROUP_LABELS_PT: Dict[str, str] = {
    "forest": "Floresta",
    "wetland": "Área úmida",
    "shrub_herb": "Arbustiva e herbácea",
    "cropland": "Lavoura e pastagem",
    "water": "Água",
    "barren": "Solo exposto, rocha, neve",
    "urban": "Área urbana e construída",
    "other": "Outros / sem dado",
}

GROUP_COLORS: Dict[str, str] = {
    "forest": "#1f8d49",
    "wetland": "#993399",
    "shrub_herb": "#d6bc74",
    "cropland": "#ffcc33",
    "water": "#2532e4",
    "barren": "#996633",
    "urban": "#cc6699",
    "other": "#9e9e9e",
}

#: VLCE2 code → group. ``81`` (treed wetland) goes to ``wetland``, not
#: ``forest``: it is a wetland the ACI would also call a wetland, and putting it
#: with forest would manufacture disagreement wherever the ACI is right.
VLCE2_TO_GROUP: Dict[int, str] = {
    210: "forest", 220: "forest", 230: "forest",
    80: "wetland", 81: "wetland",
    50: "shrub_herb", 100: "shrub_herb", 40: "shrub_herb",
    20: "water",
    31: "barren", 32: "barren", 33: "barren",
    0: "other",
}

#: ACI code → the same groups. Built from the legend-derived sets in
#: :mod:`.aafc` rather than re-listing codes, so adding a crop class upstream
#: cannot leave this table stale.
ACI_TO_GROUP: Dict[int, str] = {}
for _code in aafc.ACI_LABELS_EN:
    if _code in aafc.FOREST:
        ACI_TO_GROUP[_code] = "forest"
    elif _code in aafc.WETLAND:
        ACI_TO_GROUP[_code] = "wetland"
    elif _code in aafc.GRASS_SHRUB:
        ACI_TO_GROUP[_code] = "shrub_herb"
    elif _code in aafc.CROPLAND:
        ACI_TO_GROUP[_code] = "cropland"
    elif _code in aafc.WATER:
        ACI_TO_GROUP[_code] = "water"
    elif _code in aafc.BARREN or _code in aafc.BURNT:
        # Burnt area is a disturbance state with no VLCE2 equivalent; it reads
        # as bare ground in both products in the year it happens, so it is
        # grouped with barren rather than given a group only one side can fill.
        ACI_TO_GROUP[_code] = "barren"
    elif _code in aafc.URBAN:
        ACI_TO_GROUP[_code] = "urban"
    else:
        ACI_TO_GROUP[_code] = "other"
del _code


def group_label(group: str, lang: str = "en") -> str:
    table = GROUP_LABELS_PT if lang == "pt" else GROUP_LABELS_EN
    return table.get(group, group)


def aci_group(class_id: int) -> str:
    return ACI_TO_GROUP.get(int(class_id), "other")


def vlce2_group(class_id: int) -> str:
    return VLCE2_TO_GROUP.get(int(class_id), "other")
