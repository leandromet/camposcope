"""GBIF species-per-zone analysis — the GBIF tab's "Calcular" button.

Its own mixin rather than more of ``_layers.py``: the map layer there is
purely declarative (``LayersMixin.gbif_vectors``, no network call from
Python), while this is a real analysis run — a background event with its own
busy/error state, the same shape ``floresta``/``fogo``/``paisagem`` already
use for their own "Calcular" buttons.

Typed rows (``pydantic.BaseModel``), not plain dicts: every other table in
this app is a flat ``list[dict]`` and Reflex handles that fine, but each zone
row here nests two further lists (species, kingdoms) — Reflex's ``rx.foreach``
cannot iterate a nested list living inside an untyped dict value, only inside
a typed model field. Naturametrics hit the same wall for the same reason (see
its ``state/_gbif.py::GbifBufferRow``).
"""

from __future__ import annotations

import logging
from typing import List

import reflex as rx
from pydantic import BaseModel

from ..config.settings import GBIF_SPECIES_TABLE_LIMIT
from ..services import gbif_species
from ._proxy import plain

logger = logging.getLogger(__name__)


class GbifSpeciesRow(BaseModel):
    name: str
    count: int
    count_label: str


class GbifKingdomRow(BaseModel):
    name: str
    count: int


class GbifZoneRow(BaseModel):
    """One zone's biodiversity summary — the cumulative area out to it (see
    ``services/gbif_species.py`` for why cumulative, not per-ring)."""

    zone_key: str
    zone_label: str
    total: int
    total_label: str
    richness: int
    richness_label: str
    #: Capped at GBIF_SPECIES_TABLE_LIMIT — the only list rendered, and (with
    #: no export to spare the rest for, unlike Naturametrics) the only one
    #: kept at all.
    species_top: List[GbifSpeciesRow]
    kingdoms: List[GbifKingdomRow]
    error: str


class GbifMixin(rx.State, mixin=True):
    """Species recorded in GBIF, per zone."""

    gbif_zone_rows: List[GbifZoneRow] = []
    gbif_running: bool = False
    gbif_error: str = ""

    @rx.event(background=True)
    async def run_gbif_species(self):
        """Fan out one GBIF facet query per zone (services/gbif_species.py).

        Independent of the on-map GBIF layer (state/_layers.py::gbif_vectors),
        which needs no run — this is the aggregate count/species-list side,
        the same "chart/table behind its own button" split every other tab
        uses for a real network cost.
        """
        async with self:
            if not getattr(self, "has_imovel", False):
                return
            zones_geojson = plain(getattr(self, "zones_geojson", {})) or {}
            self.gbif_running = True
            self.gbif_error = ""

        import asyncio

        loop = asyncio.get_running_loop()
        try:
            rows = await loop.run_in_executor(
                None, gbif_species.species_by_zone, zones_geojson
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("GBIF species-per-zone analysis failed")
            async with self:
                self.gbif_running = False
                self.gbif_error = str(exc)
            return

        async with self:
            self.gbif_running = False
            # The first non-empty error is reported rather than all four:
            # they share one upstream, so four failures are one failure.
            self.gbif_error = next((r.error for r in rows if r.error), "")
            self.gbif_zone_rows = [
                GbifZoneRow(
                    zone_key=r.zone_key,
                    zone_label=r.zone_label,
                    total=r.total,
                    total_label=f"{r.total:,}",
                    richness=r.richness,
                    richness_label=(f"{r.richness}+" if r.richness_truncated
                                    else str(r.richness)),
                    species_top=[
                        GbifSpeciesRow(name=n, count=c, count_label=f"{c:,}")
                        for n, c in r.species[:GBIF_SPECIES_TABLE_LIMIT]
                    ],
                    kingdoms=[GbifKingdomRow(name=n, count=c)
                             for n, c in r.kingdoms],
                    error=r.error,
                )
                for r in rows
            ]


__all__ = ["GbifMixin", "GbifZoneRow", "GbifKingdomRow", "GbifSpeciesRow"]
