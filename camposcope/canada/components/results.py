"""Results: the zone selector and the results tabs.

Same "chart beside table" shape as ``camposcope/components/results.py`` — a
smaller chart next to its data table (``layout.split_panel``) so the numbers
are always one glance away, never behind a hover tooltip.
"""

from __future__ import annotations

import reflex as rx

from ..config import aafc as mb
from ..config.datasets import FIRE_MIN_MEANINGFUL_HA
from ..state import CanadaState as S
from .export_widgets import chart_box, table_export_button
from .layout import BORDER, MUTED, split_panel, zone_selector
from .validacao import validacao_tab


def _run_button(running_var, on_click) -> rx.Component:
    return rx.button(
        rx.cond(running_var, S.tr["calculando"], S.tr["calcular"]),
        on_click=on_click, disabled=running_var, size="1",
    )


def _map_layer_note() -> rx.Component:
    return rx.text(S.tr["map_layer_note"], size="1", color=MUTED)


# --------------------------------------------------------------------------- #
# Cobertura
# --------------------------------------------------------------------------- #
def _cobertura_table() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(S.tr["cobertura_ano"], size="1", color=MUTED),
            rx.select(
                [str(y) for y in mb.ACI_YEARS],
                value=S.aci_layer_year.to_string(),
                on_change=S.set_aci_layer_year, size="1",
            ),
            rx.spacer(),
            rx.cond(S.history_table_rows,
                   table_export_button(S.download_cobertura_csv)),
            spacing="2", align="center", width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(S.tr["cobertura_classe"]),
                    rx.table.column_header_cell("ha", text_align="right"),
                    rx.table.column_header_cell("%", text_align="right"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    S.history_table_rows,
                    lambda r: rx.table.row(
                        rx.table.cell(rx.hstack(
                            rx.box(width="10px", height="10px",
                                  border_radius="2px", background=r["color"]),
                            rx.text(r["class_label"], size="1"),
                            spacing="2", align="center",
                        )),
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
            rx.text(S.tr["cobertura_hectares"], size="1", color=MUTED),
            rx.switch(checked=S.history_normalise,
                     on_change=S.toggle_history_normalise, size="1"),
            rx.text(S.tr["cobertura_percentual"], size="1", color=MUTED),
            spacing="2", align="center",
        ),
        # More height below "md" than desktop's 260px — the figure's own
        # legend (charts.py's _style()) can wrap several rows on a phone-
        # width chart. See the Brazil page's own results.py for the full
        # rationale.
        chart_box(S.history_figure, "ca-plot-cobertura",
                 "camposcope_ca_cobertura", ["360px", "360px", "260px", "260px"]),
        spacing="2", width="100%",
    )


def cobertura_tab() -> rx.Component:
    return rx.vstack(
        zone_selector(),
        rx.cond(
            S.history_out_of_range,
            rx.callout(S.tr["cobertura_out_of_range"], icon="info",
                      color_scheme="gray", size="1"),
            rx.cond(
                S.history_error,
                rx.callout(S.history_error, icon="triangle-alert",
                          color_scheme="amber", size="1"),
            ),
        ),
        rx.cond(
            S.history_degraded,
            rx.callout(S.tr["cobertura_degraded"], icon="info",
                      color_scheme="gray", size="1"),
        ),
        rx.cond(
            S.history_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(S.tr["cobertura_running"], size="2"),
                         spacing="2"),
                height="260px",
            ),
            rx.cond(
                S.has_history,
                split_panel(_cobertura_chart(), _cobertura_table()),
                rx.center(
                    rx.text(S.tr["cobertura_empty"], size="2", color=MUTED),
                    height="200px",
                ),
            ),
        ),
        _map_layer_note(),
        rx.text(S.tr["cobertura_attribution"], size="1", color=MUTED),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# Transições
# --------------------------------------------------------------------------- #
def _year_select(value, on_change, label) -> rx.Component:
    years = [str(y) for y in mb.ACI_YEARS]
    return rx.vstack(
        rx.text(label, size="1", color=MUTED),
        rx.select(years, value=value.to_string(), on_change=on_change, size="1"),
        spacing="1", align_items="start",
    )


def transitions_tab() -> rx.Component:
    return rx.vstack(
        rx.text(S.tr["transicoes_intro"], size="1", color=MUTED),
        zone_selector(),
        rx.hstack(
            _year_select(S.sankey_year_left,
                        lambda v: S.set_sankey_years(v, S.sankey_year_right),
                        S.tr["transicoes_de"]),
            _year_select(S.sankey_year_right,
                        lambda v: S.set_sankey_years(S.sankey_year_left, v),
                        S.tr["transicoes_para"]),
            _run_button(S.sankey_running, S.run_sankey),
            spacing="3", align="start",
        ),
        rx.cond(
            S.sankey_error,
            rx.callout(S.sankey_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            S.sankey_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(S.tr["calculando"], size="2"), spacing="2"),
                height="200px",
            ),
            rx.cond(
                S.sankey_transitions,
                split_panel(
                    chart_box(S.sankey_figure, "ca-plot-sankey",
                             "camposcope_ca_transicoes", "280px"),
                    rx.vstack(
                        rx.hstack(
                            rx.text(S.tr["transicoes_maiores"], size="1",
                                   weight="medium", color=MUTED),
                            rx.spacer(),
                            table_export_button(S.download_transicoes_csv),
                            width="100%", align="center",
                        ),
                        rx.foreach(
                            S.sankey_table_rows[:10],
                            lambda r: rx.hstack(
                                rx.text(f"{r['src']} → {r['tgt']}", size="1"),
                                rx.spacer(),
                                rx.text(f"{r['area_ha']} ha", size="1",
                                       weight="bold"),
                                width="100%",
                            ),
                        ),
                        spacing="1", width="100%",
                    ),
                ),
            ),
        ),
        rx.text(
            f"{S.tr['transicoes_min_gap_note_prefix']} 3 "
            f"{S.tr['transicoes_min_gap_note_suffix']}",
            size="1", color=MUTED,
        ),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# Floresta
# --------------------------------------------------------------------------- #
def _period_stat(label, value_var, color: str, unit: str = "ha") -> rx.Component:
    return rx.vstack(
        rx.text(label, size="1", color=MUTED),
        rx.text(f"{value_var} {unit}", size="3", weight="bold", color=color),
        spacing="0",
    )


def _floresta_table() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.spacer(),
            rx.cond(S.hansen_table_rows,
                   table_export_button(S.download_floresta_csv)),
            width="100%",
        ),
        rx.table.root(
            rx.table.header(rx.table.row(
                rx.table.column_header_cell(S.tr["floresta_col_ano"]),
                rx.table.column_header_cell(S.tr["floresta_col_perda"],
                                            text_align="right"),
                rx.table.column_header_cell(S.tr["floresta_col_periodo"]),
            )),
            rx.table.body(rx.foreach(
                S.hansen_table_rows,
                lambda r: rx.table.row(
                    rx.table.cell(rx.text(r["year"], size="1")),
                    rx.table.cell(rx.text(r["area_ha"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["period_label"], size="1")),
                ),
            )),
            size="1", width="100%", variant="surface",
        ),
        spacing="1", width="100%",
    )


def _stand_age_section() -> rx.Component:
    return rx.vstack(
        rx.divider(),
        rx.hstack(
            rx.text(S.tr["floresta_age_title"], size="1", weight="medium",
                   color=MUTED),
            rx.spacer(),
            rx.button(
                rx.cond(S.age_running, S.tr["calculando"],
                       S.tr["floresta_age_run_button"]),
                on_click=S.run_stand_age, disabled=S.age_running, size="1",
            ),
            width="100%", align="center",
        ),
        rx.cond(
            S.age_error,
            rx.callout(S.age_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            S.age_has_run,
            rx.hstack(
                _period_stat(S.tr["floresta_age_mean"],
                            S.age_row_for_zone["age_mean_y"], "#1f8d49",
                            unit=S.tr["floresta_age_unit"]),
                _period_stat(S.tr["floresta_age_median"],
                            S.age_row_for_zone["age_median_y"], "#1f8d49",
                            unit=S.tr["floresta_age_unit"]),
                rx.vstack(
                    rx.text(S.tr["floresta_age_forested_pct"], size="1",
                           color=MUTED),
                    rx.text(f"{S.age_row_for_zone['forested_pct']}%", size="3",
                           weight="bold", color="#1f8d49"),
                    spacing="0",
                ),
                spacing="5", width="100%", wrap="wrap",
            ),
        ),
        rx.text(S.tr["floresta_age_note"], size="1", color=MUTED),
        rx.text(S.tr["floresta_age_attribution"], size="1", color=MUTED),
        spacing="2", width="100%",
    )


def floresta_tab() -> rx.Component:
    return rx.vstack(
        zone_selector(),
        rx.hstack(
            rx.segmented_control.root(
                rx.segmented_control.item(
                    S.tr["floresta_split_start_date"], value="start_date"),
                rx.segmented_control.item(
                    S.tr["floresta_split_undivided"], value="undivided"),
                value=S.hansen_layer_split, on_change=S.set_hansen_layer_split,
                size="1",
            ),
            _run_button(S.hansen_running, S.run_hansen),
            width="100%", align="start", wrap="wrap",
        ),
        rx.cond(
            S.hansen_error,
            rx.callout(S.hansen_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            S.hansen_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(S.tr["calculando"], size="2"), spacing="2"),
                height="200px",
            ),
            rx.cond(
                S.hansen_has_run,
                rx.vstack(
                    rx.cond(
                        ~S.hansen_is_split,
                        rx.callout(S.tr["floresta_no_start_date_note"],
                                  icon="info", color_scheme="gray", size="1"),
                    ),
                    rx.hstack(
                        rx.cond(
                            S.hansen_is_split,
                            rx.fragment(
                                _period_stat(S.tr["floresta_before_parcel"],
                                            S.hansen_loss_before_ha, "#f5a524"),
                                _period_stat(S.tr["floresta_after_parcel"],
                                            S.hansen_loss_after_ha, "#e5484d"),
                            ),
                            _period_stat(S.tr["floresta_undivided_total"],
                                        S.hansen_loss_undivided_ha, "#8b1a1a"),
                        ),
                        _period_stat(S.tr["floresta_ganho_sem_data"],
                                    S.hansen_gain_ha, "#02d659"),
                        spacing="5", width="100%", wrap="wrap",
                    ),
                    split_panel(
                        chart_box(S.hansen_figure, "ca-plot-floresta",
                                 "camposcope_ca_floresta", "230px"),
                        _floresta_table(),
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        _stand_age_section(),
        _map_layer_note(),
        rx.text(S.tr["floresta_attribution"], size="1", color=MUTED),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# Biomassa
# --------------------------------------------------------------------------- #
def _biomassa_table() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.spacer(),
            rx.cond(S.biomass_table_rows,
                   table_export_button(S.download_biomassa_csv)),
            width="100%",
        ),
        rx.table.root(
            rx.table.header(rx.table.row(
                rx.table.column_header_cell(S.tr["biomassa_col_ano"]),
                rx.table.column_header_cell(S.tr["biomassa_col_mg_ha"],
                                            text_align="right"),
                rx.table.column_header_cell(S.tr["biomassa_col_total_mg"],
                                            text_align="right"),
            )),
            rx.table.body(rx.foreach(
                S.biomass_table_rows,
                lambda r: rx.table.row(
                    rx.table.cell(rx.text(r["year"], size="1")),
                    rx.table.cell(rx.text(r["agb_mean_mgha"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["total_biomass_mg"], size="1"),
                                 text_align="right"),
                ),
            )),
            size="1", width="100%", variant="surface",
        ),
        spacing="1", width="100%",
    )


def biomassa_tab() -> rx.Component:
    return rx.vstack(
        zone_selector(),
        rx.hstack(_run_button(S.biomass_running, S.run_biomass),
                 width="100%", align="start"),
        rx.cond(
            S.biomass_error,
            rx.callout(S.biomass_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            S.biomass_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(S.tr["calculando"], size="2"), spacing="2"),
                height="200px",
            ),
            rx.cond(
                S.biomass_rows,
                split_panel(
                    chart_box(S.biomass_figure, "ca-plot-biomassa",
                             "camposcope_ca_biomassa", "260px"),
                    _biomassa_table(),
                ),
            ),
        ),
        _map_layer_note(),
        rx.text(S.tr["biomassa_canada_note"], size="1", color=MUTED),
        rx.text(S.tr["biomassa_attribution"], size="1", color=MUTED),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# Paisagem
# --------------------------------------------------------------------------- #
def _paisagem_table() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.spacer(),
            rx.cond(S.landscape_table_rows,
                   table_export_button(S.download_paisagem_csv)),
            width="100%",
        ),
        rx.table.root(
            rx.table.header(rx.table.row(
                rx.table.column_header_cell(S.tr["paisagem_col_zona"]),
                rx.table.column_header_cell(S.tr["paisagem_col_area"],
                                            text_align="right"),
                rx.table.column_header_cell(S.tr["paisagem_col_fragmentos"],
                                            text_align="right"),
                rx.table.column_header_cell(S.tr["paisagem_col_densidade"],
                                            text_align="right"),
                rx.table.column_header_cell(S.tr["paisagem_col_maior"],
                                            text_align="right"),
                rx.table.column_header_cell(S.tr["paisagem_col_borda"],
                                            text_align="right"),
                rx.table.column_header_cell(S.tr["paisagem_col_meff"],
                                            text_align="right"),
                rx.table.column_header_cell(S.tr["paisagem_col_shannon"],
                                            text_align="right"),
                rx.table.column_header_cell(S.tr["paisagem_col_simpson"],
                                            text_align="right"),
                rx.table.column_header_cell(S.tr["paisagem_col_evenness"],
                                            text_align="right"),
            )),
            rx.table.body(rx.foreach(
                S.landscape_table_rows,
                lambda r: rx.table.row(
                    rx.table.cell(rx.text(r["zone_label"], size="1")),
                    rx.table.cell(rx.text(r["area_ha"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["patches"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["patch_density"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["largest_pct"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["edge_density"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["meff_ha"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["shannon"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["simpson"], size="1"),
                                 text_align="right"),
                    rx.table.cell(rx.text(r["evenness"], size="1"),
                                 text_align="right"),
                ),
            )),
            size="1", width="100%", variant="surface",
        ),
        # No overflow_x here: used inside layout.split_panel, whose own
        # table wrapper is the single horizontal scroll container (see its
        # docstring) — a second one nested against it broke touch-drag
        # scrolling on phones. See the Brazil page's own results.py.
        spacing="1", width="100%",
    )


def _connectivity_section() -> rx.Component:
    return rx.vstack(
        rx.divider(),
        rx.hstack(
            rx.text(S.tr["connectivity_hint"], size="1", color=MUTED),
            rx.spacer(),
            rx.cond(S.connectivity_has_result,
                   table_export_button(S.download_connectivity_csv)),
            width="100%", align="center",
        ),
        rx.button(
            rx.icon("route", size=13),
            rx.cond(S.connectivity_running, S.tr["calculando"],
                   S.tr["connectivity_run_button"]),
            on_click=S.run_connectivity,
            loading=S.connectivity_running, disabled=S.connectivity_running,
            size="1", variant="soft", color_scheme="amber",
        ),
        rx.cond(
            S.connectivity_degraded,
            rx.callout(S.tr["connectivity_degraded"], icon="info",
                      color_scheme="gray", size="1"),
        ),
        rx.cond(
            S.connectivity_error != "",
            rx.callout(S.connectivity_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
            rx.cond(
                S.connectivity_has_result,
                rx.table.root(
                    rx.table.header(rx.table.row(
                        rx.table.column_header_cell(S.tr["paisagem_col_zona"]),
                        rx.table.column_header_cell(
                            S.tr["connectivity_n_fragments"], text_align="right"),
                        rx.table.column_header_cell(
                            S.tr["connectivity_enn_mean"], text_align="right"),
                        rx.table.column_header_cell(
                            S.tr["connectivity_enn_median"], text_align="right"),
                    )),
                    rx.table.body(rx.foreach(
                        S.connectivity_table_rows,
                        lambda r: rx.table.row(
                            rx.table.cell(rx.text(r["zone_label"], size="1")),
                            rx.table.cell(rx.text(r["n_fragments"], size="1"),
                                         text_align="right"),
                            rx.table.cell(rx.text(r["enn_mean"], size="1"),
                                         text_align="right"),
                            rx.table.cell(rx.text(r["enn_median"], size="1"),
                                         text_align="right"),
                        ),
                    )),
                    size="1", width="100%", variant="surface",
                ),
                rx.cond(
                    S.connectivity_running, rx.fragment(),
                    rx.text(S.tr["connectivity_empty"], size="1", color=MUTED),
                ),
            ),
        ),
        spacing="2", width="100%",
    )


def paisagem_tab() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(S.tr["paisagem_ano"], size="1", color=MUTED),
            rx.select(
                [str(y) for y in mb.ACI_YEARS],
                value=S.landscape_year.to_string(),
                on_change=S.set_landscape_year, size="1",
            ),
            _run_button(S.landscape_running, S.run_landscape_metrics),
            width="100%", align="center",
        ),
        rx.cond(
            S.landscape_error,
            rx.callout(S.landscape_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            S.landscape_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(S.tr["calculando"], size="2"), spacing="2"),
                height="200px",
            ),
            rx.cond(
                S.landscape_table_rows,
                split_panel(
                    chart_box(S.landscape_figure, "ca-plot-paisagem",
                             "camposcope_ca_paisagem", "260px"),
                    _paisagem_table(),
                ),
                rx.center(
                    rx.text(S.tr["paisagem_empty"], size="2", color=MUTED),
                    height="150px",
                ),
            ),
        ),
        _connectivity_section(),
        rx.text(S.tr["paisagem_legend_note"], size="1", color=MUTED),
        _map_layer_note(),
        rx.text(S.tr["paisagem_attribution"], size="1", color=MUTED),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# Fogo
# --------------------------------------------------------------------------- #
def _fire_stats() -> rx.Component:
    row = S.fire_table_rows[0]
    return rx.cond(
        S.fire_table_rows,
        rx.vstack(
            # Two static translation fragments around the numeric threshold,
            # not a "{min_ha}" template with .replace() — same reasoning as
            # parcel_card.py::_non_land_note.
            rx.cond(
                row["below_resolution"].to(bool),
                rx.callout(
                    f"{S.tr['fogo_below_resolution_prefix']}"
                    f"{int(FIRE_MIN_MEANINGFUL_HA)}"
                    f"{S.tr['fogo_below_resolution_suffix']}",
                    icon="info", color_scheme="gray", size="1",
                ),
            ),
            rx.hstack(
                rx.vstack(
                    rx.text(S.tr["fogo_historio_anos"], size="1", color=MUTED),
                    rx.text(f"{row['fire_history_pct']}%", size="3",
                           weight="bold", color="#d4271e"),
                    spacing="0",
                ),
                rx.vstack(
                    rx.text(S.tr["fogo_frequencia_ocorrencias"], size="1",
                           color=MUTED),
                    rx.text(row["fire_frequency"], size="3", weight="bold",
                           color="#d4271e"),
                    spacing="0",
                ),
                rx.vstack(
                    rx.text(S.tr["fogo_ultima_queimada"], size="1", color=MUTED),
                    rx.text(
                        rx.cond(row["fire_last_year"], row["fire_last_year"], "—"),
                        size="3", weight="bold", color="#8b1a1a"),
                    spacing="0",
                ),
                spacing="5", width="100%", wrap="wrap",
            ),
            spacing="3", width="100%",
        ),
    )


def _fire_source_switch() -> rx.Component:
    return rx.segmented_control.root(
        rx.segmented_control.item(S.tr["fogo_source_modis"], value="modis"),
        rx.segmented_control.item(S.tr["fogo_source_aci"], value="aci"),
        value=S.fire_source, on_change=S.set_fire_source, size="1",
    )


def _modis_section() -> rx.Component:
    return rx.vstack(
        rx.hstack(_run_button(S.fire_running, S.run_fire),
                 width="100%", align="start"),
        rx.cond(
            S.fire_error,
            rx.callout(S.fire_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            S.fire_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(S.tr["calculando"], size="2"), spacing="2"),
                height="200px",
            ),
            rx.cond(
                S.fire_rows,
                rx.vstack(
                    rx.hstack(
                        rx.spacer(),
                        rx.cond(S.fire_table_rows,
                               table_export_button(S.download_fogo_csv)),
                        width="100%",
                    ),
                    _fire_stats(),
                    chart_box(S.fire_figure, "ca-plot-fogo",
                             "camposcope_ca_fogo", "260px"),
                    rx.callout(
                        f"{S.tr['fogo_current_year_prefix']}{S.fire_current_year}"
                        f"{S.tr['fogo_current_year_suffix']}",
                        icon="info", color_scheme="amber", size="1",
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        rx.text(S.tr["fogo_attribution"], size="1", color=MUTED),
        spacing="3", width="100%",
    )


def _aci_burn_section() -> rx.Component:
    """The AAFC-source view — free once the Cobertura tab has fetched a
    parcel's history, since class 60 is just one more class in that already-
    fetched table (``canada/services/fire.py::aci_burn_rows``)."""
    return rx.vstack(
        rx.cond(
            S.has_history,
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text(S.tr["fogo_aci_years_detected"], size="1",
                               color=MUTED),
                        rx.text(S.aci_burn_years_detected, size="3",
                               weight="bold", color="#bd0026"),
                        spacing="0",
                    ),
                    rx.vstack(
                        rx.text(S.tr["fogo_aci_last_year"], size="1",
                               color=MUTED),
                        rx.text(
                            rx.cond(S.aci_burn_last_year, S.aci_burn_last_year,
                                   "—"),
                            size="3", weight="bold", color="#8b1a1a",
                        ),
                        spacing="0",
                    ),
                    spacing="5", width="100%", wrap="wrap",
                ),
                chart_box(S.aci_burn_figure, "ca-plot-fogo-aci",
                         "camposcope_ca_fogo_aci", "260px"),
                spacing="3", width="100%",
            ),
            rx.callout(S.tr["fogo_aci_empty"], icon="info",
                      color_scheme="gray", size="1"),
        ),
        rx.text(S.tr["fogo_aci_note"], size="1", color=MUTED),
        rx.text(S.tr["fogo_aci_attribution"], size="1", color=MUTED),
        spacing="3", width="100%",
    )


def fogo_tab() -> rx.Component:
    return rx.vstack(
        zone_selector(),
        _fire_source_switch(),
        rx.match(
            S.fire_source,
            ("aci", _aci_burn_section()),
            _modis_section(),
        ),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# Results panel
# --------------------------------------------------------------------------- #
def results_panel() -> rx.Component:
    return rx.cond(
        S.has_parcel,
        rx.box(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger(S.tr["tab_cobertura"], value="cobertura"),
                    rx.tabs.trigger(S.tr["tab_transicoes"], value="transicoes"),
                    rx.tabs.trigger(S.tr["tab_floresta"], value="floresta"),
                    rx.tabs.trigger(S.tr["tab_biomassa"], value="biomassa"),
                    rx.tabs.trigger(S.tr["tab_paisagem"], value="paisagem"),
                    rx.tabs.trigger(S.tr["tab_fogo"], value="fogo"),
                    rx.tabs.trigger(S.tr["tab_validacao"], value="validacao"),
                ),
                rx.tabs.content(cobertura_tab(), value="cobertura"),
                rx.tabs.content(transitions_tab(), value="transicoes"),
                rx.tabs.content(floresta_tab(), value="floresta"),
                rx.tabs.content(biomassa_tab(), value="biomassa"),
                rx.tabs.content(paisagem_tab(), value="paisagem"),
                rx.tabs.content(fogo_tab(), value="fogo"),
                rx.tabs.content(validacao_tab(), value="validacao"),
                value=S.results_tab, on_change=S.set_results_tab, width="100%",
            ),
            width="100%", border_top=BORDER, background="var(--color-panel)",
        ),
    )
