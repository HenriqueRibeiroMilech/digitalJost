from . import repository


class EventNotFoundError(LookupError):
    """O evento não existe ou já foi excluído."""


class InvalidEventScheduleError(ValueError):
    """O fim precisa ser posterior ao início do evento."""


class EventsService:
    def __init__(self, engine, permissions):
        self.engine = engine
        self.permissions = permissions

    def list(self, query, actor):
        self.permissions.require(actor, "events.read")
        with self.engine.connect() as connection:
            items, total = repository.list_events(
                connection,
                page=query.page,
                per_page=query.per_page,
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
            event = repository.get_event(connection, event_id)
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

    @staticmethod
    def _validate_schedule(data):
        if data.ends_at <= data.starts_at:
            raise InvalidEventScheduleError()
