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
