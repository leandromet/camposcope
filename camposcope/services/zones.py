"""Property polygon → the zones every analysis consumes.

The central abstraction of doc/02-architecture.md §3: a :class:`Zone` is a named
geometry with a computed area, and *every* analysis function takes a list of
them. Zone 0 is always the property; the rest are neighbourhood rings.

**Rings are measured outward from the boundary, not from a centroid**
(decision D3). A 40 000 ha property and a 12 ha one have nothing comparable
about their centroids, but "the first 500 m outside the fence" means the same
thing for both.

**Everything here is local** — shapely and pyproj, no Earth Engine. That is not
an optimisation detail: it means the rings are on the map within milliseconds of
the boundary arriving, while the EE work is still running
(doc/02-architecture.md §4).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pyproj import CRS, Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform as shapely_transform

from ..config.settings import (
    AREA_DELTA_FLAG_HA,
    AREA_DELTA_FLAG_PCT,
    RING_RADII_M,
)

logger = logging.getLogger(__name__)

WGS84 = CRS.from_epsg(4326)

#: Equal-area, continental. Areas are computed here and nowhere else — a
#: property area that disagrees with the cadastre because of a projection
#: shortcut is exactly the error Camposcope cannot afford (doc/06 §2).
BRAZIL_EQUAL_AREA = CRS.from_proj4(
    "+proj=aea +lat_1=-2 +lat_2=-22 +lat_0=-12 +lon_0=-54 "
    "+x_0=0 +y_0=0 +ellps=GRS80 +units=m +no_defs"
)


@dataclass(frozen=True)
class Zone:
    """One geometry an analysis runs over.

    ``geojson`` is a plain dict in EPSG:4326 — constraint C2: no ``ee.Geometry``
    ever reaches application state.
    """

    key: str        # "imovel" | "ring_500m" | …
    label: str      # "Imóvel" | "0–500 m" | …
    kind: str       # "property" | "ring"
    geojson: Dict[str, Any]
    area_ha: float
    radius_m: Optional[int] = None

    def to_row(self) -> Dict[str, Any]:
        return {
            "zone_key": self.key,
            "zone_label": self.label,
            "zone_kind": self.kind,
            "radius_m": self.radius_m,
            "area_ha": round(self.area_ha, 4),
        }


# --------------------------------------------------------------------------- #
# Projection
# --------------------------------------------------------------------------- #
def _utm_crs_for(lon: float, lat: float) -> CRS:
    """The UTM zone containing this point.

    Buffering happens in UTM rather than the equal-area CRS because a buffer
    must preserve *distance* — "500 m from the fence" has to be 500 m in every
    direction. Areas are then measured in the equal-area CRS, which preserves
    the other thing. Using one projection for both would get one of them wrong.
    """
    zone = int((lon + 180) // 6) + 1
    epsg = (32600 if lat >= 0 else 32700) + zone
    return CRS.from_epsg(epsg)


def _transformer(src: CRS, dst: CRS) -> Transformer:
    return Transformer.from_crs(src, dst, always_xy=True)


def _reproject(geom, src: CRS, dst: CRS):
    return shapely_transform(_transformer(src, dst).transform, geom)


def area_ha(geojson: Dict[str, Any]) -> float:
    """Geometric area in hectares, in an equal-area projection.

    This is the number compared against the cadastre's **declared** ``area``
    (decision D6). It never replaces it.
    """
    geom = shape(geojson)
    projected = _reproject(geom, WGS84, BRAZIL_EQUAL_AREA)
    return projected.area / 10_000.0


# --------------------------------------------------------------------------- #
# Area reconciliation  (decision D6)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AreaCheck:
    """Declared vs. computed, and whether the gap is worth showing.

    The disagreement is information — one of the few things Camposcope can say
    that a plain CAR extract cannot.
    """

    declared_ha: float
    computed_ha: float

    @property
    def delta_ha(self) -> float:
        return self.computed_ha - self.declared_ha

    @property
    def delta_pct(self) -> float:
        if not self.declared_ha:
            return 0.0
        return 100.0 * self.delta_ha / self.declared_ha

    @property
    def flagged(self) -> bool:
        """Above 2 % *or* 5 ha, whichever is larger (open question in D6)."""
        threshold_ha = max(AREA_DELTA_FLAG_HA,
                           abs(self.declared_ha) * AREA_DELTA_FLAG_PCT / 100.0)
        return abs(self.delta_ha) > threshold_ha


def check_area(declared_ha: float, geojson: Dict[str, Any]) -> AreaCheck:
    return AreaCheck(declared_ha=float(declared_ha), computed_ha=area_ha(geojson))


# --------------------------------------------------------------------------- #
# Zones
# --------------------------------------------------------------------------- #
def _ring_label(inner_m: int, outer_m: int) -> str:
    def fmt(m: int) -> str:
        return f"{m} m" if m < 1000 else f"{m / 1000:g} km".replace(".", ",")
    return f"{fmt(inner_m)} – {fmt(outer_m)}" if inner_m else f"0 – {fmt(outer_m)}"


def _ring_key(outer_m: int) -> str:
    return f"ring_{outer_m}m" if outer_m < 1000 else f"ring_{outer_m // 1000}km"


def build_zones(
    property_geojson: Dict[str, Any],
    *,
    radii_m: Sequence[int] = tuple(RING_RADII_M),
    property_label: str = "Imóvel",
) -> List[Zone]:
    """The property, then one true ring per radius.

    Rings are **true rings**: each excludes the property and every smaller ring,
    so their areas are disjoint and can be summed or compared without
    double-counting. Buffering is done in the property's own UTM zone and the
    result converted back to 4326.
    """
    geom = shape(property_geojson)
    if geom.is_empty:
        raise ValueError("Geometria do imóvel vazia.")
    if not geom.is_valid:
        # A self-declared polygon can be self-intersecting; buffer(0) is the
        # standard repair and is preferable to refusing to analyse the property.
        logger.warning("Property geometry invalid; repairing with buffer(0)")
        geom = geom.buffer(0)

    centroid = geom.centroid
    utm = _utm_crs_for(centroid.x, centroid.y)
    to_utm = _transformer(WGS84, utm).transform
    to_wgs = _transformer(utm, WGS84).transform

    geom_utm = shapely_transform(to_utm, geom)

    zones: List[Zone] = [
        Zone(
            key="imovel",
            label=property_label,
            kind="property",
            geojson=mapping(geom),
            area_ha=area_ha(property_geojson),
        )
    ]

    previous = geom_utm
    for radius in sorted(int(r) for r in radii_m):
        grown = geom_utm.buffer(radius)
        ring_utm = grown.difference(previous)
        previous = grown
        if ring_utm.is_empty:
            continue
        ring_wgs = shapely_transform(to_wgs, ring_utm)
        ring_geojson = mapping(ring_wgs)
        inner = 0 if len(zones) == 1 else sorted(radii_m)[len(zones) - 2]
        zones.append(
            Zone(
                key=_ring_key(radius),
                label=_ring_label(int(inner), radius),
                kind="ring",
                geojson=ring_geojson,
                area_ha=area_ha(ring_geojson),
                radius_m=radius,
            )
        )

    return zones


# --------------------------------------------------------------------------- #
# Overlaps  (decision D7)
# --------------------------------------------------------------------------- #
def overlap_areas(
    property_geojson: Dict[str, Any],
    others: Sequence[Tuple[str, Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """How much of this property each neighbouring registration covers.

    Overlapping registrations are the normal state of a self-declared cadastre
    (doc/05 §5.2). They are listed, with their areas, and never dissolved.
    Results are sorted by overlapping area, largest first, and entries that
    touch only at an edge are dropped.
    """
    base = shape(property_geojson)
    if not base.is_valid:
        base = base.buffer(0)
    base_ha = area_ha(property_geojson)

    rows: List[Dict[str, Any]] = []
    for code, other_geojson in others:
        if not other_geojson:
            continue
        other = shape(other_geojson)
        if not other.is_valid:
            other = other.buffer(0)
        inter = base.intersection(other)
        if inter.is_empty or inter.area == 0:
            continue
        inter_ha = area_ha(mapping(inter))
        if inter_ha <= 0:
            continue
        rows.append({
            "cod_imovel": code,
            "overlap_ha": round(inter_ha, 4),
            "overlap_pct_do_imovel": round(100.0 * inter_ha / base_ha, 2) if base_ha else 0.0,
        })

    rows.sort(key=lambda r: r["overlap_ha"], reverse=True)
    return rows


__all__ = [
    "Zone", "AreaCheck",
    "build_zones", "area_ha", "check_area", "overlap_areas",
]
