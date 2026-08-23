"""The only module that knows the CAR GeoServer exists.

Implements the four queries of doc/05-sicar-geoserver.md §5 and enforces the
client rules of §7. Everything above this module works with plain dicts and
never builds a URL.

Two design points worth keeping:

**There is no "fetch layer" function.** Every public entry point takes a
discriminator — a code, a point, or a municipality — so an unfiltered query
against a 218 000-polygon UF layer cannot be constructed by accident
(doc/05 §4).

**One request at a time.** The GeoServer is a public service run by the Serviço
Florestal Brasileiro for everyone; constraint C5 makes politeness structural
rather than a matter of remembering. Calls serialise through ``_LOCK``.
"""

from __future__ import annotations

import logging
import ssl
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter

from ..config import sicar as vocab
from ..config.settings import (
    SICAR_BASE,
    SICAR_CACHE_TTL_S,
    SICAR_TIMEOUT_CONNECT,
    SICAR_TIMEOUT_READ,
    SICAR_USER_AGENT,
    SICAR_VERIFY_TLS,
    SICAR_WMS,
)

logger = logging.getLogger(__name__)

_TIMEOUT = (SICAR_TIMEOUT_CONNECT, SICAR_TIMEOUT_READ)

#: Serialises SICAR traffic across the whole process (C5). There is no v1
#: scenario needing two concurrent requests, and a background Reflex handler
#: plus a user click can otherwise fire together.
_LOCK = threading.Lock()

_session: Optional[requests.Session] = None
_session_lock = threading.Lock()


class _Tls12Adapter(HTTPAdapter):
    """TLS parameters the public GeoServer actually accepts.

    Two independent things had to be fixed here, and pinning the protocol
    alone (the first attempt) fixed neither of them:

    **The real blocker is OpenSSL's cipher security level, not the TLS
    version.** Reproduced 2026-08 by running the exact `python:3.12-slim`
    image Cloud Run deploys and hitting the GeoServer from inside it: a plain
    ``ssl.create_default_context()`` — no protocol pinning at all — fails with
    `SSLV3_ALERT_HANDSHAKE_FAILURE`. Debian's OpenSSL 3.x ships
    ``CipherString = DEFAULT@SECLEVEL=2`` as the system default, which refuses
    a server offering weak-by-2026-standards but not actually broken DH/RSA
    parameters — exactly what a Java/Tomcat-era government GeoServer offers.
    ``set_ciphers("DEFAULT@SECLEVEL=1")`` is the standard, narrowly-scoped fix
    for this — it does not disable certificate verification or widen anything
    else, it only tolerates the specific legacy key sizes SECLEVEL=2 rejects.
    Verified fixed in the same container: HTTP 200 with a valid GeoJSON body.

    The TLS 1.2 pin is kept from the first attempt — harmless, and the
    GeoServer's own behaviour suggests an older stack that is unlikely to
    prefer 1.3 anyway — but on its own it changed nothing, which is why the
    error persisted in production after that fix shipped.
    """

    def __init__(self, verify_tls: bool) -> None:
        self._verify_tls = verify_tls
        super().__init__()

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.maximum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers("DEFAULT@SECLEVEL=1")
        if not self._verify_tls:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        pool_kwargs["ssl_context"] = context
        return super().init_poolmanager(
            connections, maxsize, block=block, **pool_kwargs
        )


class SicarError(RuntimeError):
    """A failure talking to the CAR GeoServer.

    Deliberately distinct from every other error in the app: the UI shows a
    cadastral failure differently from an Earth Engine failure, because the two
    halves fail independently (doc/08-ui-ux.md §6).
    """


def get_session() -> requests.Session:
    """A configured session, created once.

    ``SICAR_VERIFY_TLS`` exists because geoserver.car.gov.br has served an
    incomplete certificate chain to some clients. The decision to relax
    verification, if it is ever made, is made **here, once, visibly** — not with
    ``verify=False`` sprinkled through call sites where it stops being noticed.
    Default stays ``True``.
    """
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                s = requests.Session()
                s.headers.update({
                    "User-Agent": SICAR_USER_AGENT,
                    "Accept": "application/json, application/xml;q=0.8",
                })
                s.verify = SICAR_VERIFY_TLS
                adapter = _Tls12Adapter(SICAR_VERIFY_TLS)
                s.mount("http://", adapter)
                s.mount("https://", adapter)
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

    ``ttl=None`` means the process lifetime — used for ``cod_imovel`` lookups,
    since a property's boundary does not change during a session. Municipality
    pages get a real TTL.
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
class Imovel:
    """One CAR registration, as published.

    Attributes are carried **verbatim** from the service (constraint C4).
    ``area_declarada_ha`` is named for what it is: the number the landholder
    declared, not the area of ``geometry``. The geometric area is computed
    elsewhere (services/zones.py) and shown alongside it, never instead of it
    (decision D6).
    """

    cod_imovel: str
    uf: str
    municipio: str
    cod_municipio_ibge: int
    area_declarada_ha: float
    m_fiscal: float
    tipo_imovel: str
    status_imovel: str
    condicao: Optional[str]
    dat_criacao: Optional[str]
    data_atualizacao: Optional[str]
    geometry: Optional[dict] = field(default=None, repr=False)
    queried_at: str = ""

    @property
    def ano_criacao(self) -> Optional[int]:
        """Registration year — the axis that splits every time series.

        See doc/01-premises.md §1: this is the one date that is specific to the
        object of analysis rather than to the datasets.
        """
        if not self.dat_criacao:
            return None
        try:
            return int(self.dat_criacao[:4])
        except (ValueError, TypeError):
            return None

    @classmethod
    def from_feature(cls, feat: dict, queried_at: str) -> "Imovel":
        p = feat.get("properties") or {}
        return cls(
            cod_imovel=p.get("cod_imovel", ""),
            uf=p.get("uf", ""),
            municipio=p.get("municipio", ""),
            cod_municipio_ibge=int(p.get("cod_municipio_ibge") or 0),
            area_declarada_ha=float(p.get("area") or 0.0),
            m_fiscal=float(p.get("m_fiscal") or 0.0),
            tipo_imovel=p.get("tipo_imovel", ""),
            status_imovel=p.get("status_imovel", ""),
            condicao=p.get("condicao"),
            dat_criacao=p.get("dat_criacao"),
            data_atualizacao=p.get("data_atualizacao"),
            geometry=feat.get("geometry"),
            queried_at=queried_at,
        )


# --------------------------------------------------------------------------- #
# Transport
# --------------------------------------------------------------------------- #
def _get(params: Dict[str, Any], *, base: str = SICAR_BASE) -> requests.Response:
    """One serialised, timed, identified GET.

    Retries once on a transport error, then gives up: a public service that is
    down should produce an error naming it, not a retry loop (doc/05 §6).
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
                logger.warning("SICAR request failed (attempt %d): %s", attempt, exc)
                time.sleep(1.5 * attempt)
                continue
        logger.info("SICAR %s → %d in %.2fs",
                    params.get("request"), r.status_code, elapsed)
        if r.status_code >= 500 and attempt == 1:
            last = SicarError(f"HTTP {r.status_code}")
            time.sleep(1.5)
            continue
        if r.status_code != 200:
            raise SicarError(
                f"O GeoServer do CAR respondeu HTTP {r.status_code}."
            )
        return r
    raise SicarError(
        f"Não foi possível contatar o GeoServer do CAR ({SICAR_BASE}): {last}"
    )


def _get_json(params: Dict[str, Any]) -> dict:
    r = _get(params)
    try:
        return r.json()
    except ValueError as exc:
        # An OWS ExceptionReport comes back as XML with HTTP 200. Surfacing the
        # first 200 characters beats "Expecting value: line 1 column 1".
        snippet = r.text[:200].replace("\n", " ")
        raise SicarError(
            f"Resposta inesperada do GeoServer do CAR: {snippet}"
        ) from exc


def _wfs(**overrides: Any) -> Dict[str, Any]:
    base = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "outputFormat": "application/json",
        "srsName": vocab.REQUEST_CRS,   # server-side reprojection, always (§7.2)
    }
    base.update(overrides)
    return base


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _quote(value: str) -> str:
    """CQL string literal — single quotes doubled."""
    return "'" + str(value).replace("'", "''") + "'"


# --------------------------------------------------------------------------- #
# 1. Property by code  (doc/05 §5.1)
# --------------------------------------------------------------------------- #
def by_code(cod_imovel: str) -> Imovel:
    """Fetch one registration by its CAR code.

    The code is validated **locally** first, so a malformed paste fails
    instantly and no request reaches the service. The UF prefix picks the layer;
    there is no national layer to fall back on.
    """
    code = vocab.normalise_cod_imovel(cod_imovel)      # raises on a bad shape
    uf, _ibge, _digest = vocab.parse_cod_imovel(code)

    def produce() -> Imovel:
        data = _get_json(_wfs(
            typeName=vocab.layer_for_uf(uf),
            cql_filter=f"cod_imovel={_quote(code)}",
        ))
        feats = data.get("features") or []
        if not feats:
            raise SicarError(
                f"Nenhum imóvel encontrado para o código {code}. "
                "O CAR pode ter sido cancelado ou o código não existe."
            )
        return Imovel.from_feature(feats[0], _now())

    # No TTL: a boundary does not change during a session.
    return _cached(f"code:{code}", None, produce)


# --------------------------------------------------------------------------- #
# 2. Properties at a point  (doc/05 §5.2)
# --------------------------------------------------------------------------- #
def at_point(lat: float, lon: float, uf: str, *, limit: int = 25) -> List[Imovel]:
    """Every registration whose polygon contains this point.

    Returns a **list**, and callers must handle more than one: overlapping
    registrations are the normal state of a self-declared cadastre, not an edge
    case (decision D7). The first random point probed during design was covered
    by two. Sorted largest-first, which is the order the chooser presents.

    ``uf`` comes from the local boundary file (decision D5) — this function does
    not guess, because guessing wrong means an empty result that looks like
    "no property here".
    """
    layer = vocab.layer_for_uf(uf)
    # CQL POINT is (lon lat).
    cql = f"INTERSECTS({vocab.GEOM_COLUMN}, POINT({lon:.7f} {lat:.7f}))"

    def produce() -> List[Imovel]:
        data = _get_json(_wfs(
            typeName=layer,
            maxFeatures=limit,
            cql_filter=cql,
        ))
        now = _now()
        found = [Imovel.from_feature(f, now) for f in data.get("features") or []]
        found.sort(key=lambda i: i.area_declarada_ha, reverse=True)
        return found

    return _cached(f"pt:{uf}:{lat:.6f}:{lon:.6f}:{limit}", SICAR_CACHE_TTL_S, produce)


# --------------------------------------------------------------------------- #
# 3. Overlapping neighbours  (doc/03-roadmap.md, Phase 2)
# --------------------------------------------------------------------------- #
def overlapping(imovel: Imovel, *, limit: int = 50) -> List[Imovel]:
    """Other registrations that intersect this one.

    Surfaced, never dissolved (C4/D7). Geometry is requested so the overlapping
    area can be computed locally; the property itself is filtered out by code.
    """
    if not imovel.geometry:
        return []
    from shapely.geometry import shape           # local: keeps import cost off startup

    wkt = shape(imovel.geometry).wkt

    def produce() -> List[Imovel]:
        data = _get_json(_wfs(
            typeName=vocab.layer_for_uf(imovel.uf),
            maxFeatures=limit,
            cql_filter=f"INTERSECTS({vocab.GEOM_COLUMN}, {wkt})",
        ))
        now = _now()
        return [
            Imovel.from_feature(f, now)
            for f in data.get("features") or []
            if (f.get("properties") or {}).get("cod_imovel") != imovel.cod_imovel
        ]

    return _cached(f"ovl:{imovel.cod_imovel}:{limit}", SICAR_CACHE_TTL_S, produce)


# --------------------------------------------------------------------------- #
# 4. Municipality browser  (doc/05 §5.4)
# --------------------------------------------------------------------------- #
def count_in_municipio(uf: str, cod_municipio_ibge: int) -> int:
    """How many registrations, without fetching any.

    ``resultType=hits`` returns a header-only XML document — this is what makes
    the "1 388 imóveis" line free.
    """
    def produce() -> int:
        r = _get({
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": vocab.layer_for_uf(uf),
            "resultType": "hits",
            "cql_filter": f"cod_municipio_ibge={int(cod_municipio_ibge)}",
        })
        import re
        m = re.search(r'numberMatched="(\d+)"', r.text)
        if not m:
            raise SicarError("O GeoServer do CAR não informou a contagem.")
        return int(m.group(1))

    return _cached(f"cnt:{uf}:{cod_municipio_ibge}", SICAR_CACHE_TTL_S, produce)


def list_in_municipio(
    uf: str,
    cod_municipio_ibge: int,
    *,
    page: int = 0,
    page_size: int = 50,
    sort: str = "area D",
) -> List[Imovel]:
    """One page of a municipality's registrations, **without geometry**.

    ``propertyName`` excluding the geometry column is the difference between a
    page costing kilobytes and costing megabytes (doc/05 §5.4). The geometry
    arrives only when a row is chosen, through :func:`by_code`.
    """
    def produce() -> List[Imovel]:
        data = _get_json({
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": vocab.layer_for_uf(uf),
            "outputFormat": "application/json",
            "srsName": vocab.REQUEST_CRS,
            "count": int(page_size),
            "startIndex": int(page) * int(page_size),
            "sortBy": sort,
            "propertyName": ",".join(vocab.LIST_ATTRIBUTES),
            "cql_filter": f"cod_municipio_ibge={int(cod_municipio_ibge)}",
        })
        now = _now()
        return [Imovel.from_feature(f, now) for f in data.get("features") or []]

    key = f"lst:{uf}:{cod_municipio_ibge}:{page}:{page_size}:{sort}"
    return _cached(key, SICAR_CACHE_TTL_S, produce)


# --------------------------------------------------------------------------- #
# 5. The WMS context layer  (doc/05 §5.5)
# --------------------------------------------------------------------------- #
def wms_layer_spec(uf: str, *, opacity: float = 0.6) -> Dict[str, Any]:
    """Leaflet ``L.tileLayer.wms`` options for one UF's registrations.

    Drawing 218 000 polygons is the server's problem, not ours — this is why
    the context layer is WMS and not WFS.
    """
    return {
        "url": SICAR_WMS,
        "layers": vocab.layer_for_uf(uf),
        "format": "image/png",
        "transparent": True,
        "version": "1.1.1",
        "opacity": opacity,
        "attribution": "CAR/SICAR — Serviço Florestal Brasileiro",
    }


__all__ = [
    "Imovel", "SicarError",
    "by_code", "at_point", "overlapping",
    "count_in_municipio", "list_in_municipio",
    "wms_layer_spec", "clear_cache", "get_session",
]
