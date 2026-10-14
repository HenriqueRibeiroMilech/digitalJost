from apiflask import APIBlueprint
from flask import Blueprint, redirect, url_for

from backend.compatibility import identity
from backend.platform.http import configure_api, get_service, page_access
from backend.platform.vue_shell import render_vue_shell

from .schemas import EventCreate, EventList, EventOut, EventQuery


events_bp = APIBlueprint("events", __name__, url_prefix="/api/v1/events")
events_shell_bp = Blueprint("events_shell", __name__)
configure_api(events_bp, identity=identity, permission="GENERAL")


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
