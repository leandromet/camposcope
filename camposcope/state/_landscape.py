"""Paisagem tab: landscape (fragmentation) metrics, always free, plus the
costly fragment-to-fragment connectivity metric behind its own button.

Same split as Naturametrics' state/_analysis.py: ``run_landscape_metrics``
computes patch/edge/diversity stats for every zone in one shared Earth
Engine round trip (services.landscape_metrics); ``run_connectivity`` is a
separate, explicit action (services.connectivity) because it costs a second
round trip (vectorising) plus a local geometry search, one full pass per
zone rather than one shared reduction.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import plotly.graph_objects as go
import reflex as rx

from ..components import charts
from ..config import mapbiomas as mb
from ..translations import get_translations
from ._proxy import plain

logger = logging.getLogger(__name__)


class LandscapeMixin(rx.State, mixin=True):
    """Landscape metrics + fragment connectivity, for the active property."""

    #: Which classification year the metrics and the on-map patch layer both
    #: read — one control, not two that could disagree (same reasoning as
    #: TransitionsMixin.set_sankey_years keeping the swipe legend in step).
    landscape_year: int = mb.MAPBIOMAS_YEAR_END

    landscape_running: bool = False
    landscape_error: str = ""
    landscape_rows: List[Dict[str, Any]] = []
    #: Full Provenance.to_dict() — see AnalysisMixin.history_provenance. Read
    #: by the exports (workbook/report), not shown inline — same split every
    #: sibling tab already keeps.
    landscape_provenance: Dict[str, Any] = {}

    #: services.connectivity.fragment_connectivity — the costly true
    #: nearest-neighbour distance, opt-in (see module docstring).
    connectivity_running: bool = False
    connectivity_error: str = ""
    connectivity_degraded: bool = False
    connectivity_rows: List[Dict[str, Any]] = []
    connectivity_provenance: Dict[str, Any] = {}

    @rx.event
    def set_landscape_year(self, year: str) -> None:
        self.landscape_year = int(year)
        return self.__class__.mint_analysis_layer

    @rx.var(cache=True, deps=["landscape_rows", "lang"], auto_deps=False)
    def landscape_table_rows(self) -> List[Dict[str, str]]:
        rows = []
        for r in self.landscape_rows:
            rows.append({
                "zone_label": r["zone_label"],
                "area_ha": f'{r["area_ha"]:,.1f}',
                "patches": f'{r["patches"]:,.0f}',
                "patch_density": f'{r["patch_density"]:.2f}',
                "largest_pct": f'{r["largest_patch_pct"]:.1f}%',
                "edge_density": f'{r["edge_density"]:.1f}',
                # Effective mesh size — always available, unlike the true
                # nearest-neighbour distance below (costly enough to sit
                # behind its own button).
                "meff_ha": f'{r["meff_ha"]:,.1f}',
                "shannon": f'{r["shannon"]:.2f}',
                "simpson": f'{r["simpson"]:.2f}',
                "evenness": f'{r["simpson_evenness"]:.2f}',
            })
        return rows

    @rx.var(cache=True, deps=["landscape_rows", "lang"], auto_deps=False)
    def landscape_figure(self) -> go.Figure:
        return charts.landscape_meff_figure(self.landscape_rows, getattr(self, "lang", "pt"))

    @rx.event(background=True)
    async def run_landscape_metrics(self):
        from ..services import landscape_metrics as lm_svc
        from ..services.zones import Zone

        async with self:
            zones_geojson = plain(self.zones_geojson) or {}
            zones_meta = list(self.zones or [])
            year = self.landscape_year
            self.landscape_running = True
            self.landscape_error = ""
        if not zones_meta or not zones_geojson.get("features"):
            async with self:
                self.landscape_running = False
            return

        geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                      for f in zones_geojson["features"]}
        zone_objs = [
            Zone(key=z["zone_key"], label=z["zone_label"], kind=z["zone_kind"],
                geojson=geom_by_key[z["zone_key"]], area_ha=z["area_ha"])
            for z in zones_meta if z["zone_key"] in geom_by_key
        ]

        try:
            summary_df, _hist_df, prov = lm_svc.landscape_metrics(zone_objs, year)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("Landscape metrics failed")
            async with self:
                self.landscape_running = False
                self.landscape_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_paisagem"].format(detail=exc)
            return

        async with self:
            self.landscape_running = False
            self.landscape_rows = summary_df.to_dict("records") if not summary_df.empty else []
            self.landscape_provenance = prov.to_dict()

    # --- fragment connectivity (services.connectivity, on-demand) ------- #

    @rx.var(cache=True)
    def connectivity_has_result(self) -> bool:
        return bool(self.connectivity_rows)

    @rx.var(cache=True, deps=["connectivity_rows"], auto_deps=False)
    def connectivity_table_rows(self) -> List[Dict[str, str]]:
        rows = []
        for r in self.connectivity_rows:
            enn_mean = r.get("enn_mean_m")
            enn_median = r.get("enn_median_m")
            rows.append({
                "zone_label": r["zone_label"],
                "n_fragments": f'{r["n_fragments"]:,.0f}',
                "enn_mean": f'{enn_mean:,.0f}' if enn_mean is not None else "—",
                "enn_median": f'{enn_median:,.0f}' if enn_median is not None else "—",
            })
        return rows

    @rx.event(background=True)
    async def run_connectivity(self):
        from ..services import connectivity as conn_svc
        from ..services.zones import Zone

        async with self:
            zones_geojson = plain(self.zones_geojson) or {}
            zones_meta = list(self.zones or [])
            year = self.landscape_year
            self.connectivity_running = True
            self.connectivity_error = ""
        if not zones_meta or not zones_geojson.get("features"):
            async with self:
                self.connectivity_running = False
            return

        geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                      for f in zones_geojson["features"]}
        zone_objs = [
            Zone(key=z["zone_key"], label=z["zone_label"], kind=z["zone_kind"],
                geojson=geom_by_key[z["zone_key"]], area_ha=z["area_ha"])
            for z in zones_meta if z["zone_key"] in geom_by_key
        ]

        try:
            df, prov = conn_svc.fragment_connectivity(zone_objs, year)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("Fragment connectivity failed")
            async with self:
                self.connectivity_running = False
                self.connectivity_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_connectivity"].format(detail=exc)
            return

        async with self:
            self.connectivity_running = False
            self.connectivity_rows = df.to_dict("records") if not df.empty else []
            self.connectivity_provenance = prov.to_dict()
            self.connectivity_degraded = prov.degraded
