import json
from hashlib import sha256

from . import repository
from .domain import (
    AREA_ID, DemandConflictError, DemandNotFoundError, DemandValidationError,
)


class DemandsService:
    def __init__(self, engine, permissions, storage):
        self.engine = engine
        self.permissions = permissions
        self.storage = storage

    def list(self, query, actor):
        self.permissions.require(actor, "demands.read")
        with self.engine.connect() as connection:
            items, total = repository.list_requests(connection, AREA_ID, str(actor.id), query)
        return {"items": items, "total": total, "page": query.page, "per_page": query.per_page,
                "capabilities": {"can_create": self.permissions.can(actor, "demands.create")}}

    def contributors(self, actor):
        self.permissions.require(actor, "demands.create")
        with self.engine.connect() as connection:
            return {"items": repository.list_contributors(connection, str(actor.id))}

    def get(self, demand_id, actor):
        self.permissions.require(actor, "demands.read")
        with self.engine.connect() as connection:
            return self._detail(connection, demand_id, actor)

    def create(self, data, files, actor):
        self.permissions.require(actor, "demands.create")
        prepared = self.storage.prepare(files)
        fingerprint = sha256(json.dumps({
            "data": data.model_dump(),
            "files": [{"name": item.name, "sha256": item.digest} for item in prepared],
        }, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        actor_id = str(actor.id)
        with self.engine.begin() as connection:
            existing = repository.get_submission(connection, AREA_ID, actor_id, data.submission_key)
            if existing is not None:
                if existing["submission_fingerprint"] != fingerprint:
                    raise DemandConflictError("Este envio já foi utilizado com outros dados. Confira Minhas solicitações.")
                result = self._detail(connection, existing["id"], actor)
            else:
                self._validate_contributor(connection, data.contributor_id, actor_id)
                demand_id = repository.create_request(connection, AREA_ID, actor_id, data, fingerprint)
                saved = self.storage.save(prepared)
                try:
                    for item in saved:
                        repository.add_attachment(connection, demand_id, actor_id, item)
                    repository.add_history(connection, demand_id, actor_id, "created")
                    result = self._detail(connection, demand_id, actor)
                except Exception:
                    self.storage.remove_new(saved)
                    raise
        # O commit precede a resposta. Falha no commit preserva os arquivos para
        # conciliação: o resultado pode ser incerto e não se deve apagar um anexo válido.
        return result

    def update(self, demand_id, data, actor):
        self.permissions.require(actor, "demands.update")
        actor_id = str(actor.id)
        with self.engine.begin() as connection:
            current = repository.get_request(connection, demand_id, AREA_ID, actor_id, lock=True)
            if current is None or current["relationship"] != "requester":
                raise DemandNotFoundError()
            if current["status"] != "em_analise" or current["classification"] is not None:
                raise DemandConflictError("Esta solicitação já foi analisada e não pode mais ser editada.")
            self._validate_contributor(connection, data.contributor_id, actor_id)
            changes = {field: {"before": current[field], "after": value}
                       for field, value in data.model_dump(exclude={"row_version"}).items()
                       if current[field] != value}
            updated = repository.update_request(connection, demand_id, AREA_ID, actor_id, data)
            if updated is None:
                raise DemandConflictError("A solicitação mudou. Reabra os detalhes antes de salvar novamente.")
            if changes:
                repository.add_history(connection, demand_id, actor_id, "updated", changes)
            result = self._detail(connection, demand_id, actor)
        return result

    def attachment(self, demand_id, attachment_id, actor):
        self.permissions.require(actor, "demands.read")
        with self.engine.connect() as connection:
            if repository.get_request(connection, demand_id, AREA_ID, str(actor.id)) is None:
                raise DemandNotFoundError()
            item = repository.get_attachment(connection, demand_id, attachment_id)
            if item is None:
                raise DemandNotFoundError()
        path = self.storage.resolve(item["storage_key"])
        if not path.is_file():
            raise DemandNotFoundError()
        return path, item["original_name"]

    def _detail(self, connection, demand_id, actor):
        row = repository.get_request(connection, demand_id, AREA_ID, str(actor.id))
        if row is None:
            raise DemandNotFoundError()
        row["can_update"] = (
            self.permissions.can(actor, "demands.update")
            and row["relationship"] == "requester"
            and row["status"] == "em_analise" and row["classification"] is None
        )
        row["row_version"] = bytes(row["row_version"]).hex()
        row["attachments"] = repository.list_attachments(connection, demand_id)
        row["history"] = repository.list_history(connection, demand_id)
        return row

    @staticmethod
    def _validate_contributor(connection, contributor_id, actor_id):
        if contributor_id is None:
            return
        if contributor_id == actor_id or not repository.contributor_exists(connection, contributor_id, actor_id):
            raise DemandValidationError("contributor_id", "Selecione outra pessoa ativa com e-mail corporativo.")
