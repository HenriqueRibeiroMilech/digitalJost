-- Consulta de leitura para investigar o inicio da cobertura de paradas TD.
-- A procedure TD_OEE_ObterParadas le dbo.Mach_2_Current_Status e considera
-- CanRunProduction = 0. O resultado traz cada centro e um total geral.
-- primeiro_status_td indica o inicio observado da coleta por centro;
-- primeira_parada_td pode ser posterior mesmo sem lacuna de dados.
-- Confira a transicao com os registros do Plex antes de definir o corte.

WITH StatusTD AS (
    SELECT
        NULLIF(LTRIM(RTRIM(Workcenter)), '') AS Workcenter,
        StatusBegin,
        StatusEnd,
        CanRunProduction
    FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_Current_Status]
)
SELECT
    CASE
        WHEN GROUPING(Workcenter) = 1 THEN '(todos os centros)'
        ELSE Workcenter
    END AS centro,
    MIN(StatusBegin) AS primeiro_status_td,
    MIN(CASE
        WHEN CanRunProduction = 0
            AND (StatusEnd IS NULL OR StatusEnd > StatusBegin)
        THEN StatusBegin
    END) AS primeira_parada_td,
    MAX(CASE
        WHEN CanRunProduction = 0
            AND (StatusEnd IS NULL OR StatusEnd > StatusBegin)
        THEN StatusBegin
    END) AS ultima_parada_td,
    COUNT(CASE
        WHEN CanRunProduction = 0
            AND (StatusEnd IS NULL OR StatusEnd > StatusBegin)
        THEN 1
    END) AS quantidade_paradas
FROM StatusTD
WHERE Workcenter IS NOT NULL
GROUP BY ROLLUP (Workcenter)
ORDER BY GROUPING(Workcenter) DESC, Workcenter;
