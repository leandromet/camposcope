"""Zone construction: rings are disjoint, areas are real, overlaps are found."""

from __future__ import annotations

import math

from camposcope.services import zones

#: A 1° × 1° box would be enormous; this is roughly 1 km square near Vera/MT,
#: which keeps the numbers checkable by hand.
SQUARE = {
    "type": "Polygon",
    "coordinates": [[
        [-55.500, -12.500], [-55.491, -12.500],
        [-55.491, -12.491], [-55.500, -12.491], [-55.500, -12.500],
    ]],
}


def test_area_is_plausible():
    # ~0.009° ≈ 0.98 km on each side at this latitude → ~97 ha.
    ha = zones.area_ha(SQUARE)
    assert 90 < ha < 105, ha


def test_rings_are_disjoint_and_ordered():
    zs = zones.build_zones(SQUARE, radii_m=(500, 1000))
    assert [z.key for z in zs] == ["imovel", "ring_500m", "ring_1km"]
    assert zs[0].kind == "property"
    assert all(z.kind == "ring" for z in zs[1:])
    # A true ring excludes everything inside it, so each is larger than the
    # property but they do not nest.
    from shapely.geometry import shape
    a, b = shape(zs[1].geojson), shape(zs[2].geojson)
    assert a.intersection(b).area < 1e-12


def test_ring_areas_sum_to_the_buffer():
    """property + ring(500) must equal a 500 m buffer of the property."""
    zs = zones.build_zones(SQUARE, radii_m=(500,))
    total = zs[0].area_ha + zs[1].area_ha

    from shapely.geometry import mapping, shape
    from shapely.ops import transform as shp_transform
    from pyproj import Transformer

    to_utm = Transformer.from_crs(zones.WGS84, zones._utm_crs_for(-55.4955, -12.4955),
                                  always_xy=True).transform
    from_utm = Transformer.from_crs(zones._utm_crs_for(-55.4955, -12.4955), zones.WGS84,
                                    always_xy=True).transform
    buffered = shp_transform(from_utm, shp_transform(to_utm, shape(SQUARE)).buffer(500))
    assert math.isclose(total, zones.area_ha(mapping(buffered)), rel_tol=1e-6)


def test_area_check_flags_a_real_disagreement():
    computed = zones.area_ha(SQUARE)
    assert not zones.check_area(computed, SQUARE).flagged
    assert zones.check_area(computed * 1.5, SQUARE).flagged


def test_overlap_is_reported_with_its_share():
    half = {
        "type": "Polygon",
        "coordinates": [[
            [-55.4955, -12.500], [-55.491, -12.500],
            [-55.491, -12.491], [-55.4955, -12.491], [-55.4955, -12.500],
        ]],
    }
    rows = zones.overlap_areas(SQUARE, [("MT-0000000-" + "A" * 32, half)])
    assert len(rows) == 1
    assert 45 < rows[0]["overlap_pct_do_imovel"] < 55
