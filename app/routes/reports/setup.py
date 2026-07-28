
from datetime import datetime
import pandas as pd
import json

from flask import Blueprint, abort, jsonify, render_template, request, redirect, url_for
from flask_login import current_user

from app.utils.permissions import get_permission

reports_setup_bp = Blueprint('reports_setup', __name__)

@reports_setup_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)


def _GET_QUERY(area, t_start, t_end, webp, work):
    setup_query = ''
    if webp == 'general':

        setup_query = f"""
                        SELECT 
                            T1.*,
                            T2.setup_time * CAST(T1.TOTAL_QTT AS FLOAT) AS EXPECT_TOTAL_MINUTES,
                            T2.setup_time AS EXPECT_MINUTES,
                            T3.GRUPO AS AREA
                        FROM
                            (SELECT 
                                sFlex2String AS PROD_CODE,
                                sDescription AS WORK_CENTER,
                                COUNT(sDescription) AS TOTAL_QTT,
                                SUM(ROUND(fMinutes, 2)) AS TOTAL_MINUTES,
                                ISNULL(SUM(CASE WHEN sShift  = 'Turno 1' THEN ROUND(fMinutes, 2) END),0) AS SHIFT1_MIN,
                                ISNULL(SUM(CASE WHEN sShift  = 'Turno 1' THEN 1 END),0) AS SHIFT1_QTT,
                                ISNULL(SUM(CASE WHEN sShift  = 'Turno 2' THEN ROUND(fMinutes, 2) END),0) AS SHIFT2_MIN,
                                ISNULL(SUM(CASE WHEN sShift  = 'Turno 2' THEN 1 END),0) AS SHIFT2_QTT,
                                ISNULL(SUM(CASE WHEN sShift  = 'Turno 3' THEN ROUND(fMinutes, 2) END),0) AS SHIFT3_MIN,
                                ISNULL(SUM(CASE WHEN sShift  = 'Turno 3' THEN 1 END),0) AS SHIFT3_QTT
                            FROM 
                                OEEQEventHistory AS T1

                            WHERE
                                sEventDesc = 'Parada' AND
                                sEndVal = '100-Setup' AND
                                tStart >= '{t_start}' AND
                                tEnd <= '{t_end}' AND
                                sShift IN ('Turno 1', 'Turno 2', 'Turno 3') 
                            GROUP BY 
                                sDescription, sFlex2String) AS T1
                            LEFT JOIN
                                (SELECT DISTINCT * FROM TDG_CADASTRO_PARAMETROS_SETUP) AS T2 ON T1.PROD_CODE = T2.material AND SUBSTRING(T1.WORK_CENTER, 1, 3) = t2.ct
                            LEFT JOIN CONFIG_TABLET AS T3 ON T1.WORK_CENTER = T3.NOME_MAQUINA
                        WHERE 
                            T2.area {area} AND T1.WORK_CENTER LIKE '{work}'"""

    elif webp == 'material':
        setup_query = f"""
                        SELECT 
                            T1.sFlex2String AS PROD_CODE,
                            T1.sDescription AS WORK_CENTER,
                            T1.tStart AS START_STOP,
                            T1.tEnd AS END_STOP,
                            T1.fMinutes AS DURATION,
                            T2.setup_time AS GOAL_TIME
                        FROM 
                            OEEQEventHistory AS T1
                            LEFT JOIN
                            (SELECT DISTINCT * FROM TDG_CADASTRO_PARAMETROS_SETUP) AS T2 ON T1.sFlex2String = T2.material AND SUBSTRING(T1.sDescription, 1, 3) = t2.ct

                        WHERE
                            T1.sEventDesc = 'Parada' AND
                            T1.sEndVal = '100-Setup' AND
                            T1.tStart >= '{t_start}' AND
                            T1.tEnd <= '{t_end}' AND
                            T1.sShift IN ('Turno 1', 'Turno 2', 'Turno 3') AND
                            T1.sFlex2String = '{work}' AND T1.sDescription = '{area}'"""

    return setup_query

# PÁGINA DE ROTA PRINCIPAL, QUE USUÁRIO ACESSA EM SEGUNDA INSTÂNCIA. POR MEIO DE REQUESTS PARA UMA PÁGINA DE
# CALLBACK, ESSA ROTA RETORNA UMA PÁGINA COM UM DASHBOARD INTERATIVO CONTENDO INFORMAÇÕES GERAIS SOBRE
# OS TEMPOS DE SETUP, BEM COMO UMA TABELA COM AS INFORMAÇÕES DETALHADAS POR CT E DATA
@reports_setup_bp.route('/dashboards/setup/geral', methods=['GET', 'POST'])
def setup_general():

    def getStatus(dfs, filter_list, column):
        enviar = []
        for filters in filter_list:
            x = dfs[dfs[column] == filters].reset_index()
            if not x.empty:
                if x['EXPECT_TOTAL_MINUTES'][0] < x['TOTAL_MINUTES'][0]:
                    enviar.append(1)
                else:
                    enviar.append(0)
            else:
                enviar.append(2)

        return enviar

    cnnx = pyodbc.connect(cnnx_ftm)

    try:
        data_inicio = request.get_json()[1] + ' 00:00:00'
        data_final = request.get_json()[2] + ' 23:59:59'
    except:
        data_inicio = str(datetime.now().date()) + ' 00:00:00'
        data_final = str(datetime.now().date()) + ' 23:59:59'

    try:
        area = "LIKE '" + request.get_json()[0] + "' "
    except:
        area = "LIKE '%%'"

    if "prod" in request.args:

        query = _GET_QUERY(area, data_inicio, data_final, 'general', request.get_json()[3])

        df = pd.read_sql(query, cnnx)
        df_sum = ['EXPECT_TOTAL_MINUTES', 'TOTAL_QTT', 'TOTAL_MINUTES', 'EXPECT_MINUTES',
                    'SHIFT1_QTT', 'SHIFT1_MIN', 'SHIFT2_QTT', 'SHIFT2_MIN', 'SHIFT3_QTT', 'SHIFT3_MIN']

        df_prodCode = df.groupby(['PROD_CODE'])[df_sum].sum().reset_index()

        df_vals = [['MATERIAL', 'MIN PLAN.', 'QTD TOTAL', 'MIN TOTAL', 'SETUP PADRÃO', 'T1 QTD',
                    'T1 MIN', 'T2 QTD', 'T2 MIN', 'T3 QTD', 'T3 MIN']] + df_prodCode.values.tolist()

        cnnx.close()

        return jsonify(df_vals)

    else:

        query = _GET_QUERY(area, data_inicio, data_final, 'general', "%%")

        df = pd.read_sql(query, cnnx)
        df_sum = ['EXPECT_TOTAL_MINUTES', 'TOTAL_QTT', 'TOTAL_MINUTES']

    if request.method == 'GET':

        total_qtt = df['TOTAL_QTT'].sum()
        total_min = round(df['TOTAL_MINUTES'].sum(), 0)
        not_min = max(total_min - round(df['EXPECT_TOTAL_MINUTES'].sum(), 0), 0)
        not_min = str(abs(not_min)) + " MINUTOS DE SETUP ECONOMIZADOS" if not_min < 0 else str(
            not_min) + " MINUTOS DE SETUP EM EXCESSO"

        cnnx.close()

        return render_template('reports.setup/setup_general.html', video='net1.mp4', total_qtt=total_qtt,
                                total_min=total_min, not_min=not_min,
                                filter_start=data_inicio[0:10], filter_end=data_final[0:10])

    else:

        if "ct" in request.args:

            df_workCenter = df.groupby(['WORK_CENTER'])[df_sum].sum().reset_index()
            options = df_workCenter['WORK_CENTER'].values.tolist()
            values = getStatus(df_workCenter, options, 'WORK_CENTER')

            cnnx.close()

            return dict(zip(options, values))

        else:

            total_qtt = int(df['TOTAL_QTT'].sum())
            total_min = int(round(df['TOTAL_MINUTES'].sum(), 0))
            not_min = int(max(total_min - round(df['EXPECT_TOTAL_MINUTES'].sum(), 0), 0))
            not_min = str(abs(not_min)) + " MINUTOS DE SETUP ECONOMIZADOS" if not_min < 0 else str(
                not_min) + " MINUTOS DE SETUP EM EXCESSO"

            options = df['WORK_CENTER'].values.tolist()
            areas = ['Montagem', 'Usinagem', 'Soldagem', 'Pré-Fabricação']
            enviar = []

            for area in areas:
                area_df = df[df['AREA'] == area].reset_index()

                if not area_df.empty:  # Verifica se há pelo menos uma linha após a filtragem por área
                    df_workCenter = area_df.groupby(['WORK_CENTER'])[df_sum].sum().reset_index()
                    values = getStatus(df_workCenter, options, 'WORK_CENTER')
                    enviar.append(int(any(values)))
                else:
                    enviar.append(2)

            cnnx.close()

            return json.dumps([enviar, [total_qtt, total_min, not_min]])

# PÁGINA DE CALLBACK, QUE ATUALIZA AS INFORMAÇÕES DE FILTROS E SELEÇÕES FEITAS PELO USUÁRIO NAS PÁGINAS DE
# ROTA PRINCIPAL, INFORMANDO ESSAS ALTERAÇÕES PRA CLASSE
@reports_setup_bp.route('/dashboards/setup/material', methods=['GET', 'POST'])
def setup_material():

    def getData(query):
        df = pd.read_sql(query, cnnx)
        df['DURATION'] = round(df['DURATION'], 0)
        df['GOAL_TIME'] = df['GOAL_TIME'].str.slice(stop=-2).astype(int)

        df_vals = [['INICIO DO SETUP', 'FIM DO SETUP', 'DURAÇÃO']] + df[
            ['START_STOP', 'END_STOP', 'DURATION']].astype(str).values.tolist()

        try:
            meta_min = int(df['GOAL_TIME'][0])
        except:
            return [], [0, 0, 0, 0]

        total_qtt = len(df)

        df_group = df.groupby(['PROD_CODE'])['DURATION'].sum().reset_index()
        total_min = round(df_group['DURATION'].sum(), 0)

        not_min = round(total_min - df['GOAL_TIME'].sum(), 0)
        not_min = str(abs(not_min)) + " MINUTOS DE SETUP ECONOMIZADOS" if not_min < 0 else str(
            not_min) + " MINUTOS DE SETUP EM EXCESSO"

        return df_vals, [meta_min, total_qtt, total_min, not_min]

    if 'start' not in request.form and 'att' not in request.args:
        return redirect('/dashboards/setup/geral')

    cnnx = pyodbc.connect(cnnx_ftm)

    if 'att' not in request.args:
        data_inicio = request.form['start'] + ' 00:00:00'
        data_final = request.form['final'] + ' 23:59:59'

        query = _GET_QUERY(request.form['ct'], data_inicio, data_final, 'material',
                                request.form['material'])

        data = getData(query)

        df_vals = data[0]
        meta_min = data[1][0]
        total_qtt = data[1][1]
        total_min = data[1][2]
        not_min = data[1][3]

        return render_template('reports.setup/setup_material.html', video='net1.mp4',
                                material=request.form['material'], ct=request.form['ct'], data=df_vals,
                                total_qtt=total_qtt, total_min=total_min, not_min=not_min,
                                meta_min=meta_min, start=request.form['start'], end=request.form['final'])
    
    else:
        data_inicio = request.get_json()[1] + ' 00:00:00'
        data_final = request.get_json()[2] + ' 23:59:59'

        query = _GET_QUERY(request.get_json()[0], data_inicio, data_final, 'material',request.get_json()[3])

        data = jsonify(getData(query))

        return data

@reports_setup_bp.route('/cadastros/parametros_setup', methods=['GET', 'POST'])
def setup_register():

    return redirect('/denied')

    cnnx = pyodbc.connect(cnnx_ftm)

    df_query = f"""SELECT material, tools, area, ct, setup_time  
                    FROM TDG_CADASTRO_PARAMETROS_SETUP WHERE CONFIG_STATUS != 1"""

    if request.method == 'POST':
        cursor = cnnx.cursor()

        if 'searchByArea' in request.args:
            df = pd.read_sql(
                f"SELECT NOME_MAQUINA FROM CONFIG_TABLET WHERE GRUPO = '{request.args['searchByArea']}'",
                cnnx)
            data1 = df['NOME_MAQUINA'].values.tolist()

            query = f"""SELECT 
                            DISTINCT(T1.ID_MATER) 
                        FROM 
                            WORK_CELL_OP AS T1
                            JOIN CONFIG_TABLET AS T2 ON T2.NOME_MAQUINA = T1.CT
                        WHERE 
                            T2.GRUPO = '{request.args['searchByArea']}' ORDER BY T1.ID_MATER"""

            df = pd.read_sql(query, cnnx)
            data2 = df['ID_MATER'].values.tolist()

            return json.dumps([data1, data2])

        elif 'searchByCt' in request.args:

            query = f"""SELECT 
                            DISTINCT(ID_MATER) 
                        FROM 
                            WORK_CELL_OP
                        WHERE 
                            CT = '{request.args['searchByCt']}' ORDER BY ID_MATER"""

            df = pd.read_sql(query, cnnx)
            data = df['ID_MATER'].values.tolist()

            return json.dumps(data)

        else:
            if request.args['cmd'] == 'insert':
                info = request.args['data'].split(',')
                query = f"""INSERT INTO TDG_CADASTRO_PARAMETROS_SETUP VALUES ('{info[0]}', '{info[1]}', '{info[2]}', 
                        '{info[3]}', '{info[4]}', 0, 0, '2023-12-15 00:00:00.000')"""

            elif request.args['cmd'] == 'delete':
                data = request.get_json()
                query = f"""UPDATE TDG_CADASTRO_PARAMETROS_SETUP SET CONFIG_STATUS = 1
                            WHERE material = '{data[0]}' AND ct = '{data[1]}'"""

            elif request.args['cmd'] == 'edit':
                data = request.get_json()
                if data[3] == 'FERRAMENTAS / DISPOSITIVOS':
                    query = f"""UPDATE TDG_CADASTRO_PARAMETROS_SETUP SET tools = '{data[2]}' 
                                WHERE material = '{data[0]}' AND ct = '{data[1]}'"""
                elif data[3] == 'TEMPO DE SETUP':
                    query = f"""UPDATE TDG_CADASTRO_PARAMETROS_SETUP SET setup_time = '{data[2]}' 
                                WHERE material = '{data[0]}' AND ct = '{data[1]}'"""

            try:
                cursor.execute(query)
                cnnx.commit()
                df = pd.read_sql(df_query, cnnx)
                df = df.rename(columns={'material': 'MATERIAL', 'tools': 'FERRAMENTAS / DISPOSITIVOS',
                                        'area': 'ÁREA', 'ct': 'CENTRO DE TRABALHO',
                                        'setup_time': 'TEMPO DE SETUP'})
                df = df.fillna(value='')
                cnnx.close()

                return df.to_json()

            except pyodbc.IntegrityError:
                return render_template('record_exists.html')

    else:
        df = pd.read_sql(df_query, cnnx)
        df = df.rename(columns={'material': 'MATERIAL', 'tools': 'FERRAMENTAS / DISPOSITIVOS',
                                'area': 'ÁREA', 'ct': 'CENTRO DE TRABALHO', 'setup_time': 'TEMPO DE SETUP'})

        dg = pd.read_sql("SELECT GRUPO FROM CONFIG_TABLET GROUP BY GRUPO", cnnx)
        ahrea = [item[0] for item in dg.values.tolist()]

        dg = pd.read_sql("SELECT NOME_MAQUINA FROM CONFIG_TABLET", cnnx)
        cts = [item[0] for item in dg.values.tolist()]

        query = "SELECT DISTINCT(ID_MATER) FROM WORK_CELL_OP WHERE ID_WORK_UNIT = '' ORDER BY ID_MATER"
        dg = pd.read_sql(query, cnnx)
        produtos = [item[0] for item in dg.values.tolist()]

        cnnx.close()

        return render_template('consulta_setup_parametros.html', df=df.to_json(), ahrea=ahrea,
                                cts=cts, produtos=produtos)