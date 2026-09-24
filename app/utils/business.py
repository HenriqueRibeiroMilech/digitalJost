import json

import pandas as pd
from sqlalchemy.exc import DBAPIError

from app.utils.dynamic_constants import getPlex
from app.utils.db_utils import engine_run_query, get_engine


_APPROVED_STOP_MATCH_TOLERANCE = pd.Timedelta(minutes=1)


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


def _normalize_identifier(value):
    if pd.isna(value):
        return None

    value = str(value).strip()
    if value.endswith('.0') and value[:-2].isdigit():
        return value[:-2]

    return value


def _normalize_stop_description(value):
    if pd.isna(value):
        return ''

    return ' '.join(str(value).strip().casefold().split())


def _normalize_stop_status(value):
    if value in ('Manutenção Parada', 'Manutenção Produtiva'):
        return 'Manutenção'

    return value


def _get_stop_event_catalog():
    events_by_key = {}
    events_by_code = {}

    for row in getPlex('events')[[
        'Workcenter_Event_Key', 'Code', 'Description',
        'Workcenter_Event_Group'
    ]].itertuples(index=False):
        event = {
            'description': row.Description,
            'status': _normalize_stop_status(row.Workcenter_Event_Group)
        }
        events_by_key[_normalize_identifier(row.Workcenter_Event_Key)] = event
        events_by_code.setdefault(
            _normalize_identifier(row.Code), []
        ).append(event)

    unique_events_by_code = {
        code: code_events[0]
        for code, code_events in events_by_code.items()
        if len(code_events) == 1
    }
    return events_by_key, unique_events_by_code


def _get_stop_event(events_by_key, events_by_code, code, event_key):
    normalized_event_key = _normalize_identifier(event_key)
    if normalized_event_key is not None:
        return events_by_key.get(normalized_event_key)

    return events_by_code.get(_normalize_identifier(code))


def _apply_approved_stop_changes(event, workcenters, received_data):
    """Sobrepõe no relatório as revisões Plex concluídas pelo Digital JOST."""
    if event.empty:
        return event.drop(columns=['Source_Log_Date'], errors='ignore')

    query = """
        SELECT
            T1.requestId
            , T1.motive1
            , T1.motive2
            , T1.motive1EventKey
            , T1.motive2EventKey
            , T1.finalDate
            , T2.workcenter AS Workcenter_Key
            , T2.startDate
            , T2.endDate
        FROM JDT_REQUEST_STOPCHANGES T1
        JOIN JDT_REQUEST_STOPCHANGES_PLEX T2
            ON T2.eventId = T1.eventId
        WHERE T1.plex = 1
            AND T1.approverStatus1 = 1
            AND T1.approverStatus2 = 1
            AND T1.finalDate IS NOT NULL
            AND T1.deniedText IS NULL
            AND T2.startDate < :end_date
            AND T2.endDate > :start_date
        ORDER BY T1.finalDate, T1.requestId
    """
    params = {
        'start_date': received_data['start_date'],
        'end_date': received_data['end_date']
    }
    approved_changes = _run_query_with_deadlock_retry(query, 'jdt', params)

    if approved_changes.empty:
        return event.drop(columns=['Source_Log_Date'], errors='ignore')

    workcenter_codes = {
        _normalize_identifier(row.Workcenter_Key): str(row.Workcenter_Code)
        for row in workcenters[['Workcenter_Key', 'Workcenter_Code']].itertuples(index=False)
    }

    events_by_key, events_by_code = _get_stop_event_catalog()

    event = event.copy()
    event['_Source_Log_Date'] = pd.to_datetime(event['Source_Log_Date'])
    event['_End_Date'] = pd.to_datetime(event['End_Date'])
    event['_Normalized_Event'] = event['Event'].apply(_normalize_stop_description)

    for change in approved_changes.itertuples(index=False):
        old_event = _get_stop_event(
            events_by_key,
            events_by_code,
            change.motive1,
            change.motive1EventKey
        )
        new_event = _get_stop_event(
            events_by_key,
            events_by_code,
            change.motive2,
            change.motive2EventKey
        )
        workcenter_code = workcenter_codes.get(
            _normalize_identifier(change.Workcenter_Key)
        )

        if not old_event or not new_event or not workcenter_code:
            continue

        change_start = pd.to_datetime(change.startDate)
        change_end = pd.to_datetime(change.endDate)
        if pd.isna(change_start) or pd.isna(change_end):
            continue

        candidates = event[
            (event['Workcenter_Code'].astype(str) == workcenter_code)
            & (
                event['_Normalized_Event']
                == _normalize_stop_description(old_event['description'])
            )
            & (
                (event['_Source_Log_Date'] - change_start).abs()
                <= _APPROVED_STOP_MATCH_TOLERANCE
            )
            & (
                event['_End_Date']
                >= change_start - _APPROVED_STOP_MATCH_TOLERANCE
            )
            & (
                event['_Source_Log_Date']
                <= change_end + _APPROVED_STOP_MATCH_TOLERANCE
            )
        ]

        if candidates.empty:
            continue

        offsets = (candidates['_Source_Log_Date'] - change_start).abs()
        closest_candidates = offsets[offsets == offsets.min()]
        if len(closest_candidates) != 1:
            continue

        event_index = closest_candidates.index[0]
        event.at[event_index, 'Code'] = _normalize_identifier(change.motive2)
        event.at[event_index, 'Event'] = new_event['description']
        event.at[event_index, 'Status'] = new_event['status']
        event.at[event_index, '_Normalized_Event'] = _normalize_stop_description(
            new_event['description']
        )

    return event.drop(
        columns=[
            'Source_Log_Date', '_Source_Log_Date', '_End_Date',
            '_Normalized_Event'
        ],
        errors='ignore'
    )


def _apply_approved_stop_changes_by_event_id(event, received_data):
    """Sobrepõe revisões Plex quando a fonte preserva o Log_Key original."""
    if event.empty:
        return event

    query = """
        SELECT
            T1.eventId
            , T1.motive2
            , T1.motive2EventKey
        FROM JDT_REQUEST_STOPCHANGES T1
        JOIN JDT_REQUEST_STOPCHANGES_PLEX T2
            ON T2.eventId = T1.eventId
        WHERE T1.plex = 1
            AND T1.approverStatus1 = 1
            AND T1.approverStatus2 = 1
            AND T1.finalDate IS NOT NULL
            AND T1.deniedText IS NULL
            AND T2.startDate < :end_date
            AND T2.endDate > :start_date
        ORDER BY T1.finalDate, T1.requestId
    """
    approved_changes = _run_query_with_deadlock_retry(
        query,
        'jdt',
        {
            'start_date': received_data['start_date'],
            'end_date': received_data['end_date']
        }
    )

    if approved_changes.empty:
        return event

    events_by_key, events_by_code = _get_stop_event_catalog()

    event = event.copy()
    normalized_log_keys = event['Log_Key'].apply(_normalize_identifier)
    plex_rows = pd.to_numeric(event['Plex'], errors='coerce').eq(1)

    for change in approved_changes.itertuples(index=False):
        new_event = _get_stop_event(
            events_by_key,
            events_by_code,
            change.motive2,
            change.motive2EventKey
        )
        if not new_event:
            continue

        matching_rows = (
            plex_rows
            & (normalized_log_keys == _normalize_identifier(change.eventId))
        )
        if not matching_rows.any():
            continue

        event.loc[matching_rows, 'Code'] = _normalize_identifier(change.motive2)
        event.loc[matching_rows, 'Event'] = new_event['description']
        event.loc[matching_rows, 'Status'] = new_event['status']

    return event


def _get_current_status_stops(received_data):
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

    params = {
        'start_date': received_data['start_date'],
        'end_date': received_data['end_date'],
        'workcenter_list': ','.join(target_workcenters)
    }
    selected_shifts = {
        '1': 'Turno 1',
        '2': 'Turno 2',
        '3': 'Turno 3',
        'Extra': 'Extra'
    }
    shift_values = [
        selected_shifts[shift]
        for shift in received_data.get('shift', [])
        if shift in selected_shifts
    ]
    params['shift_list'] = ','.join(shift_values) or None

    query = """
        EXEC [JOST_INTEGRATION_PRD].[dbo].[TD_OEE_ObterParadas]
            @data_inicio = :start_date,
            @data_fim = :end_date,
            @workcenter_list = :workcenter_list,
            @shift_list = :shift_list
    """

    event = _run_query_with_deadlock_retry(query, 'plex', params)
    event = event.rename(columns={
        'id': 'Log_Key',
        'workcenter': 'Workcenter_Code',
        'status': 'Status',
        'motivo': 'Event',
        'data_inicio': 'Source_Log_Date',
        'data_fim': 'Source_End_Date',
        'turno': 'Shift',
        'minutos_parados': 'Log_Minutes'
    })

    start_date = pd.to_datetime(received_data['start_date'])
    end_date = pd.to_datetime(received_data['end_date'])
    now = pd.Timestamp.now()

    event['Source_Log_Date'] = pd.to_datetime(event['Source_Log_Date'])
    event['Source_End_Date'] = pd.to_datetime(event['Source_End_Date'])
    event['Log_Date'] = event['Source_Log_Date'].clip(lower=start_date)
    event['End_Date'] = event['Source_End_Date'].fillna(min(now, end_date))
    event['End_Date'] = event['End_Date'].clip(upper=end_date)

    event['Event'] = (
        event['Event']
        .fillna('')
        .astype(str)
        .str.strip()
        .replace('', 'Sem Justificativa')
    )
    event['Status'] = (
        event['Status']
        .fillna('')
        .astype(str)
        .str.strip()
        .replace('', 'Sem Categoria')
        .apply(_normalize_stop_status)
    )
    event['Shift'] = event['Shift'].replace({
        'Turno 1': 'Primeiro',
        'Turno 2': 'Segundo',
        'Turno 3': 'Terceiro'
    })

    event['Code'] = ''
    event['Plex'] = 1
    event = _apply_approved_stop_changes(event, workcenters, received_data)

    if received_data.get('m_group'):
        event = event[event['Status'].isin(received_data['m_group'])]

    if received_data.get('m_event'):
        event = event[event['Event'].isin(received_data['m_event'])]

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


def getStopsData(
    received_data,
    use_current_status=False,
    apply_approved_changes=False
):
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
            use_current_status: usa Mach_2_Current_Status no lugar da procedure legada
            apply_approved_changes: sobrepõe alterações aprovadas pelo Log_Key original

        LÓGICAS DE NEGOCIO: 
        1. Caso não seja enviado w_group. Os opcionais w_group, m_group e shift_plex ficarão vazios.

    """

    shift_filter = {"1": 'primeiro', "2": 'segundo', "3": 'terceiro', 'Extra': None}
    received_data["shift_plex"] = [shift_filter[shift] for shift in received_data["shift"] if shift_filter[shift] is not None]

    if use_current_status:
        event = _get_current_status_stops(received_data)
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
            workcenter_event_group = (
                ''
                if apply_approved_changes
                else json.dumps(received_data.get('m_group', '[1]'), ensure_ascii=False)
            )
            shift_group = json.dumps(received_data.get('shift_plex', '[1]'), ensure_ascii=False)
        else:
            workcenter_group = ''
            workcenter_event_group = ''
            shift_group = ''

        code = ''
        if not apply_approved_changes and isinstance(received_data.get('m_event', ''), list):
            code = json.dumps(received_data.get('m_event', ''), ensure_ascii=False)

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

    if received_data.get('m_event') and not use_current_status and not apply_approved_changes:
        filters.append(f"T3.COD_PARADA IN {format_tuple(received_data['m_event'])}")

    conditions = []
    if received_data.get('w_name_mic'):
        conditions.append(f"T1.sDescription IN {format_tuple(received_data['w_name_mic'])}")

    if received_data.get('w_name_plex'):
        conditions.append(f"T2.CT_PLEX IN {format_tuple(received_data['w_name_plex'])}")

    workcenter_condition = f"({ ' OR '.join(conditions) })" if conditions else "(1=1)"

    filter_string = "AND " + " AND ".join(filters) if filters else ""
    mic_event_description = ", T3.DESC_PARADA AS Event" if use_current_status else ""

    mic_period_end = f"""CASE
        WHEN T2.CT_PLEX_DATA < '{received_data['end_date']}'
        THEN T2.CT_PLEX_DATA
        ELSE '{received_data['end_date']}'
    END"""

    if use_current_status:
        mic_log_start = f"""CASE
            WHEN T1.tStart < '{received_data['start_date']}'
            THEN CAST('{received_data['start_date']}' AS DATETIME)
            ELSE T1.tStart
        END"""
        mic_log_end = f"""CASE
            WHEN T1.tEnd > {mic_period_end}
            THEN {mic_period_end}
            ELSE T1.tEnd
        END"""
        mic_log_minutes = (
            f"ROUND(DATEDIFF(SECOND, {mic_log_start}, {mic_log_end}) / 60.0, 2)"
        )
        mic_period_filter = f"""
            {mic_period_end} > '{received_data['start_date']}'
            AND T1.tStart < {mic_period_end}
            AND T1.tEnd > '{received_data['start_date']}'
        """
    else:
        mic_log_start = "T1.tStart"
        mic_log_end = "T1.tEnd"
        mic_log_minutes = "ROUND(T1.lSeconds / 60.0, 2)"
        mic_period_filter = f"""
            T1.tStart BETWEEN
            '{received_data['start_date']}'
            AND {mic_period_end}
        """

    query = f"""
        SELECT
            T1.lOEEEventId AS Log_Key
            , T2.CT_PLEX AS Workcenter_Key
            , T1.sDescription AS Workcenter_Name
            , T2.GRUPO AS Workcenter_Group
            , FORMAT({mic_log_start}, 'dd/MM/yyyy HH:mm:ss') AS Log_Date
            , FORMAT({mic_log_end}, 'dd/MM/yyyy HH:mm:ss') AS End_Date
            , {mic_log_minutes} AS Log_Minutes
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
            {mic_period_filter}

            AND {workcenter_condition}
            {filter_string}
    """

    mic_event = engine_run_query(query, 'ftm')

    if use_current_status and received_data.get('m_event'):
        mic_event = mic_event[mic_event['Event'].isin(received_data['m_event'])]

    data = pd.concat([event, mic_event])
    data['Code'] = data['Code'].astype(str)

    if use_current_status:
        return data

    data = pd.merge(left=data, right=events_join, left_on='Code', right_on='Code').drop(columns=['Workcenter_Event_Key', 'Workcenter_Event_Group', 'Active']).rename(columns={"Description": "Event"})

    if apply_approved_changes:
        data = _apply_approved_stop_changes_by_event_id(data, received_data)

        if received_data.get('m_group'):
            data = data[data['Status'].isin(received_data['m_group'])]

        if received_data.get('m_event'):
            selected_codes = {
                _normalize_identifier(code)
                for code in received_data['m_event']
            }
            data = data[
                data['Code'].apply(_normalize_identifier).isin(selected_codes)
            ]

    return data

# V3
