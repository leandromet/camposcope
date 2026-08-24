"""Camposcope — land-cover history and landscape context for a CAR property.

App entry point. See doc/ for premises, architecture and roadmap.
"""

from __future__ import annotations

import logging

import reflex as rx

from .api import register as register_api
from .components.layout import ACCENT
from .config.settings import GA_MEASUREMENT_ID
from .pages.index import index
from .state import AppState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def _ga_head_components() -> list[rx.Component]:
    """GA4 tag, only when CS_GA_MEASUREMENT_ID is set (empty in local dev)."""
    if not GA_MEASUREMENT_ID:
        return []
    return [
        rx.script(src=f"https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}", async_=True),
        rx.script(f"""
            window.dataLayer = window.dataLayer || [];
            function gtag(){{ dataLayer.push(arguments); }}
            gtag('js', new Date());
            gtag('config', '{GA_MEASUREMENT_ID}');
        """),
    ]


app = rx.App(
    theme=rx.theme(appearance="light", accent_color=ACCENT, radius="medium"),
    style={"fontFamily": "Inter, system-ui, sans-serif"},
    head_components=[
        # Without this, mobile browsers lay the page out at ~980px and zoom out
        # to fit — every responsive breakpoint would evaluate as "desktop" and
        # the mobile layout would never appear. Inherited from Naturametrics
        # along with the reason.
        rx.el.meta(
            name="viewport",
            content="width=device-width, initial-scale=1, viewport-fit=cover",
        ),
        rx.el.meta(name="theme-color", content="#ffffff"),
        *_ga_head_components(),
    ],
)

app.add_page(
    index,
    route="/",
    title="Camposcope — Análise de imóveis rurais do CAR",
    description=(
        "História de uso da terra e contexto de paisagem de um imóvel rural "
        "registrado no CAR, a partir do SICAR, MapBiomas e Earth Engine."
    ),
    on_load=AppState.on_load,
)

# The biome polygons are fetched by the browser over HTTP, not pushed through
# the WebSocket — see camposcope/api/__init__.py for why.
register_api(app)
