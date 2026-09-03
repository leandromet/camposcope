"""The GBIF species-per-zone tab as a spreadsheet.

Same shape as Naturametrics' equivalent (``services/gbif_export.py`` there):
a ``metadados`` tab first, then one tab per zone, in the on-screen order
(imóvel, then rings by increasing radius). Written here rather than in
``services/report.py``, which is entirely about the property's Earth Engine
analyses: nothing here touches EE, and the caveats that matter are GBIF's
own, not ours.

**Nothing here re-queries GBIF.** The workbook is built from the rows
already in state, so the file and the screen always agree.

**Zones, not radii.** Camposcope's neighbourhood rings are grown outward
from the property's own boundary (``services/zones.py``, decision D3), not
from a centroid the way Naturametrics' buffers are — but the species count
per zone is cumulative for the same reason as there: presence is not
additive, so "zona" here always means "this zone and everything inside it"
(``services/gbif_species.py::cumulative_zone_geometries``).
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Iterable, Sequence

from ..config.citation import CITATION_TEXT
from ..config.settings import (
    GBIF_EXPORT_SPECIES_LIMIT,
    GBIF_FACET_LIMIT,
    GBIF_SPECIES_TABLE_LIMIT,
)
from . import ods

logger = logging.getLogger(__name__)

MIMETYPE = ods.MIMETYPE

#: Columns of a per-zone tab, and of the flat CSV.
SPECIES_COLUMNS = ["zona", "especie", "registros", "pct_da_zona"]
CSV_COLUMNS = SPECIES_COLUMNS

#: Page-scoped, like Naturametrics' Canada gbif_export.py — only the source
#: this workbook actually draws on, not Camposcope's whole DATA_SOURCES list
#: (config/citation.py), which predates the GBIF tab and has never named it.
DATA_SOURCES = [
    ("GBIF — Registros de ocorrência de espécies",
     "GBIF.org — Global Biodiversity Information Facility. Registros "
     "consultados ao vivo pela API de ocorrências, restritos ao Brasil e à "
     "geometria da zona. Ao publicar resultados, cite a consulta e a data "
     "de acesso na forma recomendada pelo GBIF («GBIF.org (dd mmm aaaa) "
     "GBIF Occurrence Search») e credite os conjuntos de origem, que têm "
     "licenças próprias (CC0, CC-BY e CC-BY-NC). Esta consulta NÃO exclui "
     "os CC-BY-NC, que vedam uso comercial. O nó brasileiro do GBIF é o "
     "SiBBr.",
     "https://www.gbif.org"),
]


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _zone_slug(index: int, zone_key: str) -> str:
    """``(0, "imovel") -> "00_imovel"``, ``(2, "ring_2km") -> "02_ring_2km"``.

    Numbered by position rather than parsed from the key: ``rows`` already
    arrives property-first then rings by increasing radius
    (``cumulative_zone_geometries``), and a tab bar is ordered as written —
    but only until someone's spreadsheet app re-sorts sheets alphabetically,
    at which point ``ring_2km`` would sort before ``ring_500m``. The index
    prefix survives that regardless of how many zones there are.
    """
    return f"{index:02d}_{zone_key}"


def _species_rows(row: Any) -> list[list[Any]]:
    """One zone's species table, as spreadsheet rows.

    ``pct_da_zona`` is each species' share of that zone's own record total —
    the one derived number worth precomputing, because it is what makes two
    zones comparable when their totals differ by orders of magnitude.
    """
    total = getattr(row, "total", 0) or 0
    out = []
    for sp in getattr(row, "species", []) or []:
        count = int(getattr(sp, "count", 0) or 0)
        out.append([
            str(getattr(row, "zone_label", "")),
            str(getattr(sp, "name", "")),
            count,
            round(count / total * 100.0, 4) if total else 0.0,
        ])
    return out


def _metadata_sheet(rows: Sequence[Any], context: Sequence[Sequence[Any]]
                    ) -> ods.Sheet:
    """The tab the workbook opens with — where the property was, and which
    of these numbers are floors rather than counts."""
    out: list[list[Any]] = [
        ["Camposcope — espécies registradas (GBIF)", ""],
        ["gerado em (UTC)", _now_iso()],
        ["endereço", "https://www.gbif.org"],
        ["", ""],
        ["IMÓVEL", ""],
    ]
    out.extend([list(c) for c in context])

    out.append(["", ""])
    out.append(["RESUMO POR ZONA", ""])
    out.append(["  zona", "registros | espécies distintas"])
    for row in rows:
        richness = int(getattr(row, "richness", 0) or 0)
        capped = richness >= GBIF_FACET_LIMIT
        listed = len(getattr(row, "species", []) or [])
        out.append([
            f"  {getattr(row, 'zone_label', '')}",
            f"{int(getattr(row, 'total', 0) or 0)} registros | "
            f"{richness}{'+' if capped else ''} espécies"
            f" | {listed} listadas nesta planilha",
        ])
        if getattr(row, "error", ""):
            out.append(["    falha", str(row.error)])

    out.append(["", ""])
    out.append(["COMO LER ESTES NÚMEROS", ""])
    out.append([
        "  zonas",
        "Áreas CUMULATIVAS a partir do imóvel: a zona «2–5 km» inclui o "
        "imóvel e todos os anéis mais internos, não apenas o anel de 2–5 km "
        "isolado. Não são anéis disjuntos, e as abas não se somam.",
    ])
    out.append([
        "  espécies distintas",
        f"Conta os nomes científicos distintos devolvidos pelo GBIF. O teto "
        f"da consulta é {GBIF_FACET_LIMIT}; uma zona que o alcança aparece "
        f"como «{GBIF_FACET_LIMIT}+» e o valor é um PISO, não uma contagem.",
    ])
    out.append([
        "  linhas por aba",
        f"Cada aba traz as {GBIF_EXPORT_SPECIES_LIMIT} espécies mais "
        f"registradas da sua zona (a tela mostra as {GBIF_SPECIES_TABLE_LIMIT} "
        f"primeiras). Uma zona com mais espécies do que isso está truncada — "
        f"compare «espécies distintas» com «listadas» no resumo acima.",
    ])
    out.append([
        "  nomes",
        "O nome é o scientificName interpretado pelo GBIF. Um registro "
        "determinado só até família ou gênero aparece com esse nome de família "
        "ou gênero, e não como espécie.",
    ])
    out.append([
        "  esforço amostral",
        "Contagem de REGISTROS, não de indivíduos nem de abundância. Reflete "
        "onde alguém coletou ou observou, não onde a espécie ocorre — áreas "
        "perto de instituições de pesquisa são fortemente sobre-representadas.",
    ])

    out.append(["", ""])
    out.append(["LICENÇA — ATENÇÃO", ""])
    out.append([
        "  uso comercial",
        "O GBIF agrega conjuntos com licenças diferentes (CC0, CC-BY e "
        "CC-BY-NC). Esta consulta NÃO exclui os CC-BY-NC, que vedam uso "
        "comercial. Verifique a licença de cada conjunto antes de tal uso.",
    ])
    out.append([
        "  citação",
        f"Cite a consulta e a data de acesso: «GBIF.org ({_now_iso()[:10]}) "
        f"GBIF Occurrence Search» e credite os conjuntos de origem.",
    ])

    out.append(["", ""])
    out.append(["COMO CITAR ESTE APLICATIVO", ""])
    out.append(["citação", CITATION_TEXT])
    out.append(["", ""])
    out.append(["ATRIBUIÇÕES OBRIGATÓRIAS", "cite as bases usadas ao publicar"])
    for name, detail, url in DATA_SOURCES:
        out.append([name, f"{detail} {url}"])

    return ods.Sheet("metadados", ["campo", "valor"], out)


def build_ods(rows: Sequence[Any], context: Sequence[Sequence[Any]]
             ) -> tuple[bytes, str]:
    """The workbook: ``metadados`` plus one tab per zone."""
    sheets = [_metadata_sheet(rows, context)]
    for index, row in enumerate(rows):
        zone_key = str(getattr(row, "zone_key", index))
        sheets.append(ods.Sheet(
            f"especies_{_zone_slug(index, zone_key)}",
            SPECIES_COLUMNS,
            _species_rows(row),
        ))
    data = ods.write(sheets)
    return data, "camposcope_especies_gbif.ods"


def build_csv(rows: Iterable[Any]) -> tuple[bytes, str]:
    """Every zone in one flat table.

    The counterpart to the workbook, for a script rather than a reader: same
    columns as a zone tab, with ``zona`` distinguishing them, and none of the
    metadata. The caveats in the workbook's first tab apply to this file too —
    which is exactly why it is offered alongside the ODS rather than instead
    of it.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerows(_species_rows(row))
    return buffer.getvalue().encode("utf-8"), "camposcope_especies_gbif.csv"


__all__ = ["MIMETYPE", "build_ods", "build_csv", "SPECIES_COLUMNS", "CSV_COLUMNS"]
