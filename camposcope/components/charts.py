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
        xaxis=dict(title=None, tickmode="linear", dtick=5, showgrid=False),
        yaxis=dict(title=y_title, showgrid=True,
                   gridcolor="rgba(0,0,0,0.06)", zeroline=False),
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


__all__ = ["land_cover_history_figure"]
