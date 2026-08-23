"""SPOT 2008 coverage and dates — opt-in, hits Earth Engine.

These pin the *shape* of the finding in doc/12 §3, not exact percentages: the
point is to catch the mosaic silently becoming uniform, or the `date` band
changing units, either of which would quietly invalidate the pre-cutoff figure
the UI reports.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.live


def _box(lon, lat, d=0.05):
    return {"type": "Polygon", "coordinates": [[
        [lon - d, lat - d], [lon + d, lat - d],
        [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d],
    ]]}


def test_test_property_neighbourhood_is_pre_cutoff():
    from camposcope.services import spot

    summary, prov = spot.coverage(_box(-55.4977, -12.4979))
    assert summary["has_coverage"]
    assert summary["date_min"].startswith("2008")
    assert summary["pre_cutoff_pct"] == 100.0
    assert prov.dataset_id == spot.VISUAL_ASSET


def test_coverage_is_not_uniform_across_brazil():
    """The catalogue says "forest areas"; the reality is patchier than that, and
    the UI depends on being able to say so."""
    from camposcope.services import spot

    pantanal, _ = spot.coverage(_box(-56.5, -19.0))
    assert pantanal["covered_pct"] == 0.0
    assert pantanal["has_coverage"] is False
    assert pantanal["date_min"] is None


def test_some_regions_are_imaged_after_the_cutoff():
    """Litoral SP was imaged in October 2008 — after 22 July. Presenting that as
    the reference date would be wrong, which is the whole reason for doc/12 §3."""
    from camposcope.services import spot

    summary, _ = spot.coverage(_box(-46.3, -23.9))
    assert summary["has_coverage"]
    assert summary["pre_cutoff_pct"] == 0.0


def test_no_coverage_is_recorded_in_provenance():
    from camposcope.services import spot

    _, prov = spot.coverage(_box(-56.5, -19.0))
    assert any("cobertura" in n.lower() for n in prov.notes)
