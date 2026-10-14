"""The header's "Como usar" dialog — the full guide the quick-start card
points to.

Ported from Naturametrics' ``components/help.py`` and the Canada page's own
``canada/components/help.py``: a controlled ``rx.dialog`` (``help_open``),
because the quick-start card has to open it, and because a button used as
``Dialog.Close``'s child never receives the props Radix's ``asChild`` cloning
injects once Reflex extracts it into its own component — it renders and does
nothing.
"""

from __future__ import annotations

import reflex as rx

from ..state import AppState
from .layout import ACCENT

#: Steps in ``help_step{n}_title`` / ``help_step{n}_body``.
HELP_STEPS = 8


def _step(number: int) -> rx.Component:
    tr = AppState.tr
    return rx.hstack(
        rx.badge(str(number), color_scheme=ACCENT, variant="solid", size="1",
                 style={"minWidth": "22px", "justifyContent": "center"}),
        rx.vstack(
            rx.text(tr[f"help_step{number}_title"], size="2", weight="bold"),
            rx.text(tr[f"help_step{number}_body"], size="2", color_scheme="gray"),
            spacing="1", align_items="start",
        ),
        spacing="3", align_items="start", width="100%",
    )


def como_usar_dialog() -> rx.Component:
    tr = AppState.tr
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("circle-help", size=15),
                # Label collapses to an icon on phones, like the header's
                # other actions — labelled, they do not fit at 390px.
                rx.text(tr["help_trigger"],
                        display=["none", "none", "block", "block"]),
                size="1", variant="soft", color_scheme="gray",
                aria_label=tr["help_trigger"],
            )
        ),
        rx.dialog.content(
            rx.dialog.title(tr["help_dialog_title"]),
            rx.dialog.description(
                tr["help_dialog_desc"],
                size="2", color_scheme="gray", margin_bottom="0.75rem",
            ),
            rx.scroll_area(
                rx.vstack(
                    *[_step(n) for n in range(1, HELP_STEPS + 1)],
                    spacing="4", align_items="start", width="100%",
                ),
                type="auto", scrollbars="vertical",
                style={"maxHeight": "60vh", "paddingRight": "1rem"},
            ),
            rx.flex(
                rx.button(
                    rx.icon("rocket", size=14),
                    tr["help_show_quickstart"],
                    size="2", variant="ghost", color_scheme="gray",
                    on_click=AppState.reset_quickstart,
                ),
                rx.spacer(),
                rx.button(tr["help_close"], size="2", variant="soft",
                          on_click=AppState.set_help_open(False)),
                align="center", margin_top="1rem", wrap="wrap", gap="2",
            ),
            max_width=["94vw", "94vw", "640px", "640px"],
        ),
        open=AppState.help_open,
        on_open_change=AppState.set_help_open,
    )
