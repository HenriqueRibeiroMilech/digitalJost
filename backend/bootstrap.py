"""Composição do backend moderno a partir da configuração fornecida pela aplicação."""


def init_backend(app, *, config):
    from .platform.database import init_td_database
    from .platform.vue_shell import init_vue_shell
    from .modules import register_modules
    from .compatibility import identity
    from .platform.identity import RolePermissions
    from .modules.events.services import EventsService
    from .modules.demands.services import DemandsService
    from .modules.demands.storage import DemandAttachmentStorage
    from .integrations.employee_directory import EmployeeDirectory

    td_engine = init_td_database(app, config)
    app.extensions["events_service"] = EventsService(
        td_engine,
        RolePermissions(identity.can_access, {
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
        }),
        EmployeeDirectory(config.employee_directory),
    )

    app.extensions["demands_service"] = DemandsService(
        td_engine,
        RolePermissions(identity.can_access, {
            "demands.read": "GENERAL",
            "demands.create": "GENERAL",
            "demands.update": "GENERAL",
        }),
        DemandAttachmentStorage(app.instance_path),
    )

    init_vue_shell(app)
    register_modules(app)
