from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user

from app.utils.db_utils import get_engine
from app.utils.permissions import get_permission

from .repository import DemandRequestsRepository
from .services import DemandRequestsService


demand_requests_bp = Blueprint('demand_requests', __name__)

_AREA_CONFIG = {
    'Transformação Digital': 1
}


def _current_area():
    area_name = request.args.get('area')
    area_id = _AREA_CONFIG.get(area_name)
    if not area_id:
        abort(400, description='Área inválida ou não informada.')
    return area_name, area_id


def _build_service():
    return DemandRequestsService(
        engine=get_engine('jdt'),
        repository=DemandRequestsRepository()
    )


@demand_requests_bp.before_request
def authorize_request():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    if not get_permission('GENERAL').can():
        return abort(403)
    _current_area()


@demand_requests_bp.route('/demandas/solicitacoes', methods=['GET'])
def requests_page():
    area_name, area_id = _current_area()
    requests_list = _build_service().list_user_requests(area_id, current_user.id)
    initial_tab = 'minhas' if request.args.get('tab') == 'minhas' else 'nova'

    return render_template(
        'demandRequests/portal.html',
        area=area_name,
        requests=requests_list,
        initial_tab=initial_tab,
        request_sent=request.args.get('sent') == '1',
        legacy_submit_url=url_for(
            'request_improvements.improvements_small_new_post',
            area=area_name
        ),
        legacy_form_url=url_for(
            'request_improvements.improvements_small_new_get',
            area=area_name
        ),
        legacy_view_url=url_for(
            'request_improvements.improvements_view_get',
            area=area_name,
            tipo='melhorias'
        ),
        detail_url=url_for('request_improvements.improvements_detail_get')
    )
