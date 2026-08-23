# 06 — Earth Engine: the reducer, the fan-out, the budget

Earth Engine is where Camposcope spends money and latency. Two patterns, both ported from
Naturametrics because they were measured there, keep it affordable.

## 1. The budget (constraint C6)

A property analysis must cost, per gesture:

| Work | Round trips |
|---|---|
| MapBiomas trajectory, 40 years × N zones | **1** |
| Transitions, one year pair × N zones | **1 per pair** |
| Hansen loss/gain × N zones | **1** |
| Biomass, 10 snapshots × N zones | **1** |
| Tile URLs (40 MapBiomas years + layers) | fan-out, parallel, off the critical path |

Anything that makes one of the first four grow with the number of years or zones is a bug,
not a slow path.

## 2. The batched reducer

MapBiomas Collection 10.1 is **one image with 40 bands**, not 40 images
([04](04-data-sources.md) §2). That is the whole trick:

```python
zones_fc = ee.FeatureCollection([ee.Feature(ee.Geometry(z.geojson), {"zone": z.key})
                                 for z in zones])

stats = (mapbiomas_image                    # all 40 classification_* bands
         .addBands(ee.Image.pixelArea())
         .reduceRegions(collection=zones_fc,
                        reducer=ee.Reducer.frequencyHistogram(),
                        scale=30,
                        tileScale=EE_TILE_SCALE)
         .getInfo())                         # ← the only round trip
```

One call returns, for every zone, a class-frequency histogram for every year. The
DataFrame is built locally. The naive version — loop over years, loop over zones, one
`reduceRegion` each — is 200 round trips for the same answer and is how EE budgets
disappear.

**Area accounting** uses `ee.Image.pixelArea()` rather than a pixel count times a nominal
30 m × 30 m (Naturametrics decision D3, carried over). Near the equator the difference is
small; across Brazil's latitude range it is not, and a property area that disagrees with
the cadastre because of a projection shortcut is exactly the kind of error Camposcope
cannot afford ([01](01-premises.md) §1).

## 3. Transitions

Same shape, different reducer. Yvynation's `compute_transitions` encodes a year pair into
one band before reducing:

```python
combined = img_start.multiply(1000).add(img_end)     # src*1000 + tgt
hist = combined.reduceRegion(ee.Reducer.frequencyHistogram(), geometry, scale=30)
# key "1503" → class 15 became class 3
```

One call per year pair per geometry. A multi-stage Sankey over *k* years is *k−1* pairs.
Details, including the `include_unchanged` semantics, in [07](07-transitions.md).

## 4. Tile-URL fan-out

Map tiles do not come from the reducer. `services/tiles.py` mints them:

```
image.getMapId(vis) → map_id["tile_fetcher"].url_format   # memoised on a stable key
```

Each `getMapId` is a cheap EE call, and 40 of them (one per MapBiomas year) run
**in parallel** on `services/ee_concurrency.py`'s sized thread pool while the foreground
reducer is still running. By the time the chart appears, every year the slider can reach is
already warm — which is what makes scrubbing the year control feel instant and satisfies
constraint C1's spirit as well as its letter.

`ee_concurrency.py` also carries a fix worth not losing: the default `httplib2`/`urllib3`
connection pool is smaller than the thread pool, so a wide fan-out silently serialises on
connections. Both are ported verbatim.

## 5. Authentication

`services/ee_client.py`, ported verbatim, tries three sources in order:

1. a service-account JSON in an env var (the deployment path),
2. Application Default Credentials (local — `earthengine authenticate`),
3. a service-account JSON file path.

If none work it **fails loudly at startup** rather than serving a map with no data. Keep
that behaviour; a silent EE failure looks exactly like a slow network.

**Project id matters.** Naturametrics binds to `ee-leandromet` because the Earth Engine
Partner-tier grant is attached to that project and a different one silently drops to
contributor limits (their D5, and the `project_yvynation_ee_tier` note). Camposcope shares
that constraint — the fan-out in §4 is sized to the uplift. `CS_GCP_PROJECT_ID` defaults to
`ee-leandromet`; changing it is a capacity decision, not a config tweak.

## 6. What Camposcope does *not* do in EE

- **No exports to Drive/GCS, no `ee.batch` tasks.** Everything is interactive `getInfo()`.
  If a query is too big for that, the answer is a smaller query, not a task queue.
- **No asset creation.** The property polygon goes to EE as inline GeoJSON, never as an
  uploaded table. This matters: a cadastral boundary fetched at request time and uploaded
  as an EE asset would immediately be a stale copy of official data.
- **No imagery statistics in v1.** S2/Landsat are context layers only
  ([04](04-data-sources.md) §5).

## 7. Sizing a property

Most CAR properties are small — the module-fiscal distribution is heavily skewed — and a
1 000 ha property at 30 m is ~11 000 pixels, trivial. The tail is not: MT has registrations
in the tens of thousands of hectares, and a 5 km ring around one of those is a large
geometry.

Guards, in the service layer:

- `maxPixels` set explicitly, and a failure reported as *"this property is too large for an
  interactive analysis"* rather than an EE stack trace;
- `tileScale` raised for large geometries (the ported `EE_TILE_SCALE` default of 4 is
  already conservative);
- ring radii reduced automatically, with a visible notice, when the ring geometry exceeds a
  threshold — a 5 km ring around a 100 000 ha property is a different question than a 5 km
  ring around a 50 ha one, and pretending otherwise produces a slow, meaningless answer.
