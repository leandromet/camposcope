"""The World Database on Protected Areas (WDPA) — the fallback analysis area
for a click that lands on no parcel.

Most of Canada has no parcel fabric at all: ParcelMap BC is a provincial
cadastre, and even inside BC most of the province is unsurveyed Crown land
(``pmbc.py``'s module docstring). A click that misses a parcel is not
necessarily a click on nothing — it is very often a click *inside a national
or provincial park*, and WDPA is what answers that question, nationwide, from
one Earth Engine asset with no separate BC/rest-of-Canada split to maintain.

**Why WDPA and not a Canadian-specific source.** ``WCMC/WDPA/current/polygons``
is UNEP-WCMC/IUCN's global protected-area register, verified in Earth Engine on
2026-08-27: 17,029 Canadian entries (``ISO3 == "CAN"``), point queries answering
in under a second, real metadata (name, designation, IUCN category, managing
authority, reported area). It already covers every province — a park in
Ontario or Alberta answers exactly the same way a BC one does, which a
BC-scoped Parks-and-Protected-Areas layer could not offer on its own.

**Overlapping designations are the normal case, not the exception.** A national
park routinely sits inside a broader international designation — verified at
Banff, which returns both "Banff National Park Of Canada" (6,641 km²) and
"Parcs des montagnes Rocheuses canadiennes", the UNESCO World Heritage Site
umbrella covering several parks at once (23,600 km²). Picking the umbrella
would name the wrong thing for "what did this click land in": **the smallest
containing polygon wins**, which in practice means the actual local management
unit rather than the broad multi-park designation wrapped around it. No
chooser UI, unlike the parcel candidates picker — WDPA overlaps are a
containment hierarchy (bigger designations wrapping smaller ones), not
contested claims over the same ground the way two SICAR registrations are.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

WDPA_ASSET = "WCMC/WDPA/current/polygons"

#: Fields pulled from the asset — kept short deliberately. WDPA carries dozens
#: of columns (management plan URLs, ownership sub-types, verification
#: status…) that have no reader here; requesting only what the card shows
#: keeps each query small.
_FIELDS = ["NAME", "DESIG", "DESIG_ENG", "DESIG_TYPE", "IUCN_CAT", "STATUS",
          "STATUS_YR", "MANG_AUTH", "REP_AREA", "WDPAID"]

#: Process-lifetime cache, same reasoning as ``pmbc.py``'s: a protected area's
#: boundary does not change during a session.
_cache: Dict[str, "Optional[ProtectedArea]"] = {}
_cache_lock = threading.Lock()


class WdpaError(RuntimeError):
    """A failure querying the WDPA asset — distinct from ``PmbcError`` for the
    same reason that is distinct from ``SicarError`` on the Brazil page: the
    UI shows a failure here differently from a parcel-service failure, and one
    must not take the other down with it."""


@dataclass(frozen=True)
class ProtectedArea:
    """One WDPA polygon, as published. Fields are carried **verbatim** — the
    same discipline ``pmbc.Parcel`` applies to the fabric, extended to a
    register with a different kind of authority behind it (IUCN/UNEP-WCMC's
    international standard, not a provincial land title office)."""

    wdpa_id: int
    name: str
    designation: str
    designation_type: str
    iucn_category: str
    status: str
    status_year: Optional[int]
    managing_authority: str
    reported_area_km2: float
    geometry: Optional[dict] = field(default=None, repr=False)
    queried_at: str = ""

    @classmethod
    def from_feature(cls, feat: dict, queried_at: str) -> "ProtectedArea":
        p = feat.get("properties") or {}
        return cls(
            wdpa_id=int(p.get("WDPAID") or 0),
            name=p.get("NAME") or p.get("DESIG_ENG") or "",
            designation=p.get("DESIG_ENG") or p.get("DESIG") or "",
            designation_type=p.get("DESIG_TYPE") or "",
            iucn_category=p.get("IUCN_CAT") or "",
            status=p.get("STATUS") or "",
            status_year=(int(p["STATUS_YR"])
                        if p.get("STATUS_YR") not in (None, 0) else None),
            managing_authority=p.get("MANG_AUTH") or "",
            reported_area_km2=float(p.get("REP_AREA") or 0.0),
            geometry=feat.get("geometry"),
            queried_at=queried_at,
        )


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def at_point(lat: float, lon: float) -> Optional[ProtectedArea]:
    """The most specific Canadian protected area containing this point, or
    ``None``.

    "Most specific" = smallest ``REP_AREA`` among every polygon that contains
    the point — see the module docstring for why that beats "first result"
    when designations nest.
    """
    key = f"{lat:.6f}:{lon:.6f}"
    with _cache_lock:
        if key in _cache:
            return _cache[key]

    import ee

    from ...services.ee_client import get_ee

    get_ee()
    fc = (ee.FeatureCollection(WDPA_ASSET)
          .filter(ee.Filter.eq("ISO3", "CAN"))
          .filterBounds(ee.Geometry.Point([lon, lat]))
          .select(_FIELDS))

    try:
        info = fc.getInfo()
    except Exception as exc:                       # noqa: BLE001
        raise WdpaError(f"Could not query the protected-areas register: {exc}")

    features = info.get("features") or []
    if not features:
        with _cache_lock:
            _cache[key] = None
        return None

    features.sort(key=lambda f: float((f.get("properties") or {})
                                      .get("REP_AREA") or float("inf")))
    result = ProtectedArea.from_feature(features[0], _now())
    with _cache_lock:
        _cache[key] = result
    return result


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


__all__ = ["ProtectedArea", "WdpaError", "at_point", "clear_cache", "WDPA_ASSET"]
