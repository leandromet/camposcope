"""Regression tests for the swipe-comparison layer cache (state/_layers.py).

``AppState`` is instantiated with Reflex's own internal escape hatch
(``_reflex_internal_init=True``) — the same one the framework's own test
suite uses to unit-test state logic without a running app/session.
"""

from __future__ import annotations

from camposcope.state import AppState


def _fresh_state() -> AppState:
    return AppState(_reflex_internal_init=True)


def test_swipe_clip_is_read_from_key_position_not_cached_spec():
    """Regression test for a real bug: a tile is identified by its content
    (e.g. ``"mapbiomas:v10_1:2008"``), and that SAME key can legitimately be
    the left side of one comparison (Transições, if 2008 is one of the two
    chosen years) and the right side of another (Validação's SPOT×2008
    pairing) — the cache in ``analysis_layer_specs`` is shared across every
    tab that can mint that tile.

    The fix used to bake ``"clip": "left"/"right"`` INTO the cached spec dict
    at mint time. That meant whichever side a tile was FIRST minted on stuck
    forever: reproduced by visiting Transições with 2008 as one of the two
    years (caching it with clip=left, say), then Validação's SPOT×2008 mode
    (which wants that same tile on the RIGHT) — the stale cached clip="left"
    survived, so the "left" side of the NEW comparison never actually showed
    up, exactly the "fails to replace the left layer, depending on the order
    I navigate" bug report.

    This test plants a spec in the cache with the OPPOSITE clip value baked
    in (simulating exactly that stale state) and asserts `map_layers`
    ignores it, deriving `clip` fresh from the key's position in
    `swipe_layer_keys` instead.
    """
    s = _fresh_state()
    s.analysis_layer_enabled = True
    s.swipe_layer_keys = ["mapbiomas:v10_1:2008", "basemap:spot_2008_visual"]
    s.analysis_layer_specs = {
        # Poisoned: this spec was (hypothetically) cached by an EARLIER visit
        # to Transições where this same tile sat on the LEFT. It is now
        # requested as the RIGHT side of a different pairing.
        "mapbiomas:v10_1:2008": {
            "url": "https://example/mb2008", "opacity": 1.0,
            "attribution": "MapBiomas", "max_native_zoom": 15,
            "clip": "left",   # stale — must be overridden, not trusted
        },
        "basemap:spot_2008_visual": {
            "url": "https://example/spot", "opacity": 1.0,
            "attribution": "SPOT", "max_native_zoom": 16,
        },
    }

    layers = {l["id"]: l for l in s.map_layers}

    assert layers["swipe:mapbiomas:v10_1:2008"]["clip"] == "left"
    assert layers["swipe:basemap:spot_2008_visual"]["clip"] == "right"


def test_swipe_clip_flips_when_key_order_flips():
    """The same two tiles, opposite roles — as happens switching from
    Transições (older year left) to a Validação pairing where the SAME
    MapBiomas year is now the right-hand reference. `map_layers` must answer
    correctly both ways, from `swipe_layer_keys`' order alone."""
    s = _fresh_state()
    s.analysis_layer_enabled = True
    s.analysis_layer_specs = {
        "x": {"url": "u1", "opacity": 1.0, "attribution": "", "max_native_zoom": 10},
        "y": {"url": "u2", "opacity": 1.0, "attribution": "", "max_native_zoom": 10},
    }

    s.swipe_layer_keys = ["x", "y"]
    layers = {l["id"]: l for l in s.map_layers}
    assert layers["swipe:x"]["clip"] == "left"
    assert layers["swipe:y"]["clip"] == "right"

    s.swipe_layer_keys = ["y", "x"]
    layers = {l["id"]: l for l in s.map_layers}
    assert layers["swipe:y"]["clip"] == "left"
    assert layers["swipe:x"]["clip"] == "right"


def test_no_swipe_layers_when_analysis_layer_disabled():
    s = _fresh_state()
    s.analysis_layer_enabled = False
    s.swipe_layer_keys = ["x", "y"]
    s.analysis_layer_specs = {
        "x": {"url": "u1", "opacity": 1.0, "attribution": "", "max_native_zoom": 10},
        "y": {"url": "u2", "opacity": 1.0, "attribution": "", "max_native_zoom": 10},
    }
    ids = [l["id"] for l in s.map_layers]
    assert not any(i.startswith("swipe:") for i in ids)
