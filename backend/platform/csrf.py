"""CSRF da aplicação moderna, compatível com as sessões anteriores de Eventos."""

import hmac
import secrets

from flask import request, session


def get_csrf_token():
    token = session.get("backend_csrf")
    if not isinstance(token, str) or not token:
        token = session.get("events_csrf")
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
    if session.get("backend_csrf") != token:
        session["backend_csrf"] = token
    # Mantém compatibilidade com abas e com o backend anterior durante a troca.
    previous = session.get("events_csrf")
    if not isinstance(previous, str) or not previous:
        session["events_csrf"] = token
    return token


def has_valid_csrf():
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return True
    received = request.headers.get("X-CSRF-Token", "")
    if not received:
        return False
    return any(
        isinstance(expected, str) and bool(expected)
        and hmac.compare_digest(expected.encode("utf-8"), received.encode("utf-8"))
        for expected in (session.get("backend_csrf"), session.get("events_csrf"))
    )
