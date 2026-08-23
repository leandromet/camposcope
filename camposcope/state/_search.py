"""The unified search box (doc/11-search-and-navigation.md).

One field, four resolvers, tried in a fixed order and stopping at the first
match: CAR code → coordinate → município → place name. The first three are exact
and local; only the fourth reaches a third-party service, which is what keeps
the geocoder volume defensible (decision D11).

The box **echoes how it read the input** before acting on it. That one line is
what stops a transposed coordinate pair or a mistyped code from quietly
resolving somewhere plausible and wrong (doc/08-ui-ux.md §2).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import reflex as rx

from ..services import geocode, municipios
from ..services.geocode import GeocodeError

logger = logging.getLogger(__name__)


class SearchMixin(rx.State, mixin=True):
    """What the user typed, how it was read, and what came back."""

    query: str = ""
    #: Human-readable "read as …", shown before anything happens.
    echo: str = ""
    echo_kind: str = ""
    search_error: str = ""
    searching_place: bool = False

    #: Município candidates (local, instant) and place candidates (geocoded).
    municipio_hits: List[Dict[str, Any]] = []
    place_hits: List[Dict[str, Any]] = []

    @rx.var
    def has_results(self) -> bool:
        return bool(self.municipio_hits or self.place_hits or self.candidates)

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
            self.echo = resolution.echo
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
            return type(self).search_by_code

        if kind == "coordenada":
            coord = resolution.payload
            return type(self).select_at_point(coord.lat, coord.lon)

        if kind == "municipio":
            async with self:
                self.municipio_hits = resolution.payload
            # A single unambiguous hit goes straight there; several are offered.
            if len(resolution.payload) == 1:
                return type(self).choose_municipio(
                    resolution.payload[0]["cod_municipio_ibge"]
                )
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
                self.search_error = (
                    f"Nenhum lugar encontrado para “{raw}”. Tente um município, "
                    "uma coordenada ou um código CAR."
                )
            self.place_hits = [
                {
                    "label": p.label,
                    "lat": p.lat,
                    "lon": p.lon,
                    "bounds": p.bounds or [],
                }
                for p in places
            ]

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

        return type(self).load_municipio_list

    @rx.event
    def choose_place(self, index: int) -> None:
        """Frame the map on a geocoded place. **Selects no property.**"""
        try:
            place = self.place_hits[int(index)]
        except (IndexError, ValueError, TypeError):
            return
        self.place_hits = []
        if place.get("bounds"):
            # A bbox is honest about uncertainty in a way a single pin is not.
            self.fit_bounds = place["bounds"]
        else:
            self.center = [place["lat"], place["lon"]]
            self.zoom = 13
        self.query = place["label"]
        self.echo = "lugar — clique no mapa para escolher um imóvel"
        self.echo_kind = "lugar"

    @rx.event
    def clear_search(self) -> None:
        self.query = ""
        self.echo = ""
        self.echo_kind = ""
        self.search_error = ""
        self.municipio_hits = []
        self.place_hits = []
