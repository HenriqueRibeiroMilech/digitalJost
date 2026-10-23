"""Regras e limites das solicitações; sem acesso a Flask ou ao banco."""

AREA_NAME = "Transformação Digital"
AREA_ID = 1
ACTIVE_STATUSES = ("a_fazer", "em_andamento", "em_validacao", "pausado", "aguardando_terceiros", "aguardando_informacoes")
MANAGEMENT_ROLES = {action: AREA_NAME for action in ("management.read", "management.create", "management.review", "management.edit")}
ACTION_ROLES = {
    "demands.read": "GENERAL",
    "demands.create": "GENERAL",
    "demands.update": "GENERAL",
}
MAX_FILES = 10
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 40 * 1024 * 1024
MAX_REQUEST_BYTES = 45 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({
    "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "pdf",
    "png", "jpg", "jpeg", "gif", "bmp", "webp",
})


class DemandNotFoundError(Exception):
    pass


class DemandConflictError(Exception):
    pass


class DemandValidationError(Exception):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field


class DemandStorageError(Exception):
    pass
