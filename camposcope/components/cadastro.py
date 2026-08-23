"""The cadastral record card — where constraint C4 lives.

Every field is shown **verbatim** from the CAR. ``condicao`` gets no traffic
light, no badge colour and no rewording: the moment it becomes a colour,
Camposcope is issuing a verdict (doc/01-premises.md §5).

The declared-vs-computed area row is the one thing on this card that is *ours*
rather than the cadastre's, and it is labelled as such (decision D6).
"""

from __future__ import annotations

import reflex as rx

from ..state import AppState
from .layout import BORDER, MUTED, section


def _row(label: str, value, *, mono: bool = False, emphasis: bool = False) -> rx.Component:
    return rx.hstack(
        rx.text(label, size="1", color=MUTED, flex_shrink="0"),
        rx.spacer(),
        rx.text(
            value,
            size="1",
            weight=rx.cond(emphasis, "bold", "regular"),
            font_family=rx.cond(mono, "monospace", "inherit"),
            text_align="right",
        ),
        width="100%",
        align="start",
        spacing="2",
    )


def _area_block() -> rx.Component:
    """Declared vs. computed. The disagreement is information, not an error."""
    return rx.vstack(
        _row("Área declarada", f"{AppState.area_declarada_ha} ha", emphasis=True),
        _row("Área calculada (geometria)", f"{AppState.area_calculada_ha} ha"),
        rx.cond(
            AppState.area_flagged,
            rx.callout(
                f"A área declarada e a área da geometria diferem em "
                f"{AppState.area_delta_ha} ha ({AppState.area_delta_pct}%). "
                "Ambas são exibidas como estão.",
                icon="ruler",
                color_scheme="amber",
                size="1",
            ),
        ),
        spacing="1",
        width="100%",
    )


def _overlaps() -> rx.Component:
    return rx.cond(
        AppState.overlaps,
        rx.vstack(
            rx.text("Sobreposições com outros registros", size="1",
                    weight="medium", color=MUTED),
            rx.foreach(
                AppState.overlaps,
                lambda o: _row(
                    o["cod_imovel"],
                    f"{o['overlap_ha']} ha ({o['overlap_pct_do_imovel']}%)",
                    mono=True,
                ),
            ),
            spacing="1",
            width="100%",
            padding_top="2",
        ),
    )


def cadastral_card() -> rx.Component:
    return rx.cond(
        AppState.has_imovel,
        section(
            "Imóvel",
            _row("Código", AppState.imovel["cod_imovel"], mono=True),
            _row("Município",
                 f"{AppState.imovel['municipio']} / {AppState.imovel['uf']}"),
            _area_block(),
            _row("Módulos fiscais", AppState.imovel["m_fiscal"]),
            _row("Tipo", AppState.imovel["tipo_imovel"]),
            _row("Status", AppState.imovel["status_imovel"]),
            # Verbatim, in full, no truncation, no icon, no colour (C4).
            rx.vstack(
                rx.text("Condição", size="1", color=MUTED),
                rx.text(AppState.imovel["condicao"], size="1"),
                spacing="1", width="100%", align_items="start",
            ),
            _row("Registrado em", AppState.imovel["dat_criacao"]),
            _row("Atualizado em",
                 rx.cond(AppState.imovel["data_atualizacao"],
                         AppState.imovel["data_atualizacao"],
                         "não informada")),
            _overlaps(),
            # Permanent and non-dismissible. This is the whole posture of the
            # app in one line (constraint C4).
            rx.box(
                rx.text(AppState.disclosure, size="1", color=MUTED,
                        line_height="1.45"),
                padding="2",
                background="var(--gray-2)",
                border=BORDER,
                border_radius="var(--radius-2)",
                margin_top="2",
            ),
        ),
    )


def zones_panel() -> rx.Component:
    return rx.cond(
        AppState.zones,
        section(
            "Zonas",
            rx.foreach(
                AppState.zones,
                lambda z: rx.hstack(
                    rx.text(z["zone_label"], size="1"),
                    rx.spacer(),
                    rx.text(f"{z['area_ha']} ha", size="1", color=MUTED),
                    width="100%",
                ),
            ),
            rx.text(
                "Anéis medidos a partir do limite do imóvel, não do centroide.",
                size="1", color=MUTED,
            ),
        ),
    )
