"""The property's geometry, its rings, its area check and its overlaps.

Zones are what every analysis consumes (doc/02-architecture.md §3). They are
built **locally in shapely** (decision D3), so they reach the map within
milliseconds of the boundary arriving, while Earth Engine work is still running.

Constraint **C2**: every geometry here is a plain GeoJSON dict.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import reflex as rx

from ..config.settings import RING_RADII_M
from ..services import zones as zones_svc
from ..translations import get_translations

logger = logging.getLogger(__name__)


class ZonesMixin(rx.State, mixin=True):
    """Property + neighbourhood rings."""

    ring_radii_m: List[int] = list(RING_RADII_M)

    #: One dict per zone: key, label, kind, radius_m, area_ha. The geometries
    #: live in ``zones_geojson`` so a chart re-render does not carry polygons.
    zones: List[Dict[str, Any]] = []
    zones_geojson: Dict[str, Any] = {}

    #: Declared vs. computed (decision D6). The disagreement is information.
    area_declarada_ha: float = 0.0
    area_calculada_ha: float = 0.0
    area_delta_ha: float = 0.0
    area_delta_pct: float = 0.0
    area_flagged: bool = False

    #: Other registrations overlapping this one. Listed, never dissolved (D7).
    overlaps: List[Dict[str, Any]] = []

    zones_error: str = ""

    @rx.var
    def zone_count(self) -> int:
        return len(self.zones)

    @rx.var
    def map_overlays(self) -> Dict[str, Any]:
        """A FeatureCollection the Leaflet component draws above the tiles.

        Each feature carries a ``role`` property, which is what the hook styles
        on: the property boundary reads differently from a ring.
        """
        return self.zones_geojson or {"type": "FeatureCollection", "features": []}

    def build_zones(self) -> None:
        """Rebuild every zone from the currently selected property.

        Called by ``ImovelMixin._adopt``; also re-run when the ring radii change.
        Deliberately synchronous — it is shapely on one polygon, and making it a
        background task would put the rings on the map *later* for no gain.
        """
        geojson = getattr(self, "imovel_geojson", None)
        if not geojson:
            self.zones = []
            self.zones_geojson = {}
            self.overlaps = []
            return

        self.zones_error = ""
        # Zone labels are not threaded through AppState.tr — see
        # translations/__init__.py's own docstring (§3: "known gap, not an
        # oversight", the coupling cost of threading `lang` through the
        # zone-building service was judged not worth it for one word). This
        # kind-based switch stays inside that same boundary: a second plain
        # PT literal, not a step toward full i18n here.
        kind = getattr(self, "imovel", {}).get("kind", "imovel")
        label = "Área de referência" if kind == "square" else "Imóvel"
        try:
            built = zones_svc.build_zones(
                geojson, radii_m=self.ring_radii_m, property_label=label)
        except Exception as exc:                       # a self-declared polygon
            logger.exception("zone construction failed")
            self.zones_error = get_translations(getattr(self, "lang", "pt"))[
                "erro_zonas"
            ].format(detail=exc)
            self.zones = []
            self.zones_geojson = {}
            return

        self.zones = [z.to_row() for z in built]
        self.zones_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "role": "property" if z.kind == "property" else "ring",
                        "zone_key": z.key,
                        "label": z.label,
                        "area_ha": round(z.area_ha, 2),
                    },
                    "geometry": z.geojson,
                }
                for z in built
            ],
        }

        declared = float(getattr(self, "imovel", {}).get("area_declarada_ha", 0.0))
        check = zones_svc.check_area(declared, geojson)
        self.area_declarada_ha = check.declared_ha
        self.area_calculada_ha = round(check.computed_ha, 4)
        self.area_delta_ha = round(check.delta_ha, 4)
        self.area_delta_pct = round(check.delta_pct, 3)
        self.area_flagged = check.flagged

    @rx.event(background=True)
    async def load_overlaps(self):
        """Which neighbouring registrations overlap this property (D7).

        A second SICAR call, so it is a background event and its failure is
        isolated: an overlap list that cannot load must not take the cadastral
        card with it.
        """
        from ..services import sicar

        async with self:
            code = self.imovel.get("cod_imovel", "")
            uf = self.imovel.get("uf", "")
            geojson = self.imovel_geojson
        if not (code and uf and geojson):
            return

        try:
            record = sicar.by_code(code)
            others = sicar.overlapping(record)
            rows = zones_svc.overlap_areas(
                geojson, [(o.cod_imovel, o.geometry) for o in others]
            )
        except Exception as exc:
            logger.warning("overlap lookup failed: %s", exc)
            async with self:
                self.overlaps = []
            return

        async with self:
            self.overlaps = rows
