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
from typing import Any, List

import reflex as rx
from pydantic import BaseModel

from ..config.settings import GBIF_SPECIES_TABLE_LIMIT
from ..services import gbif_export, gbif_species
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
    #: Up to GBIF_EXPORT_SPECIES_LIMIT rows — what the spreadsheet export
    #: writes (services/gbif_export.py). Not rendered directly.
    species: List[GbifSpeciesRow]
    #: The first GBIF_SPECIES_TABLE_LIMIT of ``species``, and the only list
    #: the results tab renders — rx.foreach has no way to take the head of a
    #: list var, and 500 rows of DOM per card across four cards is a heavy
    #: panel for a table nobody scrolls to the bottom of on screen.
    species_top: List[GbifSpeciesRow]
    kingdoms: List[GbifKingdomRow]
    error: str


class GbifMixin(rx.State, mixin=True):
    """Species recorded in GBIF, per zone."""

    gbif_zone_rows: List[GbifZoneRow] = []
    gbif_running: bool = False
    gbif_error: str = ""
    gbif_export_error: str = ""

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
                    species=(species := [
                        GbifSpeciesRow(name=n, count=c, count_label=f"{c:,}")
                        for n, c in r.species
                    ]),
                    species_top=species[:GBIF_SPECIES_TABLE_LIMIT],
                    kingdoms=[GbifKingdomRow(name=n, count=c)
                             for n, c in r.kingdoms],
                    error=r.error,
                )
                for r in rows
            ]

    # ---------------------------------------------------------------------- #
    # Export
    # ---------------------------------------------------------------------- #
    def _gbif_export_context(self) -> List[List[Any]]:
        """The property, as the metadata sheet's opening block."""
        imovel = getattr(self, "imovel", {}) or {}
        return [
            ["  código do imóvel", imovel.get("cod_imovel") or "—"],
            ["  UF", imovel.get("uf") or "—"],
            ["  município", imovel.get("municipio") or "—"],
            ["  área declarada (ha)", imovel.get("area_declarada_ha") or 0],
            ["  tipo", imovel.get("tipo_imovel") or "—"],
            ["  condição", imovel.get("condicao") or "—"],
        ]

    def download_gbif_species_ods(self):
        """The workbook: metadata, then one tab per zone.

        Built from the rows already in state — no re-query, so the file and
        the screen cannot disagree. Synchronous, unlike the Earth Engine
        exports: there is no computation here, only formatting a few hundred
        rows already in memory.
        """
        if not self.gbif_zone_rows:
            self.gbif_export_error = self.tr["gbif_export_nothing"]
            return None
        self.gbif_export_error = ""
        try:
            data, name = gbif_export.build_ods(
                self.gbif_zone_rows, self._gbif_export_context(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("GBIF species ODS export failed")
            self.gbif_export_error = str(exc)
            return None
        return rx.download(data=data, filename=name,
                           mime_type=gbif_export.MIMETYPE)

    def download_gbif_species_csv(self):
        """Every zone in one flat table, for a script rather than a reader.

        Carries none of the workbook's caveats, which is why it sits beside
        the ODS rather than replacing it — see services/gbif_export.build_csv.
        """
        if not self.gbif_zone_rows:
            self.gbif_export_error = self.tr["gbif_export_nothing"]
            return None
        self.gbif_export_error = ""
        data, name = gbif_export.build_csv(self.gbif_zone_rows)
        return rx.download(data=data, filename=name, mime_type="text/csv")


__all__ = ["GbifMixin", "GbifZoneRow", "GbifKingdomRow", "GbifSpeciesRow"]
