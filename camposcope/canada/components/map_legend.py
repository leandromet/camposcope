"""The on-map layer control — a floating corner box, not a sidebar section,
for the one layer that changes with the active results tab.

Same visual language as ``camposcope/components/map_legend.py``: styled to sit
where a native Leaflet control would.
"""

from __future__ import annotations

import reflex as rx

from ..config import aafc as mb
from ..config.datasets import AGB_YEARS, LANDSAT_RENDERINGS
from ..config.vlce2 import COMPARABLE_YEARS
from ..state import CanadaState as S

_BOX_STYLE = dict(
    position="absolute", top="12px", right="12px",
    background="var(--color-panel-solid)", border="1px solid var(--gray-5)",
    border_radius="var(--radius-3)", box_shadow="0 2px 8px rgba(0,0,0,.15)",
    padding="8px 10px", z_index="900", min_width="180px", font_size="0.75rem",
)


def _header(title) -> rx.Component:
    return rx.hstack(
        rx.text(title, size="1", weight="bold"),
        rx.spacer(),
        rx.switch(checked=S.analysis_layer_enabled,
                 on_change=S.toggle_analysis_layer, size="1"),
        width="100%", align="center",
    )


def _basemap_section() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(S.tr["legend_landsat"], size="1", weight="medium"),
            rx.spacer(),
            rx.switch(checked=S.basemap.contains("landsat"),
                     on_change=S.toggle_landsat_basemap, size="1"),
            width="100%", align="center",
        ),
        rx.cond(
            S.basemap_busy,
            rx.hstack(rx.spinner(size="1"),
                     rx.text(S.tr["layers_loading"], size="1"),
                     spacing="2", align="center"),
        ),
        rx.cond(
            S.basemap_error,
            rx.callout(S.basemap_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            S.basemap.contains("landsat"),
            rx.vstack(
                rx.select.root(
                    rx.select.trigger(width="100%"),
                    rx.select.content(
                        *[
                            rx.select.item(conf["label_en"], value=key)
                            for key, conf in LANDSAT_RENDERINGS.items()
                        ],
                    ),
                    value=S.basemap, on_change=S.set_basemap, size="1",
                ),
                rx.select(
                    [str(y) for y in range(1984, 2027)],
                    value=S.landsat_year.to_string(),
                    on_change=S.set_landsat_year, size="1", width="100%",
                ),
                rx.text(S.tr["layers_landsat_hint"], size="1",
                       color="var(--gray-11)"),
                spacing="1", width="100%",
            ),
        ),
        spacing="2", width="100%",
    )


def _cobertura_legend() -> rx.Component:
    return rx.vstack(
        _header(S.tr["legend_aci"]),
        rx.select(
            [str(y) for y in mb.ACI_YEARS],
            value=S.aci_layer_year.to_string(),
            on_change=S.set_aci_layer_year, size="1", width="100%",
        ),
        rx.text(S.tr["legend_aci_palette"], size="1", color="var(--gray-11)"),
        spacing="2", width="100%",
    )


def _floresta_legend() -> rx.Component:
    return rx.vstack(
        _header(S.tr["legend_floresta_hansen"]),
        rx.segmented_control.root(
            rx.segmented_control.item(
                S.tr["legend_hansen_split_start_date"], value="start_date"),
            rx.segmented_control.item(
                S.tr["legend_hansen_split_undivided"], value="undivided"),
            value=S.hansen_layer_split, on_change=S.set_hansen_layer_split,
            size="1", width="100%",
        ),
        rx.hstack(
            rx.box(width="10px", height="10px", border_radius="2px",
                  background="#d4271e"),
            rx.text(S.tr["legend_perda"], size="1"),
            spacing="2", align="center",
        ),
        rx.hstack(
            rx.box(width="10px", height="10px", border_radius="2px",
                  background="#02d659"),
            rx.text(S.tr["legend_ganho"], size="1"),
            spacing="2", align="center",
        ),
        spacing="2", width="100%",
    )


def _biomassa_legend() -> rx.Component:
    return rx.vstack(
        _header(S.tr["tab_biomassa"]),
        rx.select(
            [str(y) for y in AGB_YEARS],
            value=S.biomass_layer_year.to_string(),
            on_change=S.set_biomass_layer_year, size="1", width="100%",
        ),
        spacing="2", width="100%",
    )


def _paisagem_legend() -> rx.Component:
    return rx.vstack(
        _header(S.tr["tab_paisagem"]),
        rx.select(
            [str(y) for y in mb.ACI_YEARS],
            value=S.landscape_year.to_string(),
            on_change=S.set_landscape_year, size="1", width="100%",
        ),
        spacing="2", width="100%",
    )


def _fogo_legend() -> rx.Component:
    return rx.vstack(
        _header(S.tr["tab_fogo"]),
        rx.segmented_control.root(
            rx.segmented_control.item(S.tr["fogo_source_modis"], value="modis"),
            rx.segmented_control.item(S.tr["fogo_source_aci"], value="aci"),
            value=S.fire_source, on_change=S.set_fire_source,
            size="1", width="100%",
        ),
        rx.text(
            rx.cond(S.fire_source == "aci", S.tr["fogo_aci_layer_note"],
                   S.tr["fogo_modis_layer_note"]),
            size="1", color="var(--gray-11)",
        ),
        spacing="2", width="100%",
    )


def _validacao_legend() -> rx.Component:
    return rx.vstack(
        rx.text(S.tr["tab_validacao"], size="1", weight="bold"),
        rx.select(
            [str(y) for y in COMPARABLE_YEARS],
            value=S.validation_year.to_string(),
            on_change=S.set_validation_year, size="1", width="100%",
        ),
        rx.hstack(
            rx.text(S.tr["legend_aci"], size="1", weight="medium"),
            rx.spacer(),
            rx.text("VLCE2", size="1", weight="medium"),
            width="100%",
        ),
        spacing="2", width="100%",
    )


def map_legend() -> rx.Component:
    return rx.box(
        _basemap_section(),
        rx.cond(
            S.has_parcel,
            rx.vstack(
                rx.divider(),
                rx.match(
                    S.results_tab,
                    ("cobertura", _cobertura_legend()),
                    ("floresta", _floresta_legend()),
                    ("biomassa", _biomassa_legend()),
                    ("paisagem", _paisagem_legend()),
                    ("fogo", _fogo_legend()),
                    ("validacao", _validacao_legend()),
                    rx.fragment(),
                ),
                spacing="2", width="100%",
            ),
        ),
        **_BOX_STYLE,
    )
