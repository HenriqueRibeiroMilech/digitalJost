-- Consulta de leitura: verifica os turnos dos centros sem base no Operation Meeting.
-- Periodo mensal exibido na semana 38/2026: inicio inclusivo e fim exclusivo.
-- Nao cria procedures nem altera dados.
USE [JOST_INTEGRATION_PRD];

DECLARE @inicio DATETIME = '2026-09-01T00:00:00';
DECLARE @fim DATETIME = '2026-09-21T00:00:00';
DECLARE @agora DATETIME = GETDATE();

SELECT
    Workcenter,
    CurrentShift,
    CASE
        WHEN CurrentShift IN (
            N'Primeiro', N'Segundo', N'Terceiro',
            N'Turno 1', N'Turno 2', N'Turno 3'
        )
        THEN N'Sim'
        ELSE N'Não'
    END AS Turno_aceito_pela_tela,
    COUNT_BIG(*) AS Quantidade_status,
    SUM(
        CAST(
            CASE WHEN PlannedProductionTime = 1 THEN 1 ELSE 0 END
            AS BIGINT
        )
    ) AS Status_com_tempo_planejado
FROM dbo.Mach_2_Current_Status
WHERE Workcenter IN (
    N'E01', N'E03', N'L03', N'L05',
    N'M09', N'P04', N'R01', N'S18'
)
  AND StatusBegin < @fim
  AND (
      StatusEnd > @inicio
      OR (StatusEnd IS NULL AND @agora > @inicio)
  )
GROUP BY Workcenter, CurrentShift
ORDER BY Workcenter, CurrentShift;
