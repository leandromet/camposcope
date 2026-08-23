"""Results: the zone selector and the four analysis tabs (doc/08-ui-ux.md §5)."""

from __future__ import annotations

import reflex as rx

from ..state import AppState
from .layout import BORDER, MUTED
from .sankey import transitions_tab


def zone_selector() -> rx.Component:
    """Which zone the chart and tabs describe. Selecting one never moves the
    map (constraint C1) — only ``AppState.frame_geometry`` does that, and only
    when a *property* is newly selected."""
    return rx.cond(
        AppState.zones,
        rx.hstack(
            rx.foreach(
                AppState.zones,
                lambda z: rx.button(
                    z["zone_label"],
                    on_click=AppState.set_active_zone(z["zone_key"]),
                    size="1",
                    variant=rx.cond(
                        AppState.active_zone == z["zone_key"], "solid", "soft"
                    ),
                    color_scheme=rx.cond(
                        z["zone_kind"] == "property", "amber", "blue"
                    ),
                ),
            ),
            spacing="2",
            wrap="wrap",
            width="100%",
        ),
    )


def _history_chart() -> rx.Component:
    return rx.cond(
        AppState.history_running,
        rx.center(
            rx.hstack(rx.spinner(), rx.text("Calculando trajetória MapBiomas…",
                                            size="2"), spacing="2"),
            height="340px",
        ),
        rx.cond(
            AppState.has_history,
            rx.vstack(
                rx.hstack(
                    rx.text("hectares", size="1", color=MUTED),
                    rx.switch(checked=AppState.history_normalise,
                             on_change=AppState.toggle_history_normalise,
                             size="1"),
                    rx.text("percentual", size="1", color=MUTED),
                    spacing="2", align="center",
                ),
                rx.plotly(
                    data=AppState.history_figure,
                    config={"displayModeBar": False, "displaylogo": False,
                           "responsive": True},
                    width="100%",
                    height="340px",
                ),
                spacing="2",
                width="100%",
            ),
            rx.center(
                rx.text("Selecione um imóvel para ver a trajetória de uso da terra.",
                        size="2", color=MUTED),
                height="200px",
            ),
        ),
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
        _history_chart(),
        rx.text(
            "MapBiomas Coleção 10.1 (CC BY-SA 4.0) · escala 30 m · "
            "reduceRegions em lote por zona.",
            size="1", color=MUTED,
        ),
        spacing="3",
        width="100%",
        padding="3",
    )


def _run_button(label: str, running_var, on_click) -> rx.Component:
    return rx.button(
        rx.cond(running_var, "Calculando…", label),
        on_click=on_click, disabled=running_var, size="1",
    )


def floresta_tab() -> rx.Component:
    """Hansen loss (split at the property's own registration date) and
    undated gain, kept visually and numerically separate (doc/04 §3)."""
    return rx.vstack(
        rx.hstack(
            rx.text(
                "Perda de cobertura florestal, ano a ano, dividida em antes/"
                "depois do registro no CAR. Ganho é uma camada única, sem "
                "data (2000–2012), e nunca é somado à perda.",
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
                        rx.vstack(
                            rx.text("Antes do registro", size="1", color=MUTED),
                            rx.text(f"{AppState.hansen_loss_before_ha} ha",
                                   size="3", weight="bold", color="#f5a524"),
                            spacing="0",
                        ),
                        rx.vstack(
                            rx.text("Depois do registro", size="1", color=MUTED),
                            rx.text(f"{AppState.hansen_loss_after_ha} ha",
                                   size="3", weight="bold", color="#d4271e"),
                            spacing="0",
                        ),
                        rx.vstack(
                            rx.text("Ganho (sem data)", size="1", color=MUTED),
                            rx.text(f"{AppState.hansen_gain_ha} ha",
                                   size="3", weight="bold", color="#02d659"),
                            spacing="0",
                        ),
                        spacing="6", width="100%",
                    ),
                    rx.plotly(
                        data=AppState.hansen_figure,
                        config={"displayModeBar": False, "displaylogo": False,
                               "responsive": True},
                        width="100%", height="300px",
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        rx.text(
            "Hansen/UMD/Google/USGS/NASA — Global Forest Change · escala 30 m.",
            size="1", color=MUTED,
        ),
        spacing="3", width="100%", padding="3",
    )


def biomassa_tab() -> rx.Component:
    """ESA CCI Above-Ground Biomass — a series with a real gap, drawn as a
    gap (doc/04 §4)."""
    return rx.vstack(
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
                rx.plotly(
                    data=AppState.biomass_figure,
                    config={"displayModeBar": False, "displaylogo": False,
                           "responsive": True},
                    width="100%", height="300px",
                ),
            ),
        ),
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
                ),
                rx.tabs.content(cobertura_tab(), value="cobertura"),
                rx.tabs.content(transitions_tab(), value="transicoes"),
                rx.tabs.content(floresta_tab(), value="floresta"),
                rx.tabs.content(biomassa_tab(), value="biomassa"),
                value=AppState.results_tab,
                on_change=AppState.set_results_tab,
                width="100%",
            ),
            width="100%",
            border_top=BORDER,
            background="var(--color-panel)",
        ),
    )
