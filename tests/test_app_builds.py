"""The app imports and compiles.

This test exists because of a specific, expensive failure mode: a Reflex
**event-handler signature mismatch is a build-time error that kills the backend
worker**, while the frontend keeps serving. The symptom is a grey map and a
failed WebSocket, which looks nothing like a type error. Naturametrics lost hours
to it; the test is cheap (doc/09-dev-environment.md §6).
"""

from __future__ import annotations


def test_app_imports():
    from camposcope.camposcope import app
    assert app is not None


def test_state_composes():
    from camposcope.state import AppState

    for var in ("imovel", "zones", "map_layers", "lang", "basemap"):
        assert hasattr(AppState, var), f"AppState is missing {var}"


def test_index_renders():
    """Building the component tree is what catches handler mismatches."""
    from camposcope.pages.index import index

    assert index() is not None


def test_background_handlers_never_reference_type_self():
    """Regression test for a real bug: inside an `@rx.event(background=True)`
    handler, `self` is a `StateProxy` (a wrapt object proxy). `type(self)`
    returns the proxy's own class, so `return type(self).other_handler` raises
    `AttributeError: 'StateProxy' has no attribute ...` at runtime — a failure
    this repo's default test suite (no live server) cannot otherwise catch,
    since it only shows up when a background handler actually chains to
    another event. `self.__class__` is proxied through to the real composed
    state and is the correct spelling. See camposcope/state/_imovel.py and
    _search.py for the fix and its explanation.
    """
    import pathlib
    import re

    state_dir = pathlib.Path(__file__).resolve().parent.parent / "camposcope" / "state"
    offenders = []
    for path in state_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            code = line.split("#", 1)[0]        # ignore comments and docstrings
            if re.search(r"\btype\(self\)\.", code):
                offenders.append(f"{path.name}:{i}: {line.strip()}")

    assert not offenders, "found `type(self).<handler>` — use `self.__class__` instead:\n" + "\n".join(offenders)
