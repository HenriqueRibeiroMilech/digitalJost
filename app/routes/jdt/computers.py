from flask_login import current_user
import pandas as pd

from flask import Blueprint, abort, render_template, request, redirect, url_for
from sqlalchemy import text

from app.utils.db_utils import get_engine
from app.utils.permissions import get_permission

jdt_computers_bp = Blueprint('jdt_computers', __name__)

@jdt_computers_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)

@jdt_computers_bp.route('/computadores', methods=['GET'])
def computers_get():
    return render_template('jdt.computers/computers_main.html')

@jdt_computers_bp.route('/computadores/novo', methods=['GET'])
def computers_register_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"SELECT id FROM JDT_USER_DETAILS"
        id = pd.read_sql(query, cnnx)['id'].values.tolist()

    return render_template('jdt.computers/computers_new.html', options=id)


@jdt_computers_bp.route('/computadores/novo', methods=['POST'])
def computers_register_post():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = (f"INSERT INTO TDG_REGISTRO_COMPUTADORES VALUES "
                    f"('{request.form.get('matricula')}', '{request.form.get('area')}', "
                    f"'{request.form.get('hardware')}', '{request.form.get('imobilizado')}', "
                    f"'{request.form.get('tipo')}', 1)")

        cnnx.execute(text(query))
        cnnx.commit()

    return redirect('/computadores')