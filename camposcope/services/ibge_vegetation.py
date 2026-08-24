"""IBGE Vegetação (2022, 1:250.000) as a QC comparison against MapBiomas 2022
— the ground-truth check doc/03-roadmap.md's Phase 5 addendum asks for
(ported in spirit from Naturametrics' ``services/ibge_vegetation.py``,
reshaped from buffers-around-a-point to Camposcope's zones).

**Vector, rasterized once, not a polygon-intersection.** The source asset
(``config.ibge_vegetation.IBGE_VEG_ASSET``) is a 145 458-feature
``FeatureCollection``, not an image. Intersecting that many polygons against
every zone would be the vector equivalent of the mistake this app's tile
layers never make: ``fc.reduceToImage([field], ee.Reducer.first())`` turns it
into a single-band classified image once, after which every zone read is the
same ``reduceRegions(frequencyHistogram)`` + true ``pixelArea`` pattern
already used for MapBiomas (``services.mapbiomas_history``) and Hansen
(``services.hansen``).

**The comparison is a joint histogram, not two side-by-side ones.** IBGE's
``leg2_id`` (1–54) and MapBiomas' class code share no numeric range, so they
are combined into one band via ``ibge.multiply(1000).add(mapbiomas)`` — the
same encode-two-classes-as-one-int trick ``services/transitions.py`` uses for
year-to-year transitions — and read with a single ``frequencyHistogram``.

**Both datasets are reduced to the same six buckets** (natural/anthropic ×
forest/non-forest, plus water and other — ``config.ibge_vegetation``) before
the comparison is shown. The two legends share no classes, so a raw
54 × ~30 matrix would answer nothing a person could read; the bucketed matrix
is the thing the tab actually displays, and the raw ``leg2_id``/``mb_class``
pairs stay in the returned frame for anyone who wants to drill down.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Sequence, Tuple

import pandas as pd

from ..config import ibge_vegetation as iv
from ..config import mapbiomas as mb
from ..config.settings import EE_MAX_PIXELS, EE_TILE_SCALE
from .ee_client import get_ee
from .mapbiomas_history import _zone_feature_collection
from .provenance import Provenance
from .zones import Zone

logger = logging.getLogger(__name__)

COMPARISON_COLUMNS = [
    "zone_key", "leg2_id", "ibge_group", "mb_class", "mb_group",
    "pixels", "area_ha",
]


def classified_image():
    """The IBGE vegetation FeatureCollection rasterized to one band, ``leg2``.

    Lazy — costs nothing until something reduces it, same as every other
    Earth Engine graph in this app.
    """
    import ee
    return (
        ee.FeatureCollection(iv.IBGE_VEG_ASSET)
        .reduceToImage([iv.IBGE_VEG_CLASS_FIELD], ee.Reducer.first())
        .rename("leg2")
    )


def mapbiomas_comparison(
    zones: Sequence[Zone], *, mb_year: int = iv.IBGE_COMPARE_YEAR,
) -> Tuple[pd.DataFrame, Provenance]:
    """Joint IBGE-vegetation × MapBiomas area histogram, one call for every
    zone (the same batched-``reduceRegions`` pattern as everything else in
    this app)."""
    if not zones:
        raise ValueError("Nenhuma zona para analisar.")

    get_ee()
    import ee

    asset = mb.MAPBIOMAS_COLLECTIONS[mb.MAPBIOMAS_DEFAULT_COLLECTION]
    mb_image = ee.Image(asset).select(mb.band_for_year(mb_year)).rename("mb")
    ibge_image = classified_image()
    # leg2_id is 1-54 and MapBiomas class codes never reach 1000, so this
    # encoding is exact and splits back with plain arithmetic.
    combined = ibge_image.multiply(1000).add(mb_image).rename("combined").toInt()
    fc = _zone_feature_collection(zones)

    prov = Provenance(
        name="ibge_mapbiomas_comparison",
        dataset_id=f"{iv.IBGE_VEG_ASSET} × {asset}",
        bands=["leg2", f"mapbiomas_{mb_year}"],
        scale_m=30,
        reducer="frequencyHistogram (leg2*1000 + mapbiomas class)",
        pixel_area_basis="mean ee.Image.pixelArea() per zone",
        max_pixels=EE_MAX_PIXELS,
        tile_scale=EE_TILE_SCALE,
        geometry=zones[0].geojson,
        extra={
            "zones": [z.key for z in zones], "mapbiomas_year": mb_year,
            "attribution": iv.IBGE_VEG_ATTRIBUTION,
            "caveat": (
                "Ambos os conjuntos são simplificados para uma taxonomia "
                "compartilhada de 6 grupos (natural/antrópico x floresta) "
                "apenas para esta comparação — não é a classificação de "
                "origem de nenhum dos dois. 'Vegetação Secundária' do IBGE "
                "não tem equivalente direto no MapBiomas por definição; a "
                "matriz mostra o que o MapBiomas lê hoje nesses polígonos."
            ),
        },
    )

    from concurrent.futures import ThreadPoolExecutor

    def hist_call():
        return combined.reduceRegions(
            collection=fc, reducer=ee.Reducer.frequencyHistogram(),
            scale=30, tileScale=EE_TILE_SCALE,
        ).getInfo()

    def area_call():
        return ee.Image.pixelArea().reduceRegions(
            collection=fc, reducer=ee.Reducer.mean(),
            scale=30, tileScale=EE_TILE_SCALE,
        ).getInfo()

    with ThreadPoolExecutor(max_workers=2) as ex:
        f_hist, f_area = ex.submit(hist_call), ex.submit(area_call)
        hist, areas = f_hist.result(), f_area.result()

    px_area = {
        f["properties"]["zone_key"]: float(f["properties"].get("mean") or 900.0)
        for f in areas["features"]
    }

    records = []
    for feat in hist["features"]:
        props = feat["properties"]
        zone_key = props["zone_key"]
        area_per_px_ha = px_area.get(zone_key, 900.0) / 10_000.0
        # `histogram` (single band selected implicitly here — `combined`),
        # same reducer-name fallback documented in mapbiomas_history.py.
        histogram: Dict[str, float] = props.get("histogram") or {}
        for key, count in histogram.items():
            count = float(count)
            if count <= 0:
                continue
            combined_id = int(float(key))
            leg2_id, mb_class = divmod(combined_id, 1000)
            records.append({
                "zone_key": zone_key,
                "leg2_id": leg2_id,
                "ibge_group": iv.ibge_group(leg2_id),
                "mb_class": mb_class,
                "mb_group": iv.mapbiomas_group(mb_class),
                "pixels": count,
                "area_ha": count * area_per_px_ha,
            })

    df = pd.DataFrame.from_records(records, columns=COMPARISON_COLUMNS)
    prov.extra["mean_pixel_area_m2"] = {k: round(v, 2) for k, v in px_area.items()}
    prov.extra["n_records"] = len(df)
    return df, prov


def bucket_matrix(df: pd.DataFrame, zone_key: str) -> Dict[str, Any]:
    """Pivot one zone's joint histogram to a 6×6 (ibge_group × mb_group) %
    matrix, plus the two headline numbers the tab leads with: how much of the
    zone each dataset calls forest, and how much each calls natural.

    A plain dict, not a DataFrame — this is exactly what Reflex state needs.
    """
    empty = {
        "groups": iv.GROUP_ORDER, "group_labels": iv.GROUP_LABELS_PT,
        "matrix": {}, "forest_ibge": 0.0, "forest_mb": 0.0,
        "natural_ibge": 0.0, "natural_mb": 0.0,
    }
    if df is None or df.empty or "zone_key" not in df.columns:
        return empty
    sub = df[df["zone_key"] == zone_key]
    if sub.empty:
        return empty

    total = float(sub["area_ha"].sum())
    matrix: Dict[str, Dict[str, float]] = {
        g: {g2: 0.0 for g2 in iv.GROUP_ORDER} for g in iv.GROUP_ORDER
    }
    for _, row in sub.iterrows():
        pct = float(row["area_ha"]) / total * 100.0 if total else 0.0
        matrix[row["ibge_group"]][row["mb_group"]] += pct

    forest_groups = {iv.GROUP_NATURAL_FOREST, iv.GROUP_ANTHROPIC_FOREST}
    natural_groups = {iv.GROUP_NATURAL_FOREST, iv.GROUP_NATURAL_NON_FOREST}

    def marginal(axis: str, groups: set) -> float:
        col = sub.groupby(axis)["area_ha"].sum()
        return float(col[col.index.isin(groups)].sum() / total * 100.0) if total else 0.0

    return {
        "groups": iv.GROUP_ORDER,
        "group_labels": iv.GROUP_LABELS_PT,
        "matrix": matrix,
        "forest_ibge": round(marginal("ibge_group", forest_groups), 1),
        "forest_mb": round(marginal("mb_group", forest_groups), 1),
        "natural_ibge": round(marginal("ibge_group", natural_groups), 1),
        "natural_mb": round(marginal("mb_group", natural_groups), 1),
    }


__all__ = ["classified_image", "mapbiomas_comparison", "bucket_matrix"]
