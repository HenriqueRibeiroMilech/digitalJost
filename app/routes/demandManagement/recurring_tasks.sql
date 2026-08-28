/*
    Suporte a atividades recorrentes no Gerenciador de Demandas.
    Execute manualmente no banco JDT antes de publicar o código correspondente.
    O script é idempotente e não é executado pela aplicação.
*/

SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'U') IS NULL
BEGIN
    ROLLBACK TRANSACTION;
    THROW 50001, 'A tabela dbo.JDT_DEMAND_MANAGEMENT_TASKS não existe.', 1;
END;

IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceGroupId') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS
        ADD recurrenceGroupId UNIQUEIDENTIFIER NULL;

IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceType') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS
        ADD recurrenceType NVARCHAR(20) NULL;

IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceEndDate') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS
        ADD recurrenceEndDate DATE NULL;

IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceMaxOccurrences') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS
        ADD recurrenceMaxOccurrences INT NULL;

IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceSequence') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS
        ADD recurrenceSequence INT NULL;

IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceStatus') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS
        ADD recurrenceStatus NVARCHAR(20) NULL;

IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'skipNextOccurrence') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS
        ADD skipNextOccurrence BIT NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_TASKS_skipNextOccurrence
            DEFAULT 0 WITH VALUES;

/*
    Estes comandos são compilados somente depois que as colunas acima existem.
    Isso evita o erro 207 do SQL Server ao compilar todo o lote antecipadamente.
*/
IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS')
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceType'
)
    EXEC sys.sp_executesql N'
        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS WITH CHECK
            ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceType
            CHECK (
                recurrenceType IS NULL
                OR recurrenceType IN (N''weekly'', N''biweekly'', N''monthly'')
            );
    ';

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS')
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceShape'
)
    EXEC sys.sp_executesql N'
        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS WITH CHECK
            ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceShape
            CHECK (
                (
                    recurrenceGroupId IS NULL
                    AND recurrenceType IS NULL
                    AND recurrenceSequence IS NULL
                    AND recurrenceStatus IS NULL
                )
                OR (
                    recurrenceGroupId IS NOT NULL
                    AND recurrenceType IS NOT NULL
                    AND recurrenceSequence IS NOT NULL
                    AND recurrenceStatus IS NOT NULL
                )
            );
    ';

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS')
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceStatus'
)
    EXEC sys.sp_executesql N'
        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS WITH CHECK
            ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceStatus
            CHECK (
                recurrenceStatus IS NULL
                OR recurrenceStatus IN (N''active'', N''paused'', N''ended'')
            );
    ';

IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS')
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceNumbers'
)
    EXEC sys.sp_executesql N'
        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS WITH CHECK
            ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceNumbers
            CHECK (
                (recurrenceSequence IS NULL OR recurrenceSequence > 0)
                AND (
                    recurrenceMaxOccurrences IS NULL
                    OR recurrenceMaxOccurrences > 0
                )
            );
    ';

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS')
        AND name = 'UX_JDT_DEMAND_MANAGEMENT_TASKS_recurrence'
)
    EXEC sys.sp_executesql N'
        CREATE UNIQUE INDEX UX_JDT_DEMAND_MANAGEMENT_TASKS_recurrence
            ON dbo.JDT_DEMAND_MANAGEMENT_TASKS (
                recurrenceGroupId,
                recurrenceSequence
            )
            WHERE recurrenceGroupId IS NOT NULL;
    ';

COMMIT TRANSACTION;
