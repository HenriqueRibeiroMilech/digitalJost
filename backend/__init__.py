"""Composição do backend moderno do Digital JOST, chamada pela aplicação."""


def init_backend(app, *, config):
    # Importar o pacote backend não deve montar recursos; a factory chama esta função.
    from .shared.database import init_td_database
    from .shared.vue_shell import init_vue_shell
    from .modules import register_modules
    from .modules.demands.storage import DemandAttachmentStorage
    from .shared.employee_directory import EmployeeDirectory

    init_td_database(app, config)
    app.extensions["backend_employee_directory"] = EmployeeDirectory(config.employee_directory)
    app.extensions["demands_attachment_storage"] = DemandAttachmentStorage(app.instance_path)

    init_vue_shell(app)
    register_modules(app)
