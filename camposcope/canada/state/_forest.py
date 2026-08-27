"""Hansen forest change (split at the parcel's own start date, when it has
one) and NTEMS stand age — the Floresta tab."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import plotly.graph_objects as go
import reflex as rx

from ...state._proxy import plain
from ..components import charts
from ..services import hansen
from ..translations import get_translations

logger = logging.getLogger(__name__)


class CanadaForestMixin(rx.State, mixin=True):
    """Hansen loss/gain + NTEMS stand age, for the active parcel."""

    #: "start_date" (split at the parcel's own PARCEL_START_DATE, when it has
    #: one) or "undivided" (a plain annual series). The parcel card decides
    #: which is even offered — see components/parcel_card.py.
    hansen_layer_split: str = "start_date"

    hansen_running: bool = False
    hansen_error: str = ""
    hansen_loss_rows: List[Dict[str, Any]] = []
    hansen_gain_ha: float = 0.0
    hansen_has_run: bool = False
    hansen_split_year: int = 0
    hansen_provenance: Dict[str, Any] = {}

    age_running: bool = False
    age_error: str = ""
    age_rows: List[Dict[str, Any]] = []
    age_has_run: bool = False
    age_provenance: Dict[str, Any] = {}

    def set_hansen_layer_split(self, mode: str | list[str]) -> None:
        value = mode[0] if isinstance(mode, list) else mode
        self.hansen_layer_split = value if value in ("start_date", "undivided") \
            else "start_date"
        return self.__class__.mint_analysis_layer

    def _period_labels(self) -> Dict[str, str]:
        return charts.hansen_period_labels(getattr(self, "language", "en"))

    def _hansen_period_total(self, period: str) -> float:
        return round(sum(
            r["area_ha"] for r in self.hansen_loss_rows
            if r["zone_key"] == self.active_zone and r["period"] == period
        ), 2)

    @rx.var
    def hansen_loss_before_ha(self) -> float:
        return self._hansen_period_total(hansen.PERIOD_BEFORE_PARCEL)

    @rx.var
    def hansen_loss_after_ha(self) -> float:
        return self._hansen_period_total(hansen.PERIOD_AFTER_PARCEL)

    @rx.var
    def hansen_loss_undivided_ha(self) -> float:
        return self._hansen_period_total(hansen.PERIOD_UNDIVIDED)

    @rx.var
    def hansen_is_split(self) -> bool:
        return bool(self.hansen_split_year)

    @rx.var(cache=True, deps=["active_zone", "hansen_loss_rows", "language"],
            auto_deps=False)
    def hansen_table_rows(self) -> List[Dict[str, Any]]:
        rows = sorted(
            (r for r in self.hansen_loss_rows if r["zone_key"] == self.active_zone),
            key=lambda r: r["year"])
        labels = self._period_labels()
        return [
            {"year": r["year"], "area_ha": round(r["area_ha"], 2),
             "period_label": labels.get(r["period"], r["period"])}
            for r in rows
        ]

    @rx.var(cache=True, deps=["active_zone", "hansen_loss_rows", "language"],
            auto_deps=False)
    def hansen_figure(self) -> go.Figure:
        rows = [r for r in self.hansen_loss_rows if r["zone_key"] == self.active_zone]
        return charts.hansen_figure(rows, getattr(self, "language", "en"))

    @rx.event(background=True)
    async def run_hansen(self):
        from ...services.zones import Zone

        async with self:
            zones_geojson = plain(self.zones_geojson) or {}
            zones_meta = list(self.zones or [])
            start_year = getattr(self, "parcel", {}).get("start_year") or None
            lang = getattr(self, "language", "en")
            self.hansen_running = True
            self.hansen_error = ""
        if not zones_meta or not zones_geojson.get("features"):
            async with self:
                self.hansen_running = False
            return

        geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                      for f in zones_geojson["features"]}
        zone_objs = [
            Zone(key=z["zone_key"], label=z["zone_label"], kind=z["zone_kind"],
                geojson=geom_by_key[z["zone_key"]], area_ha=z["area_ha"])
            for z in zones_meta if z["zone_key"] in geom_by_key
        ]

        try:
            df, gain_ha, prov = hansen.forest_change(
                zone_objs, parcel_year=start_year)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("Hansen forest change failed")
            async with self:
                self.hansen_running = False
                self.hansen_error = get_translations(lang)[
                    "erro_perda_florestal"].format(detail=exc)
            return

        async with self:
            self.hansen_running = False
            self.hansen_has_run = True
            self.hansen_loss_rows = df.to_dict("records") if not df.empty else []
            self.hansen_gain_ha = round(gain_ha, 4)
            self.hansen_split_year = prov.extra.get("split_year") or 0
            self.hansen_provenance = prov.to_dict()

    @rx.var(cache=True, deps=["active_zone", "age_rows"], auto_deps=False)
    def age_row_for_zone(self) -> Dict[str, Any]:
        for r in self.age_rows:
            if r["zone_key"] == self.active_zone:
                return r
        return {}

    @rx.event(background=True)
    async def run_stand_age(self):
        from ...services.zones import Zone

        async with self:
            zones_geojson = plain(self.zones_geojson) or {}
            zones_meta = list(self.zones or [])
            lang = getattr(self, "language", "en")
            self.age_running = True
            self.age_error = ""
        if not zones_meta or not zones_geojson.get("features"):
            async with self:
                self.age_running = False
            return

        geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                      for f in zones_geojson["features"]}
        zone_objs = [
            Zone(key=z["zone_key"], label=z["zone_label"], kind=z["zone_kind"],
                geojson=geom_by_key[z["zone_key"]], area_ha=z["area_ha"])
            for z in zones_meta if z["zone_key"] in geom_by_key
        ]

        try:
            df, prov = hansen.stand_age(zone_objs)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("NTEMS stand age failed")
            async with self:
                self.age_running = False
                self.age_error = get_translations(lang)[
                    "erro_idade_floresta"].format(detail=exc)
            return

        async with self:
            self.age_running = False
            self.age_has_run = True
            self.age_rows = df.to_dict("records") if not df.empty else []
            self.age_provenance = prov.to_dict()
