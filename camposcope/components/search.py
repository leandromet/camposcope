"""The unified search box and its result lists (doc/11-search-and-navigation.md).

One field resolves four kinds of input and **says how it read them** before
acting. That echo line is not decoration: it is what stops a transposed
coordinate pair or a mistyped code from quietly resolving somewhere plausible
and wrong.

Two result lists appear below it, and they are deliberately different in kind:
a município or a place **frames the map**, while a CAR registration **is
selected**. Finding a place and identifying a registration are different acts,
and the UI never blurs them (constraint C4).
"""

from __future__ import annotations

import reflex as rx

from ..state import AppState
from .layout import BORDER, MUTED, section

#: One colour per resolver, so the echo line is scannable without being read.
_ECHO_COLOR = {
    "codigo": "grass",
    "coordenada": "blue",
    "municipio": "amber",
    "lugar": "gray",
    "erro": "red",
}


def _echo_line() -> rx.Component:
    """"lido como: coordenada -12.4979, -55.4977"."""
    return rx.cond(
        AppState.echo,
        rx.hstack(
            rx.text(AppState.tr["search_read_as"], size="1", color=MUTED,
                    flex_shrink="0"),
            rx.badge(
                AppState.echo,
                size="1",
                color_scheme=rx.match(
                    AppState.echo_kind,
                    *[(k, v) for k, v in _ECHO_COLOR.items()],
                    "gray",
                ),
                variant="soft",
            ),
            spacing="2",
            align="center",
            width="100%",
            wrap="wrap",
        ),
    )


def _search_field() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.input(
                rx.input.slot(rx.icon("search", size=14)),
                placeholder=AppState.tr["search_placeholder"],
                value=AppState.query,
                on_change=AppState.set_query,
                on_key_down=lambda key: rx.cond(
                    key == "Enter", AppState.submit_search, rx.noop()
                ),
                size="2",
                width="100%",
            ),
            rx.cond(
                AppState.query,
                rx.icon_button(
                    rx.icon("x", size=14),
                    on_click=AppState.clear_search,
                    size="2",
                    variant="soft",
                    color_scheme="gray",
                ),
            ),
            spacing="1",
            width="100%",
        ),
        _echo_line(),
        rx.button(
            rx.cond(
                AppState.searching | AppState.searching_place,
                AppState.tr["search_button_busy"],
                AppState.tr["search_button"],
            ),
            on_click=AppState.submit_search,
            disabled=AppState.searching | AppState.searching_place,
            size="2",
            width="100%",
        ),
        spacing="2",
        width="100%",
    )


def _result_row(*children, on_click) -> rx.Component:
    return rx.box(
        rx.vstack(*children, spacing="1", align_items="start", width="100%"),
        on_click=on_click,
        padding="2",
        border=BORDER,
        border_radius="var(--radius-2)",
        cursor="pointer",
        width="100%",
        _hover={"background": "var(--gray-3)"},
    )


def _municipio_hits() -> rx.Component:
    return rx.cond(
        AppState.municipio_hits,
        rx.vstack(
            rx.text(AppState.tr["search_municipios_heading"], size="1",
                    weight="medium", color=MUTED),
            rx.foreach(
                AppState.municipio_hits,
                lambda m: _result_row(
                    rx.text(f"{m['nome']} / {m['uf']}", size="1", weight="medium"),
                    on_click=AppState.choose_municipio(m["cod_municipio_ibge"]),
                ),
            ),
            spacing="1",
            width="100%",
        ),
    )


def _place_hits() -> rx.Component:
    """Geocoded places. Framing only — no property is selected from here."""
    return rx.cond(
        AppState.place_hits,
        rx.vstack(
            rx.text(AppState.tr["search_places_heading"], size="1",
                    weight="medium", color=MUTED),
            rx.foreach(
                AppState.place_hits,
                lambda p, i: _result_row(
                    rx.text(p["label"], size="1"),
                    on_click=AppState.choose_place(i),
                ),
            ),
            rx.text(AppState.tr["search_places_note"], size="1", color=MUTED),
            rx.text(AppState.tr["search_places_attribution"], size="1",
                    color=MUTED, padding_bottom="2px"),
            spacing="1",
            width="100%",
        ),
    )


def candidate_chooser() -> rx.Component:
    """Shown when a click or coordinate lands on more than one registration.

    Ordered largest-first, and never auto-resolved: choosing for the user would
    be a silent editorial decision about a legally contested situation
    (decision D7).
    """
    return rx.cond(
        AppState.candidates,
        rx.vstack(
            rx.text(
                AppState.tr["search_candidates_note"],
                size="1", weight="medium",
            ),
            rx.foreach(
                AppState.candidates,
                lambda c: _result_row(
                    rx.text(c["cod_imovel"], size="1", font_family="monospace",
                           style={"overflowWrap": "anywhere"}),
                    rx.hstack(
                        rx.text(f"{c['area_declarada_ha']} ha", size="1",
                                weight="bold"),
                        rx.text(c["condicao"], size="1", color=MUTED),
                        spacing="2", wrap="wrap",
                    ),
                    on_click=AppState.choose_candidate(c["cod_imovel"]),
                ),
            ),
            spacing="2",
            width="100%",
        ),
    )


def municipio_browser() -> rx.Component:
    """A paged, geometry-less list of one município's registrations."""
    return rx.cond(
        AppState.municipio_list,
        section(
            AppState.tr["municipio_browser_title"],
            rx.hstack(
                rx.text(
                    f"{AppState.municipio_total} {AppState.tr['municipio_browser_total']}",
                    size="1", color=MUTED,
                ),
                rx.spacer(),
                rx.text(AppState.municipio_page_label, size="1", color=MUTED),
                width="100%",
            ),
            rx.foreach(
                AppState.municipio_list,
                lambda c: _result_row(
                    rx.text(c["cod_imovel"], size="1", font_family="monospace",
                           style={"overflowWrap": "anywhere"}),
                    rx.hstack(
                        rx.text(f"{c['area_declarada_ha']} ha", size="1",
                                weight="bold"),
                        rx.text(c["condicao"], size="1", color=MUTED),
                        spacing="2", wrap="wrap",
                    ),
                    on_click=AppState.choose_candidate(c["cod_imovel"]),
                ),
            ),
            rx.hstack(
                rx.button(AppState.tr["municipio_browser_prev"],
                          on_click=AppState.prev_municipio_page,
                          disabled=AppState.municipio_page <= 0,
                          size="1", variant="soft"),
                rx.spacer(),
                rx.button(AppState.tr["municipio_browser_next"],
                          on_click=AppState.next_municipio_page,
                          disabled=AppState.municipio_page + 1
                          >= AppState.municipio_pages,
                          size="1", variant="soft"),
                width="100%",
            ),
        ),
    )


def search_panel() -> rx.Component:
    """Note: ``candidate_chooser()`` is NOT called from here (it used to
    be) — it's shown separately, outside whatever collapsible group this
    panel ends up inside, because a pending pick is something the user has
    to act on, not a search-form field that's fine to hide by default.
    See ``pages/index.py::_mobile_sheet()``, where that distinction is what
    the "Busca" accordion is scoped to exclude."""
    return section(
        AppState.tr["search_title"],
        _search_field(),
        rx.cond(
            AppState.search_error,
            rx.callout(AppState.search_error, icon="triangle-alert",
                       color_scheme="amber", size="1"),
        ),
        rx.cond(
            AppState.sicar_error,
            rx.callout(AppState.sicar_error, icon="triangle-alert",
                       color_scheme="amber", size="1"),
        ),
        _municipio_hits(),
        _place_hits(),
    )
