"""The analysis-area record card — where the "shown verbatim" discipline
lives, for whichever of the three kinds actually answered a click.

Every field is shown exactly as its register publishes it — ``PARCEL_STATUS``,
``PARCEL_CLASS``, ``OWNER_TYPE`` for a parcel; ``DESIG``, ``IUCN_CAT``,
``MANG_AUTH`` for a protected area — with no traffic light or badge colour.
Only the field LABELS are translated, never the values — the same rule
``camposcope/components/cadastro.py`` documents, applied to two different
registers with two different kinds of authority behind them.

Three cards, one dispatcher (:func:`parcel_card`), switching on
``S.parcel["kind"]`` — see ``canada/state/_parcel.py``'s module docstring for
the three-tier chain that decides which kind a given click produces.
"""

from __future__ import annotations

import reflex as rx

from ..state import CanadaState as S
from .layout import BORDER, MUTED, section


def _row(label, value, *, mono: bool = False, emphasis: bool = False) -> rx.Component:
    """A label/value line. See the Brazil page's own ``cadastro.py::_row``
    for why both cells need ``overflow_wrap="anywhere"`` and ``min_width=
    "0"``: a fabric id / PID can run long enough, with no natural break
    point, to force this row wider than its container on a narrow phone
    instead of wrapping."""
    return rx.hstack(
        rx.text(label, size="1", color=MUTED, flex="0 1 auto", min_width="0",
                style={"overflowWrap": "anywhere"}),
        rx.spacer(),
        rx.text(
            value, size="1",
            weight=rx.cond(emphasis, "bold", "regular"),
            font_family=rx.cond(mono, "monospace", "inherit"),
            text_align="right",
            flex="1 1 auto", min_width="0",
            style={"overflowWrap": "anywhere"},
        ),
        width="100%", align="start", spacing="2",
    )


def _coordinate_row() -> rx.Component:
    """The point a researcher would need to relocate this analysis area in
    the field or in another tool — the point actually clicked when that is
    how the area was found, the geometry's own centroid otherwise (a PID
    search or a ``?pid=`` deep link never had a click). Shown on all three
    card kinds; the square card's ``identifier`` already repeats it in text
    form, but a dedicated row keeps the label and the copy-able numbers
    consistent across kinds. See ``canada/state/_parcel.py::_reference_point``.
    """
    from_click = S.parcel["click_lat"] != 0.0
    lat = rx.cond(from_click, S.parcel["click_lat"], S.parcel["centroid_lat"])
    lon = rx.cond(from_click, S.parcel["click_lon"], S.parcel["centroid_lon"])
    label = rx.cond(from_click, S.tr["coord_clicked"], S.tr["coord_centroid"])
    return _row(label, f"{lat}, {lon}", mono=True)


def _disclosure_box(text) -> rx.Component:
    # `margin_bottom` gives the footnote room before whatever section
    # follows (ZONAS) — see the Brazil page's own `cadastro.py::
    # _disclosure_box` for the full rationale.
    return rx.box(
        rx.text(text, size="1", color=MUTED, line_height="1.45"),
        padding="2", background="var(--gray-2)", border=BORDER,
        border_radius="var(--radius-2)", margin_top="2", margin_bottom="6px",
    )


# --------------------------------------------------------------------------- #
# Kind: parcel — ParcelMap BC
# --------------------------------------------------------------------------- #
def _area_block() -> rx.Component:
    return rx.vstack(
        _row(S.tr["parcel_area_registered"],
             f"{S.area_registered_ha} ha", emphasis=True),
        _row(S.tr["parcel_area_calculated"], f"{S.area_calculated_ha} ha"),
        rx.cond(
            S.area_flagged,
            rx.callout(
                f"{S.tr['parcel_area_disagreement_prefix']} "
                f"{S.area_delta_ha} ha ({S.area_delta_pct}%). "
                f"{S.tr['parcel_area_disagreement_suffix']}",
                icon="ruler", color_scheme="amber", size="1",
            ),
        ),
        spacing="1", width="100%",
    )


def _non_land_note() -> rx.Component:
    # Two static translation fragments around the interpolated parcel class,
    # not a single "{class_name}" template with .replace() called on it — Var
    # has no string .replace(); plain f-string interpolation is what actually
    # produces a valid reactive Var expression (same pattern as the area
    # disagreement callout above and camposcope/components/cadastro.py).
    return rx.cond(
        S.parcel["is_non_land"].to(bool),
        rx.callout(
            f"{S.tr['parcel_non_land_prefix']}{S.parcel['parcel_class']}"
            f"{S.tr['parcel_non_land_suffix']}",
            icon="info", color_scheme="amber", size="1",
        ),
    )


def _neighbours() -> rx.Component:
    return rx.cond(
        S.overlaps,
        rx.vstack(
            rx.text(S.tr["parcel_neighbours"], size="1", weight="medium",
                   color=MUTED),
            rx.text(S.tr["parcel_neighbours_note"], size="1", color=MUTED),
            rx.foreach(
                S.overlaps,
                lambda o: _row(
                    o["identifier"],
                    f"{o['overlap_ha']} ha ({o['overlap_pct_of_parcel']}%)",
                    mono=True,
                ),
            ),
            spacing="1", width="100%", padding_top="2",
        ),
    )


def _parcel_details_card() -> rx.Component:
    """A real ParcelMap BC record. The identifier row and the disclosure box
    stay outside the accordion below as the always-visible summary — same
    split the Brazil page's own ``cadastro.py::_imovel_details_card`` uses,
    for the same reason: the identifier is what someone scans for, and the
    disclosure is permanent (constraint C4's Canada-side counterpart). The
    dense field dump in between goes in one accordion, mirroring
    naturametrics' own IFN-filters accordion — open by default, since this
    is the literal payload of the click just made, not an optional
    refinement."""
    return section(
        S.tr["parcel_title"],
        _row(S.tr["parcel_identifier"], S.parcel["identifier"], mono=True),
        rx.accordion.root(
            rx.accordion.item(
                rx.accordion.header(
                    rx.accordion.trigger(
                        rx.hstack(
                            rx.icon("list", size=13),
                            rx.text(S.tr["parcel_details_toggle"], size="1",
                                   weight="medium"),
                            spacing="2", align="center",
                        ),
                    ),
                ),
                rx.accordion.content(
                    rx.vstack(
                        _coordinate_row(),
                        rx.cond(
                            S.parcel["municipality"] != "Rural",
                            _row(S.tr["parcel_municipality"],
                                 S.parcel["municipality"]),
                            _row(S.tr["parcel_regional_district"],
                                 S.parcel["regional_district"]),
                        ),
                        _area_block(),
                        _row(S.tr["parcel_class"], S.parcel["parcel_class"]),
                        _row(S.tr["parcel_status"], S.parcel["parcel_status"]),
                        _row(S.tr["parcel_owner_type"], S.parcel["owner_type"]),
                        rx.cond(
                            S.parcel["plan_number"],
                            _row(S.tr["parcel_plan_number"],
                                 S.parcel["plan_number"], mono=True),
                        ),
                        _row(
                            S.tr["parcel_start_date"],
                            rx.cond(S.parcel["parcel_start_date"],
                                   S.parcel["parcel_start_date"],
                                   S.tr["parcel_start_date_none"]),
                        ),
                        _row(
                            S.tr["parcel_updated"],
                            rx.cond(S.parcel["when_updated"],
                                   S.parcel["when_updated"],
                                   S.tr["parcel_not_reported"]),
                        ),
                        _non_land_note(),
                        _neighbours(),
                        spacing="2", width="100%", padding_top="0.25rem",
                    ),
                    # See the Brazil page's own ``cadastro.py::
                    # _imovel_details_card`` for why this needs
                    # `padding_x="0"` — Radix's AccordionContent otherwise
                    # bakes in its own 16px, stacking on top of the
                    # sidebar's own and squeezing everything inward.
                    padding_x="0",
                ),
                value="details",
            ),
            type="single", collapsible=True, variant="ghost", width="100%",
            # `default_value`, not `value` — see the Brazil page's own
            # `cadastro.py::_imovel_details_card` for why `value` here would
            # make this accordion controlled-but-never-updated, i.e. stuck
            # open and unable to respond to clicks.
            default_value="details",
        ),
        _disclosure_box(S.disclosure),
    )


# --------------------------------------------------------------------------- #
# Kind: park — WDPA
# --------------------------------------------------------------------------- #
def _park_area_block() -> rx.Component:
    return rx.vstack(
        _row(S.tr["park_area_reported"],
             f"{S.area_registered_ha} ha", emphasis=True),
        _row(S.tr["park_area_calculated"], f"{S.area_calculated_ha} ha"),
        rx.cond(
            S.area_flagged,
            rx.callout(
                f"{S.tr['park_area_disagreement_prefix']} "
                f"{S.area_delta_ha} ha ({S.area_delta_pct}%). "
                f"{S.tr['park_area_disagreement_suffix']}",
                icon="ruler", color_scheme="amber", size="1",
            ),
        ),
        spacing="1", width="100%",
    )


def _park_card() -> rx.Component:
    return section(
        S.tr["park_title"],
        rx.callout(S.tr["park_no_parcel_note"], icon="tree-pine",
                  color_scheme="jade", size="1"),
        _row(S.tr["park_name"], S.parcel["identifier"]),
        _coordinate_row(),
        _row(S.tr["park_designation"], S.parcel["designation"]),
        _row(S.tr["park_designation_type"], S.parcel["designation_type"]),
        rx.cond(
            S.parcel["iucn_category"],
            _row(S.tr["park_iucn_category"], S.parcel["iucn_category"]),
        ),
        _row(S.tr["park_status"], S.parcel["park_status"]),
        rx.cond(
            S.parcel["status_year"],
            _row(S.tr["park_status_year"], S.parcel["status_year"]),
        ),
        _row(S.tr["park_managing_authority"], S.parcel["managing_authority"]),
        _park_area_block(),
        _disclosure_box(S.tr["park_disclosure"]),
    )


# --------------------------------------------------------------------------- #
# Kind: square — synthetic fallback
# --------------------------------------------------------------------------- #
def _square_card() -> rx.Component:
    return section(
        S.tr["square_title"],
        rx.callout(S.tr["square_note"], icon="square-dashed", color_scheme="gray",
                  size="1"),
        _row(S.tr["square_coordinate"], S.parcel["identifier"], mono=True),
        _row(S.tr["parcel_area_registered"], "500 ha", emphasis=True),
        _disclosure_box(S.tr["square_disclosure"]),
    )


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #
def parcel_card() -> rx.Component:
    return rx.cond(
        S.has_parcel,
        rx.match(
            S.parcel["kind"],
            ("park", _park_card()),
            ("square", _square_card()),
            _parcel_details_card(),
        ),
    )


def zones_panel() -> rx.Component:
    return rx.cond(
        S.zones,
        section(
            S.tr["zones_title"],
            rx.foreach(
                S.zones,
                lambda z: rx.hstack(
                    rx.text(z["zone_label"], size="1"),
                    rx.spacer(),
                    rx.text(f"{z['area_ha']} ha", size="1", color=MUTED),
                    width="100%",
                ),
            ),
            info=S.tr["zones_note"],
        ),
    )
