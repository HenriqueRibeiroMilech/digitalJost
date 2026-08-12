import hmac
import secrets

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user

from app.utils.permissions import get_permission, user_has_role

from .composition import build_service
from .constants import AREA_CONFIG, DEFAULT_AREA
from .errors import DemandManagementError


demand_management_bp = Blueprint('demand_management', __name__)


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
    return render_template(
        'demandManagement/management.html',
        area=area_name,
        csrf_token=_csrf_token()
    )


@demand_management_bp.route('/demandas/gerenciador/api', methods=['GET'])
def management_list():
    _, area = _current_area()
    return jsonify(build_service().list_board(area['id']))


@demand_management_bp.route('/demandas/gerenciador/api/<int:management_id>', methods=['GET', 'PATCH'])
def management_detail(management_id):
    _, area = _current_area()
    service = build_service()
    if request.method == 'PATCH':
        return jsonify(service.update_demand(
            management_id, area['id'], request.get_json(silent=True)
        ))
    return jsonify(service.get_detail(management_id, area['id']))


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/tasks',
    methods=['POST']
)
def management_task_create(management_id):
    _, area = _current_area()
    detail = build_service().create_task(
        management_id,
        area['id'],
        request.get_json(silent=True),
        current_user.id
    )
    return jsonify(detail), 201


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/tasks/<int:task_id>',
    methods=['PATCH', 'DELETE']
)
def management_task_detail(management_id, task_id):
    _, area = _current_area()
    payload = request.get_json(silent=True) or {}
    service = build_service()
    if request.method == 'DELETE':
        detail = service.delete_task(
            management_id, task_id, area['id'], payload.get('rowVersion')
        )
    else:
        detail = service.update_task(
            management_id, task_id, area['id'], payload
        )
    return jsonify(detail)
