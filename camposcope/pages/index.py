"""The map + analysis workspace. v1 is one page (doc/08-ui-ux.md §1)."""

from __future__ import annotations

import reflex as rx

from ..components.cadastro import cadastral_card, zones_panel
from ..components.layout import BORDER, MUTED, header, section
from ..components.map.leaflet_map import leaflet_map
from ..components.map_legend import map_legend
from ..components.results import results_panel
from ..components.search import municipio_browser, search_panel
from ..config.datasets import ALL_BASEMAPS
from ..state import AppState

#: Drag-to-resize for the results drawer. Deliberately pure client-side DOM
#: manipulation, not a Python event per pixel of mouse movement — a state
#: round trip over the WebSocket for every `mousemove` would be visibly
#: laggy, and the resized height is a per-viewer convenience, not data
#: anything else needs to know about.
#:
#: A `MutationObserver` re-attaches the listener whenever the handle element
#: appears, because the results drawer (and its handle) only exists in the
#: DOM once a property is selected — `results_panel()` is conditionally
#: rendered, so React mounts a fresh element each time rather than ever
#: leaving a stale one for a one-time `DOMContentLoaded` listener to find.
_RESIZE_SCRIPT = """
(function () {
  function init() {
    var handle = document.getElementById('results-drag-handle');
    var drawer = document.getElementById('results-drawer');
    if (!handle || !drawer || handle._csDragInit) return;
    handle._csDragInit = true;
    var dragging = false, startY = 0, startHeight = 0;
    handle.addEventListener('mousedown', function (e) {
      dragging = true;
      startY = e.clientY;
      startHeight = drawer.offsetHeight;
      document.body.style.userSelect = 'none';
      e.preventDefault();
    });
    document.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      var delta = startY - e.clientY;
      var next = Math.min(window.innerHeight * 0.85,
                          Math.max(80, startHeight + delta));
      drawer.style.maxHeight = next + 'px';
    });
    document.addEventListener('mouseup', function () {
      if (dragging) { dragging = false; document.body.style.userSelect = ''; }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  new MutationObserver(init).observe(document.body, {childList: true, subtree: true});
})();
"""


def _drag_handle() -> rx.Component:
    return rx.box(
        rx.box(width="36px", height="4px", border_radius="2px",
              background="var(--gray-6)"),
        id="results-drag-handle",
        display="flex", justify_content="center", align_items="center",
        width="100%", height="14px", cursor="ns-resize", flex_shrink="0",
        _hover={"background": "var(--gray-3)"},
    )


def _layers_panel() -> rx.Component:
    return section(
        "Camadas",
        rx.select(
            list(ALL_BASEMAPS.keys()),
            value=AppState.basemap,
            on_change=AppState.set_basemap,
            size="1",
            width="100%",
        ),
        rx.cond(
            AppState.basemap_busy,
            rx.hstack(rx.spinner(size="1"), rx.text("Carregando camada…", size="1"),
                     spacing="2", align="center"),
        ),
        rx.cond(
            AppState.basemap_error,
            rx.callout(AppState.basemap_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.basemap.contains("spot"),
            rx.text(
                "Verificação de cobertura e datas: aba Floresta.",
                size="1", color=MUTED,
            ),
        ),
        rx.hstack(
            rx.switch(checked=AppState.show_car_layer,
                      on_change=AppState.toggle_car_layer, size="1"),
            rx.text("Imóveis do CAR (WMS)", size="1"),
            spacing="2", align="center",
        ),
        rx.text("Aparece a partir do zoom 8.", size="1", color=MUTED),
        rx.hstack(
            rx.switch(checked=AppState.show_biomes,
                      on_change=AppState.toggle_biomes, size="1"),
            rx.text("Biomas e domínios (IBGE)", size="1"),
            spacing="2", align="center",
        ),
        rx.text(
            "Limites aproximados (~1 km) — orientação, não decide o bioma de "
            "um imóvel específico.",
            size="1", color=MUTED,
        ),
    )


def _sidebar() -> rx.Component:
    return rx.cond(
        AppState.sidebar_open,
        rx.vstack(
            rx.hstack(
                rx.spacer(),
                rx.icon_button(
                    rx.icon("panel-left-close", size=15),
                    on_click=AppState.toggle_sidebar,
                    size="1", variant="ghost", color_scheme="gray",
                    aria_label="Esconder painel",
                ),
                width="100%", padding_top="2",
            ),
            search_panel(),
            cadastral_card(),
            municipio_browser(),
            zones_panel(),
            _layers_panel(),
            width="340px",
            min_width="340px",
            height="100%",
            overflow_y="auto",
            padding_x="4",
            border_right=BORDER,
            background="var(--color-panel)",
            align_items="stretch",
            spacing="0",
        ),
        # Collapsed: a slim always-visible handle to bring it back, rather
        # than losing the toggle along with the panel it controls.
        rx.box(
            rx.icon_button(
                rx.icon("panel-left-open", size=15),
                on_click=AppState.toggle_sidebar,
                size="1", variant="soft", color_scheme="gray",
                aria_label="Mostrar painel",
            ),
            padding="2",
            border_right=BORDER,
            background="var(--color-panel)",
            height="100%",
        ),
    )


def _map() -> rx.Component:
    """The map, filling its box, with the results drawer overlaid on top of it
    rather than sharing flex space with it (doc/08-ui-ux.md §1: the drawer
    "rises from the bottom" of the map area, it does not shrink it). Kept as a
    single box with exactly the props Leaflet has always been given here —
    ``flex="1", height="100%", position="relative"`` — so the map's own layout
    is never at the mercy of a sibling's height.
    """
    return rx.box(
        leaflet_map(
            id="camposcope-map",
            center=AppState.center,
            zoom=AppState.zoom,
            layers=AppState.map_layers,
            overlays=AppState.map_overlays,
            vectors=AppState.biome_vectors,
            fit_bounds=AppState.fit_bounds,
            on_map_click=AppState.select_at_point,
            # Transições: two MapBiomas years at once, older left / newer
            # right, dragged apart with the divider this turns on
            # (leaflet_map.js's existing swipe machinery — ported, previously
            # unused in this app).
            swipe=AppState.map_swipe_enabled,
            width="100%",
            height="100%",
        ),
        map_legend(),
        rx.box(
            _drag_handle(),
            results_panel(),
            id="results-drawer",
            position="absolute",
            bottom="0",
            left="0",
            right="0",
            max_height="42vh",
            overflow_y="auto",
            display="flex", flex_direction="column",
            # Leaflet's own panes (tile/overlay/marker/popup) use z-index up to
            # ~700 internally; anything lower than that sits UNDER the map and
            # is invisible except for whatever sliver Leaflet doesn't paint —
            # exactly the bug this value fixes. The legend sits at 900, so the
            # drawer stays above it too.
            z_index="1000",
        ),
        rx.script(_RESIZE_SCRIPT),
        flex="1",
        height="100%",
        position="relative",
    )


def index() -> rx.Component:
    return rx.vstack(
        header(),
        rx.hstack(
            _sidebar(),
            _map(),
            width="100%",
            flex="1",
            spacing="0",
            overflow="hidden",
        ),
        width="100vw",
        height="100vh",
        spacing="0",
        overflow="hidden",
    )
