"""Application state.

``AppState`` is assembled from mixins, one per coherent slice
(doc/02-architecture.md §5) — the pattern Yvynation arrived at and Naturametrics
kept. Mixins are ``rx.State, mixin=True`` and own no state at class level.

**Rule:** never store ``ee.Geometry`` or ``ee.Image`` in a state var — they are
not serialisable (constraint C2). State holds GeoJSON dicts and plain values;
Earth Engine objects are rebuilt inside service functions.
"""

from __future__ import annotations

import reflex as rx

from ._analysis import (
    AnalysisMixin, BiomassMixin, FireMixin, ForestChangeMixin, SpotCoverageMixin,
    ValidacaoMixin,
)
from ._imovel import ImovelMixin
from ._layers import LayersMixin
from ._search import SearchMixin
from ._transitions import TransitionsMixin
from ._ui import UIMixin
from ._zones import ZonesMixin


class AppState(SearchMixin, ImovelMixin, ZonesMixin, LayersMixin, AnalysisMixin,
               ForestChangeMixin, BiomassMixin, FireMixin, SpotCoverageMixin,
               ValidacaoMixin, TransitionsMixin, UIMixin, rx.State):
    """Root application state."""

    @rx.event
    def on_load(self):
        """Adopt ``?lang=`` and ``?car=`` from the URL."""
        self.adopt_lang_param()
        return AppState.adopt_car_param


__all__ = ["AppState"]
