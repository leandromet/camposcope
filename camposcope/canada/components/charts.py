"""Charts for the Canada page.

Ported from :mod:`camposcope.components.charts` onto the AAFC legend, with the
Brazil chart's CAR-registration marker replaced by the parcel's own start date
(when it has one — see ``canada/services/hansen.py`` for how often it does not).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go

from ..config import aafc as mb

#: Stacked bottom-to-top: natural formations first, cropland/pasture above,
#: water and no-data last — same ordering rule the Brazil chart uses,
#: reapplied to the ACI's own hierarchy.
_STACK_PRIORITY = mb.STACK_PRIORITY


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
    lang: str = "en",
    normalise: bool = False,
    start_year: Optional[int] = None,
) -> go.Figure:
    fig = go.Figure()
    sub = pd.DataFrame.from_records(rows) if rows else pd.DataFrame()

    if sub.empty:
        fig.add_annotation(
            text="Sem dados" if lang == "pt" else "No data",
            showarrow=False, font=dict(size=13, color="#888"),
        )
        return _style(fig, lang, normalise, start_year, years=[])

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
            x=years, y=values, name=name,
            marker_color=mb.color(int(class_id)), marker_line_width=0,
            hovertemplate=f"<b>{name}</b><br>%{{x}}<br>%{{y:,.1f}} {unit}"
                         "<extra></extra>",
        )

    return _style(fig, lang, normalise, start_year, years)


def _style(fig: go.Figure, lang: str, normalise: bool,
           start_year: Optional[int], years: List[int]) -> go.Figure:
    unit = "%" if normalise else "ha"
    y_title = ("Área (%)" if normalise else "Área (ha)") if lang == "pt" else \
              ("Area (%)" if normalise else "Area (ha)")

    fig.update_layout(
        barmode="stack", bargap=0.06, template="plotly_white",
        margin=dict(l=56, r=8, t=8, b=36), height=340,
        legend=dict(orientation="h", yanchor="top", y=-0.16, x=0,
                   font=dict(size=10), itemsizing="constant"),
        hovermode="x unified",
        xaxis=dict(title=None, tickmode="linear", dtick=2, showgrid=False),
        yaxis=dict(title=y_title, showgrid=True,
                   gridcolor="rgba(0,0,0,0.06)", zeroline=False),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    if normalise:
        fig.update_yaxes(range=[0, 100])

    if start_year and years and years[0] <= start_year <= years[-1]:
        label = "início da parcela" if lang == "pt" else "parcel start"
        fig.add_vline(
            x=start_year, line_width=1.5, line_dash="dash", line_color="#f5a524",
            annotation_text=f"{label} ({start_year})", annotation_position="top",
            annotation_font_size=10, annotation_font_color="#f5a524",
        )

    return fig


# --------------------------------------------------------------------------- #
# Floresta (Hansen), Biomassa and Fogo
# --------------------------------------------------------------------------- #
HANSEN_PERIOD_COLOR = {
    "antes_da_parcela": "#f5a524",
    "apos_a_parcela": "#e5484d",
    "sem_divisao": "#8b1a1a",
}
_HANSEN_PERIOD_LABEL_EN = {
    "antes_da_parcela": "Before the parcel existed",
    "apos_a_parcela": "After the parcel was created",
    "sem_divisao": "Loss (undivided)",
}
_HANSEN_PERIOD_LABEL_PT = {
    "antes_da_parcela": "Antes da parcela existir",
    "apos_a_parcela": "Depois da criação da parcela",
    "sem_divisao": "Perda (não dividida)",
}


def hansen_period_labels(lang: str = "en") -> Dict[str, str]:
    return _HANSEN_PERIOD_LABEL_PT if lang == "pt" else _HANSEN_PERIOD_LABEL_EN


def hansen_figure(rows: List[Dict[str, Any]], lang: str = "en") -> go.Figure:
    labels = hansen_period_labels(lang)
    fig = go.Figure()
    if not rows:
        fig.add_annotation(
            text="Sem dados" if lang == "pt" else "No data",
            showarrow=False, font=dict(size=13, color="#888"),
        )
    else:
        for period in ("antes_da_parcela", "apos_a_parcela", "sem_divisao"):
            bucket = [r for r in rows if r["period"] == period]
            if not bucket:
                continue
            fig.add_bar(
                x=[r["year"] for r in bucket], y=[r["area_ha"] for r in bucket],
                name=labels[period], marker_color=HANSEN_PERIOD_COLOR[period],
            )
    fig.update_layout(
        barmode="stack", template="plotly_white",
        margin=dict(l=48, r=8, t=8, b=36), height=260,
        legend=dict(orientation="h", yanchor="top", y=-0.22, x=0,
                   font=dict(size=9)),
        xaxis=dict(title=None, tickmode="linear", dtick=2),
        yaxis=dict(title="Perda (ha)" if lang == "pt" else "Loss (ha)"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def biomass_figure(rows: List[Dict[str, Any]], lang: str = "en") -> go.Figure:
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
        xaxis=dict(title=None, tickmode="linear", dtick=2),
        yaxis=dict(title="Biomassa (Mg/ha)" if lang == "pt" else "Biomass (Mg/ha)"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def fire_figure(rows: List[Dict[str, Any]], lang: str = "en") -> go.Figure:
    fig = go.Figure()
    if not rows:
        fig.add_annotation(
            text="Sem dados" if lang == "pt" else "No data",
            showarrow=False, font=dict(size=13, color="#888"),
        )
    else:
        ordered = sorted(rows, key=lambda r: r["year"])
        fig.add_bar(
            x=[r["year"] for r in ordered], y=[r["fire_pct"] for r in ordered],
            marker=dict(color="#d4271e"),
            hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
        )
    fig.update_layout(
        template="plotly_white", margin=dict(l=48, r=8, t=8, b=28), height=260,
        xaxis=dict(title=None, tickmode="linear", dtick=2),
        yaxis=dict(title="Área queimada (%)" if lang == "pt" else "Burned area (%)"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def aci_burn_figure(rows: List[Dict[str, Any]], lang: str = "en") -> go.Figure:
    """ACI class-60 burnt share per year — the AAFC-source counterpart to
    :func:`fire_figure`. A narrower record than MODIS (2009–2025, national
    from 2011) and sparser: most years show no bar at all, which is the
    honest picture of a land-cover class rather than a dedicated burn
    product — see ``canada/services/fire.py``'s module docstring."""
    fig = go.Figure()
    if not rows:
        fig.add_annotation(
            text="Sem dados" if lang == "pt" else "No data",
            showarrow=False, font=dict(size=13, color="#888"),
        )
    else:
        ordered = sorted(rows, key=lambda r: r["year"])
        fig.add_bar(
            x=[r["year"] for r in ordered], y=[r["burnt_pct"] for r in ordered],
            marker=dict(color="#bd0026"),
            hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
        )
    fig.update_layout(
        template="plotly_white", margin=dict(l=48, r=8, t=8, b=28), height=260,
        xaxis=dict(title=None, tickmode="linear", dtick=2),
        yaxis=dict(title="Área queimada (%)" if lang == "pt" else "Burned area (%)"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def landscape_meff_figure(rows: List[Dict[str, Any]], lang: str = "en") -> go.Figure:
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
        yaxis=dict(title="Meff (ha)"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


__all__ = [
    "land_cover_history_figure", "hansen_figure", "hansen_period_labels",
    "HANSEN_PERIOD_COLOR", "biomass_figure", "fire_figure", "aci_burn_figure",
    "landscape_meff_figure",
]
