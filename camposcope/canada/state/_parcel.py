"""Finding an analysis area, the selected record, and its zones.

Combines the Brazil page's ``ImovelMixin``/``ZonesMixin``/``SearchMixin`` into
one mixin, because the gestures here (paste a PID, click the map, pick an
area result) all funnel through the same adoption logic the way they do on the
Brazil page, and there is no third-party disclosure step this page needs its
own file for.

**Three kinds of analysis area, tried in order, and every point in Canada
resolves to one of them.** A click or a typed coordinate is a request to
analyse *somewhere*, and "no parcel here" is not the same answer as "nothing
to show" — most of the country has no parcel fabric at all, and even inside BC
most land is unsurveyed Crown land (``pmbc.py``'s module docstring). So
:meth:`select_at_point` tries three sources in turn:

1. **A parcel** (``pmbc.py``) — BC only, since ParcelMap BC is a provincial
   cadastre.
2. **A protected area** (``protected_areas.py``, WDPA) — national. A park,
   ecological reserve or conservancy is exactly the kind of place someone
   monitoring "natural areas", the way the user framing this feature put it,
   is likely to click.
3. **A synthetic 500 ha square** centred on the click
   (``zones.py::synthetic_square_geojson``) — national, and never fails: it is
   the floor under the whole chain, so a click anywhere inside the country
   always produces *something* to analyse. Only a click genuinely outside
   Canada, or one that looks transposed, is refused.

The three kinds share one ``self.parcel`` dict shape (see :func:`_base_dict`)
so every component that reads it can index the same keys regardless of which
tier answered; :attr:`self.parcel["kind"]` is what the UI branches display on.

The parcel card shows every fabric/register field **verbatim** — same
discipline the Brazil page calls constraint C4, applied to different kinds of
record: nothing here derives a verdict from ``PARCEL_STATUS``, ``OWNER_TYPE``
or a WDPA ``IUCN_CAT``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import reflex as rx

from ...state._proxy import plain  # noqa: F401  (re-exported for sibling mixins)
from ..config import pmbc as vocab
from ..services import bc_lookup, geocode, municipalities, pmbc, protected_areas
from ..services.geocode import GeocodeError
from ..services.pmbc import PmbcError
from ..services.protected_areas import ProtectedArea, WdpaError
from ..services.zones import build_zones, centroid_lat_lon, synthetic_square_geojson
from ..translations import get_translations

logger = logging.getLogger(__name__)


class CanadaParcelMixin(rx.State, mixin=True):
    """Search state and the selected parcel record."""

    # --- search box --------------------------------------------------------
    query: str = ""
    echo: str = ""
    echo_kind: str = ""
    search_error: str = ""
    searching: bool = False
    searching_place: bool = False

    area_hits: List[Dict[str, Any]] = []
    place_hits: List[Dict[str, Any]] = []
    #: More than one parcel stacked over a clicked point — see
    #: ``canada/services/pmbc.py``'s module docstring for why this is rare
    #: rather than routine here, unlike the Brazil page's overlap chooser.
    candidates: List[Dict[str, Any]] = []

    # --- the selected record -------------------------------------------
    parcel: Dict[str, Any] = {}
    parcel_geojson: Dict[str, Any] = {}
    parcel_error: str = ""

    # --- zones -----------------------------------------------------------
    ring_radii_m: List[int] = [500, 2000, 5000]
    zones: List[Dict[str, Any]] = []
    zones_geojson: Dict[str, Any] = {}
    area_registered_ha: float = 0.0
    area_calculated_ha: float = 0.0
    area_delta_ha: float = 0.0
    area_delta_pct: float = 0.0
    area_flagged: bool = False
    overlaps: List[Dict[str, Any]] = []
    active_zone: str = "parcela"
    zones_error: str = ""

    @rx.var
    def has_parcel(self) -> bool:
        """Whether *any* analysis area is selected — a parcel, a park, or a
        synthetic square. Kept the same name used throughout the rest of the
        page (results tabs, layers, exports all gate on ``S.has_parcel``)
        rather than renamed to something like ``has_analysis_area``: every
        one of those call sites means "is there something to analyse", which
        is true for all three kinds now, not "is it specifically a parcel".

        Checks ``identifier`` rather than ``fabric_id`` — the latter is only
        ever populated for kind ``"parcel"`` and defaults to 0 (falsy) for
        ``"park"``/``"square"``, which silently hid every non-parcel selection
        from the whole page until caught in testing.
        """
        return bool(self.parcel.get("identifier"))

    @rx.var
    def has_results(self) -> bool:
        return bool(self.area_hits or self.place_hits or self.candidates)

    @rx.var
    def zone_count(self) -> int:
        return len(self.zones)

    @rx.var
    def map_overlays(self) -> Dict[str, Any]:
        return self.zones_geojson or {"type": "FeatureCollection", "features": []}

    @rx.var(cache=True, deps=["language"], auto_deps=False)
    def disclosure(self) -> str:
        return (vocab.DISCLOSURE_PT if getattr(self, "language", "en") == "pt"
                else vocab.DISCLOSURE_EN)

    @rx.var(cache=True, deps=["language"], auto_deps=False)
    def bc_only_note(self) -> str:
        return (vocab.BC_ONLY_NOTE_PT if getattr(self, "language", "en") == "pt"
                else vocab.BC_ONLY_NOTE_EN)

    # --- typing --------------------------------------------------------
    def set_query(self, value: str) -> None:
        self.query = value
        self.search_error = ""
        if not value.strip():
            self.echo = ""
            self.echo_kind = ""
            return
        try:
            resolution = geocode.resolve(value)
            self.echo = self._echo_text(resolution)
            self.echo_kind = resolution.kind
        except ValueError as exc:
            self.echo = ""
            self.echo_kind = "erro"
            self.search_error = str(exc)

    def _echo_text(self, resolution) -> str:
        lang = getattr(self, "language", "en")
        msgs = get_translations(lang)
        kind, payload = resolution.kind, resolution.payload
        if kind == "pid":
            return f"{msgs['echo_pid']} {payload if isinstance(payload, str) else payload}"
        if kind == "coordenada":
            return f"{msgs['echo_coordenada']} {payload.lat:.4f}, {payload.lon:.4f}"
        if kind == "area":
            first = payload[0]
            return f"{msgs['echo_area']} {first['short_name']}"
        if kind == "lugar":
            return f'{msgs["echo_lugar"]} "{payload}"'
        return resolution.echo

    @rx.event(background=True)
    async def submit_search(self):
        async with self:
            raw = self.query.strip()
            self.search_error = ""
            self.area_hits = []
            self.place_hits = []
            lang = getattr(self, "language", "en")
            if not raw:
                return

        try:
            resolution = geocode.resolve(raw)
        except ValueError as exc:
            async with self:
                self.search_error = str(exc)
            return

        kind = resolution.kind

        if kind == "pid":
            return self.__class__.load_by_identifier(resolution.payload)

        if kind == "coordenada":
            coord = resolution.payload
            return self.__class__.select_at_point(coord.lat, coord.lon)

        if kind == "area":
            async with self:
                self.area_hits = resolution.payload
            if len(resolution.payload) == 1:
                return self.__class__.choose_area(resolution.payload[0]["pmbc_key"])
            return

        # kind == "lugar" — the only branch that touches a third party.
        async with self:
            self.searching_place = True
        try:
            places = geocode.search_places(raw, limit=5)
        except GeocodeError as exc:
            async with self:
                self.searching_place = False
                self.search_error = str(exc)
            return

        async with self:
            self.searching_place = False
            if not places:
                self.search_error = get_translations(lang)[
                    "erro_lugar_nao_encontrado"].format(query=raw)
            self.place_hits = [
                {"label": p.label, "lat": p.lat, "lon": p.lon,
                 "bounds": p.bounds or []}
                for p in places
            ]

    def choose_place(self, index: int) -> None:
        """Frame the map on a geocoded place. **Selects no parcel.**"""
        try:
            place = self.place_hits[int(index)]
        except (IndexError, ValueError, TypeError):
            return
        self.place_hits = []
        if place.get("bounds"):
            self.fit_bounds = place["bounds"]
        else:
            self.center = [place["lat"], place["lon"]]
            self.zoom = 14
        self.query = place["label"]
        self.echo = "place — click a parcel on the map to analyse it"
        self.echo_kind = "lugar"

    @rx.event(background=True)
    async def choose_area(self, pmbc_key: str):
        """Frame the map on a municipality or regional district.

        **Selects no parcel** — same split the Brazil page's ``choose_municipio``
        makes between framing a place and identifying a registration.
        """
        row = municipalities.by_key(pmbc_key)
        async with self:
            self.area_hits = []
            self.query = row["short_name"] if row else pmbc_key
            self.echo = f"area {row['short_name']}" if row else pmbc_key
            self.echo_kind = "area"
            box = row.get("bounds") if row else None
            if box:
                self.fit_bounds = box

    def clear_search(self) -> None:
        self.query = ""
        self.echo = ""
        self.echo_kind = ""
        self.search_error = ""
        self.area_hits = []
        self.place_hits = []

    # --- gestures --------------------------------------------------------
    @rx.event(background=True)
    async def load_by_identifier(self, value: str):
        """Gesture 1 — paste a PID or a fabric id. Parcel only: an identifier
        that specific belongs to one register, unlike a click or a
        coordinate, which is why this gesture has no park/square fallback."""
        async with self:
            self.parcel_error = ""
            self.candidates = []
            self.searching = True

        try:
            record = pmbc.by_identifier(value)
        except (vocab.PidError, PmbcError) as exc:
            async with self:
                self.searching = False
                self.parcel_error = str(exc)
            return

        async with self:
            self.searching = False
            self._adopt_parcel(record)
        # Nudges the mobile sheet open toward "half" — never smaller — the
        # same map-app convention as the Brazil page's own version of this
        # call; see canada/pages/index.py::_SHEET_SCRIPT's
        # window.__caSheetSnapTo.
        return [self.__class__.run_aci_history, self.__class__.mint_analysis_layer,
               rx.call_script(
                   "window.__caSheetSnapTo && window.__caSheetSnapTo('half')")]

    @rx.event(background=True)
    async def select_at_point(self, lat: float, lon: float):
        """Gesture 2 — click the map, or a resolved coordinate.

        The three-tier chain the module docstring describes: a BC parcel
        first, then a national protected area, then a synthetic 500 ha square
        that never fails to produce something. Only a point outside Canada
        entirely, or one that looks transposed, is refused before any of the
        three tiers is even tried.
        """
        async with self:
            self.parcel_error = ""
            self.candidates = []
            lang = getattr(self, "language", "en")

        verdict = bc_lookup.classify(lat, lon)
        if verdict in ("outside", "swapped"):
            async with self:
                key = ("erro_coordenada_invertida" if verdict == "swapped"
                       else "erro_fora_canada")
                self.parcel_error = get_translations(lang)[key]
            return

        async with self:
            self.searching = True

        # --- tier 1: parcel (BC only) --------------------------------- #
        if verdict == "bc":
            try:
                found = pmbc.at_point(lat, lon)
            except PmbcError as exc:
                async with self:
                    self.searching = False
                    self.parcel_error = str(exc)
                return

            if len(found) == 1:
                async with self:
                    self.searching = False
                    self._adopt_parcel(found[0], lat, lon)
                return [self.__class__.run_aci_history,
                        self.__class__.mint_analysis_layer,
                        rx.call_script("window.__caSheetSnapTo && "
                                      "window.__caSheetSnapTo('half')")]
            if len(found) > 1:
                async with self:
                    self.searching = False
                    self.candidates = [self._summary(p) for p in found]
                return
            # found == [] falls through to tier 2 — Crown land, the normal
            # case for most of BC's own landmass.

        # --- tier 2: protected area (national) ------------------------- #
        try:
            park = protected_areas.at_point(lat, lon)
        except WdpaError as exc:
            # Logged, not surfaced: a WDPA outage must not block the square
            # fallback below, which never fails and is the honest floor
            # under this whole chain.
            logger.warning("WDPA lookup failed: %s", exc)
            park = None

        # WDPA represents its smallest sites as a single point, not a
        # polygon — real for a meaningful share of Canadian entries. A point
        # has no area for the zone-ring pipeline to buffer outward from in
        # any way that reads as "the reserve's own boundary", so it is
        # treated the same as no match at all and falls through to the
        # square tier, rather than adopting a park whose "area" would read
        # as a broken zero.
        if park is not None and (park.geometry or {}).get("type") not in (
                "Polygon", "MultiPolygon"):
            logger.info("WDPA match %s has no polygon geometry — falling "
                       "through to the square tier", park.name)
            park = None

        if park is not None:
            async with self:
                self.searching = False
                self._adopt_park(park, lat, lon)
            return [self.__class__.run_aci_history,
                   self.__class__.mint_analysis_layer,
                   rx.call_script("window.__caSheetSnapTo && "
                                 "window.__caSheetSnapTo('half')")]

        # --- tier 3: synthetic square (national, never fails) ---------- #
        async with self:
            self.searching = False
            self._adopt_square(lat, lon)
        return [self.__class__.run_aci_history, self.__class__.mint_analysis_layer,
               rx.call_script(
                   "window.__caSheetSnapTo && window.__caSheetSnapTo('half')")]

    @rx.event(background=True)
    async def choose_candidate(self, identifier: str):
        """More than one parcel stacked over a clicked point (tier 1 only —
        see ``pmbc.py``'s module docstring for why this is rare rather than
        routine here)."""
        async with self:
            self.searching = True
            self.candidates = []
        try:
            record = pmbc.by_identifier(identifier)
        except (vocab.PidError, PmbcError) as exc:
            async with self:
                self.searching = False
                self.parcel_error = str(exc)
            return
        async with self:
            self.searching = False
            self._adopt_parcel(record)
        return [self.__class__.run_aci_history, self.__class__.mint_analysis_layer,
               rx.call_script(
                   "window.__caSheetSnapTo && window.__caSheetSnapTo('half')")]

    def adopt_pid_param(self) -> None:
        """Honour ``?pid=<value>`` on load — the deep-link persistence model,
        mirroring the Brazil page's ``?car=``. Parcel only, same reasoning as
        :meth:`load_by_identifier`: a park or a synthetic square has no
        identifier of its own to carry in a URL."""
        value = self.router.url.query_parameters.get("pid", "")
        if value:
            self.query = value
            return self.__class__.load_by_identifier(value)

    # --- internals -------------------------------------------------------
    @staticmethod
    def _summary(record: pmbc.Parcel) -> Dict[str, Any]:
        return {
            "identifier": record.identifier,
            "area_registered_ha": round(record.area_registered_ha, 4),
            "parcel_class": record.parcel_class,
            "owner_type": record.owner_type,
            "municipality": record.municipality,
        }

    #: Every key every kind's dict carries, defaulted to empty/zero/false —
    #: so a component can always index e.g. ``S.parcel["designation"]``
    #: without a conditional, whichever tier actually answered, and branch
    #: only on ``S.parcel["kind"]`` to decide what to *show*. Built once here
    #: rather than duplicated across the three ``_adopt_*`` methods below.
    @staticmethod
    def _base_dict(kind: str, identifier: str, area_ha: float,
                   queried_at: str) -> Dict[str, Any]:
        return {
            "kind": kind,
            "identifier": identifier,
            "area_registered_ha": round(area_ha, 4),
            "queried_at": queried_at,
            # parcel (pmbc.Parcel) fields
            "fabric_id": 0, "pid": "", "pid_formatted": "", "parcel_name": "",
            "plan_number": "", "parcel_status": "", "parcel_class": "",
            "owner_type": "", "parcel_start_date": "", "start_year": 0,
            "municipality": "", "regional_district": "", "when_updated": "",
            "is_non_land": False,
            # protected-area (WDPA) fields
            "wdpa_id": 0, "designation": "", "designation_type": "",
            "iucn_category": "", "park_status": "", "status_year": 0,
            "managing_authority": "",
            # coordinate reference, every kind — see _reference_point()
            "click_lat": 0.0, "click_lon": 0.0,
            "centroid_lat": 0.0, "centroid_lon": 0.0,
        }

    def _reference_point(self, geojson: Dict[str, Any],
                         lat: float | None, lon: float | None) -> None:
        """Stamp the coordinate row every card shows: the point actually
        clicked when selection came from a map click, and always the
        geometry's own centroid — so a parcel found by PID search or a
        ``?pid=`` deep link, which never had a click, still gets one.
        ``parcel_card.py`` prefers ``click_lat/lon`` when non-zero and falls
        back to the centroid otherwise (Canada's bbox never legitimately
        puts either at exactly 0)."""
        centroid_lat, centroid_lon = centroid_lat_lon(geojson)
        self.parcel["centroid_lat"] = round(centroid_lat, 5)
        self.parcel["centroid_lon"] = round(centroid_lon, 5)
        if lat is not None and lon is not None:
            self.parcel["click_lat"] = round(lat, 5)
            self.parcel["click_lon"] = round(lon, 5)

    def _adopt_parcel(self, record: pmbc.Parcel,
                      lat: float | None = None, lon: float | None = None
                      ) -> None:
        self._clear_analysis_results()
        self.parcel = self._base_dict(
            "parcel", record.identifier, record.area_registered_ha,
            record.queried_at)
        self.parcel.update({
            "fabric_id": record.fabric_id,
            "pid": record.pid,
            "pid_formatted": record.pid_formatted,
            "parcel_name": record.parcel_name,
            "plan_number": record.plan_number,
            "parcel_status": record.parcel_status,
            "parcel_class": record.parcel_class,
            "owner_type": record.owner_type,
            "parcel_start_date": record.parcel_start_date or "",
            "start_year": record.start_year or 0,
            "municipality": record.municipality,
            "regional_district": record.regional_district,
            "when_updated": record.when_updated or "",
            "is_non_land": record.is_non_land,
        })
        self.parcel_geojson = record.geometry or {}
        self._reference_point(self.parcel_geojson, lat, lon)
        self.build_zones()
        self.frame_geometry(self.parcel_geojson)
        self.active_zone = "parcela"

    def _adopt_park(self, park: ProtectedArea,
                    lat: float | None = None, lon: float | None = None
                    ) -> None:
        self._clear_analysis_results()
        self.parcel = self._base_dict(
            "park", park.name, park.reported_area_km2 * 100.0, park.queried_at)
        self.parcel.update({
            "wdpa_id": park.wdpa_id,
            "designation": park.designation,
            "designation_type": park.designation_type,
            "iucn_category": park.iucn_category,
            "park_status": park.status,
            "status_year": park.status_year or 0,
            "managing_authority": park.managing_authority,
        })
        self.parcel_geojson = park.geometry or {}
        self._reference_point(self.parcel_geojson, lat, lon)
        self.build_zones()
        self.frame_geometry(self.parcel_geojson)
        self.active_zone = "parcela"

    def _adopt_square(self, lat: float, lon: float) -> None:
        """The floor tier: a synthetic 500 ha square, never fetched from
        anywhere and never failing. ``identifier`` names the coordinate
        rather than any register, because there is no register behind it —
        the card says so explicitly (see
        ``canada/components/parcel_card.py::_square_card``)."""
        self._clear_analysis_results()
        geojson = synthetic_square_geojson(lat, lon, area_ha=500.0)
        self.parcel = self._base_dict(
            "square", f"{lat:.4f}, {lon:.4f}", 500.0, "")
        self.parcel_geojson = geojson
        self._reference_point(self.parcel_geojson, lat, lon)
        self.build_zones()
        self.frame_geometry(self.parcel_geojson)
        self.active_zone = "parcela"

    def _clear_analysis_results(self) -> None:
        """Wipe every manually-triggered analysis tab's output before a new
        parcel/park/square is adopted.

        Cobertura (``history_rows``) refreshes itself automatically on every
        new selection — it is in ``select_at_point``'s own return list —
        so it is excluded here. Every other tab is opt-in behind its own
        "Run" button to keep Earth Engine calls off the critical path, which
        means without this, switching to a new area left the *previous*
        area's numbers on screen, unlabelled as stale. That is what actually
        produced a real bug report: on a newly-selected parcel, the MODIS
        fire tile (a single global cached image, correct for any point) and
        the AAFC burn chart (reads live ``history_rows``, correct) both
        showed the true answer, while the MODIS fire *chart* — never
        auto-rerun — still showed whatever an earlier, different parcel had
        left behind.
        """
        self.fire_running = False
        self.fire_error = ""
        self.fire_rows = []
        self.fire_table_rows = []
        self.fire_provenance = {}

        self.biomass_running = False
        self.biomass_error = ""
        self.biomass_rows = []
        self.biomass_provenance = {}

        self.hansen_running = False
        self.hansen_error = ""
        self.hansen_loss_rows = []
        self.hansen_gain_ha = 0.0
        self.hansen_has_run = False
        self.hansen_split_year = 0
        self.hansen_provenance = {}

        self.age_running = False
        self.age_error = ""
        self.age_rows = []
        self.age_has_run = False
        self.age_provenance = {}

        self.landscape_running = False
        self.landscape_error = ""
        self.landscape_rows = []
        self.landscape_provenance = {}

        self.connectivity_running = False
        self.connectivity_error = ""
        self.connectivity_degraded = False
        self.connectivity_rows = []
        self.connectivity_provenance = {}

        self.sankey_running = False
        self.sankey_error = ""
        self.sankey_transitions = {}
        self.sankey_provenance = {}
        self.sankey_zone_label = ""

        self.validation_running = False
        self.validation_error = ""
        self.validation_summary = []
        self.validation_matrix = []
        self.validation_provenance = {}

    def build_zones(self) -> None:
        geojson = getattr(self, "parcel_geojson", None)
        lang = getattr(self, "language", "en")
        kind = self.parcel.get("kind", "parcel")
        if not geojson:
            self.zones = []
            self.zones_geojson = {}
            self.overlaps = []
            return

        self.zones_error = ""
        label_key = {"parcel": "zona_parcela", "park": "zona_park",
                    "square": "zona_square"}.get(kind, "zona_parcela")
        try:
            built = build_zones(geojson,
                                radii_m=getattr(self, "ring_radii_m",
                                               [500, 2000, 5000]),
                                parcel_label=get_translations(lang)[label_key],
                                lang=lang)
        except Exception as exc:                       # noqa: BLE001
            logger.exception("zone construction failed")
            self.zones_error = get_translations(lang)["erro_zonas"].format(
                detail=exc)
            self.zones = []
            self.zones_geojson = {}
            return

        self.zones = [z.to_row() for z in built]
        self.zones_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "role": "property" if z.kind == "property" else "ring",
                        "zone_key": z.key, "label": z.label,
                        "area_ha": round(z.area_ha, 2),
                    },
                    "geometry": z.geojson,
                }
                for z in built
            ],
        }

        # The declared-vs-computed area check is only meaningful for "parcel"
        # (a real registered figure from the fabric) and "park" (WDPA's own
        # REP_AREA, which can genuinely disagree with the polygon's geometric
        # area — the same disagreement-is-information framing decision D6
        # applies to the CAR's declared area). A synthetic square has no
        # "declared" figure distinct from what it computes to — both numbers
        # would just restate the same 500 ha, which is noise, not a check —
        # so "square" skips it: the card (parcel_card.py) never renders the
        # block for that kind, but the fields are still populated here
        # (harmlessly near-zero) rather than left stale from whatever was
        # selected before, in case a caller reads them regardless of kind.
        from ..services.zones import check_area

        declared = float(self.parcel.get("area_registered_ha", 0.0))
        check = check_area(declared, geojson)
        self.area_registered_ha = check.registered_ha
        self.area_calculated_ha = round(check.computed_ha, 4)
        self.area_delta_ha = round(check.delta_ha, 4)
        self.area_delta_pct = round(check.delta_pct, 3)
        self.area_flagged = check.flagged

    @rx.event(background=True)
    async def load_neighbours(self):
        """Which neighbouring parcels genuinely overlap this one — rare on a
        surveyed fabric, which is exactly why it is worth showing when it
        happens. See ``canada/services/pmbc.py::neighbours``."""
        async with self:
            fabric_id = self.parcel.get("fabric_id")
            geojson = self.parcel_geojson
        if not (fabric_id and geojson):
            return

        try:
            record = pmbc.by_fabric_id(int(fabric_id))
            others = pmbc.neighbours(record)
            from ..services.zones import overlap_areas

            rows = overlap_areas(
                geojson, [(o.identifier, o.geometry) for o in others])
        except Exception as exc:                       # noqa: BLE001
            logger.warning("neighbour lookup failed: %s", exc)
            async with self:
                self.overlaps = []
            return

        async with self:
            self.overlaps = rows

    def set_active_zone(self, zone_key: str) -> None:
        self.active_zone = zone_key
