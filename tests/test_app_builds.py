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


def test_every_adopt_call_site_triggers_run_history():
    """Regression test for a real bug: three call sites in `_imovel.py` call
    `self._adopt(record)` to select a property, and only two of them chained
    `return self.__class__.run_history` afterward. The third —
    `select_at_point`'s single-match branch, i.e. clicking the map when
    exactly one registration covers the point — silently left the MapBiomas
    trajectory job never triggered: the cadastral card and zones rendered
    fine (they come from `_adopt` itself), but the Cobertura tab stayed on
    its "select a property" placeholder forever, with no error shown, because
    nothing was running and nothing had failed.

    This greps the source rather than driving the UI because the failure mode
    is a MISSING call, which a HTTP/websocket-level test would only catch by
    asserting on data that never arrives — the same gap that let this ship.
    """
    import pathlib
    import re

    src = (pathlib.Path(__file__).resolve().parent.parent
           / "camposcope" / "state" / "_imovel.py").read_text(encoding="utf-8")

    # One block per call site: from `self._adopt(` to the next `@rx.event`
    # (the start of the next handler) or end of file — the rest of THIS
    # handler, not a fixed character count, so a long explanatory comment
    # between the call and its `run_history` trigger can't produce a false
    # failure here (it did: this window used to be a flat 400 chars, and
    # this file's own comments routinely run longer than that).
    adopt_positions = [m.start() for m in re.finditer(r"self\._adopt\(", src)]
    assert adopt_positions, "no self._adopt( call sites found — did _adopt get renamed?"
    event_positions = [m.start() for m in re.finditer(r"@rx\.event", src)]

    for pos in adopt_positions:
        later_events = [e for e in event_positions if e > pos]
        end = min(later_events) if later_events else len(src)
        window = src[pos:end]
        assert "run_history" in window, (
            f"a self._adopt(...) call near offset {pos} in _imovel.py has no "
            "run_history trigger before the next handler — the MapBiomas "
            "trajectory will never run for this path. Add "
            "`return self.__class__.run_history` after the `async with self:` "
            "block that calls _adopt."
        )


def test_background_handlers_never_write_state_outside_async_with():
    """Regression test for a real bug: `set_spot_band_mode` (and
    `set_validacao_mode`, same commit) were declared
    `@rx.event(background=True)` and wrote `self.spot_band_mode = value`
    directly, one indent level OUTSIDE the function's `async with self:`
    block. Inside a background handler `self` is a `StateProxy` that only
    allows mutation while inside that context manager — the app compiled and
    every other test passed, but the handler raised
    `ImmutableStateError: Background task StateProxy is immutable outside of
    a context manager` the first time a user actually clicked the control.

    This is a runtime-only failure with no static type signal, so it cannot
    be caught by test_index_renders (which only builds the component tree,
    never fires an event) — it has to be caught by reading the source shape
    directly. The two handlers turned out not to need `background=True` at
    all: matching sibling setters (`set_hansen_layer_mode` et al.) are plain
    `@rx.event` and chain `mint_analysis_layer` (itself background) just
    fine by returning it, which is the fix that was applied.

    The check: for every `@rx.event(background=True)` method, no
    `self.<name> = ` assignment line may sit at an indentation level at or
    shallower than the nearest preceding `async with self:` line — that
    shape means the assignment fell outside the block.
    """
    import pathlib
    import re

    state_dir = pathlib.Path(__file__).resolve().parent.parent / "camposcope" / "state"
    assign_re = re.compile(r"^(\s*)self\.\w+\s*=(?!=)")
    with_re = re.compile(r"^(\s*)async with self:\s*$")
    decorator_re = re.compile(r"^(\s*)@rx\.event\(background=True\)\s*$")
    def_re = re.compile(r"^(\s*)(async )?def (\w+)\(")

    offenders = []
    for path in sorted(state_dir.glob("*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        i = 0
        while i < len(lines):
            m = decorator_re.match(lines[i])
            if not m:
                i += 1
                continue
            # Found a background handler's decorator; find its def line and
            # then walk the function body until dedent back to def's indent.
            j = i + 1
            while j < len(lines) and not def_re.match(lines[j]):
                j += 1
            if j >= len(lines):
                break
            def_indent = len(def_re.match(lines[j]).group(1))
            func_name = def_re.match(lines[j]).group(3)
            body_start = j + 1
            k = body_start
            with_indent = None  # indentation of the innermost open `async with self:`
            while k < len(lines):
                line = lines[k]
                stripped = line.strip()
                if stripped:
                    indent = len(line) - len(line.lstrip())
                    if indent <= def_indent:
                        break  # dedented out of the function
                    wm = with_re.match(line)
                    if wm:
                        with_indent = len(wm.group(1))
                    else:
                        am = assign_re.match(line)
                        if am:
                            assign_indent = len(am.group(1))
                            if with_indent is None or assign_indent <= with_indent:
                                offenders.append(
                                    f"{path.name}:{k + 1}: {func_name}(): "
                                    f"{stripped}"
                                )
                        # Leaving the with-block's body dedents back to (or
                        # below) with_indent; a non-with line at exactly
                        # with_indent means the block ended.
                        if (with_indent is not None
                                and indent <= with_indent and not wm):
                            with_indent = None
                k += 1
            i = k

    assert not offenders, (
        "background event handler(s) assign to self.<attr> outside their "
        "`async with self:` block — this raises ImmutableStateError at "
        "runtime, the first time the handler actually fires:\n"
        + "\n".join(offenders)
    )
