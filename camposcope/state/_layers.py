"""Map layers: basemaps (XYZ and Earth Engine), the CAR context layer, the
biome overlay.

Trimmed from Naturametrics' ``state/_layers.py`` (decision D2).
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Sequence

import reflex as rx

from ..config.datasets import ALL_BASEMAPS, BASEMAPS, is_ee_basemap
from ..config.settings import DEFAULT_BASEMAP, DEFAULT_CENTER, DEFAULT_ZOOM
from ..services import sicar
from ..translations import get_translations
from ._proxy import plain

logger = logging.getLogger(__name__)


class LayersMixin(rx.State, mixin=True):
    """What is drawn on the map, and where the map is looking."""

    basemap: str = DEFAULT_BASEMAP
    center: List[float] = list(DEFAULT_CENTER)
    zoom: int = DEFAULT_ZOOM

    #: Tile URLs minted from Earth Engine (the SPOT 2008 mosaics — everything
    #: else is a plain XYZ template with no round trip). Cached for the process
    #: lifetime like every other tile URL (services/tiles.py): switching back
    #: and forth costs one round trip in total.
    ee_basemap_urls: Dict[str, str] = {}
    basemap_busy: bool = False
    #: Fail-closed message (doc/12-spot-2008.md §2): a licence-gated basemap
    #: that cannot mint a tile URL reverts to the default rather than showing a
    #: broken layer, and says why.
    basemap_error: str = ""

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

    #: The map layer that matches the active results tab (doc/08-ui-ux.md §1:
    #: "show the map layer related to each tab as we switch them"). Cached by
    #: spec id like every other tile — switching tabs back and forth after the
    #: first visit costs nothing. On by default; the on-map legend control
    #: (components/map_legend.py) is where a user turns it off.
    analysis_layer_enabled: bool = True
    analysis_layer_specs: Dict[str, Dict[str, Any]] = {}
    #: Which cached spec is current. Set by `mint_analysis_layer`; `map_layers`
    #: just looks this key up — it never decides which layer belongs to which
    #: tab itself, so that decision lives in exactly one place.
    active_analysis_layer_key: str = ""
    #: Transições and Validação are the two tabs with TWO layers at once
    #: instead of one — older/newer year for Transições, reference/checked
    #: for Validação — each pair split by the same swipe divider.
    #: ``[left_key, right_key]``, both into `analysis_layer_specs`; empty
    #: whenever the active tab is neither.
    swipe_layer_keys: List[str] = []
    analysis_layer_busy: bool = False
    analysis_layer_error: str = ""

    @rx.var
    def map_swipe_enabled(self) -> bool:
        return len(self.swipe_layer_keys) == 2

    @rx.event
    def toggle_analysis_layer(self) -> None:
        self.analysis_layer_enabled = not self.analysis_layer_enabled

    @rx.event(background=True)
    async def mint_analysis_layer(self):
        """Mint (or reuse) the map layer for the currently active results tab.

        Every mint is independent and the cache never evicts, so revisiting a
        tab is always free after the first visit — the same guarantee the
        SPOT basemap gives. Transições is the one tab with TWO layers instead
        of one — see `_mint_swipe_layers`.
        """
        async with self:
            # `results_tab` (UIMixin) and `has_imovel` (ImovelMixin) live on
            # sibling mixins, invisible to a static checker looking only at
            # LayersMixin — `getattr` with a default sidesteps that the same
            # way every other cross-mixin read in this function already does,
            # for consistency as much as to silence the warning.
            tab = getattr(self, "results_tab", "cobertura")
            has_property = getattr(self, "has_imovel", False)
            enabled = self.analysis_layer_enabled
            year_mb = getattr(self, "mapbiomas_layer_year", None)
            hansen_mode = getattr(self, "hansen_layer_mode", "2008")
            year_biomass = getattr(self, "biomass_layer_year", None)
            year_landscape = getattr(self, "landscape_year", None)
            zones_geojson = plain(getattr(self, "zones_geojson", {})) or {}
            cod_imovel = getattr(self, "imovel", {}).get("cod_imovel", "")
            validacao_mode = getattr(self, "validacao_mode", "spot_2008")
            spot_band_mode = getattr(self, "spot_band_mode", "visual")
            registration_year = getattr(self, "imovel", {}).get("ano_criacao") or None

        #: The two tabs with TWO layers at once, not one.
        swipe_tabs = ("transicoes", "validacao")
        if tab not in swipe_tabs:
            async with self:
                self.swipe_layer_keys = []

        if tab == "transicoes":
            if has_property and enabled:
                await self._mint_swipe_layers()
            return

        if tab == "validacao":
            if has_property and enabled:
                await self._mint_validacao_layers(validacao_mode, spot_band_mode)
            return

        if not has_property or not enabled:
            return

        from ..config.settings import HANSEN_TREECOVER_THRESHOLD
        from ..services import layers as layer_service

        cache_key: Optional[str] = None
        # A lambda ASSIGNED to `mint_fn`, not a nested `def mint_fn():` —
        # the latter declares a second, distinct symbol in the same scope
        # ("mint_fn is obscured by a declaration of the same name" from a
        # static checker), even though it works fine at runtime. An
        # assignment matches the variable's own declared type instead of
        # competing with it.
        mint_fn: Optional[Callable[[], Optional[Dict[str, Any]]]] = None

        if tab == "cobertura" and year_mb:
            cache_key = f"mapbiomas:v10_1:{year_mb}"
            mint_fn = lambda: layer_service.mapbiomas_year_spec(year_mb)

        elif tab == "floresta":
            # registration_year can be falsy (property not yet registered, or
            # not selected) even when hansen_mode == "registro" — 2008 is the
            # honest fallback either way, and it keeps `from_year` a definite
            # int rather than `int | None` going into hansen_change_spec.
            from_year = (
                int(registration_year)
                if hansen_mode == "registro" and registration_year
                else 2008
            )
            cache_key = f"hansen_change:{from_year}:{HANSEN_TREECOVER_THRESHOLD}"
            mint_fn = lambda: layer_service.hansen_change_spec(from_year)

        elif tab == "biomassa" and year_biomass:
            cache_key = f"biomass:{year_biomass}"
            mint_fn = lambda: layer_service.biomass_year_spec(year_biomass)

        elif tab == "fogo":
            cache_key = "fire_frequency"
            mint_fn = layer_service.fire_frequency_spec

        elif tab == "paisagem" and year_landscape:
            features = zones_geojson.get("features") or []
            # services/zones.py builds TRUE rings — each is the annulus
            # between its own radius and the previous one (`grown.difference
            # (previous)`), disjoint from the property and every smaller
            # ring by construction (so areas can be summed without double-
            # counting). That means the outermost feature ALONE is only the
            # outermost band, not "everything out to that radius" — clipping
            # to just it is what left patches showing only in the last ring
            # and nothing inside it. The union of every zone reconstructs
            # the full disc (property + every ring), since together they
            # tile it with no gaps and no overlaps.
            outer_geom = None
            if features:
                from shapely.geometry import mapping, shape
                from shapely.ops import unary_union

                outer_geom = mapping(unary_union(
                    [shape(f["geometry"]) for f in features]))
            if outer_geom is None:
                return
            cache_key = f"landscape_patches:{year_landscape}:{cod_imovel}"
            mint_fn = lambda: layer_service.landscape_patches_spec(
                year_landscape, outer_geom, cod_imovel)

        else:
            return

        async with self:
            if cache_key in self.analysis_layer_specs:
                self.active_analysis_layer_key = cache_key
                return
            self.analysis_layer_busy = True
            self.analysis_layer_error = ""

        import asyncio

        loop = asyncio.get_running_loop()
        try:
            spec = await loop.run_in_executor(None, mint_fn)
        except Exception as exc:                      # noqa: BLE001
            logger.warning("Analysis layer %s failed: %s", cache_key, exc)
            spec = None

        async with self:
            self.analysis_layer_busy = False
            if spec:
                self.analysis_layer_specs[cache_key] = spec
                self.active_analysis_layer_key = cache_key
            else:
                self.analysis_layer_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_camada_aba"]

    async def _mint_swipe_layers(self) -> None:
        """The Transições tab's map layer: the two selected Sankey years,
        older on the left of the swipe divider and newer on the right — the
        same `sankey_year_a`/`sankey_year_b` the two-stage diagram already
        uses, so there is exactly one place a user sets "which two years",
        not a second pair of controls that could disagree with the first.

        Both mints run concurrently (they are independent Earth Engine calls)
        and share the same cache as Cobertura's own MapBiomas layer — picking
        a year already viewed there costs nothing here.
        """
        async with self:
            year_a = getattr(self, "sankey_year_a", None)
            year_b = getattr(self, "sankey_year_b", None)

        if not year_a or not year_b:
            return
        left_year, right_year = sorted((int(year_a), int(year_b)))
        left_key = f"mapbiomas:v10_1:{left_year}"
        right_key = f"mapbiomas:v10_1:{right_year}"

        async with self:
            cached = self.analysis_layer_specs
            if left_key in cached and right_key in cached:
                self.swipe_layer_keys = [left_key, right_key]
                return
            self.analysis_layer_busy = True
            self.analysis_layer_error = ""

        import asyncio

        from ..services import layers as layer_service

        loop = asyncio.get_running_loop()
        try:
            spec_left, spec_right = await asyncio.gather(
                loop.run_in_executor(None, layer_service.mapbiomas_year_spec,
                                     left_year),
                loop.run_in_executor(None, layer_service.mapbiomas_year_spec,
                                     right_year),
            )
        except Exception as exc:                      # noqa: BLE001
            logger.warning("Swipe layers %s/%s failed: %s",
                           left_year, right_year, exc)
            spec_left = spec_right = None

        async with self:
            self.analysis_layer_busy = False
            if spec_left and spec_right:
                # The cached spec carries no `clip` — `map_layers` applies it
                # fresh from each key's position in `swipe_layer_keys` every
                # render. Baking a side into the cache here was the bug: this
                # same cache is shared with Cobertura and Validação, and a
                # tile minted "right" in one pairing must not stay clipped
                # "right" when a different pairing later needs it on the left.
                self.analysis_layer_specs[left_key] = spec_left
                self.analysis_layer_specs[right_key] = spec_right
                self.swipe_layer_keys = [left_key, right_key]
            else:
                self.analysis_layer_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_camadas_comparacao"]

    async def _mint_validacao_layers(self, mode: str, spot_band_mode: str) -> None:
        """The Validação tab's two layers: a classification checked on the
        right against reference data on the left. ``mode`` picks the pairing
        (doc/03-roadmap.md Phase 5 addendum — "like naturametrics"):

        ``spot_2008``  SPOT 2008 imagery ↔ MapBiomas 2008. ``spot_band_mode``
                       ("visual" | "analytic") picks which SPOT mosaic —
                       naturametrics offers both (`mb_spot_visual` /
                       `mb_spot_analytic`) because they answer different
                       questions: true colour reads naturally, the
                       false-colour NIR composite makes vegetation legible
                       against pasture at a glance.
        ``ibge_2022``  IBGE Vegetação 2022 ↔ MapBiomas 2022. No SPOT side, so
                       ``spot_band_mode`` is unused here.

        Reuses whatever the Cobertura tab or the SPOT toggle in Floresta's
        legend already minted — same cache, same keys. The visual/analytic
        switch is exactly why the SPOT key carries the band mode: switching
        it must mint a genuinely different tile, not silently keep showing
        whichever one was cached first.
        """
        spot_key = f"spot_2008_{spot_band_mode}"
        if mode == "spot_2008":
            left_key, right_key = f"basemap:{spot_key}", "mapbiomas:v10_1:2008"
        else:
            left_key, right_key = "ibge_vegetation:leg2", "mapbiomas:v10_1:2022"

        async with self:
            cached = self.analysis_layer_specs
            if left_key in cached and right_key in cached:
                self.swipe_layer_keys = [left_key, right_key]
                return
            self.analysis_layer_busy = True
            self.analysis_layer_error = ""

        import asyncio

        from ..services import layers as layer_service

        loop = asyncio.get_running_loop()
        try:
            if mode == "spot_2008":
                spec_left, spec_right = await asyncio.gather(
                    loop.run_in_executor(None, layer_service.ee_basemap_spec,
                                         spot_key),
                    loop.run_in_executor(None, layer_service.mapbiomas_year_spec,
                                         2008),
                )
            else:
                spec_left, spec_right = await asyncio.gather(
                    loop.run_in_executor(None, layer_service.ibge_vegetation_spec),
                    loop.run_in_executor(None, layer_service.mapbiomas_year_spec,
                                         2022),
                )
        except Exception as exc:                      # noqa: BLE001
            logger.warning("Validação layers (%s) failed: %s", mode, exc)
            spec_left = spec_right = None

        async with self:
            self.analysis_layer_busy = False
            if spec_left and spec_right:
                # No `clip` baked in here either — see `map_layers` and the
                # matching comment in `_mint_swipe_layers` for why: this
                # cache is shared with Transições and Cobertura, and the side
                # a tile sits on is a property of the current pairing, not of
                # the tile.
                self.analysis_layer_specs[left_key] = spec_left
                self.analysis_layer_specs[right_key] = spec_right
                self.swipe_layer_keys = [left_key, right_key]
            else:
                msgs = get_translations(getattr(self, "lang", "pt"))
                self.analysis_layer_error = (
                    msgs["erro_camadas_comparacao_spot"] if mode == "spot_2008"
                    else msgs["erro_camadas_comparacao"]
                )

    @rx.event(background=True)
    async def set_basemap(self, name: str):
        """Switch basemap. XYZ is instant; an Earth Engine basemap (SPOT 2008)
        mints a tile URL first, off the event loop, and fails closed
        (doc/12-spot-2008.md §2) — a licence-gated layer that cannot mint a URL
        must not silently show as broken.
        """
        if name not in ALL_BASEMAPS:
            return

        async with self:
            self.basemap_error = ""
            if not is_ee_basemap(name):
                self.basemap = name
                return
            if name in self.ee_basemap_urls:
                self.basemap = name
                return
            self.basemap_busy = True

        import asyncio

        from ..services import layers as layer_service

        loop = asyncio.get_running_loop()
        try:
            spec = await loop.run_in_executor(
                None, layer_service.ee_basemap_spec, name
            )
        except Exception as exc:                      # noqa: BLE001
            logger.warning("Basemap %s failed: %s", name, exc)
            spec = None

        async with self:
            self.basemap_busy = False
            if spec:
                self.ee_basemap_urls[name] = spec["url"]
                self.basemap = name
            else:
                # Stay on the previous basemap and say why, rather than
                # reverting silently — a silent revert would look like the
                # select control is broken, not like a permission gap.
                self.basemap_error = get_translations(
                    getattr(self, "lang", "pt")
                )["erro_basemap"].format(name=name)

    @rx.event(background=True)
    async def toggle_spot_basemap(self):
        """Switch to the SPOT 2008 mosaic, or back off it.

        SPOT is a *basemap* (real imagery replacing the tile underneath
        everything else), not an overlay like Hansen/MapBiomas/AGB — but it
        belongs to the Floresta tab's on-map legend all the same, since the
        Forest Code's 2008 reference date is exactly what that tab is about
        (doc/12-spot-2008.md). This is the toggle that legend uses, so the
        control there does not need to know SPOT's asset key or reimplement
        the licence-gated fail-closed handling in `set_basemap`.
        """
        async with self:
            current = self.basemap
        if is_ee_basemap(current) and current.startswith("spot"):
            return self.__class__.set_basemap(DEFAULT_BASEMAP)
        return self.__class__.set_basemap("spot_2008_visual")

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
        layers: List[Dict[str, Any]] = []

        if is_ee_basemap(self.basemap) and self.basemap in self.ee_basemap_urls:
            conf = ALL_BASEMAPS[self.basemap]
            layers.append({
                "id": f"basemap:{self.basemap}",
                "url": self.ee_basemap_urls[self.basemap],
                "attribution": conf["attribution"],
                "max_native_zoom": conf.get("max_native_zoom", 16),
                "opacity": 1.0,
                "z_index": 1,
            })
        else:
            # While an EE basemap is minting (or failed), the XYZ default
            # keeps the map non-empty — never a blank tile layer underneath.
            key = self.basemap if self.basemap in BASEMAPS else DEFAULT_BASEMAP
            base = BASEMAPS[key]
            layers.append({
                "id": f"basemap:{key}",
                "url": base["url"],
                "attribution": base["attribution"],
                "max_native_zoom": base.get("max_native_zoom", 19),
                "opacity": 1.0,
                "z_index": 0,
            })

        if self.analysis_layer_enabled and len(self.swipe_layer_keys) == 2:
            # Transições and Validação: two layers at once, each clipped to
            # its side of the divider by leaflet_map.js.
            #
            # `clip` is applied HERE, fresh, from each key's POSITION in
            # `swipe_layer_keys` — never trusted from `analysis_layer_specs`.
            # The specs cache is shared across every tab that can show a
            # given tile (Cobertura, Transições and Validação can all mint
            # "mapbiomas:v10_1:2008"), and which SIDE a tile sits on is
            # context — which pairing is currently active — not a property
            # of the tile itself. Baking "clip" into the cached dict at mint
            # time was the actual bug: a tile minted as the right side in one
            # pairing stayed clipped "right" forever, including the next time
            # a DIFFERENT pairing needed it on the left — reproduced by
            # visiting Transições with 2008 as one of the two years, then
            # Validação's SPOT×2008 pairing, in that order. z_index must also
            # differ or Leaflet's own pane ordering (both "overlayPane")
            # leaves the paint order to insertion order, which is fragile
            # once either layer refreshes.
            left_key, right_key = self.swipe_layer_keys
            for i, (key, side) in enumerate(((left_key, "left"), (right_key, "right"))):
                spec = self.analysis_layer_specs.get(key)
                if spec:
                    layers.append({**spec, "id": f"swipe:{key}",
                                   "clip": side, "z_index": 10 + i})
        else:
            active = self.active_analysis_layer_key
            if self.analysis_layer_enabled and active in self.analysis_layer_specs:
                layers.append(self.analysis_layer_specs[active])

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
