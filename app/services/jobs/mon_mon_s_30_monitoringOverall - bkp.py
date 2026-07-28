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
}

def default(logger):

    engine_ftm = create_engine( f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_FTM)}",)
    engine_plex = create_engine( f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_PLEX)}",)

    def run_query(query, engine, params=None):
        return pd.read_sql(query, engine, params=params)


    shift_query = f"""
                SELECT TOP 1 record_time
                FROM Mach_2_OEE T1
                WHERE shift_oee <> (
                    SELECT TOP 1 shift_oee
                    FROM Mach_2_OEE
                    WHERE workcenter = 'M07'
                    ORDER BY record_time DESC
                ) AND workcenter = 'M07'
                ORDER BY record_time DESC;
    """
    shift_info = run_query(shift_query, engine_plex)

    performance_query = f"""
        WITH target_rates_plex AS(
            SELECT *
            FROM OPENQUERY([PLEX_DSN_JOST], '
                SELECT
                    T1.Part_No
                    , T3.Workcenter_Code
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
                , T03.Workcenter_Code
                , AVG(T03.Ideal_Rate) AS Ideal_Rate
            FROM
                Mach_2_OEE_Cavity_Info T01
                JOIN Mach_2_OEE_v2 T02 ON T01.id_Mach_2_OEE_v2 = T02.id
                JOIN target_rates_plex T03 ON
                    T01.part = T03.Part_No COLLATE SQL_Latin1_General_CP1_CI_AS
                    AND T02.workcenter = T03.Workcenter_Code COLLATE SQL_Latin1_General_CP1_CI_AS
            GROUP BY T01.id_Mach_2_OEE_v2, T03.Workcenter_Code
        )
        SELECT
            T1.workcenter as Workcenter_Code
            , SUM(CAST(T1.production_difference AS INT)) AS GoodParts
            , SUM(CAST(T1.production_difference AS INT)) AS TotalParts
            , SUM(CAST(T1.time_difference AS FLOAT) / 3600.0 * CAST(T2.Ideal_Rate AS FLOAT)) AS ExpectedParts
            , COALESCE(SUM(CAST(T1.production_difference AS INT)) / NULLIF(SUM(CAST(T1.time_difference AS FLOAT) / 3600.0 * CAST(T2.Ideal_Rate AS FLOAT)), 0), 0) * 100.0 AS Performance
            , 100.0 AS Quality
        FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_OEE_v2] T1
            LEFT JOIN target_rates_final T2 ON T1.ID = T2.id_Mach_2_OEE_v2
        WHERE
            T1.record_time > ?
        GROUP BY T1.workcenter
    """

    availability_query = f"""
        DECLARE @record_time DATETIME = ?;
        WITH last_log AS (
            SELECT
                workcenter
                , wc_stauts
                , wc_status_reason_time
                , record_time
                , ROW_NUMBER() OVER (PARTITION BY workcenter ORDER BY record_time DESC) AS rn
            FROM Mach_2_Status_Reason_Time
            WHERE record_time < @record_time 
        ),
        invade_time AS (
            SELECT
                workcenter
                , wc_stauts
                , CASE
                    WHEN DATEADD(SECOND, wc_status_reason_time, record_time) > @record_time
                    THEN DATEDIFF(SECOND, @record_time, DATEADD(SECOND, wc_status_reason_time, record_time))
                    ELSE 0
                END AS invaded_seconds
            FROM last_log
            WHERE rn = 1
        ),
        workcenter_times AS (
            SELECT 
                workcenter AS Workcenter_Code
                , SUM(CASE WHEN wc_stauts = 'Produção' THEN CAST(wc_status_reason_time AS FLOAT) ELSE 0 END) AS totalRun
                , SUM(CASE WHEN wc_stauts != 'Programada' THEN CAST(wc_status_reason_time AS FLOAT) ELSE 0 END) AS totalAvail
                , SUM(CASE WHEN wc_stauts NOT IN ('Programada', 'Produção') THEN CAST(wc_status_reason_time AS FLOAT) ELSE 0 END) AS totalStopped
            FROM Mach_2_Status_Reason_Time
            WHERE record_time > @record_time
            GROUP BY workcenter
        )
        SELECT 
            wt.Workcenter_Code
            , (wt.totalRun + CASE WHEN it.wc_stauts = 'Produção' THEN it.invaded_seconds ELSE 0 END) / 60.0 AS TotalRun
            , (wt.totalAvail + CASE WHEN it.wc_stauts != 'Programada' THEN it.invaded_seconds ELSE 0 END) / 60.0 AS TotalAvail
            , (wt.totalStopped + CASE WHEN it.wc_stauts NOT IN ('Programada', 'Produção') THEN it.invaded_seconds ELSE 0 END) / 60.0 AS TotalStopped
            , COALESCE(
                (
                    wt.totalRun + 
                        CASE WHEN it.wc_stauts = 'Produção' THEN it.invaded_seconds ELSE 0 END
                ) / 
                NULLIF(
                    wt.totalAvail + 
                        CASE WHEN it.wc_stauts != 'Programada' THEN it.invaded_seconds ELSE 0 END
                , 0) * 100.0
            , 0) AS Availability
        FROM workcenter_times wt
        LEFT JOIN invade_time it
            ON wt.Workcenter_Code = it.workcenter
    """

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
        stopped_machines_mic = executor.submit(run_query, stopped_machines_mic_query, engine_ftm)
        stopped_machines_plex = executor.submit(run_query, stopped_machines_plex_query, engine_plex)

        performance_data = executor.submit(run_query, performance_query, engine_plex, (shift_info['record_time'][0],))
        availability_data = executor.submit(run_query, availability_query, engine_plex, (shift_info['record_time'][0],))

    stopped_machines_mic = stopped_machines_mic.result()
    stopped_machines_plex = stopped_machines_plex.result()

    performance_data = performance_data.result()
    availability_data = availability_data.result()

    stoppedMachines = pd.concat([stopped_machines_mic, stopped_machines_plex])

    stoppedMachines['Responsible'] = stoppedMachines['Event'].map(STOPS_FROM_AREAS).fillna(stoppedMachines['Status'])
    stoppedMachines = stoppedMachines.reset_index(drop=True)

    data = pd.merge(left=stoppedMachines, right=performance_data, on='Workcenter_Code', how='left')
    data = pd.merge(left=data, right=availability_data, on='Workcenter_Code', how='left')

    engine_jdt = create_engine( f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_JDT)}",)

    columns = [
        'Workcenter_Key', 'Workcenter_Code', 'Name', 'Workcenter_Group', 'Log_Date'
        , 'Log_Duration', 'Responsible', 'Status', 'Event', 'Performance', 'Availability', 'Quality'
        , 'GoodParts', 'TotalParts', 'ExpectedParts', 'TotalRun', 'TotalAvail', 'TotalStopped'
    ]

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
