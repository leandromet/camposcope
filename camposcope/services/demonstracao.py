"""Os números da demonstração em rolagem (``/demonstracao``).

A página de demonstração não tem números próprios: ela pede este pacote à rota
``/_demonstracao/camposcope.json`` e ele é montado pelos mesmos serviços que a
interface usa — SICAR, zonas, MapBiomas, transições, Hansen, biomassa, fogo,
SPOT 2008 e IBGE — para um imóvel de exemplo (ou outro, por ``?car=``). Se um
número da demonstração divergir do aplicativo, o defeito está aqui, não no
texto.

Medido no imóvel de teste (MT-5108501-CBE0F5…): todas as análises juntas levam
~5 s a frio, em paralelo menos que isso; por isso o pacote é calculado na hora
e guardado em memória, sem arquivo pré-gerado. As URLs de tiles saem de
``services/layers.py`` e têm o próprio cache (``services/tiles.py``), então são
remontadas a cada pedido em vez de envelhecerem dentro do pacote.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..config import datasets as ds
from ..config import mapbiomas as mb
from ..config.settings import HANSEN_TREECOVER_THRESHOLD
from . import biomass, fire, hansen, ibge_vegetation, layers, mapbiomas_history
from . import sicar, spot, transitions
from . import zones as zs

logger = logging.getLogger(__name__)

#: O imóvel de teste do projeto (README, doc/12): Vera/MT, 61 ha, floresta →
#: pastagem → soja, registrado em 2014 e com três registros sobrepostos.
EXEMPLO_PADRAO = "MT-5108501-CBE0F5EDD27A4D7888E7392EA7D44793"

ROTA = "/_demonstracao/camposcope.json"

#: O exemplo padrão, já calculado e com as geometrias simplificadas, para a
#: página abrir na hora: ``scripts/build_demonstracao.py`` o regrava a partir
#: destes mesmos serviços. Outros ``?car=`` continuam calculados na hora.
ARQUIVO_EXEMPLO = Path(__file__).resolve().parents[2] / "data" / "demonstracao" / "camposcope.json"

_TTL_S = 6 * 3600
_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
_travas: Dict[str, threading.Lock] = {}
_trava_global = threading.Lock()


def _trava(chave: str) -> threading.Lock:
    """Uma trava por imóvel: dez visitas a frio calculam o pacote uma vez."""
    with _trava_global:
        return _travas.setdefault(chave, threading.Lock())


def _prov(p: Any) -> Dict[str, Any]:
    return {
        "nome": getattr(p, "name", ""),
        "dataset": getattr(p, "dataset_id", ""),
        "escala_m": getattr(p, "scale_m", None),
        "calculado_em": getattr(p, "computed_at", ""),
        "degradado": bool(getattr(p, "degraded", False)),
    }


def _seguro(nome: str, fn: Callable[[], Any], erros: Dict[str, str]) -> Any:
    """Uma análise que falha vira uma lacuna declarada, não uma página quebrada."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        logger.exception("demonstração: %s falhou", nome)
        erros[nome] = str(exc)[:300]
        return None


def _historico(df) -> Dict[str, Any]:
    """{zona: {classe: [ha por ano]}} e a legenda das classes presentes."""
    anos = sorted(int(a) for a in df["year"].unique())
    por_zona: Dict[str, Dict[str, List[float]]] = {}
    classes: Dict[str, Dict[str, str]] = {}
    for (zona, classe), g in df.groupby(["zone_key", "class_id"]):
        serie = dict(zip(g["year"].astype(int), g["area_ha"].astype(float)))
        por_zona.setdefault(zona, {})[str(int(classe))] = [round(serie.get(a, 0.0), 3) for a in anos]
        if str(int(classe)) not in classes:
            linha = g.iloc[0]
            classes[str(int(classe))] = {"nome": str(linha["class_pt"]), "cor": str(linha["color"])}
    # o mesmo conjunto que o aplicativo chama de vegetação nativa
    # (config/mapbiomas.py: floresta + savana + campos, sem silvicultura)
    return {"anos": anos, "zonas": por_zona, "classes": classes,
            "nativas": sorted(mb.NATURAL_VEGETATION)}


def _transicoes(T: Dict[str, Dict[Any, Dict[Any, float]]]) -> Dict[str, List[Dict[str, Any]]]:
    return {
        zona: [
            {"de": int(a), "para": int(b), "ha": round(float(v), 3)}
            for a, destinos in fluxos.items() for b, v in destinos.items() if v > 0
        ]
        for zona, fluxos in T.items()
    }


def _calcular(cod: str) -> Dict[str, Any]:
    imovel = sicar.by_code(cod)
    if not imovel.geometry:
        raise sicar.SicarError(f"{cod}: o SICAR não devolveu geometria")
    zonas = zs.build_zones(imovel.geometry)
    ano_reg = imovel.ano_criacao
    ano_fim = mb.MAPBIOMAS_YEAR_END
    erros: Dict[str, str] = {}

    tarefas = {
        "historico": lambda: mapbiomas_history.land_cover_history(zonas),
        "transicoes": lambda: transitions.compute_transitions(zonas, 1985, ano_fim),
        "hansen": lambda: hansen.forest_change(zonas, registration_year=ano_reg),
        "biomassa": lambda: biomass.above_ground_biomass(zonas),
        "fogo": lambda: fire.fire_analysis(zonas),
        "spot": lambda: spot.coverage(imovel.geometry),
        "ibge": lambda: ibge_vegetation.mapbiomas_comparison(zonas),
        "sobrepostos": lambda: sicar.overlapping(imovel),
    }
    with ThreadPoolExecutor(max_workers=len(tarefas)) as pool:
        futuros = {k: pool.submit(_seguro, k, fn, erros) for k, fn in tarefas.items()}
        r = {k: f.result() for k, f in futuros.items()}

    out: Dict[str, Any] = {
        "imovel": {
            "cod_imovel": imovel.cod_imovel,
            "uf": imovel.uf,
            "municipio": imovel.municipio,
            "area_declarada_ha": imovel.area_declarada_ha,
            "area_calculada_ha": round(zonas[0].area_ha, 4),
            "m_fiscal": imovel.m_fiscal,
            "tipo_imovel": imovel.tipo_imovel,
            "status_imovel": imovel.status_imovel,
            "condicao": imovel.condicao,
            "dat_criacao": imovel.dat_criacao,
            "data_atualizacao": imovel.data_atualizacao,
            "ano_criacao": ano_reg,
            "consultado_em": imovel.queried_at,
            "geometry": imovel.geometry,
        },
        "zonas": [
            {"key": z.key, "label": z.label, "kind": z.kind, "radius_m": z.radius_m,
             "area_ha": round(z.area_ha, 4), "geojson": z.geojson}
            for z in zonas
        ],
        "procedencia": [],
        "erros": erros,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    if r["historico"]:
        df, p = r["historico"]
        out["historico"] = _historico(df)
        out["procedencia"].append(_prov(p))
    if r["transicoes"]:
        T, p = r["transicoes"]
        out["transicoes"] = {"ano_a": 1985, "ano_b": ano_fim, "zonas": _transicoes(T)}
        out["procedencia"].append(_prov(p))
    if r["hansen"]:
        perda, ganho, p = r["hansen"]
        out["hansen"] = {
            "limiar_pct": HANSEN_TREECOVER_THRESHOLD,
            "ganho_ha": round(float(ganho), 3),
            "perda": {
                zona: [{"ano": int(x.year), "ha": round(float(x.area_ha), 3), "periodo": x.period}
                       for x in g.itertuples()]
                for zona, g in perda.groupby("zone_key")
            },
        }
        out["procedencia"].append(_prov(p))
    if r["biomassa"]:
        B, p = r["biomassa"]
        out["biomassa"] = {
            zona: [{"ano": int(x.year), "mgha": round(float(x.agb_mean_mgha), 2),
                    "total_mg": round(float(x.total_biomass_mg), 1)} for x in g.itertuples()]
            for zona, g in B.groupby("zone_key")
        }
        out["procedencia"].append(_prov(p))
    if r["fogo"]:
        resumo, anual, p = r["fogo"]
        out["fogo"] = {
            "resumo": {
                x.zone_key: {"historico_pct": _num(x.fire_history_pct), "frequencia": _num(x.fire_frequency),
                             "ultimo_ano": _int(x.fire_last_year), "area_ha": _num(x.area_ha)}
                for x in resumo.itertuples()
            },
            "anual": {
                zona: [{"ano": int(x.year), "pct": round(float(x.fire_pct), 2)} for x in g.itertuples()]
                for zona, g in anual.groupby("zone_key")
            },
        }
        out["procedencia"].append(_prov(p))
    if r["spot"]:
        cobertura, p = r["spot"]
        out["spot"] = cobertura
        out["procedencia"].append(_prov(p))
    if r["ibge"]:
        df, p = r["ibge"]
        out["ibge"] = ibge_vegetation.bucket_matrix(df, "imovel")
        out["procedencia"].append(_prov(p))
    if r["sobrepostos"] is not None:
        outros = r["sobrepostos"]
        areas = {a["cod_imovel"]: a for a in zs.overlap_areas(
            imovel.geometry, [(o.cod_imovel, o.geometry) for o in outros])}
        out["sobrepostos"] = [
            {"cod_imovel": o.cod_imovel, "area_declarada_ha": o.area_declarada_ha,
             "condicao": o.condicao, "status_imovel": o.status_imovel,
             "overlap_ha": areas.get(o.cod_imovel, {}).get("overlap_ha", 0.0),
             "overlap_pct_do_imovel": areas.get(o.cod_imovel, {}).get("overlap_pct_do_imovel", 0.0),
             "geometry": o.geometry}
            for o in outros
        ]
    return out


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else round(f, 3)


def _int(v: Any) -> Optional[int]:
    f = _num(v)
    return None if f is None else int(f)


def _camadas(pacote: Dict[str, Any]) -> Dict[str, Any]:
    """Os mesmos tiles das abas do aplicativo, e os vetores de contexto."""
    imovel = pacote["imovel"]
    ano_fim = mb.MAPBIOMAS_YEAR_END
    ano_reg = imovel.get("ano_criacao")
    specs = {
        "mb_1985": lambda: layers.mapbiomas_year_spec(1985),
        f"mb_{ano_fim}": lambda: layers.mapbiomas_year_spec(ano_fim),
        "hansen_2008": lambda: layers.hansen_change_spec(2008),
        "biomassa": lambda: layers.biomass_year_spec(ds.AGB_YEARS[-1]),
        "fogo": lambda: layers.fire_frequency_spec(),
        "spot": lambda: layers.ee_basemap_spec("spot_2008_visual"),
        "ibge": lambda: layers.ibge_vegetation_spec(),
    }
    if ano_reg and ano_reg not in (1985, ano_fim):
        specs[f"mb_{ano_reg}"] = lambda: layers.mapbiomas_year_spec(ano_reg)
    erros: Dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(specs)) as pool:
        futuros = {k: pool.submit(_seguro, f"camada {k}", fn, erros) for k, fn in specs.items()}
        out = {}
        for k, f in futuros.items():
            spec = f.result()
            if spec and spec.get("url"):
                out[k] = {"url": spec["url"], "attribution": spec.get("attribution", ""),
                          "opacity": spec.get("opacity", 0.8)}
    try:
        out["sicar"] = sicar.wms_layer_spec(imovel["uf"], opacity=0.55)
    except Exception:  # noqa: BLE001 — UF fora do vocabulário: sem contexto, sem erro
        pass
    return out


def _leve(geom: Optional[Dict[str, Any]], tol: float) -> Optional[Dict[str, Any]]:
    """Geometria para desenhar: simplificada e com 5 casas (~1 m)."""
    if not geom:
        return geom
    from shapely.geometry import mapping, shape
    g = shape(geom.get("geometry", geom))
    s = g.simplify(tol, preserve_topology=True)
    g = s if not s.is_empty else g

    def arred(c):
        return [arred(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(c[0], 5), round(c[1], 5)]

    m = mapping(g)
    return {"type": m["type"], "coordinates": arred(m["coordinates"])}


def instantaneo(cod: str = EXEMPLO_PADRAO) -> Dict[str, Any]:
    """O pacote de um imóvel sem as camadas e com geometrias leves — o
    conteúdo de ``ARQUIVO_EXEMPLO``. Só a divisa do imóvel, os três anéis e
    os registros sobrepostos; nenhuma outra geometria do SICAR."""
    dados = _calcular(cod)
    dados["imovel"]["geometry"] = _leve(dados["imovel"]["geometry"], 0.00002)
    for z in dados["zonas"]:
        z["geojson"] = _leve(z["geojson"], 0.0001)
    for o in dados.get("sobrepostos") or []:
        o["geometry"] = _leve(o["geometry"], 0.0001)
    return dados


def _exemplo_guardado() -> Optional[Dict[str, Any]]:
    try:
        return json.loads(ARQUIVO_EXEMPLO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def pacote(cod: str = EXEMPLO_PADRAO) -> Dict[str, Any]:
    """O pacote completo de um imóvel, do cache quando possível."""
    cod = (cod or EXEMPLO_PADRAO).strip().upper()
    if cod == EXEMPLO_PADRAO:
        guardado = _exemplo_guardado()
        if guardado:
            return {**guardado, "camadas": _camadas(guardado), "exemplo_padrao": True}
    with _trava(cod):
        guardado = _cache.get(cod)
        if guardado and time.time() - guardado[0] < _TTL_S:
            dados = guardado[1]
        else:
            t0 = time.time()
            dados = _calcular(cod)
            logger.info("demonstração %s calculada em %.1f s", cod, time.time() - t0)
            # um pacote com lacunas não é guardado: a próxima visita tenta de novo
            if not dados["erros"]:
                _cache[cod] = (time.time(), dados)
    return {**dados, "camadas": _camadas(dados), "exemplo_padrao": cod == EXEMPLO_PADRAO}
