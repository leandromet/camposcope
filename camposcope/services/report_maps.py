"""The report's maps — doc/13 §6.

Two extents, both framed by ``report_kit.maps.MapView``:

* **detail** — the property plus its first (500 m) ring, where 10 m
  Sentinel-2 and 5 m SPOT are legible;
* **context** — the property plus its outermost ring, for MapBiomas and
  Hansen.

Every raster comes from the *same* image builder the on-screen tile layer uses
(``services/layers.py``: ``mapbiomas_year_image``, ``hansen_treecover_image``
/ ``hansen_change_image``, ``spot_image``), except the Sentinel-2 backdrop,
which is the kit's own ``imagery_backdrop``. Outlines are never painted in
Earth Engine: they travel as kit ``VectorLayer``s from ``zones_geojson``
(property solid, rings dashed), so no geometry is sent to Earth Engine and the
thumbnail cache works per bounding box.

**Blocking and networked**: call :func:`fetch_report_maps` from an executor,
never on the event loop. It initialises Earth Engine through the app's own
``get_ee()`` first (the kit requires the caller to). Each map fails on its
own — one EE error costs that map, not the report.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..config import datasets as ds
from ..config import mapbiomas as mb
from ..report_kit import LegendItem, MapComposition, MapFigure, VectorLayer
from ..report_kit.maps import MapView, fetch_thumbnail, imagery_backdrop
from . import report_text as rt

logger = logging.getLogger(__name__)

#: Hansen map: loss since the Forest Code's reference year, the Floresta tab's
#: default layer mode (``ForestChangeMixin.hansen_layer_mode == "2008"``).
HANSEN_MAP_FROM_YEAR = 2008

# Outline styles: yellow/white read on imagery, black/grey on class rasters.
_IMAGERY_STROKES = ("#ffd400", "#ffffff")
_CLASS_STROKES = ("#111111", "#444444")


def _features(zones_geojson: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list((zones_geojson or {}).get("features") or [])


def _split(zones_geojson: Dict[str, Any]) -> Tuple[Optional[dict], List[dict]]:
    prop, rings = None, []
    for f in _features(zones_geojson):
        if (f.get("properties") or {}).get("role") == "property":
            prop = f
        else:
            rings.append(f)
    return prop, rings


def _vectors(prop: Optional[dict], rings: List[dict], strokes: Tuple[str, str],
             lang: str, square: bool) -> Tuple[List[VectorLayer], List[LegendItem]]:
    vectors: List[VectorLayer] = []
    for ring in rings:
        vectors.append(VectorLayer(ring["geometry"], stroke=strokes[1], width_pt=0.8,
                                   dash=(3, 2)))
    if prop is not None:
        vectors.append(VectorLayer(prop["geometry"], stroke=strokes[0], width_pt=1.5))
    legend = [LegendItem(strokes[0] if strokes[0] != "#ffffff" else "#111111",
                         rt.t("legend_property_square" if square else "legend_property", lang),
                         "line")]
    if rings:
        legend.append(LegendItem(strokes[1] if strokes[1] != "#ffffff" else "#777777",
                                 rt.t("legend_rings", lang), "line"))
    return vectors, legend


def _mapbiomas_legend(history_rows: List[Dict[str, Any]], year: int, lang: str,
                      limit: int = 10) -> List[LegendItem]:
    """Classes present in ``year`` across every zone, largest first — read
    from the Cobertura rows already on screen, never a new EE query."""
    totals: Dict[int, Tuple[float, Dict[str, Any]]] = {}
    for r in history_rows or []:
        if int(r.get("year", 0)) != year:
            continue
        cid = int(r["class_id"])
        area, row = totals.get(cid, (0.0, r))
        totals[cid] = (area + float(r["area_ha"]), row)
    ordered = sorted(totals.items(), key=lambda kv: -kv[1][0])[:limit]
    return [LegendItem(str(row.get("color") or mb.color(cid)), rt.class_name(row, lang))
            for cid, (_, row) in ordered]


def plan_maps(zones_geojson: Dict[str, Any], spot_summary: Dict[str, Any]) -> List[str]:
    """Which maps a report for this property would carry, in order."""
    prop, _ = _split(zones_geojson)
    if prop is None:
        return []
    keys = ["s2", "mapbiomas", "hansen"]
    if (spot_summary or {}).get("has_coverage") and ds.EE_BASEMAPS.get("spot_2008_visual"):
        keys.insert(1, "spot")
    return keys


def fetch_report_maps(*, imovel: Dict[str, Any], zones: List[Dict[str, Any]],
                      zones_geojson: Dict[str, Any], spot_summary: Dict[str, Any],
                      history_rows: List[Dict[str, Any]], lang: str = "pt",
                      s2_year: Optional[int] = None,
                      ) -> Tuple[List[MapFigure], Dict[str, str], List[str]]:
    """``(map figures in order, {key: error}, extra attributions)``.

    Blocking — run in an executor.
    """
    from . import layers
    from .ee_client import get_ee

    keys = plan_maps(zones_geojson, spot_summary)
    if not keys:
        return [], {}, []
    get_ee()

    square = (imovel or {}).get("kind") == "square"
    prop, rings = _split(zones_geojson)
    detail_geoms = [prop["geometry"]] + [r["geometry"] for r in rings[:1]]
    context_geoms = [prop["geometry"]] + [r["geometry"] for r in rings[-1:]]
    detail = MapView.from_geojson(detail_geoms, "full")
    context = MapView.from_geojson(context_geoms, "full")
    outer_radius = rt.radius_label(next((z.get("radius_m") for z in reversed(zones)
                                         if z.get("zone_kind") == "ring"), None), lang)
    year_s2 = s2_year or (datetime.now(timezone.utc).year - 1)
    year_mb = mb.MAPBIOMAS_YEAR_END
    hansen_end = ds.HANSEN_GFC["loss_year_end"]

    def build(key: str) -> Tuple[MapFigure, str]:
        if key == "s2":
            picked = imagery_backdrop(detail, year_s2)
            if picked is None:
                raise RuntimeError("no imagery for this extent")
            image, attribution = picked
            data = fetch_thumbnail(image, detail, "jpg", cache_key=f"s2:{year_s2}")
            vec, legend = _vectors(prop, rings[:1], _IMAGERY_STROKES, lang, square)
            comp = MapComposition(view=detail, backdrop=data, vectors=vec,
                                  legend=legend, attribution=attribution)
            return MapFigure(comp, rt.t("cap_map_s2", lang, year=year_s2)), attribution
        if key == "spot":
            data = fetch_thumbnail(layers.spot_image("spot_2008_visual", visualize=True),
                                   detail, "jpg", cache_key="spot_2008_visual")
            vec, legend = _vectors(prop, rings[:1], _IMAGERY_STROKES, lang, square)
            attribution = ds.EE_BASEMAPS["spot_2008_visual"]["attribution"]
            comp = MapComposition(view=detail, backdrop=data, vectors=vec,
                                  legend=legend, attribution=attribution)
            return MapFigure(comp, rt.spot_map_caption(spot_summary, lang)), ""
        if key == "mapbiomas":
            data = fetch_thumbnail(layers.mapbiomas_year_image(year_mb, visualize=True),
                                   context, "png", cache_key=f"mapbiomas:{year_mb}")
            vec, legend = _vectors(prop, rings, _CLASS_STROKES, lang, square)
            comp = MapComposition(view=context, overlays=[data], vectors=vec,
                                  legend=_mapbiomas_legend(history_rows, year_mb, lang)
                                  + legend,
                                  attribution=f"MapBiomas Coleção 10.1 · {year_mb}")
            return MapFigure(comp, rt.t("cap_map_mapbiomas", lang, year=year_mb,
                                        radius=outer_radius)), ""
        if key == "hansen":
            image = layers.hansen_treecover_image(visualize=True).blend(
                layers.hansen_change_image(HANSEN_MAP_FROM_YEAR, visualize=True))
            data = fetch_thumbnail(image, context, "png",
                                   cache_key=f"hansen_map:{HANSEN_MAP_FROM_YEAR}")
            vec, legend = _vectors(prop, rings, _CLASS_STROKES, lang, square)
            legend = [LegendItem("#238443", rt.t("legend_treecover", lang)),
                      LegendItem(ds.HANSEN_GFC["loss_color"],
                                 rt.t("legend_loss", lang, from_year=HANSEN_MAP_FROM_YEAR,
                                      end=hansen_end)),
                      LegendItem(ds.HANSEN_GFC["gain_color"], rt.t("legend_gain", lang)),
                      ] + legend
            comp = MapComposition(view=context, overlays=[data], vectors=vec,
                                  legend=legend,
                                  attribution=ds.HANSEN_GFC["attribution"])
            return MapFigure(comp, rt.t("cap_map_hansen", lang,
                                        from_year=HANSEN_MAP_FROM_YEAR, end=hansen_end,
                                        radius=outer_radius)), ""
        raise KeyError(key)

    results: Dict[str, Tuple[MapFigure, str]] = {}
    errors: Dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(4, len(keys))) as pool:
        futures = {key: pool.submit(build, key) for key in keys}
        for key, fut in futures.items():
            try:
                results[key] = fut.result(timeout=120)
            except Exception as exc:                   # noqa: BLE001
                logger.warning("report map %s failed: %s", key, exc)
                errors[key] = str(exc)[:200]
    figures = [results[k][0] for k in keys if k in results]
    attributions = [results[k][1] for k in keys if k in results and results[k][1]]
    return figures, errors, attributions


__all__ = ["fetch_report_maps", "plan_maps", "HANSEN_MAP_FROM_YEAR"]
