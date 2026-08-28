"""ACI transitions and the Sankey diagram (Transições tab)."""

from __future__ import annotations

import logging
from typing import List

import plotly.graph_objects as go
import reflex as rx

from ...state._proxy import plain
from ..config import aafc as mb
from ..services import transitions as tr
from ..translations import get_translations

logger = logging.getLogger(__name__)


class CanadaTransitionsMixin(rx.State, mixin=True):
    """Sankey year selection, transition dicts, figures."""

    sankey_year_a: int = 0
    sankey_year_b: int = 0
    sankey_running: bool = False
    sankey_error: str = ""
    sankey_transitions: dict = {}
    sankey_provenance: dict = {}
    sankey_zone_label: str = ""

    @rx.var(cache=True, deps=["sankey_transitions", "language"], auto_deps=False)
    def sankey_table_rows(self) -> List[dict]:
        lang = getattr(self, "language", "en")
        rows = []
        for src_id, tgt_dict in self.sankey_transitions.items():
            for tgt_id, area in tgt_dict.items():
                rows.append({
                    "src": mb.label(int(src_id), lang),
                    "tgt": mb.label(int(tgt_id), lang),
                    "area_ha": round(float(area), 2),
                })
        rows.sort(key=lambda r: r["area_ha"], reverse=True)
        return rows

    @rx.var
    def sankey_year_left(self) -> int:
        return min(self.sankey_year_a, self.sankey_year_b) if self.sankey_year_a \
            else mb.ACI_NATIONAL_FROM

    @rx.var
    def sankey_year_right(self) -> int:
        return max(self.sankey_year_a, self.sankey_year_b) if self.sankey_year_b \
            else mb.ACI_YEAR_END

    def set_sankey_years(self, year_a: int, year_b: int) -> None:
        self.sankey_year_a, self.sankey_year_b = int(year_a), int(year_b)
        # Keeps the map's swipe comparison in step with the Sankey year
        # picker — one control, not two that could disagree (mirrors the
        # Brazil page's own set_sankey_years).
        return self.__class__.mint_analysis_layer

    def _default_years(self) -> tuple[int, int]:
        if self.sankey_year_a and self.sankey_year_b:
            return self.sankey_year_a, self.sankey_year_b
        return tr.default_year_pair()

    @rx.event(background=True)
    async def run_sankey(self):
        from ..services.zones import PARCEL_ZONE_KEY
        from ...services.zones import Zone

        async with self:
            zones_geojson = plain(self.zones_geojson) or {}
            zones_meta = list(self.zones or [])
            zone_key = self.active_zone
            lang = getattr(self, "language", "en")
            year_a, year_b = self._default_years()
            self.sankey_year_a, self.sankey_year_b = year_a, year_b
            self.sankey_running = True
            self.sankey_error = ""
            self.sankey_transitions = {}
            self.sankey_provenance = {}
        if not zones_geojson.get("features"):
            async with self:
                self.sankey_running = False
            return

        geom_by_key = {f["properties"]["zone_key"]: f["geometry"]
                      for f in zones_geojson["features"]}
        geom = geom_by_key.get(zone_key)
        if geom is None:
            async with self:
                self.sankey_running = False
            return
        zone_obj = Zone(key=zone_key, label=zone_key, kind="property",
                        geojson=geom, area_ha=0.0)

        try:
            out, prov = tr.compute_transitions(
                [zone_obj], year_a, year_b, include_unchanged=True, lang=lang)
        except tr.YearGapError as exc:
            async with self:
                self.sankey_running = False
                self.sankey_error = str(exc)
            return
        except Exception as exc:                       # noqa: BLE001
            logger.exception("ACI Sankey failed")
            async with self:
                self.sankey_running = False
                self.sankey_error = get_translations(lang)[
                    "erro_transicao"].format(detail=exc)
            return

        async with self:
            self.sankey_running = False
            self.sankey_transitions = {
                str(src): {str(tgt): area for tgt, area in tgts.items()}
                for src, tgts in out.get(zone_key, {}).items()
            }
            self.sankey_provenance = prov.to_dict()
            self.sankey_zone_label = next(
                (z["zone_label"] for z in zones_meta if z["zone_key"] == zone_key),
                zone_key)
        # sankey_year_a/b start at 0/0 (unlike the Brazil page, which has
        # concrete class defaults) and only become real years once
        # _default_years() runs above — so the map's swipe layer cannot
        # have been minted for them before now. Chaining here is what
        # actually shows the two-year comparison the first time this tab
        # runs, not just on a later explicit year change.
        return self.__class__.mint_analysis_layer

    @rx.var(cache=True,
            deps=["sankey_transitions", "sankey_year_a", "sankey_year_b",
                  "language"],
            auto_deps=False)
    def sankey_figure(self) -> go.Figure:
        transitions = {
            int(src): {int(tgt): area for tgt, area in tgts.items()}
            for src, tgts in self.sankey_transitions.items()
        }
        fig = tr.sankey_figure(
            transitions, self.sankey_year_a or mb.ACI_NATIONAL_FROM,
            self.sankey_year_b or mb.ACI_YEAR_END,
            lang=getattr(self, "language", "en"))
        return fig or go.Figure()
