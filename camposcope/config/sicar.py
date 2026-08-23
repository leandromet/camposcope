"""The CAR GeoServer's vocabulary: layer names, attribute names, UF list.

Everything here was verified against the live service on 2026-08-23 and is
documented in doc/05-sicar-geoserver.md. Nothing in this module is guessed —
if a name is not in this file, it does not exist on the service.
"""

from __future__ import annotations

import re
from typing import Dict, List

# --------------------------------------------------------------------------- #
# Layers
# --------------------------------------------------------------------------- #
#: One layer per UF; 26 states + DF. There is **no national layer**, so every
#: query has to know its UF first (doc/05 §5.3, decision D5).
UFS: List[str] = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
]

WORKSPACE = "sicar"


def layer_for_uf(uf: str) -> str:
    """``"MT"`` → ``"sicar:sicar_imoveis_mt"``.

    Raises for an unknown UF rather than building a name the server will 404 on
    — a typo here would otherwise surface as an opaque OWS exception.
    """
    key = uf.strip().upper()
    if key not in UFS:
        raise ValueError(f"UF desconhecida: {uf!r}")
    return f"{WORKSPACE}:sicar_imoveis_{key.lower()}"


# --------------------------------------------------------------------------- #
# Attributes
# --------------------------------------------------------------------------- #
#: The geometry column. **Not** ``the_geom`` — every spatial predicate refers to
#: this constant so the name lives in exactly one place.
GEOM_COLUMN = "geo_area_imovel"

#: Every non-geometry attribute, in the order the cadastral card shows them.
ATTRIBUTES: List[str] = [
    "cod_imovel",
    "status_imovel",
    "dat_criacao",
    "data_atualizacao",
    "area",
    "condicao",
    "uf",
    "municipio",
    "cod_municipio_ibge",
    "m_fiscal",
    "tipo_imovel",
]

#: What the municipality browser asks for. Excluding the geometry is what keeps
#: a 50-row page in kilobytes instead of megabytes (doc/05 §5.4).
LIST_ATTRIBUTES: List[str] = [
    "cod_imovel", "area", "condicao", "status_imovel",
    "dat_criacao", "municipio", "cod_municipio_ibge", "m_fiscal",
]

#: Native CRS of the published layers. Close enough to 4326 that confusing them
#: is invisible on a map and wrong in an area calculation — so the service
#: always asks the server to reproject rather than assuming.
NATIVE_CRS = "EPSG:4674"
REQUEST_CRS = "EPSG:4326"

# --------------------------------------------------------------------------- #
# cod_imovel
# --------------------------------------------------------------------------- #
#: ``UF-<7-digit IBGE municipality code>-<32 hex>``. Validated locally before
#: any request leaves the machine (doc/08-ui-ux.md §2).
COD_IMOVEL_RE = re.compile(r"^([A-Z]{2})-(\d{7})-([0-9A-F]{32})$")


def parse_cod_imovel(code: str) -> tuple[str, int, str]:
    """Split a CAR code into ``(uf, cod_municipio_ibge, hash)``.

    Raises ``ValueError`` with a message about the *shape* — the user pasted
    something, and "expected UF-0000000-<32 hex>" is more useful than a 404
    from a server that was never asked.
    """
    m = COD_IMOVEL_RE.match(code.strip().upper())
    if not m:
        raise ValueError(
            "Código CAR inválido. O formato é UF-0000000-"
            "<32 caracteres hexadecimais>, por exemplo "
            "MT-5108501-CBE0F5EDD27A4D7888E7392EA7D44793."
        )
    uf, ibge, digest = m.groups()
    if uf not in UFS:
        raise ValueError(f"UF desconhecida no código: {uf}")
    return uf, int(ibge), digest


def normalise_cod_imovel(code: str) -> str:
    """Canonical upper-case form, validated."""
    uf, ibge, digest = parse_cod_imovel(code)
    return f"{uf}-{ibge:07d}-{digest}"


# --------------------------------------------------------------------------- #
# Vocabulary — displayed verbatim, never re-worded (constraint C4)
# --------------------------------------------------------------------------- #
#: Glosses, for the English UI only. The source string is always shown; this is
#: a parenthetical, never a replacement. A translated ``condicao`` is no longer
#: quotable against the source (doc/08-ui-ux.md §7).
STATUS_IMOVEL_GLOSS_EN: Dict[str, str] = {
    "AT": "active registration",
    "PE": "pending",
    "SU": "suspended",
    "CA": "cancelled",
}

TIPO_IMOVEL_GLOSS_EN: Dict[str, str] = {
    "IRU": "rural property",
    "AST": "settlement",
    "PCT": "traditional peoples and communities territory",
}

#: The statement that must appear under every cadastral card and in every
#: export (constraint C4, doc/01-premises.md §5). One string, one place.
DISCLOSURE_PT = (
    "Os dados do Cadastro Ambiental Rural são autodeclaratórios: o polígono foi "
    "declarado pelo detentor do imóvel e não constitui prova de propriedade, "
    "posse ou regularidade ambiental."
)
DISCLOSURE_EN = (
    "Cadastro Ambiental Rural data is self-declared: the polygon was filed by "
    "the landholder and does not constitute proof of ownership, possession or "
    "environmental compliance."
)
