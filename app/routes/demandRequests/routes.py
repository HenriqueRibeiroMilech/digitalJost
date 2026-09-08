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

from .domain import DemandRequestsError
from .integration import DemandRequestStorage
from .repository import DemandRequestsRepository
from .services import DemandRequestsService


demand_requests_bp = Blueprint('demand_requests', __name__)

_AREA_CONFIG = {
    'Transformação Digital': {
        'id': 1,
        'role': 'Transformação Digital'
    }
}


def _current_area():
    area_name = request.args.get('area')
    area = _AREA_CONFIG.get(area_name)
    if not area:
        abort(400, description='Área inválida ou não informada.')
    return area_name, area


def _build_service():
    return DemandRequestsService(
        engine=get_engine('jdt'),
        repository=DemandRequestsRepository(),
        storage=DemandRequestStorage(current_app.root_path)
    )


def _is_admin():
    return str(getattr(current_user, 'admin', '')).strip().lower() in ('1', 'true', 'sim')


def _can_review(area):
    return _is_admin() or user_has_role(current_user.role, area['role'])


def _csrf_token():
    token = session.get('demand_requests_csrf')
    if not token:
        token = secrets.token_urlsafe(32)
        session['demand_requests_csrf'] = token
    return token


def _validate_csrf():
    received = request.headers.get('X-CSRF-Token', '') or request.form.get('csrf_token', '')
    expected = session.get('demand_requests_csrf', '')
    if not expected or not received or not hmac.compare_digest(received, expected):
        abort(400, description='Token de segurança inválido. Atualize a página.')


@demand_requests_bp.before_request
def authorize_request():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    if not get_permission('GENERAL').can():
        return abort(403)
    _current_area()
    if request.method in ('POST', 'PATCH'):
        _validate_csrf()


@demand_requests_bp.errorhandler(DemandRequestsError)
def handle_demand_requests_error(error):
    return jsonify({'error': str(error)}), error.status_code


@demand_requests_bp.route('/demandas/solicitacoes', methods=['GET'])
def requests_page():
    area_name, area = _current_area()
    service = _build_service()
    requests_list = service.list_user_requests(area['id'], current_user.id)
    contributors = service.list_contributors(current_user.id)
    requested_tab = request.args.get('tab')
    initial_tab = (
        requested_tab if requested_tab in ('minhas', 'graficos') else 'nova'
    )

    return render_template(
        'demandRequests/portal.html',
        area=area_name,
        requests=requests_list,
        contributors=contributors,
        initial_tab=initial_tab,
        request_sent=request.args.get('sent') == '1',
        initial_request_id=request.args.get('request', type=int),
        csrf_token=_csrf_token()
    )


@demand_requests_bp.route('/demandas/solicitacoes/api', methods=['POST'])
def requests_create():
    _, area = _current_area()
    detail = _build_service().create_request(
        area['id'],
        current_user.id,
        request.form,
        request.files.getlist('docs')
    )
    return jsonify(detail), 201


@demand_requests_bp.route(
    '/demandas/solicitacoes/api/graficos', methods=['GET']
)
def area_analytics():
    _, area = _current_area()
    return jsonify(_build_service().get_area_analytics(area['id']))


@demand_requests_bp.route(
    '/demandas/solicitacoes/api/<int:request_id>',
    methods=['GET', 'PATCH']
)
def request_detail(request_id):
    _, area = _current_area()
    service = _build_service()
    if request.method == 'PATCH':
        detail = service.update_pending_request(
            request_id,
            area['id'],
            current_user.id,
            request.get_json(silent=True)
        )
    else:
        detail = service.get_request(
            request_id,
            area['id'],
            current_user.id,
            _can_review(area)
        )
    return jsonify(detail)


@demand_requests_bp.route(
    '/demandas/solicitacoes/api/<int:request_id>/attachments/<int:attachment_index>',
    methods=['GET']
)
def request_attachment(request_id, attachment_index):
    _, area = _current_area()
    directory, file_name = _build_service().get_attachment(
        request_id,
        attachment_index,
        area['id'],
        current_user.id,
        _can_review(area)
    )
    return send_from_directory(directory, file_name, as_attachment=True)

# V2
