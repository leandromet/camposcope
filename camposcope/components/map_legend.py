"""The on-map layer control — a floating box in a map corner, not a sidebar
section, for the one layer that changes with the active results tab
(doc/08-ui-ux.md §1).

Styled to sit where a native Leaflet control would (a small white rounded box
in a corner), because that is the visual language a map legend is expected to
have — even though it is a plain Reflex-rendered overlay, the same technique
already used for the results drawer, not a genuine ``L.control``.
"""

from __future__ import annotations

import reflex as rx

from ..config import mapbiomas as mb
from ..config.datasets import AGB_YEARS
from ..state import AppState

_BOX_STYLE = dict(
    position="absolute",
    top="12px",
    right="12px",
    background="var(--color-panel-solid)",
    border="1px solid var(--gray-5)",
    border_radius="var(--radius-3)",
    box_shadow="0 2px 8px rgba(0,0,0,.15)",
    padding="8px 10px",
    z_index="900",           # above Leaflet's panes (~700), below the results
    min_width="180px",       # drawer (1000) — see pages/index.py's own note.
    font_size="0.75rem",
)


def _header(title: str) -> rx.Component:
    return rx.hstack(
        rx.text(title, size="1", weight="bold"),
        rx.spacer(),
        rx.switch(checked=AppState.analysis_layer_enabled,
                  on_change=AppState.toggle_analysis_layer, size="1"),
        width="100%", align="center",
    )


def _swatch_row(color: str, label: str) -> rx.Component:
    return rx.hstack(
        rx.box(width="10px", height="10px", border_radius="2px",
              background=color, flex_shrink="0"),
        rx.text(label, size="1"),
        spacing="2", align="center",
    )


def _cobertura_legend() -> rx.Component:
    return rx.vstack(
        _header("MapBiomas"),
        rx.select(
            [str(y) for y in mb.MAPBIOMAS_YEARS],
            value=AppState.mapbiomas_layer_year.to_string(),
            on_change=AppState.set_mapbiomas_layer_year,
            size="1", width="100%",
        ),
        rx.text("Cores: paleta oficial MapBiomas", size="1",
               color="var(--gray-11)"),
        spacing="2", width="100%",
    )


def _spot_section() -> rx.Component:
    """SPOT 2008 belongs here, not the generic basemap dropdown: this tab IS
    the Forest Code's 2008 reference date (doc/12-spot-2008.md). Toggling it
    on switches the map's actual imagery, not an overlay — see
    LayersMixin.toggle_spot_basemap."""
    is_spot = AppState.basemap.contains("spot")
    return rx.vstack(
        rx.divider(),
        rx.hstack(
            rx.text("Imagem SPOT 2008", size="1", weight="medium"),
            rx.spacer(),
            rx.switch(checked=is_spot, on_change=AppState.toggle_spot_basemap,
                     size="1"),
            width="100%", align="center",
        ),
        rx.cond(
            AppState.basemap_busy,
            rx.hstack(rx.spinner(size="1"), rx.text("Carregando…", size="1"),
                     spacing="2", align="center"),
        ),
        rx.cond(
            AppState.basemap_error,
            rx.callout(AppState.basemap_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            is_spot,
            rx.vstack(
                rx.button(
                    rx.cond(AppState.spot_running, "Verificando…",
                           "Verificar cobertura"),
                    on_click=AppState.run_spot_coverage,
                    disabled=AppState.spot_running, size="1", width="100%",
                ),
                rx.cond(
                    AppState.spot_error,
                    rx.callout(AppState.spot_error, icon="triangle-alert",
                              color_scheme="amber", size="1"),
                ),
                rx.cond(
                    AppState.spot_summary,
                    rx.cond(
                        AppState.spot_summary["has_coverage"].to(bool),
                        rx.vstack(
                            rx.text(
                                f"{AppState.spot_summary['date_min']} a "
                                f"{AppState.spot_summary['date_max']}",
                                size="1",
                            ),
                            rx.text(
                                f"{AppState.spot_summary['pre_cutoff_pct']}% "
                                "antes de 22/07/2008",
                                size="1", weight="medium",
                            ),
                            spacing="1",
                        ),
                        rx.text("Sem cobertura SPOT nesta zona.", size="1",
                               color="var(--gray-11)"),
                    ),
                ),
                rx.text(
                    "Não classifica área consolidada.", size="1",
                    color="var(--gray-11)",
                ),
                spacing="2", width="100%",
            ),
        ),
        spacing="2", width="100%",
    )


def _floresta_legend() -> rx.Component:
    return rx.vstack(
        _header("Floresta — Hansen"),
        rx.segmented_control.root(
            rx.segmented_control.item("desde 2008", value="2008"),
            rx.segmented_control.item("desde o registro", value="registro"),
            value=AppState.hansen_layer_mode,
            on_change=AppState.set_hansen_layer_mode,
            size="1", width="100%",
        ),
        _swatch_row("#d4271e", "Perda"),
        _swatch_row("#02d659", "Ganho (sem data)"),
        _spot_section(),
        spacing="2", width="100%",
    )


def _biomassa_legend() -> rx.Component:
    return rx.vstack(
        _header("Biomassa — ESA CCI"),
        rx.select(
            [str(y) for y in AGB_YEARS],
            value=AppState.biomass_layer_year.to_string(),
            on_change=AppState.set_biomass_layer_year,
            size="1", width="100%",
        ),
        rx.hstack(
            rx.box(width="60px", height="8px", border_radius="2px",
                  background="linear-gradient(to right, white, #1a7f37)"),
            spacing="2", align="center",
        ),
        rx.hstack(
            rx.text("0", size="1", color="var(--gray-11)"),
            rx.spacer(),
            rx.text("500 Mg/ha", size="1", color="var(--gray-11)"),
            width="100%",
        ),
        spacing="2", width="100%",
    )


def _transicoes_legend() -> rx.Component:
    """Older year on the left of the swipe divider, newer on the right — the
    same `sankey_year_a`/`sankey_year_b` the two-stage Sankey uses, so this
    legend has nothing of its own to set, only to say what is showing."""
    return rx.vstack(
        _header("MapBiomas — comparação"),
        rx.cond(
            AppState.map_swipe_enabled,
            rx.hstack(
                rx.text(AppState.sankey_year_left, size="1", weight="medium"),
                rx.icon("move-horizontal", size=12),
                rx.text(AppState.sankey_year_right, size="1", weight="medium"),
                spacing="2", align="center",
            ),
            rx.text("Escolha os anos na aba Transições.", size="1",
                   color="var(--gray-11)"),
        ),
        rx.text("Arraste a barra no mapa para comparar.", size="1",
               color="var(--gray-11)"),
        spacing="2", width="100%",
    )


def map_legend() -> rx.Component:
    """Shown only once a property is selected and the active tab has a map
    layer of its own."""
    return rx.cond(
        AppState.has_imovel,
        rx.box(
            rx.match(
                AppState.results_tab,
                ("cobertura", _cobertura_legend()),
                ("transicoes", _transicoes_legend()),
                ("floresta", _floresta_legend()),
                ("biomassa", _biomassa_legend()),
                rx.fragment(),
            ),
            **_BOX_STYLE,
        ),
    )
