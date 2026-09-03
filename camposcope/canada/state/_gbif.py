"""GBIF species-per-zone analysis — the Canada page's GBIF tab.

Same shape as the Brazil page's ``state/_gbif.py`` — see that module for the
full rationale (typed rows because a zone nests two further lists, the
"Calcular"-gated analysis separate from the always-declarative map layer).
"""

from __future__ import annotations

import logging
from typing import Any, List

import reflex as rx
from pydantic import BaseModel

from ...config.settings import GBIF_SPECIES_TABLE_LIMIT
from ...state._proxy import plain
from ..services import gbif_export, gbif_species

logger = logging.getLogger(__name__)


class CanadaGbifSpeciesRow(BaseModel):
    name: str
    count: int
    count_label: str


class CanadaGbifKingdomRow(BaseModel):
    name: str
    count: int


class CanadaGbifZoneRow(BaseModel):
    zone_key: str
    zone_label: str
    total: int
    total_label: str
    richness: int
    richness_label: str
    #: Up to GBIF_EXPORT_SPECIES_LIMIT rows — what the spreadsheet export
    #: writes (canada/services/gbif_export.py). Not rendered directly.
    species: List[CanadaGbifSpeciesRow]
    species_top: List[CanadaGbifSpeciesRow]
    kingdoms: List[CanadaGbifKingdomRow]
    error: str


class CanadaGbifMixin(rx.State, mixin=True):
    """Species recorded in GBIF, per zone."""

    gbif_zone_rows: List[CanadaGbifZoneRow] = []
    gbif_running: bool = False
    gbif_error: str = ""
    gbif_export_error: str = ""

    @rx.event(background=True)
    async def run_gbif_species(self):
        async with self:
            if not getattr(self, "has_parcel", False):
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
            self.gbif_error = next((r.error for r in rows if r.error), "")
            self.gbif_zone_rows = [
                CanadaGbifZoneRow(
                    zone_key=r.zone_key,
                    zone_label=r.zone_label,
                    total=r.total,
                    total_label=f"{r.total:,}",
                    richness=r.richness,
                    richness_label=(f"{r.richness}+" if r.richness_truncated
                                    else str(r.richness)),
                    species=(species := [
                        CanadaGbifSpeciesRow(name=n, count=c, count_label=f"{c:,}")
                        for n, c in r.species
                    ]),
                    species_top=species[:GBIF_SPECIES_TABLE_LIMIT],
                    kingdoms=[CanadaGbifKingdomRow(name=n, count=c)
                             for n, c in r.kingdoms],
                    error=r.error,
                )
                for r in rows
            ]

    # ---------------------------------------------------------------------- #
    # Export
    # ---------------------------------------------------------------------- #
    def _gbif_export_context(self) -> List[List[Any]]:
        """The parcel, as the metadata sheet's opening block."""
        parcel = getattr(self, "parcel", {}) or {}
        return [
            ["  identifier", parcel.get("identifier") or "—"],
            ["  PID", parcel.get("pid_formatted") or "—"],
            ["  municipality", parcel.get("municipality") or "—"],
            ["  regional district", parcel.get("regional_district") or "—"],
            ["  registered area (ha)", parcel.get("area_registered_ha") or 0],
        ]

    def download_gbif_species_ods(self):
        """The workbook: metadata, then one tab per zone. Built from the
        rows already in state — no re-query, so the file and the screen
        cannot disagree."""
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
        """Every zone in one flat table — see
        canada/services/gbif_export.build_csv."""
        if not self.gbif_zone_rows:
            self.gbif_export_error = self.tr["gbif_export_nothing"]
            return None
        self.gbif_export_error = ""
        data, name = gbif_export.build_csv(self.gbif_zone_rows)
        return rx.download(data=data, filename=name, mime_type="text/csv")


__all__ = ["CanadaGbifMixin", "CanadaGbifZoneRow", "CanadaGbifKingdomRow",
          "CanadaGbifSpeciesRow"]
