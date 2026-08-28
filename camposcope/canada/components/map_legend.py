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


def _class_legend_rows(rows: rx.Var) -> rx.Component:
    """Colour + label + share for whichever classes are actually present in
    the active zone/year — capped at 8 and scrollable, rather than every code
    in the full palette (200+ AAFC classes): a parcel only ever shows a
    handful, and listing the rest would be noise."""
    return rx.vstack(
        rx.foreach(
            rows[:8],
            lambda r: rx.hstack(
                rx.box(width="10px", height="10px", border_radius="2px",
                      background=r["color"], flex_shrink="0"),
                rx.text(r["class_label"], size="1", style={"flex": "1"},
                       no_of_lines=1),
                rx.text(f"{r['area_pct']}%", size="1", color="var(--gray-11)"),
                spacing="2", align="center", width="100%",
            ),
        ),
        spacing="1", width="100%", max_height="160px", overflow_y="auto",
    )


def _cobertura_legend() -> rx.Component:
    return rx.vstack(
        _header(S.tr["legend_aci"]),
        rx.select(
            [str(y) for y in mb.ACI_YEARS],
            value=S.aci_layer_year.to_string(),
            on_change=S.set_aci_layer_year, size="1", width="100%",
        ),
        rx.cond(
            S.history_table_rows,
            _class_legend_rows(S.history_table_rows),
            rx.text(S.tr["legend_aci_palette"], size="1", color="var(--gray-11)"),
        ),
        spacing="2", width="100%",
    )


def _transicoes_legend() -> rx.Component:
    """Older year on the left of the swipe divider, newer on the right — the
    same ``sankey_year_a``/``sankey_year_b`` the two-stage Sankey uses, so
    this legend has nothing of its own to set, only to say what is showing.
    Mirrors the Brazil page's own ``_transicoes_legend``."""
    return rx.vstack(
        _header(S.tr["tab_transicoes"]),
        rx.cond(
            S.map_swipe_enabled,
            rx.hstack(
                rx.text(S.sankey_year_left, size="1", weight="medium"),
                rx.icon("move-horizontal", size=12),
                rx.text(S.sankey_year_right, size="1", weight="medium"),
                spacing="2", align="center",
            ),
            rx.text(S.tr["legend_choose_years"], size="1",
                   color="var(--gray-11)"),
        ),
        rx.text(S.tr["legend_drag_to_compare"], size="1",
               color="var(--gray-11)"),
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
        # Same two palettes services/layers.py mints tiles with — MODIS'
        # 6-stop gradient (config/datasets.py MODIS_BURN["vis_palette"]) or
        # ACI's 3-stop one, so the swatch never drifts from what is on
        # screen.
        rx.cond(
            S.fire_source == "aci",
            rx.box(width="60px", height="8px", border_radius="2px",
                  background="linear-gradient(to right, #fed976, #fd8d3c, "
                            "#bd0026)"),
            rx.box(width="60px", height="8px", border_radius="2px",
                  background="linear-gradient(to right, #ffffb2, #fecc5c, "
                            "#fd8d3c, #f03b20, #bd0026, #800026)"),
        ),
        rx.text(S.tr["fogo_frequencia_ocorrencias"], size="1",
               color="var(--gray-11)"),
        rx.text(
            rx.cond(
                S.fire_source == "aci",
                S.tr["fogo_aci_layer_note"],
                f"{S.tr['fogo_modis_layer_note_prefix']}{S.fire_current_year}"
                f"{S.tr['fogo_modis_layer_note_suffix']}",
            ),
            size="1", color="var(--gray-11)",
        ),
        spacing="2", width="100%",
    )


def _validacao_side(title, rows: rx.Var, fallback) -> rx.Component:
    """One side of the swipe divider: its own header plus real classes when
    available, or a hint for why there is nothing to show yet. Mirrors the
    Brazil page's own _validacao_side."""
    return rx.vstack(
        rx.text(title, size="1", weight="medium"),
        rx.cond(rows, _class_legend_rows(rows), fallback),
        spacing="1", width="100%",
    )


def _validacao_legend() -> rx.Component:
    """Both sides get real classes present in the active zone at
    ``validation_year`` — services/vlce2.py::class_histogram, the
    native-class counterpart of agreement()'s 8-group confusion matrix (see
    that function's own docstring)."""
    return rx.vstack(
        rx.text(S.tr["tab_validacao"], size="1", weight="bold"),
        rx.select(
            [str(y) for y in COMPARABLE_YEARS],
            value=S.validation_year.to_string(),
            on_change=S.set_validation_year, size="1", width="100%",
        ),
        rx.vstack(
            _validacao_side(
                S.tr["legend_aci"], S.validation_aci_classes,
                rx.text(S.tr["legend_run_calcular"], size="1",
                       color="var(--gray-11)"),
            ),
            _validacao_side(
                "VLCE2", S.validation_vlce2_classes,
                rx.text(S.tr["legend_run_calcular"], size="1",
                       color="var(--gray-11)"),
            ),
            spacing="2", width="100%",
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
                    ("transicoes", _transicoes_legend()),
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
