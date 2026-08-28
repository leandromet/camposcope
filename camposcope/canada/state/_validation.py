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
from ..config import aafc
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
    #: The same run's joint histogram at native-class granularity (not the
    #: 8-group matrix above) — what the on-map legend's class swatches read
    #: from, for both the ACI and VLCE2 sides at once. See
    #: services/vlce2.py::class_histogram, and the Brazil page's
    #: AnalysisMixin.validacao_raw_rows for the same pattern.
    validation_raw_rows: List[Dict[str, Any]] = []

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
        from ..services.vlce2 import YearNotComparable, agreement, class_histogram
        from ...services.zones import Zone

        async with self:
            zones_geojson = plain(self.zones_geojson) or {}
            zones_meta = list(self.zones or [])
            zone_key = self.active_zone
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

        import asyncio

        loop = asyncio.get_running_loop()
        try:
            # Independent Earth Engine calls (the grouped confusion matrix,
            # the native-class breakdown for the legend) — issued together
            # so the legend's classes are never one call's wall-clock behind
            # the table's own numbers.
            (summary_df, matrix_df, prov), (raw_df, _raw_prov) = await asyncio.gather(
                loop.run_in_executor(None, agreement, zone_objs, year),
                loop.run_in_executor(None, class_histogram, zone_objs, year),
            )
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

        raw_rows = (raw_df[raw_df["zone_key"] == zone_key].to_dict("records")
                   if not raw_df.empty else [])
        async with self:
            self.validation_running = False
            self.validation_summary = (summary_df.to_dict("records")
                                       if not summary_df.empty else [])
            self.validation_matrix = (matrix_df.to_dict("records")
                                      if not matrix_df.empty else [])
            self.validation_provenance = prov.to_dict()
            self.validation_raw_rows = raw_rows

    def _validation_side_classes(
        self, id_field: str, label_fn, color_fn,
    ) -> List[Dict[str, Any]]:
        """One side's real classes (colour, label, %) from
        validation_raw_rows — same rollup-and-cap convention as the Brazil
        page's AnalysisMixin._validacao_side_classes."""
        lang = getattr(self, "language", "en")
        totals: Dict[int, float] = {}
        for row in self.validation_raw_rows:
            class_id = int(row[id_field])
            totals[class_id] = totals.get(class_id, 0.0) + float(row["area_ha"])
        total_ha = sum(totals.values()) or 1.0
        out = [
            {
                "class_label": label_fn(class_id, lang),
                "color": color_fn(class_id),
                "area_pct": round(100.0 * area_ha / total_ha, 1),
            }
            for class_id, area_ha in totals.items()
        ]
        out.sort(key=lambda r: r["area_pct"], reverse=True)
        return out[:8]

    @rx.var(cache=True, deps=["validation_raw_rows", "language"], auto_deps=False)
    def validation_aci_classes(self) -> List[Dict[str, Any]]:
        """The comparison's left side — real ACI classes present in the
        active zone at ``validation_year``."""
        return self._validation_side_classes("aci_class", aafc.label, aafc.color)

    @rx.var(cache=True, deps=["validation_raw_rows", "language"], auto_deps=False)
    def validation_vlce2_classes(self) -> List[Dict[str, Any]]:
        """The comparison's right side — real VLCE2 classes present in the
        active zone at ``validation_year``."""
        return self._validation_side_classes("vlce2_class", cfg.label, cfg.color)
