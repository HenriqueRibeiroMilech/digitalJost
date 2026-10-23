"""Casos de uso do painel, com identidade/dependências explícitas e transações por operação."""

import json
from hashlib import sha256

from . import management_repository as store, repository, notifications
from .domain import ACTIVE_STATUSES, AREA_ID, DemandConflictError, DemandNotFoundError, DemandValidationError


def _reason(value):
    if not value:
        raise DemandValidationError("reason", "Informe a justificativa ou o que precisa ser esclarecido.")
    return value


def _responsible(connection, user_id):
    if not user_id or not any(item["id"] == user_id for item in store.responsibles(connection)):
        raise DemandValidationError("responsible_id", "Selecione um responsável ativo da área.")


def _locked(connection, demand_id, actor, version, *, owned=False, override=False, requester=False):
    row = store.get(connection, demand_id, str(actor.id), lock=True)
    if row is None:
        raise DemandNotFoundError()
    if requester and row["relationship"] != "requester":
        raise DemandNotFoundError()
    if bytes(row["row_version"]).hex() != version.lower():
        raise DemandConflictError("A demanda mudou. Atualize os detalhes antes de salvar novamente.")
    if owned and not (override or row["is_owner"]):
        raise PermissionError("Somente o responsável atual pode alterar esta demanda.")
    if owned and row["status"] not in ACTIVE_STATUSES:
        raise DemandConflictError("Esta demanda está encerrada ou ainda não foi aceita.")
    return row


def _item(row, actor_id, override=False):
    return {**row, "row_version": bytes(row["row_version"]).hex(),
            "can_edit": bool((override or row["is_owner"]) and row["status"] in ACTIVE_STATUSES)}


def _detail(connection, demand_id, actor, override=False):
    row = store.get(connection, demand_id, str(actor.id))
    if row is None:
        raise DemandNotFoundError()
    return {**_item(row, str(actor.id), override), "attachments": repository.list_attachments(connection, demand_id),
            "history": repository.list_history(connection, demand_id), "tasks": store.tasks(connection, demand_id),
            "information_requests": store.information(connection, demand_id)}


def _record(connection, row, actor, event, changes, portal_url, message=None, target=None):
    history_id = repository.add_history(connection, row["id"], str(actor.id), event, changes)
    if message and (row["origin"] == "solicitacao" or event in ("status_information", "information_replied")):
        return notifications.queue(connection, row["id"], history_id, target or row["requester_id"], message, portal_url)
    return None


def _deliver(result, notification_id, engine, sender):
    if notification_id:
        try:
            sent = notifications.deliver(engine, notification_id, sender)
        except Exception:
            sent = False
        if sent:
            result["notification_warning"] = None
        else:
            result["notification_warning"] = "A alteração foi salva; o e-mail está pendente de envio."
    return result


def options(actor, *, engine, permissions):
    permissions.require(actor, "management.read")
    with engine.connect() as connection:
        return {"responsibles": store.responsibles(connection), "contributors": repository.list_contributors(connection, str(actor.id)),
                "today": store.clock(connection)["today"], "current_user_id": str(actor.id)}


def board(query, actor, *, engine, permissions, override=False):
    permissions.require(actor, "management.read")
    with engine.connect() as connection:
        today = store.clock(connection)["today"]
        if query.completed_from and query.completed_from > (query.completed_to or today):
            raise DemandValidationError("completed_from", "O início do período deve ser anterior ou igual ao fim.")
        if query.status and any(value not in (*ACTIVE_STATUSES, "concluido") for value in query.status.split(",")):
            raise DemandValidationError("status", "Selecione status válidos.")
        items = [_item(row, str(actor.id), override) for row in store.list_board(connection, str(actor.id), query, today)]
        notices = [{**row, "row_version": bytes(row["row_version"]).hex(),
                    "can_edit": override or str(row["created_by"]) == str(actor.id)} for row in store.notices(connection)]
    return {"items": items, "notices": notices, "today": today}


def reviews(actor, *, engine, permissions, override=False):
    permissions.require(actor, "management.review")
    with engine.connect() as connection:
        return {"items": [_item(row, str(actor.id), override) for row in store.reviews(connection, str(actor.id))]}


def detail(demand_id, actor, *, engine, permissions, override=False):
    permissions.require(actor, "management.read")
    with engine.connect() as connection:
        return _detail(connection, demand_id, actor, override)


def review(demand_id, data, actor, *, engine, permissions, override=False, portal_url, sender):
    permissions.require(actor, "management.review")
    with engine.begin() as connection:
        row = _locked(connection, demand_id, actor, data.row_version)
        if row["origin"] != "solicitacao" or row["responsible_id"] is not None or row["status"] not in ("em_analise", "aguardando_informacoes"):
            raise DemandConflictError("Esta solicitação já foi analisada.")
        values = {"portal_url": portal_url}
        if data.action == "accept":
            _responsible(connection, data.responsible_id)
            if row["entry_kind"] == "demanda" and not data.classification:
                raise DemandValidationError("classification", "Selecione Melhoria ou Projeto.")
            if row["entry_kind"] == "erro" and data.classification is not None:
                raise DemandValidationError("classification", "O relato mantém o tipo Erro.")
            values.update(status="a_fazer", responsible_id=data.responsible_id, classification=data.classification)
            store.close_information(connection, demand_id)
            message = "Sua solicitação foi aceita e encaminhada ao responsável."
        elif data.action == "decline":
            values.update(status="recusado")
            store.close_information(connection, demand_id)
            message = "Sua solicitação foi recusada.\n\n" + _reason(data.reason)
        else:
            if row["status"] == "aguardando_informacoes":
                raise DemandConflictError("Já existe um pedido de informações em aberto.")
            store.ask_information(connection, demand_id, str(actor.id), data.information_kind, _reason(data.reason), row["status"])
            values["status"] = "aguardando_informacoes"
            message = ("Solicitamos o agendamento de uma reunião." if data.information_kind == "reuniao" else "Precisamos de mais informações.") + "\n\n" + data.reason
        store.update(connection, demand_id, values, bytes.fromhex(data.row_version))
        changes = {key: {"before": row[key], "after": value} for key, value in values.items()
                   if key in ("status", "responsible_id", "classification") and row[key] != value}
        changes["reason"] = data.reason
        notification_id = _record(connection, row, actor, "review_" + data.action, changes, portal_url, message)
        result = _detail(connection, demand_id, actor, override)
    return _deliver(result, notification_id, engine, sender)


def create_internal(data, files, actor, *, engine, permissions, storage, override=False):
    permissions.require(actor, "management.create")
    prepared = storage.prepare(files) if files else []
    if data.demand_type != "atividade" and not prepared:
        raise DemandValidationError("files", "Adicione documentos ou evidências.")
    fingerprint = sha256(json.dumps({"data": data.model_dump(mode="json"),
        "files": [{"name": item.name, "digest": item.digest} for item in prepared]}, sort_keys=True).encode()).hexdigest()
    with engine.begin() as connection:
        existing = repository.get_submission(connection, AREA_ID, str(actor.id), data.submission_key)
        if existing:
            if existing["submission_fingerprint"] != fingerprint:
                raise DemandConflictError("Este envio já foi usado. Confira o painel antes de criar outro.")
            result = _detail(connection, existing["id"], actor, override)
        else:
            _responsible(connection, data.responsible_id)
            if data.contributor_id and not repository.contributor_exists(connection, data.contributor_id, str(actor.id)):
                raise DemandValidationError("contributor_id", "Selecione um contribuinte válido.")
            demand_id = store.create_internal(connection, data, str(actor.id), fingerprint)
            saved = storage.save(prepared) if prepared else []
            try:
                for item in saved:
                    repository.add_attachment(connection, demand_id, str(actor.id), item)
                repository.add_history(connection, demand_id, str(actor.id), "created_internal")
                result = _detail(connection, demand_id, actor, override)
            except Exception:
                storage.remove_new(saved)
                raise
    return result


def update_fields(demand_id, data, actor, *, engine, permissions, override=False):
    permissions.require(actor, "management.edit")
    with engine.begin() as connection:
        row = _locked(connection, demand_id, actor, data.row_version, owned=True, override=override)
        _responsible(connection, data.responsible_id)
        values = data.model_dump(exclude={"row_version"})
        if row["demand_type"] in ("melhoria", "projeto") and not all(values[key] for key in ("assumptions", "current_problems", "expected_benefits")):
            raise DemandValidationError("assumptions", "Preencha premissas, problemas e ganhos esperados.")
        if row["demand_type"] in ("erro", "atividade"):
            values.update(assumptions=None, current_problems=None, expected_benefits=None)
        changes = {key: {"before": row[key], "after": value} for key, value in values.items() if row[key] != value}
        store.update(connection, demand_id, values, bytes.fromhex(data.row_version))
        if changes:
            _record(connection, row, actor, "management_updated", changes, "")
        result = _detail(connection, demand_id, actor, override)
    return result


def transition(demand_id, data, actor, *, engine, permissions, override=False, portal_url, sender):
    permissions.require(actor, "management.edit")
    with engine.begin() as connection:
        row = _locked(connection, demand_id, actor, data.row_version, owned=True, override=override)
        status, action = row["status"], data.action
        allowed = {
            "a_fazer": ("start", "cancel", "schedule", "unschedule", "information"),
            "em_andamento": ("complete", "cancel", "information", "validate", "pause", "third_party"),
            "em_validacao": ("complete", "cancel", "resume", "information"),
            "pausado": ("resume", "cancel", "information"),
            "aguardando_terceiros": ("resume", "cancel", "information"),
            "aguardando_informacoes": ("cancel",),
        }
        if action not in allowed.get(status, ()):
            raise DemandConflictError("Esta ação não está disponível no status atual.")
        clock = store.clock(connection)
        values = {"portal_url": portal_url}
        if data.initial_deadline is not None:
            if row["deadline"] is not None:
                raise DemandValidationError("initial_deadline", "Altere o prazo pela ação própria, com justificativa.")
            values["deadline"] = data.initial_deadline
        if action in ("start", "schedule"):
            deadline = row["deadline"] or data.initial_deadline
            if row["demand_type"] != "atividade" and deadline is None:
                raise DemandValidationError("initial_deadline", "Informe o prazo inicial da demanda.")
            if action == "schedule":
                if not data.scheduled_start_date or data.scheduled_start_date <= clock["today"]:
                    raise DemandValidationError("scheduled_start_date", "Informe um início futuro.")
                if deadline and deadline < data.scheduled_start_date:
                    raise DemandValidationError("initial_deadline", "O prazo não pode ser anterior ao início agendado.")
                values["scheduled_start_date"] = data.scheduled_start_date
            else:
                if deadline and deadline < clock["today"]:
                    raise DemandValidationError("initial_deadline", "Revise o prazo vencido pela ação de alteração de prazo.")
                values.update(status="em_andamento", started_at=clock["now"], scheduled_start_date=None)
        elif action == "unschedule":
            values["scheduled_start_date"] = None
        elif action == "complete":
            values.update(status="concluido", completed_at=clock["now"], completed_on=clock["today"])
        elif action == "cancel":
            _reason(data.reason)
            values.update(status="cancelado", scheduled_start_date=None, expected_return=None)
            store.close_information(connection, demand_id)
        elif action == "information":
            store.ask_information(connection, demand_id, str(actor.id), data.information_kind, _reason(data.reason), status)
            values["status"] = "aguardando_informacoes"
        elif action == "validate":
            values["status"] = "em_validacao"
        elif action in ("pause", "third_party"):
            _reason(data.reason)
            if action == "pause" and data.expected_return is None:
                raise DemandValidationError("expected_return", "Informe a previsão de retorno.")
            values.update(status="pausado" if action == "pause" else "aguardando_terceiros", expected_return=data.expected_return)
        elif action == "resume":
            values.update(status="em_andamento", expected_return=None)
        store.update(connection, demand_id, values, bytes.fromhex(data.row_version))
        message = ("Solicitamos o agendamento de uma reunião." if data.information_kind == "reuniao" else "Precisamos de mais informações.") if action == "information" else "O andamento da sua demanda foi atualizado."
        message += "\n\n" + (data.reason or "")
        changes = {key: {"before": row[key], "after": value} for key, value in values.items()
                   if key in ("status", "deadline", "scheduled_start_date", "expected_return") and row[key] != value}
        changes["reason"] = data.reason
        notification_id = _record(connection, row, actor, "status_" + action, changes, portal_url, message)
        result = _detail(connection, demand_id, actor, override)
    return _deliver(result, notification_id, engine, sender)


def change_deadline(demand_id, data, actor, *, engine, permissions, override=False, portal_url, sender):
    permissions.require(actor, "management.edit")
    with engine.begin() as connection:
        row = _locked(connection, demand_id, actor, data.row_version, owned=True, override=override)
        if row["scheduled_start_date"] and data.deadline < row["scheduled_start_date"]:
            raise DemandValidationError("deadline", "O prazo não pode ser anterior ao início agendado.")
        store.update(connection, demand_id, {"deadline": data.deadline}, bytes.fromhex(data.row_version))
        notification_id = _record(connection, row, actor, "deadline_changed",
            {"deadline": {"before": row["deadline"], "after": data.deadline}, "reason": data.reason}, portal_url,
            "O prazo da demanda foi alterado para " + data.deadline.strftime("%d/%m/%Y") + ".\n\n" + data.reason)
        result = _detail(connection, demand_id, actor, override)
    return _deliver(result, notification_id, engine, sender)


def task(demand_id, data, actor, *, engine, permissions, override=False, task_id=None, remove=False):
    permissions.require(actor, "management.edit")
    with engine.begin() as connection:
        row = _locked(connection, demand_id, actor, data.row_version, owned=True, override=override)
        before = next((item for item in store.tasks(connection, demand_id) if item["id"] == task_id), None)
        if task_id is not None and before is None:
            raise DemandNotFoundError()
        if remove:
            if store.delete_task(connection, demand_id, task_id) is None:
                raise DemandNotFoundError()
            event = "task_deleted"
        else:
            if data.responsible_id:
                _responsible(connection, data.responsible_id)
            saved_id = store.save_task(connection, demand_id, data, task_id)
            if saved_id is None:
                raise DemandConflictError("A tarefa mudou. Atualize os detalhes.")
            event = "task_updated" if task_id else "task_created"
            task_id = saved_id
        after = None if remove else next(item for item in store.tasks(connection, demand_id) if item["id"] == task_id)
        changes = {key: {"before": before[key] if before else None, "after": after[key] if after else None}
                   for key in ("description", "responsible_id", "priority", "deadline", "observations", "completed_at")
                   if (before[key] if before else None) != (after[key] if after else None)}
        changes["task_id"] = task_id
        store.update(connection, demand_id, {"status": row["status"]}, bytes.fromhex(data.row_version))
        _record(connection, row, actor, event, changes, "")
        result = _detail(connection, demand_id, actor, override)
    return result


def attachments(demand_id, data, files, actor, *, engine, permissions, storage, override=False, attachment_id=None):
    permissions.require(actor, "management.edit")
    prepared = storage.prepare(files) if attachment_id is None else []
    with engine.begin() as connection:
        row = _locked(connection, demand_id, actor, data.row_version, owned=True, override=override)
        saved = []
        names = []
        if attachment_id is not None:
            names = [item["original_name"] for item in repository.list_attachments(connection, demand_id) if item["id"] == attachment_id]
            if store.hide_attachment(connection, demand_id, attachment_id) is None:
                raise DemandNotFoundError()
        else:
            if len(repository.list_attachments(connection, demand_id)) + len(prepared) > 30:
                raise DemandValidationError("files", "Cada demanda pode ter até 30 anexos.")
            saved = storage.save(prepared)
            names = [item["original_name"] for item in saved]
        try:
            for item in saved:
                repository.add_attachment(connection, demand_id, str(actor.id), item)
            store.update(connection, demand_id, {"status": row["status"]}, bytes.fromhex(data.row_version))
            _record(connection, row, actor, "attachment_removed" if attachment_id else "attachments_added",
                    {"files": ", ".join(names)}, "")
            result = _detail(connection, demand_id, actor, override)
        except Exception:
            storage.remove_new(saved)
            raise
    return result


def notice(data, actor, *, engine, permissions, override=False, notice_id=None, finalize=False):
    permissions.require(actor, "management.create" if notice_id is None else "management.edit")
    with engine.begin() as connection:
        if notice_id is None:
            fingerprint = sha256(json.dumps(data.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
            existing = store.notice_submission(connection, str(actor.id), data.submission_key)
            if existing and existing["submission_fingerprint"] != fingerprint:
                raise DemandConflictError("Este envio já foi usado com outros dados.")
            if not existing:
                store.create_notice(connection, data, str(actor.id), fingerprint)
        elif store.edit_notice(connection, notice_id, data, str(actor.id), override, finalize) is None:
            raise DemandConflictError("O aviso mudou ou você não pode alterá-lo.")
    return {"saved": True}


def reply_information(demand_id, data, files, actor, *, engine, permissions, storage, portal_url, sender):
    permissions.require(actor, "demands.update")
    prepared = storage.prepare(files) if files else []
    with engine.begin() as connection:
        row = _locked(connection, demand_id, actor, data.row_version, requester=True)
        pending = next((item for item in store.information(connection, demand_id) if item["closed_at"] is None), None)
        if row["status"] != "aguardando_informacoes" or not pending or pending["id"] != data.information_id:
            raise DemandConflictError("Este pedido de informações já foi respondido ou encerrado.")
        if len(repository.list_attachments(connection, demand_id)) + len(prepared) > 30:
            raise DemandValidationError("files", "Cada demanda pode ter até 30 anexos.")
        saved = storage.save(prepared) if prepared else []
        try:
            for item in saved:
                repository.add_attachment(connection, demand_id, str(actor.id), item)
            store.close_information(connection, demand_id, data.reply, str(actor.id))
            store.update(connection, demand_id, {"status": pending["previous_status"]}, bytes.fromhex(data.row_version))
            notification_id = _record(connection, row, actor, "information_replied", {"reply": data.reply}, portal_url,
                                     "O solicitante respondeu ao pedido de informações/reunião.\n\n" + data.reply, pending["requested_by"])
        except Exception:
            storage.remove_new(saved)
            raise
    result = {"saved": True}
    return _deliver(result, notification_id, engine, sender)
