import json
from hashlib import sha256

from apiflask import APIBlueprint
from flask import Blueprint, abort, current_app, request, send_file
from sqlalchemy import and_, case, cast, func, or_, select, update
from sqlalchemy.dialects.mssql import NVARCHAR
from sqlalchemy.orm import aliased

from backend.shared import identity
from backend.shared.database import get_td_session_factory, literal_contains, paginate
from backend.shared.http import ApiProblem, action_access, api_error, configure_api, page_access
from backend.shared.identity import RolePermissions
from backend.shared.vue_shell import render_vue_shell

from .models import Demand, DemandAttachment, DemandHistory, SharedUser
from .schemas import ContributorsOut, RequestCreate, RequestDetail, RequestList, RequestQuery, RequestUpdate
from .storage import MAX_REQUEST_BYTES


AREA_NAME = "Transformação Digital"
AREA_ID = 1
ACTION_ROLES = {
    "demands.read": "GENERAL",
    "demands.create": "GENERAL",
    "demands.update": "GENERAL",
}

permissions = RolePermissions(identity.can_access, ACTION_ROLES)
require_action = action_access(identity=identity, permissions=permissions)
demands_bp = APIBlueprint("modern_demands", __name__, url_prefix="/api/v1/demands")
demands_shell_bp = Blueprint("demands_shell", __name__)
configure_api(demands_bp, identity=identity, permission="GENERAL")


@demands_bp.before_request
def validate_area_and_size():
    if request.args.get("area", AREA_NAME) != AREA_NAME:
        return api_error(400, message="Área inválida.")
    request.max_content_length = MAX_REQUEST_BYTES


@demands_bp.after_request
def private_response(response):
    # Solicitações e anexos são pessoais; o navegador não deve guardar essas respostas.
    response.headers["Cache-Control"] = "private, no-store"
    return response


@demands_bp.errorhandler(413)
def request_too_large(error):
    return api_error(413, message="Os documentos excedem o limite de envio. Use até 40 MB no total.")


@demands_bp.get("")
@require_action("demands.read")
@demands_bp.input(RequestQuery, location="query")
@demands_bp.output(RequestList)
def list_requests(query_data):
    actor = identity.current_actor()
    statement = _request_query(str(actor.id)).where(_visible(str(actor.id)))
    if query_data.entry_kind != "todos":
        statement = statement.where(Demand.entry_kind == query_data.entry_kind)
    if query_data.search:
        statement = statement.where(or_(
            Demand.title.like(literal_contains(query_data.search), escape="~"),
            cast(Demand.id, NVARCHAR(20)) == query_data.search.lstrip("#"),
        ))
    sessions = get_td_session_factory()
    with sessions() as session:
        result = paginate(session, statement.order_by(Demand.id.desc()), query_data)
    return {**result, "capabilities": {"can_create": permissions.can(actor, "demands.create")}}


@demands_bp.get("/contributors")
@require_action("demands.create")
@demands_bp.output(ContributorsOut)
def contributors():
    sessions = get_td_session_factory()
    with sessions() as session:
        rows = session.execute(_contributors_query(str(identity.current_actor().id)).order_by(SharedUser.name, SharedUser.id))
        result = {"items": [dict(row) for row in rows.mappings()]}
    return result


@demands_bp.post("")
@require_action("demands.create")
@demands_bp.output(RequestDetail, status_code=201)
def create_request():
    if request.mimetype != "multipart/form-data" or set(request.form) != {"payload"} or set(request.files) != {"files"}:
        return api_error(400, message="Envie os dados da solicitação e seus documentos.")
    data = RequestCreate.model_validate_json(request.form["payload"])
    actor_id = str(identity.current_actor().id)
    storage = current_app.extensions["demands_attachment_storage"]
    prepared = storage.prepare(request.files.getlist("files"))
    # A impressão reúne dados normalizados e arquivos para reconhecer uma repetição do envio.
    fingerprint = sha256(json.dumps({
        "data": data.model_dump(),
        "files": [{"name": item.name, "sha256": item.digest} for item in prepared],
    }, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        # A trava e a chave única do banco coordenam requisições com a mesma chave de envio.
        existing = session.execute(select(Demand.id, Demand.submission_fingerprint).where(
            Demand.area_id == AREA_ID, Demand.requester_id == actor_id, Demand.submission_key == data.submission_key,
        ).with_hint(Demand, "WITH (UPDLOCK, HOLDLOCK)", "mssql")).mappings().one_or_none()
        if existing is not None:
            if existing["submission_fingerprint"] != fingerprint:
                raise ApiProblem(409, "Este envio já foi utilizado com outros dados. Confira Minhas solicitações.")
            result = _detail(session, existing["id"], actor_id)
        else:
            _validate_contributor(session, data.contributor_id, actor_id)
            demand = Demand(area_id=AREA_ID, requester_id=actor_id,
                            submission_fingerprint=fingerprint, **data.model_dump())
            session.add(demand)
            # Obtém o ID sem commit; solicitação, anexos e histórico serão confirmados juntos.
            session.flush()
            saved = storage.save(prepared)
            try:
                for item in saved:
                    session.add(DemandAttachment(demand_id=demand.id, created_by=actor_id, **item))
                session.add(DemandHistory(demand_id=demand.id, actor_id=actor_id, event_type="created"))
                # A compensação inclui falhas ao inserir anexos/histórico ou preparar a resposta.
                session.flush()
                result = _detail(session, demand.id, actor_id)
            except Exception:
                storage.remove_new(saved)
                raise
    # Falha no commit preserva os arquivos: o resultado da confirmação pode ser incerto.
    return result


@demands_bp.get("/<int:demand_id>")
@require_action("demands.read")
@demands_bp.output(RequestDetail)
def get_request(demand_id):
    sessions = get_td_session_factory()
    with sessions() as session:
        result = _detail(session, demand_id, str(identity.current_actor().id))
    return result


@demands_bp.put("/<int:demand_id>")
@require_action("demands.update")
@demands_bp.input(RequestUpdate)
@demands_bp.output(RequestDetail)
def update_request(demand_id, json_data):
    actor_id = str(identity.current_actor().id)
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        current = _get_request(session, demand_id, actor_id, lock=True)
        if current is None or current["relationship"] != "requester":
            raise ApiProblem(404, "Solicitação ou anexo não encontrado para seu acesso.")
        if current["status"] != "em_analise" or current["classification"] is not None:
            raise ApiProblem(409, "Esta solicitação já foi analisada e não pode mais ser editada.")
        _validate_contributor(session, json_data.contributor_id, actor_id)
        values = json_data.model_dump(exclude={"row_version"})
        changes = {field: {"before": current[field], "after": value}
                   for field, value in values.items() if current[field] != value}
        # A trava protege a leitura; a versão também rejeita dados antigos enviados pela tela.
        updated_id = session.scalar(update(Demand).where(
            Demand.id == demand_id, Demand.area_id == AREA_ID, Demand.requester_id == actor_id,
            Demand.status == "em_analise", Demand.classification.is_(None),
            Demand.row_version == bytes.fromhex(json_data.row_version),
        ).values(**values, updated_at=func.sysutcdatetime()).returning(Demand.id))
        if updated_id is None:
            raise ApiProblem(409, "A solicitação mudou. Reabra os detalhes antes de salvar novamente.")
        if changes:
            # O histórico usa a mesma transação da alteração para manter os dois consistentes.
            session.add(DemandHistory(demand_id=demand_id, actor_id=actor_id, event_type="updated",
                                      changes=json.dumps(changes, ensure_ascii=False)))
        session.flush()
        result = _detail(session, demand_id, actor_id)
    return result


@demands_bp.get("/<int:demand_id>/attachments/<int:attachment_id>")
@require_action("demands.read")
def download_attachment(demand_id, attachment_id):
    sessions = get_td_session_factory()
    with sessions() as session:
        if _get_request(session, demand_id, str(identity.current_actor().id)) is None:
            raise ApiProblem(404, "Solicitação ou anexo não encontrado para seu acesso.")
        item = session.execute(select(DemandAttachment.original_name, DemandAttachment.storage_key).where(
            DemandAttachment.id == attachment_id, DemandAttachment.demand_id == demand_id,
        )).mappings().one_or_none()
        if item is None:
            raise ApiProblem(404, "Solicitação ou anexo não encontrado para seu acesso.")
        name, storage_key = item["original_name"], item["storage_key"]
    # A sessão SQL já fechou; o storage ainda valida o caminho antes de entregar o arquivo.
    path = current_app.extensions["demands_attachment_storage"].resolve(storage_key)
    if not path.is_file():
        raise ApiProblem(404, "Solicitação ou anexo não encontrado para seu acesso.")
    response = send_file(path, as_attachment=True, download_name=name, mimetype="application/octet-stream",
                         conditional=False, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _visible(actor_id):
    # O perfil libera a ação; este filtro limita os registros por área e participação.
    return and_(Demand.area_id == AREA_ID, or_(Demand.requester_id == actor_id, Demand.contributor_id == actor_id))


def _request_query(actor_id):
    # A mesma tabela fornece os nomes de duas pessoas, usando um alias para cada papel.
    requester = aliased(SharedUser, name="requester")
    contributor = aliased(SharedUser, name="contributor")
    relationship = case((Demand.requester_id == actor_id, "requester"), else_="contributor")
    return select(
        Demand.id, Demand.entry_kind, Demand.classification, Demand.title, Demand.description,
        Demand.urgency, Demand.status, Demand.requester_id, Demand.contributor_id,
        Demand.assumptions, Demand.current_problems, Demand.expected_benefits,
        Demand.created_at, Demand.updated_at, Demand.row_version,
        requester.name.label("requester_name"), contributor.name.label("contributor_name"),
        relationship.label("relationship"),
    ).select_from(Demand).outerjoin(requester, requester.id == Demand.requester_id).outerjoin(
        contributor, contributor.id == Demand.contributor_id,
    )


def _get_request(session, demand_id, actor_id, *, lock=False):
    statement = _request_query(actor_id).where(Demand.id == demand_id, _visible(actor_id))
    if lock:
        statement = statement.with_hint(Demand, "WITH (UPDLOCK, HOLDLOCK)", "mssql")
    row = session.execute(statement).mappings().one_or_none()
    return dict(row) if row is not None else None


def _detail(session, demand_id, actor_id):
    row = _get_request(session, demand_id, actor_id)
    if row is None:
        raise ApiProblem(404, "Solicitação ou anexo não encontrado para seu acesso.")
    # A capacidade orienta o botão da tela; o PUT refaz as verificações antes de salvar.
    row["can_update"] = (permissions.can(identity.current_actor(), "demands.update")
                         and row["relationship"] == "requester"
                         and row["status"] == "em_analise" and row["classification"] is None)
    # O JSON transporta os oito bytes da versão como 16 caracteres hexadecimais.
    row["row_version"] = bytes(row["row_version"]).hex()
    row["attachments"] = [dict(item) for item in session.execute(select(
        DemandAttachment.id, DemandAttachment.original_name, DemandAttachment.size_bytes,
    ).where(DemandAttachment.demand_id == demand_id).order_by(DemandAttachment.id)).mappings()]
    row["history"] = [dict(item) for item in session.execute(select(
        DemandHistory.id, DemandHistory.event_type, SharedUser.name.label("actor_name"), DemandHistory.created_at,
    ).select_from(DemandHistory).outerjoin(SharedUser, SharedUser.id == DemandHistory.actor_id)
        .where(DemandHistory.demand_id == demand_id).order_by(DemandHistory.id.desc())).mappings()]
    return row


def _contributors_query(actor_id):
    # Flags nulas também ficam fora: é preciso estar ativo e explicitamente não ser genérico.
    return select(cast(SharedUser.id, NVARCHAR(128)).label("id"), SharedUser.name).where(
        SharedUser.active == 1, SharedUser.generic == 0, SharedUser.id != actor_id,
        SharedUser.name.is_not(None), func.nullif(func.ltrim(func.rtrim(SharedUser.company_email)), "").is_not(None),
    )


def _validate_contributor(session, contributor_id, actor_id):
    if contributor_id is None:
        return
    if contributor_id == actor_id or session.execute(
        _contributors_query(actor_id).where(SharedUser.id == contributor_id),
    ).first() is None:
        raise ApiProblem(422, detail={"json": {
            "contributor_id": ["Selecione outra pessoa ativa com e-mail corporativo."],
        }})


@demands_shell_bp.get("/app/demandas/solicitacoes")
@page_access(identity=identity, permission="GENERAL")
def requests_page():
    if request.args.get("area", AREA_NAME) != AREA_NAME:
        abort(400)
    return render_vue_shell(title="Solicitações de demandas | Digital JOST",
                            unavailable_message="Solicitações de demandas indisponível.")
