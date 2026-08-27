"""UI chrome state: language, panel visibility, header dialogs.

The Canada-page counterpart of ``camposcope/state/_ui.py``. Same shape as
Naturametrics' ``canada/state/_ui.py``, which this project's CLAUDE.md documents
as the pattern to follow: ``?lang=`` carries the language between the two pages
of this app, and the default here is English rather than the app-wide
Portuguese, because the ACI/VLCE2/NTEMS vocabulary is English-sourced the way
the CAR's is Portuguese-sourced.
"""

from __future__ import annotations

import reflex as rx

from ..config.settings import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES
from ..translations import get_translations


class CanadaUIMixin(rx.State, mixin=True):
    """Presentation state with no analytical meaning."""

    language: str = DEFAULT_LANGUAGE

    #: Mobile overlay drawer only; the desktop sidebar is always visible.
    sidebar_open: bool = False

    results_tab: str = "cobertura"

    #: The header's dialogs, fully controlled — Dialog.Close's Radix "asChild"
    #: prop-cloning never reaches a button Reflex has extracted into its own
    #: standalone helper component (same trap ``camposcope/state/_ui.py``
    #: documents), so the close buttons drive this state directly instead.
    help_open: bool = False
    cite_open: bool = False
    export_open: bool = False

    #: One transient message, for anything that is not its own dedicated error
    #: field — same role as the Brazil page's ``toast``.
    toast: str = ""

    def set_language(self, lang: str | list[str]) -> None:
        raw = lang[0] if isinstance(lang, (list, tuple)) and lang else lang
        if raw in SUPPORTED_LANGUAGES:
            self.language = raw

    def adopt_lang_param(self) -> None:
        """Honour ``?lang=`` on page load.

        Absent or unrecognised, the page keeps its own English default rather
        than the app-wide Portuguese one — arriving bare at ``/canada`` reads
        as English, exactly as arriving bare at ``/`` reads as Portuguese.
        """
        requested = (self.router.page.params or {}).get("lang")
        if requested in SUPPORTED_LANGUAGES:
            self.language = requested

    def toggle_sidebar(self) -> None:
        self.sidebar_open = not self.sidebar_open

    def set_results_tab(self, tab: str) -> None:
        self.results_tab = tab
        return self.__class__.mint_analysis_layer

    def set_help_open(self, value: bool) -> None:
        self.help_open = value

    def set_cite_open(self, value: bool) -> None:
        self.cite_open = value

    def set_export_open(self, value: bool) -> None:
        self.export_open = value

    def dismiss_toast(self) -> None:
        self.toast = ""

    @rx.var(cache=True)
    def tr(self) -> dict[str, str]:
        return get_translations(self.language)

    @rx.var
    def brazil_href(self) -> str:
        """Link back to the Brazil page, carrying the current language."""
        return f"/?lang={self.language}"
