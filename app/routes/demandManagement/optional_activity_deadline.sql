/*
    Permite agendar atividades sem prazo no Gerenciador de Demandas.

    Execute uma vez no banco TRANSFORMACAODIGITAL_JOST antes de publicar
    o código novo da aplicação e do serviço Auto.
*/

SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF COL_LENGTH(
        N'dbo.JDT_DEMAND_MANAGEMENT',
        N'scheduledStartAt'
    ) IS NULL
        OR COL_LENGTH(
            N'dbo.JDT_DEMAND_MANAGEMENT',
            N'scheduledDeadlineDays'
        ) IS NULL
        OR COL_LENGTH(
            N'dbo.JDT_DEMAND_MANAGEMENT',
            N'demandType'
        ) IS NULL
    BEGIN
        THROW 50001,
            'As colunas de agendamento do Gerenciador de Demandas não foram encontradas.',
            1;
    END;

    IF EXISTS (
        SELECT 1
        FROM sys.check_constraints
        WHERE parent_object_id = OBJECT_ID(N'dbo.JDT_DEMAND_MANAGEMENT')
          AND name = N'CK_JDT_DEMAND_MANAGEMENT_startSchedule'
    )
    BEGIN
        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
            DROP CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_startSchedule;
    END;

    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT WITH CHECK
        ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_startSchedule
        CHECK (
            scheduledStartAt IS NULL
            AND scheduledDeadlineDays IS NULL
            OR
            scheduledStartAt IS NOT NULL
            AND (
                (
                    scheduledDeadlineDays IS NOT NULL
                    AND scheduledDeadlineDays >= 0
                )
                OR (
                    ISNULL(demandType, N'') = N'atividade'
                    AND scheduledDeadlineDays IS NULL
                )
            )
        );

    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
        CHECK CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_startSchedule;

    COMMIT TRANSACTION;

    SELECT
        N'OK' AS status,
        N'Atividades podem ser agendadas sem prazo.' AS resultado;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
