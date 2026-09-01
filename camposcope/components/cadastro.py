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
    """A label/value line. Both cells get ``overflow_wrap="anywhere"`` and
    ``min_width="0"`` — a full SICAR code (``_overlaps()`` puts one in the
    LABEL slot; the main código row puts one in the value slot) is a long
    run of digits and dots with no space for the browser's default line
    breaking to use, and ``flex_shrink="0"`` on the old label cell refused
    to shrink it at all. Without both fixes, that one long, unbroken string
    forces this row — and every ancestor up to the sidebar/sheet — wider
    than its container instead of wrapping onto a second line, which is
    what actually produced the sideways overflow on a narrow phone."""
    return rx.hstack(
        rx.text(label, size="1", color=MUTED, flex="0 1 auto", min_width="0",
                style={"overflowWrap": "anywhere"}),
        rx.spacer(),
        rx.text(
            value,
            size="1",
            weight=rx.cond(emphasis, "bold", "regular"),
            font_family=rx.cond(mono, "monospace", "inherit"),
            text_align="right",
            flex="1 1 auto", min_width="0",
            style={"overflowWrap": "anywhere"},
        ),
        width="100%",
        align="start",
        spacing="2",
    )


def _disclosure_box(text) -> rx.Component:
    """The permanent, non-dismissible C4 statement box, shared by both card
    kinds. ``margin_bottom`` (new) gives the footnote room before whatever
    section follows (ZONAS) — without it the box's own bottom border sat
    right against that section's top edge, on top of them both, reading as
    one unbroken block."""
    return rx.box(
        rx.text(text, size="1", color=MUTED, line_height="1.45"),
        padding="2",
        background="var(--gray-2)",
        border=BORDER,
        border_radius="var(--radius-2)",
        margin_top="2",
        margin_bottom="6px",
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


def _imovel_details_card() -> rx.Component:
    """A real CAR record. The código row and the disclosure box stay outside
    the accordion below as the always-visible summary — código is the
    identifier someone scans for, and the disclosure is permanent and
    non-dismissible by constraint C4 (see the module docstring). Everything
    in between (município, area, módulos fiscais, tipo, status, condição,
    dates, overlaps) is the dense field dump that made this card feel
    cramped once populated, so it goes in one accordion, mirroring
    naturametrics' own IFN-filters accordion — open by default, unlike
    IFN's, since this is the literal payload of the click the user just
    made, not an optional refinement."""
    return section(
        AppState.tr["cadastro_title"],
        _row(AppState.tr["cadastro_codigo"], AppState.imovel["cod_imovel"],
             mono=True),
        rx.accordion.root(
            rx.accordion.item(
                rx.accordion.header(
                    rx.accordion.trigger(
                        rx.hstack(
                            rx.icon("list", size=13),
                            rx.text(AppState.tr["cadastro_details_toggle"],
                                   size="1", weight="medium"),
                            spacing="2", align="center",
                        ),
                    ),
                ),
                rx.accordion.content(
                    rx.vstack(
                        _row(AppState.tr["cadastro_municipio"],
                             f"{AppState.imovel['municipio']} / {AppState.imovel['uf']}"),
                        _area_block(),
                        _row(AppState.tr["cadastro_modulos_fiscais"],
                             AppState.imovel["m_fiscal"]),
                        _row(AppState.tr["cadastro_tipo"], AppState.imovel["tipo_imovel"]),
                        _row(AppState.tr["cadastro_status"], AppState.imovel["status_imovel"]),
                        # Verbatim, in full, no truncation, no icon, no
                        # colour (C4). Only the LABEL "Condição" is
                        # translated — the value never is.
                        rx.vstack(
                            rx.text(AppState.tr["cadastro_condicao"], size="1",
                                   color=MUTED),
                            rx.text(AppState.imovel["condicao"], size="1"),
                            spacing="1", width="100%", align_items="start",
                        ),
                        _row(AppState.tr["cadastro_registrado_em"],
                             AppState.imovel["dat_criacao"]),
                        _row(AppState.tr["cadastro_atualizado_em"],
                             rx.cond(AppState.imovel["data_atualizacao"],
                                     AppState.imovel["data_atualizacao"],
                                     AppState.tr["cadastro_nao_informada"])),
                        _overlaps(),
                        spacing="2", width="100%", padding_top="0.25rem",
                    ),
                    # Radix's own AccordionContent bakes in
                    # `padding_x: var(--space-4)` (16px) — stacked on top of
                    # the sidebar's own 16px, every row in here was sitting
                    # 32px from the edge instead of 16px like the código row
                    # and disclosure box just outside this accordion, which
                    # is what read as a sudden, inconsistent indent/squeeze
                    # once the accordion was added. Zeroing it here keeps
                    # this content flush with the rest of the card.
                    padding_x="0",
                ),
                value="detalhes",
            ),
            type="single", collapsible=True, variant="ghost", width="100%",
            # `default_value`, not `value` — the latter makes this a
            # CONTROLLED accordion, and with no `on_change` wired to update
            # it, Radix has nothing to change it TO when the trigger is
            # clicked, so it would render open and simply never close.
            # `default_value` only sets the *initial* state; the accordion
            # still manages its own open/closed state after that.
            default_value="detalhes",
        ),
        # Permanent and non-dismissible. This is the whole posture of the
        # app in one line (constraint C4). AppState.disclosure already
        # reads config/sicar.py's DISCLOSURE_PT/DISCLOSURE_EN directly —
        # the one legal statement, not duplicated into this table.
        _disclosure_box(AppState.disclosure),
    )


def _square_card() -> rx.Component:
    """The floor tier: no CAR record here, a synthetic 500 ha square
    instead. Mirrors the Canada page's own ``_square_card``
    (``canada/components/parcel_card.py``), CAR-flavoured."""
    return section(
        AppState.tr["square_title"],
        rx.callout(AppState.tr["square_note"], icon="square-dashed",
                  color_scheme="gray", size="1"),
        _row(AppState.tr["square_coordinate"], AppState.imovel["coordinates"],
             mono=True),
        _row(AppState.tr["cadastro_area_declarada"], "500 ha", emphasis=True),
        _disclosure_box(AppState.tr["square_disclosure"]),
    )


def cadastral_card() -> rx.Component:
    return rx.cond(
        AppState.has_imovel,
        rx.cond(
            AppState.imovel["kind"] == "square",
            _square_card(),
            _imovel_details_card(),
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
            info=AppState.tr["zonas_note"],
        ),
    )
