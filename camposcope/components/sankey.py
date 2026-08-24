"""Transitions: the two-stage and multi-stage Sankey (doc/07-transitions.md).

Both are computed only for the **active zone** (doc/07 §4) and only **on
demand** — unlike the MapBiomas trajectory, which covers every zone in one
call, a Sankey costs one Earth Engine round trip per year pair per zone
(doc/06-ee-layers.md §1), so switching zones or tabs must never silently
re-trigger it.
"""

from __future__ import annotations

import reflex as rx

from ..config import mapbiomas as mb
from ..config.settings import SANKEY_MIN_YEAR_GAP
from ..state import AppState
from .layout import BORDER, MUTED, split_panel


def _year_select(value, on_change, label) -> rx.Component:
    years = [str(y) for y in mb.MAPBIOMAS_YEARS]
    return rx.vstack(
        rx.text(label, size="1", color=MUTED),
        rx.select(years, value=value.to_string(), on_change=on_change, size="1"),
        spacing="1", align_items="start",
    )


def _two_stage_section() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            _year_select(AppState.sankey_year_a,
                        lambda v: AppState.set_sankey_years(v, AppState.sankey_year_b),
                        AppState.tr["transicoes_de"]),
            _year_select(AppState.sankey_year_b,
                        lambda v: AppState.set_sankey_years(AppState.sankey_year_a, v),
                        AppState.tr["transicoes_para"]),
            rx.button(
                rx.cond(AppState.sankey_running, AppState.tr["calculando"],
                       AppState.tr["calcular"]),
                on_click=AppState.run_sankey,
                disabled=AppState.sankey_running,
                size="1",
            ),
            spacing="3", align="start",
        ),
        rx.cond(
            AppState.sankey_error,
            rx.callout(AppState.sankey_error, icon="triangle-alert",
                       color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.sankey_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(AppState.tr["calculando"], size="2"), spacing="2"),
                height="200px",
            ),
            rx.cond(
                AppState.sankey_transitions,
                # The table stays available alongside every Sankey — the
                # figure is for seeing the shape, the table is for making a
                # claim (doc/07-transitions.md §5).
                split_panel(
                    rx.plotly(
                        data=AppState.sankey_figure,
                        config={"displayModeBar": False, "displaylogo": False,
                               "responsive": True},
                        width="100%", height="280px",
                    ),
                    rx.vstack(
                        rx.text(AppState.tr["transicoes_maiores"], size="1",
                               weight="medium", color=MUTED),
                        rx.foreach(
                            AppState.sankey_table_rows[:10],
                            lambda r: rx.hstack(
                                rx.text(f"{r['src']} → {r['tgt']}", size="1"),
                                rx.spacer(),
                                rx.text(f"{r['area_ha']} ha", size="1", weight="bold"),
                                width="100%",
                            ),
                        ),
                        spacing="1", width="100%",
                    ),
                ),
            ),
        ),
        spacing="2", width="100%",
    )


def transitions_tab() -> rx.Component:
    return rx.vstack(
        rx.text(AppState.tr["transicoes_intro"], size="1", color=MUTED),
        rx.box(_two_stage_section(), width="100%"),
        rx.text(
            f"{AppState.tr['transicoes_min_gap_note_prefix']} "
            f"{SANKEY_MIN_YEAR_GAP} "
            f"{AppState.tr['transicoes_min_gap_note_suffix']}",
            size="1", color=MUTED,
        ),
        spacing="3", width="100%", padding="3",
    )
