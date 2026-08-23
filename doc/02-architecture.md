# 02 — Architecture

## 1. Stack

| Concern | Choice | Why not something else |
|---|---|---|
| App framework | **Reflex 0.8.27** | Same minor as Yvynation and Naturametrics, so ported components compile unchanged |
| Cadastre | **OGC WFS/WMS** against `geoserver.car.gov.br` ([05](05-sicar-geoserver.md)) | It is the official source; anything else is a copy |
| Remote sensing | **Earth Engine Python API** | MapBiomas, Hansen, ESA CCI, S2/Landsat all live there |
| Map | **Leaflet**, one persistent instance | Ported component; constraint C1 |
| Charts | **Plotly** via `rx.plotly` | Sankey needs it; the rest is consistency |
| Geometry | **shapely** + **pyproj** | Rings, areas, overlaps — all local, none of it needs EE |
| Tabular | **pandas** | |
| Config | `.env` via `python-dotenv` | |

Python **3.12** in a project-local `.venv`.

## 2. Package layout

```
camposcope/
├─ rxconfig.py                  # frontend 3020 / backend 8021 (see 09 §2)
├─ camposcope/
│  ├─ __init__.py
│  ├─ camposcope.py             # rx.App(), add_page()
│  ├─ config/
│  │  ├─ settings.py            # EE project, scales, ring radii, limits, SICAR base URL
│  │  ├─ mapbiomas.py           # class ids, labels, palette, groupings   [ported]
│  │  ├─ datasets.py            # EE asset ids, year ranges, vis params   [ported, trimmed]
│  │  └─ sicar.py               # layer names, attribute names, UF list, condicao vocabulary
│  ├─ state/
│  │  ├─ __init__.py            # AppState = mixins + rx.State
│  │  ├─ _imovel.py             # ← the new one: search, selection, cadastral record
│  │  ├─ _zones.py              # property + rings geometry lifecycle
│  │  ├─ _layers.py             # visible layers, tile URLs, active year   [ported, trimmed]
│  │  ├─ _analysis.py           # MapBiomas / Hansen / biomass jobs        [ported, reshaped]
│  │  ├─ _transitions.py        # ← the new one: Sankey year selection + figures
│  │  ├─ _export.py             # export selection + download handlers     [ported]
│  │  └─ _ui.py                 # panels, tabs, language, toasts           [ported]
│  ├─ services/
│  │  ├─ sicar.py               # ← the new one: the only module that knows the GeoServer
│  │  ├─ zones.py               # ← the new one: property polygon → rings, areas, overlaps
│  │  ├─ ee_client.py           # EE init + auth                           [ported verbatim]
│  │  ├─ ee_concurrency.py      # sized EE thread pool + HTTP pool fix     [ported verbatim]
│  │  ├─ tiles.py               # getMapId + tile-URL cache                [ported verbatim]
│  │  ├─ geo.py                 # geometry conversion, equal-area helpers  [ported]
│  │  ├─ mapbiomas_history.py   # the batched multi-year reducer           [ported, zones not buffers]
│  │  ├─ transitions.py         # ← ported from Yvynation's compute_transitions
│  │  ├─ hansen.py              # loss year, gain, split at dat_criacao
│  │  ├─ biomass.py             # ESA CCI Biomass_cci v6.0                 [ported]
│  │  ├─ layers.py              # EE layer registry → vis params           [ported, trimmed]
│  │  ├─ provenance.py          # the Provenance dataclass                 [ported verbatim]
│  │  ├─ exports.py             # ZIP/CSV/GeoJSON assembly                 [ported, reshaped]
│  │  └─ ods.py                 # streaming ODS writer                     [ported verbatim]
│  ├─ components/
│  │  ├─ map/leaflet_map.py     # persistent Leaflet component + .js       [ported verbatim]
│  │  ├─ search.py              # ← the new one: the three entry gestures
│  │  ├─ cadastro.py            # ← the new one: the cadastral record card
│  │  ├─ charts.py              # stacked columns, biomass series          [ported]
│  │  ├─ sankey.py              # ← two-stage + multi-stage Sankey
│  │  ├─ layer_panel.py         # layer toggles, year control              [ported, trimmed]
│  │  ├─ results.py             # result tabs                              [ported, reshaped]
│  │  ├─ exports.py             # export panel                             [ported]
│  │  └─ layout.py              # shell, sidebar, header                   [ported]
│  ├─ api/__init__.py           # extra FastAPI routes (downloads, healthz, UF geojson)
│  └─ assets/                   # leaflet_map.js, css, logo
├─ data/
│  ├─ uf_boundaries.simplified.geojson   # committed — click → UF routing (D5)
│  └─ cache/                    # gitignored
├─ scripts/                     # offline prep, not imported by the app
├─ tests/
└─ doc/
```

**Selective port, fresh package (D2).** Nothing is copied wholesale. Each ported module is
brought over one at a time, its Naturametrics-specific assumptions stripped, and its
docstring updated to say where it came from and what changed. What is explicitly *not*
ported: `ifn.py`, `conglomerado.py`, `user_points.py`, `region_geometry.py`, `biomes.py`,
`ibge_vegetation.py`, `vegetation_age.py`, `landscape_metrics.py`, `abuse_control.py`, the
whole `canada/` subpackage. Several of those are good and may come back later (vegetation
age and landscape metrics are obvious Phase 5 candidates); carrying them in on day one
would mean maintaining code no screen calls.

## 3. The central abstraction: **zones**

Naturametrics analyses *buffers around a point*. Yvynation analyses *a territory and rings
around it*. Camposcope analyses **zones**, and every service takes a list of them:

```python
@dataclass(frozen=True)
class Zone:
    key: str          # "imovel" | "ring_500m" | "ring_1km" | "ring_2km" | "ring_5km"
    label: str        # "Imóvel", "0–500 m", "500 m – 1 km", …
    geojson: dict     # EPSG:4326, the geometry itself (C2: never an ee.Geometry)
    area_ha: float    # computed in an equal-area projection, not declared
    kind: str         # "property" | "ring"
```

Zone 0 is always the property. Rings are **true rings measured outward from the boundary**
(`boundary.buffer(r)` minus `boundary.buffer(r_prev)`), not concentric discs around a
centroid — a 40 000 ha property and a 12 ha one have nothing comparable about their
centroids, but "the first 500 m outside the fence" means the same thing for both. Decision
**D3**.

Rings are computed **locally in shapely**, in an appropriate equal-area/equidistant
projection chosen per property (`pyproj` UTM zone from the centroid), then converted back
to 4326. Nothing about ring construction needs Earth Engine, and doing it locally means
the ring geometry is available instantly for the map while EE work is still running.

Consequence for the whole codebase: **there is one geometry list**, and every analysis is
`analyse(zones, …) -> (DataFrame, Provenance)` with a `zone_key` column. The stacked-column
chart, the Sankey, the biomass series and the exports all group by the same key.

## 4. Data flow

```
user gesture                          Camposcope
────────────                          ──────────
paste cod_imovel ─┐
click on map ─────┼──▶ state/_imovel.py
pick município ───┘         │
                            ├─▶ services/sicar.py ── WFS ──▶ geoserver.car.gov.br
                            │        └─ GeoJSON property (4326) + cadastral attributes
                            │
                            ├─▶ state/_zones.py
                            │        └─▶ services/zones.py  (shapely: rings, areas, overlaps)
                            │             └─ zones pushed to the map immediately  ← C1
                            │
                            └─▶ state/_analysis.py   @rx.event(background=True)
                                     ├─▶ mapbiomas_history.py  ── ONE reduceRegions
                                     ├─▶ hansen.py             ── loss year, split at dat_criacao
                                     ├─▶ biomass.py            ── ten AGB snapshots
                                     └─▶ tiles.py fan-out      ── 40 years of tile URLs
                                            on services/ee_concurrency.py's pool
```

The SICAR half completes in ~1 s and paints the map. The EE half runs as a Reflex
**background event handler** so the cadastral record, the boundary and the rings are on
screen and interactive long before the charts arrive.

## 5. State model

```python
class AppState(ImovelMixin, ZonesMixin, LayersMixin, AnalysisMixin,
                TransitionsMixin, ExportMixin, UIMixin, rx.State):
```

| Mixin | Owns |
|---|---|
| `_imovel` | search mode + inputs, candidate list, selected `cod_imovel`, cadastral record, `dat_criacao` |
| `_zones` | ring radii, zone list (GeoJSON + areas), declared-vs-computed area delta, neighbour overlaps |
| `_layers` | visible layers, `active_year`, opacity, tile-URL registry, basemap, CAR WMS context layer |
| `_analysis` | history/hansen/biomass DataFrames (serialised), running flags, errors, provenance |
| `_transitions` | Sankey year selection (pair and multi-stage), transition dicts, figures |
| `_export` | which zones and analyses to export, download handlers |
| `_ui` | sidebar tab, language, legend state, toast queue |

**C2 is enforced here**: no mixin holds an `ee.*` object. `_zones` holds GeoJSON dicts;
services rebuild `ee.Geometry` on entry.

## 6. Analysis contract

Unchanged from Naturametrics, because it works: every analysis returns
`(DataFrame, Provenance)`, where `Provenance` carries `dataset_id`, `bands`, `scale_m`,
`reducer`, `geometry_geojson`, `pixel_area_basis` and `computed_at`. Export handlers refuse
to write without one (**C3**).

Camposcope adds two fields to the provenance block, because its object of analysis is a
cadastral record and not a coordinate:

- `sicar_queried_at` — when the boundary was fetched (the cadastre changes under us);
- `sicar_disclaimer` — the C4 statement, so it survives into every exported file.

## 7. Where Camposcope deliberately differs from its siblings

| | Yvynation / Naturametrics | Camposcope |
|---|---|---|
| Study area | Registry polygon / point buffers | **Fetched cadastral polygon + outward rings** |
| Boundary trust | Curated, trusted | **Self-declared, shown with its own metadata and caveats** |
| Time axis | Calendar years only | Calendar years **plus the property's own registration date** |
| Comparison | Territory vs. surroundings | Property vs. its rings, and declared vs. computed area |
| Failure mode to design for | EE quota | **A third-party public service being slow or down** |

That last row is why `services/sicar.py` has its own timeout, retry and cache policy
([05](05-sicar-geoserver.md) §6) and why the UI can show a cadastral record with the EE
panels still empty.
