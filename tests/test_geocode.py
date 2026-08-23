"""The unified resolver (doc/11-search-and-navigation.md §2, §3)."""

from __future__ import annotations

import pytest

from camposcope.services import geocode


# --------------------------------------------------------------------------- #
# Coordinates
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text,source", [
    ("-12.4979, -55.4977", "decimal"),
    ("-12.4979 -55.4977", "decimal"),
    ("-12,4979 -55,4977", "decimal"),          # pt-BR decimal comma
    ("12°29'52.5\"S 55°29'51.9\"W", "dms"),
    ("12 29 52.5 S, 55 29 51.9 W", "dms"),
    ("https://www.google.com/maps/@-12.4979,-55.4977,15z", "gmaps"),
    ("https://maps.google.com/?q=-12.4979,-55.4977", "gmaps"),
])
def test_coordinate_formats(text, source):
    coord = geocode.parse_coordinates(text)
    assert coord is not None, text
    assert coord.source == source
    assert coord.lat == pytest.approx(-12.4979, abs=1e-3)
    assert coord.lon == pytest.approx(-55.4977, abs=1e-3)


def test_latitude_comes_first():
    coord = geocode.parse_coordinates("-12.4979, -55.4977")
    assert coord.lat < 0 and abs(coord.lat) < abs(coord.lon)


def test_transposed_pair_is_named_not_silently_resolved():
    """A swapped pair lands in the South Atlantic; "no property here" would be
    a terrible answer to a transposition."""
    with pytest.raises(ValueError, match="invertidos"):
        geocode.parse_coordinates("-55.5, -12.5")


def test_outside_brazil_says_which_value_is_wrong():
    with pytest.raises(ValueError) as exc:
        geocode.parse_coordinates("10.0, 10.0")
    assert "latitude" in str(exc.value) and "longitude" in str(exc.value)


def test_non_coordinate_returns_none_rather_than_raising():
    # Not an error — it just means the next resolver should try.
    assert geocode.parse_coordinates("Sinop") is None
    assert geocode.parse_coordinates("") is None


# --------------------------------------------------------------------------- #
# Resolver precedence
# --------------------------------------------------------------------------- #
def test_precedence_code_before_everything():
    r = geocode.resolve("MT-5108501-CBE0F5EDD27A4D7888E7392EA7D44793")
    assert r.kind == "codigo"


def test_precedence_coordinate_before_place():
    assert geocode.resolve("-12.4979, -55.4977").kind == "coordenada"


def test_precedence_municipio_before_place():
    """"Sinop" is a município, so it must never reach the geocoder."""
    r = geocode.resolve("Sinop")
    assert r.kind == "municipio"


def test_unknown_text_falls_through_to_place():
    r = geocode.resolve("Fazenda Santa Luzia do Norte")
    assert r.kind == "lugar"


def test_empty_input_is_not_a_search():
    assert geocode.resolve("   ").kind == "vazio"


def test_resolve_performs_no_network_call():
    """resolve() classifies; the caller acts. That is what keeps the echo line
    honest — the UI shows how the input was read before a request goes out."""
    r = geocode.resolve("Fazenda Que Nao Existe Em Lugar Nenhum")
    assert r.kind == "lugar"
    assert r.payload == "Fazenda Que Nao Existe Em Lugar Nenhum"


@pytest.mark.live
def test_live_place_search():
    places = geocode.search_places("Vera, Mato Grosso", limit=3)
    assert places
    assert places[0].bounds is not None
    assert -20 < places[0].lat < -5
