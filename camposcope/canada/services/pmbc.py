"""The only module that knows the ParcelMap BC WFS exists.

Canada's counterpart to :mod:`camposcope.services.sicar`, and it keeps that
module's two load-bearing design rules:

**There is no "fetch layer" function.** Every public entry point takes a
discriminator — a PID, a fabric id, a point, or a municipality — so an
unfiltered query against a province-wide layer of roughly two million parcels
cannot be constructed by accident.

**One request at a time.** openmaps.gov.bc.ca is a public service the Province
runs for everyone; serialising through ``_LOCK`` makes politeness structural
rather than a matter of remembering, exactly as constraint C5 does for SICAR.

Three things are *simpler* here than on the Brazil side, and each removes a
whole class of bug rather than merely saving code:

1. **One province-wide layer**, not 27 per-state ones. A map click needs no
   boundary lookup to decide which layer to query, so the Brazil page's
   decision D5 — and the "guessed the wrong UF, got an empty result that looks
   like *no property here*" failure it exists to prevent — simply does not
   arise. A bounds check against BC is still done first, but only to fail fast,
   never to route.
2. **No TLS workarounds.** ``geoserver.car.gov.br`` needs a pinned TLS 1.2
   context at ``SECLEVEL=1`` to negotiate at all (see ``sicar.py::_Tls12Adapter``
   for that whole investigation). ``openmaps.gov.bc.ca`` serves a complete
   modern chain — verified from a plain session on 2026-08-27 — so this client
   is an ordinary ``requests.Session``.
3. **Overlaps are not the normal case.** The CAR is self-declared and
   registrations routinely overlap, which is why its point query returns a list
   the caller must present rather than resolve (decision D7). A surveyed parcel
   fabric is topologically clean: a point normally hits exactly one parcel. It
   can still hit more — air-space parcels, building strata and subsurface
   interests genuinely stack over the same ground — so this **also** returns a
   list and **also** never picks for the user. The chooser is rare here rather
   than routine, and its copy says why the stack exists instead of warning about
   contested boundaries.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from ..config import pmbc as vocab
from ..config.settings import (
    PMBC_BASE,
    PMBC_CACHE_TTL_S,
    PMBC_TIMEOUT_CONNECT,
    PMBC_TIMEOUT_READ,
    PMBC_USER_AGENT,
    PMBC_VERIFY_TLS,
    PMBC_WMS,
)

logger = logging.getLogger(__name__)

_TIMEOUT = (PMBC_TIMEOUT_CONNECT, PMBC_TIMEOUT_READ)

#: Serialises ParcelMap BC traffic across the whole process. No v1 scenario
#: needs two concurrent requests, and a background Reflex handler plus a user
#: click can otherwise fire together.
_LOCK = threading.Lock()

_session: Optional[requests.Session] = None
_session_lock = threading.Lock()


class PmbcError(RuntimeError):
    """A failure talking to the ParcelMap BC WFS.

    Deliberately distinct from every other error in the app, for the same
    reason ``SicarError`` is: the UI shows a cadastral failure differently from
    an Earth Engine failure, because the two halves fail independently and a
    parcel that will not load must not take the land-cover analysis with it.
    """


def get_session() -> requests.Session:
    """A configured session, created once."""
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                s = requests.Session()
                s.headers.update({
                    "User-Agent": PMBC_USER_AGENT,
                    "Accept": "application/json, application/xml;q=0.8",
                })
                s.verify = PMBC_VERIFY_TLS
                _session = s
    return _session


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #
@dataclass
class _Entry:
    value: Any
    stored_at: float
    ttl: Optional[float]

    def fresh(self) -> bool:
        return self.ttl is None or (time.time() - self.stored_at) < self.ttl


_cache: Dict[str, _Entry] = {}
_cache_lock = threading.Lock()


def _cached(key: str, ttl: Optional[float], produce):
    """Memoise ``produce()`` under ``key``.

    ``ttl=None`` means the process lifetime — used for identifier lookups, since
    a parcel's boundary does not change during a session. Municipality pages get
    a real TTL.
    """
    with _cache_lock:
        hit = _cache.get(key)
        if hit is not None and hit.fresh():
            return hit.value
    value = produce()
    with _cache_lock:
        _cache[key] = _Entry(value, time.time(), ttl)
    return value


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


# --------------------------------------------------------------------------- #
# The record
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Parcel:
    """One ParcelMap BC parcel, as published.

    Attributes are carried **verbatim** from the service. ``area_registered_ha``
    is named for what it is: the fabric's own ``FEATURE_AREA_SQM``, converted to
    hectares but not otherwise touched. The geometric area is computed
    separately (``canada/services/zones.py``) and shown alongside it, never
    instead of it — the same discipline decision D6 imposes on the Brazil page,
    and it matters here too: ``FEATURE_AREA_SQM`` is computed in BC Albers by
    the warehouse, this app computes its own in the same projection, and the two
    agreeing is a check rather than a foregone conclusion.
    """

    fabric_id: int
    pid: str                     # nine digits, or "" for a parcel with no PID
    pid_formatted: str
    pin: Optional[int]
    parcel_name: str
    plan_number: str
    parcel_status: str
    parcel_class: str
    owner_type: str
    parcel_start_date: Optional[str]
    municipality: str
    regional_district: str
    when_updated: Optional[str]
    area_registered_ha: float
    geometry: Optional[dict] = field(default=None, repr=False)
    queried_at: str = ""

    @property
    def start_year(self) -> Optional[int]:
        """The parcel's start year — the axis that splits the forest-change
        series, where the Brazil page uses the CAR registration year.

        **Frequently absent, and that is normal.** ``PARCEL_START_DATE`` is
        populated for parcels created since the fabric was digitised and null
        for the large majority of older ones — the first parcel probed during
        development had none. Callers must handle ``None`` by degrading to an
        undivided series with a visible note, never by substituting a plausible
        default: a made-up anchor date would put real forest loss in the wrong
        bucket and there would be nothing on screen to say so.
        """
        if not self.parcel_start_date:
            return None
        try:
            return int(str(self.parcel_start_date)[:4])
        except (ValueError, TypeError):
            return None

    @property
    def identifier(self) -> str:
        """What to show, and what a deep link carries.

        The PID when there is one, the fabric id otherwise. A great many BC
        parcels — Crown land, road right-of-ways, unregistered parcels — have no
        PID at all, so an app keyed only on PID could not address them.
        """
        return self.pid_formatted or f"PF-{self.fabric_id}"

    @property
    def is_non_land(self) -> bool:
        """Whether this parcel class has no meaningful land cover of its own —
        a road right-of-way, an air-space parcel, a strata unit or a registered
        interest. Not hidden, only flagged: a click that lands on one must say
        what it landed on."""
        return self.parcel_class in vocab.NON_LAND_CLASSES

    @classmethod
    def from_feature(cls, feat: dict, queried_at: str) -> "Parcel":
        p = feat.get("properties") or {}
        raw_pid = str(p.get("PID") or "").strip()
        area_sqm = float(p.get("FEATURE_AREA_SQM") or 0.0)
        return cls(
            fabric_id=int(p.get("PARCEL_FABRIC_POLY_ID") or 0),
            pid=raw_pid,
            pid_formatted=(p.get("PID_FORMATTED")
                           or (vocab.format_pid(raw_pid) if raw_pid else "")),
            pin=int(p["PIN"]) if p.get("PIN") is not None else None,
            parcel_name=p.get("PARCEL_NAME") or "",
            plan_number=p.get("PLAN_NUMBER") or "",
            parcel_status=p.get("PARCEL_STATUS") or "",
            parcel_class=p.get("PARCEL_CLASS") or "",
            owner_type=p.get("OWNER_TYPE") or "",
            parcel_start_date=p.get("PARCEL_START_DATE"),
            municipality=p.get("MUNICIPALITY") or "",
            regional_district=p.get("REGIONAL_DISTRICT") or "",
            when_updated=p.get("WHEN_UPDATED"),
            area_registered_ha=area_sqm / 10_000.0,
            geometry=feat.get("geometry"),
            queried_at=queried_at,
        )


# --------------------------------------------------------------------------- #
# Transport
# --------------------------------------------------------------------------- #
def _get(params: Dict[str, Any], *, base: str = PMBC_BASE) -> requests.Response:
    """One serialised, timed, identified GET.

    Retries once on a transport error, then gives up: a public service that is
    down should produce an error naming it, not a retry loop.
    """
    session = get_session()
    last: Optional[Exception] = None
    for attempt in (1, 2):
        with _LOCK:
            try:
                started = time.monotonic()
                r = session.get(base, params=params, timeout=_TIMEOUT)
                elapsed = time.monotonic() - started
            except requests.RequestException as exc:      # transport-level
                last = exc
                logger.warning("ParcelMap BC request failed (attempt %d): %s",
                               attempt, exc)
                time.sleep(1.5 * attempt)
                continue
        logger.info("PMBC %s → %d in %.2fs",
                    params.get("request"), r.status_code, elapsed)
        if r.status_code >= 500 and attempt == 1:
            last = PmbcError(f"HTTP {r.status_code}")
            time.sleep(1.5)
            continue
        if r.status_code != 200:
            raise PmbcError(
                f"The ParcelMap BC service responded HTTP {r.status_code}."
            )
        return r
    raise PmbcError(
        f"Could not reach the ParcelMap BC service ({base}): {last}"
    )


def _get_json(params: Dict[str, Any], *, base: str = PMBC_BASE) -> dict:
    r = _get(params, base=base)
    try:
        return r.json()
    except ValueError as exc:
        # An OWS ExceptionReport comes back as XML with HTTP 200 — the same trap
        # the SICAR client documents. Surfacing the first 200 characters beats
        # "Expecting value: line 1 column 1", and the BC service's exception
        # text is unusually good (it lists the valid property names).
        snippet = r.text[:200].replace("\n", " ")
        raise PmbcError(
            f"Unexpected response from ParcelMap BC: {snippet}"
        ) from exc


def _wfs(**overrides: Any) -> Dict[str, Any]:
    """WFS 2.0.0 parameters.

    2.0.0 throughout, unlike the SICAR client's 1.0.0 — the BC service supports
    it fully, and 2.0.0 is what makes ``count``/``startIndex`` paging and
    ``resultType=hits`` available in the first place.
    """
    base = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": vocab.LAYER,
        "outputFormat": "application/json",
        "srsName": vocab.REQUEST_CRS,   # server-side reprojection, always
    }
    base.update(overrides)
    return base


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _quote(value: str) -> str:
    """CQL string literal — single quotes doubled.

    Load-bearing here in a way it is not for a CAR code: BC municipality names
    are free text and several contain apostrophes (``Qualicum Beach, Town of``
    is fine; ``Lake Cowichan`` is fine; but the regional-district list includes
    names that do not survive naive interpolation).
    """
    return "'" + str(value).replace("'", "''") + "'"


# --------------------------------------------------------------------------- #
# 1. Parcel by identifier
# --------------------------------------------------------------------------- #
def by_pid(pid: str) -> Parcel:
    """Fetch one parcel by its Parcel Identifier.

    The PID is validated and normalised **locally** first, so a malformed paste
    fails instantly and no request reaches the service.
    """
    digits = vocab.parse_pid(pid)          # raises PidError on a bad shape

    def produce() -> Parcel:
        data = _get_json(_wfs(cql_filter=f"PID={_quote(digits)}"))
        feats = data.get("features") or []
        if not feats:
            raise PmbcError(
                f"No parcel found for PID {vocab.format_pid(digits)}. The "
                "parcel may have been cancelled by a subdivision, or the PID "
                "may not exist."
            )
        return Parcel.from_feature(feats[0], _now())

    # No TTL: a boundary does not change during a session.
    return _cached(f"pid:{digits}", None, produce)


def by_fabric_id(fabric_id: int) -> Parcel:
    """Fetch one parcel by ``PARCEL_FABRIC_POLY_ID``.

    The addressing route for the many BC parcels that carry no PID — see
    :attr:`Parcel.identifier`.
    """
    key = int(fabric_id)

    def produce() -> Parcel:
        data = _get_json(_wfs(cql_filter=f"PARCEL_FABRIC_POLY_ID={key}"))
        feats = data.get("features") or []
        if not feats:
            raise PmbcError(f"No parcel found for fabric id {key}.")
        return Parcel.from_feature(feats[0], _now())

    return _cached(f"pf:{key}", None, produce)


def by_identifier(value: str) -> Parcel:
    """Whichever of the two identifier forms this is.

    PID first — nine digits is the form a user actually has in hand, off a tax
    notice or a title search — then the fabric id.
    """
    raw = str(value).strip()
    try:
        return by_pid(raw)
    except vocab.PidError:
        pass
    return by_fabric_id(vocab.parse_fabric_id(raw))


# --------------------------------------------------------------------------- #
# 2. Parcels at a point
# --------------------------------------------------------------------------- #
def at_point(lat: float, lon: float, *, limit: int = 25) -> List[Parcel]:
    """Every parcel whose polygon contains this point.

    Returns a **list**, and callers must handle more than one — see the module
    docstring for why a clean surveyed fabric still stacks parcels over the same
    ground. Sorted largest-first, which is the order the chooser presents, so
    the parcel of land comes before the air-space parcel above it.
    """
    # CQL POINT is (lon lat). The explicit SRID prefix is required by this
    # service — an unqualified POINT() is interpreted in the layer's native
    # BC Albers metres and silently matches nothing.
    cql = (f"INTERSECTS({vocab.GEOM_COLUMN}, "
           f"SRID=4326;POINT({lon:.7f} {lat:.7f}))")

    def produce() -> List[Parcel]:
        data = _get_json(_wfs(count=limit, cql_filter=cql))
        now = _now()
        found = [Parcel.from_feature(f, now) for f in data.get("features") or []]
        found.sort(key=lambda p: p.area_registered_ha, reverse=True)
        return found

    return _cached(f"pt:{lat:.6f}:{lon:.6f}:{limit}", PMBC_CACHE_TTL_S, produce)


# --------------------------------------------------------------------------- #
# 3. Neighbouring parcels
# --------------------------------------------------------------------------- #
def neighbours(parcel: Parcel, *, limit: int = 50) -> List[Parcel]:
    """Other parcels that intersect this one.

    The Brazil page calls the equivalent ``overlapping`` and treats what it
    finds as *contested boundaries*, because in a self-declared cadastre that is
    what an overlap usually is. Here the same query mostly returns **adjacent**
    parcels sharing an edge, which is not a finding at all — a surveyed fabric
    is supposed to tile. So the results are filtered by real intersection area
    downstream (``canada/services/zones.py::overlap_areas`` drops edge-only
    touches), and what survives — a genuine area overlap — is the interesting
    case precisely because it should not happen.
    """
    if not parcel.geometry:
        return []
    from shapely.geometry import shape       # local: keeps import cost off startup

    wkt = shape(parcel.geometry).wkt

    def produce() -> List[Parcel]:
        data = _get_json(_wfs(
            count=limit,
            cql_filter=(f"INTERSECTS({vocab.GEOM_COLUMN}, "
                        f"SRID=4326;{wkt})"),
        ))
        now = _now()
        return [
            Parcel.from_feature(f, now)
            for f in data.get("features") or []
            if int((f.get("properties") or {}).get("PARCEL_FABRIC_POLY_ID") or 0)
            != parcel.fabric_id
        ]

    return _cached(f"nbr:{parcel.fabric_id}:{limit}", PMBC_CACHE_TTL_S, produce)


# --------------------------------------------------------------------------- #
# 4. Municipality browser
# --------------------------------------------------------------------------- #
#: Parcels outside any incorporated municipality carry the literal string
#: ``"Rural"`` in ``MUNICIPALITY`` — not null, and not the name of anything.
#: Verified live 2026-08-27 on a parcel in the Central Okanagan countryside.
#: That covers a great deal of exactly the land this app is about, and it is
#: useless as a browse key: every unincorporated parcel in the province shares
#: the one value. So the browser can scope by either field, and for rural land
#: the regional district is the one that actually names somewhere.
SCOPE_MUNICIPALITY = "MUNICIPALITY"
SCOPE_REGIONAL_DISTRICT = "REGIONAL_DISTRICT"


def _scope_filter(scope: str, name: str) -> str:
    if scope not in (SCOPE_MUNICIPALITY, SCOPE_REGIONAL_DISTRICT):
        raise ValueError(f"Unknown parcel browser scope: {scope!r}")
    return f"{scope}={_quote(name)}"


def count_in_scope(scope: str, name: str) -> int:
    """How many parcels, without fetching any.

    ``resultType=hits`` returns a header-only XML document — this is what makes
    the "48 213 parcels" line free. Verified against the live service; the count
    arrives as a ``numberMatched`` attribute on the ``wfs:FeatureCollection``
    element.
    """
    def produce() -> int:
        r = _get({
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": vocab.LAYER,
            "resultType": "hits",
            "cql_filter": _scope_filter(scope, name),
        })
        m = re.search(r'numberMatched="(\d+)"', r.text)
        if not m:
            raise PmbcError("ParcelMap BC did not report a count.")
        return int(m.group(1))

    return _cached(f"cnt:{scope}:{name}", PMBC_CACHE_TTL_S, produce)


def list_in_scope(
    scope: str,
    name: str,
    *,
    page: int = 0,
    page_size: int = 25,
    sort: str = "FEATURE_AREA_SQM D",
    land_only: bool = True,
) -> List[Parcel]:
    """One page of a municipality's or regional district's parcels, **without
    geometry**.

    ``propertyName`` excluding the geometry column is the difference between a
    page costing kilobytes and costing megabytes. The geometry arrives only when
    a row is chosen, through :func:`by_fabric_id`.

    ``name`` for :data:`SCOPE_MUNICIPALITY` is the fabric's own full form —
    ``"Kelowna, City of"``, not ``"Kelowna"`` — or the literal ``"Rural"`` for
    unincorporated land. ``canada/services/municipalities.py`` is what turns a
    name a human typed into one of these.

    ``land_only`` drops road right-of-ways and the other non-land classes from
    the *browse* list — unlike a map click, where landing on one must be
    reported, a list of a municipality's parcels sorted by area is otherwise
    headed by its road network, which is nobody's answer to "show me the
    properties here".
    """
    def produce() -> List[Parcel]:
        cql = _scope_filter(scope, name)
        if land_only:
            excluded = ",".join(_quote(c) for c in sorted(vocab.NON_LAND_CLASSES))
            cql = f"{cql} AND PARCEL_CLASS NOT IN ({excluded})"
        data = _get_json(_wfs(
            count=int(page_size),
            startIndex=int(page) * int(page_size),
            sortBy=sort,
            propertyName=",".join(vocab.LIST_ATTRIBUTES),
            cql_filter=cql,
        ))
        now = _now()
        return [Parcel.from_feature(f, now) for f in data.get("features") or []]

    key = f"lst:{scope}:{name}:{page}:{page_size}:{sort}:{land_only}"
    return _cached(key, PMBC_CACHE_TTL_S, produce)


# --------------------------------------------------------------------------- #
# 5. The WMS context layer
# --------------------------------------------------------------------------- #
def wms_layer_spec(*, opacity: float = 0.6) -> Dict[str, Any]:
    """Leaflet ``L.tileLayer.wms`` options for the whole parcel fabric.

    Drawing roughly two million polygons is the server's problem, not ours —
    this is why the context layer is WMS and not WFS, the same reasoning the
    Brazil page applies to 218 000 CAR polygons.
    """
    return {
        "url": PMBC_WMS,
        "layers": vocab.LAYER,
        "format": "image/png",
        "transparent": True,
        "version": "1.1.1",
        "opacity": opacity,
        "attribution": f"{vocab.SOURCE_NAME} — {vocab.SOURCE_ORG}",
    }


__all__ = [
    "Parcel", "PmbcError",
    "by_pid", "by_fabric_id", "by_identifier", "at_point", "neighbours",
    "count_in_scope", "list_in_scope",
    "SCOPE_MUNICIPALITY", "SCOPE_REGIONAL_DISTRICT",
    "wms_layer_spec", "clear_cache", "get_session",
]
