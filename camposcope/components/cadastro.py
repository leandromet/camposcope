"""The cadastral record card — where constraint C4 lives.

Every field is shown **verbatim** from the CAR. ``condicao`` gets no traffic
light, no badge colour and no rewording: the moment it becomes a colour,
Camposcope is issuing a verdict (doc/01-premises.md §5). Field VALUES are
never translated (translations/__init__.py explains why); field LABELS —
"Área declarada", "Município" — are, through ``AppState.tr``.

The declared-vs-computed area row is the one thing on this card that is *ours*
rather than the cadastre's, and it is labelled as such (decision D6).
"""

from __future__ import annotations

import reflex as rx

from ..state import AppState
from .layout import BORDER, MUTED, section


def _row(label, value, *, mono: bool = False, emphasis: bool = False) -> rx.Component:
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
        _row(AppState.tr["cadastro_area_declarada"],
             f"{AppState.area_declarada_ha} ha", emphasis=True),
        _row(AppState.tr["cadastro_area_calculada"],
             f"{AppState.area_calculada_ha} ha"),
        rx.cond(
            AppState.area_flagged,
            rx.callout(
                # Two static fragments around the interpolated numbers, not a
                # single "{delta}"/"{pct}" template string with .replace()
                # called on it — Var has no string .replace(); plain f-string
                # interpolation (used everywhere else in this app) is what
                # actually produces a valid reactive Var expression.
                f"{AppState.tr['cadastro_area_disagreement_prefix']} "
                f"{AppState.area_delta_ha} ha ({AppState.area_delta_pct}%). "
                f"{AppState.tr['cadastro_area_disagreement_suffix']}",
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
            rx.text(AppState.tr["cadastro_sobreposicoes"], size="1",
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
            AppState.tr["cadastro_title"],
            _row(AppState.tr["cadastro_codigo"], AppState.imovel["cod_imovel"],
                 mono=True),
            _row(AppState.tr["cadastro_municipio"],
                 f"{AppState.imovel['municipio']} / {AppState.imovel['uf']}"),
            _area_block(),
            _row(AppState.tr["cadastro_modulos_fiscais"], AppState.imovel["m_fiscal"]),
            _row(AppState.tr["cadastro_tipo"], AppState.imovel["tipo_imovel"]),
            _row(AppState.tr["cadastro_status"], AppState.imovel["status_imovel"]),
            # Verbatim, in full, no truncation, no icon, no colour (C4). Only
            # the LABEL "Condição" is translated — the value never is.
            rx.vstack(
                rx.text(AppState.tr["cadastro_condicao"], size="1", color=MUTED),
                rx.text(AppState.imovel["condicao"], size="1"),
                spacing="1", width="100%", align_items="start",
            ),
            _row(AppState.tr["cadastro_registrado_em"], AppState.imovel["dat_criacao"]),
            _row(AppState.tr["cadastro_atualizado_em"],
                 rx.cond(AppState.imovel["data_atualizacao"],
                         AppState.imovel["data_atualizacao"],
                         AppState.tr["cadastro_nao_informada"])),
            _overlaps(),
            # Permanent and non-dismissible. This is the whole posture of the
            # app in one line (constraint C4). AppState.disclosure already
            # reads config/sicar.py's DISCLOSURE_PT/DISCLOSURE_EN directly —
            # the one legal statement, not duplicated into this table.
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
            AppState.tr["zonas_title"],
            rx.foreach(
                AppState.zones,
                lambda z: rx.hstack(
                    rx.text(z["zone_label"], size="1"),
                    rx.spacer(),
                    rx.text(f"{z['area_ha']} ha", size="1", color=MUTED),
                    width="100%",
                ),
            ),
            rx.text(AppState.tr["zonas_note"], size="1", color=MUTED),
        ),
    )
