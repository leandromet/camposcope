"""Per-chart and per-table export icons — the Canada page's copy of
:mod:`camposcope.components.export_widgets`.

Identical in mechanism (Plotly's own client-side ``downloadImage`` against the
chart's DOM node, a plain CSV of whatever records are already on screen) and
duplicated rather than imported for one reason: the Brazil version reads its
button labels off ``AppState.tr``, and importing it here would pull in the
Brazil state root to build a Canada component. See ``camposcope/components/
export_widgets.py`` for the full reasoning behind the PNG-export mechanism
itself, which is unchanged.
"""

from __future__ import annotations

import reflex as rx

PLOTLY_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}


def chart_export_button(wrap_id: str, filename: str) -> rx.Component:
    from ..state import CanadaState as S

    return rx.tooltip(
        rx.icon_button(
            rx.icon("image-down"),
            on_click=rx.call_script(
                "(function(){"
                f"var gd = document.querySelector('#{wrap_id} .js-plotly-plot');"
                "if (gd && window.Plotly) { window.Plotly.downloadImage(gd, "
                f"{{format: 'png', filename: '{filename}', scale: 2}}); }}"
                "})()"
            ),
            size="2", variant="ghost", color_scheme="gray",
            aria_label=S.tr["export_chart_aria"],
        ),
        content=S.tr["export_chart_label"],
    )


def table_export_button(on_click) -> rx.Component:
    from ..state import CanadaState as S

    return rx.tooltip(
        rx.icon_button(
            rx.icon("download"),
            on_click=on_click,
            size="2", variant="ghost", color_scheme="gray",
            aria_label=S.tr["export_table_aria"],
        ),
        content=S.tr["export_table_label"],
    )


def chart_box(figure, wrap_id: str, filename: str, height, width: str = "100%",
             **box_props) -> rx.Component:
    # See the Brazil page's own `components/export_widgets.py::chart_box`
    # for the full rationale — including why the scroll wrapper needs its
    # OWN explicit `height=height`, not just `overflow_x="auto"` on the
    # outer (content-sized) box: per the CSS Overflow spec, one non-visible
    # overflow axis forces the other to `auto` too, and an auto-height box
    # that's also an auto-overflow container just grows to fit instead of
    # clipping — which is what made every chart render far taller than
    # intended once the tick-rotation fix reserved more margin.
    return rx.box(
        rx.box(
            rx.plotly(data=figure, config=PLOTLY_CONFIG, width="100%",
                     height=height),
            height=height,
            overflow_x="auto",
            style={"WebkitOverflowScrolling": "touch", "touchAction": "pan-x"},
        ),
        rx.hstack(
            rx.spacer(),
            chart_export_button(wrap_id, filename),
            width="100%", padding_top="0.15rem",
        ),
        id=wrap_id, width=width,
        **box_props,
    )
