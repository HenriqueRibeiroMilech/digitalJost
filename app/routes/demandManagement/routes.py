import hmac
import secrets

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for
)
from flask_login import current_user

from app.utils.db_utils import get_engine
from app.utils.permissions import get_permission, user_has_role

from .domain import AREA_CONFIG, DEFAULT_AREA, DemandManagementError
from .integration import (
    InternalDemandAttachmentStorage,
    RequestAttachmentStorage,
    RequestReviewNotifier
)
from .repository import DemandManagementRepository
from .services import DemandManagementService


demand_management_bp = Blueprint('demand_management', __name__)


def _build_service():
    """Monta as dependências concretas usadas pelas rotas."""
    return DemandManagementService(
        engine=get_engine('jdt'),
        repository=DemandManagementRepository(),
        attachment_storage=RequestAttachmentStorage(current_app.root_path),
        internal_attachment_storage=InternalDemandAttachmentStorage(
            current_app.instance_path
        ),
        review_notifier=RequestReviewNotifier()
    )


def _current_area():
    area_name = request.args.get('area', DEFAULT_AREA)
    area = AREA_CONFIG.get(area_name)
    if not area:
        abort(400, description='Área inválida.')
    return area_name, area


def _is_admin():
    return str(getattr(current_user, 'admin', '')).strip().lower() in ('1', 'true', 'sim')


def _csrf_token():
    token = session.get('demand_management_csrf')
    if not token:
        token = secrets.token_urlsafe(32)
        session['demand_management_csrf'] = token
    return token


def _validate_csrf():
    received = request.headers.get('X-CSRF-Token', '')
    expected = session.get('demand_management_csrf', '')
    if not expected or not received or not hmac.compare_digest(received, expected):
        abort(400, description='Token de segurança inválido. Atualize a página.')


@demand_management_bp.before_request
def authorize_request():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    if not get_permission('GENERAL').can():
        return abort(403)

    _, area = _current_area()
    if not _is_admin() and not user_has_role(current_user.role, area['role']):
        return abort(403)

    if request.method in ('POST', 'PATCH', 'DELETE'):
        _validate_csrf()


@demand_management_bp.errorhandler(DemandManagementError)
def handle_demand_management_error(error):
    return jsonify({'error': str(error)}), error.status_code


@demand_management_bp.route('/demandas/gerenciador', methods=['GET'])
def management_page():
    area_name, _ = _current_area()
    initial_view = request.args.get('view', 'demands')
    if initial_view not in ('demands', 'requests', 'charts'):
        initial_view = 'demands'
    return render_template(
        'demandManagement/management.html',
        area=area_name,
        csrf_token=_csrf_token(),
        initial_view=initial_view,
        current_user_id=current_user.id,
        current_user_name=current_user.name
    )


@demand_management_bp.route('/demandas/gerenciador/api', methods=['GET', 'POST'])
def management_list():
    _, area = _current_area()
    service = _build_service()
    if request.method == 'POST':
        detail = service.create_personal_demand(
            area['id'], request.get_json(silent=True), current_user.id,
            area['role']
        )
        return jsonify(detail), 201
    return jsonify(service.list_board(
        area['id'], current_user.id, area['role']
    ))


@demand_management_bp.route(
    '/demandas/gerenciador/api/notices', methods=['POST']
)
def management_notice_create():
    _, area = _current_area()
    notice = _build_service().create_wall_notice(
        area['id'], request.get_json(silent=True), current_user.id
    )
    return jsonify(notice), 201


@demand_management_bp.route(
    '/demandas/gerenciador/api/notices/<int:notice_id>', methods=['PATCH']
)
def management_notice_update(notice_id):
    _, area = _current_area()
    notice = _build_service().update_wall_notice(
        notice_id, area['id'], request.get_json(silent=True), current_user.id
    )
    return jsonify(notice)


@demand_management_bp.route('/demandas/gerenciador/api/requests', methods=['GET'])
def review_request_list():
    _, area = _current_area()
    return jsonify(_build_service().list_review_requests(area['id']))


@demand_management_bp.route(
    '/demandas/gerenciador/api/requests/<int:request_id>',
    methods=['GET']
)
def review_request_detail(request_id):
    _, area = _current_area()
    return jsonify(_build_service().get_review_request(request_id, area['id']))


@demand_management_bp.route(
    '/demandas/gerenciador/api/requests/<int:request_id>/attachments/<int:attachment_index>',
    methods=['GET']
)
def review_request_attachment(request_id, attachment_index):
    _, area = _current_area()
    directory, file_name = _build_service().get_request_attachment(
        request_id, attachment_index, area['id']
    )
    return send_from_directory(directory, file_name, as_attachment=True)


@demand_management_bp.route(
    '/demandas/gerenciador/api/requests/<int:request_id>/approve',
    methods=['POST']
)
def review_request_approve(request_id):
    area_name, area = _current_area()
    reviewer = {
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.companyEmail
    }
    result = _build_service().approve_review_request(
        request_id,
        area['id'],
        request.get_json(silent=True),
        reviewer,
        area_name,
        area['role']
    )
    return jsonify(result)


@demand_management_bp.route(
    '/demandas/gerenciador/api/requests/<int:request_id>/decline',
    methods=['POST']
)
def review_request_decline(request_id):
    area_name, area = _current_area()
    reviewer = {
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.companyEmail
    }
    result = _build_service().decline_review_request(
        request_id,
        area['id'],
        request.get_json(silent=True),
        reviewer,
        area_name
    )
    return jsonify(result)


@demand_management_bp.route('/demandas/gerenciador/api/<int:management_id>', methods=['GET', 'PATCH'])
def management_detail(management_id):
    area_name, area = _current_area()
    service = _build_service()
    if request.method == 'PATCH':
        actor = {
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.companyEmail
        }
        return jsonify(service.update_demand(
            management_id,
            area['id'],
            request.get_json(silent=True),
            actor,
            area_name,
            area['role']
        ))
    return jsonify(service.get_detail(management_id, area['id'], current_user.id))


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/attachments',
    methods=['POST']
)
def management_attachment_create(management_id):
    _, area = _current_area()
    detail = _build_service().add_internal_attachments(
        management_id,
        area['id'],
        request.files.getlist('files'),
        current_user.id
    )
    return jsonify(detail), 201


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/attachments/<string:attachment_id>',
    methods=['GET', 'DELETE']
)
def management_attachment_detail(management_id, attachment_id):
    _, area = _current_area()
    service = _build_service()
    if request.method == 'DELETE':
        detail = service.delete_internal_attachment(
            management_id, attachment_id, area['id'], current_user.id
        )
        return jsonify(detail)

    directory, stored_name, download_name = service.get_internal_attachment(
        management_id, attachment_id, area['id']
    )
    return send_from_directory(
        directory,
        stored_name,
        as_attachment=True,
        download_name=download_name
    )


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/status',
    methods=['POST']
)
def management_status(management_id):
    area_name, area = _current_area()
    actor = {
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.companyEmail
    }
    detail = _build_service().transition_status(
        management_id,
        area['id'],
        request.get_json(silent=True),
        actor,
        area_name
    )
    return jsonify(detail)


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/recurrence',
    methods=['POST']
)
def management_recurrence(management_id):
    _, area = _current_area()
    detail = _build_service().update_activity_recurrence(
        management_id,
        area['id'],
        request.get_json(silent=True),
        current_user.id
    )
    return jsonify(detail)


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/schedule',
    methods=['POST']
)
def management_schedule(management_id):
    area_name, area = _current_area()
    actor = {
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.companyEmail
    }
    detail = _build_service().update_start_schedule(
        management_id,
        area['id'],
        request.get_json(silent=True),
        actor,
        area_name
    )
    return jsonify(detail)


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/tasks',
    methods=['POST']
)
def management_task_create(management_id):
    _, area = _current_area()
    detail = _build_service().create_task(
        management_id,
        area['id'],
        request.get_json(silent=True),
        current_user.id,
        area['role']
    )
    return jsonify(detail), 201


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/tasks/<int:task_id>',
    methods=['PATCH', 'DELETE']
)
def management_task_detail(management_id, task_id):
    _, area = _current_area()
    payload = request.get_json(silent=True) or {}
    service = _build_service()
    if request.method == 'DELETE':
        detail = service.delete_task(
            management_id, task_id, area['id'], payload.get('rowVersion'),
            current_user.id
        )
    else:
        detail = service.update_task(
            management_id, task_id, area['id'], payload, current_user.id,
            area['role']
        )
    return jsonify(detail)

# V3
