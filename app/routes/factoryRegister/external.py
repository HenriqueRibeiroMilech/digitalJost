from flask import Blueprint, render_template

from app.utils.permissions import get_permission

process = get_permission('PROCESS')
quality = get_permission('QUALITY')
sysadmin = get_permission('SYSADMIN')
production = get_permission('PRODUCTION')

factoryRegister_external_bp = Blueprint('factoryRegister_external', __name__)

@factoryRegister_external_bp.route('/cadastros/paradas')
@sysadmin.require(403)
def cadastro_paradas():
    return render_template('factoryRegister.external/cadastro_paradas.html')

@factoryRegister_external_bp.route('/cadastros/agenda_paradas')
@production.require(403)
def agenda_paradas():
    return render_template('factoryRegister.external/cadastro_agenda_paradas.html')

@factoryRegister_external_bp.route('/cadastros/tablets')
@sysadmin.require(403)
def config_tablet():
    return render_template('factoryRegister.external/cadastro_tablet.html')

@factoryRegister_external_bp.route('/cadastros/qualidade')
@quality.require(403)
def cadastro_qualidade():
    return render_template('factoryRegister.external/cadastro_qualidade.html')

@factoryRegister_external_bp.route('/cadastros/py_suspensor')
@process.require(403)
def py_suspensor():
    return render_template('factoryRegister.external/cadastro_py_suspensor.html')