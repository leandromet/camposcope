"""Reflex configuration.

Ports avoid every other app on this machine — Yvynation 3000/8000, terra_web
3000/3003/3004/3005, Naturametrics 3010/8011. See doc/09-dev-environment.md §2.

A container platform injects ``PORT``; the backend must bind a *different* port
or the two fight for the same socket.
"""

import os

import reflex as rx

config = rx.Config(
    app_name="camposcope",
    app_module_import="camposcope.camposcope",
    db_url=os.environ.get("REFLEX_DB_URL", "sqlite:///reflex.db"),
    log_level=os.environ.get("REFLEX_LOG_LEVEL", "info"),
    frontend_port=int(os.environ.get("PORT", 3020)),
    backend_port=int(os.environ.get("BACKEND_PORT", 8021)),
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)
