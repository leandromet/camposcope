"""Address search (services/address.py) and the quick-start/how-to wiring."""

from __future__ import annotations

import pytest

from camposcope.services import address
from camposcope.services import geocode as br
from camposcope.canada.services import geocode as ca


# --------------------------------------------------------------------------- #
# Recognisers
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text,digits", [
    ("78890-000", "78890000"),
    ("78890000", "78890000"),
    ("78.890-000", "78890000"),
    ("CEP 01310-100", "01310100"),
    (" cep: 01310100 ", "01310100"),
])
def test_cep_formats(text, digits):
    assert address.parse_cep(text) == digits


@pytest.mark.parametrize("text", ["12345", "7889-0000", "-12.5, -55.7", "Sorriso",
                                  "123456789"])
def test_not_a_cep(text):
    assert address.parse_cep(text) is None


@pytest.mark.parametrize("text,code", [
    ("V1Y 2B3", "V1Y 2B3"), ("v1y2b3", "V1Y 2B3"), ("K1A-0A6", "K1A 0A6"),
])
def test_ca_postal_formats(text, code):
    assert address.parse_ca_postal(text) == code


@pytest.mark.parametrize("text", ["Hello1", "W1Y 2B3", "V1D 2B3", "D1Y 2B3",
                                  "Kelowna", "49.88, -119.49"])
def test_not_a_ca_postal(text):
    """W/Z never start a code; D/F/I/O/Q/U never appear — so neither a word
    nor a coordinate can ever read as one."""
    assert address.parse_ca_postal(text) is None


def test_street_address_heuristic():
    assert address.looks_like_street_address("4700 Lakeshore Rd")
    assert address.looks_like_street_address("12B Main St")
    assert not address.looks_like_street_address("Lakeshore Rd 4700")
    assert not address.looks_like_street_address("Kelowna")


# --------------------------------------------------------------------------- #
# Labels and precision
# --------------------------------------------------------------------------- #
_PAULISTA = {
    "lat": "-23.5648865", "lon": "-46.6519180", "category": "place",
    "type": "house", "addresstype": "place", "name": "",
    "display_name": "1000, Avenida Paulista, Morro dos Ingleses, Bela Vista, "
                    "São Paulo, Região Sudeste, 01310-100, Brasil",
    "address": {"house_number": "1000", "road": "Avenida Paulista",
                "suburb": "Morro dos Ingleses", "city": "São Paulo",
                "state": "São Paulo", "ISO3166-2-lvl4": "BR-SP"},
    "boundingbox": ["-23.5649365", "-23.5648365", "-46.6519680", "-46.6518680"],
}


def test_describe_street_address():
    title, subtitle = address.describe(_PAULISTA)
    assert title == "Avenida Paulista, 1000"
    assert subtitle == "Morro dos Ingleses, São Paulo – SP"
    assert address._precision_of(_PAULISTA) == "endereco"


def test_describe_named_place_keeps_its_name():
    item = {"name": "Parque Ibirapuera", "addresstype": "park",
            "address": {"road": "Avenida Pedro Álvares Cabral",
                        "city": "São Paulo", "ISO3166-2-lvl4": "BR-SP"}}
    title, subtitle = address.describe(item)
    assert title == "Parque Ibirapuera"
    assert "São Paulo" in subtitle and subtitle.endswith("SP")


def test_describe_without_address_breakdown():
    title, subtitle = address.describe({"display_name": "Sorriso, Mato Grosso, Brasil"})
    assert title == "Sorriso"
    assert subtitle == "Mato Grosso, Brasil"


def test_town_precision():
    assert address._precision_of({"addresstype": "town"}) == "cidade"
    assert address._precision_of({"addresstype": "postcode"}) == "cep"
    assert address._precision_of({"addresstype": "weird"}) == "lugar"


def test_point_precisions_zoom_in_tighter_than_fit_bounds_cap():
    """fit_bounds is capped at z12 in leaflet_map.js — a point-precision hit
    is only worth pinning if it lands closer than that."""
    for p in address.POINT_PRECISIONS:
        assert address.ZOOM_BY_PRECISION[p] > 12


def test_to_hit_is_plain_and_titled():
    p = address.Place(label="X, Y", lat=1.0, lon=2.0, bounds=None)
    hit = p.to_hit()
    assert hit["bounds"] == [] and hit["title"] == "X, Y"
    assert hit["precision"] == "lugar"


def test_merge_drops_near_duplicates_and_keeps_priority():
    a = address.Place(label="a", lat=49.81, lon=-119.50, bounds=None, source="databc")
    b = address.Place(label="b", lat=49.8101, lon=-119.5001, bounds=None)
    c = address.Place(label="c", lat=50.0, lon=-119.0, bounds=None)
    assert [p.label for p in address.merge([a], [b, c])] == ["a", "c"]


def test_attributions_credit_only_sources_shown():
    hits = [{"attribution": address.OSM_ATTRIBUTION},
            {"attribution": f"{address.OSM_ATTRIBUTION}; {address.VIACEP_ATTRIBUTION}"}]
    text = address.attributions(hits)
    assert text.count("OpenStreetMap") == 1 and "ViaCEP" in text
    assert "British Columbia" not in text
    assert address.attributions([]) == ""


# --------------------------------------------------------------------------- #
# Resolver precedence
# --------------------------------------------------------------------------- #
def test_brazil_cep_is_its_own_kind():
    r = br.resolve("01310-100")
    assert r.kind == "cep" and r.payload == "01310100"


def test_brazil_street_address_reaches_the_geocoder():
    assert br.resolve("Avenida Paulista 1000, São Paulo").kind == "lugar"


def test_canada_postal_is_its_own_kind():
    r = ca.resolve("v1y2b3")
    assert r.kind == "postal" and r.payload == "V1Y 2B3"


def test_canada_pid_still_wins():
    assert ca.resolve("010-322-060").kind == "pid"


# --------------------------------------------------------------------------- #
# Quick start + how-to: every key the components read exists in every language
# --------------------------------------------------------------------------- #
_QS_KEYS = ["qs_title", "qs_more", "qs_got_it", "qs_full_howto", "qs_close_aria",
            "help_show_quickstart", "search_as_place", "search_place_hint",
            *[f"qs_step{n}_{part}" for n in range(1, 5) for part in ("lead", "body")],
            *[f"precision_{p}" for p in address.ZOOM_BY_PRECISION]]


@pytest.mark.parametrize("lang", ["pt", "en"])
def test_brazil_quickstart_and_help_keys(lang):
    from camposcope.components.help import HELP_STEPS
    from camposcope.translations import TRANSLATIONS

    keys = _QS_KEYS + ["echo_cep", "erro_cep_nao_encontrado", "help_close",
                       *[f"help_step{n}_{p}" for n in range(1, HELP_STEPS + 1)
                         for p in ("title", "body")]]
    missing = [k for k in keys if k not in TRANSLATIONS[lang]]
    assert not missing


@pytest.mark.parametrize("lang", ["pt", "en"])
def test_canada_quickstart_keys(lang):
    from camposcope.canada.translations import TRANSLATIONS

    keys = _QS_KEYS + ["echo_postal", "erro_postal_nao_encontrado"]
    missing = [k for k in keys if k not in TRANSLATIONS[lang]]
    assert not missing


# --------------------------------------------------------------------------- #
# Live
# --------------------------------------------------------------------------- #
@pytest.mark.live
def test_live_cep_is_labelled_with_its_street():
    places, info = br.search_cep("01310100")
    assert places and places[0].title.startswith("CEP 01310-100 — Avenida Paulista")
    assert info and info["uf"] == "SP"


@pytest.mark.live
def test_live_bc_civic_address_comes_from_the_register():
    places = ca.search_places("4700 Lakeshore Rd, Kelowna")
    assert places[0].source == "databc" and places[0].precision == "endereco"
