
"""
    OperationProd
    Classe responsável por fornecer rotas e métodos para obtenção e manipulação de dados de produção (OEE, paradas, indicadores) para o sistema de acompanhamento operacional.
    
    Métodos
    -------
    getProdData(group_by_workcenter, payload)
        Executa consultas SQL em paralelo para coletar dados de produção e paradas, tanto do sistema MIC quanto do PLEX, processando e consolidando os resultados em DataFrames pandas. Permite agrupamento por centro de trabalho e diferentes granularidades de tempo. Retorna dados de OEE, paradas principais e paradas agrupadas por período.
    
    routes_operation_prod()
        Registra as rotas Flask relacionadas à produção operacional:
        - /op/producao [GET]: Exibe a página principal de produção, com seleção de mês e ano.
        - /op/producao [POST]: Retorna dados agregados de produção (OEE, disponibilidade, qualidade, performance) por grupo de centro de trabalho e período, para o mês/ano selecionado.
        - /op/producao/indicadores [GET]: Exibe a página de indicadores de produção, com possibilidade de pré-carregar filtros e lista de centros de trabalho.
        - /op/producao/indicadores [POST]: Retorna dados detalhados de OEE e paradas, conforme filtros enviados no payload (datas, turnos, centros de trabalho, etc).
        - /op/producao/indicadores/excel [POST]: Gera e retorna um arquivo Excel com os indicadores de produção, tanto gerais quanto por centro de trabalho, conforme filtros enviados.
    
    Notas
    -----
    - As rotas requerem autenticação e autorização.
    - Os métodos utilizam execução paralela para otimizar consultas em múltiplos bancos de dados.
    - Os dados retornados são preparados para visualização em dashboards e exportação.
"""

import json
import os
from datetime import datetime, timedelta
import pandas as pd

from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app.utils.db_utils import engine_run_query, timed_query
from app.utils.dynamic_constants import getPlex
from app.utils.permissions import get_permission
from app.routes.operation.shift_handoffs_repository import get_shift_handoffs


# Início do Turno 3 da data de referência domingo. Após confirmação,
# use (0, 'HH:MM') para domingo ou (1, 'HH:MM') para segunda-feira.
SUNDAY_THIRD_SHIFT_START = (1, '00:00')


operation_production_bp = Blueprint('operation_production', __name__)

@operation_production_bp.before_request
def route_auth():

    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)


@operation_production_bp.route('/op/producao/apontamentos-por-turno', methods=['GET'])
def shift_handoffs():
    selected_date = request.args.get('data') or (datetime.now().date() - timedelta(days=1)).isoformat()

    try:
        parsed_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        if parsed_date.isoformat() != selected_date:
            raise ValueError('Data inválida')
    except ValueError:
        abort(400, 'Informe uma data válida no formato AAAA-MM-DD.')

    shifts = {'Turno 1': [], 'Turno 2': [], 'Turno 3': []}
    for row in get_shift_handoffs(parsed_date):
        shift = row['turno_que_deixou']
        if shift in shifts:
            shifts[shift].append(row)

    for rows in shifts.values():
        rows.sort(key=lambda row: row['workcenter'])

    day = parsed_date.strftime('%d/%m/%Y')
    next_day = (parsed_date + timedelta(days=1)).strftime('%d/%m/%Y')
    shift_periods = {
        'Turno 1': f'{day} 07:12 – {day} 17:00',
        'Turno 2': f'{day} 17:00 – {next_day} 02:12',
        'Turno 3': f'{next_day} 02:12 – {next_day} 07:12',
    }

    if parsed_date.weekday() == 6:  # Domingo
        if SUNDAY_THIRD_SHIFT_START is None:
            shift_periods['Turno 3'] = f'Início a confirmar – {next_day} 07:12'
        else:
            day_offset, start_time = SUNDAY_THIRD_SHIFT_START
            start_day = (parsed_date + timedelta(days=day_offset)).strftime('%d/%m/%Y')
            shift_periods['Turno 3'] = f'{start_day} {start_time} – {next_day} 07:12'

    return render_template(
        'operation.prod/shift_handoffs.html',
        selected_date=selected_date,
        shifts=shifts,
        shift_periods=shift_periods,
    )
    

def _GET_PROD_DATA(group_by_workcenter, payload):

    # Função para mapear a chave de agrupamento temporal para a expressão SQL correspondente
    def get_time_group_expression(group_key, column_name):
        time_group_map = {
            '0': f"FORMAT({column_name}, 'dd/MM')"
            , '1': f"CONCAT(YEAR({column_name}), '/', RIGHT('0' + CAST(DATEPART(WEEK, DATEADD(HOUR, 1, {column_name})) AS VARCHAR), 2))"
            , '2': f"CONCAT(YEAR({column_name}), '/', RIGHT('0' + CAST(MONTH({column_name}) AS VARCHAR), 2))"
            , '3': f"CAST(YEAR({column_name}) AS VARCHAR)"
            , '4': f"FORMAT({column_name}, 'dd/MM/yyyy HH')"
            , '5': "NULL"
        }
        return time_group_map.get(group_key, time_group_map['3'])

    # ---------------
    # MIC - CONSULTAS E CLAUSULAS
    # ---------------

    mic_group_specific = {
        True : f"""
                , T1.sDescription
                , T2.GRUPO
                , CASE 
                    WHEN nShift = 1 THEN 'Primeiro'
                    WHEN nShift = 2 THEN 'Segundo'
                    WHEN nShift = 3 THEN 'Terceiro'
                    ELSE 'Hora Extra'
                END
            """
        , False : ""
    }
    mic_group_specific_col = {
        True : f"""
                , T1.sDescription AS Workcenter_Name
                , T2.GRUPO AS Workcenter_Group
                , CASE 
                    WHEN nShift = 1 THEN 'Primeiro'
                    WHEN nShift = 2 THEN 'Segundo'
                    WHEN nShift = 3 THEN 'Terceiro'
                    ELSE 'Hora Extra'
                END AS Shift_Group
            """
        , False : ""
    }

    group_by_1 = get_time_group_expression(payload.get('time_group'), 'tStartTime')
    group_by_2 = get_time_group_expression(payload.get('time_group'), 'tStart')

    where_mic_w_count = ', '.join([f':w_mic_val{i}' for i in range(len(payload['w_mic_values']))]) if payload['w_mic_values'] else ':w_mic_val0'
    if payload['w_mic_values']:
        where_mic_w_values = {f'w_mic_val{i}': v for i, v in enumerate(payload['w_mic_values'])}
    else:
        where_mic_w_values = {'w_mic_val0': 'aaa'}

    where_plex_w_count = ', '.join([f':w_plex_val{i}' for i in range(len(payload['w_plex_values']))]) if payload['w_plex_values'] else ':w_plex_val0'
    if payload['w_plex_values']:
        where_plex_w_values = {f'w_plex_val{i}': v for i, v in enumerate(payload['w_plex_values'])}
    else:
        where_plex_w_values = {'w_plex_val0': 1}

    where_mic_shift = payload['shift'][:]
    if "Extra" in where_mic_shift:
        where_mic_shift.remove("Extra")
        where_mic_shift += ['12', '13', '-1']

    where_mic_shift_count = ', '.join([f':w_mic_shift{i}' for i in range(len(where_mic_shift))]) if where_mic_shift else ':w_mic_shift0'
    if where_mic_shift:
        where_mic_shift_values = {f'w_mic_shift{i}': int(v) for i, v in enumerate(where_mic_shift)}
    else:
        where_mic_shift_values = {'w_mic_shift0': -2}
    
    # Unifica todos os parâmetros em um único dict para named binding
    where_mic_params = {
        'start_date': payload['start_date']
        , 'end_date': payload['end_date']
        , **where_mic_w_values
        , **where_plex_w_values
        , **where_mic_shift_values
    }


    # ---------------
    # PLEX - CONSULTAS E CLAUSULAS
    # ---------------

    mic_oee_query = f"""

                    SELECT  

                        {group_by_1} AS Time_Group
                        {mic_group_specific_col[group_by_workcenter]}

                        , SUM(T1.dRunSec) / 3600.0 AS TotalRun
                        , SUM(T1.dAvailSec) / 3600.0 AS TotalAvail

                        , SUM(T1.dGoodParts) AS TotalGoodParts
                        , SUM(T1.dTotalParts) AS TotalParts
                        , SUM(CASE WHEN T1.dIdealCycleTime > 1 THEN T1.dRunSec / NULLIF(T1.dIdealCycleTime, 0) ELSE 0 END) AS Expected_Pieces

                        , 100 AS PerformanceGoal
                        , AVG(T3.VL_META) AS Goal

                    FROM FTMETRICS_JOST.dbo.OEEQWorkCellDetail T1
                        JOIN FTMETRICS_JOST.dbo.CONFIG_TABLET T2 ON T1.sDescription = T2.NOME_MAQUINA
                        JOIN FTMETRICS_JOST.dbo.CADASTRO_META T3 ON T1.sDescription = T3.COD_MAQUINA

                    WHERE 

                        T1.tStartTime BETWEEN 
                            :start_date
                            AND CASE 
                                WHEN T2.CT_PLEX_DATA < :end_date
                                THEN T2.CT_PLEX_DATA 
                                ELSE :end_date
                            END

                        AND (T1.sDescription IN ({where_mic_w_count}) OR T2.CT_PLEX IN ({where_plex_w_count}))

                        AND T1.nShift IN ({where_mic_shift_count})
                        
                    GROUP BY {group_by_1} {mic_group_specific[group_by_workcenter]}
                    ORDER BY MIN(T1.tStartTime)
                """

    mic_stop_query = f"""
                    SELECT

                        SUM(lSeconds) / 60.0 AS Log_Minutes_Sum
                        , COUNT(sEndval) AS Log_Minutes_Count
                        , CAST(COD_PARADA AS VARCHAR) AS Code 
                    
                    FROM FTMETRICS_JOST.dbo.OEEQEventHistory T1
                    JOIN FTMETRICS_JOST.dbo.CONFIG_TABLET T2 ON T1.sDescription = T2.NOME_MAQUINA
                    JOIN FTMETRICS_JOST.dbo.CADASTRO_PARADA T3 ON TRIM(T1.sEndVal) = T3.MOTIVO

                    WHERE 

                        T1.tStart BETWEEN 
                            :start_date
                            AND CASE 
                                WHEN T2.CT_PLEX_DATA < :end_date
                                THEN T2.CT_PLEX_DATA 
                                ELSE :end_date
                            END

                        AND (T1.sDescription IN ({where_mic_w_count}) OR T2.CT_PLEX IN ({where_plex_w_count}))
                        AND T1.nShift IN ({where_mic_shift_count})                 
                        AND sEventDesc = 'Parada' AND T3.FL_PROGRAMADA != 1

                    GROUP BY CAST(COD_PARADA AS VARCHAR) ORDER BY Log_Minutes_Sum DESC"""

    mic_stop_aux_query = f"""
                    SELECT

                        {group_by_2} AS Time_Group
                        , SUM(lSeconds) / 60.0 AS Log_Minutes_Sum
                        , COUNT(sEndval) AS Log_Minutes_Count
                        , CAST(COD_PARADA AS VARCHAR) AS Code 
                    
                    FROM FTMETRICS_JOST.dbo.OEEQEventHistory T1
                    JOIN FTMETRICS_JOST.dbo.CONFIG_TABLET T2 ON T1.sDescription = T2.NOME_MAQUINA
                    JOIN FTMETRICS_JOST.dbo.CADASTRO_PARADA T3 ON TRIM(T1.sEndVal) = T3.MOTIVO

                    WHERE 

                        T1.tStart BETWEEN 
                            :start_date
                            AND CASE 
                                WHEN T2.CT_PLEX_DATA < :end_date
                                THEN T2.CT_PLEX_DATA 
                                ELSE :end_date
                            END

                        AND (T1.sDescription IN ({where_mic_w_count}) OR T2.CT_PLEX IN ({where_plex_w_count}))
                        AND T1.nShift IN ({where_mic_shift_count})                      
                        AND sEventDesc = 'Parada' AND T3.FL_PROGRAMADA != 1

                    GROUP BY {group_by_2}, CAST(COD_PARADA AS VARCHAR) ORDER BY Log_Minutes_Sum DESC
                    """


    plex_group_specific = {
        True : f"""
                , CONCAT(T2.Workcenter_Code, '-', T2.Name) 
                , T2.Workcenter_Group
                , T1.workcenter_shift
            """
        , False : ""
    }
    plex_group_specific_col = {
        True : f"""
                , CONCAT(T2.Workcenter_Code, '-', T2.Name) AS Workcenter_Name 
                , T2.Workcenter_Group
                , T1.workcenter_shift AS Shift_Group
            """
        , False : ""
    }
    
    group_by = get_time_group_expression(payload.get('time_group'), 'record_time')

    where_plex_shift = {'1': 'primeiro', '2': 'segundo', '3': 'terceiro'}
    where_plex_shift_values = [where_plex_shift.get(s, s) for s in payload['shift']] if payload['shift'] else ['a']
    where_plex_shift_count = ', '.join([f':w_plex_shift{i}' for i in range(len(where_plex_shift_values))]) if where_plex_shift_values else ':w_plex_shift0'
    where_plex_shift_values = {f'w_plex_shift{i}': v for i, v in enumerate(where_plex_shift_values)}


    where_plex_w_proc = json.dumps(where_plex_w_values, ensure_ascii=False)
    where_plex_shift_proc = json.dumps(where_plex_shift_values, ensure_ascii=False)

    # Unifica todos os parâmetros em um único dict para named binding (igual ao MIC)
    where_plex_params = {
        'start_date': payload['start_date'],
        'end_date': payload['end_date'],
        **where_plex_w_values,
        **where_plex_shift_values
    }
    # Unifica todos os parâmetros em um único dict para named binding (igual ao MIC)
    where_plex_params_proc = {
        'start_date': payload['start_date'],
        'end_date': payload['end_date'],
        'w_plex_w_proc': where_plex_w_proc,
        'w_plex_shift_proc': where_plex_shift_proc
    }

    plex_oee_query = f"""

        WITH target_rates_plex AS(
            SELECT *
            FROM OPENQUERY([PLEX_DSN_JOST], '
                SELECT
                    T1.Part_No
                    , T3.Workcenter_Key
                    , T3.Workcenter_Code
                    , T3.Name
                    , T3.Workcenter_Group
                    , T2.Ideal_Rate
                FROM
                    Part_v_Part T1
                    JOIN Part_v_Approved_Workcenter T2 ON T1.Part_Key = T2.Part_Key
                    JOIN Part_v_Workcenter T3 ON T2.Workcenter_Key = T3.Workcenter_Key
                    JOIN Part_v_Part_Operation T4 ON T2.Part_Operation_Key = T4.Part_Operation_Key 

                WHERE T1.Revision = ''SAP'' AND T4.Active = 1
            ')

        ), target_rates_final AS (

            SELECT
                T01.id_Mach_2_OEE_v2
                , T03.Workcenter_Key
                , T03.Workcenter_Code
                , T03.Name
                , T03.Workcenter_Group
                , AVG(T03.Ideal_Rate) AS Ideal_Rate
            FROM

                Mach_2_OEE_Cavity_Info T01
                JOIN Mach_2_OEE_v2 T02 ON T01.id_Mach_2_OEE_v2 = T02.id

                JOIN target_rates_plex T03 ON
                    T01.part = T03.Part_No COLLATE SQL_Latin1_General_CP1_CI_AS
                    AND T02.workcenter = T03.Workcenter_Code COLLATE SQL_Latin1_General_CP1_CI_AS

            GROUP BY T01.id_Mach_2_OEE_v2, T03.Workcenter_Key, T03.Workcenter_Code, T03.Name, T03.Workcenter_Group

        )

        SELECT
            {group_by} AS Time_Group
            {plex_group_specific_col[group_by_workcenter]}

            , SUM(CAST(T1.production_difference AS INT)) AS TotalParts
            , SUM(CAST(T1.time_difference AS FLOAT) / 3600.0 * CAST(T2.Ideal_Rate AS FLOAT)) AS Expected_Pieces


        FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_OEE_v2] T1
            LEFT JOIN target_rates_final T2 ON T1.ID = T2.id_Mach_2_OEE_v2
            
        WHERE
            T1.record_time BETWEEN :start_date AND :end_date
            AND T2.Workcenter_Key IN ({where_plex_w_count})
            AND T1.workcenter_shift IN ({where_plex_shift_count})

        GROUP BY {group_by} {plex_group_specific[group_by_workcenter]}

        ORDER BY MIN(T1.record_time)"""

    plex_oee_goal_query = f"""SELECT COALESCE(AVG(goal1), 85) AS Goal FROM PLEX_REGISTER_GOAL WHERE workcenter IN ({where_plex_w_count})"""

    plex_availability_query = f"""
        EXEC ('sproc329396_18311230_1264675(?, ?, ?, ?, ?, ?, ?, ?, ?)', :start_date, :end_date, :w_plex_w_proc, '[]', :w_plex_shift_proc, :time_group, :group_by_workcenter1, :group_by_workcenter2, :group_by_workcenter3) AT [PLEX_DSN_JOST]
    """

    plex_stop_query = f"""
        EXEC ('sproc329396_18311230_1245610(?, ?, ?, ?, ?)', :start_date, :end_date, :w_plex_w_proc, :w_plex_shift_proc, :time_group) AT [PLEX_DSN_JOST]
    """

    plex_stop_aux_query = f"""
        EXEC ('sproc329396_18311230_1245623(?, ?, ?, ?, ?)', :start_date, :end_date, :w_plex_w_proc, :w_plex_shift_proc, :time_group) AT [PLEX_DSN_JOST]
    """


    # ---------------
    # EXECUÇÃO PARALELA
    # ---------------

    with ThreadPoolExecutor() as executor:
        
        mic_oee_data = executor.submit(engine_run_query, mic_oee_query, 'jdt', where_mic_params)

        mic_stop = executor.submit(engine_run_query, mic_stop_query, 'jdt', where_mic_params)
        mic_stop_aux = executor.submit(engine_run_query, mic_stop_aux_query, 'jdt', where_mic_params)

        plex_oee_data = executor.submit(engine_run_query, plex_oee_query, 'plex', where_plex_params)
        plex_oee_goal = executor.submit(engine_run_query, plex_oee_goal_query, 'jdt', where_plex_w_values)


        # Adiciona os extras ao dict para cada chamada
        plex_availability_params = dict(where_plex_params_proc)
        plex_availability_params.update({
            'time_group': payload.get('time_group'),
            'group_by_workcenter1': int(group_by_workcenter),
            'group_by_workcenter2': int(group_by_workcenter),
            'group_by_workcenter3': int(group_by_workcenter)
        })
        plex_availability_data = executor.submit(timed_query, 'plex_availability_query', engine_run_query, plex_availability_query, 'jdt', plex_availability_params)

        plex_stop_params = dict(where_plex_params_proc)
        plex_stop_params.update({'time_group': payload.get('time_group')})
        plex_stop = executor.submit(timed_query, 'plex_stop_query', engine_run_query, plex_stop_query, 'jdt', plex_stop_params)

        plex_stop_aux_params = dict(where_plex_params_proc)
        plex_stop_aux_params.update({'time_group': 0 if payload.get('time_group') == 4 else payload.get('time_group')})
        plex_stop_aux = executor.submit(timed_query, 'plex_stop_aux_query', engine_run_query, plex_stop_aux_query, 'jdt', plex_stop_aux_params)

    mic_oee_data = mic_oee_data.result()

    plex_oee_data = plex_oee_data.result()
    plex_oee_goal_data = plex_oee_goal.result()
    plex_availability_data = plex_availability_data.result()

    mic_stop = mic_stop.result()
    plex_stop = plex_stop.result()

    mic_stop_aux = mic_stop_aux.result()
    plex_stop_aux = plex_stop_aux.result()

    plex_availability_data['Goal'] = plex_oee_goal_data['Goal'][0]
    plex_oee_data['TotalGoodParts'] = plex_oee_data['TotalParts']
    

    # ---------------
    # JUNÇÃO DADOS MIC X PLEX - PROCESSAMENTO DOS DADOS
    # ---------------

    if not group_by_workcenter:
        plex_oee_data = pd.merge(left=plex_oee_data, right=plex_availability_data, on=['Time_Group'], how='right')
    else:
        plex_oee_data = pd.merge(left=plex_oee_data, right=plex_availability_data, on=['Time_Group', 'Workcenter_Name', 'Workcenter_Group', 'Shift_Group'], how='right')
    
    data_oee = pd.concat([mic_oee_data, plex_oee_data])

    if not group_by_workcenter:
        data_oee = data_oee.groupby(by=['Time_Group']).agg(
            TotalRun=('TotalRun', 'sum'),
            TotalAvail=('TotalAvail', 'sum'),
            TotalGoodParts=('TotalGoodParts', 'sum'),
            TotalParts=('TotalParts', 'sum'),
            Expected_Pieces=('Expected_Pieces', 'sum'),
            Goal=('Goal', 'mean'),
        ).reset_index()


    # ---------------
    # CALCULOS DAS INFORMAÇÕES DE OEE, PERFORMANCE, DISPONIBILIDADE E QUALIDADE
    # ---------------

    data_oee['PerformanceGoal'] = 100

    data_oee['Performance'] = data_oee.apply(
        lambda row: (row['TotalParts'] / row['Expected_Pieces']) * 100 if row['Expected_Pieces'] != 0 else 0,
        axis=1
    )
    data_oee['Availability'] = data_oee.apply(
        lambda row: (row['TotalRun'] / row['TotalAvail']) * 100 if row['TotalAvail'] != 0 else 0,
        axis=1
    )
    data_oee['Quality'] = data_oee.apply(
        lambda row: (row['TotalGoodParts'] / row['TotalParts']) * 100 if row['TotalParts'] != 0 else 0,
        axis=1
    )
    data_oee['OEE'] = (data_oee['Performance'] * data_oee['Availability'] * data_oee['Quality']) / 10000

    data_oee['Expected_Pieces2'] = data_oee.apply(
        lambda row: row['Goal'] * row['Expected_Pieces'] / row['Availability'] if row['Availability'] != 0.0 else 0,
        axis=1
    )

    data_oee['TotalPartsSum'] = data_oee['TotalParts'].sum()

    data_stop = pd.concat([mic_stop, plex_stop])
    data_stop = pd.merge(left=data_stop, right=getPlex('events')[['Code', 'Description']], on=['Code'])
    data_stop['Event'] = data_stop['Code'] + '-' + data_stop['Description']

    data_stop['Log_Minutes_Sum'] = data_stop['Log_Minutes_Sum'].astype(float)


    data_stop = data_stop.groupby(by=["Event"]).agg(
        Log_Minutes_Sum=('Log_Minutes_Sum', 'sum'),
        Log_Minutes_Count=('Log_Minutes_Count', 'sum')
    ).reset_index()
    

    data_stop_aux = pd.concat([mic_stop_aux, plex_stop_aux])

    data_stop_aux = pd.merge(left=data_stop_aux, right=getPlex('events')[['Code', 'Description']], on=['Code'])
    data_stop_aux['Event'] = data_stop_aux['Code'] + '-' + data_stop_aux['Description']

    data_stop_aux['Log_Minutes_Sum'] = data_stop_aux['Log_Minutes_Sum'].astype(float)

    data_stop_aux = data_stop_aux.groupby(by=["Time_Group", "Event"]).agg(
        Log_Minutes_Sum=('Log_Minutes_Sum', 'sum'),
        Log_Minutes_Count=('Log_Minutes_Count', 'sum')
    ).reset_index()   

    if not data_stop.empty:

        data_stop['Total'] = data_stop['Log_Minutes_Sum'].sum().astype(int)
        data_stop['Log_Minutes_Sum'] = data_stop['Log_Minutes_Sum'].astype(int)
        data_stop = data_stop.nlargest(5, 'Log_Minutes_Sum')

        data_stop_aux['Total'] = data_stop_aux.groupby('Time_Group')['Log_Minutes_Sum'].transform('sum').astype(int)
        data_stop_aux['Log_Minutes_Sum'] = data_stop_aux['Log_Minutes_Sum'].astype(int)
        data_stop_aux = data_stop_aux.sort_values(['Time_Group', 'Log_Minutes_Sum'], ascending=[True, False])
        data_stop_aux = data_stop_aux.groupby('Time_Group').head(5)
    
    return data_oee, data_stop, data_stop_aux


@operation_production_bp.route('/op/producao', methods=['GET'])
def prod_main_get():

    month = datetime.now().month
    year = datetime.now().year

    return render_template('operation.prod/prod_main.html', month=month, year=year)

@operation_production_bp.route('/op/producao', methods=['POST'])
def prod_main_post():

    try:
        year = int(request.args.get('year', ''))
        month = int(request.args.get('month', ''))

        if not (2019 <= year) or not (1 <= month <= 12):
            abort(400, "Invalid year or month")
    except ValueError:
        abort(400, "Year and month must be integers")

    mic_query = f"""

                SELECT 
                    FORMAT(tStartTime, 'dd/MM') AS Time_Group
                    , T2.GRUPO AS Workcenter_Group

                    , SUM(dRunSec) / 3600.0 AS TotalRun
                    , SUM(dAvailSec) / 3600.0 AS TotalAvail

                    , SUM(dGoodParts) AS TotalGoodParts
                    , SUM(dTotalParts) AS TotalParts
                    , SUM(CASE WHEN dIdealCycleTime > 1 THEN dRunSec / NULLIF(dIdealCycleTime, 0) ELSE 0 END) AS Expected_Pieces

                FROM OEEQWorkCellDetail T1
                JOIN CONFIG_TABLET T2 ON T1.sDescription = T2.NOME_MAQUINA

                WHERE 
                    T1.tStartTime BETWEEN 
                        :start_date
                        AND CASE 
                            WHEN T2.CT_PLEX_DATA < EOMONTH(:start_date)
                            THEN T2.CT_PLEX_DATA 
                            ELSE EOMONTH(:start_date)
                        END

                        AND nShift IN (1, 2, 3)

                GROUP BY FORMAT(tStartTime, 'dd/MM'), T2.GRUPO
                ORDER BY FORMAT(tStartTime, 'dd/MM')

    """

    plex_oee_query = f"""

                WITH target_rates AS (

                    SELECT 
                        T01.id_Mach_2_OEE_v2
                        , AVG(T02.Target_Rate) as Target_Rate
                    FROM

                        Mach_2_OEE_Cavity_Info T01 

                        JOIN OPENQUERY([PLEX_DSN_JOST], '
                            SELECT 
                                T1.Part_No
                                , T2.Target_Rate
                            FROM 
                                Part_v_Part T1
                                JOIN Part_v_Approved_Workcenter T2 ON T1.Part_Key = T2.Part_Key
                        ') T02 ON T01.part = T02.Part_No COLLATE SQL_Latin1_General_CP1_CI_AS

                    GROUP BY T01.id_Mach_2_OEE_v2
                )

                SELECT
                    FORMAT(record_time, 'dd/MM') AS Time_Group
                    , T3.Workcenter_Group

                    , SUM(CAST(T1.production_difference AS INT)) AS TotalParts
                    , SUM(CAST(T1.time_difference AS FLOAT) / 3600.0 * CAST(T2.Target_Rate AS FLOAT)) AS Expected_Pieces


                FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_OEE_v2] T1
                    LEFT JOIN target_rates T2 ON T1.ID = T2.id_Mach_2_OEE_v2
                    JOIN OPENQUERY([PLEX_DSN_JOST], '
                        SELECT 
                            Workcenter_Code
                            , Workcenter_Key
                            , Name
                            , Workcenter_Group
                        FROM 
                            Part_v_Workcenter
                    ') T3 ON T1.workcenter = T3.Workcenter_Code COLLATE SQL_Latin1_General_CP1_CI_AS
                    
                WHERE
                    T1.record_time BETWEEN :start_date AND EOMONTH(:start_date)

                GROUP BY FORMAT(record_time, 'dd/MM'), T3.Workcenter_Group
                ORDER BY FORMAT(record_time, 'dd/MM')

    """

    plex_availability_query = f"""

        DECLARE @Start_Date DATE = :start_date;
        DECLARE @End_Date DATE = EOMONTH(@Start_Date);

        EXEC('sproc329396_18311230_1264675 ?, ?, ?, ?, ?, ?, ?, ?, ?',
            @Start_Date, @End_Date, '[]', '[]', '[]', 0, 1, 0, 0
        ) AT [PLEX_DSN_JOST];

    """

    with ThreadPoolExecutor() as executor:
        mic_data = executor.submit(engine_run_query, mic_query, 'ftm', {'start_date': f'{year}-{month}-01'})

        plex_oee_data = executor.submit(engine_run_query, plex_oee_query, 'plex', {'start_date': f'{year}-{month}-01'})
        plex_availability_data = executor.submit(engine_run_query, plex_availability_query, 'plex', {'start_date': f'{year}-{month}-01'})

    mic_data = mic_data.result()
    plex_oee_data = plex_oee_data.result()
    plex_availability_data = plex_availability_data.result()


    plex_oee_data['TotalGoodParts'] = plex_oee_data['TotalParts']
    plex_availability_data = plex_availability_data[['TotalRun', 'TotalAvail', 'Time_Group', 'Workcenter_Group']]

    plex_data = pd.merge(left=plex_oee_data, right=plex_availability_data, on=['Time_Group', 'Workcenter_Group'])

    grouped_data = pd.concat([mic_data, plex_data])

    grouped_data = grouped_data.groupby(by=['Time_Group', 'Workcenter_Group']).agg(
        TotalRun=('TotalRun', 'sum'),
        TotalAvail=('TotalAvail', 'sum'),
        TotalGoodParts=('TotalGoodParts', 'sum'),
        TotalParts=('TotalParts', 'sum'),
        Expected_Pieces=('Expected_Pieces', 'sum')
    ).reset_index()

    grouped_data['Performance'] = grouped_data.apply(
        lambda row: (row['TotalParts'] / row['Expected_Pieces']) * 100 if row['Expected_Pieces'] != 0 else 0,
        axis=1
    )
    grouped_data['Availability'] = grouped_data['TotalRun'] / grouped_data['TotalAvail'] * 100
    grouped_data['Quality'] = grouped_data.apply(
        lambda row: (row['TotalGoodParts'] / row['TotalParts']) * 100 if row['TotalParts'] != 0 else 0,
        axis=1
    )

    data = {'calendar' : grouped_data.to_dict(orient="records")}

    return jsonify(data)

@operation_production_bp.route('/op/producao/indicadores', methods=['GET'])
def prod_kpis_get():

    preload = {}
    if 'preload' in request.args:
        preload['preload'] = request.args['preload']
        preload['year'] = request.args['year']
        preload['month'] = request.args['month']
        preload['day'] = request.args['day']

    query = f"""SELECT 
                    GRUPO AS Workcenter_Group
                    , LEFT(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) - 1) AS Workcenter_Code
                    , SUBSTRING(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) + 1, LEN(NOME_MAQUINA)) AS Name
                    , 1 AS Workcenter_Key
                FROM CONFIG_TABLET WHERE CT_PLEX IS NULL"""
    mic_workcenters = engine_run_query(query, 'ftm')

    mes_workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]
    workcenters = pd.concat([mes_workcenters[~mes_workcenters['Workcenter_Code'].isin(mic_workcenters['Workcenter_Code'])], mic_workcenters])

    return render_template('operation.prod/prod_kpis.html'
                            , preload=preload
                            , workcenters=workcenters.sort_values(by="Workcenter_Code").to_dict(orient="records"))
    
@operation_production_bp.route('/op/producao/indicadores', methods=['POST'])
def prod_kpis_post():

    payload = request.get_json()

    payload['start_date'] = payload['start_date'].replace("T", " ") + ':00'
    payload['end_date'] = payload['end_date'].replace("T", " ") + ':00'
                        
    data_oee, data_stop, data_stop_aux = _GET_PROD_DATA(False, payload)

    if not data_stop.empty:

        data = {'data': data_oee.to_dict(orient='records'),
            'stop': data_stop.to_dict(orient='records'),
            'stop_aux': data_stop_aux.to_dict(orient='records')}

    else: 

        data = {'data': data_oee.to_dict(orient='records'),
                'stop': '',
                'stop_aux': ''}

    return jsonify(data)
    
@operation_production_bp.route('/op/producao/indicadores/excel', methods=['POST'])
def prod_kpis_excel_post():

    payload = request.get_json()

    payload['start_date'] = payload['start_date'].replace("T", " ") + ':00'
    payload['end_date'] = payload['end_date'].replace("T", " ") + ':00'

    data_oee, data_stop, data_stop_aux = _GET_PROD_DATA(False, payload)
    data_oee = data_oee.rename(columns={'TotalAvail': 'Tempo Disponível', 'TotalRun' : 'Tempo em Produção', 'TotalGoodParts': 'Peças Boas', 'Shift_Group': 'Turno', 'TotalParts': 'Peças Produzidas', 'Availability' : 'Disponibilidade', 'Quality': 'Qualidade', 'Goal': 'Meta OEE', 'Expected_Pieces' : 'Performance 100%', 'Expected_Pieces2' : 'Peças - Performance 100% + Meta disponibilidade', 'Time_Group': 'Data'})
    data_oee = data_oee.drop(columns=['TotalPartsSum', 'PerformanceGoal'])

    data_oee2, data_stop2, data_stop_aux2 = _GET_PROD_DATA(True, payload)
    data_oee2 = data_oee2.rename(columns={'TotalAvail': 'Tempo Disponível', 'TotalRun' : 'Tempo em Produção', 'TotalGoodParts': 'Peças Boas', 'Shift_Group': 'Turno', 'Workcenter_Name': 'Centro de Trabalho', 'TotalParts': 'Peças Produzidas', 'Availability' : 'Disponibilidade', 'Quality': 'Qualidade', 'Goal': 'Meta OEE', 'Expected_Pieces' : 'Performance 100%', 'Expected_Pieces2' : 'Peças - Performance 100% + Meta disponibilidade', 'Time_Group': 'Data'})
    data_oee2 = data_oee2.drop(columns=['TotalPartsSum', 'Workcenter_Group', 'PerformanceGoal'])

    path = fr'{os.getcwd()}\app\static\uploads\default'
    excel_filename = f'{path}\indicadores.xlsx'
    if os.path.exists(excel_filename):
        os.remove(excel_filename)

    with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
        data_oee.to_excel(writer, sheet_name='GERAL', index=False)
        data_oee2.to_excel(writer, sheet_name='POR CENTRO DE TRABALHO', index=False)

    return send_file(excel_filename, as_attachment=True)
