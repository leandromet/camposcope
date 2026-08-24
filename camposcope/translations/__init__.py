"""UI text in more than one language.

Ported in structure from Naturametrics' ``translations/`` package (same
problem: PT-primary domain, EN partial). Portuguese is canonical:
``TRANSLATIONS_PT`` is the reference key set, and English falls back to it
for any key not (yet) overridden — an incomplete language never shows a
blank string or a raw key, just Portuguese.

**What this covers, and what it deliberately does not.** Only static UI
chrome — labels, buttons, captions, help text — goes through this table.
Three categories never do, and never should:

1. **Cadastral fields** (``condicao``, ``status_imovel``, …) — constraint C4
   requires these verbatim from the CAR, in the language the landholder's
   own document uses. Translating ``"Aguardando análise"`` would make it
   unquotable against the source record.
2. **Official dataset vocabulary** — MapBiomas class names, the PPR-INCRA
   typology, IBGE's ``legenda_2`` — these are the names datasets publish
   under; inventing an English gloss would make a screenshot harder to trace
   back to its source, not easier.
3. **Zone labels** (``"Imóvel"``, ``"0 – 500 m"``) — generated in
   ``services/zones.py``, not read from this table. Distances are already
   near-language-neutral; only "Imóvel" itself is not, and threading `lang`
   through the zone-building service for one word was judged not worth the
   coupling. Known gap, not an oversight.

Run ``python -m camposcope.translations`` to check English's coverage
against the Portuguese reference set.
"""

from __future__ import annotations

from .en import TRANSLATIONS_EN
from .pt import TRANSLATIONS_PT

TRANSLATIONS: dict[str, dict[str, str]] = {
    "pt": TRANSLATIONS_PT,
    "en": TRANSLATIONS_EN,
}


def get_translations(lang: str) -> dict[str, str]:
    """All keys for ``lang``, with Portuguese filling in anything missing."""
    overrides = TRANSLATIONS.get(lang)
    if not overrides or lang == "pt":
        return TRANSLATIONS_PT
    return {**TRANSLATIONS_PT, **overrides}


def t(key: str, lang: str) -> str:
    return get_translations(lang).get(key, key)


def missing_keys() -> dict[str, set[str]]:
    """Keys each non-reference language is missing or has extra, vs. Portuguese."""
    ref = set(TRANSLATIONS_PT)
    out = {}
    for lang, table in TRANSLATIONS.items():
        if lang == "pt":
            continue
        diff = ref ^ set(table)
        if diff:
            out[lang] = diff
    return out
