from apiflask import APIBlueprint
from flask import abort, current_app, request, send_file, url_for
from pydantic import ValidationError

from backend.compatibility import identity
from backend.compatibility.demand_notifications import send_notification
from backend.platform.database import get_td_engine
from backend.platform.http import configure_api, page_access
from backend.platform.identity import RolePermissions
from backend.platform.vue_shell import render_vue_shell

from . import management, repository
from .domain import AREA_NAME, MANAGEMENT_ROLES, DemandNotFoundError, DemandConflictError, DemandStorageError, DemandValidationError
from .management_schemas import (BoardQuery, BoardOut, DeadlineChange, FlowAction, InternalCreate,
    ManagementDetail, ManagementOptions, ManagementUpdate, NoticeCreate, NoticeUpdate, Review,
    ReviewsOut, TaskCreate, TaskUpdate, Version)
from .routes import (demands_shell_bp, invalid_payload, invalid_request, private_response,
    request_conflict, request_not_found, request_too_large, storage_unavailable, validate_area_and_size)


management_bp = APIBlueprint("modern_demand_management", __name__, url_prefix="/api/v1/demand-management")
configure_api(management_bp, identity=identity, permission="GENERAL")
management_bp.before_request(validate_area_and_size)
management_bp.after_request(private_response)
for error, handler in ((413, request_too_large), (ValidationError, invalid_payload),
    (DemandValidationError, invalid_request), (DemandConflictError, request_conflict),
    (DemandNotFoundError, request_not_found), (DemandStorageError, storage_unavailable)):
    management_bp.register_error_handler(error, handler)


def dependencies():
    return {"engine": get_td_engine(), "permissions": RolePermissions(identity.can_access_area, MANAGEMENT_ROLES),
            "override": identity.is_admin()}


def notification_dependencies(demand_id):
    return {"portal_url": url_for("demands_shell.requests_page", tab="minhas", request=demand_id, _external=True),
            "sender": send_notification}


@management_bp.before_request
def require_area():
    if not identity.can_access_area(AREA_NAME):
        abort(403)


@management_bp.get("/options")
@management_bp.output(ManagementOptions)
def options():
    deps = dependencies()
    deps.pop("override")
    return management.options(identity.current_actor(), **deps)


@management_bp.get("")
@management_bp.input(BoardQuery, location="query")
@management_bp.output(BoardOut)
def board(query_data):
    return management.board(query_data, identity.current_actor(), **dependencies())


@management_bp.get("/requests")
@management_bp.output(ReviewsOut)
def reviews():
    return management.reviews(identity.current_actor(), **dependencies())


@management_bp.get("/<int:demand_id>")
@management_bp.output(ManagementDetail)
def detail(demand_id):
    return management.detail(demand_id, identity.current_actor(), **dependencies())


@management_bp.post("/<int:demand_id>/review")
@management_bp.input(Review)
@management_bp.output(ManagementDetail)
def review(demand_id, json_data):
    return management.review(demand_id, json_data, identity.current_actor(), **dependencies(), **notification_dependencies(demand_id))


@management_bp.post("")
@management_bp.output(ManagementDetail, status_code=201)
def create():
    data = InternalCreate.model_validate_json(request.form.get("payload", ""))
    return management.create_internal(data, request.files.getlist("files"), identity.current_actor(), **dependencies(),
        storage=current_app.extensions["demands_attachment_storage"])


@management_bp.put("/<int:demand_id>")
@management_bp.input(ManagementUpdate)
@management_bp.output(ManagementDetail)
def update(demand_id, json_data):
    return management.update_fields(demand_id, json_data, identity.current_actor(), **dependencies())


@management_bp.post("/<int:demand_id>/actions")
@management_bp.input(FlowAction)
@management_bp.output(ManagementDetail)
def transition(demand_id, json_data):
    return management.transition(demand_id, json_data, identity.current_actor(), **dependencies(), **notification_dependencies(demand_id))


@management_bp.patch("/<int:demand_id>/deadline")
@management_bp.input(DeadlineChange)
@management_bp.output(ManagementDetail)
def deadline(demand_id, json_data):
    return management.change_deadline(demand_id, json_data, identity.current_actor(), **dependencies(), **notification_dependencies(demand_id))


@management_bp.post("/<int:demand_id>/tasks")
@management_bp.input(TaskCreate)
@management_bp.output(ManagementDetail)
def create_task(demand_id, json_data):
    return management.task(demand_id, json_data, identity.current_actor(), **dependencies())


@management_bp.put("/<int:demand_id>/tasks/<int:task_id>")
@management_bp.input(TaskUpdate)
@management_bp.output(ManagementDetail)
def update_task(demand_id, task_id, json_data):
    return management.task(demand_id, json_data, identity.current_actor(), **dependencies(), task_id=task_id)


@management_bp.delete("/<int:demand_id>/tasks/<int:task_id>")
@management_bp.input(Version)
@management_bp.output(ManagementDetail)
def delete_task(demand_id, task_id, json_data):
    return management.task(demand_id, json_data, identity.current_actor(), **dependencies(), task_id=task_id, remove=True)


@management_bp.post("/<int:demand_id>/attachments")
@management_bp.output(ManagementDetail)
def add_attachments(demand_id):
    data = Version.model_validate_json(request.form.get("payload", ""))
    return management.attachments(demand_id, data, request.files.getlist("files"), identity.current_actor(),
        **dependencies(), storage=current_app.extensions["demands_attachment_storage"])


@management_bp.delete("/<int:demand_id>/attachments/<int:attachment_id>")
@management_bp.input(Version)
@management_bp.output(ManagementDetail)
def remove_attachment(demand_id, attachment_id, json_data):
    return management.attachments(demand_id, json_data, [], identity.current_actor(), **dependencies(),
        storage=current_app.extensions["demands_attachment_storage"], attachment_id=attachment_id)


@management_bp.get("/<int:demand_id>/attachments/<int:attachment_id>")
def download(demand_id, attachment_id):
    management.detail(demand_id, identity.current_actor(), **dependencies())
    with get_td_engine().connect() as connection:
        item = repository.get_attachment(connection, demand_id, attachment_id)
    if item is None:
        raise DemandNotFoundError()
    path = current_app.extensions["demands_attachment_storage"].resolve(item["storage_key"])
    if not path.is_file():
        raise DemandNotFoundError()
    response = send_file(path, as_attachment=True, download_name=item["original_name"],
                         mimetype="application/octet-stream", conditional=False, max_age=0)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@management_bp.post("/notices")
@management_bp.input(NoticeCreate)
def create_notice(json_data):
    return management.notice(json_data, identity.current_actor(), **dependencies())


@management_bp.put("/notices/<int:notice_id>")
@management_bp.input(NoticeUpdate)
def edit_notice(notice_id, json_data):
    return management.notice(json_data, identity.current_actor(), **dependencies(), notice_id=notice_id)


@management_bp.delete("/notices/<int:notice_id>")
@management_bp.input(Version)
def finish_notice(notice_id, json_data):
    return management.notice(json_data, identity.current_actor(), **dependencies(), notice_id=notice_id, finalize=True)


@demands_shell_bp.get("/app/demandas/gerenciador")
@page_access(identity=identity, permission="GENERAL")
def management_page():
    if request.args.get("area", AREA_NAME) != AREA_NAME:
        abort(400)
    if not identity.can_access_area(AREA_NAME):
        abort(403)
    return render_vue_shell(title="Gestão de demandas | Digital JOST", unavailable_message="Gestão de demandas indisponível.")
