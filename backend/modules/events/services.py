from . import repository


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
            "capabilities": {
                "can_create": self.permissions.can(actor, "events.create")
            },
        }

    def create(self, data, actor):
        self.permissions.require(actor, "events.create")
        with self.engine.begin() as connection:
            event = repository.create_event(
                connection,
                name=data.name,
                description=data.description,
                created_by=str(actor.id),
            )
        return event
