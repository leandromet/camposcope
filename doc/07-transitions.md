# 07 — Transitions and Sankey diagrams

Ported from Yvynation, where this machinery already exists and works
(`utils/mapbiomas_analysis.py::compute_transitions`, `utils/visualization.py::
create_sankey_transitions` / `create_multi_stage_sankey`). This document records what is
carried over, what changes for a property, and the two ways the figure lies if you let it.

## 1. Why transitions matter more here than in either sibling

A stacked column chart answers *what was here each year*. It does not answer *what became
what* — and for a rural property that second question is the whole point. "Forest fell from
60 % to 20 %" and "forest fell to 20 % while pasture rose and then became soy" are different
stories about the same numbers, and only the transition view separates them.

Paired with `dat_criacao` ([01](01-premises.md) §1), it becomes the question Camposcope
exists to answer: **what changed on this land before it was registered, and what changed
after.**

## 2. The computation

```python
band_a = f"classification_{year_a}"
band_b = f"classification_{year_b}"
combined = img.select(band_a).multiply(1000).add(img.select(band_b))
hist = combined.reduceRegion(
    reducer=ee.Reducer.frequencyHistogram(), geometry=geom, scale=30, maxPixels=...
).getInfo()
```

A histogram key decodes as `src = key // 1000`, `tgt = key % 1000` — so `"15003"` means
class 15 (pastagem) became class 3 (formação florestal). Pixel counts are multiplied by the
mean pixel area to give hectares.

Result shape: `{src_class_id: {tgt_class_id: area_ha}}`.

**`include_unchanged`** — Yvynation's flag, and it is not cosmetic:

| | `False` (default) | `True` |
|---|---|---|
| Emits `src == tgt` self-transitions | no | yes |
| Column totals across years | **shrink** | **constant** |
| Right for | change matrices, gains/losses tables | **multi-stage Sankey** |

A multi-stage Sankey with `include_unchanged=False` shows the land evaporating between
columns, because persistence has no ribbon. Every Sankey in Camposcope passes `True`; the
transition matrix passes `False`. This is the single most common way to get the figure
wrong.

Entries where both source and target are class 0 (nodata) are dropped; a class 0 on **one**
side is kept, because it is a real edge effect and hiding it makes the totals not reconcile.

## 3. The two figures

### 3.1 Two-stage — year A → year B

One column per year, ribbons between them, official MapBiomas colours on the nodes and
translucent source colour on the ribbons. Default pair: **`1985 → 2024`**, the full series.

### 3.2 Multi-stage — a chosen set of years

*k* columns, *k−1* reducer calls. The default set is deliberate:

```
1985  ·  <dat_criacao year>  ·  2024
```

which reads left to right as **before · at registration · now** — three columns that frame
the property's history around its own cadastral event. The user can add or remove years.

Node vertical ordering is stabilised across columns so a class stays roughly at the same
height and the eye can follow it (Plotly's Sankey y-axis runs 0 at the top). Yvynation's
implementation already does this; port it rather than reinventing it.

## 4. Per zone

Every transition view is computed per zone ([02](02-architecture.md) §3), so the property's
flows sit next to its rings'. The comparison that matters is usually not the property's
absolute change but **the difference between the property and the land immediately outside
it** — a property that cleared while its surroundings did not reads very differently from
one that changed with its whole neighbourhood.

## 5. The two ways this figure lies

**Classification flicker.** A one-year "transition" between adjacent years is often noise in
a mixed pixel, not an event ([04](04-data-sources.md) §2). Camposcope therefore refuses to
build a Sankey for year pairs less than **five years** apart, and says why rather than
silently disabling the control.

**Ribbon width is area, not importance.** A 3 ha ribbon from forest to urban may matter more
than a 300 ha rotation between two crop classes, and the figure says the opposite. Mitigated
by keeping the transition **table** available alongside every Sankey, sortable by area and
downloadable — the figure is for seeing the shape, the table is for making a claim.

## 6. Reconciliation test

The Phase 4 done test ([03](03-roadmap.md)) is a real invariant worth keeping as a unit
test: for a given zone and year pair, the Sankey's per-class column totals must equal that
zone's stacked-column areas for those years, to within pixel rounding. The two numbers come
from different reducers (`frequencyHistogram` on a combined band vs. on each band), so
agreement is genuine evidence that both are right.
