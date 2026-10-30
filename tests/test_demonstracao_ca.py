"""The English walkthrough (/walkthrough) on a Kelowna parcel: snapshot and article.

No network: the example is the committed snapshot (scripts/build_demonstracao.py ca),
and the article checks are text checks on reportagem/camposcope_ca.{en.html,js}.
"""

import json
import re
from pathlib import Path

from camposcope.canada.services import demonstracao

ARTIGO = Path(__file__).resolve().parent.parent / "camposcope" / "reportagem"


def _dados():
    return json.loads(demonstracao.ARQUIVO_EXEMPLO.read_text(encoding="utf-8"))


def test_snapshot_is_clean_and_small():
    dados = _dados()
    assert dados["erros"] == {}
    assert demonstracao.ARQUIVO_EXEMPLO.stat().st_size < 120_000
    assert "camadas" not in dados
    assert dados["parcela"]["pid"] == demonstracao.EXEMPLO_PADRAO


def test_land_cover_adds_up_to_each_zone():
    """Pixel count × pixel area must be measured on one grid: when the area came
    from a lat/long grid and the count from the ACI's Albers grid, the 12.1 ha
    parcel summed to 7.8 ha (ee_zones.mean_pixel_area)."""
    dados = _dados()
    h = dados["historico"]
    for z in dados["zonas"]:
        soma = sum(serie[-1] for serie in h["zonas"][z["key"]].values())
        assert abs(soma - z["area_ha"]) / z["area_ha"] < 0.03, (z["key"], soma, z["area_ha"])


def test_every_step_has_a_handler():
    html = (ARTIGO / "camposcope_ca.en.html").read_text(encoding="utf-8")
    js = (ARTIGO / "camposcope_ca.js").read_text(encoding="utf-8")
    passos = re.findall(r'data-passo="([a-z0-9_-]+)"', html)
    assert len(passos) == 11
    assert [p for p in passos if not re.search(rf"\b{re.escape(p)}: function", js)] == []
    assert set(passos) <= set(re.findall(r'id="camada-([a-z0-9_-]+)"', html))
    notas = re.findall(r'data-nota="(\d+)"', html)
    assert sorted(set(notas)) == sorted(set(re.findall(r'id="nota-(\d+)"', html)))


def test_pages_render():
    from camposcope.pages.demonstracao import walkthrough, walkthrough_brasil

    walkthrough().render()
    walkthrough_brasil().render()
