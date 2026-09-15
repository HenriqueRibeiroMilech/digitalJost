import urllib
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine, text

from app.utils.constants import CNNX_FTM, CNNX_JDT, CNNX_PLEX

STOPS_FROM_AREAS = {
    '20-Troca de Insumo': 'Processos'
    , '31-Processo': 'Processos'
    , '37-Centralizacao de Bico': 'Processos'
    , '32-Troca de Graxa': 'Processos'
    , '43-Falta de Ferramenta de Usinagem': 'Processos'
    , '100-Setup': 'Processos'
    , '44-Sistema Indisponivel': 'Transformação Digital'
    , '3-Medicao': 'Qualidade'
    , '4-Problema de Qualidade': 'Qualidade'
    , '65-Problema de Qualidade - @1': 'Qualidade'
    , '19-Aguardando Inspecao': 'Qualidade'
    , '42-Retrabalho': 'Qualidade'
    , '-Falta de Saldo': 'Material'
}

def default(logger):

    engine_ftm = create_engine( f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_FTM)}",)
    engine_plex = create_engine( f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_PLEX)}",)

    def run_query(query, engine, params=None):
        return pd.read_sql(query, engine, params=params)

    stopped_machines_mic_query = f"""
                WITH mic_stops AS (
                    SELECT 
                        T1.sDescription AS Workcenter_Name
                        , T3.GRUPO AS Workcenter_Group
                        , T1.tStart AS Log_Date
                        , T1.dDuration
                        , CONCAT(T2.COD_PARADA, '-', T2.DESC_PARADA) AS Event
                        , T1.sEventDescription
                        , T2.CATEGORIA AS Status
                        , ROW_NUMBER() OVER (
                            PARTITION BY T1.sDescription 
                            ORDER BY T1.tStart DESC
                        ) AS row_num
                    FROM OEEQEventDetail T1
                    LEFT JOIN CADASTRO_PARADA T2 
                        ON T1.sReasonCode = T2.MOTIVO
                    INNER JOIN CONFIG_TABLET T3 
                        ON T1.sDescription = T3.NOME_MAQUINA
                    WHERE 
                        T1.tStart >= DATEADD(DAY, -30, GETDATE())
                        AND T1.dDuration > '00:00:01'
                        AND T1.sEventDescription <> 'Fim Produção'
                        AND T3.FL_ATIVO = 1
                        AND EXISTS (
                            SELECT 1
                            FROM OEEQEventDetail T4
                            WHERE 
                                T4.sDescription = T1.sDescription
                                AND T4.sEventDescription = 'Parada'
                                AND T4.tStart >= DATEADD(DAY, -30, GETDATE())
                        )
                )

                SELECT 
                    0 AS Workcenter_Key
                    , LEFT(Workcenter_Name, CHARINDEX('-', Workcenter_Name) - 1) AS Workcenter_Code
                    , SUBSTRING(Workcenter_Name, CHARINDEX('-', Workcenter_Name) + 1, LEN(Workcenter_Name)) AS Name
                    , Workcenter_Group
                    , Log_Date
                    , dDuration AS Log_Duration
                    , Event
                    , COALESCE(Status, 'Sem Justificativa') AS Status
                FROM mic_stops
                WHERE sEventDescription = 'Parada'
                AND row_num = 1
                ORDER BY Log_Date DESC

            """

    stopped_machines_plex_query = f"""

        WITH downtime_plex AS (
            SELECT 
                workcenter
                , record_time
                , wc_status_reason_time
                , wc_reason
                , ROW_NUMBER() OVER (PARTITION BY workcenter ORDER BY record_time DESC) AS rn
            FROM Mach_2_Status_Reason_Time
            WHERE wc_status_reason_time > 30
        )

        SELECT 
            T2.Workcenter_Key
            , T1.workcenter AS Workcenter_Code
            , T2.Name
            , T2.Workcenter_Group
            , COALESCE(T3.Workcenter_Event_Group, 'Produção') AS Status
            , CONCAT(T3.Code COLLATE SQL_Latin1_General_CP1_CI_AS, '-', T1.wc_reason) AS Event
            , CONVERT(VARCHAR(8), DATEADD(SECOND, [wc_status_reason_time], 0), 108) AS Log_Duration
            , T1.record_time AS Log_Date

        FROM downtime_plex T1
        
            JOIN OPENQUERY([PLEX_DSN_JOST], '
                SELECT 
                    Workcenter_Code
                    , Workcenter_Group
                    , Workcenter_Key
                    , Name
                    , Active
                FROM Part_v_Workcenter 
                WHERE Active = 1 AND Workcenter_Group IS NOT NULL
            ') T2 ON T1.workcenter = T2.Workcenter_Code COLLATE SQL_Latin1_General_CP1_CI_AS

            LEFT JOIN OPENQUERY([PLEX_DSN_JOST], '
                SELECT 
                    Workcenter_Event_Key
                    , Description
                    , Workcenter_Event_Group
                    , Active
                    , Code 
                FROM Part_v_Workcenter_Event
            ') T3 ON T1.wc_reason = T3.Description COLLATE SQL_Latin1_General_CP1_CI_AS

        WHERE T1.rn = 1;
    """

    with ThreadPoolExecutor() as executor:
        stopped_machines_mic = executor.submit(
            run_query,
            stopped_machines_mic_query,
            engine_ftm
        )

        stopped_machines_plex = executor.submit(
            run_query,
            stopped_machines_plex_query,
            engine_plex
        )

    stopped_machines_mic = stopped_machines_mic.result()
    stopped_machines_plex = stopped_machines_plex.result()

    stoppedMachines = pd.concat([stopped_machines_mic, stopped_machines_plex])

    stoppedMachines['Responsible'] = stoppedMachines['Event'].map(STOPS_FROM_AREAS).fillna(stoppedMachines['Status'])
    stoppedMachines = stoppedMachines.reset_index(drop=True)

    data = stoppedMachines.copy()

    engine_jdt = create_engine( f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_JDT)}",)

    columns = [
        'Workcenter_Key', 'Workcenter_Code', 'Name', 'Workcenter_Group', 'Log_Date'
        , 'Log_Duration', 'Responsible', 'Status', 'Event', 'Performance', 'Availability', 'Quality'
        , 'GoodParts', 'TotalParts', 'ExpectedParts', 'TotalRun', 'TotalAvail', 'TotalStopped'
    ]
    
    for col in [
        'Performance',
        'Availability',
        'Quality',
        'GoodParts',
        'TotalParts',
        'ExpectedParts',
        'TotalRun',
        'TotalAvail',
        'TotalStopped'
    ]:
        data[col] = 0

    insert_query = """
        INSERT INTO TEMP_WORKCENTER_STATUS (
            Workcenter_Key
            , Workcenter_Code
            , Name
            , Workcenter_Group
            , Log_Date
            , Log_Duration
            , Responsible
            , Status
            , Event
            , Performance
            , Availability
            , Quality
            , GoodParts
            , TotalParts
            , ExpectedParts
            , TotalRun
            , TotalAvail
            , TotalStopped
        ) VALUES (
            :Workcenter_Key, :Workcenter_Code, :Name, :Workcenter_Group, :Log_Date
            , :Log_Duration, :Responsible, :Status, :Event, :Performance, :Availability, :Quality
            , :GoodParts, :TotalParts, :ExpectedParts, :TotalRun, :TotalAvail, :TotalStopped
        )
    """

    with engine_jdt.begin() as conn:
        conn.execute(text("DELETE FROM TEMP_WORKCENTER_STATUS"))
        for _, row in data[columns].iterrows():
            conn.execute(text(insert_query), {
                'Workcenter_Key': row['Workcenter_Key']
                , 'Workcenter_Code': row['Workcenter_Code']
                , 'Name': row['Name']
                , 'Workcenter_Group': row['Workcenter_Group']
                , 'Log_Date': row['Log_Date']
                , 'Log_Duration': row['Log_Duration']
                , 'Responsible': row['Responsible']
                , 'Status': row['Status']
                , 'Event': row['Event']
                , 'Performance': row['Performance'] if pd.notnull(row['Performance']) else 0
                , 'Availability': row['Availability'] if pd.notnull(row['Availability']) else 0
                , 'Quality': row['Quality'] if pd.notnull(row['Quality']) else 0
                , 'GoodParts': row['GoodParts'] if pd.notnull(row['GoodParts']) else 0
                , 'TotalParts': row['TotalParts'] if pd.notnull(row['TotalParts']) else 0
                , 'ExpectedParts': row['ExpectedParts'] if pd.notnull(row['ExpectedParts']) else 0
                , 'TotalRun': row['TotalRun'] if pd.notnull(row['TotalRun']) else 0
                , 'TotalAvail': row['TotalAvail'] if pd.notnull(row['TotalAvail']) else 0
                , 'TotalStopped': row['TotalStopped'] if pd.notnull(row['TotalStopped']) else 0
            })

# V1
