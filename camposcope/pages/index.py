"""The map + analysis workspace. v1 is one page (doc/08-ui-ux.md §1)."""

from __future__ import annotations

import reflex as rx

from ..components.cadastro import cadastral_card, zones_panel
from ..components.layout import BORDER, MUTED, header, section
from ..components.map.leaflet_map import leaflet_map
from ..components.results import results_panel
from ..components.search import municipio_browser, search_panel
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
        rx.hstack(
            rx.switch(checked=AppState.show_biomes,
                      on_change=AppState.toggle_biomes, size="1"),
            rx.text("Biomas e domínios (IBGE)", size="1"),
            spacing="2", align="center",
        ),
        rx.text(
            "Limites aproximados (~1 km) — orientação, não decide o bioma de "
            "um imóvel específico.",
            size="1", color=MUTED,
        ),
    )


def _sidebar() -> rx.Component:
    return rx.vstack(
        search_panel(),
        cadastral_card(),
        municipio_browser(),
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
    """The map, filling its box, with the results drawer overlaid on top of it
    rather than sharing flex space with it (doc/08-ui-ux.md §1: the drawer
    "rises from the bottom" of the map area, it does not shrink it). Kept as a
    single box with exactly the props Leaflet has always been given here —
    ``flex="1", height="100%", position="relative"`` — so the map's own layout
    is never at the mercy of a sibling's height.
    """
    return rx.box(
        leaflet_map(
            id="camposcope-map",
            center=AppState.center,
            zoom=AppState.zoom,
            layers=AppState.map_layers,
            overlays=AppState.map_overlays,
            vectors=AppState.biome_vectors,
            fit_bounds=AppState.fit_bounds,
            on_map_click=AppState.select_at_point,
            width="100%",
            height="100%",
        ),
        rx.box(
            results_panel(),
            position="absolute",
            bottom="0",
            left="0",
            right="0",
            max_height="42vh",
            overflow_y="auto",
            # Leaflet's own panes (tile/overlay/marker/popup) use z-index up to
            # ~700 internally; anything lower than that sits UNDER the map and
            # is invisible except for whatever sliver Leaflet doesn't paint —
            # exactly the bug this value fixes.
            z_index="1000",
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
