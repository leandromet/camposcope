#!/usr/bin/env python3
"""Build the BC municipality / regional-district catalogue for the Canada page.

Run once. Writes ``data/bc_admin_areas.json``, which
``camposcope/canada/services/municipalities.py`` reads at runtime. The
counterpart to ``scripts/fetch_municipios.py`` on the Brazil side, and it exists
for the same reason: a dropdown must not wait on a network round trip, and a
name the user types has to resolve locally and instantly.

**Why this needs to be a script rather than a runtime fetch, and why it is more
than a download.** Two BC services have to be joined, and they disagree about
how to spell a municipality:

* ``ABMS_MUNICIPALITIES_SP`` publishes the legal name — ``"City of Kelowna"``,
  ``"The Corporation of the Village of Hazelton"`` — plus a short form and the
  containing regional district, and it has the boundary geometry the map needs
  for framing.
* The **parcel fabric** stores a different word order in ``MUNICIPALITY`` —
  ``"Kelowna, City of"`` — and that is the only string a ``CQL_FILTER`` will
  match.

A mechanical re-ordering gets most of them (verified: 6 of the first 7), but not
all — ``"The Corporation of the Village of Hazelton"`` has no obvious re-ordering
and the naive one returns zero parcels. Guessing wrong is silent: the browser
shows "0 parcels" for a real municipality, which reads as a data problem rather
than a join problem.

So this script **verifies every candidate against the fabric** with a free
``resultType=hits`` count and records the form that actually matched, along with
the count. Anything it cannot resolve is written out with
``"pmbc_key": null`` and listed at the end, so an unresolved municipality is a
visible gap rather than a silently empty page.

Usage::

    python scripts/fetch_bc_admin_areas.py [--out data/bc_admin_areas.json]
"""

from __future__ import annotations

import argparse
import json
import logging
import pathlib
import re
import sys
import time
from typing import Any, Dict, Iterable, List, Optional

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("fetch_bc_admin_areas")

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

PMBC_BASE = ("https://openmaps.gov.bc.ca/geo/pub/"
             "WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW/ows")
PMBC_LAYER = "pub:WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW"

MUNI_BASE = ("https://openmaps.gov.bc.ca/geo/pub/"
             "WHSE_LEGAL_ADMIN_BOUNDARIES.ABMS_MUNICIPALITIES_SP/ows")
MUNI_LAYER = "pub:WHSE_LEGAL_ADMIN_BOUNDARIES.ABMS_MUNICIPALITIES_SP"

RD_BASE = ("https://openmaps.gov.bc.ca/geo/pub/"
           "WHSE_LEGAL_ADMIN_BOUNDARIES.ABMS_REGIONAL_DISTRICTS_SP/ows")
RD_LAYER = "pub:WHSE_LEGAL_ADMIN_BOUNDARIES.ABMS_REGIONAL_DISTRICTS_SP"

USER_AGENT = "Camposcope/0.1 (+https://github.com/leandromet/camposcope)"

#: Be a good citizen: these are public provincial services and this script
#: issues a few hundred requests in one go.
PAUSE_S = 0.35

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})


def _get(base: str, params: Dict[str, Any]) -> requests.Response:
    for attempt in (1, 2, 3):
        try:
            r = session.get(base, params=params, timeout=(10, 90))
        except requests.RequestException as exc:
            logger.warning("request failed (attempt %d): %s", attempt, exc)
            time.sleep(2 * attempt)
            continue
        if r.status_code == 200:
            return r
        logger.warning("HTTP %s (attempt %d)", r.status_code, attempt)
        time.sleep(2 * attempt)
    raise SystemExit(f"giving up on {base}")


def _quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


# --------------------------------------------------------------------------- #
# Candidate name forms
# --------------------------------------------------------------------------- #
_TYPE_RE = re.compile(
    r"^(?:The Corporation of the )?"
    r"(City|District|Town|Village|Township|Municipality|Resort Municipality|"
    r"Regional Municipality|Corporation)"
    r" of (?:the )?(.+)$"
)


#: Municipalities where ABMS and the parcel fabric disagree about more than
#: word order — a different generic type word ("Village" vs "District"), an
#: apostrophe ABMS drops, or a "St"/"Mt" abbreviation the fabric punctuates and
#: ABMS does not. No regex covers all of these at once without risking a wrong
#: match elsewhere, so they are recorded here as verified literal answers
#: (checked directly against the fabric on 2026-08-27) rather than guessed.
#: Tried before the mechanical candidates below.
MANUAL_OVERRIDES: Dict[str, str] = {
    "City of Fort St John": "Fort St. John, City of",
    "District of Fort St James": "Fort St. James, District of",
    "District of Hudsons Hope": "Hudson's Hope, District of",
    "Sun Peaks Mountain Resort Municipality": "Sun Peaks, Mountain Resort "
        "Municipality",
    "Bowen Island Municipality": "Bowen Island, Municipality",
    # ABMS calls this a Village; the fabric calls it a District.
    "Corporation of the Village of Tofino": "Tofino, District of",
    # The fabric omits "The" that the mechanical candidate would include.
    "Corporation of the Township of Esquimalt": "Esquimalt, Corporation of "
        "the Township of",
    # ABMS' "District Municipality of X" becomes the fabric's ordinary
    # "X, The Corporation of the District of" — a different generic type
    # entirely, not a reordering of the same one.
    "District Municipality of West Vancouver": "West Vancouver, The "
        "Corporation of the District of",
}


def candidates(legal_name: str, short_name: str) -> List[str]:
    """Every plausible ``MUNICIPALITY`` spelling, best guess first.

    Ordered by how likely each is to be the fabric's form, so the first hit is
    almost always the first query. The bare short name is last because it is the
    most likely to collide with a different municipality's — ``"Langley"`` is
    both a City and a Township, and they are different places.
    """
    out: List[str] = []
    if legal_name in MANUAL_OVERRIDES:
        out.append(MANUAL_OVERRIDES[legal_name])
    m = _TYPE_RE.match(legal_name)
    if m:
        kind, bare = m.group(1), m.group(2)
        out.append(f"{bare}, {kind} of")
        out.append(f"{bare}, The Corporation of the {kind} of")
        out.append(f"{bare}, {kind}")
    out.append(legal_name)
    if short_name and short_name not in out:
        out.append(short_name)
    # dict.fromkeys: dedupe while preserving the priority order above.
    return list(dict.fromkeys(out))


def parcel_count(field: str, value: str) -> int:
    """``resultType=hits`` — a header-only response, so this is nearly free."""
    r = _get(PMBC_BASE, {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": PMBC_LAYER, "resultType": "hits",
        "cql_filter": f"{field}={_quote(value)}",
    })
    m = re.search(r'numberMatched="(\d+)"', r.text)
    return int(m.group(1)) if m else -1


def resolve(field: str, options: Iterable[str]) -> tuple[Optional[str], int]:
    """The first candidate the fabric actually has parcels for."""
    for candidate in options:
        count = parcel_count(field, candidate)
        time.sleep(PAUSE_S)
        if count > 0:
            return candidate, count
    return None, 0


# --------------------------------------------------------------------------- #
# Boundaries
# --------------------------------------------------------------------------- #
def fetch_admin_areas(base: str, layer: str, extra_fields: List[str]
                      ) -> List[Dict[str, Any]]:
    """Names plus bounding boxes, without the polygons.

    The geometry is fetched only to derive a bbox for map framing and is thrown
    away immediately — 160 municipal outlines at full resolution is many
    megabytes, and nothing in the app draws them.
    """
    fields = ["ADMIN_AREA_NAME", "ADMIN_AREA_ABBREVIATION"] + extra_fields
    r = _get(base, {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": layer, "outputFormat": "application/json",
        "srsName": "EPSG:4326", "count": 500,
        "propertyName": ",".join(fields + ["SHAPE"]),
    })
    payload = r.json()

    rows = []
    for feature in payload.get("features", []):
        props = feature.get("properties") or {}
        bounds = _bbox(feature.get("geometry"))
        rows.append({
            "name": props.get("ADMIN_AREA_NAME") or "",
            "short_name": props.get("ADMIN_AREA_ABBREVIATION") or "",
            "regional_district": props.get("ADMIN_AREA_GROUP_NAME") or "",
            "bounds": bounds,
        })
    return rows


def _bbox(geometry: Optional[dict]) -> Optional[list]:
    """``[[south, west], [north, east]]`` from any polygon geometry."""
    if not geometry:
        return None
    xs: List[float] = []
    ys: List[float] = []

    def walk(node):
        if isinstance(node, (int, float)):
            return
        if (isinstance(node, list) and len(node) >= 2
                and all(isinstance(v, (int, float)) for v in node[:2])):
            xs.append(float(node[0]))
            ys.append(float(node[1]))
            return
        if isinstance(node, list):
            for child in node:
                walk(child)

    walk(geometry.get("coordinates"))
    if not xs or not ys:
        return None
    return [[min(ys), min(xs)], [max(ys), max(xs)]]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "data" /
                                             "bc_admin_areas.json"))
    parser.add_argument("--skip-verify", action="store_true",
                        help="Write the best-guess key without confirming it "
                             "against the parcel fabric. Fast, and produces a "
                             "catalogue with silently-wrong entries — for "
                             "development only.")
    args = parser.parse_args()

    logger.info("Fetching regional districts…")
    districts = fetch_admin_areas(RD_BASE, RD_LAYER, [])
    logger.info("  %d regional districts", len(districts))

    logger.info("Fetching municipalities…")
    munis = fetch_admin_areas(MUNI_BASE, MUNI_LAYER, ["ADMIN_AREA_GROUP_NAME"])
    logger.info("  %d municipalities", len(munis))

    unresolved: List[str] = []

    # Regional districts first: the fabric spells these exactly as ABMS does
    # (verified), so they resolve on the first candidate every time — but they
    # are still verified rather than assumed, because "verified once in
    # development" is not the same as "true for all 28".
    for row in districts:
        if args.skip_verify:
            row["pmbc_key"], row["parcel_count"] = row["name"], None
            continue
        key, count = resolve("REGIONAL_DISTRICT", [row["name"],
                                                   row["short_name"]])
        row["pmbc_key"], row["parcel_count"] = key, count
        if key is None:
            unresolved.append(f"RD: {row['name']}")
        logger.info("  RD %-46s → %-46s %s", row["name"], key, count or "")

    for row in munis:
        if args.skip_verify:
            row["pmbc_key"], row["parcel_count"] = (
                candidates(row["name"], row["short_name"])[0], None)
            continue
        key, count = resolve("MUNICIPALITY",
                             candidates(row["name"], row["short_name"]))
        row["pmbc_key"], row["parcel_count"] = key, count
        if key is None:
            unresolved.append(f"municipality: {row['name']}")
        logger.info("  %-52s → %-40s %s", row["name"], key, count or "")

    # The fabric's catch-all for everything outside an incorporated
    # municipality. Not in ABMS — it is not an administrative area at all — but
    # it is a real MUNICIPALITY value covering a great deal of BC, and without
    # it the browser cannot reach any of that land by name.
    rural_count = (None if args.skip_verify
                   else parcel_count("MUNICIPALITY", "Rural"))

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {
            "municipalities": MUNI_LAYER,
            "regional_districts": RD_LAYER,
            "parcel_fabric": PMBC_LAYER,
        },
        "verified": not args.skip_verify,
        "rural": {
            "name": "Rural (outside any municipality)",
            "short_name": "Rural",
            "pmbc_key": "Rural",
            "parcel_count": rural_count,
            "bounds": None,
            "regional_district": "",
        },
        "regional_districts": districts,
        "municipalities": munis,
    }

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    logger.info("Wrote %s (%.1f KiB)", out_path,
                out_path.stat().st_size / 1024)

    if unresolved:
        logger.warning("%d area(s) could not be matched to a parcel-fabric "
                       "key; they are written with pmbc_key=null and the "
                       "browser will skip them:", len(unresolved))
        for name in unresolved:
            logger.warning("  - %s", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
