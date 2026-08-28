"""Charts.

The signature view is the land-cover trajectory: one stacked column per year,
1985–2024, coloured with the **official MapBiomas palette**
(doc/08-ui-ux.md §5). Ported in spirit from Naturametrics'
``components/charts.py``: same stack ordering, same styling — the one addition
is the property's own registration-date marker on the axis
(doc/01-premises.md §1, doc/03-roadmap.md Phase 3).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go

from ..config import mapbiomas as mb

#: Classes are stacked in this order so the reading is stable across years:
#: natural formations at the bottom, anthropic above, water and no-data last.
_STACK_PRIORITY = (
    list(mb.FOREST_FORMATIONS) + list(mb.SAVANNA_FORMATIONS)
    + list(mb.NATURAL_NON_FOREST) + list(mb.PLANTED_FOREST)
)


def _order_classes(class_ids: List[int]) -> List[int]:
    def key(c: int):
        if c in _STACK_PRIORITY:
            return (0, _STACK_PRIORITY.index(c))
        if c in mb.WATER:
            return (2, c)
        if c in mb.NO_DATA:
            return (3, c)
        return (1, c)
    return sorted(class_ids, key=key)


def land_cover_history_figure(
    rows: List[Dict[str, Any]],
    *,
    lang: str = "pt",
    normalise: bool = False,
    registration_year: Optional[int] = None,
) -> go.Figure:
    """Stacked columns: one column per year, segments coloured by MapBiomas
    class, for rows already filtered to one zone.

    ``registration_year`` draws the property's own ``dat_criacao`` on the axis
    — the one line no other app in the family has anywhere to put
    (doc/01-premises.md §1).
    """
    fig = go.Figure()
    sub = pd.DataFrame.from_records(rows) if rows else pd.DataFrame()

    if sub.empty:
        fig.add_annotation(
            text="Sem dados" if lang == "pt" else "No data",
            showarrow=False, font=dict(size=13, color="#888"),
        )
        return _style(fig, lang, normalise, registration_year, years=[])

    value_col = "area_ha"
    if normalise:
        sub = sub.copy()
        totals = sub.groupby("year")["area_ha"].transform("sum")
        sub["area_pct"] = sub["area_ha"] / totals * 100.0
        value_col = "area_pct"

    years = sorted(sub["year"].unique())
    unit = "%" if normalise else "ha"

    for class_id in _order_classes(sorted(sub["class_id"].unique())):
        by_year = sub[sub["class_id"] == class_id].set_index("year")
        values = [float(by_year[value_col].get(y, 0.0)) for y in years]
        if not any(values):
            continue
        name = mb.label(int(class_id), lang)
        fig.add_bar(
            x=years,
            y=values,
            name=name,
            marker_color=mb.color(int(class_id)),
            marker_line_width=0,
            hovertemplate=f"<b>{name}</b><br>%{{x}}<br>%{{y:,.1f}} {unit}<extra></extra>",
        )

    return _style(fig, lang, normalise, registration_year, years)


def _style(
    fig: go.Figure, lang: str, normalise: bool,
    registration_year: Optional[int], years: List[int],
) -> go.Figure:
    unit = "%" if normalise else "ha"
    y_title = ("Área (%)" if normalise else "Área (ha)") if lang == "pt" else \
              ("Area (%)" if normalise else "Area (ha)")

    fig.update_layout(
        barmode="stack",
        bargap=0.06,
        template="plotly_white",
        margin=dict(l=56, r=8, t=8, b=36),
        height=340,
        legend=dict(
            orientation="h", yanchor="top", y=-0.16, x=0,
            font=dict(size=10), itemsizing="constant",
        ),
        hovermode="x unified",
        # dragmode False + fixedrange on both axes: with the modebar off
        # (export_widgets.PLOTLY_CONFIG), Plotly's own click-drag zoom/pan was
        # already undiscoverable on desktop, but on a phone it still grabbed
        # a one-finger touch-drag for itself — the gesture that should have
        # scrolled the sheet/page past the chart instead started a zoom.
        # Disabling it here lets that touch fall through to the container.
        dragmode=False,
        xaxis=dict(title=None, tickmode="linear", dtick=5, showgrid=False,
                   fixedrange=True),
        yaxis=dict(title=y_title, showgrid=True,
                   gridcolor="rgba(0,0,0,0.06)", zeroline=False,
                   fixedrange=True),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    if normalise:
        fig.update_yaxes(range=[0, 100])

    # The property's own registration date, drawn on every trajectory chart —
    # doc/01-premises.md §1: this is the axis no sibling app has anywhere to
    # put. Only drawn when it falls inside the plotted range.
    if registration_year and years and years[0] <= registration_year <= years[-1]:
        label = "registro CAR" if lang == "pt" else "CAR registration"
        fig.add_vline(
            x=registration_year,
            line_width=1.5,
            line_dash="dash",
            line_color="#f5a524",
            annotation_text=f"{label} ({registration_year})",
            annotation_position="top",
            annotation_font_size=10,
            annotation_font_color="#f5a524",
        )

    return fig


# --------------------------------------------------------------------------- #
# Floresta (Hansen), Biomassa and Fogo — extracted from state/_analysis.py's
# own rx.var figure builders (services/report.py needs the exact figure the
# screen shows, built off the same rows, and a Reflex state class is not
# importable from a plain service module — same "one figure-builder, two
# callers" discipline land_cover_history_figure above already followed).
# --------------------------------------------------------------------------- #

#: One colour per Hansen loss period — amber/red/dark-red reading as
#: "further from today", not a severity scale.
HANSEN_PERIOD_COLOR = {
    "ate_2008": "#f5a524",
    "2008_ate_registro": "#e5484d",
    "apos_registro": "#8b1a1a",
}
_HANSEN_PERIOD_LABEL_PT = {
    "ate_2008": "Até 2008",
    "2008_ate_registro": "2008 até o registro",
    "apos_registro": "Depois do registro",
}
_HANSEN_PERIOD_LABEL_EN = {
    "ate_2008": "Up to 2008",
    "2008_ate_registro": "2008 to registration",
    "apos_registro": "After registration",
}


def hansen_period_labels(lang: str = "pt") -> Dict[str, str]:
    return _HANSEN_PERIOD_LABEL_EN if lang == "en" else _HANSEN_PERIOD_LABEL_PT


def hansen_figure(rows: List[Dict[str, Any]], lang: str = "pt") -> go.Figure:
    """Hansen forest-loss bars, split into the three periods anchored on the
    Forest Code's 2008 reference date and the property's own registration
    (doc/04 §3) — for rows already filtered to one zone."""
    labels = hansen_period_labels(lang)
    fig = go.Figure()
    if not rows:
        fig.add_annotation(
            text="Sem dados" if lang == "pt" else "No data",
            showarrow=False, font=dict(size=13, color="#888"),
        )
    else:
        for period in ("ate_2008", "2008_ate_registro", "apos_registro"):
            bucket = [r for r in rows if r["period"] == period]
            if not bucket:
                continue
            fig.add_bar(
                x=[r["year"] for r in bucket], y=[r["area_ha"] for r in bucket],
                name=labels[period],
                marker_color=HANSEN_PERIOD_COLOR[period],
            )
    fig.update_layout(
        barmode="stack", template="plotly_white",
        margin=dict(l=48, r=8, t=8, b=36), height=260,
        legend=dict(orientation="h", yanchor="top", y=-0.22, x=0,
                   font=dict(size=9)),
        # See land_cover_history_figure's _style() for why: stops a
        # one-finger touch on the chart from being captured as a zoom
        # gesture instead of scrolling the sheet/page past it.
        dragmode=False,
        xaxis=dict(title=None, tickmode="linear", dtick=2, fixedrange=True),
        yaxis=dict(title="Perda (ha)" if lang == "pt" else "Loss (ha)",
                   fixedrange=True),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def biomass_figure(rows: List[Dict[str, Any]], lang: str = "pt") -> go.Figure:
    """ESA CCI above-ground biomass, ten snapshots with a real gap drawn as a
    gap — for rows already filtered to one zone."""
    fig = go.Figure()
    ordered = sorted(rows, key=lambda r: r["year"]) if rows else []
    if not ordered:
        fig.add_annotation(
            text="Sem dados" if lang == "pt" else "No data",
            showarrow=False, font=dict(size=13, color="#888"),
        )
    else:
        fig.add_scatter(
            x=[r["year"] for r in ordered], y=[r["agb_mean_mgha"] for r in ordered],
            mode="markers+lines", connectgaps=False,
            line=dict(color="#1f8d49"), marker=dict(size=8),
            hovertemplate="%{x}: %{y:.1f} Mg/ha<extra></extra>",
        )
    fig.update_layout(
        template="plotly_white", margin=dict(l=48, r=8, t=8, b=28), height=300,
        dragmode=False,
        xaxis=dict(title=None, tickmode="linear", dtick=2, fixedrange=True),
        yaxis=dict(title="Biomassa (Mg/ha)" if lang == "pt" else "Biomass (Mg/ha)",
                   fixedrange=True),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def fire_figure(annual_rows: List[Dict[str, Any]], lang: str = "pt") -> go.Figure:
    """One bar per MapBiomas Fire year, % of the zone burned that year — for
    annual rows already filtered to one zone."""
    from ..services.fire import FIRE_YEARS

    values_by_year = {r["year"]: r["fire_pct"] for r in annual_rows}
    fig = go.Figure()
    if not values_by_year:
        fig.add_annotation(
            text="Sem dados" if lang == "pt" else "No data",
            showarrow=False, font=dict(size=13, color="#888"),
        )
    else:
        years = FIRE_YEARS
        values = [values_by_year.get(y, 0.0) for y in years]
        fig.add_bar(
            x=years, y=values,
            marker=dict(color="#d4271e"),
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        )
    fig.update_layout(
        template="plotly_white", margin=dict(l=48, r=8, t=8, b=28), height=260,
        dragmode=False,
        xaxis=dict(title=None, tickmode="linear", dtick=5, fixedrange=True),
        yaxis=dict(
            title="Área queimada (%)" if lang == "pt" else "Burned area (%)",
            range=[0, 100], fixedrange=True,
        ),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def landscape_meff_figure(rows: List[Dict[str, Any]], lang: str = "pt") -> go.Figure:
    """Effective mesh size (meff_ha) per zone — one bar per zone, property
    first then rings outward, so fragmentation can be read at a glance
    without cross-referencing the table."""
    fig = go.Figure()
    if not rows:
        fig.add_annotation(
            text="Sem dados" if lang == "pt" else "No data",
            showarrow=False, font=dict(size=13, color="#888"),
        )
    else:
        fig.add_bar(
            x=[r["zone_label"] for r in rows], y=[r["meff_ha"] for r in rows],
            marker=dict(color="#1f8d49"),
            hovertemplate="%{x}: %{y:,.1f} ha<extra></extra>",
        )
    fig.update_layout(
        template="plotly_white", margin=dict(l=48, r=8, t=8, b=48), height=260,
        dragmode=False,
        xaxis=dict(fixedrange=True),
        yaxis=dict(title="Meff (ha)", fixedrange=True),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


__all__ = [
    "land_cover_history_figure", "hansen_figure", "hansen_period_labels",
    "HANSEN_PERIOD_COLOR", "biomass_figure", "fire_figure",
    "landscape_meff_figure",
]
