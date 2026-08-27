"""Validação: the ACI checked against NTEMS VLCE2 for the same year.

One swipe divider on the map, a summary stat, and the confusion-matrix table —
see ``canada/services/vlce2.py`` for what this comparison can and cannot say.
"""

from __future__ import annotations

import reflex as rx

from ..config.vlce2 import COMPARABLE_YEARS
from ..state import CanadaState as S
from .export_widgets import table_export_button
from .layout import MUTED, zone_selector


def _matrix_row(r: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(r["aci_label"], size="1")),
        rx.table.cell(rx.text(r["vlce2_label"], size="1")),
        rx.table.cell(rx.text(r["area_ha"], size="1"), text_align="right"),
        rx.table.cell(
            rx.icon(
                rx.cond(r["is_agreement"].to(bool), "check", "x"), size=13,
                color=rx.cond(r["is_agreement"].to(bool), "#1f8d49", "#e5484d"),
            ),
            text_align="center",
        ),
    )


def validacao_tab() -> rx.Component:
    return rx.vstack(
        rx.text(S.tr["validacao_intro"], size="1", color=MUTED),
        zone_selector(),
        rx.hstack(
            rx.text(S.tr["validacao_ano"], size="1", color=MUTED),
            rx.select(
                [str(y) for y in COMPARABLE_YEARS],
                value=S.validation_year.to_string(),
                on_change=S.set_validation_year, size="1",
            ),
            rx.button(
                rx.cond(S.validation_running, S.tr["calculando"],
                       S.tr["calcular"]),
                on_click=S.run_validation, disabled=S.validation_running,
                size="1",
            ),
            width="100%", align="center",
        ),
        rx.cond(
            S.validation_error,
            rx.callout(S.validation_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            S.validation_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(S.tr["calculando"], size="2"), spacing="2"),
                height="200px",
            ),
            rx.cond(
                S.validation_matrix,
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.text(S.tr["validacao_agreement_label"], size="1",
                                   color=MUTED),
                            rx.text(
                                f"{S.validation_summary_for_zone['agreement_pct']}%",
                                size="4", weight="bold", color="#1f8d49",
                            ),
                            spacing="0",
                        ),
                        rx.vstack(
                            rx.text(S.tr["validacao_area_label"], size="1",
                                   color=MUTED),
                            rx.text(
                                f"{S.validation_summary_for_zone['area_ha']} ha",
                                size="4", weight="bold",
                            ),
                            spacing="0",
                        ),
                        spacing="6", width="100%", wrap="wrap",
                    ),
                    rx.hstack(
                        rx.spacer(),
                        table_export_button(S.download_validacao_csv),
                        width="100%",
                    ),
                    rx.table.root(
                        rx.table.header(rx.table.row(
                            rx.table.column_header_cell(S.tr["validacao_col_aci"]),
                            rx.table.column_header_cell(
                                S.tr["validacao_col_vlce2"]),
                            rx.table.column_header_cell(
                                S.tr["validacao_col_area"], text_align="right"),
                            rx.table.column_header_cell(
                                S.tr["validacao_col_agreement"],
                                text_align="center"),
                        )),
                        rx.table.body(rx.foreach(
                            S.validation_matrix_rows, _matrix_row)),
                        size="1", width="100%", variant="surface",
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        rx.callout(S.tr["validacao_no_verdict"], icon="info",
                  color_scheme="gray", size="1"),
        rx.text(S.tr["validacao_group_note"], size="1", color=MUTED),
        rx.text(S.tr["validacao_attribution"], size="1", color=MUTED),
        spacing="3", width="100%", padding="3",
    )
