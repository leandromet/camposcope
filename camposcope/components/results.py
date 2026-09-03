"""Results: the zone selector and the four analysis tabs (doc/08-ui-ux.md §5).

Every tab uses the same shape — a smaller chart beside a data table
(``layout.split_panel``) rather than one full-width chart, so the numbers
behind a figure are always visible, not hidden behind a hover tooltip.
"""

from __future__ import annotations

import reflex as rx

from ..config import gbif as gbif_cfg
from ..config import mapbiomas as mb
from ..config.datasets import AGB_YEARS
from ..state import AppState
from .export_widgets import chart_box, table_export_button
from .fogo import fogo_tab
from .layout import BORDER, MUTED, split_panel, zone_selector
from .sankey import transitions_tab
from .validacao import validacao_tab


def _run_button(label_key: str, running_var, on_click) -> rx.Component:
    return rx.button(
        rx.cond(running_var, AppState.tr["calculando"], AppState.tr[label_key]),
        on_click=on_click, disabled=running_var, size="1",
    )


def _map_layer_note() -> rx.Component:
    """A one-line reminder that this tab's map layer can be turned on/off from
    the on-map legend, not repeated controls in every tab."""
    return rx.text(AppState.tr["map_layer_note"], size="1", color=MUTED)


# --------------------------------------------------------------------------- #
# Cobertura
# --------------------------------------------------------------------------- #
def _cobertura_table() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(AppState.tr["cobertura_ano"], size="1", color=MUTED),
            rx.select(
                [str(y) for y in mb.MAPBIOMAS_YEARS],
                value=AppState.mapbiomas_layer_year.to_string(),
                on_change=AppState.set_mapbiomas_layer_year,
                size="1",
            ),
            rx.spacer(),
            rx.cond(
                AppState.history_table_rows,
                table_export_button(AppState.download_cobertura_csv),
                rx.fragment(),
            ),
            spacing="2", align="center", width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(AppState.tr["cobertura_classe"]),
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
                                rx.text(r["class_label"], size="1"),
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
            rx.text(AppState.tr["cobertura_hectares"], size="1", color=MUTED),
            rx.switch(checked=AppState.history_normalise,
                     on_change=AppState.toggle_history_normalise, size="1"),
            rx.text(AppState.tr["cobertura_percentual"], size="1", color=MUTED),
            spacing="2", align="center",
        ),
        # More height below "md" than desktop's 260px: the figure's own
        # legend (charts.py's _style()) can wrap to several rows on a phone-
        # width chart where it only ever needed one on desktop — see that
        # function's own comment. `rx.plotly`'s `config.responsive` resizes
        # the plot to match *this* box's actual rendered height (not the
        # figure's own `layout.height`), so this is the number that actually
        # controls how much room the wrapped legend gets on a phone.
        chart_box(AppState.history_figure, "cs-plot-cobertura",
                 "camposcope_cobertura", ["360px", "360px", "260px", "260px"]),
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
            rx.callout(AppState.tr["cobertura_degraded"], icon="info",
                       color_scheme="gray", size="1"),
        ),
        rx.cond(
            AppState.history_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(AppState.tr["cobertura_running"], size="2"),
                         spacing="2"),
                height="260px",
            ),
            rx.cond(
                AppState.has_history,
                split_panel(_cobertura_chart(), _cobertura_table()),
                rx.center(
                    rx.text(AppState.tr["cobertura_empty"], size="2", color=MUTED),
                    height="200px",
                ),
            ),
        ),
        _map_layer_note(),
        rx.text(AppState.tr["cobertura_attribution"], size="1", color=MUTED, padding_bottom="2px"),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# Floresta — up to 2008 / 2008 até o registro / depois do registro
# --------------------------------------------------------------------------- #
def _period_stat(label, value_var, color: str) -> rx.Component:
    return rx.vstack(
        rx.text(label, size="1", color=MUTED),
        rx.text(f"{value_var} ha", size="3", weight="bold", color=color),
        spacing="0",
    )


def _floresta_table() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.spacer(),
            rx.cond(
                AppState.hansen_table_rows,
                table_export_button(AppState.download_floresta_csv),
                rx.fragment(),
            ),
            width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(AppState.tr["floresta_col_ano"]),
                    rx.table.column_header_cell(AppState.tr["floresta_col_perda"],
                                                text_align="right"),
                    rx.table.column_header_cell(AppState.tr["floresta_col_periodo"]),
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
        ),
        spacing="1", width="100%",
    )


def floresta_tab() -> rx.Component:
    """Hansen loss split into three periods anchored on the Forest Code's own
    2008 reference date and the property's CAR registration (doc/04 §3)."""
    return rx.vstack(
        zone_selector(),
        rx.hstack(
            _run_button("calcular", AppState.hansen_running, AppState.run_hansen),
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
                rx.hstack(rx.spinner(),
                         rx.text(AppState.tr["calculando"], size="2"),
                         spacing="2"),
                height="200px",
            ),
            rx.cond(
                AppState.hansen_has_run,
                rx.vstack(
                    rx.hstack(
                        _period_stat(AppState.tr["floresta_ate_2008"],
                                    AppState.hansen_loss_up_to_2008_ha, "#f5a524"),
                        _period_stat(AppState.tr["floresta_2008_ate_registro"],
                                    AppState.hansen_loss_2008_to_registration_ha,
                                    "#e5484d"),
                        _period_stat(AppState.tr["floresta_depois_registro"],
                                    AppState.hansen_loss_after_registration_ha,
                                    "#8b1a1a"),
                        _period_stat(AppState.tr["floresta_ganho_sem_data"],
                                    AppState.hansen_gain_ha, "#02d659"),
                        spacing="5", width="100%", wrap="wrap",
                    ),
                    split_panel(
                        chart_box(AppState.hansen_figure, "cs-plot-floresta",
                                 "camposcope_floresta", "230px"),
                        _floresta_table(),
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        _map_layer_note(),
        rx.text(AppState.tr["floresta_attribution"], size="1", color=MUTED, padding_bottom="2px"),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# Biomassa
# --------------------------------------------------------------------------- #
def _biomassa_table() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.spacer(),
            rx.cond(
                AppState.biomass_table_rows,
                table_export_button(AppState.download_biomassa_csv),
                rx.fragment(),
            ),
            width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(AppState.tr["biomassa_col_ano"]),
                    rx.table.column_header_cell(AppState.tr["biomassa_col_mg_ha"],
                                                text_align="right"),
                    rx.table.column_header_cell(AppState.tr["biomassa_col_total_mg"],
                                                text_align="right"),
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
        ),
        spacing="1", width="100%",
    )


def biomassa_tab() -> rx.Component:
    """ESA CCI Above-Ground Biomass — a series with a real gap, drawn as a
    gap (doc/04 §4)."""
    return rx.vstack(
        zone_selector(),
        rx.hstack(
            _run_button("calcular", AppState.biomass_running, AppState.run_biomass),
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
                rx.hstack(rx.spinner(),
                         rx.text(AppState.tr["calculando"], size="2"),
                         spacing="2"),
                height="200px",
            ),
            rx.cond(
                AppState.biomass_rows,
                split_panel(
                    chart_box(AppState.biomass_figure, "cs-plot-biomassa",
                             "camposcope_biomassa", "260px"),
                    _biomassa_table(),
                ),
            ),
        ),
        _map_layer_note(),
        rx.text(AppState.tr["biomassa_attribution"], size="1", color=MUTED, padding_bottom="2px"),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# Paisagem — landscape (fragmentation) metrics, always free, plus the costly
# fragment-to-fragment connectivity metric behind its own button.
# --------------------------------------------------------------------------- #
def _paisagem_table() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.spacer(),
            rx.cond(
                AppState.landscape_table_rows,
                table_export_button(AppState.download_paisagem_csv),
                rx.fragment(),
            ),
            width="100%",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(AppState.tr["paisagem_col_zona"]),
                    rx.table.column_header_cell(AppState.tr["paisagem_col_area"],
                                                text_align="right"),
                    rx.table.column_header_cell(AppState.tr["paisagem_col_fragmentos"],
                                                text_align="right"),
                    rx.table.column_header_cell(AppState.tr["paisagem_col_densidade"],
                                                text_align="right"),
                    rx.table.column_header_cell(AppState.tr["paisagem_col_maior"],
                                                text_align="right"),
                    rx.table.column_header_cell(AppState.tr["paisagem_col_borda"],
                                                text_align="right"),
                    rx.table.column_header_cell(AppState.tr["paisagem_col_meff"],
                                                text_align="right"),
                    rx.table.column_header_cell(AppState.tr["paisagem_col_shannon"],
                                                text_align="right"),
                    rx.table.column_header_cell(AppState.tr["paisagem_col_simpson"],
                                                text_align="right"),
                    rx.table.column_header_cell(AppState.tr["paisagem_col_evenness"],
                                                text_align="right"),
                ),
            ),
            rx.table.body(
                rx.foreach(
                    AppState.landscape_table_rows,
                    lambda r: rx.table.row(
                        rx.table.cell(rx.text(r["zone_label"], size="1")),
                        rx.table.cell(rx.text(r["area_ha"], size="1"), text_align="right"),
                        rx.table.cell(rx.text(r["patches"], size="1"), text_align="right"),
                        rx.table.cell(rx.text(r["patch_density"], size="1"), text_align="right"),
                        rx.table.cell(rx.text(r["largest_pct"], size="1"), text_align="right"),
                        rx.table.cell(rx.text(r["edge_density"], size="1"), text_align="right"),
                        rx.table.cell(rx.text(r["meff_ha"], size="1"), text_align="right"),
                        rx.table.cell(rx.text(r["shannon"], size="1"), text_align="right"),
                        rx.table.cell(rx.text(r["simpson"], size="1"), text_align="right"),
                        rx.table.cell(rx.text(r["evenness"], size="1"), text_align="right"),
                    ),
                ),
            ),
            size="1", width="100%", variant="surface",
        ),
        # No overflow_x here: this table is used inside layout.split_panel,
        # whose own table wrapper is now the single horizontal scroll
        # container (see its docstring) — a second one nested right against
        # it broke touch-drag scrolling on phones.
        spacing="1", width="100%",
    )


def _connectivity_row(r: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(r["zone_label"], size="1")),
        rx.table.cell(rx.text(r["n_fragments"], size="1"), text_align="right"),
        rx.table.cell(rx.text(r["enn_mean"], size="1"), text_align="right"),
        rx.table.cell(rx.text(r["enn_median"], size="1"), text_align="right"),
    )


def _connectivity_section() -> rx.Component:
    """The costly, opt-in half of landscape metrics — mean/median distance to
    the nearest forest fragment (services.connectivity), behind its own
    button rather than fetched alongside the table above."""
    return rx.vstack(
        rx.divider(),
        rx.hstack(
            rx.text(AppState.tr["connectivity_hint"], size="1", color=MUTED),
            rx.spacer(),
            rx.cond(
                AppState.connectivity_has_result,
                table_export_button(AppState.download_connectivity_csv),
                rx.fragment(),
            ),
            width="100%", align="center",
        ),
        rx.button(
            rx.icon("route", size=13),
            rx.cond(AppState.connectivity_running, AppState.tr["calculando"],
                   AppState.tr["connectivity_run_button"]),
            on_click=AppState.run_connectivity,
            loading=AppState.connectivity_running,
            disabled=AppState.connectivity_running,
            size="1", variant="soft", color_scheme="amber",
        ),
        rx.cond(
            AppState.connectivity_degraded,
            rx.callout(AppState.tr["connectivity_degraded"], icon="info",
                      color_scheme="gray", size="1"),
        ),
        rx.cond(
            AppState.connectivity_error != "",
            rx.callout(AppState.connectivity_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
            rx.cond(
                AppState.connectivity_has_result,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(AppState.tr["paisagem_col_zona"]),
                            rx.table.column_header_cell(
                                AppState.tr["connectivity_n_fragments"], text_align="right"),
                            rx.table.column_header_cell(
                                AppState.tr["connectivity_enn_mean"], text_align="right"),
                            rx.table.column_header_cell(
                                AppState.tr["connectivity_enn_median"], text_align="right"),
                        ),
                    ),
                    rx.table.body(rx.foreach(AppState.connectivity_table_rows,
                                             _connectivity_row)),
                    size="1", width="100%", variant="surface",
                ),
                rx.cond(
                    AppState.connectivity_running,
                    rx.fragment(),
                    rx.text(AppState.tr["connectivity_empty"], size="1", color=MUTED),
                ),
            ),
        ),
        spacing="2", width="100%",
    )


def paisagem_tab() -> rx.Component:
    """Landscape (fragmentation) metrics for every zone at once — the
    property, then its rings — plus the on-map patch layer
    (services/layers.py::landscape_patches_spec) so a user can see the same
    fragments the numbers describe."""
    return rx.vstack(
        rx.hstack(
            rx.text(AppState.tr["paisagem_ano"], size="1", color=MUTED),
            rx.select(
                [str(y) for y in mb.MAPBIOMAS_YEARS],
                value=AppState.landscape_year.to_string(),
                on_change=AppState.set_landscape_year,
                size="1",
            ),
            _run_button("calcular", AppState.landscape_running,
                       AppState.run_landscape_metrics),
            width="100%", align="center",
        ),
        rx.cond(
            AppState.landscape_error,
            rx.callout(AppState.landscape_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.landscape_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(AppState.tr["calculando"], size="2"),
                         spacing="2"),
                height="200px",
            ),
            rx.cond(
                AppState.landscape_table_rows,
                split_panel(
                    chart_box(AppState.landscape_figure, "cs-plot-paisagem",
                             "camposcope_paisagem", "260px"),
                    _paisagem_table(),
                ),
                rx.center(
                    rx.text(AppState.tr["paisagem_empty"], size="2", color=MUTED),
                    height="150px",
                ),
            ),
        ),
        _connectivity_section(),
        _map_layer_note(),
        rx.text(AppState.tr["paisagem_attribution"], size="1", color=MUTED, padding_bottom="2px"),
        spacing="3", width="100%", padding="3",
    )


# --------------------------------------------------------------------------- #
# GBIF — biodiversity occurrences
# --------------------------------------------------------------------------- #
def _kingdom_color(name: rx.Var) -> rx.Var:
    """A kingdom name → its map-dot colour, for the chip labels below.

    An ``rx.match`` rather than a Python dict lookup: ``name`` only exists as
    a value inside the browser (one row of ``AppState.gbif_zone_rows``,
    reached through ``rx.foreach``), so the lookup has to compile to a
    client-side expression, not run once at component-definition time.
    """
    return rx.match(
        name,
        *[(k, f"#{c}") for k, c in gbif_cfg.KINGDOM_COLORS.items()
          if k != "incertae sedis"],
        f"#{gbif_cfg.DEFAULT_COLOR}",
    )


def _kingdom_chip(k: rx.Var) -> rx.Component:
    color = _kingdom_color(k.name)
    return rx.badge(
        f"{k.name} · {k.count}",
        variant="outline", size="1",
        style={"color": color, "borderColor": color},
    )


def _kingdom_chips(row: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.foreach(row.kingdoms, _kingdom_chip),
        spacing="1", wrap="wrap",
    )


def _zone_species_table(row: rx.Var) -> rx.Component:
    return rx.cond(
        row.species_top.length() > 0,
        rx.scroll_area(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(AppState.tr["gbif_col_species"]),
                        rx.table.column_header_cell(AppState.tr["gbif_col_records"],
                                                    text_align="right"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        row.species_top,
                        lambda sp: rx.table.row(
                            rx.table.cell(rx.text(sp.name, size="1",
                                                  style={"fontStyle": "italic"})),
                            rx.table.cell(rx.text(sp.count_label, size="1"),
                                         text_align="right"),
                        ),
                    ),
                ),
                size="1", variant="ghost", width="100%",
            ),
            type="auto", scrollbars="vertical", style={"maxHeight": "220px"},
        ),
        rx.text(AppState.tr["gbif_zone_empty"], size="1", color=MUTED),
    )


def _zone_card(row: rx.Var) -> rx.Component:
    """One zone: the cumulative totals, the kingdom split, and its species
    table — the GBIF tab's counterpart to every other tab's chart+table
    pair, ``split_panel``'d the same way but as a card per zone instead,
    since there are four zones to show at once rather than one series."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(row.zone_label, color_scheme="jade", variant="solid",
                        size="2"),
                rx.spacer(),
                rx.vstack(
                    rx.text(row.total_label, size="3", weight="bold"),
                    rx.text(AppState.tr["gbif_records_word"], size="1", color=MUTED),
                    spacing="0", align_items="end",
                ),
                rx.vstack(
                    rx.text(row.richness_label, size="3", weight="bold"),
                    rx.text(AppState.tr["gbif_species_word"], size="1", color=MUTED),
                    spacing="0", align_items="end",
                ),
                width="100%", align="center", spacing="4",
            ),
            rx.cond(
                row.error != "",
                rx.callout(row.error, icon="triangle-alert", color_scheme="amber",
                          size="1"),
            ),
            _kingdom_chips(row),
            _zone_species_table(row),
            spacing="2", width="100%", align_items="stretch",
        ),
        width="100%",
    )


def gbif_tab() -> rx.Component:
    """Species recorded in GBIF, one cumulative zone at a time — "Calcular"
    fans out one facet query per zone (state/_gbif.py::run_gbif_species,
    services/gbif_species.py). Independent of the on-map point layer
    (state/_layers.py::gbif_vectors), which needs no run and appears as soon
    as this tab is selected."""
    return rx.vstack(
        rx.hstack(
            _run_button("calcular", AppState.gbif_running, AppState.run_gbif_species),
            rx.spacer(),
            # Only once there is something to export — two dead buttons
            # beside a "calcular" call to action read as broken rather than
            # as not-yet-applicable.
            rx.cond(
                AppState.gbif_zone_rows.length() > 0,
                rx.hstack(
                    rx.tooltip(
                        rx.button(
                            rx.icon("table", size=14), "ODS",
                            size="1", variant="soft", color_scheme="gray",
                            on_click=AppState.download_gbif_species_ods,
                        ),
                        content=AppState.tr["gbif_export_ods_hint"],
                    ),
                    rx.tooltip(
                        rx.button(
                            rx.icon("download", size=14), "CSV",
                            size="1", variant="soft", color_scheme="gray",
                            on_click=AppState.download_gbif_species_csv,
                        ),
                        content=AppState.tr["gbif_export_csv_hint"],
                    ),
                    spacing="2", align="center",
                ),
                rx.fragment(),
            ),
            width="100%", align="center",
        ),
        rx.text(AppState.tr["gbif_cumulative_note"], size="1", color=MUTED),
        rx.cond(
            AppState.gbif_error,
            rx.callout(AppState.gbif_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.gbif_export_error != "",
            rx.callout(AppState.gbif_export_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.gbif_running,
            rx.center(
                rx.hstack(rx.spinner(),
                         rx.text(AppState.tr["calculando"], size="2"),
                         spacing="2"),
                height="200px",
            ),
            rx.cond(
                AppState.gbif_zone_rows,
                rx.grid(
                    rx.foreach(AppState.gbif_zone_rows, _zone_card),
                    columns=rx.breakpoints(initial="1", md="2"),
                    spacing="3", width="100%",
                ),
                rx.center(
                    rx.text(AppState.tr["gbif_empty"], size="2", color=MUTED),
                    height="150px",
                ),
            ),
        ),
        rx.callout(AppState.tr["gbif_zoom_note"], icon="zoom-in", size="1",
                  color_scheme="blue"),
        _map_layer_note(),
        rx.text(AppState.tr["gbif_attribution"], size="1", color=MUTED, padding_bottom="2px"),
        spacing="3", width="100%", padding="3",
    )


def _tab_trigger_with_hint(label, value: str, hint) -> rx.Component:
    """A tabs.trigger with a small info icon carrying an explanatory
    tooltip — the tooltip can't wrap the trigger itself (Reflex enforces
    tabs.trigger's parent to be tabs.list at the component level), so the
    icon lives *inside* the trigger instead, right next to the label.
    Ported from naturametrics' same helper."""
    return rx.tabs.trigger(
        rx.hstack(
            rx.text(label),
            rx.tooltip(
                rx.icon("info", size=12, color="var(--gray-9)"),
                content=hint,
            ),
            spacing="1", align="center",
        ),
        value=value,
    )


def results_panel() -> rx.Component:
    return rx.cond(
        AppState.has_imovel,
        rx.box(
            rx.tabs.root(
                rx.tabs.list(
                    _tab_trigger_with_hint(
                        AppState.tr["tab_cobertura"], "cobertura",
                        AppState.tr["tab_cobertura_hint"]),
                    _tab_trigger_with_hint(
                        AppState.tr["tab_transicoes"], "transicoes",
                        AppState.tr["tab_transicoes_hint"]),
                    _tab_trigger_with_hint(
                        AppState.tr["tab_floresta"], "floresta",
                        AppState.tr["tab_floresta_hint"]),
                    _tab_trigger_with_hint(
                        AppState.tr["tab_biomassa"], "biomassa",
                        AppState.tr["tab_biomassa_hint"]),
                    _tab_trigger_with_hint(
                        AppState.tr["tab_paisagem"], "paisagem",
                        AppState.tr["tab_paisagem_hint"]),
                    _tab_trigger_with_hint(
                        AppState.tr["tab_fogo"], "fogo",
                        AppState.tr["tab_fogo_hint"]),
                    _tab_trigger_with_hint(
                        AppState.tr["tab_validacao"], "validacao",
                        AppState.tr["tab_validacao_hint"]),
                    _tab_trigger_with_hint(
                        AppState.tr["tab_gbif"], "gbif",
                        AppState.tr["tab_gbif_hint"]),
                ),
                rx.tabs.content(cobertura_tab(), value="cobertura"),
                rx.tabs.content(transitions_tab(), value="transicoes"),
                rx.tabs.content(floresta_tab(), value="floresta"),
                rx.tabs.content(biomassa_tab(), value="biomassa"),
                rx.tabs.content(paisagem_tab(), value="paisagem"),
                rx.tabs.content(fogo_tab(), value="fogo"),
                rx.tabs.content(validacao_tab(), value="validacao"),
                rx.tabs.content(gbif_tab(), value="gbif"),
                value=AppState.results_tab,
                on_change=AppState.set_results_tab,
                width="100%",
            ),
            width="100%",
            border_top=BORDER,
            background="var(--color-panel)",
        ),
    )
