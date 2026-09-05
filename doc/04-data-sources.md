# 04 — Data sources

Every dataset Camposcope reads, with its licence, its resolution, and the specific way it
will mislead you if you are careless. Asset identifiers verified against the Earth Engine
catalogue and the live GeoServer on **2026-08-23**.

## 1. The cadastre — SICAR / CAR

| | |
|---|---|
| **Source** | Serviço Florestal Brasileiro, `geoserver.car.gov.br` (OGC WFS/WMS) |
| **Layers** | `sicar:sicar_imoveis_<uf>`, 27 of them — one per UF ([05](05-sicar-geoserver.md)) |
| **CRS** | EPSG:4674 (SIRGAS 2000) native; server reprojects on request |
| **Scale** | 218 105 polygons in MT alone |
| **Licence** | Public data under the Lei de Acesso à Informação; attribution to SFB/SICAR required |
| **Updated** | Continuously; `data_atualizacao` is per-record and often `null` |

**The trap:** the CAR is **auto-declaratório**. The polygon is what the landholder drew.
It is not a survey, it is not a title, and neighbouring registrations overlap routinely.
`condicao = "Aguardando análise"` is the most common state and means nobody has checked it.
Constraint **C4** ([01](01-premises.md) §5) exists entirely because of this row, and it
governs every label in the UI.

Second trap: `area` is **declared**, and it is not the area of `geo_area_imovel`. Camposcope
computes the geometric area itself and shows both. Where they disagree materially that is
information, not an error to hide.

Not available here: APP, Reserva Legal, vegetação nativa, área consolidada, hidrografia.
See [05](05-sicar-geoserver.md) §2.

## 2. MapBiomas Collection 10.1 — land cover 1985–2024

| | |
|---|---|
| **Asset** | `projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_coverage_v1` |
| **Bands** | `classification_1985` … `classification_2024` — one image, 40 bands |
| **Resolution** | 30 m |
| **Licence** | CC BY-SA 4.0 — attribution *and* share-alike |

The single-image-many-bands shape is what makes the batched reducer possible
([06](06-ee-layers.md) §2): all 40 years come out of one `reduceRegions` call.

**The trap:** MapBiomas is a classification, not a measurement. Class flicker between
adjacent years is common in mixed pixels, and a one-year "conversion" that reverts the next
year is usually noise. Never report a single-year transition as an event; the Sankey work
([07](07-transitions.md)) chooses year *pairs* far enough apart to be meaningful, and says
so under the figure.

The class ids, Portuguese and English labels, and the official palette are ported verbatim
from Naturametrics' `config/mapbiomas.py`. **Do not re-derive the palette** — the official
one is what makes the charts recognisable to anyone who has seen a MapBiomas map.

## 3. Hansen Global Forest Change

| | |
|---|---|
| **Asset** | `UMD/hansen/global_forest_change_2025_v1_13` |
| **Bands used** | `treecover2000`, `lossyear` (1–24 → 2001–2024), `gain` |
| **Resolution** | ~30 m |
| **Licence** | CC BY 4.0 — Hansen/UMD/Google/USGS/NASA |

Used for one thing Camposcope specifically needs: **dated** loss, bucketed into three
periods anchored on the two dates that actually govern a CAR property — **até 2008** (the
Forest Code's own reference year for *área rural consolidada*), **2008 até o registro**, and
**depois do registro** (the property's own `dat_criacao`). See `services/hansen.py` for the
exact boundary rule (Hansen's `lossyear` has no month, so the cutoff falls on the year, not
the 22 July date).

**Three traps.** (1) `gain` is **undated** — it is a single 2000–2012 layer and cannot be
placed on a timeline or summed with loss; it is drawn as its own layer and never enters an
arithmetic. (2) "Forest" here is tree *cover*, so it counts eucalyptus and mature oil palm
as forest; on a property with planted forest the Hansen and MapBiomas readings will
disagree and both are right. (3) Loss is not deforestation — it includes harvest, fire and
windthrow.

## 4. ESA CCI Above-Ground Biomass v6.0

| | |
|---|---|
| **Asset** | `ESA/CCI/Above_Ground_Biomass/V6_0/{year}` — one asset per year |
| **Years** | 2007, 2010, **2015–2022** |
| **Resolution** | 100 m native |
| **Licence** | CC BY 4.0 — Santoro & Cartus (2025), doi:10.5285/95913ffb6467447ca72c4e9d8cf30501 |

Ported from Naturametrics, including the stitching step that turns "one asset per year"
back into a single multi-band image so it costs one `reduceRegions` like everything else.

**The trap:** the series has a **hole**. 2007 and 2010 are isolated snapshots; the run only
becomes annual in 2015. Charts must draw the gap as a gap. Reduce at 100 m — reducing at
MapBiomas' 30 m does not add detail, it only makes EE resample and bills you for it.

## 5. Sentinel-2 and Landsat — context imagery

| | |
|---|---|
| **Sentinel-2** | `COPERNICUS/S2_SR_HARMONIZED`, 10–20 m, 2017– |
| **Landsat** | `LANDSAT/LC09/C02/T1_L2`, `LC08`, `LE07`, `LT05` — Collection 2 Level-2, 30 m, 1984– |
| **Licence** | Copernicus open licence; USGS public domain |

Composites only — Camposcope shows imagery so the user can *look* at the property, and
computes nothing from it in v1. Cloud-masked median composites per year, clipped to the
study area.

**The trap:** `S2_SR_HARMONIZED` handles the 2022 processing-baseline offset; the
unharmonised collection does not. Use the harmonised one and nothing else.

## 6. Google Brazil Forest Imagery Dataset 2008 (SPOT)

| | |
|---|---|
| **Assets** | `GOOGLE/BRAZIL_FOREST_2008/V1/VISUAL` and `.../ANALYTIC` |
| **Resolution** | 5 m (visual) / 10 m (analytic) |
| **Coverage** | Brazil's **forest areas only** — partial by design |
| **Licence** | Standard public Earth Engine catalog asset — access is scoped to the GCP project (`ee-leandromet`), not per calling account. `CS_SPOT_ENABLED` was shipped `false` at first on the mistaken assumption it needed per-account acceptance; corrected 2026-08 (doc/12 §2). |
| **Attribution** | Google LLC, Brazil Forest Imagery Dataset 2008, created from circa 2008 SPOT images |

Not just another basemap. The Código Florestal's *área rural consolidada* hinges on
**22 July 2008**, and this is the only imagery Camposcope has at that date and at that
resolution. Both assets verified accessible from `ee-leandromet` on 2026-08-23.

**The trap, and it is a serious one:** the mosaic is *circa* 2008 and the `date` band carries
per-pixel acquisition time as Unix epoch seconds. Over the test property the pixels date to
22 May and 11 June 2008 — before the cutoff — but that is a property-by-property fact, not a
property of the dataset. Never present this imagery as showing the cutoff date without
reporting the acquisition dates actually under the property. Full treatment, including the
line between observation and legal classification, in [12-spot-2008.md](12-spot-2008.md).

## 7. IBGE biomes, domains and natural regions

| | |
|---|---|
| **Asset** | `projects/ee-leandromet/assets/ibge_biome_domain_250k` — 271 polygons, verified 2026-08-23 |
| **Scale** | 1:250 000, simplified to ~1.5 km for delivery |
| **Licence** | IBGE, public data with attribution |

Ported from Naturametrics, including its delivery mechanism: the only layer served to the
browser as **vector** rather than tiles, because it must name itself on hover.

**The trap:** the delivered geometry is approximate to roughly a kilometre. It is an
orientation aid, never an input to a number ([11](11-search-and-navigation.md) §6).

## 8. IBGE municípios

Two representations of the same 5 570 units ([11](11-search-and-navigation.md) §4):

- **`data/municipios.csv`** — committed, ~200 kB, drives the cascading selector and the
  type-ahead. `cod_municipio_ibge` is what the WFS filter needs, so this table is also what
  makes the municipality browser possible without querying the CAR layer for its own index.
- **An Earth Engine asset** under `ee-leandromet` — supplies the *geometry*, for framing and
  clipping. Registered in `config/datasets.py::IBGE_MUNICIPIOS`.

`cod_municipio_ibge` joins them. Source: IBGE localidades API and malhas territoriais.

## 9. Nominatim (OpenStreetMap) — place search

| | |
|---|---|
| **Endpoint** | `nominatim.openstreetmap.org/search`, `countrycodes=br` |
| **Licence** | ODbL — attribution required *with the results*, not only in an About page |

Used only as the last of four resolvers ([11](11-search-and-navigation.md) §2, §5), because
rural properties largely do not have addresses.

**The trap:** its usage policy caps it at roughly one request per second and forbids bulk
use. Debounced, submit-only, serialised, cached — and never called at all when a code, a
coordinate or a município name would have answered.

## 10. IBGE Vegetação do Brasil (1:250.000, 2022)

| | |
|---|---|
| **Asset** | `projects/ee-leandromet/assets/vege_area` — 145 458 polygons, verified accessible from this project 2026-08 |
| **Class field** | `legenda_2` (`leg2_id`, 1–54) — ported verbatim from Naturametrics, see `config/ibge_vegetation.py` |
| **Licence** | IBGE, public data with attribution |

Ground-truth vegetation classification, used only for the Validação tab's IBGE × MapBiomas
2022 comparison ([03](03-roadmap.md) Phase 5 addendum) — never as an input to any property
number, since its 54-class taxonomy shares no classes with MapBiomas and comparing them
requires reducing both to a shared 6-bucket grouping first.

**The trap:** it is a *vector* asset rasterized once per session (`reduceToImage`), not a
pre-baked raster — treating `vege_area` as if it were already an image would silently drop
every feature's classification.

## 11. IBGE UF boundaries — local, committed

A **simplified** GeoJSON of the 27 UF polygons, committed to `data/`, used only to route a
map click to the right `sicar_imoveis_<uf>` layer (**D5**). Simplified aggressively —
it never needs to be accurate to the metre, only correct about which state a point is in,
and near a state line the property query itself is the arbiter.

Source: IBGE malhas territoriais, public domain with attribution.

## 11b. FUNAI terras indígenas and CNUC unidades de conservação — local, committed

Two **simplified**, pre-gzipped GeoJSON files plus one CSV catalogue, committed to `data/`
and built offline by `scripts/fetch_territorios.py` from the FUNAI and CNUC GeoPackages.
657 terras indígenas and 3 247 unidades de conservação (2026-05 snapshot).

They serve two purposes and only two: **map overlays** (gold for terras indígenas, dark
purple for unidades de conservação, labelled from zoom 8) and a **search resolver** that
frames the map on a named territory ([11-search-and-navigation.md](11-search-and-navigation.md)
§6b). Simplified to ~200 m and rounded to ~110 m — orientation, never a determination that a
property falls inside one. They are not an input to any number this app reports.

Committed rather than fetched at runtime because reading a GeoPackage needs
geopandas/fiona, which are deliberately absent from `requirements.txt`
([09-dev-environment.md](09-dev-environment.md) §5), and the source files are not in this
repo — same reasoning as §11 above.

Sources: FUNAI — Terras Indígenas (poligonais e portarias); MMA/ICMBio — Cadastro Nacional
de Unidades de Conservação (CNUC). Both public data with attribution.

## 12. Basemaps

Ported from Naturametrics along with its open caveat: the default Google tile endpoints
(`mt1.google.com/vt`) are undocumented, not a licensed Maps Platform API in their own
right. As of 2026-09 the GCP project backing this app's Cloud Run deployment has the
Google Maps API activated, which is the account-level cover this needed; `google_hybrid`
is now the production default (cloudbuild.yaml). Esri/OSM remain available as fallback
options in `BASEMAPS`.

## 13. Attribution block

Every export and the About page carry, in full:

> Cadastro Ambiental Rural (CAR) — Serviço Florestal Brasileiro, via `geoserver.car.gov.br`.
> **Os dados do CAR são autodeclaratórios e não constituem prova de propriedade,
> regularidade ou posse.**
> MapBiomas Collection 10.1 (CC BY-SA 4.0) · Hansen Global Forest Change, Hansen/UMD/Google/USGS/NASA (CC BY 4.0) ·
> ESA CCI Biomass v6.0, Santoro & Cartus 2025 (CC BY 4.0) · Copernicus Sentinel-2 · USGS Landsat ·
> Google LLC, Brazil Forest Imagery Dataset 2008, criado a partir de imagens SPOT de aproximadamente 2008 ·
> IBGE — biomas e domínios morfoclimáticos 1:250.000, malhas territoriais e localidades ·
> Funai — Terras Indígenas (poligonais e portarias) · MMA/ICMBio — Cadastro Nacional de Unidades de Conservação (CNUC) ·
> Busca de lugares © colaboradores do OpenStreetMap (ODbL) · Processado no Google Earth Engine.
