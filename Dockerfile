# Camposcope — Cloud Run image
#
# Reflex's --single-port production mode: one process serves the compiled
# frontend and the backend on $PORT. Cloud Run injects $PORT and only routes to
# one port, so the dev-time split (3020/8021, rxconfig.py) does not apply here.
# The Reflex JS runtime rewrites ws://localhost/_event to wss://<cloud-run-host>/_event
# when the page is served over HTTPS, so the WebSocket follows automatically.
#
# Modelled on naturametrics/Dockerfile — same base, same reasoning, same
# single-port pattern. Deliberately light for the same reasons:
#   * no chromium/kaleido — chart export is client-side, nothing renders headless
#   * no GDAL — shapely and pyproj ship manylinux wheels with GEOS/PROJ bundled;
#     geopandas is not used anywhere, not even in scripts/ (doc/09-dev-environment.md §5)

FROM python:3.12-slim

WORKDIR /app

# ── System dependencies ──────────────────────────────────────────────────────
# Only what Bun's installer needs. Everything else comes from wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── Bun (Reflex's frontend build toolchain) ──────────────────────────────────
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:$PATH"

# ── Python dependencies (own layer, cached ahead of the code copy) ───────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# ── Application code ─────────────────────────────────────────────────────────
# data/municipios.csv, data/uf_boundaries.simplified.geojson,
# data/territorios.csv and the two data/*.geojson.gz territory overlays are
# committed and MUST ship in the image — they are the local tables click→UF
# routing (D5), the município selector (D12) and the terra indígena / unidade
# de conservação search and overlays read at runtime, with no network
# fallback. Only data/cache/ (rebuildable, gitignored) is excluded — see
# .dockerignore.
COPY . .

ENV REFLEX_ENV=prod \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ── Frontend toolchain + build, baked into the image ─────────────────────────
# `reflex init` installs node_modules under .web/. `reflex export --frontend-only`
# then runs the Vite production build at IMAGE BUILD time rather than on first
# request — without it every cold start pays a multi-minute frontend build, which
# Cloud Run's startup probe will not wait for.
RUN reflex init \
    && reflex export --frontend-only --no-zip

# ── Build-time smoke test ────────────────────────────────────────────────────
# Catches import errors and — importantly — Reflex event-handler signature
# mismatches, which otherwise kill the backend worker at runtime and present as
# a grey map with a failed WebSocket (see tests/test_app_builds.py, and the
# StateProxy/`type(self)` bug this repo hit and fixed during development).
RUN python -c "\
from camposcope.camposcope import app; \
from camposcope.pages.index import index; \
index().render(); \
print('App builds OK')"

# Cloud Run sets $PORT; 8080 is its default and a sane local fallback.
ENV PORT=8080
EXPOSE 8080

# --single-port     → frontend and backend share $PORT (required on Cloud Run)
# --backend-host    → 0.0.0.0 so Cloud Run's health checks reach the container
CMD ["sh", "-c", "reflex run --env prod --single-port --backend-port ${PORT:-8080} --backend-host 0.0.0.0 --loglevel info"]
