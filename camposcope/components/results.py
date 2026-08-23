"""Results: the zone selector and the MapBiomas trajectory tab.

One results drawer, tabs across the top (doc/08-ui-ux.md §5). Only "Cobertura"
exists so far (Phase 3); the others (Transições, Floresta, Biomassa) are
Phase 4-5 stubs so the tab strip's shape is right from the start.
"""

from __future__ import annotations

import reflex as rx

from ..state import AppState
from .layout import BORDER, MUTED


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


def _stub_tab(label_pt: str) -> rx.Component:
    return rx.center(
        rx.text(f"{label_pt} — em construção.", size="2", color=MUTED),
        height="200px",
        padding="3",
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
                rx.tabs.content(_stub_tab("Transições"), value="transicoes"),
                rx.tabs.content(_stub_tab("Floresta"), value="floresta"),
                rx.tabs.content(_stub_tab("Biomassa"), value="biomassa"),
                value=AppState.results_tab,
                on_change=AppState.set_results_tab,
                width="100%",
            ),
            width="100%",
            border_top=BORDER,
            background="var(--color-panel)",
        ),
    )
