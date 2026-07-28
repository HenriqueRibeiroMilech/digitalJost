import oracledb
from datetime import datetime, timedelta
import pandas as pd
import json

import plotly
import plotly.graph_objects as go

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user

from app.utils.constants import APP_PATH
from app.utils.data_utils import get_current_shift, return_options
from app.utils.db_utils import get_engine
from app.utils.permissions import get_permission

reports_productiveHours_bp = Blueprint('reports_productiveHours', __name__)

@reports_productiveHours_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))

    
    if not get_permission('GENERAL').can():
        return abort(403)


def _STD_CHART(df):
    fig = go.Figure()

    for area in df.keys():
        fig.add_trace(go.Bar(x=[area],
                                y=[df[area]],
                                name=area,
                                text=df[area],
                                textposition='inside',
                                insidetextanchor='start',
                                textfont=dict(color="white"),
                                )
                        )
    fig.update_layout(title=dict(
        text='Nº DE OPERADORES DO TURNO',
        x=0.5,
        y=0.01,
        yanchor='bottom',
        font=dict(color="White")
    ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(
            family="Montserrat SemiBold, monospace",
            color='white'),
        legend=dict(
            font=dict(color="White")),
        xaxis=dict(color='rgba(193,193,193, 0)'),
        barmode='group')

    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    graph_json = json.loads(graph_json)
    graph_json['config'] = {'responsive': True, 'displayModeBar': False}
    graph_json = json.dumps(graph_json)
    return graph_json

# FUNÇÃO QUE RETORNA OS DADOS DA TELA INICIAL DA APLICAÇÃO DE CONTROLE DE HORAS PRODUTIVAS
def _MAIN_SCREEN(json_data):

    cc_sap = pd.read_excel(f'{APP_PATH}/app/static/chp/cc.xlsx', sheet_name='Centro de Custo 2300')
    cc_sap = cc_sap.fillna('')
    cc_sap = cc_sap.loc[cc_sap['Centro Trab.'] != '']

    ora_filter = ora_df_day['CCUS'].astype(str).isin(cc_sap['CC SAP'].astype(str).values.tolist())
    ora_df_filter = ora_df_day.loc[ora_filter].sort_values(by=['MATRICULA'])

    codes = cc_sap.loc[cc_sap['CC SAP'].astype(str).isin(ora_df_filter['CCUS'])]

    desc_setor = ora_df_filter['TURNO'].values.tolist()
    turnos = [item.split(' ')[len(item.split(' ')) - 1] for item in desc_setor]
    ora_df_filter['TURNO'] = turnos
    turnos_info = {'AUSENTES': 0, 'NO CT DE ORIGEM': 0, 'EM EMPRÉSTIMO': 0, 'NÃO ALOCADOS': 0}
    turno = get_current_shift()
    turno_n = turno[1].split(' ')[1]

    for n in range(len(ora_df_filter.values.tolist())):
        mat = ora_df_filter['MATRICULA'].values.tolist()[n]
        ccus = str(ora_df_filter['CCUS'].values.tolist()[n])
        ct = codes.loc[codes['CC SAP'].astype(str).isin([ccus])]['Centro Trab.'].values.tolist()[0]
        if 'desativado' in ct:
            ct = 'S12'

        query = f"""UPDATE CONTROLE_OPERADORES SET CT_ORIGEM = '{ct}' WHERE MATRICULA = '{mat}'"""
        cursor.execute(query)

    cnnx.commit()

    query = f"""SELECT * FROM CONTROLE_OPERADORES WHERE DATA_SAIDA IS NULL"""
    df = pd.read_sql(query, cnnx)
    orig = 0
    emps = 0
    for n in range(len(df)):
        if df['CT_Atual'][n][0:3] == df['CT_Origem'][n]:
            orig += 1
        else:
            emps += 1

    aus = ora_df_filter.loc[(ora_df_filter['HORA_E1'].astype(str) == 'NaT') &
                            (ora_df_filter['TURNO'] == turno_n)]
    prs = ora_df_filter.loc[(ora_df_filter['HORA_E1'].astype(str) != 'NaT') &
                            (ora_df_filter['TURNO'] == turno_n) &
                            (ora_df_filter['HORA_S2'].astype(str) == 'NaT')]

    day_data = {'TURNO 1': turnos_info, 'TURNO 2': turnos_info, 'TURNO 3': turnos_info}
    day_data[turno[1]]['AUSENTES'] = len(aus)
    day_data[turno[1]]['NO CT DE ORIGEM'] = orig
    day_data[turno[1]]['EM EMPRÉSTIMO'] = emps
    day_data[turno[1]]['NÃO ALOCADOS'] = len(prs) - (orig - emps)

    json_data.append(day_data[turno[1]])

    graph_json = _STD_CHART(day_data[turno[1]])
    json_data.append(graph_json)

    return json.dumps(json_data)

# FUNÇÃO QUE RETORNA OS DADOS DA ABA "OPERADORES" DO CT PARA FILTRO DE TEMPO REAL
def _OPERS_REALTIME(arg, json_data, realtime_query):
    
    query = f"""SELECT NOME, DATA_ENTRADA, CT_ORIGEM, MATRICULA, TURNO,
    ROUND(CAST(DATEDIFF(SECOND, DATA_ENTRADA, GETDATE()) AS FLOAT)/3600, 2) AS HORAS FROM 
    CONTROLE_OPERADORES WHERE CT_ATUAL = '{arg}' AND Data_Saida IS NULL"""

    oper_df = pd.read_sql(query, cnnx)
    oper_stop_df = pd.DataFrame(columns=['H_PARADO', 'H_PROD', 'H_DISP'])
    for n in range(len(oper_df.values.tolist())):
        oper_stop_query = f"""SELECT ROUND(SUM(dDownSec)/3600, 2) AS H_PARADO,
        ROUND(SUM(dRunSec)/3600, 2) AS H_PROD, ROUND(SUM(dAvailSec)/3600, 2) AS H_DISP 
        FROM OEEQWorkCellDetail WHERE sDescription = '{arg}' 
        AND tStartTime >= '{str(oper_df['DATA_ENTRADA'][n]).split(".")[0]}' GROUP BY nShift"""
        oper_stop_df = pd.concat([oper_stop_df, pd.read_sql(oper_stop_query, cnnx)], ignore_index=True)

    oper_stop_df = oper_stop_df.reset_index(level=0)[['H_PARADO', 'H_PROD', 'H_DISP']]
    oper_full_df = pd.concat([oper_df, oper_stop_df], axis=1).sort_values(by=['MATRICULA'])
    oper_full_df = oper_full_df.reset_index(level=0, drop=True)

    oper_full_df['MATRICULA'] = oper_full_df['MATRICULA'].fillna(0)
    ora_filter = ora_df_day['MATRICULA'].isin(oper_full_df['MATRICULA'].astype(int).values.tolist())
    ora_df_filter = pd.DataFrame(ora_df_day.loc[ora_filter], index=None).sort_values(by=['MATRICULA'])
    ora_df_filter = ora_df_filter.drop_duplicates()

    ponto = []
    for n in range(len(ora_df_filter)):
        data = ora_df_filter['HORA_E1'].astype(str).values.tolist()[n]
        if data != 'NaT':
            entrada = datetime.strptime(data, '%Y-%m-%d %H:%M:%S')
            time_diff = round((datetime.now() - entrada).seconds / 3600, 2)
            ponto.append(time_diff)
        else:
            ponto.append(oper_full_df['HORAS'][n])

    while len(ponto) < len(oper_full_df):
        ponto.append(0)

    oper_full_df['PONTO'] = ponto
    oper_full_df['CT_ORIGEM'] = [desc[0: len(desc) - 2] for desc in ora_df_filter['TURNO']]

    pct = []
    for n in range(len(oper_full_df)):
        if oper_full_df['HORAS'][n] > oper_full_df['H_DISP'][n]:
            horas = oper_full_df['HORAS'][n]
            oper_full_df['HORAS'][n] = round(horas - (horas - oper_full_df['H_DISP'][n]), 2)
        pct.append(round((oper_full_df['HORAS'][n] / oper_full_df['PONTO'][n]) * 100, 2))

    oper_full_df['PCT'] = pct

    status_df = pd.read_sql(realtime_query, cnnx)
    json_data.append(status_df.to_json())

    oper_full_df = oper_full_df.fillna('-')
    json_data.append(oper_full_df.to_json())

    return json.dumps(json_data)

# FUNÇÃO QUE RETORNA OS DADOS DA ABA "OPERADORES" DO CT PARA FILTROS DE PERÍODO
def _OPERS_PERIODIC(arg, json_data, init, end):
    json_data.append(pd.DataFrame().to_json())
    query = f"""SELECT NOME,  
    CASE WHEN DATA_SAIDA IS NULL THEN 
        ROUND(CAST(DATEDIFF(SECOND, DATA_ENTRADA, GETDATE()) AS FLOAT)/3600, 2) 
    ELSE
        ROUND(CAST(DATEDIFF(SECOND, DATA_ENTRADA, DATA_SAIDA) AS FLOAT)/3600, 2) END
    AS HORAS, TURNO, CT_ORIGEM, MATRICULA, DATA_ENTRADA, DATA_SAIDA FROM
    CONTROLE_OPERADORES WHERE CT_ATUAL = '{arg}' AND '{end} 23:59:59' >= DATA_ENTRADA AND
    DATA_ENTRADA >= '{init} 00:00:00' ORDER BY NOME, TURNO"""

    oper_df = pd.read_sql(query, cnnx)
    oper_df['DATA_SAIDA'] = oper_df['DATA_SAIDA'].fillna(datetime.now().replace(microsecond=0))
    oper_data = dict.fromkeys(oper_df['NOME'].values.tolist(),
                                {'H_LOG': 0, 'H_PARADO': 0, 'H_DISP': 0, 'H_PROD': 0})

    oper_full_df = pd.DataFrame(columns=['NOME', 'CT_ORIGEM', 'TURNO', 'HORAS', 'H_PARADO',
                                            'H_PROD', 'H_DISP', 'MATRICULA'])

    for key in oper_data:
        oper_data[key]['H_LOG'] = 0
        oper_data[key]['H_PARADO'] = 0
        oper_data[key]['H_PROD'] = 0
        oper_data[key]['H_DISP'] = 0
        for n in range(len(oper_df.values.tolist())):
            if key == oper_df['NOME'][n]:
                ct = oper_df['CT_ORIGEM'][n]
                turno = oper_df['TURNO'][n]
                logon = oper_df['MATRICULA'][n]
                oper_stop_query = f"""SELECT ROUND(SUM(dDownSec)/3600, 2) AS H_PARADO,
                ROUND(SUM(dRunSec)/3600, 2) AS H_PROD, ROUND(SUM(dAvailSec)/3600, 2) AS H_DISP 
                FROM OEEQWorkCellDetail WHERE sDescription = '{arg}' AND 
                tStartTime >= '{str(oper_df['DATA_ENTRADA'][n]).split(".")[0]}' AND tStartTime <= 
                '{str(oper_df["DATA_SAIDA"][n]).split(".")[0]}' GROUP BY nShift"""
                oper_stop_df = pd.read_sql(oper_stop_query, cnnx)
                if oper_stop_df.values.tolist():
                    oper_data[key]['H_LOG'] += round(oper_df['HORAS'][n], 2)
                    oper_data[key]['H_PARADO'] += round(oper_stop_df['H_PARADO'][0], 2)
                    oper_data[key]['H_PROD'] += round(oper_stop_df['H_PROD'][0], 2)
                    oper_data[key]['H_DISP'] += round(oper_stop_df['H_DISP'][0], 2)

        line_info = [key, oper_data[key]['H_LOG'], oper_data[key]['H_PARADO'],
                        oper_data[key]['H_PROD'], oper_data[key]['H_DISP']]
        line = pd.DataFrame({'NOME': [line_info[0]], 'HORAS': [line_info[1]],
                                'H_PARADO': [line_info[2]], 'H_PROD': [line_info[3]],
                                'H_DISP': [line_info[4]], 'CT_ORIGEM': ct, 'TURNO': turno,
                                'MATRICULA': logon})

        if oper_data[key]['H_LOG'] > 0:
            oper_full_df = pd.concat([oper_full_df, line], ignore_index=True)

    oper_full_df = oper_full_df.reset_index(level=0, drop=True)
    ora_df_filter = pd.DataFrame(columns=['NOME', 'TURNO', 'MATRICULA', 'CCUS', 'DATA_MARCACAO', 'HORA_E1',
                                            'HORA_S1', 'HORA_E2', 'HORA_S2', 'HORA_E3', 'HORA_S3'])
    ora_cnnx_str = oracledb.makedsn('sgf-ora-15-vip', '1521', service_name='EMRA')
    ora_cnnx = oracledb.connect(user='JOST_ROCKWEL', password='RANDON2022', dsn=ora_cnnx_str)

    init_month = int(init.split('-')[1])
    end_month = int(end.split('-')[1])
    while init_month < end_month + 1:
        year = init.split('-')[0]
        mon = f'{init_month:02d}'
        for oper in oper_full_df['MATRICULA'].astype(int).values.tolist():
            ora_query = f"""SELECT * FROM 
            TABLE(ponto.pack_dados_frequencia_randon.busca_dados(PCOD_EMPRESA => '2300', 
            PMATRICULA => {oper}, PPERIODO => to_date('{''.join([year, mon, '01'])}', 'yyyymmdd')))"""
            ora_df_period = pd.read_sql(ora_query, ora_cnnx)

            ora_df_filter = pd.concat([ora_df_filter, ora_df_period[ora_df_period['HORA_E1'].astype(str) != 'NaT']], ignore_index=True)

        init_month += 1

    ponto = []
    for n in range(len(oper_full_df)):
        matricula = oper_full_df['MATRICULA'].astype(str).values.tolist()[n]
        oper_data = ora_df_filter[(ora_df_filter['MATRICULA'].astype(str) == matricula)]
        ct_hours = oper_full_df['HORAS'][n]
        logs = oper_df[(oper_df['MATRICULA'] == matricula)]['DATA_ENTRADA'].astype(str).values.tolist()
        logs = list(dict.fromkeys([date.split(' ')[0] for date in logs]))
        time_diff = 0
        for m in range(len(oper_data)):
            oper_data = oper_data.fillna('vazio')
            registro_in = oper_data['HORA_E1'].astype(str).values.tolist()[m]
            registro_aux = oper_data['DATA_MARCACAO'].astype(str).values.tolist()[m]
            horarios_e = [col for col in oper_data.columns.tolist() if 'HORA_E' in col]
            horarios_t = [col for col in oper_data.columns.tolist() if 'HORA' in col]
            registro_out = list(
                dict.fromkeys(
                    [oper_data[col].astype(str).values.tolist()[m].split(' ')[0] for col in horarios_t if
                        oper_data[col].astype(str).values.tolist()[m] != 'vazio']
                )
            )
            registro_out = list(dict.fromkeys([item for item in registro_out if item in logs]))
            last_saida = 'vazio'
            if registro_aux in logs or registro_out:
                ctrl = datetime.strptime(f'{init} 23:55:00', '%Y-%m-%d %H:%M:%S') - timedelta(days=1)
                ctrl_e = datetime.strptime(registro_in, '%Y-%m-%d %H:%M:%S')
                if ctrl_e >= ctrl:
                    for step in range(len(horarios_e)):
                        entrada = oper_data[f'HORA_E{step + 1}'].astype(str).values.tolist()[m]
                        saida = oper_data[f'HORA_S{step + 1}'].astype(str).values.tolist()[m]
                        if entrada != 'vazio' and saida == 'vazio':
                            e = datetime.strptime(entrada, '%Y-%m-%d %H:%M:%S')
                            s = datetime.now()
                            time_diff += (s - e).seconds / 3600
                        elif entrada != 'vazio' and saida != 'vazio':
                            e = datetime.strptime(entrada, '%Y-%m-%d %H:%M:%S')
                            s = datetime.strptime(saida, '%Y-%m-%d %H:%M:%S')
                            time_diff += (s - e).seconds / 3600
                        elif entrada == 'vazio' and saida != 'vazio' and last_saida != 'vazio':
                            e = datetime.strptime(last_saida, '%Y-%m-%d %H:%M:%S')
                            s = datetime.strptime(saida, '%Y-%m-%d %H:%M:%S')
                            time_diff += (s - e).seconds / 3600
                        elif entrada == 'vazio' and saida != 'vazio' and last_saida == 'vazio':
                            e = datetime.strptime(registro_in, '%Y-%m-%d %H:%M:%S')
                            s = datetime.strptime(saida, '%Y-%m-%d %H:%M:%S')
                            time_diff += (s - e).seconds / 3600
                        elif entrada == 'vazio' and saida == 'vazio' and last_saida != 'vazio' and step < 2:
                            e = datetime.strptime(last_saida, '%Y-%m-%d %H:%M:%S')
                            s = datetime.now()
                            time_diff += (s - e).seconds / 3600

                        last_saida = saida

        if ct_hours > oper_full_df['H_DISP'][n]:
            oper_full_df['HORAS'][n] = round(ct_hours - (ct_hours - oper_full_df['H_DISP'][n]), 2)

        if time_diff > 0:
            ponto.append(round(time_diff, 2))
        else:
            ponto.append(oper_full_df['HORAS'][n])

    oper_full_df['PONTO'] = ponto

    pct = []
    for n in range(len(oper_full_df)):
        pct.append(round((oper_full_df['HORAS'][n] / oper_full_df['PONTO'][n]) * 100, 2))

    oper_full_df['PCT'] = pct
    oper_full_df = oper_full_df.fillna('-')
    json_data.append(oper_full_df.to_json())

    return json.dumps(json_data)

# FUNÇÃO QUE RETORNA OS DADOS DA ABA "GERAL" DO CT
def _GENERAL_DATA(arg, json_data, realtime_query, dash_type, init, end):
    query = f"""SELECT (CASE WHEN (SUM(dAvailSec) = 0 OR SUM(dTotalParts) = 0) THEN 0 ELSE 
    SUM(dRunSec) / SUM(CASE WHEN (dAvailSec = 0) THEN dRunSec ELSE dAvailSec END) END) * 100 
    AS DISPONIBILIDADE, ROUND(SUM(dRunSec)/3600, 2) AS H_RODANDO, 
    ROUND((SUM(dAvailSec) - SUM(dRunSec))/3600, 2) AS H_PARADO,
    ROUND(SUM(dAvailSec)/3600, 2) AS H_DISPONIVEL,
    (SELECT SUM(VL_META)/COUNT(VL_META) FROM CADASTRO_META 
    WHERE COD_MAQUINA = '{arg}') AS META_OEE,
    (CASE WHEN SUM(dTotalParts) = 0 THEN 0 ELSE SUM(dGoodParts) / 
    SUM(dTotalParts) END) * 100 AS QUALIDADE, (CASE WHEN SUM(dRunSec) > 0 THEN 
    SUM(dGoodParts * NULLIF(dIdealCycleTime, 0)) / SUM(dRunSec) ELSE 0 END) * 100 AS PERFORMANCE, 
    ((CASE WHEN (SUM(dAvailSec) = 0 OR SUM(dTotalParts) = 0) THEN 0 ELSE SUM(dRunSec) / 
    SUM(CASE WHEN (dAvailSec = 0) THEN dRunSec ELSE dAvailSec END) END)) * 
    ((CASE WHEN SUM(dTotalParts) = 0 THEN 0 ELSE SUM(dGoodParts) / SUM(dTotalParts) END)) * 
    ((CASE WHEN SUM(dRunSec) > 0 THEN SUM(dGoodParts * NULLIF(dIdealCycleTime, 0)) / SUM(dRunSec) 
    ELSE 0 END)) * 100 AS OEE FROM OEEQWorkCellDetail WITH (NOLOCK) WHERE sDescription = '{arg}'"""

    stop_query = f"""SELECT ROUND(SUM(dDownSec)/3600, 2) AS H_PARADO,
    ROUND(SUM(dRunSec)/3600, 2) AS H_PROD, ROUND(SUM(dAvailSec)/3600, 2) AS H_DISP, 
    nShift AS TURNO FROM OEEQWorkCellDetail WHERE sDescription = '{arg}' AND nShift IN (1, 2, 3)"""

    if dash_type == 'realtime':
        query += f""" AND tStartTime >= '{datetime.now().date()} 00:00:00'"""
        status_df = pd.read_sql(realtime_query, cnnx)
        status_df['Tempo'][0] = datetime.now() - status_df['Início'][0]
        hours = status_df['Tempo'][0].seconds // 3600
        minutes = (status_df['Tempo'][0].seconds // 60) - (hours * 60)
        seconds = status_df['Tempo'][0].seconds - (minutes * 60) - (hours * 3600)
        format_datetime = ("%02d" % hours) + ':' + ("%02d" % minutes) + ':' + ("%02d" % seconds)
        status_df['Tempo'][0] = format_datetime
        json_data.append(status_df.to_json())
        stop_query += f""" AND tStartTime >= '{datetime.now().date()} 00:00:00' GROUP BY nShift"""
    else:
        query += f""" AND tStartTime >= '{init} 00:00:00' AND tStartTime <= '{end} 23:59:59'"""
        stop_query += f""" AND tStartTime >= '{init} 00:00:00' AND tStartTime <= '{end} 23:59:59' 
                                GROUP BY nShift"""

    if len(json_data) == 0:
        json_data.append(pd.DataFrame().to_json())

    df = pd.read_sql(query, cnnx)
    df = df.fillna(0)
    json_data.append(df.to_json())

    stop_df = pd.read_sql(stop_query, cnnx)
    stop_df = stop_df.fillna(0)
    json_data.append(stop_df.to_json())

    return json.dumps(json_data)

# FUNÇÃO QUE RETORNA OS DADOS DA ABA "EMPRÉSTIMO" DO CT
def _EMP_DATA(arg, json_data, realtime_query, dash_type, init, end):
    if dash_type == 'realtime':
        status_df = pd.read_sql(realtime_query, cnnx)
        status_df = status_df.fillna(0)
        json_data.append(status_df.to_json())
        aux = "DATA_SAIDA IS NULL AND CT_ATUAL NOT LIKE ('%' + CT_ORIGEM + '%')"
    else:
        aux = f"""'{end} 23:59:59' >= DATA_ENTRADA AND DATA_ENTRADA >= '{init} 00:00:00' 
        AND CT_ATUAL NOT LIKE ('%' + CT_ORIGEM + '%')"""

    query = f"""SELECT NOME, TURNO, MATRICULA, CT_ORIGEM, SUM(H_TRABALHADAS) AS 
    H_TRABALHADAS, SUM(H_PONTO) AS H_PONTO FROM (SELECT NOME, CASE WHEN DATA_SAIDA IS NULL THEN 
    ROUND(CAST(DATEDIFF(SECOND, DATA_ENTRADA, GETDATE()) AS FLOAT)/3600, 2) ELSE
    ROUND(CAST(DATEDIFF(SECOND, DATA_ENTRADA, DATA_SAIDA) AS FLOAT)/3600, 2) END AS H_TRABALHADAS, 
    (CASE WHEN TURNO = 1 THEN CAST(8.48 AS float) ELSE (CASE WHEN TURNO = 2 THEN CAST(8.2 AS float) ELSE 
    (CASE WHEN TURNO = 3 AND DATEPART(WEEKDAY, DATA_ENTRADA) NOT IN (1, 7) THEN CAST(4.75 AS float) ELSE 
    (CASE WHEN Turno = 3 AND DATEPART(WEEKDAY, DATA_ENTRADA) = 1 THEN CAST(6.2 AS float) ELSE 
    CAST(9.5 AS float) END) END) END) END) AS H_PONTO, TURNO, CT_ORIGEM, MATRICULA FROM CONTROLE_OPERADORES 
    WHERE CT_ATUAL = '{arg}' AND {aux}) T1 GROUP BY NOME, TURNO, MATRICULA, CT_ORIGEM 
    ORDER BY NOME, TURNO"""

    if len(json_data) == 0:
        json_data.append(pd.DataFrame().to_json())

    df = pd.read_sql(query, cnnx)
    json_data.append(df.to_json())


    return json.dumps(json_data)


@reports_productiveHours_bp.route('/dashboards/chp', methods=['GET'])
def productiveHours_get():
    return render_template('reports.productiveHours/ph_route.html', video='net1.mp4', res=0)

# OVERVIEW DO CONTROLE DE HORAS PRODUTIVAS, PÁGINA INICIAL QUE RETORNA OS DADOS
@reports_productiveHours_bp.route('/dashboards/chp/overview', methods=['GET'])
def productiveHours_overview_get():
    return render_template(
        'reports.productiveHours/ph_overview.html'
        , video='net1.mp4'
        , res=0
    )


# PÁGINA DE SELEÇÃO DE VISUALIZAÇÃO DE CENTROS DE TRABALHO
@reports_productiveHours_bp.route('/dashboards/chp/select', methods=['GET'])
def productiveHours_panel_get():
    return render_template(
        'reports.productiveHours/ph_workCenter_panel.html'
        , video='net1.mp4'
        , res=0
    )

@reports_productiveHours_bp.route('/dashboards/chp/select', methods=['POST'])
def productiveHours_panel_post():

    query = "select distinct sDescription from OEEQWorkCellDetail"
    options = return_options(query, 'sDescription', 'ftm')

    info = [['CT', 'STATUS', 'PLAN', 'REAL', 'DIF']]
    engine = get_engine('ftm')
    with engine.connect() as cnnx:

        for option in options:

            if option != 'Torneamento':
        
                query = (
                    f"SELECT TOP(1) sDescription 'Máquina', sEventDescription 'Status', tStart "
                    f"'Início', dDuration 'Tempo', sReasonCode 'Descricao' "
                    f"FROM dbo.OEEQEventDetail WITH (NOLOCK) WHERE sDescription='{option}' AND ("
                    f"sEventDescription='Parada' OR sEventDescription='Produção') "
                    f"AND tStart>=(GetDate()-30) AND dDuration>'00:00:01' ORDER BY tStart DESC")

                status = pd.read_sql(query, cnnx)['Status'].values.tolist()[0]

                if status != 'Produção':
                    status = pd.read_sql(query, cnnx)['Descricao'].values.tolist()[0]

                query = (f"SELECT TOP(1) NR_OPERADORES "
                            f"FROM WORK_CELL_OP WHERE ID_WORK_UNIT='{option.split('-')[0]}' ORDER BY "
                            f"DT_EXEC_START DESC, DT_PLANN_START DESC")

                numplan = pd.read_sql(query, cnnx).values.tolist()
                if not numplan:
                    numplan = 0
                else:
                    numplan = numplan[0][0]

                query = (f"SELECT CT_Atual, COUNT(Matricula) as qtdOperadores "
                            f"FROM CONTROLE_OPERADORES WHERE Data_Saida IS NULL GROUP BY CT_Atual")

                numreal = pd.read_sql(query, cnnx).values.tolist()
                numreal_val = 0
                if numreal:
                    for val in numreal:
                        if option in val:
                            numreal_val = numreal[numreal.index(val)][1]
                            break
                        else:
                            numreal_val = 0

                info.append([option, status, numplan, numreal_val, numreal_val - int(numplan)])

    return json.dumps({'data': info})

# PÁGINA DE EXIBIÇÃO DOS DADOS DO CT EM ESPECÍFICO, QUE ATUALIZA COM UMA TAXA PERIÓDICA DE 5 SEGUNDOS
@reports_productiveHours_bp.route('/dashboards/chp/ct', methods=['GET'])
def productiveHours_workcenter_get():

    return render_template(
        'reports.productiveHours/ph_workCenter_detail.html'
        , video='net1.mp4'
        , res=20
        , ct=request.args["ct"]
        , today=str(datetime.now().date())
    )

@reports_productiveHours_bp.route('/dashboards/chp/ct', methods=['POST'])
def productiveHours_workcenter_post():

    arg = request.get_json()[0]
    json_data = []
    init = ''
    end = ''
    if arg == 'geral':
        return_val = _MAIN_SCREEN(json_data)
        return return_val

    else:
        realtime_query = f"""SELECT TOP(1) sDescription 'Máquina', sEventDescription 'Status', tStart 
        'Início', dDuration 'Tempo', sReasonCode 'Descricao', (SELECT COUNT(Matricula) FROM 
        CONTROLE_OPERADORES WHERE Data_Saida IS NULL AND CT_ATUAL = '{arg}') AS NUMREAL, (SELECT TOP(1) 
        NR_OPERADORES FROM WORK_CELL_OP WHERE ID_WORK_UNIT = '{arg.split("-")[0]}' ORDER BY DT_EXEC_START, DT_PLANN_START 
        DESC) AS NUMPLAN FROM dbo.OEEQEventDetail WITH (NOLOCK) WHERE sDescription = '{arg}' AND 
        (sEventDescription='Parada' OR sEventDescription='Produção')AND tStart>=(GetDate()-30) 
        AND dDuration>'00:00:01' ORDER BY tStart DESC"""

        dash_type = request.get_json()[1]
        dash_area = request.get_json()[2]
        if dash_area == 'oper':
            if dash_type == 'realtime':
                return_val = _OPERS_REALTIME(arg, json_data, realtime_query)
                return return_val

            elif dash_type == 'periodic':
                init = request.get_json()[3]
                end = request.get_json()[4]
                return_val = _OPERS_PERIODIC(arg, json_data, init, end)
                return return_val

        elif dash_area == 'gen':
            if dash_type == 'periodic':
                init = request.get_json()[3]
                end = request.get_json()[4]
            return_val = _GENERAL_DATA(arg, json_data, realtime_query, dash_type, init, end)
            return return_val

        else:
            if dash_type == 'periodic':
                init = request.get_json()[3]
                end = request.get_json()[4]
            return_val = _EMP_DATA(arg, json_data, realtime_query, dash_type, init, end)
            return return_val
