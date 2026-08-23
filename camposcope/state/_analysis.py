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


class ForestChangeMixin(rx.State, mixin=True):
    """Hansen forest change: dated loss split at registration, undated gain
    kept separate (doc/04-data-sources.md §3)."""

    hansen_running: bool = False
    hansen_error: str = ""
    hansen_loss_rows: List[Dict[str, Any]] = []
    hansen_gain_ha: float = 0.0
    hansen_has_run: bool = False

    @rx.var
    def hansen_loss_before_ha(self) -> float:
        return round(sum(
            r["area_ha"] for r in self.hansen_loss_rows
            if r["zone_key"] == self.active_zone and r["before_registration"]
        ), 2)

    @rx.var
    def hansen_loss_after_ha(self) -> float:
        return round(sum(
            r["area_ha"] for r in self.hansen_loss_rows
            if r["zone_key"] == self.active_zone and not r["before_registration"]
        ), 2)

    @rx.var(cache=True)
    def hansen_figure(self) -> go.Figure:
        rows = [r for r in self.hansen_loss_rows if r["zone_key"] == self.active_zone]
        fig = go.Figure()
        if not rows:
            fig.add_annotation(text="Sem dados", showarrow=False,
                              font=dict(size=13, color="#888"))
        else:
            before = [r for r in rows if r["before_registration"]]
            after = [r for r in rows if not r["before_registration"]]
            if before:
                fig.add_bar(x=[r["year"] for r in before],
                           y=[r["area_ha"] for r in before],
                           name="Antes do registro", marker_color="#f5a524")
            if after:
                fig.add_bar(x=[r["year"] for r in after],
                           y=[r["area_ha"] for r in after],
                           name="Depois do registro", marker_color="#d4271e")
        fig.update_layout(
            barmode="stack", template="plotly_white",
            margin=dict(l=48, r=8, t=8, b=36), height=300,
            legend=dict(orientation="h", yanchor="top", y=-0.2, x=0,
                       font=dict(size=10)),
            xaxis=dict(title=None, tickmode="linear", dtick=2),
            yaxis=dict(title="Perda (ha)"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    @rx.event(background=True)
    async def run_hansen(self):
        from ..services import hansen
        from ..services.zones import Zone

        async with self:
            zones_geojson = dict(self.zones_geojson or {})
            zones_meta = list(self.zones or [])
            registration_year = (getattr(self, "imovel", {}).get("ano_criacao")
                                 or None)
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
            df, gain_ha, _prov = hansen.forest_change(
                zone_objs, registration_year=registration_year
            )
        except Exception as exc:                       # noqa: BLE001
            logger.exception("Hansen forest change failed")
            async with self:
                self.hansen_running = False
                self.hansen_error = f"Não foi possível calcular a perda florestal: {exc}"
            return

        async with self:
            self.hansen_running = False
            self.hansen_has_run = True
            self.hansen_loss_rows = df.to_dict("records") if not df.empty else []
            self.hansen_gain_ha = round(gain_ha, 4)


class BiomassMixin(rx.State, mixin=True):
    """ESA CCI Above-Ground Biomass — ten snapshots, gaps drawn as gaps."""

    biomass_running: bool = False
    biomass_error: str = ""
    biomass_rows: List[Dict[str, Any]] = []

    @rx.var(cache=True)
    def biomass_figure(self) -> go.Figure:
        rows = sorted(
            (r for r in self.biomass_rows if r["zone_key"] == self.active_zone),
            key=lambda r: r["year"],
        )
        fig = go.Figure()
        if not rows:
            fig.add_annotation(text="Sem dados", showarrow=False,
                              font=dict(size=13, color="#888"))
        else:
            # The series has a real gap (2011-2014 missing) — connectgaps=False
            # draws it as a gap instead of interpolating across it.
            fig.add_scatter(
                x=[r["year"] for r in rows], y=[r["agb_mean_mgha"] for r in rows],
                mode="markers+lines", connectgaps=False,
                line=dict(color="#1f8d49"), marker=dict(size=8),
                hovertemplate="%{x}: %{y:.1f} Mg/ha<extra></extra>",
            )
        fig.update_layout(
            template="plotly_white", margin=dict(l=48, r=8, t=8, b=28), height=300,
            xaxis=dict(title=None, tickmode="linear", dtick=2),
            yaxis=dict(title="Biomassa (Mg/ha)"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        return fig

    @rx.event(background=True)
    async def run_biomass(self):
        from ..services import biomass as biomass_svc
        from ..services.zones import Zone

        async with self:
            zones_geojson = dict(self.zones_geojson or {})
            zones_meta = list(self.zones or [])
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
            df, _prov = biomass_svc.above_ground_biomass(zone_objs)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("Biomass failed")
            async with self:
                self.biomass_running = False
                self.biomass_error = f"Não foi possível calcular a biomassa: {exc}"
            return

        async with self:
            self.biomass_running = False
            self.biomass_rows = df.to_dict("records") if not df.empty else []


class SpotCoverageMixin(rx.State, mixin=True):
    """SPOT 2008 coverage and acquisition dates for the active zone
    (doc/12-spot-2008.md §3) — never a classification, only what was
    photographed and when.
    """

    spot_running: bool = False
    spot_error: str = ""
    spot_summary: Dict[str, Any] = {}

    @rx.event(background=True)
    async def run_spot_coverage(self):
        from ..services import spot
        from ..services.zones import Zone

        async with self:
            zones_geojson = dict(self.zones_geojson or {})
            zone_key = self.active_zone
            self.spot_running = True
            self.spot_error = ""
            self.spot_summary = {}
        if not zones_geojson.get("features"):
            async with self:
                self.spot_running = False
            return

        geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                      for f in zones_geojson["features"]}
        geom = geom_by_key.get(zone_key)
        if geom is None:
            async with self:
                self.spot_running = False
            return

        try:
            summary, _prov = spot.coverage(geom)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("SPOT coverage failed")
            async with self:
                self.spot_running = False
                self.spot_error = f"Não foi possível verificar a cobertura SPOT: {exc}"
            return

        async with self:
            self.spot_running = False
            self.spot_summary = summary
