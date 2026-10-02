from datetime import datetime, timedelta
from requests.auth import HTTPBasicAuth

import pandas as pd

from flask_mail import Message
from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import text

from app.utils.business import getStopsData, get_stops_workcenters
from app.utils.constants import MES_MAIN_PASSWORD, MES_MAIN_USER
from app.utils.data_utils import POST_WITH_AUTH
from app.utils.db_utils import engine_run_query, get_engine
from app.config import mail
from app.utils.dynamic_constants import getPlex
from app.utils.permissions import get_permission
from sqlalchemy.exc import IntegrityError

_PROBLEM_CATEGORY = pd.DataFrame([
                                {"areaId": 8, "Code": 2}
                                , {"areaId": 12, "Code": 3}
                                , {"areaId": 12, "Code": 4}
                                , {"areaId": 8, "Code": 5}
                                , {"areaId": 8, "Code": 6}
                                , {"areaId": 8,   "Code": 7}
                                , {"areaId": 13,  "Code": 8}
                                , {"areaId": 13,  "Code": 9}
                                , {"areaId": 13,  "Code": 10}
                                , {"areaId": 13,  "Code": 11}
                                , {"areaId": 8,   "Code": 12}
                                , {"areaId": 2,   "Code": 13}
                                , {"areaId": 8,   "Code": 14}
                                , {"areaId": 8,   "Code": 15}
                                , {"areaId": 13,  "Code": 16}
                                , {"areaId": 13,  "Code": 18}
                                , {"areaId": 12,  "Code": 19}
                                , {"areaId": 2,   "Code": 20}
                                , {"areaId": 13,  "Code": 22}
                                , {"areaId": 2,   "Code": 31}
                                , {"areaId": 2,   "Code": 32}
                                , {"areaId": 13,  "Code": 35}
                                , {"areaId": 2,   "Code": 37}
                                , {"areaId": 12,  "Code": 42}
                                , {"areaId": 2,   "Code": 43}
                                , {"areaId": 2,   "Code": 44}
                                , {"areaId": 13,  "Code": 45}
                                , {"areaId": 13,  "Code": 46}
                                , {"areaId": 3,   "Code": 50}
                                , {"areaId": 3,   "Code": 51}
                                , {"areaId": 3,   "Code": 52}
                                , {"areaId": 3,   "Code": 53}
                                , {"areaId": 3,   "Code": 54}
                                , {"areaId": 8,   "Code": 55}
                                , {"areaId": 13,  "Code": 56}
                                , {"areaId": 13,  "Code": 58}
                                , {"areaId": 8,   "Code": 59}
                                , {"areaId": 8,   "Code": 60}
                                , {"areaId": 13,  "Code": 61}
                                , {"areaId": 3,   "Code": 62}
                                , {"areaId": 12,  "Code": 65}
                                , {"areaId": 13,  "Code": 66}
                                , {"areaId": 2,   "Code": 100}
                            ])

_USER_FILTERS = {}

_TRANSFORMATION_DIGITAL_AREA_NAME = 'Transformação Digital'
_TRANSFORMATION_DIGITAL_PRIMARY_SHIFT = 0
_TRANSFORMATION_DIGITAL_SECONDARY_SHIFT = 99
# Sistema Indisponível também é responsabilidade da Transformação Digital.
_TRANSFORMATION_DIGITAL_MOTIVE_CODES = {44}
_CURRENT_STATUS_MATCH_TOLERANCE = timedelta(minutes=1)


class _CurrentStatusMatchError(Exception):
    pass


def _current_user_is_admin():
    admin_value = str(getattr(current_user, 'admin', '')).strip().lower()
    return admin_value in {'1', 'true', 'yes'} or get_permission('SYSADMIN').can()


def _normalize_catalog_id(value):
    if pd.isna(value):
        return None

    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value).strip()


def _normalize_stop_reason(value):
    if pd.isna(value):
        return ''
    return ' '.join(str(value).strip().casefold().split())


def _normalize_stop_group(value):
    group = _normalize_stop_reason(value)
    return 'manutenção' if group in {
        'manutenção parada', 'manutenção produtiva'
    } else group


def _get_plex_event(events, code=None, event_key=None):
    normalized_event_key = _normalize_catalog_id(event_key)
    if normalized_event_key is not None:
        matching_events = events[
            events['Workcenter_Event_Key']
            .apply(_normalize_catalog_id)
            .eq(normalized_event_key)
        ]
    else:
        normalized_code = _normalize_catalog_id(code)
        matching_events = events[
            events['Code'].apply(_normalize_catalog_id).eq(normalized_code)
        ]

    if len(matching_events) != 1:
        raise _CurrentStatusMatchError(
            'MOTIVO DA PARADA NAO FOI IDENTIFICADO DE FORMA UNICA.'
        )

    return matching_events.iloc[0]


def _is_transformation_digital_motive(
    code,
    events,
    event_key=None,
    assigned_approver=None,
    transformation_digital_approvers=None
):
    code = int(code)
    if code in _TRANSFORMATION_DIGITAL_MOTIVE_CODES:
        return True

    try:
        event = _get_plex_event(events, code, event_key)
    except _CurrentStatusMatchError:
        return (
            transformation_digital_approvers is not None
            and str(assigned_approver) in transformation_digital_approvers
        )

    return str(event['Workcenter_Event_Group']).strip() == 'Programada'


def _get_transformation_digital_approvers():
    approvers = engine_run_query(
        """
            SELECT DISTINCT T1.userId
            FROM JDT_USER_STOPCHANGES AS T1
            JOIN JDT_GENERAL_AREA AS T2 ON T2.areaId = T1.areaId
            WHERE T2.name = :area_name
        """,
        'jdt',
        {'area_name': _TRANSFORMATION_DIGITAL_AREA_NAME}
    )

    if approvers.empty:
        return set()

    return set(approvers['userId'].dropna().astype(str))


def _get_problem_area_id(
    code,
    events,
    transformation_digital_area_id,
    event_key=None
):
    code = int(code)

    if _is_transformation_digital_motive(code, events, event_key):
        return transformation_digital_area_id

    problem_area = _PROBLEM_CATEGORY[_PROBLEM_CATEGORY['Code'] == code]
    if problem_area.empty:
        return None

    return int(problem_area.iloc[0]['areaId'])


def _get_area_approver(
    approvers,
    area_id,
    shift,
    transformation_digital_area_id
):
    area_approvers = approvers[approvers['areaId'] == area_id]

    if area_id == transformation_digital_area_id:
        return area_approvers[
            area_approvers['shift'].astype(str)
            == str(_TRANSFORMATION_DIGITAL_PRIMARY_SHIFT)
        ].head(1)

    if len(area_approvers) > 1:
        area_approvers = area_approvers[
            area_approvers['shift'].astype(str) == str(shift)
        ]

    return area_approvers


def _add_motive_descriptions(table, events):
    table = table.copy()
    event_by_key = {
        _normalize_catalog_id(row.Workcenter_Event_Key): row.Description
        for row in events[['Workcenter_Event_Key', 'Description']]
        .itertuples(index=False)
    }
    descriptions_by_code = {}
    for row in events[['Code', 'Description']].itertuples(index=False):
        if pd.isna(row.Description):
            continue
        code = _normalize_catalog_id(row.Code)
        descriptions_by_code.setdefault(code, set()).add(str(row.Description))
    descriptions_by_code = {
        code: next(iter(descriptions))
        for code, descriptions in descriptions_by_code.items()
        if len(descriptions) == 1
    }

    def get_description(row, code_column, event_key_column):
        event_key = _normalize_catalog_id(row.get(event_key_column))
        if event_key is not None and event_key in event_by_key:
            return event_by_key[event_key]

        code = _normalize_catalog_id(row.get(code_column))
        return descriptions_by_code.get(
            code,
            'Motivo com código duplicado; identificação pendente'
        )

    table['motiveDesc1'] = table.apply(
        get_description,
        axis=1,
        args=('motive1', 'motive1EventKey')
    )
    table['motiveDesc2'] = table.apply(
        get_description,
        axis=1,
        args=('motive2', 'motive2EventKey')
    )
    if {'stopSource', 'currentStatusReason'}.issubset(table.columns):
        td_rows = table['stopSource'].eq('td')
        table.loc[td_rows, 'motiveDesc1'] = table.loc[
            td_rows, 'currentStatusReason'
        ]
    return table


def _find_current_status_stop(check_request, events):
    workcenters = getPlex('workcenters')
    workcenter_key = pd.to_numeric(
        pd.Series([check_request['workcenter']]),
        errors='coerce'
    ).iloc[0]
    matching_workcenters = workcenters[
        pd.to_numeric(workcenters['Workcenter_Key'], errors='coerce')
        .eq(workcenter_key)
    ]

    if matching_workcenters.empty:
        raise _CurrentStatusMatchError(
            'CENTRO DE TRABALHO NAO ENCONTRADO PARA A PARADA DO PLEX.'
        )

    old_motive = _get_plex_event(
        events,
        check_request['motive1'],
        check_request.get('motive1EventKey')
    )
    new_motive = _get_plex_event(
        events,
        check_request['motive2'],
        check_request.get('motive2EventKey')
    )
    start_date = pd.to_datetime(check_request['startDate'])
    end_date = pd.to_datetime(check_request['endDate'])

    if pd.isna(start_date) or pd.isna(end_date):
        raise _CurrentStatusMatchError(
            'PERIODO DA PARADA DO PLEX NAO FOI ENCONTRADO.'
        )

    query = """
        SELECT
            ID
            , ABS(
                DATEDIFF_BIG(MILLISECOND, :start_date, StatusBegin)
            ) AS StartDifference
        FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_Current_Status]
        WHERE Workcenter = :workcenter
            AND CanRunProduction = 0
            AND StatusBegin >= :minimum_start
            AND StatusBegin <= :maximum_start
            AND COALESCE(StatusEnd, GETDATE()) > :start_date
            AND StatusBegin < :end_date
            AND LTRIM(RTRIM(COALESCE(WcReason, ''))) IN (
                :old_reason,
                :new_reason
            )
        ORDER BY StartDifference, ID
    """
    params = {
        'workcenter': str(matching_workcenters.iloc[0]['Workcenter_Code']),
        'start_date': start_date.to_pydatetime(),
        'end_date': end_date.to_pydatetime(),
        'minimum_start': (
            start_date - _CURRENT_STATUS_MATCH_TOLERANCE
        ).to_pydatetime(),
        'maximum_start': (
            start_date + _CURRENT_STATUS_MATCH_TOLERANCE
        ).to_pydatetime(),
        'old_reason': str(old_motive['Description']).strip(),
        'new_reason': str(new_motive['Description']).strip()
    }
    candidates = engine_run_query(query, 'plex', params)

    if candidates.empty:
        raise _CurrentStatusMatchError(
            'PARADA CORRESPONDENTE NAO ENCONTRADA NO CURRENT STATUS.'
        )

    closest_difference = candidates['StartDifference'].min()
    closest_candidates = candidates[
        candidates['StartDifference'] == closest_difference
    ]
    if len(closest_candidates) != 1:
        raise _CurrentStatusMatchError(
            'MAIS DE UMA PARADA CORRESPONDENTE FOI ENCONTRADA NO CURRENT STATUS.'
        )

    return int(closest_candidates.iloc[0]['ID']), new_motive


def _update_current_status_stop(current_status_id, new_motive, expected_status=None):
    new_status = str(new_motive['Workcenter_Event_Group']).strip()
    if new_status in {'Manutenção Parada', 'Manutenção Produtiva'}:
        new_status = 'Manutenção'

    is_planned_stop = new_status == 'Programada'
    query = """
        UPDATE [JOST_INTEGRATION_PRD].[dbo].[Mach_2_Current_Status]
        SET WcStatus = :status,
            WcReason = :reason,
            CanRunProduction = 0,
            ProductionStatus = 0,
            DowntimeStatus = :downtime_status,
            PlannedProductionTime = :planned_production_time
        WHERE ID = :current_status_id
    """
    params = {
        'status': new_status,
        'reason': str(new_motive['Description']).strip(),
        'downtime_status': 0 if is_planned_stop else 1,
        'planned_production_time': 0 if is_planned_stop else 1,
        'current_status_id': current_status_id
    }
    if expected_status is not None:
        query += """
            AND Workcenter = :expected_workcenter
            AND StatusBegin = :expected_start
            AND LTRIM(RTRIM(COALESCE(WcReason, ''))) = :expected_reason
            AND CanRunProduction = 0
        """
        params.update({
            'expected_workcenter': expected_status['currentStatusWorkcenter'],
            'expected_start': expected_status['currentStatusStart'],
            'expected_reason': str(expected_status['currentStatusReason']).strip()
        })

    engine = get_engine('plex')
    with engine.begin() as cnnx:
        result = cnnx.execute(text(query), params)
        if result.rowcount != 1:
            raise _CurrentStatusMatchError(
                'NAO FOI POSSIVEL ATUALIZAR A PARADA NO CURRENT STATUS.'
            )


def _get_current_status_event(event_id):
    rows = engine_run_query("""
        SELECT ID, Workcenter, StatusBegin, StatusEnd, WcReason, WcStatus,
               CurrentShift
        FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_Current_Status]
        WHERE ID = :event_id AND CanRunProduction = 0
    """, 'plex', {'event_id': event_id})
    if len(rows) != 1:
        raise _CurrentStatusMatchError('PARADA NAO ENCONTRADA NO CURRENT STATUS.')
    return rows.iloc[0]


def _get_current_status_motive(status_row, events):
    reason = _normalize_stop_reason(status_row['WcReason'])
    status = _normalize_stop_group(status_row['WcStatus'])
    matching = events[
        events['Description'].apply(_normalize_stop_reason) == reason
    ]
    if status:
        matching = matching[
            matching['Workcenter_Event_Group'].apply(_normalize_stop_group)
            == status
        ]
    if len(matching) != 1:
        raise _CurrentStatusMatchError(
            'MOTIVO ATUAL DO CURRENT STATUS NAO FOI IDENTIFICADO DE FORMA UNICA.'
        )
    return matching.iloc[0]


def _get_matching_plex_log(status_row, events):
    workcenters = getPlex('workcenters')
    matching_workcenters = workcenters[
        workcenters['Workcenter_Code'].astype(str).str.strip()
        == str(status_row['Workcenter']).strip()
    ]
    if matching_workcenters.empty:
        return None
    if len(matching_workcenters) != 1:
        raise _CurrentStatusMatchError(
            'CENTRO DE TRABALHO NAO FOI IDENTIFICADO DE FORMA UNICA NO PLEX.'
        )

    plex_start = pd.to_datetime(status_row['StatusBegin']) + timedelta(hours=1)
    rows = engine_run_query("""
        DECLARE @workcenter_key BIGINT = :workcenter_key;
        DECLARE @minimum_start DATETIME = :minimum_start;
        DECLARE @maximum_start DATETIME = :maximum_start;
        EXEC('
            SELECT Log_Key, Workcenter_Key, Log_Date, Log_Hours,
                   Workcenter_Event_Key
            FROM Part_v_Workcenter_Log
            WHERE Workcenter_Key = ?
              AND Log_Date BETWEEN ? AND ?
        ', @workcenter_key, @minimum_start, @maximum_start) AT [PLEX_DSN_JOST]
    """, 'plex', {
        'workcenter_key': int(matching_workcenters.iloc[0]['Workcenter_Key']),
        'minimum_start': (
            plex_start - _CURRENT_STATUS_MATCH_TOLERANCE
        ).to_pydatetime(),
        'maximum_start': (
            plex_start + _CURRENT_STATUS_MATCH_TOLERANCE
        ).to_pydatetime()
    })
    if rows.empty:
        return None

    reason = _normalize_stop_reason(status_row['WcReason'])
    event_descriptions = {
        _normalize_catalog_id(row.Workcenter_Event_Key):
            _normalize_stop_reason(row.Description)
        for row in events[['Workcenter_Event_Key', 'Description']]
        .itertuples(index=False)
    }
    matching = rows[
        rows['Workcenter_Event_Key'].apply(_normalize_catalog_id)
        .map(event_descriptions).eq(reason)
    ]
    if len(matching) != 1:
        raise _CurrentStatusMatchError(
            'REGISTRO PLEX CORRESPONDENTE NAO FOI IDENTIFICADO DE FORMA UNICA.'
        )
    plex_log = matching.iloc[0]
    if pd.notna(status_row['StatusEnd']):
        status_minutes = (
            pd.to_datetime(status_row['StatusEnd'])
            - pd.to_datetime(status_row['StatusBegin'])
        ).total_seconds() / 60
        plex_minutes = float(plex_log['Log_Hours']) * 60
        if abs(status_minutes - plex_minutes) > 2:
            raise _CurrentStatusMatchError(
                'DURACAO DA PARADA DIFERE DO REGISTRO PLEX CORRESPONDENTE.'
            )
    return plex_log


def _get_request_stops(payload):
    workcenters = get_stops_workcenters()
    selected_workcenter_codes = {
        str(code).strip() for code in (payload.get('w_codes') or [])
    }
    selected_plex = payload.get('w_name_plex') or []
    if selected_workcenter_codes:
        workcenters = workcenters[
            workcenters['Workcenter_Code'].isin(selected_workcenter_codes)
        ]
    elif selected_plex:
        workcenters = workcenters[
            workcenters['Workcenter_Key'].apply(_normalize_catalog_id)
            == _normalize_catalog_id(selected_plex[0])
        ]
    else:
        selected_name = (payload.get('w_name_mic') or [''])[0]
        workcenters = workcenters[
            workcenters['Workcenter_Code'].astype(str) + '-'
            + workcenters['Name'].astype(str) == selected_name
        ]
    if workcenters.empty:
        return pd.DataFrame(columns=[
            'Log_Key', 'Source', 'Log_Date', 'End_Date', 'Log_Minutes',
            'Code', 'Event', 'Workcenter_Name', 'Workcenter_Key', 'Plex'
        ])

    source_payload = {
        key: value.copy() if isinstance(value, list) else value
        for key, value in payload.items()
    }
    legacy_workcenter = (
        workcenters['Workcenter_Key'].apply(_normalize_catalog_id) == '1'
    )
    source_payload['w_codes'] = workcenters['Workcenter_Code'].tolist()
    source_payload['w_name_plex'] = workcenters.loc[
        ~legacy_workcenter, 'Workcenter_Key'
    ].tolist()
    source_payload['w_name_mic'] = (
        workcenters.loc[legacy_workcenter, 'Workcenter_Code']
        + '-'
        + workcenters.loc[legacy_workcenter, 'Name']
    ).tolist()
    source_payload['m_event'] = []

    current_payload = {
        key: value.copy() if isinstance(value, list) else value
        for key, value in source_payload.items()
    }
    current = getStopsData(
        current_payload,
        use_current_status=True,
        current_status_workcenters=workcenters
    )
    current['Source'] = current['Plex'].apply(
        lambda value: 'td' if int(value) == 1 else 'ftm'
    )

    catalog_events = getPlex('events')
    catalog_codes = {}
    for event in catalog_events[['Code', 'Description']].itertuples(index=False):
        description = _normalize_stop_reason(event.Description)
        catalog_codes.setdefault(description, set()).add(
            _normalize_catalog_id(event.Code)
        )
    unique_codes = {
        description: next(iter(codes))
        for description, codes in catalog_codes.items()
        if len(codes) == 1
    }
    td_rows = current['Source'] == 'td'
    current.loc[td_rows, 'Code'] = (
        current.loc[td_rows, 'Event'].apply(_normalize_stop_reason)
        .map(unique_codes).fillna('')
    )

    legacy_payload = {
        key: value.copy() if isinstance(value, list) else value
        for key, value in source_payload.items()
    }
    legacy = getStopsData(
        legacy_payload,
        apply_approved_changes=True,
        unique_event_codes=True
    )
    legacy = legacy[pd.to_numeric(legacy['Plex'], errors='coerce').eq(1)].copy()
    legacy['Source'] = 'plex'

    td_stops = current[td_rows]
    if not td_stops.empty and not legacy.empty:
        td_dates = pd.to_datetime(td_stops['Log_Date'], dayfirst=True)
        keep_legacy = []
        for row in legacy.itertuples(index=False):
            legacy_date = pd.to_datetime(row.Log_Date, dayfirst=True)
            matching = td_stops[
                td_stops['Workcenter_Key'].apply(_normalize_catalog_id)
                == _normalize_catalog_id(row.Workcenter_Key)
            ]
            offsets = (td_dates.loc[matching.index] - legacy_date).abs()
            keep_legacy.append(
                not offsets.le(_CURRENT_STATUS_MATCH_TOLERANCE).any()
            )
        legacy = legacy.loc[keep_legacy]

    data = pd.concat([current, legacy], ignore_index=True, sort=False)
    selected_codes = {
        _normalize_catalog_id(code) for code in (payload.get('m_event') or [])
    }
    if selected_codes:
        selected_descriptions = {
            _normalize_stop_reason(event.Description)
            for event in catalog_events[['Code', 'Description']]
            .itertuples(index=False)
            if _normalize_catalog_id(event.Code) in selected_codes
        }
        data = data[
            data['Code'].apply(_normalize_catalog_id).isin(selected_codes)
            | (
                data['Source'].eq('td')
                & data['Event'].apply(_normalize_stop_reason)
                .isin(selected_descriptions)
            )
        ]
    return data

request_workcentersLogChange_bp = Blueprint('request_workcentersLogChange', __name__)

@request_workcentersLogChange_bp.before_request
def route_auth():
    # Verifica se o usuário está autenticado
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))

    # Verifica permissão geral
    if not get_permission('GENERAL').can():
        return abort(403)


# PÁGINA DE ROTAS
@request_workcentersLogChange_bp.route('/oee/paradas/alterar', methods=['GET'])
def stopChanges_home():
    return render_template('request.stopChanges/stopChanges_main.html')


@request_workcentersLogChange_bp.route('/oee/paradas/alterar/resumo', methods=['GET'])
def stopChanges_summary():

    query = """
    SELECT 
        COALESCE(SUM(
            CASE
                WHEN finalDate IS NULL
                    AND (
                        (approver1 = :user_id AND approverStatus1 = 0)
                        OR (approver2 = :user_id AND approverStatus2 = 0)
                    )
                THEN 1
                ELSE 0
            END
        ), 0) AS s0,
        COALESCE(SUM(CASE WHEN (approver1 = :user_id AND approverStatus1 = 1) OR (approver2 = :user_id AND approverStatus2 = 1) THEN 1 ELSE 0 END), 0) AS s1,
        COALESCE(SUM(CASE WHEN (approver1 = :user_id AND approverStatus1 = 2) OR (approver2 = :user_id AND approverStatus2 = 2) THEN 1 ELSE 0 END), 0) AS s2,
        COALESCE(SUM(CASE WHEN requesterId = :user_id THEN 1 ELSE 0 END), 0) AS r0

    FROM JDT_REQUEST_STOPCHANGES
    WHERE approver1 = :user_id OR approver2 = :user_id
        OR requesterId = :user_id;
    """

    results = engine_run_query(query, 'jdt', {'user_id': str(current_user.id)})
    counts = results.iloc[0]
    return jsonify({key: int(counts[key]) for key in ('s0', 's1', 's2', 'r0')})


# MÉTODO PARA CONSULTAR AS PARADAS E SOLICITAR UMA ALTERAÇÃO DE PARADA
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/solicitar', methods=['GET', 'POST'])
def stopChanges_main():
    
    if request.method == 'POST':

        if request.args['type'] == 'search':

            payload = request.get_json()
            _USER_FILTERS[current_user.id] = payload

            payload['start_date'] = payload['start_date'].replace('T', ' ') + ':00'
            payload['end_date'] = payload['end_date'].replace('T', ' ') + ':00'

            data = _get_request_stops(payload)

            query = f"""SELECT 

                            T1.eventId
                            , CASE
                                WHEN T1.stopSource = 'td' THEN 'td'
                                WHEN T1.plex = 1 THEN 'plex'
                                ELSE 'ftm'
                              END AS Source
                            , T1.plexLogKey
                            , T2.name as approver1
                            , T3.name as approver2
                            , T1.approverStatus1
                            , T1.approverStatus2
                            , T1.motive2
                            , 1 AS requested
            
                        FROM JDT_REQUEST_STOPCHANGES T1

                        LEFT JOIN JDT_USER_DETAILS AS T2 ON T1.approver1 = T2.id
                        LEFT JOIN JDT_USER_DETAILS AS T3 ON T1.approver2 = T3.id

                        WHERE T1.finalDate IS NULL
                            AND (
                                T1.approverStatus1 = 0
                                OR T1.approverStatus2 = 0
                            )"""
            table = engine_run_query(query, 'jdt')

            linked = table[
                table['Source'].eq('td') & table['plexLogKey'].notna()
            ].copy()
            linked['Source'] = 'plex'
            linked['eventId'] = linked['plexLogKey']
            table = pd.concat([table, linked], ignore_index=True)
            table = table.drop_duplicates(subset=['Source', 'eventId'])
            data = pd.merge(
                left=data, right=table,
                left_on=['Source', 'Log_Key'], right_on=['Source', 'eventId'],
                how='left'
            )

            return data.to_json(orient='records')
        
        else:
            
            payload = request.get_json()
            source = payload.get('Source')
            if source is None:
                source = 'plex' if payload.get('Plex') else 'ftm'
            if source not in {'td', 'plex', 'ftm'}:
                return 'ORIGEM DA PARADA INVALIDA.', 400
            try:
                event_id = int(payload['Log_Key'])
                if event_id <= 0:
                    raise ValueError
            except (TypeError, ValueError, KeyError):
                return 'IDENTIFICADOR DA PARADA INVALIDO.', 400

            status_row = None
            plex_log = None
            if source == 'td':
                try:
                    status_row = _get_current_status_event(event_id)
                    events = getPlex('events')
                    plex_log = _get_matching_plex_log(status_row, events)
                    old_motive = (
                        _get_plex_event(
                            events,
                            event_key=plex_log['Workcenter_Event_Key']
                        ) if plex_log is not None
                        else _get_current_status_motive(status_row, events)
                    )
                except (TypeError, ValueError, KeyError):
                    return 'IDENTIFICADOR DA PARADA INVALIDO.', 400
                except _CurrentStatusMatchError as error:
                    return str(error), 409

                start_date = pd.to_datetime(status_row['StatusBegin'])
                end_date = pd.to_datetime(status_row['StatusEnd'])
                if pd.isna(end_date):
                    end_date = pd.Timestamp.now()
                if end_date <= start_date:
                    return 'PERIODO DA PARADA INVALIDO.', 409
                shift_name = (
                    str(status_row['CurrentShift']).strip().upper()
                    if pd.notna(status_row['CurrentShift']) else ''
                )
                shift = {
                    'PRIMEIRO': 1, 'TURNO 1': 1,
                    'SEGUNDO': 2, 'TURNO 2': 2,
                    'TERCEIRO': 3, 'TURNO 3': 3
                }.get(shift_name)
                if shift is None:
                    return 'TURNO DA PARADA NAO IDENTIFICADO.', 409
                check_request = pd.Series({
                    'Workcenter_Name': str(status_row['Workcenter']),
                    'Workcenter_Key': (
                        plex_log['Workcenter_Key'] if plex_log is not None else None
                    ),
                    'Log_Date': start_date.strftime('%d/%m/%Y %H:%M:%S'),
                    'End_Date': end_date.strftime('%d/%m/%Y %H:%M:%S'),
                    'Log_Minutes': round((end_date - start_date).total_seconds() / 60, 2),
                    'Code': old_motive['Code'],
                    'MotiveEventKey': old_motive['Workcenter_Event_Key'],
                    'Shift': shift
                })

            if source == 'plex':
                
                query = f"""

                            SELECT 

                                Workcenter_Key
                                , CONCAT(Workcenter_Code, '-', Workcenter_Name) AS Workcenter_Name
                                , FORMAT(Log_Date, 'dd/MM/yyyy HH:mm:ss') AS Log_Date
                                , FORMAT(DATEADD(MINUTE, Log_Hours * 60.0, Log_Date), 'dd/MM/yyyy HH:mm:ss') AS End_Date
                                , CAST(ROUND(Log_Hours * 60, 0) AS INT) AS Log_Minutes
                                , Code
                                , MotiveEventKey
                                , CASE Shift
                                    WHEN 'Primeiro' THEN 1
                                    WHEN 'Segundo' THEN 2
                                    WHEN 'Terceiro' THEN 3
                                END AS Shift

                            FROM OPENQUERY([PLEX_DSN_JOST], '

                                SELECT

                                    T1.Workcenter_Key
                                    , T1.Log_Date
                                    , T1.Log_Hours
                                    , T2.Name AS Workcenter_Name
                                    , T2.Workcenter_Code
                                    , T3.Code AS Code
                                    , T1.Workcenter_Event_Key AS MotiveEventKey
                                    , T5.Shift_Group AS Shift
                                    , T1.Log_Key

                                FROM

                                    Part_v_Workcenter_Log T1
                                    JOIN Part_v_Workcenter T2 ON T1.Workcenter_Key = T2.Workcenter_Key
                                    LEFT JOIN Part_v_Workcenter_Event T3 ON T1.Workcenter_Event_Key = T3.Workcenter_Event_Key
                                    JOIN Common_v_Shift T5 ON T1.Shift_Key = T5.Shift_Key

                                WHERE
                                    T1.Log_Key = {event_id}
                                ') EH
                            
                            WHERE NOT EXISTS (
                                SELECT 1 
                                FROM JDT_REQUEST_STOPCHANGES JDT 
                                WHERE (
                                    (JDT.eventId = EH.Log_Key
                                        AND (JDT.stopSource IS NULL OR JDT.stopSource = 'plex'))
                                    OR (JDT.stopSource = 'td'
                                        AND JDT.plexLogKey = EH.Log_Key)
                                )
                                    AND JDT.finalDate IS NULL
                            );
                """ 

            elif source == 'ftm':

                query = f"""

                            SELECT 
                                TRIM(sDescription) AS Workcenter_Name
                                , FORMAT(tStart, 'dd/MM/yyyy HH:mm:ss') AS Log_Date
                                , FORMAT(tEnd, 'dd/MM/yyyy HH:mm:ss') AS End_Date
                                , DATEDIFF(MINUTE, tStart, tEnd) AS Log_Minutes
                                , CAST(SUBSTRING(TRIM(sEndVal), 0, 4) AS INT) AS Code
                                , NULL AS MotiveEventKey
                                , CASE sShift
                                    WHEN 'TURNO 1' THEN 1
                                    WHEN 'TURNO 2' THEN 2
                                    WHEN 'TURNO 3' THEN 3
                                END AS Shift

                            FROM FTMETRICS_JOST.dbo.OEEQEventHistory EH
                            WHERE lOEEEventId = {event_id}
                            AND NOT EXISTS (
                                SELECT 1 
                                FROM JDT_REQUEST_STOPCHANGES JDT 
                                WHERE JDT.eventId = EH.lOEEEventId
                                    AND (JDT.stopSource IS NULL OR JDT.stopSource = 'ftm')
                                    AND JDT.finalDate IS NULL
                            );
                """
            
            engine = get_engine('jdt')
            with engine.connect() as cnnx:
                if source == 'td':
                    pending = pd.read_sql(text("""
                        SELECT TOP 1 requestId
                        FROM JDT_REQUEST_STOPCHANGES
                        WHERE finalDate IS NULL AND (
                            (stopSource = 'td' AND eventId = :event_id)
                            OR (plexLogKey = :plex_log_key AND :plex_log_key IS NOT NULL)
                            OR (
                                (stopSource IS NULL OR stopSource = 'plex')
                                AND plex = 1 AND eventId = :plex_log_key
                                AND :plex_log_key IS NOT NULL
                            )
                        )
                    """), cnnx, params={
                        'event_id': event_id,
                        'plex_log_key': (
                            int(plex_log['Log_Key']) if plex_log is not None else None
                        )
                    })
                    if not pending.empty:
                        return 'A REQUEST ALREADY EXISTS WITHIN THIS EVENT.', 403
                else:
                    check_request = pd.read_sql(query, cnnx)
                    if check_request.empty:
                        return 'A REQUEST ALREADY EXISTS WITHIN THIS EVENT.', 403
                    check_request = check_request.iloc[0]

                if source == 'plex':
                    approved_motive = pd.read_sql(
                        text("""
                            SELECT TOP 1 motive2, motive2EventKey
                            FROM JDT_REQUEST_STOPCHANGES
                            WHERE eventId = :event_id
                                AND plex = 1
                                AND (stopSource IS NULL OR stopSource = 'plex')
                                AND approverStatus1 = 1
                                AND approverStatus2 = 1
                                AND finalDate IS NOT NULL
                                AND deniedText IS NULL
                            ORDER BY finalDate DESC, requestId DESC
                        """),
                        cnnx,
                        params={"event_id": event_id}
                    )

                    if not approved_motive.empty:
                        check_request['Code'] = approved_motive.iloc[0]['motive2']
                        if pd.notna(approved_motive.iloc[0]['motive2EventKey']):
                            check_request['MotiveEventKey'] = (
                                approved_motive.iloc[0]['motive2EventKey']
                            )

                query = f"""SELECT 
                            T1.userId
                            , T1.areaId
                            , T1.shift
                            , T2.companyEmail
                        FROM 
                            JDT_USER_STOPCHANGES AS T1
                            LEFT JOIN JDT_USER_DETAILS AS T2 ON T2.id = T1.userId"""   
                approvers_info = pd.read_sql(query, cnnx)

                transformation_digital_area = pd.read_sql(
                    text("""
                        SELECT TOP 1 areaId
                        FROM JDT_GENERAL_AREA
                        WHERE name = :area_name
                    """),
                    cnnx,
                    params={"area_name": _TRANSFORMATION_DIGITAL_AREA_NAME}
                )
                transformation_digital_area_id = (
                    int(transformation_digital_area.iloc[0]['areaId'])
                    if not transformation_digital_area.empty
                    else None
                )

                events = getPlex('events')
                active_events = events[events['Active'] == 1]
                try:
                    new_motive = _get_plex_event(
                        active_events,
                        event_key=payload.get('newMotiveEventKey')
                    )
                except _CurrentStatusMatchError as error:
                    return str(error), 400

                new_motive_code = _normalize_catalog_id(new_motive['Code'])
                new_motive_event_key = int(float(
                    new_motive['Workcenter_Event_Key']
                ))
                old_motive_event_key = (
                    int(float(check_request['MotiveEventKey']))
                    if pd.notna(check_request.get('MotiveEventKey'))
                    else None
                )
                try:
                    problemAreaOld = _get_problem_area_id(
                        check_request['Code'],
                        events,
                        transformation_digital_area_id,
                        old_motive_event_key
                    )
                    problemAreaNew = _get_problem_area_id(
                        new_motive_code,
                        events,
                        transformation_digital_area_id,
                        new_motive_event_key
                    )
                except (TypeError, ValueError):
                    return 'AREA RESPONSAVEL PELO MOTIVO NAO CONFIGURADA.', 409

                if problemAreaOld is None or problemAreaNew is None:
                    return 'AREA RESPONSAVEL PELO MOTIVO NAO CONFIGURADA.', 409

                approver1 = _get_area_approver(
                    approvers_info,
                    problemAreaOld,
                    check_request['Shift'],
                    transformation_digital_area_id
                )
                approver2 = _get_area_approver(
                    approvers_info,
                    problemAreaNew,
                    check_request['Shift'],
                    transformation_digital_area_id
                )

                if approver1.empty or approver2.empty:
                    return 'APROVADOR DO MOTIVO NAO CONFIGURADO.', 409


                query = f"""SELECT COALESCE(MAX(requestId) + 1, 1) AS newId FROM JDT_REQUEST_STOPCHANGES"""
                newId = pd.read_sql(query, cnnx)['newId'][0]

                cnnx.execute(text("""
                    INSERT INTO JDT_REQUEST_STOPCHANGES (
                        requestId,
                        requesterId,
                        approver1,
                        approver2,
                        openDate,
                        finalDate,
                        approverStatus1,
                        approverStatus2,
                        approverDate1,
                        approverDate2,
                        motive1,
                        motive2,
                        plex,
                        eventId,
                        requestText,
                        deniedText,
                        motive1EventKey,
                        motive2EventKey,
                        stopSource,
                        plexLogKey,
                        currentStatusWorkcenter,
                        currentStatusStart,
                        currentStatusEnd,
                        currentStatusMinutes,
                        currentStatusReason
                    ) VALUES (
                        :request_id,
                        :requester_id,
                        :approver1,
                        :approver2,
                        GETDATE(),
                        NULL,
                        0,
                        0,
                        NULL,
                        NULL,
                        :motive1,
                        :motive2,
                        :plex,
                        :event_id,
                        :request_text,
                        NULL,
                        :motive1_event_key,
                        :motive2_event_key,
                        :stop_source,
                        :plex_log_key,
                        :current_status_workcenter,
                        :current_status_start,
                        :current_status_end,
                        :current_status_minutes,
                        :current_status_reason
                    )
                """), {
                    'request_id': int(newId),
                    'requester_id': str(current_user.id),
                    'approver1': str(approver1['userId'].iloc[0]),
                    'approver2': str(approver2['userId'].iloc[0]),
                    'motive1': _normalize_catalog_id(check_request['Code']),
                    'motive2': new_motive_code,
                    'plex': int(source != 'ftm'),
                    'event_id': event_id,
                    'request_text': payload['requestText'],
                    'motive1_event_key': old_motive_event_key,
                    'motive2_event_key': new_motive_event_key,
                    'stop_source': source,
                    'plex_log_key': (
                        int(plex_log['Log_Key']) if plex_log is not None else None
                    ),
                    'current_status_workcenter': (
                        str(status_row['Workcenter']) if status_row is not None else None
                    ),
                    'current_status_start': (
                        pd.to_datetime(status_row['StatusBegin']).to_pydatetime()
                        if status_row is not None else None
                    ),
                    'current_status_end': (
                        pd.to_datetime(status_row['StatusEnd']).to_pydatetime()
                        if status_row is not None
                        and pd.notna(status_row['StatusEnd']) else None
                    ),
                    'current_status_minutes': (
                        check_request['Log_Minutes'] if status_row is not None else None
                    ),
                    'current_status_reason': (
                        str(status_row['WcReason']) if status_row is not None else None
                    )
                })
            
                if source == 'plex' or (source == 'td' and plex_log is not None):

                    try:
                        plex_event_id = (
                            int(plex_log['Log_Key']) if plex_log is not None
                            else event_id
                        )
                        plex_workcenter = (
                            int(plex_log['Workcenter_Key']) if plex_log is not None
                            else int(check_request['Workcenter_Key'])
                        )
                        plex_log_date = (
                            pd.to_datetime(plex_log['Log_Date']) - timedelta(hours=1)
                            if plex_log is not None
                            else pd.to_datetime(
                                check_request['Log_Date'], format='%d/%m/%Y %H:%M:%S'
                            )
                        )
                        plex_log_minutes = (
                            float(plex_log['Log_Hours']) * 60
                            if plex_log is not None else check_request['Log_Minutes']
                        )
                        query = f"""
                                IF NOT EXISTS (
                                    SELECT 1
                                    FROM JDT_REQUEST_STOPCHANGES_PLEX
                                    WHERE eventId = :plex_event_id
                                )
                                BEGIN
                                    INSERT INTO JDT_REQUEST_STOPCHANGES_PLEX (
                                        eventId
                                        , workcenter
                                        , startDate
                                        , endDate
                                        , logMinutes
                                    ) VALUES (
                                        :plex_event_id
                                        , :plex_workcenter
                                        , :plex_log_date
                                        , :plex_end_date
                                        , :plex_log_minutes
                                    )
                                END
                        """
                        cnnx.execute(text(query), {
                            'plex_event_id': plex_event_id,
                            'plex_workcenter': plex_workcenter,
                            'plex_log_date': plex_log_date.to_pydatetime(),
                            'plex_end_date': (
                                plex_log_date + timedelta(minutes=plex_log_minutes)
                            ).to_pydatetime(),
                            'plex_log_minutes': plex_log_minutes
                        })
                    except Exception as e:
                        # SQLAlchemy IntegrityError is sqlalchemy.exc.IntegrityError
                        if isinstance(e, IntegrityError):
                            # SQL Server error codes for duplicate key: 2627, 2601
                            if any(code in str(e.orig) for code in ['2627', '2601']):
                                pass
                            else:
                                print(e, flush=True)
                                return 'INTERN SERVER ERROR.', 500
                        else:
                            print(e, flush=True)
                            return 'INTERN SERVER ERROR.', 500

                cnnx.commit()

            email_approvers = pd.concat([approver1, approver2])
            if transformation_digital_area_id in {problemAreaOld, problemAreaNew}:
                email_approvers = pd.concat([
                    email_approvers,
                    approvers_info[
                        (approvers_info['areaId'] == transformation_digital_area_id)
                        & approvers_info['shift'].astype(str).isin({
                            str(_TRANSFORMATION_DIGITAL_PRIMARY_SHIFT),
                            str(_TRANSFORMATION_DIGITAL_SECONDARY_SHIFT)
                        })
                    ]
                ])

            recipient_emails = (
                email_approvers['companyEmail']
                .dropna()
                .astype(str)
                .str.strip()
            )
            recipient_emails = recipient_emails[
                recipient_emails != ''
            ].drop_duplicates().tolist()

            msg = Message(f'Alteração de Paradas - Nova Solicitação',
                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                recipients=recipient_emails)
            
            def format_event(event):
                return f"{event['Code']}-{event['Description']}"

            try:
                motive_old_text = format_event(_get_plex_event(
                    events,
                    check_request['Code'],
                    old_motive_event_key
                ))
            except _CurrentStatusMatchError:
                motive_old_text = (
                    f"{check_request['Code']}-Motivo com identificação pendente"
                )
            
            msg.html = render_template('request.stopChanges/stopChanges_email_new_request.html'
                                        , requestId=newId
                                        , userName=current_user.name
                                        , workCenter=check_request['Workcenter_Name']
                                        , stopDate=check_request['Log_Date']
                                        , shift=check_request['Shift']
                                        , duration=check_request['Log_Minutes']
                                        , motiveOld=motive_old_text
                                        , motiveNew=format_event(new_motive)
                                        , requestText=payload["requestText"])
            
            mail.send(msg)

            return f'NEW ID {str(newId)}'                        
    
    else:
        workcenters = get_stops_workcenters()
        
        data = pd.DataFrame(columns=["sDescription", "tStart", "tEnd", "sEndVal", "dDuration"])
        if current_user.id not in _USER_FILTERS.keys():
            _USER_FILTERS[current_user.id] = {
                'shift' : ['1', '2', '3', 'Extra']
                , 'm_event': []
                , 'w_name_mic': []
                , 'start_date': ''
                , 'end_date': ''
                , 'w_name_plex': []
            }

        current_user_filters = _USER_FILTERS[current_user.id]

        events = getPlex('events')
        events = events[(events['Code'] != '64') & (events['Active'] == 1)]
        events = events.sort_values(by='Code', key=lambda col: col.fillna('0').astype(int)).to_dict(orient='records')

        return render_template('request.stopChanges/stopChanges_request.html'
                                , workcenters=workcenters.sort_values(by="Workcenter_Code").to_dict(orient='records')
                                , events=events
                                , data=data.to_json(orient='records')
                                , workCenterFilter=current_user_filters['w_name_plex'] or current_user_filters['w_name_mic']
                                , motiveFilter=current_user_filters['m_event']
                                , initDateFilter=current_user_filters['start_date']
                                , endDateFilter=current_user_filters['end_date'])


# PÁGINA ONDE SE VISUALIZAM AS SOLICITAÇÕES FEITAS PELO USUÁRIO
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/solicitacoes', methods=['GET', 'POST'])
def stopChanges_view():

    if request.method == 'GET':

        this_week = datetime.now().date()
        last_week = this_week - timedelta(weeks=2)

        return render_template('request.stopChanges/stopChanges_view.html', this_week=this_week, last_week=last_week)
    
    else:


        query = f"""
                    
            SELECT 
                T1.requestId
                , FORMAT(T1.openDate, 'dd/MM/yyyy') AS openDate
                , T1.motive1
                , T1.motive2
                , T1.motive1EventKey
                , T1.motive2EventKey
                , T1.approverStatus1
                , T1.approverStatus2
                , T1.Plex
                , T1.stopSource
                , T1.currentStatusReason
                , COALESCE(T1.currentStatusWorkcenter, CAST(T2.workcenter AS varchar), T3.sDescription) AS Workcenter_Name
                , FORMAT(COALESCE(T1.currentStatusStart, T2.endDate, T3.tStart), 'dd/MM/yyyy') AS tStart
                , COALESCE(T1.currentStatusMinutes, T2.logMinutes, T3.lSeconds / 60) AS dDuration
                , T4.name
            FROM 
                JDT_REQUEST_STOPCHANGES AS T1

                LEFT JOIN JDT_REQUEST_STOPCHANGES_PLEX AS T2 
                    ON T1.PLEX = 1 AND (T1.stopSource IS NULL OR T1.stopSource = 'plex')
                    AND T1.eventId = T2.eventId

                LEFT JOIN FTMETRICS_JOST.dbo.OEEQEventHistory AS T3 
                    ON T1.PLEX = 0 AND (T1.stopSource IS NULL OR T1.stopSource = 'ftm')
                    AND T1.eventId = T3.lOEEEventId

                JOIN JDT_USER_DETAILS AS T4 ON T1.requesterId = T4.id
            
            WHERE 
                
                T1.openDate BETWEEN '{request.get_json()['last_week']} 00:00' AND '{request.get_json()['this_week']} 23:59'

            ORDER BY T1.openDate DESC"""

        table = engine_run_query(query, 'jdt')

        table = _add_motive_descriptions(table, getPlex('events'))
        
        workcenters = getPlex('workcenters')
        workcenters['Workcenter_Key'] = workcenters['Workcenter_Key'].astype(str)

        map_dict = workcenters.set_index('Workcenter_Key').apply(
            lambda row: f"{row['Workcenter_Code']} - {row['Name']}", axis=1
        ).to_dict()
        
        plex_rows = table['Plex'].eq(1) & table['stopSource'].ne('td')
        table.loc[plex_rows, 'Workcenter_Name'] = (
            table.loc[plex_rows, 'Workcenter_Name'].map(map_dict)
        )

        return table.to_json(orient='records')


# ROTA PARA CONSULTAR UMA SOLICITAÇÃO DE PARADA EM ESPECIFICA E VER O SEU STATUS
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/solicitacoes/<int:requestId>', methods=['GET'])
def stopChanges_status(requestId):

    query = f"""
                SELECT 
                    FORMAT(T1.openDate, 'dd/MM/yyyy HH:mm:ss') as openDate
                    , FORMAT(T1.finalDate, 'dd/MM/yyyy HH:mm:ss') as finalDate
                    , T1.motive1
                    , T1.motive2
                    , T1.motive1EventKey
                    , T1.motive2EventKey
                    , T1.approverStatus1
                    , T1.approverStatus2
                    , T1.eventId
                    , T1.requestId
                    , T1.deniedText
                    , T1.requestText
                    , T1.plex
                    , T1.stopSource
                    , T1.currentStatusWorkcenter
                    , T1.currentStatusStart
                    , T1.currentStatusMinutes
                    , T1.currentStatusReason
                    , T2.name as requesterName
                    , T3.name as approver1
                    , GA1.name as approverArea1
                    , T4.name as approver2
                    , GA2.name as approverArea2
                FROM JDT_REQUEST_STOPCHANGES AS T1
                    JOIN JDT_USER_DETAILS AS T2 ON T1.requesterId = T2.id
                    LEFT JOIN JDT_USER_DETAILS AS T3 ON T1.approver1 = T3.id
                    LEFT JOIN JDT_USER_DETAILS AS T4 ON T1.approver2 = T4.id
                    LEFT JOIN JDT_GENERAL_AREA AS GA1 ON T3.areaId = GA1.areaId
                    LEFT JOIN JDT_GENERAL_AREA AS GA2 ON T4.areaId = GA2.areaId

                WHERE T1.requestId = {requestId}"""
    data = engine_run_query(query, 'jdt')

    if data.empty:
        return render_template('request.stopChanges/stopChanges_alert_not_exists.html'), 404

    data['eventId'] = data['eventId'].astype(int).astype(str)

    if data['stopSource'][0] == 'td':
        stop_data = pd.DataFrame([{
            'startDate': pd.to_datetime(
                data['currentStatusStart'][0]
            ).strftime('%d/%m/%Y %H:%M:%S'),
            'workcenter': data['currentStatusWorkcenter'][0],
            'logMinutes': data['currentStatusMinutes'][0]
        }])
    elif data['plex'][0]:
        query = f"""
                    SELECT 
                        FORMAT(startDate, 'dd/MM/yyyy HH:mm:ss') AS startDate
                        , workcenter
                        , logMinutes
                    FROM JDT_REQUEST_STOPCHANGES_PLEX WHERE eventId = {data['eventId'][0]}
                """
    
    else:
        query = f"""
                    SELECT 
                        FORMAT(tStart, 'dd/MM/yyyy HH:mm:ss') AS startDate
                        , REPLACE(sDescription, '-', ' - ') AS workcenter
                        , lSeconds / 60 AS logMinutes
                    FROM [FTMETRICS_JOST].[dbo].[OEEQEventHistory] WHERE lOEEEventId = {data['eventId'][0]}
                """

    if data['stopSource'][0] != 'td':
        stop_data = engine_run_query(query, 'jdt')

    if data['stopSource'][0] != 'td' and data['plex'][0]:
        stop_data = pd.merge(left=stop_data, right=getPlex('workcenters')[['Workcenter_Key', 'Name', 'Workcenter_Code']], left_on='workcenter', right_on='Workcenter_Key')
        stop_data['workcenter'] = stop_data['Workcenter_Code'] + ' - ' + stop_data['Name']
    
    data = _add_motive_descriptions(data, getPlex('events'))

    back = request.args.get('origin', 'solicitacoes')

    return render_template(
        'request.stopChanges/stopChanges_status.html'
        , data=data.to_dict(orient="records")
        , stop_data=stop_data.to_dict(orient="records")
        , back=back, requestId=requestId
    )


# METODO PARA CONSULTA E APROVAÇÃO DAS SOLICITAÇÕES PENDENTES DE CADA USUÁRIO
# ADMIN CONSEGUE VER E APROVAR TODAS AS SOLICITAÇÕES PENDENTES
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/pendencias', methods=['GET', 'POST'])
def stopChanges_manage():

    if request.method == 'GET':

        is_admin = _current_user_is_admin()
        aux = 'T1.finalDate IS NULL'
        if not is_admin:
            aux = f"""T1.finalDate IS NULL AND (
                        (T1.approver1 = '{current_user.id}' AND T1.approverStatus1 = 0)
                        OR (T1.approver2 = '{current_user.id}' AND T1.approverStatus2 = 0)
                    )"""
        
        query = f"""
                    
                    SELECT 
                        T1.requestId
                        , T1.approver1
                        , T1.approver2
                        , FORMAT(T1.openDate, 'dd/MM/yyyy') AS openDate
                        , T1.motive1
                        , T1.motive2
                        , T1.motive1EventKey
                        , T1.motive2EventKey
                        , T1.approverStatus1
                        , T1.approverStatus2
                        , T1.Plex
                        , T1.stopSource
                        , T1.currentStatusReason
                        , T1.requestText
                        , COALESCE(T1.currentStatusWorkcenter, CAST(T2.workcenter AS varchar), T3.sDescription) AS Workcenter_Name
                        , FORMAT(COALESCE(T1.currentStatusStart, T2.endDate, T3.tStart), 'dd/MM/yyyy') AS tStart
                        , COALESCE(T1.currentStatusMinutes, T2.logMinutes, T3.lSeconds / 60) AS dDuration
                        , T4.name
                    FROM 
                        JDT_REQUEST_STOPCHANGES AS T1

                        LEFT JOIN JDT_REQUEST_STOPCHANGES_PLEX AS T2 
                            ON T1.PLEX = 1 AND (T1.stopSource IS NULL OR T1.stopSource = 'plex')
                            AND T1.eventId = T2.eventId

                        LEFT JOIN FTMETRICS_JOST.dbo.OEEQEventHistory AS T3 
                            ON T1.PLEX = 0 AND (T1.stopSource IS NULL OR T1.stopSource = 'ftm')
                            AND T1.eventId = T3.lOEEEventId

                        JOIN JDT_USER_DETAILS AS T4 ON T1.requesterId = T4.id
                    
                    WHERE {aux}

                    ORDER BY T1.openDate ASC"""

        table = engine_run_query(query, 'jdt') 

        events = getPlex('events')
        table = _add_motive_descriptions(table, events)
        
        workcenters = getPlex('workcenters')
        workcenters['Workcenter_Key'] = workcenters['Workcenter_Key'].astype(str)

        map_dict = workcenters.set_index('Workcenter_Key').apply(
            lambda row: f"{row['Workcenter_Code']} - {row['Name']}", axis=1
        ).to_dict()

        plex_rows = table['Plex'].eq(1) & table['stopSource'].ne('td')
        table.loc[plex_rows, 'Workcenter_Name'] = (
            table.loc[plex_rows, 'Workcenter_Name'].map(map_dict)
        )

        transformation_digital_table = table
        if is_admin and not table.empty:
            transformation_digital_approvers = (
                _get_transformation_digital_approvers()
            )
            motive1_is_transformation_digital = table.apply(
                lambda row: _is_transformation_digital_motive(
                    row['motive1'],
                    events,
                    row['motive1EventKey'],
                    row['approver1'],
                    transformation_digital_approvers
                ),
                axis=1
            )
            motive2_is_transformation_digital = table.apply(
                lambda row: _is_transformation_digital_motive(
                    row['motive2'],
                    events,
                    row['motive2EventKey'],
                    row['approver2'],
                    transformation_digital_approvers
                ),
                axis=1
            )
            status1 = pd.to_numeric(table['approverStatus1'], errors='coerce')
            status2 = pd.to_numeric(table['approverStatus2'], errors='coerce')
            transformation_digital_table = table[
                (
                    motive1_is_transformation_digital
                    & status1.eq(0)
                )
                | (
                    motive2_is_transformation_digital
                    & status2.eq(0)
                )
            ]

        return render_template(
            'request.stopChanges/stopChanges_pending.html',
            table=transformation_digital_table.to_json(orient='records'),
            adminTable=table.to_json(orient='records'),
            isAdmin=is_admin
        )
    
    else:

        received_data = request.get_json()

        query = f"""SELECT  
                        approver1, approverStatus1,
                        approver2, approverStatus2,
                        motive1, motive2,
                        motive1EventKey, motive2EventKey,
                        requestText, deniedText, finalDate, requesterId
                    
                    FROM JDT_REQUEST_STOPCHANGES WHERE requestId = {received_data['requestId']} ORDER BY openDate DESC"""
        check_request = engine_run_query(query, 'jdt')
        is_admin = _current_user_is_admin()
        approval_scope = received_data.get('scope')

        # SEÇÃO PARA VERIFICAR PERMISSÃO
        if len(check_request) == 0:
            abort(403)

        elif str(current_user.id) not in [str(check_request['approver1'][0]), str(check_request['approver2'][0])] and not is_admin:
            abort(403)
        
        elif check_request['finalDate'][0] == 'None':
            return render_template('request.stopChanges/stopChanges_alert_end.html'), 403
        
        elif not is_admin and str(check_request['approver1'][0]) == str(current_user.id) and check_request['approverStatus1'][0] != 0:
            abort(403)

        elif not is_admin and str(check_request['approver2'][0]) == str(current_user.id) and check_request['approverStatus2'][0] != 0:
            abort(403)

        elif is_admin and approval_scope not in {'transformationDigital', 'admin'}:
            abort(400)

        transformation_digital_sides = {1: False, 2: False}
        if is_admin and approval_scope == 'transformationDigital':
            events = getPlex('events')
            transformation_digital_approvers = (
                _get_transformation_digital_approvers()
            )
            transformation_digital_sides = {
                1: _is_transformation_digital_motive(
                    check_request['motive1'][0],
                    events,
                    check_request['motive1EventKey'][0],
                    check_request['approver1'][0],
                    transformation_digital_approvers
                ),
                2: _is_transformation_digital_motive(
                    check_request['motive2'][0],
                    events,
                    check_request['motive2EventKey'][0],
                    check_request['approver2'][0],
                    transformation_digital_approvers
                )
            }

            has_pending_transformation_digital_side = (
                transformation_digital_sides[1]
                and check_request['approverStatus1'][0] == 0
            ) or (
                transformation_digital_sides[2]
                and check_request['approverStatus2'][0] == 0
            )
            if not has_pending_transformation_digital_side:
                abort(403)


        # SEÇÃO PARA ATUALIZAR A SOLICITAÇÃO
        userId = str(current_user.id)

        engine = get_engine('jdt')
        with engine.connect() as cnnx:

            if received_data['type'] == 'approve':
            
                if is_admin and approval_scope == 'admin':
                    query = f"""UPDATE JDT_REQUEST_STOPCHANGES SET 
                                    approver1 = '{userId}', 
                                    approver2 = '{userId}', 
                                    approverStatus1 = 1, 
                                    approverStatus2 = 1,
                                    approverDate1 = GETDATE(),   
                                    approverDate2 = GETDATE()
                                WHERE 
                                    requestId = {received_data['requestId']}"""
                    cnnx.execute(text(query))

                elif is_admin:
                    if (
                        transformation_digital_sides[1]
                        and check_request['approverStatus1'][0] == 0
                    ):
                        cnnx.execute(text("""
                            UPDATE JDT_REQUEST_STOPCHANGES
                            SET approver1 = :user_id,
                                approverStatus1 = 1,
                                approverDate1 = GETDATE()
                            WHERE requestId = :request_id
                        """), {
                            "user_id": userId,
                            "request_id": received_data['requestId']
                        })

                    if (
                        transformation_digital_sides[2]
                        and check_request['approverStatus2'][0] == 0
                    ):
                        cnnx.execute(text("""
                            UPDATE JDT_REQUEST_STOPCHANGES
                            SET approver2 = :user_id,
                                approverStatus2 = 1,
                                approverDate2 = GETDATE()
                            WHERE requestId = :request_id
                        """), {
                            "user_id": userId,
                            "request_id": received_data['requestId']
                        })

                else:

                    if userId == str(check_request['approver1'][0]):
                        query = f"""UPDATE JDT_REQUEST_STOPCHANGES SET 
                                        approverStatus1 = 1, 
                                        approverDate1 = GETDATE() 
                                    WHERE 
                                        requestId = {received_data['requestId']}"""
                        cnnx.execute(text(query))

                    if userId == str(check_request['approver2'][0]):
                        query = f"""UPDATE JDT_REQUEST_STOPCHANGES SET 
                                        approverStatus2 = 1, 
                                        approverDate2 = GETDATE() 
                                    WHERE 
                                        requestId = {received_data['requestId']}"""
                        cnnx.execute(text(query))
                
                query = f"""SELECT 
                                TOP(1) T1.*, T2.workcenter,
                                T2.startDate, T2.endDate,
                                T2.logMinutes / 60.0 AS logHours
                            FROM JDT_REQUEST_STOPCHANGES T1
                                LEFT JOIN JDT_REQUEST_STOPCHANGES_PLEX T2
                                    ON T2.eventId = CASE
                                        WHEN T1.stopSource = 'td' THEN T1.plexLogKey
                                        ELSE T1.eventId
                                    END
                            
                            WHERE requestId = {received_data['requestId']}"""
                check_request = pd.read_sql(query, cnnx)
                check_request = check_request.iloc[0]

                if not check_request['approverStatus1'] or not check_request['approverStatus2']:
                    cnnx.commit()
                    return 'REQUEST APPROVED.', 200

                if check_request['plex']:

                    status_key = {
                        'Mão de Obra': 10779, 'Método': 222,
                        'Manutenção': 213, 'Manutenção Parada': 213,
                        'Manutenção Produtiva': 213, 'Material': 10781,
                        'Movimentação': 10780, 'Programada': 10778
                    }
                    events = getPlex('events')
                    td_source = check_request['stopSource'] == 'td'
                    linked_plex = not td_source or pd.notna(check_request['plexLogKey'])

                    try:
                        if td_source:
                            current = _get_current_status_event(
                                int(check_request['eventId'])
                            )
                            if (
                                str(current['Workcenter']).strip()
                                != str(check_request['currentStatusWorkcenter']).strip()
                                or pd.to_datetime(current['StatusBegin'])
                                != pd.to_datetime(check_request['currentStatusStart'])
                                or str(current['WcReason']).strip()
                                != str(check_request['currentStatusReason']).strip()
                            ):
                                raise _CurrentStatusMatchError(
                                    'PARADA NO CURRENT STATUS FOI ALTERADA APOS A SOLICITACAO.'
                                )
                        if linked_plex:
                            current_status_id, newMotivePlex = _find_current_status_stop(
                                check_request,
                                events
                            )
                            if td_source and current_status_id != int(check_request['eventId']):
                                raise _CurrentStatusMatchError(
                                    'REGISTRO PLEX CORRESPONDE A OUTRA PARADA.'
                                )
                        else:
                            current_status_id = int(check_request['eventId'])
                            newMotivePlex = _get_plex_event(
                                events,
                                event_key=check_request['motive2EventKey']
                            )
                    except _CurrentStatusMatchError as error:
                        cnnx.rollback()
                        return str(error), 409

                    if linked_plex:
                        if newMotivePlex['Workcenter_Event_Group'] not in status_key:
                            cnnx.rollback()
                            return 'CATEGORIA DO NOVO MOTIVO NAO CONFIGURADA NO PLEX.', 409
                        plex_event_id = (
                            int(check_request['plexLogKey']) if td_source
                            else int(check_request['eventId'])
                        )
                        payload = {
                            'inputs' : {
                                'Log_Key': str(plex_event_id)
                                , 'Workcenter_Event_Key' : f"{newMotivePlex['Workcenter_Event_Key']}"
                                , 'Workcenter_Key' : f"{check_request['workcenter']}"
                                , 'Workcenter_Status_Key' : f"{status_key[newMotivePlex['Workcenter_Event_Group']]}"
                                , 'Log_Hours': check_request['logHours']
                                , 'Reviewed': 1
                            }
                        }

                        response = POST_WITH_AUTH("https://jost.on.plex.com/api/datasources/12272/execute", HTTPBasicAuth(MES_MAIN_USER, MES_MAIN_PASSWORD), payload)

                        if "errors" in response:
                            cnnx.rollback()
                            return 'PLEX ERROR.', 400

                    try:
                        _update_current_status_stop(
                            current_status_id,
                            newMotivePlex,
                            expected_status=check_request if td_source else None
                        )
                    except _CurrentStatusMatchError as error:
                        cnnx.rollback()
                        return str(error), 409

                else:
                    
                    engine_ftm = get_engine('ftm')
                    with engine_ftm.begin() as cnnx2:
                        query = f"""UPDATE [FTMETRICS_JOST].[dbo].OEEQEventHistory SET sEndVal = '{check_request['motive2']}' WHERE lOEEEventId = '{check_request['eventId'].astype(int)}'"""
                        cnnx2.execute(text(query))

                query = f"""UPDATE JDT_REQUEST_STOPCHANGES SET
                                finalDate = GETDATE()
                            WHERE
                                requestId = '{received_data['requestId']}'"""
                cnnx.execute(text(query))
                cnnx.commit()

                query = f"""SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = '{check_request['requesterId']}'"""
                requesterEmail = pd.read_sql(query, cnnx)['companyEmail'][0]

                msg = Message(f"Alteração de Paradas - Solicitação {received_data['requestId']} aprovada",
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=[requesterEmail])

                msg.html = render_template('request.stopChanges/stopChanges_email_approved.html',
                                        requestId=received_data['requestId'],
                                        requestText=check_request['requestText'])
                mail.send(msg)

                return 'REQUEST APPROVED.', 200

            else:

                if is_admin and approval_scope == 'admin':
                    cnnx.execute(text("""
                        UPDATE JDT_REQUEST_STOPCHANGES
                        SET approver1 = :user_id,
                            approver2 = :user_id,
                            approverStatus1 = 2,
                            approverStatus2 = 2,
                            deniedText = :denied_text,
                            approverDate1 = GETDATE(),
                            approverDate2 = GETDATE(),
                            finalDate = GETDATE()
                        WHERE requestId = :request_id
                    """), {
                        "user_id": userId,
                        "denied_text": received_data['deniedText'],
                        "request_id": received_data['requestId']
                    })

                elif is_admin:
                    if (
                        transformation_digital_sides[1]
                        and check_request['approverStatus1'][0] == 0
                    ):
                        cnnx.execute(text("""
                            UPDATE JDT_REQUEST_STOPCHANGES
                            SET approver1 = :user_id,
                                approverStatus1 = 2,
                                deniedText = :denied_text,
                                approverDate1 = GETDATE(),
                                finalDate = GETDATE()
                            WHERE requestId = :request_id
                        """), {
                            "user_id": userId,
                            "denied_text": received_data['deniedText'],
                            "request_id": received_data['requestId']
                        })

                    if (
                        transformation_digital_sides[2]
                        and check_request['approverStatus2'][0] == 0
                    ):
                        cnnx.execute(text("""
                            UPDATE JDT_REQUEST_STOPCHANGES
                            SET approver2 = :user_id,
                                approverStatus2 = 2,
                                deniedText = :denied_text,
                                approverDate2 = GETDATE(),
                                finalDate = GETDATE()
                            WHERE requestId = :request_id
                        """), {
                            "user_id": userId,
                            "denied_text": received_data['deniedText'],
                            "request_id": received_data['requestId']
                        })

                elif userId == str(check_request['approver1'][0]):
                    cnnx.execute(text("""
                        UPDATE JDT_REQUEST_STOPCHANGES
                        SET approverStatus1 = 2,
                            deniedText = :denied_text,
                            approverDate1 = GETDATE(),
                            finalDate = GETDATE()
                        WHERE requestId = :request_id
                    """), {
                        "denied_text": received_data['deniedText'],
                        "request_id": received_data['requestId']
                    })

                elif userId == str(check_request['approver2'][0]):
                    cnnx.execute(text("""
                        UPDATE JDT_REQUEST_STOPCHANGES
                        SET approverStatus2 = 2,
                            deniedText = :denied_text,
                            approverDate2 = GETDATE(),
                            finalDate = GETDATE()
                        WHERE requestId = :request_id
                    """), {
                        "denied_text": received_data['deniedText'],
                        "request_id": received_data['requestId']
                    })


                query = f"""SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = '{check_request['requesterId'][0]}'"""
                requesterEmail = pd.read_sql(query, cnnx)['companyEmail'][0]

                msg = Message(f"Alteração de Paradas - Solicitação {received_data['requestId']} recusada",
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=[requesterEmail])

                msg.html = render_template('request.stopChanges/stopChanges_email_denied.html',
                                            requestId=received_data['requestId'],
                                            approverName=current_user.name,
                                            deniedText=received_data['deniedText'],
                                            requestText=check_request['requestText'][0])
                mail.send(msg)
                cnnx.commit()

                return 'REQUEST DENIED.', 200


# ROTA PARA CONSULTAR OS GRÁFICOS DE ALTERAÇÃO DE PARARADAS
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/dash')
def stopChanges_dash():
    return render_template('general_maintenance.html')

    query = "SELECT NOME_MAQUINA as Name FROM CONFIG_TABLET WHERE FL_ATIVO = 1"
    mic_workcenters = engine_run_query(query, 'ftm')

    mes_workcenters = getPlex('workcenters')[['Name']]
    workcenters = pd.concat([mic_workcenters, mes_workcenters])

    return render_template('request.stopChanges/stopChanges_dash.html', 
                            events=getPlex('events').sort_values(by='Description').to_dict(orient='records'), 
                            workcenters=workcenters.to_dict(orient='records'))

# ROTA PARA PEGAR OS DADOS DOS GRÁFICOS
@request_workcentersLogChange_bp.route('/oee/paradas/alterar/dash_callback', methods=['POST'])
def dash_callback():
    return render_template('general_maintenance.html')

    received_data = request.get_json()

    conditions = []

    def add_filter(field_name, column_name, conditions):
        local_filter = received_data.get(field_name)
        if local_filter:
            filter_list = ', '.join(f"'{w}'" for w in local_filter)
            conditions.append(f"{column_name} IN ({filter_list})")

    add_filter('m_old', 'T3.CATEGORIA', conditions)
    add_filter('m_new', 'T4.CATEGORIA', conditions)
    add_filter('event_old', 'T1.motive1', conditions)
    add_filter('event_new', 'T1.motive2', conditions)

    main_where_clause = f"AND {' AND '.join(conditions)}" if conditions else ""

    conditions = []
    add_filter('workcenters', 'sDescription', conditions)
    workcenter_where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f""" 
                WITH
                    EVENTS AS (
                        SELECT
                            lOEEEventId,
                            sDescription
                        FROM
                            [FTMETRICS_JOST].[dbo].OEEQEventHistory 
                        {workcenter_where_clause}

                    ),
                    STOPS AS (
                        SELECT
                            CATEGORIA,
                            CASE
                                WHEN MOTIVO = 'Sem Justificativa' THEN MOTIVO
                                ELSE SUBSTRING(MOTIVO, 5, LEN(MOTIVO))
                            END AS MOTIVO
                        FROM
                            [FTMETRICS_JOST].[dbo].CADASTRO_PARADA
                    ),
                    REQUESTS AS (
                        SELECT
                            eventId,
                            CASE
                                WHEN motive1 = 'Sem Justificativa' THEN motive1
                                ELSE SUBSTRING(motive1, 5, LEN(motive1))
                            END AS motive1,
                            CASE
                                WHEN motive2 = 'Sem Justificativa' THEN motive2
                                ELSE SUBSTRING(motive2, 5, LEN(motive2))
                            END AS motive2,
                            DATEDIFF(SECOND, openDate, CASE WHEN finalDate IS NULL
                                THEN GETDATE()
                                ELSE finalDate
                                END) AS duration,
                            openDate,
                            approverStatus1,
                            approverStatus2
                        FROM JDT_REQUEST_STOPCHANGES
                    )
                
                SELECT
                    T1.motive1,
                    T1.motive2,
                    T1.duration,
                    T3.CATEGORIA AS m_1,
                    T4.CATEGORIA AS m_2,
                    T2.sDescription,

                    CASE 
                        WHEN (approverStatus1 = 1 AND approverStatus2 = 1) THEN 'Aprovada'
                        WHEN (approverStatus1 = 2 OR approverStatus2 = 2) THEN 'Reprovada'
                        ELSE 'Aguardando'
                    END AS status

                FROM REQUESTS AS T1
                    JOIN EVENTS AS T2 ON T2.lOEEEventId = T1.eventId
                    JOIN STOPS AS T3 ON T3.MOTIVO = T1.motive1
                    JOIN STOPS AS T4 ON T4.MOTIVO = T1.motive2

                WHERE
                    T1.openDate BETWEEN '{received_data['start_date']}' AND '{received_data['end_date']}'
                    {main_where_clause}
            """
    
    data = pd.read_sql(query, cnnx)
    data = data[data['status'].astype(str).isin(received_data['status'])]

    events_by_motive = data.groupby(['motive1', 'motive2']).size().reset_index(name='QTT')
    m_1 = data['m_1'].value_counts().reset_index().rename(columns={'m_1': 'LABELS', 'count': 'QTT'})
    m_2 = data['m_2'].value_counts().reset_index().rename(columns={'m_2': 'LABELS', 'count': 'QTT'})

    total_requests = data.shape[0]

    def seconds_to_dhms(seconds):
        days = seconds // (24 * 3600)
        seconds = seconds % (24 * 3600)
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return f'{days}d {hours}h {minutes}m {seconds}s'

    def aggregate_durations(group):
        return pd.Series({
            'max': seconds_to_dhms(group['duration'].max()),
            'min': seconds_to_dhms(group['duration'].min()),
            'mean': seconds_to_dhms(int(group['duration'].mean())),
            'count': group['duration'].count()
        })

    if data.empty:
        table = pd.DataFrame(columns=['motive1', 'motive2', 'sDescription', 'max', 'min', 'mean', 'count'])
    else:
        table = data.groupby(['motive1', 'motive2', 'sDescription']).apply(aggregate_durations).reset_index()

    data_to_send = {
        'barChart1': events_by_motive.to_json(orient='records'),
        'pieChart1': m_1.to_json(orient='records'),
        'pieChart2': m_2.to_json(orient='records'),
        'totalRequests': str(total_requests),
        'table': table.to_json(orient='records')
    }

    return data_to_send

# V2
