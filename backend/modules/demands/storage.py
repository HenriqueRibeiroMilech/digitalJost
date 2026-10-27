"""Anexos privados novos; não acessa nem move uploads do sistema antigo."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename

from backend.platform.http import ApiProblem


MAX_FILES = 10
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 40 * 1024 * 1024
MAX_REQUEST_BYTES = 45 * 1024 * 1024
ALLOWED_EXTENSIONS = frozenset({
    "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "pdf",
    "png", "jpg", "jpeg", "gif", "bmp", "webp",
})


@dataclass(frozen=True)
class PreparedFile:
    name: str
    content: bytes
    digest: str


class DemandAttachmentStorage:
    def __init__(self, instance_path):
        # Apenas compõe o caminho. Nenhum I/O durante import/composição/startup.
        self.base = Path(instance_path) / "modern_demand_attachments"

    @staticmethod
    def prepare(files):
        if not 1 <= len(files) <= MAX_FILES:
            raise ApiProblem(422, detail={"json": {"files": ["Adicione entre 1 e 10 documentos ou evidências."]}})
        prepared = []
        total = 0
        for uploaded in files:
            name = secure_filename(uploaded.filename or "")
            extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if not name or extension not in ALLOWED_EXTENSIONS:
                raise ApiProblem(422, detail={"json": {
                    "files": ["Use documentos Word, Excel, PowerPoint, PDF, texto ou imagens permitidas."],
                }})
            stem = name.rsplit(".", 1)[0]
            name = f"{stem[:180]}.{extension}"
            content = uploaded.stream.read(MAX_FILE_BYTES + 1)
            total += len(content)
            if not content or len(content) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise ApiProblem(422, detail={"json": {
                    "files": ["Cada arquivo deve ter conteúdo e até 10 MB; o total deve ser de até 40 MB."],
                }})
            prepared.append(PreparedFile(name, content, sha256(content).hexdigest()))
        return prepared

    def save(self, prepared):
        saved = []
        try:
            self.base.mkdir(parents=True, exist_ok=True)
            for item in prepared:
                key = uuid4().hex
                # O nome original nunca compõe o caminho de armazenamento.
                with (self.base / key).open("xb") as target:
                    saved.append({"original_name": item.name, "storage_key": key,
                                  "size_bytes": len(item.content), "sha256": item.digest})
                    target.write(item.content)
        except OSError as error:
            self.remove_new(saved)
            raise ApiProblem(503, "Não foi possível guardar os documentos. Tente novamente mais tarde.") from error
        return saved

    def remove_new(self, items):
        # Compensação restrita aos arquivos criados pela operação corrente.
        for item in items:
            try:
                self.resolve(item["storage_key"]).unlink(missing_ok=True)
            except (OSError, ApiProblem):
                pass

    def resolve(self, storage_key):
        if len(storage_key) != 32 or any(character not in "0123456789abcdef" for character in storage_key):
            raise ApiProblem(404, "Solicitação ou anexo não encontrado para seu acesso.")
        base = self.base.resolve()
        candidate = base / storage_key
        if candidate.is_symlink() or candidate.resolve().parent != base:
            raise ApiProblem(404, "Solicitação ou anexo não encontrado para seu acesso.")
        return candidate
