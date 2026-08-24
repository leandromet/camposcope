"""Validação: check a classification against reference data
(doc/03-roadmap.md Phase 5 addendum, "like naturametrics").

Two pairings, one swipe divider each — the map does the comparing, this tab
carries the mode switch and, for the IBGE pairing, the numbers behind it.
SPOT is imagery: there is nothing to tabulate, only to look at
(doc/12-spot-2008.md).
"""

from __future__ import annotations

import reflex as rx

from ..config import ibge_vegetation as iv
from ..state import AppState
from .layout import MUTED, zone_selector


def _mode_switch() -> rx.Component:
    return rx.segmented_control.root(
        rx.segmented_control.item("SPOT × MapBiomas 2008", value="spot_2008"),
        rx.segmented_control.item("IBGE × MapBiomas 2022", value="ibge_2022"),
        value=AppState.validacao_mode,
        on_change=AppState.set_validacao_mode,
        size="1", width="100%",
    )


def _spot_band_switch() -> rx.Component:
    """Visual (true colour) vs. analytic (false-colour NIR) — the same two
    SPOT 2008 mosaics offered as basemap choices, here as the comparison's
    left-hand layer instead. NIR-in-red is what makes 2008 vegetation
    legible against pasture at a glance (doc/04-data-sources.md §6)."""
    return rx.vstack(
        rx.text("Mosaico SPOT", size="1", color=MUTED),
        rx.segmented_control.root(
            rx.segmented_control.item("Visual", value="visual"),
            rx.segmented_control.item("Falsa-cor (NIR)", value="analytic"),
            value=AppState.spot_band_mode,
            on_change=AppState.set_spot_band_mode,
            size="1", width="100%",
        ),
        spacing="1", width="100%",
    )


def _spot_note() -> rx.Component:
    return rx.vstack(
        rx.text(
            "Imagens SPOT de aproximadamente 2008 ao lado da classificação "
            "MapBiomas para o mesmo ano — a referência visual mais próxima "
            "da data de corte do Código Florestal (22/07/2008).",
            size="1", color=MUTED,
        ),
        _spot_band_switch(),
        rx.text(
            "Não classifica área consolidada nem avalia regularidade.",
            size="1", color=MUTED,
        ),
        spacing="2", width="100%",
    )


def _matrix_table() -> rx.Component:
    """The 6×6 group matrix — every non-zero cell as a row, since a literal
    grid at this width would be unreadable rather than merely dense."""
    groups = iv.GROUP_ORDER
    labels = iv.GROUP_LABELS_PT
    return rx.vstack(
        rx.hstack(
            rx.vstack(
                rx.text("Floresta", size="1", color=MUTED),
                rx.hstack(
                    rx.text(f"IBGE {AppState.validacao_matrix['forest_ibge']}%",
                           size="2", weight="bold"),
                    rx.text("·", color=MUTED),
                    rx.text(f"MapBiomas {AppState.validacao_matrix['forest_mb']}%",
                           size="2", weight="bold"),
                    spacing="1",
                ),
                spacing="0",
            ),
            rx.vstack(
                rx.text("Natural", size="1", color=MUTED),
                rx.hstack(
                    rx.text(f"IBGE {AppState.validacao_matrix['natural_ibge']}%",
                           size="2", weight="bold"),
                    rx.text("·", color=MUTED),
                    rx.text(f"MapBiomas {AppState.validacao_matrix['natural_mb']}%",
                           size="2", weight="bold"),
                    spacing="1",
                ),
                spacing="0",
            ),
            spacing="6", width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("IBGE (esquerda)"),
                    rx.table.column_header_cell("MapBiomas (direita)"),
                    rx.table.column_header_cell("%", text_align="right"),
                ),
            ),
            rx.table.body(
                # GROUP_ORDER is a fixed, small (7-element) build-time constant,
                # not reactive state — a plain Python double loop unrolls the
                # 49 candidate rows once, at compile time, each individually
                # guarded by rx.cond. Nesting rx.foreach over this same list
                # was tried first and fails to compile: Reflex cannot infer a
                # concrete type for a value indexed by ANOTHER foreach's loop
                # variable (`matrix[g_ibge]` — `g_ibge` is a Var with no
                # static type), which a plain string key at build time
                # sidesteps entirely.
                *[
                    rx.cond(
                        AppState.validacao_matrix["matrix"].to(dict)[g_ibge]
                        .to(dict)[g_mb].to(float) > 0,
                        rx.table.row(
                            rx.table.cell(rx.text(labels[g_ibge], size="1")),
                            rx.table.cell(rx.text(labels[g_mb], size="1")),
                            rx.table.cell(
                                rx.text(
                                    AppState.validacao_matrix["matrix"].to(dict)[g_ibge]
                                    .to(dict)[g_mb].to(float).to_string(),
                                    size="1",
                                ),
                                text_align="right",
                            ),
                        ),
                    )
                    for g_ibge in groups
                    for g_mb in groups
                ],
            ),
            size="1", width="100%", variant="surface",
        ),
        spacing="3", width="100%",
    )


def _ibge_section() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                "IBGE Vegetação (1:250.000, 2022) contra a classificação "
                "MapBiomas do mesmo ano, reduzidas a uma taxonomia comum de "
                "6 grupos — os dois mapas não compartilham classes.",
                size="1", color=MUTED,
            ),
            rx.spacer(),
            rx.button(
                rx.cond(AppState.validacao_running, "Calculando…", "Calcular"),
                on_click=AppState.run_validacao,
                disabled=AppState.validacao_running,
                size="1",
            ),
            width="100%", align="start",
        ),
        rx.cond(
            AppState.validacao_error,
            rx.callout(AppState.validacao_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.validacao_running,
            rx.center(
                rx.hstack(rx.spinner(), rx.text("Calculando…", size="2"),
                         spacing="2"),
                height="150px",
            ),
            rx.cond(AppState.validacao_matrix, _matrix_table()),
        ),
        rx.text(
            "'Vegetação Secundária' do IBGE não tem equivalente direto no "
            "MapBiomas por definição; a tabela mostra o que o MapBiomas lê "
            "hoje nesses polígonos.",
            size="1", color=MUTED,
        ),
        spacing="3", width="100%",
    )


def validacao_tab() -> rx.Component:
    return rx.vstack(
        zone_selector(),
        _mode_switch(),
        rx.cond(
            AppState.validacao_mode == "spot_2008",
            _spot_note(),
            _ibge_section(),
        ),
        rx.text(
            "IBGE — Mapa de Vegetação do Brasil 1:250.000 (2022) · "
            "Google Brazil Forest Imagery Dataset 2008.",
            size="1", color=MUTED,
        ),
        spacing="3", width="100%", padding="3",
    )
