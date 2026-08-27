"""Downloads: per-table CSVs of whatever a tab has already computed.

Scoped narrower than the Brazil page's ``ExportMixin`` deliberately — this page
ships the per-chart PNG and per-table CSV icons every tab already has
(``components/export_widgets.py``), which is most of what a working paper
needs. The bulk ODS workbook and the paper-formatted HTML report
(``camposcope/services/exports.py`` and ``services/report.py``) are **not**
ported: both are substantial, Brazil-shaped documents (grau de fundamentação
tables, CAR-specific metadata sheets) that would need their own redesign rather
than a substitution pass, and are left for a follow-up rather than shipped as a
half-adapted copy of a Brazilian report.
"""

from __future__ import annotations

import csv
import io

import reflex as rx

from ...state._proxy import plain


def _records_to_csv(records: list[dict], columns: list[str] | None = None) -> bytes:
    if not records:
        return b""
    fieldnames = columns or list(records[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    return buf.getvalue().encode("utf-8")


class CanadaExportMixin(rx.State, mixin=True):
    """One CSV-download event per results table."""

    def download_cobertura_csv(self):
        rows = plain(getattr(self, "history_table_rows", []))
        return rx.download(
            data=_records_to_csv(rows), filename="camposcope_ca_cobertura.csv")

    def download_transicoes_csv(self):
        rows = plain(getattr(self, "sankey_table_rows", []))
        return rx.download(
            data=_records_to_csv(rows), filename="camposcope_ca_transicoes.csv")

    def download_floresta_csv(self):
        rows = plain(getattr(self, "hansen_table_rows", []))
        return rx.download(
            data=_records_to_csv(rows), filename="camposcope_ca_floresta.csv")

    def download_biomassa_csv(self):
        rows = plain(getattr(self, "biomass_table_rows", []))
        return rx.download(
            data=_records_to_csv(rows), filename="camposcope_ca_biomassa.csv")

    def download_fogo_csv(self):
        rows = plain(getattr(self, "fire_table_rows", []))
        return rx.download(
            data=_records_to_csv(rows), filename="camposcope_ca_fogo.csv")

    def download_paisagem_csv(self):
        rows = plain(getattr(self, "landscape_table_rows", []))
        return rx.download(
            data=_records_to_csv(rows), filename="camposcope_ca_paisagem.csv")

    def download_connectivity_csv(self):
        rows = plain(getattr(self, "connectivity_table_rows", []))
        return rx.download(
            data=_records_to_csv(rows), filename="camposcope_ca_conectividade.csv")

    def download_validacao_csv(self):
        rows = plain(getattr(self, "validation_matrix_rows", []))
        return rx.download(
            data=_records_to_csv(rows), filename="camposcope_ca_validacao.csv")
