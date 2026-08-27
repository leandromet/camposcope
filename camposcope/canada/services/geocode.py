"""Resolving what the user typed, on the Canada page.

Four resolvers, tried in a fixed order and stopping at the first match: a parcel
identifier, a coordinate, a BC municipality or regional district, a place name.
The order is the Brazil page's and so is the reasoning — the first three are
exact and local, only the fourth is a guess against someone else's public
service, so most searches never reach a geocoder at all.

**A place-name result frames the map and selects no parcel.** Finding a place
and identifying a parcel are different acts, and a fuzzy address match must
never become an implied claim about a specific piece of land.

**What differs from the Brazil resolver, beyond the vocabulary.** Rural
addresses barely exist in either country, but BC has something Brazil does not:
addresses on the map are *good*, and a user is far more likely to type "4700
Lakeshore Road" than a PID. That is exactly why address search stays last
anyway — a street address resolves to a point on a road, and the parcel it
fronts is a guess. Framing the map there and letting the user click the parcel
they mean is the honest interaction; auto-selecting the nearest parcel to a
geocoded pin would be inventing a match.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from ...config.settings import (
    GEOCODER_ENABLED,
    GEOCODER_TIMEOUT_READ,
    GEOCODER_URL,
    GEOCODER_USER_AGENT,
)
from ..config.settings import (
    CANADA_BBOX,
    GEOCODER_COUNTRY_CODES,
    PMBC_TIMEOUT_CONNECT,
)
from . import bc_lookup

logger = logging.getLogger(__name__)

CA_WEST, CA_SOUTH, CA_EAST, CA_NORTH = CANADA_BBOX


class GeocodeError(RuntimeError):
    """A failure talking to the geocoding service."""


# --------------------------------------------------------------------------- #
# Coordinates
# --------------------------------------------------------------------------- #
#: A Google Maps URL carries the coordinate in one of two places.
_GMAPS_AT = re.compile(r"@(-?\d+(?:[.,]\d+)?),(-?\d+(?:[.,]\d+)?)")
_GMAPS_Q = re.compile(r"[?&]q=(-?\d+(?:[.,]\d+)?)(?:,|%2C)\s*(-?\d+(?:[.,]\d+)?)")

#: 49°53'16.8"N  /  49 53 16.8 N  /  49º53'16.8''N
_DMS = re.compile(
    r"""(?P<deg>\d{1,3})\s*[°º:\s]\s*
        (?P<min>\d{1,2})\s*['′:\s]\s*
        (?P<sec>\d{1,2}(?:[.,]\d+)?)\s*(?:["”″']{0,2})\s*
        (?P<hem>[NSEWLO])""",
    re.VERBOSE | re.IGNORECASE,
)

_DECIMAL_PAIR = re.compile(
    r"^\s*(-?\d{1,3}(?:[.,]\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:[.,]\d+)?)\s*$"
)


@dataclass(frozen=True)
class Coordinate:
    lat: float
    lon: float
    source: str          # "decimal" | "dms" | "gmaps"


def _to_float(raw: str) -> float:
    """Accept ``.`` or ``,`` as the decimal separator.

    Kept from the Brazil resolver even though the Canada page defaults to
    English: the two pages share a user, and someone who pastes
    ``49,88 -119,49`` out of habit deserves an answer rather than a fall-through
    to an address search.
    """
    return float(raw.strip().replace(",", "."))


def _hemisphere_sign(hem: str) -> int:
    # 'L' = leste and 'O' = oeste, the Portuguese cardinal letters — a
    # pt-BR-keyboard user on the Canada page still types them.
    return -1 if hem.upper() in ("S", "W", "O") else 1


def parse_coordinates(text: str) -> Optional[Coordinate]:
    """Parse a coordinate in any of the formats users actually paste.

    Returns ``None`` when the text is not a coordinate at all — not an error,
    it just means the next resolver should try. Raises ``ValueError`` when the
    text *is* a coordinate but an unusable one, because that deserves a message
    rather than a silent fall-through to a place-name search.

    **Latitude first**, always. The CQL the service layer builds is
    ``POINT(lon lat)``, and that inversion lives there, not here.
    """
    raw = (text or "").strip()
    if not raw:
        return None

    # --- Google Maps URL ---------------------------------------------------
    for pattern in (_GMAPS_AT, _GMAPS_Q):
        m = pattern.search(raw)
        if m:
            return _validated(_to_float(m.group(1)), _to_float(m.group(2)),
                              "gmaps")

    # --- DMS ---------------------------------------------------------------
    dms = list(_DMS.finditer(raw))
    if len(dms) >= 2:
        values: Dict[str, float] = {}
        for m in dms[:2]:
            deg = float(m.group("deg"))
            minutes = float(m.group("min"))
            seconds = _to_float(m.group("sec"))
            hem = m.group("hem").upper()
            decimal = (deg + minutes / 60 + seconds / 3600) * _hemisphere_sign(hem)
            values["lat" if hem in ("N", "S") else "lon"] = decimal
        if "lat" in values and "lon" in values:
            return _validated(values["lat"], values["lon"], "dms")

    # --- decimal pair ------------------------------------------------------
    m = _DECIMAL_PAIR.match(raw)
    if m:
        a, b = m.group(1), m.group(2)
        # "49,88 -119,49" is two comma-decimals separated by a space; but
        # "49.88, -119.49" is two dot-decimals separated by a comma. Both match
        # the same pattern, and only the presence of a dot tells them apart —
        # so a value containing BOTH is ambiguous and refused.
        if "," in a and "." in a:
            raise ValueError(f"Ambiguous coordinate: {a!r}")
        return _validated(_to_float(a), _to_float(b), "decimal")

    return None


def _validated(lat: float, lon: float, source: str) -> Coordinate:
    """Refuse a coordinate outside Canada, naming which value looks wrong.

    **Not** refused for being outside BC. A parcel search is BC-only, but a
    coordinate is a request to analyse *somewhere*, and the three-tier chain
    ``CanadaParcelMixin.select_at_point`` runs — parcel, then protected area,
    then a synthetic analysis square — answers everywhere in the country
    except a handful of BC-only steps at the top. Refusing here for anything
    short of "not in Canada at all" would block search from ever reaching the
    two tiers that do not need BC at all.

    Transposition is still worth catching on its own terms: Canada's latitude
    range (41–83.5) and longitude range (-141.5 to -52) do not overlap, so a
    swapped pair is unambiguous rather than merely suspicious, and left
    unchecked it lands somewhere on a different continent with nothing to say
    why.
    """
    verdict = bc_lookup.classify(lat, lon)
    if verdict in ("bc", "canada"):
        return Coordinate(lat=lat, lon=lon, source=source)

    if verdict == "swapped":
        raise ValueError(
            f"That is outside Canada, but {lon:.4f}, {lat:.4f} would be "
            "inside — the values look transposed. Latitude comes first."
        )

    culprit = []
    if not (CA_SOUTH <= lat <= CA_NORTH):
        culprit.append(
            f"latitude {lat:.4f} (expected between {CA_SOUTH} and {CA_NORTH})")
    if not (CA_WEST <= lon <= CA_EAST):
        culprit.append(
            f"longitude {lon:.4f} (expected between {CA_WEST} and {CA_EAST})")
    raise ValueError("Coordinate outside Canada: " + "; ".join(culprit) + ".")


# --------------------------------------------------------------------------- #
# Place names
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Place:
    """A geocoded place. Frames the map; never selects a parcel."""

    label: str
    lat: float
    lon: float
    #: ``[[south, west], [north, east]]`` — framing a bbox is honest about
    #: uncertainty in a way a single pin is not.
    bounds: Optional[List[List[float]]]
    attribution: str = "© OpenStreetMap contributors (ODbL)"


#: Nominatim's policy caps us at ~1 request/second and forbids bulk use, so
#: requests serialise through here exactly as the parcel service's do.
_LOCK = threading.Lock()
_cache: Dict[str, List[Place]] = {}
_cache_lock = threading.Lock()
_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": GEOCODER_USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "en-CA,en",
        })
        _session = s
    return _session


def search_places(query: str, *, limit: int = 5) -> List[Place]:
    """Geocode a place name. **The last resort, never the first try.**

    Results outside Canada are dropped rather than shown: ``countrycodes=ca``
    alone still lets through Nominatim's occasional cross-border mismatch (a
    "Vancouver" candidate in Washington State, say), and framing the map
    there would put the user somewhere this page cannot answer about, with
    nothing on screen to say why. Nowhere near as narrow a filter as the BC-
    only one this function used to apply: the analysis chain a place-search
    result feeds into (``select_at_point``'s parcel → protected-area →
    synthetic-square tiers) now answers anywhere in the country, so a result
    in Manitoba is exactly as usable as one in the Fraser Valley.
    """
    q = (query or "").strip()
    if not q:
        return []
    if not GEOCODER_ENABLED:
        raise GeocodeError("Place search is disabled in this installation.")

    key = f"{q.lower()}:{limit}"
    with _cache_lock:
        hit = _cache.get(key)
        if hit is not None:
            return hit

    params = {
        "q": q,
        "format": "jsonv2",
        # Over-fetch, because the BC filter below discards some of what comes
        # back and the user should still get `limit` usable results.
        "limit": limit * 3,
        "countrycodes": GEOCODER_COUNTRY_CODES,
        # Bias toward Canada. A hint, not a filter — Nominatim will still
        # return matches outside the box, which is why the filter below
        # exists too.
        "viewbox": f"{CA_WEST},{CA_NORTH},{CA_EAST},{CA_SOUTH}",
    }

    with _LOCK:
        try:
            r = _get_session().get(
                GEOCODER_URL, params=params,
                timeout=(PMBC_TIMEOUT_CONNECT, GEOCODER_TIMEOUT_READ),
            )
        except requests.RequestException as exc:
            raise GeocodeError(f"Could not reach the place-search service: {exc}")
        # One request per second is the policy; hold the lock for it rather than
        # trusting callers to pace themselves.
        time.sleep(1.0)

    if r.status_code != 200:
        raise GeocodeError(f"The place-search service responded HTTP "
                           f"{r.status_code}.")

    try:
        payload = r.json()
    except ValueError as exc:
        raise GeocodeError("Unexpected response from the place-search "
                           "service.") from exc

    places: List[Place] = []
    for item in payload:
        try:
            lat, lon = float(item["lat"]), float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if not bc_lookup.in_canada(lat, lon):
            continue
        bbox = item.get("boundingbox")
        bounds = None
        if bbox and len(bbox) == 4:
            try:
                s, n, w, e = (float(v) for v in bbox)
                bounds = [[s, w], [n, e]]
            except (TypeError, ValueError):
                bounds = None
        places.append(Place(label=item.get("display_name", q),
                            lat=lat, lon=lon, bounds=bounds))
        if len(places) >= limit:
            break

    with _cache_lock:
        _cache[key] = places
    return places


# --------------------------------------------------------------------------- #
# The unified resolver
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Resolution:
    """What the search box decided the input was.

    ``kind`` drives both the action and the echo line the UI shows *before*
    acting — the line that stops a transposed pair or a mistyped identifier from
    quietly resolving somewhere plausible and wrong.
    """

    kind: str        # "pid" | "coordenada" | "area" | "lugar" | "vazio"
    echo: str        # human-readable "read as …"
    payload: Any = None


def resolve(text: str) -> Resolution:
    """Classify the input without performing any network call.

    Deliberately does **not** geocode: it says *what it would do*, and the
    caller performs it. That keeps the echo line honest — the UI can show how
    the input was read before a single request goes out, which is what makes
    showing it on every keystroke affordable.
    """
    raw = (text or "").strip()
    if not raw:
        return Resolution("vazio", "")

    from ..config import pmbc as vocab

    # 1 — parcel identifier. Exact and local.
    #
    # PID before fabric id, and both before the coordinate parser, because a
    # bare nine-digit PID with no separators ("010322060") is not a coordinate
    # in any format and would otherwise fall through to an address search.
    if vocab.PID_RE.match(raw):
        digits = vocab.parse_pid(raw)
        return Resolution("pid", f"PID {vocab.format_pid(digits)}", digits)
    if vocab.FABRIC_ID_RE.match(raw) and raw.upper().startswith("PF-"):
        # A bare number is NOT treated as a fabric id: it is far more likely to
        # be half a coordinate or a house number, and silently loading an
        # arbitrary parcel would be worse than asking again. The "PF-" prefix
        # is how a user says they mean the fabric id — it is what the parcel
        # card shows and what a deep link carries.
        return Resolution("pid", f"parcel {raw.upper()}", raw.upper())

    # 2 — coordinate. Exact and local. A ValueError here is a real message.
    coord = parse_coordinates(raw)
    if coord is not None:
        return Resolution("coordenada",
                          f"coordinate {coord.lat:.4f}, {coord.lon:.4f}", coord)

    # 3 — municipality or regional district. Exact and local.
    from . import municipalities

    if municipalities.is_available():
        matches = municipalities.search(raw, limit=5)
        if matches:
            first = matches[0]
            return Resolution("area", f"area {first['short_name']}", matches)

    # 4 — place name. The only resolver that touches a third party.
    return Resolution("lugar", f"place “{raw}”", raw)


__all__ = [
    "Coordinate", "Place", "Resolution", "GeocodeError",
    "parse_coordinates", "search_places", "resolve",
]
