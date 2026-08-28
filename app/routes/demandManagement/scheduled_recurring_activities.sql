/*
    Ajusta recorrências e adiciona início agendado ao Gerenciador de Demandas.

    Execute manualmente no banco JDT depois de recurring_activities.sql e antes
    de publicar o código correspondente. O script é idempotente e transacional.
*/

SET XACT_ABORT ON;
BEGIN TRANSACTION;
BEGIN TRY

IF OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT', 'U') IS NULL
BEGIN
    ROLLBACK TRANSACTION;
    THROW 50010, 'A tabela dbo.JDT_DEMAND_MANAGEMENT não existe.', 1;
END;

IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceGroupId') IS NULL
    OR COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceType') IS NULL
    OR COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceEndDate') IS NULL
    OR COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceSequence') IS NULL
    OR COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceStatus') IS NULL
    OR COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceAvailableDate') IS NULL
    OR COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'skipNextOccurrence') IS NULL
BEGIN
    ROLLBACK TRANSACTION;
    THROW 50011, 'Execute primeiro a migration recurring_activities.sql.', 1;
END;

DECLARE @biweeklyRows INT = 0;
EXEC sys.sp_executesql
    N'SELECT @total = COUNT(*) FROM dbo.JDT_DEMAND_MANAGEMENT WHERE recurrenceType = N''biweekly'';',
    N'@total INT OUTPUT',
    @total = @biweeklyRows OUTPUT;

IF @biweeklyRows > 0
BEGIN
    ROLLBACK TRANSACTION;
    THROW 50012, 'Existem recorrências quinzenais. Nenhuma alteração foi feita; revise essas séries antes de remover a frequência.', 1;
END;

IF EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_recurrenceType'
)
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
        DROP CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_recurrenceType;

EXEC sys.sp_executesql N'
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT WITH CHECK
        ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_recurrenceType
        CHECK (recurrenceType IS NULL OR recurrenceType IN (N''daily'', N''weekly'', N''monthly''));
';

IF EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'IX_JDT_DEMAND_MANAGEMENT_recurrenceAvailableDate'
)
    DROP INDEX IX_JDT_DEMAND_MANAGEMENT_recurrenceAvailableDate
        ON dbo.JDT_DEMAND_MANAGEMENT;

IF EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_recurrenceShape'
)
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
        DROP CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_recurrenceShape;

IF EXISTS (
    SELECT 1
    FROM sys.columns AS C
    JOIN sys.types AS T ON T.user_type_id = C.user_type_id
    WHERE C.object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND C.name = 'recurrenceAvailableDate'
        AND T.name = 'date'
)
    EXEC sys.sp_executesql N'
        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
            ALTER COLUMN recurrenceAvailableDate DATETIME2(0) NULL;
        UPDATE dbo.JDT_DEMAND_MANAGEMENT
        SET recurrenceAvailableDate = DATEADD(
            MINUTE, 1, CAST(CAST(recurrenceAvailableDate AS DATE) AS DATETIME2(0))
        )
        WHERE recurrenceAvailableDate IS NOT NULL;
    ';

IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'scheduledStartAt') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
        ADD scheduledStartAt DATETIME2(0) NULL;

IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'scheduledDeadlineDays') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
        ADD scheduledDeadlineDays INT NULL;

EXEC sys.sp_executesql N'
    UPDATE dbo.JDT_DEMAND_MANAGEMENT
    SET
        recurrenceEndDate = NULL,
        recurrenceStatus = CASE
            WHEN recurrenceStatus = N''paused'' THEN N''active''
            ELSE recurrenceStatus
        END,
        skipNextOccurrence = 0
    WHERE recurrenceGroupId IS NOT NULL;
';

IF EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_recurrenceStatus'
)
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
        DROP CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_recurrenceStatus;

EXEC sys.sp_executesql N'
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT WITH CHECK
        ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_recurrenceStatus
        CHECK (recurrenceStatus IS NULL OR recurrenceStatus IN (N''active'', N''ended''));
';

EXEC sys.sp_executesql N'
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT WITH CHECK
        ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_recurrenceShape
        CHECK (
            (
                recurrenceGroupId IS NULL
                AND recurrenceType IS NULL
                AND recurrenceSequence IS NULL
                AND recurrenceStatus IS NULL
                AND recurrenceEndDate IS NULL
                AND recurrenceMaxOccurrences IS NULL
                AND recurrenceAvailableDate IS NULL
                AND skipNextOccurrence = 0
            )
            OR (
                recurrenceGroupId IS NOT NULL
                AND recurrenceType IS NOT NULL
                AND recurrenceSequence IS NOT NULL
                AND recurrenceStatus IS NOT NULL
                AND sourceRequestId IS NULL
                AND demandType = N''atividade''
            )
        );
';

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_startSchedule'
)
    EXEC sys.sp_executesql N'
        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT WITH CHECK
            ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_startSchedule
            CHECK (
                (scheduledStartAt IS NULL AND scheduledDeadlineDays IS NULL)
                OR (
                    scheduledStartAt IS NOT NULL
                    AND scheduledDeadlineDays IS NOT NULL
                    AND scheduledDeadlineDays >= 0
                )
            );
    ';

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'IX_JDT_DEMAND_MANAGEMENT_recurrenceAvailableDate'
)
    EXEC sys.sp_executesql N'
        CREATE INDEX IX_JDT_DEMAND_MANAGEMENT_recurrenceAvailableDate
            ON dbo.JDT_DEMAND_MANAGEMENT (areaId, recurrenceAvailableDate)
            INCLUDE (status, responsibleId)
            WHERE recurrenceAvailableDate IS NOT NULL;
    ';

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'IX_JDT_DEMAND_MANAGEMENT_scheduledStartAt'
)
    EXEC sys.sp_executesql N'
        CREATE INDEX IX_JDT_DEMAND_MANAGEMENT_scheduledStartAt
            ON dbo.JDT_DEMAND_MANAGEMENT (scheduledStartAt)
            INCLUDE (status, areaId, responsibleId, scheduledDeadlineDays)
            WHERE scheduledStartAt IS NOT NULL;
    ';

COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
