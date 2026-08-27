"""Basemaps and Earth Engine asset identifiers for the Canada page.

Three kinds of entry live here, and the distinction matters:

**Shared, imported unchanged.** The plain XYZ basemaps, Hansen Global Forest
Change and ESA CCI Biomass are global products with no Canadian variant — they
are re-exported from :mod:`camposcope.config.datasets` rather than copied, so a
change to the Hansen version number happens once and reaches both pages.

**Substituted.** SPOT 2008 is a Brazilian mosaic tied to a Brazilian legal date
and has no Canadian counterpart. In its place the page offers **annual Landsat
composites** (``LANDSAT/COMPOSITES/C02/T1_L2_ANNUAL``, verified 2026-08-27:
43 images, 1984–2026, one cloud-free composite per year, global). Where SPOT was
one snapshot to toggle on, this is a 43-year series to scrub through — strictly
more useful as a visual reference, and it reaches back before the ACI starts,
which is the only way to see a parcel's pre-2009 condition at all.

**New.** MODIS MCD64A1 burned area, backing the Fogo tab. See its own section
for why this rather than a Canadian product.
"""

from __future__ import annotations

from typing import Any, Dict

# Re-exported unchanged — global products, one definition, both pages.
from ...config.datasets import AGB, AGB_YEARS, BASEMAPS, HANSEN_GFC  # noqa: F401

# --------------------------------------------------------------------------- #
# AAFC Annual Crop Inventory — the MapBiomas substitute
# --------------------------------------------------------------------------- #
#: The land-cover product this page's Cobertura and Transições tabs are built
#: on. The details (years, coverage limits, legend) are in
#: :mod:`canada.config.aafc`; this entry exists so provenance and attribution
#: read from the same table every other dataset does.
ACI = {
    "asset": "AAFC/ACI",
    "year_start": 2009,
    "year_end": 2025,
    "scale_m": 30,
    "attribution": "Agriculture and Agri-Food Canada — Annual Crop Inventory",
}

# --------------------------------------------------------------------------- #
# Landsat annual composites — the SPOT 2008 substitute
# --------------------------------------------------------------------------- #
LANDSAT_ANNUAL = {
    "asset": "LANDSAT/COMPOSITES/C02/T1_L2_ANNUAL",
    "year_start": 1984,
    "year_end": 2026,
    "attribution": (
        "Landsat annual composites — USGS/NASA, Collection 2 Tier 1 Level-2"
    ),
}

#: Bands are named ``blue, green, red, nir, swir1, swir2, thermal`` — **not**
#: Collection-2's ``SR_B*`` ids — and carry scaled reflectance in roughly 0–1.
#: So the vis ranges below are reflectance, not DN, and `max` is 0.3 for true
#: colour because vegetated land sits well under 1.0: stretching to 1.0 renders
#: most of Canada near-black.
LANDSAT_RENDERINGS: Dict[str, Dict[str, Any]] = {
    "landsat_true": {
        "label_en": "Landsat — True colour",
        "label_pt": "Landsat — Cor natural",
        "note_en": "Annual cloud-free composite. Pick the year in the legend.",
        "note_pt": "Composto anual sem nuvens. Escolha o ano na legenda.",
        "vis": {"bands": ["red", "green", "blue"], "min": 0.0, "max": 0.3,
                "gamma": 1.2},
        "max_native_zoom": 14,
    },
    "landsat_nir": {
        "label_en": "Landsat — False colour (NIR)",
        "label_pt": "Landsat — Falsa-cor (NIR)",
        "note_en": ("Near-infrared in the red channel: vegetation reads bright "
                    "red, which makes clearings, burns and cutblocks legible."),
        "note_pt": ("Infravermelho no canal vermelho: a vegetação aparece em "
                    "vermelho vivo, realçando cortes, queimadas e talhões."),
        "vis": {"bands": ["nir", "red", "green"], "min": 0.0, "max": 0.4,
                "gamma": 1.2},
        "max_native_zoom": 14,
    },
}

#: The year a Landsat basemap opens on. 2022 rather than the latest available:
#: it is the last year VLCE2 also covers, so the imagery under the Validação
#: tab lines up with both products being compared.
LANDSAT_DEFAULT_YEAR = 2022

# --------------------------------------------------------------------------- #
# MODIS MCD64A1 burned area — the MapBiomas Fogo substitute
# --------------------------------------------------------------------------- #
# ⚠️ This is a **coarse** product and the UI must say so. 463 m pixels against
# MapBiomas Fogo's 30 m: a fire smaller than roughly 20 ha will not register at
# all, and a burn's edge is placed to within about half a kilometre. For a
# 4 000 ha ranch that is a usable screening layer; for a 2 ha parcel it is not,
# and the tab says which case it is in rather than printing a precise-looking
# percentage of a number it cannot resolve.
#
# **Why not a Canadian product.** The National Burned Area Composite (NBAC) and
# the Canadian National Fire Database are the authoritative national sources and
# are far better resolved — but neither is published in Earth Engine (four
# candidate asset paths checked on 2026-08-27, all absent). Ingesting them would
# mean this app maintaining a private mirror of a dataset NRCan revises annually.
# MCD64A1 is global, current to within a couple of months, and needs no such
# copy. Revisit if NBAC ever lands in the public catalogue.
MODIS_BURN = {
    "asset": "MODIS/061/MCD64A1",
    "band": "BurnDate",
    #: The collection starts 2000-11 and the newest image is partway through the
    #: current year, so only whole years are offered — a partial year would read
    #: as a quiet fire season when it is really an incomplete one.
    "year_start": 2001,
    "year_end": 2025,
    "scale_m": 500,
    "attribution": (
        "MODIS MCD64A1 v6.1 Burned Area — Giglio, Justice, Boschetti & Roy, "
        "NASA LP DAAC"
    ),
    #: The colour ramp's ceiling — calibrated against the *observed*
    #: distribution, not the theoretical one. "One possible burn per year
    #: across the 25-year record" would put this at 25, which is the trap: at
    #: 500 m almost nothing in Canada reburns that often. Sampled nationally
    #: at native scale on 2026-08-27 (``ee.Reducer.frequencyHistogram()`` over
    #: all of Canada): 4.28M pixels at frequency 1, 206K at 2, dropping to
    #: single digits by 7–9, with exactly one pixel ever reaching 9. A ceiling
    #: of 25 compresses that whole distribution into the bottom third of the
    #: ramp, which is what painted the map a near-uniform pale wash instead of
    #: a gradient — reproduced and fixed 2026-08-27. 8 covers every pixel but
    #: the single outlier at 9, which clips to the top colour instead of
    #: stretching the ramp for it.
    "max_frequency": 8,
    "vis_palette": ["ffffb2", "fecc5c", "fd8d3c", "f03b20", "bd0026", "800026"],
}

MODIS_BURN_YEARS = list(
    range(MODIS_BURN["year_start"], MODIS_BURN["year_end"] + 1)
)

#: Below this parcel area the fire numbers are reported with an explicit
#: "coarser than this parcel" warning: a 463 m pixel is ~21 ha, so a parcel of
#: a few hundred hectares is only a handful of pixels across and its burned
#: fraction is dominated by pixel-edge effects.
FIRE_MIN_MEANINGFUL_HA = 500.0

# --------------------------------------------------------------------------- #
# NTEMS forest age — a Canadian bonus the Brazil page cannot have
# --------------------------------------------------------------------------- #
#: ``CANADA/NFIS/NTEMS/CA_FOREST_AGE`` publishes a **measured** stand age, where
#: Brazil has to derive one by counting years a pixel stayed vegetated in a
#: series that only starts in 1985. Two properties, verified 2026-08-27:
#:
#: * It must be read through ``.mosaic()``. Sampling ``.first()`` returns null
#:   everywhere — the single-image collection does not resolve to a plain Image
#:   the way ``ee.Image(asset)`` would.
#: * It is **masked to forested pixels**: a null means "not forest here", not
#:   "no data". That is the semantics the Floresta tab wants, and why the
#:   non-forest share is reported rather than silently dropped.
NTEMS_AGE = {
    "asset": "CANADA/NFIS/NTEMS/CA_FOREST_AGE",
    "band": "forest",
    #: Ages are "as of" this year. A stand reported as 40 y old is ~47 y old
    #: today — the UI says so rather than quietly ageing the numbers forward,
    #: which would be inventing precision.
    "reference_year": 2019,
    "scale_m": 30,
    "vis": {"min": 0, "max": 200,
            "palette": ["d9f0a3", "addd8e", "78c679", "41ab5d", "238443",
                        "006837", "004529"]},
    "attribution": "NRCan / NFIS — NTEMS Canada forest age (2019)",
}

# --------------------------------------------------------------------------- #
# Basemap panel
# --------------------------------------------------------------------------- #
#: Every basemap the panel offers, XYZ and Earth Engine alike, in display order.
#: Unlike the Brazil page's ``ALL_BASEMAPS`` there is no licence flag to gate on
#: — the Landsat composites are public, so nothing here can be dropped at import
#: time and no option can appear that then fails.
ALL_BASEMAPS: Dict[str, Dict[str, Any]] = {
    **BASEMAPS,
    **LANDSAT_RENDERINGS,
}


def is_ee_basemap(key: str) -> bool:
    """EE basemaps need a tile URL minted per session, so they are switched on
    by a background event rather than a plain state write."""
    return key in LANDSAT_RENDERINGS
