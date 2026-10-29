"""Quadro, cadastro direto, planejamento e execução das demandas modernas."""

import json
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from zoneinfo import ZoneInfo

from apiflask import APIBlueprint
from flask import current_app, request, send_file
from sqlalchemy import case, cast, func, or_, select, update
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import aliased

from backend.shared import identity
from backend.shared.database import get_td_session_factory, literal_contains, paginate
from backend.shared.http import ApiProblem, action_access, api_error, configure_api
from backend.shared.identity import RolePermissions

from .models import Demand, DemandAttachment, SharedUser, WorkAttachment, WorkHistory, WorkItem
from .routes import AREA_ID, AREA_NAME, _responsibles_query, _validate_contributor
from .schemas import WorkAction, WorkBoard, WorkCreate, WorkDetail, WorkList, WorkPlan, WorkQuery
from .storage import MAX_REQUEST_BYTES


permissions = RolePermissions(identity.can_access, {
    "demands.work.read": "SYSADMIN",
    "demands.work.create": "SYSADMIN",
    "demands.work.update": "SYSADMIN",
})
require_action = action_access(identity=identity, permissions=permissions)
work_bp = APIBlueprint("modern_demand_work", __name__, url_prefix="/api/v1/demands/work")
configure_api(work_bp, identity=identity, permission="GENERAL")

ACTION_STATUSES = {
    "start": "em_andamento", "schedule": "agendado", "cancel": "cancelado",
    "request_information": "aguardando_informacoes", "complete": "concluido",
    "validate": "em_validacao", "pause": "pausado", "wait_third_party": "aguardando_terceiros",
    "resume": "em_andamento",
}
EXECUTION_FIELDS = ("status", "scheduled_start_on", "started_on", "due_on", "closed_at")


def _available_actions(work):
    if work["kind"] == "aviso" or not permissions.can(identity.current_actor(), "demands.work.update"):
        return []
    status = work["status"]
    if status in ("a_fazer", "agendado", "aguardando_informacoes") and work["started_on"] is None:
        actions = ["start", "cancel", "schedule", "request_information"]
    elif status in ("em_andamento", "em_validacao", "pausado", "aguardando_terceiros", "aguardando_informacoes") and work["started_on"] is not None:
        actions = ["complete", "cancel", "request_information", "validate", "pause", "wait_third_party"]
        if status != "em_andamento":
            actions.insert(0, "resume")
    else:
        return []
    actions = [action for action in actions if ACTION_STATUSES[action] != status or action == "schedule"]
    if work["started_on"] is not None or work["scheduled_start_on"] is not None:
        actions.append("change_deadline")
    return actions


@work_bp.before_request
def validate_work_request():
    if request.args.get("area", AREA_NAME) != AREA_NAME:
        return api_error(400, message="Área inválida.")
    request.max_content_length = MAX_REQUEST_BYTES


@work_bp.after_request
def private_work_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


@work_bp.errorhandler(413)
def work_too_large(error):
    return api_error(413, message="Use até 40 MB de documentos no total.")


@work_bp.get("/board")
@require_action("demands.work.read")
@work_bp.output(WorkBoard)
def work_board():
    sessions = get_td_session_factory()
    with sessions() as session:
        # Pessoas inativas com registros continuam acessíveis no quadro.
        rows = session.execute(select(
            WorkItem.responsible_id.label("id"), SharedUser.name, func.count(WorkItem.id).label("total"),
        ).select_from(WorkItem).outerjoin(SharedUser, SharedUser.id == WorkItem.responsible_id)
            .where(WorkItem.area_id == AREA_ID, WorkItem.kind != "aviso")
            .group_by(WorkItem.responsible_id, SharedUser.name)).mappings()
        owners = {row["id"]: {**dict(row), "name": row["name"] or "Usuário indisponível"} for row in rows}
        for person in session.execute(_responsibles_query()).mappings():
            owners.setdefault(person["id"], {**dict(person), "total": 0})
        notice_total = session.scalar(select(func.count(WorkItem.id)).where(
            WorkItem.area_id == AREA_ID, WorkItem.kind == "aviso",
        ))
    actor = identity.current_actor()
    return {"owners": sorted(owners.values(), key=lambda item: (item["name"].casefold(), item["id"])),
            "notice_total": notice_total, "actor_id": str(actor.id),
            "can_create": permissions.can(actor, "demands.work.create")}


@work_bp.get("")
@require_action("demands.work.read")
@work_bp.input(WorkQuery, location="query")
@work_bp.output(WorkList)
def list_work(query_data):
    statement = _work_query().where(WorkItem.area_id == AREA_ID)
    if query_data.view == "notices":
        statement = statement.where(WorkItem.kind == "aviso")
    else:
        owner_id = query_data.owner_id or str(identity.current_actor().id)
        statement = statement.where(WorkItem.kind != "aviso", WorkItem.responsible_id == owner_id)
        if query_data.kind != "todos":
            statement = statement.where(WorkItem.kind == query_data.kind)
    if query_data.search:
        statement = statement.where(or_(
            WorkItem.title.like(literal_contains(query_data.search), escape="~"),
            cast(WorkItem.id, NVARCHAR(20)) == query_data.search.lstrip("#"),
        ))
    sessions = get_td_session_factory()
    with sessions() as session:
        result = paginate(session, statement.order_by(
            case((WorkItem.priority.is_(None), 1), else_=0), WorkItem.priority, WorkItem.id.desc(),
        ), query_data)
    return {**result, "capabilities": {"can_create": permissions.can(identity.current_actor(), "demands.work.create")}}


@work_bp.post("")
@require_action("demands.work.create")
@work_bp.output(WorkDetail, status_code=201)
def create_work():
    if request.mimetype != "multipart/form-data" or set(request.form) != {"payload"} or not set(request.files) <= {"files"}:
        return api_error(400, message="Envie os dados do cadastro e seus documentos opcionais.")
    data = WorkCreate.model_validate_json(request.form["payload"])
    actor_id = str(identity.current_actor().id)
    uploaded = request.files.getlist("files")
    if uploaded and data.kind in ("atividade", "aviso"):
        raise ApiProblem(422, detail={"json": {"files": ["Atividades e avisos não usam anexos neste cadastro."]}})
    storage = current_app.extensions["demands_attachment_storage"]
    prepared = storage.prepare(uploaded) if uploaded else []
    fingerprint = sha256(json.dumps({
        "data": data.model_dump(mode="json"),
        "files": [{"name": item.name, "sha256": item.digest} for item in prepared],
    }, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        existing = session.execute(select(WorkItem.id, WorkItem.submission_fingerprint).where(
            WorkItem.area_id == AREA_ID, WorkItem.created_by == actor_id, WorkItem.submission_key == data.submission_key,
        ).with_hint(WorkItem, "WITH (UPDLOCK, HOLDLOCK)", "mssql")).mappings().one_or_none()
        if existing is not None:
            if existing["submission_fingerprint"] != fingerprint:
                raise ApiProblem(409, "Este envio já foi usado com outros dados. Confira o quadro antes de cadastrar novamente.")
            result = _work_detail(session, existing["id"])
        else:
            if session.execute(_responsibles_query().where(SharedUser.id == data.responsible_id)).first() is None:
                raise ApiProblem(422, detail={"json": {"responsible_id": ["Selecione uma pessoa ativa da equipe."]}})
            _validate_contributor(session, data.contributor_id, actor_id)
            item = WorkItem(area_id=AREA_ID, requester_id=actor_id, created_by=actor_id,
                            submission_fingerprint=fingerprint, **data.model_dump())
            session.add(item)
            session.flush()
            saved = storage.save(prepared) if prepared else []
            try:
                for attachment in saved:
                    session.add(WorkAttachment(work_id=item.id, created_by=actor_id, **attachment))
                session.add(WorkHistory(work_id=item.id, actor_id=actor_id, event_type="created"))
                session.flush()
                result = _work_detail(session, item.id)
            except Exception:
                storage.remove_new(saved)
                raise
    # Em falha de commit, preservar arquivos para conciliação do resultado incerto.
    return result


@work_bp.get("/<int:work_id>")
@require_action("demands.work.read")
@work_bp.output(WorkDetail)
def get_work(work_id):
    sessions = get_td_session_factory()
    with sessions() as session:
        result = _work_detail(session, work_id)
    return result


@work_bp.put("/<int:work_id>/planning")
@require_action("demands.work.update")
@work_bp.input(WorkPlan)
@work_bp.output(WorkDetail)
def update_work_plan(work_id, json_data):
    actor_id = str(identity.current_actor().id)
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        current = _get_work(session, work_id, lock=True)
        if current["kind"] == "aviso":
            raise ApiProblem(409, "Avisos não possuem planejamento de demanda.")
        values = json_data.model_dump(exclude={"row_version"})
        for field in ("estimated_hours", "daily_hours", "completed_hours"):
            if values[field] is not None:
                values[field] = Decimal(str(values[field]))
        changes = {field: {"before": current[field], "after": value}
                   for field, value in values.items() if current[field] != value}
        updated_id = session.scalar(update(WorkItem).where(
            WorkItem.id == work_id, WorkItem.area_id == AREA_ID,
            WorkItem.row_version == bytes.fromhex(json_data.row_version),
        ).values(**values, updated_at=func.sysutcdatetime()).returning(WorkItem.id))
        if updated_id is None:
            raise ApiProblem(409, "A demanda mudou. Recarregue os detalhes antes de salvar novamente.")
        if changes:
            session.add(WorkHistory(work_id=work_id, actor_id=actor_id, event_type="planning_updated",
                                    changes=json.dumps(changes, ensure_ascii=False, default=str)))
        session.flush()
        result = _work_detail(session, work_id)
    return result


@work_bp.post("/<int:work_id>/actions")
@require_action("demands.work.update")
@work_bp.input(WorkAction)
@work_bp.output(WorkDetail)
def execute_work_action(work_id, json_data):
    actor_id = str(identity.current_actor().id)
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        current = _get_work(session, work_id, lock=True)
        if bytes(current["row_version"]) != bytes.fromhex(json_data.row_version):
            raise ApiProblem(409, "A demanda mudou. Recarregue os detalhes antes de registrar outra ação.")
        action = json_data.action
        if action not in _available_actions(current):
            raise ApiProblem(409, "Esta ação não está disponível na situação atual. Recarregue os detalhes.")
        now = datetime.now(timezone.utc)
        today = now.astimezone(ZoneInfo("America/Sao_Paulo")).date()
        values = {}
        if action == "start":
            values = {"started_on": today, "scheduled_start_on": None, "due_on": json_data.due_on}
        elif action == "schedule":
            if json_data.scheduled_start_on < today:
                raise ApiProblem(422, detail={"json": {"scheduled_start_on": ["O início deve ser hoje ou uma data futura."]}})
            values = {"scheduled_start_on": json_data.scheduled_start_on, "due_on": json_data.due_on}
        elif action == "change_deadline":
            if json_data.due_on == current["due_on"]:
                raise ApiProblem(422, detail={"json": {"due_on": ["Informe um prazo diferente do atual."]}})
            values = {"due_on": json_data.due_on}
        elif action in ("complete", "cancel"):
            values = {"closed_at": now.replace(tzinfo=None, microsecond=now.microsecond // 1000 * 1000)}
        if json_data.due_on is not None:
            start = values.get("started_on") or values.get("scheduled_start_on") or current["started_on"] or current["scheduled_start_on"] or today
            if json_data.due_on < max(today, start):
                raise ApiProblem(422, detail={"json": {"due_on": ["O prazo deve ser igual ou posterior a hoje e ao início."]}})
        if action != "change_deadline":
            values["status"] = ACTION_STATUSES[action]
        changes = {field: {"before": current[field], "after": value}
                   for field, value in values.items() if current[field] != value}
        if json_data.message is not None:
            changes["message"] = json_data.message
        updated_id = session.scalar(update(WorkItem).where(
            WorkItem.id == work_id, WorkItem.area_id == AREA_ID,
            WorkItem.row_version == bytes.fromhex(json_data.row_version),
        ).values(**values, updated_at=func.sysutcdatetime()).returning(WorkItem.id))
        if updated_id is None:
            raise ApiProblem(409, "A demanda mudou. Recarregue os detalhes antes de registrar outra ação.")
        session.add(WorkHistory(work_id=work_id, actor_id=actor_id, event_type=action,
                                changes=json.dumps(changes, ensure_ascii=False, default=str)))
        session.flush()
        result = _work_detail(session, work_id)
    return result


@work_bp.get("/<int:work_id>/attachments/<int:attachment_id>")
@require_action("demands.work.read")
def work_attachment(work_id, attachment_id):
    sessions = get_td_session_factory()
    with sessions() as session:
        work = _get_work(session, work_id)
        if work["source_request_id"] is not None:
            statement = select(DemandAttachment.original_name, DemandAttachment.storage_key).join(
                Demand, Demand.id == DemandAttachment.demand_id,
            ).where(DemandAttachment.id == attachment_id, Demand.id == work["source_request_id"], Demand.area_id == AREA_ID)
        else:
            statement = select(WorkAttachment.original_name, WorkAttachment.storage_key).where(
                WorkAttachment.id == attachment_id, WorkAttachment.work_id == work_id,
            )
        attachment = session.execute(statement).mappings().one_or_none()
        if attachment is None:
            raise ApiProblem(404, "Documento não encontrado para seu acesso.")
        name, key = attachment["original_name"], attachment["storage_key"]
    path = current_app.extensions["demands_attachment_storage"].resolve(key)
    if not path.is_file():
        raise ApiProblem(404, "Documento não encontrado para seu acesso.")
    response = send_file(path, as_attachment=True, download_name=name, mimetype="application/octet-stream",
                         conditional=False, max_age=0)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _work_query():
    responsible = aliased(SharedUser, name="work_responsible")
    requester = aliased(SharedUser, name="work_requester")
    contributor = aliased(SharedUser, name="work_contributor")
    return select(
        WorkItem.id, WorkItem.source_request_id, WorkItem.kind, WorkItem.title, WorkItem.description,
        WorkItem.responsible_id, responsible.name.label("responsible_name"), requester.name.label("requester_name"),
        contributor.name.label("contributor_name"), WorkItem.urgency, WorkItem.assumptions,
        WorkItem.current_problems, WorkItem.expected_benefits, WorkItem.starts_at, WorkItem.ends_at,
        WorkItem.status, WorkItem.difficulty, WorkItem.priority, WorkItem.estimated_hours,
        WorkItem.scheduled_start_on, WorkItem.started_on, WorkItem.due_on, WorkItem.closed_at,
        WorkItem.daily_hours, WorkItem.completed_hours, WorkItem.observations,
        WorkItem.created_at, WorkItem.updated_at, WorkItem.row_version,
    ).select_from(WorkItem).outerjoin(responsible, responsible.id == WorkItem.responsible_id).outerjoin(
        requester, requester.id == WorkItem.requester_id,
    ).outerjoin(contributor, contributor.id == WorkItem.contributor_id)


def _get_work(session, work_id, *, lock=False):
    statement = _work_query().where(WorkItem.id == work_id, WorkItem.area_id == AREA_ID)
    if lock:
        statement = statement.with_hint(WorkItem, "WITH (UPDLOCK, HOLDLOCK)", "mssql")
    row = session.execute(statement).mappings().one_or_none()
    if row is None:
        raise ApiProblem(404, "Demanda ou aviso não encontrado para seu acesso.")
    return dict(row)


def _work_detail(session, work_id):
    row = _get_work(session, work_id)
    row["row_version"] = bytes(row["row_version"]).hex()
    row["can_update"] = row["kind"] != "aviso" and permissions.can(identity.current_actor(), "demands.work.update")
    row["available_actions"] = _available_actions(row)
    if row["source_request_id"] is not None:
        attachments = select(DemandAttachment.id, DemandAttachment.original_name, DemandAttachment.size_bytes).join(
            Demand, Demand.id == DemandAttachment.demand_id,
        ).where(Demand.id == row["source_request_id"], Demand.area_id == AREA_ID).order_by(DemandAttachment.id)
    else:
        attachments = select(WorkAttachment.id, WorkAttachment.original_name, WorkAttachment.size_bytes).where(
            WorkAttachment.work_id == work_id,
        ).order_by(WorkAttachment.id)
    row["attachments"] = [dict(item) for item in session.execute(attachments).mappings()]
    row["history"] = []
    for event in session.execute(select(
        WorkHistory.id, WorkHistory.event_type, WorkHistory.created_at, WorkHistory.changes,
        SharedUser.name.label("actor_name"),
    ).select_from(WorkHistory).outerjoin(SharedUser, SharedUser.id == WorkHistory.actor_id)
        .where(WorkHistory.work_id == work_id).order_by(WorkHistory.id.desc())).mappings():
        entry = dict(event)
        changes = json.loads(entry.pop("changes") or "{}")
        if not isinstance(changes, dict):
            changes = {}
        transitions = [{"field": field, "before": changes[field].get("before"), "after": changes[field].get("after")}
                       for field in EXECUTION_FIELDS if isinstance(changes.get(field), dict)]
        row["history"].append({**entry, "fields": [field for field in changes if field != "message"],
                               "message": changes.get("message") if isinstance(changes.get("message"), str) else None,
                               "transitions": transitions})
    return row
