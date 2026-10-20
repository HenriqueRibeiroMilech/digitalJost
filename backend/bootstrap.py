"""Composição do backend moderno a partir da configuração fornecida pela aplicação."""


def init_backend(app, *, config):
    from .platform.database import init_td_database
    from .platform.vue_shell import init_vue_shell
    from .modules import register_modules
    from .modules.demands.storage import DemandAttachmentStorage
    from .integrations.employee_directory import EmployeeDirectory

    init_td_database(app, config)
    app.extensions["backend_employee_directory"] = EmployeeDirectory(config.employee_directory)
    app.extensions["demands_attachment_storage"] = DemandAttachmentStorage(app.instance_path)

    init_vue_shell(app)
    register_modules(app)
