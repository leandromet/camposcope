"""Camposcope — land-cover history and landscape context for a CAR property.

App entry point. See doc/ for premises, architecture and roadmap.
"""

from __future__ import annotations

import logging

import reflex as rx

from .components.layout import ACCENT
from .pages.index import index
from .state import AppState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

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
