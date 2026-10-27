"""Autorização HTTP, CSRF e respostas de erro da API moderna."""

import hmac
import secrets
from functools import wraps

from apiflask import HTTPError
from flask import abort, jsonify, redirect, request, session, url_for
from pydantic import ValidationError


_MESSAGES = {
    400: "Requisição inválida.",
    401: "Sessão expirada.",
    403: "Acesso negado.",
    404: "Recurso não encontrado.",
    405: "Método não permitido.",
    422: "Dados inválidos.",
    500: "Não foi possível concluir a operação.",
}


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


class ApiProblem(Exception):
    """Falha esperada da operação, com contrato público e sem detalhes internos."""

    def __init__(self, status, message=None, *, detail=None):
        super().__init__(message or _MESSAGES.get(status, "Não foi possível concluir a operação."))
        self.status = status
        self.message = message
        self.detail = detail


def action_access(*, identity, permissions):
    """Produz o decorator de ações do módulo, consultando a identidade por chamada."""
    def require_action(action):
        def decorate(view):
            @wraps(view)
            def authorized(*args, **kwargs):
                permissions.require(identity.current_actor(), action)
                return view(*args, **kwargs)
            return authorized
        return decorate
    return require_action


def is_api_request():
    return request.path == "/api/v1" or request.path.startswith("/api/v1/")


def api_error(status, *, message=None, detail=None, headers=None):
    response = jsonify(
        message=message or _MESSAGES.get(status, "Não foi possível concluir a operação."),
        detail=detail if detail is not None else {},
    )
    response.status_code = status
    # Preserva Allow/WWW-Authenticate sem substituir o tipo e tamanho do JSON.
    for name, value in (headers or {}).items():
        if name.lower() not in ("content-type", "content-length"):
            response.headers[name] = value
    return response


def http_exception_response(error):
    return api_error(error.code, headers=error.get_response().headers)


def configure_api(blueprint, *, identity, permission):
    # Esta guarda protege o módulo; ação e acesso ao registro são conferidos nas rotas.
    @blueprint.before_request
    def authorize_api():
        if not identity.is_authenticated():
            return api_error(401)
        if not identity.can_access(permission):
            return api_error(403)
        if not has_valid_csrf():
            return api_error(400, message="Token de segurança inválido. Atualize a página.")

    def access_denied(error):
        return api_error(403)

    blueprint.register_error_handler(PermissionError, access_denied)

    @blueprint.errorhandler(ApiProblem)
    def operation_error(error):
        return api_error(error.status, message=error.message, detail=error.detail)

    @blueprint.errorhandler(ValidationError)
    def invalid_payload(error):
        # Inclui o JSON validado manualmente no multipart, mantendo os erros por campo.
        fields = {}
        for item in error.errors(include_url=False, include_context=False, include_input=False):
            field = str(item["loc"][0]) if item["loc"] else "payload"
            fields.setdefault(field, []).append(item["msg"])
        return api_error(422, detail={"json": fields})

    for status in (400, 401, 403, 404, 405, 500):
        blueprint.register_error_handler(status, http_exception_response)

    @blueprint.errorhandler(HTTPError)
    def api_http_error(error):
        # APIFlask fornece detail.json/detail.query na validação Pydantic.
        if error.status_code == 422:
            return api_error(422, message=error.message, detail=error.detail, headers=error.headers)
        return api_error(error.status_code, headers=error.headers)


def page_access(*, identity, permission):
    # A página pode redirecionar ao login; a API usa JSON com status 401.
    def decorate(view):
        @wraps(view)
        def authorized(*args, **kwargs):
            if not identity.is_authenticated():
                return redirect(url_for("auth.login", next=request.url))
            if not identity.can_access(permission):
                abort(403)
            return view(*args, **kwargs)
        return authorized
    return decorate
