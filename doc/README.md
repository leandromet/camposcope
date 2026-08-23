# Camposcope — documentation

Land-cover history and landscape context **for a rural property registered in the CAR**.

Read in order; each document is self-contained but assumes the one before it.

| | Document | What it settles |
|---|---|---|
| 01 | [premises.md](01-premises.md) | Why a separate app, v1 scope, constraints, non-goals |
| 02 | [architecture.md](02-architecture.md) | Stack, package layout, state model, analysis contract |
| 03 | [roadmap.md](03-roadmap.md) | Phases 0–6, what "done" means for each |
| 04 | [data-sources.md](04-data-sources.md) | Every dataset, its licence, its resolution, its trap |
| 05 | [sicar-geoserver.md](05-sicar-geoserver.md) | The CAR GeoServer: layers, schema, queries, limits — **verified against the live service** |
| 06 | [ee-layers.md](06-ee-layers.md) | Earth Engine assets, the batched reducer, the tile fan-out |
| 07 | [transitions.md](07-transitions.md) | Land-cover transitions and the Sankey diagrams |
| 08 | [ui-ux.md](08-ui-ux.md) | Screen anatomy, the three gestures, the panels |
| 09 | [dev-environment.md](09-dev-environment.md) | Python, ports, env vars, how to run it |
| 10 | [open-decisions.md](10-open-decisions.md) | Decision record — what was chosen and what is still open |
| 11 | [search-and-navigation.md](11-search-and-navigation.md) | Finding a property: codes, coordinates, municípios, addresses; the biome overlay |
| 12 | [spot-2008.md](12-spot-2008.md) | The SPOT 2008 mosaic and the Forest Code's 22 July 2008 reference date |

Alongside them: `geoserver_car_getcap_wfs.xml` / `geoserver_car_getcap_wms.xml` — the raw
capabilities dumps that [05](05-sicar-geoserver.md) is derived from, and
`deepseek_geoserver.md` — scratch notes whose layer names are wrong; see
[05](05-sicar-geoserver.md) §9.

## The one-paragraph version

Camposcope takes a **CAR property** — found by its `cod_imovel`, by clicking the map, or
by picking it out of a municipality — pulls its official boundary from
`geoserver.car.gov.br` over WFS, and then runs, **inside that boundary and in a set of
neighbourhood rings around it**, the analysis stack Naturametrics already proved:
MapBiomas land-cover trajectory 1985–2024, Hansen forest loss, ESA CCI above-ground
biomass, Sentinel-2/Landsat context imagery, the SPOT 2008 mosaic at the Forest Code's own
reference date, and Yvynation's transition Sankey diagrams.
The output is a property dossier: what this land was, what it is, how it differs from its
surroundings, and how much of the change happened after the property was registered.
