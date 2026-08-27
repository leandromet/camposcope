"""The map + analysis workspace for the Canada page. One page, mirroring the
Brazil page's own v1 shape."""

from __future__ import annotations

import reflex as rx

from ...components.map.leaflet_map import leaflet_map
from ..components.layout import BORDER, MUTED, header
from ..components.map_legend import map_legend
from ..components.parcel_card import parcel_card, zones_panel
from ..components.results import results_panel
from ..components.search import search_panel
from ..config.datasets import ALL_BASEMAPS
from ..state import CanadaState as S

_RESIZE_SCRIPT = """
(function () {
  if (window._caResizeInit) return;
  window._caResizeInit = true;
  var dragging = false, startY = 0, startHeight = 0;
  document.addEventListener('mousedown', function (e) {
    var handle = e.target.closest && e.target.closest('#ca-results-drag-handle');
    if (!handle) return;
    var drawer = document.getElementById('ca-results-drawer');
    if (!drawer) return;
    dragging = true;
    startY = e.clientY;
    startHeight = drawer.offsetHeight;
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });
  document.addEventListener('mousemove', function (e) {
    if (!dragging) return;
    var drawer = document.getElementById('ca-results-drawer');
    if (!drawer) return;
    var delta = startY - e.clientY;
    var next = Math.min(window.innerHeight * 0.75,
                        Math.max(80, startHeight + delta));
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
        id="ca-results-drag-handle",
        display="flex", justify_content="center", align_items="center",
        width="100%", height="14px", cursor="ns-resize", flex_shrink="0",
        _hover={"background": "var(--gray-3)"},
    )


def _layers_panel() -> rx.Component:
    from ..components.layout import section

    return section(
        S.tr["layers_title"],
        rx.select(
            list(ALL_BASEMAPS.keys()), value=S.basemap,
            on_change=S.set_basemap,
            size="1", width="100%",
        ),
        rx.hstack(
            rx.switch(checked=S.show_parcel_layer,
                     on_change=S.toggle_parcel_layer, size="1"),
            rx.text(S.tr["layers_parcel_wms"], size="1"),
            spacing="2", align="center",
        ),
        rx.text(S.tr["layers_parcel_wms_note"], size="1", color=MUTED),
        rx.hstack(
            rx.switch(checked=S.show_ecozones, on_change=S.toggle_ecozones,
                     size="1"),
            rx.text(S.tr["layers_ecozones"], size="1"),
            spacing="2", align="center",
        ),
        rx.text(S.tr["layers_ecozones_note"], size="1", color=MUTED),
    )


def _sidebar() -> rx.Component:
    return rx.fragment(
        rx.cond(
            S.sidebar_open,
            rx.box(
                on_click=S.toggle_sidebar,
                display=["block", "block", "none", "none"],
                position="fixed", top="0", left="0", right="0", bottom="0",
                background="rgba(0, 0, 0, 0.4)", z_index="1050",
            ),
        ),
        rx.cond(
            S.sidebar_open,
            rx.vstack(
                rx.hstack(
                    rx.spacer(),
                    rx.icon_button(
                        rx.icon("panel-left-close"),
                        on_click=S.toggle_sidebar,
                        size=rx.breakpoints(initial="3", sm="3", md="1", lg="1"),
                        variant="ghost", color_scheme="gray",
                        aria_label=S.tr["sidebar_hide_aria"],
                    ),
                    width="100%", padding_top="2",
                ),
                search_panel(),
                parcel_card(),
                zones_panel(),
                _layers_panel(),
                width=["82vw", "82vw", "340px", "340px"],
                max_width=["320px", "320px", "340px", "340px"],
                min_width=["0", "0", "340px", "340px"],
                height="100%", overflow_y="auto", padding_x="4",
                border_right=BORDER, background="var(--color-panel)",
                align_items="stretch", spacing="0",
                position=["fixed", "fixed", "static", "static"],
                top="0", left="0", z_index=["1100", "1100", "auto", "auto"],
                box_shadow=["0 0 32px rgba(0, 0, 0, 0.35)",
                           "0 0 32px rgba(0, 0, 0, 0.35)", "none", "none"],
            ),
            rx.fragment(
                rx.box(
                    rx.icon_button(
                        rx.icon("panel-left-open", size=15),
                        on_click=S.toggle_sidebar,
                        size="1", variant="soft", color_scheme="gray",
                        aria_label=S.tr["sidebar_show_aria"],
                    ),
                    display=["none", "none", "block", "block"],
                    padding="2", border_right=BORDER,
                    background="var(--color-panel)", height="100%",
                ),
                rx.icon_button(
                    rx.icon("panel-left-open", size=20),
                    on_click=S.toggle_sidebar,
                    size="4", variant="solid", color_scheme="jade",
                    aria_label=S.tr["sidebar_show_aria"],
                    display=["flex", "flex", "none", "none"],
                    position="fixed", top="68px", left="12px", z_index="1100",
                    box_shadow="0 2px 10px rgba(0, 0, 0, 0.35)",
                ),
            ),
        ),
    )


def _map() -> rx.Component:
    return rx.box(
        leaflet_map(
            id="camposcope-ca-map",
            center=S.center,
            zoom=S.zoom,
            layers=S.map_layers,
            overlays=S.map_overlays,
            vectors=S.ecozone_vectors,
            fit_bounds=S.fit_bounds,
            on_map_click=S.select_at_point,
            swipe=S.map_swipe_enabled,
            width="100%", height="100%",
        ),
        map_legend(),
        rx.box(
            _drag_handle(),
            results_panel(),
            id="ca-results-drawer",
            position="absolute", bottom="0", left="0", right="0",
            max_height="42vh", overflow_y="auto",
            display="flex", flex_direction="column",
            z_index="1000",
        ),
        flex="1", height="100%", position="relative",
        on_mount=rx.call_script(_RESIZE_SCRIPT),
    )


def canada_index() -> rx.Component:
    return rx.vstack(
        header(),
        rx.hstack(_sidebar(), _map(), width="100%", flex="1", spacing="0",
                 overflow="hidden"),
        width="100vw", height="100vh", spacing="0", overflow="hidden",
    )
