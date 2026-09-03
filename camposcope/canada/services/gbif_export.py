"""The GBIF species-per-zone tab as a spreadsheet — the Canada page.

Same shape as the Brazil page's ``services/gbif_export.py`` (one metadata
tab, then one tab per zone) — see that file for the full rationale. Not
reused directly, unlike ``gbif_species.py``: the Brazil version's metadata
sheet is written entirely in Portuguese, matching the Brazil export
convention (``camposcope/services/exports.py`` is Portuguese too). The
Canada page's own workbooks are English throughout, so this file follows
that convention rather than the Brazil one.

Nothing here re-queries GBIF — same reasoning as the Brazil file: the
workbook is built from the rows already in state, so the file and the
screen agree.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Iterable, Sequence

from ...config.settings import (
    GBIF_EXPORT_SPECIES_LIMIT,
    GBIF_FACET_LIMIT,
    GBIF_SPECIES_TABLE_LIMIT,
)
from ...services import ods
from ..config.citation import CITATION_TEXT_EN

logger = logging.getLogger(__name__)

MIMETYPE = ods.MIMETYPE

SPECIES_COLUMNS = ["zone", "species", "records", "pct_of_zone"]
CSV_COLUMNS = SPECIES_COLUMNS

#: Page-scoped, like the Brazil file — only the source this workbook draws
#: on, not the Canada page's whole DATA_SOURCES_EN list (config/citation.py),
#: which predates the GBIF tab and has never named it.
DATA_SOURCES = [
    ("GBIF — Species occurrence records",
     "GBIF.org — Global Biodiversity Information Facility. Records queried "
     "live through the occurrence API, restricted to the zone's geometry. "
     "When publishing results, cite the query and access date in GBIF's "
     "recommended form (“GBIF.org (dd mmm yyyy) GBIF Occurrence "
     "Search”) and credit the constituent datasets, which carry their "
     "own licences (CC0, CC-BY and CC-BY-NC). This query does NOT exclude "
     "CC-BY-NC data, which prohibits commercial use. GBIF's Canadian node "
     "is CBIF (Canada Biodiversity Information Facility).",
     "https://www.gbif.org"),
]


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _zone_slug(index: int, zone_key: str) -> str:
    """Same index-prefixed, sort-proof tab-naming scheme as the Brazil
    file — see that module's comment for why the index, not the key."""
    return f"{index:02d}_{zone_key}"


def _species_rows(row: Any) -> list[list[Any]]:
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
    out: list[list[Any]] = [
        ["Camposcope Canada — species recorded (GBIF)", ""],
        ["generated_utc", _now_iso()],
        ["source", "https://www.gbif.org"],
        ["", ""],
        ["PARCEL", ""],
    ]
    out.extend([list(c) for c in context])

    out.append(["", ""])
    out.append(["SUMMARY BY ZONE", ""])
    out.append(["  zone", "records | distinct species"])
    for row in rows:
        richness = int(getattr(row, "richness", 0) or 0)
        capped = richness >= GBIF_FACET_LIMIT
        listed = len(getattr(row, "species", []) or [])
        out.append([
            f"  {getattr(row, 'zone_label', '')}",
            f"{int(getattr(row, 'total', 0) or 0)} records | "
            f"{richness}{'+' if capped else ''} species"
            f" | {listed} listed in this sheet",
        ])
        if getattr(row, "error", ""):
            out.append(["    failed", str(row.error)])

    out.append(["", ""])
    out.append(["HOW TO READ THESE NUMBERS", ""])
    out.append([
        "  zones",
        "Cumulative areas from the parcel: the “2–5 km” zone "
        "includes the parcel and every inner ring, not just the 2–5 km "
        "ring on its own. They are not disjoint rings, and the tabs do not "
        "add up.",
    ])
    out.append([
        "  distinct species",
        f"Counts distinct scientific names returned by GBIF. The query is "
        f"capped at {GBIF_FACET_LIMIT}; a zone that reaches it shows as "
        f"«{GBIF_FACET_LIMIT}+» and the value is a FLOOR, not a "
        f"count.",
    ])
    out.append([
        "  rows per tab",
        f"Each tab carries the {GBIF_EXPORT_SPECIES_LIMIT} most-recorded "
        f"species for its zone (the screen shows the first "
        f"{GBIF_SPECIES_TABLE_LIMIT}). A zone with more species than that "
        f"is truncated — compare «distinct species» with "
        f"«listed» above.",
    ])
    out.append([
        "  names",
        "The name is the scientificName GBIF interpreted. A record "
        "determined only to family or genus appears under that family or "
        "genus name, not as a species.",
    ])
    out.append([
        "  sampling effort",
        "Counts RECORDS, not individuals or abundance. Reflects where "
        "someone collected or observed, not where the species occurs — "
        "areas near research institutions are heavily over-represented.",
    ])

    out.append(["", ""])
    out.append(["LICENCE — NOTE", ""])
    out.append([
        "  commercial use",
        "GBIF aggregates datasets under different licences (CC0, CC-BY and "
        "CC-BY-NC). This query does NOT exclude CC-BY-NC ones, which "
        "prohibit commercial use. Check each dataset's licence before such "
        "use.",
    ])
    out.append([
        "  citation",
        f"Cite the query and the access date: «GBIF.org "
        f"({_now_iso()[:10]}) GBIF Occurrence Search» and credit the "
        f"source datasets.",
    ])

    out.append(["", ""])
    out.append(["HOW TO CITE THIS APPLICATION", ""])
    out.append(["citation", CITATION_TEXT_EN])
    out.append(["", ""])
    out.append(["ATTRIBUTIONS", "cite the sources used when publishing"])
    for name, detail, url in DATA_SOURCES:
        out.append([name, f"{detail} {url}"])

    return ods.Sheet("metadata", ["field", "value"], out)


def build_ods(rows: Sequence[Any], context: Sequence[Sequence[Any]]
             ) -> tuple[bytes, str]:
    """The workbook: ``metadata`` plus one tab per zone."""
    sheets = [_metadata_sheet(rows, context)]
    for index, row in enumerate(rows):
        zone_key = str(getattr(row, "zone_key", index))
        sheets.append(ods.Sheet(
            f"species_{_zone_slug(index, zone_key)}",
            SPECIES_COLUMNS,
            _species_rows(row),
        ))
    data = ods.write(sheets)
    return data, "camposcope_canada_species_gbif.ods"


def build_csv(rows: Iterable[Any]) -> tuple[bytes, str]:
    """Every zone in one flat table — the Brazil file's ``build_csv``,
    ported. Same caveats as the workbook apply, which is why it ships beside
    it rather than instead of it."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerows(_species_rows(row))
    return buffer.getvalue().encode("utf-8"), "camposcope_canada_species_gbif.csv"


__all__ = ["MIMETYPE", "build_ods", "build_csv", "SPECIES_COLUMNS", "CSV_COLUMNS"]
