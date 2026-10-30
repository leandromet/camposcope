"""``/demonstracao`` — o passo a passo em rolagem de um imóvel de verdade.

O artigo é ``reportagem/camposcope.{html,js}`` sobre o kit compartilhado; os
números vêm de ``/_demonstracao/camposcope.json`` (services/demonstracao.py).
``?car=`` troca o imóvel, como na página principal.
"""

from __future__ import annotations

import reflex as rx

from ..reportagem.kit import pagina


def demonstracao() -> rx.Component:
    return pagina("camposcope")


def walkthrough() -> rx.Component:
    """``/walkthrough`` — the English walkthrough, on a Kelowna parcel
    (camposcope_ca.{en.html,js}, numbers from canada/services/demonstracao.py)."""
    return pagina("camposcope_ca", lingua="en")


def walkthrough_brasil() -> rx.Component:
    """``/walkthrough/brazil`` — the Brazil article in English (camposcope.en.html)."""
    return pagina("camposcope", lingua="en")
