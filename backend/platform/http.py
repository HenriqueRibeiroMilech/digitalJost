"""Autorização HTTP e respostas de erro da API moderna."""

from functools import wraps

from apiflask import HTTPError
from flask import abort, current_app, jsonify, redirect, request, url_for

from .csrf import has_valid_csrf


_MESSAGES = {
    400: "Requisição inválida.",
    401: "Sessão expirada.",
    403: "Acesso negado.",
    404: "Recurso não encontrado.",
    405: "Método não permitido.",
    422: "Dados inválidos.",
    500: "Não foi possível concluir a operação.",
}


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
    for status in (400, 401, 403, 404, 405, 500):
        blueprint.register_error_handler(status, http_exception_response)

    @blueprint.errorhandler(HTTPError)
    def api_http_error(error):
        # APIFlask fornece detail.json/detail.query na validação Pydantic.
        if error.status_code == 422:
            return api_error(422, message=error.message, detail=error.detail, headers=error.headers)
        return api_error(error.status_code, headers=error.headers)


def page_access(*, identity, permission):
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


def get_service(name):
    return current_app.extensions[name]
