"""The property report — one content model, rendered as PDF or HTML.

doc/13 (plan) and its §2 (the shared ``report_kit`` contract). This module
turns the ``_gather()`` snapshot of what is already on screen into a
``report_kit.Report``; the kit renders it (``render_pdf`` / ``render_html``,
decision R4 — the two formats can not disagree because there is one model).

Three rules shape everything here:

* **Nothing is recomputed.** Every number comes from rows a results tab
  already fetched; charts are rebuilt from those rows with the *same* builder
  functions the screen uses (``components/charts.py``,
  ``services/transitions.sankey_figure``), so a chart in the report is the
  chart on screen. Tabs that were never run are listed as "not run" in the
  "About this report" contents, never silently dropped.
* **Constraint C4.** The disclosure (``config/sicar.py::disclosure_for``) is
  the first block of the first section — above every heading. ``condicao``,
  ``status_imovel`` and ``tipo_imovel`` are printed verbatim, untranslated and
  uncoloured. The prose (``services/report_text.py``) describes, never judges;
  ``tests/test_report_c4.py`` scans it.
* **No Earth Engine and no network here.** Maps are fetched beforehand by
  ``services/report_maps.py`` and chart PNGs by the browser
  (``state/_export.py``, doc/13 §2.7); both arrive as arguments.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .. import report_kit as rk
from ..config import datasets as ds
from ..config import mapbiomas as mb
from ..config.citation import (APP_URL, CITATION_TEXT, DATA_SOURCES, DATA_SOURCES_EN,
                               attribution_block)
from ..config.settings import HANSEN_TREECOVER_THRESHOLD
from ..config.sicar import disclosure_for
from ..report_kit import images as kit_images
from ..report_kit.text import fmt_date, fmt_ha, fmt_num
from . import report_text as rt
from .exports import spot_coverage_line

logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"
ACCENT = "#2f7d4f"

#: (slot, aspect) per chart — the page size the chart is laid out at (R9).
FIGURE_LAYOUT: Dict[str, Tuple[str, float]] = {
    "cobertura": ("full", 0.62),
    "transicoes": ("full", 0.66),
    "floresta": ("full", 0.46),
    "biomassa": ("full", 0.42),
    "paisagem": ("full", 0.42),
    "fogo": ("full", 0.42),
}

#: The analysis sections, in the on-screen tab order (doc/13 §3).
ANALYSIS_KEYS = ("cobertura", "transicoes", "floresta", "biomassa", "paisagem",
                 "fogo", "validacao", "spot", "gbif")


@dataclass
class ReportOptions:
    """The export dialog's checkboxes (doc/13 §7)."""

    maps: bool = True
    figures: bool = True
    tables: bool = True
    appendix: bool = False
    gbif: bool = False


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def _is_square(imovel: Dict[str, Any]) -> bool:
    return (imovel or {}).get("kind") == "square"


def _gbif_dict(row: Any) -> Dict[str, Any]:
    """GbifZoneRow pydantic objects (plain() leaves them as objects) or dicts."""
    if isinstance(row, dict):
        return row
    if hasattr(row, "model_dump"):
        return row.model_dump()
    return {k: getattr(row, k, None) for k in
            ("zone_key", "zone_label", "total", "richness")}


def _registration_year(imovel: Dict[str, Any]) -> Optional[int]:
    year = (imovel or {}).get("ano_criacao") or 0
    try:
        return int(year) or None
    except (TypeError, ValueError):
        return None


def _transition_rows(transitions: Dict[Any, Dict[Any, float]], lang: str) -> List[tuple]:
    rows = []
    for src, tgts in (transitions or {}).items():
        for tgt, area in (tgts or {}).items():
            if float(area) <= 0:
                continue
            rows.append((mb.label(int(src), lang), mb.label(int(tgt), lang),
                         float(area), int(src) == int(tgt)))
    return rows


def report_filename(imovel: Dict[str, Any], fmt: str,
                    when: Optional[datetime] = None) -> str:
    """``camposcope_<cod_imovel>_<YYYYMMDD-HHMM>.<fmt>`` (doc/13 §8); the
    square has no code, so its centre point stands in."""
    when = when or datetime.now(timezone.utc)
    stamp = when.strftime("%Y%m%d-%H%M")
    if _is_square(imovel):
        coords = str(imovel.get("coordinates") or "").replace(" ", "")
        lat, _, lon = coords.partition(",")
        slug = f"quadrado_{lat or 'x'}_{lon or 'x'}"
    else:
        slug = str(imovel.get("cod_imovel") or "imovel")
    safe = "".join(c if (c.isalnum() or c in "-_.") else "-" for c in slug)
    return f"camposcope_{safe}_{stamp}.{fmt}"


# --------------------------------------------------------------------------- #
# Figures — built from the snapshot with the screen's own builders
# --------------------------------------------------------------------------- #

def report_figures(*, imovel: Dict[str, Any], zones: List[Dict[str, Any]],
                   history_rows: List[Dict[str, Any]] | None = None,
                   hansen_loss_rows: List[Dict[str, Any]] | None = None,
                   biomass_rows: List[Dict[str, Any]] | None = None,
                   landscape_rows: List[Dict[str, Any]] | None = None,
                   sankey_transitions: Dict[str, Dict[str, float]] | None = None,
                   sankey_year_a: int = 0, sankey_year_b: int = 0,
                   fire_annual_rows: List[Dict[str, Any]] | None = None,
                   focus_zone: str = "imovel", lang: str = "pt",
                   **_ignored: Any) -> Dict[str, dict]:
    """``{key: plotly figure dict}`` for every chart with data, in section
    order. Plain dicts (``fig.to_plotly_json()``), so they can travel to the
    browser for capture and into the HTML unchanged."""
    from ..components import charts
    from .transitions import sankey_figure

    out: Dict[str, dict] = {}

    def zone_rows(rows):
        return [r for r in rows or [] if r.get("zone_key") == focus_zone]

    rows = zone_rows(history_rows)
    if rows:
        fig = charts.land_cover_history_figure(
            rows, lang=lang, registration_year=_registration_year(imovel)).to_plotly_json()
        # The on-screen chart's t=8 margin clips the "registro CAR (year)"
        # label drawn above the plot; a page has room for it.
        margin = fig.setdefault("layout", {}).setdefault("margin", {})
        margin["t"] = max(int(margin.get("t") or 0), 30)
        out["cobertura"] = fig
    if sankey_transitions:
        fig = sankey_figure({int(s): {int(t): float(a) for t, a in tg.items()}
                             for s, tg in sankey_transitions.items()},
                            sankey_year_a, sankey_year_b, lang=lang)
        if fig is not None:
            out["transicoes"] = fig.to_plotly_json()
    rows = zone_rows(hansen_loss_rows)
    if rows:
        out["floresta"] = charts.hansen_figure(rows, lang).to_plotly_json()
    rows = zone_rows(biomass_rows)
    if rows:
        out["biomassa"] = charts.biomass_figure(rows, lang).to_plotly_json()
    if landscape_rows:
        out["paisagem"] = charts.landscape_meff_figure(landscape_rows, lang).to_plotly_json()
    rows = zone_rows(fire_annual_rows)
    if rows:
        out["fogo"] = charts.fire_figure(rows, lang).to_plotly_json()
    return out


def capture_specs(figs: Dict[str, dict]) -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """(prepared figures, export options) for the browser capture script."""
    prepared, opts = {}, {}
    for key, fig in figs.items():
        slot, aspect = FIGURE_LAYOUT.get(key, ("full", 0.56))
        prepared[key] = kit_images.prepare_figure(fig, slot, aspect)
        opts[key] = kit_images.chart_opts(slot, aspect)
    return prepared, opts


# --------------------------------------------------------------------------- #
# The report
# --------------------------------------------------------------------------- #

def build_imovel_report(
    *,
    imovel: Dict[str, Any],
    zones: List[Dict[str, Any]],
    history_rows: List[Dict[str, Any]] | None = None,
    history_provenance: Dict[str, Any] | None = None,
    hansen_loss_rows: List[Dict[str, Any]] | None = None,
    hansen_gain_ha: float = 0.0,
    hansen_provenance: Dict[str, Any] | None = None,
    biomass_rows: List[Dict[str, Any]] | None = None,
    biomass_provenance: Dict[str, Any] | None = None,
    landscape_rows: List[Dict[str, Any]] | None = None,
    landscape_provenance: Dict[str, Any] | None = None,
    connectivity_rows: List[Dict[str, Any]] | None = None,
    connectivity_provenance: Dict[str, Any] | None = None,
    sankey_transitions: Dict[str, Dict[str, float]] | None = None,
    sankey_zone_label: str = "",
    sankey_year_a: int = 0,
    sankey_year_b: int = 0,
    sankey_provenance: Dict[str, Any] | None = None,
    fire_rows: List[Dict[str, Any]] | None = None,
    fire_annual_rows: List[Dict[str, Any]] | None = None,
    fire_provenance: Dict[str, Any] | None = None,
    validacao_matrix: Dict[str, Any] | None = None,
    validacao_zone_label: str = "",
    validacao_provenance: Dict[str, Any] | None = None,
    spot_summary: Dict[str, Any] | None = None,
    spot_provenance: Dict[str, Any] | None = None,
    gbif_zone_rows: List[Any] | None = None,
    overlaps: List[Dict[str, Any]] | None = None,
    overlaps_checked: bool = False,
    overlaps_error: str = "",
    area_calculada_ha: float = 0.0,
    area_delta_ha: float = 0.0,
    area_delta_pct: float = 0.0,
    zones_geojson: Dict[str, Any] | None = None,
    focus_zone: str = "imovel",
    lang: str = "pt",
    options: ReportOptions | None = None,
    figures: Dict[str, dict] | None = None,
    figure_pngs: Dict[str, Optional[bytes]] | None = None,
    figure_errors: Dict[str, str] | None = None,
    maps: List[rk.MapFigure] | None = None,
    map_errors: Dict[str, str] | None = None,
    map_attributions: List[str] | None = None,
    generated_at: Optional[datetime] = None,
    **_ignored: Any,
) -> rk.Report:
    """The whole report as a ``report_kit.Report`` (doc/13 §3 outline).

    ``figures`` are the ``report_figures()`` dicts (built here when omitted);
    ``figure_pngs`` the browser's captures (PDF only — the HTML embeds the
    figure dicts); ``maps`` the ``report_maps.fetch_report_maps`` output.
    Unknown keyword arguments are ignored, so ``**_gather()`` can be splatted
    in as it grows.
    """
    lang = "en" if lang == "en" else "pt"
    opts = options or ReportOptions()
    imovel = imovel or {}
    zones = zones or []
    history_rows = history_rows or []
    hansen_loss_rows = hansen_loss_rows or []
    biomass_rows = biomass_rows or []
    landscape_rows = landscape_rows or []
    connectivity_rows = connectivity_rows or []
    sankey_transitions = sankey_transitions or {}
    fire_rows = fire_rows or []
    fire_annual_rows = fire_annual_rows or []
    validacao_matrix = validacao_matrix or {}
    spot_summary = spot_summary or {}
    gbif_rows = [_gbif_dict(r) for r in (gbif_zone_rows or [])]
    overlaps = overlaps or []
    square = _is_square(imovel)
    if focus_zone not in {z.get("zone_key") for z in zones}:
        focus_zone = "imovel"
    focus_label = rt.zone_label(zones, focus_zone)
    reg_year = _registration_year(imovel)
    T = lambda key, **kw: rt.t(key, lang, **kw)  # noqa: E731

    if figures is None and opts.figures:
        figures = report_figures(
            imovel=imovel, zones=zones, history_rows=history_rows,
            hansen_loss_rows=hansen_loss_rows, biomass_rows=biomass_rows,
            landscape_rows=landscape_rows, sankey_transitions=sankey_transitions,
            sankey_year_a=sankey_year_a, sankey_year_b=sankey_year_b,
            fire_annual_rows=fire_annual_rows, focus_zone=focus_zone, lang=lang)
    figures = figures or {}
    figure_pngs = figure_pngs or {}
    figure_errors = figure_errors or {}

    def figure(key: str, caption: str) -> List[rk.Block]:
        if not opts.figures or key not in figures:
            return []
        slot, aspect = FIGURE_LAYOUT.get(key, ("full", 0.56))
        png = figure_pngs.get(key)
        reason = ""
        if png is None:
            detail = figure_errors.get(key) or (
                "capture needs a browser" if lang == "en" else "captura requer o navegador")
            reason = T("figure_capture_failed", detail=detail)
        return [rk.Figure(key=key, caption=caption, slot=slot, aspect=aspect,
                          fig_json=figures[key], png=png, unavailable_reason=reason)]

    def table(columns, rows, caption, **kw) -> List[rk.Block]:
        if not opts.tables or not rows:
            return []
        return [rk.Table(columns=columns, rows=rows, caption=caption, **kw)]

    sections: List[rk.Section] = []

    # 0 — the disclosure, above everything (C4) --------------------------- #
    sections.append(rk.Section("", [rk.Callout(disclosure_for(imovel, lang),
                                               kind="disclosure")], key="disclosure"))

    # 1 — identification ------------------------------------------------- #
    kv: List[Tuple[str, str]] = []
    if square:
        kv += [(T("kv_kind_square"), T("kv_kind_square_value")),
               (T("kv_coordinates"), str(imovel.get("coordinates") or "—")),
               (T("kv_area_calculada"), fmt_ha(area_calculada_ha, 1, lang))]
    else:
        muni = str(imovel.get("municipio") or "—")
        if imovel.get("cod_municipio_ibge"):
            muni += f" ({imovel['cod_municipio_ibge']})"
        m_fiscal = imovel.get("m_fiscal")
        kv += [
            (T("kv_cod_imovel"), str(imovel.get("cod_imovel") or "—")),
            (T("kv_uf"), str(imovel.get("uf") or "—")),
            (T("kv_municipio"), muni),
            # verbatim CAR fields — never translated, glossed or coloured (C4)
            (T("kv_tipo"), str(imovel.get("tipo_imovel") or "—")),
            (T("kv_status"), str(imovel.get("status_imovel") or "—")),
            (T("kv_condicao"), str(imovel.get("condicao") or "—")),
            (T("kv_dat_criacao"), fmt_date(imovel.get("dat_criacao"), lang)),
            (T("kv_data_atualizacao"), fmt_date(imovel.get("data_atualizacao"), lang)),
            (T("kv_m_fiscal"), fmt_num(m_fiscal, 2, lang) if m_fiscal not in (None, "")
             else "—"),
            (T("kv_area_declarada"), fmt_ha(imovel.get("area_declarada_ha"), 2, lang)),
            (T("kv_area_calculada"), fmt_ha(area_calculada_ha, 2, lang)),
            (T("kv_area_delta"), f"{rt.signed(area_delta_ha, 2, lang)} ha "
                                 f"({rt.signed(area_delta_pct, 1, lang)}"
                                 f"{'' if lang == 'en' else ' '}%)"),
            (T("kv_queried_at"), str(imovel.get("queried_at") or "—")
             .replace("T", " ")[:19]),
        ]
    prop_geom = next((f["geometry"] for f in (zones_geojson or {}).get("features", [])
                      if (f.get("properties") or {}).get("role") == "property"), None)
    ident_blocks: List[rk.Block] = []
    if prop_geom:
        ident_blocks.append(rk.SideBySide(
            rk.KeyValues(kv),
            rk.LocatorMap(prop_geom, T("locator_label"),
                          highlight_ufs=[imovel["uf"]] if imovel.get("uf") else ())))
    else:
        ident_blocks.append(rk.KeyValues(kv))
    if square:
        ident_blocks.append(rk.Paragraph(rt.area_square_text(
            area_calculada_ha, str(imovel.get("coordinates") or ""), lang)))
    else:
        ident_blocks.append(rk.Paragraph(rt.area_text(
            float(imovel.get("area_declarada_ha") or 0.0), area_calculada_ha,
            area_delta_pct, lang)))
    sections.append(rk.Section(T("sec_identification"), ident_blocks, key="identification"))

    # 1b — zones ---------------------------------------------------------- #
    kind_label = {"property": T("kind_square") if square else T("kind_property"),
                  "ring": T("kind_ring")}
    zone_table = [[z.get("zone_label", ""), kind_label.get(z.get("zone_kind"),
                                                           z.get("zone_kind", "")),
                   z.get("radius_m"), float(z.get("area_ha") or 0.0)] for z in zones]
    sections.append(rk.Section(T("sec_zones"), [
        rk.Paragraph(rt.zones_text(zones, lang)),
        rk.Table([T("h_zone"), T("h_kind"), T("h_radius"), T("h_area_ha")], zone_table,
                 T("cap_zones"), align=["l", "l", "r", "r"], decimals=[None, None, 0, 1]),
    ], key="zones"))

    # 1c — overlaps (D7: listed, never dissolved or ranked) ---------------- #
    ov_blocks: List[rk.Block] = [rk.Paragraph(rt.overlaps_text(
        overlaps, overlaps_checked, overlaps_error, square=square, lang=lang))]
    if overlaps and not square:
        ov_blocks.append(rk.Table(
            [T("h_cod"), T("h_overlap_ha"), T("h_overlap_pct")],
            [[o.get("cod_imovel", ""), float(o.get("overlap_ha") or 0.0),
              float(o.get("overlap_pct_do_imovel") or 0.0)] for o in overlaps],
            T("cap_overlaps"), align=["l", "r", "r"], decimals=[None, 2, 2]))
    sections.append(rk.Section(T("sec_overlaps"), ov_blocks, key="overlaps"))

    # 2 — about this report ---------------------------------------------- #
    not_run = T("not_run_reason")
    status: Dict[str, Tuple[str, str]] = {
        "cobertura": ("included", "") if history_rows else ("not_run", not_run),
        "transicoes": ("included", "") if sankey_transitions else ("not_run", not_run),
        "floresta": ("included", "") if (hansen_provenance or hansen_loss_rows)
        else ("not_run", not_run),
        "biomassa": ("included", "") if biomass_rows else ("not_run", not_run),
        "paisagem": ("included", "") if (landscape_rows or connectivity_rows)
        else ("not_run", not_run),
        "fogo": ("included", "") if fire_rows else ("not_run", not_run),
        "validacao": ("included", "") if validacao_matrix.get("matrix")
        else ("not_run", T("validacao_mode_reason")),
        "spot": ("included", "") if spot_summary else ("not_run", not_run),
        "gbif": (("excluded", T("excluded_reason")) if not opts.gbif
                 else ("included", "") if gbif_rows else ("not_run", not_run)),
    }
    map_errors = map_errors or {}
    maps = maps or []
    if not opts.maps:
        maps_status = ("excluded", T("excluded_reason"))
    elif not maps:
        detail = "; ".join(sorted(set(map_errors.values()))) or "—"
        maps_status = ("unavailable", T("maps_failed_reason", detail=detail[:160]))
    elif map_errors:
        maps_status = ("included", T("maps_failed_reason",
                                     detail=", ".join(sorted(map_errors))))
    else:
        maps_status = ("included", "")
    contents = [rk.ContentsItem(T("sec_maps"), *maps_status)]
    contents += [rk.ContentsItem(T(f"sec_{k}"), *status[k]) for k in ANALYSIS_KEYS]
    if opts.appendix:
        contents.append(rk.ContentsItem(T("sec_appendix"), "included"))
    about = [rk.ContentsList(contents),
             rk.Paragraph(rt.about_text(zones, mb.MAPBIOMAS_YEAR_START, mb.MAPBIOMAS_YEAR_END,
                                        ds.HANSEN_GFC["loss_year_start"],
                                        ds.HANSEN_GFC["loss_year_end"], lang))]
    if focus_zone != "imovel":
        about.append(rk.Paragraph(T("about_focus", zone=focus_label)))
    sections.append(rk.Section(T("sec_about"), about, key="about"))

    # 3 — maps ------------------------------------------------------------ #
    if opts.maps and maps:
        sections.append(rk.Section(T("sec_maps"), list(maps), key="maps"))

    # 4 — Cobertura ------------------------------------------------------- #
    if status["cobertura"][0] == "included":
        zone_hist = [r for r in history_rows if r.get("zone_key") == focus_zone]
        years = sorted({int(r["year"]) for r in zone_hist})
        blocks: List[rk.Block] = [rk.Paragraph(T("intro_cobertura",
                                                 start=mb.MAPBIOMAS_YEAR_START,
                                                 end=mb.MAPBIOMAS_YEAR_END))]
        blocks += figure("cobertura", T("cap_cobertura", zone=focus_label))
        if years:
            ya, yb = years[0], years[-1]
            by_class: Dict[int, List[Any]] = {}
            tot = {ya: 0.0, yb: 0.0}
            for r in zone_hist:
                y = int(r["year"])
                if y not in tot:
                    continue
                tot[y] += float(r["area_ha"])
                row = by_class.setdefault(int(r["class_id"]),
                                          [rt.class_name(r, lang), 0.0, 0.0])
                row[1 if y == ya else 2] += float(r["area_ha"])
            trows = [[name, a, 100.0 * a / (tot[ya] or 1), b, 100.0 * b / (tot[yb] or 1)]
                     for name, a, b in by_class.values()]
            trows.sort(key=lambda r: -r[3])
            blocks += table([T("h_class"), f"{ya} (ha)", f"{ya} (%)", f"{yb} (ha)",
                             f"{yb} (%)"], trows,
                            T("cap_cobertura_table", year_a=ya, year_b=yb, zone=focus_label),
                            align=["l", "r", "r", "r", "r"], decimals=[None, 1, 1, 1, 1])
        blocks.append(rk.Paragraph(rt.cobertura_text(history_rows, zones, focus_zone, lang)))
        sections.append(rk.Section(T("sec_cobertura"), blocks, key="cobertura"))

    # 5 — Transições ------------------------------------------------------ #
    if status["transicoes"][0] == "included":
        zl = sankey_zone_label or focus_label
        trs = _transition_rows(sankey_transitions, lang)
        blocks = [rk.Paragraph(T("intro_transicoes", year_a=sankey_year_a,
                                 year_b=sankey_year_b, zone=zl))]
        blocks += figure("transicoes", T("cap_transicoes", year_a=sankey_year_a,
                                         year_b=sankey_year_b, zone=zl))
        top = sorted((r for r in trs if not r[3]), key=lambda r: -r[2])[:10]
        blocks += table([T("h_from"), T("h_to"), T("h_area_ha")],
                        [[s, t, a] for s, t, a, _ in top],
                        T("cap_transicoes_table", year_a=sankey_year_a,
                          year_b=sankey_year_b, zone=zl),
                        align=["l", "l", "r"], decimals=[None, None, 1])
        blocks.append(rk.Paragraph(rt.transitions_text(trs, sankey_year_a, sankey_year_b,
                                                       lang)))
        sections.append(rk.Section(T("sec_transicoes"), blocks, key="transicoes"))

    # 6 — Floresta -------------------------------------------------------- #
    if status["floresta"][0] == "included":
        start, end = ds.HANSEN_GFC["loss_year_start"], ds.HANSEN_GFC["loss_year_end"]
        blocks = [rk.Paragraph(T("intro_floresta", start=start, end=end,
                                 threshold=HANSEN_TREECOVER_THRESHOLD))]
        blocks += figure("floresta", T("cap_floresta", zone=focus_label))
        prow = []
        for z in zones:
            p = rt.hansen_period_totals(hansen_loss_rows, z["zone_key"])
            prow.append([z.get("zone_label", ""), p["ate_2008"], p["2008_ate_registro"],
                         p["apos_registro"], sum(p.values())])
        blocks += table([T("h_zone"), T("h_up_to_2008"), T("h_to_reg"), T("h_after_reg"),
                         T("h_total")], prow, T("cap_floresta_table"),
                        align=["l", "r", "r", "r", "r"], decimals=[None, 1, 1, 1, 1])
        blocks.append(rk.Paragraph(rt.floresta_text(hansen_loss_rows, reg_year, start, end,
                                                    lang)))
        blocks.append(rk.Paragraph(rt.floresta_gain_text(hansen_gain_ha, lang)))
        sections.append(rk.Section(T("sec_floresta"), blocks, key="floresta"))

    # 7 — Biomassa -------------------------------------------------------- #
    if status["biomassa"][0] == "included":
        zb = sorted((r for r in biomass_rows if r.get("zone_key") == focus_zone),
                    key=lambda r: r["year"])
        blocks = [rk.Paragraph(T("intro_biomassa"))]
        blocks += figure("biomassa", T("cap_biomassa", zone=focus_label))
        blocks += table([T("h_year"), T("h_agb"), T("h_agb_total")],
                        [[str(r["year"]), r.get("agb_mean_mgha"), r.get("total_biomass_mg")]
                         for r in zb],
                        T("cap_biomassa_table", zone=focus_label),
                        align=["l", "r", "r"], decimals=[None, 1, 0])
        blocks.append(rk.Paragraph(rt.biomass_text(zb, focus_label, lang)))
        sections.append(rk.Section(T("sec_biomassa"), blocks, key="biomassa"))

    # 8 — Paisagem -------------------------------------------------------- #
    if status["paisagem"][0] == "included":
        blocks = [rk.Paragraph(T("intro_paisagem"))]
        blocks += figure("paisagem", T("cap_paisagem"))
        blocks += table([T("h_zone"), T("h_area_ha"), T("h_patches"), T("h_largest_pct"),
                         T("h_edge_density"), T("h_meff"), T("h_shannon")],
                        [[r.get("zone_label", ""), r.get("area_ha"), r.get("patches"),
                          r.get("largest_patch_pct"), r.get("edge_density"),
                          r.get("meff_ha"), r.get("shannon")] for r in landscape_rows],
                        T("cap_paisagem_table"), align=["l"] + ["r"] * 6,
                        decimals=[None, 1, 0, 1, 1, 1, 2])
        blocks += table([T("h_zone"), T("h_n_frag"), T("h_enn_mean"), T("h_enn_median")],
                        [[r.get("zone_label", ""), r.get("n_fragments"), r.get("enn_mean_m"),
                          r.get("enn_median_m")] for r in connectivity_rows],
                        T("cap_conectividade_table"), align=["l", "r", "r", "r"],
                        decimals=[None, 0, 0, 0])
        if landscape_rows:
            blocks.append(rk.Paragraph(rt.landscape_text(landscape_rows, lang)))
        sections.append(rk.Section(T("sec_paisagem"), blocks, key="paisagem"))

    # 9 — Fogo ------------------------------------------------------------ #
    if status["fogo"][0] == "included":
        blocks = [rk.Paragraph(T("intro_fogo"))]
        blocks += figure("fogo", T("cap_fogo", zone=focus_label))
        blocks += table([T("h_zone"), T("h_fire_hist"), T("h_fire_freq"), T("h_fire_last")],
                        [[r.get("zone_label", ""), r.get("fire_history_pct"),
                          r.get("fire_frequency"),
                          str(rt.year_or_none(r.get("fire_last_year")) or "—")]
                         for r in fire_rows],
                        T("cap_fogo_table"), align=["l", "r", "r", "r"],
                        decimals=[None, 1, 0, None])
        blocks.append(rk.Paragraph(rt.fire_text(fire_rows, zones, focus_zone, lang)))
        sections.append(rk.Section(T("sec_fogo"), blocks, key="fogo"))

    # 10 — Validação ------------------------------------------------------ #
    if status["validacao"][0] == "included":
        from ..config import ibge_vegetation as iv

        labels = iv.GROUP_LABELS_EN if lang == "en" else iv.GROUP_LABELS_PT
        groups = list(validacao_matrix.get("groups") or iv.GROUP_ORDER)
        cells = validacao_matrix.get("matrix") or {}
        vrows = [[labels.get(g, g)] + [float((cells.get(g) or {}).get(g2, 0.0))
                                       for g2 in groups] for g in groups]
        zl = validacao_zone_label or focus_label
        blocks = [rk.Paragraph(T("intro_validacao", zone=zl))]
        blocks += table(["IBGE \\ MapBiomas"] + [labels.get(g, g) for g in groups], vrows,
                        T("cap_validacao_table", zone=zl),
                        align=["l"] + ["r"] * len(groups),
                        decimals=[None] + [1] * len(groups))
        blocks.append(rk.Paragraph(rt.validacao_text(validacao_matrix, lang)))
        sections.append(rk.Section(T("sec_validacao"), blocks, key="validacao"))

    # 11 — SPOT 2008 (D10: dates and the pre-cutoff share, never "2008" alone) #
    if status["spot"][0] == "included":
        blocks = [rk.Paragraph(T("intro_spot")),
                  rk.Paragraph(rt.spot_text(spot_summary, lang))]
        if opts.tables:
            blocks.append(rk.KeyValues([(T("spot_row"),
                                         spot_coverage_line(spot_summary, lang))]))
        sections.append(rk.Section(T("sec_spot"), blocks, key="spot"))

    # 12 — GBIF (optional) ------------------------------------------------- #
    if status["gbif"][0] == "included":
        blocks = [rk.Paragraph(T("intro_gbif"))]
        blocks += table([T("h_zone"), T("h_records"), T("h_species")],
                        [[g.get("zone_label", ""), g.get("total"), g.get("richness")]
                         for g in gbif_rows],
                        T("cap_gbif_table"), align=["l", "r", "r"], decimals=[None, 0, 0])
        focus_g = next((g for g in gbif_rows if g.get("zone_key") == focus_zone),
                       gbif_rows[0])
        blocks.append(rk.Paragraph(rt.gbif_text(focus_g.get("zone_label", ""),
                                                focus_g.get("total"),
                                                focus_g.get("richness"), lang)))
        sections.append(rk.Section(T("sec_gbif"), blocks, key="gbif"))

    # 13 — provenance (C3: SPOT included) ---------------------------------- #
    provs = [p for p in (history_provenance, sankey_provenance, hansen_provenance,
                         biomass_provenance, landscape_provenance,
                         connectivity_provenance, fire_provenance,
                         validacao_provenance, spot_provenance) if p]
    if provs:
        sections.append(rk.Section(T("sec_provenance"), [rk.ProvenanceTable(provs)],
                                   key="provenance"))

    # 14 — sources, citation and the doc/04 §13 attribution block ---------- #
    sources = [f"{name} — {detail} {url}"
               for name, detail, url in (DATA_SOURCES_EN if lang == "en" else DATA_SOURCES)]
    attributions = attribution_block(lang) + [a for a in (map_attributions or []) if a]
    sections.append(rk.Section(T("sec_sources"), [
        rk.Citation(CITATION_TEXT, sources, attributions)], key="sources"))

    # 15 — appendix (optional) --------------------------------------------- #
    if opts.appendix:
        blocks = []
        if history_rows:
            all_years = sorted({int(r["year"]) for r in history_rows})
            pick = sorted({y for y in all_years if y % 5 == 0} | {all_years[0], all_years[-1]})
            acc: Dict[Tuple[str, str], Dict[int, float]] = {}
            order: List[Tuple[str, str]] = []
            for z in zones:
                for r in history_rows:
                    if r.get("zone_key") != z["zone_key"] or int(r["year"]) not in pick:
                        continue
                    key = (z.get("zone_label", ""), rt.class_name(r, lang))
                    if key not in acc:
                        acc[key] = {}
                        order.append(key)
                    acc[key][int(r["year"])] = acc[key].get(int(r["year"]), 0.0) + float(
                        r["area_ha"])
            arows = [[zl, cls] + [acc[(zl, cls)].get(y) for y in pick] for zl, cls in order]
            blocks.append(rk.Table([T("h_zone"), T("h_class")] + [str(y) for y in pick], arows,
                                   T("cap_appendix_cobertura"),
                                   align=["l", "l"] + ["r"] * len(pick), max_rows=0,
                                   decimals=[None, None] + [0] * len(pick)))
        if fire_annual_rows:
            fyears = sorted({int(r["year"]) for r in fire_annual_rows})
            fz = [z for z in zones if any(r.get("zone_key") == z["zone_key"]
                                          for r in fire_annual_rows)]
            val = {(r["zone_key"], int(r["year"])): r.get("fire_pct")
                   for r in fire_annual_rows}
            frows = [[str(y)] + [val.get((z["zone_key"], y)) for z in fz] for y in fyears]
            blocks.append(rk.Table([T("h_year")] + [z.get("zone_label", "") for z in fz],
                                   frows, T("cap_appendix_fogo"),
                                   align=["l"] + ["r"] * len(fz), max_rows=0,
                                   decimals=[None] + [1] * len(fz)))
        if blocks:
            sections.append(rk.Section(T("sec_appendix"), blocks, key="appendix"))

    subject_bits = [str(imovel.get("cod_imovel") or imovel.get("coordinates") or "")]
    if imovel.get("municipio"):
        subject_bits.append(f"{imovel['municipio']}/{imovel.get('uf', '')}")
    meta = rk.ReportMeta(
        app="Camposcope", app_url=APP_URL, app_version=APP_VERSION,
        title=T("report_title_square" if square else "report_title"),
        subject=" · ".join(b for b in subject_bits if b), lang=lang,
        generated_at=generated_at or datetime.now(timezone.utc),
        brand=rk.Brand(accent=ACCENT, app_line="umaterra · Camposcope"))
    return rk.Report(meta, sections)


def render(report: rk.Report, fmt: str) -> bytes:
    """``fmt`` "pdf" or "html"."""
    return rk.render_pdf(report) if fmt == "pdf" else rk.render_html(report)


__all__ = ["APP_VERSION", "ReportOptions", "FIGURE_LAYOUT", "ANALYSIS_KEYS",
           "build_imovel_report", "report_figures", "capture_specs",
           "report_filename", "render"]
