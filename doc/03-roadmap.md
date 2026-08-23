# 03 — Roadmap

Seven phases. Each has a **done test** — a thing that either works or does not, checkable
from the browser. A phase is not done because its code exists.

| Phase | Theme | Status |
|---|---|---|
| 0 | Skeleton, SICAR service, map | ✅ done |
| 1 | Find a property → boundary + cadastral record | 🚧 code + map click done; município browser pending |
| 2 | Zones: rings, areas, overlaps | 🚧 services done; UI partial |
| 3 | MapBiomas trajectory | planned |
| 4 | Transitions & Sankey | planned |
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

The three entry gestures of [01](01-premises.md) §2, and the cadastral record.

- Search by `cod_imovel`, with validation of the `UF-<ibge>-<32hex>` shape before any
  network call, and UF extracted from the prefix.
- Click-to-select: UF routing from the local boundary file (**D5**), `INTERSECTS` query,
  and **the chooser when more than one property is returned** — this is the normal case,
  not an edge case ([05](05-sicar-geoserver.md) §5.2).
- Municipality browser: UF select → município select → paged, sorted, geometry-less list.
- The cadastral card: every attribute of [05](05-sicar-geoserver.md) §3 verbatim, the
  permanent C4 disclosure line, and a deep link (`/?car=<cod_imovel>`).

**Done test:** all three gestures land on the same screen for the same property; a point
covered by two overlapping registrations offers both; a bad code fails before any request
leaves the machine.

## Phase 2 — Zones

- `services/zones.py`: outward rings in a per-property UTM projection, converted back to
  4326; equal-area computation of `area_ha` for every zone.
- **Declared vs. computed area** shown with its delta and percentage.
- **Neighbour overlaps**: a second `INTERSECTS` query with the property polygon as the
  predicate, listing other CAR registrations that overlap it and by how much. Surfaced,
  never dissolved (C4).
- Ring radii configurable; the zone list is what every later phase consumes.

**Done test:** a property with a known overlap lists it; ring areas sum correctly; the
rings redraw without moving the viewport (C1).

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

**Done test:** loss-before / loss-after figures for a property with known post-2020
clearing; the biomass chart shows 2007 and 2010 as isolated points, not interpolated.

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
