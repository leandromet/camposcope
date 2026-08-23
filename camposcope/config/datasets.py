"""Basemaps and Earth Engine asset identifiers.

Ported from Naturametrics' ``config/datasets.py`` (decision D2), trimmed to what
Camposcope actually uses. Every entry is documented in doc/04-data-sources.md
with its licence and its caveat.
"""

from __future__ import annotations

from typing import Any, Dict

# --------------------------------------------------------------------------- #
# Basemaps — plain XYZ, no Earth Engine involved
# --------------------------------------------------------------------------- #
# ⚠️ Inherited debt, not a decision: the `mt1.google.com` endpoints are NOT a
# licensed public Google API. They are fast, they work, and they are fine for
# local development. Before any public deployment this must become a Google Maps
# Platform key or fall back to Esri/OSM, which are licensed for this use.
# See doc/04-data-sources.md §7.
BASEMAPS: Dict[str, Dict[str, Any]] = {
    "google_hybrid": {
        "label_pt": "Google — Híbrido",
        "label_en": "Google — Hybrid",
        "url": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        "attribution": "© Google",
        "max_native_zoom": 20,
    },
    "google_satellite": {
        "label_pt": "Google — Satélite",
        "label_en": "Google — Satellite",
        "url": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "attribution": "© Google",
        "max_native_zoom": 20,
    },
    "osm": {
        "label_pt": "OpenStreetMap",
        "label_en": "OpenStreetMap",
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": "© OpenStreetMap contributors",
        "max_native_zoom": 19,
    },
}

# --------------------------------------------------------------------------- #
# MapBiomas Collection 10.1 — doc/04 §2
# --------------------------------------------------------------------------- #
#: One image, forty bands. That shape is what makes the batched reducer possible
#: (doc/06-ee-layers.md §2) — do not "simplify" it into an ImageCollection.
MAPBIOMAS_LULC = {
    "asset": (
        "projects/mapbiomas-public/assets/brazil/lulc/collection10_1/"
        "mapbiomas_brazil_collection10_1_coverage_v1"
    ),
    "year_start": 1985,
    "year_end": 2024,
    "band_template": "classification_{year}",
    "scale_m": 30,
    "attribution": "MapBiomas Collection 10.1 (CC BY-SA 4.0)",
}

# --------------------------------------------------------------------------- #
# Hansen Global Forest Change — doc/04 §3
# --------------------------------------------------------------------------- #
HANSEN_GFC = {
    "asset": "UMD/hansen/global_forest_change_2025_v1_13",
    "loss_year_start": 2001,
    "loss_year_end": 2024,          # lossyear band: 1..24 → 2001..2024
    "treecover_vis": {"min": 0, "max": 100,
                      "palette": ["ffffff", "d9f0a3", "78c679", "238443", "004529"]},
    "loss_color": "#d4271e",
    #: `gain` is a single UNDATED 2000–2012 layer. It cannot go on a timeline and
    #: must never be summed with loss (doc/04 §3).
    "gain_color": "#02d659",
    "attribution": "Hansen/UMD/Google/USGS/NASA — Global Forest Change",
}

# --------------------------------------------------------------------------- #
# ESA CCI Above-Ground Biomass v6.0 — doc/04 §4
# --------------------------------------------------------------------------- #
#: The series has a HOLE: 2007 and 2010 are isolated snapshots, and it only
#: becomes annual in 2015. Charts draw the gap as a gap.
AGB_YEARS = [2007, 2010, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022]
AGB = {
    "asset_template": "ESA/CCI/Above_Ground_Biomass/V6_0/{year}",
    "dataset_id": "ESA/CCI/Above_Ground_Biomass/V6_0",
    #: The product's native resolution. Reducing at MapBiomas' 30 m adds no
    #: detail — EE just resamples a 100 m raster and bills for it.
    "scale_m": 100,
    "vis": {"min": 0, "max": 500, "palette": ["white", "green"]},
    "attribution": "ESA CCI Biomass v6.0 — Santoro & Cartus (2025), CC BY 4.0",
}

# --------------------------------------------------------------------------- #
# Satellite context — doc/04 §5
# --------------------------------------------------------------------------- #
#: HARMONIZED, never the plain collection: it corrects the 2022 processing
#: baseline offset, and the unharmonised one does not.
SENTINEL2 = {
    "collection": "COPERNICUS/S2_SR_HARMONIZED",
    "year_start": 2017,
    "attribution": "Copernicus Sentinel-2",
}

LANDSAT = {
    "collections": {
        "LC09": "LANDSAT/LC09/C02/T1_L2",
        "LC08": "LANDSAT/LC08/C02/T1_L2",
        "LE07": "LANDSAT/LE07/C02/T1_L2",
        "LT05": "LANDSAT/LT05/C02/T1_L2",
    },
    "year_start": 1984,
    "attribution": "USGS Landsat Collection 2 Level-2",
}
