"""Canada-page settings.

Deliberately thin, the same way ``naturametrics/canada/config/settings.py`` is:
everything about *Earth Engine* or *this deployment* — project id, concurrency,
tile cache, scale, ring radii, area-flag thresholds — is imported from the main
:mod:`camposcope.config.settings`, because those are properties of the machine
and must not drift between the two pages. Only what is genuinely Canadian, or
genuinely about ParcelMap BC, lives here.

Prefix ``CS_CA_`` throughout, so a shell that already carries the Brazil page's
``CS_`` variables cannot cross-configure this one.
"""

from __future__ import annotations

import os

from ...config.settings import _int

# --------------------------------------------------------------------------- #
# ParcelMap BC  (BC Data Catalogue → BC Geographic Warehouse WFS)
# --------------------------------------------------------------------------- #
#: The one endpoint this page's cadastre comes from. Verified live 2026-08-27:
#: WFS 2.0.0, ``outputFormat=application/json``, ``CQL_FILTER`` and server-side
#: reprojection to EPSG:4326 all work, and ``resultType=hits`` returns a
#: header-only count.
PMBC_BASE = os.environ.get(
    "CS_CA_PMBC_BASE",
    "https://openmaps.gov.bc.ca/geo/pub/"
    "WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW/ows",
)

#: The same service published as WMS, for the "draw every parcel" context layer.
#: Same reasoning as the Brazil page's SICAR WMS: rendering a province's worth of
#: parcels is the server's problem, not ours.
PMBC_WMS = os.environ.get(
    "CS_CA_PMBC_WMS", "https://openmaps.gov.bc.ca/geo/pub/wms"
)

#: BC's administrative-area layers, for the municipality / regional-district
#: browser. 160 municipalities and 28 regional districts, verified 2026-08-27.
BC_MUNICIPALITIES_BASE = os.environ.get(
    "CS_CA_BC_MUNI_BASE",
    "https://openmaps.gov.bc.ca/geo/pub/"
    "WHSE_LEGAL_ADMIN_BOUNDARIES.ABMS_MUNICIPALITIES_SP/ows",
)
BC_REGIONAL_DISTRICTS_BASE = os.environ.get(
    "CS_CA_BC_RD_BASE",
    "https://openmaps.gov.bc.ca/geo/pub/"
    "WHSE_LEGAL_ADMIN_BOUNDARIES.ABMS_REGIONAL_DISTRICTS_SP/ows",
)

#: Never leave these unset: requests' default is *no timeout*, which hangs a
#: Reflex background handler with no way out. Same rule as the SICAR client.
PMBC_TIMEOUT_CONNECT = _int("CS_CA_PMBC_TIMEOUT_CONNECT", 10)
PMBC_TIMEOUT_READ = _int("CS_CA_PMBC_TIMEOUT_READ", 60)

#: Municipality pages go stale; a parcel's boundary does not change during a
#: session, so PID lookups are cached for the process lifetime instead.
PMBC_CACHE_TTL_S = _int("CS_CA_PMBC_CACHE_TTL", 3600)

#: openmaps.gov.bc.ca is a public service run by the Province for everyone. An
#: identifiable User-Agent is the cheapest courtesy available — the same posture
#: constraint C5 imposes on the Brazil page's SICAR traffic.
PMBC_USER_AGENT = os.environ.get(
    "CS_CA_PMBC_USER_AGENT",
    "Camposcope/0.1 (+https://github.com/leandromet/camposcope)",
)

#: Unlike geoserver.car.gov.br, openmaps.gov.bc.ca serves a complete, modern
#: certificate chain and negotiates TLS 1.3 without complaint — so this client
#: needs none of the SECLEVEL/TLS-pinning machinery ``services/sicar.py``
#: carries. Verified 2026-08-27 from a plain ``requests`` session.
PMBC_VERIFY_TLS = os.environ.get("CS_CA_PMBC_VERIFY_TLS", "true").lower() != "false"

# --------------------------------------------------------------------------- #
# Extent
# --------------------------------------------------------------------------- #
#: British Columbia, padded. west, south, east, north. The parcel fabric is
#: provincial, so a click outside this box has no cadastre behind it at all and
#: is refused before any request leaves the machine — the same fail-early rule
#: ``services/uf_lookup.py`` applies to clicks outside Brazil.
BC_BBOX = (-139.2, 48.2, -113.9, 60.1)

#: Canada as a whole, for the land-cover half. The ACI, VLCE2, Hansen, AGB and
#: MODIS layers all answer well outside BC; only the *parcel* is provincial.
#: Kept so a future extension to another province's cadastre does not have to
#: relitigate what "in Canada" means.
CANADA_BBOX = (-141.5, 41.0, -52.0, 83.5)

# --------------------------------------------------------------------------- #
# Map
# --------------------------------------------------------------------------- #
DEFAULT_BASEMAP = os.environ.get("CS_CA_BASEMAP", "google_hybrid")
#: Centred on BC's interior rather than its centroid: the centroid sits in a
#: mountain range nobody searches, and the populated south would be a sliver.
DEFAULT_CENTER = (53.7, -123.0)
DEFAULT_ZOOM = _int("CS_CA_DEFAULT_ZOOM", 5)

#: Initial framing as ``[[south, west], [north, east]]``.
BC_VIEW_BOUNDS = ((48.2, -139.2), (60.1, -113.9))

# --------------------------------------------------------------------------- #
# Language
# --------------------------------------------------------------------------- #
#: The Canada page opens in English; the Brazil page opens in Portuguese. An
#: explicit choice wins over both — the header link between the pages carries
#: ``?lang=`` and ``state/_ui.py`` honours it.
DEFAULT_LANGUAGE = os.environ.get("CS_CA_LANGUAGE", "en")

#: The Brazil page hardcodes its two-language check inline (``UIMixin.set_lang``
#: accepts only "pt"/"en" literally); this page names the set instead, since
#: ``_ui.py`` checks against it in two places and a literal in each risks the
#: two drifting apart.
SUPPORTED_LANGUAGES = ("en", "pt")

# --------------------------------------------------------------------------- #
# Geocoding
# --------------------------------------------------------------------------- #
#: Never widen this. The page covers British Columbia; a search that can wander
#: off it will. Nominatim has no province filter, so the country filter plus the
#: BC bbox check in ``services/geocode.py`` is what actually bounds it.
GEOCODER_COUNTRY_CODES = "ca"
