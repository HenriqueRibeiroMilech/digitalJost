import json

import pandas as pd
from sqlalchemy.exc import DBAPIError

from app.utils.dynamic_constants import getPlex
from app.utils.db_utils import engine_run_query, get_engine


def _add_parameterized_list_filter(conditions, params, expression, values, prefix):
    if not values:
        return

    placeholders = []
    for index, value in enumerate(values):
        parameter_name = f'{prefix}_{index}'
        placeholders.append(f':{parameter_name}')
        params[parameter_name] = value

    conditions.append(f"{expression} IN ({', '.join(placeholders)})")


def _run_query_with_deadlock_retry(query, engine_name, params):
    try:
        return engine_run_query(query, engine_name, params)
    except DBAPIError as error:
        if '1205' not in str(error.orig):
            raise

        return engine_run_query(query, engine_name, params)


def _get_status_reason_time_stops(received_data):
    workcenters = getPlex('workcenters')[[
        'Workcenter_Key', 'Workcenter_Code', 'Name', 'Workcenter_Group'
    ]].copy()

    scoped_workcenters = workcenters.copy()

    if received_data.get('w_name_plex'):
        selected_keys = {str(value) for value in received_data['w_name_plex']}
        scoped_workcenters = scoped_workcenters[
            scoped_workcenters['Workcenter_Key'].astype(str).isin(selected_keys)
        ]
    elif received_data.get('w_name_mic'):
        return pd.DataFrame(columns=[
            'Log_Key', 'Workcenter_Key', 'Workcenter_Name', 'Workcenter_Group',
            'Log_Date', 'End_Date', 'Log_Minutes', 'Code', 'Status', 'Shift',
            'Plex', 'Event'
        ])

    if received_data.get('w_group'):
        scoped_workcenters = scoped_workcenters[
            scoped_workcenters['Workcenter_Group'].isin(received_data['w_group'])
        ]

    target_workcenters = (
        scoped_workcenters['Workcenter_Code']
        .dropna()
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    if not target_workcenters:
        return pd.DataFrame(columns=[
            'Log_Key', 'Workcenter_Key', 'Workcenter_Name', 'Workcenter_Group',
            'Log_Date', 'End_Date', 'Log_Minutes', 'Code', 'Status', 'Shift',
            'Plex', 'Event'
        ])

    reason_expression = (
        "COALESCE(NULLIF(LTRIM(RTRIM(T1.wc_reason)), ''), 'Sem Justificativa')"
    )
    status_expression = """CASE
        WHEN NULLIF(LTRIM(RTRIM(T1.wc_stauts)), '') IS NULL THEN 'Sem Categoria'
        WHEN LTRIM(RTRIM(T1.wc_stauts)) IN ('Manutenção Parada', 'Manutenção Produtiva') THEN 'Manutenção'
        ELSE LTRIM(RTRIM(T1.wc_stauts))
    END"""
    shift_expression = """CASE T1.wc_shift
        WHEN 'Turno 1' THEN 'Primeiro'
        WHEN 'Turno 2' THEN 'Segundo'
        WHEN 'Turno 3' THEN 'Terceiro'
        ELSE T1.wc_shift
    END"""
    duration_end_expression = (
        "DATEADD(SECOND, T1.wc_status_reason_time, T1.record_time)"
    )
    end_expression = f"""CASE
        WHEN T1.NextReasonTime IS NOT NULL
            AND (
                {duration_end_expression} IS NULL
                OR T1.NextReasonTime < {duration_end_expression}
            )
        THEN T1.NextReasonTime
        ELSE COALESCE({duration_end_expression}, GETDATE())
    END"""

    params = {
        'start_date': received_data['start_date'],
        'end_date': received_data['end_date']
    }
    target_workcenter_rows = []
    for index, workcenter in enumerate(target_workcenters):
        parameter_name = f'target_workcenter_{index}'
        params[parameter_name] = workcenter
        target_workcenter_rows.append(f'(CAST(:{parameter_name} AS VARCHAR(50)))')

    conditions = [
        "NULLIF(LTRIM(RTRIM(T1.workcenter)), '') IS NOT NULL",
        """(
            NULLIF(LTRIM(RTRIM(T1.wc_reason)), '') IS NOT NULL
            OR COALESCE(NULLIF(LTRIM(RTRIM(T1.wc_stauts)), ''), 'Produção') <> 'Produção'
        )""",
        f'{end_expression} > :start_date'
    ]

    if received_data.get('w_group'):
        _add_parameterized_list_filter(
            conditions,
            params,
            status_expression,
            received_data.get('m_group', []),
            'status'
        )

        selected_shifts = {
            '1': 'Primeiro',
            '2': 'Segundo',
            '3': 'Terceiro',
            'Extra': 'Extra'
        }
        shift_values = [
            selected_shifts[shift]
            for shift in received_data.get('shift', [])
            if shift in selected_shifts
        ]
        _add_parameterized_list_filter(
            conditions,
            params,
            shift_expression,
            shift_values,
            'shift'
        )

    _add_parameterized_list_filter(
        conditions,
        params,
        reason_expression,
        received_data.get('m_event', []),
        'reason'
    )

    query = f"""
        WITH TargetWorkcenters AS (
            SELECT Workcenter_Code
            FROM (VALUES {', '.join(target_workcenter_rows)}) AS Target(Workcenter_Code)
        ),
        PeriodRows AS (
            SELECT
                T1.id
                , T1.workcenter
                , T1.wc_shift
                , T1.wc_stauts
                , T1.wc_reason
                , T1.wc_status_reason_time
                , T1.record_time
            FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_Status_Reason_Time] T1
            JOIN TargetWorkcenters Target
                ON Target.Workcenter_Code = T1.workcenter
            WHERE T1.record_time >= :start_date
                AND T1.record_time < :end_date
        ),
        PreviousRows AS (
            SELECT Previous.*
            FROM TargetWorkcenters Target
            CROSS APPLY (
                SELECT TOP 1
                    T1.id
                    , T1.workcenter
                    , T1.wc_shift
                    , T1.wc_stauts
                    , T1.wc_reason
                    , T1.wc_status_reason_time
                    , T1.record_time
                FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_Status_Reason_Time] T1
                WHERE T1.workcenter = Target.Workcenter_Code
                    AND T1.record_time < :start_date
                ORDER BY T1.record_time DESC, T1.id DESC
            ) Previous
        ),
        CandidateRows AS (
            SELECT * FROM PreviousRows
            UNION ALL
            SELECT * FROM PeriodRows
        ),
        PreparedRows AS (
            SELECT
                CandidateRows.*
                , LEAD(record_time) OVER (
                    PARTITION BY workcenter
                    ORDER BY record_time, id
                ) AS NextReasonTime
            FROM CandidateRows
        )

        SELECT
            T1.id AS Log_Key
            , T1.workcenter AS Workcenter_Code
            , Bounds.Log_Start AS Log_Date
            , Bounds.Log_End AS End_Date
            , ROUND(DATEDIFF(SECOND, Bounds.Log_Start, Bounds.Log_End) / 60.0, 2) AS Log_Minutes
            , CAST('' AS VARCHAR(1)) AS Code
            , {status_expression} AS Status
            , {shift_expression} AS Shift
            , 1 AS Plex
            , {reason_expression} AS Event

        FROM PreparedRows T1

        CROSS APPLY (
            SELECT
                CASE
                    WHEN T1.record_time < :start_date THEN CAST(:start_date AS DATETIME2)
                    ELSE T1.record_time
                END AS Log_Start
                , CASE
                    WHEN {end_expression} > :end_date
                    THEN CAST(:end_date AS DATETIME2)
                    ELSE {end_expression}
                END AS Log_End
        ) Bounds

        WHERE {' AND '.join(conditions)}
            AND Bounds.Log_End > Bounds.Log_Start
    """

    event = _run_query_with_deadlock_retry(query, 'plex', params)

    if not event.empty:
        event['Log_Date'] = pd.to_datetime(event['Log_Date']).dt.strftime('%d/%m/%Y %H:%M:%S')
        event['End_Date'] = pd.to_datetime(event['End_Date']).dt.strftime('%d/%m/%Y %H:%M:%S')

    event = pd.merge(
        left=event,
        right=workcenters,
        how='left',
        on='Workcenter_Code'
    )

    event['Workcenter_Name'] = (
        event['Workcenter_Code'].astype(str)
        + event['Name'].fillna('').apply(lambda name: f'-{name}' if name else '')
    )
    event['Workcenter_Group'] = event['Workcenter_Group'].fillna('Sem Área')

    return event


def getStopsData(received_data, use_status_reason_time=False):
    """
        DADOS DE PAYLOAD:
        
        1. OBRIGATÓRIOS:
            start_date: YYYY/MM/DD HH:mm:SS
            end_date: YYYY/MM/DD HH:mm:SS

        2. OPCIONAIS:
            w_name_plex: LISTA DE Workcenter_Key
            w_name_mic: LISTA DE NOME_MAQUINA
            w_group: LISTA DE Workcenter_Group/GRUPO
            m_group: LISTA DE Workcenter_Event_Group/CATEGORIA

        3. CONTROLE DA FONTE PLEX:
            use_status_reason_time: usa Mach_2_Status_Reason_Time no lugar da procedure legada

        LÓGICAS DE NEGOCIO: 
        1. Caso não seja enviado w_group. Os opcionais w_group, m_group e shift_plex ficarão vazios.

    """

    shift_filter = {"1": 'primeiro', "2": 'segundo', "3": 'terceiro', 'Extra': None}
    received_data["shift_plex"] = [shift_filter[shift] for shift in received_data["shift"] if shift_filter[shift] is not None]

    if use_status_reason_time:
        event = _get_status_reason_time_stops(received_data)
    else:
        events_join = getPlex('events')
        events_join.loc[len(events_join)] = [1, 'Sem Justificativa', 'Sem Categoria', 1, "0"]

        workcenter_filter = ''
        if received_data.get('w_name_plex'):
            workcenter_filter = json.dumps(received_data['w_name_plex'], ensure_ascii=False)
        elif received_data.get('w_name_mic'):
            workcenter_filter = '[1]'

        if received_data.get('w_group'):
            workcenter_group = json.dumps(received_data.get('w_group', '[1]'), ensure_ascii=False)
            workcenter_event_group = json.dumps(received_data.get('m_group', '[1]'), ensure_ascii=False)
            shift_group = json.dumps(received_data.get('shift_plex', '[1]'), ensure_ascii=False)
        else:
            workcenter_group = ''
            workcenter_event_group = ''
            shift_group = ''

        code = json.dumps(received_data.get('m_event', ''), ensure_ascii=False) if isinstance(received_data.get('m_event', ''), list) else ''

        # AJUSTE DE FUSO HORÁRIO DO PLEX
        # ALTERAÇÃO FEITA PARA TESTE DO AJUSTE DA HORA NO DJ.
        # COMO O PLEX ESTÁ +1 HORA EM RELAÇÃO À TELA:
        # 1) SOMA +1 HORA NO FILTRO ENVIADO PARA O PLEX.
        # 2) DEPOIS SUBTRAI -1 HORA NO RESULTADO RETORNADO.
        plex_start_date = (
            pd.to_datetime(received_data['start_date']) + pd.Timedelta(hours=1)
        ).strftime('%Y-%m-%d %H:%M:%S')

        plex_end_date = (
            pd.to_datetime(received_data['end_date']) + pd.Timedelta(hours=1)
        ).strftime('%Y-%m-%d %H:%M:%S')

        query = f"""EXEC('sproc329396_18311230_1268435(?, ?, ?, ?, ?, ?, ?)'
                        , '{plex_start_date}'
                        , '{plex_end_date}'
                        , '{workcenter_filter}'
                        , '{workcenter_group}'
                        , '{workcenter_event_group}'
                        , '{shift_group}'
                        , '{code}'
                    ) AT [PLEX_DSN_JOST]"""

        event = engine_run_query(query, 'plex')

        # AJUSTE DE FUSO HORÁRIO DO RESULTADO DO PLEX
        # ATUALMENTE CONFIGURADO PARA -1 HORA.
        if not event.empty:
            event['Log_Date'] = pd.to_datetime(event['Log_Date'], format='%d/%m/%Y %H:%M:%S') - pd.Timedelta(hours=1)
            event['End_Date'] = pd.to_datetime(event['End_Date'], format='%d/%m/%Y %H:%M:%S') - pd.Timedelta(hours=1)

            event['Log_Date'] = event['Log_Date'].dt.strftime('%d/%m/%Y %H:%M:%S')
            event['End_Date'] = event['End_Date'].dt.strftime('%d/%m/%Y %H:%M:%S')

    def format_tuple(data):
        return f"('{data[0]}')" if len(data) == 1 else tuple(data)
    
    if "Extra" in received_data["shift"]:
        received_data["shift"].pop()
        received_data["shift"].append('12')
        received_data["shift"].append('13')
        received_data["shift"].append('-1')

    filters = [
        f"T1.nShift IN {format_tuple(received_data['shift'])}" if received_data['shift'] else "T1.nShift = -2",
        f"T2.GRUPO IN {format_tuple(received_data['w_group'])}" if received_data['w_group'] else "T2.GRUPO = 'aaa'",
        f"T3.CATEGORIA IN {format_tuple(received_data['m_group'])}" if received_data['m_group'] else "T3.CATEGORIA = 'aaa'"
    ] if received_data.get('w_group') else []

    if received_data.get('m_event') and not use_status_reason_time:
        filters.append(f"T3.COD_PARADA IN {format_tuple(received_data['m_event'])}")

    conditions = []
    if received_data.get('w_name_mic'):
        conditions.append(f"T1.sDescription IN {format_tuple(received_data['w_name_mic'])}")

    if received_data.get('w_name_plex'):
        conditions.append(f"T2.CT_PLEX IN {format_tuple(received_data['w_name_plex'])}")

    workcenter_condition = f"({ ' OR '.join(conditions) })" if conditions else "(1=1)"

    filter_string = "AND " + " AND ".join(filters) if filters else ""
    mic_event_description = ", T3.DESC_PARADA AS Event" if use_status_reason_time else ""

    query = f"""
        SELECT
            T1.lOEEEventId AS Log_Key
            , T2.CT_PLEX AS Workcenter_Key
            , T1.sDescription AS Workcenter_Name
            , T2.GRUPO AS Workcenter_Group
            , FORMAT(T1.tStart, 'dd/MM/yyyy HH:mm:ss') AS Log_Date
            , FORMAT(T1.tEnd, 'dd/MM/yyyy HH:mm:ss') AS End_Date
            , ROUND(T1.lSeconds / 60.0, 2) AS Log_Minutes
            , T3.COD_PARADA AS Code
            , T3.CATEGORIA AS Status
            {mic_event_description}
            , CASE 
                WHEN T1.nShift = 1 THEN 'Primeiro'
                WHEN T1.nShift = 2 THEN 'Segundo'
                WHEN T1.nShift = 3 THEN 'Terceiro'
                ELSE NULL
            END AS Shift
            , 0 AS Plex 

        FROM
            OEEQEventHistory AS T1
        JOIN (
            SELECT CT_PLEX, NOME_MAQUINA, GRUPO, CT_PLEX_DATA, CT_PLEX_NAME, FL_ATIVO
            FROM CONFIG_TABLET
        ) AS T2 ON T1.sDescription = T2.NOME_MAQUINA
        JOIN (
            SELECT DESC_PARADA, MOTIVO, CATEGORIA, COD_PARADA 
            FROM CADASTRO_PARADA
            UNION ALL
            SELECT 'Sem Justificativa', 'Sem Justificativa', 'Sem Categoria', 0
        ) AS T3 ON LTRIM(T1.sEndVal) = T3.MOTIVO

        WHERE 
            T1.tStart BETWEEN 
            '{received_data['start_date']}' 
            AND CASE 
                WHEN T2.CT_PLEX_DATA < '{received_data['end_date']}'
                THEN T2.CT_PLEX_DATA 
                ELSE '{received_data['end_date']}'
            END 
            
            AND {workcenter_condition}
            {filter_string}
    """

    mic_event = engine_run_query(query, 'ftm')

    if use_status_reason_time and received_data.get('m_event'):
        mic_event = mic_event[mic_event['Event'].isin(received_data['m_event'])]

    data = pd.concat([event, mic_event])
    data['Code'] = data['Code'].astype(str)

    if use_status_reason_time:
        return data

    data = pd.merge(left=data, right=events_join, left_on='Code', right_on='Code').drop(columns=['Workcenter_Event_Key', 'Workcenter_Event_Group', 'Active']).rename(columns={"Description": "Event"})

    return data
