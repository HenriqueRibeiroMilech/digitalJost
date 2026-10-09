"""Composição do backend moderno com dependências fornecidas pela aplicação."""


def init_backend(app, *, td_engine):
    from .modules import register_modules
    from .modules.events.routes import GeneralEventsPermissions
    from .modules.events.services import EventsService

    app.extensions["events_service"] = EventsService(
        td_engine,
        GeneralEventsPermissions(),
    )

    register_modules(app)
