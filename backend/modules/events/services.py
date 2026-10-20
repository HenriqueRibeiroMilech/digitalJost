from . import repository


class EventNotFoundError(LookupError):
    """O evento não existe ou já foi excluído."""


class InvalidEventScheduleError(ValueError):
    """O fim precisa ser posterior ao início do evento."""


class InvalidEventTypeError(ValueError):
    """O tipo selecionado não existe."""


class EventTypeNotFoundError(LookupError):
    """O tipo não existe ou já foi excluído."""


class EventTypeInUseError(ValueError):
    """Eventos ainda usam este tipo."""


class AttendanceListNotFoundError(LookupError):
    """A lista não existe neste evento."""


class AttendanceEntryNotFoundError(LookupError):
    """O participante não está nesta lista."""


class AttendancePdfUnavailableError(RuntimeError):
    """Os recursos necessários para gerar o PDF não estão disponíveis."""


class AttendanceIdentificationError(ValueError):
    """A consulta não identificou uma única pessoa; nenhuma presença deve ser gravada."""

    def __init__(self, status):
        super().__init__("Não foi possível identificar o participante.")
        self.status = status


def list_events(query, actor, *, engine, permissions):
    permissions.require(actor, "events.read")
    with engine.connect() as connection:
        now = repository.current_time(connection)
        items, total = repository.list_events(
            connection,
            page=query.page,
            per_page=query.per_page,
            search=query.search,
            statuses=query.status.split(","),
            now=now,
        )
    return {
        "items": items,
        "page": query.page,
        "per_page": query.per_page,
        "total": total,
        "capabilities": _capabilities(actor, permissions),
    }


def get_event(event_id, actor, *, engine, permissions):
    permissions.require(actor, "events.read")
    with engine.connect() as connection:
        event = repository.get_event(connection, event_id, now=repository.current_time(connection))
    if event is None:
        raise EventNotFoundError()
    return {**event, "capabilities": _capabilities(actor, permissions)}


def create_event(data, actor, *, engine, permissions):
    permissions.require(actor, "events.create")
    _validate_schedule(data)
    with engine.begin() as connection:
        _require_event_type(connection, data.event_type_id)
        event = repository.create_event(
            connection,
            name=data.name,
            description=data.description,
            event_type_id=data.event_type_id,
            instructor=data.instructor or None,
            syllabus=data.syllabus or None,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            created_by=str(actor.id),
            now=repository.current_time(connection),
        )
    return event


def update_event(event_id, data, actor, *, engine, permissions):
    permissions.require(actor, "events.update")
    _validate_schedule(data)
    with engine.begin() as connection:
        _require_event_type(connection, data.event_type_id)
        event = repository.update_event(
            connection,
            event_id,
            name=data.name,
            description=data.description,
            event_type_id=data.event_type_id,
            instructor=data.instructor or None,
            syllabus=data.syllabus or None,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            now=repository.current_time(connection),
        )
        if event is None:
            raise EventNotFoundError()
    return event


def delete_event(event_id, actor, *, engine, permissions):
    permissions.require(actor, "events.delete")
    with engine.begin() as connection:
        deleted_id = repository.delete_event(connection, event_id)
        if deleted_id is None:
            raise EventNotFoundError()
    return {"id": deleted_id}


def _capabilities(actor, permissions):
    return {
        "can_create": permissions.can(actor, "events.create"),
        "can_update": permissions.can(actor, "events.update"),
        "can_delete": permissions.can(actor, "events.delete"),
    }


def create_event_type(data, actor, *, engine, permissions):
    permissions.require(actor, "events.types.create")
    with engine.begin() as connection:
        event_type = repository.create_event_type(connection, name=data.name, created_by=str(actor.id))
    return event_type


def delete_event_type(event_type_id, actor, *, engine, permissions):
    permissions.require(actor, "events.types.delete")
    with engine.begin() as connection:
        if repository.lock_event_type(connection, event_type_id) is None:
            raise EventTypeNotFoundError()
        if repository.event_type_in_use(connection, event_type_id):
            raise EventTypeInUseError()
        deleted_id = repository.delete_event_type(connection, event_type_id)
        if deleted_id is None:
            raise EventTypeNotFoundError()
    return {"id": deleted_id}


def _require_event_type(connection, event_type_id):
    if not repository.event_type_exists(connection, event_type_id):
        raise InvalidEventTypeError()


def list_attendance_lists(event_id, query, actor, *, engine, permissions):
    permissions.require(actor, "events.attendance.read")
    with engine.connect() as connection:
        if not repository.event_exists(connection, event_id):
            raise EventNotFoundError()
        items, total = repository.list_attendance_lists(
            connection, event_id, page=query.page, per_page=query.per_page,
        )
    return _attendance_page(items, total, query, actor, permissions)


def create_attendance_list(event_id, data, actor, *, engine, permissions):
    permissions.require(actor, "events.attendance.create")
    with engine.begin() as connection:
        if not repository.event_exists(connection, event_id, lock=True):
            raise EventNotFoundError()
        return repository.create_attendance_list(
            connection, event_id, name=data.name, created_by=str(actor.id),
        )


def get_attendance_list(event_id, list_id, actor, *, engine, permissions):
    permissions.require(actor, "events.attendance.read")
    with engine.connect() as connection:
        attendance_list = _require_attendance_list(connection, event_id, list_id)
    return {**attendance_list, "capabilities": _attendance_capabilities(actor, permissions)}


def update_attendance_list(event_id, list_id, data, actor, *, engine, permissions):
    permissions.require(actor, "events.attendance.update")
    with engine.begin() as connection:
        _require_attendance_list(connection, event_id, list_id, lock=True)
        updated = repository.update_attendance_list(connection, event_id, list_id, name=data.name)
        if updated is None:
            raise AttendanceListNotFoundError()
    return updated


def delete_attendance_list(event_id, list_id, actor, *, engine, permissions):
    permissions.require(actor, "events.attendance.delete")
    with engine.begin() as connection:
        _require_attendance_list(connection, event_id, list_id, lock=True)
        deleted_id = repository.delete_attendance_list(connection, event_id, list_id)
        if deleted_id is None:
            raise AttendanceListNotFoundError()
    return {"id": deleted_id}


def delete_attendance_entry(event_id, list_id, entry_id, actor, *, engine, permissions):
    permissions.require(actor, "events.attendance.delete_entry")
    with engine.begin() as connection:
        _require_attendance_list(connection, event_id, list_id, lock=True)
        deleted_id = repository.delete_attendance_entry(connection, list_id, entry_id)
        if deleted_id is None:
            raise AttendanceEntryNotFoundError()
    return {"id": deleted_id}


def list_attendance_entries(event_id, list_id, query, actor, *, engine, permissions):
    permissions.require(actor, "events.attendance.read")
    with engine.connect() as connection:
        _require_attendance_list(connection, event_id, list_id)
        items, total = repository.list_attendance_entries(
            connection, list_id, page=query.page, per_page=query.per_page,
        )
    return _attendance_page(items, total, query, actor, permissions)


def export_attendance_pdf(event_id, list_id, actor, *, engine, permissions):
    permissions.require(actor, "events.attendance.export")
    with engine.begin() as connection:
        # Mantém cabeçalho e presenças consistentes com as escritas do módulo.
        if not repository.event_exists(connection, event_id, lock=True):
            raise EventNotFoundError()
        attendance_list = _require_attendance_list(connection, event_id, list_id, lock=True)
        now = repository.current_time(connection)
        event = repository.get_event(connection, event_id, now=now)
        entries = repository.export_attendance_entries(connection, list_id)
    # Renderiza em memória, após liberar a conexão e as travas do TD.
    try:
        from .attendance_pdf import build_attendance_pdf
        return build_attendance_pdf(event, attendance_list, entries, generated_at=now)
    except (ImportError, OSError) as error:
        raise AttendancePdfUnavailableError() from error


def register_attendance(event_id, list_id, data, actor, *, engine, permissions, employee_directory):
    permissions.require(actor, "events.attendance.register")
    # Autoriza o recurso antes da consulta externa; não retém conexão/trava SQL no LDAP.
    with engine.connect() as connection:
        _require_attendance_list(connection, event_id, list_id)

    # Revalidar também as repetições: registros antigos não comprovam a leitura atual.
    employee = employee_directory.find_by_badge(data.registration)
    if employee.status not in ("complete", "partial"):
        raise AttendanceIdentificationError(employee.status)
    with engine.begin() as connection:
        # Revalidar após o LDAP: a lista pode ter sido excluída durante a consulta.
        _require_attendance_list(connection, event_id, list_id, lock=True)
        result = repository.register_attendance(
            connection, list_id, registration=data.registration, created_by=str(actor.id),
            name=employee.name, department=employee.department, company=employee.company,
        )
    item = result["item"]
    lookup_status = (
        "complete" if all(item[field] for field in ("name", "department", "company")) else "partial"
    )
    return {**result, "lookup_status": lookup_status}


def _attendance_capabilities(actor, permissions):
    return {
        "can_export": permissions.can(actor, "events.attendance.export"),
        "can_create": permissions.can(actor, "events.attendance.create"),
        "can_register": permissions.can(actor, "events.attendance.register"),
        "can_update": permissions.can(actor, "events.attendance.update"),
        "can_delete": permissions.can(actor, "events.attendance.delete"),
        "can_delete_entry": permissions.can(actor, "events.attendance.delete_entry"),
    }


def _attendance_page(items, total, query, actor, permissions):
    return {
        "items": items, "total": total, "page": query.page, "per_page": query.per_page,
        "capabilities": _attendance_capabilities(actor, permissions),
    }


def _require_attendance_list(connection, event_id, list_id, *, lock=False):
    attendance_list = repository.get_attendance_list(connection, event_id, list_id, lock=lock)
    if attendance_list is None:
        raise AttendanceListNotFoundError()
    return attendance_list


def _validate_schedule(data):
    if data.ends_at <= data.starts_at:
        raise InvalidEventScheduleError()
