from datetime import datetime, timedelta
import pandas as pd
import json

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import text

from app.utils.db_utils import engine_run_query, get_engine
from app.utils.permissions import get_permission


p_logistic = get_permission('LOGISTIC')

operation_logistic_bp = Blueprint('operation_logistic', __name__)

@operation_logistic_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)
    
def _lgs_form(cnnx, form, ran):
    index = int(form['index'])
    copy = json.loads(form['copy'])
    info = []
    for n in range(ran):
        info.append(form[f'col_{n}_{index}'])
    info.append(form['date'])
    info.append(form[f'line_id_{index}'])

    if form['area'] == 'Entregas':
        query = f"""SELECT TOP(1) id FROM JDT_OPE_LOG_DELIVERY ORDER BY id DESC"""
        try:
            line_id = str(pd.read_sql(query, cnnx)['id'][0] + 1)
        except IndexError:
            line_id = '0'

        if info[9] != 'new':
            query = f"""UPDATE JDT_OPE_LOG_DELIVERY SET
            freight = '{info[0]}', product = '{info[1]}', quantity = '{info[2]}', client = '{info[3]}',
            performance = '{info[4]}', statusGeneral = '{info[5]}', statusCause = '{info[6]}', 
            statusAction = '{info[7]}', date = '{form["date"]}' WHERE id = '{info[9]}'"""

            if copy:
                info[9] = line_id
                info = info
                query = f"INSERT INTO JDT_OPE_LOG_DELIVERY VALUES {tuple(info)}"

        else:
            info[9] = line_id
            info = info
            query = f"INSERT INTO JDT_OPE_LOG_DELIVERY VALUES {tuple(info)}"

    else:
        query = f"""SELECT TOP(1) id FROM JDT_OPE_LOG_MTR ORDER BY id DESC"""
        try:
            line_id = str(pd.read_sql(query, cnnx)['id'][0] + 1)
        except IndexError:
            line_id = '0'

        if info[8] != 'new':
            query = f"""UPDATE JDT_OPE_LOG_MTR SET
            item = '{info[0]}', time = '{info[1]}', family = '{info[2]}', status = '{info[3]}',
            supplier = '{info[4]}', resp = '{info[5]}', type = '{info[6]}', 
            date = '{form["date"]}' WHERE id = '{info[8]}'"""

            if copy:
                info[8] = line_id
                info = info
                query = f"INSERT INTO JDT_OPE_LOG_MTR VALUES {tuple(info)}"

        else:
            info[8] = line_id
            info = info
            query = f"INSERT INTO JDT_OPE_LOG_MTR VALUES {tuple(info)}"

    return query


@operation_logistic_bp.route('/op/logistica', methods=['GET'])
def logistic_get():
    return render_template('operation.logis/op_lgs_route.html')

# METODO PARA VERIFICAR SE EXISTEM DADOS PARA A DATA QUE SERÁ CONSULTADA PELO USUARIO
@operation_logistic_bp.route('/op/logistica/check', methods=['POST'])
def logistic_check_post():
    data = request.get_json()
    area = data[0]
    date = data[1].split('T')[0]

    df = pd.DataFrame()
    max_back = 31  # segurança para não loopar infinito

    for _ in range(max_back):
        if area == 'Entregas':
            query = f"""
                SELECT * FROM JDT_OPE_LOG_DELIVERY
                WHERE date = '{date}'
                ORDER BY freight DESC, performance DESC
            """
        elif area == 'Manufaturados':
            query = f"""
                SELECT * FROM JDT_OPE_LOG_MTR
                WHERE date = '{date}' AND supplier = 'JOST'
            """
        else:
            query = f"""
                SELECT * FROM JDT_OPE_LOG_MTR
                WHERE date = '{date}' AND supplier != 'JOST'
            """

        df = engine_run_query(query, 'jdt')

        if not df.empty:
            return date  # encontrado

        # retrocede 1 dia
        date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

    return date


# METODO GET: PAGINA DE CONSULTA DOS DADOS DAS LINHAS
@operation_logistic_bp.route('/op/logistica/edit', methods=['GET'])
def logistic_edit_get():
    return render_template('operation.logis/op_lgs_edit.html', date=datetime.now().date())

# METODO POST: QUERIES QUE FAZEM AS CONSULTAS DOS DADOS
@operation_logistic_bp.route('/op/logistica/edit', methods=['POST'])
def logistic_edit_post():

    data = request.get_json()
    area, date_str = data[0], data[1].split('T')[0]

    if area == 'Entregas':
        query = f"SELECT * FROM JDT_OPE_LOG_DELIVERY WHERE date = '{date_str}' ORDER BY freight DESC, performance DESC"
        id_query = "SELECT TOP(1) id FROM JDT_OPE_LOG_DELIVERY ORDER BY id DESC"
        rename_map = {
            'statusGeneral': 'Status', 'statusCause': 'Causa', 'statusAction': 'Ação',
            'freight': 'Frete', 'product': 'Produto', 'client': 'Cliente'
        }
    else:
        supplier_cond = "supplier = 'JOST'" if area == 'Manufaturados' else "supplier != 'JOST'"
        query = f"SELECT * FROM JDT_OPE_LOG_MTR WHERE date = '{date_str}' AND {supplier_cond}"
        id_query = "SELECT TOP(1) id FROM JDT_OPE_LOG_MTR ORDER BY id DESC"
        rename_map = {
            'time': 'Tempo de Cobertura', 'type': 'Tipo do Material',
            'family': 'Familias', 'supplier': 'Fornecedor', 'resp': 'Responsável'
        }

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        df = pd.read_sql(query, cnnx)
        
        renamed_cols = {col: col.capitalize() for col in df.columns}
        renamed_cols.update(rename_map)
        df = df.rename(columns=renamed_cols)

        try:
            line_id = str(pd.read_sql(id_query, cnnx)['id'][0] + 1)
        except IndexError:
            line_id = '0'

    if request.args['copy'] == 'true':

        for n in range(len(df)):
            df['Id'][n] = int(line_id) + n

    return df.to_json()

# METODO PARA ATUALIZAR OS DADOS DE LINHAS ESPECIFICAS
@operation_logistic_bp.route('/op/logistica/update', methods=['POST'])
@p_logistic.require(403)
def logistic_update_post():

    form = request.form

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        area = form['area']
        ran = 8 if area == 'Entregas' else 7
        cnnx.execute(text(_lgs_form(cnnx, form, ran)))
        cnnx.commit()

        table = 'JDT_OPE_LOG_DELIVERY' if area == 'Entregas' else 'JDT_OPE_LOG_MTR'
        query = f"SELECT TOP(1) id FROM {table} ORDER BY id DESC"
        line_id = str(pd.read_sql(query, cnnx)['id'][0])

    return line_id

# METODO PARA DELETAR LINHAS ESPECIFICAS
@operation_logistic_bp.route('/op/logistica/delete', methods=['POST'])
@p_logistic.require(403)
def logistic_delete_post():

    area, line_id = request.get_json()
    if str(line_id).lower() == "new":
        return "Linha não criada ainda, nada para deletar.", 400

    table = 'JDT_OPE_LOG_DELIVERY' if area == 'Entregas' else 'JDT_OPE_LOG_MTR'
    query = f"DELETE FROM {table} WHERE id = {line_id}"

    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        cnnx.execute(text(query))

    return f"Deleted line {line_id} successfully"
