"""Ecozones of Canada — the navigation overlay, Canada's answer to IBGE biomes.

Source: the **National Ecological Framework for Canada** (Agriculture and
Agri-Food Canada / Environment Canada, developed 1991–1999), open.canada.ca
dataset ``3ef8e8a9-8d05-4fea-a8bf-7f5023d2b6e1``. Fifteen terrestrial ecozones,
verified against the live service on 2026-08-27.

**Why the ArcGIS FeatureServer and not an Earth Engine asset.** The Brazil
page's biome layer comes from an EE asset because that is where IBGE's polygons
already lived. There is no equivalent published EE asset for the Canadian
ecozones, and uploading one would mean this app maintaining a private copy of
federal data that upstream can revise without telling us. The framework is
published as a plain ArcGIS REST service and as pre-packaged GeoJSON, so the
polygons are fetched from source, simplified once, and disk-cached — the same
three-tier memo/disk/gzip arrangement :mod:`camposcope.services.biomes` uses,
minus the Earth Engine round trip.

**Orientation only, exactly like the biome layer.** Nothing this app reports is
derived from which ecozone a parcel falls in. The polygons are simplified for
delivery to the browser (they must name themselves on hover, which a raster tile
cannot do), so boundaries drawn from this layer are approximate and must never
decide anything.
"""

from __future__ import annotations

from typing import Dict, List

# --------------------------------------------------------------------------- #
# Source
# --------------------------------------------------------------------------- #
#: The ArcGIS REST layer. ``maxRecordCount`` is 2000 and there are 15 ecozones
#: (in a few hundred polygon parts), so one paged query fetches the lot.
ECOZONE_FEATURESERVER = (
    "https://services.arcgis.com/lGOekm0RsNxYnT3j/arcgis/rest/services/"
    "National_ecological_framework_of_Canada_ecozones/FeatureServer/0"
)

#: The pre-packaged GeoJSON, used as the fallback when the REST service is
#: unreachable. Full resolution and large, which is why it is not the primary.
ECOZONE_GEOJSON_URL = (
    "https://agriculture.canada.ca/atlas/data_donnees/"
    "nationalEcologicalFramework/data_donnees/geoJSON/ez/"
    "nef_ca_ter_ecozone_v2_2.geojson"
)

ECOZONE_DATASET_PAGE = (
    "https://open.canada.ca/data/en/dataset/"
    "3ef8e8a9-8d05-4fea-a8bf-7f5023d2b6e1"
)

ATTRIBUTION = (
    "National Ecological Framework for Canada — Agriculture and Agri-Food "
    "Canada / Environment Canada (Open Government Licence — Canada)"
)

#: Field names on the service, verified 2026-08-27.
FIELDS = {
    "id": "ECOZONE_ID",
    "name_en": "ECOZONE_NAME_EN",
    "name_fr": "ECOZONE_NAME_FR",
}

# --------------------------------------------------------------------------- #
# The fifteen ecozones
# --------------------------------------------------------------------------- #
#: ``ECOZONE_ID`` → English name, exactly as the service publishes them
#: (including its own spellings). Portuguese is a gloss added here — the
#: framework publishes English and French only.
ECOZONE_NAMES_EN: Dict[int, str] = {
    1: "Arctic Cordillera",
    2: "Northern Arctic",
    3: "Southern Arctic",
    4: "Taiga Plains",
    5: "Taiga Shield",
    6: "Boreal Shield",
    7: "Atlantic Maritime",
    8: "Mixedwood Plains",
    9: "Boreal Plains",
    10: "Prairies",
    11: "Taiga Cordillera",
    12: "Boreal Cordillera",
    13: "Pacific Maritime",
    14: "Montane Cordillera",
    15: "Hudson Plains",
}

ECOZONE_NAMES_PT: Dict[int, str] = {
    1: "Cordilheira Ártica",
    2: "Ártico Setentrional",
    3: "Ártico Meridional",
    4: "Planícies da Taiga",
    5: "Escudo da Taiga",
    6: "Escudo Boreal",
    7: "Marítima do Atlântico",
    8: "Planícies de Floresta Mista",
    9: "Planícies Boreais",
    10: "Pradarias",
    11: "Cordilheira da Taiga",
    12: "Cordilheira Boreal",
    13: "Marítima do Pacífico",
    14: "Cordilheira Montana",
    15: "Planícies Hudsonianas",
}

#: The six that reach British Columbia — the only ones a parcel on this page can
#: actually fall in. Kept so the legend can lead with them instead of listing
#: fifteen, twelve of which are unreachable from any BC parcel.
BC_ECOZONE_IDS: List[int] = [4, 9, 10, 11, 12, 13, 14]

#: Roughly the framework's own cartography — cool blues and greys for the
#: arctic/taiga zones, greens through the boreal and maritime forests, warm
#: tones for the prairies. Keyed by English name because that is the string
#: carried in the delivered GeoJSON and the value the browser colours on.
PALETTE: Dict[str, str] = {
    "Arctic Cordillera": "b9c6d6",
    "Northern Arctic": "d5dde6",
    "Southern Arctic": "9fb4c7",
    "Taiga Plains": "8fbfa8",
    "Taiga Shield": "6fa88f",
    "Boreal Shield": "3f8f6a",
    "Atlantic Maritime": "2f6f4e",
    "Mixedwood Plains": "6cbf5a",
    "Boreal Plains": "7fbf7a",
    "Prairies": "d9a441",
    "Taiga Cordillera": "a8bfd6",
    "Boreal Cordillera": "5f9fa8",
    "Pacific Maritime": "1a7f8f",
    "Montane Cordillera": "8a6fbf",
    "Hudson Plains": "3f8fbf",
}

DEFAULT_COLOR = "9e9e9e"

#: Simplification tolerance and matching coordinate precision — the same trade
#: ``services/biomes.py`` documents: rounding finer than the simplification adds
#: bytes without adding accuracy. 2 km here rather than Brazil's 1.5 km because
#: the ecozones are a coarser framework over a larger country.
SIMPLIFY_M = 2000
COORD_DECIMALS = 2

FILL_ALPHA = "59"        # ~35 % — a wash, not a mask
OUTLINE_WIDTH = 1.5

#: Fifteen labels across the whole of Canada is legible; the same labels over a
#: single parcel are noise. Below this zoom the on-map labels are hidden
#: regardless of the toggle — same mechanism as the Brazil biome layer.
LABEL_MIN_ZOOM = 5


def name(ecozone_id: int, lang: str = "en") -> str:
    table = ECOZONE_NAMES_PT if lang == "pt" else ECOZONE_NAMES_EN
    return table.get(int(ecozone_id), f"Ecozone {ecozone_id}")


def color(name_en: str) -> str:
    return PALETTE.get(name_en, DEFAULT_COLOR)
