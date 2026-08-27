"""Landscape (fragmentation) metrics from one MapBiomas classification year,
one row per zone.

Ported from Naturametrics' ``services/landscape_metrics.py`` with the same
reshaping ``services/mapbiomas_history.py`` and ``services/biomass.py``
already did: buffers become zones (property + rings, ``services/zones.py``,
decision D3), and the whole "N zones" matrix is one ``reduceRegions`` round
trip per statistic, over the same ``_zone_feature_collection`` every sibling
service reduces over.

``meff_ha`` (effective mesh size, Jaeger 2000) is always computed — it falls
out of the same connected-components image already built for
``largest_patch_ha``, at the cost of one extra ``reduceRegions`` call. The
pricier true nearest-neighbour distance between fragments lives in
``services.connectivity`` instead, behind its own button, for the same
reason it does upstream: it needs a second Earth Engine round trip
(vectorising) plus a local geometry search, not one more cheap reduction.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Sequence, Tuple

import pandas as pd

from ..config import mapbiomas as mb
from ..config.settings import EE_DEFAULT_SCALE_M, EE_MAX_PIXELS, EE_TILE_SCALE
from .ee_client import get_ee
from .mapbiomas_history import _zone_feature_collection
from .provenance import Provenance
from .zones import Zone

logger = logging.getLogger(__name__)

#: One row per zone. Same column set as Naturametrics' ``METRIC_COLUMNS``,
#: with ``radius_km`` replaced by ``zone_key``/``zone_label`` — see that
#: module's docstring for what each column means; the formulas are identical.
METRIC_COLUMNS = [
    "zone_key", "zone_label", "area_ha", "patches", "patch_density",
    "largest_patch_ha", "largest_patch_pct", "edge_m", "edge_density",
    "mean_patch_ha", "patch_area_sq_ha", "meff_ha", "shannon", "simpson",
    "simpson_evenness",
]

#: The per-class histogram behind the summary above — long format, one row
#: per zone × class, the same shape ``mapbiomas_history.land_cover_history``
#: uses for one year instead of forty.
HISTOGRAM_COLUMNS = ["zone_key", "zone_label", "class_id", "pixels", "area_ha"]


def _diversity(hist_df: pd.DataFrame, zone_key: str) -> Dict[str, float]:
    """Shannon / Gini-Simpson / Simpson's evenness for one zone's class-area
    histogram — the same formula Naturametrics applies per buffer."""
    sub = hist_df[hist_df["zone_key"] == zone_key] if not hist_df.empty else hist_df
    total = float(sub["area_ha"].sum()) if not sub.empty else 0.0
    if total <= 0:
        return {"shannon": 0.0, "simpson": 0.0, "simpson_evenness": 0.0}
    proportions = (sub["area_ha"] / total).to_numpy()
    shannon = -sum(p * math.log(p) for p in proportions if p > 0)
    simpson = 1.0 - float(sum(p * p for p in proportions))
    richness = int((proportions > 0).sum())
    evenness = simpson / (1.0 - 1.0 / richness) if richness > 1 else 0.0
    return {"shannon": shannon, "simpson": simpson, "simpson_evenness": evenness}


def _summary_from_properties(
    props: Dict[str, Any], zone_key: str, zone_label: str,
    pixel_area_m2: float, pixel_scale_m: float,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """One zone's summary row, plus its class histogram as long-format
    records — identical arithmetic to Naturametrics'
    ``_summary_from_properties``, keyed by zone instead of radius."""
    histogram = props.get("histogram") or {}
    counts = {int(float(k)): float(v) for k, v in histogram.items() if float(v) > 0}
    pixels = sum(counts.values())
    area_ha = pixels * pixel_area_m2 / 10_000.0
    patches = float(props.get("patches") or 0)
    largest_pixels = float(props.get("largest_patch") or 0)
    edge_fraction = float(props.get("edge_fraction") or 0)
    largest_ha = largest_pixels * pixel_area_m2 / 10_000.0
    edge_m = edge_fraction * pixels * pixel_scale_m
    patch_size_sum = float(props.get("patch_size_sum") or 0)
    patch_area_sq_ha = patch_size_sum * (pixel_area_m2 ** 2) / 1e8
    summary = {
        "zone_key": zone_key,
        "zone_label": zone_label,
        "area_ha": area_ha,
        "patches": patches,
        "patch_density": patches / max(area_ha, 1e-9),
        "largest_patch_ha": largest_ha,
        "largest_patch_pct": largest_ha / max(area_ha, 1e-9) * 100.0,
        "edge_m": edge_m,
        "edge_density": edge_m / max(area_ha, 1e-9),
        "mean_patch_ha": area_ha / max(patches, 1.0),
        "patch_area_sq_ha": patch_area_sq_ha,
        "meff_ha": patch_area_sq_ha / max(area_ha, 1e-9),
    }
    hist_records = [
        {"zone_key": zone_key, "zone_label": zone_label, "class_id": class_id,
         "pixels": count, "area_ha": count * pixel_area_m2 / 10_000.0}
        for class_id, count in counts.items()
    ]
    return summary, hist_records


def landscape_metrics(
    zones: Sequence[Zone],
    year: int = mb.MAPBIOMAS_YEAR_END,
) -> Tuple[pd.DataFrame, pd.DataFrame, Provenance]:
    """Patch/edge/diversity metrics for one classification year, one row per
    zone (the property, then its rings).

    Patches are contiguous 8-neighbour regions of equal MapBiomas class,
    found with the same ``connectedComponents`` construction Naturametrics
    uses; NP/LPI/Meff read off it, ED off a native-raster neighbourhood
    comparison. Diversity (Shannon/Simpson/evenness) is computed locally from
    the returned class histogram by :func:`_diversity`.
    """
    if not zones:
        raise ValueError("Nenhuma zona para analisar.")

    get_ee()
    import ee

    asset = mb.MAPBIOMAS_COLLECTIONS[mb.MAPBIOMAS_DEFAULT_COLLECTION]
    image = ee.Image(asset).select(mb.band_for_year(year)).rename("class")
    kernel = ee.Kernel.square(1)
    labels = image.connectedComponents(kernel, 1024).select("labels")
    component_size = image.connectedPixelCount(1024, True).rename("patch_size")
    neighbours = image.neighborhoodToBands(ee.Kernel.plus(1))
    edge = neighbours.neq(image).reduce(ee.Reducer.sum()).gt(0).rename("edge")

    fc = _zone_feature_collection(zones)
    scale, tile_scale = EE_DEFAULT_SCALE_M, EE_TILE_SCALE

    reduced = image.reduceRegions(collection=fc, reducer=ee.Reducer.frequencyHistogram(),
                                  scale=scale, tileScale=tile_scale)
    patch_reduced = labels.reduceRegions(collection=fc, reducer=ee.Reducer.countDistinct(),
                                        scale=scale, tileScale=tile_scale)
    largest_reduced = component_size.reduceRegions(collection=fc, reducer=ee.Reducer.max(),
                                                   scale=scale, tileScale=tile_scale)
    mesh_reduced = component_size.reduceRegions(collection=fc, reducer=ee.Reducer.sum(),
                                                scale=scale, tileScale=tile_scale)
    edge_reduced = edge.reduceRegions(collection=fc, reducer=ee.Reducer.mean(),
                                      scale=scale, tileScale=tile_scale)
    area_reduced = ee.Image.pixelArea().reduceRegions(
        collection=fc, reducer=ee.Reducer.mean(), scale=scale, tileScale=tile_scale)

    hist_info = reduced.getInfo()
    patch_info = patch_reduced.getInfo()
    largest_info = largest_reduced.getInfo()
    mesh_info = mesh_reduced.getInfo()
    edge_info = edge_reduced.getInfo()
    area_info = area_reduced.getInfo()

    zone_labels = {z.key: z.label for z in zones}
    patch_by_key = {f["properties"]["zone_key"]: f["properties"]
                    for f in patch_info.get("features", [])}
    largest_by_key = {f["properties"]["zone_key"]: f["properties"]
                      for f in largest_info.get("features", [])}
    mesh_by_key = {f["properties"]["zone_key"]: f["properties"]
                  for f in mesh_info.get("features", [])}
    edge_by_key = {f["properties"]["zone_key"]: f["properties"]
                  for f in edge_info.get("features", [])}
    area_by_key = {f["properties"]["zone_key"]: f["properties"]
                  for f in area_info.get("features", [])}

    summaries: List[Dict[str, Any]] = []
    hist_records: List[Dict[str, Any]] = []
    for feature in hist_info.get("features", []):
        props = feature.get("properties", {})
        zone_key = props["zone_key"]
        zone_label = zone_labels.get(zone_key, zone_key)
        patch_props = patch_by_key.get(zone_key, {})
        largest_props = largest_by_key.get(zone_key, {})
        mesh_props = mesh_by_key.get(zone_key, {})
        edge_props = edge_by_key.get(zone_key, {})
        area_props = area_by_key.get(zone_key, {})
        summary, records = _summary_from_properties(
            {"histogram": props.get("histogram"),
             "patches": patch_props.get("countDistinct", patch_props.get("count")),
             "largest_patch": largest_props.get("max"),
             "patch_size_sum": mesh_props.get("sum"),
             "edge_fraction": edge_props.get("mean")},
            zone_key, zone_label, float(area_props.get("mean") or 900.0),
            EE_DEFAULT_SCALE_M,
        )
        summaries.append(summary)
        hist_records.extend(records)

    summary_cols = [c for c in METRIC_COLUMNS if c not in ("shannon", "simpson", "simpson_evenness")]
    summary_df = pd.DataFrame.from_records(summaries, columns=summary_cols)
    hist_df = pd.DataFrame.from_records(hist_records, columns=HISTOGRAM_COLUMNS)

    if not summary_df.empty:
        diversity = [_diversity(hist_df, k) for k in summary_df["zone_key"]]
        summary_df["shannon"] = [d["shannon"] for d in diversity]
        summary_df["simpson"] = [d["simpson"] for d in diversity]
        summary_df["simpson_evenness"] = [d["simpson_evenness"] for d in diversity]
    else:
        for col in ("shannon", "simpson", "simpson_evenness"):
            summary_df[col] = pd.Series(dtype="float64")
    summary_df = summary_df[METRIC_COLUMNS]

    order = {z.key: i for i, z in enumerate(zones)}
    summary_df["_zone_order"] = summary_df["zone_key"].map(order)
    summary_df = summary_df.sort_values("_zone_order").drop(columns="_zone_order")
    summary_df = summary_df.reset_index(drop=True)

    prov = Provenance(
        name="landscape_metrics",
        dataset_id=asset,
        bands=[mb.band_for_year(year)],
        scale_m=EE_DEFAULT_SCALE_M,
        reducer="frequencyHistogram + connectedComponents + neighbourhood edge",
        pixel_area_basis="mean ee.Image.pixelArea() per zone",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={
            "year": year, "zones": [z.key for z in zones],
            "connectivity": "8-neighbour", "edge_basis": "native raster pixels",
            # connectedComponents/connectedPixelCount mask/cap at this many
            # pixels (~92 ha) — a patch bigger than that reads as truncated,
            # common for large intact-forest zones. Kept in provenance rather
            # than silently accepted, per constraint C6.
            "patch_size_cap_pixels": 1024,
        },
    )
    logger.info("Landscape metrics: %s zones, %s classes", len(summary_df), len(hist_df))
    return summary_df, hist_df, prov


__all__ = ["landscape_metrics", "METRIC_COLUMNS", "HISTOGRAM_COLUMNS"]
