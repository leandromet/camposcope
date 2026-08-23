# Camposcope

**Land-cover history and landscape context for a rural property registered in the CAR.**

Find a property — by its `cod_imovel`, by clicking the map, or by browsing a município —
and Camposcope pulls its official boundary from the Serviço Florestal Brasileiro's
GeoServer, builds neighbourhood rings around it, and runs the full land-use analysis stack
inside both: MapBiomas trajectory 1985–2024, land-cover transitions as Sankey diagrams,
Hansen forest loss split at the property's registration date, ESA CCI above-ground biomass,
Sentinel-2 / Landsat context imagery, and the SPOT 2008 mosaic — the imagery nearest the
Forest Code's own reference date of 22 July 2008.

Camposcope is a sibling of [Naturametrics](https://github.com/leandromet) and
[Yvynation](https://github.com/leandromet), not a fork of either. The three are defined by
**what kind of object they study**:

| App | Object of analysis | Boundary comes from |
|---|---|---|
| Yvynation | Protected and Indigenous territories | A curated registry |
| Naturametrics | An arbitrary place | A coordinate you click |
| **Camposcope** | **A rural property** | **The CAR — an official, self-declared cadastre** |

They share engineering — Earth Engine access, tile caching, the Reflex state structure, the
persistent Leaflet map — not a product.

---

## ⚠️ What the CAR is, and what it is not

The Cadastro Ambiental Rural is **auto-declaratório**. A registered polygon means someone
drew a boundary and filed it. It is **not** a survey, **not** a title, and **not** proof of
ownership, possession or environmental compliance. Registrations overlap routinely — the
first random point tested during development was covered by two.

Camposcope shows every cadastral field verbatim, surfaces overlaps instead of dissolving
them, and issues **no compliance verdict of any kind**. See
[`doc/01-premises.md`](doc/01-premises.md) §5.

---

## Status

| Phase | | |
|---|---|---|
| 0 | Skeleton, SICAR service, persistent map | ✅ working |
| 1 | Find a property → boundary + cadastral record | ✅ done |
| 2 | Zones: rings, areas, overlaps, biome overlay | ✅ done |
| 3 | MapBiomas trajectory | ✅ done |
| 4 | Transitions & Sankey | ✅ done |
| 5 | Hansen, biomass, satellite context, SPOT 2008 | 🚧 Hansen + biomass + SPOT done; satellite imagery layers planned |
| 6 | Export & provenance | planned |

Full plan in [`doc/03-roadmap.md`](doc/03-roadmap.md).

### Finding a property

One search box resolves four kinds of input, in order, stopping at the first match — a CAR
code, a coordinate (decimal, DMS or a Google Maps URL), a município, and only then a place
name. Rural properties largely do not have street addresses, so address search is the last
resort rather than the headline, and a place result **frames the map without selecting any
property**. See [`doc/11-search-and-navigation.md`](doc/11-search-and-navigation.md).

---

## Quick start

Requires **Python 3.12**, **Node ≥ 18**, and Earth Engine access to the `ee-leandromet`
project (needed from Phase 3 on; Phases 0–2 run without it).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

cp .env.example .env        # then edit

python scripts/fetch_uf_boundaries.py   # once — click → UF routing
python scripts/fetch_municipios.py      # once — the município selector

reflex run
```

Then open **http://localhost:3020**. Deep-link straight to a property:

```
http://localhost:3020/?car=MT-5108501-CBE0F5EDD27A4D7888E7392EA7D44793
```

The first `reflex run` compiles the frontend toolchain and takes a few minutes; later
starts take seconds.

### Earth Engine authentication

```bash
earthengine authenticate          # once
export CS_GCP_PROJECT_ID=ee-leandromet
```

The Partner-tier grant is attached to that project — a different one silently drops to
contributor limits.

---

## Tests

```bash
pytest              # default — no network, no Earth Engine
pytest -m live      # opt-in — hits the real CAR GeoServer
```

---

## Documentation

Everything is in [`doc/`](doc/README.md). Start with
[`doc/01-premises.md`](doc/01-premises.md) for scope and constraints, and
[`doc/05-sicar-geoserver.md`](doc/05-sicar-geoserver.md) for the CAR GeoServer — its layers,
schema, queries and limits, all verified against the live service.

---

## Data sources

CAR/SICAR (Serviço Florestal Brasileiro) · MapBiomas Collection 10.1 (CC BY-SA 4.0) ·
Hansen Global Forest Change, Hansen/UMD/Google/USGS/NASA (CC BY 4.0) · ESA CCI Biomass v6.0,
Santoro & Cartus 2025 (CC BY 4.0) · Copernicus Sentinel-2 · USGS Landsat ·
Google LLC, Brazil Forest Imagery Dataset 2008, from circa 2008 SPOT images ·
IBGE — biomes and domains 1:250,000, territorial meshes and localities ·
Place search © OpenStreetMap contributors (ODbL) · Processed on Google Earth Engine.

Full table with licences and caveats: [`doc/04-data-sources.md`](doc/04-data-sources.md).
