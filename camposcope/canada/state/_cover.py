"""The AAFC crop-inventory trajectory (Cobertura tab).

The Canadian counterpart of ``camposcope/state/_analysis.py::AnalysisMixin``.
Runs as a background handler for the same reason: the parcel card and rings are
already on screen and interactive while this is still fetching.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import plotly.graph_objects as go
import reflex as rx

from ...state._proxy import plain
from ..components import charts
from ..config import aafc as mb
from ..translations import get_translations

logger = logging.getLogger(__name__)


class CanadaCoverMixin(rx.State, mixin=True):
    """ACI history: the job, its result, its failure."""

    history_running: bool = False
    history_error: str = ""
    history_rows: List[Dict[str, Any]] = []
    history_degraded: bool = False
    history_notes: List[str] = []
    history_provenance: Dict[str, Any] = {}
    #: Set when the parcel is north of the ACI's coverage — an empty result
    #: is expected there and the tab says so instead of reading as an error.
    history_out_of_range: bool = False

    history_normalise: bool = False
    aci_layer_year: int = mb.ACI_YEAR_END

    @rx.var
    def has_history(self) -> bool:
        return bool(self.history_rows)

    @rx.var
    def history_rows_for_zone(self) -> List[Dict[str, Any]]:
        zone = self.active_zone
        return [r for r in self.history_rows if r["zone_key"] == zone]

    @rx.var(cache=True,
            deps=["history_rows", "active_zone", "aci_layer_year", "language"],
            auto_deps=False)
    def history_table_rows(self) -> List[Dict[str, Any]]:
        year = self.aci_layer_year
        lang = getattr(self, "language", "en")
        class_key = "class_pt" if lang == "pt" else "class_en"
        rows = [r for r in self.history_rows_for_zone if r["year"] == year]
        total = sum(r["area_ha"] for r in rows) or 1.0
        out = [
            {"class_label": r[class_key], "color": r["color"],
             "area_ha": round(r["area_ha"], 2),
             "area_pct": round(100.0 * r["area_ha"] / total, 1)}
            for r in rows
        ]
        out.sort(key=lambda r: r["area_ha"], reverse=True)
        return out

    def set_aci_layer_year(self, year: str) -> None:
        self.aci_layer_year = int(year)
        return self.__class__.mint_analysis_layer

    @rx.var(cache=True,
            deps=["history_rows", "active_zone", "history_normalise", "parcel",
                  "language"],
            auto_deps=False)
    def history_figure(self) -> go.Figure:
        return charts.land_cover_history_figure(
            self.history_rows_for_zone,
            lang=getattr(self, "language", "en"),
            normalise=self.history_normalise,
            start_year=getattr(self, "parcel", {}).get("start_year") or None,
        )

    def toggle_history_normalise(self) -> None:
        self.history_normalise = not self.history_normalise

    @rx.event(background=True)
    async def run_aci_history(self):
        from ..services.aci_history import land_cover_history
        from ...services.zones import Zone

        async with self:
            zones_geojson = plain(self.zones_geojson) or {}
            zones_meta = list(self.zones or [])
            lang = getattr(self, "language", "en")
            self.history_running = True
            self.history_error = ""
            self.history_rows = []
            self.history_degraded = False
            self.history_notes = []
            self.history_provenance = {}
            self.history_out_of_range = False

        if not zones_meta or not zones_geojson.get("features"):
            async with self:
                self.history_running = False
            return

        try:
            geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                          for f in zones_geojson["features"]}
            zone_objs = [
                Zone(key=z["zone_key"], label=z["zone_label"], kind=z["zone_kind"],
                    geojson=geom_by_key[z["zone_key"]], area_ha=z["area_ha"],
                    radius_m=z.get("radius_m"))
                for z in zones_meta if z["zone_key"] in geom_by_key
            ]
            df, prov = land_cover_history(zone_objs)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("ACI history failed")
            async with self:
                self.history_running = False
                self.history_error = get_translations(lang)[
                    "erro_trajetoria_aci"].format(detail=exc)
            return

        async with self:
            self.history_running = False
            self.history_rows = df.to_dict("records") if not df.empty else []
            self.history_degraded = prov.degraded
            self.history_notes = list(prov.notes)
            self.history_provenance = prov.to_dict()
            if df.empty:
                self.history_out_of_range = True
                self.history_error = get_translations(lang)["erro_aci_sem_classes"]
