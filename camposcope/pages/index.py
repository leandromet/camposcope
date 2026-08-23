"""The map + analysis workspace. v1 is one page (doc/08-ui-ux.md §1)."""

from __future__ import annotations

import reflex as rx

from ..components.cadastro import cadastral_card, zones_panel
from ..components.layout import BORDER, MUTED, header, section
from ..components.map.leaflet_map import leaflet_map
from ..components.search import search_panel
from ..config.datasets import BASEMAPS
from ..state import AppState


def _layers_panel() -> rx.Component:
    return section(
        "Camadas",
        rx.select(
            list(BASEMAPS.keys()),
            value=AppState.basemap,
            on_change=AppState.set_basemap,
            size="1",
            width="100%",
        ),
        rx.hstack(
            rx.switch(checked=AppState.show_car_layer,
                      on_change=AppState.toggle_car_layer, size="1"),
            rx.text("Imóveis do CAR (WMS)", size="1"),
            spacing="2", align="center",
        ),
        rx.text("Aparece a partir do zoom 8.", size="1", color=MUTED),
    )


def _sidebar() -> rx.Component:
    return rx.vstack(
        search_panel(),
        cadastral_card(),
        zones_panel(),
        _layers_panel(),
        width="340px",
        min_width="340px",
        height="100%",
        overflow_y="auto",
        padding_x="4",
        border_right=BORDER,
        background="var(--color-panel)",
        align_items="stretch",
        spacing="0",
    )


def _map() -> rx.Component:
    return rx.box(
        leaflet_map(
            id="camposcope-map",
            center=AppState.center,
            zoom=AppState.zoom,
            layers=AppState.map_layers,
            overlays=AppState.map_overlays,
            fit_bounds=AppState.fit_bounds,
            on_map_click=AppState.select_at_point,
            width="100%",
            height="100%",
        ),
        flex="1",
        height="100%",
        position="relative",
    )


def index() -> rx.Component:
    return rx.vstack(
        header(),
        rx.hstack(
            _sidebar(),
            _map(),
            width="100%",
            flex="1",
            spacing="0",
            overflow="hidden",
        ),
        width="100vw",
        height="100vh",
        spacing="0",
        overflow="hidden",
    )
