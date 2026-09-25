"""Constraint C4 in the laid-out report — doc/13 §9, run on the model.

The report describes; it never issues a verdict. This guard scans the content
model (not the PDF text) in **pt and en**:

1. the first block of the first section is the disclosure ``Callout`` — the
   exact ``DISCLOSURE_*`` constant for the language, or ``square_disclosure``
   for the synthetic square;
2. every template ``services/report_text.py`` holds, and every section title,
   caption, paragraph, table header/cell and contents entry of generated
   reports, is checked against the banned vocabulary below;
3. exempt, because they are verbatim constants required elsewhere: the
   ``DISCLOSURE_*`` constants (they contain "regularidade ambiental" /
   "compliance"), the doc/04 §13 attribution block and the sources/citation
   block, and the verbatim CAR fields (``condicao``, ``status_imovel``,
   ``tipo_imovel``).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from camposcope import report_kit as rk  # noqa: E402
from camposcope.config.sicar import DISCLOSURE_EN, DISCLOSURE_PT  # noqa: E402
from camposcope.services import report_text as rt  # noqa: E402
from camposcope.services.report import ReportOptions, build_imovel_report  # noqa: E402
from camposcope.translations import get_translations  # noqa: E402

from test_report import (IMOVEL, SQUARE, _full_gather, _map_figure,  # noqa: E402
                         _minimal_gather)

#: doc/13 §9, verbatim, plus two D13 / "inside a TI/UC" guards.
BANNED = [
    r"irregular", r"consolidad", r"passivo", r"ilegal|illegal",
    r"infraç|infraction|violation", r"conformidade|complian",
    r"regularidade|regularity", r"déficit|deficit", r"excedente|surplus",
    r"reserva legal|legal reserve", r"due diligence", r"veredito|verdict",
    r"avaliação do imóvel|valuation",
    # D13: never state a biome; never claim the property is inside a TI/UC.
    r"\bbiom[ae]s?\b", r"terra indígena|indigenous land",
    r"unidade de conservação|conservation unit",
]
_BANNED_RE = [re.compile(p, re.I) for p in BANNED]
_APP_RE = re.compile(r"\bAPP\b")          # case-sensitive: the legal acronym


def _violations(text: str) -> list[str]:
    hits = [p.pattern for p in _BANNED_RE if p.search(text or "")]
    if _APP_RE.search(text or ""):
        hits.append(r"\bAPP\b")
    return hits


def _strings(report: rk.Report, verbatim: set[str]) -> list[str]:
    """Every app-authored string in the model, minus the exempt ones."""
    out: list[str] = [report.meta.title]
    for section in report.sections:
        out.append(section.title)
        for block in section.blocks:
            parts = [block.left, block.right] if isinstance(block, rk.SideBySide) else [block]
            for b in parts:
                if isinstance(b, rk.Callout):
                    if b.kind != "disclosure":          # disclosure: exempt constant
                        out += [b.title, b.text]
                elif isinstance(b, rk.Paragraph):
                    out.append(b.text)
                elif isinstance(b, rk.KeyValues):
                    out.append(b.caption)
                    for key, value in b.rows:
                        out.append(key)
                        if value not in verbatim:
                            out.append(value)
                elif isinstance(b, rk.Table):
                    out += [b.caption, b.note] + list(b.columns)
                    out += [c for row in b.rows for c in row
                            if isinstance(c, str) and c not in verbatim]
                elif isinstance(b, rk.Figure):
                    out += [b.caption, b.unavailable_reason]
                elif isinstance(b, rk.MapFigure):
                    out.append(b.caption)
                    out += [item.label for item in b.composition.legend]
                elif isinstance(b, rk.LocatorMap):
                    out.append(b.label)
                elif isinstance(b, rk.ContentsList):
                    out += [i.title for i in b.items] + [i.reason for i in b.items]
                # Citation (citation, sources, §13 attributions): exempt.
    return [s for s in out if s]


# --- 1. the disclosure opens the report ------------------------------------ #

@pytest.mark.parametrize("lang,expected", [("pt", DISCLOSURE_PT), ("en", DISCLOSURE_EN)])
def test_first_block_is_the_exact_car_disclosure(lang, expected):
    for gather in (_minimal_gather(), _full_gather()):
        rep = build_imovel_report(**gather, lang=lang)
        first = rep.sections[0].blocks[0]
        assert isinstance(first, rk.Callout) and first.kind == "disclosure"
        assert first.text == expected
        assert rep.sections[0].title == ""       # nothing, not even a heading, above it


@pytest.mark.parametrize("lang", ["pt", "en"])
def test_square_opens_with_square_disclosure(lang):
    rep = build_imovel_report(**_minimal_gather(SQUARE), lang=lang)
    first = rep.sections[0].blocks[0]
    assert isinstance(first, rk.Callout) and first.kind == "disclosure"
    assert first.text == get_translations(lang)["square_disclosure"]
    assert first.text not in (DISCLOSURE_PT, DISCLOSURE_EN)


# --- 2. vocabulary ---------------------------------------------------------- #

@pytest.mark.parametrize("lang", ["pt", "en"])
def test_every_template_is_clean(lang):
    bad = {key: _violations(text) for key, text in rt.TEMPLATES[lang].items()
           if _violations(text)}
    assert not bad, f"banned vocabulary in report_text templates: {bad}"


def _poisoned_car():
    """Verbatim CAR fields may say anything — they are the landholder's
    record, printed as filed — so poison them and prove only they are exempt."""
    return dict(IMOVEL, condicao="Pendente — irregularidade (texto do CAR)",
                status_imovel="Cancelado por decisão administrativa",
                tipo_imovel="IRU")


@pytest.mark.parametrize("lang", ["pt", "en"])
@pytest.mark.parametrize("variant", ["full", "minimal", "square", "no_overlap_lookup"])
def test_generated_report_is_clean(lang, variant):
    imovel = _poisoned_car()
    if variant == "full":
        gather = dict(_full_gather(), imovel=imovel)
        extra = dict(maps=[_map_figure()], options=ReportOptions(gbif=True, appendix=True),
                     figure_errors={"fogo": "timed out"})
    elif variant == "minimal":
        gather, extra = _minimal_gather(imovel), dict(map_errors={"s2": "EE timeout"})
    elif variant == "square":
        gather, extra = _minimal_gather(SQUARE), {}
    else:
        gather = dict(_full_gather(), imovel=imovel, overlaps=[], overlaps_checked=False)
        extra = dict(overlaps_error="SICAR indisponível")
    rep = build_imovel_report(**gather, lang=lang, **extra)
    verbatim = {imovel["condicao"], imovel["status_imovel"], imovel["tipo_imovel"]}
    bad = [(s, _violations(s)) for s in _strings(rep, verbatim) if _violations(s)]
    assert not bad, f"banned vocabulary in the {lang} report: {bad}"


@pytest.mark.parametrize("lang", ["pt", "en"])
def test_spot_text_never_labels_the_imagery(lang):
    """D10 / doc/12 §4: dates and the pre-cutoff share, never "0 %" for an
    unknown share and never a label derived from the imagery."""
    unknown = {"has_coverage": True, "covered_pct": 80.0, "date_min": "2008-05-01",
               "date_max": "2008-09-01", "pre_cutoff_pct": None, "cutoff": "2008-07-22"}
    for text in (rt.spot_text(unknown, lang), rt.spot_map_caption(unknown, lang),
                 rt.spot_text({"has_coverage": False}, lang)):
        assert not _violations(text), text
        assert not re.search(r"(?<![\d,.])0\s?%", text), text
    caption = rt.spot_map_caption(dict(unknown, pre_cutoff_pct=64.0), lang)
    assert "2008" in caption and ("64 %" in caption or "64%" in caption)


def test_car_fields_are_neither_translated_nor_coloured():
    """condicao/status_imovel verbatim in the English report, as plain text
    (a KeyValues value carries no colour — there is nowhere to put one)."""
    imovel = _poisoned_car()
    rep = build_imovel_report(**dict(_full_gather(), imovel=imovel), lang="en")
    kv = next(b.left for s in rep.sections for b in s.blocks
              if isinstance(b, rk.SideBySide))
    values = [v for _, v in kv.rows]
    assert imovel["condicao"] in values and imovel["status_imovel"] in values
