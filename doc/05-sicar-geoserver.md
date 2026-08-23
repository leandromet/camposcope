# 05 — The CAR GeoServer

Everything in this document was **verified against the live service on 2026-08-23**. Where
a capability is stated, it was exercised; where a limit is stated, it was measured. Redo
the probes in [§8](#8-reprobing) before trusting any of it a year from now.

## 1. Endpoint

```
https://geoserver.car.gov.br/geoserver/sicar/ows      # WFS + WMS, workspace-scoped
https://geoserver.car.gov.br/geoserver/sicar/wms      # WMS alias
https://geoserver.car.gov.br/geoserver/sicar/wfs      # WFS alias
```

GeoServer behind nginx. **Anonymous, no key, no login.** HTTPS certificate chain is
incomplete for some clients — `curl` needed `-k` during probing, so the HTTP client must
be configured explicitly rather than left to hope (see §7).

> **The workspace path is mandatory.** The global endpoint
> `…/geoserver/ows?request=GetCapabilities` answers **200 with an empty layer list** — no
> layers, no workspaces, nothing. It looks like the service is broken; it is not. Only the
> workspace-scoped `…/geoserver/sicar/ows` enumerates anything. Every other workspace name
> tried (`car`, `publico`, `public`, `temas`) returns 404.

## 2. What is actually published — and what is not

**27 layers, all of the same kind:**

```
sicar:sicar_imoveis_ac   sicar:sicar_imoveis_al   sicar:sicar_imoveis_am
sicar:sicar_imoveis_ap   sicar:sicar_imoveis_ba   sicar:sicar_imoveis_ce
sicar:sicar_imoveis_df   sicar:sicar_imoveis_es   sicar:sicar_imoveis_go
sicar:sicar_imoveis_ma   sicar:sicar_imoveis_mg   sicar:sicar_imoveis_ms
sicar:sicar_imoveis_mt   sicar:sicar_imoveis_pa   sicar:sicar_imoveis_pb
sicar:sicar_imoveis_pe   sicar:sicar_imoveis_pi   sicar:sicar_imoveis_pr
sicar:sicar_imoveis_rj   sicar:sicar_imoveis_rn   sicar:sicar_imoveis_ro
sicar:sicar_imoveis_rr   sicar:sicar_imoveis_rs   sicar:sicar_imoveis_sc
sicar:sicar_imoveis_se   sicar:sicar_imoveis_sp   sicar:sicar_imoveis_to
```

One layer per UF, 26 states + DF. **That is the entire public surface.**

**There are no theme layers.** No APP, no Reserva Legal, no vegetação nativa, no área
consolidada, no hidrografia, no servidão administrativa. Those exist only in the
per-municipality shapefile bundles behind the captcha at `consultapublica.car.gov.br`.
This is the single most important fact in this document and it is the reason
[01-premises.md](01-premises.md) §4 rules RL/APP analysis out of v1.

**Layer selection is by UF, and the UF must be known before the query.** There is no
national layer. For a `cod_imovel` the UF is its first two characters
(`MT-5108501-CBE0…` → `MT`). For a map click there is no such shortcut — see §5.3.

## 3. Feature schema

`DescribeFeatureType` on any of the 27 layers returns the same shape:

| Attribute | Type | Nillable | Notes |
|---|---|---|---|
| `cod_imovel` | string | no | `UF-<IBGE municipality code>-<32 hex>`; the primary key |
| `status_imovel` | string | no | `AT` = ativo, and other codes; **show verbatim** (C4) |
| `dat_criacao` | dateTime | no | Registration date — **the before/after axis** ([01](01-premises.md) §1) |
| `data_atualizacao` | dateTime | **yes** | Frequently `null`; do not assume it is present |
| `area` | decimal | no | **Declared** area in hectares — compare against the geometry, never substitute |
| `condicao` | string | yes | Long free text, e.g. *"Analisado, aguardando regularização ambiental (Lei nº 12.651/2012)"* |
| `uf` | string | no | Redundant with the layer, useful in exports |
| `municipio` | string | no | Name |
| `cod_municipio_ibge` | int | no | 7-digit IBGE code — the fastest filter for the municipality browser |
| `m_fiscal` | decimal | no | Módulos fiscais; `area / MF_municipal`. Useful directly for size class |
| `tipo_imovel` | string | no | `IRU` (imóvel rural), and others |
| `geo_area_imovel` | MultiPolygon | yes | The geometry column — **this name, not `the_geom`**, in every spatial filter |

Native CRS is **EPSG:4674 (SIRGAS 2000)**. Not 4326. The two are close enough that a
mistake is invisible on a map and wrong in an area calculation — so reprojection is
explicit everywhere (§5.1).

## 4. Scale

Measured with `resultType=hits`:

| Query | `numberMatched` | Wall time |
|---|---|---|
| All of `sicar_imoveis_mt` | **218 105** | 2.1 s |
| One município (Vera, MT — `cod_municipio_ibge=5108501`) | 1 388 | < 1 s |

A UF layer is in the hundreds of thousands of polygons. **Never fetch a UF layer
unfiltered.** Every WFS call Camposcope makes carries either a `cod_imovel` equality, a
spatial predicate, or a municipality code — enforced in the service layer, not by
convention (§7).

## 5. The four queries Camposcope makes

All four are `GET` on `…/geoserver/sicar/ows`.

### 5.1 Property by code — the primary lookup

```
service=WFS  version=1.0.0  request=GetFeature
typeName=sicar:sicar_imoveis_mt
outputFormat=application/json
srsName=EPSG:4326
cql_filter=cod_imovel='MT-5108501-CBE0F5EDD27A4D7888E7392EA7D44793'
```

→ **~1 s**, GeoJSON `FeatureCollection`, one MultiPolygon, coordinates already in 4326
because `srsName` was passed. GeoServer reprojects server-side; this is the cheapest
correct way to get 4326 out and the only one used.

The response also carries `numberMatched` / `numberReturned`, which is how the service
distinguishes *not found* (0) from *found* (1) without a second call.

### 5.2 Property at a point — the map click

```
version=1.0.0  request=GetFeature
typeName=sicar:sicar_imoveis_mt
outputFormat=application/json  srsName=EPSG:4326  maxFeatures=25
cql_filter=INTERSECTS(geo_area_imovel, POINT(-55.5 -12.5))
```

→ **~1 s**. Note the axis order: `POINT(lon lat)`.

**This returns more than one feature routinely.** The probe above landed on a point covered
by two overlapping registrations (61 ha and 448 ha, both `AT`, same município). That is not
an error in the data, it is what a self-declared cadastre looks like — so the click handler
must present a chooser whenever `numberReturned > 1`, ordered by area, and must never
silently take the first. C4 again.

### 5.3 Which UF layer does a click belong to?

There is no national layer, so a click has to be routed to one of 27 layers before it can
be queried. Three options, in order of preference:

1. **Local point-in-polygon against IBGE UF boundaries**, shipped as a simplified GeoJSON
   in `data/`. No network call, deterministic, ~50 kB. **Chosen (D5).**
2. Try the layer for the UF whose bbox contains the point — cheap but ambiguous near
   borders, and the capabilities bboxes are coarse.
3. Fan out to all candidate UFs — wasteful against a public service, ruled out by C5.

### 5.4 Municipality browser

```
version=2.0.0  request=GetFeature
typeNames=sicar:sicar_imoveis_mt
outputFormat=application/json
count=50  startIndex=0
sortBy=area D
propertyName=cod_imovel,area,condicao,municipio
cql_filter=cod_municipio_ibge=5108501
```

WFS **2.0.0 is supported**, and with it the things the browser needs:

- `resultType=hits` → a count without a payload (used for the "1 388 properties" header);
- `count` + `startIndex` → real paging, plus a `next` URL in the response;
- `sortBy=area D` → server-side ordering;
- `propertyName=…` → **drops the geometry** (`"geometry": null` in the GeoJSON). This is
  the difference between a 50-row page costing kilobytes and costing megabytes. The
  browser list never requests geometry; the geometry arrives only when a row is selected,
  via §5.1.

### 5.5 WMS, for the boundary layer

```
…/geoserver/sicar/wms?service=WMS&version=1.1.1&request=GetMap
&layers=sicar:sicar_imoveis_mt&styles=&format=image/png&transparent=true
&srs=EPSG:3857&width=256&height=256&bbox={bbox}
```

→ **1.2 s cold for a 256×256 tile**, valid RGBA PNG, EPSG:3857. Leaflet can consume this
directly as an `L.tileLayer.wms`, which is exactly how the "all CAR properties" context
layer is drawn — no WFS involved, no polygon count problem.

`GetFeatureInfo` also works and returns `application/json`, but Camposcope does **not** use
it: it answers in 3857 with 3857 coordinates and a truncated attribute set, and §5.2 gives
a better answer for the same click. Recorded here so nobody rediscovers it and switches.

## 6. Rate limiting and caching (constraint C5)

This is a public service operated by the Serviço Florestal Brasileiro for everyone. The
posture is: **be a well-behaved client, visibly**.

- `User-Agent: Camposcope/<version> (+<repo url>)` on every request — identifiable, not
  anonymous.
- **One in-flight SICAR request at a time per session**, serialised through the service
  layer. There is no scenario in v1 where two are needed at once.
- **Cache by query, not by response**: a `cod_imovel` lookup is cached for the process
  lifetime (a CAR polygon does not change during a session); a municipality page is cached
  for an hour; WMS tiles are cached by the browser and by Leaflet, untouched by us.
- **No batch enumeration.** No crawling a UF layer, no building a local mirror. If
  Camposcope ever needs bulk CAR data, the correct route is the official downloads, not
  218 105 paged WFS calls.
- Failures are surfaced, never retried in a loop: one retry with backoff, then an error in
  the UI naming the service.

## 7. Client rules

The service module (`services/sicar.py`) is the only place in the codebase that knows this
endpoint exists, and it enforces:

1. **No unfiltered query can be constructed.** Every public function takes a discriminator
   (code, point, or municipality) — there is no "fetch layer" function to misuse.
2. **`srsName=EPSG:4326` on every WFS call.** Never reproject 4674→4326 locally; never
   assume they are the same.
3. **`geo_area_imovel` is the geometry column name**, referenced through one constant.
4. **Explicit TLS handling.** The chain issue is handled once, in one place, with the
   decision written down next to it — not with a scattered `verify=False`.
5. **Explicit timeouts** (connect 10 s, read 60 s) — the default of *forever* would hang a
   Reflex background handler with no way out.
6. **Areas are computed from the geometry**, in an equal-area projection, and reported
   alongside the declared `area` — never instead of it.

## 8. Reprobing

The probe commands that produced this document are worth keeping runnable:

```bash
BASE=https://geoserver.car.gov.br/geoserver/sicar/ows

# 1. layers still there?
curl -sk "$BASE?service=WFS&version=1.1.0&request=GetCapabilities" | grep -o '<Name>[^<]*</Name>'

# 2. schema unchanged?
curl -sk "$BASE?service=WFS&version=1.1.0&request=DescribeFeatureType&typeName=sicar:sicar_imoveis_mt"

# 3. still ~1 s for a code lookup?
time curl -sk -G "$BASE" -d service=WFS -d version=1.0.0 -d request=GetFeature \
  -d typeName=sicar:sicar_imoveis_mt -d outputFormat=application/json -d srsName=EPSG:4326 \
  --data-urlencode "cql_filter=cod_imovel='MT-5108501-CBE0F5EDD27A4D7888E7392EA7D44793'"

# 4. WFS 2.0 paging still supported?
curl -sk -G "$BASE" -d service=WFS -d version=2.0.0 -d request=GetFeature \
  -d typeNames=sicar:sicar_imoveis_mt -d resultType=hits \
  --data-urlencode "cql_filter=cod_municipio_ibge=5108501"
```

`tests/test_sicar_live.py` runs 1, 3 and 4 as an opt-in live test (`-m live`), kept out of
the default suite so CI never depends on a third party's uptime.

## 9. Correction: guessed layer names that do not exist

`doc/deepseek_geoserver.md` (scratch notes) proposes `sicar:imovel`, `car:imovel_geometria`,
`sicar:car_imovel_geo` as candidate layer names and `area_declarada` as an attribute. **None
of them exist.** The layers are `sicar:sicar_imoveis_<uf>`, one per UF, and the declared-area
attribute is `area`. The capabilities dumps committed next to it
(`geoserver_car_getcap_wfs.xml`, `geoserver_car_getcap_wms.xml`) are the evidence, and this
document is the canonical reference. The scratch file's *shape* — WMS for display, WFS for
analysis — is right and is what [02](02-architecture.md) implements; only its identifiers
are wrong.

Two further corrections from the same file, both worth stating because they would cost real
time:

- **`GetFeatureInfo` is not the click handler.** It answers in the map's CRS with a
  truncated attribute set and a `feature_count` that hides overlaps. §5.2's WFS
  `INTERSECTS` query is the click handler, and it returns *every* overlapping registration,
  which is the point (D7).
- **Do not push CAR features into Earth Engine as a `FeatureCollection` upload.** Camposcope
  analyses **one property at a time**, passing its geometry inline
  ([06](06-ee-layers.md) §6). Fetching 10 000 features for a UF and uploading them is both a
  violation of C5 and an instant stale copy of official data.
