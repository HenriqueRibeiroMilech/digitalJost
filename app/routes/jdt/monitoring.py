"""
    JDT Monitoring
    Rotas e métodos para monitoramento industrial, incluindo visualização de paradas, OEE, hardware, erros e permissões.

    Métodos
    -------
    route_auth()
        Verifica autenticação e permissão do usuário antes de acessar as rotas do blueprint.
    monitoring_get()
        Exibe página principal do monitoramento.
    monitoring_stop_get(), monitoring_stop_post()
        Visualiza e filtra paradas dos centros de trabalho.
    monitoring_overall_get(), monitoring_overall_post()
        Painel geral de status, performance e disponibilidade.
    monitoring_hardware_get(), monitoring_hardware_post(), monitoring_hardware_register_post()
        Gerencia e registra hardwares industriais.
    monitoring_oee_get(), monitoring_oee_post()
        Visualiza OEE detalhado por centro de trabalho.
    monitoring_mach2_get(), monitoring_mach2_post()
        Visualiza e consulta erros de integração Plex.

    Notas
    -----
    - Todas as rotas exigem autenticação e permissões específicas.
    - Utiliza SQLAlchemy para acesso ao banco.
    - Funções auxiliares internas iniciam com '_'.
    - Dados retornados são preparados para visualização, cadastro e exportação.
"""

import re
import traceback
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import text
from app.utils.ping_utils import ping_lote,ping_info_cached,verificar_config_lote

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.utils.db_utils import engine_run_query, get_engine
from app.utils.permissions import get_permission
from app.utils.dynamic_constants import getPlex
from backend.modules.monitoring.current_status import CurrentStatusError, STATUS_COLUMNS, read_current_status
from backend.shared.database import get_td_session_factory

jdt_monitoring_bp = Blueprint('jdt_monitoring', __name__)


def _current_status_frame(sessions, **filters):
    return pd.DataFrame(read_current_status(
        sessions, mach2_engine=get_engine('plex'), ftm_engine=get_engine('ftm'), **filters,
    ), columns=STATUS_COLUMNS)


@jdt_monitoring_bp.errorhandler(CurrentStatusError)
def _current_status_error(error):
    return jsonify({'error': str(error)}), 503


@jdt_monitoring_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)


# MENU PRINCIPAL
@jdt_monitoring_bp.route('/monitoramento', methods=['GET'])
def monitoring_get():

    workcenters = getPlex('workcenters')

    workcenters = workcenters[workcenters['Active'] == 1][['Name', 'Workcenter_Code']]
    workcenters['Name'] = workcenters['Workcenter_Code'] + "-" + workcenters['Name']

    return render_template('jdt.monitoring/monitoring_main.html', workcenters=workcenters.sort_values(by='Workcenter_Code').to_dict(orient='records'))


# TELA DE VISUALIZAÇÃO DAS PARADAS
@jdt_monitoring_bp.route('/monitoramento/paradas', methods=['GET'])
def monitoring_stop_get():
    # ARGUMENTOS PARA PARADAS CARREGAR AUTOMATICO, APENAS BOTAR O NÚMERO
    # 0: Processos
    # 1: Qualidade
    # 2: Produção
    # 3: Logística
    # 4: Manutenção
    # 5: rSem Justificativa
    # 6: Transfomação Digital

    preload = {'load': []}
    if 'preload' in request.args:
        preload['load'] = [int(char) for char in request.args['preload']]
        
    return render_template('jdt.monitoring/monitoring_stop.html', preload=preload)

@jdt_monitoring_bp.route('/monitoramento/paradas', methods=['POST'])
def monitoring_stop_post():
    data = _current_status_frame(get_td_session_factory(), stops_only=True, exclude_s18=True)
    data['_started_at'] = pd.to_datetime(data['Log_Date'], format='%d/%m/%Y %H:%M:%S')
    data = data.sort_values(['Workcenter_Group', '_started_at'])[[
        'Workcenter_Code', 'Workcenter', 'Workcenter_Group', 'Log_Date',
        'Log_Duration', 'Event', 'Event_Code', 'Responsible',
    ]]

    return data[data['Responsible'].isin(request.get_json()['statusFilter'])].to_json(orient='records')


# PAINEL DE CONTROLE - VERDÃO NOVA
@jdt_monitoring_bp.route('/monitoramento/geral', methods=['GET'])
def monitoring_overall_get():
    return render_template('jdt.monitoring/monitoring_overall.html')

@jdt_monitoring_bp.route('/monitoramento/geral', methods=['POST'])
def monitoring_overall_post():
    query_oee = """
        WITH last_oee AS (
            SELECT
                Workcenter,
                OEE,
                ROW_NUMBER() OVER (
                    PARTITION BY Workcenter
                    ORDER BY RecordDate DESC
                ) rn
            FROM Mach_2_OEE_Real_Time
        )

        SELECT
            Workcenter AS OEE_Workcenter,
            OEE
        FROM last_oee
        WHERE rn = 1
    """

    sessions = get_td_session_factory()
    with ThreadPoolExecutor() as executor:
        status_future = executor.submit(_current_status_frame, sessions, exclude_s18=True)

        oee_future = executor.submit(
            engine_run_query,
            query_oee,
            'plex'
        )

    data = status_future.result()[[
        'Workcenter_Key', 'Workcenter_Code', 'Workcenter', 'Workcenter_Group',
        'Log_Date', 'Log_Duration', 'Event', 'Event_Code', 'Responsible', 'Goal',
    ]]
    oee_data = oee_future.result()

    data = pd.merge(
        data,
        oee_data,
        left_on='Workcenter_Code',
        right_on='OEE_Workcenter',
        how='left'
    )

    data.drop(
        columns=[
            'workcenter',
            'OEE_Workcenter'
        ],
        inplace=True,
        errors='ignore'
    )

    data['Goal'] = data['Goal'].fillna(0)
    data['OEE'] = data['OEE'].fillna(0)

    if len(request.get_json()['statusFilter']) > 0:
        data = data[data['Workcenter_Group'].isin(request.get_json()['statusFilter'])]

    return data.to_json(orient='records')


def _is_hardware_admin():
    return current_user.admin or get_permission('MAINTENANCE').can()


# TELA DE VISUALIZAÇÃO DE CONEXÃO COM HARDWARES INDUSTRIAIS
@jdt_monitoring_bp.route('/monitoramento/hardware', methods=['GET'])
def monitoring_hardware_get():

    # return render_template('general_maintenance.html')

    engine = get_engine('ftm')
    with engine.connect() as cnnx:
        query = f"""SELECT 
                            GRUPO AS Workcenter_Group
                            , LEFT(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) - 1) AS Workcenter_Code
                            , SUBSTRING(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) + 1, LEN(NOME_MAQUINA)) AS Name
                            , 1 AS Workcenter_Key
                        FROM CONFIG_TABLET WHERE CT_PLEX IS NULL"""
        mic_workcenters = pd.read_sql(query, cnnx)

    mes_workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]
    workcenters = pd.concat([mes_workcenters[~mes_workcenters['Workcenter_Code'].isin(mic_workcenters['Workcenter_Code'])], mic_workcenters])

    admin = 1 if _is_hardware_admin() else 0    

    return render_template('jdt.monitoring/monitoring_hardware.html', cts=workcenters, data={}, admin=admin)

# TELA DE VISUALIZAÇÃO DE CONEXÃO COM HARDWARES INDUSTRIAIS
@jdt_monitoring_bp.route('/monitoramento/hardware', methods=['POST'])
def monitoring_hardware_post():

    engine = get_engine('jdt')

    with engine.connect() as cnnx:
        query = """
            SELECT 
                rj AS nome,
                [type] AS tipo,
                workCenter AS descricao,
                ip,
                coord_x AS x,
                coord_y AS y
            FROM JDT_MONITORING_HARDWARE
        """

        data = pd.read_sql(query, cnnx)

    return jsonify(data.to_dict(orient='records'))

# REGISTRO DE HARDWARES INDUSTRIAIS
@jdt_monitoring_bp.route('/monitoramento/hardware/registro', methods=['POST'])
def monitoring_hardware_register_post():

    # return render_template('general_maintenance.html')

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        if "add" in request.args:

            if not _is_hardware_admin():
                abort(403)

            data = request.get_json()
            query = (f"INSERT INTO JDT_MONITORING_HARDWARE "
                        f"(rj, [type], workCenter, ip, coord_x, coord_y) VALUES ("
                        f"'{data['rj']}', '{data['tipo']}', "
                        f"'{data['ct']}', '{data['ip']}', "
                        f"'{data['coord_x']}', '{data['coord_y']}')")

            cnnx.execute(text(query))

        elif "layout" in request.args:

            data = request.get_json()
            for chave, valor in data.items():
                query = (f"UPDATE JDT_MONITORING_HARDWARE SET "
                            f"coord_x = '{valor[0]}', coord_y = '{valor[1]}' "
                            f"WHERE rj = '{chave}'")

                cnnx.execute(text(query))

        elif "delete" in request.args:

            if not _is_hardware_admin():
                abort(403)

            query = (f"DELETE FROM JDT_MONITORING_HARDWARE "
                        f"WHERE rj = '{request.args['delete']}'")

            cnnx.execute(text(query))

        elif "edit" in request.args:

            if not _is_hardware_admin():
                abort(403)

            data = request.get_json()
            rj_original = data.get('rj_original', data['rj'])

            query = (f"UPDATE JDT_MONITORING_HARDWARE SET "
                        f"rj = '{data['rj']}', "
                        f"[type] = '{data['tipo']}', "
                        f"workCenter = '{data['ct']}', "
                        f"ip = '{data['ip']}' "
                        f"WHERE rj = '{rj_original}'")

            cnnx.execute(text(query))

        cnnx.commit()

    return "CHANGES COMMITED"



# TELA DE VISUALIZAÇÃO DE QUADRO HORA HORA DE CADA CENTRO DE TRABALHO
@jdt_monitoring_bp.route('/monitoramento/quadro', methods=['GET'])
def monitoring_frame_get():
    return render_template('jdt.monitoring/monitoring_frame.html', workcenter=request.args['ct'], user=current_user.id)

@jdt_monitoring_bp.route('/monitoramento/quadro', methods=['POST'])
def monitoring_frame_post():
        
    workcenter_filter = request.args.get('ct', 'M01')

    # Validação: 1 a 4 caracteres, apenas letras maiúsculas e números
    if not re.fullmatch(r'[A-Z0-9]{1,4}', workcenter_filter):
        abort(400, description="Invalid workcenter code format. Must be 1-4 uppercase letters or numbers.")

    try:

        shift_query = f"""
                        SELECT TOP 1 record_time, shift_oee
                        FROM Mach_2_OEE T1
                        WHERE workcenter = :workcenter
                        AND shift_oee <> (
                            SELECT TOP 1 shift_oee
                            FROM Mach_2_OEE
                            WHERE workcenter = :workcenter
                            ORDER BY record_time DESC
                        )
                        ORDER BY record_time DESC;
                """

        sessions = get_td_session_factory()
        with ThreadPoolExecutor() as executor:
            shift_info_future = executor.submit(engine_run_query, shift_query, 'plex', params={'workcenter': workcenter_filter})
            status_query_future = executor.submit(_current_status_frame, sessions, workcenter=workcenter_filter)

        shift_info = shift_info_future.result()
        status_info = status_query_future.result()

        if status_info.empty:
            return jsonify({'error': 'Nenhum estado atual encontrado para o centro de trabalho.'}), 404

        if shift_info.empty:
            abort(404, description="No shift information found for the specified work center.")

        where_plex_params = {
            'start_date': shift_info['record_time'][0]
            , 'workcenter': workcenter_filter
        }

        plex_signal_query = f"""

            WITH target_rates_plex AS(
                SELECT *
                FROM OPENQUERY([PLEX_DSN_JOST], '
                    SELECT
                        T1.Part_No
                        , T3.Workcenter_Key
                        , T3.Workcenter_Code
                        , T3.Name
                        , CASE
                            WHEN T2.Ideal_Rate = 0.0 THEN 0.0
                            ELSE 60.0 / T2.Ideal_Rate
                        END AS Routing_Time
                    FROM
                        Part_v_Part T1
                        JOIN Part_v_Approved_Workcenter T2 ON T1.Part_Key = T2.Part_Key
                        JOIN Part_v_Workcenter T3 ON T2.Workcenter_Key = T3.Workcenter_Key

                    WHERE T1.Revision = ''SAP''
                ')

            ), target_rates_final AS (

                SELECT
                    T01.id_Mach_2_OEE_v2
                    , T03.Workcenter_Key
                    , T03.Workcenter_Code
                    , T03.Name
                    , AVG(T03.Routing_Time) AS Routing_Time
                FROM

                    Mach_2_OEE_Cavity_Info T01
                    JOIN Mach_2_OEE_v2 T02 ON T01.id_Mach_2_OEE_v2 = T02.id

                    JOIN target_rates_plex T03 ON
                        T01.part = T03.Part_No COLLATE SQL_Latin1_General_CP1_CI_AS
                        AND T02.workcenter = T03.Workcenter_Code COLLATE SQL_Latin1_General_CP1_CI_AS

                GROUP BY T01.id_Mach_2_OEE_v2, T03.Workcenter_Key, T03.Workcenter_Code, T03.Name   

            ), actual_rates AS (
                SELECT
                    T02.id_Mach_2_OEE_v2
                    , STRING_AGG(CASE WHEN T02.part = 'n/a' THEN NULL ELSE T02.part END, ', ') AS Part
                    , STRING_AGG(CASE WHEN T02.job = 'N/A' THEN NULL ELSE T02.job END, ', ') AS Job
                FROM Mach_2_OEE_Cavity_Info T02

                GROUP BY T02.id_Mach_2_OEE_v2
            )

            SELECT

                FORMAT(record_time, 'dd/MM/yyyy HH:mm:ss') AS Record_Time
                , Workcenter_Code
                , Name
                , Part
                , Job
                , CAST(T1.production_difference AS INT) AS Signal
                , Routing_Time
                , CAST(T1.time_difference AS FLOAT) / 60.0 AS Duration


            FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_OEE_v2] T1
                JOIN target_rates_final T2 ON T1.ID = T2.id_Mach_2_OEE_v2
                JOIN actual_rates T3 ON T1.id = T3.id_Mach_2_OEE_v2

            WHERE 
                T1.record_time > :start_date
                AND T2.Workcenter_Code = :workcenter

            ORDER BY record_time DESC

        """

        signal_data = engine_run_query(plex_signal_query, 'plex', where_plex_params)


        # CRIAR DATAFRAME DE PEÇAS POR HORA

        initial_time = pd.to_datetime(shift_info['record_time'][0]).floor('H')
        final_time = pd.Timestamp.now().floor('H')

        hours = pd.date_range(start=initial_time, end=final_time, freq='H')

        if not signal_data.empty:
            pieces_by_hour = (
                signal_data.groupby(pd.Grouper(key='Record_Time', freq='H')).sum().reset_index()
                .set_index('Record_Time')
                .reindex(hours, fill_value=0)
                .reset_index()
            )
        else:
            pieces_by_hour = pd.DataFrame({'index': hours, 'TotalParts': [0] * len(hours)})

        # Transformar datetime para string no formato '9h', '10h', etc., e ordenar
        pieces_by_hour['x'] = pieces_by_hour['index'].dt.hour.astype(str) + 'h'
        pieces_by_hour['y'] = pieces_by_hour['TotalParts'] if 'TotalParts' in pieces_by_hour else pieces_by_hour['y']

        # Garantir ordenação do mais velho para o mais novo
        pieces_by_hour = pieces_by_hour[['x', 'y']].reset_index(drop=True)

        data = {
            'workcenter': str(status_info['Workcenter'][0])
            , 'status': status_info['Status'][0]
            , 'reason': status_info['Event'][0]
            , 'statusTime': str(status_info['Log_Duration'][0])
            , 'pieces_by_hour': pieces_by_hour.to_dict(orient='records')
        }

    except CurrentStatusError as error:
        return _current_status_error(error)
    except Exception as e:
        traceback_info = traceback.format_exc()  # Captura o rastreamento completo da exceção
        print("Detalhes do erro:\n", traceback_info, flush=True)

        return jsonify({"error": f"{e}"}), 500
    
    else:

        return jsonify(data)
    
# TELA DE VISUALIZAÇÃO DE OEE DE CADA CENTRO DE TRABALHO
@jdt_monitoring_bp.route('/monitoramento/oee', methods=['GET'])
def monitoring_oee_get():
    return render_template('jdt.monitoring/monitoring_oee.html', workcenter=request.args['ct'], user=current_user.id)
    
@jdt_monitoring_bp.route('/monitoramento/oee', methods=['POST'])
def monitoring_oee_post():
        
    workcenter_filter = request.args.get('ct', 'M01')

    # Validação: 1 a 4 caracteres, apenas letras maiúsculas e números
    if not re.fullmatch(r'[A-Z0-9]{1,4}', workcenter_filter):
        abort(400, description="Invalid workcenter code format. Must be 1-4 uppercase letters or numbers.")                

    try:

        shift_query = f"""
                        SELECT TOP 1 record_time, shift_oee
                        FROM Mach_2_OEE T1
                        WHERE workcenter = :workcenter
                        AND shift_oee <> (
                            SELECT TOP 1 shift_oee
                            FROM Mach_2_OEE
                            WHERE workcenter = :workcenter
                            ORDER BY record_time DESC
                        )
                        ORDER BY record_time DESC;
                """

        actual_query = f"""
                SELECT TOP 4 
                    CASE WHEN T1.workcenter_shift = 'Primeiro' THEN '1' WHEN T1.workcenter_shift = 'Segundo' THEN '2' WHEN T1.workcenter_shift = 'Terceiro' THEN '3' ELSE 'Extra' END AS shift
                    , NULLIF(T2.job, 'N/A') AS job
                    , NULLIF(T2.part, 'n/a') AS part
                    , COALESCE(T3.Crew_Size, 0) AS Crew_Size

                FROM Mach_2_OEE_v2 T1 
                    JOIN Mach_2_OEE_Cavity_Info T2 ON T1.id = T2.id_Mach_2_OEE_v2
                    LEFT JOIN OPENQUERY([PLEX_DSN_JOST], '
                        SELECT
                            T3.Workcenter_Code
                            , T3.Name
                            , T2.Crew_Size
                            , T1.Part_No
                        FROM
                            Part_v_Part T1
                            JOIN Part_v_Approved_Workcenter T2 ON T1.Part_Key = T2.Part_Key
                            JOIN Part_v_Workcenter T3 ON T2.Workcenter_Key = T3.Workcenter_Key
                            JOIN Part_v_Part_Operation T4 ON T2.Part_Operation_Key = T4.Part_Operation_Key 

                        WHERE T1.Revision = ''SAP'' AND T4.Active = 1 AND T3.Workcenter_Code = ''{workcenter_filter}''
                    ') T3 ON 
                        T1.workcenter = T3.Workcenter_Code COLLATE SQL_Latin1_General_CP1_CI_AS AND
                        T2.part = T3.Part_No COLLATE SQL_Latin1_General_CP1_CI_AS

                WHERE T1.workcenter = :workcenter

                ORDER BY T1.record_time DESC
        """

        with ThreadPoolExecutor() as executor:
            shift_info_future = executor.submit(engine_run_query, shift_query, 'plex', params={'workcenter': workcenter_filter})
            actual_info_future = executor.submit(engine_run_query, actual_query, 'plex', params={'workcenter': workcenter_filter})

        shift_info = shift_info_future.result()
        actual_info = actual_info_future.result()

        if shift_info.empty:
            abort(404, description="No shift information found for the specified work center.")

        # BUILD DAS VARIAVEIS GERAIS

        parts = actual_info['part'].dropna().unique()

        # BUILD DAS QUERIES QUE RODAM EM TEMPO SIMULTANEO

        program_5s_medal_query = f"""
                    SELECT COALESCE(
                        (
                            SELECT CASE 
                                WHEN T1.grade < 65 THEN 4
                                WHEN T1.grade < 80 THEN 3
                                WHEN T1.grade < 91 THEN 2
                                ELSE 1
                            END
                            FROM JDT_REGISTER_5S_GRADE T1
                            JOIN JDT_REGISTER_5S_PLACE T2 ON T1.placeId = T2.id
                            WHERE T2.place = :workcenter AND (SELECT MAX(T3.auditId) FROM JDT_REGISTER_5S_GRADE T3 WHERE T3.placeId = T1.placeId) = T1.auditId
                        ), 4
                    ) AS grade
                """
        
        signal_query = f"""

                    SELECT
                        T1.record_time
                        , CAST(T1.production_difference AS INT) AS TotalParts

                    FROM Mach_2_OEE_v2 T1
                        
                    WHERE
                        T1.record_time > :record_time AND T1.workcenter = :workcenter

                    ORDER BY T1.record_time

        """

        status_logs_query = f"""
            DECLARE @record_time DATETIME = :record_time;
            DECLARE @workcenter_filter VARCHAR(10) = :workcenter;

            -- Traga todos os eventos do Plex para uma CTE
            WITH plex_events AS (
                SELECT 
                    Workcenter_Event_Key,
                    Description COLLATE SQL_Latin1_General_CP1_CI_AS AS Description,
                    Workcenter_Event_Group,
                    Active,
                    Code COLLATE SQL_Latin1_General_CP1_CI_AS AS Code
                FROM OPENQUERY([PLEX_DSN_JOST], '
                    SELECT 
                        Workcenter_Event_Key
                        , Description
                        , Workcenter_Event_Group
                        , Active
                        , Code 
                    FROM Part_v_Workcenter_Event
                ')
            ),
            last_log AS (
                SELECT
                    wc_reason,
                    wc_status_reason_time,
                    record_time,
                    ROW_NUMBER() OVER (PARTITION BY workcenter ORDER BY record_time DESC) AS rn
                FROM Mach_2_Status_Reason_Time
                WHERE record_time < @record_time AND workcenter = @workcenter_filter
            ),
            invade_time AS (
                SELECT
                    COALESCE(plex.Workcenter_Event_Group, 'Produção') AS Status,
                    CONCAT(plex.Code, '-', log.wc_reason) AS Event,
                    CASE
                        WHEN DATEADD(SECOND, log.wc_status_reason_time, log.record_time) > @record_time
                        THEN DATEDIFF(SECOND, @record_time, DATEADD(SECOND, log.wc_status_reason_time, log.record_time))
                        ELSE 0
                    END AS Log_Duration
                FROM last_log log
                LEFT JOIN plex_events plex ON log.wc_reason = plex.Description
                WHERE log.rn = 1
            ),
            main_events AS (
                SELECT
                    COALESCE(plex.Workcenter_Event_Group, 'Produção') AS Status,
                    CONCAT(plex.Code, '-', t1.wc_reason) AS Event,
                    t1.wc_status_reason_time AS Log_Duration
                FROM Mach_2_Status_Reason_Time t1
                LEFT JOIN plex_events plex ON t1.wc_reason = plex.Description
                WHERE t1.record_time > @record_time AND t1.workcenter = @workcenter_filter
            )

            SELECT TOP 5   
                Event AS reason
                , CAST(SUM(Log_Duration) / 60.0 AS INT) AS [time]
            FROM (
                SELECT * FROM main_events
                UNION ALL
                SELECT * FROM invade_time
            ) all_events
            WHERE Status NOT IN ('Produção', 'Programada')
            GROUP BY Event
            ORDER BY [time] DESC
        """

        logged_operators_query = f"""SELECT operators FROM Mach_2_Logged_Operators WHERE wc = :workcenter"""

        # para cada part, é criado uma condição de LIKE para o prodCode
        deviation_condition = ' OR '.join([f"prodCode LIKE '%{v}%'" for v in parts]) or '1 = 0'
        deviation_query = f"""
                    SELECT 
                        deviationId
                        , status
                    FROM 
                        JDT_REQUEST_DEV 
                    WHERE 
                        status IN (5, 6) AND
                        workcenter LIKE :workcenter AND (({deviation_condition}) OR prodCode = '["Todos"]')
                    """

        sessions = get_td_session_factory()
        with ThreadPoolExecutor() as executor:
            program_5s_medal_data = executor.submit(engine_run_query, program_5s_medal_query, 'jdt', params={'workcenter': workcenter_filter})
            status_data = executor.submit(_current_status_frame, sessions, workcenter=workcenter_filter)
            deviation_data = executor.submit(engine_run_query, deviation_query, 'jdt', params={'workcenter': f"%{workcenter_filter}%"})

            signal_data = executor.submit(engine_run_query, signal_query, 'plex', params={'record_time': shift_info['record_time'][0], 'workcenter': workcenter_filter})
            top_stops_data = executor.submit(engine_run_query, status_logs_query, 'plex', params={'record_time': shift_info['record_time'][0], 'workcenter': workcenter_filter})
            logged_operators_data = executor.submit(engine_run_query, logged_operators_query, 'plex', params={'workcenter': workcenter_filter})

        program_5s_medal_data = program_5s_medal_data.result()
        status_data = status_data.result()
        if status_data.empty:
            return jsonify({'error': 'Nenhum estado atual encontrado para o centro de trabalho.'}), 404
        signal_data = signal_data.result()
        top_stops_data = top_stops_data.result()
        deviation_data = deviation_data.result()
        logged_operators_data = logged_operators_data.result()

        # CONFIGURAR DATAFRAMES

        signal_data['record_time'] = pd.to_datetime(signal_data['record_time'])


        # CRIAR DATAFRAME DE PEÇAS POR HORA

        initial_time = pd.to_datetime(shift_info['record_time'][0]).floor('H')
        final_time = pd.Timestamp.now().floor('H')

        hours = pd.date_range(start=initial_time, end=final_time, freq='H')

        if not signal_data.empty:
            pieces_by_hour = (
                signal_data.groupby(pd.Grouper(key='record_time', freq='H')).sum().reset_index()
                .set_index('record_time')
                .reindex(hours, fill_value=0)
                .reset_index()
            )
        else:
            pieces_by_hour = pd.DataFrame({'index': hours, 'TotalParts': [0] * len(hours)})

        # Transformar datetime para string no formato '9h', '10h', etc., e ordenar
        pieces_by_hour['x'] = pieces_by_hour['index'].dt.hour.astype(str) + 'h'
        pieces_by_hour['y'] = pieces_by_hour['TotalParts'] if 'TotalParts' in pieces_by_hour else pieces_by_hour['y']

        # Garantir ordenação do mais velho para o mais novo
        pieces_by_hour = pieces_by_hour[['x', 'y']].reset_index(drop=True)


        # CRIAR DATAFRAME COM PROBLEMAS DE QUALIDADE
        # falta a lógica de seleção dos dados e filtro top 5

        quality_problems = pd.DataFrame(columns=['x', 'y'])


        # PEGAR A QUANTIDADE DE OPERADORES LOGADOS NO CENTRO DE TRABALHO

        crew_size = len(logged_operators_data['operators'][0].split("|")) - 1
        
        data = {
            'workcenter': str(status_data['Workcenter'][0])
            , 'status': status_data['Status'][0]
            , 'reason': status_data['Event'][0]
            , 'statusTime': str(status_data['Log_Duration'][0])
            , 'performance': str(status_data['Performance'][0])
            , 'availability': str(status_data['Availability'][0])
            , 'quality': str(status_data['Quality'][0])
            , 'oee': str(status_data['OEE'][0])
            , 'piecesProducedPerHour': pieces_by_hour.to_dict(orient='records')
            , 'topStops': top_stops_data.to_dict(orient='records')
            , 'topQualityProblems': quality_problems.to_dict(orient='records')
            , 'currentOperators': str(crew_size)
            , 'expectedOperators': str(int(actual_info['Crew_Size'].max()))
            , 'totalParts': str(int(status_data['TotalParts'][0]))
            , 'expectedParts': str(int(round(status_data['ExpectedParts'][0])))
            , 'producingAvailability': str(status_data['TotalRun'][0])
            , 'stoppedAvailability': str(status_data['TotalStopped'][0])
            , 'approvedQuality': str(int(status_data['GoodParts'][0]))
            , 'shiftOee': str(actual_info['shift'][0])
            , 'part': parts.tolist()
            , 'deviation': deviation_data.to_dict(orient='records')
            , 'oeeGoal': str(status_data['Goal'][0])
            , 'medal': str(program_5s_medal_data['grade'][0])
        }

    
    except CurrentStatusError as error:
        return _current_status_error(error)
    except Exception as e:
        traceback_info = traceback.format_exc()  # Captura o rastreamento completo da exceção
        print("Detalhes do erro:\n", traceback_info, flush=True)

        return jsonify({"error": f"{e}"}), 500
    
    else:

        return jsonify(data)

# MONITORAMENTO DOS ERROS - TRANSAÇÕES PLEX
@jdt_monitoring_bp.route('/monitoramento/erros', methods=['GET'])
def monitoring_mach2_get():
    return render_template('jdt.monitoring/monitoring_error.html')

@jdt_monitoring_bp.route('/monitoramento/erros', methods=['POST'])
def monitoring_mach2_post():

    query_errors = f"""EXEC SP_STATUS_REPORT"""
    query_shift = f"""
                WITH RankedShifts AS (
                SELECT 
                    [shift_oee],
                    [record_time],
                    ROW_NUMBER() OVER (PARTITION BY [shift_oee] ORDER BY [record_time] ASC) AS RowAsc,
                    ROW_NUMBER() OVER (PARTITION BY [shift_oee] ORDER BY [record_time] DESC) AS RowDesc
                FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_OEE]
                WHERE workcenter = 'M07'
                AND record_time > DATEADD(DAY, -2, GETDATE())

                )
                SELECT 
                [shift_oee],
                MIN(CASE WHEN RowAsc = 1 THEN [record_time] END) AS record_time_init,
                MAX(CASE WHEN RowDesc = 1 THEN [record_time] END) AS record_time_end
                FROM RankedShifts
                GROUP BY [shift_oee]
                ORDER BY record_time_init DESC
                """

    engine = get_engine('plex')
    with engine.connect() as cnnx:
        data = pd.read_sql(query_errors, cnnx)
        data_shift = pd.read_sql(query_shift, cnnx)

    def shift_verify(ddate, df_turnos):
        
        if ddate > df_turnos['record_time_end'][0]:
            return 'actual'
        elif ddate > df_turnos['record_time_end'][1]:
            return 'past'
        else:
            return 'others'

    data['shift'] = data['DDate'].apply(lambda x: shift_verify(x, data_shift))
    data['DDatePTBR'] = data['DDate'].dt.strftime('%d/%m/%Y %H:%M:%S')

    return data.to_json(orient='records')


@jdt_monitoring_bp.route('/monitoramento/IA', methods=['GET'])
def monitoring_IA_GET():

     return render_template('general_development.html')




''''ROTAS DE PING E VERIFICAÇÃO DE CONFIGURAÇÃO - HARDWARES INDUSTRIAIS'''



@jdt_monitoring_bp.route('/monitoramento/ping-lote', methods=['POST'])
def monitoring_ping_lote():

    data = request.get_json()
    ips = data.get("ips", [])

    result = ping_lote(ips)

    return jsonify(result)


@jdt_monitoring_bp.route('/monitoramento/verificar-config', methods=['POST'])
def monitoring_verificar_config():

    print("ROTA /monitoramento/verificar-config FOI CHAMADA", flush=True)

    data = request.get_json()
    hardwares = data.get("hardwares", [])

    result = verificar_config_lote(hardwares)

    return jsonify(result)


@jdt_monitoring_bp.route('/monitoramento/ping/<ip>', methods=['GET'])
def monitoring_ping(ip):

    data = ping_info_cached(ip)

    return jsonify(data)

# V2

