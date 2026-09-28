"""Fontes e cálculos de disponibilidade do Operation Meeting, em minutos."""

from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from app.utils.business import getStopsData
from app.utils.db_utils import engine_run_query
from app.utils.dynamic_constants import getPlex


WORKCENTER_GROUPS = ('Montagem', 'Usinagem', 'Soldagem', 'Pré-Fabricação')
# A procedure de disponibilidade compara CurrentShift sem normalizar os nomes.
PLANNING_SHIFTS = 'Primeiro,Turno 1,Segundo,Turno 2,Terceiro,Turno 3'
_MINUTE_TOLERANCE = 0.000001  # Somente diferenças de ponto flutuante.


def get_planned_availability(start_date, end_date):
    workcenters = getPlex('workcenters')[[
        'Workcenter_Code', 'Name', 'Workcenter_Group'
    ]].copy()
    workcenters = workcenters[
        workcenters['Workcenter_Group'].isin(WORKCENTER_GROUPS)
    ].dropna(subset=['Workcenter_Code']).drop_duplicates()
    workcenters['Workcenter_Code'] = workcenters['Workcenter_Code'].astype(str).str.strip()
    workcenters['Workcenter_Name'] = (
        workcenters['Workcenter_Code']
        + workcenters['Name'].fillna('').apply(lambda name: f'-{name}' if name else '')
    )
    workcenters = workcenters.drop(columns='Name')

    if workcenters['Workcenter_Code'].duplicated().any():
        raise ValueError('Centro de trabalho com mais de um cadastro de área ou nome.')

    if pd.Timestamp(start_date) >= pd.Timestamp(end_date) or workcenters.empty:
        workcenters['PlannedMinutes'] = float('nan')
        workcenters['RunMinutes'] = float('nan')
        return workcenters

    data = engine_run_query("""
        EXEC [JOST_INTEGRATION_PRD].[dbo].[TD_OEE_CalcularDisponibilidadePorCentro]
            @data_inicio = :start_date,
            @data_fim = :end_date,
            @workcenter_list = :workcenter_list,
            @shift_list = :shift_list
    """, 'plex', {
        'start_date': start_date,
        'end_date': end_date,
        'workcenter_list': ','.join(workcenters['Workcenter_Code']),
        'shift_list': PLANNING_SHIFTS
    }).rename(columns={
        'Workcenter': 'Workcenter_Code',
        'Disponibilidade_Tempo_Planejado': 'PlannedMinutes',
        'Disponibilidade_Tempo_Produzindo': 'RunMinutes'
    })
    data['Workcenter_Code'] = data['Workcenter_Code'].astype(str).str.strip()
    # Não usamos Disponibilidade nem Tempo_Parado: incluem todas as categorias.
    data = workcenters.merge(
        data[['Workcenter_Code', 'PlannedMinutes', 'RunMinutes']],
        on='Workcenter_Code', how='left', validate='one_to_one'
    )
    for column in ('PlannedMinutes', 'RunMinutes'):
        data[column] = pd.to_numeric(data[column], errors='coerce')
        data[column] = data[column].where(
            data[column].ge(0) & data[column].lt(float('inf'))
        )
    return data


def get_weekly_planned_availability(start_date, end_date):
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    periods = []
    # A janela dos gráficos começa na segunda-feira de uma semana ISO.
    for offset in range(4):
        week_start = start + pd.Timedelta(weeks=offset)
        periods.append((week_start, min(week_start + pd.Timedelta(weeks=1), end)))

    def fetch_week(period):
        week_start, week_end = period
        data = get_planned_availability(week_start, week_end)
        iso_year, iso_week, _ = week_start.isocalendar()
        data['DATA'] = f'{iso_year}/{iso_week:02d}'
        return data

    with ThreadPoolExecutor(max_workers=4) as executor:
        return pd.concat(list(executor.map(fetch_week, periods)), ignore_index=True)


def get_planning_stops(payload, include_legacy=True):
    """Mantém rankings históricos; identifica quais paradas têm base planejada TD."""
    if pd.Timestamp(payload['start_date']) >= pd.Timestamp(payload['end_date']):
        return pd.DataFrame(columns=[
            'Log_Key', 'Workcenter_Key', 'Workcenter_Code', 'Workcenter_Name',
            'Workcenter_Group', 'Log_Date', 'End_Date', 'Log_Minutes', 'Code',
            'Status', 'Shift', 'Plex', 'Event', 'In_Planned_Time'
        ])

    stops = getStopsData(
        payload, use_current_status=True, include_all_statuses=True,
        include_legacy=include_legacy
    ).reset_index(drop=True)
    if 'Workcenter_Code' not in stops:
        stops['Workcenter_Code'] = pd.NA
    stops['Workcenter_Code'] = stops['Workcenter_Code'].astype('string').str.strip()
    td_rows = pd.to_numeric(stops['Plex'], errors='coerce').eq(1)
    target_codes = stops.loc[td_rows, 'Workcenter_Code'].dropna().drop_duplicates()
    if target_codes.empty:
        stops['In_Planned_Time'] = False
        return stops
    # A TD_OEE_ObterParadas não retorna PlannedProductionTime. Conferimos o
    # mesmo ID de status, sem alterar a procedure nem inferir pela categoria.
    planned_ids = engine_run_query("""
        SELECT ID
        FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_Current_Status]
        WHERE PlannedProductionTime = 1
            AND CanRunProduction = 0
            AND StatusBegin < :end_date
            AND (StatusEnd > :start_date OR StatusEnd IS NULL)
            AND Workcenter IN (
                SELECT TRIM(value) FROM STRING_SPLIT(:workcenter_list, ',')
            )
    """, 'plex', {
        'start_date': payload['start_date'],
        'end_date': payload['end_date'],
        'workcenter_list': ','.join(target_codes)
    })
    stops['In_Planned_Time'] = (
        td_rows
        & pd.to_numeric(stops['Log_Key'], errors='coerce').isin(
            pd.to_numeric(planned_ids['ID'], errors='coerce').dropna()
        )
    )
    return stops


def valid_planned_base(planned_minutes, stopped_minutes):
    return (
        planned_minutes.notna() & planned_minutes.gt(0)
        & stopped_minutes.le(planned_minutes + _MINUTE_TOLERANCE)
    )


def summarize_weekly_availability(stops, availability, categories):
    planned_stops = stops[stops['In_Planned_Time'].eq(True)]
    center_totals = planned_stops.groupby(
        ['Workcenter_Code', 'Workcenter_Group', 'DATA'], as_index=False
    ).agg(StoppedMinutes=('Planned_Log_Minutes', 'sum'))
    centers = availability.merge(
        center_totals, on=['Workcenter_Code', 'Workcenter_Group', 'DATA'], how='outer',
        validate='one_to_one'
    )
    centers['StoppedMinutes'] = centers['StoppedMinutes'].fillna(0)
    centers['InvalidBase'] = centers['StoppedMinutes'].gt(0) & (
        centers['PlannedMinutes'].isna()
        | centers['StoppedMinutes'].gt(centers['PlannedMinutes'] + _MINUTE_TOLERANCE)
    )
    base = centers.groupby(['Workcenter_Group', 'DATA'], as_index=False).agg(
        PlannedMinutes=('PlannedMinutes', lambda values: values.sum(min_count=1)),
        InvalidBase=('InvalidBase', 'any')
    )
    # Inclui 0% quando existe base e nenhuma parada; null quando falta base.
    grid = pd.DataFrame({'Status': list(categories)})
    result = base.merge(grid, how='cross').merge(
        planned_stops.groupby(
            ['Workcenter_Group', 'DATA', 'Status'], as_index=False
        ).agg(
            Log_Minutes_Sum=('Planned_Log_Minutes', 'sum'),
            Log_Minutes_Count=('Log_Minutes', 'count')
        ), on=['Workcenter_Group', 'DATA', 'Status'], how='left',
        validate='one_to_one'
    )
    result[['Log_Minutes_Sum', 'Log_Minutes_Count']] = result[[
        'Log_Minutes_Sum', 'Log_Minutes_Count'
    ]].fillna(0)
    result['BaseValid'] = result['PlannedMinutes'].gt(0) & ~result['InvalidBase']
    denominator = result['PlannedMinutes'].where(result['BaseValid'])
    result['Log_Minutes_Percentage'] = (
        result['Log_Minutes_Sum'] / denominator * 100.0
    ).round(10)
    return result.rename(columns={'DATA': 'WEEK', 'Status': 'MS'}).sort_values('WEEK')


def summarize_monthly_availability(stops, availability):
    planned_stops = stops[stops['In_Planned_Time'].eq(True)]
    events = planned_stops.groupby('Workcenter_Code', as_index=False).agg(
        Log_Minutes_Sum=('Log_Minutes', 'sum'),
        Log_Minutes_Count=('Log_Minutes', 'count'),
        Workcenter_Name=('Workcenter_Name', 'first'),
        Workcenter_Group=('Workcenter_Group', 'first')
    )
    data = availability.merge(
        events, on='Workcenter_Code', how='outer', validate='one_to_one',
        suffixes=('', '_event')
    )
    for column in ('Workcenter_Name', 'Workcenter_Group'):
        data[column] = data[column].combine_first(data[f'{column}_event'])
        data = data.drop(columns=f'{column}_event')
    data[['Log_Minutes_Sum', 'Log_Minutes_Count']] = data[[
        'Log_Minutes_Sum', 'Log_Minutes_Count'
    ]].fillna(0)
    valid = valid_planned_base(data['PlannedMinutes'], data['Log_Minutes_Sum'])
    denominator = data['PlannedMinutes'].where(valid)
    data['CALC'] = (1 - data['Log_Minutes_Sum'] / denominator).round(10)
    failures = data['Log_Minutes_Count'].where(data['Log_Minutes_Count'].gt(0))
    data['MTTR'] = (data['Log_Minutes_Sum'] / failures).where(valid)
    data['MTBF'] = ((denominator - data['Log_Minutes_Sum']) / failures).where(valid)
    # Campos mantidos em horas por compatibilidade com o JSON anterior.
    data['TotalAvail'] = data['PlannedMinutes'] / 60.0
    data['TotalRun'] = data['RunMinutes'] / 60.0
    data['Availability_Status'] = 'Calculado'
    data.loc[~valid, 'Availability_Status'] = 'Paradas excedem o tempo planejado'
    data.loc[data['PlannedMinutes'].eq(0), 'Availability_Status'] = 'Sem tempo planejado'
    data.loc[data['PlannedMinutes'].isna(), 'Availability_Status'] = 'Sem histórico na fonte TD'

    invalid_stops = data['Log_Minutes_Sum'].gt(0) & ~valid
    total_planned = data['PlannedMinutes'].sum(min_count=1)
    overall = None
    if pd.notna(total_planned) and total_planned > 0 and not invalid_stops.any():
        # Média ponderada pelo tempo, não média simples dos percentuais dos centros.
        overall = round(1 - float(data['Log_Minutes_Sum'].sum() / total_planned), 10)
    return data.sort_values('CALC', ascending=False, na_position='last'), overall


def json_records(data):
    """Ausência de base vira null JSON, nunca NaN, infinito ou 100% fictício."""
    return data.astype(object).where(pd.notna(data), None).to_dict(orient='records')
