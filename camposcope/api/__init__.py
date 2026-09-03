"""Backend HTTP routes.

Reflex talks to the browser over a WebSocket, and that is the right channel for
everything the app normally exchanges — events and small state deltas. It is the
wrong channel for a half-megabyte of geometry: a state var is re-serialised into
the session, held in server memory for as long as the session lives, and
re-sent on every reload, none of which a static, identical-for-everyone
FeatureCollection needs.

So the biome polygons are served as an ordinary HTTP GET the browser can cache.
Ported from Naturametrics' ``api/__init__.py``, trimmed to what Camposcope
actually serves this way (no IFN points here).
"""

from __future__ import annotations

import gzip
import logging
from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..canada.config import ecozones as ecozones_cfg
from ..canada.config.settings import CANADA_BBOX
from ..canada.services import ecozones
from ..canada.services import gbif as gbif_ca
from ..config.settings import BRAZIL_BBOX
from ..services import biomes
from ..services import gbif

logger = logging.getLogger(__name__)

#: The asset is static, so the browser may hold it for a day.
_CACHE_CONTROL = "public, max-age=86400"


async def _run_blocking(fn):
    """Earth Engine and the disk cache are both blocking; the event loop is not."""
    import asyncio

    return await asyncio.get_running_loop().run_in_executor(None, fn)


async def biomes_geojson(request: Request) -> Response:
    """The simplified IBGE biome polygons, pre-gzipped.

    ``Content-Encoding: gzip`` is set by hand rather than relying on compression
    middleware: the payload is compressed once, when it is built, and cached that
    way, so re-compressing it per request would be pure waste.

    The first call after a cold start builds it from Earth Engine (~5-10 s), then
    every later call is a memoised ~1 ms. It is triggered by the user switching
    the layer on, and the control shows a spinner meanwhile.
    """
    try:
        payload = await _run_blocking(biomes.geojson_gzipped)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Biome GeoJSON could not be produced")
        return JSONResponse(
            {"error": "biomas indisponíveis", "detail": str(exc)}, status_code=503
        )

    headers = {"Cache-Control": _CACHE_CONTROL}
    # Every browser accepts gzip, but a client that says it does not gets the
    # plain bytes rather than an encoding it never asked for.
    if "gzip" in request.headers.get("accept-encoding", ""):
        headers["Content-Encoding"] = "gzip"
    else:
        payload = await _run_blocking(lambda: gzip.decompress(payload))

    headers["Content-Length"] = str(len(payload))
    return Response(content=payload, media_type="application/geo+json",
                    headers=headers)


async def _ecoframework_geojson(request: Request, level: str) -> Response:
    """Shared body for the three ecological-framework routes below.

    Same shape as :func:`biomes_geojson`, and unlike it involves no Earth
    Engine call at all — the source is the ArcGIS FeatureServer
    (``canada/services/ecozones.py``), so a cold start's first request costs a
    plain HTTP fetch, not an EE round trip. One handler per level rather than
    a single ``/_ecozones.geojson?level=`` route, so each stays a plain,
    cacheable static GET the browser can key on its URL alone.
    """
    try:
        payload = await _run_blocking(lambda: ecozones.geojson_gzipped(level))
    except Exception as exc:  # noqa: BLE001
        logger.exception("%s GeoJSON could not be produced", level)
        return JSONResponse(
            {"error": f"{level} unavailable", "detail": str(exc)}, status_code=503
        )

    headers = {"Cache-Control": _CACHE_CONTROL}
    if "gzip" in request.headers.get("accept-encoding", ""):
        headers["Content-Encoding"] = "gzip"
    else:
        payload = await _run_blocking(lambda: gzip.decompress(payload))

    headers["Content-Length"] = str(len(payload))
    return Response(content=payload, media_type="application/geo+json",
                    headers=headers)


async def ecozones_geojson(request: Request) -> Response:
    return await _ecoframework_geojson(request, "ecozone")


async def ecoregions_geojson(request: Request) -> Response:
    return await _ecoframework_geojson(request, "ecoregion")


async def ecodistricts_geojson(request: Request) -> Response:
    return await _ecoframework_geojson(request, "ecodistrict")


def _float_param(request: Request, name: str) -> Optional[float]:
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


async def gbif_geojson(request: Request) -> Response:
    """GBIF occurrences inside a viewport — the Brazil page's GBIF tab.

    A missing/invalid bbox (the first fetch before the map has ever reported
    its own viewport) falls back to the whole of Brazil rather than the whole
    world — cheaper, and every result would be off-country anyway once
    ``services/gbif.py`` filters on ``country``.
    """
    west = _float_param(request, "west")
    south = _float_param(request, "south")
    east = _float_param(request, "east")
    north = _float_param(request, "north")
    if None in (west, south, east, north):
        west, south, east, north = BRAZIL_BBOX

    try:
        payload = await _run_blocking(
            lambda: gbif.points_in_bbox(west, south, east, north)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("GBIF GeoJSON could not be produced")
        return JSONResponse(
            {"error": "ocorrências GBIF indisponíveis", "detail": str(exc)},
            status_code=503,
        )

    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


async def gbif_ca_geojson(request: Request) -> Response:
    """GBIF occurrences inside a viewport — the Canada page's GBIF tab."""
    west = _float_param(request, "west")
    south = _float_param(request, "south")
    east = _float_param(request, "east")
    north = _float_param(request, "north")
    if None in (west, south, east, north):
        west, south, east, north = CANADA_BBOX

    try:
        payload = await _run_blocking(
            lambda: gbif_ca.points_in_bbox(west, south, east, north)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("GBIF GeoJSON (Canada) could not be produced")
        return JSONResponse(
            {"error": "GBIF occurrences unavailable", "detail": str(exc)},
            status_code=503,
        )

    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


async def healthz(request: Request) -> Response:
    return JSONResponse({"status": "ok"})


def register(app) -> None:
    """Attach the routes to the Reflex app's Starlette instance."""
    api = getattr(app, "_api", None)
    if api is None:
        logger.warning("Reflex app exposes no Starlette instance — routes skipped")
        return
    api.add_route(biomes.GEOJSON_PATH, biomes_geojson, methods=["GET"])
    api.add_route(ecozones_cfg.LEVELS["ecozone"].geojson_path,
                 ecozones_geojson, methods=["GET"])
    api.add_route(ecozones_cfg.LEVELS["ecoregion"].geojson_path,
                 ecoregions_geojson, methods=["GET"])
    api.add_route(ecozones_cfg.LEVELS["ecodistrict"].geojson_path,
                 ecodistricts_geojson, methods=["GET"])
    api.add_route(gbif.GEOJSON_PATH, gbif_geojson, methods=["GET"])
    api.add_route(gbif_ca.GEOJSON_PATH, gbif_ca_geojson, methods=["GET"])
    api.add_route("/healthz", healthz, methods=["GET"])
    logger.info("Registered backend routes %s, %s, %s, %s, %s, %s, /healthz",
                biomes.GEOJSON_PATH,
                ecozones_cfg.LEVELS["ecozone"].geojson_path,
                ecozones_cfg.LEVELS["ecoregion"].geojson_path,
                ecozones_cfg.LEVELS["ecodistrict"].geojson_path,
                gbif.GEOJSON_PATH, gbif_ca.GEOJSON_PATH)
