"""GBIF occurrences — endpoints, the slim record shape, and the display
palette for the GBIF tab's map layer.

Trimmed from Naturametrics' ``config/gbif.py``, decision D2 (this app carries
only what it renders — no taxonomy cascade, no basis-of-record/year/UF filter
accordion, no species-in-buffer analysis). What survives the trim is exactly
what ``services/gbif.py`` needs to fetch, slim and colour one viewport's worth
of occurrences: the endpoint, the field mapping, and the kingdom palette.
"""

from __future__ import annotations

import os

API_BASE = os.environ.get("CS_GBIF_API_BASE", "https://api.gbif.org/v1")
OCCURRENCE_SEARCH = f"{API_BASE}/occurrence/search"

#: Sent on every request. GBIF has no hard published rate limit but asks for
#: identifiable traffic.
USER_AGENT = "camposcope/0.1 (contact: leandromet@gmail.com)"

ATTRIBUTION = "GBIF.org — Global Biodiversity Information Facility"
PORTAL_URL = "https://www.gbif.org"

#: Everything is scoped to Brazil here — the Canada page's own module
#: (``canada/config/gbif.py``) scopes to "CA" the same way.
COUNTRY = "BR"

# --------------------------------------------------------------------------- #
# The slim record
# --------------------------------------------------------------------------- #
#: GBIF JSON key → the property name carried in our GeoJSON. A record off the
#: wire is ~7.4 KB of verbatim Darwin Core; this is the ~200 bytes of it that
#: the tooltip and the kingdom colouring actually read. Anything not listed
#: here is dropped in services/gbif.py::_slim.
SLIM_FIELDS = {
    "key": "gbif_id",
    "scientificName": "scientific_name",
    "species": "species",
    "genus": "genus",
    "family": "family",
    "order": "order",
    "class": "class_name",       # `class` is a Python keyword — renamed here,
    "phylum": "phylum",          # and the JS tooltip reads the renamed value.
    "kingdom": "kingdom",
    "taxonRank": "taxon_rank",
    "eventDate": "event_date",
    "year": "year",
    "basisOfRecord": "basis_of_record",
    "recordedBy": "recorded_by",
    "institutionCode": "institution_code",
    "datasetName": "dataset_name",
    "coordinateUncertaintyInMeters": "coordinate_uncertainty_m",
    "occurrenceStatus": "occurrence_status",
}

#: Fields drawn from a controlled vocabulary or a taxonomic backbone: every
#: legitimate value is one or two words. Some publishers ship records with
#: unrelated content packed into these — a mapping error between the
#: collection and GBIF, not a long name. A value over this length in one of
#: these fields is DROPPED rather than truncated: a 400-character "kingdom"
#: is not a kingdom.
CONTROLLED_FIELDS = (
    "kingdom", "phylum", "class_name", "order", "family", "genus", "species",
    "taxon_rank", "basis_of_record", "occurrence_status",
)
CONTROLLED_MAX_CHARS = 60

#: Free-text fields where a long value is usually legitimate — truncated with
#: an ellipsis rather than dropped.
FREETEXT_MAX_CHARS = 180

#: Coordinates are pulled out into the geometry, not the properties — but the
#: click/hover handler in leaflet_map.js reads `lat`/`lon` off properties, so
#: they are copied there too (see services/gbif.py::_slim).
LAT_FIELD = "decimalLatitude"
LON_FIELD = "decimalLongitude"

# --------------------------------------------------------------------------- #
# Display
# --------------------------------------------------------------------------- #
#: One hue per kingdom — the coarsest split that still tells a reader whether
#: a dot is an animal, a plant or a fungus at a glance. Keyed by the kingdom
#: NAME as GBIF returns it, handed straight to leaflet_map.js's styleFor()
#: with `color_property: "kingdom"`.
KINGDOM_COLORS = {
    "Animalia": "d1495b",
    "Plantae":  "2a9d3f",
    "Fungi":    "8e5ea2",
    "Chromista": "00898f",
    "Protozoa": "d98c00",
    "Bacteria": "3d7ea6",
    "Archaea":  "7a7a7a",
    "Viruses":  "c2185b",
    "incertae sedis": "9e9e9e",
}
DEFAULT_COLOR = "9e9e9e"

#: The eight GBIF backbone kingdoms, with their nub keys — GBIF's
#: ``kingdomKey`` facet returns the key, not the name, so the species-per-zone
#: analysis (services/gbif_species.py) needs this to label its kingdom
#: breakdown. Fixed and global, not per-country.
KINGDOMS = [
    (1, "Animalia"),
    (6, "Plantae"),
    (5, "Fungi"),
    (4, "Chromista"),
    (7, "Protozoa"),
    (3, "Bacteria"),
    (2, "Archaea"),
    (8, "Viruses"),
]

__all__ = [
    "API_BASE", "OCCURRENCE_SEARCH", "USER_AGENT", "ATTRIBUTION",
    "PORTAL_URL", "COUNTRY", "SLIM_FIELDS", "CONTROLLED_FIELDS",
    "CONTROLLED_MAX_CHARS", "FREETEXT_MAX_CHARS", "LAT_FIELD", "LON_FIELD",
    "KINGDOM_COLORS", "DEFAULT_COLOR", "KINGDOMS",
]
