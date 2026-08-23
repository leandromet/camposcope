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

Used for one thing Camposcope specifically needs: **dated** loss, which splits cleanly at
the property's `dat_criacao`.

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

## 6. IBGE UF boundaries — local, committed

A **simplified** GeoJSON of the 27 UF polygons, committed to `data/`, used only to route a
map click to the right `sicar_imoveis_<uf>` layer (**D5**). Simplified aggressively —
it never needs to be accurate to the metre, only correct about which state a point is in,
and near a state line the property query itself is the arbiter.

Source: IBGE malhas territoriais, public domain with attribution.

## 7. Basemaps

Ported from Naturametrics along with its open caveat: the default Google tile endpoints
(`mt1.google.com/vt`) are **undocumented, not a licensed API**. They work and they are fast,
and they are fine for local development. Before any public deployment this must become
either a Google Maps Platform key or a fall back to Esri/OSM, which are licensed for this
use. Carried here as an inherited debt, not a decision.

## 8. Attribution block

Every export and the About page carry, in full:

> Cadastro Ambiental Rural (CAR) — Serviço Florestal Brasileiro, via `geoserver.car.gov.br`.
> **Os dados do CAR são autodeclaratórios e não constituem prova de propriedade,
> regularidade ou posse.**
> MapBiomas Collection 10.1 (CC BY-SA 4.0) · Hansen Global Forest Change, Hansen/UMD/Google/USGS/NASA (CC BY 4.0) ·
> ESA CCI Biomass v6.0, Santoro & Cartus 2025 (CC BY 4.0) · Copernicus Sentinel-2 · USGS Landsat ·
> Malhas territoriais IBGE · Processado no Google Earth Engine.
