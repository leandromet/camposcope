"""services/report.py — the laid-out property report (doc/13 §11).

Offline only: the report is built from rows the caller already computed, maps
and chart PNGs arrive as arguments, so every test here runs on synthetic data
with no Earth Engine, SICAR or browser.
"""

import io
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

pytest.importorskip("reportlab")

from camposcope import report_kit as rk  # noqa: E402
from camposcope.config.citation import CITATION_TEXT  # noqa: E402
from camposcope.config.sicar import DISCLOSURE_EN, DISCLOSURE_PT  # noqa: E402
from camposcope.services import report_text as rt  # noqa: E402
from camposcope.services.report import (ReportOptions, build_imovel_report,  # noqa: E402
                                        render, report_figures, report_filename)
from camposcope.translations import get_translations  # noqa: E402

ZONES = [
    {"zone_key": "imovel", "zone_label": "Imóvel", "zone_kind": "property",
     "radius_m": None, "area_ha": 120.0},
    {"zone_key": "ring_500", "zone_label": "0 – 500 m", "zone_kind": "ring",
     "radius_m": 500, "area_ha": 340.0},
]

IMOVEL = {"kind": "imovel", "cod_imovel": "MT-5107925-ABCD1234", "uf": "MT",
          "municipio": "Sinop", "cod_municipio_ibge": "5107909",
          "area_declarada_ha": 120.0, "condicao": "Ativo",
          "status_imovel": "Aguardando análise", "tipo_imovel": "IRU",
          "dat_criacao": "2015-03-01", "data_atualizacao": "2020-01-02",
          "m_fiscal": 1.3, "ano_criacao": 2015,
          "queried_at": "2026-09-24T12:00:00+00:00", "coordinates": ""}

SQUARE = {"kind": "square", "cod_imovel": "", "uf": "", "municipio": "",
          "area_declarada_ha": 500.0, "coordinates": "-12.5000, -55.7000"}


def _square_geom(lon=-55.7, lat=-12.5, d=0.005):
    return {"type": "Polygon", "coordinates": [[
        [lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d],
        [lon - d, lat + d], [lon - d, lat - d]]]}


ZONES_GEOJSON = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"role": "property", "zone_key": "imovel"},
     "geometry": _square_geom()},
    {"type": "Feature", "properties": {"role": "ring", "zone_key": "ring_500"},
     "geometry": _square_geom(d=0.01)},
]}


def _prov(name="landuse_history"):
    return {"name": name, "dataset_id": "asset", "bands": ["b1"], "scale_m": 30,
            "reducer": "frequencyHistogram", "pixel_area_basis": "", "max_pixels": 1e9,
            "tile_scale": 4, "geometry": None, "degraded": False, "notes": [],
            "computed_at": "2026-01-01T00:00:00+00:00", "extra": {}}


def _history_rows():
    rows = []
    for z in ZONES:
        for year in (1985, 2024):
            forest = 90.0 if year == 1985 else 30.0
            rows.append({"zone_key": z["zone_key"], "zone_label": z["zone_label"],
                         "year": year, "class_id": 3, "class_pt": "Formação Florestal",
                         "class_en": "Forest Formation", "pixels": 100, "area_ha": forest,
                         "color": "#1f8d49"})
            rows.append({"zone_key": z["zone_key"], "zone_label": z["zone_label"],
                         "year": year, "class_id": 15, "class_pt": "Pastagem",
                         "class_en": "Pasture", "pixels": 100, "area_ha": 120 - forest,
                         "color": "#edde8e"})
    return rows


def _full_gather():
    """Every tab computed — the "everything on screen" snapshot."""
    return dict(
        imovel=IMOVEL, zones=ZONES, zones_geojson=ZONES_GEOJSON,
        history_rows=_history_rows(), history_provenance=_prov(),
        hansen_loss_rows=[
            {"zone_key": "imovel", "zone_label": "Imóvel", "year": 2005,
             "period": "ate_2008", "area_ha": 12.0},
            {"zone_key": "imovel", "zone_label": "Imóvel", "year": 2011,
             "period": "2008_ate_registro", "area_ha": 3.5},
            {"zone_key": "ring_500", "zone_label": "0 – 500 m", "year": 2019,
             "period": "apos_registro", "area_ha": 1.2}],
        hansen_gain_ha=0.8, hansen_provenance=_prov("hansen"),
        biomass_rows=[{"zone_key": "imovel", "zone_label": "Imóvel", "year": y,
                       "agb_mean_mgha": 80.0 + y % 7, "total_biomass_mg": 9000.0}
                      for y in (2010, 2015, 2022)],
        biomass_provenance=_prov("biomass"),
        landscape_rows=[{"zone_key": z["zone_key"], "zone_label": z["zone_label"],
                         "area_ha": z["area_ha"], "patches": 4, "largest_patch_pct": 30.0,
                         "edge_density": 12.0, "meff_ha": 20.5, "shannon": 1.1}
                        for z in ZONES],
        landscape_provenance=_prov("landscape"),
        sankey_transitions={"3": {"3": 30.0, "15": 60.0}, "15": {"15": 30.0}},
        sankey_zone_label="Imóvel", sankey_year_a=1985, sankey_year_b=2024,
        sankey_provenance=_prov("sankey"),
        fire_rows=[{"zone_key": z["zone_key"], "zone_label": z["zone_label"],
                    "fire_history_pct": 12.0, "fire_frequency": 3, "fire_last_year": 2020,
                    "area_ha": z["area_ha"]} for z in ZONES],
        fire_annual_rows=[{"zone_key": "imovel", "zone_label": "Imóvel", "year": y,
                           "fire_pct": 1.0} for y in range(1985, 2026)],
        fire_provenance=_prov("fire"),
        validacao_matrix={"groups": ["forest", "other"],
                          "matrix": {"forest": {"forest": 40.0, "other": 5.0},
                                     "other": {"forest": 10.0, "other": 45.0}},
                          "forest_ibge": 45.0, "forest_mb": 50.0,
                          "natural_ibge": 50.0, "natural_mb": 55.0},
        validacao_zone_label="Imóvel", validacao_provenance=_prov("validacao"),
        spot_summary={"has_coverage": True, "covered_pct": 100.0,
                      "date_min": "2008-05-14", "date_max": "2008-07-03",
                      "pre_cutoff_pct": 100.0, "cutoff": "2008-07-22"},
        spot_provenance=_prov("spot_2008_coverage"),
        gbif_zone_rows=[{"zone_key": "imovel", "zone_label": "Imóvel", "total": 12,
                         "richness": 7}],
        overlaps=[{"cod_imovel": "MT-5107925-OTHER", "overlap_ha": 2.5,
                   "overlap_pct_do_imovel": 2.1}],
        overlaps_checked=True,
        area_calculada_ha=119.2, area_delta_ha=-0.8, area_delta_pct=-0.667,
    )


def _minimal_gather(imovel=IMOVEL):
    """Only Cobertura (the one automatic tab) has run."""
    return dict(imovel=imovel, zones=ZONES, zones_geojson=ZONES_GEOJSON,
                history_rows=_history_rows(), history_provenance=_prov(),
                area_calculada_ha=119.2, area_delta_ha=-0.8, area_delta_pct=-0.667)


def _keys(report):
    return [s.key for s in report.sections]


# --- structure ------------------------------------------------------------ #

def test_sections_follow_the_doc13_outline():
    rep = build_imovel_report(**_full_gather(),
                              options=ReportOptions(gbif=True, appendix=True))
    order = ["disclosure", "identification", "zones", "overlaps", "about",
             "cobertura", "transicoes", "floresta", "biomassa", "paisagem", "fogo",
             "validacao", "spot", "gbif", "provenance", "sources", "appendix"]
    assert _keys(rep) == order          # no maps passed → no maps section


def test_uncomputed_tabs_are_not_run_and_unticked_ones_excluded():
    rep = build_imovel_report(**_minimal_gather(), options=ReportOptions(maps=False))
    contents = next(b for b in rep.blocks() if isinstance(b, rk.ContentsList))
    status = {i.title: i.status for i in contents.items}
    t = lambda k: rt.t(k, "pt")  # noqa: E731
    assert status[t("sec_cobertura")] == "included"
    for key in ("transicoes", "floresta", "biomassa", "paisagem", "fogo",
                "validacao", "spot"):
        assert status[t(f"sec_{key}")] == "not_run", key
    assert status[t("sec_gbif")] == "excluded"
    assert status[t("sec_maps")] == "excluded"
    # not-run tabs get no section of their own
    assert "floresta" not in _keys(rep) and "maps" not in _keys(rep)


def test_maps_ticked_but_failed_are_unavailable_with_reason():
    rep = build_imovel_report(**_minimal_gather(), map_errors={"s2": "timeout"})
    contents = next(b for b in rep.blocks() if isinstance(b, rk.ContentsList))
    item = next(i for i in contents.items if i.title == rt.t("sec_maps", "pt"))
    assert item.status == "unavailable" and "timeout" in item.reason


def test_disclosure_is_the_first_block_in_the_report_language():
    for lang, text in (("pt", DISCLOSURE_PT), ("en", DISCLOSURE_EN)):
        rep = build_imovel_report(**_minimal_gather(), lang=lang)
        first = rep.sections[0]
        assert first.title == ""                   # above every heading
        assert isinstance(first.blocks[0], rk.Callout)
        assert first.blocks[0].kind == "disclosure" and first.blocks[0].text == text


def test_square_gets_its_own_disclosure_and_no_overlap_claim():
    rep = build_imovel_report(**_minimal_gather(SQUARE), lang="en")
    assert rep.sections[0].blocks[0].text == get_translations("en")["square_disclosure"]
    texts = " ".join(b.text for b in rep.blocks() if isinstance(b, rk.Paragraph))
    assert rt.t("overlaps_square", "en") in texts
    assert rt.t("overlaps_none", "en") not in texts


def test_unchecked_overlaps_are_never_reported_as_none_found():
    rep = build_imovel_report(**_minimal_gather(), overlaps_checked=False,
                              overlaps_error="SICAR down")
    texts = " ".join(b.text for b in rep.blocks() if isinstance(b, rk.Paragraph))
    assert rt.t("overlaps_none", "pt") not in texts
    assert "SICAR down" in texts


def test_car_fields_are_verbatim_and_areas_present():
    rep = build_imovel_report(**_full_gather(), lang="en")
    kv = next(b for b in rep.blocks() if isinstance(b, rk.KeyValues))
    values = dict(kv.rows)
    assert values[rt.t("kv_status", "en")] == "Aguardando análise"   # untranslated
    assert values[rt.t("kv_condicao", "en")] == "Ativo"
    assert values[rt.t("kv_tipo", "en")] == "IRU"
    assert "119.20 ha" in values[rt.t("kv_area_calculada", "en")]
    assert values[rt.t("kv_area_delta", "en")].startswith("-0.80 ha")


def test_hansen_three_periods_and_undated_gain():
    rep = build_imovel_report(**_full_gather(), lang="en")
    floresta = next(s for s in rep.sections if s.key == "floresta")
    text = " ".join(b.text for b in floresta.blocks if isinstance(b, rk.Paragraph))
    assert "12.0 ha up to 2008" in text
    assert "3.5 ha between 2008 and the CAR registration (2015)" in text
    assert "none after registration" in text
    assert "undated" in text


def test_spot_sentence_carries_dates_and_pre_cutoff_share():
    rep = build_imovel_report(**_full_gather(), lang="pt")
    spot = next(s for s in rep.sections if s.key == "spot")
    text = " ".join(b.text for b in spot.blocks if isinstance(b, rk.Paragraph))
    assert "22/07/2008" in text and "14/05/2008" in text and "100 %" in text


def test_english_report_has_no_portuguese_template_text():
    rep = build_imovel_report(**_full_gather(), lang="en",
                              options=ReportOptions(gbif=True, appendix=True))
    verbatim = {IMOVEL["condicao"], IMOVEL["status_imovel"], IMOVEL["tipo_imovel"]}
    strings = []
    for s in rep.sections:
        strings.append(s.title)
        for b in rep_blocks(s):
            if isinstance(b, rk.Paragraph):
                strings.append(b.text)
            elif isinstance(b, (rk.Figure, rk.MapFigure, rk.Table)):
                strings.append(b.caption)
            elif isinstance(b, rk.KeyValues):
                strings += [k for k, v in b.rows] + [v for k, v in b.rows if v not in verbatim]
            elif isinstance(b, rk.ContentsList):
                strings += [i.title for i in b.items] + [i.reason for i in b.items]
    blob = "\n".join(strings)
    pt, en = rt.TEMPLATES["pt"], rt.TEMPLATES["en"]
    for key, text in pt.items():
        if en.get(key) == text:
            continue                               # identical in both (e.g. "UF")
        for fragment in re.split(r"\{[^}]*\}", text):
            fragment = fragment.strip(" .,;:()«»")
            if len(fragment) >= 12:
                assert fragment not in blob, f"pt template {key!r} leaked: {fragment!r}"


def rep_blocks(section):
    for b in section.blocks:
        if isinstance(b, rk.SideBySide):
            yield b.left
            yield b.right
        else:
            yield b


def test_figures_are_built_with_the_screen_builders():
    figs = report_figures(**_full_gather())
    assert list(figs) == ["cobertura", "transicoes", "floresta", "biomassa",
                          "paisagem", "fogo"]
    assert all(isinstance(f, dict) and "data" in f for f in figs.values())
    # the registration marker of the on-screen chart comes along
    assert any("2015" in str(s.get("text", ""))
               for s in figs["cobertura"]["layout"].get("annotations", []))


def test_missing_chart_png_becomes_a_stated_placeholder():
    rep = build_imovel_report(**_full_gather(), lang="en",
                              figure_errors={"cobertura": "timed out"})
    fig = next(b for b in rep.blocks() if isinstance(b, rk.Figure) and b.key == "cobertura")
    assert fig.png is None and "timed out" in fig.unavailable_reason


def test_options_drop_figures_and_tables():
    rep = build_imovel_report(**_full_gather(),
                              options=ReportOptions(figures=False, tables=False))
    kinds = {type(b) for s in rep.sections if s.key not in ("zones", "overlaps")
             for b in s.blocks}
    assert rk.Figure not in kinds
    assert rk.Table not in kinds


# --- rendering ------------------------------------------------------------ #

def _png(w=1004, h=560):
    from PIL import Image
    img = Image.new("RGB", (w, h), (240, 240, 240))
    px = img.load()
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            px[x, y] = ((x * 3) % 255, (y * 5) % 255, 90)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _map_figure():
    from camposcope.report_kit.maps import MapView
    view = MapView.from_geojson([f["geometry"] for f in ZONES_GEOJSON["features"]])
    comp = rk.MapComposition(view=view, backdrop=_png(1004, 650),
                             vectors=[rk.VectorLayer(ZONES_GEOJSON["features"][0]["geometry"])],
                             legend=[rk.LegendItem("#111111", "Limite", "line")],
                             attribution="test")
    return rk.MapFigure(comp, "mapa de teste")


@pytest.mark.parametrize("lang", ["pt", "en"])
def test_both_formats_render_within_budget(lang):
    gather = _full_gather()
    pngs = {k: _png() for k in report_figures(**gather)}
    rep = build_imovel_report(**gather, lang=lang, figure_pngs=pngs,
                              maps=[_map_figure() for _ in range(4)],
                              options=ReportOptions(gbif=True, appendix=True))
    pdf = render(rep, "pdf")
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) <= 3_000_000, f"{len(pdf) / 1e6:.2f} MB"
    html = render(rep, "html").decode("utf-8")
    assert html.startswith("<!doctype html>")
    import html as _html
    assert _html.escape(DISCLOSURE_EN if lang == "en" else DISCLOSURE_PT,
                        quote=False) in html
    assert "Plotly.newPlot" in html or "Plotly.react" in html   # interactive charts


def test_car_fields_are_escaped_not_executed():
    poisoned = dict(IMOVEL, municipio="<script>alert(1)</script>")
    rep = build_imovel_report(**dict(_minimal_gather(), imovel=poisoned))
    html = render(rep, "html").decode("utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_citation_and_language_sources():
    from camposcope.config.citation import DATA_SOURCES, DATA_SOURCES_EN
    en = build_imovel_report(**_minimal_gather(), lang="en")
    cit = next(b for b in en.blocks() if isinstance(b, rk.Citation))
    assert cit.text == CITATION_TEXT
    joined = " ".join(cit.sources)
    assert DATA_SOURCES_EN[0][1] in joined and DATA_SOURCES[0][1] not in joined
    assert any("OpenStreetMap" in a for a in cit.attributions)


def test_filenames():
    from datetime import datetime, timezone
    when = datetime(2026, 9, 24, 15, 30, tzinfo=timezone.utc)
    assert report_filename(IMOVEL, "pdf", when) == \
        "camposcope_MT-5107925-ABCD1234_20260924-1530.pdf"
    assert report_filename(SQUARE, "html", when) == \
        "camposcope_quadrado_-12.5000_-55.7000_20260924-1530.html"
