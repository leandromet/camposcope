"""The three entry gestures (doc/08-ui-ux.md §2).

All three produce the same state; none is privileged. The chooser that appears
when a click hits several overlapping registrations is a first-class part of this
component, not an error dialog — overlaps are the normal state of a self-declared
cadastre (decision D7).
"""

from __future__ import annotations

import reflex as rx

from ..config.sicar import UFS
from ..state import AppState
from .layout import BORDER, MUTED, section


def _by_code() -> rx.Component:
    return rx.vstack(
        rx.input(
            placeholder="MT-5108501-CBE0F5EDD27A4D7888E7392EA7D44793",
            value=AppState.code_input,
            on_change=AppState.set_code_input,
            size="2",
            width="100%",
            font_family="monospace",
            font_size="0.75rem",
        ),
        rx.button(
            rx.cond(AppState.searching, "Buscando…", "Buscar imóvel"),
            on_click=AppState.search_by_code,
            disabled=AppState.searching,
            size="2",
            width="100%",
        ),
        spacing="2",
        width="100%",
    )


def _by_map() -> rx.Component:
    return rx.vstack(
        rx.text(
            "Clique no mapa sobre um imóvel. Se mais de um registro cobrir o "
            "ponto, todos serão listados.",
            size="1", color=MUTED,
        ),
        rx.cond(
            AppState.searching,
            rx.hstack(rx.spinner(size="1"), rx.text("Consultando o CAR…", size="1"),
                      spacing="2", align="center"),
        ),
        spacing="2",
        width="100%",
    )


def _by_municipio() -> rx.Component:
    return rx.vstack(
        rx.select(UFS, value=AppState.search_uf, on_change=AppState.set_search_uf,
                  size="2", width="100%"),
        rx.text("Lista por município — Fase 1.", size="1", color=MUTED),
        spacing="2",
        width="100%",
    )


def candidate_chooser() -> rx.Component:
    """Shown when a click lands on more than one registration.

    Ordered largest-first, and never auto-resolved: choosing for the user would
    be a silent editorial decision about a legally contested situation.
    """
    return rx.cond(
        AppState.candidates,
        rx.vstack(
            rx.text(
                "Mais de um imóvel registrado cobre este ponto. "
                "Sobreposições são comuns no CAR — escolha qual analisar:",
                size="1", weight="medium",
            ),
            rx.foreach(
                AppState.candidates,
                lambda c: rx.box(
                    rx.vstack(
                        rx.text(c["cod_imovel"], size="1", font_family="monospace"),
                        rx.hstack(
                            rx.text(f"{c['area_declarada_ha']} ha", size="1",
                                    weight="bold"),
                            rx.text(c["condicao"], size="1", color=MUTED),
                            spacing="2", wrap="wrap",
                        ),
                        spacing="1", align_items="start",
                    ),
                    on_click=AppState.choose_candidate(c["cod_imovel"]),
                    padding="2",
                    border=BORDER,
                    border_radius="var(--radius-2)",
                    cursor="pointer",
                    width="100%",
                    _hover={"background": "var(--gray-3)"},
                ),
            ),
            spacing="2",
            width="100%",
        ),
    )


def search_panel() -> rx.Component:
    return section(
        "Busca",
        rx.segmented_control.root(
            rx.segmented_control.item("Código", value="codigo"),
            rx.segmented_control.item("Mapa", value="mapa"),
            rx.segmented_control.item("Município", value="municipio"),
            value=AppState.search_mode,
            on_change=AppState.set_search_mode,
            size="1",
            width="100%",
        ),
        rx.match(
            AppState.search_mode,
            ("codigo", _by_code()),
            ("mapa", _by_map()),
            ("municipio", _by_municipio()),
            _by_code(),
        ),
        rx.cond(
            AppState.sicar_error,
            rx.callout(AppState.sicar_error, icon="triangle-alert",
                       color_scheme="amber", size="1"),
        ),
        candidate_chooser(),
    )
