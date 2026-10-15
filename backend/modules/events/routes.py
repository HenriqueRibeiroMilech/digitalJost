from apiflask import APIBlueprint
from flask import Blueprint, redirect, url_for

from backend.compatibility import identity
from backend.platform.http import api_error, configure_api, get_service, page_access
from backend.platform.vue_shell import render_vue_shell

from .schemas import EventCreate, EventDeleted, EventDetail, EventList, EventOut, EventQuery
from .services import EventNotFoundError, InvalidEventScheduleError


events_bp = APIBlueprint("events", __name__, url_prefix="/api/v1/events")
events_shell_bp = Blueprint("events_shell", __name__)
configure_api(events_bp, identity=identity, permission="GENERAL")


@events_bp.errorhandler(EventNotFoundError)
def event_not_found(error):
    return api_error(404, message="Evento não encontrado ou já excluído.")


@events_bp.errorhandler(InvalidEventScheduleError)
def invalid_event_schedule(error):
    return api_error(422, detail={
        "json": {"ends_at": ["O fim deve ser posterior ao início do evento."]}
    })


@events_bp.get("")
@events_bp.input(EventQuery, location="query")
@events_bp.output(EventList)
def list_events(query_data):
    return get_service("events_service").list(query_data, identity.current_actor())


@events_bp.post("")
@events_bp.input(EventCreate)
@events_bp.output(EventOut, status_code=201)
def create_event(json_data):
    return get_service("events_service").create(json_data, identity.current_actor())


@events_bp.get("/<int:event_id>")
@events_bp.output(EventDetail)
def get_event(event_id):
    return get_service("events_service").get(event_id, identity.current_actor())


@events_bp.put("/<int:event_id>")
@events_bp.input(EventCreate)
@events_bp.output(EventOut)
def update_event(event_id, json_data):
    return get_service("events_service").update(event_id, json_data, identity.current_actor())


@events_bp.delete("/<int:event_id>")
@events_bp.output(EventDeleted)
def delete_event(event_id):
    return get_service("events_service").delete(event_id, identity.current_actor())


@events_shell_bp.get("/app/")
@page_access(identity=identity, permission="GENERAL")
def app_home():
    return redirect(url_for("events_shell.events_page"))


@events_shell_bp.get("/app/eventos")
@page_access(identity=identity, permission="GENERAL")
def events_page():
    return render_vue_shell(
        title="Eventos | Digital JOST",
        unavailable_message="Aplicação de Eventos indisponível.",
    )
