"""Basemaps and Earth Engine asset identifiers.

Ported from Naturametrics' ``config/datasets.py`` (decision D2), trimmed to what
Camposcope actually uses. Every entry is documented in doc/04-data-sources.md
with its licence and its caveat.
"""

from __future__ import annotations

import os

from typing import Any, Dict

from .settings import SPOT_ENABLED

# --------------------------------------------------------------------------- #
# Basemaps — plain XYZ, no Earth Engine involved
# --------------------------------------------------------------------------- #
# The `mt1.google.com` endpoints are the same undocumented tile servers
# Yvynation/Naturametrics use — not a documented Google Maps Platform API in
# their own right. Cloud Run now deploys under a GCP project with the Google
# Maps API activated (2026-09), which is the account-level cover this needed
# before it went to production as the default (`google_hybrid`,
# cloudbuild.yaml); Esri/OSM remain the fallback options below either way.
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
    "esri_imagery": {
        "label_pt": "Esri — Satélite",
        "label_en": "Esri — Imagery",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": "Tiles © Esri",
        "max_native_zoom": 19,
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


# --------------------------------------------------------------------------- #
# SPOT 2008 — doc/12-spot-2008.md
# --------------------------------------------------------------------------- #
# ⚠️ Licence-gated: requires accepting the "Brazil Forest Imagery Dataset 2008"
# agreement, granted per service account. Verified accessible from
# ee-leandromet on 2026-08-23.
#
# This is NOT just a basemap. The Código Florestal's *área rural consolidada*
# turns on 22 July 2008, and this is the only 5-10 m imagery near that date.
# The `date` band carries per-pixel acquisition time as Unix epoch seconds, and
# the layer is never shown without reporting the dates actually under the
# property — see services/spot.py and doc/12 §3.
EE_BASEMAPS: Dict[str, Dict[str, Any]] = {
    "spot_2008_visual": {
        "label_pt": "SPOT 2008 — Visual (Brasil)",
        "label_en": "SPOT 2008 — Visual (Brazil)",
        "asset": "GOOGLE/BRAZIL_FOREST_2008/V1/VISUAL",
        "vis": {"bands": ["R", "G", "B"], "min": 0, "max": 255},
        "attribution": (
            "Google LLC, Brazil Forest Imagery Dataset 2008 created from circa "
            "2008 SPOT images"
        ),
        "max_native_zoom": 16,
        "note_pt": "Mosaico SPOT ~2008, só sobre áreas florestais do Brasil.",
        "note_en": "SPOT mosaic, ~2008, covering only Brazil's forest areas.",
    },
    "spot_2008_analytic": {
        "label_pt": "SPOT 2008 — Falsa-cor (NIR)",
        "label_en": "SPOT 2008 — False colour (NIR)",
        "asset": "GOOGLE/BRAZIL_FOREST_2008/V1/ANALYTIC",
        # N,R,G puts near-infrared in the red channel: 2008 vegetation reads
        # bright red, which is what makes it legible against pasture.
        "vis": {"bands": ["N", "R", "G"], "min": [156, 62, 53],
                "max": [6408, 2584, 2211], "gamma": 0.9},
        "attribution": (
            "Google LLC, Brazil Forest Imagery Dataset 2008 created from circa "
            "2008 SPOT images"
        ),
        "max_native_zoom": 16,
        "note_pt": "Infravermelho em vermelho: vegetação de 2008 aparece realçada.",
        "note_en": "Near-infrared shown in red: 2008 vegetation appears highlighted.",
    },
}

#: Bands carried into provenance alongside the imagery (doc/12 §3).
SPOT_META_BANDS = ["date", "scale", "satellite"]

#: Lei 12.651/2012 art. 3º IV — *área rural consolidada* is occupation preexisting
#: this date. Camposcope reports how each property's SPOT pixels fall relative to
#: it, and classifies NOTHING (doc/12 §4, decision D9).
FOREST_CODE_CUTOFF_EPOCH = 1_216_684_800      # 2008-07-22T00:00:00Z
FOREST_CODE_CUTOFF_ISO = "2008-07-22"
#: The calendar year alone — Hansen's ``lossyear`` band has no sub-annual
#: precision, so a year-granular split (services/hansen.py) can only place the
#: cutoff on a year boundary, not the exact July date. Loss recorded in 2008
#: itself is grouped with "up to 2008" rather than split further, since there
#: is no month field to split it by.
FOREST_CODE_CUTOFF_YEAR = 2008

#: Every basemap the panel offers, XYZ and Earth Engine alike, in display order.
#: The SPOT entries are dropped entirely when the licence flag is off, rather
#: than offered and then failing.
ALL_BASEMAPS: Dict[str, Dict[str, Any]] = {
    **BASEMAPS,
    **(EE_BASEMAPS if SPOT_ENABLED else {}),
}


def is_ee_basemap(key: str) -> bool:
    """EE basemaps need a tile URL minted per session, so they are switched on by
    a background event rather than a plain state write."""
    return key in EE_BASEMAPS


# --------------------------------------------------------------------------- #
# IBGE biomes, domains and natural regions — doc/11 §6, decision D13
# --------------------------------------------------------------------------- #
#: 271 polygons, verified accessible 2026-08-23. Delivered to the browser as a
#: SIMPLIFIED vector (~1.5 km) because it must name itself on hover, which a tile
#: cannot do. Orientation only: boundaries from this layer are approximate to
#: roughly a kilometre and must never decide which biome a property falls in.
IBGE_BIOME_DOMAIN = {
    "asset": "projects/ee-leandromet/assets/ibge_biome_domain_250k",
    "attribution": "IBGE — Biomas e domínios morfoclimáticos 1:250.000",
    "fields": {
        "biome": "nm_bm",
        "phyto_domain": "nm_dm_fito",
        "natural_region": "nm_reg_nat",
        "vegetation": "vg_dom",
    },
    #: The seven values in `nm_bm`, verified against the asset. Order is the
    #: legend order.
    "biomes": [
        "Amazônia", "Cerrado", "Mata Atlântica", "Caatinga",
        "Pampa", "Pantanal", "Ilhas Oceânicas",
    ],
    #: Roughly IBGE's own biome cartography, ported verbatim from Naturametrics.
    "palette": {
        "Amazônia": "1a7f37",
        "Cerrado": "d9a441",
        "Mata Atlântica": "2f6f4e",
        "Caatinga": "c96a3a",
        "Pampa": "8fbf5a",
        "Pantanal": "3f8fbf",
        "Ilhas Oceânicas": "8a6fbf",
    },
    "fill_alpha": "59",     # ~35% — a wash, not a mask
    "outline_alpha": "ff",
    "outline_width": 1.5,
    "simplify_m": 1500,
    "coord_decimals": 2,
}

# --------------------------------------------------------------------------- #
# IBGE municípios — doc/11 §4, decision D12
# --------------------------------------------------------------------------- #
#: The *list* comes from the committed CSV (services/municipios.py); this asset
#: supplies the *geometry*, for framing and clipping. `cod_municipio_ibge` joins
#: them. A dropdown must not wait on an Earth Engine round trip, and a boundary
#: must not be approximated by a bounding box.
#:
#: 5 573 features, verified 2026-08-23. `CD_MUN` is the 7-digit IBGE code **as a
#: string** — the join to data/municipios.csv's integer `cod_municipio_ibge`, so
#: every filter casts explicitly rather than relying on EE's coercion.
IBGE_MUNICIPIOS = {
    "asset": os.environ.get(
        "CS_MUNICIPIOS_ASSET",
        "projects/ee-leandromet/assets/br_municipios_2025",
    ),
    "attribution": "IBGE — Malhas territoriais municipais 2025",
    "fields": {
        "code": "CD_MUN",          # string, 7 digits
        "name": "NM_MUN",
        "uf": "SIGLA_UF",
        "uf_name": "NM_UF",
        "area_km2": "AREA_KM2",
        "region": "NM_REGIAO",
        "immediate_region": "NM_RGI",
        "intermediate_region": "NM_RGINT",
    },
}

# --------------------------------------------------------------------------- #
# Territórios protegidos — terras indígenas (FUNAI) e unidades de conservação
# (CNUC/ICMBio)
# --------------------------------------------------------------------------- #
#: Both layers work exactly like IBGE_BIOME_DOMAIN above — browser-side vectors
#: rather than Earth Engine tiles, because each polygon has to name itself on
#: hover and carry a permanent on-map label, which a tile cannot do.
#:
#: They differ in where the geometry comes from. The biome layer is built from
#: an Earth Engine asset on first request and cached; these two are built
#: offline by ``scripts/fetch_territorios.py`` from the FUNAI and CNUC
#: GeoPackages and **committed** — reading a GeoPackage needs geopandas/fiona,
#: which are deliberately not runtime dependencies (doc/09-dev-environment.md
#: §5), and the source files are not in this repo for a deploy to rebuild from.
#:
#: Orientation only, exactly as the biome layer is: simplified to ~200 m and
#: rounded to ~110 m, so a boundary drawn here must never decide whether a
#: property falls inside a protected area. Nothing in this app asks it to.
#:
#: The two colours are fixed rather than per-feature palettes: one layer, one
#: hue, so a reader can tell the two apart at a glance without consulting a
#: legend. Gold for terras indígenas, dark purple for unidades de conservação.
FUNAI_TERRAS_INDIGENAS = {
    "data_file": "terras_indigenas.geojson.gz",
    "attribution": "FUNAI — Terras Indígenas (poligonais e portarias)",
    "color": "d4af37",          # gold
    "fill_alpha": "59",         # ~35% — a wash, not a mask
    "outline_width": 1.6,
    # `rotulo`, not `nome`: the on-map label is a ~92 px wrapped block, and
    # the official CNUC name leads with its category ("RESERVA PARTICULAR DO
    # PATRIMÔNIO NATURAL TOCA FURADA") — eight wrapped lines of which seven
    # repeat what the swatch and the tooltip already say.
    # `scripts/fetch_territorios.py` writes the short form alongside the full
    # one; the tooltip, the search list and territorios.csv all keep `nome`.
    "label_property": "rotulo",
    "tooltip": [
        {"label": "Terra indígena", "property": "nome"},
        {"label": "Etnia", "property": "etnia"},
        {"label": "Fase", "property": "fase"},
        {"label": "UF", "property": "uf"},
        {"label": "Municípios", "property": "municipios"},
        {"label": "Área (ha)", "property": "area_ha"},
    ],
}

ICMBIO_UNIDADES_CONSERVACAO = {
    "data_file": "unidades_conservacao.geojson.gz",
    "attribution": "MMA/ICMBio — Cadastro Nacional de Unidades de Conservação (CNUC)",
    "color": "4b0082",          # dark purple
    "fill_alpha": "59",
    "outline_width": 1.6,
    # `rotulo`, not `nome`: the on-map label is a ~92 px wrapped block, and
    # the official CNUC name leads with its category ("RESERVA PARTICULAR DO
    # PATRIMÔNIO NATURAL TOCA FURADA") — eight wrapped lines of which seven
    # repeat what the swatch and the tooltip already say.
    # `scripts/fetch_territorios.py` writes the short form alongside the full
    # one; the tooltip, the search list and territorios.csv all keep `nome`.
    "label_property": "rotulo",
    "tooltip": [
        {"label": "Unidade de conservação", "property": "nome"},
        {"label": "Categoria", "property": "categoria"},
        {"label": "Grupo", "property": "grupo"},
        {"label": "Esfera", "property": "esfera"},
        {"label": "Órgão gestor", "property": "gestor"},
        {"label": "UF", "property": "uf"},
        {"label": "Área (ha)", "property": "area_ha"},
    ],
}

#: ``tipo`` in ``data/territorios.csv`` → its layer config. One dict, so the
#: service, the state and the search all agree on the two type keys.
TERRITORIOS = {
    "indigena": FUNAI_TERRAS_INDIGENAS,
    "conservacao": ICMBIO_UNIDADES_CONSERVACAO,
}
