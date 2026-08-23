"""Land-cover transitions and the Sankey diagrams (doc/07-transitions.md).

The reducer is ported from Yvynation's ``compute_transitions``
(``band1 * 1000 + band2 → frequencyHistogram``), reshaped from one geometry to
Camposcope's zones — the same batched-``reduceRegions`` trick as
``mapbiomas_history.py``: one round trip covers every zone at once, not one
call per zone.

The two figure builders are ported from Yvynation's ``create_sankey_transitions``
/ ``create_multi_stage_sankey`` (``utils/visualization.py``), rewired onto this
app's own MapBiomas label/colour functions and language switch, otherwise the
same layout logic — it already works.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence, Tuple

import plotly.graph_objects as go

from ..config import mapbiomas as mb
from ..config.settings import EE_DEFAULT_SCALE_M, EE_MAX_PIXELS, EE_TILE_SCALE, SANKEY_MIN_YEAR_GAP
from .ee_client import get_ee
from .mapbiomas_history import MAPBIOMAS_ASSET, _zone_feature_collection
from .provenance import Provenance
from .zones import Zone

logger = logging.getLogger(__name__)

#: zone_key -> {src_class_id: {tgt_class_id: area_ha}}
TransitionsByZone = Dict[str, Dict[int, Dict[int, float]]]


class YearGapError(ValueError):
    """Raised when a Sankey pair is closer than :data:`SANKEY_MIN_YEAR_GAP`.

    At one- or two-year gaps most "transitions" are classification flicker in
    mixed pixels, not events on the ground (doc/07-transitions.md §5). Refused
    rather than silently produced.
    """


def _check_gap(year_a: int, year_b: int) -> None:
    if abs(year_b - year_a) < SANKEY_MIN_YEAR_GAP:
        raise YearGapError(
            f"Anos muito próximos ({year_a}→{year_b}): a diferença mínima "
            f"para um diagrama de transições é de {SANKEY_MIN_YEAR_GAP} anos, "
            "para não confundir ruído de classificação com mudança real."
        )


def compute_transitions(
    zones: Sequence[Zone],
    year_a: int,
    year_b: int,
    *,
    include_unchanged: bool = True,
    enforce_min_gap: bool = True,
) -> Tuple[TransitionsByZone, Provenance]:
    """Pixel-level transitions ``year_a → year_b`` for every zone, one call.

    ``include_unchanged`` (decision D8): ``True`` for a Sankey, so persistence
    gets a ribbon and the columns' totals stay constant — ``False`` would show
    land evaporating between columns. ``False`` for a transition matrix /
    gains-losses table, where only change is being counted.
    """
    if enforce_min_gap:
        _check_gap(year_a, year_b)
    if not zones:
        raise ValueError("Nenhuma zona para analisar.")

    get_ee()
    import ee

    band_a, band_b = mb.band_for_year(year_a), mb.band_for_year(year_b)
    img = ee.Image(MAPBIOMAS_ASSET)
    combined = (img.select(band_a).multiply(1000).add(img.select(band_b))
               .rename("combined"))
    fc = _zone_feature_collection(zones)

    prov = Provenance(
        name="mapbiomas_transitions",
        dataset_id=MAPBIOMAS_ASSET,
        bands=[band_a, band_b],
        scale_m=EE_DEFAULT_SCALE_M,
        reducer="frequencyHistogram(src*1000+tgt)",
        pixel_area_basis="mean ee.Image.pixelArea() per zone",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={"year_a": year_a, "year_b": year_b,
              "include_unchanged": include_unchanged,
              "zones": [z.key for z in zones]},
    )

    from concurrent.futures import ThreadPoolExecutor

    def hist_call():
        return combined.reduceRegions(
            collection=fc, reducer=ee.Reducer.frequencyHistogram(),
            scale=EE_DEFAULT_SCALE_M, tileScale=EE_TILE_SCALE,
        ).getInfo()

    def area_call():
        return ee.Image.pixelArea().reduceRegions(
            collection=fc, reducer=ee.Reducer.mean(),
            scale=EE_DEFAULT_SCALE_M, tileScale=EE_TILE_SCALE,
        ).getInfo()

    with ThreadPoolExecutor(max_workers=2) as ex:
        f_hist, f_area = ex.submit(hist_call), ex.submit(area_call)
        hist, areas = f_hist.result(), f_area.result()

    px_area = {
        f["properties"]["zone_key"]: float(f["properties"].get("mean") or 900.0)
        for f in areas["features"]
    }

    out: TransitionsByZone = {}
    for feat in hist["features"]:
        props = feat["properties"]
        zone_key = props["zone_key"]
        area_per_px_ha = px_area.get(zone_key, 900.0) / 10_000.0
        # `reduceRegions` names the output after the reducer ("histogram") when
        # exactly one band is selected — it does NOT use the band's own name,
        # even when it was explicitly `.rename("combined")`. Same quirk
        # documented in mapbiomas_history.py for the single-year case.
        raw: Dict[str, float] = props.get("histogram") or {}

        zone_transitions: Dict[int, Dict[int, float]] = {}
        for combined_str, count in raw.items():
            combined_val = int(float(combined_str))
            src, tgt = combined_val // 1000, combined_val % 1000
            if src == 0 and tgt == 0:
                continue
            if not include_unchanged and src == tgt:
                continue
            area_ha = float(count) * area_per_px_ha
            if area_ha <= 0:
                continue
            zone_transitions.setdefault(src, {})[tgt] = (
                zone_transitions.setdefault(src, {}).get(tgt, 0.0) + area_ha
            )
        out[zone_key] = zone_transitions

    prov.extra["mean_pixel_area_m2"] = {k: round(v, 2) for k, v in px_area.items()}
    logger.info("Transitions %s→%s: %s zones", year_a, year_b, len(out))
    return out, prov


# --------------------------------------------------------------------------- #
# Two-stage Sankey
# --------------------------------------------------------------------------- #
def _label(class_id: Any, lang: str) -> str:
    try:
        return mb.label(int(class_id), lang)
    except (ValueError, TypeError):
        return str(class_id)


def _color(class_id: Any) -> str:
    try:
        return f"#{mb.color(int(class_id)).lstrip('#')}"
    except (ValueError, TypeError):
        return "#cccccc"


def sankey_figure(
    transitions: Dict[int, Dict[int, float]],
    year_a: int,
    year_b: int,
    *,
    lang: str = "pt",
) -> "go.Figure | None":
    """Two-stage Sankey for one zone's transitions dict.

    Ported from Yvynation's ``create_sankey_transitions``: node height ∝ total
    flow through it, ribbons take the SOURCE class's colour, nodes sorted
    largest-first.
    """
    if not transitions:
        return None

    sources: List[str] = []
    targets: List[str] = []
    values: List[float] = []
    link_colors: List[str] = []

    for src_id, tgt_dict in transitions.items():
        for tgt_id, area in tgt_dict.items():
            if area <= 0:
                continue
            src_label = f"{_label(src_id, lang)} ({year_a})"
            tgt_label = f"{_label(tgt_id, lang)} ({year_b})"
            sources.append(src_label)
            targets.append(tgt_label)
            values.append(area)
            link_colors.append(_color(src_id))

    if not sources:
        return None

    all_nodes = list(dict.fromkeys(sources + targets))
    node_flow: Dict[str, float] = {}
    for s, t, v in zip(sources, targets, values):
        node_flow[s] = node_flow.get(s, 0) + v
        node_flow[t] = node_flow.get(t, 0) + v

    sorted_nodes = sorted(all_nodes, key=lambda n: node_flow.get(n, 0), reverse=True)
    node_labels = [f"{n}<br>({node_flow.get(n, 0):,.0f} ha)" for n in sorted_nodes]
    node_idx = {n: i for i, n in enumerate(sorted_nodes)}
    node_colors = [_color_from_display(n) for n in sorted_nodes]

    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=20, thickness=20, line=dict(color="black", width=0.5),
                  label=node_labels, color=node_colors),
        link=dict(
            source=[node_idx[s] for s in sources],
            target=[node_idx[t] for t in targets],
            value=values,
            color=link_colors,
            label=[f"{s} → {t} ({v:,.1f} ha)" for s, t, v in zip(sources, targets, values)],
        ),
    )])
    fig.update_layout(
        margin=dict(l=8, r=8, t=8, b=8),
        font=dict(size=10),
        height=420,
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _color_from_display(node_label: str) -> str:
    """A node's own colour, recovered from its display string.

    The node label carries the class name, not its id — this walks the
    MapBiomas legend to find the matching colour rather than threading a
    parallel id list through the whole node-building pass above.
    """
    name = node_label.split(" (")[0]
    for cid in range(0, 62):
        if mb.label(cid, "pt") == name or mb.label(cid, "en") == name:
            return _color(cid)
    return "#cccccc"


# --------------------------------------------------------------------------- #
# Multi-stage Sankey
# --------------------------------------------------------------------------- #
def multi_stage_sankey_figure(
    stages: List[Tuple[int, int, Dict[int, Dict[int, float]]]],
    *,
    lang: str = "pt",
) -> "go.Figure | None":
    """Sankey across an arbitrary ordered list of years, one zone.

    ``stages``: ``[(year_from, year_to, transitions_dict), ...]`` — chained,
    so ``stages[i].year_to == stages[i+1].year_from``. Ported from Yvynation's
    ``create_multi_stage_sankey``: node height ∝ share of that year's total,
    columns positioned left→right by year.
    """
    if not stages:
        return None

    year_order = [stages[0][0]] + [s[1] for s in stages]
    year_totals: Dict[int, Dict[int, float]] = {y: {} for y in year_order}
    records: List[Tuple[int, int, int, int, float]] = []

    n_stages = len(stages)
    for i, (y_from, y_to, tdict) in enumerate(stages):
        is_last = i == n_stages - 1
        for src_id, tgt_dict in tdict.items():
            for tgt_id, area in tgt_dict.items():
                if area <= 0:
                    continue
                records.append((y_from, src_id, y_to, tgt_id, area))
                year_totals[y_from][src_id] = year_totals[y_from].get(src_id, 0.0) + area
                if is_last:
                    year_totals[y_to][tgt_id] = year_totals[y_to].get(tgt_id, 0.0) + area

    if not records:
        return None

    n_years = len(year_order)
    x_positions = {y: max(0.001, min(0.999, i / max(n_years - 1, 1)))
                  for i, y in enumerate(year_order)}

    node_index: Dict[Tuple[int, int], int] = {}
    node_labels: List[str] = []
    node_colors: List[str] = []
    node_x: List[float] = []
    node_y: List[float] = []
    GAP = 0.01

    for y in year_order:
        classes = year_totals[y]
        if not classes:
            continue
        total = sum(classes.values()) or 1.0
        ordered = sorted(classes.items(), key=lambda kv: kv[1], reverse=True)
        n = len(ordered)
        usable = max(1e-6, 1.0 - GAP * (n - 1))
        cursor = 0.0
        for cls_id, area in ordered:
            frac = area / total
            height = frac * usable
            y_center = cursor + height / 2.0
            cursor += height + GAP
            node_index[(y, cls_id)] = len(node_labels)
            node_labels.append(
                f"{_label(cls_id, lang)} ({y})<br>{area:,.0f} ha ({frac * 100:.1f}%)"
            )
            node_colors.append(_color(cls_id))
            node_x.append(x_positions[y])
            node_y.append(max(0.001, min(0.999, y_center)))

    sources_i: List[int] = []
    targets_i: List[int] = []
    values: List[float] = []
    link_colors: List[str] = []
    for y_from, src_id, y_to, tgt_id, area in records:
        s = node_index.get((y_from, src_id))
        t = node_index.get((y_to, tgt_id))
        if s is None or t is None:
            continue
        sources_i.append(s)
        targets_i.append(t)
        values.append(area)
        link_colors.append(_color(src_id))

    if not sources_i:
        return None

    fig = go.Figure(data=[go.Sankey(
        arrangement="fixed",
        node=dict(pad=12, thickness=18, line=dict(color="black", width=0.4),
                  label=node_labels, color=node_colors, x=node_x, y=node_y),
        link=dict(source=sources_i, target=targets_i, value=values,
                  color=link_colors,
                  label=[f"{v:,.1f} ha" for v in values]),
    )])
    n_cols = len(year_order)
    fig.update_layout(
        margin=dict(l=8, r=8, t=8, b=8),
        font=dict(size=10),
        width=min(1600, max(500, 110 * n_cols)),
        height=460,
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def default_multi_stage_years(
    year_start: int, registration_year: "int | None", year_end: int,
) -> List[int]:
    """Before · at registration · now (doc/07-transitions.md §3.2).

    The property's own registration date framed between the series' bounds —
    the default set that makes the multi-stage Sankey read as a story about
    THIS property rather than a generic 40-year strip.
    """
    years = {year_start, year_end}
    if registration_year and year_start < registration_year < year_end:
        years.add(registration_year)
    return sorted(years)


__all__ = [
    "TransitionsByZone", "YearGapError",
    "compute_transitions", "sankey_figure", "multi_stage_sankey_figure",
    "default_multi_stage_years",
]
