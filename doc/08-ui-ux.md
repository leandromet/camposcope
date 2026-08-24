# 08 — UI / UX

## 1. The screen

One page. A map that fills the viewport, a left sidebar that holds everything else, and a
results drawer that rises from the bottom when there is something to show.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Camposcope            [buscar imóvel…]              [pt|en]  [?]     │
├────────────────┬─────────────────────────────────────────────────────┤
│ BUSCA          │                                                     │
│  ○ código CAR  │                                                     │
│  ○ no mapa     │                    MAP                              │
│  ○ município   │         CAR boundaries (WMS) · property (GeoJSON)   │
│                │         rings · MapBiomas year layer · imagery      │
│ ── IMÓVEL ──   │                                                     │
│  MT-5108501-…  │                                          [year ◀▶]  │
│  Vera / MT     │                                          [legend]   │
│  3 240,10 ha   │                                                     │
│  (calc. 3 238) │                                                     │
│  AT · Analisado│                                                     │
│  reg. 2025-11  │                                                     │
│  ⓘ autodeclar. ├─────────────────────────────────────────────────────┤
│                │  COBERTURA │ TRANSIÇÕES │ FLORESTA │ BIOMASSA │ ⇩   │
│ ── ZONAS ──    │                                                     │
│ ── CAMADAS ──  │              charts for the selected zone           │
│ ── EXPORTAR ── │                                                     │
└────────────────┴─────────────────────────────────────────────────────┘
```

## 2. The search box and the gestures

One box resolves four kinds of input in a fixed order — code, coordinate, município, place
name — and **says how it read what you typed** before acting on it
([11-search-and-navigation.md](11-search-and-navigation.md) §2):

```
┌──────────────────────────────────────────┐
│ 🔍  código CAR, coordenada ou lugar…     │
└──────────────────────────────────────────┘
   ↳ lido como: coordenada -12.4979, -55.4977
```

That echo line is not decoration. It is what stops a transposed coordinate pair or a
mistyped code from quietly resolving somewhere plausible and wrong.

A place-name result **frames the map and selects no property**. Finding a place and
identifying a registration are different acts, and a fuzzy address match must never become
an implied claim about who holds what.

**Paste a code.** The `UF-<ibge>-<32hex>` shape is validated locally first — a malformed
code fails instantly with a message about its shape, and no request leaves the machine. The
UF prefix picks the layer.

**Click the map.** Point → UF (local boundaries, **D5**) → `INTERSECTS` query. **When more
than one property comes back — the normal case — a chooser appears**, listing each
candidate with its area, `condicao` and registration date, and the map highlights the one
under the cursor. Never auto-select the first ([05](05-sicar-geoserver.md) §5.2).

**Browse a município.** UF select → município select → a paged, sortable list showing code,
area and `condicao`. Geometry is not requested for the list, only for the row that is
clicked — the difference between kilobytes and megabytes.

**Type a place.** Last resort, and deliberately so: rural properties largely do not have
street addresses ([11](11-search-and-navigation.md) §1). The result is a framed map plus the
OpenStreetMap attribution shown *with the result*, not buried in an About page.

A property is also addressable: `/?car=MT-5108501-CBE0…` loads straight into it, which is
the whole persistence model ([01](01-premises.md) §4).

## 3. The cadastral card — where C4 lives

Sits directly under the search, permanently visible once a property is selected:

| Field | Presentation |
|---|---|
| `cod_imovel` | monospace, click to copy |
| `municipio` / `uf` | plain |
| `area` | **declared**, labelled as declared |
| computed area | next to it, with the delta and % when it differs materially |
| `m_fiscal` | with the size class in words (pequena / média / grande propriedade) |
| `condicao` | **verbatim**, in full, no truncation, no icon, no colour |
| `status_imovel` | **verbatim** code |
| `dat_criacao` / `data_atualizacao` | dates; `data_atualizacao` shown as *"não informada"* when null |
| disclosure | **permanent, non-dismissible**: the CAR is self-declared and does not prove ownership, regularity or possession |

`condicao` gets no traffic light, no badge colour and no rewording. The temptation to turn
*"Analisado, aguardando regularização ambiental"* into a red chip is exactly what C4
forbids: the moment it becomes a colour, Camposcope is issuing a verdict
([01](01-premises.md) §5).

## 4. Zones

A zone selector — the property, then each ring — governs which geometry the charts describe.
Selecting a zone highlights it on the map; hovering a chart series highlights the
corresponding class on the map layer. **The viewport does not move** (C1), ever, for any of
this.

Ring radii are editable (default 500 m / 2 km / 5 km — three rings, not four; a fourth ring added little and cost an extra Earth Engine feature per analysis). Large properties get reduced
radii automatically with a visible notice explaining why ([06](06-ee-layers.md) §7).

## 5. Results tabs

| Tab | Content | Map layer while active |
|---|---|---|
| **Cobertura** | Chart + class-breakdown table side by side, `dat_criacao` marked on the axis | MapBiomas, selected year |
| **Transições** | Two-stage Sankey + table side by side, plus the multi-stage diagram ([07](07-transitions.md)) | none — a diagram, not a single raster |
| **Floresta** | Three period stats (até 2008 / 2008 até o registro / depois do registro) + chart + table | Hansen loss/gain since 2008 or since registration |
| **Biomassa** | Chart + snapshot table side by side, gaps drawn as gaps | ESA CCI, selected snapshot |
| **Validação** | Mode switch (SPOT×2008 / IBGE×2022); bucket-matrix table for the IBGE mode | Two layers, swipe-clipped left/right |
| **⇩** | Export panel | — |

Chart and table are always side by side (`components/layout.py::split_panel`), stacking only
on a narrow drawer — a full-width chart with the numbers behind it a tooltip away was the
wrong trade once every tab needed a table.

**The map shows whatever the active tab is about.** Switching tabs mints (or reuses) that
tab's tile layer — never a fresh Earth Engine call on a tab already visited this session — and
an **on-map legend control**, not a sidebar section, carries its on/off switch and the one
control specific to that layer: a year for Cobertura and Biomassa, "desde 2008" / "desde o
registro" for Floresta. It sits where a native Leaflet control would, in the map's corner,
above Leaflet's own panes and below the results drawer in z-order.

Each figure also carries a one-line provenance strip underneath — dataset, scale, date
computed — not in a tooltip, not behind an info icon. If a claim can be screenshotted, its
sources go in the screenshot.

Two layers carry a permanent note in the sidebar layer panel for the same reason — they are
orientation/context layers, not tied to a results tab, so they stay in the sidebar rather
than the on-map legend:

- **SPOT 2008** — the acquisition date range of the pixels under *this* property, the
  fraction imaged before 2008-07-22, the fraction not covered at all, and the statement that
  Camposcope does not classify área consolidada ([12](12-spot-2008.md) §4). The mosaic is
  *circa* 2008; a screenshot without its dates implies a date it may not have.
- **Biomas e domínios** — approximate to roughly a kilometre, for orientation only
  ([11](11-search-and-navigation.md) §6). It names itself on hover, which is why it is the
  one vector layer in an app of tiles.

## 6. Loading and failure

The two halves of the app fail independently and the UI must show that
([02](02-architecture.md) §7):

- **SICAR pending** (~1 s): skeleton on the card, map unchanged.
- **SICAR failed**: an error naming the service and offering retry. Nothing else on the page
  is blocked; a previously loaded property stays.
- **EE pending** (seconds to a minute): the boundary, rings, card and map are fully
  interactive; each results tab shows its own progress.
- **EE failed**: per-analysis error in its own tab. A failed biomass call must not hide a
  successful cobertura chart.

The one thing never done: a full-page spinner. Something useful is on screen within a second
of every gesture.

## 7. Language

pt-BR default, English available, following Naturametrics' `translations/` package. Source
terms — `condicao` values, `status_imovel`, `tipo_imovel` — are **never translated**. They
are cadastral vocabulary; the English UI shows them in Portuguese with a gloss, because a
translated `condicao` is no longer quotable against the source.

## 8. Mobile

The sidebar collapses to a bottom sheet; the map keeps the full viewport. Reflex needs the
explicit viewport meta tag or every breakpoint evaluates as desktop — ported from
Naturametrics' app entry, along with the comment explaining why.
