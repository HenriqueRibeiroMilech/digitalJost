"""Carregamento do build Vue e renderização do shell para os módulos modernos."""

import json
from pathlib import Path

from flask import Blueprint, current_app, make_response, render_template, url_for
from jinja2 import PrefixLoader

from .csrf import get_csrf_token


def init_vue_shell(app):
    resources = Blueprint(
        "backend_vue",
        "backend",
        static_folder="static/app",
        static_url_path="/static/app",
        template_folder="templates",
    )
    # O prefixo distingue o shell moderno de eventuais cópias no legado.
    resources.jinja_loader = PrefixLoader({"backend": resources.jinja_loader})
    app.register_blueprint(resources)


def _manifest_assets():
    static_folder = current_app.blueprints["backend_vue"].static_folder
    manifest_path = Path(static_folder) / ".vite" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["index.html"]
    stylesheets = []
    visited = set()

    def collect(chunk):
        for filename in chunk.get("css", []):
            stylesheet = url_for("backend_vue.static", filename=filename)
            if stylesheet not in stylesheets:
                stylesheets.append(stylesheet)
        for key in chunk.get("imports", []):
            if key not in visited:
                visited.add(key)
                collect(manifest[key])

    collect(entry)
    return url_for("backend_vue.static", filename=entry["file"]), stylesheets


def render_vue_shell(*, title, unavailable_message, csrf_token_provider=get_csrf_token):
    """Renderiza após a autorização do módulo e fornece o token CSRF compartilhado."""
    try:
        entry_script, stylesheets = _manifest_assets()
    except (OSError, KeyError, ValueError):
        return unavailable_message, 503
    response = make_response(render_template(
        "backend/app/shell.html",
        title=title,
        csrf_token=csrf_token_provider(),
        entry_script=entry_script,
        stylesheets=stylesheets,
    ))
    response.headers["Cache-Control"] = "private, no-store"
    return response
