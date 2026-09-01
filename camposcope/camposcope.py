"""Camposcope — land-cover history and landscape context for a CAR property.

App entry point. See doc/ for premises, architecture and roadmap.
"""

from __future__ import annotations

import logging

import reflex as rx

from .api import register as register_api
from .canada.pages.index import canada_index
from .canada.state import CanadaState
from .components.layout import ACCENT
from .config.settings import GA_MEASUREMENT_ID
from .pages.index import index
from .state import AppState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def _ga_head_components() -> list[rx.Component]:
    """GA4 tag, only when CS_GA_MEASUREMENT_ID is set (empty in local dev)."""
    if not GA_MEASUREMENT_ID:
        return []
    return [
        rx.el.script(src=f"https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}", async_=True),
        rx.el.script(f"""
            window.dataLayer = window.dataLayer || [];
            function gtag(){{ dataLayer.push(arguments); }}
            gtag('js', new Date());
            gtag('config', '{GA_MEASUREMENT_ID}');
        """),
    ]


app = rx.App(
    theme=rx.theme(appearance="light", accent_color=ACCENT, radius="medium"),
    style={"fontFamily": "Inter, system-ui, sans-serif"},
    head_components=[
        # Without this, mobile browsers lay the page out at ~980px and zoom out
        # to fit — every responsive breakpoint would evaluate as "desktop" and
        # the mobile layout would never appear. Inherited from Naturametrics
        # along with the reason.
        rx.el.meta(
            name="viewport",
            content="width=device-width, initial-scale=1, viewport-fit=cover",
        ),
        rx.el.meta(name="theme-color", content="#ffffff"),
        # The mobile/desktop split (pages/index.py's `_sidebar`/`_mobile_sheet`/
        # `results-drawer`, and canada/pages/index.py's own copy of the same
        # shape) is width-only (`display=[...]` breakpoints), and a phone
        # rotated to landscape is routinely wider than the 768px "md" cutoff
        # (iPhone 13: 844px) while still only ~390px tall — it fell into the
        # desktop sidebar + results-drawer chrome, sized for a viewport with
        # far more height to spare, and the analysis area read as a small
        # corner next to empty space rather than the mobile sheet it should
        # have gotten. This overrides by height instead wherever a landscape
        # phone lands: `id`s set on the relevant boxes in pages/index.py and
        # canada/pages/index.py — one stylesheet covers both pages since
        # `head_components` here applies globally, not per-page.
        #
        # The second rule is the same override applied one level deeper.
        # `components/layout.py::split_panel` (and the Canada page's copy of
        # it) puts the chart and its data table side by side from Radix's
        # `md` (48em = 768px) up — also width-only, so the same landscape
        # phone that needed the rules above ALSO took the two-column branch:
        # measured live at 844x390, the trajectory chart rendered 403px wide
        # inside an 844px sheet, the table filling the other half, on the
        # viewport with the least height to give either of them. Stacking
        # them back into one column here hands the chart the sheet's full
        # width and drops the table below it, exactly as portrait already
        # does. `!important` because Radix's own `md:` class carries a media
        # query of its own — this one has to win where both apply.
        rx.el.style("""
            @media (max-height: 500px) and (orientation: landscape) {
              #desktop-sidebar, #results-drawer,
              #ca-desktop-sidebar, #ca-results-drawer { display: none !important; }
              #mobile-sheet, #ca-mobile-sheet { display: flex !important; }
              .cs-split-panel { flex-direction: column !important; }
              .cs-split-chart { width: 100% !important; }
            }
        """),
        *_ga_head_components(),
        # `rx.plotly`'s `config.responsive: true` resizes a chart via its own
        # internal ResizeObserver on the plot's container — which watches
        # that ELEMENT's own box, not the viewport. A phone rotation changes
        # the viewport's dimensions, and the container's box does follow
        # (through the normal CSS cascade), but that observer doesn't
        # reliably fire for every browser/orientation-change combination —
        # a real report here: charts kept rendering at whatever size they'd
        # had in the PREVIOUS orientation, so a chart sized for a wide
        # landscape viewport was still that wide after rotating to a narrow
        # portrait one (using what had been the landscape *width* as if it
        # were still correct, rather than shrinking to the new one) — every
        # analysis-area chart in this app is a `.js-plotly-plot`, so a
        # single global listener that force-resizes all of them on the
        # browser's own `resize`/`orientationchange` events is a reliable
        # fallback that doesn't depend on that internal observer at all.
        rx.el.script("""
            (function () {
              if (window._csPlotlyResizeInit) return;
              window._csPlotlyResizeInit = true;
              var timer = null;
              function resizeAll() {
                if (!window.Plotly) return;
                document.querySelectorAll('.js-plotly-plot').forEach(function (gd) {
                  try { window.Plotly.Plots.resize(gd); } catch (err) { /* not fully mounted yet */ }
                });
              }
              function scheduleResize() {
                window.clearTimeout(timer);
                timer = window.setTimeout(resizeAll, 120);
              }
              window.addEventListener('resize', scheduleResize);
              window.addEventListener('orientationchange', scheduleResize);
            })();
        """),
        # Idle tabs otherwise keep the Reflex WebSocket reconnecting forever,
        # which pins a billed Cloud Run instance with nobody using it — see
        # assets/idle_guard.js and assets/paused.html.
        rx.el.script(src="/assets/idle_guard.js", defer=True),
    ],
)

app.add_page(
    index,
    route="/",
    title="Camposcope — Análise de imóveis rurais do CAR",
    description=(
        "História de uso da terra e contexto de paisagem de um imóvel rural "
        "registrado no CAR, a partir do SICAR, MapBiomas e Earth Engine."
    ),
    on_load=AppState.on_load,
)

# The Canada page is a self-contained sibling under camposcope/canada/ — its
# own state root, services, components and translations. It shares Earth
# Engine access, the tile cache, the ODS writer and the Leaflet component, and
# nothing else: the two cadastres, legends and years differ, so a shared state
# root would mean every var carrying a "which country" qualifier. See
# camposcope/canada/__init__.py for the full substitution table.
app.add_page(
    canada_index,
    route="/canada",
    title="Camposcope Canada — Earth Engine for Rural Properties",
    description=(
        "Rural property analysis from the ParcelMap BC parcel fabric, the "
        "AAFC Annual Crop Inventory, Hansen Global Forest Change and NTEMS "
        "VLCE2, on Earth Engine."
    ),
    on_load=CanadaState.on_load,
)

# The biome and ecozone polygons are fetched by the browser over HTTP, not
# pushed through the WebSocket — see camposcope/api/__init__.py for why.
register_api(app)
