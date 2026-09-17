import os
import pandas as pd
from datetime import timedelta, datetime

from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app.utils.business import getStopsData
from app.utils.db_utils import engine_run_query
from app.utils.dynamic_constants import getPlex
from app.utils.permissions import get_permission


reports_oee_bp = Blueprint('reports_oee', __name__)

@reports_oee_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)


def _SIGNAL_DATA(payload):

    plex_data = pd.DataFrame()
    mic_data = pd.DataFrame()

    if payload['workcenters_plex']:

        where_plex_w_count = ', '.join([f':w_plex_val{i}' for i in range(len(payload['workcenters_plex']))]) if payload['workcenters_plex'] else ':w_plex_val0'
        if payload['workcenters_plex']:
            where_plex_w_values = {f'w_plex_val{i}': v for i, v in enumerate(payload['workcenters_plex'])}
        else:
            where_plex_w_values = {'w_plex_val0': 'M00'}

        where_plex_params = {
            'start_date': payload['start_date']
            , 'end_date': payload['end_date']
            , **where_plex_w_values
        }

        plex_signal_query = f"""

            WITH target_rates_plex AS(
                SELECT *
                FROM OPENQUERY([PLEX_DSN_JOST], '
                    SELECT
                        T1.Part_No
                        , T3.Workcenter_Code
                        , CASE
                            WHEN T2.Ideal_Rate = 0.0 THEN 0.0
                            ELSE 60.0 / T2.Ideal_Rate
                        END AS Routing_Time
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
                    , T03.Workcenter_Code
                    , AVG(T03.Routing_Time) AS Routing_Time
                FROM

                    Mach_2_OEE_Cavity_Info T01
                    JOIN Mach_2_OEE_v2 T02 ON T01.id_Mach_2_OEE_v2 = T02.id

                    JOIN target_rates_plex T03 ON
                        T01.part = T03.Part_No COLLATE SQL_Latin1_General_CP1_CI_AS
                        AND T02.workcenter = T03.Workcenter_Code COLLATE SQL_Latin1_General_CP1_CI_AS

                GROUP BY T01.id_Mach_2_OEE_v2, T03.Workcenter_Code 

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
                , Part
                , Job
                , CAST(T1.production_difference AS INT) AS Signal
                , Routing_Time
                , CAST(T1.time_difference AS FLOAT) / 60.0 AS Duration


            FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_OEE_v2] T1
                JOIN target_rates_final T2 ON T1.ID = T2.id_Mach_2_OEE_v2
                JOIN actual_rates T3 ON T1.id = T3.id_Mach_2_OEE_v2

            WHERE 
                T1.record_time BETWEEN :start_date AND :end_date
                AND T1.workcenter IN ({where_plex_w_count})

            ORDER BY record_time DESC

        """

        plex_data = engine_run_query(plex_signal_query, 'plex', where_plex_params)

        plex_data = pd.merge(left=plex_data, right=getPlex('workcenters')[['Workcenter_Code', 'Name']], how='left', on='Workcenter_Code')


    if payload['workcenters_mic']:

        where_mic_w_count = ', '.join([f':w_mic_val{i}' for i in range(len(payload['workcenters_mic']))]) if payload['workcenters_mic'] else ':w_mic_val0'
        if payload['workcenters_mic']:
            where_mic_w_values = {f'w_mic_val{i}': v for i, v in enumerate(payload['workcenters_mic'])}
        else:
            where_mic_w_values = {'w_mic_val0': 'M00'}

        where_mic_params = {
            'start_date': payload['start_date']
            , 'end_date': payload['end_date']
            , **where_mic_w_values
        }

        mic_signal_query = f"""
            DECLARE @start_date DATETIME = :start_date
            DECLARE @end_date DATETIME = :end_date

            ;WITH target_rates AS (
                SELECT sPartId, sDescription, dIdealCycleTime
                FROM (
                    SELECT 
                        sPartId
                        , sDescription
                        , dIdealCycleTime
                        , ROW_NUMBER() OVER (
                            PARTITION BY sPartId, sDescription 
                            ORDER BY tStart DESC
                        ) AS rn
                    FROM OEEQWorkCell
                    WHERE tStart BETWEEN @start_date AND @end_date AND sDescription IN ({where_mic_w_count})
                ) AS ranked
                WHERE rn = 1
            )

            SELECT 
                FORMAT(T1.tStart, 'dd/MM/yyyy HH:mm:ss') AS Record_Time
                , SUBSTRING(T1.sDescription, CHARINDEX('-', T1.sDescription) + 1, LEN(T1.sDescription)) AS Name
                , LEFT(T1.sDescription, CHARINDEX('-', T1.sDescription) - 1) AS Workcenter_Code
                , T1.sPartId AS Part
                , '' AS Job
                , 1 AS Signal
                , DATEDIFF(SECOND, 0, T1.dDuration) AS Duration
                , T3.dIdealCycleTime / 60.0 AS Routing_Time
            FROM JOST_OEEventDetail T1
            LEFT JOIN CADASTRO_SINAIS_COLETA T2 
                ON T1.sPartId = T2.MATERIAL AND T1.sDescription = T2.COD_MAQUINA
            JOIN target_rates T3 
                ON T1.sPartId = T3.sPartId AND T1.sDescription = T3.sDescription
            WHERE 
                T1.tStart BETWEEN @start_date AND @end_date
                AND T1.sDescription IN ({where_mic_w_count})
                AND T1.sEventDescription = 'Contagem Peça'
        """
        
        mic_data = engine_run_query(mic_signal_query, 'ftm', where_mic_params)

    data = pd.concat([plex_data, mic_data])

    carry = 0
    adjusted_duration = []

    for row in reversed(list(data.itertuples())):
        if row.Signal < 0:
            carry += row.Duration
            adjusted_duration.append(0)
        else:
            adjusted_duration.append(row.Duration + carry)
            carry = 0

    data['Duration'] = list(reversed(adjusted_duration))

    return data

        
# DASHBOARD - PARADAS
@reports_oee_bp.route('/oee/paradas', methods=["GET"])
def oee_stops_get():

    query = f"""SELECT 
                    GRUPO AS Workcenter_Group
                    , LEFT(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) - 1) AS Workcenter_Code
                    , SUBSTRING(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) + 1, LEN(NOME_MAQUINA)) AS Name
                    , 1 AS Workcenter_Key
                FROM CONFIG_TABLET WHERE CT_PLEX IS NULL"""
    mic_workcenters = engine_run_query(query, 'ftm')

    mes_workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]
    workcenters = pd.concat([mes_workcenters[~mes_workcenters['Workcenter_Code'].isin(mic_workcenters['Workcenter_Code'])], mic_workcenters])

    events_query = """
        SELECT DISTINCT
            COALESCE(
                NULLIF(LTRIM(RTRIM(wc_reason)), ''),
                'Sem Justificativa'
            ) AS Description
        FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_Status_Reason_Time]
        WHERE NULLIF(LTRIM(RTRIM(workcenter)), '') IS NOT NULL
            AND (
                NULLIF(LTRIM(RTRIM(wc_reason)), '') IS NOT NULL
                OR COALESCE(NULLIF(LTRIM(RTRIM(wc_stauts)), ''), 'Produção') <> 'Produção'
            )
    """
    events = engine_run_query(events_query, 'plex')

    preload = {}
    if 'preload' in request.args:

        def get_week_start_end(year, week):
            start_of_week = datetime.strptime(
                f'{year}-W{week}-1',
                "%G-W%V-%u"
            ).replace(hour=0, minute=0, second=0)
            end_of_week = start_of_week + timedelta(days=7)
            
            return start_of_week.strftime('%Y-%m-%dT%H:%M'), end_of_week.strftime('%Y-%m-%dT%H:%M')

        start, end = get_week_start_end(int(request.args['year']), int(request.args['week']))

        preload['preload'] = request.args['preload']
        preload['area'] = request.args['area']
        preload['start'] = start
        preload['end'] = end

    return render_template(
        'reports.oee/oee_stops.html'
        , events=events.sort_values(by='Description').to_dict(orient='records')
        , workcenters=workcenters.sort_values(by="Workcenter_Code").to_dict(orient="records")
        , preload=preload
    )

@reports_oee_bp.route('/oee/paradas', methods=['POST'])
def oee_stops_post():

    payload = request.get_json()
    payload['start_date'] = payload['start_date'].replace('T', ' ') + ':00'
    payload['end_date'] = payload['end_date'].replace('T', ' ') + ':00'

    event = getStopsData(payload, use_status_reason_time=True)
    table1 = event[['Workcenter_Name', 'Workcenter_Group', 'Log_Date', 'End_Date', 'Log_Minutes', 'Event', 'Status']]

    if table1.shape[0] > 5000:

        result_row = {
            'Workcenter_Name': 'Limite de 5.000 linhas atingido.',
            'Workcenter_Group': 'Para ver esta tabela, baixe o Excel.',
            'Log_Date': '-',
            'End_Date': '-',
            'Log_Minutes': '0',
            'Event': '-',
            'Status': 'Os gráficos não foram afetados.'
        }

        table1 = pd.DataFrame([result_row])


    table2 = event[['Event', 'Shift', 'Log_Minutes']].groupby(by=['Event', 'Shift']).agg(
        Log_Minutes_Count=('Log_Minutes', 'count'),
        Log_Minutes_Sum=('Log_Minutes', 'sum')
    ).reset_index()

    table2['Percentage'] = (
        table2['Log_Minutes_Sum'].astype(float) /
        table2.groupby('Shift')['Log_Minutes_Sum'].transform('sum')
    ).fillna(0) * 100

    table3 = event[['Workcenter_Name', 'Log_Minutes']].groupby(by='Workcenter_Name').agg(
        Log_Minutes_Count=('Log_Minutes', 'count'),
        Log_Minutes_Sum=('Log_Minutes', 'sum')
    ).reset_index().rename(columns={'Workcenter_Name' : 'label'})

    table4 = event[['Event', 'Status', 'Log_Minutes']].groupby(by=['Event', 'Status']).agg(
        Log_Minutes_Count=('Log_Minutes', 'count'),
        Log_Minutes_Sum=('Log_Minutes', 'sum')
    ).reset_index().rename(columns={'Event' : 'label'})

    table4['Log_Hours_Sum'] = table4['Log_Minutes_Sum'] / 60

    total_sum = table4['Log_Minutes_Sum'].sum()
    if total_sum != 0:
        table4['Percentage'] = (table4['Log_Minutes_Sum'] / total_sum) * 100
    else:
        table4['Percentage'] = 0  # ou np.nan, se preferir

        
    event['Log_Date'] = pd.to_datetime(event['Log_Date'], format='%d/%m/%Y %H:%M:%S')
    event['End_Date'] = pd.to_datetime(event['End_Date'], format='%d/%m/%Y %H:%M:%S')

    # Função para dividir logs que atravessam meses
    def logs_between_months(row):
        init = row['Log_Date']
        end = row['End_Date']
        
        # Verifica se o log atravessa para o próximo mês
        if init.month != end.month:

            # Primeiro mês (do inicio até o final do mês)
            end_first_month = init + pd.offsets.MonthEnd(0)
            duration_first_month = (end_first_month - init).total_seconds() / 60
            
            # Segundo mês (do início do mês até fim do log)
            init_second_month = end_first_month + timedelta(seconds=1)
            duration_second_month = (end - init_second_month).total_seconds() / 60
            
            return [
                {'Month': init, 'Log_Minutes': duration_first_month},
                {'Month': end, 'Log_Minutes': duration_second_month}
            ]
        else:
            # Caso o log esteja todo em um único mês
            duracao_total = (end - init).total_seconds() / 60
            return [{'Month': init, 'Log_Minutes': duracao_total}]

    if not event.empty:
        table5 = pd.DataFrame([item for sublist in event[['Log_Minutes', 'Log_Date', 'End_Date']].apply(logs_between_months, axis=1) for item in sublist])
        table5['Month'] = table5['Month'].dt.strftime('%b-%Y')
        table5 = table5.groupby('Month')['Log_Minutes'].sum().reset_index().sort_values(by='Month', key=lambda x: pd.to_datetime(x.str.replace('-', ' ')))
    else:
        table5 = pd.DataFrame(columns=['Month', 'Log_Minutes'])

    data_to_send = {
        'table1': table1.to_json(orient='records'),
        'table2': table2[table2['Shift'] == 'Primeiro'].sort_values(by='Log_Minutes_Sum', ascending=False).to_json(orient='records'),
        'table3': table2[table2['Shift'] == 'Segundo'].sort_values(by='Log_Minutes_Sum', ascending=False).to_json(orient='records'),
        'table4': table2[table2['Shift'] == 'Terceiro'].sort_values(by='Log_Minutes_Sum', ascending=False).to_json(orient='records'),
        'table5': table4.sort_values(by='Log_Minutes_Sum', ascending=False).to_json(orient='records'),
        'barchart1': table3.sort_values(by='Log_Minutes_Sum', ascending=False).to_json(orient='records'),
        'barchart2': table4.drop(columns=['Percentage', 'Status', 'Log_Hours_Sum']).sort_values(by='Log_Minutes_Sum', ascending=False).to_json(orient='records'),
        'barchart3': table5.to_json(orient='records'),
        'total_minutes': str(round(event['Log_Minutes'].sum(), 2)),
        'total_qtt': str(event.shape[0])
    }

    return data_to_send


@reports_oee_bp.route('/oee/sinal', methods=['GET'])
def oee_signal_get():

    now = datetime.now()
    start_of_week = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())

    this_week = now
    last_week = start_of_week

    this_week_str = this_week.strftime("%Y-%m-%dT%H:%M")
    last_week_str = last_week.strftime("%Y-%m-%dT%H:%M")

    query = f"""SELECT 
                    GRUPO AS Workcenter_Group
                    , LEFT(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) - 1) AS Workcenter_Code
                    , SUBSTRING(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) + 1, LEN(NOME_MAQUINA)) AS Name
                    , 1 AS Workcenter_Key
                FROM CONFIG_TABLET WHERE CT_PLEX IS NULL"""
    mic_workcenters = engine_run_query(query, 'ftm')

    mes_workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]
    workcenters = pd.concat([mes_workcenters[~mes_workcenters['Workcenter_Code'].isin(mic_workcenters['Workcenter_Code'])], mic_workcenters]).sort_values(by="Workcenter_Code")

    return render_template(
        'reports.oee/oee_signal.html'
        , this_week=this_week_str
        , last_week=last_week_str
        , workcenters=workcenters.to_dict(orient="records")
    )

@reports_oee_bp.route('/oee/sinal', methods=['POST'])
def oee_signal_post():

    payload = request.get_json()

    if not (payload.get('workcenters_plex') or payload.get('workcenters_mic')):
        return jsonify({'message': 'Nenhum centro de trabalho selecionado.'}), 400

    
    payload['start_date'] = payload['start_date'].replace("T", " ")
    payload['end_date'] = payload['end_date'].replace("T", " ")

    data = _SIGNAL_DATA(payload)

    if len(data) > 1000:

        result_row = {
            'Workcenter_Code': 'Limite de 1.000 linhas atingido ',
            'Name': ' Para ver esta tabela, baixe o Excel.',
            'Job': '',
            'Part': '',
            'Record_Time': '',
            'Signal': '',
            'Routing_Time': ''
        }

        data = pd.DataFrame([result_row])

    return ({'data': data.to_dict(orient='records')})


@reports_oee_bp.route('/oee/paradas/excel', methods=['POST'])
def oee_stops_excel():

    path = fr'{os.getcwd()}\app\static\uploads\default'
    excel_filename = f'{path}\paradas.xlsx'
    if os.path.exists(excel_filename):
        os.remove(excel_filename)

    payload = request.get_json()
    payload['start_date'] = payload['start_date'].replace('T', ' ') + ':00'
    payload['end_date'] = payload['end_date'].replace('T', ' ') + ':00'

    data = getStopsData(payload, use_status_reason_time=True)[['Workcenter_Name', 'Workcenter_Group', 'Status', 'Event', 'Log_Minutes', 'Shift', 'Log_Date', 'End_Date']]
    data = data.rename(columns={'Workcenter_Name': 'Centro de Trabalho', 'Shift': 'Turno', 'Event': 'Parada', 'Status': 'Ms', 'Log_Date': 'Hora de Início', 'Workcenter_Group': 'Área', 'Log_Minutes': 'Duração em Minutos', 'End_Date' : 'Data Fim'})
    data.to_excel(excel_filename, index=False, header=True)


    return send_file(excel_filename, as_attachment=True)

@reports_oee_bp.route('/oee/sinal/excel', methods=['POST'])
def oee_signal_excel():

    payload = request.get_json()

    if not (payload.get('workcenters_plex') or payload.get('workcenters_mic')):
        return jsonify({'message': 'Nenhum centro de trabalho selecionado.'}), 400

    payload['start_date'] = payload['start_date'].replace("T", " ")
    payload['end_date'] = payload['end_date'].replace("T", " ")

    path = fr'{os.getcwd()}\app\static\uploads\default'
    excel_filename = f'{path}\sinal.xlsx'
    if os.path.exists(excel_filename):
        os.remove(excel_filename)


    data = _SIGNAL_DATA(request.get_json())

    data['Workcenter'] = data['Workcenter_Code'] + '-' + data['Name']
    data = data[['Record_Time', 'Workcenter', 'Part', 'Job', 'Signal', 'Routing_Time', 'Duration']]

    data = data.rename(columns={'Record_Time': 'Fim', 'Workcenter': 'Centro de Trabalho', 'Part': 'Peça', 'Job': 'Ordem de Produção', 'Signal': 'Sinal', 'Routing_Time': 'Tempo Padrão (min)', 'Duration': 'Duração (min)'})
    data.to_excel(excel_filename, index=False, header=True)

    return send_file(excel_filename, as_attachment=True)

# V2
