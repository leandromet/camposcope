"""BC municipalities and regional districts — the parcel browser's catalogue.

The counterpart to :mod:`camposcope.services.municipios`. Reads the committed
``data/bc_admin_areas.json`` built by ``scripts/fetch_bc_admin_areas.py``; that
script's docstring explains why the catalogue has to be built and verified
offline rather than fetched live (the two BC services spell a municipality
differently, and the naive re-ordering between them is wrong for some of them).

**What each row carries, and why all three names exist.**

``name``
    The legal name — ``"City of Kelowna"``. What a citation should say.
``short_name``
    The bare name — ``"Kelowna"``. What a user types, and what the matcher
    scores against.
``pmbc_key``
    The exact string the parcel fabric stores — ``"Kelowna, City of"``. The only
    one a ``CQL_FILTER`` will match, and the only one that is ever sent to the
    service.

A row whose ``pmbc_key`` is ``null`` could not be matched to the fabric when the
catalogue was built. Those are **excluded from search results** rather than
offered and then failing: an option that never works is worse than one that is
not there, the same rule the Brazil page applies to a licence-gated basemap.
"""

from __future__ import annotations

import json
import logging
import threading
import unicodedata
from typing import Any, Dict, List, Optional

from ...config.settings import REPO_ROOT

logger = logging.getLogger(__name__)

_DATA = REPO_ROOT / "data" / "bc_admin_areas.json"

_lock = threading.Lock()
_catalogue: Optional[Dict[str, Any]] = None


class CatalogueMissing(RuntimeError):
    """The committed catalogue is absent.

    Raised with the command that builds it, rather than letting the search box
    silently return nothing forever — the same failure mode
    ``services/uf_lookup.py`` guards against on the Brazil side.
    """


def _load() -> Dict[str, Any]:
    global _catalogue
    if _catalogue is None:
        with _lock:
            if _catalogue is None:
                if not _DATA.exists():
                    raise CatalogueMissing(
                        f"{_DATA} not found. Run "
                        "`python scripts/fetch_bc_admin_areas.py` once."
                    )
                data = json.loads(_DATA.read_text(encoding="utf-8"))
                rows: List[Dict[str, Any]] = []
                for kind, key in (("municipality", "municipalities"),
                                  ("regional_district", "regional_districts")):
                    for row in data.get(key, []):
                        if not row.get("pmbc_key"):
                            # See the module docstring: unmatched areas are
                            # dropped, not offered.
                            continue
                        rows.append({**row, "kind": kind})
                rural = data.get("rural")
                if rural and rural.get("pmbc_key"):
                    rows.append({**rural, "kind": "municipality"})
                for row in rows:
                    row["_haystack"] = _fold(
                        f"{row['short_name']} {row['name']}")
                _catalogue = {"rows": rows, "meta": data}
                logger.info(
                    "BC admin-area catalogue loaded: %d areas (%d skipped "
                    "for lacking a parcel-fabric key)",
                    len(rows),
                    sum(1 for k in ("municipalities", "regional_districts")
                        for r in data.get(k, []) if not r.get("pmbc_key")),
                )
    return _catalogue


def _fold(text: str) -> str:
    """Casefold and strip accents, for forgiving name matching.

    BC place names are mostly plain ASCII, but not all — ``Ucluelet``,
    ``Nakusp`` and ``Esquimalt`` are fine, while a user searching for
    ``"Metro Vancouver"`` or typing an accent from a Portuguese keyboard layout
    should still match. Same normalisation the Brazil município search uses, and
    for the same reason: the match should forgive what the user cannot be
    expected to reproduce exactly.
    """
    stripped = unicodedata.normalize("NFKD", str(text))
    stripped = "".join(c for c in stripped if not unicodedata.combining(c))
    return stripped.casefold().strip()


# --------------------------------------------------------------------------- #
# Lookup
# --------------------------------------------------------------------------- #
def all_areas() -> List[Dict[str, Any]]:
    return list(_load()["rows"])


def search(query: str, *, limit: int = 8) -> List[Dict[str, Any]]:
    """Areas whose name matches, best first.

    Scored rather than merely filtered, because substring matching alone puts
    ``"North Vancouver"`` above ``"Vancouver"`` for the query ``"vancouver"``,
    which is the wrong answer to an obvious question. An exact short-name match
    wins, then a prefix match, then a substring — and ties break toward the
    area with more parcels, which is a decent proxy for the one more people mean.
    """
    needle = _fold(query)
    if not needle:
        return []

    scored: List[tuple] = []
    for row in _load()["rows"]:
        short = _fold(row["short_name"])
        haystack = row["_haystack"]
        if short == needle:
            rank = 0
        elif short.startswith(needle):
            rank = 1
        elif needle in haystack:
            rank = 2
        else:
            continue
        # Negated so a larger count sorts earlier under an ascending sort.
        scored.append((rank, -(row.get("parcel_count") or 0),
                       row["short_name"], row))

    scored.sort(key=lambda item: item[:3])
    return [row for _rank, _count, _name, row in scored[:limit]]


def by_key(pmbc_key: str) -> Optional[Dict[str, Any]]:
    """One area by the exact parcel-fabric key."""
    for row in _load()["rows"]:
        if row["pmbc_key"] == pmbc_key:
            return row
    return None


def bounds(pmbc_key: str) -> Optional[list]:
    """``[[south, west], [north, east]]`` for framing the map, or ``None``.

    ``None`` for the ``"Rural"`` catch-all, which is not a place and has no
    meaningful extent — it is scattered across the whole province. The caller
    must not frame on it, and there is nothing sensible to frame on.
    """
    row = by_key(pmbc_key)
    return row.get("bounds") if row else None


def is_available() -> bool:
    """Whether the catalogue is present, without raising.

    Lets the UI degrade to "search by PID or click the map" rather than showing
    a broken area search, on a checkout where the build script has not been run.
    """
    try:
        _load()
        return True
    except (CatalogueMissing, ValueError, OSError):
        return False


__all__ = ["all_areas", "search", "by_key", "bounds", "is_available",
           "CatalogueMissing"]
