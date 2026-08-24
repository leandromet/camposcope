# 03 — Roadmap

Seven phases. Each has a **done test** — a thing that either works or does not, checkable
from the browser. A phase is not done because its code exists.

| Phase | Theme | Status |
|---|---|---|
| 0 | Skeleton, SICAR service, map | ✅ done |
| 1 | Find a property → boundary + cadastral record | ✅ all four resolvers + município browser done |
| 2 | Zones: rings, areas, overlaps | ✅ done, incl. biome overlay (D13) |
| 3 | MapBiomas trajectory | ✅ done — batched reducer, chart, registration-date marker |
| 4 | Transitions & Sankey | ✅ done — batched reducer, two-stage + multi-stage figures, reconciled against Cobertura |
| 5 | Hansen, biomass, satellite context | planned |
| 6 | Export & provenance | planned |
| 7 | Beyond v1 | speculative |

---

## Phase 0 — Skeleton, SICAR service, map

The repository becomes a running Reflex app that can talk to the CAR GeoServer.

- `rxconfig.py`, `requirements.txt`, `.env.example`, package skeleton.
- `services/sicar.py` — the four queries of [05](05-sicar-geoserver.md) §5, with the
  client rules of §7 enforced, plus its cache.
- `services/ee_client.py`, `ee_concurrency.py`, `tiles.py`, `provenance.py` ported verbatim
  from Naturametrics.
- `components/map/leaflet_map.py` + its `.js` ported verbatim; the CAR WMS layer wired as a
  context layer so all registered properties are visible from the first run.
- `tests/test_app_builds.py` — the import-and-compile smoke test. Naturametrics learned the
  hard way that a Reflex event-handler signature mismatch kills the backend worker while
  the frontend keeps serving, so the symptom is a grey map, not a stack trace. This test is
  cheap and catches it.

**Done test:** `reflex run`, map of Brazil appears, CAR property boundaries draw as a WMS
overlay, and `python -c "from camposcope.services import sicar; print(sicar.by_code('MT-5108501-CBE0F5EDD27A4D7888E7392EA7D44793').municipio)"` prints `Vera`.

## Phase 1 — Find a property

The entry gestures of [01](01-premises.md) §2 and [11](11-search-and-navigation.md), and the
cadastral record.

- **One search box, four resolvers** ([11](11-search-and-navigation.md) §2): `cod_imovel` →
  coordinates → município → place name. Tried in that order, stopping at the first match, so
  the common cases never touch a geocoder. The box **states how it read the input** before
  acting on it.
- Search by `cod_imovel`, with validation of the `UF-<ibge>-<32hex>` shape before any
  network call, and UF extracted from the prefix.
- Coordinate parsing — decimal, DMS, Google Maps URLs, pt-BR decimal commas — with a
  transposed pair refused by name rather than resolved into the South Atlantic
  ([11](11-search-and-navigation.md) §3).
- Click-to-select: UF routing from the local boundary file (**D5**), `INTERSECTS` query,
  and **the chooser when more than one property is returned** — this is the normal case,
  not an edge case ([05](05-sicar-geoserver.md) §5.2).
- Municipality browser off the committed IBGE table (**D12**): UF → município → paged,
  sorted, geometry-less list.
- Place-name search via Nominatim (**D11**), debounced and serialised, which **frames the
  map and selects no property**.
- The cadastral card: every attribute of [05](05-sicar-geoserver.md) §3 verbatim, the
  permanent C4 disclosure line, and a deep link (`/?car=<cod_imovel>`).

**Done test:** each of the four input kinds resolves to the right thing; all gestures land on
the same screen for the same property; a point covered by two overlapping registrations
offers both; a bad code fails before any request leaves the machine; a transposed coordinate
pair is refused with a message naming the problem; and no geocoder request is made for an
input the first three resolvers could handle.

## Phase 2 — Zones

- `services/zones.py`: outward rings in a per-property UTM projection, converted back to
  4326; equal-area computation of `area_ha` for every zone.
- **Declared vs. computed area** shown with its delta and percentage.
- **Neighbour overlaps**: a second `INTERSECTS` query with the property polygon as the
  predicate, listing other CAR registrations that overlap it and by how much. Surfaced,
  never dissolved (C4).
- Ring radii configurable; the zone list is what every later phase consumes.
- **Biome / domain overlay** ported from Naturametrics ([11](11-search-and-navigation.md) §6)
  — the one browser-side vector layer, with its hover naming and its permanent
  "approximate to ~1 km, orientation only" caveat.

**Done test:** a property with a known overlap lists it; ring areas sum correctly; the
rings redraw without moving the viewport (C1); the biome layer names itself on hover and
carries its accuracy caveat.

## Phase 3 — MapBiomas trajectory

- `services/mapbiomas_history.py` ported, reshaped from buffers to zones: **one batched
  `reduceRegions` for all years × all zones**, the pattern that makes this affordable
  ([06](06-ee-layers.md)).
- Stacked column chart per zone, official palette, 1985–2024.
- Land-cover map layer with a year control; tile URLs for all 40 years pre-minted on the EE
  thread pool so scrubbing is instant.
- **The `dat_criacao` marker on the time axis** — the property's own registration date drawn
  on every time series. This is the feature that makes Camposcope Camposcope.

**Done test:** property and rings each get a full 40-year stacked column chart; the year
slider repaints the map with no viewport movement; the registration-date marker is on the
chart and in the exported CSV.

## Phase 4 — Transitions & Sankey

Ported from Yvynation, which already has the EE pattern and the figures
([07](07-transitions.md)).

- `services/transitions.py`: the `band1 * 1000 + band2 → frequencyHistogram` reducer,
  returning `{src_class: {tgt_class: area_ha}}`.
- Two-stage Sankey (year A → year B), with a persistence toggle (`include_unchanged`).
- Multi-stage Sankey across a chosen year set — the default set being
  `1985 · dat_criacao · 2024`, which reads as *before, at registration, now*.
- Per zone, so the property's flows can be compared with its rings'.

**Done test:** the Sankey totals reconcile with the stacked-column areas for the same
years and zone, to within pixel rounding.

## Phase 5 — Hansen, biomass, satellite context

- `services/hansen.py`: tree-cover loss year, **split at `dat_criacao`** (loss before vs.
  after registration), and gain as its own undated layer — never summed with loss.
- `services/biomass.py` ported: ESA CCI Biomass_cci v6.0, its ten snapshots, per zone, with
  the gaps drawn as gaps.
- Sentinel-2 and Landsat composites, selectable by year, clipped to the study area.
- **SPOT 2008** ([12](12-spot-2008.md)) — the visual and false-colour mosaics, licence-gated
  on `CS_SPOT_ENABLED`, and with them the coverage/date reducer: acquisition date range under
  the property, fraction of pixels imaged before 2008-07-22, fraction with no coverage. This
  is the imagery at the Forest Code's own reference date, and it is the place where the app
  is most tempted to cross the line D9 draws.

**Done test:** loss-before / loss-after figures for a property with known post-2020
clearing; the biomass chart shows 2007 and 2010 as isolated points, not interpolated; the
SPOT panel reports its three date/coverage numbers, a property outside the mosaic's footprint
says so rather than showing an empty map, and the word "consolidada" appears nowhere as a
classification of area.

### Phase 5 addendum — Validação tab (QC against reference data)

Ported in spirit from Naturametrics' `compare_mode` (`state/_layers.py`) — a swipe divider,
not just a chart, because the question is "does this classification match reality" and a
map answers that more directly than a table alone.

- `config/ibge_vegetation.py` ported verbatim: the IBGE Vegetação 2022 asset
  (`projects/ee-leandromet/assets/vege_area`, 145 458 polygons, 54-class `legenda_2`), its
  official colours, and the shared natural/anthropic × forest 6-bucket taxonomy used to
  compare it against MapBiomas — the two legends share no classes.
- `services/ibge_vegetation.py` reshaped from Naturametrics' buffers-around-a-point to
  Camposcope's zones: `classified_image()` rasterizes the 145k-polygon FeatureCollection
  once (`reduceToImage`), `mapbiomas_comparison()` runs the same batched
  `reduceRegions(frequencyHistogram)` pattern as every other analysis in this app, and
  `bucket_matrix()` pivots one zone's joint histogram into the 6×6 % table the tab displays.
- Two modes, one swipe divider each: **SPOT × MapBiomas 2008** (reference imagery vs. the
  classification at the Forest Code's own year — visual only, nothing to tabulate) and
  **IBGE × MapBiomas 2022** (two classifications, so the bucket matrix + the two headline
  numbers — forest %, natural % — per source).
- Both pairings reuse whatever the Cobertura tab or Floresta's SPOT toggle already minted —
  same tile-URL cache, same keys.

**Done test:** switching to Validação and choosing a mode draws two clipped layers on the
map with a working swipe handle; the IBGE mode's bucket matrix reconciles to the zone's
total area; a property with heavy post-2022 clearing shows IBGE reading more "natural
forest" than MapBiomas for the same zone (IBGE's polygons are coarser and don't track
year-to-year change the way MapBiomas' per-pixel classification does) — verified live on
the test property: IBGE 35.9% natural vs. MapBiomas 20.7%, consistent with its
pasture→soy trajectory in Cobertura.

## Phase 6 — Export & provenance

- Grouped ZIP: `imovel.csv` + one directory per zone + `geometries.geojson` +
  `provenance.json`.
- Flat long-format CSV alternative; ODS workbook via the streaming writer.
- Every chart as PNG / SVG / HTML / CSV.
- **C3 enforced**: the export refuses to write any result lacking a `Provenance`, and every
  file carries `sicar_queried_at` and the C4 disclosure.

**Done test:** an export opened a week later still says which datasets, which scales, which
day the cadastre was read, and that the CAR is self-declared.

## Phase 7 — Beyond v1 (not committed)

Listed so they are not mistaken for oversights:

- **RL / APP themes**, if and when a licensed, automatable source exists — with our own
  estimates clearly labelled as estimates ([01](01-premises.md) §4).
- **Vegetation age** — Naturametrics' estimator applied to the property; a good fit,
  deliberately held back until the core loop is solid.
- **Landscape metrics** — fragmentation of the property vs. its rings.
- **Batch mode** over a municipality — blocked on the SICAR rate-limit story (C5).
- **PRODES / DETER alerts** inside the property.
- **Deployment** — Cloud Run, mirroring Naturametrics' D10. Not needed while the app is
  developed locally, and the shape of the SICAR caching decides the instance sizing.
