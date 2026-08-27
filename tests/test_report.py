"""services/report.py — the bulk "paper-friendly" HTML report.

Offline only: report-building itself makes no Earth Engine or SICAR calls (it
only lays out rows the caller already computed), so every test here runs on
synthetic data.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from camposcope.config.citation import CITATION_TEXT  # noqa: E402
from camposcope.services.report import imovel_report_html  # noqa: E402

ZONES = [
    {"zone_key": "imovel", "zone_label": "Imóvel", "zone_kind": "property",
     "radius_m": None, "area_ha": 120.0},
    {"zone_key": "ring_500", "zone_label": "0 – 500 m", "zone_kind": "ring",
     "radius_m": 500, "area_ha": 340.0},
]

IMOVEL = {"cod_imovel": "MT-5107925-ABCD1234", "uf": "MT", "municipio": "Sinop",
         "area_declarada_ha": 120.0, "condicao": "Ativo",
         "status_imovel": "Aguardando análise", "dat_criacao": "2015-03-01",
         "ano_criacao": 2015}


def _history_rows():
    rows = []
    for z in ZONES:
        for year in (1985, 2024):
            rows.append({"zone_key": z["zone_key"], "zone_label": z["zone_label"],
                        "year": year, "class_id": 3, "class_pt": "Formação Florestal",
                        "class_en": "Forest", "pixels": 100, "area_ha": 90.0,
                        "color": "#1f8d49"})
    return rows


def _prov(name="landuse_history"):
    return {"name": name, "dataset_id": "asset", "bands": ["b1"], "scale_m": 30,
           "reducer": "frequencyHistogram", "pixel_area_basis": "", "max_pixels": 1e9,
           "tile_scale": 4, "geometry": None, "degraded": False, "notes": [],
           "computed_at": "2026-01-01T00:00:00+00:00", "extra": {}}


def test_report_is_one_self_contained_html_file():
    data, name = imovel_report_html(
        IMOVEL, ZONES, _history_rows(), history_provenance=_prov(),
    )
    assert name.endswith(".html")
    doc = data.decode("utf-8")
    assert doc.startswith("<!doctype html>")
    # Plotly's bundle is injected exactly once however many figures follow.
    assert doc.count("Plotly.newPlot") >= len(ZONES)


def test_figures_and_tables_can_be_toggled_independently():
    figures_only, _ = imovel_report_html(
        IMOVEL, ZONES, _history_rows(), include_figures=True, include_tables=False)
    doc = figures_only.decode("utf-8")
    assert "<h2>Figuras</h2>" in doc
    assert "<h2>Tabelas</h2>" not in doc

    tables_only, _ = imovel_report_html(
        IMOVEL, ZONES, _history_rows(), include_figures=False, include_tables=True,
        history_provenance=_prov())
    doc = tables_only.decode("utf-8")
    assert "<h2>Figuras</h2>" not in doc
    assert "Tabelas" in doc
    assert "<table>" in doc
    # Provenance always shows, independent of which two checkboxes were used.
    assert "<h2>Proveniência</h2>" in doc


def test_citation_and_data_sources_are_always_present():
    data, _ = imovel_report_html(IMOVEL, ZONES, _history_rows())
    doc = data.decode("utf-8")
    assert CITATION_TEXT.split(".")[0] in doc
    assert "car.gov.br" in doc


def test_empty_rows_produce_empty_notes_not_a_crash():
    data, name = imovel_report_html(IMOVEL, [], [])
    assert name.endswith(".html")
    doc = data.decode("utf-8")
    assert "cs-empty" in doc


def test_imovel_fields_are_escaped_not_executed():
    """A CAR field is carried verbatim (constraint C4), never sanitised for
    display — but the export must still escape it for safe HTML, the same
    OWASP reasoning as the ODS formula-injection guard for Naturametrics."""
    poisoned = dict(IMOVEL, municipio="<script>alert(1)</script>")
    data, _ = imovel_report_html(poisoned, ZONES, _history_rows())
    doc = data.decode("utf-8")
    assert "<script>alert(1)</script>" not in doc
    assert "&lt;script&gt;" in doc


def test_transitions_and_validacao_tables_use_the_zone_that_computed_them():
    """Sankey/validação are per-zone, on demand (state/_transitions.py,
    state/_analysis.py.ValidacaoMixin) — the report must say which zone,
    not assume it is still the one currently selected."""
    transitions = {"3": {"15": 12.5}}
    data, _ = imovel_report_html(
        IMOVEL, ZONES, [], sankey_transitions=transitions,
        sankey_zone_label="0 – 500 m", sankey_year_a=1985, sankey_year_b=2024,
        include_figures=False,
    )
    doc = data.decode("utf-8")
    assert "0 – 500 m" in doc
    assert "1985" in doc and "2024" in doc
