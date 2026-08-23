"""Map click → which ``sicar_imoveis_<uf>`` layer to query.

Decision **D5**. The CAR GeoServer has no national layer, so every spatial query
must know its UF first (doc/05-sicar-geoserver.md §5.3). This module answers that
from a committed, simplified IBGE boundary file — no network call, deterministic,
and it cannot fail in the one way that matters: guessing wrong returns an empty
result that looks exactly like "no property registered here".

The boundaries are deliberately coarse. Near a state line
:func:`candidate_ufs` offers the neighbours, and the property query itself is the
arbiter — one bounded fallback, not a fan-out across 27 layers (constraint C5).
"""

from __future__ import annotations

import json
import logging
import pathlib
import threading
from typing import List, Optional, Tuple

from shapely.geometry import Point, shape
from shapely.prepared import prep

logger = logging.getLogger(__name__)

_DATA = (pathlib.Path(__file__).resolve().parent.parent.parent
         / "data" / "uf_boundaries.simplified.geojson")

_lock = threading.Lock()
_index: Optional[List[Tuple[str, object, object]]] = None   # (uf, prepared, geom)


def _load() -> List[Tuple[str, object, object]]:
    """Load and prepare the polygons once.

    ``shapely.prepared.prep`` builds an index that makes repeated
    point-in-polygon tests cheap — this is called on every map click.
    """
    global _index
    if _index is None:
        with _lock:
            if _index is None:
                if not _DATA.exists():
                    raise FileNotFoundError(
                        f"{_DATA} não encontrado. Rode "
                        "`python scripts/fetch_uf_boundaries.py`."
                    )
                data = json.loads(_DATA.read_text(encoding="utf-8"))
                built = []
                for feat in data["features"]:
                    geom = shape(feat["geometry"])
                    built.append((feat["properties"]["uf"], prep(geom), geom))
                _index = built
                logger.info("UF boundary index built: %d polygons", len(built))
    return _index


def uf_for_point(lat: float, lon: float) -> Optional[str]:
    """The UF containing this point, or ``None`` if it is outside Brazil."""
    pt = Point(lon, lat)
    for uf, prepared, _geom in _load():
        if prepared.contains(pt):
            return uf
    return None


def candidate_ufs(lat: float, lon: float, *, tolerance_deg: float = 0.05) -> List[str]:
    """The containing UF first, then any whose boundary is within ``tolerance``.

    The simplified geometry can put a point a few hundred metres on the wrong
    side of a state line. Rather than accept a false "no property here", the
    caller may try the neighbour — once. ``tolerance_deg`` of 0.05 is roughly
    5 km, comfortably more than the simplification error.
    """
    pt = Point(lon, lat)
    inside: List[str] = []
    near: List[str] = []
    for uf, prepared, geom in _load():
        if prepared.contains(pt):
            inside.append(uf)
        elif geom.distance(pt) <= tolerance_deg:
            near.append(uf)
    return inside + near


__all__ = ["uf_for_point", "candidate_ufs"]
