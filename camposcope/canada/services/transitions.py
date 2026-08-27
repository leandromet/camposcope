"""ACI land-cover transitions and the Sankey diagram.

A port of :mod:`camposcope.services.transitions` onto the AAFC legend. The
reducer is the same ``band_a * 1000 + band_b → frequencyHistogram`` trick, over
the same batched ``zone_feature_collection``: one round trip covers every zone.

**One thing had to change, and it is not cosmetic.** The Brazil version packs
two class codes into one integer as ``src * 1000 + tgt``, which is safe because
MapBiomas codes top out at 62. **ACI codes go up to 230**, so ``src * 1000 +
tgt`` is still unambiguous (230 < 1000) — but only just, and only because the
multiplier was already generous. It is asserted at import rather than left as a
coincidence that a future legend extension could silently break: a code of 1000
or more would fold two different transitions onto the same integer and the
resulting Sankey would be quietly wrong rather than obviously broken.

**The minimum year gap is different too.** MapBiomas spans forty years and the
Brazil page refuses pairs closer than five, because at one or two years apart
most "transitions" are classification flicker in mixed pixels. The ACI spans
fifteen usable years, so a five-year floor would leave very few legal pairs —
and its flicker problem is worse, not better, since annual crop rotation is a
real land-cover change that a user is rarely asking about. The floor is kept at
three years and the copy says explicitly that a change of crop between two years
is rotation, not conversion.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence, Tuple

import plotly.graph_objects as go

from ...config.settings import EE_DEFAULT_SCALE_M, EE_MAX_PIXELS, EE_TILE_SCALE
from ...services.ee_client import get_ee
from ...services.provenance import Provenance
from ...services.zones import Zone
from ..config import aafc
from .aci_history import ACI_ASSET, stacked_aci_image
from .ee_zones import mean_pixel_area, px_area_by_zone, zone_feature_collection

logger = logging.getLogger(__name__)

#: zone_key -> {src_class_id: {tgt_class_id: area_ha}}
TransitionsByZone = Dict[str, Dict[int, Dict[int, float]]]

#: The packing multiplier — see the module docstring. Asserted, not assumed.
_PACK = 1000
assert max(aafc.ACI_LABELS_EN) < _PACK, (
    "An ACI class code has outgrown the transition packing multiplier; "
    "src*%d+tgt would collide." % _PACK
)

#: Three years, not the Brazil page's five. See the module docstring.
MIN_YEAR_GAP = 3


class YearGapError(ValueError):
    """Raised when a Sankey pair is closer than :data:`MIN_YEAR_GAP`."""


def _check_gap(year_a: int, year_b: int, lang: str = "en") -> None:
    if abs(year_b - year_a) >= MIN_YEAR_GAP:
        return
    if lang == "pt":
        raise YearGapError(
            f"Anos muito próximos ({year_a}→{year_b}): a diferença mínima para "
            f"um diagrama de transições é de {MIN_YEAR_GAP} anos. Entre anos "
            "consecutivos, a maior parte das 'transições' do inventário de "
            "culturas é rotação de lavoura, não conversão de uso da terra."
        )
    raise YearGapError(
        f"Those years are too close ({year_a}→{year_b}): the minimum gap for a "
        f"transition diagram is {MIN_YEAR_GAP} years. Between consecutive years "
        "most crop-inventory 'transitions' are crop rotation, not a change of "
        "land use."
    )


def compute_transitions(
    zones: Sequence[Zone],
    year_a: int,
    year_b: int,
    *,
    include_unchanged: bool = True,
    enforce_min_gap: bool = True,
    lang: str = "en",
) -> Tuple[TransitionsByZone, Provenance]:
    """Pixel-level transitions ``year_a → year_b`` for every zone, one call.

    ``include_unchanged`` is ``True`` for a Sankey, so persistence gets a ribbon
    and the columns' totals stay constant — ``False`` would show land
    evaporating between columns. ``False`` for a transition matrix, where only
    change is being counted.
    """
    if enforce_min_gap:
        _check_gap(year_a, year_b, lang)
    if not zones:
        raise ValueError("No zones to analyse.")

    get_ee()
    import ee

    from concurrent.futures import ThreadPoolExecutor

    band_a, band_b = aafc.band_for_year(year_a), aafc.band_for_year(year_b)
    # Only the two years are stacked, not all seventeen: the reducer needs two
    # bands and building the other fifteen would cost EE work nothing reads.
    img = stacked_aci_image([year_a, year_b])
    combined = (img.select(band_a).multiply(_PACK).add(img.select(band_b))
                .rename("combined"))
    fc = zone_feature_collection(zones)

    prov = Provenance(
        name="aafc_aci_transitions",
        dataset_id=ACI_ASSET,
        bands=[band_a, band_b],
        scale_m=EE_DEFAULT_SCALE_M,
        reducer=f"frequencyHistogram(src*{_PACK}+tgt)",
        pixel_area_basis="mean ee.Image.pixelArea() per zone",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={"year_a": year_a, "year_b": year_b,
               "include_unchanged": include_unchanged,
               "zones": [z.key for z in zones],
               "min_year_gap": MIN_YEAR_GAP},
    )

    def hist_call():
        return combined.reduceRegions(
            collection=fc, reducer=ee.Reducer.frequencyHistogram(),
            scale=EE_DEFAULT_SCALE_M, tileScale=EE_TILE_SCALE,
        ).getInfo()

    with ThreadPoolExecutor(max_workers=2) as ex:
        f_hist = ex.submit(hist_call)
        f_area = ex.submit(mean_pixel_area, fc, EE_DEFAULT_SCALE_M, EE_TILE_SCALE)
        hist, areas = f_hist.result(), f_area.result()

    px_area = px_area_by_zone(areas)

    out: TransitionsByZone = {}
    for feat in hist["features"]:
        props = feat["properties"]
        zone_key = props["zone_key"]
        area_per_px_ha = px_area.get(zone_key, 900.0) / 10_000.0
        # ``reduceRegions`` names the output after the reducer ("histogram")
        # when exactly one band is selected — it does NOT use the band's own
        # name, even after an explicit ``.rename("combined")``. Same quirk the
        # history parser documents for the single-year case.
        raw: Dict[str, float] = props.get("histogram") or {}

        zone_transitions: Dict[int, Dict[int, float]] = {}
        for combined_str, count in raw.items():
            combined_val = int(float(combined_str))
            src, tgt = combined_val // _PACK, combined_val % _PACK
            if src == 0 and tgt == 0:
                continue
            if not include_unchanged and src == tgt:
                continue
            area_ha = float(count) * area_per_px_ha
            if area_ha <= 0:
                continue
            bucket = zone_transitions.setdefault(src, {})
            bucket[tgt] = bucket.get(tgt, 0.0) + area_ha
        out[zone_key] = zone_transitions

    prov.extra["mean_pixel_area_m2"] = {k: round(v, 2) for k, v in px_area.items()}
    logger.info("ACI transitions %s→%s: %s zones", year_a, year_b, len(out))
    return out, prov


# --------------------------------------------------------------------------- #
# Sankey
# --------------------------------------------------------------------------- #
def _label(class_id: Any, lang: str) -> str:
    try:
        return aafc.label(int(class_id), lang)
    except (ValueError, TypeError):
        return str(class_id)


def _color(class_id: Any) -> str:
    try:
        return f"#{aafc.color(int(class_id)).lstrip('#')}"
    except (ValueError, TypeError):
        return "#cccccc"


def sankey_figure(
    transitions: Dict[int, Dict[int, float]],
    year_a: int,
    year_b: int,
    *,
    lang: str = "en",
) -> "go.Figure | None":
    """Two-stage Sankey for one zone's transitions dict.

    Node height ∝ total flow through it, ribbons take the SOURCE class's colour,
    nodes sorted largest-first — the same layout the Brazil page uses, so the
    two read identically.

    **Node identity is carried, not recovered.** The Brazil version reconstructs
    a node's colour by walking the legend for a matching label string
    (``_color_from_display``). That works with 60-odd classes whose names are
    unique; the ACI has 74, several of which are near-duplicates ("Other Grains"
    / "Other Crops" / "Other Oilseeds"), and its Portuguese and English tables
    are not injective either. So the class id is kept alongside each node
    instead of being re-derived from its label — one list, no lookup that can
    silently match the wrong class.
    """
    if not transitions:
        return None

    sources: List[str] = []
    targets: List[str] = []
    values: List[float] = []
    link_colors: List[str] = []
    #: node display string → its class id, populated as nodes are created.
    node_class: Dict[str, int] = {}

    for src_id, tgt_dict in transitions.items():
        for tgt_id, area in tgt_dict.items():
            if area <= 0:
                continue
            src_label = f"{_label(src_id, lang)} ({year_a})"
            tgt_label = f"{_label(tgt_id, lang)} ({year_b})"
            node_class.setdefault(src_label, int(src_id))
            node_class.setdefault(tgt_label, int(tgt_id))
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
    node_colors = [_color(node_class.get(n, -1)) for n in sorted_nodes]

    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=20, thickness=20, line=dict(color="black", width=0.5),
                  label=node_labels, color=node_colors),
        link=dict(
            source=[node_idx[s] for s in sources],
            target=[node_idx[t] for t in targets],
            value=values,
            color=link_colors,
            label=[f"{s} → {t} ({v:,.1f} ha)"
                   for s, t, v in zip(sources, targets, values)],
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


def default_year_pair() -> Tuple[int, int]:
    """The pair the Transições tab opens on: the first nationally-covered year
    and the last.

    The Brazil page frames its default around the property's own CAR
    registration date. ``PARCEL_START_DATE`` is null for most BC parcels (see
    ``pmbc.Parcel.start_year``), so there is no cadastral event to frame on for
    the majority of parcels — the full available span is the honest default
    instead of one that works for a minority.
    """
    return aafc.ACI_NATIONAL_FROM, aafc.ACI_YEAR_END


__all__ = [
    "TransitionsByZone", "YearGapError", "MIN_YEAR_GAP",
    "compute_transitions", "sankey_figure", "default_year_pair",
]
