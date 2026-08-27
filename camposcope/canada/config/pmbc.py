"""ParcelMap BC's vocabulary: layer name, attributes, PID format, disclosure.

Everything here was verified against the live BC Geographic Warehouse WFS on
2026-08-27 (``DescribeFeatureType`` plus real point and PID queries) and nothing
is guessed — if a name is not in this file, it is not on the service. Same rule
as :mod:`camposcope.config.sicar`, and for the same reason: a typo in an
attribute name surfaces as an opaque OWS exception rather than as an error about
the thing that is actually wrong.

**How this cadastre differs from the CAR, and why the UI cannot treat them
alike.** The Brazil page's central caveat is that the CAR is *auto-declaratório*
— a polygon someone drew and filed. ParcelMap BC is the opposite kind of object:
it is the Province's authoritative parcel fabric, assembled by the Land Title
and Survey Authority from registered survey plans. That does **not** make it a
stronger claim about the same thing; it makes it a claim about a *different*
thing:

* It is a **boundary** record, not an **ownership** record. There are no owner
  names in this layer at all — ``OWNER_TYPE`` is a broad class (Crown
  Provincial, Private, Local Government, First Nations…), never a person. Title
  is held in the Land Title Register, which this is not.
* A parcel boundary is the *legal* description, which is not necessarily where
  a fence, a hedge or a field edge is on the ground.
* ``PARCEL_STATUS`` distinguishes active parcels from historical ones, and
  ``PARCEL_CLASS`` distinguishes real subdivided parcels from Crown
  subdivisions, road right-of-ways, park reserves and building strata.

So the disclosure below says something different from the Brazil page's, rather
than being a translation of it. Both are shown verbatim, permanently, and
neither is dismissible.
"""

from __future__ import annotations

import re
from typing import Dict, List

# --------------------------------------------------------------------------- #
# Layer
# --------------------------------------------------------------------------- #
#: One province-wide layer, unlike the CAR's 27 per-UF layers. That single fact
#: removes the whole "which layer do I query" problem decision D5 exists to
#: solve on the Brazil page — a click here needs no boundary lookup first, only
#: a bounds check to fail fast outside BC.
WORKSPACE = "pub"
LAYER = "pub:WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW"

#: Human name of the source, for attributions and provenance.
SOURCE_NAME = "ParcelMap BC — Parcel Fabric"
SOURCE_ORG = "Land Title and Survey Authority of British Columbia"

# --------------------------------------------------------------------------- #
# Attributes
# --------------------------------------------------------------------------- #
#: The geometry column. **Not** ``the_geom`` and not ``GEOMETRY`` — every
#: spatial predicate refers to this constant so the name lives in one place.
GEOM_COLUMN = "SHAPE"

#: Every non-geometry attribute, in the order the parcel card shows them.
ATTRIBUTES: List[str] = [
    "PARCEL_FABRIC_POLY_ID",
    "PID",
    "PID_FORMATTED",
    "PIN",
    "PARCEL_NAME",
    "PLAN_NUMBER",
    "PARCEL_STATUS",
    "PARCEL_CLASS",
    "OWNER_TYPE",
    "PARCEL_START_DATE",
    "MUNICIPALITY",
    "REGIONAL_DISTRICT",
    "WHEN_UPDATED",
    "FEATURE_AREA_SQM",
]

#: What the municipality browser asks for. Excluding the geometry is what keeps
#: a 25-row page in kilobytes rather than megabytes — the same trick the CAR
#: browser uses, and it matters more here: a BC municipality can hold tens of
#: thousands of parcels.
LIST_ATTRIBUTES: List[str] = [
    "PARCEL_FABRIC_POLY_ID", "PID", "PID_FORMATTED", "PARCEL_CLASS",
    "PARCEL_STATUS", "OWNER_TYPE", "MUNICIPALITY", "FEATURE_AREA_SQM",
]

#: Native CRS of the published layer — BC Albers. Close enough to nothing that
#: confusing it with 4326 is impossible (the coordinates are metres), but the
#: service always reprojects server-side rather than the client assuming.
NATIVE_CRS = "EPSG:3005"
REQUEST_CRS = "EPSG:4326"

# --------------------------------------------------------------------------- #
# PID
# --------------------------------------------------------------------------- #
#: The Parcel Identifier: nine digits, conventionally written ``000-000-000``.
#: Stored on the service **as a nine-character zero-padded string** in ``PID``
#: and hyphenated in ``PID_FORMATTED`` — both verified live. A user will paste
#: either form, or a form with spaces, so both are normalised to the bare nine
#: digits before any request is built.
PID_RE = re.compile(r"^(\d{3})[-\s]?(\d{3})[-\s]?(\d{3})$")

#: ``PARCEL_FABRIC_POLY_ID`` — the fabric's own surrogate key. Accepted as an
#: alternative identifier because a great many BC parcels have **no PID at all**
#: (Crown land, road right-of-ways, unregistered parcels): ``PID`` is null on
#: those, and without this there would be no way to link to one.
FABRIC_ID_RE = re.compile(r"^(?:PF-)?(\d{4,10})$", re.IGNORECASE)


class PidError(ValueError):
    """A PID that does not have the shape of a PID.

    Raised **locally**, before any request leaves the machine, so a malformed
    paste fails instantly with a message about the *shape* rather than as an
    empty result from a service that was never asked a sensible question.
    """


def parse_pid(value: str) -> str:
    """``"010-322-060"`` / ``"010322060"`` → ``"010322060"``.

    Zero padding is preserved, not stripped: ``PID`` is a string column on the
    service and ``010322060`` does not match ``10322060``.
    """
    match = PID_RE.match(str(value).strip())
    if not match:
        raise PidError(
            "Invalid PID. A Parcel Identifier is nine digits, usually written "
            "000-000-000 — for example 010-322-060."
        )
    return "".join(match.groups())


def format_pid(pid: str) -> str:
    """``"010322060"`` → ``"010-322-060"``, the form the LTSA prints."""
    digits = "".join(ch for ch in str(pid) if ch.isdigit()).zfill(9)
    return f"{digits[0:3]}-{digits[3:6]}-{digits[6:9]}"


def parse_fabric_id(value: str) -> int:
    """``"PF-1501666"`` / ``"1501666"`` → ``1501666``."""
    match = FABRIC_ID_RE.match(str(value).strip())
    if not match:
        raise PidError("Not a ParcelMap BC fabric id.")
    return int(match.group(1))


# --------------------------------------------------------------------------- #
# Vocabulary — displayed verbatim, never re-worded
# --------------------------------------------------------------------------- #
# The same constraint the Brazil page calls C4: cadastral field VALUES are shown
# exactly as the source publishes them. These tables are Portuguese glosses for
# the PT UI, shown as a parenthetical *beside* the source string, never instead
# of it — a translated PARCEL_CLASS is no longer quotable against the record.

PARCEL_STATUS_GLOSS_PT: Dict[str, str] = {
    "Active": "ativo",
    "Historic": "histórico",
    "Pending": "pendente",
    "Inactive": "inativo",
}

#: The published PARCEL_CLASS domain. Only the classes actually observed on the
#: service are listed; an unknown value falls through and is shown bare.
PARCEL_CLASS_GLOSS_PT: Dict[str, str] = {
    "Subdivision": "loteamento registrado",
    "Crown Subdivision": "subdivisão da Coroa",
    "Air Space": "espaço aéreo",
    "Building Strata": "condomínio edificado",
    "Bare Land Strata": "condomínio de lotes",
    "Interest": "direito real",
    "Part Of Primary Parcel": "parte de parcela principal",
    "Primary": "parcela principal",
    "Road": "faixa de domínio (via)",
    "Absolute Fee Book": "registro em Absolute Fee Book",
    "Park": "parque",
    "Common Ownership": "propriedade comum",
}

OWNER_TYPE_GLOSS_PT: Dict[str, str] = {
    "Private": "particular",
    "Crown Provincial": "Coroa provincial",
    "Crown Agency": "autarquia da Coroa",
    "Federal": "federal",
    "Local Government": "governo local",
    "First Nations": "Primeiras Nações",
    "Mixed Ownership": "propriedade mista",
    "Municipal": "municipal",
    "None": "não informado",
    "Unclassified": "não classificado",
}

#: ``PARCEL_CLASS`` values that are not somebody's land in the sense this app
#: analyses — a road right-of-way or an air-space parcel has no land cover to
#: speak of. They are **not filtered out** (a click that lands on one must say
#: what it landed on, not pretend nothing is there); the parcel card flags them
#: so a user knows why the land-cover numbers look strange.
NON_LAND_CLASSES = frozenset({"Road", "Air Space", "Interest", "Building Strata"})

#: The statement that appears under every parcel card and in every export. One
#: string, one place — see the module docstring for why it is not a translation
#: of the CAR disclosure.
DISCLOSURE_EN = (
    "ParcelMap BC shows the legal parcel fabric maintained by the Land Title "
    "and Survey Authority. It is a record of boundaries, not of ownership: it "
    "carries no owner names, and it does not establish title, possession or "
    "any right of access. A parcel boundary is a legal description and need "
    "not follow any fence, hedge or field edge on the ground."
)
DISCLOSURE_PT = (
    "O ParcelMap BC mostra a malha legal de parcelas mantida pela Land Title "
    "and Survey Authority. É um registro de limites, não de propriedade: não "
    "traz nomes de proprietários e não estabelece titularidade, posse ou "
    "direito de acesso. O limite de uma parcela é uma descrição jurídica e não "
    "corresponde necessariamente a nenhuma cerca, sebe ou divisa no terreno."
)

#: Shown wherever the page could be mistaken for covering Canada. The land-cover
#: half genuinely is national; the cadastre is not.
BC_ONLY_NOTE_EN = (
    "Parcel search covers British Columbia only — ParcelMap BC is a provincial "
    "cadastre and Canada has no national parcel fabric. The land-cover, forest, "
    "biomass and fire layers cover the whole country."
)
BC_ONLY_NOTE_PT = (
    "A busca de parcelas cobre apenas a Colúmbia Britânica — o ParcelMap BC é "
    "um cadastro provincial e o Canadá não tem malha fundiária nacional. As "
    "camadas de cobertura, floresta, biomassa e fogo cobrem o país inteiro."
)
