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
from reflex.utils.format import format_queue_events

from ..report_kit import browser_capture
from ..services import exports, report
from ..translations import get_translations
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

    #: The laid-out report's checkboxes (doc/13 §7, shared anatomy §2.9) —
    #: what goes into the PDF/HTML. Maps cost four Earth Engine thumbnails.
    exp_report_maps: bool = True
    exp_report_figures: bool = True
    exp_report_tables: bool = True
    exp_report_appendix: bool = False
    #: The GBIF per-zone species tables — off by default like the two above,
    #: but its own flag rather than folded into exp_report_tables: it governs
    #: the workbook too (which has no other opt-in toggle), and the species
    #: list can be large enough on its own to be worth a deliberate choice.
    exp_include_gbif: bool = False

    report_busy: bool = False
    report_stage: str = ""
    report_error: str = ""
    report_result: str = ""
    #: Which property a running report was started for — chart PNGs captured
    #: for one property are never laid out under another's identity.
    _report_for: str = ""

    export_busy: bool = False
    export_stage: str = ""
    export_error: str = ""
    export_result: str = ""

    def set_export_open(self, value: bool):
        self.export_open = value
        if value:
            self.export_error = ""
            self.export_result = ""
            if not self.report_busy:
                self.report_error = ""
                self.report_result = ""

    def toggle_exp_report_figures(self, checked: bool):
        self.exp_report_figures = checked

    def toggle_exp_report_tables(self, checked: bool):
        self.exp_report_tables = checked

    def toggle_exp_include_gbif(self, checked: bool):
        self.exp_include_gbif = checked

    def toggle_exp_report_maps(self, checked: bool):
        self.exp_report_maps = checked

    def toggle_exp_report_appendix(self, checked: bool):
        self.exp_report_appendix = checked

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
            spot_summary=plain(self.spot_summary),
            spot_provenance=plain(self.spot_provenance),
            gbif_zone_rows=plain(self.gbif_zone_rows),
            overlaps=plain(self.overlaps),
            overlaps_checked=self.overlaps_checked,
            area_calculada_ha=self.area_calculada_ha,
            area_delta_ha=self.area_delta_ha,
            area_delta_pct=self.area_delta_pct,
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
    # The laid-out report, PDF or HTML (doc/13, shared kit contract §2.7)
    #
    # start_report   normal      snapshot → chart figures → capture job; returns
    #                            [one capture script, build_report]
    # receive_report_chart  normal  one browser-rendered chart → JobStore
    # build_report   background  maps (EE, executor) while the browser renders,
    #                            then wait for the charts, build, render, download
    # ---------------------------------------------------------------------- #

    def _report_disabled_reason(self) -> str:
        tr = get_translations(getattr(self, "lang", "pt"))
        if not getattr(self, "imovel", None):
            return tr["report_reason_no_property"]
        if self.report_busy:
            return tr["report_reason_busy"]
        if getattr(self, "history_running", False):
            return tr["report_reason_history"]
        return ""

    @rx.var(cache=True, deps=["imovel", "report_busy", "history_running", "lang"],
            auto_deps=False)
    def report_disabled_reason(self) -> str:
        """Why the PDF/HTML buttons are disabled ("" when they are not).
        Explicit deps: ``imovel``/``history_running``/``lang`` live on sibling
        mixins and are read through getattr (see ImovelMixin.disclosure).
        Disabled while Cobertura is still loading, so the charts captured at
        start_report are the ones the report is built from."""
        return self._report_disabled_reason()

    @rx.var(cache=True, deps=["imovel", "report_busy", "history_running", "lang"],
            auto_deps=False)
    def report_disabled(self) -> bool:
        return bool(self._report_disabled_reason())

    def _report_subject(self) -> str:
        imovel = getattr(self, "imovel", {}) or {}
        return str(imovel.get("cod_imovel") or imovel.get("coordinates") or "")

    @rx.event
    def start_report(self, fmt: str):
        """PDF or HTML. A normal (not background) handler: it snapshots the
        charts and, for the PDF, hands the browser ONE capture script whose
        per-chart callbacks post each PNG back to receive_report_chart, then
        chains the background build (doc/13 §2.7)."""
        fmt = "html" if fmt == "html" else "pdf"
        tr = self.tr
        if self.report_busy:
            return None
        reason = self._report_disabled_reason()
        if reason:
            self.report_error = reason
            return None
        self.report_busy = True
        self.report_error = ""
        self.report_result = ""
        self._report_for = self._report_subject()
        if fmt == "html" or not self.exp_report_figures:
            self.report_stage = tr["report_stage_building"]
            return self.__class__.build_report("", fmt)

        snapshot = self._gather()
        figs = report.report_figures(**snapshot, focus_zone=self.active_zone,
                                     lang=self.lang)
        if not figs:
            self.report_stage = tr["report_stage_building"]
            return self.__class__.build_report("", fmt)
        prepared, opts = report.capture_specs(figs)
        job_id = browser_capture.STORE.create(self.router.session.client_token,
                                              prepared.keys())
        callbacks = {
            key: str(format_queue_events(
                self.__class__.receive_report_chart(job_id, key),
                args_spec=lambda d: [d]))
            for key in prepared
        }
        self.report_stage = tr["report_stage_charts"].format(got=0, total=len(prepared))
        return [
            rx.call_script(browser_capture.build_capture_script(prepared, callbacks, opts)),
            self.__class__.build_report(job_id, fmt),
        ]

    @rx.event
    def receive_report_chart(self, job_id: str, key: str, data: str):
        """One chart rasterised by the browser. A public RPC: JobStore.put
        checks the job's client token, the PNG prefix, size and dimensions."""
        store = browser_capture.STORE
        if not store.put(job_id, key, data, self.router.session.client_token):
            return
        got, total = store.progress(job_id)
        if self.report_busy and total:
            self.report_stage = self.tr["report_stage_charts"].format(got=got, total=total)

    @rx.event(background=True)
    async def build_report(self, job_id: str, fmt: str):
        from ..services import report_maps
        from ..services.report import ReportOptions

        fmt = "html" if fmt == "html" else "pdf"
        await self._wait_for_history()

        async with self:
            tr = self.tr
            lang = self.lang
            payload = self._gather()
            payload["zones_geojson"] = plain(self.zones_geojson)
            payload["overlaps_error"] = self.overlaps_error
            focus_zone = self.active_zone
            subject_changed = self._report_subject() != self._report_for
            options = ReportOptions(
                maps=self.exp_report_maps, figures=self.exp_report_figures,
                tables=self.exp_report_tables, appendix=self.exp_report_appendix,
                gbif=self.exp_include_gbif)
            imovel_geojson = plain(self.imovel_geojson)
            self.report_stage = tr["report_stage_maps"]

        imovel = payload["imovel"]
        loop = asyncio.get_running_loop()

        maps_future = None
        if options.maps:
            maps_future = loop.run_in_executor(None, lambda: report_maps.fetch_report_maps(
                imovel=imovel, zones=payload["zones"],
                zones_geojson=payload["zones_geojson"],
                spot_summary=payload["spot_summary"],
                history_rows=payload["history_rows"], lang=lang))
        overlaps_future = None
        if (imovel.get("kind") != "square" and not payload["overlaps_checked"]
                and imovel.get("cod_imovel") and imovel_geojson):
            from ._zones import lookup_overlaps
            overlaps_future = loop.run_in_executor(
                None, lambda: lookup_overlaps(imovel["cod_imovel"], imovel_geojson))

        # The charts: the browser has been rendering since start_report.
        pngs: dict = {}
        errors: dict = {}
        if job_id:
            store = browser_capture.STORE
            _, total = store.progress(job_id)
            deadline = loop.time() + browser_capture.wait_deadline_s(total)
            while not store.done(job_id) and loop.time() < deadline:
                await asyncio.sleep(0.25)
            pngs, errors = store.take(job_id)
            if subject_changed:     # captured for another property: never mix
                pngs, errors = {}, {k: "property changed" for k in pngs}

        maps_list, map_errors, map_attr = [], {}, []
        if maps_future is not None:
            async with self:
                self.report_stage = tr["report_stage_maps"]
            try:
                maps_list, map_errors, map_attr = await asyncio.wait_for(maps_future, 180)
            except Exception as exc:                   # noqa: BLE001
                logger.warning("report maps failed: %s", exc)
                map_errors = {"maps": str(exc)[:200] or type(exc).__name__}
        if overlaps_future is not None:
            try:
                payload["overlaps"] = await asyncio.wait_for(overlaps_future, 60)
                payload["overlaps_checked"] = True
                async with self:
                    if self._report_subject() == self._report_for:
                        self.overlaps = payload["overlaps"]
                        self.overlaps_checked = True
                        self.overlaps_error = ""
            except Exception as exc:                   # noqa: BLE001
                logger.warning("overlap lookup for the report failed: %s", exc)
                payload["overlaps_error"] = str(exc)[:160] or type(exc).__name__

        async with self:
            self.report_stage = tr["report_stage_building"]
        try:
            def build() -> bytes:
                rep = report.build_imovel_report(
                    **payload, focus_zone=focus_zone, lang=lang, options=options,
                    figure_pngs=pngs, figure_errors=errors, maps=maps_list,
                    map_errors=map_errors, map_attributions=map_attr)
                return report.render(rep, fmt)

            data = await loop.run_in_executor(None, build)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("Property report failed")
            async with self:
                self.report_busy = False
                self.report_stage = ""
                self.report_error = tr["export_report_failed"].format(exc=exc)
            return

        name = report.report_filename(imovel, fmt)
        async with self:
            self.report_busy = False
            self.report_stage = ""
            self.report_result = f"{name} ({len(data) // 1024} KiB)"
        return rx.download(data=data, filename=name,
                           mime_type="application/pdf" if fmt == "pdf" else "text/html")

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
