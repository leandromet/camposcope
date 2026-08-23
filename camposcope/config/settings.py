"""Runtime settings, all overridable by environment variables.

Prefix ``CS_`` throughout, so a shell that also has Naturametrics' ``NM_`` and
Yvynation's variables loaded cannot cross-configure the three apps. The full
table with defaults and rationale is in doc/09-dev-environment.md §4.
"""

from __future__ import annotations

import os
import pathlib
from typing import List

#: Repo root — for data/cache paths that must work regardless of cwd.
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- #
# Earth Engine
# --------------------------------------------------------------------------- #
#: The Partner-tier grant is attached to *this* project. Pointing at a different
#: one does not fail — it silently drops to contributor limits, and the tile
#: fan-out (doc/06-ee-layers.md §4) crawls. Changing this is a capacity
#: decision, not a config tweak.
GCP_PROJECT_ID = os.environ.get("CS_GCP_PROJECT_ID", "ee-leandromet")
EE_SERVICE_ACCOUNT_JSON = os.environ.get("CS_EE_SERVICE_ACCOUNT_JSON", "")
EE_SERVICE_ACCOUNT_FILE = os.environ.get("CS_EE_SERVICE_ACCOUNT_FILE", "")

#: Earth Engine tier. The Partner-tier grant on GCP_PROJECT_ID is what makes the
#: wide tile fan-out affordable (doc/06-ee-layers.md §4); `contributor` is the
#: rollback if that uplift lapses.
EE_TIER = os.environ.get("CS_EE_TIER", "partner").strip().lower()

#: Thread-pool width for parallel Earth Engine calls. Sized to the tier — a
#: contributor-tier project throttled at 64 concurrent requests just queues.
EE_CONCURRENCY = _int("CS_EE_CONCURRENCY", 64 if EE_TIER == "partner" else 4)

#: Minted tile URLs are memoised on a stable cache key (services/tiles.py).
TILE_CACHE_TTL_SECONDS = _int("CS_TILE_CACHE_TTL", 3600)
TILE_CACHE_MAX_ENTRIES = _int("CS_TILE_CACHE_MAX", 512)

EE_DEFAULT_SCALE_M = _int("CS_EE_SCALE_M", 30)
#: Raised for very large properties — see doc/06-ee-layers.md §7.
EE_TILE_SCALE = _int("CS_EE_TILE_SCALE", 4)
EE_MAX_PIXELS = _int("CS_EE_MAX_PIXELS", 1_000_000_000)

# --------------------------------------------------------------------------- #
# SICAR / CAR GeoServer  (doc/05-sicar-geoserver.md)
# --------------------------------------------------------------------------- #
SICAR_BASE = os.environ.get(
    "CS_SICAR_BASE", "https://geoserver.car.gov.br/geoserver/sicar/ows"
)
SICAR_WMS = os.environ.get(
    "CS_SICAR_WMS", "https://geoserver.car.gov.br/geoserver/sicar/wms"
)

#: Connect/read timeouts in seconds. Never leave these unset: requests' default
#: is *no timeout*, which hangs a Reflex background handler with no way out.
SICAR_TIMEOUT_CONNECT = _int("CS_SICAR_TIMEOUT_CONNECT", 10)
SICAR_TIMEOUT_READ = _int("CS_SICAR_TIMEOUT_READ", 60)

#: Municipality pages go stale; a property's boundary does not change during a
#: session, so code lookups are cached for the process lifetime instead.
SICAR_CACHE_TTL_S = _int("CS_SICAR_CACHE_TTL", 3600)

#: The public GeoServer is run by the SFB for everyone (constraint C5). An
#: identifiable User-Agent is the cheapest courtesy available.
SICAR_USER_AGENT = os.environ.get(
    "CS_SICAR_USER_AGENT",
    "Camposcope/0.1 (+https://github.com/leandromet/camposcope)",
)

#: The certificate chain served by geoserver.car.gov.br is incomplete for some
#: clients. Handled explicitly here rather than with a `verify=False` scattered
#: through the service — see services/sicar.py::_session for the full note.
SICAR_VERIFY_TLS = os.environ.get("CS_SICAR_VERIFY_TLS", "true").lower() != "false"

# --------------------------------------------------------------------------- #
# Zones  (doc/02-architecture.md §3, decision D3)
# --------------------------------------------------------------------------- #
def _radii(name: str, default: str) -> List[int]:
    raw = os.environ.get(name, default)
    out: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                out.append(int(part))
            except ValueError:
                continue
    return out or [int(x) for x in default.split(",")]


#: Rings are measured **outward from the property boundary**, not from a
#: centroid (D3). Metres.
RING_RADII_M: List[int] = _radii("CS_RING_RADII_M", "500,1000,2000,5000")

#: Above this, ring construction is scaled back with a visible notice rather
#: than producing a slow, meaningless answer (doc/06-ee-layers.md §7).
LARGE_PROPERTY_HA = _int("CS_LARGE_PROPERTY_HA", 50_000)

#: Declared vs. computed area disagreement worth flagging (D6, still open):
#: whichever of these is larger.
AREA_DELTA_FLAG_PCT = float(os.environ.get("CS_AREA_DELTA_FLAG_PCT", "2.0"))
AREA_DELTA_FLAG_HA = float(os.environ.get("CS_AREA_DELTA_FLAG_HA", "5.0"))

# --------------------------------------------------------------------------- #
# Map
# --------------------------------------------------------------------------- #
DEFAULT_BASEMAP = os.environ.get("CS_BASEMAP", "google_hybrid")
#: Centre of Brazil, zoomed to the whole country.
DEFAULT_CENTER = (-14.5, -52.0)
DEFAULT_ZOOM = _int("CS_DEFAULT_ZOOM", 4)

# --------------------------------------------------------------------------- #
# Feature flags
# --------------------------------------------------------------------------- #
#: SPOT 2008 requires accepting the "Brazil Forest Imagery Dataset 2008" licence
#: agreement, granted per service account. Verified working for ee-leandromet on
#: 2026-08-23 (both VISUAL and ANALYTIC mint tile URLs), so the default is on and
#: this flag is the kill switch for a deployment whose account lacks the grant.
#: When off, the layers are DROPPED from the panel rather than offered and then
#: failing — an option that never works is worse than one that is not there.
#: See doc/12-spot-2008.md.
SPOT_ENABLED = os.environ.get("CS_SPOT_ENABLED", "true").lower() != "false"

# --------------------------------------------------------------------------- #
# Geocoding  (doc/11-search-and-navigation.md §5, decision D11)
# --------------------------------------------------------------------------- #
#: Nominatim's usage policy caps this at roughly one request per second and
#: forbids bulk use. It is the LAST of four resolvers — a code, a coordinate or a
#: município name never reaches it.
GEOCODER_URL = os.environ.get(
    "CS_GEOCODER_URL", "https://nominatim.openstreetmap.org/search"
)
GEOCODER_ENABLED = os.environ.get("CS_GEOCODER_ENABLED", "true").lower() != "false"
GEOCODER_USER_AGENT = os.environ.get(
    "CS_GEOCODER_USER_AGENT",
    "Camposcope/0.1 (+https://github.com/leandromet/camposcope)",
)
GEOCODER_TIMEOUT_READ = _int("CS_GEOCODER_TIMEOUT_READ", 20)
#: Never widen this. The app covers Brazil; a search that can wander off it will.
GEOCODER_COUNTRY_CODES = "br"

#: Brazil's bounding box, used to refuse a transposed coordinate pair BEFORE it
#: resolves to somewhere plausible in the South Atlantic
#: (doc/11-search-and-navigation.md §3).
BRAZIL_BBOX = (-74.0, -34.0, -28.0, 6.0)   # west, south, east, north

# --------------------------------------------------------------------------- #
# Transitions  (doc/07-transitions.md §5, open question O1)
# --------------------------------------------------------------------------- #
#: Year pairs closer than this are refused for a Sankey: at one- or two-year
#: gaps most "transitions" are classification flicker in mixed pixels, not
#: events on the ground.
SANKEY_MIN_YEAR_GAP = _int("CS_SANKEY_MIN_YEAR_GAP", 5)
