"""Building the downloadable spreadsheet.

One ODS workbook per property — the same "one file, tabs not a ZIP"
reasoning as Naturametrics' ``services/exports.py`` (see ``services/ods.py``'s
own docstring), applied to a single CAR property instead of a bulk selection:
Camposcope has no multi-property selection to make a second, bulk-shaped
export meaningful for, so there is only ever one workbook shape here.

Constraint **C6** (doc/01-premises.md, ported) is enforced the same way it is
upstream: the workbook always starts with a ``metadados`` tab built from
whichever :class:`~camposcope.services.provenance.Provenance` records the
state class has already collected (``state/_analysis.py``,
``state/_transitions.py``). Nothing here is recomputed — the workbook reads
whatever is already on screen, so the file and the screen cannot disagree
(doc/11-style discipline, ported from Naturametrics).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

import pandas as pd

from ..config import mapbiomas as mb
from ..config.citation import APP_URL, CITATION_TEXT, DATA_SOURCES
from . import gbif_export, ods
from .provenance import Provenance

logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# --------------------------------------------------------------------------- #
# The metadata tab — ported verbatim in shape from Naturametrics'
# services/exports.py (same two helpers, same constraint C6 reasoning).
# --------------------------------------------------------------------------- #

def _provenance_rows(prov: Provenance) -> list[list[Any]]:
    """One provenance record flattened into key/value rows."""
    d = prov.to_dict()
    rows: list[list[Any]] = [
        [f"— {d['name']} —", ""],
        ["  conjunto de dados", d["dataset_id"]],
        ["  bandas", f"{len(d['bands'])} ({d['bands'][0]}…{d['bands'][-1]})"
                     if d["bands"] else ""],
        ["  escala (m)", d["scale_m"]],
        ["  redutor", d["reducer"]],
        ["  base de área", d["pixel_area_basis"]],
        ["  tileScale", d["tile_scale"]],
        ["  maxPixels", d["max_pixels"]],
        ["  calculado em", d["computed_at"]],
        ["  resultado degradado", bool(d["degraded"])],
    ]
    for note in d.get("notes") or []:
        rows.append(["  aviso", note])
    for key, value in (d.get("extra") or {}).items():
        rows.append([f"  {key}", str(value)])
    return rows


def _metadata_sheet(title: str, context: Sequence[Sequence[Any]],
                    provenances: Iterable[Provenance]) -> ods.Sheet:
    """The tab every workbook opens with — prose plus key/value pairs, not raw
    JSON: this is the sheet somebody reads months later to decide whether they
    can defend the numbers beside it."""
    rows: list[list[Any]] = [
        ["Camposcope — " + title, ""],
        ["gerado em (UTC)", _now_iso()],
        ["versão do aplicativo", APP_VERSION],
        ["endereço", APP_URL],
        ["", ""],
    ]
    rows.extend([list(r) for r in context])
    rows.append(["", ""])
    rows.append(["PROVENIÊNCIA", "cada consulta ao Earth Engine que gerou estes dados"])
    for prov in provenances:
        rows.extend(_provenance_rows(prov))
        rows.append(["", ""])

    rows.append(["COMO CITAR", ""])
    rows.append(["citação", CITATION_TEXT])
    rows.append(["", ""])
    rows.append(["ATRIBUIÇÕES OBRIGATÓRIAS", "cite as bases usadas ao publicar"])
    for name, detail, url in DATA_SOURCES:
        rows.append([name, f"{detail} {url}"])
    return ods.Sheet("metadados", ["campo", "valor"], rows)


def _classes_sheet() -> ods.Sheet:
    """The MapBiomas code → name → colour dictionary."""
    rows = [[cid, mb.label(cid, "pt"), mb.label(cid, "en"), mb.color(cid)]
            for cid in sorted(mb.MAPBIOMAS_LABELS_PT)]
    return ods.Sheet("classes_mapbiomas",
                     ["class_id", "classe_pt", "class_en", "cor_hex"], rows)


# --------------------------------------------------------------------------- #
# Per-tab sheets — plain DataFrame builders, one per results tab. Each reads
# exactly the rows its tab already has in state; none of this recomputes
# anything (see module docstring).
# --------------------------------------------------------------------------- #

def _zones_sheet(zones: list[dict[str, Any]]) -> ods.Sheet:
    df = pd.DataFrame(zones, columns=["zone_key", "zone_label", "zone_kind",
                                      "radius_m", "area_ha"])
    return ods.sheet_from_dataframe("zonas", df)


def _cobertura_sheet(history_rows: list[dict[str, Any]]) -> ods.Sheet:
    df = pd.DataFrame(history_rows) if history_rows else pd.DataFrame(
        columns=["zone_key", "zone_label", "year", "class_id", "pixels",
                "area_ha", "class_pt", "class_en", "color"])
    return ods.sheet_from_dataframe(
        "cobertura", df,
        ["zone_key", "zone_label", "year", "class_id", "class_pt", "class_en",
         "pixels", "area_ha"],
    )


def _floresta_sheet(hansen_loss_rows: list[dict[str, Any]],
                    gain_ha: float) -> tuple[ods.Sheet, ods.Sheet]:
    df = pd.DataFrame(hansen_loss_rows) if hansen_loss_rows else pd.DataFrame(
        columns=["zone_key", "zone_label", "year", "period", "area_ha"])
    loss = ods.sheet_from_dataframe(
        "floresta_perda", df,
        ["zone_key", "zone_label", "year", "period", "area_ha"])
    gain = ods.Sheet("floresta_ganho", ["ganho_sem_data_ha"], [[round(gain_ha, 4)]])
    return loss, gain


def _biomassa_sheet(biomass_rows: list[dict[str, Any]]) -> ods.Sheet:
    df = pd.DataFrame(biomass_rows) if biomass_rows else pd.DataFrame(
        columns=["zone_key", "zone_label", "year", "agb_mean_mgha",
                "total_biomass_mg"])
    return ods.sheet_from_dataframe(
        "biomassa", df,
        ["zone_key", "zone_label", "year", "agb_mean_mgha", "total_biomass_mg"])


def _transicoes_sheet(sankey_transitions: dict[str, dict[str, float]],
                      zone_label: str, year_a: int, year_b: int,
                      lang: str = "pt") -> ods.Sheet:
    """Flattened src → tgt transitions for whichever single zone was last
    computed (Sankey is per-zone, on demand — see state/_transitions.py)."""
    rows = [
        {"zona": zone_label, "ano_de": year_a, "ano_para": year_b,
         "classe_origem": mb.label(int(src), lang),
         "classe_destino": mb.label(int(tgt), lang), "area_ha": round(float(area), 4)}
        for src, tgts in sankey_transitions.items()
        for tgt, area in tgts.items()
    ]
    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["zona", "ano_de", "ano_para", "classe_origem",
                "classe_destino", "area_ha"])
    if not df.empty:
        df = df.sort_values("area_ha", ascending=False)
    return ods.sheet_from_dataframe("transicoes", df)


def _fogo_sheet(fire_rows: list[dict[str, Any]],
               fire_annual_rows: list[dict[str, Any]]) -> tuple[ods.Sheet, ods.Sheet]:
    summary_df = pd.DataFrame(fire_rows) if fire_rows else pd.DataFrame(
        columns=["zone_key", "zone_label", "fire_history_pct", "fire_frequency",
                "fire_last_year", "area_ha"])
    annual_df = pd.DataFrame(fire_annual_rows) if fire_annual_rows else pd.DataFrame(
        columns=["zone_key", "zone_label", "year", "fire_pct"])
    return (ods.sheet_from_dataframe("fogo_resumo", summary_df),
           ods.sheet_from_dataframe("fogo_anual", annual_df))


def _paisagem_sheet(landscape_rows: list[dict[str, Any]]) -> ods.Sheet:
    df = pd.DataFrame(landscape_rows) if landscape_rows else pd.DataFrame(
        columns=["zone_key", "zone_label", "area_ha", "patches", "patch_density",
                "largest_patch_ha", "largest_patch_pct", "edge_m", "edge_density",
                "mean_patch_ha", "patch_area_sq_ha", "meff_ha", "shannon",
                "simpson", "simpson_evenness"])
    return ods.sheet_from_dataframe("paisagem", df)


def _conectividade_sheet(connectivity_rows: list[dict[str, Any]]) -> ods.Sheet:
    df = pd.DataFrame(connectivity_rows) if connectivity_rows else pd.DataFrame(
        columns=["zone_key", "zone_label", "n_fragments", "enn_mean_m",
                "enn_median_m"])
    return ods.sheet_from_dataframe("conectividade", df)


def _gbif_sheets(gbif_zone_rows: list[Any]) -> list[ods.Sheet]:
    """One sheet per zone, same species-table shape as the GBIF tab's own
    dedicated export (services/gbif_export.py) — reused rather than
    reimplemented, so a species list means the same thing whether it arrived
    via this bundled workbook or the GBIF tab's own download button.

    Prefixed ``gbif_`` (not ``especies_``) to keep it visually distinct from
    the workbook's other per-tab sheets in a spreadsheet's tab bar.
    """
    return [
        ods.Sheet(
            f"gbif_{gbif_export._zone_slug(index, str(getattr(row, 'zone_key', index)))}",
            gbif_export.SPECIES_COLUMNS,
            gbif_export._species_rows(row),
        )
        for index, row in enumerate(gbif_zone_rows)
    ]


def _validacao_sheet(matrix: dict[str, Any], zone_label: str) -> ods.Sheet:
    """The 6×6 IBGE×MapBiomas bucket matrix, flattened — every cell, not only
    the non-zero ones shown on screen (a CSV/ODS reader can filter zeros
    themselves; hiding them here would be a second, silent filter)."""
    from ..config import ibge_vegetation as iv

    cells = matrix.get("matrix") or {}
    rows = [
        {"zona": zone_label, "ibge": iv.GROUP_LABELS_PT.get(g_ibge, g_ibge),
         "mapbiomas": iv.GROUP_LABELS_PT.get(g_mb, g_mb),
         "pct_area": round(float(pct), 4)}
        for g_ibge, row in cells.items()
        for g_mb, pct in row.items()
    ]
    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["zona", "ibge", "mapbiomas", "pct_area"])
    return ods.sheet_from_dataframe("validacao_ibge", df)


# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #

def imovel_workbook(
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
    gbif_zone_rows: list[Any] | None = None,
    include_gbif: bool = False,
    lang: str = "pt",
) -> tuple[bytes, str]:
    """One spreadsheet for the property currently on screen.

    Every argument is already-computed state (``.to_dict("records")``/
    ``Provenance.to_dict()``), matching every ``run_*`` handler in
    ``state/_analysis.py`` and ``state/_transitions.py`` — nothing is
    recomputed here (doc/11 §5, ported from Naturametrics).
    """

    def revive(d: dict[str, Any] | None) -> Provenance | None:
        return Provenance(**d) if d else None

    history_prov = revive(history_provenance)
    hansen_prov = revive(hansen_provenance)
    biomass_prov = revive(biomass_provenance)
    landscape_prov = revive(landscape_provenance)
    connectivity_prov = revive(connectivity_provenance)
    sankey_prov = revive(sankey_provenance)
    fire_prov = revive(fire_provenance)
    validacao_prov = revive(validacao_provenance)

    context: list[list[Any]] = [
        ["ESCOPO", "imóvel do CAR"],
        ["código do imóvel", imovel.get("cod_imovel", "")],
        ["UF", imovel.get("uf", "")],
        ["município", imovel.get("municipio", "")],
        ["área declarada (ha)", imovel.get("area_declarada_ha", "")],
        ["condição", imovel.get("condicao", "")],
        ["situação", imovel.get("status_imovel", "")],
        ["data de criação", imovel.get("dat_criacao", "")],
        ["ano de registro", imovel.get("ano_criacao", "")],
        ["", ""],
        ["anos (uso da terra)", f"{mb.MAPBIOMAS_YEAR_START}–{mb.MAPBIOMAS_YEAR_END}"],
    ]
    if not history_rows:
        context.append([
            "AVISO — aba cobertura",
            "Ainda não calculada quando este arquivo foi gerado.",
        ])
    if not hansen_loss_rows:
        context.append([
            "AVISO — abas floresta_*",
            "Ainda não calculadas — clique «Calcular» na aba Floresta e "
            "baixe novamente.",
        ])
    if not biomass_rows:
        context.append([
            "AVISO — aba biomassa",
            "Ainda não calculada — clique «Calcular» na aba Biomassa e "
            "baixe novamente.",
        ])
    if not landscape_rows:
        context.append([
            "AVISO — aba paisagem",
            "Ainda não calculada — clique «Calcular» na aba Paisagem e "
            "baixe novamente.",
        ])
    if not connectivity_rows:
        context.append([
            "AVISO — aba conectividade",
            "Ainda não calculada (opcional) — clique «Calcular "
            "conectividade» na aba Paisagem e baixe novamente.",
        ])
    if not sankey_transitions:
        context.append([
            "AVISO — aba transicoes",
            "Ainda não calculada — clique «Calcular» na aba Transições e "
            "baixe novamente.",
        ])
    else:
        context.append([
            "aba transicoes calculada para", f"{sankey_zone_label} "
            f"({sankey_year_a}→{sankey_year_b})",
        ])
    if not fire_rows:
        context.append([
            "AVISO — abas fogo_*",
            "Ainda não calculadas — clique «Calcular» na aba Fogo e baixe "
            "novamente.",
        ])
    if validacao_matrix:
        context.append(["aba validacao_ibge calculada para", validacao_zone_label])
    if include_gbif and not gbif_zone_rows:
        context.append([
            "AVISO — abas gbif_*",
            "Espécies (GBIF) marcado para incluir, mas ainda não calculado — "
            "clique «Calcular» na aba GBIF e baixe novamente.",
        ])

    provenances = [p for p in (history_prov, hansen_prov, biomass_prov,
                              landscape_prov, connectivity_prov,
                              sankey_prov, fire_prov, validacao_prov)
                  if p is not None]

    sheets = [
        _metadata_sheet("imóvel do CAR", context, provenances),
        _zones_sheet(zones),
        _cobertura_sheet(history_rows),
    ]
    loss_sheet, gain_sheet = _floresta_sheet(hansen_loss_rows or [], hansen_gain_ha)
    sheets.extend([loss_sheet, gain_sheet])
    sheets.append(_biomassa_sheet(biomass_rows or []))
    sheets.append(_paisagem_sheet(landscape_rows or []))
    sheets.append(_conectividade_sheet(connectivity_rows or []))
    sheets.append(_transicoes_sheet(sankey_transitions or {}, sankey_zone_label,
                                    sankey_year_a, sankey_year_b, lang))
    fogo_summary, fogo_annual = _fogo_sheet(fire_rows or [], fire_annual_rows or [])
    sheets.extend([fogo_summary, fogo_annual])
    if validacao_matrix:
        sheets.append(_validacao_sheet(validacao_matrix, validacao_zone_label))
    if include_gbif and gbif_zone_rows:
        sheets.extend(_gbif_sheets(gbif_zone_rows))
    sheets.append(_classes_sheet())

    label = imovel.get("cod_imovel") or "imovel"
    name = f"camposcope_{label}_{_timestamp()}.ods"
    data = ods.write(sheets)
    logger.info("Property workbook: %s (%s KiB)", name, len(data) // 1024)
    return data, name
