"""Limites e erros públicos das solicitações; sem acesso a contexto ou banco."""

from backend.platform.http import ApiProblem

AREA_NAME = "Transformação Digital"
AREA_ID = 1
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


class DemandNotFoundError(ApiProblem):
    def __init__(self):
        super().__init__(404, "Solicitação ou anexo não encontrado para seu acesso.")


class DemandConflictError(ApiProblem):
    def __init__(self, message):
        super().__init__(409, message)


class DemandValidationError(ApiProblem):
    def __init__(self, field, message):
        super().__init__(422, detail={"json": {field: [message]}})
        self.field = field


class DemandStorageError(ApiProblem):
    def __init__(self):
        super().__init__(503, "Não foi possível guardar os documentos. Tente novamente mais tarde.")
