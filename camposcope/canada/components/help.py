"""Header dialogs for the Canada page: how to use, how to cite, export.

Adds a **"how to use" dialog** the Brazil page does not have — the user's own
requirement for this page, placed next to "how to cite" the way the analogous
Naturametrics Canada page does it (see this project's CLAUDE.md).
"""

from __future__ import annotations

import reflex as rx

from ..config.citation import (
    CITATION_TEXT_EN, CITATION_TEXT_PT, DATA_SOURCES_EN, DATA_SOURCES_PT,
)
from ..state import CanadaState as S


def _step(number: str, title, body) -> rx.Component:
    return rx.hstack(
        rx.badge(number, color_scheme="jade", variant="solid", size="1",
                style={"minWidth": "22px", "justifyContent": "center"}),
        rx.vstack(
            rx.text(title, size="2", weight="bold"),
            rx.text(body, size="2", color_scheme="gray"),
            spacing="1", align_items="start",
        ),
        spacing="3", align_items="start", width="100%",
    )


def how_to_use_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("circle-help", size=15),
                rx.text(S.tr["help_trigger"],
                        display=["none", "none", "block", "block"]),
                size="1", variant="soft", color_scheme="gray",
                aria_label=S.tr["help_trigger"],
            )
        ),
        rx.dialog.content(
            rx.dialog.title(S.tr["help_dialog_title"]),
            rx.dialog.description(S.tr["help_dialog_desc"], size="2",
                                  color_scheme="gray", margin_bottom="0.75rem"),
            rx.scroll_area(
                rx.vstack(
                    _step("1", S.tr["help_step1_title"], S.tr["help_step1_body"]),
                    _step("2", S.tr["help_step2_title"], S.tr["help_step2_body"]),
                    _step("3", S.tr["help_step3_title"], S.tr["help_step3_body"]),
                    _step("4", S.tr["help_step4_title"], S.tr["help_step4_body"]),
                    _step("5", S.tr["help_step5_title"], S.tr["help_step5_body"]),
                    _step("6", S.tr["help_step6_title"], S.tr["help_step6_body"]),
                    _step("7", S.tr["help_step7_title"], S.tr["help_step7_body"]),
                    rx.divider(),
                    rx.text(S.tr["help_limitations_title"], size="2", weight="bold"),
                    rx.unordered_list(
                        rx.list_item(S.tr["help_limit_1"]),
                        rx.list_item(S.tr["help_limit_2"]),
                        rx.list_item(S.tr["help_limit_3"]),
                        rx.list_item(S.tr["help_limit_4"]),
                        font_size="var(--font-size-2)", color="var(--gray-11)",
                    ),
                    spacing="4", align_items="start", width="100%",
                ),
                type="auto", scrollbars="vertical",
                style={"maxHeight": "60vh", "paddingRight": "1rem"},
            ),
            rx.flex(
                # A plain button driving state directly, not rx.dialog.close —
                # Dialog.Close's Radix "asChild" prop-cloning never reaches a
                # button Reflex has extracted into its own standalone helper
                # component. See naturametrics/components/help.py for the trace.
                rx.button(S.tr["close_button"], size="2", variant="soft",
                         on_click=S.set_help_open(False)),
                justify="end", margin_top="1rem",
            ),
            max_width=["94vw", "94vw", "640px", "640px"],
        ),
        open=S.help_open, on_open_change=S.set_help_open,
    )


def _source_row(name_pt: str, desc_pt: str, url_pt: str,
                name_en: str, desc_en: str, url_en: str) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(rx.cond(S.language == "pt", name_pt, name_en),
                    size="2", weight="medium"),
            rx.link(rx.icon("external-link", size=12),
                   href=rx.cond(S.language == "pt", url_pt, url_en),
                   is_external=True),
            spacing="1", align="center",
        ),
        rx.text(rx.cond(S.language == "pt", desc_pt, desc_en),
               size="1", color="var(--gray-11)"),
        spacing="0", align_items="start", width="100%",
    )


def how_to_cite_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("quote", size=15),
                rx.text(S.tr["cite_trigger"],
                        display=["none", "none", "block", "block"]),
                size="1", variant="soft", color_scheme="gray",
            )
        ),
        rx.dialog.content(
            rx.dialog.title(S.tr["cite_dialog_title"]),
            rx.dialog.description(S.tr["cite_dialog_desc"], size="2",
                                  color="var(--gray-11)", margin_bottom="0.75rem"),
            rx.scroll_area(
                rx.vstack(
                    rx.text(S.tr["cite_example_title"], size="2", weight="bold"),
                    rx.box(
                        rx.text(rx.cond(S.language == "pt", CITATION_TEXT_PT,
                                       CITATION_TEXT_EN),
                               size="2", style={"lineHeight": "1.6"}),
                        padding="0.75rem", background="var(--gray-3)",
                        border_radius="6px", width="100%",
                    ),
                    rx.button(
                        rx.icon("copy", size=13),
                        rx.cond(S.language == "pt", "Copiar citação",
                               "Copy citation"),
                        on_click=rx.set_clipboard(
                            rx.cond(S.language == "pt", CITATION_TEXT_PT,
                                   CITATION_TEXT_EN)),
                        size="1", variant="soft", color_scheme="jade",
                    ),

                    rx.divider(),
                    rx.text(S.tr["cite_sources_title"], size="2", weight="bold"),
                    rx.text(S.tr["cite_sources_desc"], size="1",
                           color="var(--gray-11)"),
                    rx.vstack(
                        *[
                            _source_row(n_pt, d_pt, u_pt, n_en, d_en, u_en)
                            for (n_pt, d_pt, u_pt), (n_en, d_en, u_en)
                            in zip(DATA_SOURCES_PT, DATA_SOURCES_EN)
                        ],
                        spacing="3", align_items="start", width="100%",
                    ),
                    spacing="3", align_items="start", width="100%",
                ),
                type="auto", scrollbars="vertical",
                style={"maxHeight": "60vh", "paddingRight": "1rem"},
            ),
            rx.flex(
                rx.button(S.tr["close_button"], size="2", variant="soft",
                         on_click=S.set_cite_open(False)),
                justify="end", margin_top="1rem",
            ),
            max_width=["94vw", "94vw", "620px", "620px"],
        ),
        open=S.cite_open, on_open_change=S.set_cite_open,
    )


def export_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("download", size=15),
                rx.text(S.tr["download_button"],
                        display=["none", "none", "block", "block"]),
                size="1", variant="soft", color_scheme="gray",
            )
        ),
        rx.dialog.content(
            rx.dialog.title(S.tr["export_dialog_title"]),
            rx.dialog.description(S.tr["export_dialog_desc"], size="2",
                                  color="var(--gray-11)"),
            rx.flex(
                rx.button(S.tr["close_button"], size="2", variant="soft",
                         on_click=S.set_export_open(False)),
                justify="end", margin_top="1rem",
            ),
            max_width=["94vw", "94vw", "480px", "480px"],
        ),
        open=S.export_open, on_open_change=S.set_export_open,
    )


def header_actions() -> rx.Component:
    return rx.hstack(export_dialog(), how_to_use_dialog(), how_to_cite_dialog(),
                     spacing="2")
