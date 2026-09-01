"""The unified search box and its result lists.

Same shape as ``camposcope/components/search.py``: one field resolves four
kinds of input and echoes how it read them before acting, and the result lists
below it are deliberately different in kind — an area **frames the map**, a
parcel **is selected**.
"""

from __future__ import annotations

import reflex as rx

from ..state import CanadaState as S
from .layout import BORDER, MUTED, section

_ECHO_COLOR = {
    "pid": "jade", "coordenada": "blue", "area": "amber", "lugar": "gray",
    "erro": "red",
}


def _echo_line() -> rx.Component:
    return rx.cond(
        S.echo,
        rx.hstack(
            rx.text(S.tr["search_read_as"], size="1", color=MUTED,
                    flex_shrink="0"),
            rx.badge(
                S.echo, size="1",
                color_scheme=rx.match(
                    S.echo_kind, *[(k, v) for k, v in _ECHO_COLOR.items()],
                    "gray"),
                variant="soft",
            ),
            spacing="2", align="center", width="100%", wrap="wrap",
        ),
    )


def _search_field() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.input(
                rx.input.slot(rx.icon("search", size=14)),
                placeholder=S.tr["search_placeholder"],
                value=S.query, on_change=S.set_query,
                on_key_down=lambda key: rx.cond(
                    key == "Enter", S.submit_search, rx.noop()),
                size="2", width="100%",
            ),
            rx.cond(
                S.query,
                rx.icon_button(
                    rx.icon("x", size=14), on_click=S.clear_search,
                    size="2", variant="soft", color_scheme="gray",
                ),
            ),
            spacing="1", width="100%",
        ),
        _echo_line(),
        rx.button(
            rx.cond(S.searching | S.searching_place, S.tr["search_button_busy"],
                   S.tr["search_button"]),
            on_click=S.submit_search,
            disabled=S.searching | S.searching_place,
            size="2", width="100%",
        ),
        spacing="2", width="100%",
    )


def _result_row(*children, on_click) -> rx.Component:
    return rx.box(
        rx.vstack(*children, spacing="1", align_items="start", width="100%"),
        on_click=on_click, padding="2", border=BORDER,
        border_radius="var(--radius-2)", cursor="pointer", width="100%",
        _hover={"background": "var(--gray-3)"},
    )


def _area_hits() -> rx.Component:
    return rx.cond(
        S.area_hits,
        rx.vstack(
            rx.text(S.tr["search_areas_heading"], size="1", weight="medium",
                   color=MUTED),
            rx.foreach(
                S.area_hits,
                lambda a: _result_row(
                    rx.text(a["short_name"], size="1", weight="medium"),
                    on_click=S.choose_area(a["pmbc_key"]),
                ),
            ),
            spacing="1", width="100%",
        ),
    )


def _place_hits() -> rx.Component:
    return rx.cond(
        S.place_hits,
        rx.vstack(
            rx.text(S.tr["search_places_heading"], size="1", weight="medium",
                   color=MUTED),
            rx.foreach(
                S.place_hits,
                lambda p, i: _result_row(
                    rx.text(p["label"], size="1"),
                    on_click=S.choose_place(i),
                ),
            ),
            rx.text(S.tr["search_places_note"], size="1", color=MUTED),
            rx.text(S.tr["search_places_attribution"], size="1", color=MUTED,
                   padding_bottom="2px"),
            spacing="1", width="100%",
        ),
    )


def candidate_chooser() -> rx.Component:
    return rx.cond(
        S.candidates,
        rx.vstack(
            rx.text(S.tr["search_candidates_note"], size="1", weight="medium"),
            rx.foreach(
                S.candidates,
                lambda c: _result_row(
                    rx.text(c["identifier"], size="1", font_family="monospace",
                           style={"overflowWrap": "anywhere"}),
                    rx.hstack(
                        rx.text(f"{c['area_registered_ha']} ha", size="1",
                               weight="bold"),
                        rx.text(c["parcel_class"], size="1", color=MUTED),
                        spacing="2", wrap="wrap",
                    ),
                    on_click=S.choose_candidate(c["identifier"]),
                ),
            ),
            spacing="2", width="100%",
        ),
    )


def search_panel() -> rx.Component:
    """Note: ``candidate_chooser()`` is NOT called from here (it used to
    be) — see the Brazil page's own ``search.py::search_panel`` for why:
    it's shown separately, outside whatever collapsible group this panel
    ends up inside, since a pending pick needs action, not hiding."""
    return section(
        S.tr["search_title"],
        _search_field(),
        rx.text(S.bc_only_note, size="1", color=MUTED),
        rx.cond(
            S.search_error,
            rx.callout(S.search_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        rx.cond(
            S.parcel_error,
            rx.callout(S.parcel_error, icon="triangle-alert",
                      color_scheme="amber", size="1"),
        ),
        _area_hits(),
        _place_hits(),
    )
