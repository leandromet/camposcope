# 10 — Decision record

Recorded on **2026-08-23**. A decision without its rationale is unreviewable later, so the
alternatives stay.

| | Decision | Chosen | Phase |
|---|---|---|---|
| D1 | Object of analysis | **Property + neighbourhood rings** | 1–2 |
| D2 | How to seed from Naturametrics | **Selective port into a fresh package** | 0 |
| D3 | Ring geometry | **Outward rings from the boundary**, computed locally | 2 |
| D4 | Which CAR themes | **Property polygons only** — nothing else is public | 1 |
| D5 | Click → UF routing | **Local IBGE boundary file** | 1 |
| D6 | Area accounting | **Compute geometrically, show alongside declared** | 2 |
| D7 | Overlapping registrations | **Show all, choose explicitly, never dissolve** | 1–2 |
| D8 | Sankey persistence | **`include_unchanged=True` for Sankey, `False` for matrices** | 4 |
| D9 | Compliance verdict | **Never** | — |
| D10 | SPOT 2008 | **Ship it — as imagery + its dates, never as a classification** | 5 |
| D11 | Geocoding provider | **Nominatim, sparingly; last of four resolvers** | 1 |
| D12 | Municípios | **Local IBGE table for the list, EE asset for the geometry** | 1 |
| D13 | Biome / domain overlay | **Port it, as navigation — not as an input** | 2 |
| **O1** | Minimum year gap for a Sankey pair | *open* — 5 years proposed | 4 |
| **O2** | Deployment target | *open* | 7 |
| ~~O3~~ | ~~Municipality list source~~ | **settled by D12** | — |

---

## D1 — Property + neighbourhood rings

**Chosen.** The property alone is not interpretable: 30 % pasture is unremarkable in a
region that is 80 % pasture and striking in one that is 5 %. Rings supply the control group,
which is Yvynation's external-ring idea applied to a cadastral parcel.

*Rejected:* property only (cheap, but every number needs a comparison the user has to
supply from memory); municipality-wide aggregation (a different product, and blocked on the
SICAR rate-limit story — [05](05-sicar-geoserver.md) §6; kept as Phase 7).

**Cost:** every EE call carries N+1 geometries instead of 1. The batched reducer
([06](06-ee-layers.md) §2) makes that a wider payload, not more round trips, which is why
this is affordable at all.

## D2 — Selective port into a fresh package

**Chosen.** Modules are brought over one at a time, stripped of Naturametrics-specific
assumptions, each docstring recording where it came from and what changed.

*Rejected:* copy the tree and prune. Faster to a running app by perhaps a day, and it
carries in `ifn.py`, `conglomerado.py`, `canada/`, `user_points.py`, `biomes.py` and
`vegetation_age.py` — thousands of lines no Camposcope screen calls, which then get
maintained, imported by accident, and eventually shape the design of things that should have
been written for a property.

Ported verbatim (no changes expected): `ee_client.py`, `ee_concurrency.py`, `tiles.py`,
`provenance.py`, `ods.py`, `components/map/leaflet_map.py` + its `.js`.
Ported and reshaped: `mapbiomas_history.py`, `biomass.py`, `layers.py`, `exports.py`,
`charts.py`, `layer_panel.py`, `layout.py`, `state/_layers.py`, `state/_ui.py`,
`state/_export.py`.
Ported from Yvynation: `compute_transitions`, `create_sankey_transitions`,
`create_multi_stage_sankey`.
Not ported: everything else.

## D3 — Outward rings from the boundary, computed locally

**Chosen.** `boundary.buffer(r)` minus `boundary.buffer(r_prev)`, in a per-property UTM
projection from the centroid, converted back to 4326.

*Rejected:* concentric discs around the centroid (Naturametrics' model). A 40 000 ha
property and a 12 ha one have nothing comparable about their centroids; "the first 500 m
outside the fence" means the same thing for both.

**Local, in shapely, not in EE** — so the rings are on the map immediately while the EE work
is still running, which is what makes the app feel responsive ([02](02-architecture.md) §4).

**Open sub-question:** what happens when rings around adjacent properties overlap, or when a
ring crosses into another registration? Currently: nothing, the ring is the ring. That is
defensible — the neighbourhood is the neighbourhood, whoever owns it — but it should be
revisited once real examples exist.

## D4 — Property polygons only

**Forced, not chosen.** APP, Reserva Legal, vegetação nativa, área consolidada and
hidrografia are **not published** on the public GeoServer; the only public route is the
per-municipality shapefile bundles behind a captcha ([05](05-sicar-geoserver.md) §2).

The alternative — estimating RL/APP ourselves from MapBiomas and a hydrography layer — is
technically easy and was **rejected for v1**: an estimate rendered next to `condicao` and
`m_fiscal` will be read as an official figure no matter what the caption says. Revisit in
Phase 7 with an explicit "estimativa Camposcope" treatment that is visually incapable of
being mistaken for cadastral data.

## D5 — Click → UF routing from a local boundary file

**Chosen.** A simplified IBGE UF GeoJSON in `data/`, point-in-polygon locally.

*Rejected:* capabilities bboxes (ambiguous near borders, and the published bboxes are
coarse); fanning out to candidate UF layers (wasteful against a public service — C5).

Near a state line the property query itself is the arbiter: if the chosen layer returns
nothing, the neighbouring UF is tried once. That single fallback is bounded and honest.

## D6 — Compute area geometrically, show alongside declared

**Chosen.** `area` in the CAR is **declared**. Camposcope computes the geometry's area in an
equal-area projection and shows both, with the delta when they differ materially.

*Rejected:* trusting `area` (it is the declarant's number); replacing it (it is the official
field, and it is what appears on the landholder's own documents). The disagreement is
information — it is one of the few things Camposcope can say that a CAR extract cannot.

**Open:** what counts as "materially"? Proposed: flag above 2 % or 5 ha, whichever is
larger. Needs a look at the real distribution.

## D7 — Show overlaps, choose explicitly, never dissolve

**Chosen.** A click returning several properties raises a chooser; overlaps with
neighbouring registrations are listed with their overlapping area.

*Rejected:* taking the largest, the smallest, or the most recent. All three are silent
editorial decisions about a legally contested situation, and the probe in
[05](05-sicar-geoserver.md) §5.2 found a two-property overlap on the *first random point
tried* — this is the normal state of the cadastre, not an edge case.

## D8 — Sankey persistence flag

**Chosen.** `include_unchanged=True` for every Sankey, `False` for transition matrices and
gains/losses tables. Yvynation already carries the flag; the failure mode of getting it
wrong is a diagram where land visibly disappears between columns
([07](07-transitions.md) §2).

## D9 — No compliance verdict, ever

**Chosen, and not revisitable within this product.** Camposcope does not compute
*regularidade ambiental*, does not score a property, and does not colour `condicao`. That
work exists in terra_web (`relatorio-car`, `avalia_imoveis_mt`) with a different legal
posture and a different audience. See [01](01-premises.md) §5.

---

## Open questions

**O1 — Minimum year gap for a Sankey pair.** Five years is proposed
([07](07-transitions.md) §5) to keep classification flicker out of the figure. The right
number probably depends on the class pair — pasture↔agriculture flickers far more than
forest↔urban — and a single global threshold may be too blunt. Decide with real examples.

**O2 — Deployment.** Naturametrics went to Cloud Run (2 vCPU / 4 GiB). Camposcope has an
extra consideration: a public deployment multiplies SICAR traffic by the user count, and C5
is a promise made to someone else's server. The rate-limit and caching design has to be
settled *before* the app is public, not after.

**O3 — Municipality list.** *Settled 2026-08-23 by D12: ship the IBGE table locally.*


---

## D10 — SPOT 2008: ship it, as imagery and its dates
**Chosen.** Both `GOOGLE/BRAZIL_FOREST_2008/V1/{VISUAL,ANALYTIC}` mosaics, ported from
Naturametrics, licence-gated on `CS_SPOT_ENABLED`, and always accompanied by the
per-property acquisition-date summary ([12](12-spot-2008.md) §3).

This dataset is not a basemap in this app. The Código Florestal's *área rural consolidada*
turns on **22 July 2008**, and this is the only 5–10 m imagery Camposcope has near that date
— which makes it the most useful layer here and the most dangerous.

*Rejected:* shipping the mosaic as a plain basemap with no date reporting. The mosaic is
*circa* 2008 and its `date` band varies per pixel; over the test property the imagery is
from 22 May and 11 June 2008, but that is a fact about that property, not about the dataset.
A SPOT screenshot without its dates is a picture implying a date it may not have.

*Also rejected, firmly:* computing an *área consolidada* figure. Showing what the land looked
like around the reference date is data. Classifying an area as consolidated is a legal
determination that depends on facts no imagery contains, and D9 forbids it. The line, with
the permitted and forbidden lists, is [12](12-spot-2008.md) §4.

## D11 — Geocoding: Nominatim, sparingly, last
**Chosen.** Verified working 2026-08-23 (~1 s, returns a `boundingbox`, good coverage of
Brazilian places). Same courtesy posture as the SICAR client: identifiable User-Agent,
debounced, submit-only, one in flight, cached, `countrycodes=br`, and **never called when a
code, coordinate or município name would have answered** ([11](11-search-and-navigation.md)
§5).

*Rejected:* Google Geocoding (needs a key and a bill — revisit only if a deployment already
carries Maps Platform credentials); self-hosted Nominatim (the honest answer at scale,
disproportionate now); **no geocoder at all** (considered seriously — resolvers 1–3 cover the
expert user, but "where is Sinop" is a fair thing to ask a map of Brazil). Photon is the
documented fallback if the public instance rate-limits us.

**The framing that matters more than the provider:** a geocode result **frames the map and
selects no property**. Rural Brazil largely has no street addresses, and letting a fuzzy
address match select a registration would turn a guess into an implied claim about who holds
what.

## D12 — Municípios: local table for the list, EE asset for the geometry
**Chosen**, and it settles **O3**.

`data/municipios.csv` (5 570 rows, ~200 kB, committed, from the IBGE localidades API) drives
the cascading selector and the type-ahead — instant, offline, free. The Earth Engine
município asset under `ee-leandromet` supplies boundary geometry for framing and clipping.
`cod_municipio_ibge` joins them.

*Rejected:* deriving the list from distinct `cod_municipio_ibge` in a CAR UF layer — a query
over hundreds of thousands of rows to populate a dropdown, which is exactly what C5 exists to
prevent. *Also rejected:* using the EE asset for the list too. A dropdown must not wait on an
Earth Engine round trip, and a boundary must not be approximated by a bounding box; each
representation does what it is good at.

## D13 — Biome / domain overlay: navigation, not input
**Chosen.** Ported from Naturametrics with its delivery mechanism intact: the only
browser-side vector layer in the app, because a tile is pixels and cannot answer "what is
under the cursor". Served as a cacheable HTTP GET rather than pushed through the WebSocket.

**The inherited constraint is restated rather than quietly dropped**: the delivered geometry
is simplified to ~1.5 km, so boundaries drawn from it are approximate to roughly a kilometre.
It orients the user — *"I am in the Cerrado, near the Amazônia transition"* — and it must
never decide which biome a property falls in. If Camposcope ever needs a property's biome, it
is a separate full-resolution question answered once and stored, exactly as Naturametrics did
for its IFN points.

That is why the layer is documented under [11 — search and navigation](11-search-and-navigation.md)
rather than under data sources: it helps people find where they are, and it is not an input
to any number the app reports.
