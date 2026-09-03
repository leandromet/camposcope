"""Canada page state.

``CanadaState`` is a separate root state, not a mixin added to the Brazil
page's ``AppState`` — same reasoning as Naturametrics' Canada page (see this
project's CLAUDE.md): the two pages disagree about almost every var, from the
year range to what a zone even is, and sharing a root would mean every var
carrying a "which country" qualifier.

The one thing genuinely shared — the chosen UI language — is handled by
``CanadaUIMixin`` reading a query parameter, so the link between the pages
carries the language and nothing else does.

Same rule as the Brazil state: never store ``ee.Geometry`` or ``ee.Image`` in a
state var. State holds GeoJSON dicts and plain values; Earth Engine objects are
rebuilt inside service functions.
"""

from __future__ import annotations

import reflex as rx

from ._biomass import CanadaBiomassMixin
from ._cover import CanadaCoverMixin
from ._export import CanadaExportMixin
from ._fire import CanadaFireMixin
from ._forest import CanadaForestMixin
from ._gbif import CanadaGbifMixin
from ._landscape import CanadaLandscapeMixin
from ._layers import CanadaLayersMixin
from ._parcel import CanadaParcelMixin
from ._transitions import CanadaTransitionsMixin
from ._ui import CanadaUIMixin
from ._validation import CanadaValidationMixin


class CanadaState(CanadaParcelMixin, CanadaLayersMixin, CanadaCoverMixin,
                  CanadaTransitionsMixin, CanadaForestMixin, CanadaBiomassMixin,
                  CanadaFireMixin, CanadaLandscapeMixin, CanadaValidationMixin,
                  CanadaGbifMixin, CanadaExportMixin, CanadaUIMixin, rx.State):
    """Root state for the ``/canada`` route."""

    @rx.event
    def on_load(self):
        """Adopt ``?lang=`` and ``?pid=`` from the URL."""
        self.adopt_lang_param()
        return CanadaState.adopt_pid_param


__all__ = ["CanadaState"]
