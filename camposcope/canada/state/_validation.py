"""Validação tab: the ACI checked against NTEMS VLCE2 for the same year.

See ``canada/services/vlce2.py`` for what this comparison can and cannot say —
it never adjudicates which product is right, the same posture the Brazil page's
SPOT tab takes toward the CAR.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import reflex as rx

from ...state._proxy import plain
from ..config import vlce2 as cfg
from ..translations import get_translations

logger = logging.getLogger(__name__)


class CanadaValidationMixin(rx.State, mixin=True):
    validation_year: int = cfg.COMPARABLE_YEAR_END
    validation_running: bool = False
    validation_error: str = ""
    validation_summary: List[Dict[str, Any]] = []
    validation_matrix: List[Dict[str, Any]] = []
    validation_provenance: Dict[str, Any] = {}

    @rx.var
    def validation_summary_for_zone(self) -> Dict[str, Any]:
        for r in self.validation_summary:
            if r["zone_key"] == self.active_zone:
                return r
        return {}

    @rx.var(cache=True, deps=["validation_matrix", "active_zone", "language"],
            auto_deps=False)
    def validation_matrix_rows(self) -> List[Dict[str, Any]]:
        """Non-zero cells for the active zone, largest first, with translated
        group labels — the confusion-matrix table beside the swipe map."""
        lang = getattr(self, "language", "en")
        rows = [r for r in self.validation_matrix if r["zone_key"] == self.active_zone]
        out = [
            {
                "aci_label": cfg.group_label(r["aci_group"], lang),
                "vlce2_label": cfg.group_label(r["vlce2_group"], lang),
                "area_ha": round(r["area_ha"], 1),
                "is_agreement": r["is_agreement"],
            }
            for r in rows
        ]
        out.sort(key=lambda r: r["area_ha"], reverse=True)
        return out

    def set_validation_year(self, year: str) -> None:
        self.validation_year = int(year)
        return self.__class__.mint_analysis_layer

    @rx.event(background=True)
    async def run_validation(self):
        from ..services.vlce2 import YearNotComparable, agreement
        from ...services.zones import Zone

        async with self:
            zones_geojson = plain(self.zones_geojson) or {}
            zones_meta = list(self.zones or [])
            year = self.validation_year
            lang = getattr(self, "language", "en")
            self.validation_running = True
            self.validation_error = ""
        if not zones_meta or not zones_geojson.get("features"):
            async with self:
                self.validation_running = False
            return

        geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                      for f in zones_geojson["features"]}
        zone_objs = [
            Zone(key=z["zone_key"], label=z["zone_label"], kind=z["zone_kind"],
                geojson=geom_by_key[z["zone_key"]], area_ha=z["area_ha"])
            for z in zones_meta if z["zone_key"] in geom_by_key
        ]

        try:
            summary_df, matrix_df, prov = agreement(zone_objs, year)
        except YearNotComparable as exc:
            async with self:
                self.validation_running = False
                self.validation_error = str(exc)
            return
        except Exception as exc:                       # noqa: BLE001
            logger.exception("ACI/VLCE2 agreement failed")
            async with self:
                self.validation_running = False
                self.validation_error = get_translations(lang)[
                    "erro_validacao"].format(detail=exc)
            return

        async with self:
            self.validation_running = False
            self.validation_summary = (summary_df.to_dict("records")
                                       if not summary_df.empty else [])
            self.validation_matrix = (matrix_df.to_dict("records")
                                      if not matrix_df.empty else [])
            self.validation_provenance = prov.to_dict()
