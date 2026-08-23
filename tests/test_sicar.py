"""SICAR client — validation happens locally, before any request is made."""

from __future__ import annotations

import pytest

from camposcope.config import sicar as vocab


def test_layer_names_match_the_published_ones():
    assert vocab.layer_for_uf("MT") == "sicar:sicar_imoveis_mt"
    assert vocab.layer_for_uf("df") == "sicar:sicar_imoveis_df"
    assert len(vocab.UFS) == 27


def test_unknown_uf_is_refused_rather_than_404ed():
    with pytest.raises(ValueError):
        vocab.layer_for_uf("XX")


def test_cod_imovel_parses():
    uf, ibge, digest = vocab.parse_cod_imovel(
        "mt-5108501-cbe0f5edd27a4d7888e7392ea7d44793"
    )
    assert (uf, ibge) == ("MT", 5108501)
    assert len(digest) == 32


@pytest.mark.parametrize("bad", ["", "MT-123-abc", "ZZ-5108501-" + "A" * 32,
                                 "MT-5108501-" + "A" * 31])
def test_bad_codes_fail_before_any_network_call(bad):
    with pytest.raises(ValueError):
        vocab.parse_cod_imovel(bad)


def test_geometry_column_is_the_published_name():
    # Not `the_geom` — every spatial predicate depends on this.
    assert vocab.GEOM_COLUMN == "geo_area_imovel"


def test_geoserver_session_uses_tls_12():
    from camposcope.services import sicar

    session = sicar.get_session()
    context = session.get_adapter("https://").poolmanager.connection_pool_kw[
        "ssl_context"
    ]
    assert context.minimum_version == context.maximum_version


@pytest.mark.live
def test_live_lookup():
    from camposcope.services import sicar

    record = sicar.by_code("MT-5108501-CBE0F5EDD27A4D7888E7392EA7D44793")
    assert record.municipio == "Vera"
    assert record.uf == "MT"
    assert record.geometry["type"] == "MultiPolygon"


@pytest.mark.live
def test_live_overlap_is_normal():
    """The first point probed during design was covered by two registrations."""
    from camposcope.services import sicar

    found = sicar.at_point(-12.5, -55.5, "MT")
    assert len(found) >= 2, "expected overlapping registrations at this point"
