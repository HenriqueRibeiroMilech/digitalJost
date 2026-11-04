-- Consulta somente de leitura. Execute diretamente em JOST_INTEGRATION_PRD.
-- Não acessa as tabelas JDT nem o linked server do Plex.
-- Troque cada NULL pelo centro_codigo_plex correspondente, obtido na consulta
-- diagnostico_aprovacao_paradas_3350_3352_3359.sql, por exemplo N'P04'.
-- Confira também inicio_plex no primeiro arquivo e ajuste os horários abaixo
-- se houver diferença em relação aos valores salvos na JDT.
-- Com NULL, a consulta mostra todos os centros ativos no instante e pode
-- retornar muitas linhas; use o código do centro para identificar a parada.

USE [JOST_INTEGRATION_PRD];

WITH Casos AS (
    SELECT
        V.requestId,
        V.eventId,
        V.inicio_plex,
        V.centro_codigo
    FROM (VALUES
        (3350, 2350016667, CONVERT(datetime2(3), '2026-10-03T11:26:21.000'), CAST(NULL AS nvarchar(30))),
        (3352, 2351905487, CONVERT(datetime2(3), '2026-10-06T10:52:34.000'), CAST(NULL AS nvarchar(30))),
        (3359, 2354495007, CONVERT(datetime2(3), '2026-10-10T09:51:30.000'), CAST(NULL AS nvarchar(30)))
    ) AS V(requestId, eventId, inicio_plex, centro_codigo)
)
SELECT
    C.requestId,
    C.eventId,
    C.inicio_plex,
    C.centro_codigo AS centro_filtrado,
    S.ID AS current_status_id,
    S.Workcenter AS centro_current_status,
    S.StatusBegin,
    S.StatusEnd,
    S.CanRunProduction,
    S.WcStatus,
    S.WcReason,
    DATEDIFF(SECOND, S.StatusBegin, C.inicio_plex)
        AS segundos_do_inicio_status_ate_plex,
    CASE
        WHEN S.ID IS NULL THEN N'Nenhum status cobre o instante'
        WHEN S.CanRunProduction = 1 THEN N'Estado de produção'
        WHEN S.CanRunProduction = 0
            AND S.StatusBegin >= DATEADD(MINUTE, -1, C.inicio_plex)
            THEN N'Parada iniciada até um minuto antes'
        WHEN S.CanRunProduction = 0 THEN N'Parada iniciada há mais de um minuto'
        ELSE N'Estado sem classificação'
    END AS indicio
FROM Casos AS C
LEFT JOIN dbo.Mach_2_Current_Status AS S
    ON (C.centro_codigo IS NULL OR S.Workcenter = C.centro_codigo)
    AND S.StatusBegin <= C.inicio_plex
    AND COALESCE(S.StatusEnd, GETDATE()) >= C.inicio_plex
ORDER BY C.requestId, S.Workcenter, S.StatusBegin DESC, S.ID;
