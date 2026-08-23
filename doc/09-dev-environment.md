# 09 — Development environment

## 1. Requirements

- **Python 3.12** in a project-local `.venv`
- **Node ≥ 18** (Reflex installs its own frontend toolchain on first run)
- **Earth Engine access** to the `ee-leandromet` project ([06](06-ee-layers.md) §5)
- Network access to `geoserver.car.gov.br`

## 2. Ports

This machine runs several Reflex and Next.js apps at once. Camposcope's ports are chosen to
collide with none of them:

| App | Frontend | Backend |
|---|---|---|
| Yvynation | 3000 | 8000 |
| terra_web | 3000 / 3003 / 3004 / 3005 | — |
| Naturametrics | 3010 | 8011 |
| **Camposcope** | **3020** | **8021** |

`rxconfig.py` reads `PORT` and `BACKEND_PORT` from the environment with those defaults —
the `PORT` indirection is what a container platform injects, and the backend must bind a
*different* port or the two fight for the same socket.

## 3. Setup

```bash
cd /server/camposcope

python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

cp .env.example .env        # then edit
earthengine authenticate    # once, if not already done

reflex run
```

Then **http://localhost:3020**. The first `reflex run` compiles the frontend toolchain and
takes minutes; later starts take seconds.

## 4. Configuration

All settings are environment variables with working defaults, prefix `CS_`:

| Variable | Default | Purpose |
|---|---|---|
| `CS_GCP_PROJECT_ID` | `ee-leandromet` | Earth Engine project. **The Partner-tier grant is attached to this one**; a different project silently drops to contributor limits and the tile fan-out will crawl |
| `CS_EE_SERVICE_ACCOUNT_JSON` | — | Service-account JSON (deployment path); ADC is used locally when unset |
| `CS_SICAR_BASE` | `https://geoserver.car.gov.br/geoserver/sicar/ows` | The CAR GeoServer ([05](05-sicar-geoserver.md) §1) |
| `CS_SICAR_TIMEOUT_READ` | `60` | Read timeout, seconds. Never unset — the default is *forever* and it hangs a background handler |
| `CS_SICAR_CACHE_TTL` | `3600` | Municipality-page cache, seconds. Code lookups are cached for the process lifetime |
| `CS_RING_RADII_M` | `500,1000,2000,5000` | Default neighbourhood rings |
| `CS_EE_SCALE_M` | `30` | Reducer scale for MapBiomas/Hansen |
| `CS_EE_TILE_SCALE` | `4` | EE `tileScale`; raise for very large properties |
| `CS_BASEMAP` | `google_hybrid` | See [04](04-data-sources.md) §7 for the licensing caveat |
| `PORT` / `BACKEND_PORT` | `3020` / `8021` | §2 |

## 5. Dependencies, and what is deliberately absent

Runtime: `reflex==0.8.27` (pinned to the same minor as its siblings so ported components
compile unchanged), `earthengine-api`, `google-auth`, `pandas`, `numpy`, `plotly`,
`shapely`, `pyproj`, `requests`, `pydantic`, `python-dotenv>=1.2.2`.

Absent on purpose:

- **`geopandas` / `fiona` / `gdal`** — shapely + pyproj cover ring construction and area
  computation, and the heavy stack would triple the image for nothing. Offline prep scripts
  under `scripts/` may use it; the app never imports it.
- **`OWSLib`** — the four WFS queries ([05](05-sicar-geoserver.md) §5) are four URLs. A
  capabilities-parsing library would add a dependency, a startup round trip, and an
  abstraction over an interface documented in this repo.
- **A spreadsheet library** — ODS is written by streaming XML into a ZIP, ported from
  Naturametrics, where `odfpy` was measured at 42 s for 60 000 rows against 3.9 s for
  600 000.

## 6. Tests

```bash
pytest                 # default suite — no network, no Earth Engine
pytest -m live         # opt-in: hits the real CAR GeoServer
```

Two that matter from day one:

- `tests/test_app_builds.py` — imports the app and compiles it. A Reflex event-handler
  signature mismatch is a **build-time error that kills the backend worker while the
  frontend keeps serving**, so the symptom is a grey map and a dead WebSocket, which looks
  nothing like a type error. Naturametrics lost hours to this.
- `tests/test_sicar_live.py` — the reprobe commands of [05](05-sicar-geoserver.md) §8, as an
  opt-in test. Kept out of the default suite so CI never depends on a third party's uptime,
  but runnable the moment something looks wrong.

## 7. Git

Repository: `https://github.com/leandromet/camposcope`. Working directory is the repo root
(unlike terra_web, where the git root is a subdirectory).

Commit messages in Portuguese, `feat:` / `fix:` / `doc:` style, matching the sibling
projects. Nothing is committed or pushed without being asked.

## 8. Repository layout notes

- `data/cache/` and `.web/`, `.states/`, `.venv/` are gitignored.
- `data/uf_boundaries.simplified.geojson` **is** committed — it is small, derived, and the
  app does not work without it ([05](05-sicar-geoserver.md) §5.3).
- `scripts/` is offline prep, never imported by the app.
- `doc/deepseek_geoserver.md` is scratch notes; [05](05-sicar-geoserver.md) is the canonical
  GeoServer reference.
