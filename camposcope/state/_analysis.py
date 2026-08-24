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
from ..translations import get_translations

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
    #: Which year's class breakdown the Cobertura table shows, and — via
    #: LayersMixin.mapbiomas_map_layers — which year's MapBiomas tile draws on
    #: the map while this tab is active. One selector drives both, so the
    #: table and the map never show two different years at once.
    mapbiomas_layer_year: int = mb.MAPBIOMAS_YEAR_END

    @rx.var
    def has_history(self) -> bool:
        return bool(self.history_rows)

    @rx.var
    def history_rows_for_zone(self) -> List[Dict[str, Any]]:
        zone = self.active_zone
        return [r for r in self.history_rows if r["zone_key"] == zone]

    @rx.var
    def history_table_rows(self) -> List[Dict[str, Any]]:
        """The active zone's class breakdown for ``mapbiomas_layer_year``,
        largest first — the compact table shown beside the trajectory chart
        (not one row per year: forty years of every class would not fit)."""
        year = self.mapbiomas_layer_year
        class_key = "class_en" if getattr(self, "lang", "pt") == "en" else "class_pt"
        rows = [r for r in self.history_rows_for_zone if r["year"] == year]
        total = sum(r["area_ha"] for r in rows) or 1.0
        out = [
            {
                "class_label": r[class_key], "color": r["color"],
                "area_ha": round(r["area_ha"], 2),
                "area_pct": round(100.0 * r["area_ha"] / total, 1),
            }
            for r in rows
        ]
        out.sort(key=lambda r: r["area_ha"], reverse=True)
        return out

    @rx.event
    def set_mapbiomas_layer_year(self, year: str) -> None:
        # rx.select always passes a string (see UIMixin.set_lang for the same
        # rule applied to rx.segmented_control).
        self.mapbiomas_layer_year = int(year)
        return self.__class__.mint_analysis_layer

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
                self.history_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_trajetoria_mapbiomas"].format(detail=exc)
            return

        async with self:
            self.history_running = False
            self.history_rows = df.to_dict("records") if not df.empty else []
            self.history_degraded = prov.degraded
            self.history_notes = list(prov.notes)
            if df.empty:
                self.history_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_mapbiomas_sem_classes"]


class ForestChangeMixin(rx.State, mixin=True):
    """Hansen forest change: dated loss split at registration, undated gain
    kept separate (doc/04-data-sources.md §3)."""

    #: Which turning point the Floresta map layer shows loss *since* —
    #: "2008" (the Forest Code's own reference year) or "registro" (this
    #: property's CAR registration). Not an arbitrary year picker: these two
    #: dates are the ones that actually matter here (doc/04 §3).
    hansen_layer_mode: str = "2008"

    @rx.event
    def set_hansen_layer_mode(self, mode: str | list[str]) -> None:
        # rx.segmented_control passes str | list[str] (see UIMixin.set_lang).
        value = mode[0] if isinstance(mode, list) else mode
        self.hansen_layer_mode = value if value in ("2008", "registro") else "2008"
        return self.__class__.mint_analysis_layer

    hansen_running: bool = False
    hansen_error: str = ""
    hansen_loss_rows: List[Dict[str, Any]] = []
    hansen_gain_ha: float = 0.0
    hansen_has_run: bool = False

    #: One colour per period — amber/red/dark-red reading as "further from
    #: today", not a severity scale (loss before 2008 is not "worse").
    _PERIOD_COLOR = {
        "ate_2008": "#f5a524",
        "2008_ate_registro": "#e5484d",
        "apos_registro": "#8b1a1a",
    }
    _PERIOD_LABEL_PT = {
        "ate_2008": "Até 2008",
        "2008_ate_registro": "2008 até o registro",
        "apos_registro": "Depois do registro",
    }
    _PERIOD_LABEL_EN = {
        "ate_2008": "Up to 2008",
        "2008_ate_registro": "2008 to registration",
        "apos_registro": "After registration",
    }

    def _period_labels(self) -> Dict[str, str]:
        return (self._PERIOD_LABEL_EN if getattr(self, "lang", "pt") == "en"
               else self._PERIOD_LABEL_PT)

    def _hansen_period_total(self, period: str) -> float:
        return round(sum(
            r["area_ha"] for r in self.hansen_loss_rows
            if r["zone_key"] == self.active_zone and r["period"] == period
        ), 2)

    @rx.var
    def hansen_loss_up_to_2008_ha(self) -> float:
        return self._hansen_period_total("ate_2008")

    @rx.var
    def hansen_loss_2008_to_registration_ha(self) -> float:
        return self._hansen_period_total("2008_ate_registro")

    @rx.var
    def hansen_loss_after_registration_ha(self) -> float:
        return self._hansen_period_total("apos_registro")

    @rx.var
    def hansen_table_rows(self) -> List[Dict[str, Any]]:
        rows = sorted(
            (r for r in self.hansen_loss_rows if r["zone_key"] == self.active_zone),
            key=lambda r: r["year"],
        )
        labels = self._period_labels()
        return [
            {"year": r["year"], "area_ha": round(r["area_ha"], 2),
             "period_label": labels.get(r["period"], r["period"])}
            for r in rows
        ]

    @rx.var(cache=True)
    def hansen_figure(self) -> go.Figure:
        lang = getattr(self, "lang", "pt")
        rows = [r for r in self.hansen_loss_rows if r["zone_key"] == self.active_zone]
        labels = self._period_labels()
        fig = go.Figure()
        if not rows:
            fig.add_annotation(
                text="Sem dados" if lang == "pt" else "No data",
                showarrow=False, font=dict(size=13, color="#888"),
            )
        else:
            for period in ("ate_2008", "2008_ate_registro", "apos_registro"):
                bucket = [r for r in rows if r["period"] == period]
                if not bucket:
                    continue
                fig.add_bar(
                    x=[r["year"] for r in bucket], y=[r["area_ha"] for r in bucket],
                    name=labels[period],
                    marker_color=self._PERIOD_COLOR[period],
                )
        fig.update_layout(
            barmode="stack", template="plotly_white",
            margin=dict(l=48, r=8, t=8, b=36), height=260,
            legend=dict(orientation="h", yanchor="top", y=-0.22, x=0,
                       font=dict(size=9)),
            xaxis=dict(title=None, tickmode="linear", dtick=2),
            yaxis=dict(title="Perda (ha)" if lang == "pt" else "Loss (ha)"),
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
                self.hansen_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_perda_florestal"].format(detail=exc)
            return

        async with self:
            self.hansen_running = False
            self.hansen_has_run = True
            self.hansen_loss_rows = df.to_dict("records") if not df.empty else []
            self.hansen_gain_ha = round(gain_ha, 4)


class BiomassMixin(rx.State, mixin=True):
    """ESA CCI Above-Ground Biomass — ten snapshots, gaps drawn as gaps."""

    #: Which snapshot the Biomassa map layer shows. Defaults to the most
    #: recent — the "current state" reading is usually the one someone wants
    #: first; the on-map control offers the other nine.
    biomass_layer_year: int = 2022

    biomass_running: bool = False
    biomass_error: str = ""
    biomass_rows: List[Dict[str, Any]] = []

    @rx.event
    def set_biomass_layer_year(self, year: str) -> None:
        self.biomass_layer_year = int(year)
        return self.__class__.mint_analysis_layer

    @rx.var
    def biomass_table_rows(self) -> List[Dict[str, Any]]:
        """All ten snapshots for the active zone — compact enough (unlike
        Cobertura's per-class table) to list in full rather than one year."""
        rows = sorted(
            (r for r in self.biomass_rows if r["zone_key"] == self.active_zone),
            key=lambda r: r["year"],
        )
        return [
            {"year": r["year"], "agb_mean_mgha": round(r["agb_mean_mgha"], 1),
             "total_biomass_mg": round(r["total_biomass_mg"], 0)}
            for r in rows
        ]

    @rx.var(cache=True)
    def biomass_figure(self) -> go.Figure:
        lang = getattr(self, "lang", "pt")
        rows = sorted(
            (r for r in self.biomass_rows if r["zone_key"] == self.active_zone),
            key=lambda r: r["year"],
        )
        fig = go.Figure()
        if not rows:
            fig.add_annotation(
                text="Sem dados" if lang == "pt" else "No data",
                showarrow=False, font=dict(size=13, color="#888"),
            )
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
            yaxis=dict(title="Biomassa (Mg/ha)" if lang == "pt" else "Biomass (Mg/ha)"),
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
                self.biomass_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_biomassa"].format(detail=exc)
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
                self.spot_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_spot_cobertura"].format(detail=exc)
            return

        async with self:
            self.spot_running = False
            self.spot_summary = summary


class ValidacaoMixin(rx.State, mixin=True):
    """SPOT/IBGE vs MapBiomas comparison — a quality-control check against
    reference data, not a new analysis of the property (doc/03-roadmap.md
    Phase 5 addendum). Two modes, one swipe divider on the map either way:

    ``spot_2008``  SPOT imagery (left) vs MapBiomas 2008 classification (right)
    ``ibge_2022``  IBGE Vegetação 2022 (left) vs MapBiomas 2022 (right), plus
                   the bucket-matrix numbers below — IBGE has no imagery to
                   look at, only another classification to check against.
    """

    validacao_mode: str = "spot_2008"
    #: Which SPOT band combination the spot_2008 pairing shows — true colour
    #: or the false-colour near-infrared composite (doc/04-data-sources.md §6:
    #: NIR-in-red is what makes 2008 vegetation legible against pasture).
    #: Meaningless in ibge_2022 mode, where there is no SPOT side to pick.
    spot_band_mode: str = "visual"

    validacao_running: bool = False
    validacao_error: str = ""
    #: Only meaningful for ibge_2022 — spot_2008 is visual-only, nothing to
    #: tabulate (doc/12-spot-2008.md: SPOT is imagery, not a classification).
    validacao_matrix: Dict[str, Any] = {}

    @rx.event
    def set_validacao_mode(self, mode: str | list[str]):
        # Plain event, not background — see set_hansen_layer_mode for the
        # same shape. A background handler mutating self.xxx directly outside
        # `async with self:` raises ImmutableStateError; a plain one just
        # writes and returns the next event to chain, which is all this
        # needs (mint_analysis_layer is itself background).
        value = mode[0] if isinstance(mode, list) else mode
        self.validacao_mode = value if value in ("spot_2008", "ibge_2022") else "spot_2008"
        return self.__class__.mint_analysis_layer

    @rx.event
    def set_spot_band_mode(self, mode: str | list[str]):
        value = mode[0] if isinstance(mode, list) else mode
        self.spot_band_mode = value if value in ("visual", "analytic") else "visual"
        return self.__class__.mint_analysis_layer

    @rx.event(background=True)
    async def run_validacao(self):
        """Compute the IBGE-vs-MapBiomas bucket matrix for the active zone.
        A no-op in spot_2008 mode — see class docstring."""
        from ..services import ibge_vegetation as iv
        from ..services.zones import Zone

        async with self:
            if self.validacao_mode != "ibge_2022":
                return
            zones_geojson = dict(self.zones_geojson or {})
            zones_meta = list(self.zones or [])
            zone_key = self.active_zone
            self.validacao_running = True
            self.validacao_error = ""

        if not zones_meta or not zones_geojson.get("features"):
            async with self:
                self.validacao_running = False
            return

        geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                      for f in zones_geojson["features"]}
        zone_objs = [
            Zone(key=z["zone_key"], label=z["zone_label"], kind=z["zone_kind"],
                geojson=geom_by_key[z["zone_key"]], area_ha=z["area_ha"])
            for z in zones_meta if z["zone_key"] in geom_by_key
        ]

        try:
            df, _prov = iv.mapbiomas_comparison(zone_objs)
            matrix = iv.bucket_matrix(df, zone_key)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("IBGE/MapBiomas comparison failed")
            async with self:
                self.validacao_running = False
                self.validacao_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_comparacao_ibge"].format(detail=exc)
            return

        async with self:
            self.validacao_running = False
            self.validacao_matrix = matrix
