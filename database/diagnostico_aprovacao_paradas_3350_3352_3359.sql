-- Consulta somente de leitura para as solicitações 3350, 3352 e 3359.
-- Execute na conexão JDT que tenha acesso ao linked server PLEX_DSN_JOST
-- e ao banco JOST_INTEGRATION_PRD. Não altera solicitações nem paradas.
-- Uma solicitação pode aparecer em várias linhas se houver mais de um
-- registro do Current Status cobrindo o instante da parada no Plex.

DECLARE @event_ids nvarchar(max);

SELECT @event_ids = STRING_AGG(
    CONVERT(varchar(20), TRY_CONVERT(bigint, R.eventId)), ','
)
FROM JDT_REQUEST_STOPCHANGES AS R
WHERE R.requestId IN (3350, 3352, 3359)
    AND R.plex = 1
    AND TRY_CONVERT(bigint, R.eventId) IS NOT NULL;

-- OPENQUERY exige uma consulta literal; a lista contém apenas IDs numéricos
-- lidos da tabela de solicitações.
SET @event_ids = COALESCE(@event_ids, N'-1');

DECLARE @sql nvarchar(max) = N'
SELECT
    R.requestId,
    R.eventId,
    R.plex,
    R.approverStatus1,
    R.approverStatus2,
    R.finalDate,
    P.workcenter AS centro_salvo_key,
    P.startDate AS inicio_salvo,
    P.endDate AS fim_salvo,
    P.logMinutes AS minutos_salvos,
    PL.Workcenter_Key AS centro_plex_key,
    PL.Workcenter_Code AS centro_plex_codigo,
    PL.Log_Date AS inicio_plex,
    PL.Log_Hours AS horas_plex,
    DATEADD(SECOND, CAST(ROUND(PL.Log_Hours * 3600.0, 0) AS int), PL.Log_Date)
        AS fim_plex_em_segundos,
    PL.Plex_Reason AS motivo_plex,
    S.ID AS current_status_id,
    S.StatusBegin AS current_status_inicio,
    S.StatusEnd AS current_status_fim,
    S.CanRunProduction,
    S.WcStatus,
    S.WcReason,
    DATEDIFF(SECOND, S.StatusBegin, PL.Log_Date)
        AS segundos_do_inicio_status_ate_plex,
    CASE
        WHEN PL.Log_Key IS NULL THEN N''Parada não encontrada no Plex''
        WHEN S.ID IS NULL THEN N''Nenhuma linha cobre o instante''
        WHEN S.CanRunProduction = 1 THEN N''Estado de produção''
        WHEN S.CanRunProduction = 0
            AND S.StatusBegin >= DATEADD(MINUTE, -1, PL.Log_Date)
            THEN N''Parada iniciada até um minuto antes''
        WHEN S.CanRunProduction = 0 THEN N''Parada iniciada há mais de um minuto''
        ELSE N''Estado sem classificação''
    END AS indicio
FROM JDT_REQUEST_STOPCHANGES AS R
LEFT JOIN JDT_REQUEST_STOPCHANGES_PLEX AS P
    ON P.eventId = R.eventId
LEFT JOIN OPENQUERY([PLEX_DSN_JOST], ''
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
    WHERE L.Log_Key IN (' + @event_ids + N')
'') AS PL ON PL.Log_Key = R.eventId
OUTER APPLY (
    SELECT
        CS.ID,
        CS.StatusBegin,
        CS.StatusEnd,
        CS.CanRunProduction,
        CS.WcStatus,
        CS.WcReason
    FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_Current_Status] AS CS
    WHERE CS.Workcenter COLLATE DATABASE_DEFAULT
        = PL.Workcenter_Code COLLATE DATABASE_DEFAULT
        AND CS.StatusBegin <= PL.Log_Date
        AND COALESCE(CS.StatusEnd, GETDATE()) >= PL.Log_Date
) AS S
WHERE R.requestId IN (3350, 3352, 3359)
ORDER BY R.requestId, S.StatusBegin DESC, S.ID;';

EXEC sys.sp_executesql @sql;
