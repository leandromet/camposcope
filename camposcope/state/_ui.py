"""Panels, tabs, language and toasts."""

from __future__ import annotations

from typing import Dict

import reflex as rx

from ..translations import get_translations


class UIMixin(rx.State, mixin=True):
    """Everything about what is on screen and in which language."""

    lang: str = "pt"
    sidebar_open: bool = True
    results_tab: str = "cobertura"
    #: One transient message. Cadastral and Earth Engine failures each render in
    #: their own place (doc/08-ui-ux.md §6); this is for everything else.
    toast: str = ""

    @rx.var(cache=True)
    def tr(self) -> Dict[str, str]:
        """Static UI text for the current language — every component reads
        labels/buttons/captions through this rather than hardcoding Portuguese
        (translations/__init__.py explains what deliberately stays OUT of this
        table: cadastral fields, dataset vocabulary, zone labels)."""
        return get_translations(self.lang)

    @rx.event
    def set_lang(self, lang: str | list[str]) -> None:
        # rx.segmented_control passes `str | list[str]`: its multi-select mode
        # sends a list. Accepting both is what keeps this a compile-time-valid
        # handler — a signature mismatch here kills the backend worker while the
        # frontend keeps serving (see tests/test_app_builds.py).
        value = lang[0] if isinstance(lang, list) else lang
        self.lang = "en" if value == "en" else "pt"

    @rx.event
    def set_results_tab(self, tab: str) -> None:
        self.results_tab = tab
        # Show the map layer this tab is about (doc/08-ui-ux.md §1) — a no-op
        # via LayersMixin.mint_analysis_layer if nothing is selected yet, or
        # if that tab's layer is already cached from an earlier visit.
        return self.__class__.mint_analysis_layer

    @rx.event
    def toggle_sidebar(self) -> None:
        self.sidebar_open = not self.sidebar_open

    @rx.event
    def dismiss_toast(self) -> None:
        self.toast = ""

    @rx.event
    def adopt_lang_param(self) -> None:
        """Honour ``?lang=en`` on load."""
        value = self.router.url.query_parameters.get("lang", "")
        if value in ("pt", "en"):
            self.lang = value

    @rx.var
    def canada_href(self) -> str:
        """Link to the Canada page, carrying the current language — the
        counterpart of ``canada/state/_ui.py::CanadaUIMixin.brazil_href``."""
        return f"/canada?lang={self.lang}"
