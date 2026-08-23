"""Finding a property, and the cadastral record once found.

The three entry gestures of doc/08-ui-ux.md §2 all land here and all produce the
same thing: a selected ``cod_imovel`` and its record. None is privileged.

Constraint **C4** lives in this mixin as much as in the components: nothing here
derives a verdict, a score or a colour from ``condicao`` or ``status_imovel``.
The fields are carried and displayed verbatim.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import reflex as rx

from ..config import sicar as vocab
from ..services import sicar
from ..services.sicar import SicarError

logger = logging.getLogger(__name__)


class ImovelMixin(rx.State, mixin=True):
    """Search state and the selected cadastral record."""

    # --- search ----------------------------------------------------------
    search_mode: str = "codigo"            # "codigo" | "mapa" | "municipio"
    code_input: str = ""
    search_uf: str = "MT"
    search_municipio_ibge: str = ""

    searching: bool = False
    #: A cadastral failure is shown on its own, and never blocks the rest of the
    #: page (doc/08-ui-ux.md §6).
    sicar_error: str = ""

    #: Populated when a click hits more than one registration. Overlapping
    #: registrations are the normal state of a self-declared cadastre, so this
    #: is a first-class UI state, not an error path (decision D7).
    candidates: List[Dict[str, Any]] = []

    # --- the município browser (doc/05 §5.4) ------------------------------
    #: One page of a município's registrations, geometry-less. Geometry arrives
    #: only when a row is chosen, through ``by_code``.
    municipio_list: List[Dict[str, Any]] = []
    municipio_total: int = 0
    municipio_page: int = 0
    municipio_page_size: int = 25
    loading_list: bool = False

    # --- the selected record ---------------------------------------------
    imovel: Dict[str, Any] = {}
    imovel_geojson: Dict[str, Any] = {}

    @rx.var
    def has_imovel(self) -> bool:
        return bool(self.imovel.get("cod_imovel"))

    @rx.var
    def disclosure(self) -> str:
        """The C4 statement. Permanent, non-dismissible, one source of truth."""
        return (vocab.DISCLOSURE_EN if getattr(self, "lang", "pt") == "en"
                else vocab.DISCLOSURE_PT)

    # --- gestures --------------------------------------------------------
    @rx.event
    def set_search_mode(self, mode: str | list[str]) -> None:
        # See UIMixin.set_lang for why this accepts a list too.
        self.search_mode = mode[0] if isinstance(mode, list) else mode
        self.sicar_error = ""
        self.candidates = []

    @rx.event
    def set_code_input(self, value: str) -> None:
        self.code_input = value

    @rx.event
    def set_search_uf(self, uf: str) -> None:
        self.search_uf = uf

    @rx.event(background=True)
    async def search_by_code(self):
        """Gesture 1 — paste a code.

        Validation happens locally first, so a malformed paste fails instantly
        and no request reaches the public service (C5).
        """
        async with self:
            self.sicar_error = ""
            self.candidates = []
            raw = self.code_input.strip()
            if not raw:
                return
            self.searching = True

        try:
            record = sicar.by_code(raw)
        except (ValueError, SicarError) as exc:
            async with self:
                self.searching = False
                self.sicar_error = str(exc)
            return

        async with self:
            self.searching = False
            self._adopt(record)
        return [self.__class__.run_history, self.__class__.mint_analysis_layer]

    @rx.event(background=True)
    async def select_at_point(self, lat: float, lon: float):
        """Gesture 2 — click the map.

        The UF is resolved locally before the query (decision D5): guessing wrong
        returns an empty result that looks exactly like "no property here".
        """
        from ..services.uf_lookup import uf_for_point

        async with self:
            self.sicar_error = ""
            self.candidates = []
            self.searching = True

        uf = uf_for_point(lat, lon)
        if uf is None:
            async with self:
                self.searching = False
                self.sicar_error = (
                    "Este ponto está fora do território brasileiro coberto pelo CAR."
                )
            return

        try:
            found = sicar.at_point(lat, lon, uf)
        except SicarError as exc:
            async with self:
                self.searching = False
                self.sicar_error = str(exc)
            return

        single_match = len(found) == 1
        async with self:
            self.searching = False
            if not found:
                self.sicar_error = (
                    f"Nenhum imóvel registrado no CAR neste ponto ({uf})."
                )
            elif single_match:
                self._adopt(found[0])
            else:
                # More than one registration covers this point. Present them
                # all; never take the first (decision D7).
                self.candidates = [self._summary(i) for i in found]

        if single_match:
            return [self.__class__.run_history, self.__class__.mint_analysis_layer]

    @rx.event(background=True)
    async def choose_candidate(self, cod_imovel: str):
        """Pick one of several overlapping registrations."""
        async with self:
            self.searching = True
            self.candidates = []
        try:
            record = sicar.by_code(cod_imovel)
        except (ValueError, SicarError) as exc:
            async with self:
                self.searching = False
                self.sicar_error = str(exc)
            return
        async with self:
            self.searching = False
            self._adopt(record)
        return [self.__class__.run_history, self.__class__.mint_analysis_layer]

    @rx.var
    def municipio_pages(self) -> int:
        if not self.municipio_total:
            return 0
        return -(-self.municipio_total // self.municipio_page_size)

    @rx.var
    def municipio_page_label(self) -> str:
        if not self.municipio_total:
            return ""
        return f"página {self.municipio_page + 1} de {self.municipio_pages}"

    @rx.event(background=True)
    async def load_municipio_list(self):
        """Fetch one page of a município's registrations.

        Two SICAR calls: a ``resultType=hits`` count (header only, free) and one
        page with the geometry excluded via ``propertyName`` — the difference
        between kilobytes and megabytes (doc/05 §5.4).
        """
        async with self:
            uf = self.search_uf
            code = self.search_municipio_ibge
            page = self.municipio_page
            size = self.municipio_page_size
            self.loading_list = True
            self.sicar_error = ""
        if not (uf and code):
            async with self:
                self.loading_list = False
            return

        try:
            total = sicar.count_in_municipio(uf, int(code))
            rows = sicar.list_in_municipio(
                uf, int(code), page=page, page_size=size
            )
        except (ValueError, SicarError) as exc:
            async with self:
                self.loading_list = False
                self.sicar_error = str(exc)
            return

        async with self:
            self.loading_list = False
            self.municipio_total = total
            self.municipio_list = [self._summary(r) for r in rows]

    @rx.event
    def next_municipio_page(self):
        if self.municipio_page + 1 < self.municipio_pages:
            self.municipio_page += 1
            return self.__class__.load_municipio_list

    @rx.event
    def prev_municipio_page(self):
        if self.municipio_page > 0:
            self.municipio_page -= 1
            return self.__class__.load_municipio_list

    @rx.event
    def adopt_car_param(self) -> None:
        """Honour ``?car=<cod_imovel>`` on load — the whole persistence model."""
        code = self.router.url.query_parameters.get("car", "")
        if code:
            self.code_input = code
            # `self.__class__` — the composed AppState — not the mixin, and not
            # `type(self)`. Inside a background handler `self` is a `StateProxy`
            # (a wrapt object proxy): `type(self)` returns the proxy's own
            # class, but `self.__class__` is proxied through to the real state
            # — which is what Reflex needs to resolve a returned event by class
            # reference (`type(self).search_by_code` raised `AttributeError:
            # 'StateProxy' has no attribute 'search_by_code'` here in testing).
            return self.__class__.search_by_code

    # --- internals -------------------------------------------------------
    @staticmethod
    def _summary(record: sicar.Imovel) -> Dict[str, Any]:
        """What the chooser shows for one candidate — no geometry."""
        return {
            "cod_imovel": record.cod_imovel,
            "area_declarada_ha": record.area_declarada_ha,
            "condicao": record.condicao or "",
            "status_imovel": record.status_imovel,
            "dat_criacao": record.dat_criacao or "",
            "municipio": record.municipio,
        }

    def _adopt(self, record: sicar.Imovel) -> None:
        """Make this record the selected property and rebuild the zones.

        The geometry goes to ``imovel_geojson`` as a plain dict — constraint C2:
        no ``ee.Geometry`` ever reaches state.
        """
        self.imovel = {
            "cod_imovel": record.cod_imovel,
            "uf": record.uf,
            "municipio": record.municipio,
            "cod_municipio_ibge": record.cod_municipio_ibge,
            "area_declarada_ha": record.area_declarada_ha,
            "m_fiscal": record.m_fiscal,
            "tipo_imovel": record.tipo_imovel,
            "status_imovel": record.status_imovel,
            "condicao": record.condicao or "",
            "dat_criacao": record.dat_criacao or "",
            "data_atualizacao": record.data_atualizacao or "",
            "ano_criacao": record.ano_criacao or 0,
            "queried_at": record.queried_at,
        }
        self.imovel_geojson = record.geometry or {}
        self.build_zones()          # provided by ZonesMixin
        # Selecting a new property IS a request to look somewhere else, so this
        # is the one sanctioned viewport move (LayersMixin.frame_geometry).
        # Constraint C1 forbids the map moving for a layer toggle or a year
        # change — not for this.
        self.frame_geometry(self.imovel_geojson)
        self.active_zone = "imovel"
