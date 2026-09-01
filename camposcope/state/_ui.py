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
    #: The on-map legend (components/map_legend.py) collapsed to just its
    #: header. Open by default; `adopt_viewport` below closes it on a narrow
    #: screen before the first paint the user sees.
    legend_open: bool = True
    #: Whether `adopt_viewport` has already run for this session. The legend
    #: is conditionally rendered (it appears with the first selected
    #: property), so its `on_mount` fires again on every remount — without
    #: this guard a phone user who opened the legend would have it snap shut
    #: again the next time it re-rendered.
    _viewport_adopted: bool = False
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
    def toggle_legend(self) -> None:
        self.legend_open = not self.legend_open

    @rx.event
    def adopt_viewport(self, narrow: bool) -> None:
        """Collapse the legend on a phone, once per session.

        The default has to differ by screen size — on a desktop map the legend
        is a small box in a large corner, on a phone it is a slab over a third
        of the only map there is — and a Reflex state default is a single
        Python value that knows nothing about the client. Radix's `display`
        breakpoints cannot express it either: this is one boolean feeding
        `rx.cond`, not two variants to show and hide. So the viewport is asked
        once, from the browser, via `rx.call_script(..., callback=...)` — see
        `components/map_legend.py::map_legend`.

        Only ever collapses. A wide viewport leaves the default alone, so
        this can never fight a user who opened the legend themselves.
        """
        if self._viewport_adopted:
            return
        self._viewport_adopted = True
        if narrow:
            self.legend_open = False

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
