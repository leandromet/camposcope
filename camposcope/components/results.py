"""Results: the zone selector and the four analysis tabs (doc/08-ui-ux.md §5).

Every tab uses the same shape — a smaller chart beside a data table
(``layout.split_panel``) rather than one full-width chart, so the numbers
behind a figure are always visible, not hidden behind a hover tooltip.
"""

from __future__ import annotations

import reflex as rx

from ..config import mapbiomas as mb
from ..config.datasets import AGB_YEARS
from ..state import AppState
from .layout import BORDER, MUTED, split_panel, zone_selector
from .sankey import transitions_tab
from .validacao import validacao_tab


def _run_button(label: str, running_var, on_click) -> rx.Component:
    return rx.button(
        rx.cond(running_var, "Calculando…", label),
        on_click=on_click, disabled=running_var, size="1",
    )


def _map_layer_note() -> rx.Component:
    """A one-line reminder that this tab's map layer can be turned on/off from
    the on-map legend, not repeated controls in every tab."""
    return rx.text(
        "A camada correspondente aparece no mapa — use a legenda no canto do "
        "mapa para ligar/desligar ou trocar o ano.",
        size="1", color=MUTED,
    )


# --------------------------------------------------------------------------- #
# Cobertura
# --------------------------------------------------------------------------- #
def _cobertura_table() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("Ano", size="1", color=MUTED),
            rx.select(
                [str(y) for y in mb.MAPBIOMAS_YEARS],
                value=AppState.mapbiomas_layer_year.to_string(),
                on_change=AppState.set_mapbiomas_layer_year,
                size="1",
            ),
            spacing="2", align="center",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Classe"),
                    rx.table.column_header_cell("ha", text_align="right"),
                    rx.table.column_header_cell("%", text_align="right"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    AppState.history_table_rows,
                    lambda r: rx.table.row(
                        rx.table.cell(
                            rx.hstack(
                                rx.box(width="10px", height="10px",
                                      border_radius="2px",
                                      background=r["color"]),
                                rx.text(r["class_pt"], size="1"),
                                spacing="2", align="center",
                            ),
                        ),
                        rx.table.cell(rx.text(r["area_ha"], size="1"),
                                     text_align="right"),
                        rx.table.cell(rx.text(r["area_pct"], size="1"),
                                     text_align="right"),
                    ),
                ),
            ),
            size="1", width="100%", variant="surface",
        ),
        spacing="2", width="100%",
    )


def _cobertura_chart() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("hectares", size="1", color=MUTED),
            rx.switch(checked=AppState.history_normalise,
                     on_change=AppState.toggle_history_normalise, size="1"),
            rx.text("percentual", size="1", color=MUTED),
            spacing="2", align="center",
        ),
        rx.plotly(
            data=AppState.history_figure,
            config={"displayModeBar": False, "displaylogo": False,
                   "responsive": True},
            width="100%", height="260px",
        ),
        spacing="2", width="100%",
    )


def cobertura_tab() -> rx.Component:
    return rx.vstack(
        zone_selector(),
        rx.cond(
            AppState.history_error,
            rx.callout(AppState.history_error, icon="triangle-alert",
                       color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.history_degraded,
            rx.callout(
                "Resultado calculado em resolução reduzida após uma falha "
                "temporária do Earth Engine.",
                icon="info", color_scheme="gray", size="1",
            ),
        ),
        rx.cond(
            AppState.history_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text("Calculando trajetória MapBiomas…", size="2"),
                         spacing="2"),
                height="260px",
            ),
            rx.cond(
                AppState.has_history,
                split_panel(_cobertura_chart(), _cobertura_table()),
                rx.center(
                    rx.text("Selecione um imóvel para ver a trajetória de "
                           "uso da terra.", size="2", color=MUTED),
                    height="200px",
                ),
            ),
        ),
        _map_layer_note(),
        rx.text(
            "MapBiomas Coleção 10.1 (CC BY-SA 4.0) · escala 30 m · "
            "reduceRegions em lote por zona.",
            size="1", color=MUTED,
        ),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# Floresta — up to 2008 / 2008 até o registro / depois do registro
# --------------------------------------------------------------------------- #
def _period_stat(label: str, value_var, color: str) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="1", color=MUTED),
        rx.text(f"{value_var} ha", size="3", weight="bold", color=color),
        spacing="0",
    )


def _floresta_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Ano"),
                rx.table.column_header_cell("Perda (ha)", text_align="right"),
                rx.table.column_header_cell("Período"),
            ),
        ),
        rx.table.body(
            rx.foreach(
                AppState.hansen_table_rows,
                lambda r: rx.table.row(
                    rx.table.cell(rx.text(r["year"], size="1")),
                    rx.table.cell(rx.text(r["area_ha"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["period_label"], size="1")),
                ),
            ),
        ),
        size="1", width="100%", variant="surface",
    )


def floresta_tab() -> rx.Component:
    """Hansen loss split into three periods anchored on the Forest Code's own
    2008 reference date and the property's CAR registration (doc/04 §3)."""
    return rx.vstack(
        zone_selector(),
        rx.hstack(
            rx.text(
                "Perda de cobertura florestal por período: até 2008 (data de "
                "corte do Código Florestal), de 2008 até o registro no CAR, "
                "e depois do registro. Ganho é uma camada única, sem data "
                "(2000–2012), nunca somado à perda.",
                size="1", color=MUTED,
            ),
            rx.spacer(),
            _run_button("Calcular", AppState.hansen_running, AppState.run_hansen),
            width="100%", align="start",
        ),
        rx.cond(
            AppState.hansen_error,
            rx.callout(AppState.hansen_error, icon="triangle-alert",
                       color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.hansen_running,
            rx.center(
                rx.hstack(rx.spinner(), rx.text("Calculando…", size="2"),
                         spacing="2"),
                height="200px",
            ),
            rx.cond(
                AppState.hansen_has_run,
                rx.vstack(
                    rx.hstack(
                        _period_stat("Até 2008", AppState.hansen_loss_up_to_2008_ha,
                                    "#f5a524"),
                        _period_stat("2008 até o registro",
                                    AppState.hansen_loss_2008_to_registration_ha,
                                    "#e5484d"),
                        _period_stat("Depois do registro",
                                    AppState.hansen_loss_after_registration_ha,
                                    "#8b1a1a"),
                        _period_stat("Ganho (sem data)", AppState.hansen_gain_ha,
                                    "#02d659"),
                        spacing="5", width="100%", wrap="wrap",
                    ),
                    split_panel(
                        rx.plotly(
                            data=AppState.hansen_figure,
                            config={"displayModeBar": False, "displaylogo": False,
                                   "responsive": True},
                            width="100%", height="230px",
                        ),
                        _floresta_table(),
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        _map_layer_note(),
        rx.text(
            "Hansen/UMD/Google/USGS/NASA — Global Forest Change · escala 30 m.",
            size="1", color=MUTED,
        ),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# Biomassa
# --------------------------------------------------------------------------- #
def _biomassa_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Ano"),
                rx.table.column_header_cell("Mg/ha", text_align="right"),
                rx.table.column_header_cell("Total (Mg)", text_align="right"),
            ),
        ),
        rx.table.body(
            rx.foreach(
                AppState.biomass_table_rows,
                lambda r: rx.table.row(
                    rx.table.cell(rx.text(r["year"], size="1")),
                    rx.table.cell(rx.text(r["agb_mean_mgha"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["total_biomass_mg"], size="1"),
                                 text_align="right"),
                ),
            ),
        ),
        size="1", width="100%", variant="surface",
    )


def biomassa_tab() -> rx.Component:
    """ESA CCI Above-Ground Biomass — a series with a real gap, drawn as a
    gap (doc/04 §4)."""
    return rx.vstack(
        zone_selector(),
        rx.hstack(
            rx.text(
                "Biomassa acima do solo, dez anos: 2007, 2010 e anual a "
                "partir de 2015. O intervalo entre eles é uma lacuna real da "
                "fonte, não um dado ausente — não interpolado.",
                size="1", color=MUTED,
            ),
            rx.spacer(),
            _run_button("Calcular", AppState.biomass_running, AppState.run_biomass),
            width="100%", align="start",
        ),
        rx.cond(
            AppState.biomass_error,
            rx.callout(AppState.biomass_error, icon="triangle-alert",
                       color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.biomass_running,
            rx.center(
                rx.hstack(rx.spinner(), rx.text("Calculando…", size="2"),
                         spacing="2"),
                height="200px",
            ),
            rx.cond(
                AppState.biomass_rows,
                split_panel(
                    rx.plotly(
                        data=AppState.biomass_figure,
                        config={"displayModeBar": False, "displaylogo": False,
                               "responsive": True},
                        width="100%", height="260px",
                    ),
                    _biomassa_table(),
                ),
            ),
        ),
        _map_layer_note(),
        rx.text(
            "ESA CCI Biomass v6.0 — Santoro & Cartus (2025) · escala 100 m.",
            size="1", color=MUTED,
        ),
        spacing="3", width="100%", padding="3",
    )


def results_panel() -> rx.Component:
    return rx.cond(
        AppState.has_imovel,
        rx.box(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("Cobertura", value="cobertura"),
                    rx.tabs.trigger("Transições", value="transicoes"),
                    rx.tabs.trigger("Floresta", value="floresta"),
                    rx.tabs.trigger("Biomassa", value="biomassa"),
                    rx.tabs.trigger("Validação", value="validacao"),
                ),
                rx.tabs.content(cobertura_tab(), value="cobertura"),
                rx.tabs.content(transitions_tab(), value="transicoes"),
                rx.tabs.content(floresta_tab(), value="floresta"),
                rx.tabs.content(biomassa_tab(), value="biomassa"),
                rx.tabs.content(validacao_tab(), value="validacao"),
                value=AppState.results_tab,
                on_change=AppState.set_results_tab,
                width="100%",
            ),
            width="100%",
            border_top=BORDER,
            background="var(--color-panel)",
        ),
    )
