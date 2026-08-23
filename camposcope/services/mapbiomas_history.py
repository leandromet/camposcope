"""MapBiomas land-cover history for a property's zones (doc/06-ee-layers.md §2).

This is the performance-critical path. MapBiomas Collection 10.1 ships all 40
years as 40 **bands of one image**, so the whole "40 years × N zones" matrix is
a *single* ``reduceRegions`` call — not to ration Earth Engine calls (the
Partner tier makes that unnecessary) but because one round trip beats forty.

**Zones, not buffers.** Naturametrics reduces over concentric discs around a
point; Camposcope reduces over the property polygon and its outward rings
(``services.zones.Zone``, decision D3). The reducer and the parsing are
otherwise the same pattern, ported and reshaped.

**Area accounting (decision D3, carried from Naturametrics).** Pixel counts
alone would need a flat area-per-pixel assumption, which drifts with latitude.
Instead a second, concurrent call measures the *mean true pixel area* inside
each zone with ``ee.Image.pixelArea()``, and areas are
``count × mean_pixel_area``. Within a single zone the pixel area varies by far
less than the classification error, so this is exact for practical purposes and
costs one extra cheap round trip issued in parallel.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Sequence, Tuple

import pandas as pd

from ..config import mapbiomas as mb
from ..config.settings import EE_DEFAULT_SCALE_M, EE_MAX_PIXELS, EE_TILE_SCALE
from .ee_client import get_ee
from .provenance import Provenance
from .zones import Zone

logger = logging.getLogger(__name__)

MAPBIOMAS_ASSET = mb.MAPBIOMAS_COLLECTIONS[mb.MAPBIOMAS_DEFAULT_COLLECTION]


def _zone_feature_collection(zones: Sequence[Zone]):
    """Zones as an ``ee.FeatureCollection``, one feature per zone.

    Geometries travel to Earth Engine inline, as GeoJSON already computed
    locally by ``services.zones`` — never as an uploaded asset (doc/06 §6):
    a cadastral boundary fetched at request time and uploaded as an asset
    would immediately be a stale copy of official data.
    """
    import ee

    return ee.FeatureCollection([
        ee.Feature(ee.Geometry(z.geojson), {
            "zone_key": z.key,
            "zone_label": z.label,
            "zone_kind": z.kind,
        })
        for z in zones
    ])


def _histogram_call(fc, asset: str, bands: List[str], scale: int, tile_scale: int):
    import ee
    return (
        ee.Image(asset)
        .select(bands)
        .reduceRegions(
            collection=fc,
            reducer=ee.Reducer.frequencyHistogram(),
            scale=scale,
            tileScale=tile_scale,
        )
        .getInfo()
    )


def _pixel_area_call(fc, scale: int, tile_scale: int):
    """Mean true pixel area (m²) inside each zone — the D3 area basis."""
    import ee
    return (
        ee.Image.pixelArea()
        .reduceRegions(
            collection=fc,
            reducer=ee.Reducer.mean(),
            scale=scale,
            tileScale=tile_scale,
        )
        .getInfo()
    )


def land_cover_history(
    zones: Sequence[Zone],
    *,
    years: List[int] | None = None,
    collection: str = mb.MAPBIOMAS_DEFAULT_COLLECTION,
) -> Tuple[pd.DataFrame, Provenance]:
    """Land-cover area by year, class and zone.

    Returns a long-format frame — ``zone_key, zone_label, year, class_id,
    pixels, area_ha`` — plus the provenance record that must travel with it
    (constraint C3). Long format rather than wide-by-year: 40 years × ~15
    classes × N zones is a natural long table, and wide-by-year breaks the
    moment the year range changes.
    """
    if not zones:
        raise ValueError("Nenhuma zona para analisar.")

    get_ee()

    years = years or mb.MAPBIOMAS_YEARS
    bands = [mb.band_for_year(y) for y in years]
    asset = mb.MAPBIOMAS_COLLECTIONS[collection]
    fc = _zone_feature_collection(zones)

    prov = Provenance(
        name="mapbiomas_history",
        dataset_id=asset,
        bands=bands,
        scale_m=EE_DEFAULT_SCALE_M,
        reducer="frequencyHistogram",
        pixel_area_basis="mean ee.Image.pixelArea() per zone",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,        # the property; rings are in extra
        extra={
            "collection": collection,
            "zones": [z.key for z in zones],
            "year_start": years[0],
            "year_end": years[-1],
        },
    )

    scale, tile_scale = EE_DEFAULT_SCALE_M, EE_TILE_SCALE
    hist = areas = None

    # Retry ladder (doc/06 §7). Never coarsen without recording it via
    # prov.degrade — a degraded result is usable and exportable, but it must
    # say so.
    for attempt, (s, ts) in enumerate([(scale, tile_scale), (scale, 8), (60, 8)]):
        try:
            # Both calls are independent, so issue them together: the pair
            # costs one round trip of wall-clock, not two.
            with ThreadPoolExecutor(max_workers=2) as ex:
                f_hist = ex.submit(_histogram_call, fc, asset, bands, s, ts)
                f_area = ex.submit(_pixel_area_call, fc, s, ts)
                hist, areas = f_hist.result(), f_area.result()
            if attempt > 0:
                prov.degrade(
                    f"Repetido em scale={s} m, tileScale={ts} após falha em "
                    f"scale={scale} m, tileScale={tile_scale}.",
                    scale_m=s, tile_scale=ts,
                )
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning("history attempt %s (scale=%s, tileScale=%s) failed: %s",
                           attempt + 1, s, ts, exc)
            if attempt == 2:
                raise

    px_area: Dict[str, float] = {
        f["properties"]["zone_key"]: float(f["properties"].get("mean") or 900.0)
        for f in areas["features"]
    }
    zone_labels = {z.key: z.label for z in zones}

    records: List[Dict[str, Any]] = []
    for feat in hist["features"]:
        props = feat["properties"]
        zone_key = props["zone_key"]
        area_per_px_ha = px_area.get(zone_key, 900.0) / 10_000.0

        # Earth Engine names the reduceRegions output per BAND when several
        # bands are selected, but falls back to the reducer's own name
        # ("histogram") when there is exactly one — a parser that only looks
        # for "classification_*" silently returns nothing for a single-year
        # query.
        single_band = len(bands) == 1
        for key, histogram in props.items():
            if not isinstance(histogram, dict):
                continue
            if key.startswith("classification_"):
                year = int(key.rsplit("_", 1)[1])
            elif single_band and key == "histogram":
                year = years[0]
            else:
                continue
            for class_id, count in histogram.items():
                count = float(count)
                if count <= 0:
                    continue
                records.append({
                    "zone_key": zone_key,
                    "zone_label": zone_labels.get(zone_key, zone_key),
                    "year": year,
                    "class_id": int(float(class_id)),
                    "pixels": count,
                    "area_ha": count * area_per_px_ha,
                })

    df = pd.DataFrame.from_records(
        records,
        columns=["zone_key", "zone_label", "year", "class_id", "pixels", "area_ha"],
    )
    if not df.empty:
        df["class_pt"] = df["class_id"].map(lambda c: mb.label(c, "pt"))
        df["class_en"] = df["class_id"].map(lambda c: mb.label(c, "en"))
        df["color"] = df["class_id"].map(mb.color)
        # Zones in the order they were passed (property first, rings outward),
        # not alphabetically — the order the UI reasons about them in.
        order = {z.key: i for i, z in enumerate(zones)}
        df["_zone_order"] = df["zone_key"].map(order)
        df = df.sort_values(
            ["_zone_order", "year", "area_ha"], ascending=[True, True, False]
        ).drop(columns="_zone_order").reset_index(drop=True)

    prov.extra["mean_pixel_area_m2"] = {k: round(v, 2) for k, v in px_area.items()}
    prov.extra["n_records"] = len(df)
    logger.info("MapBiomas history: %s records across %s zones", len(df), len(zones))
    return df, prov


def to_shares(df: pd.DataFrame, zone_key: str) -> pd.DataFrame:
    """Per-year percentage shares for one zone — what the stacked chart plots."""
    if df is None or df.empty or "zone_key" not in df.columns:
        return pd.DataFrame()
    sub = df[df["zone_key"] == zone_key].copy()
    if sub.empty:
        return sub
    totals = sub.groupby("year")["area_ha"].transform("sum")
    sub["area_pct"] = (sub["area_ha"] / totals * 100.0).fillna(0.0)
    return sub


def year_totals(df: pd.DataFrame, zone_key: str) -> pd.Series:
    """Total classified area per year for one zone — the reconciliation check
    the Sankey work in doc/07 §6 compares against."""
    if df is None or df.empty:
        return pd.Series(dtype=float)
    sub = df[df["zone_key"] == zone_key]
    return sub.groupby("year")["area_ha"].sum()


__all__ = ["land_cover_history", "to_shares", "year_totals", "MAPBIOMAS_ASSET"]
