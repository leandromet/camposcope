# 01 — Premises

## 1. Why a separate application

The family now has three members, and each is defined by **what kind of object it
studies**:

| App | Object of analysis | Boundary comes from |
|---|---|---|
| **Yvynation** | Protected and Indigenous territories | A curated registry (FUNAI, ICMBio, WDPA) |
| **Naturametrics** | An arbitrary place | A coordinate the user clicks |
| **Camposcope** | **A rural property** | **The CAR — an official, self-declared cadastre** |

That third row is not a variation on the first two, it is a different problem. A CAR
polygon is neither curated nor arbitrary: it is **declared by the landholder**, carries a
legal status (`condicao`, `status_imovel`), a registration date, an area the declarant
stated and an area the geometry actually has. The analysis has to hold all of that at
once — *this is what the land did, and this is what the cadastre says about it* — which is
a framing neither sibling has anywhere to put.

Three consequences shape everything downstream:

1. **The boundary is data, not input.** It is fetched, it can be stale, it can overlap its
   neighbours, and it can disagree with its own declared area. Camposcope must show that,
   not hide it.
2. **Registration date is an analytical axis.** `dat_criacao` splits the MapBiomas series
   into before-CAR and after-CAR. No other app in the family has a meaningful per-object
   date to cut on.
3. **The neighbourhood is the control group.** A property's land-cover profile means
   little in isolation; it means a lot next to the rings around it. This is Yvynation's
   external-ring idea applied to a cadastral parcel.

**What is shared is engineering, not product**: Earth Engine auth and the sized thread
pool, the tile-URL cache, the persistent Leaflet component, the MapBiomas class/colour
dictionaries, the streaming ODS writer, the Reflex state-mixin structure, and Yvynation's
transition/Sankey machinery. All of it is ported deliberately, module by module — see
[02-architecture.md](02-architecture.md) §2 and decision **D2**.

## 2. Scope — v1

The first shippable version does exactly this:

1. **Find a property.** One search box and a map click, all producing the same thing
   ([11-search-and-navigation.md](11-search-and-navigation.md)):
   - paste a `cod_imovel` (`MT-5108501-CBE0F5…`) → exact WFS lookup;
   - paste a coordinate (decimal, DMS, or a Google Maps URL) → a point;
   - click the map → `INTERSECTS` WFS query at that point, disambiguated when several
     properties overlap;
   - pick UF + município → the property list for that municipality, filterable;
   - type a place name → the map is framed there, and **no property is selected**.
2. **Show the cadastral record.** Boundary on the map, and a card with `cod_imovel`,
   `status_imovel`, `condicao`, `dat_criacao` / `data_atualizacao`, declared `area`,
   **geometry-derived area**, `m_fiscal` (módulos fiscais), `tipo_imovel`, `municipio`.
   Where declared and computed area disagree, say so with the delta.
3. **Build the study geometry.** The property polygon itself, plus **neighbourhood rings**
   at 500 m / 2 km / 5 km measured outward from the boundary (not from a centroid —
   see **D3**). Rings are true rings: each excludes the property and every smaller ring.
4. **MapBiomas trajectory 1985–2024** for the property and for each ring, as a stacked
   column chart with the official palette, and as a map layer with a year control.
5. **Transitions as Sankey diagrams** — the property's land cover flowing from one year to
   another, two-stage (year A → year B) and multi-stage across a chosen set of years.
   Ported from Yvynation; see [07-transitions.md](07-transitions.md).
6. **Hansen Global Forest Change** — tree-cover loss year inside the property, the loss
   split at `dat_criacao`, and gain as a separate, undated layer.
7. **Above-ground biomass** from ESA CCI Biomass_cci v6.0 for the property and the rings,
   over its ten snapshots (2007, 2010, 2015–2022).
8. **Satellite context** — Sentinel-2 and Landsat composites, selectable by year, clipped
   to the study area, so the user can look at the place rather than only at its statistics.
9. **SPOT 2008** — the Google Brazil Forest 2008 mosaic at 5–10 m, which is the imagery
   nearest the Código Florestal's own reference date of 22 July 2008, always shown with the
   acquisition dates of the pixels actually covering the property. It is data and a date,
   never a classification — [12-spot-2008.md](12-spot-2008.md) draws the line.
10. **Orientation layers** — the IBGE biome / domain overlay, naming itself on hover, so a
   user can tell where they are before they know what they are looking at.
11. **Export everything** with provenance: a grouped ZIP with `imovel.csv` plus one
   directory per zone (property, each ring), the geometries as GeoJSON, the charts as
   PNG / SVG / HTML / CSV, an ODS workbook for the tabular results.

## 3. Constraints

| | Constraint |
|---|---|
| **C1** | **The viewport never moves on its own.** Layer toggles, year changes and chart interactions must not re-centre the map. (Naturametrics D1; the same custom Leaflet component is ported.) |
| **C2** | **Never store `ee.Geometry` / `ee.Image` in state vars.** State holds GeoJSON dicts and plain values; EE objects are rebuilt inside services. Yvynation violates this and pays for it. |
| **C3** | **Every analysis result carries a `Provenance`.** Export handlers refuse to write a file without one. |
| **C4** | **The CAR is a declaration, never a title.** No screen, label, export header or tooltip may imply that a CAR polygon proves ownership, legality or compliance. See §5. |
| **C5** | **One SICAR request per user gesture, cached.** The GeoServer is a public service run by the SFB; Camposcope must not hammer it. Per-property and per-tile caching, and a hard rate limit. See [05-sicar-geoserver.md](05-sicar-geoserver.md) §6. |
| **C6** | **Earth Engine cost is bounded per property.** The batched reducer pattern (one `reduceRegions` for all 40 years × all zones) is not an optimisation, it is the budget. See [06-ee-layers.md](06-ee-layers.md). |

## 4. Non-goals for v1

- **No APP / Reserva Legal / vegetação nativa themes.** They are *not on the public
  GeoServer* — only property polygons are (verified, [05](05-sicar-geoserver.md) §2). The
  theme shapefiles come from `consultapublica.car.gov.br` behind a captcha, per
  municipality. Any RL/APP reading in v1 would be **our own estimate**, and an estimate
  presented next to official cadastral fields will be read as official. Deferred to Phase 6
  and clearly labelled when it lands.
- **No compliance verdict.** Camposcope does not compute *regularidade ambiental*, does not
  score a property and does not output anything a bank or a buyer could treat as a
  due-diligence result. That is what terra_web's `relatorio-car` and `avalia_imoveis_mt`
  are for, and they are separate products with a separate legal posture.
- **No valuation.** Deliberately: the Score VTM work lives in terra_web.
- **No *área rural consolidada* figure.** Camposcope ships the 2008 imagery and reports when
  it was taken; it does not classify any hectare as consolidated. That is a legal
  determination resting on facts no photograph contains
  ([12-spot-2008.md](12-spot-2008.md) §4).
- **No batch mode over many properties.** Phase 6 at the earliest, and it needs the SICAR
  rate-limit story solved first.
- **No user accounts, no saved projects.** A URL with a `cod_imovel` is the whole
  persistence model.

## 5. The disclosure posture (C4, in full)

The CAR is **auto-declaratório**. A registered polygon means someone drew a boundary and
filed it; `status_imovel = 'AT'` means the registration is active, not that the property is
legal, verified, or the declarant's to sell. `condicao` values such as *"Aguardando
análise"* mean precisely that nobody has checked it yet. Properties overlap. Boundaries
follow no survey.

Concretely this requires:

- a permanent, non-dismissible line under the cadastral card stating the CAR is
  self-declared and does not prove ownership;
- `condicao` and `status_imovel` shown **verbatim from the source**, never re-worded into
  a traffic light;
- overlaps with neighbouring CAR polygons surfaced, not silently dissolved;
- every export carrying the same statement in its provenance block;
- the word *"irregular"* appearing nowhere in the UI.

## 6. Audience

Researchers, journalists, public prosecutors' technical staff, extension agents and
landholders themselves — people who want to see **what happened on a piece of land**, with
the sources named, and who are able to read a chart with a caveat on it. Not a
credit-analysis tool and not a consumer product.
