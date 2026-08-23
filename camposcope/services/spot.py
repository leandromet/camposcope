"""SPOT 2008 coverage and acquisition dates (doc/12-spot-2008.md).

The Google Brazil Forest 2008 mosaic is *circa* 2008, and its ``date`` band
carries **per-pixel acquisition time as Unix epoch seconds**. The Código
Florestal's *área rural consolidada* turns on 22 July 2008, so "when was this
pixel actually photographed" is not a footnote here — it is the difference
between imagery that predates the legal reference date and imagery that does not.

This module answers that for one property. It does **not** classify anything:
reporting that 96 % of a property's pixels were imaged before the cutoff is an
observation; calling the area *consolidada* is a legal determination resting on
facts no photograph contains, and decision D9 forbids it. See doc/12 §4.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict, Optional, Tuple

from ..config.datasets import (
    EE_BASEMAPS,
    FOREST_CODE_CUTOFF_EPOCH,
    FOREST_CODE_CUTOFF_ISO,
    SPOT_META_BANDS,
)
from ..config.settings import EE_MAX_PIXELS, SPOT_ENABLED
from .provenance import Provenance

logger = logging.getLogger(__name__)

#: The question is "when was this imaged", not "what colour is this pixel", and
#: 100 m answers it for a fraction of a 5 m reduction's cost.
DATE_SCALE_M = 100

VISUAL_ASSET = EE_BASEMAPS["spot_2008_visual"]["asset"]


def _iso(epoch: Optional[float]) -> Optional[str]:
    if epoch is None:
        return None
    return dt.datetime.fromtimestamp(float(epoch), dt.timezone.utc).date().isoformat()


def coverage(geojson: Dict[str, Any]) -> Tuple[Dict[str, Any], Provenance]:
    """Acquisition-date summary for the SPOT pixels under one geometry.

    Returns ``(summary, provenance)`` like every analysis in this app
    (doc/02-architecture.md §6). The summary carries:

    ``covered_pct``
        Share of the geometry with any SPOT coverage. The mosaic covers Brazil's
        **forest areas only** — a gap is the dataset, not a failure, and a
        property with no coverage must be told so rather than shown an empty map.
    ``date_min`` / ``date_max``
        ISO dates of the earliest and latest pixel actually over this property.
    ``pre_cutoff_pct``
        Share of the *covered* pixels acquired before 2008-07-22.
    """
    if not SPOT_ENABLED:
        raise RuntimeError(
            "SPOT 2008 está desativado nesta instalação (CS_SPOT_ENABLED)."
        )

    import ee

    from .ee_client import get_ee

    get_ee()

    geom = ee.Geometry(geojson)
    img = ee.Image(VISUAL_ASSET)

    # `date` is 0/masked where there is no scene. Reducing the mask alongside the
    # date is what separates "no coverage" from "coverage, old date" — two very
    # different answers that a single reducer would blur together.
    date_band = img.select("date")
    covered = date_band.mask().rename("covered")
    pre_cutoff = (date_band.lt(FOREST_CODE_CUTOFF_EPOCH)
                  .rename("pre_cutoff")
                  .updateMask(date_band.mask()))

    stats = (
        date_band.rename("date")
        .addBands(covered)
        .addBands(pre_cutoff)
        .addBands(img.select("scale").rename("scale"))
        .reduceRegion(
            reducer=(ee.Reducer.minMax()
                     .combine(ee.Reducer.mean(), sharedInputs=True)),
            geometry=geom,
            scale=DATE_SCALE_M,
            maxPixels=EE_MAX_PIXELS,
            bestEffort=True,
        )
        .getInfo()
    ) or {}

    covered_mean = stats.get("covered_mean")
    date_min, date_max = stats.get("date_min"), stats.get("date_max")
    pre_mean = stats.get("pre_cutoff_mean")

    # `covered_mean` is the fraction of pixels with data because the mask is 1/0.
    covered_pct = None if covered_mean is None else round(100.0 * covered_mean, 1)
    has_coverage = bool(covered_pct)

    summary: Dict[str, Any] = {
        "has_coverage": has_coverage,
        "covered_pct": covered_pct,
        "date_min": _iso(date_min) if has_coverage else None,
        "date_max": _iso(date_max) if has_coverage else None,
        "pre_cutoff_pct": (None if (pre_mean is None or not has_coverage)
                           else round(100.0 * pre_mean, 1)),
        "cutoff": FOREST_CODE_CUTOFF_ISO,
        "scale_min_m": stats.get("scale_min"),
        "scale_max_m": stats.get("scale_max"),
        # Carried so the UI never has to reconstruct the wording, and so it
        # survives into every export that includes this layer (doc/12 §4).
        "note_pt": (
            "Imagens SPOT de aproximadamente 2008, referência visual para a data "
            f"de corte do Código Florestal ({FOREST_CODE_CUTOFF_ISO}). A data de "
            "aquisição varia por pixel. Camposcope não classifica área "
            "consolidada nem avalia regularidade."
        ),
    }

    prov = Provenance(
        name="spot_2008_coverage",
        dataset_id=VISUAL_ASSET,
        bands=list(SPOT_META_BANDS),
        scale_m=DATE_SCALE_M,
        reducer="minMax+mean",
        pixel_area_basis="none (date/mask statistics only)",
        max_pixels=EE_MAX_PIXELS,
        geometry=geojson,
        extra={
            "forest_code_cutoff": FOREST_CODE_CUTOFF_ISO,
            "attribution": EE_BASEMAPS["spot_2008_visual"]["attribution"],
        },
    )
    if not has_coverage:
        prov.notes.append(
            "Sem cobertura SPOT 2008 sobre esta geometria — o mosaico cobre "
            "apenas áreas florestais do Brasil."
        )
    return summary, prov


__all__ = ["coverage", "DATE_SCALE_M", "VISUAL_ASSET"]
