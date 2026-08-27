"""ESA CCI above-ground biomass — the Biomassa tab."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import plotly.graph_objects as go
import reflex as rx

from ...state._proxy import plain
from ..components import charts
from ..config.datasets import AGB_YEARS
from ..translations import get_translations

logger = logging.getLogger(__name__)


class CanadaBiomassMixin(rx.State, mixin=True):
    biomass_running: bool = False
    biomass_error: str = ""
    biomass_rows: List[Dict[str, Any]] = []
    biomass_provenance: Dict[str, Any] = {}
    biomass_layer_year: int = AGB_YEARS[-1]

    @rx.var(cache=True, deps=["biomass_rows", "active_zone"], auto_deps=False)
    def biomass_table_rows(self) -> List[Dict[str, Any]]:
        rows = [r for r in self.biomass_rows if r["zone_key"] == self.active_zone]
        return [
            {"year": r["year"], "agb_mean_mgha": round(r["agb_mean_mgha"], 1),
             "total_biomass_mg": round(r["total_biomass_mg"], 0)}
            for r in sorted(rows, key=lambda r: r["year"])
        ]

    @rx.var(cache=True, deps=["biomass_rows", "active_zone", "language"],
            auto_deps=False)
    def biomass_figure(self) -> go.Figure:
        rows = [r for r in self.biomass_rows if r["zone_key"] == self.active_zone]
        return charts.biomass_figure(rows, getattr(self, "language", "en"))

    def set_biomass_layer_year(self, year: str) -> None:
        self.biomass_layer_year = int(year)
        return self.__class__.mint_analysis_layer

    @rx.event(background=True)
    async def run_biomass(self):
        from ..services.biomass import above_ground_biomass
        from ...services.zones import Zone

        async with self:
            zones_geojson = plain(self.zones_geojson) or {}
            zones_meta = list(self.zones or [])
            lang = getattr(self, "language", "en")
            self.biomass_running = True
            self.biomass_error = ""
        if not zones_meta or not zones_geojson.get("features"):
            async with self:
                self.biomass_running = False
            return

        geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                      for f in zones_geojson["features"]}
        zone_objs = [
            Zone(key=z["zone_key"], label=z["zone_label"], kind=z["zone_kind"],
                geojson=geom_by_key[z["zone_key"]], area_ha=z["area_ha"])
            for z in zones_meta if z["zone_key"] in geom_by_key
        ]

        try:
            df, prov = above_ground_biomass(zone_objs)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("Biomass failed")
            async with self:
                self.biomass_running = False
                self.biomass_error = get_translations(lang)[
                    "erro_biomassa"].format(detail=exc)
            return

        async with self:
            self.biomass_running = False
            self.biomass_rows = df.to_dict("records") if not df.empty else []
            self.biomass_provenance = prov.to_dict()
