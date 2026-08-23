# 11 — Search and navigation

## 1. The short answer on addresses

**Yes — but an address is the weakest of the four ways to find a rural property, and the
plan treats it as the last resort rather than the headline feature.**

Rural Brazil largely does not have street addresses. A *fazenda* has a município, a road and
a kilometre marker, a name locals know, and often a gate on an unnamed estrada vicinal.
Typing "Rua X, 123" into a map of rural Mato Grosso finds nothing, and a geocoder that
confidently returns a point in the nearest town centre is worse than one that returns
nothing, because the user will click there and get somebody else's property.

So Camposcope ships **one search box that resolves four kinds of input**, in a fixed
precedence, with place-name geocoding at the bottom.

## 2. One box, four resolvers

The user types into a single field. The resolver tries, in order, and stops at the first
that matches:

| | Input | Resolver | Result |
|---|---|---|---|
| 1 | `MT-5108501-CBE0F5…` | `config/sicar.py::parse_cod_imovel` | **The property**, directly |
| 2 | Coordinates, any common format | `services/geocode.py::parse_coordinates` | A point → the `INTERSECTS` query ([05](05-sicar-geoserver.md) §5.2) |
| 3 | A município name | local IBGE table (§4) | The município framed; the property list opened |
| 4 | Anything else | a geocoding provider (§5) | A place, framed — **not** a property |

The precedence is not arbitrary. 1 and 2 are **exact** and cost no third-party call; 3 is
exact and local; only 4 is a guess against someone else's service. Trying them in that order
means the common cases never touch a geocoder at all.

**Results 3 and 4 move the map; they never select a property.** That distinction is
load-bearing: finding a *place* and identifying a *registration* are different acts, and
collapsing them would let a fuzzy address match become an implied claim about who holds
what. After a place is framed, the user still clicks to pick a property, which runs the
normal disambiguation ([05](05-sicar-geoserver.md) §5.2, decision D7).

## 3. Coordinates — the resolver that actually gets used

The gesture that matters in practice: someone has a coordinate from a GPS, a phone, a court
document or a WhatsApp message, and wants to see that place. `parse_coordinates` accepts:

```
-12.4979, -55.4977              decimal, comma
-12.4979 -55.4977               decimal, space
12°29'52.5"S 55°29'51.9"W       DMS with hemisphere letters
12 29 52.5 S, 55 29 51.9 W      DMS, plain
-12.4979,-55.4977 (Google Maps URL, /@lat,lon,zoom or ?q=lat,lon)
```

Rules, all of them learned the boring way:

- **Latitude first**, always — the input convention, unlike the CQL `POINT(lon lat)` the
  service layer builds ([05](05-sicar-geoserver.md) §5.2).
- Reject anything outside Brazil's bounding box, and say *which* value looks wrong. A
  swapped pair (`-55.5, -12.5`) lands in the South Atlantic, and "no property here" would be
  a terrible answer to a transposition.
- Accept `.` or `,` as the decimal separator when it is unambiguous — pt-BR keyboards
  produce commas, and `-12,4979 -55,4977` is a real thing users paste.

## 4. Municípios

Two representations, deliberately, because they answer different questions:

**A local IBGE table** (`data/municipios.csv`, 5 571 rows, ~200 kB committed) drives the
*list and the search*: the UF → município cascade, the type-ahead, and the code the WFS
filter needs (`cod_municipio_ibge`). It is instant, works offline, and costs nothing. This
settles open question **O3** ([10](10-open-decisions.md)) in favour of the local table:
querying distinct `cod_municipio_ibge` out of a 218 000-row UF layer to populate a dropdown
is exactly the kind of query constraint C5 exists to prevent.

**An Earth Engine município asset** provides the *geometry* — framing the map on a
município, clipping a layer to it, and any spatial operation that needs the boundary. This
is the asset being prepared under `ee-leandromet`; `config/datasets.py::IBGE_MUNICIPIOS`
holds its id and its field mapping, following the pattern of `IBGE_BIOME_DOMAIN`.

The split matters: a dropdown must not wait on an Earth Engine round trip, and a boundary
must not be approximated by a bounding box. Each representation does the thing it is good
at, and `cod_municipio_ibge` is the join between them.

## 5. Geocoding provider

**Chosen: Nominatim (OpenStreetMap), used sparingly, with the same courtesy posture as
SICAR** (decision **D11**).

Verified 2026-08-23: `nominatim.openstreetmap.org/search?q=Vera,+Mato+Grosso&format=jsonv2
&countrycodes=br` returns in ~1 s with a `boundingbox` — which is what the map needs, since
framing a bbox is honest about uncertainty in a way a single pin is not.

| Option | Why / why not |
|---|---|
| **Nominatim public** *(chosen)* | Free, no key, ODbL, good Brazilian coverage for places and municípios. **Its usage policy caps it at ~1 request/second and forbids bulk use** — acceptable for a human typing, unacceptable for anything automated |
| Photon (Komoot) | Also free, type-ahead friendly; kept as the documented fallback if Nominatim rate-limits us |
| Google Geocoding API | Best coverage, needs a key and a bill; revisit only if a deployment already has Maps Platform credentials ([04](04-data-sources.md) §7 raises the same question for basemaps) |
| Self-hosted Nominatim | The honest answer at any real scale; disproportionate for a research tool today |
| No geocoder at all | Considered seriously. Rejected: resolvers 1–3 cover the expert user, but "where is Sinop" is a reasonable thing to ask a map of Brazil |

The client rules mirror `services/sicar.py` ([05](05-sicar-geoserver.md) §7), for the same
reason — this is someone else's public service:

- an identifiable `User-Agent` naming Camposcope and its repository;
- **debounced**, and only on submit — never a request per keystroke;
- **one in flight at a time**, serialised;
- results cached by query string for the process lifetime;
- `countrycodes=br` always, so the search cannot wander off the map Camposcope covers;
- explicit timeouts, one retry, then an error naming the service;
- **never called for resolvers 1–3**, which is what keeps the volume low enough to be
  defensible.

The attribution — *"Busca de lugares © colaboradores do OpenStreetMap (ODbL)"* — appears
with the results, not only in an About page.

## 6. Biome and domain overlay — orientation, not analysis

A related navigation aid, carried over from Naturametrics: the **IBGE biomes, domains and
natural regions** layer (`projects/ee-leandromet/assets/ibge_biome_domain_250k`, 271
polygons, verified accessible 2026-08-23).

It is the one layer in the app that is a **browser-side vector rather than tiles**, and for
a specific reason: a tile is pixels and cannot answer *"what is under the cursor"*. The
biome layer has to name itself on hover, so the polygons themselves go to the browser —
simplified to 1.5 km and rounded to ~1.1 km, about 2.5 MB of JSON, 0.5 MB gzipped, served as
a cacheable HTTP GET rather than pushed through the WebSocket. Naturametrics' `api/` route,
`services/biomes.py` and the `vectors` machinery in `leaflet_map.js` all port directly; the
`vectors` prop is already present in the component this repo carries.

**The accuracy trade is inherited and must be restated here**: boundaries drawn from this
layer are approximate to roughly a kilometre. It is for orientation — *"I am in the Cerrado,
near the Amazônia transition"* — and it must never be used to decide which biome a specific
property falls in. A property's biome, if Camposcope ever needs one, is a separate
full-resolution question answered once and stored, exactly as Naturametrics did for its IFN
points.

Given that constraint, the biome layer is filed here under navigation rather than under data
sources: it helps people find where they are, and it is not an input to any number the app
reports.

## 7. What this adds to the UI

The search panel of [08-ui-ux.md](08-ui-ux.md) §2 gains a fourth mode — or rather, its three
modes collapse into **one box plus an explicit município browser**:

```
┌──────────────────────────────────────────┐
│ 🔍  código CAR, coordenada ou lugar…     │
└──────────────────────────────────────────┘
   ↳ resolved as: coordenada -12.4979, -55.4977
   ↳ 2 imóveis registrados neste ponto — escolha:
```

The box **says how it interpreted the input** before acting on it. That one line prevents
the failure this design is most exposed to: a coordinate silently read as a place name, or a
transposed pair quietly resolving somewhere plausible and wrong.

**Done test (Phase 1):** each of the four input kinds resolves to the right thing; a
transposed coordinate pair is refused with a message naming the problem; a place-name search
frames the map and selects **no** property; and no geocoder request is made for an input
that resolvers 1–3 could handle.
