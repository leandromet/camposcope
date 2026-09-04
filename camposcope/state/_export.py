"""Downloads: the property workbook and the paper-friendly report.

One property, one workbook, one report — Camposcope has no multi-property
selection to make a second, bulk-shaped export meaningful for (see
``services/exports.py``'s own docstring), so unlike Naturametrics there is
only ever one download target of each kind here, not two.

Three export paths, same reasoning as Naturametrics (``services/report.py``'s
docstring, ported): the per-chart/per-table icons in ``components/results.py``
and friends for one figure or one table at a time; the ODS workbook for every
number, reprocessable; this report for "send someone everything, already laid
out". ``rx.download`` carries the bytes to the browser inside the event
payload, same caveat as upstream — fine at these sizes (a few hundred KiB at
most for one property), the reason a bulk-selection cap exists over there and
not here.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging

import reflex as rx

from ..services import exports, report
from ._proxy import plain

logger = logging.getLogger(__name__)


def _records_to_csv(records: list[dict], columns: list[str] | None = None) -> bytes:
    """One data table, straight from the records already on screen — the
    per-table "download this one" affordance next to each results table
    (see components/export_widgets.py), for a paper's own reprocessing
    rather than a screenshot."""
    if not records:
        return b""
    fieldnames = columns or list(records[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue().encode("utf-8")


class ExportMixin(rx.State, mixin=True):
    """The export panel."""

    export_open: bool = False

    #: The study-point "paper-friendly" HTML report (services.report) — a
    #: third export path alongside the ODS workbook and the per-chart/per-
    #: table icons. Both default off: the workbook button stays the one-click
    #: default action.
    exp_report_figures: bool = False
    exp_report_tables: bool = False
    #: The GBIF per-zone species tables — off by default like the two above,
    #: but its own flag rather than folded into exp_report_tables: it governs
    #: the workbook too (which has no other opt-in toggle), and the species
    #: list can be large enough on its own to be worth a deliberate choice.
    exp_include_gbif: bool = False

    export_busy: bool = False
    export_stage: str = ""
    export_error: str = ""
    export_result: str = ""

    def set_export_open(self, value: bool):
        self.export_open = value
        if value:
            self.export_error = ""
            self.export_result = ""

    def toggle_exp_report_figures(self, checked: bool):
        self.exp_report_figures = checked

    def toggle_exp_report_tables(self, checked: bool):
        self.exp_report_tables = checked

    def toggle_exp_include_gbif(self, checked: bool):
        self.exp_include_gbif = checked

    @rx.var
    def export_report_any(self) -> bool:
        return self.exp_report_figures or self.exp_report_tables

    # ---------------------------------------------------------------------- #
    # Shared: gather whatever the property's results tabs have computed
    # ---------------------------------------------------------------------- #

    async def _wait_for_history(self) -> None:
        """The one automatic fetch (run_history, chained straight off
        search_by_code/select_at_point/choose_candidate) can still be in
        flight if the download is requested the instant a property loads —
        every other tab's data is manual ("Calcular"), so nothing else races
        this. Bounded so a genuinely stuck fetch cannot hang the download
        forever; past the bound the export still proceeds with whatever
        landed, same as Naturametrics' equivalent wait."""
        waited = 0.0
        while waited < 20.0:
            async with self:
                running = self.history_running
                if running:
                    self.export_stage = self.tr["export_stage_waiting"]
            if not running:
                return
            await asyncio.sleep(0.4)
            waited += 0.4

    def _gather(self) -> dict:
        """Every already-computed field the workbook/report both read —
        identical argument shape for both, since they are the same "what's on
        screen for this property" snapshot laid out two different ways."""
        return dict(
            imovel=plain(self.imovel),
            zones=plain(self.zones),
            history_rows=plain(self.history_rows),
            history_provenance=plain(self.history_provenance),
            hansen_loss_rows=plain(self.hansen_loss_rows),
            hansen_gain_ha=self.hansen_gain_ha,
            hansen_provenance=plain(self.hansen_provenance),
            biomass_rows=plain(self.biomass_rows),
            biomass_provenance=plain(self.biomass_provenance),
            landscape_rows=plain(self.landscape_rows),
            landscape_provenance=plain(self.landscape_provenance),
            connectivity_rows=plain(self.connectivity_rows),
            connectivity_provenance=plain(self.connectivity_provenance),
            sankey_transitions=plain(self.sankey_transitions),
            sankey_zone_label=self.sankey_zone_label,
            sankey_year_a=self.sankey_year_a,
            sankey_year_b=self.sankey_year_b,
            sankey_provenance=plain(self.sankey_provenance),
            fire_rows=plain(self.fire_rows),
            fire_annual_rows=plain(self.fire_annual_rows),
            fire_provenance=plain(self.fire_provenance),
            validacao_matrix=plain(self.validacao_matrix),
            validacao_zone_label=self.validacao_zone_label,
            validacao_provenance=plain(self.validacao_provenance),
            gbif_zone_rows=plain(self.gbif_zone_rows),
        )

    # ---------------------------------------------------------------------- #
    # The ODS workbook
    # ---------------------------------------------------------------------- #

    @rx.event(background=True)
    async def download_imovel_workbook(self):
        async with self:
            if not self.has_imovel:
                self.export_error = self.tr["export_choose_imovel_first"]
                return
            self.export_busy = True
            self.export_stage = self.tr["export_stage_building"]
            self.export_error = ""
            self.export_result = ""

        await self._wait_for_history()

        async with self:
            self.export_stage = self.tr["export_stage_building"]
            payload = self._gather()
            payload["lang"] = self.lang
            payload["include_gbif"] = self.exp_include_gbif

        loop = asyncio.get_running_loop()
        try:
            data, name = await loop.run_in_executor(
                None, lambda: exports.imovel_workbook(**payload))
        except Exception as exc:                       # noqa: BLE001
            logger.exception("Property workbook failed")
            async with self:
                self.export_busy = False
                self.export_error = self.tr["export_workbook_failed"].format(exc=exc)
            return

        async with self:
            self.export_busy = False
            self.export_stage = ""
            self.export_result = f"{name} ({len(data) // 1024} KiB)"
        return rx.download(data=data, filename=name,
                           mime_type="application/vnd.oasis.opendocument.spreadsheet")

    # ---------------------------------------------------------------------- #
    # The HTML report
    # ---------------------------------------------------------------------- #

    @rx.event(background=True)
    async def download_imovel_report(self):
        async with self:
            if not self.has_imovel:
                self.export_error = self.tr["export_choose_imovel_first"]
                return
            if not self.export_report_any:
                return
            self.export_busy = True
            self.export_stage = self.tr["export_stage_building"]
            self.export_error = ""
            self.export_result = ""

        await self._wait_for_history()

        async with self:
            self.export_stage = self.tr["export_stage_building"]
            payload = self._gather()
            payload["lang"] = self.lang
            payload["include_figures"] = self.exp_report_figures
            payload["include_tables"] = self.exp_report_tables
            payload["include_gbif"] = self.exp_include_gbif

        loop = asyncio.get_running_loop()
        try:
            data, name = await loop.run_in_executor(
                None, lambda: report.imovel_report_html(**payload))
        except Exception as exc:                       # noqa: BLE001
            logger.exception("Property report failed")
            async with self:
                self.export_busy = False
                self.export_error = self.tr["export_report_failed"].format(exc=exc)
            return

        async with self:
            self.export_busy = False
            self.export_stage = ""
            self.export_result = f"{name} ({len(data) // 1024} KiB)"
        return rx.download(data=data, filename=name, mime_type="text/html")

    # ---------------------------------------------------------------------- #
    # Per-table CSV — the raw records behind each results-tab table, not the
    # display-formatted strings (thousands separators, "—" placeholders).
    # ---------------------------------------------------------------------- #

    def download_cobertura_csv(self):
        rows = [r for r in plain(self.history_rows)
               if r["zone_key"] == self.active_zone]
        if not rows:
            return None
        return rx.download(
            data=_records_to_csv(rows, ["zone_key", "zone_label", "year",
                                       "class_id", "class_pt", "class_en",
                                       "pixels", "area_ha"]),
            filename="camposcope_cobertura.csv", mime_type="text/csv")

    def download_floresta_csv(self):
        rows = [r for r in plain(self.hansen_loss_rows)
               if r["zone_key"] == self.active_zone]
        if not rows:
            return None
        return rx.download(
            data=_records_to_csv(rows, ["zone_key", "zone_label", "year",
                                       "period", "area_ha"]),
            filename="camposcope_floresta.csv", mime_type="text/csv")

    def download_biomassa_csv(self):
        rows = [r for r in plain(self.biomass_rows)
               if r["zone_key"] == self.active_zone]
        if not rows:
            return None
        return rx.download(
            data=_records_to_csv(rows, ["zone_key", "zone_label", "year",
                                       "agb_mean_mgha", "total_biomass_mg"]),
            filename="camposcope_biomassa.csv", mime_type="text/csv")

    def download_paisagem_csv(self):
        rows = plain(self.landscape_rows)
        if not rows:
            return None
        return rx.download(
            data=_records_to_csv(rows, ["zone_key", "zone_label", "area_ha",
                                       "patches", "patch_density",
                                       "largest_patch_ha", "largest_patch_pct",
                                       "edge_m", "edge_density", "mean_patch_ha",
                                       "patch_area_sq_ha", "meff_ha", "shannon",
                                       "simpson", "simpson_evenness"]),
            filename="camposcope_paisagem.csv", mime_type="text/csv")

    def download_connectivity_csv(self):
        rows = plain(self.connectivity_rows)
        if not rows:
            return None
        return rx.download(
            data=_records_to_csv(rows, ["zone_key", "zone_label", "n_fragments",
                                       "enn_mean_m", "enn_median_m"]),
            filename="camposcope_conectividade.csv", mime_type="text/csv")

    def download_transicoes_csv(self):
        from ..config import mapbiomas as mb

        transitions = plain(self.sankey_transitions)
        rows = [
            {"classe_origem": mb.label(int(src), self.lang),
             "classe_destino": mb.label(int(tgt), self.lang),
             "area_ha": round(float(area), 4)}
            for src, tgts in transitions.items()
            for tgt, area in tgts.items()
        ]
        if not rows:
            return None
        rows.sort(key=lambda r: r["area_ha"], reverse=True)
        return rx.download(
            data=_records_to_csv(rows, ["classe_origem", "classe_destino", "area_ha"]),
            filename="camposcope_transicoes.csv", mime_type="text/csv")

    def download_fogo_csv(self):
        rows = [r for r in plain(self.fire_rows)
               if r["zone_key"] == self.active_zone]
        if not rows:
            return None
        return rx.download(
            data=_records_to_csv(rows, ["zone_key", "zone_label",
                                       "fire_history_pct", "fire_frequency",
                                       "fire_last_year", "area_ha"]),
            filename="camposcope_fogo.csv", mime_type="text/csv")

    def download_validacao_csv(self):
        from ..config import ibge_vegetation as iv

        matrix = plain(self.validacao_matrix)
        cells = matrix.get("matrix") or {}
        rows = [
            {"ibge": iv.GROUP_LABELS_PT.get(g_ibge, g_ibge),
             "mapbiomas": iv.GROUP_LABELS_PT.get(g_mb, g_mb),
             "pct_area": round(float(pct), 4)}
            for g_ibge, row in cells.items()
            for g_mb, pct in row.items()
        ]
        if not rows:
            return None
        return rx.download(
            data=_records_to_csv(rows, ["ibge", "mapbiomas", "pct_area"]),
            filename="camposcope_validacao.csv", mime_type="text/csv")
