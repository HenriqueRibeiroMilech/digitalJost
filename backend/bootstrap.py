"""Composição do backend moderno a partir da configuração fornecida pela aplicação."""


def init_backend(app, *, config):
    from .platform.database import init_td_database
    from .platform.vue_shell import init_vue_shell
    from .modules import register_modules
    from .compatibility import identity
    from .platform.identity import RolePermissions
    from .modules.events.services import EventsService

    td_engine = init_td_database(app, config)
    app.extensions["events_service"] = EventsService(
        td_engine,
        RolePermissions(identity.can_access, {
            "events.read": "GENERAL",
            "events.create": "GENERAL",
            "events.update": "GENERAL",
            "events.delete": "GENERAL",
        }),
    )

    init_vue_shell(app)
    register_modules(app)
