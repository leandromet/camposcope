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


def split_panel(chart: rx.Component, table: rx.Component,
                *, chart_width: str = "50%") -> rx.Component:
    """Chart and data table side by side — the layout every results tab uses
    (Cobertura, Transições, Floresta, Biomassa) so a full-width chart never
    dominates the results drawer, and the numbers behind it are always one
    glance away rather than a hover-tooltip away.

    Stacks vertically below ~640px (a narrow drawer/phone) rather than
    squeezing two illegible columns.
    """
    return rx.flex(
        rx.box(chart, width=["100%", "100%", chart_width], flex_shrink="0"),
        rx.box(table, flex="1", min_width="0", overflow_y="auto",
              max_height="300px"),
        direction=rx.breakpoints(initial="column", md="row"),
        spacing="4", width="100%", align="start",
    )


def zone_selector() -> rx.Component:
    """Which zone the active tab describes. Shared by every tab that has one
    (Cobertura, Floresta, Biomassa, Validação) — lives here rather than in
    ``results.py`` so ``validacao.py`` can use it without a circular import.
    Selecting a zone never moves the map (constraint C1) — only
    ``AppState.frame_geometry`` does that, and only when a *property* is
    newly selected."""
    from ..state import AppState

    return rx.cond(
        AppState.zones,
        rx.hstack(
            rx.foreach(
                AppState.zones,
                lambda z: rx.button(
                    z["zone_label"],
                    on_click=AppState.set_active_zone(z["zone_key"]),
                    size="1",
                    variant=rx.cond(
                        AppState.active_zone == z["zone_key"], "solid", "soft"
                    ),
                    color_scheme=rx.cond(
                        z["zone_kind"] == "property", "amber", "blue"
                    ),
                ),
            ),
            spacing="2",
            wrap="wrap",
            width="100%",
        ),
    )


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
    from .citation import cite_dialog
    from .exports import export_dialog

    return rx.hstack(
        rx.hstack(
            rx.icon("scan-search", size=20),
            rx.heading(AppState.tr["app_name"], size="4", weight="bold"),
            spacing="2",
            align="center",
        ),
        rx.spacer(),
        rx.link(
            rx.button(
                rx.text("🇨🇦", font_size="0.95rem"),
                rx.text(AppState.tr["go_to_canada"],
                        display=["none", "none", "block", "block"]),
                size="1", variant="soft", color_scheme="gray",
                aria_label=AppState.tr["go_to_canada"],
            ),
            href=AppState.canada_href,
        ),
        export_dialog(),
        cite_dialog(),
        rx.segmented_control.root(
            rx.segmented_control.item("🇧🇷 PT", value="pt"),
            rx.segmented_control.item("🇨🇦 EN", value="en"),
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
