"""Tarefas do trabalho moderno, com versão própria e auditoria na demanda."""

import json
from hashlib import sha256

from sqlalchemy import case, delete, func, select, update

from backend.shared import identity
from backend.shared.database import get_td_session_factory, paginate
from backend.shared.http import ApiProblem

from .models import SharedUser, WorkHistory, WorkItem, WorkTask
from .schemas import TaskCreate, TaskDelete, TaskList, TaskQuery, TaskUpdate, WorkDetail
from .work_routes import _check_version, _clock, _get_work, _validate_responsible, _work_detail, permissions, require_action, work_bp


def _editable(work):
    return work["kind"] != "aviso" and work["status"] not in ("concluido", "cancelado")


def _require_editable(work):
    if not _editable(work):
        raise ApiProblem(409, "Avisos e demandas encerradas não permitem alterações de tarefas.")


def _record_change(session, work, actor_id, event_type, message, *, changes=None):
    # A versão do pai muda também: planejamento/ações abertos antes da tarefa devem ser recarregados.
    updated_id = session.scalar(update(WorkItem).where(WorkItem.id == work["id"],
        WorkItem.row_version == work["row_version"])
        .values(updated_at=func.sysutcdatetime()).returning(WorkItem.id))
    if updated_id is None:
        raise ApiProblem(409, "A demanda mudou. Recarregue os detalhes.")
    session.add(WorkHistory(work_id=work["id"], actor_id=actor_id, event_type=event_type,
        changes=json.dumps({"message": message, **(changes or {})}, ensure_ascii=False, default=str)))
    session.flush()


@work_bp.get("/<int:work_id>/tasks")
@require_action("demands.work.read")
@work_bp.input(TaskQuery, location="query")
@work_bp.output(TaskList)
def list_tasks(work_id, query_data):
    sessions = get_td_session_factory()
    with sessions() as session:
        work = _get_work(session, work_id)
        if work["kind"] == "aviso":
            raise ApiProblem(409, "Avisos não possuem tarefas.")
        statement = select(WorkTask.id, WorkTask.title, WorkTask.description, WorkTask.responsible_id,
            SharedUser.name.label("responsible_name"), WorkTask.priority, WorkTask.due_on,
            WorkTask.completed_at, WorkTask.row_version).outerjoin(SharedUser, SharedUser.id == WorkTask.responsible_id)
        statement = statement.where(WorkTask.work_id == work_id)
        if query_data.status != "all":
            statement = statement.where(WorkTask.completed_at.is_(None) if query_data.status == "pending"
                                        else WorkTask.completed_at.is_not(None))
        priority = (case((WorkTask.priority.is_(None), 1), else_=0), WorkTask.priority)
        deadline = (case((WorkTask.due_on.is_(None), 1), else_=0), WorkTask.due_on)
        ordering = (*deadline, *priority) if query_data.sort == "deadline" else (*priority, *deadline)
        result = paginate(session, statement.order_by(case((WorkTask.completed_at.is_(None), 0), else_=1),
            *ordering, WorkTask.id), query_data)
        for task in result["items"]:
            task["row_version"] = bytes(task["row_version"]).hex()
    return {**result, "capabilities": {"can_update": _editable(work) and permissions.can(identity.current_actor(), "demands.work.update")}}


@work_bp.post("/<int:work_id>/tasks")
@require_action("demands.work.update")
@work_bp.input(TaskCreate)
@work_bp.output(WorkDetail, status_code=201)
def create_task(work_id, json_data):
    actor_id = str(identity.current_actor().id)
    fields = json_data.model_dump(exclude={"row_version", "submission_key"})
    fingerprint = sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        work = _get_work(session, work_id, lock=True)
        # Conferir repetição antes da versão permite recuperar um POST já confirmado.
        existing = session.scalar(select(WorkTask).where(WorkTask.work_id == work_id,
            WorkTask.created_by == actor_id, WorkTask.submission_key == json_data.submission_key))
        if existing is not None:
            if existing.submission_fingerprint != fingerprint:
                raise ApiProblem(409, "A chave da tarefa já foi usada com outros dados. Recarregue os detalhes.")
        else:
            _require_editable(work)
            _check_version(work, json_data.row_version)
            _validate_responsible(session, json_data.responsible_id)
            completed = fields.pop("completed")
            now, _ = _clock()
            task = WorkTask(work_id=work_id, created_by=actor_id, submission_key=json_data.submission_key,
                submission_fingerprint=fingerprint, completed_at=now if completed else None, **fields)
            session.add(task)
            session.flush()
            _record_change(session, work, actor_id, "task_created", f"Tarefa #{task.id} criada: {task.title}")
        result = _work_detail(session, work_id)
    return result


@work_bp.put("/<int:work_id>/tasks/<int:task_id>")
@require_action("demands.work.update")
@work_bp.input(TaskUpdate)
@work_bp.output(WorkDetail)
def update_task(work_id, task_id, json_data):
    actor_id = str(identity.current_actor().id)
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        work = _get_work(session, work_id, lock=True)
        _require_editable(work)
        _check_version(work, json_data.row_version)
        task = session.scalar(select(WorkTask).where(WorkTask.id == task_id, WorkTask.work_id == work_id))
        if task is None:
            raise ApiProblem(404, "Tarefa não encontrada nesta demanda.")
        if json_data.responsible_id != task.responsible_id:
            _validate_responsible(session, json_data.responsible_id)
        fields = json_data.model_dump(exclude={"row_version", "task_row_version", "completed"})
        now, _ = _clock()
        fields["completed_at"] = (task.completed_at or now) if json_data.completed else None
        changed = [field for field, value in fields.items() if getattr(task, field) != value]
        changes = {field: {"before": getattr(task, field), "after": fields[field]} for field in changed}
        updated_id = session.scalar(update(WorkTask).where(WorkTask.id == task_id, WorkTask.work_id == work_id,
            WorkTask.row_version == bytes.fromhex(json_data.task_row_version))
            .values(**fields, updated_at=func.sysutcdatetime()).returning(WorkTask.id))
        if updated_id is None:
            raise ApiProblem(409, "A tarefa mudou. Recarregue os detalhes antes de salvar novamente.")
        if changed:
            _record_change(session, work, actor_id, "task_updated", f"Tarefa #{task_id} atualizada: {json_data.title}",
                changes={"task": {"id": task_id, "changes": changes}})
        result = _work_detail(session, work_id)
    return result


@work_bp.delete("/<int:work_id>/tasks/<int:task_id>")
@require_action("demands.work.update")
@work_bp.input(TaskDelete)
@work_bp.output(WorkDetail)
def delete_task(work_id, task_id, json_data):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        work = _get_work(session, work_id, lock=True)
        _require_editable(work)
        _check_version(work, json_data.row_version)
        title = session.scalar(delete(WorkTask).where(WorkTask.id == task_id, WorkTask.work_id == work_id,
            WorkTask.row_version == bytes.fromhex(json_data.task_row_version)).returning(WorkTask.title))
        if title is None:
            raise ApiProblem(409, "A tarefa mudou ou foi excluída. Recarregue os detalhes.")
        _record_change(session, work, str(identity.current_actor().id), "task_deleted", f"Tarefa #{task_id} excluída: {title}")
        result = _work_detail(session, work_id)
    return result
