"""Choosing another property must forget the previous one's results (doc/13 §1).

Regression: every tab but Cobertura is computed on demand, and each cleared
only its own fields when re-run — so after switching property the previous
property's Hansen/biomass/fire/landscape/validation/Sankey/SPOT/GBIF numbers
stayed in state and the ODS/HTML exports shipped them under the new
property's identity (a C3/C4 failure: numbers attributed to the wrong CAR).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from camposcope.state._imovel import PROPERTY_RESULT_DEFAULTS, ImovelMixin  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent / "camposcope"


def _method(src: str, header: str) -> str:
    """The source of one method: from its header to the next def/decorator
    at the same indentation, or the end of the file."""
    body = src[src.index(header):]
    m = re.search(r"\n    (?:def |async def |@)", body[len(header):])
    return body if m is None else body[:len(header) + m.start()]


def test_every_cleared_field_exists_on_the_state():
    from camposcope.state import AppState
    fields = set(AppState.backend_vars) | set(AppState.base_vars)
    missing = [f for f in PROPERTY_RESULT_DEFAULTS if f not in fields]
    assert not missing, f"not state fields (typo?): {missing}"


def test_every_exported_result_is_cleared():
    """Whatever _gather() hands to the exports, apart from the property's own
    identity/zones and Cobertura (run_history is always chained on adopt),
    must be in the clear list — a new tab added to _gather but not here would
    reintroduce the bug."""
    src = (ROOT / "state" / "_export.py").read_text()
    body = _method(src, "def _gather")
    gathered = set(re.findall(r"self\.([a-z_]+)", body))
    exempt = {"imovel", "zones", "history_rows", "history_provenance",
              "sankey_year_a", "sankey_year_b",
              # The property's own geometry facts, not tab results: rebuilt
              # (and the overlaps reset) by ZonesMixin.build_zones, which
              # both adopt paths call right after clearing (see below).
              "overlaps", "overlaps_checked", "area_calculada_ha",
              "area_delta_ha", "area_delta_pct"}
    missing = sorted(gathered - exempt - set(PROPERTY_RESULT_DEFAULTS))
    assert not missing, f"exported but never cleared on property change: {missing}"


def test_clear_resets_to_fresh_empty_values():
    stale = SimpleNamespace(**{k: ["old"] if isinstance(v, list) else "old"
                               for k, v in PROPERTY_RESULT_DEFAULTS.items()})
    ImovelMixin._clear_property_results(stale)
    for k, v in PROPERTY_RESULT_DEFAULTS.items():
        assert getattr(stale, k) == v
    a, b = SimpleNamespace(), SimpleNamespace()
    ImovelMixin._clear_property_results(a)
    ImovelMixin._clear_property_results(b)
    assert a.fire_rows is not b.fire_rows  # no shared mutable default


def test_both_adopt_paths_clear_before_building_zones():
    src = (ROOT / "state" / "_imovel.py").read_text()
    for name in ("def _adopt(", "def _adopt_square("):
        body = _method(src, name)
        assert "self._clear_property_results()" in body, name
        assert body.index("self._clear_property_results()") < body.index(
            "self.build_zones()"), name


def test_build_zones_forgets_the_previous_overlaps():
    """overlaps/overlaps_checked are exempt above because build_zones owns
    them: it must reset them before anything else, or the report would list
    (or claim "none found" for) the previous property's overlaps."""
    src = (ROOT / "state" / "_zones.py").read_text()
    body = _method(src, "def build_zones")
    head = body[:body.index("if not geojson")]
    assert "self.overlaps = []" in head and "self.overlaps_checked = False" in head
