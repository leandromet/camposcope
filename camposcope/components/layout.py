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
        # `overflow="auto"` (both axes on the same element), not just
        # `overflow_y` — a wide table (Paisagem's 9 columns) needs its own
        # horizontal scroller too. Leaving overflow-x unset let the CSS spec's
        # own "visible + non-visible sibling -> auto" rule create a *second*,
        # empty horizontal scroll container here on top of the table's own,
        # which is what made a one-finger touch drag ambiguous between the
        # two nested scrollers and lose the horizontal gesture entirely on
        # phones (confirmed: only vertical scroll worked, mouse-drag on a
        # real scrollbar was never tested since phones don't have one).
        rx.box(table, flex="1", min_width="0", overflow="auto",
              max_height="300px",
              style={"WebkitOverflowScrolling": "touch",
                     "touchAction": "pan-x pan-y"}),
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


def _info_icon(text) -> rx.Component:
    """A tap/click affordance, not a hover tooltip — this app is mobile-first
    throughout, and hover has no equivalent on touch. Ported from
    naturametrics' own ``components/layer_panel.py::_info_icon``."""
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
    """A titled sidebar block. ``info``, when given, renders as a tap-to-open
    (i) icon next to the title instead of a permanently-visible caption —
    the same ``_section(..., info=...)`` convention naturametrics uses, so
    an explanatory note that used to sit as its own line of gray text no
    longer counts against how much of the block is visible at a glance."""
    header = rx.text(title, size="1", weight="bold", color=MUTED,
                     letter_spacing="0.08em", text_transform="uppercase")
    return rx.vstack(
        rx.hstack(header, _info_icon(info), spacing="1", align="center")
        if info is not None else header,
        *children,
        align_items="stretch",
        # One token up from the previous "2"/"3" on both (`spacing` only
        # accepts Radix's literal 0-9 scale, not an arbitrary calc() — a
        # calc string here is a Reflex TypeError at build time) — a section
        # sitting right up against its neighbour above/below, and its own
        # rows sitting right up against each other, was the "everything
        # reads as compressed" complaint once the sidebar started showing
        # real content (a cadastral record, its zones) instead of empty
        # placeholders.
        spacing="3",
        width="100%",
        padding_y="calc(var(--space-3) + 3px)",
        border_bottom=BORDER,
        **props,
    )


def header() -> rx.Component:
    from ..state import AppState
    from .citation import cite_dialog
    from .exports import export_dialog

    return rx.hstack(
        rx.hstack(
            rx.icon("scan-search", size=20, flex_shrink="0"),
            # Hidden outright on a phone, not truncated: the app's four
            # header actions (Canada, export, cite, language) plus this
            # title used to force the heading's own word-wrap into three
            # lines, pushing everything below (including the mobile
            # drawer's floating reopen button, positioned by a fixed pixel
            # offset that assumed a one-line header) out of place. An
            # ellipsis-truncated fragment ("C...") turned out to read worse
            # than no title at all — the icon alone already identifies the
            # app next to a URL bar that says which one this is.
            rx.heading(AppState.tr["app_name"], size="4", weight="bold",
                      white_space="nowrap", overflow="hidden",
                      text_overflow="ellipsis", min_width="0",
                      display=["none", "none", "block", "block"]),
            spacing="2",
            align="center",
            min_width="0", overflow="hidden", flex_shrink="1",
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
