"""Resolving what the user typed (doc/11-search-and-navigation.md).

Six resolvers, tried in a fixed order and stopping at the first match: a CAR
code, a CEP, a coordinate, a município, a protected territory (terra indígena
or unidade de conservação), a place name or street address. The order is not
arbitrary — the first five are exact (a CEP is recognised locally and then
looked up, see ``services/address.py``), and only the last is a guess against
someone else's public service. Most searches therefore never reach a geocoder at all, which is
what keeps the geocoder usage defensible (decision D11).

The território resolver is the one that does not *only* stop at the first
match. A município and a territory can share a name — "Jaú" is both a município
in São Paulo and a national park in Amazonas — and picking one silently would
be a coin flip. So a query that matches a município still carries its territory
hits alongside (``Resolution.territorios``): the echo line still says
"município", because that is what the input reads as first, and the territory
matches are offered rather than assumed.

**A place-name or territory result frames the map and selects no property.**
Finding a place and identifying a registration are different acts; a fuzzy
address match must never become an implied claim about who holds what.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import address
from .address import Place
from ..config.settings import (
    BRAZIL_BBOX,
    GEOCODER_COUNTRY_CODES,
    GEOCODER_ENABLED,
    GEOCODER_TIMEOUT_READ,
    GEOCODER_URL,
    GEOCODER_USER_AGENT,
    SICAR_TIMEOUT_CONNECT,
)

logger = logging.getLogger(__name__)

WEST, SOUTH, EAST, NORTH = BRAZIL_BBOX


class GeocodeError(RuntimeError):
    """A failure talking to the geocoding service."""


# --------------------------------------------------------------------------- #
# Coordinates
# --------------------------------------------------------------------------- #
#: A Google Maps URL carries the coordinate in one of two places.
_GMAPS_AT = re.compile(r"@(-?\d+(?:[.,]\d+)?),(-?\d+(?:[.,]\d+)?)")
_GMAPS_Q = re.compile(r"[?&]q=(-?\d+(?:[.,]\d+)?)(?:,|%2C)\s*(-?\d+(?:[.,]\d+)?)")

#: 12°29'52.5"S  /  12 29 52.5 S  /  12º29'52.5''S
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

    pt-BR keyboards produce commas, and ``-12,4979 -55,4977`` is a real thing
    users paste.
    """
    return float(raw.strip().replace(",", "."))


def _hemisphere_sign(hem: str) -> int:
    # 'L' = leste and 'O' = oeste, the Portuguese cardinal letters.
    return -1 if hem.upper() in ("S", "W", "O") else 1


def _in_brazil(lat: float, lon: float) -> bool:
    return SOUTH <= lat <= NORTH and WEST <= lon <= EAST


def parse_coordinates(text: str) -> Optional[Coordinate]:
    """Parse a coordinate in any of the formats users actually paste.

    Returns ``None`` when the text is not a coordinate at all — that is not an
    error, it just means the next resolver should try. Raises ``ValueError``
    when the text *is* a coordinate but an unusable one, because that deserves a
    message rather than a silent fall-through to a place-name search.

    **Latitude first**, always. The CQL the service layer builds is
    ``POINT(lon lat)`` (doc/05 §5.2), and that inversion lives there, not here.
    """
    raw = (text or "").strip()
    if not raw:
        return None

    # --- Google Maps URL ---------------------------------------------------
    for pattern in (_GMAPS_AT, _GMAPS_Q):
        m = pattern.search(raw)
        if m:
            lat, lon = _to_float(m.group(1)), _to_float(m.group(2))
            return _validated(lat, lon, "gmaps")

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
        # "-12,4979 -55,4977" is two comma-decimals separated by a space; but
        # "-12.4979, -55.4977" is two dot-decimals separated by a comma. Both
        # match the same pattern, and only the presence of a dot tells them
        # apart — so a value containing BOTH is ambiguous and refused.
        if "," in a and "." in a:
            raise ValueError(f"Coordenada ambígua: {a!r}")
        return _validated(_to_float(a), _to_float(b), "decimal")

    return None


def _validated(lat: float, lon: float, source: str) -> Coordinate:
    """Refuse a coordinate outside Brazil, naming which value looks wrong.

    A transposed pair (``-55.5, -12.5``) lands in the South Atlantic, and
    "nenhum imóvel neste ponto" would be a terrible answer to a transposition.
    """
    if _in_brazil(lat, lon):
        return Coordinate(lat=lat, lon=lon, source=source)

    if _in_brazil(lon, lat):
        raise ValueError(
            f"Coordenada fora do Brasil, mas {lon:.4f}, {lat:.4f} estaria dentro "
            "— os valores parecem invertidos. A latitude vem primeiro."
        )
    culprit = []
    if not (SOUTH <= lat <= NORTH):
        culprit.append(f"latitude {lat:.4f} (esperado entre {SOUTH} e {NORTH})")
    if not (WEST <= lon <= EAST):
        culprit.append(f"longitude {lon:.4f} (esperado entre {WEST} e {EAST})")
    raise ValueError("Coordenada fora do Brasil: " + "; ".join(culprit) + ".")


# --------------------------------------------------------------------------- #
# Place names, addresses and CEPs  (decision D11)
# --------------------------------------------------------------------------- #
#: The client lives in services/address.py (shared, verbatim, with the sibling
#: apps); this module only configures it for Brazil and keeps the error type
#: the state layer already catches.
_geocoder = address.AddressGeocoder(
    url=GEOCODER_URL,
    user_agent=GEOCODER_USER_AGENT,
    accept_language="pt-BR,pt",
    # Never widen this. The app covers Brazil; a search that can wander off
    # it will.
    countrycodes=GEOCODER_COUNTRY_CODES,
    enabled=GEOCODER_ENABLED,
    timeout=(SICAR_TIMEOUT_CONNECT, GEOCODER_TIMEOUT_READ),
    keep=_in_brazil,
    viewbox=BRAZIL_BBOX,
)


def search_places(query: str, *, limit: int = 6) -> List[Place]:
    """Geocode a place name or street address. **The last resort, never the
    first try.**

    Callers must have already ruled out a CAR code, a coordinate, a CEP and a
    município — see :func:`resolve`. Results are cached for the process
    lifetime; a place name does not move.
    """
    if not GEOCODER_ENABLED:
        raise GeocodeError("A busca por lugares está desativada nesta instalação.")
    try:
        return _geocoder.search(query, limit=limit)
    except address.AddressError as exc:
        raise GeocodeError(f"Não foi possível contatar o serviço de busca: {exc}")


def search_cep(digits: str) -> Tuple[List[Place], Optional[Dict[str, str]]]:
    """A CEP → its place(s), plus ViaCEP's record (whose ``ibge`` code lets the
    caller fall back to framing the município when OSM knows neither the CEP
    nor its street)."""
    if not GEOCODER_ENABLED:
        raise GeocodeError("A busca por lugares está desativada nesta instalação.")
    try:
        return _geocoder.search_cep(digits)
    except address.AddressError as exc:
        raise GeocodeError(f"Não foi possível contatar o serviço de busca: {exc}")


# --------------------------------------------------------------------------- #
# The unified resolver  (doc/11 §2)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Resolution:
    """What the search box decided the input was.

    ``kind`` drives both the action and the echo line the UI shows *before*
    acting — the line that stops a transposed pair or a mistyped code from
    quietly resolving somewhere plausible and wrong (doc/08-ui-ux.md §2).
    """

    kind: str            # "codigo" | "cep" | "coordenada" | "municipio" | "territorio" | "lugar" | "vazio"
    echo: str            # human-readable "read as …"
    payload: Any = None
    #: Territory matches carried ALONGSIDE a município hit, not instead of it —
    #: see this module's docstring for why. Always empty for every other kind:
    #: a CAR code or a coordinate is unambiguous, and a query that reached the
    #: geocoder matched no territory by definition.
    territorios: List[Dict[str, Any]] = field(default_factory=list)


def resolve(text: str) -> Resolution:
    """Classify the input without performing any network call.

    Deliberately does **not** geocode: it says *what it would do*, and the
    caller performs it. That keeps the echo line honest — the UI can show how
    the input was read before a single request goes out.
    """
    raw = (text or "").strip()
    if not raw:
        return Resolution("vazio", "")

    # 1 — CAR code. Exact and local.
    from ..config import sicar as vocab

    if vocab.COD_IMOVEL_RE.match(raw.upper()):
        code = vocab.normalise_cod_imovel(raw)
        return Resolution("codigo", f"código CAR {code}", code)

    # 1b — CEP. Exact, and recognised locally; only acting on it needs a
    # lookup. Before the coordinate parser so "78890-000" can never be read
    # as anything numeric.
    cep = address.parse_cep(raw)
    if cep:
        return Resolution("cep", f"CEP {address.format_cep(cep)}", cep)

    # 2 — coordinate. Exact and local. A ValueError here is a real message.
    coord = parse_coordinates(raw)
    if coord is not None:
        return Resolution(
            "coordenada",
            f"coordenada {coord.lat:.4f}, {coord.lon:.4f}",
            coord,
        )

    # 3 — município. Exact and local (decision D12).
    from . import municipios, territorios

    matches = municipios.search(raw, limit=5)
    # 4 — território. Exact and local too, so it costs the same nothing to run
    # it even when a município already matched — which is exactly what lets a
    # name shared by both be offered rather than silently decided.
    territory_hits = territorios.search(raw, limit=8)

    if matches:
        first = matches[0]
        return Resolution(
            "municipio",
            f"município {first['nome']}/{first['uf']}",
            matches,
            territory_hits,
        )

    if territory_hits:
        first = territory_hits[0]
        return Resolution(
            "territorio",
            f"território {first['nome']}",
            territory_hits,
        )

    # 5 — place name. The only resolver that touches a third party.
    return Resolution("lugar", f"lugar “{raw}”", raw)


__all__ = [
    "Coordinate", "Place", "Resolution", "GeocodeError",
    "parse_coordinates", "search_places", "search_cep", "resolve",
]
