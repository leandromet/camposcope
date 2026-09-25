# 13 — PDF report

> **The property dossier as a document.** Metadata and the disclosure first, then maps, charts
> and tables, each with a short paragraph describing what they show. It describes; it never
> issues a verdict.

Planned on **2026-09-24**. It is planned together with the same feature in Naturametrics
(`doc/14-pdf-report.md`, the **canonical copy** of the shared kit) and Yvynation
(`reflex_app/docs/PDF_REPORT.md`). The three reports share one layout, one kit and one set of
image rules (§2). The decision is recorded as **D14** in
[10-open-decisions.md](10-open-decisions.md).

---

## 1. Purpose and scope

The export dialog (`components/exports.py:59-152`, opened from the header) offers an ODS
workbook and a **"Relatório em HTML"**: `services/report.py::imovel_report_html`, ported from
Naturametrics, with Plotly inlined and print CSS. It falls short of this app's own rules:

- **The C4 disclosure is missing.** `DISCLOSURE_PT/EN` (`config/sicar.py:129-138`) is shown
  only under the cadastral card (`state/_imovel.py:73`). Neither `services/report.py` nor
  `services/exports.py` uses it, although [01](01-premises.md) §5 and
  [04](04-data-sources.md) §13 require it in **every export**.
- **Missing content:**
  - no maps;
  - no overlaps (D7);
  - no computed area or its difference from the declared area (D6);
  - no SPOT 2008 summary (D10);
  - no `queried_at` ([02](02-architecture.md) §6 wants `sicar_queried_at`);
  - no `tipo_imovel`, `m_fiscal` or `data_atualizacao`.
- **Portuguese bias.** It uses inline `lang == "pt"` switches, and the footer always prints the
  Portuguese `DATA_SOURCES` (`services/report.py:503`).

**This plan adds a PDF and rebuilds the HTML report on the same content model (R4).** Both gain
maps, explanatory paragraphs, an "about this report" list and the full C4 posture.

**Scope:** one report per **selected property and its rings** (`RING_RADII_M`, default
500 m / 2 km / 5 km, `config/settings.py:112`). The synthetic 500 ha square (`kind="square"`, no
`cod_imovel`) gets the same report, headed by `tr["square_disclosure"]` instead of the CAR
disclosure. Batch reports over many properties stay a non-goal ([01](01-premises.md) §4).

**Existing gaps this work fixes first** (they ship even if the PDF slipped):

1. Add the disclosure to the HTML report **and to the ODS `metadados` tab**
   (`services/exports.py::_metadata_sheet`, L72).
2. Use the sources list for the active language in every export footer.
3. Extend `_gather()` (`state/_export.py:112-142`) with `overlaps`, `area_calculada_ha`,
   `area_delta_ha`, `area_delta_pct`, `spot_summary` and a new `spot_provenance`.
   `run_spot_coverage` (`state/_analysis.py:431`) currently discards its `Provenance`, which
   breaks C3 for any export that shows SPOT.

**Status (2026-09-24): fixed, together with a fourth bug found while fixing them.**

- **Disclosure.** `config/sicar.py::disclosure_for(imovel, lang)` is now the one place that picks
  between the CAR disclosure and the square's own. It opens the HTML report (the `cs-disclosure`
  block, before any heading) and sits in the `AVISO` row of both ODS `metadados` tabs: the
  property workbook and the GBIF workbook. CSVs stay metadata-free by design.
- **Sources.** The HTML footer lists `DATA_SOURCES_EN` in English.
- **SPOT provenance.** `spot_provenance` is kept. `spot_summary` and `spot_provenance` flow
  through `_gather()` into both exports: a context line from `services/exports.spot_coverage_line`
  (dates and the share imaged before the cutoff, "unavailable" when unknown, never "0 %"), plus a
  provenance row.
- **New bug: results survived a change of property.** Every tab but Cobertura is computed on
  demand, and each cleared only its own fields when re-run. After choosing another property, the
  previous one's Hansen, biomass, fire, landscape, validation, Sankey, SPOT and GBIF results stayed
  in state. The ODS and HTML exported them under the new property's `cod_imovel`.
  `state/_imovel.py::PROPERTY_RESULT_DEFAULTS` and `_clear_property_results()` now reset them in
  both `_adopt` paths.
  `tests/test_property_switch.py` also fails if a field is added to `_gather()` without being
  cleared.
- **Remaining risk.** A background run started for the previous property that finishes *after*
  the switch can still write its result. Guarding every `run_*` handler with a property epoch is
  still open.
- The `_gather()` additions for overlaps and areas landed with the model rebase (see §11,
  status). `load_overlaps` was never wired to any gesture, so `overlaps` was always empty:
  `ZonesMixin` now carries `overlaps_checked`/`overlaps_error`, `build_zones` resets all
  three, and the report runs the lookup itself when it has not run, so "none found" is only
  ever printed after a real lookup.

---

## 2. The shared report kit (same text in all three apps)

> **This section is copied word for word** into Naturametrics `doc/14-pdf-report.md`,
> Camposcope `doc/13-pdf-report.md` and Yvynation `reflex_app/docs/PDF_REPORT.md`. Edit it in
> Naturametrics only, then copy it again. Everything outside §2 is specific to each app.

### 2.1 What the kit is, and why it is copied into each app

Naturametrics, Camposcope and Yvynation are three umaterra apps, and all three need the same
kind of document. That is a readable report with metadata first, then maps, charts and
tables, joined by short paragraphs. If each app built its own, they would drift apart within a
month. So the page model, the renderers, the map framing and the image rules live in one
package, **`report_kit`**, which knows nothing about any app.

| Copy | Path |
| --- | --- |
| **Canonical** | `/server/naturametrics/naturametrics/report_kit/` |
| Vendored | `/server/camposcope/camposcope/report_kit/` |
| Vendored | `/home/leandromb/google_eengine/yvynation/reflex_app/yvynation/report_kit/` |

`scripts/sync_report_kit.py` in Naturametrics copies the canonical tree into the other two
apps and rewrites `report_kit/MANIFEST`, which holds the sha256 of every file.
`tests/test_report_kit_manifest.py` in each app recomputes the hashes and fails on any
difference. **A fix made in a vendored copy would be lost at the next sync, so kit fixes go into
the canonical copy only.** This is the same copy-with-provenance pattern already used for
`ods.py`, `provenance.py` and `tiles.py`. A shared pip package was rejected: it would add a
private package source to three Cloud Build pipelines for about 1 500 lines of code.

**Rules for kit code:**

- Relative imports only.
- Never import the host app or `reflex`, and never import `ee` at module level. `ee` is
  imported lazily inside `maps.fetch_thumbnail`.
- Must run on **Python 3.11** (Yvynation's image). No nested same-quote f-strings and no
  `type X = …` aliases.
- Dependencies: `reportlab>=4.2,<5` and `pillow>=10`. pandas is imported lazily, only by
  `Table.from_frame`.

### 2.2 Decisions shared by the three apps (agreed 2026-09-24)

| # | Decision | Chosen | Rejected, and why |
| --- | --- | --- | --- |
| R1 | PDF engine | **reportlab**: a pure wheel with no system packages, and native tables that split across pages | Chromium printing: Naturametrics and Camposcope deliberately carry no Chromium. WeasyPrint: needs pango/cairo in the image and cannot run Plotly. matplotlib `PdfPages`: poor text layout |
| R2 | Chart images, Naturametrics and Camposcope | **Rendered by the browser**: `Plotly.toImage` of figure JSON sent by the server (§2.7) | kaleido + Chromium: about 300 MB of image, the most fragile part of Yvynation's deploy, and it reverses Naturametrics `doc/11-exports.md` §4. matplotlib re-draws: duplicate chart code, and the charts would no longer match the screen |
| R3 | Chart images, Yvynation | **Its existing server-side kaleido path** (`export_service._plotly_to_png_bytes`) | Browser capture: batch runs have no browser |
| R4 | HTML and PDF | **One content model, two renderers** (`render_pdf`, `render_html`), so the two formats cannot disagree | Two independent generators, as today, would drift |
| R5 | Map backdrop | **Earth Engine only**, via `getThumbURL`, using the same palettes as the screen | Google or Esri tiles: redistributing them inside a PDF is a terms-of-service problem |
| R6 | Explanatory text | **Deterministic templates for each language**, fed from the frames the charts already use | An LLM: not reproducible, and it could produce claims the data does not support |
| R7 | Sharing the code | **Vendored copies checked against a manifest** (§2.1) | A private pip package |
| R9 | Image resolution | **Screen quality, sized to the page: 150 dpi at the slot's size** (§2.5) | 300 dpi print: files 4× larger for a document read on screen |

(R8 is specific to Naturametrics' scope and is in its own doc.)

### 2.3 Content model: `report_kit/model.py`

Each app builds a `Report`, and the kit renders it. The model uses plain dataclasses and
contains no Reflex or Earth Engine objects.

```python
Slot = Literal["full", "half"]            # 170 mm or 82 mm wide (style.py)

@dataclass
class Brand:        accent: str; app_line: str        # e.g. "#2f7d4f", "umaterra · Camposcope"
@dataclass
class ReportMeta:   app: str; app_url: str; app_version: str; title: str; subject: str
                    lang: str                          # "pt" | "en" | "es" | "fr"
                    generated_at: datetime             # tz-aware UTC
                    brand: Brand
@dataclass
class Report:       meta: ReportMeta; sections: list[Section]
@dataclass
class Section:      title: str; blocks: list[Block]; key: str = ""   # key feeds ContentsList

# Blocks
Paragraph(text: str, lead: bool = False)             # **bold** / *italic* only; the kit escapes all else
KeyValues(rows: list[tuple[str, str]], caption: str = "")
Figure(key: str, caption: str, slot: Slot = "full", aspect: float = 0.56,
       fig_json: dict | None = None,                 # HTML: interactive Plotly
       png: bytes | None = None,                      # PDF: the rasterised chart
       unavailable_reason: str = "")                  # neither → a "figure unavailable" placeholder
MapFigure(composition: MapComposition, caption: str, slot: Slot = "full")
LocatorMap(geometry: dict, label: str, slot: Slot = "half")   # GeoJSON of the object
Table(columns: list[str], rows: list[list], caption: str,
      align: list[str] | None = None,                 # "l" / "r" per column
      max_rows: int = 40, note: str = "",             # overflow → "n more rows in the appendix/ODS"
      decimals: list[int | None] | None = None)       # numeric cells are locale-formatted by the kit
Table.from_frame(df, headers: dict[str, str], caption, **kw)
Callout(text: str, kind: Literal["disclosure", "note", "warning"] = "note", title: str = "")
ContentsList(items: list[ContentsItem])
ContentsItem(title: str, status: Literal["included", "not_run", "unavailable", "excluded"],
             reason: str = "")
ProvenanceTable(rows: list[dict])                     # each app's Provenance.to_dict()
Citation(text: str, sources: list[str], attributions: list[str])
SideBySide(left: Block, right: Block)                 # two half-slot blocks on one row
PageBreak()
```

Figures, maps and locators share one "Figure n" counter, and tables have their own. Captions
are prefixed by the kit ("Figura 3 —", "Table 2 —"). `ProvenanceTable` shows `name`,
`dataset_id`, `bands`, `scale_m`, `reducer`, `degraded` and `computed_at`, with `notes`
underneath. A degraded row is always shown, never hidden.

### 2.4 The same outline in every report

1. **Title block.** App line, report title, subject, the time it was generated (UTC and local
   time of the requested language), app version and URL.
2. *(Camposcope only)* **Disclosure callout.**
3. **Identification.** `KeyValues` of the object's metadata, `SideBySide` with the `LocatorMap`.
4. **About this report.** A `ContentsList`: every section the app can produce, marked included,
   not run, unavailable or excluded (by a checkbox), with the reason. Then one paragraph giving
   the period, the zones or buffers, and how to read the document: *data, not a verdict*.
5. **Maps.**
6. **Analysis sections**, one per dataset, in each app's on-screen order. Each has a one-sentence
   intro (what the dataset is), the figure, a summary table, and a *reading* paragraph built
   from the numbers.
7. **Methods and provenance.** `ProvenanceTable`.
8. **Sources, citation and attributions.** In the report's language, including "Contains
   modified Copernicus Sentinel data {year}" and "Landsat: USGS/NASA" whenever those backdrops
   appear.
9. **Appendix** (optional). Full tables. Always off in batch runs.

**Page, `style.py`.**

- A4 portrait, margins 20 mm on both sides and 18 mm at top and bottom, text width **170 mm**.
- Noto Sans (OFL, in `report_kit/fonts/`): body 9.5 pt on 13.5 pt leading, H1 16 pt, H2 12.5 pt,
  captions 8.5 pt.
- The header band on pages 2 onwards carries the app line in the accent colour, with the subject
  on the right.
- Footer: `umaterra · <App> · <url> — página x de y — gerado em <date>`, in the report's
  language.
- Tables: `LongTable(repeatRows=1)`, zebra rows, numbers right-aligned and formatted for the
  locale.

Noto Sans covers Guarani and Portuguese diacritics (ỹ, g̃). reportlab does no text shaping, so
combining marks can sit slightly off. This is accepted.

The system Noto Sans has **no − (U+2212), →, ≥, ≤ or ↳**, and reportlab drops a missing glyph
silently: "−3,2" printed as "3,2". Since kit v0.1.1, `fonts/NotoSansMath-Subset.ttf` (35 KB,
arrows, math operators and the true minus) is registered as a fallback. `pdf._glyph_fallback`
wraps any character the main font lacks in that font, and canvas strings (header, footer, scale
bar) get ASCII stand-ins. Apps may use these characters freely.

### 2.5 Images: screen quality, sized to the page (R9)

The reports are read on screens. Every raster is produced **for the slot it fills, at 150 dpi**,
never at print resolution and never larger than its slot.

| Slot | Width | Pixels at 150 dpi | Chart layout in CSS px (96 dpi) | Plotly/kaleido `scale` |
| --- | --- | --- | --- | --- |
| `full` | 170 mm | ≈ 1004 | 643 × (643·aspect) | 150/96 = **1.5625** |
| `half` | 82 mm | ≈ 484 | 310 × (310·aspect) | 1.5625 |
| full map | 170 × 110 mm | ≈ 1004 × 650 | — | — |

- **Charts are laid out at their true on-page CSS size and rasterised at `scale = 150/96`.**
  Plotly's pixel font sizes then print at about their nominal point size next to the 9.5 pt body
  text. A chart laid out 1000 px wide and shrunk to 170 mm would print its 12 px labels at about
  6 pt.
- `images.chart_opts(slot, aspect) -> {"width", "height", "scale"}` gives the numbers above to
  both chart paths (browser and kaleido).
- `images.prepare_figure(fig_json, slot, aspect) -> dict` works on a copy of the figure dict and
  needs no plotly import. It:
  - sets width and height;
  - sets a white paper and plot background (on-screen charts are transparent);
  - raises fonts to at least 10 px;
  - moves legends with more than six entries below the plot;
  - removes `updatemenus` and `sliders`.
- `images.fit_image(data, slot_mm, kind)`:
  - reads the PNG IHDR or JPEG SOF header **before** decoding, and refuses anything over 40 MP;
  - downsamples to the slot's size at 150 dpi;
  - re-encodes imagery (`kind="photo"`) as **JPEG q≈80**, and class rasters and charts
    (`kind="flat"`) as **PNG**, palette-quantised when there are 256 colours or fewer.
  - Both renderers call it, so an oversized input can never inflate the file.
- **Budget:** a synthetic report with 8 figures and 4 maps must stay **at or under 3 MB**, and a
  kit test asserts it.

### 2.6 Maps: `report_kit/maps.py` and `locator.py`

- **`MapView.from_geojson(geoms, slot, margin=0.08)`.** Computes the bounding box in EPSG:3857,
  padded and stretched to the slot's aspect ratio, so the fetched raster fills the frame exactly.
  It exposes `bbox_lonlat`, `bbox_3857`, `px` and `metres_per_px`.
- **`fetch_thumbnail(image, view, fmt, *, cache_key)`** is the kit's **only network call**. It
  calls `image.getThumbURL({"region": ee.Geometry.Rectangle(view.bbox_lonlat, None, False),
  "dimensions": f"{view.px_w}x{view.px_h}", "crs": "EPSG:3857", "format": fmt})` and makes an
  HTTP GET (`urllib`, 60 s timeout). Both dimensions are passed, so the raster is exactly the
  view's size. Results are cached in the process by `(cache_key, bbox rounded to 1e-5, px, fmt)`.
  - The caller must have initialised Earth Engine (its own `get_ee()`).
  - The caller must run it in an executor, never on the event loop.
  - In Yvynation it runs **before** entering a render lane.
- **`imagery_backdrop(view, year) -> ee.Image | None`** picks the backdrop by map extent:

| Longest side of the view | Backdrop | Visualisation |
| --- | --- | --- |
| ≤ 50 km (property, rings, buffers) | `COPERNICUS/S2_SR_HARMONIZED` masked with `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED` `cs ≥ 0.60`, median of the dry season (Jun–Sep) of `year`, falling back to the full year | B4/B3/B2, 0–3000, JPEG |
| 50–300 km (territories) | `LANDSAT/COMPOSITES/C02/T1_L2_ANNUAL`, image for `year` | red/green/blue, 0–0.3, gamma 1.2, JPEG |
| > 300 km | none: class layers and the locator only | — |

- **Class layers** (MapBiomas, Hansen, change masks and so on) are **provided by the app** as an
  already-visualised `ee.Image`, built by the *same* `<layer>_image()` function its tile layer
  uses (see §6 of each app doc). The PDF and the screen then share their pixels and palettes.
  They are fetched as PNG with transparency.
- **`MapComposition`** contains:
  - `view`;
  - `backdrop` (JPEG bytes or `None`);
  - `overlays` (PNG bytes, bottom to top);
  - `vectors`: `VectorLayer(geojson, stroke, width_pt, dash=None, fill=None, label="")`;
  - `clip_to` (GeoJSON that masks the overlays to the object's shape, or `None`);
  - `legend`: `LegendItem(color, label, kind="fill"|"line")`;
  - `attribution`.

  **Outlines and rings are drawn as vectors by the renderer, not painted in Earth Engine.** They
  stay sharp at any zoom, no geometry is sent to Earth Engine, and the thumbnail cache works per
  bounding box.
- **Frame furniture**, drawn by both renderers:
  - a thin frame;
  - a scale bar with a round length of about ⅕ of the width, corrected by cos(latitude);
  - a north arrow;
  - the legend **below** the map, never on top of it;
  - the attribution in 7 pt.

  The PDF renderer uses a reportlab `Drawing`. The HTML renderer uses the `<img>` layers plus
  inline SVG.
- **`LocatorMap`.** Draws Brazil's states from the kit's `data/br_uf.simplified.geojson`
  (copied from Camposcope `data/uf_boundaries.simplified.geojson`, 99 KB) as vectors. It
  highlights the object's state or states and marks the object (a point, or its bounding box
  when larger than 2 % of the map).

### 2.7 Chart capture in the browser (Naturametrics and Camposcope)

The kit provides the JavaScript and the job store. Each app writes the three handlers. The
flow was verified against Reflex 0.8.27: `state.js` L354–379 awaits a Promise returned by
`call_script`, and `reflex/utils/format.py:588` `format_queue_events` builds callbacks.

```text
[PDF button] ─► start_report("pdf")                 (normal, non-background handler: snapshot + job)
                 ├─ figs = {key: prepare_figure(fig_json, slot, aspect)}   ← same charts.* builders as the screen
                 ├─ job = JobStore.create(client_token, expected=figs.keys())
                 └─ return [rx.call_script(build_capture_script(figs, callbacks, opts)),   # no callback
                            State.build_report(job.id, "pdf")]                          # background
browser:  await window.Plotly (≤ 8 s) → for each key: try { d = await Plotly.toImage(fig, opts) }
          catch { d = "" }; if d.length > 900 000 retry at scale 1; cb[key](d)   ← one socket event per chart
          ─► receive_report_chart(job_id, key, data)  → JobStore.put(...)   (validates, stores bytes)
build_report(job_id, fmt)  [background]
   ├─ starts the EE thumbnails in an executor immediately (they overlap the browser's rendering)
   ├─ polls JobStore every 250 ms until every key is resolved or 15 s + 2 s × n_figures elapse
   ├─ a missing or failed key → Figure(png=None, unavailable_reason=…)   (never hangs)
   └─ builds the Report → render_pdf → rx.download(data=…, filename=…, mime_type="application/pdf")
```

- **Callbacks** are created in the app, because the kit cannot import Reflex. For each key:
  `str(format_queue_events(State.receive_report_chart(job_id, key), args_spec=lambda d: [d]))`.
  They are passed to `build_capture_script(figs, callbacks, opts)` as a `{key: js_source}`
  mapping.
- **One script, not N `call_script`s.** Each `call_script` holds the page's event queue while its
  Promise is pending, and a rejected Promise never fires its callback. One script with
  per-chart callbacks avoids both problems.
- **`JobStore`** (`browser_capture.STORE`) is a module-level dict with a lock and a 10-minute
  TTL, pruned on every access. Its API is `create(token, keys) -> job_id`,
  `put(job_id, key, data_url, token) -> bool`, `progress(job_id) -> (got, expected)`, `done()`,
  and `take(job_id) -> ({key: png | None}, {key: error})`. `wait_deadline_s(n)` gives the build
  task's timeout.
  It holds images outside Reflex state, because even `_backend` vars are pickled on every event.
  `put()` rejects:
  - a client token that differs from the job's;
  - data without the `data:image/png;base64,` prefix;
  - anything over 3 MB decoded;
  - a PNG whose IHDR exceeds 4000 × 4000.

  An empty string means the browser failed, and is recorded as such.
- **Incoming socket limit.** Reflex caps incoming messages at `REFLEX_SOCKET_MAX_HTTP_BUFFER_SIZE`
  (default 1 000 000 bytes). Beyond it, engine.io drops the connection *silently*. R9-sized charts
  are 50–200 KB, and the Dockerfile sets `REFLEX_SOCKET_MAX_HTTP_BUFFER_SIZE=4000000` as headroom.
- **`window.Plotly`** exists only after the first `rx.plotly` has mounted, because its bundle loads
  lazily. The report block mounts a hidden 1×1 `rx.plotly` so that the bundle is present, and the
  8 s wait plus the placeholder cover everything else.
- **The HTML format needs no capture.** It embeds `fig_json` directly, so `start_report("html")`
  goes straight to `build_report`.
- **Background-handler rules still apply:** no `type(self)` in background tasks, and every state
  write inside `async with self`. Wrap the snapshot in the app's `plain()`.

### 2.8 Explanatory text

- Each app has `services/report_text.py`: pure functions `(frames…, lang) -> str` returning
  one to three sentences. They are held as one template dict per language, with the app's
  reference language as fallback. `report_kit/text.py` formats numbers, areas, percentages
  and dates for pt, en, es and fr. The kit's own fixed strings are in those four languages too.
- **Describe, never judge.**
  - The sentences state quantities, changes over the period, and comparisons with the rings or
    the buffer.
  - No causal claims ("because of…").
  - No legal, compliance or valuation vocabulary.
  - Camposcope enforces this with a test (its doc, §9). The other two follow it by review.
- Every number in a sentence comes from the same frame the chart or table in that section was
  drawn from. **Nothing is recomputed at export.**

### 2.9 The export UI block: same anatomy in the three apps

```text
┌ Relatório  ·  Report ───────────────────────────────────────────┐
│ A laid-out document: identification, maps, charts and tables    │
│ with short explanations. Language = the interface's.            │
│ [✓] Mapas   [✓] Gráficos   [✓] Tabelas-resumo   [ ] Apêndice    │
│ [ ] GBIF  (where the app has it)                                │
│ ( PDF )  primary          ( HTML )  secondary                   │
│ Gráficos 3/7 · Mapas 2/3 · Montando PDF…      ← stage line      │
│ ⓘ reason when disabled (no result yet / wrong mode / running)   │
└──────────────────────────────────────────────────────────────────┘
```

**Common names:**

- State vars: `exp_report_maps`, `exp_report_figures`, `exp_report_tables`,
  `exp_report_appendix` (Naturametrics and Camposcope already have the figures and tables
  ones), plus `report_busy`, `report_stage` and `report_error`.
- Handlers: `toggle_exp_report_*` and `start_report(fmt: str)`, where `fmt` is a string because
  of the Reflex arg-type rule.
- Translation keys use the prefix `report_`.

**File names:**

- `<app>_<object-slug>_<YYYYMMDD-HHMM>.pdf` (or `.html`), for example
  `camposcope_MT-5108501-CBE0F5_20260924-1530.pdf`.
- Batch runs: `territory/{slug}/{slug}_report.pdf`.

### 2.10 Kit tests (canonical, run through each vendored copy)

**Status (2026-09-24): kit v0.1.0 is built** in the canonical location. The tests below pass
(`tests/test_report_kit.py`, 23 tests, plus `tests/test_report_kit_manifest.py`), and a report
also renders under a real CPython 3.11.15. A synthetic 7-page report with every block type,
6 charts, a 4000 px backdrop and a 120-row table is 0.37 MB and renders in 0.4 s.
`scripts/sync_report_kit.py --check` verifies all copies. Both repositories' `.gitignore`
ignored any file named `MANIFEST`; `!**/report_kit/MANIFEST` now overrides that.

- A synthetic `Report` using **every block type** produces bytes starting with `%PDF` and one
  self-contained HTML file with no external URLs.
- A 4000 px input image is embedded at the slot's pixel size or smaller, and a JPEG backdrop
  stays JPEG.
- 8 figures + 4 maps + 3 tables produce a file of **3 MB or less**.
- A 120-row `Table` spans pages and repeats its header row.
- `fmt_num(1234.5)` gives `1.234,5` in pt, es and fr style and `1,234.5` in en. The kit strings
  exist in all four languages.
- `Figure(png=None)` renders the placeholder and does not raise.
- `JobStore` rejects wrong tokens, prefixes and sizes, and an oversized IHDR; a job times out
  into "unavailable" entries.
- `MapView` aspect and scale-bar arithmetic are checked at the equator and at 30°S.
- The suite runs under Python 3.12 (Naturametrics, Camposcope) **and 3.11** (the Yvynation
  venv).

---

## 3. Report outline (Camposcope)

This fills in the common outline of §2.4. Every section except Cobertura is computed only when
the user presses *Calcular* on its tab (`state/_export.py:93`). The `ContentsList` is therefore
often "not run", and it says so plainly rather than leaving gaps.

| # | Section | Blocks |
| --- | --- | --- |
| 0 | **Disclosure** | `Callout(kind="disclosure")` holding `DISCLOSURE_PT`/`_EN`, or `tr["square_disclosure"]`. **On page 1, above everything else** |
| 1 | Identification | `KeyValues`: `cod_imovel`, UF, município (IBGE code), `tipo_imovel`, **`status_imovel` and `condicao` verbatim** (untranslated, uncoloured), `dat_criacao`, `data_atualizacao`, `m_fiscal`, declared area, computed area, difference (ha and %; D6: "the disagreement is information"), "cadastro lido em" `queried_at`. `SideBySide` with the `LocatorMap` |
| 1b | Zones | `Table` of zones: label, kind, `radius_m`, `area_ha` |
| 1c | Overlaps | `Table` of `overlaps` (`cod_imovel`, `overlap_ha`, `overlap_pct_do_imovel`), or the sentence "no overlapping registration was found". **Listed, never dissolved or ranked** (D7) |
| 2 | About this report | `ContentsList`: Cobertura, Transições, Floresta, Biomassa, Paisagem, Fogo, Validação, SPOT 2008, GBIF, each with its status and reason |
| 3 | Maps | See §6 |
| 4 | Cobertura | `land_cover_history_figure` (active zone) + the zone table (`history_table_rows`) + reading paragraph |
| 5 | Transições | `sankey_figure` (`sankey_zone_label`, `sankey_year_a` → `_b`) + top-10 transitions table |
| 6 | Floresta | `hansen_figure` + three-period table (up to 2008 / 2008→registration / after registration, `services/hansen.py` `PERIOD_*`), plus the Hansen gain note: undated, 2000–2012 only |
| 7 | Biomassa | `biomass_figure` + table |
| 8 | Paisagem | `landscape_meff_figure` + connectivity table |
| 9 | Fogo | `fire_figure` + `fire_rows` table |
| 10 | Validação | `validacao_matrix` as a table (IBGE × MapBiomas, `validacao_zone_label`) |
| 11 | SPOT 2008 | Coverage sentence from `spot_summary`: `covered_pct`, `date_min`–`date_max`, `pre_cutoff_pct` against the 2008-07-22 cutoff ([12](12-spot-2008.md) §4) |
| 12 | GBIF *(optional)* | `gbif_zone_rows`, pydantic objects converted with `.model_dump()` |
| 13 | Methods and provenance | `ProvenanceTable`, SPOT included once fixed (§1) |
| 14 | Sources and citation | `CITATION_TEXT` plus the **full attribution block of [04](04-data-sources.md) §13**, in the report's language |
| 15 | Appendix *(optional)* | Full land-cover and fire tables per zone |

The multi-stage Sankey (`multi_stage_figure`, `state/_transitions.py:248`) is **not** included:
no component renders it and it has no provenance (`_transitions.py:36-44`). Nothing appears in
the report that does not appear on screen.

### 3a. Explanatory text: examples (`services/report_text.py`, pt reference, en fallback to pt)

| Section | pt | en |
| --- | --- | --- |
| Area | "A área declarada é 1.052,3 ha; a área calculada a partir do polígono é 1.049,8 ha (−0,2 %)." | "The declared area is 1,052.3 ha; the area computed from the polygon is 1,049.8 ha (−0.2%)." |
| Overlaps | "O polígono deste registro se sobrepõe a 2 outros registros do CAR (Tabela 2). As sobreposições são listadas como constam no cadastro, sem interpretação." | "This registration's polygon overlaps 2 other CAR registrations (Table 2). Overlaps are listed as they appear in the cadastre, without interpretation." |
| Cobertura | "No imóvel, a pastagem ocupava 612 ha (58 %) em 1985; em 2024 a soja ocupa 701 ha (66 %). No anel de 5 km, a formação florestal passou de 41 % para 23 % no mesmo período." | "Within the property, pasture covered 612 ha (58%) in 1985; in 2024 soybean covers 701 ha (66%). In the 5 km ring, forest formation went from 41% to 23% over the same period." |
| Floresta | "O Hansen registra 212 ha de perda de cobertura arbórea no imóvel entre 2001 e 2024: 190 ha até 2008, 22 ha entre 2008 e o registro no CAR (2014) e nenhuma após o registro." | "Hansen records 212 ha of tree-cover loss within the property between 2001 and 2024: 190 ha up to 2008, 22 ha between 2008 and the CAR registration (2014), and none after registration." |
| SPOT 2008 | "O mosaico SPOT cobre 100 % do imóvel; 100 % dessa área foi imageada antes de 22/07/2008 (imagens de 14/05/2008 a 03/07/2008)." | "The SPOT mosaic covers 100% of the property; 100% of that area was imaged before 2008-07-22 (images from 2008-05-14 to 2008-07-03)." |

---

## 4. Where each block comes from

| Block | Source in the code |
| --- | --- |
| Disclosure | `config/sicar.py:129-138` `DISCLOSURE_PT` / `DISCLOSURE_EN`; `translations/pt.py:81` `square_disclosure` |
| Identification | `imovel` dict (`state/_imovel.py:325-341`, from `services/sicar.py:176-212`); `queried_at` inside it |
| Areas | `area_declarada_ha`, `area_calculada_ha`, `area_delta_ha`, `area_delta_pct` (`state/_zones.py:34-38`) |
| Zones / overlaps | `zones` (`_zones.py:31`), `zones_geojson` (32, vectors for the maps), `overlaps` (42) |
| Cobertura | `history_rows` (`state/_analysis.py:37`), `history_table_rows` (68) → `charts.land_cover_history_figure` (`components/charts.py:40`) |
| Transições | `sankey_transitions`, `sankey_zone_label`, `sankey_year_a/b` (`state/_transitions.py:36-49`) → `services/transitions.sankey_figure` (L169) |
| Floresta | `hansen_loss_rows`, `hansen_gain_ha`, period totals (`_analysis.py:228-255`) → `charts.hansen_figure` (L207) |
| Biomassa | `biomass_rows` (`_analysis.py:344`) → `charts.biomass_figure` (L253) |
| Paisagem | `landscape_rows`, `connectivity_rows` (`state/_landscape.py:38,49`) → `charts.landscape_meff_figure` (L324) |
| Fogo | `fire_rows`, `fire_annual_rows` (`_analysis.py:663,667`) → `charts.fire_figure` (L285) |
| Validação | `validacao_matrix`, `validacao_zone_label` (`_analysis.py:494-503`) |
| SPOT | `spot_summary` (`_analysis.py:428`; keys in `services/spot.py:63-75`) + the new `spot_provenance` |
| GBIF | `gbif_zone_rows` (`state/_gbif.py:68`) |
| Provenance | every `*_provenance` dict in `_gather()` |
| Citation | `config/citation.py`: `CITATION_TEXT` (L30), `DATA_SOURCES` (L46) / `DATA_SOURCES_EN` (L108), `APP_URL` (L17) |

Figures are built **on the server from the `_gather()` snapshot**, using the same builder
functions as the on-screen computed vars, and turned into dicts with `fig.to_plotly_json()` and
then `report_kit.images.prepare_figure`. Radix tabs unmount hidden panels
(`components/results.py:774-781`), so on-screen divs cannot be the source.

---

## 5. Chart path

This app uses browser capture, exactly as in §2.7, with the handlers in `state/_export.py`:

| Handler | Kind | Role |
| --- | --- | --- |
| `start_report(fmt)` | normal | Snapshot and create the job |
| `receive_report_chart(job_id, key, data)` | normal | Store one captured chart |
| `build_report(job_id, fmt)` | background | Wait for charts, build and deliver |

**This app's Reflex rules**, enforced by `tests/test_app_builds.py`:

- Background tasks reach sibling handlers through **`self.__class__`**, never `type(self)`
  (L32-55).
- **Every state write happens inside `async with self`** (L102-186).
- `build_report` first awaits `_wait_for_history()` (L93, bounded at 20 s), as both current
  downloads do.

---

## 6. Maps

There are two map extents. The **detail** view is the property plus its 500 m ring, where 10 m
Sentinel-2 and 5 m SPOT are legible. The **context** view is the property plus its outer ring
(5 km).

| Map | View | Image builder | Status |
| --- | --- | --- | --- |
| Sentinel-2 + property + rings | detail | `report_kit.maps.imagery_backdrop` | kit |
| MapBiomas last year + outlines | context | `mapbiomas_year_image(year)`, split out of `mapbiomas_year_spec` (`services/layers.py:83`) | **to split** |
| Hansen loss by period + outlines | context | `hansen_change_image(mode, dat_criacao)`, split out of `hansen_change_spec` (L141) | **to split** |
| SPOT 2008, only if `spot_summary.has_coverage` | detail | `spot_image(key)`, split out of `ee_basemap_spec` (L48, `ds.EE_BASEMAPS`) | **to split** |

- Outlines come from `zones_geojson` as vectors (§2.6): the property in solid black and the rings
  dashed. Overlapping registrations are **not** drawn in v1: their geometries are not kept in
  state.
- The SPOT caption always carries its dates and the pre-cutoff percentage. It is never labelled
  simply "2008" (D10).
- EE cost (constraint **C6**): four `getThumbURL` calls per report, no reducers, cached per
  bounding box.

**Status (2026-09-24): built** in `services/report_maps.py`. `layers.py` now has
`spot_image`, `mapbiomas_year_image`, `hansen_treecover_image` and `hansen_change_image`
(`visualize=True` for thumbnails); the tile specs call the same functions. The Hansen map is
the Floresta tab's default layer (loss since 2008, undated gain) blended over tree cover 2000,
in one thumbnail. Outline strokes: yellow/white on imagery, black/grey on class rasters.

---

## 7. UI

The **"Relatório / Report"** block (§2.9) replaces the HTML subsection of `export_dialog()`
(`components/exports.py:104-127`) and keeps its `grass` colour scheme.

- **Checkboxes:** `exp_report_maps` and `exp_report_appendix` are new. `exp_report_figures`,
  `exp_report_tables` and `exp_include_gbif` (`state/_export.py:57-63`) are reused.
- **Disabled** without a property (`~has_imovel`) or while `report_busy`. The disabled reason is
  shown as text.
- A hidden 1×1 `rx.plotly` forces the Plotly bundle to load (§2.7).
- Translations go in `translations/pt.py` and `en.py` with the prefix `report_`. Check coverage
  with `python -m camposcope.translations`. The old `check_report_*` and
  `download_report_button` keys are retired.
- Cached computed vars that read `lang` through `getattr` need an explicit `deps=[..., "lang"]`
  with `auto_deps=False` (`state/_imovel.py:72-88`).

---

## 8. Delivery

`rx.download(data=bytes, filename=…, mime_type="application/pdf")`, the same mechanism as the
ODS and today's HTML (`state/_export.py:182,227`).

- File name: `camposcope_<cod_imovel>_<YYYYMMDD-HHMM>.pdf`.
- For the square: `camposcope_quadrado_<lat>_<lon>_…`.

---

## 9. Guardrails: C4 and D9 are hard requirements

**The report must never:**

- imply ownership, possession, legality or compliance;
- colour, translate or rank `condicao` or `status_imovel`;
- use the word "irregular";
- give an *área consolidada* figure or a "consolidada / não consolidada" label;
- mention *passivo ambiental*, restoration duty or RL/APP figures;
- give a score, verdict or valuation;
- state a biome from the navigation overlay (D13);
- claim the property is "inside a TI/UC".

**Allowed:**

- "n % imaged before 2008-07-22";
- "already cleared in the 2008 imagery";
- Hansen loss split into the three periods;
- overlaps listed as they are.

**Automated guard (`tests/test_report_c4.py`, run on the model, not on PDF text):**

1. The first block of the first section is a disclosure `Callout` with the exact
   `DISCLOSURE_*` constant for the language, or `square_disclosure` for the square.
2. Every string produced by `services/report_text.py`, and every section title and caption, is
   scanned in **pt and en** against:
   `irregular`, `consolidad`, `passivo`, `ilegal|illegal`, `infraç|infraction|violation`,
   `conformidade|complian`, `regularidade|regularity`, `déficit|deficit`, `excedente|surplus`,
   `reserva legal|legal reserve`, `\bAPP\b`, `due diligence`, `veredito|verdict`,
   `avaliação do imóvel|valuation`.
3. **Exempt**, because they are verbatim constants required elsewhere: the `DISCLOSURE_*`
   constants, which contain "regularidade ambiental" / "compliance"; the §13 attribution block;
   and the verbatim CAR fields (`condicao`, `status_imovel`, `tipo_imovel`).

**C3, provenance:** no section without its `Provenance`. SPOT gets one (§1, item 3).

---

## 10. Files to add or change

| File | Change |
| --- | --- |
| `camposcope/report_kit/**` | **Vendored** from Naturametrics by `scripts/sync_report_kit.py` there. Never edited here |
| `camposcope/services/report.py` | Becomes `build_imovel_report(**gather, lang, options) -> Report`; the HTML comes from `report_kit.render_html` |
| `camposcope/services/report_text.py` | New: explanatory templates (pt, en) |
| `camposcope/services/layers.py` | Split `mapbiomas_year_image`, `hansen_change_image` and `spot_image` out of their specs |
| `camposcope/services/exports.py` | Disclosure row in `_metadata_sheet`; sources by language |
| `camposcope/state/_export.py` | `_gather()` extended (§1); new vars (§2.9); `start_report`, `receive_report_chart`, `build_report`; remove `download_imovel_report` (L189-227) |
| `camposcope/state/_analysis.py` | Keep `spot_provenance` in `run_spot_coverage` (L431) |
| `camposcope/components/exports.py` | The report block (§7) |
| `camposcope/translations/pt.py`, `en.py` | `report_*` keys |
| `requirements.txt` | `reportlab>=4.2,<5`, `pillow>=10` |
| `Dockerfile` | `ENV REFLEX_SOCKET_MAX_HTTP_BUFFER_SIZE=4000000`; the "no chromium/kaleido" comment stays true |
| `tests/test_report.py` | Rewritten against the model |
| `tests/test_report_c4.py` | New (§9) |
| `tests/test_exports.py` | Assert the disclosure in `metadados` |
| `tests/test_report_kit_manifest.py` | New |
| `doc/10`, `doc/03`, `doc/README.md` | D14; Phase 6 entry; index row 13 |

---

## 11. Tests and the done test

**Offline** (`pytest`, default `-m "not live"`):

- `build_imovel_report` on the synthetic `IMOVEL` / `ZONES` fixtures of today's
  `tests/test_report.py`:
  - sections come in the §3 order;
  - uncomputed tabs are `not_run`, and unticked ones are `excluded`;
  - the square gets `square_disclosure`.
- The C4 guard (§9), and the disclosure in ODS.
- An English report contains no Portuguese template text. Verbatim CAR fields are exempt.
- `test_app_builds` passes: `index()` renders, there is no `type(self).`, and there are no
  writes outside `async with self`.
- The kit and manifest tests pass.

**Live** (`-m live`, run locally):

1. Property `MT-5108501-CBE0F5EDD27A4D7888E7392EA7D44793`: press *Calcular* on every tab, then
   PDF and HTML, in pt and en.
2. The same with only Cobertura computed, to check the "not run" statuses.
3. One property in Pantanal, where SPOT coverage is 0 %, to check that the SPOT section says so
   and that there is no SPOT map.

**Done test.** A reader with only the PDF can tell:

- that the CAR is self-declared, from the first lines of page 1;
- which property it is, read on which day, and its declared and computed areas;
- which registrations overlap it;
- what the land was and is, in the property and in each ring;
- how much Hansen loss fell before 2008, between 2008 and registration, and after registration;
- which datasets at which scales produced each number.

They should find no word that reads as a verdict. The file is at most 3 MB, and the HTML
version holds the same content.

**Status (2026-09-24): built.** `services/report.py` (`build_imovel_report`, `report_figures`,
`capture_specs`, `report_filename`), `services/report_text.py`, `services/report_maps.py`,
the three handlers in `state/_export.py` and the report block in `components/exports.py`.
`download_imovel_report` and the `check_report_*` / `download_report_button` keys are gone.
Tests: `tests/test_report.py` (rewritten on the model) and `tests/test_report_c4.py`; the
whole suite passes offline. Verified live for `MT-5108501-CBE0F5EDD27A4D7888E7392EA7D44793`
(Earth Engine and SICAR): four maps, two overlapping registrations, ~0.46 MB PDF; and end to
end in headless Chromium against `reflex run`, where the browser-captured Cobertura chart
lands in the PDF. Not yet run: the Pantanal (no SPOT) case and a session with every tab
computed through the UI.

Notes from the build:

- The kit's Noto Sans subset lacks U+2212 (−), U+2192 (→), U+2265 (≥) and U+21B3 (↳), so
  reportlab silently drops them. `text.fmt_signed` emits U+2212 and the provenance table
  prints ↳, both inside the kit. The app avoids those glyphs (`report_text.signed` uses an
  ASCII minus). The fix belongs to the canonical kit: a font subset with those glyphs, or
  ASCII fallbacks.
- The MapBiomas Fire service returned `fire_last_year = None` for every zone of the live
  property, while `fire_history_pct` was non-zero. The report says nothing about the last
  year in that case. The bug is in `services/fire.py`, not in the report.
- Per-zone charts use the zone active on screen (`active_zone`), and the report says which.

---

## 12. Deliberately deferred

- Maps of overlapping registrations (their geometries are not in state), and a biomass or fire
  map.
- The multi-stage Sankey, until it has a UI and a provenance.
- Reports over many properties (non-goal, [01](01-premises.md) §4).
- A per-chart "include in report" toggle.
