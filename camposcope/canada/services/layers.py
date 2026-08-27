"""Tile-URL specs for the Canada map.

Same contract as :mod:`camposcope.services.layers` — a layer spec is the plain
dict the Leaflet hook diffs on — and the plain-XYZ basemap builder is imported
from there unchanged rather than copied, since Google/Esri/OSM are global.

What is Canadian is which Earth Engine images get minted: the ACI for one year,
VLCE2 for one year, Hansen tree cover and the loss/gain mask, ESA CCI biomass,
NTEMS stand age, the MODIS burn-frequency layer, ACI patches for the Paisagem
tab, and the annual Landsat composites that stand in for Brazil's SPOT mosaics.
Every one goes through the shared :func:`~camposcope.services.tiles.get_tile_url`
cache, so switching years costs one round trip the first time and nothing after.

**Cache keys are prefixed ``ca:``.** The tile cache is process-wide and shared
with the Brazil page. Without the prefix, ``hansen_change:2008:30`` minted for a
Brazilian property would be served to a BC parcel — the same Hansen image, so
the tiles would even look right, which is exactly what would make the collision
hard to notice. Every key here carries the prefix for that reason.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ...config.datasets import AGB, AGB_YEARS, HANSEN_GFC
from ...config.settings import HANSEN_TREECOVER_THRESHOLD
from ...services.layers import basemap_spec  # noqa: F401  (re-exported unchanged)
from ...services.tiles import get_tile_url
from ..config import aafc
from ..config import datasets as ds
from ..config import vlce2 as vlce2_cfg

logger = logging.getLogger(__name__)

LayerSpec = Dict[str, Any]

ACI_ATTRIBUTION = "Agriculture and Agri-Food Canada — Annual Crop Inventory"
NTEMS_ATTRIBUTION = ds.NTEMS_AGE["attribution"]
HANSEN_ATTRIBUTION = HANSEN_GFC["attribution"]


def _spec(cache_key: str, url: Optional[str], *, opacity: float, z_index: int,
          attribution: str, max_native_zoom: int = 15,
          clip: Optional[str] = None) -> Optional[LayerSpec]:
    """Assemble a layer spec, or ``None`` if the URL could not be minted.

    Every builder below fails closed the same way: a layer that cannot mint a
    tile URL returns ``None`` so the caller can say so, rather than handing
    Leaflet a broken template that renders as silent grey.
    """
    if url is None:
        return None
    spec: LayerSpec = {
        "id": cache_key, "url": url, "opacity": opacity, "z_index": z_index,
        "attribution": attribution, "max_native_zoom": max_native_zoom,
    }
    if clip is not None:
        spec["clip"] = clip
    return spec


def _mint(cache_key: str, build, vis) -> Optional[str]:
    try:
        return get_tile_url(cache_key, build, vis)
    except Exception as exc:                      # noqa: BLE001
        logger.warning("Layer %s failed: %s", cache_key, exc)
        return None


# --------------------------------------------------------------------------- #
# Basemaps
# --------------------------------------------------------------------------- #
def landsat_basemap_spec(key: str, year: int, *, z_index: int = 1
                         ) -> Optional[LayerSpec]:
    """One year of the annual Landsat composite, in the chosen rendering.

    The Canadian substitute for the Brazil page's SPOT basemap, and unlike SPOT
    it takes a year — the whole point is that it is a series, not a snapshot.
    """
    conf = ds.LANDSAT_RENDERINGS.get(key)
    if conf is None:
        logger.warning("Unknown Landsat rendering %r", key)
        return None
    if not (ds.LANDSAT_ANNUAL["year_start"] <= year
            <= ds.LANDSAT_ANNUAL["year_end"]):
        logger.warning("Landsat year %s outside %s–%s", year,
                       ds.LANDSAT_ANNUAL["year_start"],
                       ds.LANDSAT_ANNUAL["year_end"])
        return None

    cache_key = f"ca:landsat:{key}:{year}"

    def build():
        import ee
        col = ee.ImageCollection(ds.LANDSAT_ANNUAL["asset"])
        return ee.Image(
            col.filterDate(f"{year}-01-01", f"{year}-12-31").first()
        )

    return _spec(
        cache_key, _mint(cache_key, build, conf["vis"]),
        opacity=1.0, z_index=z_index,
        attribution=f"{ds.LANDSAT_ANNUAL['attribution']} — {year}",
        max_native_zoom=conf.get("max_native_zoom", 14),
    )


# --------------------------------------------------------------------------- #
# Cobertura — the ACI
# --------------------------------------------------------------------------- #
def aci_year_spec(year: int, *, opacity: float = 0.75, z_index: int = 10
                  ) -> Optional[LayerSpec]:
    """AAFC Annual Crop Inventory for one year — the Cobertura tab's layer."""
    if year not in aafc.ACI_YEARS:
        logger.warning("ACI year %s outside %s–%s", year,
                       aafc.ACI_YEAR_START, aafc.ACI_YEAR_END)
        return None

    from .aci_history import aci_year_image

    cache_key = f"ca:aci:{year}"
    return _spec(
        cache_key,
        _mint(cache_key, lambda: aci_year_image(year), aafc.ACI_VIS),
        opacity=opacity, z_index=z_index,
        attribution=f"{ACI_ATTRIBUTION} {year}",
    )


# --------------------------------------------------------------------------- #
# Validação — VLCE2
# --------------------------------------------------------------------------- #
def vlce2_year_spec(year: int, *, opacity: float = 0.75, z_index: int = 10
                    ) -> Optional[LayerSpec]:
    """NTEMS VLCE2 for one year — the Validação tab's left-hand layer."""
    if year not in vlce2_cfg.VLCE2_YEARS:
        logger.warning("VLCE2 year %s outside %s–%s", year,
                       vlce2_cfg.VLCE2_YEAR_START, vlce2_cfg.VLCE2_YEAR_END)
        return None

    from .vlce2 import vlce2_year_image

    cache_key = f"ca:vlce2:{year}"
    return _spec(
        cache_key,
        _mint(cache_key, lambda: vlce2_year_image(year), vlce2_cfg.VLCE2_VIS),
        opacity=opacity, z_index=z_index,
        attribution=f"{vlce2_cfg.VLCE2_ATTRIBUTION} — {year}",
    )


# --------------------------------------------------------------------------- #
# Floresta — Hansen and NTEMS age
# --------------------------------------------------------------------------- #
def hansen_change_spec(
    from_year: int, *, threshold: int = HANSEN_TREECOVER_THRESHOLD,
    opacity: float = 0.85, z_index: int = 16,
) -> Optional[LayerSpec]:
    """Loss since ``from_year`` (red) and gain (green, undated).

    Loss is gated by the canopy threshold — a pixel that was never forest cannot
    lose it. Gain is not: Hansen publishes it as one undated flag with no canopy
    percentage to threshold against. So moving the baseline changes the red and
    leaves the green alone, which the legend says out loud, because a control
    that silently governs only half of what it draws is a trap.
    """
    year_start = HANSEN_GFC["loss_year_start"]
    year_end = HANSEN_GFC["loss_year_end"]
    if not (year_start <= from_year <= year_end):
        logger.warning("Hansen loss year %s outside %s–%s",
                       from_year, year_start, year_end)
        return None

    cache_key = f"ca:hansen_change:{from_year}:{threshold}"

    def build():
        import ee
        gfc = ee.Image(HANSEN_GFC["asset"])
        forest2000 = gfc.select("treecover2000").gte(threshold)
        code = from_year - year_start + 1
        loss = (gfc.select("loss").eq(1).And(forest2000)
                .And(gfc.select("lossyear").gte(code)))
        gain = gfc.select("gain").eq(1)
        # 1 = loss, 2 = gain. Loss painted second so a pixel flagged both ways
        # reads as loss — the conservative call for a screening layer.
        return ee.Image(0).where(gain, 2).where(loss, 1).selfMask().rename("change")

    vis = {"min": 1, "max": 2,
           "palette": [HANSEN_GFC["loss_color"].lstrip("#"),
                       HANSEN_GFC["gain_color"].lstrip("#")]}
    return _spec(
        cache_key, _mint(cache_key, build, vis),
        opacity=opacity, z_index=z_index,
        attribution=(f"{HANSEN_ATTRIBUTION} — loss {from_year}–{year_end}, "
                     "gain (undated)"),
        max_native_zoom=13,
    )


def forest_age_spec(*, opacity: float = 0.75, z_index: int = 12
                    ) -> Optional[LayerSpec]:
    """NTEMS stand age. One image, no year parameter — a 2019 snapshot.

    Read through ``.mosaic()``, which is load-bearing: sampling ``.first()``
    returns null everywhere (see ``canada/config/datasets.py::NTEMS_AGE``).
    """
    cache_key = "ca:ntems_age"

    def build():
        import ee
        return (ee.ImageCollection(ds.NTEMS_AGE["asset"]).mosaic()
                .select(ds.NTEMS_AGE["band"]))

    return _spec(
        cache_key, _mint(cache_key, build, ds.NTEMS_AGE["vis"]),
        opacity=opacity, z_index=z_index, attribution=NTEMS_ATTRIBUTION,
    )


# --------------------------------------------------------------------------- #
# Biomassa
# --------------------------------------------------------------------------- #
def biomass_year_spec(year: int, *, opacity: float = 0.75, z_index: int = 14
                      ) -> Optional[LayerSpec]:
    """ESA CCI above-ground biomass for one year."""
    if year not in AGB_YEARS:
        logger.warning("Biomass year %s not in %s", year, AGB_YEARS)
        return None

    cache_key = f"ca:biomass:{year}"

    def build():
        import ee
        return ee.Image(AGB["asset_template"].format(year=year)).select([0])

    return _spec(
        cache_key, _mint(cache_key, build, AGB["vis"]),
        opacity=opacity, z_index=z_index, attribution=AGB["attribution"],
        max_native_zoom=12,
    )


# --------------------------------------------------------------------------- #
# Fogo
# --------------------------------------------------------------------------- #
def fire_frequency_spec(*, opacity: float = 0.75, z_index: int = 12
                        ) -> Optional[LayerSpec]:
    """Burn frequency from MODIS MCD64A1 — how many years each pixel burned.

    Derived from the annual stack rather than a published frequency band, since
    MODIS has no equivalent of MapBiomas' pre-computed one. The palette matches
    the legend's gradient bar exactly, so the on-map colours and the swatch can
    never drift apart.

    **Masked here, and only here.** ``fire.fire_frequency_image()`` is
    deliberately dense (every pixel carries a value, unburned ones included) —
    ``fire_analysis()`` needs that density for the zone mean to include the
    unburned pixels it is averaged over. A map *tile* built from that same dense
    image instead paints "0 = white" over the entire basemap, which is not a
    frequency layer, it is a translucent wash indistinguishable at a glance from
    a broken tile. ``selfMask()`` drops the zero pixels so only ever-burned
    ground draws at all — the mask stays local to this function so
    ``fire_analysis()``'s reducer input is untouched.
    """
    from .fire import FIRE_FREQUENCY_MAX, fire_frequency_image

    cache_key = "ca:fire_frequency"
    vis = {"min": 1, "max": FIRE_FREQUENCY_MAX, "palette": ds.MODIS_BURN["vis_palette"]}

    return _spec(
        cache_key,
        _mint(cache_key, lambda: fire_frequency_image().selfMask(), vis),
        opacity=opacity, z_index=z_index,
        attribution=f"{ds.MODIS_BURN['attribution']} · {ds.MODIS_BURN['scale_m']} m",
        max_native_zoom=11,
    )


def aci_burn_frequency_spec(*, opacity: float = 0.85, z_index: int = 13
                            ) -> Optional[LayerSpec]:
    """AAFC ACI class 60 composited across the whole record — the
    higher-resolution complement to the MODIS frequency layer above.

    30 m against MODIS' 500 m. Mirrors :func:`fire_frequency_spec` in shape
    for the same reason: a single-year layer went dark for every parcel
    except the one year it last burned, out of step with the analysis
    chart's full-record answer — see
    ``fire.aci_burn_frequency_image``'s docstring. ``selfMask()`` for the
    same reason as the MODIS layer: the underlying image is dense so the
    zone-mean statistic includes never-burnt pixels, and a dense image
    painted as a map tile washes the whole basemap instead of highlighting
    only the burnt ground.
    """
    from .fire import ACI_BURN_FREQUENCY_MAX, aci_burn_frequency_image

    cache_key = "ca:aci_burn_frequency"
    vis = {"min": 1, "max": ACI_BURN_FREQUENCY_MAX,
           "palette": ["fed976", "fd8d3c", "bd0026"]}

    return _spec(
        cache_key,
        _mint(cache_key, lambda: aci_burn_frequency_image().selfMask(), vis),
        opacity=opacity, z_index=z_index,
        attribution=(f"{ACI_ATTRIBUTION} {aafc.ACI_YEAR_START}–"
                     f"{aafc.ACI_YEAR_END} — burnt-area class · 30 m"),
    )


# --------------------------------------------------------------------------- #
# Paisagem — patches
# --------------------------------------------------------------------------- #
#: A hash-like palette, not a true graph colouring (Earth Engine has none) —
#: enough that adjacent patches usually differ in colour, which is the point:
#: making patch BOUNDARIES visible, not identifying any specific patch by hue.
_PATCH_PALETTE = ["e6194b", "3cb44b", "ffe119", "4363d8", "f58231", "911eb4",
                  "46f0f0", "f032e6", "bcf60c", "fabebe", "008080", "e6beff"]


def landscape_patches_spec(
    year: int, clip_geojson: Dict[str, Any], cache_id: str,
    *, opacity: float = 0.75, z_index: int = 18,
) -> Optional[LayerSpec]:
    """Connected-component patches for one ACI year, clipped to the parcel's
    own analysis extent.

    **Clipped, unlike every sibling layer here.** A patch's colour is an
    arbitrary ``labels.mod(palette)`` hash with no meaning outside the parcel
    being analysed, so panning out would paint the visible extent with
    unrelated, equally arbitrary colours — noise, not data. This is therefore
    the one layer clipped to ``clip_geojson``, and the one whose cache key must
    carry the parcel's identity: the clip is baked into the minted tile, so a
    different parcel cannot reuse another's cached URL.
    """
    if year not in aafc.ACI_YEARS:
        logger.warning("Landscape patches year %s outside %s–%s", year,
                       aafc.ACI_YEAR_START, aafc.ACI_YEAR_END)
        return None
    if not clip_geojson:
        return None

    from .aci_history import aci_year_image

    cache_key = f"ca:landscape_patches:{year}:{cache_id}"

    def build():
        import ee
        image = aci_year_image(year).rename("class")
        labels = image.connectedComponents(
            ee.Kernel.square(1), 1024).select("labels")
        return labels.mod(len(_PATCH_PALETTE)).clip(ee.Geometry(clip_geojson))

    vis = {"min": 0, "max": len(_PATCH_PALETTE) - 1, "palette": _PATCH_PALETTE}
    return _spec(
        cache_key, _mint(cache_key, build, vis),
        opacity=opacity, z_index=z_index,
        attribution=(f"{ACI_ATTRIBUTION} {year} — patches "
                     "(connectedComponents, 8-neighbour), clipped to the "
                     "analysis extent"),
    )


__all__ = [
    "basemap_spec", "landsat_basemap_spec", "aci_year_spec", "vlce2_year_spec",
    "hansen_change_spec", "forest_age_spec", "biomass_year_spec",
    "fire_frequency_spec", "aci_burn_frequency_spec", "landscape_patches_spec",
]
