"""The map + analysis workspace for the Canada page. One page, mirroring the
Brazil page's own v1 shape."""

from __future__ import annotations

import reflex as rx

from ...components.map.leaflet_map import leaflet_map
from ..components.layout import ACCENT, BORDER, _info_icon, header
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
  var drawerEl = null, snapMode = 'free', movedFar = false;
  // See the Brazil page's own `_SHEET_SCRIPT` for the full rationale: real
  // device touch reported dragging not working reliably on a phone even
  // though it worked fine with a mouse in a desktop emulator, so a plain
  // tap (no meaningful pointer movement) is now the primary way to toggle
  // the mobile sheet between 30%/70% — see `tapTarget()`/`end()` below.
  // The desktop results drawer (`snapMode === 'free'`) is untouched.
  var TAP_SLOP_PX = 6;

  function snapPoints() {
    return [80, window.innerHeight * 0.45, window.innerHeight * 0.75];
  }

  function tapTarget(height) {
    var lo = window.innerHeight * 0.30, hi = window.innerHeight * 0.70;
    return height > (lo + hi) / 2 ? lo : hi;
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
    updateTab(el);
  }

  // The mobile sheet's handle is a coloured tab with a chevron, not the
  // plain bar the desktop drawer keeps — see _drag_handle()'s snap=True
  // branch. The chevron flips to point the way dragging would go.
  function updateTab(el) {
    var tab = el.querySelector && el.querySelector('[data-sheet-tab]');
    if (!tab) return;
    var chevron = tab.querySelector('[data-chevron]');
    if (!chevron) return;
    chevron.style.transform = el.offsetHeight > 160 ? 'rotate(180deg)' : 'rotate(0deg)';
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
    movedFar = false;
    pointerId = e.pointerId;
    startY = e.clientY;
    startHeight = drawerEl.offsetHeight;
    try { handle.setPointerCapture(e.pointerId); } catch (err) { /* older browsers */ }
    document.body.style.userSelect = 'none';
  });

  document.addEventListener('pointermove', function (e) {
    if (!dragging || e.pointerId !== pointerId || !drawerEl) return;
    var delta = startY - e.clientY;
    if (Math.abs(delta) > TAP_SLOP_PX) movedFar = true;
    var next = Math.min(window.innerHeight * 0.75, Math.max(80, startHeight + delta));
    drawerEl.style.height = next + 'px';
    drawerEl.style.maxHeight = next + 'px';
    updateTab(drawerEl);
  });

  function end(e) {
    if (!dragging || e.pointerId !== pointerId || !drawerEl) return;
    dragging = false;
    document.body.style.userSelect = '';
    if (snapMode === 'snap') {
      settle(drawerEl, movedFar
        ? nearest(drawerEl.offsetHeight, snapPoints())
        : tapTarget(startHeight));
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

  var initial = document.getElementById('ca-mobile-sheet');
  if (initial) updateTab(initial);
})();
"""


def _drag_handle(*, drawer_id: str, handle_id: str, snap: bool) -> rx.Component:
    """See ``camposcope/pages/index.py::_drag_handle`` for the full
    rationale — ported verbatim: a coloured, chevron-bearing tab for the
    mobile sheet (``snap=True``), the original plain bar for the desktop
    drawer's free-drag feel (``snap=False``)."""
    if snap:
        handle_content = rx.box(
            rx.icon("chevron-up", size=16, color="white",
                   custom_attrs={"data-chevron": "1"},
                   style={"transition": "transform 200ms ease"}),
            custom_attrs={"data-sheet-tab": "1"},
            display="flex", align_items="center", justify_content="center",
            width="56px", height="22px",
            background=f"var(--{ACCENT}-9)",
            border_radius="11px",
            box_shadow="0 2px 6px rgba(0, 0, 0, 0.3)",
        )
    else:
        handle_content = rx.box(width="36px", height="4px", border_radius="2px",
                                background="var(--gray-6)")
    return rx.box(
        handle_content,
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
        width="100%", height="30px" if snap else "14px",
        cursor="ns-resize", flex_shrink="0", padding_top="4px" if snap else "0",
        _hover={} if snap else {"background": "var(--gray-3)"},
        _focus_visible={"background": "var(--gray-4)",
                        "box_shadow": "inset 0 0 0 2px var(--accent-8)"},
    )


def _start_hint() -> rx.Component:
    """A first-visit nudge over the empty map — see the Brazil page's own
    ``pages/index.py::_start_hint`` for the full rationale. Gone the instant
    anything is selected (``S.has_parcel`` — a real parcel, a protected
    area, or the 500 ha fallback square, see ``state/_parcel.py``)."""
    return rx.cond(
        ~S.has_parcel,
        rx.box(
            rx.text(S.tr["start_hint"], size="2", weight="medium",
                    color="white"),
            position="absolute", top="16px", left="50%",
            transform="translateX(-50%)",
            background=f"var(--{ACCENT}-9)", padding="8px 16px",
            border_radius="var(--radius-4)",
            box_shadow="0 2px 8px rgba(0,0,0,.25)",
            z_index="950",
            pointer_events="none",
            white_space="nowrap",
        ),
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
            _info_icon(S.tr["layers_parcel_wms_note"]),
            spacing="2", align="center",
        ),
        rx.hstack(
            rx.switch(checked=S.show_ecozones, on_change=S.toggle_ecozones,
                     size="1"),
            rx.text(S.tr["layers_ecozones"], size="1"),
            _info_icon(S.tr["layers_ecozones_note"]),
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
    )


#: Desktop ("md" and up) only, now — the mobile drawer is `_mobile_sheet()`.
#: See the Brazil page's own `_sidebar()` for the full rationale; this is
#: the same shape, ported. `id="ca-desktop-sidebar"` on both branches below
#: is read by the same `max-height`/`orientation: landscape` override in
#: camposcope.py's head style that covers the Brazil page's sidebar — a
#: landscape phone routinely exceeds the "md" 768px width cutoff these
#: `display=[...]` breakpoints use, on a viewport with nowhere near
#: desktop's usual height to spare.
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
            id="ca-desktop-sidebar",
        ),
        # A coloured tab, not a small grey icon_button — see
        # camposcope/pages/index.py's own version of this fix.
        rx.box(
            rx.box(
                rx.icon("chevron-right", size=18, color="white"),
                on_click=S.toggle_sidebar,
                role="button", cursor="pointer",
                aria_label=S.tr["sidebar_show_aria"],
                display="flex", align_items="center", justify_content="center",
                width="28px", height="56px",
                background=f"var(--{ACCENT}-9)",
                border_radius="0 8px 8px 0",
                box_shadow="2px 0 6px rgba(0, 0, 0, 0.2)",
                _hover={"background": f"var(--{ACCENT}-10)"},
            ),
            display=["none", "none", "flex", "flex"],
            align_items="center",
            padding="2", border_right=BORDER,
            background="var(--color-panel-solid)", height="100%",
            id="ca-desktop-sidebar",
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
            # See the Brazil page's own `_mobile_sheet()` for the full
            # rationale — same fix: search/parcel-card/zones/layers all
            # collapse behind one accordion so reaching the results tabs on
            # a phone doesn't mean scrolling past the whole stack first.
            # Open by default, so nothing changes for a first visit.
            rx.accordion.root(
                rx.accordion.item(
                    rx.accordion.header(
                        rx.accordion.trigger(
                            rx.hstack(
                                rx.icon("sliders-horizontal", size=13),
                                rx.text(S.tr["mobile_options_toggle"],
                                       size="1", weight="medium"),
                                spacing="2", align="center",
                            ),
                        ),
                    ),
                    rx.accordion.content(
                        rx.vstack(
                            search_panel(),
                            parcel_card(),
                            zones_panel(),
                            _layers_panel(),
                            spacing="2", width="100%",
                        ),
                        # See the Brazil page's own `pages/index.py::
                        # _mobile_sheet` for why this needs `padding_x="0"`.
                        padding_x="0",
                    ),
                    value="options",
                ),
                type="single", collapsible=True, variant="ghost", width="100%",
                # `default_value`, not `value` — see the Brazil page's own
                # `pages/index.py::_mobile_sheet` for why `value` here would
                # make this accordion controlled-but-never-updated.
                default_value="options",
            ),
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
        _start_hint(),
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
