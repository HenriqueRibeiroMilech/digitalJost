from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user

from app.utils.permissions import get_permission


reports_powerbi_bp = Blueprint('reports_powerbi', __name__)

@reports_powerbi_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)

# DASHBOARD - QUALIDADE
@reports_powerbi_bp.route('/dashboards/qualidade')
def qualidade():
    return render_template('reports.powerbi/powerbi_quality.html')

# DASHBOARD - QUALIDADE - CNQ
@reports_powerbi_bp.route('/dashboards/cnq')
def cnq():
    return render_template('reports.powerbi/powerbi_cnq.html')

# DASHBOARD - TRILHOS
@reports_powerbi_bp.route('/dashboards/trilhos')
def eficiencia():
    return render_template('reports.powerbi/powerbi_rails.html')