""""Como citar" — Camposcope's own citation, and every dataset it draws on.

Discharges constraint C4 (doc/01-premises.md) the same way Naturametrics'
version does: a citation string, a BibTeX entry, and the full source list, all
copy-pasteable, so a reader who wants to credit this work — or check what it is
built on — never has to reverse-engineer it from the UI.
"""

from __future__ import annotations

import reflex as rx

from ..config.citation import (
    APP_YEAR, AUTHORS, BIBTEX, CITATION_TEXT, DATA_SOURCES, DATA_SOURCES_EN,
)
from ..state import AppState


def _source_row(name_pt: str, name_en: str, desc_pt: str, desc_en: str,
                url: str) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(rx.cond(AppState.lang == "en", name_en, name_pt),
                    size="2", weight="medium"),
            rx.link(rx.icon("external-link", size=12), href=url, is_external=True),
            spacing="1", align="center",
        ),
        rx.text(rx.cond(AppState.lang == "en", desc_en, desc_pt),
                size="1", color="var(--gray-11)"),
        spacing="0", align_items="start", width="100%",
    )


def cite_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("quote", size=15),
                rx.text(rx.cond(AppState.lang == "en", "Cite", "Como citar"),
                        display=["none", "none", "block", "block"]),
                size="1", variant="soft", color_scheme="gray",
            )
        ),
        rx.dialog.content(
            rx.dialog.title(
                rx.cond(AppState.lang == "en", "How to cite", "Como citar")
            ),
            rx.dialog.description(
                rx.cond(
                    AppState.lang == "en",
                    "Camposcope and the datasets it draws on.",
                    "Camposcope e as fontes de dados que ele utiliza.",
                ),
                size="2", color="var(--gray-11)", margin_bottom="0.75rem",
            ),
            rx.scroll_area(
                rx.vstack(
                    rx.text(
                        rx.cond(AppState.lang == "en", "Suggested citation",
                               "Citação sugerida"),
                        size="2", weight="bold",
                    ),
                    rx.box(
                        rx.text(CITATION_TEXT, size="2", style={"lineHeight": "1.6"}),
                        padding="0.75rem", background="var(--gray-3)",
                        border_radius="6px", width="100%",
                    ),
                    rx.button(
                        rx.icon("copy", size=13),
                        rx.cond(AppState.lang == "en", "Copy citation",
                               "Copiar citação"),
                        on_click=rx.set_clipboard(CITATION_TEXT),
                        size="1", variant="soft", color_scheme="grass",
                    ),

                    rx.divider(),
                    rx.text("BibTeX", size="2", weight="bold"),
                    rx.code_block(BIBTEX, language="latex", show_line_numbers=False,
                                  wrap_long_lines=True, font_size="0.75rem"),
                    rx.button(
                        rx.icon("copy", size=13),
                        rx.cond(AppState.lang == "en", "Copy BibTeX",
                               "Copiar BibTeX"),
                        on_click=rx.set_clipboard(BIBTEX),
                        size="1", variant="soft", color_scheme="grass",
                    ),

                    rx.divider(),
                    rx.text(rx.cond(AppState.lang == "en", "Author", "Autor"),
                            size="2", weight="bold"),
                    rx.vstack(
                        *[
                            rx.vstack(
                                rx.text(name, size="2", weight="medium"),
                                rx.text(inst, size="1", color="var(--gray-11)"),
                                spacing="0", align_items="start",
                            )
                            for name, inst in AUTHORS
                        ],
                        spacing="2", align_items="start", width="100%",
                    ),

                    rx.divider(),
                    rx.text(
                        rx.cond(AppState.lang == "en", "Data sources",
                               "Fontes de dados"),
                        size="2", weight="bold",
                    ),
                    rx.vstack(
                        *[
                            _source_row(n_pt, n_en, d_pt, d_en, u)
                            for (n_pt, d_pt, u), (n_en, d_en, _)
                            in zip(DATA_SOURCES, DATA_SOURCES_EN)
                        ],
                        spacing="3", align_items="start", width="100%",
                    ),
                ),
                type="always", scrollbars="vertical",
                style={"maxHeight": "70vh"},
            ),
            rx.dialog.close(
                rx.button(
                    rx.cond(AppState.lang == "en", "Close", "Fechar"),
                    size="1", variant="soft", margin_top="1rem",
                ),
            ),
            max_width="560px",
        ),
    )
