"""Who made this, how to cite it, and what must be credited.

Lives in ``config`` rather than beside the dialog that displays it because
constraint **C4** (doc/01-premises.md) applies to every way the facts leave the
app — the "Como citar" panel and the metadata sheet of every export have to say
the same thing, and two copies drift.

Single-author citation, unlike Naturametrics: Camposcope is Leandro's own
project. ``DATA_SOURCES`` is Camposcope's own list — CAR/SICAR plus everything
in doc/04-data-sources.md — not copied from Naturametrics' broader multi-author
list, even though several datasets (MapBiomas, Hansen, ESA CCI Biomass) are
shared between the two apps.
"""

from __future__ import annotations

APP_URL = "https://camposcope-mxkgbkorua-uw.a.run.app"
APP_YEAR = "2026"

AUTHORS = [
    ("Leandro Meneguelli Biondo",
     "University of British Columbia Okanagan (UBC Okanagan), Canadá"),
]

AUTHORS_EN = [
    (name, inst.replace("Canadá", "Canada"))
    for name, inst in AUTHORS
]

CITATION_TEXT = (
    f"Biondo, L. M. ({APP_YEAR}). Camposcope: análise de imóveis rurais do "
    "Cadastro Ambiental Rural. University of British Columbia Okanagan. "
    f"Disponível em: {APP_URL}"
)

BIBTEX = f"""@software{{camposcope_{APP_YEAR},
  title   = {{Camposcope: análise de imóveis rurais do Cadastro Ambiental Rural}},
  author  = {{Biondo, Leandro Meneguelli}},
  year    = {{{APP_YEAR}}},
  organization = {{University of British Columbia Okanagan}},
  url     = {{{APP_URL}}}
}}"""

#: Constraint C4 — every source the app draws on is credited here, whether or
#: not the current property happens to use all of them (doc/04-data-sources.md).
DATA_SOURCES = [
    ("CAR / SICAR",
     "Serviço Florestal Brasileiro — Cadastro Ambiental Rural, via "
     "geoserver.car.gov.br. Dados autodeclaratórios; não constituem prova de "
     "propriedade, posse ou regularidade ambiental.",
     "https://www.car.gov.br"),
    ("MapBiomas — Coleção 10.1",
     "Projeto MapBiomas — Mapeamento Anual de Cobertura e Uso da Terra no "
     "Brasil. Licença CC-BY-SA. Base das abas «Cobertura» e «Transições».",
     "https://mapbiomas.org"),
    ("Hansen Global Forest Change",
     "Hansen, M. C. et al. (2013). High-Resolution Global Maps of 21st-Century "
     "Forest Cover Change. Science 342, 850–853. Licença CC-BY 4.0. Base da "
     "aba «Floresta».",
     "https://glad.earthengine.app/view/global-forest-change"),
    ("ESA CCI Biomass (Biomass_cci) v6.0",
     "Santoro, M.; Cartus, O. (2025). ESA Biomass Climate Change Initiative "
     "(Biomass_cci): Global datasets of forest above-ground biomass for the "
     "years 2007, 2010, 2015–2022, v6.0. NERC EDS Centre for Environmental "
     "Data Analysis. doi:10.5285/95913ffb6467447ca72c4e9d8cf30501. Base da "
     "aba «Biomassa».",
     "https://doi.org/10.5285/95913ffb6467447ca72c4e9d8cf30501"),
    ("Google Brazil Forest Imagery Dataset 2008 (SPOT)",
     "Google LLC — mosaico de imagens SPOT de aproximadamente 2008, sobre "
     "áreas florestais do Brasil. Referência visual para a data de corte do "
     "Código Florestal (22/07/2008); Camposcope não classifica área "
     "consolidada.",
     "https://developers.google.com/earth-engine/datasets/catalog/"
     "GOOGLE_BRAZIL_FOREST_2008_V1_VISUAL"),
    ("IBGE — Biomas e domínios morfoclimáticos",
     "IBGE — Biomas e domínios morfoclimáticos do Brasil, 1:250.000. Camada "
     "de orientação; limites aproximados (~1 km).",
     "https://www.ibge.gov.br"),
    ("IBGE — Malhas territoriais e localidades",
     "Fronteiras de UF e município, e o cadastro de municípios usado na "
     "busca.",
     "https://www.ibge.gov.br"),
    ("Nominatim (OpenStreetMap)",
     "Busca de lugares. © colaboradores do OpenStreetMap, licença ODbL.",
     "https://nominatim.openstreetmap.org"),
    ("Google Earth Engine",
     "Gorelick, N. et al. (2017). Google Earth Engine: Planetary-scale "
     "geospatial analysis for everyone. Remote Sensing of Environment 202, "
     "18–27.",
     "https://earthengine.google.com"),
    ("Mapas base",
     "Esri World Imagery; OpenStreetMap contributors; Google.",
     "https://www.openstreetmap.org/copyright"),
]

DATA_SOURCES_EN = [
    ("CAR / SICAR",
     "Brazilian Forest Service — Rural Environmental Registry, via "
     "geoserver.car.gov.br. Self-declared data; does not constitute proof of "
     "ownership, possession or environmental compliance.",
     "https://www.car.gov.br"),
    ("MapBiomas — Collection 10.1",
     "MapBiomas Project — Annual Land Use and Land Cover Mapping in Brazil. "
     "CC-BY-SA license. Basis of the «Cobertura» and «Transições» tabs.",
     "https://mapbiomas.org"),
    ("Hansen Global Forest Change",
     "Hansen, M. C. et al. (2013). High-Resolution Global Maps of 21st-Century "
     "Forest Cover Change. Science 342, 850–853. CC-BY 4.0 license. Basis of "
     "the «Floresta» tab.",
     "https://glad.earthengine.app/view/global-forest-change"),
    ("ESA CCI Biomass (Biomass_cci) v6.0",
     "Santoro, M.; Cartus, O. (2025). ESA Biomass Climate Change Initiative "
     "(Biomass_cci): Global datasets of forest above-ground biomass for the "
     "years 2007, 2010, 2015–2022, v6.0. NERC EDS Centre for Environmental "
     "Data Analysis. doi:10.5285/95913ffb6467447ca72c4e9d8cf30501. Basis of "
     "the «Biomassa» tab.",
     "https://doi.org/10.5285/95913ffb6467447ca72c4e9d8cf30501"),
    ("Google Brazil Forest Imagery Dataset 2008 (SPOT)",
     "Google LLC — circa-2008 SPOT mosaic, over Brazil's forest areas. Visual "
     "reference for the Forest Code's cutoff date (22 July 2008); Camposcope "
     "does not classify consolidated area.",
     "https://developers.google.com/earth-engine/datasets/catalog/"
     "GOOGLE_BRAZIL_FOREST_2008_V1_VISUAL"),
    ("IBGE — Biomes and morphoclimatic domains",
     "IBGE — Brazil's biomes and morphoclimatic domains, 1:250,000. "
     "Orientation layer; boundaries approximate (~1 km).",
     "https://www.ibge.gov.br"),
    ("IBGE — Territorial meshes and localities",
     "UF and município boundaries, and the município catalogue used in "
     "search.",
     "https://www.ibge.gov.br"),
    ("Nominatim (OpenStreetMap)",
     "Place search. © OpenStreetMap contributors, ODbL licence.",
     "https://nominatim.openstreetmap.org"),
    ("Google Earth Engine",
     "Gorelick, N. et al. (2017). Google Earth Engine: Planetary-scale "
     "geospatial analysis for everyone. Remote Sensing of Environment 202, "
     "18–27.",
     "https://earthengine.google.com"),
    ("Base maps",
     "Esri World Imagery; OpenStreetMap contributors; Google.",
     "https://www.openstreetmap.org/copyright"),
]
