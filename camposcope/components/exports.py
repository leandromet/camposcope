"""The download dialog: the property workbook and the paper-friendly report.

Ported in structure from Naturametrics' ``components/exports.py`` — a dialog
rather than a sidebar section, same reason: the sidebar already carries the
search panel and results tabs, and this sits beside "Como citar" in the
header instead. Camposcope has no multi-property selection (see
``services/exports.py``'s own docstring), so unlike Naturametrics there is
only one section here, not two.
"""

from __future__ import annotations

import reflex as rx

from ..state import AppState


def _check(label: str, detail: str, checked, on_change) -> rx.Component:
    return rx.hstack(
        rx.checkbox(checked=checked, on_change=on_change, size="2",
                    color_scheme="grass", margin_top="2px"),
        rx.vstack(
            rx.text(label, size="2", weight="medium"),
            rx.text(detail, size="1", color="var(--gray-11)",
                    style={"lineHeight": "1.35"}),
            spacing="0", align_items="start",
        ),
        spacing="3", align_items="start", width="100%",
    )


def _status() -> rx.Component:
    return rx.vstack(
        rx.cond(
            AppState.export_busy,
            rx.hstack(
                rx.spinner(size="1"),
                rx.text(AppState.export_stage, size="1"),
                spacing="2", align="center", width="100%",
            ),
            rx.fragment(),
        ),
        rx.cond(
            AppState.export_error != "",
            rx.callout(AppState.export_error, icon="triangle-alert",
                      color_scheme="red", size="1", width="100%"),
            rx.fragment(),
        ),
        rx.cond(
            AppState.export_result != "",
            rx.callout(AppState.export_result, icon="circle-check",
                      color_scheme="grass", size="1", width="100%"),
            rx.fragment(),
        ),
        spacing="2", width="100%",
    )


def export_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("download", size=15),
                rx.text(AppState.tr["download_button"],
                       display=["none", "none", "block", "block"]),
                size="1", variant="soft", color_scheme="gray",
                aria_label=AppState.tr["download_button"],
            )
        ),
        rx.dialog.content(
            rx.dialog.title(AppState.tr["export_dialog_title"]),
            rx.dialog.description(
                AppState.tr["export_dialog_desc"],
                size="2", color="var(--gray-11)", margin_bottom="0.75rem",
            ),
            rx.scroll_area(
                rx.vstack(
                    rx.hstack(
                        rx.text(AppState.imovel["cod_imovel"], size="2", weight="bold"),
                        rx.spacer(),
                        rx.cond(
                            AppState.has_imovel,
                            rx.badge(AppState.imovel["municipio"], size="1",
                                    variant="soft", color_scheme="grass"),
                            rx.badge(AppState.tr["download_workbook_hint"], size="1",
                                    variant="soft", color_scheme="gray"),
                        ),
                        width="100%", align="center",
                    ),
                    rx.text(AppState.tr["workbook_desc"], size="1",
                           color="var(--gray-11)", style={"lineHeight": "1.45"}),
                    _check(
                        AppState.tr["check_gbif_label"],
                        AppState.tr["check_gbif_detail"],
                        AppState.exp_include_gbif, AppState.toggle_exp_include_gbif,
                    ),
                    rx.button(
                        rx.icon("download", size=14),
                        AppState.tr["download_workbook_button"],
                        on_click=AppState.download_imovel_workbook,
                        disabled=~AppState.has_imovel | AppState.export_busy,
                        size="2", color_scheme="grass", width="100%",
                    ),

                    rx.divider(),
                    rx.text(AppState.tr["report_section_title"], size="2",
                           weight="medium"),
                    rx.text(AppState.tr["report_section_desc"], size="1",
                           color="var(--gray-11)", style={"lineHeight": "1.4"}),
                    _check(
                        AppState.tr["check_report_figures_label"],
                        AppState.tr["check_report_figures_detail"],
                        AppState.exp_report_figures, AppState.toggle_exp_report_figures,
                    ),
                    _check(
                        AppState.tr["check_report_tables_label"],
                        AppState.tr["check_report_tables_detail"],
                        AppState.exp_report_tables, AppState.toggle_exp_report_tables,
                    ),
                    rx.button(
                        rx.icon("file-text", size=14),
                        AppState.tr["download_report_button"],
                        on_click=AppState.download_imovel_report,
                        disabled=(~AppState.has_imovel | AppState.export_busy
                                 | ~AppState.export_report_any),
                        size="2", variant="soft", color_scheme="grass", width="100%",
                    ),

                    rx.divider(),
                    _status(),
                    spacing="4", align_items="start", width="100%",
                ),
                type="auto", scrollbars="vertical",
                style={"maxHeight": "62vh", "paddingRight": "1rem"},
            ),
            rx.flex(
                # A plain button driving export_open directly, not
                # rx.dialog.close — Naturametrics' components/exports.py hit
                # a prop-cloning issue with Dialog.Close on a button whose
                # on_click also needs to reset export-panel state; the same
                # shape is used here defensively even though Camposcope's own
                # citation dialog uses rx.dialog.close without trouble (it
                # has no state to reset on close).
                rx.button(AppState.tr["export_close_button"], size="2", variant="soft",
                         on_click=AppState.set_export_open(False)),
                justify="end", margin_top="1rem",
            ),
            max_width=["94vw", "94vw", "480px", "480px"],
        ),
        open=AppState.export_open,
        on_open_change=AppState.set_export_open,
    )
