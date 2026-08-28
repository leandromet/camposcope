"""The map + analysis workspace. v1 is one page (doc/08-ui-ux.md §1)."""

from __future__ import annotations

import reflex as rx

from ..components.cadastro import cadastral_card, zones_panel
from ..components.layout import ACCENT, BORDER, MUTED, header, section
from ..components.map.leaflet_map import leaflet_map
from ..components.map_legend import map_legend
from ..components.results import results_panel
from ..components.search import municipio_browser, search_panel
from ..config.datasets import ALL_BASEMAPS
from ..state import AppState

#: Drag-to-resize, shared by the desktop results drawer and the mobile
#: bottom sheet. Deliberately pure client-side DOM manipulation, not a
#: Python event per pixel of pointer movement — a state round trip over the
#: WebSocket for every `pointermove` would be visibly laggy, and the dragged
#: height is a per-viewer convenience, not data anything else needs to know
#: about.
#:
#: **Pointer Events, not mouse events.** The original version listened for
#: `mousedown`/`mousemove`/`mouseup` only, which meant the drag handle simply
#: did not respond to touch at all — confirmed live on a phone-sized
#: viewport via CDP. Pointer Events unify mouse/touch/pen behind one API and
#: support `setPointerCapture`, which a fast finger-drag actually needs:
#: without it, intermediate `pointermove` events can land on whatever
#: element the finger is currently over rather than staying with the handle.
#:
#: **Event DELEGATION on `document`**, not a direct listener on the handle
#: element. The first version attached listeners to the specific handle DOM
#: node via a MutationObserver, which broke: the drawer this handle belongs
#: to is conditionally rendered, so React tears down and recreates that node
#: on state changes far more often than expected, silently orphaning the
#: listeners each time. Delegating to `document` and looking the handle up
#: by ID *inside* the event callback means there is nothing to re-attach —
#: whichever node currently has that ID is found fresh on every event.
#:
#: **One script, two drawers, one behavioural difference.** Which drawer a
#: drag targets, and whether it snaps on release, is read from the handle's
#: own `data-drawer-handle`/`data-snap` attributes rather than hard-coded
#: here — see `_drag_handle()`. The desktop results drawer keeps its
#: original free-drag feel (`data-snap="free"`, unchanged behaviour, just
#: touch-capable now as a side effect of sharing this script). Only the
#: mobile sheet (`data-snap="snap"`) gets the new three-stop snap points —
#: desktop is deliberately not changed by this redesign.
_SHEET_SCRIPT = """
(function () {
  if (window._csSheetInit) return;
  window._csSheetInit = true;

  var dragging = false, pointerId = null, startY = 0, startHeight = 0;
  var drawerEl = null, snapMode = 'free';

  function snapPoints() {
    // peek / half / full — see components/layout.py's docstring for why
    // these three and not a free-form height on the mobile sheet.
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
    updateTab(el);
  }

  // The mobile sheet's handle is a coloured tab with a chevron, not the
  // plain bar the desktop drawer keeps — see _drag_handle()'s snap=True
  // branch. The chevron flips to point the way dragging would go: up while
  // still closer to peek ("drag up for more"), down once past it ("drag
  // down to collapse"). 160px sits well below every snap point but peek,
  // so it flips early rather than only right at the very top.
  function updateTab(el) {
    var tab = el.querySelector && el.querySelector('[data-sheet-tab]');
    if (!tab) return;
    var chevron = tab.querySelector('[data-chevron]');
    if (!chevron) return;
    chevron.style.transform = el.offsetHeight > 160 ? 'rotate(180deg)' : 'rotate(0deg)';
  }

  // Exposed so a Python event (selecting a property) can ask the sheet to
  // expand without needing to know anything about drag state — see
  // components/results.py's use of this from AppState. Snap-only: calling
  // it on the free-drag desktop drawer would be a behaviour change desktop
  // was never asked for, so it is a no-op there.
  window.__csSheetSnapTo = function (name) {
    var el = document.getElementById('mobile-sheet');
    if (!el) return;
    var pts = snapPoints();
    var target = name === 'full' ? pts[2] : name === 'peek' ? pts[0] : pts[1];
    // Never collapses an already-more-open sheet — a fresh selection should
    // reveal its own results, not interrupt someone already reading a
    // wider sheet by snapping it smaller.
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
    // Capped at 3/4 of the viewport, not more: past that the map itself
    // stops being useful as a map, and the whole point of a drawer/sheet
    // (over a separate results page) is that the map stays visible
    // alongside it.
    var next = Math.min(window.innerHeight * 0.75, Math.max(80, startHeight + delta));
    // height, not just maxHeight: neither drawer has an explicit height of
    // its own (only a maxHeight it starts with), so it sizes to its
    // *content* — a short tab's content stops growing well under the cap,
    // and the handle stops tracking the pointer right there, which reads
    // as "hit a limit" even though maxHeight is nowhere near it yet.
    // Setting height forces the box itself to the dragged size regardless
    // of how much content is in it.
    drawerEl.style.height = next + 'px';
    drawerEl.style.maxHeight = next + 'px';
    updateTab(drawerEl);
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

  // Keyboard access, mobile sheet only (its handle is the one focusable
  // element and the one carrying data-snap="snap") — Up/Down step directly
  // between the three stops rather than pixel-by-pixel, which is the
  // natural keyboard mapping for a 3-stop control and reuses the same
  // nearest()/settle() the pointer path already has.
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

  // Match the chevron to the sheet's own starting height (it opens at
  // "half", not "peek" — see _mobile_sheet()'s own docstring) rather than
  // waiting for the first drag to set it correctly.
  var initial = document.getElementById('mobile-sheet');
  if (initial) updateTab(initial);
})();
"""


def _drag_handle(*, drawer_id: str, handle_id: str, snap: bool) -> rx.Component:
    """A drag target for `_SHEET_SCRIPT`. ``snap=True`` marks the mobile
    sheet's own handle: it gets the keyboard-slider treatment, the script's
    three-stop snap behaviour, and — unlike a plain grey bar, which turned
    out not to read as an interactive control at all — a solid,
    accent-coloured tab with a chevron that flips to show which way
    dragging goes (``_SHEET_SCRIPT``'s ``updateTab()``). It is now the
    sheet's only "open" affordance, replacing what used to be a separate
    header/FAB button. ``snap=False`` (the desktop results drawer) keeps
    the original plain-bar free-drag feel — same script, deliberately
    different data attribute, see the script's own docstring."""
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
        aria_label=AppState.tr["sheet_handle_aria"] if snap else None,
        outline="none",
        display="flex", justify_content="center", align_items="center",
        width="100%", height="30px" if snap else "14px",
        cursor="ns-resize", flex_shrink="0", padding_top="4px" if snap else "0",
        _hover={} if snap else {"background": "var(--gray-3)"},
        _focus_visible={"background": "var(--gray-4)",
                        "box_shadow": "inset 0 0 0 2px var(--accent-8)"},
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


#: Desktop ("md" and up) only, now — the mobile drawer is `_mobile_sheet()`,
#: always mounted with its own drag-to-collapse rather than an open/close
#: toggle. Desktop keeps exactly the original collapsible in-flow panel:
#: an open 340px panel, or a slim always-visible rail when collapsed.
def _sidebar() -> rx.Component:
    return rx.cond(
        AppState.sidebar_open,
        rx.vstack(
            rx.hstack(
                rx.spacer(),
                rx.box(
                    rx.icon("panel-left-close", size=18),
                    on_click=AppState.toggle_sidebar,
                    role="button", cursor="pointer",
                    aria_label=AppState.tr["sidebar_hide_aria"],
                    display="flex", align_items="center",
                    justify_content="center",
                    width="28px", height="28px",
                    border_radius="var(--radius-2)",
                    _hover={"background": "var(--gray-4)"},
                ),
                width="100%", padding_top="8px",
            ),
            search_panel(),
            cadastral_card(),
            municipio_browser(),
            zones_panel(),
            _layers_panel(),
            width="340px", max_width="340px", min_width="340px",
            height="100%", overflow_y="auto", padding_x="4",
            border_right=BORDER, background="var(--color-panel-solid)",
            align_items="stretch", spacing="0",
            display=["none", "none", "flex", "flex"],
        ),
        # A coloured tab, not the small grey icon_button this used to be —
        # measured against the same complaint the mobile sheet's old plain
        # handle bar got: a tiny, gray, icon-only control in a thin rail
        # doesn't read as "click here," especially collapsed to its
        # smallest state. Same visual language as the mobile sheet's own
        # tab (_drag_handle()'s snap=True branch) for consistency.
        rx.box(
            rx.box(
                rx.icon("chevron-right", size=18, color="white"),
                on_click=AppState.toggle_sidebar,
                role="button", cursor="pointer",
                aria_label=AppState.tr["sidebar_show_aria"],
                display="flex", align_items="center", justify_content="center",
                width="28px", height="56px",
                background=f"var(--{ACCENT}-9)",
                border_radius="0 8px 8px 0",
                box_shadow="2px 0 6px rgba(0, 0, 0, 0.2)",
                _hover={"background": f"var(--{ACCENT}-10)"},
            ),
            display=["none", "none", "flex", "flex"],
            align_items="center",
            padding="2",
            border_right=BORDER,
            background="var(--color-panel-solid)",
            height="100%",
        ),
    )


def _mobile_sheet() -> rx.Component:
    """Below "md": the map's *only* interaction surface — one draggable
    bottom sheet replacing both the old full-screen sidebar overlay and the
    separate results drawer.

    **Always mounted, never "closed".** The old mobile sidebar was either a
    full-screen overlay or entirely absent (replaced by a floating
    reopen button) — two DOM states to keep in sync, and the moment it was
    "closed" every one of search/results/layers was unreachable except via
    that one small button. Here, "closed" is just the sheet's own peek snap
    point (80px: handle plus a sliver of the search bar) — always there,
    always draggable open, no separate affordance to find first.

    **Starts at "half"** (see `_SHEET_SCRIPT`'s `snapPoints()`), not peek —
    matching this app's own convention that the way in should be visible on
    load, not hidden a gesture away (the Canada page's `sidebar_open`
    default is the same call).
    """
    return rx.vstack(
        _drag_handle(drawer_id="mobile-sheet", handle_id="mobile-sheet-handle",
                    snap=True),
        rx.box(
            search_panel(),
            cadastral_card(),
            municipio_browser(),
            zones_panel(),
            _layers_panel(),
            results_panel(),
            padding_x="4", overflow_y="auto", flex="1", min_height="0",
        ),
        id="mobile-sheet",
        display=["flex", "flex", "none", "none"],
        flex_direction="column",
        position="absolute", bottom="0", left="0", right="0",
        height="45vh", max_height="45vh",
        background="var(--color-panel-solid)",
        border_top_left_radius="var(--radius-4)",
        border_top_right_radius="var(--radius-4)",
        box_shadow="0 -4px 24px rgba(0, 0, 0, 0.25)",
        # Above the map's own panes (~700) and the legend (900) for the same
        # reason the old results-drawer sat at 1000 — this sheet now covers
        # that drawer's job too, so it takes over its z-index.
        z_index="1000",
        overflow="hidden",
        spacing="0",
    )


def _map() -> rx.Component:
    """The map, filling its box. Two overlays sit on top of it rather than
    sharing flex space with it: the desktop-only results drawer (unchanged
    position/behaviour from before this redesign) and the mobile-only
    unified sheet (`_mobile_sheet()`) — exactly one of the two is ever
    mounted at a given breakpoint. Kept as a single box with exactly the
    props Leaflet has always been given here — ``flex="1", height="100%",
    position="relative"`` — so the map's own layout is never at the mercy of
    a sibling's height.

    Neither overlay resizes the map's own container: both are
    ``position: absolute`` over it, so Leaflet's container never actually
    changes size when a drawer/sheet is dragged, only how much of it is
    visually covered — there is nothing here for `invalidateSize()` to fix
    (checked directly: dragging never changes `leaflet_map`'s own box
    dimensions). That gap is real on naturametrics, whose mobile map
    currently lives in a flex-sized box that *does* change size — out of
    scope for this pass.
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
            _drag_handle(drawer_id="results-drawer",
                        handle_id="results-drag-handle", snap=False),
            results_panel(),
            id="results-drawer",
            display=["none", "none", "flex", "flex"],
            position="absolute",
            bottom="0",
            left="0",
            right="0",
            max_height="42vh",
            overflow_y="auto",
            flex_direction="column",
            # Leaflet's own panes (tile/overlay/marker/popup) use z-index up to
            # ~700 internally; anything lower than that sits UNDER the map and
            # is invisible except for whatever sliver Leaflet doesn't paint —
            # exactly the bug this value fixes. The legend sits at 900, so the
            # drawer stays above it too.
            z_index="1000",
        ),
        _mobile_sheet(),
        flex="1",
        height="100%",
        position="relative",
        # NOT rx.script(_SHEET_SCRIPT) as a child — that compiles to a plain
        # <script> body nested inside react-helmet's <Helmet>, and neither
        # React's own commit (scripts inserted as JSX children are set via
        # innerHTML, which browsers refuse to execute) nor Helmet's here ever
        # actually ran it: confirmed live via headless Chromium + CDP,
        # window._csResizeInit stayed false and a simulated drag never moved
        # the drawer. on_mount=rx.call_script(...) fires through Reflex's own
        # event pipeline instead — the same mechanism already proven to work
        # for the per-chart PNG export buttons (components/export_widgets.py)
        # — so the browser actually executes it once this box mounts.
        on_mount=rx.call_script(_SHEET_SCRIPT),
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
