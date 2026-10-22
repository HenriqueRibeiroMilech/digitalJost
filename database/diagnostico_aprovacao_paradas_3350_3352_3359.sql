-- Diagnóstico somente de leitura. Execute na conexão JDT.
-- Não consulta JOST_INTEGRATION_PRD e não altera dados.
-- O primeiro resultado usa apenas tabelas JDT. O segundo usa o linked server
-- PLEX_DSN_JOST, já empregado pela aplicação para ler as paradas do Plex.
-- Se o segundo SELECT falhar por permissão, envie o erro e o primeiro resultado.

SELECT
    R.requestId,
    R.eventId,
    R.plex,
    R.approverStatus1,
    R.approverStatus2,
    R.finalDate,
    R.motive1,
    R.motive2,
    R.motive1EventKey,
    R.motive2EventKey,
    P.workcenter AS centro_key_salvo,
    P.startDate AS inicio_salvo,
    P.endDate AS fim_salvo,
    P.logMinutes AS minutos_salvos
FROM JDT_REQUEST_STOPCHANGES AS R
LEFT JOIN JDT_REQUEST_STOPCHANGES_PLEX AS P ON P.eventId = R.eventId
WHERE R.requestId IN (3350, 3352, 3359)
ORDER BY R.requestId;

SELECT
    R.requestId,
    R.eventId,
    PL.Workcenter_Key AS centro_key_plex,
    PL.Workcenter_Code AS centro_codigo_plex,
    PL.Log_Date AS inicio_plex,
    PL.Log_Hours AS horas_plex,
    DATEADD(
        SECOND,
        CAST(ROUND(PL.Log_Hours * 3600.0, 0) AS int),
        PL.Log_Date
    ) AS fim_plex_em_segundos,
    PL.Plex_Reason AS motivo_plex
FROM JDT_REQUEST_STOPCHANGES AS R
LEFT JOIN OPENQUERY([PLEX_DSN_JOST], '
    SELECT
        L.Log_Key,
        L.Log_Date,
        L.Log_Hours,
        L.Workcenter_Key,
        W.Workcenter_Code,
        E.Description AS Plex_Reason
    FROM Part_v_Workcenter_Log L
    JOIN Part_v_Workcenter W ON W.Workcenter_Key = L.Workcenter_Key
    LEFT JOIN Part_v_Workcenter_Event E
        ON E.Workcenter_Event_Key = L.Workcenter_Event_Key
    WHERE L.Log_Key IN (2350016667, 2351905487, 2354495007)
') AS PL ON PL.Log_Key = R.eventId
WHERE R.requestId IN (3350, 3352, 3359)
ORDER BY R.requestId;
