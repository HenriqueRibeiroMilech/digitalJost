import hmac
import secrets
from types import SimpleNamespace

from apiflask import APIBlueprint
from flask import Blueprint, abort, current_app, jsonify, redirect, request, session, url_for
from flask_login import current_user

from app.utils.permissions import get_permission

from backend.platform.vue_shell import render_vue_shell

from .schemas import EventCreate, EventList, EventOut, EventQuery


events_bp = APIBlueprint("events", __name__, url_prefix="/api/v1/events")
events_shell_bp = Blueprint("events_shell", __name__)


class GeneralEventsPermissions:
    """Mapeia as ações de Eventos para o acesso geral já existente."""

    def can(self, actor, action):
        return action in ("events.read", "events.create") and get_permission("GENERAL").can()

    def require(self, actor, action):
        if not self.can(actor, action):
            raise PermissionError("Acesso negado")


def current_actor():
    return SimpleNamespace(id=current_user.id)


def get_events_service():
    return current_app.extensions["events_service"]


def _csrf_token():
    token = session.get("events_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["events_csrf"] = token
    return token


@events_bp.before_request
def authorize_api():
    if not current_user.is_authenticated:
        return jsonify(message="Sessão expirada.", detail={}), 401
    if not get_permission("GENERAL").can():
        return jsonify(message="Acesso negado.", detail={}), 403
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        expected = session.get("events_csrf", "")
        received = request.headers.get("X-CSRF-Token", "")
        if not expected or not received or not hmac.compare_digest(expected, received):
            return jsonify(message="Token de segurança inválido. Atualize a página.", detail={}), 400


@events_bp.errorhandler(PermissionError)
def access_denied(error):
    return jsonify(message="Acesso negado.", detail={}), 403


@events_bp.errorhandler(400)
def bad_request(error):
    return jsonify(message="Requisição inválida.", detail={}), 400


@events_bp.errorhandler(500)
def api_error(error):
    return jsonify(message="Não foi possível concluir a operação.", detail={}), 500


@events_bp.get("")
@events_bp.input(EventQuery, location="query")
@events_bp.output(EventList)
def list_events(query_data):
    return get_events_service().list(query_data, current_actor())


@events_bp.post("")
@events_bp.input(EventCreate)
@events_bp.output(EventOut, status_code=201)
def create_event(json_data):
    return get_events_service().create(json_data, current_actor())


@events_shell_bp.get("/app/")
def app_home():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.url))
    if not get_permission("GENERAL").can():
        abort(403)
    return redirect(url_for("events_shell.events_page"))


@events_shell_bp.get("/app/eventos")
def events_page():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.url))
    if not get_permission("GENERAL").can():
        abort(403)
    return render_vue_shell(
        title="Eventos | Digital JOST",
        csrf_token_provider=_csrf_token,
        unavailable_message="Aplicação de Eventos indisponível.",
    )
