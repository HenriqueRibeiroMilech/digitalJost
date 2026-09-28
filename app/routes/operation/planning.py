"""
---LABEL ENCODING---

TIPO DE PLANO DE AÇÃO:
    0 : CONTENÇÃO
    1 : CORRETIVA

ÁREA PLANO DE AÇÃO:
    0 : MÃO DE OBRA
    1 : MOVIMENTAÇÃO
    2 : MATERIAL
    3 : MANUTENÇÃO
    4 : MÉTODO (QUALIDADE)
    5 : MÉTODO (PROCESSOS)

STATUS DE UMA AÇÃO:
    -2 : CANCELADO
    -1 : RECUSADO
    0 : NÃO INICIADO
    1 a 99 : EM ANDAMENTO
    100 : CONCLUÍDO

AREA FABRIL:
    0 : MONTAGEM
    1 : USINAGEM
    2 : SOLDAGEM
    3 : PRÉ-FABRICAÇÃO
"""

import json
import os
import calendar
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

from sqlalchemy import text

from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user
from flask_mail import Message

from app.utils.business import getStopsData
from app.utils.db_utils import engine_run_query, get_engine
from app.utils.dynamic_constants import getPlex
from app.utils.permissions import get_permission
from app.utils.planning_availability import (
    get_planned_availability, get_weekly_planned_availability, get_planning_stops,
    summarize_weekly_availability, summarize_monthly_availability, json_records
)
from app.config import mail


p_goal = get_permission('GOAL_OP_M')

operation_planning_bp = Blueprint('operation_planning', __name__)

@operation_planning_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)


_MAP_AREA_SLIDES = {
    0: 'Mão de Obra',
    1: 'Movimentação',
    2: 'Material',
    3: 'Manutenção',
    4: 'Método (Qualidade)',
    5: 'Método (Processos)'
}

_STOP_AREAS = {
    '3': 'Método (Qualidade)', '4': 'Método (Qualidade)',
    '19': 'Método (Qualidade)', '42': 'Método (Qualidade)',
    '44': 'Método (Processos)', '65': 'Método (Qualidade)',
    '20': 'Método (Processos)', '31': 'Método (Processos)',
    '32': 'Método (Processos)', '37': 'Método (Processos)',
    '43': 'Método (Processos)', '100': 'Método (Processos)'
}


def _infer_planning_event_codes(stopped_event):
    """Recupera códigos só quando a descrição do motivo identifica um único evento."""
    if stopped_event.empty:
        return stopped_event['Event_Code'].fillna('').astype(str)

    catalog = getPlex('events')[[
        'Description', 'Workcenter_Event_Group', 'Code'
    ]].dropna(subset=['Description', 'Code']).copy()

    def normalize(value):
        return ' '.join(str(value).strip().casefold().split()) if pd.notna(value) else ''

    catalog['Code'] = (
        catalog['Code'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    )
    catalog = catalog[catalog['Code'] != '']
    catalog['_event'] = catalog['Description'].apply(normalize)
    catalog['_status'] = catalog['Workcenter_Event_Group'].replace({
        'Manutenção Parada': 'Manutenção',
        'Manutenção Produtiva': 'Manutenção'
    }).apply(normalize)

    def unique_codes(keys):
        return catalog.groupby(keys)['Code'].agg(
            lambda codes: codes.iloc[0] if codes.nunique() == 1 else None
        )

    by_event_and_status = unique_codes(['_event', '_status'])
    by_event = unique_codes('_event')
    codes = (
        stopped_event['Event_Code'].fillna('').astype(str)
        .str.strip().str.replace(r'\.0$', '', regex=True)
    )

    for index in stopped_event.index[codes.eq('')]:
        event_name = normalize(stopped_event.at[index, 'Event'])
        status_name = normalize(stopped_event.at[index, 'Status'])
        code = by_event_and_status.get((event_name, status_name))
        if code is None or pd.isna(code):
            code = by_event.get(event_name)
        if code is not None and pd.notna(code):
            codes.at[index] = code

    return codes


def _classify_planning_stops(stops):
    stops = stops.rename(columns={'Code': 'Event_Code'}).reset_index(drop=True)
    stops['Status'] = stops['Status'].replace({
        'Manutenção Parada': 'Manutenção',
        'Manutenção Produtiva': 'Manutenção'
    })
    stops['Event_Code'] = _infer_planning_event_codes(stops)
    stops['Status'] = stops['Event_Code'].map(_STOP_AREAS).fillna(stops['Status'])
    return stops


# PAGINA PRINCIPAL DA APLICAÇÃO
@operation_planning_bp.route('/op/plano', methods=['GET'])
def planning_get():
    return render_template('operation.planning/planning_main.html')


# PAGINA ESPECIFICA DE CADA ÁREA
@operation_planning_bp.route('/op/plano/area/<int:areaId>', methods=['GET'])
def planning_area_get(areaId):

    if areaId == 2:
        return redirect('/op/plano/area/1')

    now = datetime.now()

    areaName = _MAP_AREA_SLIDES[areaId] if areaId not in [1,2] else 'Movimentação e Material'
    areaList = [_MAP_AREA_SLIDES[areaId]] if areaId not in [1,2] else ['Movimentação', 'Material']

    return render_template(f'operation.planning/planning_area{areaId}.html'
                           , areaId=areaId, areaName=areaName, areaList=areaList
                           , year=now.isocalendar()[0], week=now.isocalendar()[1])

@operation_planning_bp.route('/op/plano/area/<int:areaId>', methods=['POST'])
def planning_area_post(areaId):

    try:
        filter_year = int(request.args.get('year', 2024))
        filter_week = int(request.args.get('week', 1))
        if filter_year <= 0 or filter_week <= 0:
            raise ValueError("Ano ou semana inválidos.")
        selected_week_start = datetime.fromisocalendar(filter_year, filter_week, 1)
    except (ValueError, KeyError):
            return {"error": "Parâmetros inválidos. Forneça 'year' e 'week' válidos."}, 400

    # Chave YYYY/WW (2 dígitos) para bater com Time_Group da SP e DATA das paradas
    week_key = f"{filter_year}/{filter_week:02d}"

    if request.args['type'] == 'graph':

        last_week_start = selected_week_start - timedelta(weeks=3)
        # Um único corte para as duas fontes evita diferenças em status abertos.
        window_end = min(selected_week_start + timedelta(days=7), datetime.now())
        last_week_start_iso = last_week_start.strftime('%Y-%m-%d %H:%M:%S')
        current_week_end_exclusive_iso = window_end.strftime('%Y-%m-%d %H:%M:%S')


        actionPlan_query = f"""
                WITH deadline AS (
                    SELECT 
                        id
                        , type
                        , STRING_AGG(FORMAT(deadline, 'dd/MM/yyyy'), ', ') 
                            WITHIN GROUP (ORDER BY changeDate DESC) AS deadline
                    FROM JDT_OPE_PLANNING_DEADLINE
                    GROUP BY id, type
                ), userName AS (
                    SELECT 
                        id
                        , name
                    FROM JDT_USER_DETAILS
                ), events AS (
                    SELECT
                        planId
                        , STRING_AGG(description, ', ') AS relatedEvents
                    FROM (
                        SELECT DISTINCT planId, description 
                        FROM JDT_OPE_PLANNING_EVENT
                    ) AS unique_events
                    GROUP BY planId
                )

                SELECT 
                    T1.planId
                    , T1.id
                    , CASE WHEN T1.type = 0 THEN 'Contenção' ELSE 'Corretiva' END AS type
                    , T6.name AS responsible
                    , T5.name
                    , T1.text
                    , T1.istraining
                    , T1.status
                    , T2.deadline
                    , T3.deadline AS mainDeadline
                    , T4.description
                    , T4.presentationArea
                    , T4.presentationMotive
                    , T4.status AS planStatus
                    , T4.workcenter
                    , T4.[group] AS localGroup
                    , T7.relatedEvents

                FROM JDT_OPE_PLANNING_ACTION T1

                    LEFT JOIN deadline T2 ON T1.id = T2.id AND T2.type = 1
                    LEFT JOIN deadline T3 ON T1.planId = T3.id AND T3.type = 0
                    
                    LEFT JOIN (SELECT year, week, presentationArea, presentationMotive, description, id, status, createdBy, endDate, workcenter, [group] FROM JDT_OPE_PLANNING) T4 ON T1.planId = T4.id

                    LEFT JOIN userName T5 ON T1.userId = T5.id
                    LEFT JOIN userName T6 ON T4.createdBy = T6.id

                    LEFT JOIN events T7 ON T1.planId = T7.planId
                    
                WHERE T4.year = {request.args['year']} AND T4.week = {request.args['week']} AND T4.presentationMotive = {areaId}

                ORDER BY T1.createDate ASC;"""
            
        oldActionPlan_query = f"""
                WITH deadline AS (
                    SELECT 
                        id
                        , type
                        , STRING_AGG(FORMAT(deadline, 'dd/MM/yyyy'), ', ') 
                            WITHIN GROUP (ORDER BY changeDate DESC) AS deadline
                    FROM JDT_OPE_PLANNING_DEADLINE
                    GROUP BY id, type
                ), userName AS (
                    SELECT 
                        id
                        , name
                    FROM JDT_USER_DETAILS
                ), events AS (
                    SELECT
                        planId
                        , STRING_AGG(description, ', ') AS relatedEvents
                    FROM (
                        SELECT DISTINCT planId, description 
                        FROM JDT_OPE_PLANNING_EVENT
                    ) AS unique_events
                    GROUP BY planId
                )

                SELECT 
                    T1.planId
                    , T1.id
                    , CASE WHEN T1.type = 0 THEN 'Contenção' ELSE 'Corretiva' END AS type
                    , T6.name AS responsible
                    , T5.name
                    , T1.text
                    , T1.istraining
                    , T1.status
                    , T2.deadline
                    , T3.deadline AS mainDeadline
                    , T4.description
                    , T4.presentationArea
                    , T4.presentationMotive
                    , T4.status AS planStatus
                    , T4.workcenter
                    , T4.[group] AS localGroup
                    , T7.relatedEvents

                FROM JDT_OPE_PLANNING_ACTION T1

                    LEFT JOIN deadline T2 ON T1.id = T2.id AND T2.type = 1
                    LEFT JOIN deadline T3 ON T1.planId = T3.id AND T3.type = 0
                    
                    LEFT JOIN (SELECT year, week, presentationArea, presentationMotive, description, id, status, createdBy, endDate, workcenter, [group] FROM JDT_OPE_PLANNING) T4 ON T1.planId = T4.id

                    LEFT JOIN userName T5 ON T1.userId = T5.id
                    LEFT JOIN userName T6 ON T4.createdBy = T6.id

                    LEFT JOIN events T7 ON T1.planId = T7.planId
                    
                WHERE 
                    (T4.year * 100 + T4.week) < ({request.args['year']} * 100 + {request.args['week']}) 
                    AND T4.presentationMotive = {areaId} 
                    AND (T4.endDate is NULL OR DATEPART(YEAR, T4.endDate) = {request.args['year']} AND DATEPART(WEEK, T4.endDate) = {request.args['week']})
                
                ORDER BY T1.createDate ASC;"""

        goal_query = f"""WITH RankedGoals AS (
                        SELECT 
                            presentationMotive
                            , presentationArea
                            , goal
                            , ROW_NUMBER() OVER (
                                PARTITION BY presentationMotive, presentationArea 
                                ORDER BY changeDate DESC
                            ) AS RowNum
                        FROM JDT_OPE_PLANNING_GOAL_MAIN
                    )
                    SELECT 
                        presentationMotive
                        , presentationArea
                        , goal
                    FROM RankedGoals
                    WHERE RowNum = 1;
                    """
        
        stops_payload = {
            'start_date': last_week_start_iso,
            'end_date': current_week_end_exclusive_iso,
            'w_name_plex': [],
            'w_name_mic': [],
            'w_group': ['Montagem', 'Usinagem', 'Soldagem', 'Pré-Fabricação'],
            'm_group': [],
            'm_event': [],
            'shift': ['1', '2', '3']
        }

        with ThreadPoolExecutor() as executor:
            stopped_event_future = executor.submit(
                get_planning_stops, stops_payload
            )
            actionPlan = executor.submit(engine_run_query, actionPlan_query, 'jdt')
            oldActionPlan = executor.submit(engine_run_query, oldActionPlan_query, 'jdt')
            goal = executor.submit(engine_run_query, goal_query, 'jdt')
            availability_future = executor.submit(
                get_weekly_planned_availability,
                last_week_start_iso, current_week_end_exclusive_iso
            )

        stopped_event = stopped_event_future.result()
        stopped_event = _classify_planning_stops(stopped_event[
            stopped_event['Shift'].isin(['Primeiro', 'Segundo', 'Terceiro'])
            | (
                stopped_event['Shift'].eq('A confirmar')
                & stopped_event['In_Planned_Time'].eq(True)
            )
        ])
        actionPlan = actionPlan.result()
        oldActionPlan = oldActionPlan.result()
        goal = goal.result()
        availability = availability_future.result()


        goal['presentationMotiveName'] = goal['presentationMotive'].map(_MAP_AREA_SLIDES)

        stopped_event['Log_Date'] = pd.to_datetime(
            stopped_event['Log_Date'],
            format='%d/%m/%Y %H:%M:%S',
            errors='coerce'
        )
        stopped_event['End_Date'] = pd.to_datetime(
            stopped_event['End_Date'],
            format='%d/%m/%Y %H:%M:%S',
            errors='coerce'
        )

        # Cada semana recebe somente os minutos que caem dentro dos seus limites.
        weekly_segments = []
        for _, stopped_row in stopped_event.iterrows():
            segment_start = stopped_row['Log_Date']
            event_end = stopped_row['End_Date']

            if pd.isna(segment_start) or pd.isna(event_end) or event_end <= segment_start:
                continue

            while segment_start < event_end:
                next_week_start = (
                    segment_start.normalize()
                    + pd.Timedelta(days=7 - segment_start.weekday())
                )
                segment_end = min(event_end, next_week_start)
                segment = stopped_row.copy()
                segment['Log_Date'] = segment_start
                segment['End_Date'] = segment_end
                segment['Log_Minutes'] = round(
                    (segment_end - segment_start).total_seconds() / 60.0,
                    2
                )
                segment['Planned_Log_Minutes'] = (
                    (segment_end - segment_start).total_seconds() / 60.0
                    if stopped_row['In_Planned_Time'] else 0.0
                )
                weekly_segments.append(segment)
                segment_start = segment_end

        if weekly_segments:
            stopped_event = pd.DataFrame(weekly_segments)
        else:
            stopped_event = stopped_event.iloc[0:0].copy()
            stopped_event['Planned_Log_Minutes'] = pd.Series(dtype=float)
        # DATA usa ano e semana ISO para todos os segmentos de parada.
        _week = stopped_event['Log_Date'].dt.isocalendar().week.astype(str).str.zfill(2)
        stopped_event['DATA'] = stopped_event['Log_Date'].dt.isocalendar().year.astype(str) + '/' + _week


        result_df = summarize_weekly_availability(
            stopped_event, availability, _MAP_AREA_SLIDES.values()
        )

        filtered_stopped_event = stopped_event[
            (stopped_event['DATA'] == week_key)
            & (stopped_event['Status'] == _MAP_AREA_SLIDES[areaId])
        ]

        grouped_area = result_df[result_df['MS'].isin([_MAP_AREA_SLIDES[areaId]])].rename(columns={'Log_Minutes_Percentage': 'Percentage', 'WEEK': 'Label'})
        
        # AGRUPAR DADOS DE PARADAS POR CENTRO
        if areaId != 5:
            grouped_wc = filtered_stopped_event.groupby(['Workcenter_Group', 'Workcenter_Name'], as_index=False).agg(
                Log_Minutes_Sum=('Log_Minutes', 'sum'),
                Log_Minutes_Count=('Log_Minutes', 'count')
            ).rename(columns={'Workcenter_Name': 'Label'})
        
        else:
            grouped_wc = filtered_stopped_event[filtered_stopped_event['Event'] == 'Processo'].groupby(['Workcenter_Group', 'Workcenter_Name'], as_index=False).agg(
                Log_Minutes_Sum=('Log_Minutes', 'sum'),
                Log_Minutes_Count=('Log_Minutes', 'count')
            ).rename(columns={'Workcenter_Name': 'Label'})     

        # AGRUPAR DADOS DE PARADA POR MOTIVO
        grouped_motive = filtered_stopped_event.groupby(['Workcenter_Group', 'Event'], as_index=False).agg(
            Log_Minutes_Sum=('Log_Minutes', 'sum'),
            Log_Minutes_Count=('Log_Minutes', 'count')
        ).rename(columns={'Event': 'Label'})

        filtered_results = result_df[(result_df["MS"] == _MAP_AREA_SLIDES[areaId]) & (result_df["WEEK"] == week_key)]

        # GERAR GRÁFICOS PADRÕES
        def process_workcenter(idx, wc):
            filtered_wc = grouped_wc[grouped_wc["Workcenter_Group"] == wc]
            filtered_motive = grouped_motive[grouped_motive["Workcenter_Group"] == wc]
            filtered_area = grouped_area[grouped_area["Workcenter_Group"] == wc]

            sum_value = filtered_motive["Log_Minutes_Sum"].sum()
            count_value = filtered_motive["Log_Minutes_Count"].sum()

            current_result = filtered_results[filtered_results['Workcenter_Group'] == wc]
            goal_percent = goal[
                (goal['presentationMotive'] == areaId) & (goal['presentationArea'] == idx)
            ]['goal']
            goal_value = None
            planned_sum = float(current_result['Log_Minutes_Sum'].sum())
            if (
                not current_result.empty and current_result['BaseValid'].all()
                and not goal_percent.empty and pd.notna(goal_percent.iloc[0])
            ):
                goal_value = float(
                    goal_percent.iloc[0] * current_result['PlannedMinutes'].iloc[0] / 100.0
                )

            return {
                f"totals{idx}": {
                    "sum": str(sum_value),
                    "count": str(count_value),
                    "goal": goal_value,
                    "planned_sum": planned_sum
                },
                f"barchart{idx * 3 + 1}": filtered_wc.nlargest(5, "Log_Minutes_Sum").to_dict(orient="records"),
                f"barchart{idx * 3 + 2}": filtered_motive.nlargest(5, "Log_Minutes_Sum").to_dict(orient="records"),
                f"barchart{idx * 3 + 3}": json_records(filtered_area),
            }

        graphs = {}
        workcenter_groups = ['Montagem', 'Usinagem', 'Soldagem', 'Pré-Fabricação']

        with ThreadPoolExecutor() as executor:
            results = executor.map(process_workcenter, range(len(workcenter_groups)), workcenter_groups)

        for result in results:
            graphs.update(result)

        data = {

                'totals': {
                    'sum': str(filtered_stopped_event['Log_Minutes'].sum()),
                    'count': str(filtered_stopped_event['Log_Minutes'].count()),
                },
                
                "general": {
                    "0": json_records(result_df[result_df['Workcenter_Group'] == 'Montagem']),
                    "1": json_records(result_df[result_df['Workcenter_Group'] == 'Usinagem']),
                    "2": json_records(result_df[result_df['Workcenter_Group'] == 'Soldagem']),
                    "3": json_records(result_df[result_df['Workcenter_Group'] == 'Pré-Fabricação'])
                },

                "area": graphs, 

                "goal": goal.to_dict(orient='records'),

                "actionPlan": actionPlan.to_dict(orient='records'),

                "oldActionPlan" : oldActionPlan.to_dict(orient='records')
            }
        

        if areaId == 5:

            specific_goal = f"""SELECT event, workcenter, goal FROM JDT_OPE_PLANNING_GOAL_SPECIFIC WHERE presentationMotive = 5"""
            specific_goal = engine_run_query(specific_goal, 'jdt')

            specific_goal['workcenter'] = specific_goal['workcenter'].astype(str)
            specific_goal['event'] = specific_goal['event'].astype(str)
            filtered_stopped_event['Workcenter_Key'] = filtered_stopped_event['Workcenter_Key'].fillna(0).astype(int).astype(str)
            filtered_stopped_event['Event_Code'] = filtered_stopped_event['Event_Code'].astype(str)

            def process_extra(s_goal, filtered_data, event_code, workcenter_group=None):
                """Filtra, agrupa e faz merge com specific_goal."""

                df = filtered_data[filtered_data['Event_Code'] == event_code]

                if workcenter_group:
                    df = df[df['Workcenter_Group'] == workcenter_group]

                df = df.groupby(['Event_Code', 'Workcenter_Name'], as_index=False).agg(
                    Workcenter_Key=('Workcenter_Key', 'first'),
                    Log_Minutes_Sum=('Log_Minutes', 'sum'),
                    Log_Minutes_Count=('Log_Minutes', 'count'),
                ).rename(columns={'Workcenter_Name': 'Label'})

                df = pd.merge(df, s_goal, how='left', left_on=['Event_Code', 'Workcenter_Key'], right_on=['event', 'workcenter'])
                df['Log_Minutes_Sum'] = df['Log_Minutes_Sum'] / df['Log_Minutes_Count']
                df['Log_Minutes_Count'] = df['goal'].fillna(0)
                
                return df.drop(columns=['workcenter', 'Workcenter_Key', 'event', 'goal']).to_dict('records')

            data['extra0'] = process_extra(specific_goal, filtered_stopped_event, '20', 'Usinagem')
            data['extra1'] = process_extra(specific_goal, filtered_stopped_event, '100', 'Soldagem')
            data['extra2'] = process_extra(specific_goal, filtered_stopped_event, '100', 'Pré-Fabricação')

        
        return jsonify(data)

    else:

        def get_month_range(filter_year, filter_week):
            # Obter a segunda-feira da semana fornecida
            monday = datetime.fromisocalendar(filter_year, filter_week, 1)
            # Primeiro dia do mês da segunda-feira
            first_day = datetime(monday.year, monday.month, 1)

            # Último dia da semana atual (domingo)
            end_of_week = monday + timedelta(days=6)
            # Último dia do mês da segunda-feira
            last_day_of_month = datetime(monday.year, monday.month, calendar.monthrange(monday.year, monday.month)[1])

            # Se o último dia da semana está no próximo mês, pega o último dia do mês
            if end_of_week.month != monday.month:
                last_day = last_day_of_month
            else:
                last_day = end_of_week

            end_exclusive = min(last_day + timedelta(days=1), datetime.now())
            return (
                monday.month, first_day.strftime('%Y-%m-%d %H:%M:%S'),
                end_exclusive.strftime('%Y-%m-%d %H:%M:%S')
            )

        target_month, first_day, end_exclusive = get_month_range(filter_year, filter_week)

        payload = {
            'start_date': first_day
            , 'end_date': end_exclusive
            , 'w_group': ['Montagem', 'Pré-Fabricação', 'Soldagem', 'Usinagem']
            , 'm_group': []
            , 'shift': ['1', '2', '3']
        }

        availability_diagnostic_enabled = areaId == 3 and request.args.get('diagnostic') == '1'

        with ThreadPoolExecutor() as executor:
            availability_future = executor.submit(get_planned_availability, first_day, end_exclusive)
            maintenance_future = executor.submit(get_planning_stops, payload, include_legacy=False)

        maintenance_stops = _classify_planning_stops(maintenance_future.result())
        maintenance_stops = maintenance_stops[maintenance_stops['Status'].eq('Manutenção')]
        merged_data, overall = summarize_monthly_availability(
            maintenance_stops, availability_future.result()
        )

        data = {
            'month': target_month,
            'extra': json_records(merged_data),
            'overall': overall
        }

        if availability_diagnostic_enabled:
            data['availability_zero_diagnostic'] = {
                'start_date': first_day,
                'end_date': end_exclusive,
                'source': 'TD_OEE_CalcularDisponibilidadePorCentro',
                'rows': json_records(merged_data[merged_data['CALC'].isna()])
            }

        return jsonify(data)


# PAGINA PARA CADASTRO E VISUALIZAÇÃO DAS METAS - FALTA EDITAR METAS ESPECIFICAS
@operation_planning_bp.route('/op/plano/metas/<int:motiveId>', methods=['GET'])
def planning_goals_get(motiveId):

    admin = '0'
    if p_goal.can():
        admin = '1'

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT 
                        T1.*,
                        T2.name AS userName
                    FROM JDT_OPE_PLANNING_GOAL_MAIN T1
                        JOIN JDT_USER_DETAILS T2 ON T1.userId = T2.id
                    
                    WHERE T1.presentationMotive = {motiveId}
                    
                    ORDER BY T1.changeDate DESC"""
        goal = pd.read_sql(query, cnnx)

        query = f"""SELECT 
                        T1.*,
                        T2.name AS userName
                    FROM JDT_OPE_PLANNING_GOAL_SPECIFIC T1
                        JOIN JDT_USER_DETAILS T2 ON T1.userId = T2.id
                    
                    WHERE T1.presentationMotive = {motiveId}
                    
                    ORDER BY T1.changeDate DESC"""
        goal_specific = pd.read_sql(query, cnnx)

    last_goals = goal.groupby('presentationArea').first().reset_index()    

    workcenters = getPlex('workcenters')
    workcenters = workcenters[workcenters['Active'] == 1][['Workcenter_Key', 'Workcenter_Code', 'Name']]

    events = getPlex('events')
    events = events[(events['Active'] == 1) & (~events['Code'].isna())]
    events['Code'] = events['Code'].astype(int)

    goal_specific = pd.merge(goal_specific, workcenters, left_on='workcenter', right_on='Workcenter_Key')

    return render_template('operation.planning/planning_goal.html', motiveId=motiveId, admin=admin
                            , areaName=_MAP_AREA_SLIDES[motiveId]
                            , goalAll=goal.to_json(orient='records')
                            , goalLast=last_goals.to_dict(orient='records')
                            , goalSpecific=goal_specific.to_dict(orient='records')
                            , workcenters=workcenters.to_dict(orient='records')
                            , events=events.sort_values(by='Code').to_dict(orient='records'))

@operation_planning_bp.route('/op/plano/metas/<int:motiveId>', methods=['POST'])
@p_goal.require(403)
def planning_goals_post(motiveId):
    
    payload = request.get_json()

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        if request.args['type'] == 'general':

            query = f"""
                        SELECT DISTINCT presentationArea,
                            FIRST_VALUE(goal) OVER (PARTITION BY presentationArea ORDER BY changeDate DESC) AS last_goal
                        FROM JDT_OPE_PLANNING_GOAL_MAIN
                        WHERE presentationMotive = {motiveId};"""
            last_goals = pd.read_sql(query, cnnx)


            def insertNewGoal(row):
                area = payload[f"area{int(row['presentationArea'])}"]
                if float(area) != row['last_goal']:
                    query = f"""INSERT INTO JDT_OPE_PLANNING_GOAL_MAIN VALUES (
                                    {motiveId}, {int(row['presentationArea'])}, {area}, 
                                    GETDATE(), '{current_user.id}'
                                )"""
                    cnnx.execute(text(query))

            last_goals.apply(insertNewGoal, axis=1) 
        
        elif request.args['type'] == 'specific':

            query = f"""INSERT INTO JDT_OPE_PLANNING_GOAL_SPECIFIC VALUES (
                            {motiveId}, {payload['type']}, {payload['event']}, '{payload['workcenter']}', {payload['goal']}, GETDATE(), '{current_user.id}'
                        )"""
            cnnx.execute(text(query))

        cnnx.commit()

    return jsonify({
        "msg": "commited",
    }), 200           


# ROTAS VOLTADAS PARA CRUD DE PLANO DE AÇÃO

# PAGINA PARA CADASTRO E VISUALIZAÇÃO DAS METAS
@operation_planning_bp.route('/op/plano/novo', methods=['GET'])
def planning_new_get():
    workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]

    events = getPlex('events')
    events = events[~events['Code'].isna()]
    events['Code'] = events['Code'].astype(int)

    now = datetime.now()

    return render_template('operation.planning/planning_new.html'
                            , workcenters=workcenters.sort_values(by='Workcenter_Code').to_dict(orient="records")
                            , events=events.sort_values(by='Code').to_dict(orient='records')
                            , week=now.isocalendar()[1] - 2)

@operation_planning_bp.route('/op/plano/novo', methods=['POST'])
def planning_new_post():

    if request.args['type'] == 'data':

        payload = request.get_json()

        payload['start_date'] = payload['start_date'].replace('T', ' ') + ':00'
        payload['end_date'] = payload['end_date'].replace('T', ' ') + ':00'

        data = getStopsData(payload)

        return data.to_json(orient='records')

    else:

        payload = request.get_json()

        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            query = f"""SELECT COALESCE(max(id) + 1, 0) AS new FROM JDT_OPE_PLANNING"""
            new = pd.read_sql(query, cnnx)['new'][0]

            query = f"""INSERT INTO JDT_OPE_PLANNING VALUES (
                    {new}, '{current_user.id}', GETDATE(), NULL, YEAR(GETDATE()), {payload['p_week']}, '{json.dumps(payload['areas'])}', '{json.dumps(payload['workcenters'])}',
                    '{payload['description']}', 0, {payload['p_ms']}, {payload['p_area']}
            )"""
            cnnx.execute(text(query))

            query = f"""INSERT INTO JDT_OPE_PLANNING_DEADLINE VALUES (
                            {new}, '{payload['deadline']}', 'Prazo Inicial', GETDATE(), 0

            )"""
            cnnx.execute(text(query))

            if payload['relatedStops'] != {}:
                events = pd.DataFrame.from_dict(data=payload['relatedStops'], orient='index')
                events['Log_Date'] = pd.to_datetime(events['Log_Date'], format='%d/%m/%Y %H:%M:%S')
                events['End_Date'] = pd.to_datetime(events['End_Date'], format='%d/%m/%Y %H:%M:%S')


                def insertEvents(row):
                    query = f"""
                        INSERT INTO JDT_OPE_PLANNING_EVENT VALUES (
                            {new}, {row['Log_Key']}, '{row['Workcenter_Name']}', '{row['Event']}', 
                            '{row['Log_Date']}', '{row['End_Date']}', '{row['Log_Minutes']}', {row['Plex']}
                        )
                    """
                    cnnx.execute(text(query))

                events.apply(insertEvents, axis=1)

            cnnx.commit()

        return jsonify({
            "id": str(new),
        }), 200           


# PAGINA PARA CONSULTA DE PLANOS DE AÇÕES
@operation_planning_bp.route('/op/plano/historico', methods=['GET'])
def planning_history_get():

    this_week = datetime.now().date()
    last_week = this_week - timedelta(weeks=2)

    return render_template('operation.planning/planning_history_action.html', this_week=this_week, last_week=last_week)

@operation_planning_bp.route('/op/plano/historico', methods=['POST'])
def planning_history_post():

    toFilter = request.get_json()

    query = f"""
                WITH ResponsibleCTE AS (
                    SELECT 
                        T01.planId,
                        '[' + STRING_AGG('"' + T02.name + '"', ', ') + ']' AS responsible
                    FROM 
                        JDT_OPE_PLANNING_ACTION T01
                    LEFT JOIN 
                        JDT_USER_DETAILS T02 ON T01.userId = T02.id
                    GROUP BY 
                        T01.planId
                ),
                LatestDeadlineCTE AS (
                    SELECT 
                        T03.id,
                        T03.deadline,
                        T03.changeDate,
                        ROW_NUMBER() OVER (PARTITION BY T03.id ORDER BY T03.changeDate DESC) AS rn
                    FROM 
                        JDT_OPE_PLANNING_DEADLINE T03
                    WHERE T03.type = 0
                ),
                EventsCTE AS (
                    SELECT 
                        T05.planId,
                        '[' + STRING_AGG('"' + T05.description + '"', ', ') + ']' AS event
                    FROM (SELECT DISTINCT T04.planId, T04.description FROM JDT_OPE_PLANNING_EVENT T04) AS T05
                    GROUP BY T05.planId
                )
                

                SELECT 
                    T1.id,
                    T1.week,
                    T2.name,
                    T1.[group],
                    T1.workcenter,
                    ECTE.event,
                    T1.status,
                    T1.presentationMotive,
                    RCTE.responsible,
                    T1.description,
                    FORMAT(LCTE.deadline, 'dd/MM/yyyy') AS deadline
                FROM 
                    JDT_OPE_PLANNING T1
                LEFT JOIN 
                    JDT_USER_DETAILS T2 ON T1.createdBy = T2.id
                LEFT JOIN 
                    ResponsibleCTE RCTE ON T1.id = RCTE.planId
                LEFT JOIN 
                    LatestDeadlineCTE LCTE ON T1.id = LCTE.id AND LCTE.rn = 1
                LEFT JOIN 
                    EventsCTE ECTE ON T1.id = ECTE.planId
                WHERE 
                    (T1.year * 100 + T1.week) BETWEEN 
                        YEAR('{toFilter['last_week']}') * 100 +  DATEPART(WEEK, '{toFilter['last_week']}') AND 
                        (YEAR('{toFilter['this_week']}') * 100 +  DATEPART(WEEK, '{toFilter['this_week']}'))
            """
    data = engine_run_query(query, 'jdt')

    def concatenate_lists(row, column1, column2=None):

        if row[column1] == None:
            return ""
        
        combined = eval(row[column1])

        if column2:
            combined.extend(eval(row[column2]))

        combined = [item for item in combined if item]

        if len(combined) == 0:
            return ""
        elif len(combined) == 1:
            return combined[0]
        else:
            return ', '.join(combined[:-1]) + ' e ' + combined[-1]

    if not data.empty:
        data['local'] = data.apply(lambda row: concatenate_lists(row, 'workcenter', 'group'), axis=1)
        data['event'] = data.apply(lambda row: concatenate_lists(row, 'event'), axis=1)

        data['responsible'] = data.apply(lambda row: concatenate_lists(row, 'responsible'), axis=1)

        data['presentationMotive'] = data['presentationMotive'].map(_MAP_AREA_SLIDES)

    return data.to_json(orient='records')


# PAGINA PARA CONSULTA DE PLANOS DE AÇÕES
@operation_planning_bp.route('/op/plano/historico/responsaveis', methods=['GET'])
def planning_history_responsible_get():

    this_week = datetime.now().date()
    last_week = this_week - timedelta(weeks=2)

    return render_template('operation.planning/planning_history_responsible.html', this_week=this_week, last_week=last_week)
    
@operation_planning_bp.route('/op/plano/historico/responsaveis', methods=['POST'])
def planning_history_responsible_post():

    toFilter = request.get_json()

    query = f"""

                WITH LatestDeadlineCTE AS (
                    SELECT 
                        T03.id,
                        FORMAT(T03.deadline, 'dd/MM/yyyy') AS deadline,
                        T03.changeDate,
                        ROW_NUMBER() OVER (PARTITION BY T03.id ORDER BY T03.changeDate DESC) AS rn
                    FROM 
                        JDT_OPE_PLANNING_DEADLINE T03

                    WHERE type = 1
                )

                SELECT 
                    T1.*, T2.[description], T2.presentationMotive, T2.week, T3.name, T4.deadline

                FROM JDT_OPE_PLANNING_ACTION T1
                JOIN JDT_OPE_PLANNING T2 ON T1.planId = T2.id
                JOIN JDT_USER_DETAILS T3 ON T1.userId = T3.id
                JOIN LatestDeadlineCTE T4 ON T1.id = T4.id

                WHERE 
                    T1.createDate BETWEEN '{toFilter['last_week']}' AND '{toFilter['this_week']}'
            """
    data = engine_run_query(query, 'jdt')

    data['presentationMotive'] = data['presentationMotive'].map(_MAP_AREA_SLIDES)

    return data.to_json(orient='records')


# PAGINA PARA CONSULTA DE UM PLANO DE AÇÃO ESPECIFICO 
@operation_planning_bp.route('/op/plano/historico/<int:plan_id>', methods=['GET'])
def planning_history_detail_get(plan_id):

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT 
                        T1.createdBy,
                        T2.name, 
                        T2.companyEmail,
                        FORMAT(T1.createDate, 'dd/MM/yyyy') as createDate, 
                        T1.week, 
                        T1.description, 
                        T1.status,
                        T1.[group],
                        T1.workcenter,
                        T1.presentationMotive,
                        T1.presentationArea
                    FROM JDT_OPE_PLANNING AS T1 
                        JOIN JDT_USER_DETAILS AS T2 ON T1.createdBy = T2.id
                    
                    WHERE T1.id = {plan_id}"""
        general_info = pd.read_sql(query, cnnx)

        if len(general_info) == 0:
            abort(403)

        query = f"""SELECT FORMAT(deadline, 'dd/MM/yyyy') AS deadline, text FROM JDT_OPE_PLANNING_DEADLINE WHERE type = 0 AND id = {plan_id} ORDER BY changeDate DESC"""
        deadline_info = pd.read_sql(query, cnnx)

        query = f"""SELECT 
                        eventId AS Log_Key,
                        eventId AS Log_Key1,
                        workcenter AS Workcenter_Name,
                        description AS Event,
                        FORMAT(eventDate, 'dd/MM/yyyy HH:mm:ss') AS Log_Date,
                        FORMAT(eventDateEnd, 'dd/MM/yyyy HH:mm:ss') AS End_Date,
                        duration AS Log_Minutes,
                        systemType AS [Type]

                    FROM JDT_OPE_PLANNING_EVENT WHERE planId = {plan_id} ORDER BY eventDate DESC"""
        events_info = pd.read_sql(query, cnnx)

        query = f"""
                    SELECT 
                        T1.id, 
                        T1.type * 1 AS type, 
                        T2.companyEmail,
                        T2.name, 
                        T1.text, 
                        T1.istraining * 1 AS istraining, 
                        T1.status,
                        T1.refuseText
                    FROM JDT_OPE_PLANNING_ACTION T1
                    LEFT JOIN (SELECT name, id, companyEmail FROM JDT_USER_DETAILS) T2 ON T1.userId = T2.id
                    WHERE T1.planId = {plan_id} 
                    ORDER BY T1.createDate DESC;
                """
        action_info = pd.read_sql(query, cnnx)

        query = f"""SELECT FORMAT(T1.deadline, 'dd/MM/yyyy') AS deadline, T1.text, T1.id 
                    FROM JDT_OPE_PLANNING_DEADLINE AS T1
                        JOIN JDT_OPE_PLANNING_ACTION T2 ON T1.id = T2.id AND T1.type = 1
                    
                    WHERE T2.planId = {plan_id} ORDER BY T1.changeDate DESC"""
        action_deadline = pd.read_sql(query, cnnx)

        query = f"""SELECT companyEmail FROM JDT_USER_DETAILS WHERE generic = 0 AND active = 1 AND companyName LIKE 'Jost%'"""
        users_info = pd.read_sql(query, cnnx)


    general_info['presentationMotiveDesc'] = general_info['presentationMotive'].map(_MAP_AREA_SLIDES)
    general_info['presentationAreaDesc'] = general_info['presentationArea'].map({0: 'Montagem', 1: 'Usinagem', 2 : 'Soldagem', 3: 'Pré-Fabricação'})

    admin = '0'
    if current_user.id == general_info['createdBy'][0]:
        admin = '1'
    if current_user.admin:
        admin = '2'

    workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]

    events = getPlex('events')
    events = events[~events['Code'].isna()]
    events['Code'] = events['Code'].astype(int)

    return render_template('operation.planning/planning_detail.html'
                                , current_user_email=current_user.companyEmail
                                , create_user_email=general_info['companyEmail'][0]
                                , plan_id=plan_id, admin=admin
                                , name=general_info['name'][0]
                                , createDate=general_info['createDate'][0]
                                , week=general_info['week'][0]
                                , description=general_info['description'][0]
                                , status=general_info['status'][0]
                                , impacted_areas=eval(general_info['group'][0])
                                , impacted_workcenters=eval(general_info['workcenter'][0])
                                , action_deadline=action_deadline.to_json(orient='records')
                                , deadline_info=deadline_info.to_json(orient='records')
                                , events_info=events_info.set_index("Log_Key1").to_dict(orient="index")
                                , action_info=action_info.to_json(orient='records')
                                , presentationMotiveDesc=general_info['presentationMotiveDesc'][0]
                                , presentationMotive=general_info['presentationMotive'][0]
                                , presentationAreaDesc=general_info['presentationAreaDesc'][0]
                                , presentationArea=general_info['presentationArea'][0]
                                , workcenters=workcenters.sort_values(by='Workcenter_Code').to_dict(orient="records")
                                , events=events.sort_values(by='Code').to_dict(orient='records')
                                , users_info=users_info.sort_values(by='companyEmail').to_dict(orient='records')) 

# PAGINA PARA CONSULTA DE UM PLANO DE AÇÃO ESPECIFICO 
@operation_planning_bp.route('/op/plano/historico/<int:plan_id>', methods=['POST'])
def planning_history_detail_post(plan_id):

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT createdBy, description FROM JDT_OPE_PLANNING WHERE id = {plan_id}"""
        info = pd.read_sql(query, cnnx)

        payload = request.get_json()

        if info['createdBy'][0] != current_user.id:
            
            if 'refuse' in payload:

                query = f"""SELECT userId FROM JDT_OPE_PLANNING_ACTION WHERE id = {payload['id']}"""
                responsible = pd.read_sql(query, cnnx)['userId'][0]

                if responsible == current_user.id or current_user.admin:
                    query = f"""UPDATE JDT_OPE_PLANNING_ACTION SET
                                    status = -1,
                                    refuseText = '{payload['refuse']}',
                                    endDate = GETDATE()
                                WHERE id = {payload['id']}
                        """
                    
                    cnnx.execute(text(query))
                    cnnx.commit()

                    return jsonify({
                        "id": "success",
                    }), 200

            if not current_user.admin:
                return {"error": "Sem permissão."}, 403

        if request.args['type'] == 'stops':

            # Criar o DataFrame a partir do payload
            events = pd.DataFrame.from_dict(data=payload['relatedStops'], orient='index')

            query = f"""
                SELECT eventId FROM JDT_OPE_PLANNING_EVENT WHERE planId = {plan_id}
            """
            existing_events = pd.read_sql(query, cnnx)['eventId'].tolist()

            if events.empty:
                # Se estiver vazio, deletar todos os eventos do banco para o plano correspondente
                query = f"""
                    DELETE FROM JDT_OPE_PLANNING_EVENT WHERE planId = {plan_id}
                """
                cnnx.execute(text(query))
            else:
                existing_events_set = set(existing_events)  # Converter para um conjunto para busca rápida

                # Obter o conjunto de Log_Keys do DataFrame
                current_events_set = set(events['Log_Key'])

                # Identificar os eventos a serem deletados (existem no banco, mas não no DataFrame)
                events_to_delete = existing_events_set - current_events_set

                # Deletar os eventos que não estão mais no DataFrame
                if events_to_delete:
                    ids_to_delete = ", ".join(map(str, events_to_delete))  # Converter para uma string separada por vírgulas
                    query = f"""
                        DELETE FROM JDT_OPE_PLANNING_EVENT 
                        WHERE planId = {plan_id} AND eventId IN ({ids_to_delete})
                    """
                    cnnx.execute(text(query))

                # Filtrar apenas os eventos que precisam ser inseridos (não estão no banco)
                new_events = events[~events['Log_Key'].isin(existing_events_set)]

                # Inserir os eventos em batch
                if not new_events.empty:

                    new_events['Log_Date'] = pd.to_datetime(new_events['Log_Date'], format='%d/%m/%Y %H:%M:%S')
                    new_events['End_Date'] = pd.to_datetime(new_events['End_Date'], format='%d/%m/%Y %H:%M:%S')

                    for _, row in new_events.iterrows():
                        query = f"""
                            INSERT INTO JDT_OPE_PLANNING_EVENT VALUES (
                                {plan_id}, {row['Log_Key']}, '{row['Workcenter_Name']}', '{row['Event']}', 
                                '{row['Log_Date']}', '{row['End_Date']}', '{row['Log_Minutes']}', {row['Plex']}
                            )
                        """
                        cnnx.execute(text(query))

        elif request.args['type'] == 'edit': 
            
            if 'cancel' in payload:
                query = f"""UPDATE JDT_OPE_PLANNING SET
                            status = -2,
                            endDate = GETDATE()

                        WHERE id = {plan_id}"""
                cnnx.execute(text(query))

            else: 
                
                extra = 'endDate = NULL'
                if str(int(payload['status'])) == '100':
                    query = f"""SELECT 
                                    MIN(status) AS minStatus
                                FROM JDT_OPE_PLANNING_ACTION WHERE planId = {plan_id} AND status != -2"""
                    
                    if pd.read_sql(query, cnnx)['minStatus'][0] != 100:
                        return {"error": "Existem ações pendentes, não é possível finalizar."}, 409
                    
                    extra = 'endDate = GETDATE()'
                    

                query = f"""UPDATE JDT_OPE_PLANNING SET
                                week = {payload['p_week']},
                                presentationMotive = {payload['p_ms']},
                                presentationArea = {payload['p_area']},
                                description = '{payload['description']}',
                                [group] = '{json.dumps(payload['areas'])}',
                                workcenter = '{json.dumps(payload['workcenters'])}',
                                status = {payload['status']},
                                {extra}

                            WHERE id = {plan_id}"""
                cnnx.execute(text(query))

                if 'justifyText' in payload:
                    query = f"""INSERT INTO JDT_OPE_PLANNING_DEADLINE VALUES (
                                    {plan_id}, '{payload['deadline']}', '{payload['justifyText']}', GETDATE(), 0
                        )"""

                    cnnx.execute(text(query))

        elif request.args['type'] == 'action':

            if 'cancel' in payload:
                query = f"""UPDATE JDT_OPE_PLANNING_ACTION SET
                                status = -2,
                                endDate = GETDATE()
                            WHERE id = {payload['id']}
                    """
                cnnx.execute(text(query))

            elif 'id' in payload:

                extra = 'endDate = NULL'
                if payload['status'] == '100':
                    if payload['training'] == '1':
                        group_folder = os.path.join('app', 'static', 'uploads', 'operation', 'plan', str(plan_id), str(payload['id']))

                        if not os.path.exists(group_folder) or not os.path.isdir(group_folder):
                            return jsonify({
                                "error": "Nenhuma evidência de conclusão do treinamento foi anexada."
                            }), 404
                        
                        if len(os.listdir(group_folder)) == 0:
                            return jsonify({
                                "error": "Nenhuma evidência de conclusão do treinamento foi anexada."
                            }), 422
                    
                    extra = 'endDate = GETDATE()'

                query = f"""SELECT userId FROM JDT_OPE_PLANNING_ACTION WHERE id = {payload['id']}"""
                past_user = pd.read_sql(query, cnnx)['userId'][0]

                query = f"""SELECT id FROM JDT_USER_DETAILS WHERE companyEmail = '{payload['user']}'"""
                new_user = pd.read_sql(query, cnnx)['id'][0]

                query = f"""UPDATE JDT_OPE_PLANNING_ACTION SET 
                                [type] = {payload['type']},
                                [text] = '{payload['text']}',
                                userId = '{new_user}', 
                                isTraining = {payload['training']}, 
                                [status] = {payload['status']},
                                {extra}
                            WHERE id = {payload['id']}
                    """
                cnnx.execute(text(query))

                if payload['justifyText'] != '':
                    query = f"""INSERT INTO JDT_OPE_PLANNING_DEADLINE VALUES (
                                    {payload['id']}, '{payload['deadline']}', '{payload['justifyText']}', GETDATE(), 1
                        )"""
                    cnnx.execute(text(query))

                if past_user != new_user and new_user != current_user.id:
                    msg = Message(f"Operation Meeting - Plano de Ação",
                                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                    recipients=[payload['user']])

                    msg.html = render_template('operation.planning/planning_email_action_new.html',
                                            userName=current_user.name,
                                            planDescription=info['description'][0],
                                            actionType=payload['type'],
                                            actionDescription=payload['text'],
                                            actionDeadline=payload['deadline'],
                                            planId=plan_id)
                    mail.send(msg)

            else:

                query = f"""SELECT COALESCE(max(id) + 1, 0) AS new FROM JDT_OPE_PLANNING_ACTION"""
                new = pd.read_sql(query, cnnx)['new'][0]

                query = f"""SELECT id FROM JDT_USER_DETAILS WHERE companyEmail = '{payload['user']}'"""
                user = pd.read_sql(query, cnnx)['id'][0]

                if payload['status'] == '100':
                    return jsonify({
                        "error": "Não é permitido criar com status 100."
                    }), 403
                                    
                query = f"""INSERT INTO JDT_OPE_PLANNING_ACTION VALUES (
                                {new}, {plan_id}, {payload['type']}, '{user}', '{payload['text']}', {payload['training']}, {payload['status']}, GETDATE(), NULL, NULL
                    )"""
                cnnx.execute(text(query))

                query = f"""INSERT INTO JDT_OPE_PLANNING_DEADLINE VALUES (
                                {new}, '{payload['deadline']}', 'Prazo Inicial', GETDATE(), 1
                    )"""
                cnnx.execute(text(query))

                if payload['user'] != current_user.companyEmail:

                    msg = Message(f"Operation Meeting - Plano de Ação",
                                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                    recipients=[payload['user']])

                    msg.html = render_template('operation.planning/planning_email_action_new.html',
                                            userName=current_user.name,
                                            planDescription=info['description'][0],
                                            actionType=payload['type'],
                                            actionDescription=payload['text'],
                                            actionDeadline=payload['deadline'],
                                            planId=plan_id)
                    mail.send(msg)
        
        cnnx.commit()

    return jsonify({
        "id": "success",
    }), 200


# PAGINA PARA UPLOAD, DOWNLOAD E DELETE DE ARQUIVOS
@operation_planning_bp.route('/op/plano/historico/<int:plan_id>/<int:action>/files', methods=['GET', 'POST'])
def planning_history_detail_files(plan_id, action):

    group_folder = os.path.join('app', 'static', 'uploads', 'operation', 'plan', str(plan_id), str(action))

    if request.method == 'GET':

        if not os.path.exists(group_folder):
            return jsonify([]), 200

        files = os.listdir(group_folder)
        files_info = []
        for filename in files:
            file_path = os.path.join(group_folder, filename)
            if os.path.isfile(file_path):
                files_info.append({
                    'name': filename,
                    'size': round(os.path.getsize(file_path) / 1024, 2)  # Tamanho em KB
                })
        return jsonify(files_info)
    
    else:

        if request.args['type'] == 'download':

            data = request.json
            if 'file' not in data:
                return "File path is required", 400

            file_path = os.path.join(group_folder, data['file'])
            if not os.path.exists(file_path):
                return "File not found", 404

            return send_file(file_path, as_attachment=True)      

        elif request.args['type'] == 'delete':

            query = f"""SELECT T1.createdBy FROM JDT_OPE_PLANNING AS T1 WHERE T1.id = {plan_id}"""
            createdBy = engine_run_query(query, 'jdt')['createdBy'][0]

            if createdBy != current_user.id and not current_user.admin:
                abort(403)


            data = request.json
            if 'file' not in data:
                return "File path is required", 400

            file_path = os.path.join(group_folder, data['file'])

            if not os.path.exists(file_path):
                return "File not found", 404

            os.remove(file_path)
            return "File deleted", 200
        
        else:

            query = f"""SELECT T1.createdBy FROM JDT_OPE_PLANNING AS T1 WHERE T1.id = {plan_id}"""
            createdBy = engine_run_query(query, 'jdt')['createdBy'][0]

            if createdBy != current_user.id and not current_user.admin:
                abort(403)

            if not os.path.exists(group_folder):
                os.makedirs(group_folder)

            files = request.files.getlist("files")
            for file in files:
                original_name = file.filename
                file_path = os.path.join(group_folder, original_name)

                # Verifica se o arquivo já existe
                if os.path.exists(file_path):
                    name, ext = os.path.splitext(original_name)  # Divide o nome e a extensão
                    counter = 1

                    while os.path.exists(file_path):
                        file_path = os.path.join(group_folder, f"{name}_{counter}{ext}")
                        counter += 1

                file.save(file_path)

            return "Upload successful", 200

# V2
