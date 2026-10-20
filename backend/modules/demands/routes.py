from apiflask import APIBlueprint
from flask import Blueprint, abort, current_app, request, send_file
from pydantic import ValidationError

from backend.compatibility import identity
from backend.platform.database import get_td_engine
from backend.platform.http import api_error, configure_api, page_access
from backend.platform.identity import RolePermissions
from backend.platform.vue_shell import render_vue_shell

from . import repository, services
from .domain import (
    ACTION_ROLES, AREA_NAME, MAX_REQUEST_BYTES, DemandConflictError, DemandNotFoundError,
    DemandStorageError, DemandValidationError,
)
from .schemas import ContributorsOut, RequestCreate, RequestDetail, RequestList, RequestQuery, RequestUpdate


demands_bp = APIBlueprint("modern_demands", __name__, url_prefix="/api/v1/demands")
demands_shell_bp = Blueprint("demands_shell", __name__)
configure_api(demands_bp, identity=identity, permission="GENERAL")


def _permissions():
    return RolePermissions(identity.can_access, ACTION_ROLES)


def _service_deps():
    return {
        "engine": get_td_engine(),
        "permissions": _permissions(),
    }


@demands_bp.before_request
def validate_area_and_size():
    if request.args.get("area", AREA_NAME) != AREA_NAME:
        return api_error(400, message="Área inválida.")
    # Limite por requisição, antes do parsing multipart (inclui transferências sem Content-Length).
    request.max_content_length = MAX_REQUEST_BYTES


@demands_bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


@demands_bp.errorhandler(413)
def request_too_large(error):
    return api_error(413, message="Os documentos excedem o limite de envio. Use até 40 MB no total.")


@demands_bp.errorhandler(DemandNotFoundError)
def request_not_found(error):
    return api_error(404, message="Solicitação ou anexo não encontrado para seu acesso.")


@demands_bp.errorhandler(DemandConflictError)
def request_conflict(error):
    return api_error(409, message=str(error))


@demands_bp.errorhandler(DemandValidationError)
def invalid_request(error):
    return api_error(422, detail={"json": {error.field: [str(error)]}})


@demands_bp.errorhandler(DemandStorageError)
def storage_unavailable(error):
    return api_error(503, message="Não foi possível guardar os documentos. Tente novamente mais tarde.")


@demands_bp.errorhandler(ValidationError)
def invalid_payload(error):
    fields = {}
    for item in error.errors(include_url=False, include_context=False, include_input=False):
        field = str(item["loc"][0]) if item["loc"] else "payload"
        fields.setdefault(field, []).append(item["msg"])
    return api_error(422, detail={"json": fields})


@demands_bp.get("")
@demands_bp.input(RequestQuery, location="query")
@demands_bp.output(RequestList)
def list_requests(query_data):
    return services.list_requests(
        query_data, identity.current_actor(), **_service_deps(),
    )


@demands_bp.get("/contributors")
@demands_bp.output(ContributorsOut)
def contributors():
    actor = identity.current_actor()
    _permissions().require(actor, "demands.create")
    with get_td_engine().connect() as connection:
        return {"items": repository.list_contributors(connection, str(actor.id))}


@demands_bp.post("")
@demands_bp.output(RequestDetail, status_code=201)
def create_request():
    if request.mimetype != "multipart/form-data" or set(request.form) != {"payload"} or set(request.files) != {"files"}:
        return api_error(400, message="Envie os dados da solicitação e seus documentos.")
    data = RequestCreate.model_validate_json(request.form["payload"])
    return services.create_request(
        data, request.files.getlist("files"), identity.current_actor(),
        **_service_deps(),
        storage=current_app.extensions["demands_attachment_storage"],
    )


@demands_bp.get("/<int:demand_id>")
@demands_bp.output(RequestDetail)
def get_request(demand_id):
    return services.get_request(
        demand_id, identity.current_actor(), **_service_deps(),
    )


@demands_bp.put("/<int:demand_id>")
@demands_bp.input(RequestUpdate)
@demands_bp.output(RequestDetail)
def update_request(demand_id, json_data):
    return services.update_request(
        demand_id, json_data, identity.current_actor(), **_service_deps(),
    )


@demands_bp.get("/<int:demand_id>/attachments/<int:attachment_id>")
def download_attachment(demand_id, attachment_id):
    path, name = services.get_attachment(
        demand_id, attachment_id, identity.current_actor(),
        **_service_deps(),
        storage=current_app.extensions["demands_attachment_storage"],
    )
    response = send_file(path, as_attachment=True, download_name=name, mimetype="application/octet-stream",
                         conditional=False, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@demands_shell_bp.get("/app/demandas/solicitacoes")
@page_access(identity=identity, permission="GENERAL")
def requests_page():
    if request.args.get("area", AREA_NAME) != AREA_NAME:
        abort(400)
    return render_vue_shell(title="Solicitações de demandas | Digital JOST",
                            unavailable_message="Solicitações de demandas indisponível.")
