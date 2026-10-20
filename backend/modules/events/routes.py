from apiflask import APIBlueprint
from flask import Blueprint, current_app, redirect, send_file, url_for

from backend.compatibility import identity
from backend.platform.database import get_td_engine
from backend.platform.http import api_error, configure_api, page_access
from backend.platform.identity import RolePermissions
from backend.platform.schemas import PaginationQuery
from backend.platform.vue_shell import render_vue_shell

from . import repository, services
from .schemas import (
    AttendanceCreate, AttendanceDeleted, AttendanceEntries, AttendanceListCreate, AttendanceListDetail,
    AttendanceListOut, AttendanceLists, AttendanceRegistered,
    EventCreate, EventDeleted, EventDetail, EventList, EventOut, EventQuery,
    EventTypeCreate, EventTypeDeleted, EventTypeOut, EventTypes,
)
from .services import (
    AttendanceEntryNotFoundError, AttendanceIdentificationError, AttendanceListNotFoundError,
    AttendancePdfUnavailableError,
    EventNotFoundError, EventTypeInUseError, EventTypeNotFoundError,
    InvalidEventScheduleError, InvalidEventTypeError,
)


ACTION_ROLES = {
    "events.read": "GENERAL",
    "events.create": "GENERAL",
    "events.update": "GENERAL",
    "events.delete": "GENERAL",
    "events.types.create": "GENERAL",
    "events.types.delete": "GENERAL",
    "events.attendance.read": "GENERAL",
    "events.attendance.export": "GENERAL",
    "events.attendance.create": "GENERAL",
    "events.attendance.register": "GENERAL",
    "events.attendance.update": "GENERAL",
    "events.attendance.delete": "GENERAL",
    "events.attendance.delete_entry": "GENERAL",
}

events_bp = APIBlueprint("events", __name__, url_prefix="/api/v1/events")
events_shell_bp = Blueprint("events_shell", __name__)
configure_api(events_bp, identity=identity, permission="GENERAL")


def _permissions():
    return RolePermissions(identity.can_access, ACTION_ROLES)


def _service_deps():
    return {
        "engine": get_td_engine(),
        "permissions": _permissions(),
    }


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
    actor = identity.current_actor()
    permissions = _permissions()
    permissions.require(actor, "events.read")
    with get_td_engine().connect() as connection:
        items = repository.list_event_types(connection)
    return {
        "items": items,
        "can_create": permissions.can(actor, "events.types.create"),
        "can_delete": permissions.can(actor, "events.types.delete"),
    }


@events_bp.post("/types")
@events_bp.input(EventTypeCreate)
@events_bp.output(EventTypeOut)
def create_event_type(json_data):
    return services.create_event_type(
        json_data, identity.current_actor(), **_service_deps(),
    )


@events_bp.errorhandler(EventTypeNotFoundError)
def event_type_not_found(error):
    return api_error(404, message="Tipo de evento não encontrado ou já excluído.")


@events_bp.errorhandler(EventTypeInUseError)
def event_type_in_use(error):
    return api_error(409, message="Este tipo está em uso por eventos. Altere o tipo desses eventos antes de excluí-lo.")


@events_bp.delete("/types/<int:event_type_id>")
@events_bp.output(EventTypeDeleted)
def delete_event_type(event_type_id):
    return services.delete_event_type(
        event_type_id, identity.current_actor(), **_service_deps(),
    )


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


@events_bp.errorhandler(AttendancePdfUnavailableError)
def attendance_pdf_unavailable(error):
    return api_error(503, message="Geração de PDF indisponível. Solicite ao responsável conferir os recursos no servidor.")


@events_bp.get("")
@events_bp.input(EventQuery, location="query")
@events_bp.output(EventList)
def list_events(query_data):
    return services.list_events(
        query_data, identity.current_actor(), **_service_deps(),
    )


@events_bp.post("")
@events_bp.input(EventCreate)
@events_bp.output(EventOut, status_code=201)
def create_event(json_data):
    return services.create_event(
        json_data, identity.current_actor(), **_service_deps(),
    )


@events_bp.get("/<int:event_id>")
@events_bp.output(EventDetail)
def get_event(event_id):
    return services.get_event(
        event_id, identity.current_actor(), **_service_deps(),
    )


@events_bp.put("/<int:event_id>")
@events_bp.input(EventCreate)
@events_bp.output(EventOut)
def update_event(event_id, json_data):
    return services.update_event(
        event_id, json_data, identity.current_actor(), **_service_deps(),
    )


@events_bp.delete("/<int:event_id>")
@events_bp.output(EventDeleted)
def delete_event(event_id):
    return services.delete_event(
        event_id, identity.current_actor(), **_service_deps(),
    )


@events_bp.get("/<int:event_id>/attendance-lists")
@events_bp.input(PaginationQuery, location="query")
@events_bp.output(AttendanceLists)
def list_attendance_lists(event_id, query_data):
    return services.list_attendance_lists(
        event_id, query_data, identity.current_actor(), **_service_deps(),
    )


@events_bp.post("/<int:event_id>/attendance-lists")
@events_bp.input(AttendanceListCreate)
@events_bp.output(AttendanceListOut, status_code=201)
def create_attendance_list(event_id, json_data):
    return services.create_attendance_list(
        event_id, json_data, identity.current_actor(), **_service_deps(),
    )


@events_bp.get("/<int:event_id>/attendance-lists/<int:list_id>")
@events_bp.output(AttendanceListDetail)
def get_attendance_list(event_id, list_id):
    return services.get_attendance_list(
        event_id, list_id, identity.current_actor(), **_service_deps(),
    )


@events_bp.put("/<int:event_id>/attendance-lists/<int:list_id>")
@events_bp.input(AttendanceListCreate)
@events_bp.output(AttendanceListOut)
def update_attendance_list(event_id, list_id, json_data):
    return services.update_attendance_list(
        event_id, list_id, json_data, identity.current_actor(),
        **_service_deps(),
    )


@events_bp.delete("/<int:event_id>/attendance-lists/<int:list_id>")
@events_bp.output(AttendanceDeleted)
def delete_attendance_list(event_id, list_id):
    return services.delete_attendance_list(
        event_id, list_id, identity.current_actor(), **_service_deps(),
    )


@events_bp.get("/<int:event_id>/attendance-lists/<int:list_id>/entries")
@events_bp.input(PaginationQuery, location="query")
@events_bp.output(AttendanceEntries)
def list_attendance_entries(event_id, list_id, query_data):
    return services.list_attendance_entries(
        event_id, list_id, query_data, identity.current_actor(),
        **_service_deps(),
    )


@events_bp.get("/<int:event_id>/attendance-lists/<int:list_id>/pdf")
def export_attendance_pdf(event_id, list_id):
    document = services.export_attendance_pdf(
        event_id, list_id, identity.current_actor(), **_service_deps(),
    )
    response = send_file(
        document, mimetype="application/pdf", as_attachment=True,
        download_name=f"lista-presenca-evento-{event_id}-lista-{list_id}.pdf",
        conditional=False, max_age=0,
    )
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@events_bp.post("/<int:event_id>/attendance-lists/<int:list_id>/entries")
@events_bp.input(AttendanceCreate)
@events_bp.output(AttendanceRegistered)
def register_attendance(event_id, list_id, json_data):
    return services.register_attendance(
        event_id, list_id, json_data, identity.current_actor(),
        **_service_deps(),
        employee_directory=current_app.extensions["backend_employee_directory"],
    )


@events_bp.delete("/<int:event_id>/attendance-lists/<int:list_id>/entries/<int:entry_id>")
@events_bp.output(AttendanceDeleted)
def delete_attendance_entry(event_id, list_id, entry_id):
    return services.delete_attendance_entry(
        event_id, list_id, entry_id, identity.current_actor(),
        **_service_deps(),
    )


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
