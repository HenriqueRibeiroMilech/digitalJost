"""Relatório de manutenção com a mesma base TD do Operation Meeting."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import pandas as pd

from app.utils.db_utils import engine_run_query
from app.utils.dynamic_constants import getPlex
from app.utils.planning_availability import (
    WORKCENTER_GROUPS, _UNASSIGNED_SHIFT_WORKCENTER, classify_planning_stops,
    get_planned_availability, get_planning_stops, json_records,
    summarize_monthly_availability
)


def maintenance_event_catalog():
    catalog = getPlex('events').dropna(subset=['Code']).reset_index(drop=True).copy()
    classified = classify_planning_stops(catalog.rename(columns={
        'Description': 'Event', 'Workcenter_Event_Group': 'Status'
    }))
    catalog = catalog[classified['Status'].eq('Manutenção')].copy()
    catalog['Code'] = pd.to_numeric(catalog['Code'], errors='coerce')
    catalog = catalog.dropna(subset=['Code'])
    catalog['Code'] = catalog['Code'].astype(int)
    return catalog


def _periods(start, end, group):
    periods = []
    current = pd.Timestamp(start)
    end = pd.Timestamp(end)
    while current < end:
        if group == '0':
            boundary = current.normalize() + pd.Timedelta(days=1)
            label = current.strftime('%Y-%m-%d')
        elif group == '1':
            boundary = current.normalize() + pd.Timedelta(days=7 - current.weekday())
            year, week, _ = current.isocalendar()
            label = f'{year}/{week:02d}'
        elif group == '2':
            boundary = (current + pd.offsets.MonthBegin(1)).normalize()
            label = current.strftime('%Y/%m')
        elif group == '3':
            boundary = pd.Timestamp(datetime(current.year + 1, 1, 1))
            label = current.strftime('%Y')
        else:
            boundary = end
            label = 'Livre'
        period_end = min(boundary, end)
        periods.append({'label': label, 'start': current, 'end': period_end})
        current = period_end
    return periods


def _grouped_base(periods, availability, shift_list, include_unassigned):
    """Uma leitura para todos os períodos; não chama uma proc por dia."""
    data = engine_run_query("""
        ;WITH Periodos AS (
            SELECT Time_Group, Inicio, Fim
            FROM OPENJSON(:periods) WITH (
                Time_Group NVARCHAR(20) '$.label',
                Inicio DATETIME '$.start',
                Fim DATETIME '$.end'
            )
        ), StatusJanela AS (
            SELECT S.Workcenter AS Workcenter_Code, P.Time_Group,
                S.ProductionStatus, S.PlannedProductionTime,
                DATEDIFF(SECOND,
                    CASE WHEN S.StatusBegin < P.Inicio THEN P.Inicio ELSE S.StatusBegin END,
                    CASE WHEN ISNULL(S.StatusEnd, :end_date) > P.Fim
                        THEN P.Fim ELSE ISNULL(S.StatusEnd, :end_date) END
                ) / 60.0 AS Minutos
            FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_Current_Status] AS S
            JOIN Periodos AS P ON S.StatusBegin < P.Fim
                AND (S.StatusEnd > P.Inicio OR S.StatusEnd IS NULL)
            WHERE S.Workcenter IN (
                SELECT TRIM(value) FROM STRING_SPLIT(:workcenter_list, ',')
            ) AND (
                S.CurrentShift IN (
                    SELECT TRIM(value) FROM STRING_SPLIT(:shift_list, ',')
                ) OR (
                    :include_unassigned = 1 AND S.Workcenter = :unassigned_workcenter
                    AND NULLIF(LTRIM(RTRIM(S.CurrentShift)), N'') IS NULL
                    AND S.PlannedProductionTime = 1
                )
            )
        )
        SELECT Workcenter_Code, Time_Group,
            SUM(CASE WHEN PlannedProductionTime = 1 THEN Minutos ELSE 0 END)
                AS PlannedMinutes,
            SUM(CASE WHEN ProductionStatus = 1 THEN Minutos ELSE 0 END)
                AS RunMinutes
        FROM StatusJanela
        WHERE Minutos > 0
        GROUP BY Workcenter_Code, Time_Group
    """, 'plex', {
        'periods': json.dumps([{
            'label': p['label'], 'start': p['start'].strftime('%Y-%m-%dT%H:%M:%S'),
            'end': p['end'].strftime('%Y-%m-%dT%H:%M:%S')
        } for p in periods]),
        'end_date': periods[-1]['end'].strftime('%Y-%m-%d %H:%M:%S'),
        'workcenter_list': ','.join(availability['Workcenter_Code']),
        'shift_list': shift_list,
        'include_unassigned': int(include_unassigned),
        'unassigned_workcenter': _UNASSIGNED_SHIFT_WORKCENTER
    })
    data['Workcenter_Code'] = data['Workcenter_Code'].astype(str).str.strip()
    metadata = availability[['Workcenter_Code', 'Workcenter_Name', 'Workcenter_Group']]
    grid = metadata.merge(pd.DataFrame({'Time_Group': [p['label'] for p in periods]}), how='cross')
    grid = grid.merge(data, on=['Workcenter_Code', 'Time_Group'], how='left', validate='one_to_one')
    for column in ('PlannedMinutes', 'RunMinutes'):
        grid[column] = pd.to_numeric(grid[column], errors='coerce')
        grid[column] = grid[column].where(grid[column].ge(0) & grid[column].lt(float('inf')))
    return grid


def _overall(data, calc):
    stopped = float(data['Log_Minutes_Sum'].sum())
    count = int(data['Log_Minutes_Count'].sum())
    planned = data['PlannedMinutes'].sum(min_count=1)
    planned = float(planned) if pd.notna(planned) else None
    return {
        'CALC': calc, 'Log_Minutes_Sum': stopped, 'Log_Minutes_Count': count,
        'Availability': planned,
        'MTTR': stopped / count if calc is not None and count > 0 else None,
        'MTBF': (planned - stopped) / count if calc is not None and count > 0 else None
    }


def get_maintenance_availability_data(payload):
    if not isinstance(payload, dict):
        raise ValueError('Informe os filtros do relatório.')
    group = str(payload.get('time_group', '5'))
    if group not in {'0', '1', '2', '3', '5'}:
        raise ValueError('Agrupador inválido.')
    try:
        start = datetime.fromisoformat(payload['start_date'])
        selected_end = datetime.fromisoformat(payload['end_date'])
    except (KeyError, TypeError, ValueError):
        raise ValueError('Informe datas válidas de início e fim.') from None
    if start.tzinfo is not None or selected_end.tzinfo is not None:
        raise ValueError('Use datas e horários locais, sem fuso horário.')
    if start.second or start.microsecond or selected_end.second or selected_end.microsecond:
        raise ValueError('Informe as datas com precisão de minutos.')
    # datetime-local seleciona o último minuto inclusivo; as fontes TD usam fim exclusivo.
    end = selected_end + timedelta(minutes=1)
    if start >= end:
        raise ValueError('A data final deve ser posterior à inicial.')
    end = min(end, datetime.now().replace(microsecond=0))

    for field in ('shift', 'w_group', 'w_name_plex', 'w_name_mic', 'm_event'):
        if not isinstance(payload.get(field, []), list):
            raise ValueError('Filtros inválidos.')
        if any(not isinstance(value, (str, int)) or isinstance(value, bool) for value in payload.get(field, [])):
            raise ValueError('Filtros inválidos.')
    shifts = [str(value) for value in payload.get('shift', [])]
    if not shifts or not set(shifts).issubset({'1', '2', '3'}):
        raise ValueError('Selecione ao menos um turno válido.')
    aliases = {'1': ('Primeiro', 'Turno 1'), '2': ('Segundo', 'Turno 2'), '3': ('Terceiro', 'Turno 3')}
    shift_list = ','.join(alias for shift in sorted(set(shifts)) for alias in aliases[shift])
    include_unassigned = set(shifts) == {'1', '2', '3'}
    groups = payload.get('w_group', [])
    if not set(groups).issubset(WORKCENTER_GROUPS):
        raise ValueError('Área inválida.')

    catalog = getPlex('workcenters').copy()
    selected_keys = {str(value) for value in payload.get('w_name_plex', [])}
    codes = set(catalog.loc[catalog['Workcenter_Key'].astype(str).isin(selected_keys), 'Workcenter_Code'].dropna().astype(str).str.strip())
    # Compatibilidade com filtros salvos do relatório antigo: só códigos conhecidos no Plex.
    legacy_codes = {str(value).split('-', 1)[0].strip() for value in payload.get('w_name_mic', [])}
    codes.update(set(catalog['Workcenter_Code'].dropna().astype(str).str.strip()) & legacy_codes)
    effective_keys = catalog.loc[
        catalog['Workcenter_Code'].astype(str).str.strip().isin(codes), 'Workcenter_Key'
    ].dropna().astype(str).tolist()
    event_codes = {str(value).strip() for value in payload.get('m_event', [])}
    all_event_codes = set(maintenance_event_catalog()['Code'].astype(str))
    filter_events = bool(event_codes) and event_codes != all_event_codes
    start_text = start.strftime('%Y-%m-%d %H:%M:%S')
    end_text = end.strftime('%Y-%m-%d %H:%M:%S')
    source_payload = {
        'start_date': start_text, 'end_date': end_text, 'w_group': groups,
        'w_name_plex': effective_keys, 'w_name_mic': [], 'm_group': [],
        'm_event': [], 'shift': sorted(set(shifts))
    }
    with ThreadPoolExecutor(max_workers=2) as executor:
        base_future = executor.submit(
            get_planned_availability, start_text, end_text, workcenter_codes=codes,
            groups=groups, shift_list=shift_list, include_unassigned_shift=include_unassigned
        )
        stops_future = None
        if codes and groups and start < end:
            stops_future = executor.submit(
                get_planning_stops, source_payload, include_legacy=False,
                include_unassigned_shift=include_unassigned
            )
    availability = base_future.result()
    if stops_future is None:
        stops = pd.DataFrame(columns=[
            'Workcenter_Code', 'Workcenter_Name', 'Workcenter_Group', 'Log_Minutes',
            'Log_Date', 'End_Date', 'In_Planned_Time'
        ])
    else:
        stops = classify_planning_stops(stops_future.result())
        stops = stops[stops['Status'].eq('Manutenção') & stops['Workcenter_Code'].isin(codes)]
        if filter_events:
            stops = stops[stops['Event_Code'].isin(event_codes)]

    total_data, calc = summarize_monthly_availability(stops, availability)
    overall = _overall(total_data, calc)
    periods = _periods(start, end, group)
    if group == '5' or availability.empty or not periods:
        rows = total_data.copy()
        rows['Time_Group'] = 'Livre'
    else:
        grouped_base = _grouped_base(periods, availability, shift_list, include_unassigned)
        stops = stops.copy()
        stops['Log_Date'] = pd.to_datetime(stops['Log_Date'], format='%d/%m/%Y %H:%M:%S')
        stops['End_Date'] = pd.to_datetime(stops['End_Date'], format='%d/%m/%Y %H:%M:%S')
        frames = []
        for period in periods:
            segment = stops[
                stops['Log_Date'].lt(period['end']) & stops['End_Date'].gt(period['start'])
            ].copy()
            segment['Log_Minutes'] = (
                segment['End_Date'].clip(upper=period['end'])
                - segment['Log_Date'].clip(lower=period['start'])
            ).dt.total_seconds() / 60.0
            frame, _ = summarize_monthly_availability(
                segment, grouped_base[grouped_base['Time_Group'].eq(period['label'])]
            )
            frame['Time_Group'] = period['label']
            frames.append(frame)
        rows = pd.concat(frames, ignore_index=True)
    # Só oculta centros/períodos sem planejamento. Inconsistências com base positiva ficam visíveis.
    visible = rows[rows['PlannedMinutes'].gt(0) | rows['Log_Minutes_Sum'].gt(0)]
    return {
        'workcenters': json_records(visible.sort_values(['Time_Group', 'CALC'], ascending=[True, False])),
        'overall': overall,
        'period': {'start_date': start_text, 'end_date_exclusive': end_text}
    }
