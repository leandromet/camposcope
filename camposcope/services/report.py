"""A single, self-contained HTML report — figures and tables laid out for
reading (or printing to PDF) the way a manuscript's site-characterisation
section would be, rather than five separate chart screenshots pasted in by
hand.

Ported in structure from Naturametrics' ``services/report.py`` — same three-
way split (this report vs. the per-chart/per-table icons in
``components/results.py`` and friends vs. the ODS workbook in
``services/exports.py``), same reasoning for embedding Plotly **inline**
rather than via CDN or kaleido (a headless-Chromium dependency this app does
not otherwise carry). See that module's docstring for the fuller argument;
it applies here unchanged.

The one structural difference from Naturametrics: Camposcope has *zones*
(the property plus its rings), not buffer radii, and no multi-property
selection — so where the source report iterates ``BUFFER_RADII_KM``, this one
iterates whatever ``zones`` the caller passed (property first, rings after,
however many ``services/zones.py`` built).
"""

from __future__ import annotations

import html
import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import plotly.io as pio

from ..components import charts
from ..config import mapbiomas as mb
from ..config.citation import APP_URL, CITATION_TEXT, DATA_SOURCES
from .exports import _provenance_rows
from .provenance import Provenance

logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _esc(value: Any) -> str:
    """Bare-minimum HTML-escaping for a cell/heading. Every value here comes
    from a computed number, a class label, a CAR field or this app's own
    identity strings — never third-party free text — but escaping costs
    nothing, and a stray "<" in a município name should not be able to break
    the page."""
    if isinstance(value, float):
        value = f"{value:,.2f}".rstrip("0").rstrip(".")
    return html.escape(str(value))


def _table_html(df: pd.DataFrame, headers: dict[str, str],
                caption: str, empty_note: str) -> str:
    if df is None or df.empty:
        return (f'<p class="cs-figure-caption">{_esc(caption)}</p>'
                f'<p class="cs-empty">{_esc(empty_note)}</p>')
    cols = [c for c in headers if c in df.columns]
    head = "".join(f"<th>{_esc(headers[c])}</th>" for c in cols)
    rows = "".join(
        "<tr>" + "".join(f"<td>{_esc(row[c])}</td>" for c in cols) + "</tr>"
        for _, row in df.iterrows()
    )
    return (
        f'<p class="cs-figure-caption">{_esc(caption)}</p>'
        f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"
    )


def _fig_html(fig, div_id: str, first: bool) -> str:
    return pio.to_html(
        fig, full_html=False, include_plotlyjs=("inline" if first else False),
        div_id=div_id,
        config={"displayModeBar": False, "displaylogo": False, "responsive": True},
    )


_CSS = """
:root { color-scheme: light; }
body { font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
       color: #1a1a1a; max-width: 960px; margin: 2rem auto; padding: 0 1.5rem;
       line-height: 1.5; }
h1 { font-size: 1.4rem; margin-bottom: 0.2rem; }
h2 { font-size: 1.1rem; margin-top: 2.5rem; border-bottom: 2px solid #f5a524;
     padding-bottom: 0.3rem; }
h3 { font-size: 0.95rem; margin-top: 1.75rem; color: #333; }
.cs-subtitle { color: #666; font-size: 0.9rem; margin-top: 0; }
.cs-meta { font-size: 0.82rem; color: #555; }
.cs-meta dt { font-weight: 600; display: inline; }
.cs-meta dd { display: inline; margin: 0 1.2rem 0 0.3rem; }
.cs-figure-caption { font-size: 0.85rem; font-weight: 600; margin: 0 0 0.3rem 0; }
.cs-caveat { font-size: 0.78rem; color: #a15c00; background: #fff8e6;
             border: 1px solid #f0d59b; border-radius: 4px; padding: 0.5rem 0.75rem;
             margin: 0.5rem 0 1.5rem 0; }
table { border-collapse: collapse; width: 100%; font-size: 0.8rem; margin-bottom: 1.5rem; }
th, td { border: 1px solid #ddd; padding: 0.3rem 0.5rem; text-align: right; }
th { background: #f3f3f3; text-align: right; }
th:first-child, td:first-child { text-align: left; }
.cs-empty { color: #888; font-size: 0.85rem; }
.cs-footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid #ddd;
             font-size: 0.78rem; color: #555; }
.cs-footer ul { padding-left: 1.2rem; }
@media print {
  body { max-width: none; margin: 0; padding: 0 0.5in; }
  h2.cs-page-break { page-break-before: always; }
  table { font-size: 9pt; }
}
"""


def imovel_report_html(
    imovel: dict[str, Any],
    zones: list[dict[str, Any]],
    history_rows: list[dict[str, Any]],
    history_provenance: dict[str, Any] | None = None,
    hansen_loss_rows: list[dict[str, Any]] | None = None,
    hansen_gain_ha: float = 0.0,
    hansen_provenance: dict[str, Any] | None = None,
    biomass_rows: list[dict[str, Any]] | None = None,
    biomass_provenance: dict[str, Any] | None = None,
    landscape_rows: list[dict[str, Any]] | None = None,
    landscape_provenance: dict[str, Any] | None = None,
    connectivity_rows: list[dict[str, Any]] | None = None,
    connectivity_provenance: dict[str, Any] | None = None,
    sankey_transitions: dict[str, dict[str, float]] | None = None,
    sankey_zone_label: str = "",
    sankey_year_a: int = 0,
    sankey_year_b: int = 0,
    sankey_provenance: dict[str, Any] | None = None,
    fire_rows: list[dict[str, Any]] | None = None,
    fire_annual_rows: list[dict[str, Any]] | None = None,
    fire_provenance: dict[str, Any] | None = None,
    validacao_matrix: dict[str, Any] | None = None,
    validacao_zone_label: str = "",
    validacao_provenance: dict[str, Any] | None = None,
    include_figures: bool = True,
    include_tables: bool = True,
    lang: str = "pt",
) -> tuple[bytes, str]:
    """One HTML page for the property currently on screen.

    Same already-computed-state contract as ``services.exports.imovel_workbook``
    (same argument list, in fact) — nothing here is recomputed.
    """
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

    title = "Relatório do imóvel — Camposcope" if lang == "pt" \
        else "Property report — Camposcope"
    parts: list[str] = [f"<h1>{_esc(title)}</h1>"]

    subtitle_bits = [str(imovel.get("cod_imovel", ""))]
    if imovel.get("municipio"):
        subtitle_bits.append(f"{imovel['municipio']}/{imovel.get('uf', '')}")
    parts.append(f'<p class="cs-subtitle">{_esc(" · ".join(subtitle_bits))}</p>')

    parts.append('<dl class="cs-meta">')
    meta_rows = [
        ("Gerado em (UTC)" if lang == "pt" else "Generated (UTC)", _now_iso()),
        ("Área declarada (ha)" if lang == "pt" else "Declared area (ha)",
         imovel.get("area_declarada_ha", "")),
        ("Condição" if lang == "pt" else "Condition", imovel.get("condicao", "")),
        ("Situação" if lang == "pt" else "Status", imovel.get("status_imovel", "")),
        ("Data de criação" if lang == "pt" else "Registration date",
         imovel.get("dat_criacao", "")),
        ("Anos (uso da terra)" if lang == "pt" else "Years (land use)",
         f"{mb.MAPBIOMAS_YEAR_START}–{mb.MAPBIOMAS_YEAR_END}"),
        ("Zonas" if lang == "pt" else "Zones",
         ", ".join(z["zone_label"] for z in zones)),
    ]
    for k, v in meta_rows:
        parts.append(f"<dt>{_esc(k)}:</dt><dd>{_esc(v)}</dd>")
    parts.append("</dl>")

    fig_count = 0
    first_fig = True

    def add_figure(fig, div_prefix: str, caption: str) -> None:
        nonlocal fig_count, first_fig
        fig_count += 1
        prefix = "Figura" if lang == "pt" else "Figure"
        parts.append(f'<p class="cs-figure-caption">{prefix} {fig_count}. '
                     f'{_esc(caption)}</p>')
        parts.append(_fig_html(fig, f"{div_prefix}-{fig_count}", first_fig))
        first_fig = False

    if include_figures:
        parts.append(f'<h2>{"Figuras" if lang == "pt" else "Figures"}</h2>')
        registration_year = imovel.get("ano_criacao") or None

        for zone in zones:
            zk, zl = zone["zone_key"], zone["zone_label"]
            zone_history = [r for r in history_rows if r["zone_key"] == zk]
            if zone_history:
                add_figure(
                    charts.land_cover_history_figure(
                        zone_history, lang=lang,
                        registration_year=registration_year),
                    "cs-hist",
                    (f"Cobertura e uso da terra — {zl}." if lang == "pt"
                     else f"Land use and cover — {zl}."),
                )

        for zone in zones:
            zk, zl = zone["zone_key"], zone["zone_label"]
            zone_loss = [r for r in hansen_loss_rows if r["zone_key"] == zk]
            if zone_loss:
                add_figure(
                    charts.hansen_figure(zone_loss, lang),
                    "cs-floresta",
                    (f"Perda florestal (Hansen) — {zl}." if lang == "pt"
                     else f"Forest loss (Hansen) — {zl}."),
                )

        for zone in zones:
            zk, zl = zone["zone_key"], zone["zone_label"]
            zone_biomass = [r for r in biomass_rows if r["zone_key"] == zk]
            if zone_biomass:
                add_figure(
                    charts.biomass_figure(zone_biomass, lang),
                    "cs-biomassa",
                    (f"Biomassa acima do solo (ESA CCI) — {zl}." if lang == "pt"
                     else f"Above-ground biomass (ESA CCI) — {zl}."),
                )

        if landscape_rows:
            add_figure(
                charts.landscape_meff_figure(landscape_rows, lang),
                "cs-paisagem",
                ("Tamanho efetivo de malha (Meff) por zona." if lang == "pt"
                 else "Effective mesh size (Meff) per zone."),
            )

        for zone in zones:
            zk, zl = zone["zone_key"], zone["zone_label"]
            zone_fire = [r for r in fire_annual_rows if r["zone_key"] == zk]
            if zone_fire:
                add_figure(
                    charts.fire_figure(zone_fire, lang),
                    "cs-fogo",
                    (f"Histórico de fogo (MapBiomas Fogo) — {zl}." if lang == "pt"
                     else f"Fire history (MapBiomas Fire) — {zl}."),
                )

        if sankey_transitions:
            from . import transitions as tr

            transitions_int = {
                int(src): {int(tgt): area for tgt, area in tgts.items()}
                for src, tgts in sankey_transitions.items()
            }
            fig = tr.sankey_figure(transitions_int, sankey_year_a, sankey_year_b,
                                   lang=lang)
            if fig is not None:
                add_figure(
                    fig, "cs-sankey",
                    (f"Transições {sankey_year_a}→{sankey_year_b} — "
                     f"{sankey_zone_label}." if lang == "pt" else
                     f"Transitions {sankey_year_a}→{sankey_year_b} — "
                     f"{sankey_zone_label}."),
                )

        if fig_count == 0:
            parts.append(f'<p class="cs-empty">'
                         f'{"Nenhuma figura disponível ainda." if lang == "pt" else "No figures available yet."}'
                         f"</p>")

    table_count = 0

    def add_table(df: pd.DataFrame, headers: dict[str, str], caption: str,
                  empty_note: str) -> None:
        nonlocal table_count
        table_count += 1
        prefix = "Tabela" if lang == "pt" else "Table"
        parts.append(_table_html(df, headers, f"{prefix} {table_count}. {caption}",
                                 empty_note))

    if include_tables:
        heading_class = ' class="cs-page-break"' if include_figures else ""
        parts.append(f'<h2{heading_class}>{"Tabelas" if lang == "pt" else "Tables"}</h2>')

        zones_df = pd.DataFrame(zones)
        add_table(
            zones_df,
            {"zone_label": "Zona" if lang == "pt" else "Zone",
             "zone_kind": "Tipo" if lang == "pt" else "Kind",
             "radius_m": "Raio (m)" if lang == "pt" else "Radius (m)",
             "area_ha": "Área (ha)" if lang == "pt" else "Area (ha)"},
            "Zonas analisadas — o imóvel e seus anéis de vizinhança."
            if lang == "pt" else
            "Analysed zones — the property and its neighbourhood rings.",
            "",
        )

        history_df = pd.DataFrame(history_rows)
        if not history_df.empty:
            latest_year = int(history_df["year"].max())
            latest = history_df[history_df["year"] == latest_year]
            name_col = "class_en" if lang == "en" else "class_pt"
            latest = latest.sort_values("area_ha", ascending=False)
        else:
            latest, latest_year, name_col = pd.DataFrame(), None, "class_pt"
        add_table(
            latest, {"zone_label": "Zona" if lang == "pt" else "Zone",
                    name_col: "Classe" if lang == "pt" else "Class",
                    "area_ha": "Área (ha)" if lang == "pt" else "Area (ha)"},
            (f"Cobertura em {latest_year}, por zona." if latest_year and lang == "pt"
             else f"Land cover in {latest_year}, per zone." if latest_year
             else "Cobertura." if lang == "pt" else "Land cover."),
            "Cobertura ainda não calculada." if lang == "pt"
            else "Land cover not computed yet.",
        )

        loss_df = pd.DataFrame(hansen_loss_rows)
        if not loss_df.empty:
            labels = charts.hansen_period_labels(lang)
            loss_df = loss_df.copy()
            loss_df["period_label"] = loss_df["period"].map(
                lambda p: labels.get(p, p))
        add_table(
            loss_df,
            {"zone_label": "Zona" if lang == "pt" else "Zone",
             "year": "Ano" if lang == "pt" else "Year",
             "area_ha": "Perda (ha)" if lang == "pt" else "Loss (ha)",
             "period_label": "Período" if lang == "pt" else "Period"},
            (f"Perda florestal (Hansen) por ano e zona. Ganho sem data: "
             f"{hansen_gain_ha:,.1f} ha." if lang == "pt" else
             f"Forest loss (Hansen) by year and zone. Undated gain: "
             f"{hansen_gain_ha:,.1f} ha."),
            "Floresta ainda não calculada." if lang == "pt"
            else "Forest change not computed yet.",
        )

        biomass_df = pd.DataFrame(biomass_rows)
        add_table(
            biomass_df,
            {"zone_label": "Zona" if lang == "pt" else "Zone",
             "year": "Ano" if lang == "pt" else "Year",
             "agb_mean_mgha": "Mg/ha", "total_biomass_mg": "Total (Mg)"},
            "Biomassa acima do solo (ESA CCI), por zona." if lang == "pt"
            else "Above-ground biomass (ESA CCI), per zone.",
            "Biomassa ainda não calculada." if lang == "pt"
            else "Biomass not computed yet.",
        )

        landscape_df = pd.DataFrame(landscape_rows)
        add_table(
            landscape_df,
            {"zone_label": "Zona" if lang == "pt" else "Zone",
             "area_ha": "Área (ha)" if lang == "pt" else "Area (ha)",
             "patches": "Fragmentos" if lang == "pt" else "Patches",
             "patch_density": "Densidade" if lang == "pt" else "Density",
             "largest_patch_pct": "Maior (%)" if lang == "pt" else "Largest (%)",
             "edge_density": "Borda" if lang == "pt" else "Edge",
             "meff_ha": "Meff (ha)",
             "shannon": "Shannon", "simpson": "Simpson"},
            "Métricas de paisagem por zona (NP, PD, LPI, ED, Meff, diversidade)."
            if lang == "pt" else
            "Landscape metrics per zone (NP, PD, LPI, ED, Meff, diversity).",
            "Paisagem ainda não calculada." if lang == "pt"
            else "Landscape metrics not computed yet.",
        )

        connectivity_df = pd.DataFrame(connectivity_rows)
        add_table(
            connectivity_df,
            {"zone_label": "Zona" if lang == "pt" else "Zone",
             "n_fragments": "Fragmentos" if lang == "pt" else "Fragments",
             "enn_mean_m": "Dist. média (m)" if lang == "pt" else "Mean dist. (m)",
             "enn_median_m": "Mediana (m)" if lang == "pt" else "Median (m)"},
            "Conectividade entre fragmentos de floresta (vizinho mais próximo)."
            if lang == "pt" else
            "Connectivity between forest fragments (nearest neighbour).",
            "Conectividade ainda não calculada (opcional)." if lang == "pt"
            else "Connectivity not computed yet (optional).",
        )

        transitions_rows = [
            {"classe_origem": mb.label(int(src), lang),
             "classe_destino": mb.label(int(tgt), lang), "area_ha": round(float(area), 2)}
            for src, tgts in sankey_transitions.items()
            for tgt, area in tgts.items()
        ]
        transitions_df = pd.DataFrame(transitions_rows)
        if not transitions_df.empty:
            transitions_df = transitions_df.sort_values("area_ha", ascending=False)
        add_table(
            transitions_df,
            {"classe_origem": "De" if lang == "pt" else "From",
             "classe_destino": "Para" if lang == "pt" else "To",
             "area_ha": "Área (ha)" if lang == "pt" else "Area (ha)"},
            (f"Transições {sankey_year_a}→{sankey_year_b} — {sankey_zone_label}."
             if sankey_zone_label else
             ("Transições." if lang == "pt" else "Transitions.")),
            "Transições ainda não calculadas." if lang == "pt"
            else "Transitions not computed yet.",
        )

        fire_df = pd.DataFrame(fire_rows)
        add_table(
            fire_df,
            {"zone_label": "Zona" if lang == "pt" else "Zone",
             "fire_history_pct": "Histórico (%)" if lang == "pt" else "History (%)",
             "fire_frequency": "Frequência" if lang == "pt" else "Frequency",
             "fire_last_year": "Última queimada" if lang == "pt" else "Last fire"},
            "Fogo — resumo por zona (MapBiomas Fogo)." if lang == "pt"
            else "Fire — summary per zone (MapBiomas Fire).",
            "Fogo ainda não calculado." if lang == "pt"
            else "Fire not computed yet.",
        )

        if validacao_matrix:
            cells = validacao_matrix.get("matrix") or {}
            from ..config import ibge_vegetation as iv

            val_rows = [
                {"ibge": iv.GROUP_LABELS_PT.get(g_ibge, g_ibge),
                 "mapbiomas": iv.GROUP_LABELS_PT.get(g_mb, g_mb),
                 "pct_area": round(float(pct), 2)}
                for g_ibge, row in cells.items()
                for g_mb, pct in row.items() if float(pct) > 0
            ]
            val_df = pd.DataFrame(val_rows)
            if not val_df.empty:
                val_df = val_df.sort_values("pct_area", ascending=False)
            add_table(
                val_df,
                {"ibge": "IBGE", "mapbiomas": "MapBiomas",
                 "pct_area": "% da área" if lang == "pt" else "% of area"},
                (f"Validação IBGE × MapBiomas — {validacao_zone_label}."
                 if lang == "pt" else
                 f"IBGE × MapBiomas validation — {validacao_zone_label}."),
                "",
            )

    provenances = [
        Provenance(**p) for p in (
            history_provenance, hansen_provenance, biomass_provenance,
            landscape_provenance, connectivity_provenance,
            sankey_provenance, fire_provenance, validacao_provenance,
        ) if p
    ]
    if provenances:
        parts.append(f'<h2>{"Proveniência" if lang == "pt" else "Provenance"}</h2>')
        prov_rows = [row for pr in provenances for row in _provenance_rows(pr)]
        head = ("<th>Campo</th><th>Valor</th>" if lang == "pt"
               else "<th>Field</th><th>Value</th>")
        body = "".join(
            f"<tr><td>{_esc(k)}</td><td>{_esc(v)}</td></tr>" for k, v in prov_rows)
        parts.append(f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")

    parts.append('<div class="cs-footer">')
    parts.append(f"<p>{_esc(CITATION_TEXT)}</p>")
    parts.append("<ul>")
    for name, detail, url in DATA_SOURCES:
        parts.append(f'<li>{_esc(name)} — {_esc(detail)} '
                     f'<a href="{_esc(url)}">{_esc(url)}</a></li>')
    parts.append("</ul>")
    parts.append(f'<p><a href="{_esc(APP_URL)}">{_esc(APP_URL)}</a> · '
                 f"Camposcope v{APP_VERSION}</p>")
    parts.append("</div>")

    doc = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{_esc(title)}</title><style>{_CSS}</style></head><body>"
        + "".join(parts) + "</body></html>"
    )

    label = imovel.get("cod_imovel") or "imovel"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"camposcope_relatorio_{label}_{ts}.html"
    data = doc.encode("utf-8")
    logger.info("Property report: %s (%s KiB, %s figures, %s tables)",
               name, len(data) // 1024, fig_count, table_count)
    return data, name
