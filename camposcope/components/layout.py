"""Shell: header, sidebar, and the visual language.

Ported in spirit from Naturametrics' ``components/layout.py``; the palette is
Camposcope's own — the object of analysis is a property, and the app should not
look like a copy of its sibling.
"""

from __future__ import annotations

import reflex as rx

ACCENT = "grass"

#: Zone colours. The property is the only saturated thing on the map; rings fade
#: outward so the eye reads them as context rather than as findings.
PROPERTY_COLOR = "#f5a524"
RING_COLORS = ["#8ec5ff", "#6aa9e9", "#4a86c4", "#33639b"]

MUTED = "var(--gray-11)"
BORDER = "1px solid var(--gray-5)"


def section(title: str, *children, **props) -> rx.Component:
    """A titled sidebar block."""
    return rx.vstack(
        rx.text(title, size="1", weight="bold", color=MUTED,
                letter_spacing="0.08em", text_transform="uppercase"),
        *children,
        align_items="stretch",
        spacing="2",
        width="100%",
        padding_y="3",
        border_bottom=BORDER,
        **props,
    )


def header() -> rx.Component:
    from ..state import AppState

    return rx.hstack(
        rx.hstack(
            rx.icon("scan-search", size=20),
            rx.heading("Camposcope", size="4", weight="bold"),
            spacing="2",
            align="center",
        ),
        rx.spacer(),
        rx.segmented_control.root(
            rx.segmented_control.item("PT", value="pt"),
            rx.segmented_control.item("EN", value="en"),
            value=AppState.lang,
            on_change=AppState.set_lang,
            size="1",
        ),
        width="100%",
        padding_x="4",
        padding_y="2",
        border_bottom=BORDER,
        align="center",
        background="var(--color-panel)",
    )
