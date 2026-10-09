"""Carregamento do build Vue e renderização do shell para os módulos modernos."""

import json
from pathlib import Path

from flask import current_app, make_response, render_template, url_for


def _manifest_assets():
    manifest_path = Path(current_app.static_folder) / "app" / ".vite" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest["index.html"]
    stylesheets = []
    visited = set()

    def collect(chunk):
        for filename in chunk.get("css", []):
            stylesheet = url_for("static", filename=f"app/{filename}")
            if stylesheet not in stylesheets:
                stylesheets.append(stylesheet)
        for key in chunk.get("imports", []):
            if key not in visited:
                visited.add(key)
                collect(manifest[key])

    collect(entry)
    return url_for("static", filename=f"app/{entry['file']}"), stylesheets


def render_vue_shell(*, title, csrf_token_provider, unavailable_message):
    """Renderiza após a autorização do módulo, que também fornece seu token CSRF."""
    try:
        entry_script, stylesheets = _manifest_assets()
    except (OSError, KeyError, ValueError):
        return unavailable_message, 503
    response = make_response(render_template(
        "app/shell.html",
        title=title,
        csrf_token=csrf_token_provider(),
        entry_script=entry_script,
        stylesheets=stylesheets,
    ))
    response.headers["Cache-Control"] = "private, no-store"
    return response
