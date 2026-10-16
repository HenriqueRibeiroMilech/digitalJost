from . import repository


class EventNotFoundError(LookupError):
    """O evento não existe ou já foi excluído."""


class InvalidEventScheduleError(ValueError):
    """O fim precisa ser posterior ao início do evento."""


class AttendanceListNotFoundError(LookupError):
    """A lista não existe neste evento."""


class AttendanceIdentificationError(ValueError):
    """A consulta não identificou uma única pessoa; nenhuma presença deve ser gravada."""

    def __init__(self, status):
        super().__init__("Não foi possível identificar o participante.")
        self.status = status


class EventsService:
    def __init__(self, engine, permissions, employee_directory):
        self.engine = engine
        self.permissions = permissions
        self.employee_directory = employee_directory

    def list(self, query, actor):
        self.permissions.require(actor, "events.read")
        with self.engine.connect() as connection:
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
            "capabilities": self._capabilities(actor),
        }

    def get(self, event_id, actor):
        self.permissions.require(actor, "events.read")
        with self.engine.connect() as connection:
            event = repository.get_event(connection, event_id, now=repository.current_time(connection))
        if event is None:
            raise EventNotFoundError()
        return {**event, "capabilities": self._capabilities(actor)}

    def create(self, data, actor):
        self.permissions.require(actor, "events.create")
        self._validate_schedule(data)
        with self.engine.begin() as connection:
            event = repository.create_event(
                connection,
                name=data.name,
                description=data.description,
                starts_at=data.starts_at,
                ends_at=data.ends_at,
                created_by=str(actor.id),
                now=repository.current_time(connection),
            )
        return event

    def update(self, event_id, data, actor):
        self.permissions.require(actor, "events.update")
        self._validate_schedule(data)
        with self.engine.begin() as connection:
            event = repository.update_event(
                connection,
                event_id,
                name=data.name,
                description=data.description,
                starts_at=data.starts_at,
                ends_at=data.ends_at,
                now=repository.current_time(connection),
            )
            if event is None:
                raise EventNotFoundError()
        return event

    def delete(self, event_id, actor):
        self.permissions.require(actor, "events.delete")
        with self.engine.begin() as connection:
            deleted_id = repository.delete_event(connection, event_id)
            if deleted_id is None:
                raise EventNotFoundError()
        return {"id": deleted_id}

    def _capabilities(self, actor):
        return {
            "can_create": self.permissions.can(actor, "events.create"),
            "can_update": self.permissions.can(actor, "events.update"),
            "can_delete": self.permissions.can(actor, "events.delete"),
        }

    def list_attendance_lists(self, event_id, query, actor):
        self.permissions.require(actor, "events.attendance.read")
        with self.engine.connect() as connection:
            if not repository.event_exists(connection, event_id):
                raise EventNotFoundError()
            items, total = repository.list_attendance_lists(
                connection, event_id, page=query.page, per_page=query.per_page,
            )
        return self._attendance_page(items, total, query, actor)

    def create_attendance_list(self, event_id, data, actor):
        self.permissions.require(actor, "events.attendance.create")
        with self.engine.begin() as connection:
            if not repository.event_exists(connection, event_id, lock=True):
                raise EventNotFoundError()
            return repository.create_attendance_list(
                connection, event_id, name=data.name, created_by=str(actor.id),
            )

    def get_attendance_list(self, event_id, list_id, actor):
        self.permissions.require(actor, "events.attendance.read")
        with self.engine.connect() as connection:
            attendance_list = self._require_attendance_list(connection, event_id, list_id)
        return {**attendance_list, "capabilities": self._attendance_capabilities(actor)}

    def list_attendance_entries(self, event_id, list_id, query, actor):
        self.permissions.require(actor, "events.attendance.read")
        with self.engine.connect() as connection:
            self._require_attendance_list(connection, event_id, list_id)
            items, total = repository.list_attendance_entries(
                connection, list_id, page=query.page, per_page=query.per_page,
            )
        return self._attendance_page(items, total, query, actor)

    def register_attendance(self, event_id, list_id, data, actor):
        self.permissions.require(actor, "events.attendance.register")
        # Autoriza o recurso antes da consulta externa; não retém conexão/trava SQL no LDAP.
        with self.engine.connect() as connection:
            self._require_attendance_list(connection, event_id, list_id)

        # Revalidar também as repetições: registros antigos não comprovam a leitura atual.
        employee = self.employee_directory.find_by_badge(data.registration)
        if employee.status not in ("complete", "partial"):
            raise AttendanceIdentificationError(employee.status)
        with self.engine.begin() as connection:
            # Revalidar após o LDAP: a lista pode ter sido excluída durante a consulta.
            self._require_attendance_list(connection, event_id, list_id, lock=True)
            result = repository.register_attendance(
                connection, list_id, registration=data.registration, created_by=str(actor.id),
                name=employee.name, department=employee.department, company=employee.company, shift=employee.shift,
            )
        item = result["item"]
        lookup_status = (
            "complete" if all(item[field] for field in ("name", "department", "company", "shift")) else "partial"
        )
        return {**result, "lookup_status": lookup_status}

    def _attendance_capabilities(self, actor):
        return {
            "can_create": self.permissions.can(actor, "events.attendance.create"),
            "can_register": self.permissions.can(actor, "events.attendance.register"),
        }

    def _attendance_page(self, items, total, query, actor):
        return {
            "items": items, "total": total, "page": query.page, "per_page": query.per_page,
            "capabilities": self._attendance_capabilities(actor),
        }

    @staticmethod
    def _require_attendance_list(connection, event_id, list_id, *, lock=False):
        attendance_list = repository.get_attendance_list(connection, event_id, list_id, lock=lock)
        if attendance_list is None:
            raise AttendanceListNotFoundError()
        return attendance_list

    @staticmethod
    def _validate_schedule(data):
        if data.ends_at <= data.starts_at:
            raise InvalidEventScheduleError()
