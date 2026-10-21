USE [JOST_INTEGRATION_PRD]
GO

SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE OR ALTER PROCEDURE [dbo].[TD_OEE_ObterParadas]
    @data_inicio DATETIME,
    @data_fim DATETIME,
    @workcenter_list NVARCHAR(MAX) = NULL,
    @shift_list NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @data_inicio IS NULL
    BEGIN
        THROW 50001, 'Informe a data inicial.', 1;
    END;

    IF @data_fim IS NULL
    BEGIN
        THROW 50002, 'Informe a data final.', 1;
    END;

    IF @data_inicio >= @data_fim
    BEGIN
        THROW 50003, 'A data inicial deve ser menor que a data final.', 1;
    END;

    DECLARE @agora DATETIME = GETDATE();

    -- Considera toda parada que sobrepõe a janela pesquisada
    -- e calcula somente os minutos dentro dessa janela.
    ;WITH ParadasClassificadas AS (
        SELECT
            ID,
            Workcenter,
            WcStatus,
            WcReason,
            StatusBegin,
            StatusEnd,

            CASE UPPER(LTRIM(RTRIM(ISNULL(CurrentShift, N''))))
                WHEN N'PRIMEIRO' THEN N'Turno 1'
                WHEN N'TURNO 1' THEN N'Turno 1'
                WHEN N'SEGUNDO' THEN N'Turno 2'
                WHEN N'TURNO 2' THEN N'Turno 2'
                WHEN N'TERCEIRO' THEN N'Turno 3'
                WHEN N'TURNO 3' THEN N'Turno 3'
                WHEN N'EXTRA' THEN N'Extra'
                ELSE N'A confirmar'
            END AS turno,

            CASE
                WHEN StatusBegin < @data_inicio
                THEN @data_inicio
                ELSE StatusBegin
            END AS inicio_calculo,

            CASE
                WHEN ISNULL(StatusEnd, @agora) > @data_fim
                THEN @data_fim
                ELSE ISNULL(StatusEnd, @agora)
            END AS fim_calculo

        FROM dbo.Mach_2_Current_Status

        WHERE
            CanRunProduction = 0
            AND StatusBegin < @data_fim
            AND (
                StatusEnd > @data_inicio
                OR (
                    StatusEnd IS NULL
                    AND @agora > @data_inicio
                )
            )
            AND (
                @workcenter_list IS NULL
                OR @workcenter_list = N''
                OR Workcenter IN (
                    SELECT TRIM(value)
                    FROM STRING_SPLIT(@workcenter_list, N',')
                )
            )
    ),
    ParadasFiltradas AS (
        SELECT
            ID,
            Workcenter,
            WcStatus,
            WcReason,
            StatusBegin,
            StatusEnd,
            turno,
            inicio_calculo,
            fim_calculo
        FROM ParadasClassificadas
        WHERE
            @shift_list IS NULL
            OR @shift_list = N''
            OR turno IN (
                SELECT TRIM(value)
                FROM STRING_SPLIT(@shift_list, N',')
            )
    )

    SELECT
        ID AS id,
        Workcenter AS workcenter,
        WcStatus AS status,
        WcReason AS motivo,
        StatusBegin AS data_inicio,
        StatusEnd AS data_fim,
        turno,
        CAST(
            DATEDIFF(SECOND, inicio_calculo, fim_calculo) / 60.0
            AS FLOAT
        ) AS minutos_parados
    FROM ParadasFiltradas
    WHERE fim_calculo > inicio_calculo
    ORDER BY StatusBegin, Workcenter;
END;
GO
