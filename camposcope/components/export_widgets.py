"""Per-chart and per-table export icons — the "instead of a screenshot" pair.

Ported in structure from Naturametrics' ``components/results.py`` (the same
helpers, made public here since Camposcope spreads its charts and tables
across four files — ``results.py``, ``fogo.py``, ``sankey.py``,
``validacao.py`` — rather than one).

**Why not Plotly's own modebar.** Every ``rx.plotly`` call in this app sets
``displayModeBar: False`` — the modebar has no "away" state on touch (no
mouse, no hover-to-reveal), so it would sit permanently on top of the plot on
a phone. A plain icon placed *below* the plot, not layered on it, avoids that
regression entirely.

**How the PNG export works.** ``Plotly.downloadImage`` runs entirely client-
side (no kaleido/headless-browser dependency, no server round-trip) against
the plot's own DOM node. It needs that node, and a ``divId`` prop threaded
through ``rx.plotly`` did not reach it reliably in testing — so this targets
Plotly's own ``.js-plotly-plot`` class (which Plotly.js always stamps onto
the graph div it creates; its own modebar button finds "self" the same way)
inside a plain HTML ``id`` on the wrapping box, which has no such prop-
plumbing to go wrong.
"""

from __future__ import annotations

import reflex as rx

#: Standard chart config across the app: no Plotly modebar — see module
#: docstring for why.
PLOTLY_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}


def chart_export_button(wrap_id: str, filename: str) -> rx.Component:
    """A small "download this chart" icon-button with a hover tooltip."""
    from ..state import AppState

    return rx.tooltip(
        rx.icon_button(
            # IconButton.create (reflex/components/radix/themes/components/
            # icon_button.py) unconditionally overwrites its child icon's
            # size from the button's own `size` token, so no size= here —
            # size="2" below is what actually renders (24px).
            rx.icon("image-down"),
            on_click=rx.call_script(
                "(function(){"
                f"var gd = document.querySelector('#{wrap_id} .js-plotly-plot');"
                "if (gd && window.Plotly) { window.Plotly.downloadImage(gd, "
                f"{{format: 'png', filename: '{filename}', scale: 2}}); }}"
                "})()"
            ),
            size="2", variant="ghost", color_scheme="gray",
            aria_label=AppState.tr["export_chart_aria"],
        ),
        content=AppState.tr["export_chart_label"],
    )


def table_export_button(on_click) -> rx.Component:
    """The table counterpart of :func:`chart_export_button` — a plain CSV of
    the records already on screen, for a paper's own reprocessing rather than
    a screenshot."""
    from ..state import AppState

    return rx.tooltip(
        rx.icon_button(
            rx.icon("download"),
            on_click=on_click,
            size="2", variant="ghost", color_scheme="gray",
            aria_label=AppState.tr["export_table_aria"],
        ),
        content=AppState.tr["export_table_label"],
    )


def chart_box(figure, wrap_id: str, filename: str, height, width: str = "100%",
             **box_props) -> rx.Component:
    """A Plotly chart plus its own export icon, in a slim row *below* the
    plot rather than overlapping it (see module docstring)."""
    return rx.box(
        rx.plotly(data=figure, config=PLOTLY_CONFIG, width="100%", height=height),
        rx.hstack(
            rx.spacer(),
            chart_export_button(wrap_id, filename),
            width="100%", padding_top="0.15rem",
        ),
        id=wrap_id, width=width,
        **box_props,
    )
