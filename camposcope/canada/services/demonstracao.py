"""The numbers of the Canada walkthrough (``/walkthrough``, Kelowna).

The English walkthrough opens a BC parcel instead of a CAR property, so Canadian
readers see land they know. Like the Brazil package
(``camposcope/services/demonstracao.py``) it has no numbers of its own: it is
built by the same services the Canada page uses — ParcelMap BC, the AAFC Annual
Crop Inventory, transitions, Hansen, ESA CCI biomass, MODIS fire and the VLCE2
cross-check — for one example parcel (or another, by ``?pid=``). If a number on
the page disagrees with the app, the defect is here, not in the text.

Measured on the example parcel (2026-10-29): every analysis together takes
~6 s cold. The example is still stored, with light geometries, so the page opens
at once; tile URLs are minted per request, because Earth Engine's expire.
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

from ...config.settings import HANSEN_TREECOVER_THRESHOLD
from ...services.demonstracao import _int, _leve, _num, _prov, _seguro, _transicoes
from ..config import aafc
from ..config import vlce2 as vcfg
from ..config.datasets import AGB_YEARS
from . import biomass, fire, hansen, layers, pmbc, transitions, vlce2
from . import zones as cz
from .aci_history import land_cover_history

logger = logging.getLogger(__name__)

#: An orchard parcel on the East Kelowna bench, 12 ha, ringed by orchards,
#: vineyards, subdivisions and the forested slopes above Mission Creek.
EXEMPLO_PADRAO = "003269451"

ROTA = "/_demonstracao/camposcope_ca.json"

ARQUIVO_EXEMPLO = Path(__file__).resolve().parents[3] / "data" / "demonstracao" / "camposcope_ca.json"

_TTL_S = 6 * 3600
_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
_travas: Dict[str, threading.Lock] = {}
_trava_global = threading.Lock()


def _trava(chave: str) -> threading.Lock:
    with _trava_global:
        return _travas.setdefault(chave, threading.Lock())


def _historico(df) -> Dict[str, Any]:
    """{zone: {class: [ha per year]}} and the legend of the classes present."""
    anos = sorted(int(a) for a in df["year"].unique())
    por_zona: Dict[str, Dict[str, List[float]]] = {}
    classes: Dict[str, Dict[str, str]] = {}
    for (zona, classe), g in df.groupby(["zone_key", "class_id"]):
        serie = dict(zip(g["year"].astype(int), g["area_ha"].astype(float)))
        por_zona.setdefault(zona, {})[str(int(classe))] = [round(serie.get(a, 0.0), 3) for a in anos]
        if str(int(classe)) not in classes:
            linha = g.iloc[0]
            classes[str(int(classe))] = {"nome": str(linha["class_pt"]), "nome_en": str(linha["class_en"]),
                                         "cor": str(linha["color"])}
    # what the Canada page calls natural vegetation (config/aafc.py: forest,
    # wetland, grassland and shrub; the ACI cannot tell planted from natural stands)
    return {"anos": anos, "zonas": por_zona, "classes": classes,
            "nativas": sorted(aafc.NATURAL_VEGETATION)}


def _calcular(pid: str) -> Dict[str, Any]:
    parcela = pmbc.by_identifier(pid)
    if not parcela.geometry:
        raise pmbc.PmbcError(f"{pid}: ParcelMap BC returned no geometry")
    geom = parcela.geometry.get("geometry", parcela.geometry)
    zonas = cz.build_zones(geom)
    ano_a, ano_b = transitions.default_year_pair()
    ano_v = vlce2.default_year()
    erros: Dict[str, str] = {}

    tarefas: Dict[str, Callable[[], Any]] = {
        "historico": lambda: land_cover_history(zonas),
        "transicoes": lambda: transitions.compute_transitions(zonas, ano_a, ano_b),
        "hansen": lambda: hansen.forest_change(zonas, parcel_year=parcela.start_year),
        "biomassa": lambda: biomass.above_ground_biomass(zonas),
        "fogo": lambda: fire.fire_analysis(zonas),
        "vlce2": lambda: vlce2.agreement(zonas, ano_v),
    }
    with ThreadPoolExecutor(max_workers=len(tarefas)) as pool:
        futuros = {k: pool.submit(_seguro, k, fn, erros) for k, fn in tarefas.items()}
        r = {k: f.result() for k, f in futuros.items()}

    out: Dict[str, Any] = {
        "parcela": {
            "pid": parcela.pid,
            "pid_formatado": parcela.pid_formatted,
            "fabric_id": parcela.fabric_id,
            "identificador": parcela.identifier,
            "classe": parcela.parcel_class,
            "tipo_dono": parcela.owner_type,
            "status": parcela.parcel_status,
            "plano": parcela.plan_number,
            "municipio": parcela.municipality,
            "distrito": parcela.regional_district,
            "area_registrada_ha": parcela.area_registered_ha,
            "area_calculada_ha": round(zonas[0].area_ha, 4),
            "ano_inicio": parcela.start_year,
            "atualizado_em": parcela.when_updated,
            "consultado_em": parcela.queried_at,
            "geometry": geom,
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
        out["transicoes"] = {"ano_a": ano_a, "ano_b": ano_b, "zonas": _transicoes(T)}
        out["procedencia"].append(_prov(p))
    if r["hansen"]:
        perda, ganho, p = r["hansen"]
        out["hansen"] = {
            "limiar_pct": HANSEN_TREECOVER_THRESHOLD,
            "ganho_ha": round(float(ganho), 3),
            "divide_em": hansen.splits_at(parcela.start_year),
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
            "fonte": p.dataset_id, "escala_m": p.scale_m,
            "resumo": {
                x.zone_key: {"historico_pct": _num(x.fire_history_pct), "frequencia": _num(x.fire_frequency),
                             "ultimo_ano": _int(x.fire_last_year), "area_ha": _num(x.area_ha),
                             "abaixo_resolucao": bool(getattr(x, "below_resolution", False))}
                for x in resumo.itertuples()
            },
            "anual": {
                zona: [{"ano": int(x.year), "pct": round(float(x.fire_pct), 2)} for x in g.itertuples()]
                for zona, g in anual.groupby("zone_key")
            },
        }
        out["procedencia"].append(_prov(p))
    if r["vlce2"]:
        resumo, matriz, p = r["vlce2"]
        out["vlce2"] = {
            "ano": ano_v,
            "grupos": {k: {"nome": vcfg.GROUP_LABELS_PT.get(k, k), "nome_en": vcfg.GROUP_LABELS_EN.get(k, k),
                           "cor": vcfg.GROUP_COLORS.get(k, "#9aa8a1")} for k in vcfg.GROUP_LABELS_EN},
            "resumo": {x.zone_key: {"concordancia_pct": _num(x.agreement_pct), "area_ha": _num(x.area_ha)}
                       for x in resumo.itertuples()},
            "matriz": {
                zona: [{"aci": x.aci_group, "vlce2": x.vlce2_group, "ha": round(float(x.area_ha), 3)}
                       for x in g.itertuples() if x.area_ha > 0]
                for zona, g in matriz.groupby("zone_key")
            },
        }
        out["procedencia"].append(_prov(p))
    return out


def _camadas(pacote: Dict[str, Any]) -> Dict[str, Any]:
    """The same tiles as the Canada page's tabs."""
    h = pacote.get("historico") or {}
    anos = h.get("anos") or [aafc.ACI_YEAR_END]
    ano_v = (pacote.get("vlce2") or {}).get("ano")
    specs: Dict[str, Callable[[], Any]] = {
        f"aci_{anos[0]}": lambda: layers.aci_year_spec(anos[0]),
        f"aci_{anos[-1]}": lambda: layers.aci_year_spec(anos[-1]),
        "hansen_2001": lambda: layers.hansen_change_spec(2001),
        "biomassa": lambda: layers.biomass_year_spec(AGB_YEARS[-1]),
        "fogo": lambda: layers.fire_frequency_spec(),
    }
    if ano_v:
        specs[f"vlce2_{ano_v}"] = lambda: layers.vlce2_year_spec(ano_v)
    erros: Dict[str, str] = {}
    out: Dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=len(specs)) as pool:
        futuros = {k: pool.submit(_seguro, f"layer {k}", fn, erros) for k, fn in specs.items()}
        for k, f in futuros.items():
            spec = f.result()
            if spec and spec.get("url"):
                out[k] = {"url": spec["url"], "attribution": spec.get("attribution", ""),
                          "opacity": spec.get("opacity", 0.8)}
    try:
        out["pmbc"] = pmbc.wms_layer_spec(opacity=0.55)
    except Exception:  # noqa: BLE001 — context only
        pass
    return out


def instantaneo(pid: str = EXEMPLO_PADRAO) -> Dict[str, Any]:
    """The package without layers and with light geometries — ``ARQUIVO_EXEMPLO``."""
    dados = _calcular(pid)
    dados["parcela"]["geometry"] = _leve(dados["parcela"]["geometry"], 0.00002)
    for z in dados["zonas"]:
        z["geojson"] = _leve(z["geojson"], 0.0001)
    return dados


def _exemplo_guardado() -> Optional[Dict[str, Any]]:
    try:
        return json.loads(ARQUIVO_EXEMPLO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def pacote(pid: str = EXEMPLO_PADRAO) -> Dict[str, Any]:
    """The whole package for one parcel, from the cache when possible."""
    pid = "".join(ch for ch in (pid or EXEMPLO_PADRAO) if ch.isdigit()) or EXEMPLO_PADRAO
    if pid == EXEMPLO_PADRAO:
        guardado = _exemplo_guardado()
        if guardado:
            return {**guardado, "camadas": _camadas(guardado), "exemplo_padrao": True}
    with _trava(pid):
        guardado = _cache.get(pid)
        if guardado and time.time() - guardado[0] < _TTL_S:
            dados = guardado[1]
        else:
            t0 = time.time()
            dados = _calcular(pid)
            logger.info("walkthrough %s computed in %.1f s", pid, time.time() - t0)
            if not dados["erros"]:
                _cache[pid] = (time.time(), dados)
    return {**dados, "camadas": _camadas(dados), "exemplo_padrao": pid == EXEMPLO_PADRAO}
