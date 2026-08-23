"""Click → UF routing (decision D5)."""

from __future__ import annotations

import pytest

from camposcope.services.uf_lookup import candidate_ufs, uf_for_point


@pytest.mark.parametrize("lat,lon,expected", [
    (-12.50, -55.50, "MT"),
    (-23.55, -46.63, "SP"),
    (-15.79, -47.88, "DF"),
    (-3.11, -60.02, "AM"),
    (-30.03, -51.23, "RS"),
    (-1.46, -48.49, "PA"),
])
def test_known_points(lat, lon, expected):
    assert uf_for_point(lat, lon) == expected


def test_outside_brazil_is_none():
    assert uf_for_point(0.0, 0.0) is None
    assert uf_for_point(48.86, 2.35) is None


def test_near_a_border_offers_neighbours():
    assert candidate_ufs(-9.0, -55.0)
