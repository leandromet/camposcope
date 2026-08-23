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
| **O1** | Minimum year gap for a Sankey pair | *open* — 5 years proposed | 4 |
| **O2** | Deployment target | *open* | 7 |
| **O3** | Municipality list source | *open* | 1 |

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

**O3 — Municipality list.** The UF → município select needs a list. Options: derive it from
distinct `cod_municipio_ibge` in the layer (a query per UF over hundreds of thousands of
rows — bad); ship the IBGE municipality table locally (5 570 rows, ~200 kB, static, offline
— probably right); or query lazily and cache. Leaning local table, for the same reason as
D5.
