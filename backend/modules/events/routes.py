from apiflask import APIBlueprint
from flask import Blueprint, current_app, redirect, send_file, url_for
from sqlalchemy import case, delete, func, or_, select, update

from backend.shared import identity
from backend.shared.database import get_td_session_factory, literal_contains, paginate
from backend.shared.http import ApiProblem, action_access, configure_api, page_access
from backend.shared.identity import RolePermissions
from backend.shared.schemas import PaginationQuery
from backend.shared.vue_shell import render_vue_shell

from .models import AttendanceEntry, AttendanceList, Event, EventType
from .schemas import (
    AttendanceCreate, AttendanceDeleted, AttendanceEntries, AttendanceListCreate, AttendanceListDetail,
    AttendanceListOut, AttendanceLists, AttendanceOut, AttendanceRegistered,
    EventCreate, EventDeleted, EventDetail, EventList, EventOut, EventQuery,
    EventTypeCreate, EventTypeDeleted, EventTypeOut, EventTypes,
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
permissions = RolePermissions(identity.can_access, ACTION_ROLES)
require_action = action_access(identity=identity, permissions=permissions)
events_bp = APIBlueprint("events", __name__, url_prefix="/api/v1/events")
events_shell_bp = Blueprint("events_shell", __name__)
configure_api(events_bp, identity=identity, permission="GENERAL")


@events_bp.get("/types")
@require_action("events.read")
@events_bp.output(EventTypes)
def list_event_types():
    sessions = get_td_session_factory()
    with sessions() as session:
        items = session.execute(select(EventType.id, EventType.name).order_by(EventType.name, EventType.id))
        # Copia os campos públicos antes de fechar a sessão usada pela consulta.
        result = {"items": [dict(row) for row in items.mappings()]}
    actor = identity.current_actor()
    return {
        **result,
        "can_create": permissions.can(actor, "events.types.create"),
        "can_delete": permissions.can(actor, "events.types.delete"),
    }


@events_bp.post("/types")
@require_action("events.types.create")
@events_bp.input(EventTypeCreate)
@events_bp.output(EventTypeOut)
def create_event_type(json_data):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        # A trava de intervalo e a chave única preservam o cadastro pelo mesmo nome.
        existing = session.execute(
            select(EventType.id, EventType.name).where(EventType.name == json_data.name)
            .with_hint(EventType, "WITH (UPDLOCK, HOLDLOCK)", "mssql"),
        ).mappings().one_or_none()
        if existing is not None:
            result = dict(existing)
        else:
            event_type = EventType(name=json_data.name, created_by=str(identity.current_actor().id))
            session.add(event_type)
            session.flush()
            result = EventTypeOut.model_validate(event_type, from_attributes=True).model_dump()
    return result


@events_bp.delete("/types/<int:event_type_id>")
@require_action("events.types.delete")
@events_bp.output(EventTypeDeleted)
def delete_event_type(event_type_id):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        # A trava coordena a exclusão com as rotas que vinculam eventos a este tipo.
        existing = session.scalar(
            select(EventType.id).where(EventType.id == event_type_id)
            .with_hint(EventType, "WITH (XLOCK, HOLDLOCK)", "mssql"),
        )
        if existing is None:
            raise ApiProblem(404, "Tipo de evento não encontrado ou já excluído.")
        if session.scalar(select(Event.id).where(Event.event_type_id == event_type_id).limit(1)) is not None:
            raise ApiProblem(409, "Este tipo está em uso por eventos. Altere o tipo desses eventos antes de excluí-lo.")
        deleted_id = session.scalar(delete(EventType).where(EventType.id == event_type_id).returning(EventType.id))
        if deleted_id is None:
            raise ApiProblem(404, "Tipo de evento não encontrado ou já excluído.")
    return {"id": deleted_id}


@events_bp.get("")
@require_action("events.read")
@events_bp.input(EventQuery, location="query")
@events_bp.output(EventList)
def list_events(query_data):
    sessions = get_td_session_factory()
    with sessions() as session:
        # Filtros e status usam o relógio do banco, evitando depender do horário do navegador.
        events = _event_query(session.scalar(select(func.sysdatetime()))).subquery()
        statement = select(events).where(
            events.c.status.in_(query_data.status.split(",")),
            events.c.name.like(literal_contains(query_data.search), escape="~"),
        ).order_by(events.c.id.desc())
        result = paginate(session, statement, query_data)
    return {**result, "capabilities": _capabilities()}


@events_bp.post("")
@require_action("events.create")
@events_bp.input(EventCreate)
@events_bp.output(EventOut, status_code=201)
def create_event(json_data):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        _validate_event(session, json_data)
        now = session.scalar(select(func.sysdatetime()))
        event = Event(**_event_values(json_data), created_by=str(identity.current_actor().id))
        session.add(event)
        # flush obtém o ID; o bloco begin confirma a gravação antes do retorno de sucesso.
        session.flush()
        result = _event(session, event.id, now=now)
    return result


@events_bp.get("/<int:event_id>")
@require_action("events.read")
@events_bp.output(EventDetail)
def get_event(event_id):
    sessions = get_td_session_factory()
    with sessions() as session:
        result = _event(session, event_id)
    return {**result, "capabilities": _capabilities()}


@events_bp.put("/<int:event_id>")
@require_action("events.update")
@events_bp.input(EventCreate)
@events_bp.output(EventOut)
def update_event(event_id, json_data):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        _validate_event(session, json_data)
        now = session.scalar(select(func.sysdatetime()))
        updated_id = session.scalar(
            update(Event).where(Event.id == event_id).values(**_event_values(json_data)).returning(Event.id),
        )
        if updated_id is None:
            raise ApiProblem(404, "Evento não encontrado ou já excluído.")
        result = _event(session, updated_id, now=now)
    return result


@events_bp.delete("/<int:event_id>")
@require_action("events.delete")
@events_bp.output(EventDeleted)
def delete_event(event_id):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        deleted_id = session.scalar(delete(Event).where(Event.id == event_id).returning(Event.id))
        if deleted_id is None:
            raise ApiProblem(404, "Evento não encontrado ou já excluído.")
    return {"id": deleted_id}


@events_bp.get("/<int:event_id>/attendance-lists")
@require_action("events.attendance.read")
@events_bp.input(PaginationQuery, location="query")
@events_bp.output(AttendanceLists)
def list_attendance_lists(event_id, query_data):
    sessions = get_td_session_factory()
    with sessions() as session:
        _require_event(session, event_id)
        result = paginate(session, _lists_query().where(AttendanceList.event_id == event_id)
                          .order_by(AttendanceList.id.desc()), query_data)
    return {**result, "capabilities": _attendance_capabilities()}


@events_bp.post("/<int:event_id>/attendance-lists")
@require_action("events.attendance.create")
@events_bp.input(AttendanceListCreate)
@events_bp.output(AttendanceListOut, status_code=201)
def create_attendance_list(event_id, json_data):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        _require_event(session, event_id, lock=True)
        attendance_list = AttendanceList(
            event_id=event_id, name=json_data.name, created_by=str(identity.current_actor().id),
        )
        session.add(attendance_list)
        session.flush()
        result = {"id": attendance_list.id, "event_id": event_id, "name": attendance_list.name, "total": 0}
    return result


@events_bp.get("/<int:event_id>/attendance-lists/<int:list_id>")
@require_action("events.attendance.read")
@events_bp.output(AttendanceListDetail)
def get_attendance_list(event_id, list_id):
    sessions = get_td_session_factory()
    with sessions() as session:
        result = _attendance_list(session, event_id, list_id)
    return {**result, "capabilities": _attendance_capabilities()}


@events_bp.put("/<int:event_id>/attendance-lists/<int:list_id>")
@require_action("events.attendance.update")
@events_bp.input(AttendanceListCreate)
@events_bp.output(AttendanceListOut)
def update_attendance_list(event_id, list_id, json_data):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        _attendance_list(session, event_id, list_id, lock=True)
        session.execute(update(AttendanceList).where(
            AttendanceList.id == list_id, AttendanceList.event_id == event_id,
        ).values(name=json_data.name))
        result = _attendance_list(session, event_id, list_id)
    return result


@events_bp.delete("/<int:event_id>/attendance-lists/<int:list_id>")
@require_action("events.attendance.delete")
@events_bp.output(AttendanceDeleted)
def delete_attendance_list(event_id, list_id):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        _attendance_list(session, event_id, list_id, lock=True)
        deleted_id = session.scalar(delete(AttendanceList).where(
            AttendanceList.id == list_id, AttendanceList.event_id == event_id,
        ).returning(AttendanceList.id))
        if deleted_id is None:
            raise ApiProblem(404, "Lista de presença não encontrada neste evento.")
    return {"id": deleted_id}


@events_bp.get("/<int:event_id>/attendance-lists/<int:list_id>/entries")
@require_action("events.attendance.read")
@events_bp.input(PaginationQuery, location="query")
@events_bp.output(AttendanceEntries)
def list_attendance_entries(event_id, list_id, query_data):
    sessions = get_td_session_factory()
    with sessions() as session:
        _attendance_list(session, event_id, list_id)
        result = paginate(session, _entries_query().where(AttendanceEntry.list_id == list_id)
                          .order_by(AttendanceEntry.id.desc()), query_data)
    return {**result, "capabilities": _attendance_capabilities()}


@events_bp.get("/<int:event_id>/attendance-lists/<int:list_id>/pdf")
@require_action("events.attendance.export")
def export_attendance_pdf(event_id, list_id):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        _require_event(session, event_id, lock=True)
        attendance_list = _attendance_list(session, event_id, list_id, lock=True)
        now = session.scalar(select(func.sysdatetime()))
        event = _event(session, event_id, now=now)
        # A exportação inclui a lista inteira, independentemente da página aberta na tela.
        entries = [dict(row) for row in session.execute(
            _entries_query().where(AttendanceEntry.list_id == list_id).order_by(AttendanceEntry.id.desc()),
        ).mappings()]
    # O PDF é montado em memória depois de liberar conexão e travas.
    try:
        from .attendance_pdf import build_attendance_pdf
        document = build_attendance_pdf(event, attendance_list, entries, generated_at=now)
    except (ImportError, OSError) as error:
        raise ApiProblem(503, "Geração de PDF indisponível. Solicite ao responsável conferir os recursos no servidor.") from error
    response = send_file(document, mimetype="application/pdf", as_attachment=True,
                         download_name=f"lista-presenca-evento-{event_id}-lista-{list_id}.pdf",
                         conditional=False, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@events_bp.post("/<int:event_id>/attendance-lists/<int:list_id>/entries")
@require_action("events.attendance.register")
@events_bp.input(AttendanceCreate)
@events_bp.output(AttendanceRegistered)
def register_attendance(event_id, list_id, json_data):
    sessions = get_td_session_factory()
    with sessions() as session:
        _attendance_list(session, event_id, list_id)
    # Nenhuma conexão SQL fica retida durante o LDAP, inclusive em repetições.
    directory = current_app.extensions["backend_employee_directory"]
    employee = directory.find_by_badge(json_data.registration)
    if employee.status not in ("complete", "partial"):
        unavailable = employee.status == "unavailable"
        message = ("Não foi possível consultar os participantes agora. Esta leitura não foi registrada."
                   if unavailable else
                   "Leitura não reconhecida. Mantenha o crachá encostado e tente novamente. Esta leitura não foi registrada.")
        raise ApiProblem(503 if unavailable else 422, message, detail={"lookup_status": employee.status})
    with sessions.begin() as session:
        # O estado pode ter mudado durante o LDAP; revalida a lista e coordena suas escritas.
        _attendance_list(session, event_id, list_id, lock=True)
        # Os quatro primeiros dígitos variam por empresa; a comparação usa os oito finais.
        existing = session.execute(_entries_query().where(
            AttendanceEntry.list_id == list_id,
            func.right(AttendanceEntry.registration, 8) == json_data.registration[4:],
        ).order_by(AttendanceEntry.id).limit(1)).mappings().one_or_none()
        values = {"name": employee.name, "department": employee.department, "company": employee.company}
        if existing is not None:
            item = dict(existing)
            # Releituras só completam campos vazios, preservando os dados já registrados.
            if any(values[field] and not item[field] for field in values):
                item = dict(session.execute(update(AttendanceEntry).where(
                    AttendanceEntry.id == item["id"], AttendanceEntry.list_id == list_id,
                ).values(**{
                    field: func.coalesce(func.nullif(getattr(AttendanceEntry, field), ""), value)
                    for field, value in values.items()
                }).returning(*_entry_columns())).mappings().one())
            created = False
        else:
            entry = AttendanceEntry(list_id=list_id, registration=json_data.registration,
                                    created_by=str(identity.current_actor().id), **values)
            session.add(entry)
            session.flush()
            item = AttendanceOut.model_validate(entry, from_attributes=True).model_dump()
            created = True
    lookup_status = "complete" if all(item[field] for field in values) else "partial"
    return {"item": item, "created": created, "lookup_status": lookup_status}


@events_bp.delete("/<int:event_id>/attendance-lists/<int:list_id>/entries/<int:entry_id>")
@require_action("events.attendance.delete_entry")
@events_bp.output(AttendanceDeleted)
def delete_attendance_entry(event_id, list_id, entry_id):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        _attendance_list(session, event_id, list_id, lock=True)
        deleted_id = session.scalar(delete(AttendanceEntry).where(
            AttendanceEntry.id == entry_id, AttendanceEntry.list_id == list_id,
        ).returning(AttendanceEntry.id))
        if deleted_id is None:
            raise ApiProblem(404, "Participante não encontrado nesta lista.")
    return {"id": deleted_id}


def _event_query(now):
    # O status é calculado pelo período; não existe uma gravação só para avançá-lo com o tempo.
    status = case(
        (or_(Event.starts_at.is_(None), Event.ends_at.is_(None)), "unscheduled"),
        (Event.ends_at <= now, "completed"),
        (Event.starts_at <= now, "ongoing"),
        else_="upcoming",
    )
    return select(
        Event.id, Event.name, Event.description, Event.starts_at, Event.ends_at,
        Event.event_type_id, EventType.name.label("event_type_name"), Event.instructor,
        Event.syllabus, status.label("status"),
    ).select_from(Event).outerjoin(EventType, EventType.id == Event.event_type_id)


def _event(session, event_id, *, now=None):
    if now is None:
        now = session.scalar(select(func.sysdatetime()))
    row = session.execute(_event_query(now).where(Event.id == event_id)).mappings().one_or_none()
    if row is None:
        raise ApiProblem(404, "Evento não encontrado ou já excluído.")
    return dict(row)


def _event_values(data):
    return {**data.model_dump(), "instructor": data.instructor or None, "syllabus": data.syllabus or None}


def _validate_event(session, data):
    if data.ends_at <= data.starts_at:
        raise ApiProblem(422, detail={"json": {"ends_at": ["O fim deve ser posterior ao início do evento."]}})
    if session.scalar(select(EventType.id).where(EventType.id == data.event_type_id)
                      .with_hint(EventType, "WITH (HOLDLOCK)", "mssql")) is None:
        raise ApiProblem(422, detail={"json": {"event_type_id": ["Selecione um tipo de evento cadastrado."]}})


def _require_event(session, event_id, *, lock=False):
    statement = select(Event.id).where(Event.id == event_id)
    if lock:
        statement = statement.with_hint(Event, "WITH (HOLDLOCK)", "mssql")
    if session.scalar(statement) is None:
        raise ApiProblem(404, "Evento não encontrado ou já excluído.")


def _lists_query():
    # O total de presenças vem na mesma consulta das listas, sem outra chamada por item.
    total = select(func.count()).select_from(AttendanceEntry).where(
        AttendanceEntry.list_id == AttendanceList.id,
    ).correlate(AttendanceList).scalar_subquery()
    return select(AttendanceList.id, AttendanceList.event_id, AttendanceList.name, total.label("total"))


def _attendance_list(session, event_id, list_id, *, lock=False):
    statement = _lists_query().where(AttendanceList.id == list_id, AttendanceList.event_id == event_id)
    if lock:
        statement = statement.with_hint(AttendanceList, "WITH (UPDLOCK, HOLDLOCK)", "mssql")
    row = session.execute(statement).mappings().one_or_none()
    if row is None:
        raise ApiProblem(404, "Lista de presença não encontrada neste evento.")
    return dict(row)


def _entry_columns():
    return (AttendanceEntry.id, AttendanceEntry.registration, AttendanceEntry.name,
            AttendanceEntry.department, AttendanceEntry.company)


def _entries_query():
    return select(*_entry_columns())


def _capabilities():
    actor = identity.current_actor()
    return {"can_create": permissions.can(actor, "events.create"),
            "can_update": permissions.can(actor, "events.update"),
            "can_delete": permissions.can(actor, "events.delete")}


def _attendance_capabilities():
    actor = identity.current_actor()
    return {"can_export": permissions.can(actor, "events.attendance.export"),
            "can_create": permissions.can(actor, "events.attendance.create"),
            "can_register": permissions.can(actor, "events.attendance.register"),
            "can_update": permissions.can(actor, "events.attendance.update"),
            "can_delete": permissions.can(actor, "events.attendance.delete"),
            "can_delete_entry": permissions.can(actor, "events.attendance.delete_entry")}


@events_shell_bp.get("/app/")
@page_access(identity=identity, permission="GENERAL")
def app_home():
    return redirect(url_for("events_shell.events_page"))


@events_shell_bp.get("/app/eventos")
@page_access(identity=identity, permission="GENERAL")
def events_page():
    return render_vue_shell(title="Eventos | Digital JOST", unavailable_message="Aplicação de Eventos indisponível.")
