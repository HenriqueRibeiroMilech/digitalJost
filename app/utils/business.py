import json
import pandas as pd


from app.utils.dynamic_constants import getPlex
from app.utils.db_utils import engine_run_query, get_engine

def getStopsData(received_data):
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

        LÓGICAS DE NEGOCIO: 
        1. Caso não seja enviado w_group. Os opcionais w_group, m_group e shift_plex ficarão vazios.

    """

    shift_filter = {"1": 'primeiro', "2": 'segundo', "3": 'terceiro', 'Extra': None}
    received_data["shift_plex"] = [shift_filter[shift] for shift in received_data["shift"] if shift_filter[shift] is not None]

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

    if received_data.get('m_event'):
        filters.append(f"T3.COD_PARADA IN {format_tuple(received_data['m_event'])}")

    conditions = []
    if received_data.get('w_name_mic'):
        conditions.append(f"T1.sDescription IN {format_tuple(received_data['w_name_mic'])}")

    if received_data.get('w_name_plex'):
        conditions.append(f"T2.CT_PLEX IN {format_tuple(received_data['w_name_plex'])}")

    workcenter_condition = f"({ ' OR '.join(conditions) })" if conditions else "(1=1)"

    filter_string = "AND " + " AND ".join(filters) if filters else ""

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

    data = pd.concat([event, mic_event])
    data['Code'] = data['Code'].astype(str)
    
    data = pd.merge(left=data, right=events_join, left_on='Code', right_on='Code').drop(columns=['Workcenter_Event_Key', 'Workcenter_Event_Group', 'Active']).rename(columns={"Description": "Event"})

    return data