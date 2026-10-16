from apiflask import APIBlueprint
from flask import Blueprint, redirect, url_for

from backend.compatibility import identity
from backend.platform.http import api_error, configure_api, get_service, page_access
from backend.platform.schemas import PaginationQuery
from backend.platform.vue_shell import render_vue_shell

from .schemas import (
    AttendanceCreate, AttendanceDeleted, AttendanceEntries, AttendanceListCreate, AttendanceListDetail,
    AttendanceListOut, AttendanceLists, AttendanceRegistered,
    EventCreate, EventDeleted, EventDetail, EventList, EventOut, EventQuery,
    EventTypeCreate, EventTypeOut, EventTypes,
)
from .services import (
    AttendanceEntryNotFoundError, AttendanceIdentificationError, AttendanceListNotFoundError,
    EventNotFoundError, InvalidEventScheduleError, InvalidEventTypeError,
)


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


@events_bp.errorhandler(InvalidEventTypeError)
def invalid_event_type(error):
    return api_error(422, detail={
        "json": {"event_type_id": ["Selecione um tipo de evento cadastrado."]}
    })


@events_bp.get("/types")
@events_bp.output(EventTypes)
def list_event_types():
    return get_service("events_service").list_event_types(identity.current_actor())


@events_bp.post("/types")
@events_bp.input(EventTypeCreate)
@events_bp.output(EventTypeOut)
def create_event_type(json_data):
    return get_service("events_service").create_event_type(json_data, identity.current_actor())


@events_bp.errorhandler(AttendanceListNotFoundError)
def attendance_list_not_found(error):
    return api_error(404, message="Lista de presença não encontrada neste evento.")


@events_bp.errorhandler(AttendanceEntryNotFoundError)
def attendance_entry_not_found(error):
    return api_error(404, message="Participante não encontrado nesta lista.")


@events_bp.errorhandler(AttendanceIdentificationError)
def attendance_identification_failed(error):
    unavailable = error.status == "unavailable"
    message = (
        "Não foi possível consultar os participantes agora. Esta leitura não foi registrada."
        if unavailable else
        "Leitura não reconhecida. Mantenha o crachá encostado e tente novamente. Esta leitura não foi registrada."
    )
    return api_error(503 if unavailable else 422, message=message, detail={"lookup_status": error.status})


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


@events_bp.get("/<int:event_id>/attendance-lists")
@events_bp.input(PaginationQuery, location="query")
@events_bp.output(AttendanceLists)
def list_attendance_lists(event_id, query_data):
    return get_service("events_service").list_attendance_lists(event_id, query_data, identity.current_actor())


@events_bp.post("/<int:event_id>/attendance-lists")
@events_bp.input(AttendanceListCreate)
@events_bp.output(AttendanceListOut, status_code=201)
def create_attendance_list(event_id, json_data):
    return get_service("events_service").create_attendance_list(event_id, json_data, identity.current_actor())


@events_bp.get("/<int:event_id>/attendance-lists/<int:list_id>")
@events_bp.output(AttendanceListDetail)
def get_attendance_list(event_id, list_id):
    return get_service("events_service").get_attendance_list(event_id, list_id, identity.current_actor())


@events_bp.put("/<int:event_id>/attendance-lists/<int:list_id>")
@events_bp.input(AttendanceListCreate)
@events_bp.output(AttendanceListOut)
def update_attendance_list(event_id, list_id, json_data):
    return get_service("events_service").update_attendance_list(event_id, list_id, json_data, identity.current_actor())


@events_bp.delete("/<int:event_id>/attendance-lists/<int:list_id>")
@events_bp.output(AttendanceDeleted)
def delete_attendance_list(event_id, list_id):
    return get_service("events_service").delete_attendance_list(event_id, list_id, identity.current_actor())


@events_bp.get("/<int:event_id>/attendance-lists/<int:list_id>/entries")
@events_bp.input(PaginationQuery, location="query")
@events_bp.output(AttendanceEntries)
def list_attendance_entries(event_id, list_id, query_data):
    return get_service("events_service").list_attendance_entries(event_id, list_id, query_data, identity.current_actor())


@events_bp.post("/<int:event_id>/attendance-lists/<int:list_id>/entries")
@events_bp.input(AttendanceCreate)
@events_bp.output(AttendanceRegistered)
def register_attendance(event_id, list_id, json_data):
    return get_service("events_service").register_attendance(event_id, list_id, json_data, identity.current_actor())


@events_bp.delete("/<int:event_id>/attendance-lists/<int:list_id>/entries/<int:entry_id>")
@events_bp.output(AttendanceDeleted)
def delete_attendance_entry(event_id, list_id, entry_id):
    return get_service("events_service").delete_attendance_entry(event_id, list_id, entry_id, identity.current_actor())


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
