"""Application shell for the Canada page.

Structurally the naturametrics/canada shell adapted to Camposcope's own
sidebar-plus-map arrangement (``pages/index.py`` — the property drawer overlays
the map rather than sharing flex space with it). The palette is the Canada
page's own: jade, distinct from Brazil's grass, so the two pages never look like
one copied onto the other.
"""

from __future__ import annotations

import reflex as rx

from ..state import CanadaState as S

ACCENT = "jade"

PROPERTY_COLOR = "#f5a524"
RING_COLORS = ["#8ec5ff", "#6aa9e9", "#4a86c4", "#33639b"]

MUTED = "var(--gray-11)"
BORDER = "1px solid var(--gray-5)"


def split_panel(chart: rx.Component, table: rx.Component,
                *, chart_width: str = "50%") -> rx.Component:
    return rx.flex(
        rx.box(chart, width=["100%", "100%", chart_width], flex_shrink="0"),
        # `overflow="auto"` (both axes on the same element), not just
        # `overflow_y` — see the Brazil page's own `components/layout.py`
        # (same helper, ported): a wide table needs its own horizontal
        # scroller, and leaving overflow-x unset creates a *second*, empty
        # one here on top of the table's own, which breaks touch-drag
        # scrolling on a phone.
        rx.box(table, flex="1", min_width="0", overflow="auto",
              max_height="300px",
              style={"WebkitOverflowScrolling": "touch",
                     "touchAction": "pan-x pan-y"}),
        direction=rx.breakpoints(initial="column", md="row"),
        spacing="4", width="100%", align="start",
    )


def zone_selector() -> rx.Component:
    return rx.cond(
        S.zones,
        rx.hstack(
            rx.foreach(
                S.zones,
                lambda z: rx.button(
                    z["zone_label"],
                    on_click=S.set_active_zone(z["zone_key"]),
                    size="1",
                    variant=rx.cond(S.active_zone == z["zone_key"], "solid", "soft"),
                    color_scheme=rx.cond(
                        z["zone_kind"] == "property", "amber", "blue"),
                ),
            ),
            spacing="2", wrap="wrap", width="100%",
        ),
    )


def _info_icon(text) -> rx.Component:
    """A tap/click affordance, not a hover tooltip — see the Brazil page's
    own ``components/layout.py::_info_icon`` for the full rationale."""
    return rx.popover.root(
        rx.popover.trigger(
            rx.icon_button(
                rx.icon("info", size=12),
                size="1", variant="ghost", color_scheme="gray",
                aria_label=text,
            ),
        ),
        rx.popover.content(
            rx.text(text, size="1", style={"lineHeight": "1.4"}),
            max_width="260px",
        ),
    )


def section(title: str, *children, info=None, **props) -> rx.Component:
    header = rx.text(title, size="1", weight="bold", color=MUTED,
                     letter_spacing="0.08em", text_transform="uppercase")
    return rx.vstack(
        rx.hstack(header, _info_icon(info), spacing="1", align="center")
        if info is not None else header,
        *children,
        align_items="stretch", spacing="2", width="100%", padding_y="3",
        border_bottom=BORDER, **props,
    )


def header() -> rx.Component:
    from .help import header_actions

    return rx.hstack(
        rx.hstack(
            rx.icon("scan-search", size=20, color=f"var(--{ACCENT}-11)",
                   flex_shrink="0"),
            # Hidden outright on a phone, not truncated: this page has five
            # header actions (Brazil, help, export, cite, language) that
            # used to force the heading's own word-wrap into three lines,
            # pushing everything below (including the mobile drawer's
            # floating reopen button, positioned by a fixed pixel offset
            # that assumed a one-line header) out of place. Nowrap alone
            # only traded that for a hard, ellipsis-less clip past the
            # viewport edge — an ellipsis-truncated fragment ("C...") read
            # worse than no title at all, so it is hidden below "md" rather
            # than shown broken.
            rx.heading(S.tr["app_name"], size="4", weight="bold",
                      white_space="nowrap", overflow="hidden",
                      text_overflow="ellipsis", min_width="0",
                      display=["none", "none", "block", "block"]),
            spacing="2", align="center", min_width="0", overflow="hidden",
            flex_shrink="1",
        ),
        rx.spacer(),
        rx.link(
            rx.button(
                rx.text("🇧🇷", font_size="0.95rem"),
                rx.text(S.tr["go_to_brazil"],
                        display=["none", "none", "block", "block"]),
                size="1", variant="soft", color_scheme="gray",
                aria_label=S.tr["go_to_brazil"],
            ),
            href=S.brazil_href,
        ),
        header_actions(),
        rx.segmented_control.root(
            rx.segmented_control.item("🇨🇦 EN", value="en"),
            rx.segmented_control.item("🇧🇷 PT", value="pt"),
            value=S.language, on_change=S.set_language, size="1",
            aria_label=S.tr["language_label"],
        ),
        width="100%", padding_x="4", padding_y="2", border_bottom=BORDER,
        align="center", background="var(--color-panel)",
    )
