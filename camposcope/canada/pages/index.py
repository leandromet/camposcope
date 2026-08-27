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

#: Shared by the desktop results drawer and the mobile bottom sheet — see
#: ``camposcope/pages/index.py``'s own ``_SHEET_SCRIPT`` for the full design
#: rationale (Pointer Events over mouse-only, document-level delegation,
#: the ``data-drawer-handle``/``data-snap`` driven behaviour split). This is
#: the same script, `_ca`-prefixed guard flag so it can never collide with
#: the Brazil page's own copy if both ever shared a browser tab.
_SHEET_SCRIPT = """
(function () {
  if (window._caSheetInit) return;
  window._caSheetInit = true;

  var dragging = false, pointerId = null, startY = 0, startHeight = 0;
  var drawerEl = null, snapMode = 'free';

  function snapPoints() {
    return [80, window.innerHeight * 0.45, window.innerHeight * 0.75];
  }

  function nearest(height, points) {
    var best = points[0], bestDist = Math.abs(height - points[0]);
    for (var i = 1; i < points.length; i++) {
      var d = Math.abs(height - points[i]);
      if (d < bestDist) { best = points[i]; bestDist = d; }
    }
    return best;
  }

  function settle(el, target) {
    el.style.transition = 'height 200ms ease-out';
    el.style.height = target + 'px';
    el.style.maxHeight = target + 'px';
    window.setTimeout(function () { el.style.transition = ''; }, 220);
  }

  window.__caSheetSnapTo = function (name) {
    var el = document.getElementById('ca-mobile-sheet');
    if (!el) return;
    var pts = snapPoints();
    var target = name === 'full' ? pts[2] : name === 'peek' ? pts[0] : pts[1];
    if (el.offsetHeight >= target) return;
    settle(el, target);
  };

  document.addEventListener('pointerdown', function (e) {
    var handle = e.target.closest && e.target.closest('[data-drawer-handle]');
    if (!handle) return;
    var drawerId = handle.getAttribute('data-drawer-handle');
    drawerEl = document.getElementById(drawerId);
    if (!drawerEl) return;
    snapMode = handle.getAttribute('data-snap') || 'free';
    dragging = true;
    pointerId = e.pointerId;
    startY = e.clientY;
    startHeight = drawerEl.offsetHeight;
    try { handle.setPointerCapture(e.pointerId); } catch (err) { /* older browsers */ }
    document.body.style.userSelect = 'none';
  });

  document.addEventListener('pointermove', function (e) {
    if (!dragging || e.pointerId !== pointerId || !drawerEl) return;
    var delta = startY - e.clientY;
    var next = Math.min(window.innerHeight * 0.75, Math.max(80, startHeight + delta));
    drawerEl.style.height = next + 'px';
    drawerEl.style.maxHeight = next + 'px';
  });

  function end(e) {
    if (!dragging || e.pointerId !== pointerId || !drawerEl) return;
    dragging = false;
    document.body.style.userSelect = '';
    if (snapMode === 'snap') {
      settle(drawerEl, nearest(drawerEl.offsetHeight, snapPoints()));
    }
    drawerEl = null;
  }
  document.addEventListener('pointerup', end);
  document.addEventListener('pointercancel', end);

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown') return;
    var active = document.activeElement;
    var handle = active && active.closest &&
      active.closest('[data-drawer-handle][data-snap="snap"]');
    if (!handle) return;
    var drawer = document.getElementById(handle.getAttribute('data-drawer-handle'));
    if (!drawer) return;
    var pts = snapPoints();
    var idx = pts.indexOf(nearest(drawer.offsetHeight, pts));
    idx = e.key === 'ArrowUp' ? Math.min(pts.length - 1, idx + 1) : Math.max(0, idx - 1);
    settle(drawer, pts[idx]);
    e.preventDefault();
  });
})();
"""


def _drag_handle(*, drawer_id: str, handle_id: str, snap: bool) -> rx.Component:
    return rx.box(
        rx.box(width="36px", height="4px", border_radius="2px",
              background="var(--gray-6)"),
        id=handle_id,
        custom_attrs={
            "data-drawer-handle": drawer_id,
            "data-snap": "snap" if snap else "free",
        },
        tab_index=0 if snap else None,
        role="slider" if snap else None,
        aria_label=S.tr["sheet_handle_aria"] if snap else None,
        outline="none",
        display="flex", justify_content="center", align_items="center",
        width="100%", height="14px", cursor="ns-resize", flex_shrink="0",
        _hover={"background": "var(--gray-3)"},
        _focus_visible={"background": "var(--gray-4)",
                        "box_shadow": "inset 0 0 0 2px var(--accent-8)"},
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
        rx.cond(
            S.show_ecozones,
            rx.segmented_control.root(
                rx.segmented_control.item(S.tr["layers_ecozone_level_ecozone"],
                                          value="ecozone"),
                rx.segmented_control.item(S.tr["layers_ecozone_level_ecoregion"],
                                          value="ecoregion"),
                rx.segmented_control.item(S.tr["layers_ecozone_level_ecodistrict"],
                                          value="ecodistrict"),
                value=S.ecozone_level, on_change=S.set_ecozone_level,
                size="1", width="100%",
            ),
        ),
        rx.text(S.tr["layers_ecozones_note"], size="1", color=MUTED),
    )


#: Desktop ("md" and up) only, now — the mobile drawer is `_mobile_sheet()`.
#: See the Brazil page's own `_sidebar()` for the full rationale; this is
#: the same shape, ported.
def _sidebar() -> rx.Component:
    return rx.cond(
        S.sidebar_open,
        rx.vstack(
            rx.hstack(
                rx.spacer(),
                rx.box(
                    rx.icon("panel-left-close", size=18),
                    on_click=S.toggle_sidebar,
                    role="button", cursor="pointer",
                    aria_label=S.tr["sidebar_hide_aria"],
                    display="flex", align_items="center",
                    justify_content="center",
                    width="28px", height="28px",
                    border_radius="var(--radius-2)",
                    _hover={"background": "var(--gray-4)"},
                ),
                width="100%", padding_top="8px",
            ),
            search_panel(),
            parcel_card(),
            zones_panel(),
            _layers_panel(),
            width="340px", max_width="340px", min_width="340px",
            height="100%", overflow_y="auto", padding_x="4",
            border_right=BORDER, background="var(--color-panel-solid)",
            align_items="stretch", spacing="0",
            display=["none", "none", "flex", "flex"],
        ),
        rx.box(
            rx.icon_button(
                rx.icon("panel-left-open", size=15),
                on_click=S.toggle_sidebar,
                size="1", variant="soft", color_scheme="gray",
                aria_label=S.tr["sidebar_show_aria"],
            ),
            display=["none", "none", "block", "block"],
            padding="2", border_right=BORDER,
            background="var(--color-panel-solid)", height="100%",
        ),
    )


def _mobile_sheet() -> rx.Component:
    """Below "md": the map's only interaction surface. See the Brazil
    page's own `_mobile_sheet()` for the full design rationale — this is
    the same shape, ported: always mounted, peek/half/full snap points,
    starts at "half"."""
    return rx.vstack(
        _drag_handle(drawer_id="ca-mobile-sheet",
                    handle_id="ca-mobile-sheet-handle", snap=True),
        rx.box(
            search_panel(),
            parcel_card(),
            zones_panel(),
            _layers_panel(),
            results_panel(),
            padding_x="4", overflow_y="auto", flex="1", min_height="0",
        ),
        id="ca-mobile-sheet",
        display=["flex", "flex", "none", "none"],
        flex_direction="column",
        position="absolute", bottom="0", left="0", right="0",
        height="45vh", max_height="45vh",
        background="var(--color-panel-solid)",
        border_top_left_radius="var(--radius-4)",
        border_top_right_radius="var(--radius-4)",
        box_shadow="0 -4px 24px rgba(0, 0, 0, 0.25)",
        z_index="1000",
        overflow="hidden",
        spacing="0",
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
            _drag_handle(drawer_id="ca-results-drawer",
                        handle_id="ca-results-drag-handle", snap=False),
            results_panel(),
            id="ca-results-drawer",
            display=["none", "none", "flex", "flex"],
            position="absolute", bottom="0", left="0", right="0",
            max_height="42vh", overflow_y="auto",
            flex_direction="column",
            z_index="1000",
        ),
        _mobile_sheet(),
        flex="1", height="100%", position="relative",
        on_mount=rx.call_script(_SHEET_SCRIPT),
    )


def canada_index() -> rx.Component:
    return rx.vstack(
        header(),
        rx.hstack(_sidebar(), _map(), width="100%", flex="1", spacing="0",
                 overflow="hidden"),
        width="100vw", height="100vh", spacing="0", overflow="hidden",
    )
