"""Fogo (Fire): MapBiomas Fire analysis showing fire history, frequency, and last fire year."""

from __future__ import annotations

import reflex as rx

from ..state import AppState
from .export_widgets import chart_box, table_export_button
from .layout import MUTED, zone_selector


def _fire_stats() -> rx.Component:
    """Display key fire statistics in colored stat boxes."""
    return rx.cond(
        AppState.fire_table_rows,
        rx.hstack(
            rx.vstack(
                rx.text(AppState.tr["fogo_historio_anos"], size="1", color=MUTED),
                rx.text(
                    rx.cond(
                        AppState.fire_table_rows,
                        rx.cond(
                            AppState.fire_table_rows[0]["fire_history_pct"],
                            f"{AppState.fire_table_rows[0]['fire_history_pct']:.1f}%",
                            "—",
                        ),
                        "—",
                    ),
                    size="3",
                    weight="bold",
                    color="#d4271e",
                ),
                spacing="0",
            ),
            rx.vstack(
                rx.text(AppState.tr["fogo_frequencia_ocorrencias"], size="1", color=MUTED),
                rx.text(
                    rx.cond(
                        AppState.fire_table_rows,
                        AppState.fire_table_rows[0]["fire_frequency"],
                        "—",
                    ),
                    size="3",
                    weight="bold",
                    color="#d4271e",
                ),
                spacing="0",
            ),
            rx.vstack(
                rx.text(AppState.tr["fogo_ultima_queimada"], size="1", color=MUTED),
                rx.text(
                    rx.cond(
                        AppState.fire_table_rows,
                        AppState.fire_table_rows[0]["fire_last_year"],
                        "—",
                    ),
                    size="3",
                    weight="bold",
                    color="#8b1a1a",
                ),
                spacing="0",
            ),
            spacing="5",
            width="100%",
            wrap="wrap",
        ),
    )


def fogo_tab() -> rx.Component:
    return rx.vstack(
        zone_selector(),
        rx.hstack(
            rx.button(
                rx.cond(AppState.fire_running, AppState.tr["calculando"],
                       AppState.tr["calcular"]),
                on_click=AppState.run_fire,
                disabled=AppState.fire_running,
                size="1",
            ),
            width="100%", align="start",
        ),
        rx.cond(
            AppState.fire_error,
            rx.callout(AppState.fire_error, icon="triangle-alert",
                       color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.fire_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(AppState.tr["calculando"], size="2"),
                         spacing="2"),
                height="200px",
            ),
            rx.cond(
                AppState.fire_rows,
                rx.vstack(
                    rx.hstack(
                        rx.spacer(),
                        rx.cond(
                            AppState.fire_table_rows,
                            table_export_button(AppState.download_fogo_csv),
                            rx.fragment(),
                        ),
                        width="100%",
                    ),
                    _fire_stats(),
                    chart_box(AppState.fire_figure, "cs-plot-fogo",
                             "camposcope_fogo", "260px"),
                    spacing="3", width="100%",
                ),
            ),
        ),
        rx.text(AppState.tr["fogo_attribution"], size="1", color=MUTED, padding_bottom="2px"),
        spacing="3", width="100%", padding="3",
    )
