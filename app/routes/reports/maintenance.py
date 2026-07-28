import io
import json
import numpy as np
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import pandas as pd
from zeep import Client
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPBasicAuth
from datetime import time

from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app.utils.business import getStopsData
from app.utils.db_utils import engine_run_query
from app.utils.dynamic_constants import getPlex
from app.utils.permissions import get_permission

maintenance = get_permission('MAINTENANCE')

reports_maintenance_bp = Blueprint('reports_maintenance', __name__)

@reports_maintenance_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)


# CRIA CONEXÃO COM WEB SERVICE SOAP SAP
def _CREATE_CONNECTION():
    # URL do serviço WSDL do SAP
    wsdl_url = 'https://ecp.sap.randon.com.br:443/sap/bc/srt/wsdl/flv_10002A1011D1/bndg_url/sap/bc/srt/scs/sap/zmes_bbp_rfc_read_table?sap-client=190'

    # Credenciais de autenticação
    username = 'JOST_ROCKWEL'
    password = 'f9c3s2m4'

    # Configurar sessão HTTP com autenticação básica
    session = Session()
    session.auth = HTTPBasicAuth(username, password)

    # Configurar transporte com a sessão HT  TP
    transport = Transport(session=session)

    return session, Client(wsdl_url, transport=transport)

# FUNÇÃO PARA PEGAR OS DADOS DO WEB SERVICE
def _GET_WEB_SERVICE_DATA(fields, options, table, client):

    to_filter = {
        'Data': {'item': []},
        'Delimiter': '$',
        'Fields': {'item': fields},
        'NoData': '',
        'Options': {'item': options},
        'QueryTable': table
    }

    RECEIVED_DATA = client.service.BbpRfcReadTable(**to_filter)
    NEW_ROWS = RECEIVED_DATA['Data']['item'] if RECEIVED_DATA['Data'] else []
    NEW_DATA = [row['Wa'].split(to_filter['Delimiter']) for row in NEW_ROWS]
    
    NEW_COLUMNS = [field['Fieldname'] for field in to_filter['Fields']['item']]

    return pd.DataFrame(NEW_DATA, columns=NEW_COLUMNS)

# CHAMA A FUNÇÃO getWebServiceData COM OS PARAMETROS E TRATA PREVIAMENTE OS DADOS PRINCIPAIS DOS DASHS E RELATÓRIOS
def _TRANSFORM_WEB_SERVICE_DATA(minorDate, upperDate, note):
    
    session, client = _CREATE_CONNECTION()

    # Estrutura de dados para a solicitação
    FIELDS = [
                {'Fieldname': 'QMNUM', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'QMDAT', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'MZEIT', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'QMART', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'LTRMN', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'AUFNR', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'QMTXT', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'EQUNR', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'KOSTL', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'AUSBS', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'ARBPL', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'NOTIFICATIONPERSONRESPONSIBLE', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'PHASE', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
            ]
    
    if minorDate:
        EXTRA = "QMDAT >= '" + minorDate + "'"
    else:
        EXTRA = "QMNUM = '0000" + note + "'"
    OPTIONS = [
                {'Text': f"""(IWERK = '2310' AND {EXTRA}) AND """},
                {'Text': f"(QMART = 'MC')"}
            ]
    VIQMEL = _GET_WEB_SERVICE_DATA(FIELDS, OPTIONS, 'VIQMEL', client)

    noteFilter = ''
    if len(VIQMEL) == 1:
        noteFilter = "AND AUFNR = '" + VIQMEL['AUFNR'][0] + "'" if VIQMEL['AUFNR'][0] != '            ' else ''

    # Estrutura de dados para a solicitação
    FIELDS = [
                {'Fieldname': 'AUART', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'AUFNR', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''}
            ]
    
    if minorDate:
        EXTRA = "AND ERDAT >= '" + minorDate + "'"
    else:
        EXTRA = noteFilter
    OPTIONS = [
                {'Text': f"WERKS = '2310' {EXTRA} AND AUART LIKE 'M%'"}
            ]
    CAUFV = _GET_WEB_SERVICE_DATA(FIELDS, OPTIONS, 'CAUFV', client)

    # Estrutura de dados para a solicitação
    FIELDS = [
                {'Fieldname': 'PERNR', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'ISMNW', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'LTXA1', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'AUFNR', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''}
            ]
    if minorDate:
        EXTRA = "AND ERSDA >= '" + minorDate + "'"
    else:
        EXTRA = noteFilter
    OPTIONS = [
                {'Text': f"WERKS = '2310' AND ORIND = '3' {EXTRA}"}
            ]
    AFRU = _GET_WEB_SERVICE_DATA(FIELDS, OPTIONS, 'AFRU', client)

    # Estrutura de dados para a solicitação
    FIELDS = [
                {'Fieldname': 'EQUNR', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'EQKTU', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''}
            ]
    OPTIONS = [
                {'Text': f"EQUNR LIKE 'MJ%' OR EQUNR LIKE 'FJ%'"}
            ]
    EQKT = _GET_WEB_SERVICE_DATA(FIELDS, OPTIONS, 'EQKT', client)

    # Estrutura de dados para a solicitação]
    FIELDS = [
                {'Fieldname': 'KTEXT', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'KOSTL', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''}
            ]
    OPTIONS = [
                {'Text': f"KOSTL LIKE '2300%'"}
            ]
    CSKT = _GET_WEB_SERVICE_DATA(FIELDS, OPTIONS, 'CSKT', client)

    # Estrutura de dados para a solicitação]
    FIELDS = [
                {'Fieldname': 'ARBPL', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
                {'Fieldname': 'OBJID', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''}
            ]
    OPTIONS = [
                {'Text': f"WERKS = '2310'"}
            ]
    CRHD = _GET_WEB_SERVICE_DATA(FIELDS, OPTIONS, 'CRHD', client)


    session.close()
    
    order_map = {   
        'MPRV': 'Preventiva',
        'MPRO': 'Programada',
        'MCOR': 'Corretiva',
        'MFER': 'Ferramentaria',
        'MMLH': 'Melhoria',
        'MPRD': 'Preditiva',
        'MTPM': 'Manutenção TPM',
        'MINV': 'Investimento'
    }

    VIQMEL['QMDATS'] = pd.to_datetime(VIQMEL['QMDAT'] + ' ' + VIQMEL['MZEIT']).dt.strftime('%d/%m/%Y %H:%M:%S')
    VIQMEL['QMDATWEEK'] = pd.to_datetime(VIQMEL['QMDAT'] + ' ' + VIQMEL['MZEIT']).dt.dayofweek 
    VIQMEL['QMDAT'] = pd.to_datetime(VIQMEL['QMDAT'] + ' ' + VIQMEL['MZEIT'])
    VIQMEL.drop(columns=['MZEIT'], inplace=True)

    if upperDate:
        VIQMEL = VIQMEL[VIQMEL['QMDAT'] <= upperDate + ' 23:59:00']

    if not VIQMEL.empty:
        VIQMEL['SHIFT'] = VIQMEL.apply(_GET_SHIFT, axis=1)
    else:
        VIQMEL['SHIFT'] = None

    VIQMEL['QMNUM'] = VIQMEL['QMNUM'].str.slice(4)
    VIQMEL['AUFNR'] = VIQMEL['AUFNR'].apply(lambda x: None if str(x) == '            ' else x).str.slice(4)
    VIQMEL['AUSBS'] = VIQMEL['AUSBS'].apply(lambda x: None if str(x) == '00000000' else x)
    VIQMEL['QMTXT'] = VIQMEL['QMTXT'].str.strip()

    VIQMEL['LTRMN'] = VIQMEL['LTRMN'].apply(lambda x: None if str(x) == '00000000' else x)
    VIQMEL['LTRMN'] = pd.to_datetime(VIQMEL['LTRMN']).dt.strftime('%d/%m/%Y')

    CAUFV['AUART'] = CAUFV['AUART'].map(order_map).astype(str)
    CAUFV['AUFNR'] = CAUFV['AUFNR'].str.slice(4)

    AFRU['AUFNR'] = AFRU['AUFNR'].str.slice(4)
    AFRU['LTXA1'] = AFRU['LTXA1'].str.strip()
    AFRU['ISMNW'] = AFRU['ISMNW'].str.strip().astype(float)


    phase_map = {
        '1' : 'Em aberto',
        '2' : 'Adiado',
        '3' : 'Em processamento',
        '4' : 'Concluído',
        '5' : 'Eliminação',
    }

    VIQMEL['PHASE'] = VIQMEL['PHASE'].map(phase_map).astype(str)
    
    CRHD['ARBPL'] = CRHD['ARBPL'].str.strip()

    
    query = "SELECT registration, name FROM JDT_USER_DETAILS"
    tec_names = engine_run_query(query, 'jdt')

    VIQMEL = pd.merge(left=VIQMEL, right=tec_names, left_on='NOTIFICATIONPERSONRESPONSIBLE', right_on='registration', how='left')
    AFRU = pd.merge(left=AFRU, right=tec_names, left_on='PERNR', right_on='registration', how='left')

    ALL_DATA = pd.merge(left=VIQMEL, right=CRHD, left_on='ARBPL', right_on='OBJID', how='left')
    ALL_DATA = pd.merge(left=ALL_DATA, right=CAUFV, on='AUFNR', how='left')
    ALL_DATA = pd.merge(left=ALL_DATA, right=CSKT, on='KOSTL', how='left')
    ALL_DATA = pd.merge(left=ALL_DATA, right=AFRU, on='AUFNR', how='left')
    ALL_DATA = pd.merge(left=ALL_DATA, right=EQKT, on='EQUNR', how='left')

    return ALL_DATA

# CHAMA A FUNÇÃO getWebServiceData COM OS PARAMETROS E LISTA OS CENTROS DE TRABALHOS
def _GET_WORKCENTERS():
    session, client = _CREATE_CONNECTION()

    FIELDS = [
            {'Fieldname': 'KTEXT', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
            {'Fieldname': 'KOSTL', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''}
        ]
    OPTIONS = [
            {'Text': f"KOSTL LIKE '2300%'"}
        ]

    CSKT = _GET_WEB_SERVICE_DATA(FIELDS, OPTIONS, 'CSKT', client)
    FIELDS = [
            {'Fieldname': 'KOSAR', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''},
            {'Fieldname': 'KOSTL', 'Offset': '', 'Length': '', 'Type': '', 'Fieldtext': ''}
        ]
    OPTIONS = [
            {'Text': f"KOSTL LIKE '2300%'"}
        ]
    CSKS = _GET_WEB_SERVICE_DATA(FIELDS, OPTIONS, 'CSKS', client)

    session.close()

    CSKT = pd.merge(left=CSKT, right=CSKS, on='KOSTL', how='left').sort_values(by='KTEXT', ascending=True)
    CSKT = CSKT[(CSKT['KOSAR'] == 'P') & (CSKT['KTEXT'].str.strip() != 'Aprendizes')]

    return CSKT

# FUNCÃO PARA PEGAR UM TURNO DE TRABALHO
def _GET_SHIFT(row):
    t = row['QMDAT'].time()
    d = row['QMDATWEEK']

    if d == 6 or d == 7:  # Sábado
        if time(2, 12) <= t <= time(12, 48):
            return '3'
    else:  # Segunda a Sexta
        if time(7, 12) <= t <= time(17, 0):
            return '1'
        elif time(17, 0) <= t <= time(23, 59) or time(0, 0) <= t <= time(2, 12):
            return '2'
        elif time(2, 12) <= t <= time(7, 12):
            return '3'
    
    return None

# FUNÇÃO PARA PEGAR OS DADOS DE DISPONIBILIDADE E MTTR/MTBF
def _GET_MAINTENANCE_AVAILABILITY_DATA(payload):

    payload['m_group'] = ["Manutenção"]

    mic_group_time_map = {
        '0': "FORMAT(tStartTime, 'dd/MM')",
        '1': "CONCAT(YEAR(tStartTime), '/', RIGHT('0' + CAST(DATEPART(WEEK, tStartTime) AS VARCHAR), 2))",
        '2': "CONCAT(YEAR(tStartTime), '/', RIGHT('0' + CAST(MONTH(tStartTime) AS VARCHAR), 2))",
        '3': "CAST(YEAR(tStartTime) AS VARCHAR)",
        '5': "NULL"
    }

    group_by_clause = f"T1.sDescription, T2.GRUPO"
    if payload['time_group'] != '5':
        group_by_clause += f", {mic_group_time_map[payload['time_group']]}"

    where_mic_w_count = ', '.join([f':w_mic_val{i}' for i in range(len(payload['w_name_mic']))]) if payload['w_name_mic'] else ':w_mic_val0'
    if payload['w_name_mic']:
        where_mic_w_values = {f'w_mic_val{i}': v for i, v in enumerate(payload['w_name_mic'])}
    else:
        where_mic_w_values = {'w_mic_val0': 'aaa'}

    where_plex_w_count = ', '.join([f':w_plex_val{i}' for i in range(len(payload['w_name_plex']))]) if payload['w_name_plex'] else ':w_plex_val0'
    if payload['w_name_plex']:
        where_plex_w_values = {f'w_plex_val{i}': v for i, v in enumerate(payload['w_name_plex'])}
    else:
        where_plex_w_values = {'w_plex_val0': 1}

    where_group_count = ', '.join([f':w_group_val{i}' for i in range(len(payload['w_group']))]) if payload['w_group'] else ':w_group_val0'
    if payload['w_group']:
        where_group_values = {f'w_group_val{i}': v for i, v in enumerate(payload['w_group'])}
    else:
        where_group_values = {'w_group_val0': 'aaa'}

    where_mic_params = {
        'start_date': payload['start_date']
        , 'end_date': payload['end_date']
        , **where_mic_w_values
        , **where_plex_w_values
        , **where_group_values
    }

    availability_mic_query = f"""
        
        SELECT
        
            NULLIF(SUM(dAvailSec), 0) / 60.0 / 60.0 AS TotalAvail
            , SUM(dRunSec) / 60.0 AS TotalRun

            , T1.sDescription AS Workcenter_Name
            , T2.GRUPO AS Workcenter_Group
            , {mic_group_time_map[payload['time_group']]} AS Time_Group
        
        FROM OEEQWorkCellDetail T1
        JOIN CONFIG_TABLET T2 ON T1.sDescription = T2.NOME_MAQUINA

        WHERE 

            T1.tStartTime BETWEEN
            :start_date
            AND CASE 
                WHEN T2.CT_PLEX_DATA < :end_date
                THEN T2.CT_PLEX_DATA 
                ELSE :end_date
            END

            AND (T1.sDescription IN ({where_mic_w_count}) OR T2.CT_PLEX IN ({where_plex_w_count}))
            AND T2.GRUPO IN ({where_group_count})
            AND T1.nShift in ('1', '2', '3')

        GROUP BY {group_by_clause}"""
    
    where_plex_w_proc = json.dumps(payload['w_name_plex'], ensure_ascii=False)
    where_group_proc = json.dumps(payload['w_group'], ensure_ascii=False)
    where_plex_shift_pc = json.dumps(['Primeiro', 'Segundo', 'Terceiro'], ensure_ascii=False)

    where_plex_params_proc = {
        'start_date': payload['start_date']
        , 'end_date': payload['end_date']
        , 'plex_w': where_plex_w_proc
        , 'plex_g': where_group_proc
        , 'plex_s': where_plex_shift_pc
        , 'group': payload.get('time_group')
    }

    availability_plex_query = f"""
            EXEC ('sproc329396_18311230_1264675(?, ?, ?, ?, ?, ?, ?, ?, ?)'
                            , :start_date
                            , :end_date
                            , :plex_w
                            , :plex_g
                            , :plex_s
                            , :group
                            , 1
                            , 1
                            , 0)
                        AT [PLEX_DSN_JOST]
                """
    print(availability_plex_query)
    print(where_plex_params_proc)
    with ThreadPoolExecutor() as executor:
        availability_mic = executor.submit(engine_run_query, availability_mic_query, 'ftm', where_mic_params)
        availability_plex = executor.submit(engine_run_query, availability_plex_query, 'plex', where_plex_params_proc)
        maintenance_events = executor.submit(getStopsData, payload)

    availability_mic = availability_mic.result()
    availability_plex = availability_plex.result()
    maintenance_events = maintenance_events.result()

    availability = pd.concat([availability_plex[['TotalRun', 'TotalAvail', 'Workcenter_Name', 'Workcenter_Group', 'Time_Group']], availability_mic])

    maintenance_events['Log_Date'] = pd.to_datetime(maintenance_events['Log_Date'], format='%d/%m/%Y %H:%M:%S')

    if payload['time_group'] == '0':
        maintenance_events['Time_Group'] = maintenance_events['Log_Date'].dt.strftime('%d/%m')
    elif payload['time_group'] == '1':
        maintenance_events['Time_Group'] = maintenance_events['Log_Date'].dt.year.astype(str) + '/' + maintenance_events['Log_Date'].dt.isocalendar().week.astype(str).str.zfill(2)
    elif payload['time_group'] == '2':
        maintenance_events['Time_Group'] = maintenance_events['Log_Date'].dt.year.astype(str) + '/' + maintenance_events['Log_Date'].dt.month.astype(str).str.zfill(2)
    elif payload['time_group'] == '3':
        maintenance_events['Time_Group'] = maintenance_events['Log_Date'].dt.year.astype(str)

    if payload['time_group'] != '5':
        events = maintenance_events.groupby(['Workcenter_Name', 'Workcenter_Group', 'Time_Group'], as_index=False).agg(
            Log_Minutes_Sum=('Log_Minutes', 'sum'),
            Log_Minutes_Count=('Log_Minutes', 'count')
        )
        merged_data = pd.merge(events, availability, on=['Workcenter_Name', 'Workcenter_Group', 'Time_Group'], how='outer')

    else: 
        events = maintenance_events.groupby(['Workcenter_Name', 'Workcenter_Group'], as_index=False).agg(
            Log_Minutes_Sum=('Log_Minutes', 'sum'),
            Log_Minutes_Count=('Log_Minutes', 'count')
        )
        merged_data = pd.merge(events, availability, on=['Workcenter_Name', 'Workcenter_Group'], how='outer')



    merged_data['Log_Minutes_Sum'] = merged_data['Log_Minutes_Sum'].fillna(0)
    merged_data['Log_Minutes_Count'] = merged_data['Log_Minutes_Count'].fillna(0)

    merged_data['MTTR'] = np.where(
        merged_data['Log_Minutes_Count'] > 0,
        merged_data['Log_Minutes_Sum'] / merged_data['Log_Minutes_Count'],
        0
    )

    merged_data['MTBF'] = np.where(
        merged_data['Log_Minutes_Count'] > 0,
        (merged_data['TotalAvail'] * 60.0 - merged_data['Log_Minutes_Sum']) / merged_data['Log_Minutes_Count'],
        1
    )

    denominator = merged_data['MTBF'] + merged_data['MTTR']
    merged_data['CALC'] = np.where(
        denominator > 0,
        merged_data['MTBF'] / denominator,
        1
    )

    Log_Minutes_Sum_Total = float(merged_data['Log_Minutes_Sum'].sum())
    Log_Minutes_Count_Total = float(merged_data['Log_Minutes_Count'].sum())
    Availability_Total = float(merged_data['TotalAvail'].sum()  * 60.0)

    # MTTR: Média de tempo para reparar
    if Log_Minutes_Count_Total > 0:
        MTTR = float(Log_Minutes_Sum_Total / Log_Minutes_Count_Total)
    else:
        MTTR = 0.0

    # MTBF: Média de tempo entre falhas
    if Log_Minutes_Count_Total > 0:
        MTBF = float((Availability_Total - Log_Minutes_Sum_Total) / Log_Minutes_Count_Total)
    else:
        MTBF = 1.0  # Como fallback padrão

    # CALC: Disponibilidade (MTBF / (MTBF + MTTR))
    denominator = MTBF + MTTR
    if denominator > 0:
        CALC = float(MTBF / denominator)
    else:
        CALC = 1.0  # Fallback para 100% disponível


    return merged_data, MTTR, MTBF, CALC, Log_Minutes_Sum_Total, Log_Minutes_Count_Total, Availability_Total


# PAGINA PARA CONSULTA DE NOTAS - APP DA FÁBRICA
@reports_maintenance_bp.route('/manutencao/controle/consulta', methods=['GET'])
def maintenance_search_get():

    workCenterList = _GET_WORKCENTERS()['KTEXT'].drop_duplicates().values.tolist()

    return render_template(
        'reports.maintenance/maintenance_search.html'
        , workCenter=workCenterList
        , user=current_user.id
    )

@reports_maintenance_bp.route('/manutencao/controle/consulta', methods=['POST'])
def maintenance_search_post():

    if 'noteNumber' in request.get_json():

        ALL_DATA = _TRANSFORM_WEB_SERVICE_DATA(None, None, request.get_json()['noteNumber']).astype(str)
        ALL_DATA = ALL_DATA[ALL_DATA['PHASE'] != "Eliminação"]

        if len(ALL_DATA) != 0:
            return jsonify({
                    'id': ALL_DATA['QMNUM'][0],
                    'main_order': ALL_DATA['AUFNR'][0],
                    'noteType': ALL_DATA['QMART'][0],
                    'type': ALL_DATA['AUART'][0],
                    'statusOrder': ALL_DATA['PHASE'][0],
                    'openDate': ALL_DATA['QMDATS'][0],
                    'workCenter': ALL_DATA['KTEXT'][0],
                    'equipmentName': ALL_DATA['EQKTU'][0],
                    'problem': ALL_DATA['QMTXT'][0],
                    'text': ALL_DATA['LTXA1'][0],
                    'responsible': ALL_DATA['name_x'][0],
                    'deadline': ALL_DATA['LTRMN'][0]
            })
        return jsonify({'id': 'NOT FOUND'})
    
    else:

        status = ['Concluído', 'Adiado', 'Eliminação'] if request.get_json()['activated'] else ['Em aberto', 'Em processamento']

        ALL_DATA = _TRANSFORM_WEB_SERVICE_DATA(request.get_json()['startDate'].replace('-', ''), request.get_json()['endDate'], None).astype(str)
        ALL_DATA = ALL_DATA[(ALL_DATA['KTEXT'] == request.get_json()['workCenter']) & (ALL_DATA['PHASE'].isin(status)) & (ALL_DATA['PHASE'] != "Eliminação")].drop_duplicates(subset=['QMNUM'], keep='first')
        send_json = {
            'id': ALL_DATA['QMNUM'].to_list(),
            'main_order': ALL_DATA['AUFNR'].to_list(),
            'openDate': ALL_DATA['QMDATS'].to_list(),
            'equipmentName': ALL_DATA['EQKTU'].to_list(),
            'noteType': ALL_DATA['QMART'].to_list(),
            'responsible': ALL_DATA['name_x'].to_list(),
            'deadline': ALL_DATA['LTRMN'].to_list(),
            'problem': ALL_DATA['QMTXT'].to_list()
        }

        return jsonify(send_json)


# PAGINA PARA VISUALIZAR OS GRÁFICOS DAS NOTAS
@reports_maintenance_bp.route('/manutencao/controle', methods=['GET'])
def maintenance_notes_get():

    query = f"""SELECT
                    DISTINCT name, registration
                FROM 
                    JDT_USER_DETAILS
                WHERE department LIKE 'Manutenção%' AND position LIKE 'Técnico%'"""
    names = engine_run_query(query, 'jdt')['name'].dropna().tolist()

    workCenterList = _GET_WORKCENTERS()['KTEXT'].drop_duplicates().str.strip().values.tolist()

    return render_template('reports.maintenance/maintenance_dash_notes.html', names=names, equipments=workCenterList)


# MÉTODO PARA RETORNAR A ESTRUTURA/DADOS DOS GRÁFICOS DAS NOTAS
@reports_maintenance_bp.route('/manutencao/controle', methods=['POST'])
def maintenance_notes_post():

    data_to_send = _TRANSFORM_WEB_SERVICE_DATA(request.get_json()['start_date'].replace('-', ''), request.get_json()['end_date'], None)

    status_request = request.get_json()['status']
    status = []

    if status_request[0] == 'Abertas':
        status += ['Em aberto', 'Em processamento']
    if status_request[1] == 'Fechadas':
        status+= ['Concluído', 'Adiado', 'Eliminação']

    responsible = request.get_json()['responsible'] + [np.nan] if "None" in request.get_json()['responsible'] else request.get_json()['responsible']

    data_to_send = data_to_send[(data_to_send['KTEXT'].isin(request.get_json()['workCenter'])) & 
                                (data_to_send['ARBPL_y'].isin(request.get_json()['area'])) & 
                                (data_to_send['SHIFT'].isin(request.get_json()['shift'])) &
                                (data_to_send['name_x'].isin(responsible)) &
                                (data_to_send['PHASE'].isin(status))]

    # BARCHARTS CONFIG    
    hours_by_tech = data_to_send[data_to_send['AUART'].notnull()].groupby(['name_y', 'AUART']).agg({'ISMNW': 'sum'}).reset_index().rename(columns={'name_y': 'KTEXT', 'AUART': 'PHASE', 'ISMNW': 'QTT'})

    data_to_send = data_to_send.drop_duplicates(subset='QMNUM')
    notes_by_workCenter = data_to_send.groupby(['KTEXT', 'PHASE']).size().reset_index(name='QTT')


    # PIECHARTS CONFIG
    notes_by_status = data_to_send['PHASE'].value_counts().reset_index().rename(columns={'PHASE': 'LABELS', 'count': 'QTT'})
    notes_by_type = data_to_send['QMART'].value_counts().reset_index().rename(columns={'QMART': 'LABELS', 'count': 'QTT'})

    orders_by_status = data_to_send[data_to_send['AUART'].notnull()]['PHASE'].value_counts().reset_index().rename(columns={'PHASE': 'LABELS', 'count': 'QTT'})
    orders_by_type = data_to_send[data_to_send['AUART'].notnull()]['AUART'].value_counts().reset_index().rename(columns={'AUART': 'LABELS', 'count': 'QTT'})

    # KPI CONFIG
    total_notes = data_to_send['QMNUM'].count()

    # TABLE CONFIG
    table = data_to_send.sort_values(by='QMDAT', ascending=False)[['QMDATS', 'QMNUM', 'KTEXT', 'QMTXT', 'name_x', 'LTRMN', 'AUFNR', 'AUART', 'PHASE']]

    data_to_send = {
        'barChart1': hours_by_tech.to_json(orient='records')
        , 'barChart2': notes_by_workCenter.to_json(orient='records')
        , 'pieChart1': notes_by_status.to_json(orient='records')
        , 'pieChart2': notes_by_type.to_json(orient='records')
        , 'pieChart3': orders_by_status.to_json(orient='records')
        , 'pieChart4': orders_by_type.to_json(orient='records')
        , 'totalNotes': str(total_notes)
        , 'table': table.to_json(orient='records')
    }

    return data_to_send

# PAGINA PARA VISUALIZAR OS GRÁFICOS DE MTBF E MTTR
@reports_maintenance_bp.route('/manutencao/disponibilidade', methods=['GET'])
def maintenance_availability_get():

    query = f"""SELECT 
                    GRUPO AS Workcenter_Group
                    , LEFT(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) - 1) AS Workcenter_Code
                    , SUBSTRING(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) + 1, LEN(NOME_MAQUINA)) AS Name
                    , 1 AS Workcenter_Key
                FROM CONFIG_TABLET WHERE CT_PLEX IS NULL"""
    mic_workcenters = engine_run_query(query, 'ftm')

    mes_workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]
    workcenters = pd.concat([mes_workcenters[~mes_workcenters['Workcenter_Code'].isin(mic_workcenters['Workcenter_Code'])], mic_workcenters])

    events = getPlex('events')
    events = events[(~events['Code'].isna()) & (events['Workcenter_Event_Group'] == 'Manutenção')].reset_index(drop=True)
    events['Code'] = events['Code'].astype(int)

    return render_template(
        'reports.maintenance/maintenance_availability.html'
        , events=events.sort_values(by='Code').to_dict(orient='records')
        , workcenters=workcenters.sort_values(by="Workcenter_Code").to_dict(orient="records")
    )

@reports_maintenance_bp.route('/manutencao/disponibilidade', methods=['POST'])
def maintenance_availability_post():

    payload = request.get_json()
    payload['start_date'] = payload['start_date'].replace('T', ' ') + ':00'
    payload['end_date'] = payload['end_date'].replace('T', ' ') + ':00'

    merged_data, MTTR, MTBF, CALC, Log_Minutes_Sum_Total, Log_Minutes_Count_Total, Availability_Total = _GET_MAINTENANCE_AVAILABILITY_DATA(payload)

    if request.args.get('type') == 'dash':
        
        return jsonify({   
                'workcenters': merged_data.sort_values(by="CALC", ascending=False).to_dict(orient='records'),
                'overall': {
                    'MTTR': MTTR,
                    'MTBF': MTBF,
                    'CALC': CALC,
                    'Log_Minutes_Sum': Log_Minutes_Sum_Total,
                    'Log_Minutes_Count': Log_Minutes_Count_Total,
                    'Availability': Availability_Total
                }})
    
    else:

        merged_data['TotalRun'] = merged_data['TotalRun'] * 60
        merged_data['TotalAvail'] = merged_data['TotalAvail'] * 60

        # 1. Renomear colunas do DataFrame principal
        merged_data = merged_data.rename(columns={
            'Time_Group': 'Agrupador',
            'Workcenter_Name': 'Centro de Trabalho',
            'Workcenter_Group': 'Grupo',
            'Log_Minutes_Sum': 'Tempo Parado (Min.)',
            'Log_Minutes_Count': 'Quantidade de Parada',
            'TotalRun': 'Tempo em Produção (Min.)',
            'TotalAvail': 'Tempo Disponível (Min.)',
            'MTBF': 'MTBF',
            'MTTR': 'MTTR',
            'CALC': 'Disponibilidade'
        })

        # 2. Criar dicionário com dados do resumo
        overall = {
            'MTTR': MTTR,
            'MTBF': MTBF,
            'Disponibilidade': CALC,
            'Tempo Parado (Min.)': Log_Minutes_Sum_Total,
            'Quantidade de Parada': Log_Minutes_Count_Total,
            'Tempo Disponível (Min.)': Availability_Total
        }
        overall_df = pd.DataFrame(list(overall.items()), columns=["Métrica", "Valor"])

        # 3. Criar planilha Excel com openpyxl
        wb = Workbook()

        # Aba 1: Workcenters
        ws1 = wb.active
        ws1.title = "Workcenters"

        for row in dataframe_to_rows(merged_data, index=False, header=True):
            ws1.append(row)

        # Ajustar largura das colunas da aba Workcenters
        for column_cells in ws1.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
            col_letter = column_cells[0].column_letter
            ws1.column_dimensions[col_letter].width = max(20, max_length + 2)

        # Aba 2: Resumo Geral
        ws2 = wb.create_sheet("Resumo Geral")
        for row in dataframe_to_rows(overall_df, index=False, header=True):
            ws2.append(row)

        # Ajustar largura das colunas da aba Resumo Geral
        for column_cells in ws2.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
            col_letter = column_cells[0].column_letter
            ws2.column_dimensions[col_letter].width = max(25, max_length + 2)

        # 4. Salvar em memória e enviar como download
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        return send_file(
            output,
            download_name="relatorio_kpi.xlsx",
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )