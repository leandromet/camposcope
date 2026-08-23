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
