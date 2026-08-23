"""The MapBiomas trajectory analysis (doc/06-ee-layers.md, Phase 3).

Runs as a Reflex **background event handler** so the cadastral card, boundary
and rings are already on screen and interactive while this is still running
(doc/02-architecture.md §4) — the SICAR half completes in ~1 s and paints the
map; this half can take longer and must never block it.

The DataFrame is serialised to a list of dicts for state, because a state var
must be JSON-able (constraint C2 extends the same discipline to pandas: nothing
that cannot cross the WebSocket lives here).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import plotly.graph_objects as go
import reflex as rx

from ..components.charts import land_cover_history_figure
from ..config import mapbiomas as mb

logger = logging.getLogger(__name__)


class AnalysisMixin(rx.State, mixin=True):
    """MapBiomas history: the job, its result, its failure."""

    history_running: bool = False
    history_error: str = ""
    #: Long-format rows: zone_key, zone_label, year, class_id, pixels, area_ha,
    #: class_pt, class_en, color. One fetch serves every zone and every year.
    history_rows: List[Dict[str, Any]] = []
    history_year_start: int = mb.MAPBIOMAS_YEAR_START
    history_year_end: int = mb.MAPBIOMAS_YEAR_END
    history_degraded: bool = False
    history_notes: List[str] = []

    #: Which zone the chart and results tabs describe. Defaults to the property.
    active_zone: str = "imovel"
    #: Hectares vs. percentage share — the toggle the chart reads.
    history_normalise: bool = False

    @rx.var
    def has_history(self) -> bool:
        return bool(self.history_rows)

    @rx.var
    def history_rows_for_zone(self) -> List[Dict[str, Any]]:
        zone = self.active_zone
        return [r for r in self.history_rows if r["zone_key"] == zone]

    @rx.var(cache=True)
    def history_figure(self) -> go.Figure:
        """Built server-side from already-fetched rows — never a fresh EE call.

        Cached so switching UI tabs or toggling something unrelated does not
        rebuild the figure; it is invalidated automatically when
        ``history_rows``, ``active_zone``, ``history_normalise`` or ``lang``
        change, since those are exactly the vars this reads.
        """
        return land_cover_history_figure(
            self.history_rows_for_zone,
            lang=getattr(self, "lang", "pt"),
            normalise=self.history_normalise,
            registration_year=getattr(self, "imovel", {}).get("ano_criacao") or None,
        )

    @rx.event
    def set_active_zone(self, zone_key: str) -> None:
        self.active_zone = zone_key

    @rx.event
    def toggle_history_normalise(self) -> None:
        self.history_normalise = not self.history_normalise

    @rx.event(background=True)
    async def run_history(self):
        """Run the MapBiomas trajectory for the currently selected zones.

        Reset first, run, then either fill the result or the error — never both,
        so the chart cannot show a stale trajectory next to a fresh error.
        """
        async with self:
            zones_geojson = dict(self.zones_geojson or {})
            zones_meta = list(self.zones or [])
            self.history_running = True
            self.history_error = ""
            self.history_rows = []
            self.history_degraded = False
            self.history_notes = []

        if not zones_meta or not zones_geojson.get("features"):
            async with self:
                self.history_running = False
            return

        try:
            from ..services.mapbiomas_history import land_cover_history
            from ..services.zones import Zone

            # Rebuild Zone objects from state — state holds plain dicts (C2),
            # services rebuild what they need.
            geom_by_key = {
                f["properties"]["zone_key"]: f["geometry"]
                for f in zones_geojson["features"]
            }
            zone_objs = [
                Zone(
                    key=z["zone_key"], label=z["zone_label"], kind=z["zone_kind"],
                    geojson=geom_by_key[z["zone_key"]], area_ha=z["area_ha"],
                    radius_m=z.get("radius_m"),
                )
                for z in zones_meta
                if z["zone_key"] in geom_by_key
            ]

            df, prov = land_cover_history(zone_objs)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("MapBiomas history failed")
            async with self:
                self.history_running = False
                self.history_error = (
                    f"Não foi possível calcular a trajetória MapBiomas: {exc}"
                )
            return

        async with self:
            self.history_running = False
            self.history_rows = df.to_dict("records") if not df.empty else []
            self.history_degraded = prov.degraded
            self.history_notes = list(prov.notes)
            if df.empty:
                self.history_error = (
                    "A consulta ao MapBiomas não retornou classes para esta "
                    "geometria."
                )
