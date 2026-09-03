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

from ..config import gbif as gbif_cfg
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
    # Collapsed this box is just "LEGENDA ⌄", so the 180px floor the
    # expanded panel wants would leave a wide empty bar sitting over the
    # map — exactly the clutter collapsing it is meant to remove.
    min_width=rx.cond(AppState.legend_open, "180px", "0"),  # drawer (1000) —
                             # see pages/index.py's own note.
    # Collapsed, this box is just its header row; expanded on a phone it was
    # free to grow to whatever the widest class label happened to be and to
    # run off the bottom of the screen. Both are capped here rather than on
    # the inner panels so every tab's legend obeys the same bounds.
    max_width=["62vw", "62vw", "240px", "240px"],
    max_height="60vh",
    overflow_y="auto",
    font_size="0.75rem",
)


def _layer_switch() -> rx.Component:
    """The active layer's on/off toggle. Every tab's panel used to open with
    its own title-plus-switch row; the title moved up into
    ``_collapse_header`` (where it stays readable with the panel closed) and
    the switch came with it, so this is now used once, there, rather than
    seven times below. The layer it toggles is the same in every tab —
    ``analysis_layer_enabled`` is a single layer slot re-minted per tab
    (state/_layers.py::mint_analysis_layer)."""
    return rx.switch(checked=AppState.analysis_layer_enabled,
                     on_change=AppState.toggle_analysis_layer, size="1")


def _swatch_row(color: str, label) -> rx.Component:
    return rx.hstack(
        rx.box(width="10px", height="10px", border_radius="2px",
              background=color, flex_shrink="0"),
        rx.text(label, size="1"),
        spacing="2", align="center",
    )


def _class_legend_rows(rows: rx.Var) -> rx.Component:
    """Colour + label + share for whichever classes are actually present in
    the active zone/year — capped at 8 and scrollable, rather than every code
    in the full palette (60+ MapBiomas classes, 200+ AAFC ones): a property
    only ever shows a handful, and listing the rest would be noise."""
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
        rx.select(
            [str(y) for y in mb.MAPBIOMAS_YEARS],
            value=AppState.mapbiomas_layer_year.to_string(),
            on_change=AppState.set_mapbiomas_layer_year,
            size="1", width="100%",
        ),
        rx.cond(
            AppState.history_table_rows,
            _class_legend_rows(AppState.history_table_rows),
            rx.text(AppState.tr["legend_mapbiomas_palette"], size="1",
                   color="var(--gray-11)"),
        ),
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
            rx.text(AppState.tr["legend_spot_2008"], size="1", weight="medium"),
            rx.spacer(),
            rx.switch(checked=is_spot, on_change=AppState.toggle_spot_basemap,
                     size="1"),
            width="100%", align="center",
        ),
        rx.cond(
            AppState.basemap_busy,
            rx.hstack(rx.spinner(size="1"),
                     rx.text(AppState.tr["legend_loading"], size="1"),
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
                    rx.cond(AppState.spot_running, AppState.tr["legend_verifying"],
                           AppState.tr["legend_verify_coverage"]),
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
                                f"{AppState.tr['legend_spot_before_cutoff']}",
                                size="1", weight="medium",
                            ),
                            spacing="1",
                        ),
                        rx.text(AppState.tr["legend_no_coverage"], size="1",
                               color="var(--gray-11)"),
                    ),
                ),
                rx.text(AppState.tr["validacao_no_verdict_short"], size="1",
                       color="var(--gray-11)"),
                spacing="2", width="100%",
            ),
        ),
        spacing="2", width="100%",
    )


def _floresta_legend() -> rx.Component:
    return rx.vstack(
        rx.segmented_control.root(
            rx.segmented_control.item(AppState.tr["legend_hansen_since_2008"],
                                      value="2008"),
            rx.segmented_control.item(AppState.tr["legend_hansen_since_registro"],
                                      value="registro"),
            value=AppState.hansen_layer_mode,
            on_change=AppState.set_hansen_layer_mode,
            size="1", width="100%",
        ),
        _swatch_row("#d4271e", AppState.tr["legend_perda"]),
        _swatch_row("#02d659", AppState.tr["legend_ganho_sem_data"]),
        _spot_section(),
        spacing="2", width="100%",
    )


def _biomassa_legend() -> rx.Component:
    return rx.vstack(
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


def _fire_legend() -> rx.Component:
    """Fire frequency legend — same 6-stop palette as
    services/layers.py::fire_frequency_spec, so the on-map colours and this
    swatch never drift apart."""
    return rx.vstack(
        rx.hstack(
            rx.box(width="60px", height="8px", border_radius="2px",
                  background="linear-gradient(to right, #ffffb2, "
                            "#fecc5c, #fd8d3c, #f03b20, #bd0026, #800026)"),
            spacing="2", align="center",
        ),
        rx.hstack(
            rx.text("1", size="1", color="var(--gray-11)"),
            rx.spacer(),
            rx.text("15+", size="1", color="var(--gray-11)"),
            width="100%",
        ),
        rx.text(AppState.tr["legend_fogo_ocorrencias"], size="1", color="var(--gray-11)"),
        spacing="2", width="100%",
    )


def _transicoes_legend() -> rx.Component:
    """Older year on the left of the swipe divider, newer on the right — the
    same `sankey_year_a`/`sankey_year_b` the two-stage Sankey uses, so this
    legend has nothing of its own to set, only to say what is showing."""
    return rx.vstack(
        rx.cond(
            AppState.map_swipe_enabled,
            rx.hstack(
                rx.text(AppState.sankey_year_left, size="1", weight="medium"),
                rx.icon("move-horizontal", size=12),
                rx.text(AppState.sankey_year_right, size="1", weight="medium"),
                spacing="2", align="center",
            ),
            rx.text(AppState.tr["legend_choose_years"], size="1",
                   color="var(--gray-11)"),
        ),
        rx.text(AppState.tr["legend_drag_to_compare"], size="1",
               color="var(--gray-11)"),
        spacing="2", width="100%",
    )


def _paisagem_legend() -> rx.Component:
    """No swatch/gradient — unlike every sibling legend, this layer's colour
    (``services/layers.py::landscape_patches_spec``) is an arbitrary
    ``labels.mod(palette)`` hash with no fixed meaning to key a legend to
    (patch A being red says nothing beyond "different patch from its
    neighbour"). So this is on/off only, same header every other legend
    uses for its own toggle."""
    # Nothing but the title and the layer switch, both of which now live in
    # `_collapse_header` — so this tab's panel body is genuinely empty.
    return rx.fragment()


def _gbif_legend() -> rx.Component:
    """Kingdom colour key plus the zoom gate — the dots
    (services/gbif.py::vector_spec) are meaningless without knowing which
    kingdom each colour is, and the layer draws nothing below
    ``GBIF_MIN_ZOOM``."""
    return rx.vstack(
        *[
            _swatch_row(f"#{color}", kingdom)
            for kingdom, color in gbif_cfg.KINGDOM_COLORS.items()
            if kingdom != "incertae sedis"
        ],
        rx.text(AppState.tr["legend_gbif_zoom_note"], size="1",
               color="var(--gray-11)"),
        spacing="2", width="100%",
    )


def _validacao_side(title, rows: rx.Var, fallback) -> rx.Component:
    """One side of the swipe divider: its own header plus real classes when
    available, or a hint for why there is nothing to show yet."""
    return rx.vstack(
        rx.text(title, size="1", weight="medium"),
        rx.cond(rows, _class_legend_rows(rows), fallback),
        spacing="1", width="100%",
    )


def _validacao_legend() -> rx.Component:
    """Left/right is fixed by the pairing (reference on the left, checked
    classification on the right), not a free choice — but which SPOT mosaic
    sits on the left in spot_2008 mode IS a choice, so unlike Transições this
    legend carries one control, mirroring the same switch in the Validação
    tab (components/validacao.py::_spot_band_switch).

    Each side gets its own real class swatches, not just a label — SPOT is
    the one exception (imagery, nothing to classify): spot_2008 mode's left
    side stays label-only, but its MapBiomas-2008 right side gets swatches
    the same as ibge_2022's both sides do (state._analysis.py's
    validacao_ibge_classes / validacao_mb_classes / validacao_spot_mb_classes)."""
    return rx.vstack(
        rx.cond(
            AppState.validacao_mode == "spot_2008",
            rx.segmented_control.root(
                rx.segmented_control.item(AppState.tr["legend_visual"],
                                          value="visual"),
                rx.segmented_control.item(AppState.tr["legend_falsa_cor"],
                                          value="analytic"),
                value=AppState.spot_band_mode,
                on_change=AppState.set_spot_band_mode,
                size="1", width="100%",
            ),
        ),
        rx.cond(
            AppState.map_swipe_enabled,
            rx.cond(
                AppState.validacao_mode == "spot_2008",
                rx.vstack(
                    rx.text("SPOT 2008", size="1", weight="medium"),
                    _validacao_side(
                        "MapBiomas 2008", AppState.validacao_spot_mb_classes,
                        rx.text(AppState.tr["legend_run_cobertura"], size="1",
                               color="var(--gray-11)"),
                    ),
                    spacing="2", width="100%",
                ),
                rx.vstack(
                    _validacao_side(
                        "IBGE", AppState.validacao_ibge_classes,
                        rx.text(AppState.tr["legend_run_calcular"], size="1",
                               color="var(--gray-11)"),
                    ),
                    _validacao_side(
                        "MapBiomas 2022", AppState.validacao_mb_classes,
                        rx.text(AppState.tr["legend_run_calcular"], size="1",
                               color="var(--gray-11)"),
                    ),
                    spacing="2", width="100%",
                ),
            ),
            rx.text(AppState.tr["legend_choose_mode"], size="1",
                   color="var(--gray-11)"),
        ),
        rx.text(AppState.tr["legend_drag_to_compare"], size="1",
               color="var(--gray-11)"),
        spacing="2", width="100%",
    )


#: Asked once per session, from the browser, when the legend first mounts.
#: A Reflex state default is one Python value with no idea what it is being
#: rendered on, and this default genuinely differs by screen: on desktop the
#: legend is a small box in a large corner; on a phone the same box covers a
#: third of the only map there is, over exactly the pixels a legend is
#: describing. 768px is Radix's own `md`, the cutoff the rest of this app
#: already splits mobile from desktop on.
_NARROW_VIEWPORT_JS = "window.innerWidth < 768"


def _active_layer_title() -> rx.Component:
    """What the legend is currently describing, for the collapse row.

    Not the generic word "legend": this app shows exactly ONE map layer at a
    time and swaps it with the active results tab (`map_legend`'s `rx.match`
    below), so each tab's own panel already opens with its layer's name —
    "MapBiomas", "Floresta — Hansen", and so on. A second, generic header
    above that would just say the same thing twice while expanded, and while
    COLLAPSED it would be strictly worse: the one line still on screen would
    no longer tell you which of seven layers is painted on the map. Same
    strings the panels used to open with themselves, before that row moved
    up here.
    """
    return rx.match(
        AppState.results_tab,
        ("cobertura", rx.text(AppState.tr["legend_mapbiomas"])),
        ("transicoes", rx.text(AppState.tr["legend_mapbiomas_comparacao"])),
        ("floresta", rx.text(AppState.tr["legend_floresta_hansen"])),
        ("biomassa", rx.text(AppState.tr["legend_biomassa_esa"])),
        ("paisagem", rx.text(AppState.tr["legend_paisagem_fragmentos"])),
        ("fogo", rx.text(AppState.tr["legend_fogo_frequencia"])),
        ("validacao", rx.text(
            rx.cond(
                AppState.validacao_mode == "spot_2008",
                AppState.tr["validacao_mode_spot"],
                AppState.tr["validacao_mode_ibge"],
            ),
        )),
        ("gbif", rx.text(AppState.tr["legend_gbif"])),
        rx.text(AppState.tr["legend_title"]),
    )


def _collapse_header() -> rx.Component:
    """The legend's own title bar, and its only collapse affordance.

    The whole row is the control, not a small chevron button inside it —
    a legend on a phone is competing with the map for touch targets, and the
    row is already there.
    """
    return rx.hstack(
        rx.icon("list", size=13, color="var(--gray-11)", flex_shrink="0"),
        rx.box(
            _active_layer_title(),
            style={
                "fontSize": "var(--font-size-1)",
                "fontWeight": "bold",
                "color": "var(--gray-11)",
                "textTransform": "uppercase",
                "letterSpacing": "0.06em",
                "whiteSpace": "nowrap",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
                "minWidth": "0",
            },
        ),
        rx.spacer(),
        # The layer's own on/off switch, hoisted out of the panels below so it
        # is still reachable with the legend collapsed — turning a layer off
        # is the single most likely reason to be looking at this box on a
        # phone, and it should not require expanding the thing that is in the
        # way. `on_click` stops here: the switch drives its own state, and
        # letting the click bubble to the row would toggle the panel open or
        # shut every time a layer is switched.
        rx.box(
            _layer_switch(),
            on_click=rx.stop_propagation,
            display="flex", align_items="center", flex_shrink="0",
        ),
        rx.icon(
            "chevron-down", size=14, color="var(--gray-11)", flex_shrink="0",
            style={
                "transition": "transform 150ms ease",
                "transform": rx.cond(AppState.legend_open,
                                     "rotate(180deg)", "rotate(0deg)"),
            },
        ),
        on_click=AppState.toggle_legend,
        role="button",
        tab_index=0,
        cursor="pointer",
        aria_expanded=AppState.legend_open.to_string(),
        aria_label=rx.cond(AppState.legend_open,
                           AppState.tr["legend_collapse_aria"],
                           AppState.tr["legend_expand_aria"]),
        width="100%", spacing="2", align="center",
        # A touch target, not a text row: 28px is the same height the
        # sidebar's own collapse control uses (pages/index.py::_sidebar).
        min_height="28px",
    )


def map_legend() -> rx.Component:
    """Shown only once a property is selected and the active tab has a map
    layer of its own.

    Collapsible, and collapsed by default on a phone — see
    `_NARROW_VIEWPORT_JS` and `AppState.adopt_viewport`. Collapsing leaves
    the header row in place rather than hiding the box outright: a legend
    that vanishes completely needs a *second* affordance somewhere else to
    bring it back, and there is no room on this map for one.
    """
    return rx.cond(
        AppState.has_imovel,
        rx.box(
            _collapse_header(),
            rx.cond(
                AppState.legend_open,
                rx.box(
                    rx.match(
                        AppState.results_tab,
                        ("cobertura", _cobertura_legend()),
                        ("transicoes", _transicoes_legend()),
                        ("floresta", _floresta_legend()),
                        ("biomassa", _biomassa_legend()),
                        ("paisagem", _paisagem_legend()),
                        ("fogo", _fire_legend()),
                        ("validacao", _validacao_legend()),
                        ("gbif", _gbif_legend()),
                        rx.fragment(),
                    ),
                    padding_top="6px",
                ),
            ),
            on_mount=rx.call_script(_NARROW_VIEWPORT_JS,
                                   callback=AppState.adopt_viewport),
            **_BOX_STYLE,
        ),
    )
