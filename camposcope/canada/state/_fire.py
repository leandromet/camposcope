"""Burned area — the Fogo tab.

Two independent sources, never merged into one number — see
``canada/services/fire.py``'s module docstring for why a blended total would
misrepresent both:

MODIS MCD64A1
    A purpose-built daily burn product, national, 2001–2025, 500 m. The
    default: it is the longer record and the one with no land-cover
    classifier's blind spots.
ACI class 60 ("Forest Fire and Burnt Area")
    The crop inventory's own burnt-area class, 30 m — seven times finer, and
    already sitting in ``history_rows`` from the Cobertura fetch, so reading it
    here costs no second Earth Engine call. Shorter record (2009–2025,
    national from 2011) and it is a land-cover class, not a burn product: it
    can miss a fire MODIS catches, the same way it can catch one at finer
    detail than MODIS resolves.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import plotly.graph_objects as go
import reflex as rx

from ...state._proxy import plain
from ..components import charts
from ..translations import get_translations

logger = logging.getLogger(__name__)


class CanadaFireMixin(rx.State, mixin=True):
    fire_running: bool = False
    fire_error: str = ""
    fire_rows: List[Dict[str, Any]] = []
    fire_table_rows: List[Dict[str, Any]] = []
    fire_provenance: Dict[str, Any] = {}

    #: "modis" | "aci" — which source the tab and the map layer show. The map
    #: layer year for "aci" is the Cobertura tab's own ``aci_layer_year``, not
    #: a second year picker: it is literally the same yearly classification,
    #: just filtered to one class, so one control is enough.
    fire_source: str = "modis"

    def set_fire_source(self, source: str | list[str]) -> None:
        value = source[0] if isinstance(source, list) else source
        self.fire_source = value if value in ("modis", "aci") else "modis"
        return self.__class__.mint_analysis_layer

    @rx.var(cache=True, deps=["fire_rows", "active_zone", "language"],
            auto_deps=False)
    def fire_figure(self) -> go.Figure:
        rows = [r for r in self.fire_rows if r["zone_key"] == self.active_zone]
        return charts.fire_figure(rows, getattr(self, "language", "en"))

    # --- ACI class 60, read from the Cobertura fetch already in state ----- #

    @rx.var(cache=True,
            deps=["history_rows", "active_zone", "zones", "language"],
            auto_deps=False)
    def aci_burn_rows_for_zone(self) -> List[Dict[str, Any]]:
        """Per-year burnt share of the active zone, from ACI class 60 — no
        Earth Engine call, just a filter over ``history_rows``.

        **Dense over the whole ACI record, not just the years a fire was
        detected.** ``aci_burn_rows`` only returns rows for years class 60
        actually showed up — one row for a parcel with a single 2023 fire.
        Plotted as-is, a bar chart with one category on its x-axis renders
        that one bar stretched across the whole plot area, which reads as
        "constant fire" rather than "one year out of seventeen." Filling
        every other year in with an explicit 0 %, the same way
        ``fire.fire_analysis``'s ``annual_df`` already does for the MODIS
        chart, is what actually fixed the reported bug.

        ``getattr`` for ``history_rows``/``zones``: both live on sibling
        mixins (``CanadaCoverMixin``/``CanadaParcelMixin``), invisible to a
        static checker looking only at this class — same pattern as every
        other cross-mixin read in this app (see e.g.
        ``camposcope/state/_imovel.py::ImovelMixin.disclosure`` for the fuller
        explanation of why ``deps`` must be explicit here too).
        """
        from ..config import aafc as _aafc
        from ..services.fire import aci_burn_rows

        history = getattr(self, "history_rows", [])
        zone_key = self.active_zone
        zone_area = next(
            (z["area_ha"] for z in getattr(self, "zones", [])
             if z["zone_key"] == zone_key), 0.0)
        if not zone_area:
            return []
        burnt_ha_by_year = {
            r["year"]: r["area_ha"]
            for r in aci_burn_rows(history) if r["zone_key"] == zone_key
        }
        return [
            {"year": year,
             "burnt_ha": round(burnt_ha_by_year.get(year, 0.0), 2),
             "burnt_pct": round(
                 100.0 * burnt_ha_by_year.get(year, 0.0) / zone_area, 2)}
            for year in _aafc.ACI_YEARS
        ]

    @rx.var(cache=True, deps=["history_rows", "active_zone", "zones"],
            auto_deps=False)
    def aci_burn_years_detected(self) -> int:
        # aci_burn_rows_for_zone is dense (every ACI year, 0 filled in) so the
        # chart never renders a lone bar as if it filled the whole record —
        # counting every entry here would always equal len(ACI_YEARS), so a
        # detected burn is a nonzero share, not mere row presence.
        return sum(1 for r in self.aci_burn_rows_for_zone if r["burnt_ha"] > 0)

    @rx.var(cache=True, deps=["history_rows", "active_zone", "zones"],
            auto_deps=False)
    def aci_burn_last_year(self) -> int:
        years = [r["year"] for r in self.aci_burn_rows_for_zone
                if r["burnt_ha"] > 0]
        return max(years) if years else 0

    @rx.var(cache=True,
            deps=["history_rows", "active_zone", "zones", "language"],
            auto_deps=False)
    def aci_burn_figure(self) -> go.Figure:
        return charts.aci_burn_figure(self.aci_burn_rows_for_zone,
                                      getattr(self, "language", "en"))

    @rx.event(background=True)
    async def run_fire(self):
        from ..services.fire import fire_analysis
        from ...services.zones import Zone

        async with self:
            zones_geojson = plain(self.zones_geojson) or {}
            zones_meta = list(self.zones or [])
            active_zone = self.active_zone
            lang = getattr(self, "language", "en")
            self.fire_running = True
            self.fire_error = ""
        if not zones_meta or not zones_geojson.get("features"):
            async with self:
                self.fire_running = False
            return

        geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                      for f in zones_geojson["features"]}
        zone_objs = [
            Zone(key=z["zone_key"], label=z["zone_label"], kind=z["zone_kind"],
                geojson=geom_by_key[z["zone_key"]], area_ha=z["area_ha"])
            for z in zones_meta if z["zone_key"] in geom_by_key
        ]

        try:
            summary_df, annual_df, prov = fire_analysis(zone_objs)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("MODIS burned-area failed")
            async with self:
                self.fire_running = False
                self.fire_error = get_translations(lang)[
                    "erro_fogo"].format(detail=exc)
            return

        summary_rows = summary_df.to_dict("records") if not summary_df.empty else []
        active_summary = [r for r in summary_rows if r["zone_key"] == active_zone]

        async with self:
            self.fire_running = False
            self.fire_rows = annual_df.to_dict("records") if not annual_df.empty \
                else []
            self.fire_table_rows = summary_rows
            self.fire_provenance = prov.to_dict()
