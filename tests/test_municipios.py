"""The committed município table (decision D12)."""

from __future__ import annotations

from camposcope.services import municipios


def test_table_is_complete():
    rows = municipios.for_uf("MT")
    assert len(rows) == 142                      # MT has 141 municípios + 1
    assert municipios.by_code(5108501)["nome"] == "Vera"


def test_every_uf_has_municipios():
    from camposcope.config.sicar import UFS

    for uf in UFS:
        assert municipios.for_uf(uf), f"{uf} has no municípios"


def test_search_is_accent_insensitive():
    names = [r["nome"] for r in municipios.search("sao felix")]
    assert any("São Félix" in n for n in names)


def test_search_prefers_prefix_matches():
    """A user typing "cuia" means Cuiabá, not something containing "cuia"."""
    first = municipios.search("cuiab")[0]
    assert first["nome"] == "Cuiabá"


def test_search_accepts_a_uf_suffix():
    rows = municipios.search("vera/MT")
    assert rows[0]["nome"] == "Vera"
    assert all(r["uf"] == "MT" for r in rows)


def test_search_empty_is_empty():
    assert municipios.search("") == []
