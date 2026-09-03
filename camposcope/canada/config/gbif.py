"""GBIF occurrences for the Canada page.

The endpoint, the slim-field mapping and the kingdom palette are GBIF-global,
not Brazil-specific — imported from ``camposcope/config/gbif.py`` rather than
duplicated. Only the country code differs, the same way every other Canada
config module in this app imports what is shared and states only what is
genuinely Canadian.
"""

from __future__ import annotations

from ...config.gbif import (
    API_BASE, ATTRIBUTION, CONTROLLED_FIELDS, CONTROLLED_MAX_CHARS,
    DEFAULT_COLOR, FREETEXT_MAX_CHARS, KINGDOM_COLORS, KINGDOMS, LAT_FIELD,
    LON_FIELD, OCCURRENCE_SEARCH, PORTAL_URL, SLIM_FIELDS, USER_AGENT,
)

#: Everything is scoped to Canada here — the Brazil page's own module scopes
#: to "BR" the same way (see its docstring).
COUNTRY = "CA"

__all__ = [
    "API_BASE", "OCCURRENCE_SEARCH", "USER_AGENT", "ATTRIBUTION",
    "PORTAL_URL", "COUNTRY", "SLIM_FIELDS", "CONTROLLED_FIELDS",
    "CONTROLLED_MAX_CHARS", "FREETEXT_MAX_CHARS", "LAT_FIELD", "LON_FIELD",
    "KINGDOM_COLORS", "DEFAULT_COLOR", "KINGDOMS",
]
