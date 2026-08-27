"""Who made this, how to cite it, and what the Canada page must credit.

Same role as :mod:`camposcope.config.citation`, and separate from it for the
same reason that module gives for not reusing Naturametrics' list: the citation
panel and the metadata sheet of every export have to say the same thing, and the
two pages draw on different data. Only the *author* and the software citation
are shared — this is one app with two workspaces, not two apps.

``DATA_SOURCES`` here is the Canadian list. Nothing Brazilian appears in it, and
nothing here appears in the Brazil list, except the two global products both
pages genuinely use (Hansen and ESA CCI Biomass), which are stated in both
because a reader of either page has to be able to credit what they saw.
"""

from __future__ import annotations

from ...config.citation import APP_URL, APP_YEAR, AUTHORS, AUTHORS_EN  # noqa: F401

CANADA_URL = f"{APP_URL}/canada"

CITATION_TEXT_EN = (
    f"Biondo, L. M. ({APP_YEAR}). Camposcope Canada: rural property analysis "
    "from the ParcelMap BC parcel fabric. University of British Columbia "
    f"Okanagan. Available at: {CANADA_URL}"
)

CITATION_TEXT_PT = (
    f"Biondo, L. M. ({APP_YEAR}). Camposcope Canadá: análise de propriedades "
    "rurais a partir da malha fundiária ParcelMap BC. University of British "
    f"Columbia Okanagan. Disponível em: {CANADA_URL}"
)

BIBTEX = f"""@software{{camposcope_canada_{APP_YEAR},
  title   = {{Camposcope Canada: rural property analysis from the ParcelMap BC parcel fabric}},
  author  = {{Biondo, Leandro Meneguelli}},
  year    = {{{APP_YEAR}}},
  organization = {{University of British Columbia Okanagan}},
  url     = {{{CANADA_URL}}}
}}"""

#: Every source the Canada page draws on, whether or not the current parcel
#: happens to use all of them. Tuples are ``(name, description, url)`` and the
#: two lists are index-aligned — the citation dialog zips them.
DATA_SOURCES_EN = [
    ("ParcelMap BC — Parcel Fabric",
     "Land Title and Survey Authority of British Columbia, via the BC Data "
     "Catalogue and openmaps.gov.bc.ca. A record of legal parcel boundaries, "
     "not of ownership: it carries no owner names and establishes no title. "
     "Open Government Licence — British Columbia.",
     "https://catalogue.data.gov.bc.ca/dataset/parcelmap-bc-parcel-fabric"),
    ("AAFC Annual Crop Inventory",
     "Agriculture and Agri-Food Canada — Annual Crop Inventory, 2009–2025, "
     "30 m. National coverage from 2011; the inventory stops at roughly "
     "54–58°N. Basis of the «Cobertura» and «Transições» tabs. Open "
     "Government Licence — Canada.",
     "https://www.agr.gc.ca/atlas/aci"),
    ("NTEMS VLCE2 — Canada land cover",
     "Hermosilla, T., Wulder, M. A., White, J. C., Coops, N. C. — Virtual Land "
     "Cover Engine v2, Canadian Forest Service NTEMS, 1984–2022, 30 m. The "
     "independent product the «Validação» tab checks the ACI against.",
     "https://opendata.nfis.org/mapserver/nfis-change_eng.html"),
    ("National Ecological Framework for Canada",
     "Agriculture and Agri-Food Canada / Environment Canada — terrestrial "
     "ecozones. Orientation layer; boundaries are approximate at the scale "
     "delivered here and decide nothing. Open Government Licence — Canada.",
     "https://open.canada.ca/data/en/dataset/"
     "3ef8e8a9-8d05-4fea-a8bf-7f5023d2b6e1"),
    ("Hansen Global Forest Change",
     "Hansen, M. C. et al. (2013). High-Resolution Global Maps of "
     "21st-Century Forest Cover Change. Science 342, 850–853. CC BY 4.0. "
     "Basis of the «Floresta» tab. Gain is a single undated 2000–2012 layer "
     "and is never summed with dated loss.",
     "https://glad.earthengine.app/view/global-forest-change"),
    ("NTEMS Canada forest age",
     "Natural Resources Canada / NFIS — measured stand age as of 2019, 30 m, "
     "masked to forested pixels. Shown alongside Hansen in the «Floresta» tab.",
     "https://opendata.nfis.org"),
    ("ESA CCI Biomass (Biomass_cci) v6.0",
     "Santoro, M.; Cartus, O. (2025). ESA Biomass Climate Change Initiative: "
     "global datasets of forest above-ground biomass for 2007, 2010 and "
     "2015–2022, v6.0. NERC EDS CEDA. "
     "doi:10.5285/95913ffb6467447ca72c4e9d8cf30501. Basis of the «Biomassa» "
     "tab; the series has a real gap and is never interpolated.",
     "https://doi.org/10.5285/95913ffb6467447ca72c4e9d8cf30501"),
    ("MODIS MCD64A1 v6.1 Burned Area",
     "Giglio, L., Justice, C., Boschetti, L., Roy, D. — NASA LP DAAC, "
     "2000–present, 463 m. Basis of the «Fogo» tab. Coarse: a fire under "
     "roughly 20 ha does not register, so the tab reports whether the parcel "
     "is large enough for the numbers to mean anything.",
     "https://lpdaac.usgs.gov/products/mcd64a1v061/"),
    ("Landsat annual composites",
     "USGS/NASA Landsat Collection 2 Tier 1 Level-2, annual cloud-free "
     "composites 1984–2026. The visual reference series, reaching back well "
     "before the crop inventory starts.",
     "https://developers.google.com/earth-engine/datasets/catalog/"
     "LANDSAT_COMPOSITES_C02_T1_L2_ANNUAL"),
    ("BC administrative boundaries",
     "Province of British Columbia — ABMS municipalities and regional "
     "districts, used by the parcel browser and for framing the map.",
     "https://catalogue.data.gov.bc.ca"),
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

DATA_SOURCES_PT = [
    ("ParcelMap BC — malha fundiária",
     "Land Title and Survey Authority da Colúmbia Britânica, via o BC Data "
     "Catalogue e openmaps.gov.bc.ca. Registro de limites legais de parcelas, "
     "não de propriedade: não traz nomes de proprietários e não estabelece "
     "titularidade. Open Government Licence — British Columbia.",
     "https://catalogue.data.gov.bc.ca/dataset/parcelmap-bc-parcel-fabric"),
    ("AAFC Annual Crop Inventory",
     "Agriculture and Agri-Food Canada — inventário anual de culturas, "
     "2009–2025, 30 m. Cobertura nacional a partir de 2011; o inventário "
     "termina por volta de 54–58°N. Base das abas «Cobertura» e «Transições». "
     "Open Government Licence — Canada.",
     "https://www.agr.gc.ca/atlas/aci"),
    ("NTEMS VLCE2 — cobertura da terra do Canadá",
     "Hermosilla, T., Wulder, M. A., White, J. C., Coops, N. C. — Virtual Land "
     "Cover Engine v2, NTEMS / Serviço Florestal Canadense, 1984–2022, 30 m. "
     "O produto independente contra o qual a aba «Validação» confere o ACI.",
     "https://opendata.nfis.org/mapserver/nfis-change_eng.html"),
    ("Cadre écologique national pour le Canada",
     "Agriculture and Agri-Food Canada / Environment Canada — ecozonas "
     "terrestres. Camada de orientação; os limites são aproximados na escala "
     "entregue aqui e não decidem nada. Open Government Licence — Canada.",
     "https://open.canada.ca/data/en/dataset/"
     "3ef8e8a9-8d05-4fea-a8bf-7f5023d2b6e1"),
    ("Hansen Global Forest Change",
     "Hansen, M. C. et al. (2013). High-Resolution Global Maps of "
     "21st-Century Forest Cover Change. Science 342, 850–853. Licença CC BY "
     "4.0. Base da aba «Floresta». O ganho é uma camada única e sem data "
     "(2000–2012) e nunca é somado à perda datada.",
     "https://glad.earthengine.app/view/global-forest-change"),
    ("NTEMS — idade de povoamento florestal",
     "Natural Resources Canada / NFIS — idade medida do povoamento em 2019, "
     "30 m, mascarada aos pixels florestais. Exibida junto ao Hansen na aba "
     "«Floresta».",
     "https://opendata.nfis.org"),
    ("ESA CCI Biomass (Biomass_cci) v6.0",
     "Santoro, M.; Cartus, O. (2025). ESA Biomass Climate Change Initiative: "
     "conjuntos globais de biomassa florestal acima do solo para 2007, 2010 e "
     "2015–2022, v6.0. NERC EDS CEDA. "
     "doi:10.5285/95913ffb6467447ca72c4e9d8cf30501. Base da aba «Biomassa»; "
     "a série tem lacuna real e nunca é interpolada.",
     "https://doi.org/10.5285/95913ffb6467447ca72c4e9d8cf30501"),
    ("MODIS MCD64A1 v6.1 — área queimada",
     "Giglio, L., Justice, C., Boschetti, L., Roy, D. — NASA LP DAAC, "
     "2000–presente, 463 m. Base da aba «Fogo». Grosseiro: um incêndio abaixo "
     "de cerca de 20 ha não é registrado, por isso a aba informa se a parcela "
     "é grande o bastante para os números significarem algo.",
     "https://lpdaac.usgs.gov/products/mcd64a1v061/"),
    ("Compostos anuais Landsat",
     "USGS/NASA Landsat Collection 2 Tier 1 Level-2, compostos anuais sem "
     "nuvens 1984–2026. A série de referência visual, que alcança bem antes "
     "do início do inventário de culturas.",
     "https://developers.google.com/earth-engine/datasets/catalog/"
     "LANDSAT_COMPOSITES_C02_T1_L2_ANNUAL"),
    ("Limites administrativos da BC",
     "Província da Colúmbia Britânica — municípios e distritos regionais "
     "ABMS, usados pelo navegador de parcelas e para enquadrar o mapa.",
     "https://catalogue.data.gov.bc.ca"),
    ("Nominatim (OpenStreetMap)",
     "Busca de lugares. © colaboradores do OpenStreetMap, licença ODbL.",
     "https://nominatim.openstreetmap.org"),
    ("Google Earth Engine",
     "Gorelick, N. et al. (2017). Google Earth Engine: Planetary-scale "
     "geospatial analysis for everyone. Remote Sensing of Environment 202, "
     "18–27.",
     "https://earthengine.google.com"),
    ("Mapas base",
     "Esri World Imagery; colaboradores do OpenStreetMap; Google.",
     "https://www.openstreetmap.org/copyright"),
]
