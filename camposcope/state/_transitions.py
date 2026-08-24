"""Transitions and the Sankey diagrams (doc/07-transitions.md).

Two figures share one computation: the multi-stage default set is
before · registration · now (services/transitions.py::default_multi_stage_years),
and the two-stage view is just its first and last year unless the user picks a
different pair. Both run as background handlers so the UI stays responsive —
each pair costs one Earth Engine round trip (doc/06-ee-layers.md §1).
"""

from __future__ import annotations

import logging
from typing import List

import plotly.graph_objects as go
import reflex as rx

from ..config import mapbiomas as mb
from ..translations import get_translations

logger = logging.getLogger(__name__)


class TransitionsMixin(rx.State, mixin=True):
    """Sankey year selection, transition dicts, figures."""

    sankey_year_a: int = mb.MAPBIOMAS_YEAR_START
    sankey_year_b: int = mb.MAPBIOMAS_YEAR_END
    sankey_running: bool = False
    sankey_error: str = ""
    #: {src_class_id_str: {tgt_class_id_str: area_ha}} for the active zone —
    #: kept as state (not just the figure) so the transition table can read it
    #: too (doc/07-transitions.md §5: the table stays available alongside
    #: every Sankey).
    sankey_transitions: dict = {}

    multi_stage_years: List[int] = []
    multi_stage_running: bool = False
    multi_stage_error: str = ""

    @rx.var(cache=True, deps=["sankey_transitions", "lang"], auto_deps=False)
    def sankey_table_rows(self) -> List[dict]:
        """The transition dict flattened for a sortable table — the figure is
        for seeing the shape, the table is for making a claim
        (doc/07-transitions.md §5). Explicit ``deps`` for the same reason as
        ``ImovelMixin.disclosure``: ``lang`` is read via ``getattr``, which
        Reflex's auto-dependency scan cannot see."""
        rows = []
        for src_id, tgt_dict in self.sankey_transitions.items():
            for tgt_id, area in tgt_dict.items():
                rows.append({
                    "src": mb.label(int(src_id), getattr(self, "lang", "pt")),
                    "tgt": mb.label(int(tgt_id), getattr(self, "lang", "pt")),
                    "area_ha": round(float(area), 2),
                })
        rows.sort(key=lambda r: r["area_ha"], reverse=True)
        return rows

    @rx.var
    def sankey_year_left(self) -> int:
        """Older of the two selected years — the map's swipe legend reads
        this rather than doing min/max in the component, since Var has
        neither method."""
        return min(self.sankey_year_a, self.sankey_year_b)

    @rx.var
    def sankey_year_right(self) -> int:
        return max(self.sankey_year_a, self.sankey_year_b)

    @rx.event
    def set_sankey_years(self, year_a: int, year_b: int) -> None:
        self.sankey_year_a, self.sankey_year_b = int(year_a), int(year_b)
        # Keeps the map's swipe comparison in step with the Sankey year
        # picker — one control, not two that could disagree.
        return self.__class__.mint_analysis_layer

    @rx.event(background=True)
    async def run_sankey(self):
        """Two-stage Sankey for the active zone, current year pair."""
        from ..services import transitions as tr
        from ..services.zones import Zone

        async with self:
            zones_geojson = dict(self.zones_geojson or {})
            zone_key = self.active_zone
            year_a, year_b = self.sankey_year_a, self.sankey_year_b
            self.sankey_running = True
            self.sankey_error = ""
            self.sankey_transitions = {}
        if not zones_geojson.get("features"):
            async with self:
                self.sankey_running = False
            return

        geom_by_key = {
            f["properties"]["zone_key"]: f["geometry"]
            for f in zones_geojson["features"]
        }
        geom = geom_by_key.get(zone_key)
        if geom is None:
            async with self:
                self.sankey_running = False
            return
        zone_obj = Zone(key=zone_key, label=zone_key, kind="property",
                        geojson=geom, area_ha=0.0)

        try:
            out, _prov = tr.compute_transitions(
                [zone_obj], year_a, year_b, include_unchanged=True
            )
        except tr.YearGapError as exc:
            async with self:
                self.sankey_running = False
                self.sankey_error = str(exc)
            return
        except Exception as exc:                       # noqa: BLE001
            logger.exception("Sankey failed")
            async with self:
                self.sankey_running = False
                self.sankey_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_transicao"].format(detail=exc)
            return

        async with self:
            self.sankey_running = False
            # str keys: state vars are JSON, and dict keys travel as strings.
            self.sankey_transitions = {
                str(src): {str(tgt): area for tgt, area in tgts.items()}
                for src, tgts in out.get(zone_key, {}).items()
            }

    @rx.var(cache=True, deps=["sankey_transitions", "sankey_year_a", "sankey_year_b", "lang"],
            auto_deps=False)
    def sankey_figure(self) -> go.Figure:
        from ..services import transitions as tr

        transitions = {
            int(src): {int(tgt): area for tgt, area in tgts.items()}
            for src, tgts in self.sankey_transitions.items()
        }
        fig = tr.sankey_figure(
            transitions, self.sankey_year_a, self.sankey_year_b,
            lang=getattr(self, "lang", "pt"),
        )
        return fig or go.Figure()

    @rx.event(background=True)
    async def run_multi_stage_sankey(self):
        """Multi-stage Sankey: before · registration · now, for the active
        zone (doc/07-transitions.md §3.2) — the default that frames the
        property's own history around its own cadastral event.
        """
        from ..services import transitions as tr
        from ..services.zones import Zone

        async with self:
            zones_geojson = dict(self.zones_geojson or {})
            zone_key = self.active_zone
            registration_year = (getattr(self, "imovel", {}).get("ano_criacao")
                                 or None)
            lang = getattr(self, "lang", "pt")
            self.multi_stage_running = True
            self.multi_stage_error = ""
        if not zones_geojson.get("features"):
            async with self:
                self.multi_stage_running = False
            return

        geom_by_key = {
            f["properties"]["zone_key"]: f["geometry"]
            for f in zones_geojson["features"]
        }
        geom = geom_by_key.get(zone_key)
        if geom is None:
            async with self:
                self.multi_stage_running = False
            return
        zone_obj = Zone(key=zone_key, label=zone_key, kind="property",
                        geojson=geom, area_ha=0.0)

        years = tr.default_multi_stage_years(
            mb.MAPBIOMAS_YEAR_START, registration_year, mb.MAPBIOMAS_YEAR_END
        )

        try:
            stages = []
            for a, b in zip(years[:-1], years[1:]):
                out, _prov = tr.compute_transitions(
                    [zone_obj], a, b, include_unchanged=True,
                    enforce_min_gap=False,   # the default set is curated, not typed
                )
                stages.append((a, b, out.get(zone_key, {})))
        except Exception as exc:                       # noqa: BLE001
            logger.exception("Multi-stage Sankey failed")
            async with self:
                self.multi_stage_running = False
                self.multi_stage_error = get_translations(lang)[
                    "erro_transicoes_multi"
                ].format(detail=exc)
            return

        fig = tr.multi_stage_sankey_figure(stages, lang=lang)

        async with self:
            self.multi_stage_running = False
            self.multi_stage_years = years
            self._multi_stage_stages = stages
            if fig is None:
                self.multi_stage_error = get_translations(lang)[
                    "erro_transicao_dados_insuficientes"
                ]

    #: Not a state var (figures built from it are cached below) — holds the
    #: raw stage data between the background handler and the computed var.
    _multi_stage_stages: list = []

    @rx.var(cache=True, deps=["multi_stage_years", "lang"], auto_deps=False)
    def multi_stage_figure(self) -> go.Figure:
        from ..services import transitions as tr

        stages = getattr(self, "_multi_stage_stages", [])
        fig = tr.multi_stage_sankey_figure(stages, lang=getattr(self, "lang", "pt"))
        return fig or go.Figure()
