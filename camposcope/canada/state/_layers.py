"""Map layers: basemaps (XYZ and Landsat), the parcel WMS context layer, the
ecozone overlay, and the per-tab analysis layer.

Trimmed from the Brazil page's ``state/_layers.py`` the same way Naturametrics'
Canada page trims its own — the mint-per-tab dispatch table is the one piece of
real logic; everything else is direct substitution.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

import reflex as rx

from ...state._proxy import plain
from ..config import datasets as ds
from ..config.datasets import ALL_BASEMAPS
from ..config.settings import (
    BC_VIEW_BOUNDS, DEFAULT_BASEMAP as _DEFAULT_BASEMAP, DEFAULT_CENTER,
    DEFAULT_ZOOM,
)
# Hoisted to module level, unlike the imports inside the background event
# methods below: Reflex's static dependency scanner for a plain (non-cached)
# @rx.var walks the function body looking for imports to resolve, and a
# function-local relative import here made it emit a spurious "No module
# named 'services'" warning at class-definition time. Harmless either way —
# map_layers is not cached, so nothing depends on the scan succeeding — but
# hoisting the one import map_layers itself needs is what makes the warning
# go away rather than living with it.
from ..services import gbif as gbif_service
from ..services.pmbc import wms_layer_spec
from ..translations import get_translations

logger = logging.getLogger(__name__)


class CanadaLayersMixin(rx.State, mixin=True):
    """What is drawn on the map, and where the map is looking."""

    basemap: str = _DEFAULT_BASEMAP
    center: List[float] = list(DEFAULT_CENTER)
    zoom: int = DEFAULT_ZOOM

    #: Landsat basemap tile URLs, minted per (rendering, year). Cached for the
    #: process lifetime like every other tile URL.
    landsat_urls: Dict[str, str] = {}
    landsat_year: int = 2022
    basemap_busy: bool = False
    basemap_error: str = ""

    #: The parcel fabric drawn as a WMS overlay — how a couple of million
    #: parcels get on screen without any of them travelling to the browser as
    #: vectors.
    show_parcel_layer: bool = True
    parcel_layer_opacity: float = 0.35
    parcel_layer_min_zoom: int = 12

    fit_bounds: List[List[float]] = list(BC_VIEW_BOUNDS)

    #: The ecological-framework overlay — navigation, not an input. Off by
    #: default. ``ecozone_level`` picks which of the framework's three tiers
    #: draws: "ecozone" (coarsest, the default), "ecoregion", or
    #: "ecodistrict" (finest — no name of its own, see
    #: ``canada/services/ecozones.py``). Switching level while the overlay is
    #: on just re-requests a different static GeoJSON; it never touches
    #: analysis.
    show_ecozones: bool = False
    ecozone_level: str = "ecozone"
    show_ecozone_labels: bool = True
    ecozone_opacity: float = 0.45

    analysis_layer_enabled: bool = True
    analysis_layer_specs: Dict[str, Dict[str, Any]] = {}
    active_analysis_layer_key: str = ""
    #: Validação is the one tab with two layers at once — ACI left,
    #: VLCE2 right, split by the same swipe divider the Brazil Transições tab
    #: uses.
    swipe_layer_keys: List[str] = []
    analysis_layer_busy: bool = False
    analysis_layer_error: str = ""

    @rx.var
    def map_swipe_enabled(self) -> bool:
        return len(self.swipe_layer_keys) == 2

    def toggle_analysis_layer(self) -> None:
        """Flip the on-map analysis layer on/off.

        While off, `mint_analysis_layer` skips minting entirely (cost
        control) — which means `active_analysis_layer_key` can go stale if
        the results tab changes while the layer is hidden. Re-running the
        mint on the way back ON is what makes the layer that reappears match
        whatever tab is active NOW, not whichever tab was active when it was
        last turned off.
        """
        self.analysis_layer_enabled = not self.analysis_layer_enabled
        if self.analysis_layer_enabled:
            return self.__class__.mint_analysis_layer

    def toggle_parcel_layer(self, checked: bool) -> None:
        self.show_parcel_layer = checked

    def toggle_ecozones(self, checked: bool) -> None:
        self.show_ecozones = checked

    def set_ecozone_level(self, level: str | list[str]) -> None:
        value = level[0] if isinstance(level, list) else level
        from ..config.ecozones import LEVELS
        self.ecozone_level = value if value in LEVELS else "ecozone"

    def frame_geometry(self, geojson: Dict[str, Any]) -> None:
        """Fit the map to a geometry's bounds — the one sanctioned viewport
        move, fired only when a new parcel is selected."""
        from shapely.geometry import shape

        if not geojson:
            return
        try:
            minx, miny, maxx, maxy = shape(geojson).bounds
        except Exception:                       # noqa: BLE001
            return
        new_bounds = [[miny, minx], [maxy, maxx]]
        if new_bounds != self.fit_bounds:
            self.fit_bounds = new_bounds

    @rx.event(background=True)
    async def mint_analysis_layer(self):
        async with self:
            tab = getattr(self, "results_tab", "cobertura")
            has_parcel = getattr(self, "has_parcel", False)
            enabled = self.analysis_layer_enabled
            year_aci = getattr(self, "aci_layer_year", None)
            hansen_split = getattr(self, "hansen_layer_split", "start_date")
            year_biomass = getattr(self, "biomass_layer_year", None)
            year_landscape = getattr(self, "landscape_year", None)
            year_validation = getattr(self, "validation_year", None)
            sankey_year_a = getattr(self, "sankey_year_a", None)
            sankey_year_b = getattr(self, "sankey_year_b", None)
            fire_source = getattr(self, "fire_source", "modis")
            zones_geojson = plain(getattr(self, "zones_geojson", {})) or {}
            identifier = getattr(self, "parcel", {}).get("identifier", "")
            start_year = getattr(self, "parcel", {}).get("start_year") or None

        #: Transições and Validação are the two tabs with TWO layers at once
        #: instead of one — mirrors the Brazil page's own split.
        swipe_tabs = ("transicoes", "validacao")
        if tab not in swipe_tabs:
            async with self:
                self.swipe_layer_keys = []

        if tab == "transicoes":
            if has_parcel and enabled:
                await self._mint_transitions_layers(sankey_year_a, sankey_year_b)
            return

        if tab == "validacao":
            if has_parcel and enabled and year_validation:
                await self._mint_validation_layers(year_validation)
            return

        if not has_parcel or not enabled:
            return

        from ..services import layers as layer_service

        cache_key: Optional[str] = None
        mint_fn: Optional[Callable[[], Optional[Dict[str, Any]]]] = None

        if tab == "cobertura" and year_aci:
            cache_key = f"ca:aci:{year_aci}"
            mint_fn = lambda: layer_service.aci_year_spec(year_aci)

        elif tab == "floresta":
            from ...config.settings import HANSEN_TREECOVER_THRESHOLD

            from_year = start_year if hansen_split == "start_date" and start_year \
                else 2001
            cache_key = f"ca:hansen_change:{from_year}:{HANSEN_TREECOVER_THRESHOLD}"
            mint_fn = lambda: layer_service.hansen_change_spec(from_year)

        elif tab == "biomassa" and year_biomass:
            cache_key = f"ca:biomass:{year_biomass}"
            mint_fn = lambda: layer_service.biomass_year_spec(year_biomass)

        elif tab == "fogo":
            if fire_source == "aci":
                cache_key = "ca:aci_burn_frequency"
                mint_fn = layer_service.aci_burn_frequency_spec
            else:
                cache_key = "ca:fire_frequency"
                mint_fn = layer_service.fire_frequency_spec

        elif tab == "paisagem" and year_landscape:
            features = zones_geojson.get("features") or []
            outer_geom = None
            if features:
                from shapely.geometry import mapping, shape
                from shapely.ops import unary_union

                outer_geom = mapping(unary_union(
                    [shape(f["geometry"]) for f in features]))
            if outer_geom is None:
                return
            cache_key = f"ca:landscape_patches:{year_landscape}:{identifier}"
            mint_fn = lambda: layer_service.landscape_patches_spec(
                year_landscape, outer_geom, identifier)

        elif tab == "gbif":
            # See the Brazil page's own mint_analysis_layer for why this has
            # to clear the key rather than fall through to "else: return" —
            # otherwise whichever raster the previous tab minted stays on
            # screen underneath the GBIF dots.
            async with self:
                self.active_analysis_layer_key = ""
            return

        else:
            return

        async with self:
            if cache_key in self.analysis_layer_specs:
                self.active_analysis_layer_key = cache_key
                return
            self.analysis_layer_busy = True
            self.analysis_layer_error = ""

        loop = asyncio.get_running_loop()
        try:
            spec = await loop.run_in_executor(None, mint_fn)
        except Exception as exc:                       # noqa: BLE001
            logger.warning("Analysis layer %s failed: %s", cache_key, exc)
            spec = None

        async with self:
            self.analysis_layer_busy = False
            if spec:
                self.analysis_layer_specs[cache_key] = spec
                self.active_analysis_layer_key = cache_key
            else:
                self.analysis_layer_error = get_translations(
                    getattr(self, "language", "en"))["erro_camada_aba"]

    async def _mint_transitions_layers(self, year_a: Optional[int],
                                        year_b: Optional[int]) -> None:
        """The Transições tab's map layer: the two selected Sankey years,
        older on the left of the swipe divider and newer on the right — the
        same ``sankey_year_a``/``sankey_year_b`` the diagram itself uses, so
        there is exactly one place to pick "which two years", not a second
        pair of controls that could disagree with the first. Mirrors the
        Brazil page's own ``_mint_swipe_layers``.

        Reuses the same cache Cobertura's own ACI layer uses (``ca:aci:
        {year}``) — a year already viewed there costs nothing here.

        ``year_a``/``year_b`` start at 0/0 (the Sankey has not run yet) —
        unlike Validação's ``validation_year``, which has a real default and
        so mints on the very first tab visit. Falling back to the same pair
        the Sankey itself opens on (``default_year_pair``) is what makes
        Transições behave the same way Validação already does: a sensible
        comparison on screen immediately, not a stale layer left over from
        whichever tab was active before, nor a blank map until "Calculate"
        is pressed.
        """
        if not year_a or not year_b:
            from ..services.transitions import default_year_pair
            year_a, year_b = default_year_pair()
        left_year, right_year = sorted((int(year_a), int(year_b)))
        left_key = f"ca:aci:{left_year}"
        right_key = f"ca:aci:{right_year}"

        async with self:
            cached = self.analysis_layer_specs
            if left_key in cached and right_key in cached:
                self.swipe_layer_keys = [left_key, right_key]
                return
            self.analysis_layer_busy = True
            self.analysis_layer_error = ""

        from ..services import layers as layer_service

        loop = asyncio.get_running_loop()
        try:
            spec_left, spec_right = await asyncio.gather(
                loop.run_in_executor(None, layer_service.aci_year_spec, left_year),
                loop.run_in_executor(None, layer_service.aci_year_spec, right_year),
            )
        except Exception as exc:                       # noqa: BLE001
            logger.warning("Transitions layers %s/%s failed: %s",
                           left_year, right_year, exc)
            spec_left = spec_right = None

        async with self:
            self.analysis_layer_busy = False
            if spec_left and spec_right:
                # No `clip` baked in here either — see `map_layers` and the
                # matching comment on Validação's own mint for why: this
                # cache is shared with Cobertura, and which side a tile sits
                # on is a property of the current pairing, not of the tile.
                self.analysis_layer_specs[left_key] = spec_left
                self.analysis_layer_specs[right_key] = spec_right
                self.swipe_layer_keys = [left_key, right_key]
            else:
                self.analysis_layer_error = get_translations(
                    getattr(self, "language", "en"))["erro_camada_aba"]

    async def _mint_validation_layers(self, year: int) -> None:
        from ..services import layers as layer_service

        left_key = f"ca:aci:{year}"
        right_key = f"ca:vlce2:{year}"

        async with self:
            cached = self.analysis_layer_specs
            if left_key in cached and right_key in cached:
                self.swipe_layer_keys = [left_key, right_key]
                return
            self.analysis_layer_busy = True
            self.analysis_layer_error = ""

        loop = asyncio.get_running_loop()
        try:
            spec_left, spec_right = await asyncio.gather(
                loop.run_in_executor(None, layer_service.aci_year_spec, year),
                loop.run_in_executor(None, layer_service.vlce2_year_spec, year),
            )
        except Exception as exc:                       # noqa: BLE001
            logger.warning("Validation layers %s failed: %s", year, exc)
            async with self:
                self.analysis_layer_busy = False
                self.analysis_layer_error = get_translations(
                    getattr(self, "language", "en"))["erro_camada_aba"]
            return

        async with self:
            self.analysis_layer_busy = False
            if spec_left:
                self.analysis_layer_specs[left_key] = spec_left
            if spec_right:
                self.analysis_layer_specs[right_key] = spec_right
            if spec_left and spec_right:
                self.swipe_layer_keys = [left_key, right_key]

    @rx.event(background=True)
    async def set_basemap(self, name: str):
        """Switch basemap. Plain XYZ is instant; a Landsat rendering mints a
        tile URL first, off the event loop, and fails closed — the same
        contract the Brazil page's ``set_basemap`` applies to the SPOT
        basemap, ported here as one handler rather than the switch-plus-picker
        pair an earlier draft of this file used, which could disagree about
        which basemap was actually showing.
        """
        if name not in ALL_BASEMAPS:
            return

        async with self:
            self.basemap_error = ""
            if name not in ds.LANDSAT_RENDERINGS:
                self.basemap = name
                return
            year = self.landsat_year
            cache_key = f"{name}:{year}"
            if cache_key in self.landsat_urls:
                self.basemap = name
                return
            self.basemap_busy = True

        from ..services import layers as layer_service

        loop = asyncio.get_running_loop()
        try:
            spec = await loop.run_in_executor(
                None, layer_service.landsat_basemap_spec, name, year)
        except Exception as exc:                       # noqa: BLE001
            logger.warning("Landsat basemap failed: %s", exc)
            spec = None

        async with self:
            self.basemap_busy = False
            if spec is None:
                self.basemap_error = get_translations(
                    getattr(self, "language", "en"))["legend_landsat_error"]
                return
            self.landsat_urls[cache_key] = spec["url"]
            self.basemap = name

    @rx.event(background=True)
    async def set_landsat_year(self, year: str):
        async with self:
            self.landsat_year = int(year)
            current = self.basemap
        if current in ds.LANDSAT_RENDERINGS:
            return self.__class__.set_basemap(current)

    def toggle_landsat_basemap(self, checked: bool) -> "list | None":
        """The legend's on/off switch: hop to the default Landsat rendering,
        or back to the plain XYZ default. A thin wrapper over
        :meth:`set_basemap` so the switch and the sidebar's basemap dropdown
        can never disagree about how a Landsat basemap gets shown."""
        if checked:
            return self.__class__.set_basemap("landsat_true")
        self.basemap = _DEFAULT_BASEMAP
        self.basemap_error = ""

    @rx.var
    def map_layers(self) -> List[Dict[str, Any]]:
        layers: List[Dict[str, Any]] = []
        conf = ALL_BASEMAPS.get(self.basemap)
        if self.basemap.startswith("landsat"):
            url = self.landsat_urls.get(f"{self.basemap}:{self.landsat_year}")
            if url:
                layers.append({
                    "id": f"basemap:{self.basemap}:{self.landsat_year}",
                    "url": url, "opacity": 1.0, "z_index": 0,
                    "attribution": (conf or {}).get("label_en", "Landsat"),
                    "max_native_zoom": (conf or {}).get("max_native_zoom", 14),
                })
        elif conf:
            layers.append({
                "id": f"basemap:{self.basemap}", "url": conf["url"],
                "opacity": 1.0, "z_index": 0, "attribution": conf["attribution"],
                "max_native_zoom": conf.get("max_native_zoom", 19),
            })

        if self.analysis_layer_enabled and len(self.swipe_layer_keys) == 2:
            # `clip` is applied HERE, fresh, from each key's POSITION in
            # swipe_layer_keys — never trusted from analysis_layer_specs. The
            # specs cache is shared across every tab that can show a given
            # tile (Cobertura and Validação can both mint "ca:aci:2022"), and
            # which SIDE a tile sits on is context, not a property of the
            # tile itself. Baking "clip" into the cached dict at mint time
            # would be the exact bug the Brazil page's own map_layers
            # documents fixing. z_index must also differ or Leaflet's own
            # pane ordering leaves paint order to insertion order.
            left_key, right_key = self.swipe_layer_keys
            for i, (key, side) in enumerate(
                    ((left_key, "left"), (right_key, "right"))):
                spec = self.analysis_layer_specs.get(key)
                if spec:
                    layers.append({**spec, "id": f"swipe:{key}",
                                   "clip": side, "z_index": 10 + i})
        elif self.analysis_layer_enabled and self.active_analysis_layer_key:
            spec = self.analysis_layer_specs.get(self.active_analysis_layer_key)
            if spec:
                layers.append(spec)

        if self.show_parcel_layer:
            spec = wms_layer_spec(opacity=self.parcel_layer_opacity)
            layers.append({
                "id": "pmbc:fabric", "kind": "wms",
                "url": spec["url"], "layers": spec["layers"],
                "format": spec["format"], "transparent": spec["transparent"],
                "version": spec["version"], "opacity": spec["opacity"],
                "attribution": spec["attribution"],
                "min_zoom": self.parcel_layer_min_zoom, "z_index": 5,
            })

        return layers

    @rx.var(deps=["show_ecozones", "ecozone_level", "show_ecozone_labels",
                 "ecozone_opacity", "language"], auto_deps=False)
    def ecozone_vectors(self) -> List[Dict[str, Any]]:
        """The browser-side ecological-framework vector layer spec, at
        whichever level ``ecozone_level`` currently picks, or nothing when
        toggled off. Involves no Earth Engine or network call from here — the
        fetch happens in the browser against the HTTP route
        (``camposcope/api``), so unlike every tile spec this cannot fail on
        the Python side. Same contract as the Brazil page's ``biome_vectors``.
        """
        if not self.show_ecozones:
            return []
        from ..services import ecozones

        return [ecozones.vector_spec(
            self.ecozone_level,
            opacity=self.ecozone_opacity,
            show_labels=self.show_ecozone_labels,
            lang=getattr(self, "language", "en"),
        )]

    @rx.var(cache=True, deps=["results_tab", "analysis_layer_enabled"],
           auto_deps=False)
    def gbif_vectors(self) -> List[Dict[str, Any]]:
        """The GBIF occurrence point layer — shown only while the GBIF tab is
        active, gated by the same on-map legend switch every other per-tab
        layer uses (`analysis_layer_enabled`). See the Brazil page's own
        `gbif_vectors` for the full contract, including why the explicit
        ``results_tab`` dep is required rather than decorative (it lives on
        the sibling ``CanadaUIMixin`` and is read via ``getattr`` below —
        the same reasoning ``ecozone_vectors`` above already needed for
        ``language``)."""
        tab = getattr(self, "results_tab", "")
        if tab != "gbif" or not self.analysis_layer_enabled:
            return []
        return [gbif_service.vector_spec()]

    @rx.var(cache=True, deps=["show_ecozones", "ecozone_level",
                              "show_ecozone_labels", "ecozone_opacity",
                              "language", "results_tab",
                              "analysis_layer_enabled"], auto_deps=False)
    def map_vectors(self) -> List[Dict[str, Any]]:
        """Every browser-fetched vector layer at once — the ecozone overlay
        (an independent toggle) and the GBIF tab's own layer, combined
        because `leaflet_map` takes a single `vectors` list. Deps are the
        union of `ecozone_vectors`' and `gbif_vectors`' own — a computed var
        built from other computed vars does not inherit their dependency
        lists for free."""
        return self.ecozone_vectors + self.gbif_vectors
