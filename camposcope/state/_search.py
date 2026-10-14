"""The unified search box (doc/11-search-and-navigation.md).

One field, five resolvers, tried in a fixed order and stopping at the first
match: CAR code → coordinate → município → território → place name. The first
four are exact and local; only the fifth reaches a third-party service, which
is what keeps the geocoder volume defensible (decision D11).

Território covers terras indígenas (FUNAI) and unidades de conservação
(CNUC/ICMBio). Because a município and a territory can share a name, that one
resolver is offered alongside a município hit rather than only after it — see
``services/geocode.py``'s own docstring.

The box **echoes how it read the input** before acting on it. That one line is
what stops a transposed coordinate pair or a mistyped code from quietly
resolving somewhere plausible and wrong (doc/08-ui-ux.md §2).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import reflex as rx

from ..services import address, geocode, municipios, territorios
from ..services.geocode import GeocodeError
from ..translations import get_translations

logger = logging.getLogger(__name__)


class SearchMixin(rx.State, mixin=True):
    """What the user typed, how it was read, and what came back."""

    query: str = ""
    #: Human-readable "read as …", shown before anything happens.
    echo: str = ""
    echo_kind: str = ""
    search_error: str = ""
    searching_place: bool = False

    #: Município and território candidates (local, instant) and place
    #: candidates (geocoded).
    municipio_hits: List[Dict[str, Any]] = []
    territorio_hits: List[Dict[str, Any]] = []
    place_hits: List[Dict[str, Any]] = []
    #: ``[lat, lon]`` of the last geocoded place the user chose, drawn as a pin
    #: (``ZonesMixin.map_overlays``). A pin, because an address framed only by
    #: a viewport leaves the user hunting for which building it meant.
    search_pin: List[float] = []

    @rx.var
    def place_attribution(self) -> str:
        """Credit exactly the sources the listed places came from."""
        return address.attributions(self.place_hits)

    @rx.var
    def can_search_as_place(self) -> bool:
        """The escape hatch: a query a local resolver claimed (a município, a
        territory) may still have been meant as an address — "São José" is
        dozens of municípios and a street in every one of them."""
        return self.echo_kind in ("municipio", "territorio") and bool(self.query.strip())

    @rx.var
    def has_results(self) -> bool:
        return bool(self.municipio_hits or self.territorio_hits
                    or self.place_hits or self.candidates)

    def _echo_text(self, resolution) -> str:
        """Rebuild the echo line in the current language.

        ``geocode.resolve`` is PT-only by design (it is a pure classifier, not
        a UI-facing service — doc/11-search-and-navigation.md) and returns its
        own ``.echo`` pre-formatted in Portuguese. Only the noun ("código
        CAR"/"coordenada"/"município"/"território"/"lugar") needs a language,
        so it is
        rebuilt here from ``kind`` + ``payload`` rather than adding ``lang`` to
        a service that otherwise has no notion of it.
        """
        msgs = get_translations(getattr(self, "lang", "pt"))
        kind, payload = resolution.kind, resolution.payload
        if kind == "codigo":
            return f"{msgs['echo_codigo']} {payload}"
        if kind == "cep":
            return f"{msgs['echo_cep']} {address.format_cep(payload)}"
        if kind == "coordenada":
            return f"{msgs['echo_coordenada']} {payload.lat:.4f}, {payload.lon:.4f}"
        if kind == "municipio":
            first = payload[0]
            return f"{msgs['echo_municipio']} {first['nome']}/{first['uf']}"
        if kind == "territorio":
            first = payload[0]
            return f"{msgs['echo_territorio']} {first['nome']}"
        if kind == "lugar":
            return f"{msgs['echo_lugar']} “{payload}”"
        return resolution.echo

    # --- typing ----------------------------------------------------------
    @rx.event
    def set_query(self, value: str) -> None:
        """Update the echo line as the user types — locally, with no requests.

        ``geocode.resolve`` classifies without performing anything, which is
        precisely what makes a live echo affordable: every keystroke costs a
        regex and a dict lookup, never a round trip.
        """
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
            # A coordinate that parsed but is unusable — a transposed pair, say.
            # Surface it while typing rather than on submit: the user is looking
            # at the field right now.
            self.echo = ""
            self.echo_kind = "erro"
            self.search_error = str(exc)

    # --- submitting -------------------------------------------------------
    @rx.event(background=True)
    async def submit_search(self):
        """Act on whatever the echo line already said this was."""
        async with self:
            raw = self.query.strip()
            self.search_error = ""
            self.municipio_hits = []
            self.territorio_hits = []
            self.place_hits = []
            if not raw:
                return

        try:
            resolution = geocode.resolve(raw)
        except ValueError as exc:
            async with self:
                self.search_error = str(exc)
            return

        kind = resolution.kind

        if kind == "codigo":
            async with self:
                self.code_input = resolution.payload
            return self.__class__.search_by_code

        if kind == "cep":
            return self.__class__.search_cep_code(resolution.payload)

        if kind == "coordenada":
            coord = resolution.payload
            return self.__class__.select_at_point(coord.lat, coord.lon)

        if kind == "municipio":
            async with self:
                self.municipio_hits = resolution.payload
                self.territorio_hits = list(resolution.territorios)
            # A single unambiguous hit goes straight there; several are
            # offered. A territory sharing the name makes it ambiguous too,
            # even when only one município matched — jumping to Jaú/SP while
            # a Parque Nacional do Jaú sits unmentioned in the list below
            # would be exactly the silent coin flip carrying both lists is
            # meant to avoid.
            if len(resolution.payload) == 1 and not resolution.territorios:
                return self.__class__.choose_municipio(
                    resolution.payload[0]["cod_municipio_ibge"]
                )
            return

        if kind == "territorio":
            async with self:
                self.territorio_hits = resolution.payload
            if len(resolution.payload) == 1:
                return self.__class__.choose_territorio(
                    resolution.payload[0]["tipo"], resolution.payload[0]["codigo"]
                )
            return

        # kind == "lugar" — the only branch that touches a third party.
        return self.__class__.search_as_place

    @rx.event(background=True)
    async def search_as_place(self):
        """Geocode the query as a place name or street address.

        Reached two ways: as the last resolver, and from the "search as an
        address" link under a município/território match — the user saying
        the local reading was not what they meant.
        """
        async with self:
            raw = self.query.strip()
            if not raw:
                return
            self.search_error = ""
            self.municipio_hits = []
            self.territorio_hits = []
            self.place_hits = []
            self.searching_place = True
            self.echo = self._echo_text(geocode.Resolution("lugar", "", raw))
            self.echo_kind = "lugar"
        try:
            places = geocode.search_places(raw, limit=6)
        except GeocodeError as exc:
            async with self:
                self.searching_place = False
                self.search_error = str(exc)
            return

        async with self:
            self.searching_place = False
            if not places:
                self.search_error = get_translations(self.lang)[
                    "erro_lugar_nao_encontrado"
                ].format(query=raw)
            self.place_hits = [p.to_hit() for p in places]
        # One unambiguous street-level hit is an answer, not a choice.
        if len(places) == 1:
            return self.__class__.choose_place(0)

    @rx.event(background=True)
    async def search_cep_code(self, digits: str):
        """A CEP: OSM's postcode centroid, labelled with ViaCEP's street and
        bairro; failing both, the município ViaCEP names — framed exactly as
        if the user had typed it."""
        async with self:
            self.searching_place = True
            self.search_error = ""
        try:
            places, info = geocode.search_cep(digits)
        except GeocodeError as exc:
            async with self:
                self.searching_place = False
                self.search_error = str(exc)
            return

        async with self:
            self.searching_place = False
            self.place_hits = [p.to_hit() for p in places]
            if not places and not (info and info.get("ibge")):
                self.search_error = get_translations(self.lang)[
                    "erro_cep_nao_encontrado"
                ].format(cep=address.format_cep(digits))
        if places:
            return self.__class__.choose_place(0)
        if info and info.get("ibge", "").isdigit():
            return self.__class__.choose_municipio(int(info["ibge"]))

    # --- acting on a result ----------------------------------------------
    @rx.event(background=True)
    async def choose_municipio(self, cod_municipio_ibge: int):
        """Frame the map on a município and open its property list.

        **Selects no property.** Framing a place and identifying a registration
        are different acts (doc/11 §2).
        """
        row = municipios.by_code(int(cod_municipio_ibge))
        if row is None:
            return

        async with self:
            self.municipio_hits = []
            self.search_uf = row["uf"]
            self.search_municipio_ibge = str(row["cod_municipio_ibge"])
            self.search_mode = "municipio"
            self.query = f"{row['nome']}/{row['uf']}"
            self.echo = f"município {row['nome']}/{row['uf']}"
            self.echo_kind = "municipio"

        # The boundary is the only part that costs a round trip, and only once a
        # município is actually chosen (decision D12).
        box = municipios.bounds(int(cod_municipio_ibge))
        async with self:
            if box:
                self.fit_bounds = box

        return self.__class__.load_municipio_list

    @rx.event
    def choose_territorio(self, tipo: str, codigo: str) -> None:
        """Frame the map on a terra indígena or unidade de conservação, and
        draw the layer it belongs to. **Selects no property.**

        Turning the layer on is the point of the gesture: framing a territory
        and then not drawing it would leave the user looking at an unmarked
        rectangle of map and wondering whether the search worked. It is not a
        viewport move triggered by a layer toggle (constraint C1 forbids that)
        — it is the other way round, a search gesture that also draws what it
        found.

        No round trip, unlike ``choose_municipio``: the bbox is a committed
        column in ``data/territorios.csv``, computed from the full geometry,
        so framing is both instant and exact even though the drawn overlay is
        simplified to ~200 m.
        """
        key = f"{tipo}:{codigo}"
        row = territorios.by_key(key)
        if row is None:
            return

        self.territorio_hits = []
        self.municipio_hits = []
        self.place_hits = []
        if tipo == "indigena":
            self.show_terras_indigenas = True
        else:
            self.show_unidades_conservacao = True

        box = territorios.bounds(key)
        if box:
            self.fit_bounds = box

        # Only for a single-UF territory. Several span two or three, and
        # `search_uf` drives which of SICAR's 27 per-UF CAR layers is drawn —
        # picking one of three arbitrarily would put the wrong state's
        # registrations on screen and look like an answer.
        ufs = [u for u in row["uf"].split(", ") if u]
        if len(ufs) == 1:
            self.search_uf = ufs[0]

        self.query = row["nome"]
        msgs = get_translations(getattr(self, "lang", "pt"))
        self.echo = f"{msgs['echo_territorio']} {row['nome']}"
        self.echo_kind = "territorio"

    @rx.event
    def choose_place(self, index: int) -> None:
        """Frame the map on a geocoded place and pin it. **Selects no
        property.**

        A street address or postcode has a bounding box a few metres wide, and
        ``fit_bounds`` is capped at z12 (see leaflet_map.js) — so those go to a
        centre + zoom chosen by precision instead, close enough to see the
        properties around the pin. A town or a region keeps its box: a bbox is
        honest about uncertainty in a way a single pin is not.
        """
        try:
            place = self.place_hits[int(index)]
        except (IndexError, ValueError, TypeError):
            return
        precision = place.get("precision", "lugar")
        if place.get("bounds") and precision not in address.POINT_PRECISIONS:
            self.fit_bounds = place["bounds"]
        else:
            self.center = [place["lat"], place["lon"]]
            self.zoom = address.ZOOM_BY_PRECISION.get(precision, 14)
        self.search_pin = [place["lat"], place["lon"]]
        title = place.get("title") or place["label"]
        subtitle = place.get("subtitle") or ""
        self.query = f"{title}, {subtitle}" if subtitle else title
        msgs = get_translations(getattr(self, "lang", "pt"))
        self.echo = f"{msgs['echo_lugar']} — {msgs['search_place_hint']}"
        self.echo_kind = "lugar"

    @rx.event
    def clear_search(self) -> None:
        self.query = ""
        self.echo = ""
        self.echo_kind = ""
        self.search_error = ""
        self.municipio_hits = []
        self.territorio_hits = []
        self.place_hits = []
        self.search_pin = []
