"""Map layers: basemap, the CAR context layer, and (later) Earth Engine tiles.

Trimmed from Naturametrics' ``state/_layers.py`` (decision D2). The Earth Engine
half arrives in Phase 3; what is here now is what Phase 0 needs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

import reflex as rx

from ..config.datasets import BASEMAPS
from ..config.settings import DEFAULT_BASEMAP, DEFAULT_CENTER, DEFAULT_ZOOM
from ..services import sicar


class LayersMixin(rx.State, mixin=True):
    """What is drawn on the map, and where the map is looking."""

    basemap: str = DEFAULT_BASEMAP
    center: List[float] = list(DEFAULT_CENTER)
    zoom: int = DEFAULT_ZOOM

    #: Draw every CAR registration in the current UF as a WMS overlay. This is
    #: how 218 000 polygons get on screen without any of them travelling to the
    #: browser as vectors (doc/05-sicar-geoserver.md §5.5).
    show_car_layer: bool = True
    car_layer_opacity: float = 0.35
    #: Below this the polygons are an unreadable smear and the request is
    #: pointless, so the layer simply does not draw.
    car_layer_min_zoom: int = 8

    #: ``[[south, west], [north, east]]`` — re-applied only when it CHANGES, so
    #: framing a newly found property does not fight constraint C1 (the viewport
    #: never moves on its own for a layer toggle or a year change).
    fit_bounds: List[List[float]] = []

    #: The IBGE biome/domain overlay — navigation, not an input (decision D13,
    #: doc/11-search-and-navigation.md §6). Off by default: it is orientation,
    #: not something every session needs drawn.
    show_biomes: bool = False
    show_biome_labels: bool = True
    biome_opacity: float = 0.45

    @rx.event
    def set_basemap(self, name: str) -> None:
        if name in BASEMAPS:
            self.basemap = name

    @rx.event
    def toggle_car_layer(self) -> None:
        self.show_car_layer = not self.show_car_layer

    @rx.event
    def toggle_biomes(self) -> None:
        self.show_biomes = not self.show_biomes

    @rx.event
    def toggle_biome_labels(self) -> None:
        self.show_biome_labels = not self.show_biome_labels

    @rx.var(deps=["show_biomes", "show_biome_labels", "biome_opacity"],
            auto_deps=False)
    def biome_vectors(self) -> List[Dict[str, Any]]:
        """The browser-side vector layer spec, or nothing when toggled off.

        Involves no Earth Engine call from here — the fetch happens in the
        browser against the HTTP route (camposcope/api), so unlike every tile
        spec this cannot fail on the Python side.
        """
        if not self.show_biomes:
            return []
        from ..services import biomes

        return [biomes.vector_spec(
            opacity=self.biome_opacity,
            show_labels=self.show_biome_labels,
        )]

    @rx.var
    def map_layers(self) -> List[Dict[str, Any]]:
        """The ordered layer spec the Leaflet component diffs against."""
        base = BASEMAPS.get(self.basemap, BASEMAPS[DEFAULT_BASEMAP])
        layers: List[Dict[str, Any]] = [{
            "id": f"basemap:{self.basemap}",
            "url": base["url"],
            "attribution": base["attribution"],
            "max_native_zoom": base.get("max_native_zoom", 19),
            "opacity": 1.0,
            "z_index": 0,
        }]

        uf = getattr(self, "imovel", {}).get("uf") or getattr(self, "search_uf", "")
        if self.show_car_layer and uf:
            spec = sicar.wms_layer_spec(uf, opacity=self.car_layer_opacity)
            layers.append({
                "id": f"car:{uf}",
                "kind": "wms",
                "url": spec["url"],
                "layers": spec["layers"],
                "format": spec["format"],
                "transparent": spec["transparent"],
                "version": spec["version"],
                "opacity": spec["opacity"],
                "attribution": spec["attribution"],
                "min_zoom": self.car_layer_min_zoom,
                "z_index": 10,
            })

        return layers

    def frame_geometry(self, geojson: Dict[str, Any]) -> None:
        """Fit the view to a geometry — the one sanctioned viewport move.

        Called when a *new property is selected*, which is a user gesture asking
        to look somewhere else. Never called from a layer toggle (C1).
        """
        if not geojson:
            return
        from shapely.geometry import shape

        minx, miny, maxx, maxy = shape(geojson).bounds
        self.fit_bounds = [[miny, minx], [maxy, maxx]]
