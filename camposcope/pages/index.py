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
#: Event DELEGATION on `document`, not a direct listener on the handle
#: element. The first version attached listeners to the specific handle DOM
#: node via a MutationObserver, which broke: `results_panel()` is
#: conditionally rendered, so React tears down and recreates that node on
#: state changes far more often than expected, silently orphaning the
#: listeners each time. Delegating to `document` and looking the handle up by
#: ID *inside* the event callback means there is nothing to re-attach —
#: whichever node currently has that ID is found fresh on every event.
_RESIZE_SCRIPT = """
(function () {
  if (window._csResizeInit) return;
  window._csResizeInit = true;
  var dragging = false, startY = 0, startHeight = 0;
  document.addEventListener('mousedown', function (e) {
    var handle = e.target.closest && e.target.closest('#results-drag-handle');
    if (!handle) return;
    var drawer = document.getElementById('results-drawer');
    if (!drawer) return;
    dragging = true;
    startY = e.clientY;
    startHeight = drawer.offsetHeight;
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });
  document.addEventListener('mousemove', function (e) {
    if (!dragging) return;
    var drawer = document.getElementById('results-drawer');
    if (!drawer) return;
    var delta = startY - e.clientY;
    // Capped at 3/4 of the viewport, not more: past that the map itself
    // stops being useful as a map, and the whole point of a drawer (over a
    // separate results page) is that the map stays visible alongside it.
    var next = Math.min(window.innerHeight * 0.75,
                        Math.max(80, startHeight + delta));
    // height, not just maxHeight: the drawer has no explicit height of its
    // own (only the 42vh maxHeight it starts with), so it sizes to its
    // *content* — a short tab's content stops growing well under the cap,
    // and the handle stops tracking the mouse right there, which reads as
    // "hit a limit" even though maxHeight is nowhere near it yet. Setting
    // height forces the box itself to the dragged size regardless of how
    // much content is in it.
    drawer.style.height = next + 'px';
    drawer.style.maxHeight = next + 'px';
  });
  document.addEventListener('mouseup', function () {
    if (dragging) { dragging = false; document.body.style.userSelect = ''; }
  });
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
        AppState.tr["layers_title"],
        rx.select(
            list(ALL_BASEMAPS.keys()),
            value=AppState.basemap,
            on_change=AppState.set_basemap,
            size="1",
            width="100%",
        ),
        rx.cond(
            AppState.basemap_busy,
            rx.hstack(rx.spinner(size="1"),
                     rx.text(AppState.tr["layers_loading"], size="1"),
                     spacing="2", align="center"),
        ),
        rx.cond(
            AppState.basemap_error,
            rx.callout(AppState.basemap_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.basemap.contains("spot"),
            rx.text(AppState.tr["layers_spot_hint"], size="1", color=MUTED),
        ),
        rx.hstack(
            rx.switch(checked=AppState.show_car_layer,
                      on_change=AppState.toggle_car_layer, size="1"),
            rx.text(AppState.tr["layers_car_wms"], size="1"),
            spacing="2", align="center",
        ),
        rx.text(AppState.tr["layers_car_wms_note"], size="1", color=MUTED),
        rx.hstack(
            rx.switch(checked=AppState.show_biomes,
                      on_change=AppState.toggle_biomes, size="1"),
            rx.text(AppState.tr["layers_biomes"], size="1"),
            spacing="2", align="center",
        ),
        rx.text(AppState.tr["layers_biomes_note"], size="1", color=MUTED),
    )


#: Below "md" (~48em / phone and small-tablet width), the sidebar stops
#: sharing flex space with the map — at 340px fixed it would leave the map a
#: sliver on an actual phone — and becomes a slide-over drawer instead:
#: fixed position, above the map, dismissible by its own close button or by
#: tapping the backdrop. At "md" and up it is exactly the original in-flow
#: panel, unchanged.
def _sidebar() -> rx.Component:
    return rx.fragment(
        # The backdrop: mobile-only (desktop's in-flow panel needs nothing
        # behind it), and only while open — tapping it is the same gesture as
        # tapping outside any mobile drawer, faster to find than hunting for
        # a specific close icon.
        rx.cond(
            AppState.sidebar_open,
            rx.box(
                on_click=AppState.toggle_sidebar,
                display=["block", "block", "none", "none"],
                position="fixed", top="0", left="0", right="0", bottom="0",
                background="rgba(0, 0, 0, 0.4)",
                z_index="1050",
            ),
        ),
        rx.cond(
            AppState.sidebar_open,
            rx.vstack(
                rx.hstack(
                    rx.spacer(),
                    rx.icon_button(
                        rx.icon("panel-left-close"),
                        on_click=AppState.toggle_sidebar,
                        # Bigger on mobile (44px+ is the usual minimum comfortable
                        # touch target) — size="1" reads fine as a mouse target on
                        # desktop but is exactly the kind of small hit-area that
                        # prompted this change in the first place. A literal-typed
                        # prop like `size` needs rx.breakpoints(), not a plain
                        # list — a plain list only works for style props.
                        size=rx.breakpoints(initial="3", sm="3", md="1", lg="1"),
                        variant="ghost", color_scheme="gray",
                        aria_label=AppState.tr["sidebar_hide_aria"],
                    ),
                    width="100%", padding_top="2",
                ),
                search_panel(),
                cadastral_card(),
                municipio_browser(),
                zones_panel(),
                _layers_panel(),
                width=["82vw", "82vw", "340px", "340px"],
                max_width=["320px", "320px", "340px", "340px"],
                min_width=["0", "0", "340px", "340px"],
                height="100%",
                overflow_y="auto",
                padding_x="4",
                border_right=BORDER,
                background="var(--color-panel)",
                align_items="stretch",
                spacing="0",
                position=["fixed", "fixed", "static", "static"],
                top="0", left="0",
                z_index=["1100", "1100", "auto", "auto"],
                box_shadow=["0 0 32px rgba(0, 0, 0, 0.35)",
                           "0 0 32px rgba(0, 0, 0, 0.35)", "none", "none"],
            ),
            rx.fragment(
                # Collapsed, desktop: the original slim always-visible rail —
                # unchanged, works fine with a mouse.
                rx.box(
                    rx.icon_button(
                        rx.icon("panel-left-open", size=15),
                        on_click=AppState.toggle_sidebar,
                        size="1", variant="soft", color_scheme="gray",
                        aria_label=AppState.tr["sidebar_show_aria"],
                    ),
                    display=["none", "none", "block", "block"],
                    padding="2",
                    border_right=BORDER,
                    background="var(--color-panel)",
                    height="100%",
                ),
                # Collapsed, mobile: a floating button instead of a sliver at
                # the edge of the screen — the whole point of this change is
                # that it has to be *found* first, by touch, without a mouse
                # to hover-discover it with.
                rx.icon_button(
                    rx.icon("panel-left-open", size=20),
                    on_click=AppState.toggle_sidebar,
                    size="4", variant="solid", color_scheme="grass",
                    aria_label=AppState.tr["sidebar_show_aria"],
                    display=["flex", "flex", "none", "none"],
                    position="fixed", top="68px", left="12px", z_index="1100",
                    box_shadow="0 2px 10px rgba(0, 0, 0, 0.35)",
                ),
            ),
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
        flex="1",
        height="100%",
        position="relative",
        # NOT rx.script(_RESIZE_SCRIPT) as a child — that compiles to a plain
        # <script> body nested inside react-helmet's <Helmet>, and neither
        # React's own commit (scripts inserted as JSX children are set via
        # innerHTML, which browsers refuse to execute) nor Helmet's here ever
        # actually ran it: confirmed live via headless Chromium + CDP,
        # window._csResizeInit stayed false and a simulated drag never moved
        # the drawer. on_mount=rx.call_script(...) fires through Reflex's own
        # event pipeline instead — the same mechanism already proven to work
        # for the per-chart PNG export buttons (components/export_widgets.py)
        # — so the browser actually executes it once this box mounts.
        on_mount=rx.call_script(_RESIZE_SCRIPT),
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
