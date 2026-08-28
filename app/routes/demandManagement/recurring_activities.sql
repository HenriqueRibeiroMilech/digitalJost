/*
    Recorrência para cards criados por "+ Nova atividade".

    Execute manualmente no banco JDT antes de publicar o código correspondente.
    O script é idempotente e não é executado pela aplicação.

    Correção cautelosa da versão anterior:
    - remove as colunas de recorrência adicionadas por engano à tabela de tarefas;
    - interrompe sem remover nada se encontrar uma tarefa que realmente usou a
      recorrência antiga;
    - cria a estrutura correta em JDT_DEMAND_MANAGEMENT.
*/

SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT', 'U') IS NULL
BEGIN
    ROLLBACK TRANSACTION;
    THROW 50001, 'A tabela dbo.JDT_DEMAND_MANAGEMENT não existe.', 1;
END;

DECLARE @wrongRecurrenceRows INT = 0;

IF OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'U') IS NOT NULL
BEGIN
    IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceGroupId') IS NOT NULL
        EXEC sys.sp_executesql
            N'SELECT @total = COUNT(*) FROM dbo.JDT_DEMAND_MANAGEMENT_TASKS WHERE recurrenceGroupId IS NOT NULL;',
            N'@total INT OUTPUT',
            @total = @wrongRecurrenceRows OUTPUT;

    IF @wrongRecurrenceRows = 0
        AND COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceType') IS NOT NULL
        EXEC sys.sp_executesql
            N'SELECT @total = COUNT(*) FROM dbo.JDT_DEMAND_MANAGEMENT_TASKS WHERE recurrenceType IS NOT NULL;',
            N'@total INT OUTPUT',
            @total = @wrongRecurrenceRows OUTPUT;

    IF @wrongRecurrenceRows > 0
    BEGIN
        ROLLBACK TRANSACTION;
        THROW 50002, 'Foram encontradas tarefas usando a recorrência antiga. Nenhuma alteração foi feita; preserve os dados e revise a migração.', 1;
    END;

    IF EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS')
            AND name = 'UX_JDT_DEMAND_MANAGEMENT_TASKS_recurrence'
    )
        EXEC sys.sp_executesql N'DROP INDEX UX_JDT_DEMAND_MANAGEMENT_TASKS_recurrence ON dbo.JDT_DEMAND_MANAGEMENT_TASKS;';

    DECLARE @taskConstraint SYSNAME;
    DECLARE @taskSql NVARCHAR(MAX);
    DECLARE task_constraints CURSOR LOCAL FAST_FORWARD FOR
        SELECT name
        FROM sys.check_constraints
        WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS')
            AND name IN (
                'CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceType',
                'CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceShape',
                'CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceStatus',
                'CK_JDT_DEMAND_MANAGEMENT_TASKS_recurrenceNumbers'
            );

    OPEN task_constraints;
    FETCH NEXT FROM task_constraints INTO @taskConstraint;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @taskSql = N'ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS DROP CONSTRAINT '
            + QUOTENAME(@taskConstraint) + N';';
        EXEC sys.sp_executesql @taskSql;
        FETCH NEXT FROM task_constraints INTO @taskConstraint;
    END;
    CLOSE task_constraints;
    DEALLOCATE task_constraints;

    DECLARE @taskDefault SYSNAME;
    SELECT @taskDefault = DC.name
    FROM sys.default_constraints AS DC
    JOIN sys.columns AS C
        ON C.object_id = DC.parent_object_id
        AND C.column_id = DC.parent_column_id
    WHERE DC.parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS')
        AND C.name = 'skipNextOccurrence';

    IF @taskDefault IS NOT NULL
    BEGIN
        SET @taskSql = N'ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS DROP CONSTRAINT '
            + QUOTENAME(@taskDefault) + N';';
        EXEC sys.sp_executesql @taskSql;
    END;

    IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'skipNextOccurrence') IS NOT NULL
        EXEC sys.sp_executesql N'ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS DROP COLUMN skipNextOccurrence;';
    IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceStatus') IS NOT NULL
        EXEC sys.sp_executesql N'ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS DROP COLUMN recurrenceStatus;';
    IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceSequence') IS NOT NULL
        EXEC sys.sp_executesql N'ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS DROP COLUMN recurrenceSequence;';
    IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceMaxOccurrences') IS NOT NULL
        EXEC sys.sp_executesql N'ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS DROP COLUMN recurrenceMaxOccurrences;';
    IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceEndDate') IS NOT NULL
        EXEC sys.sp_executesql N'ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS DROP COLUMN recurrenceEndDate;';
    IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceType') IS NOT NULL
        EXEC sys.sp_executesql N'ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS DROP COLUMN recurrenceType;';
    IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'recurrenceGroupId') IS NOT NULL
        EXEC sys.sp_executesql N'ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS DROP COLUMN recurrenceGroupId;';
END;

IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceGroupId') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT ADD recurrenceGroupId UNIQUEIDENTIFIER NULL;
IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceType') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT ADD recurrenceType NVARCHAR(20) NULL;
IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceEndDate') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT ADD recurrenceEndDate DATE NULL;
IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceMaxOccurrences') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT ADD recurrenceMaxOccurrences INT NULL;
IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceSequence') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT ADD recurrenceSequence INT NULL;
IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceStatus') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT ADD recurrenceStatus NVARCHAR(20) NULL;
IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'recurrenceAvailableDate') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT ADD recurrenceAvailableDate DATE NULL;
IF COL_LENGTH('dbo.JDT_DEMAND_MANAGEMENT', 'skipNextOccurrence') IS NULL
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
        ADD skipNextOccurrence BIT NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_skipNextOccurrence
            DEFAULT 0 WITH VALUES;

IF EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'skipNextOccurrence'
        AND is_nullable = 1
)
BEGIN
    EXEC sys.sp_executesql N'
        UPDATE dbo.JDT_DEMAND_MANAGEMENT
        SET skipNextOccurrence = 0
        WHERE skipNextOccurrence IS NULL;
        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
            ALTER COLUMN skipNextOccurrence BIT NOT NULL;
    ';
END;

IF NOT EXISTS (
    SELECT 1
    FROM sys.default_constraints AS DC
    JOIN sys.columns AS C
        ON C.object_id = DC.parent_object_id
        AND C.column_id = DC.parent_column_id
    WHERE DC.parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND C.name = 'skipNextOccurrence'
)
    ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
        ADD CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_skipNextOccurrence
            DEFAULT 0 FOR skipNextOccurrence;

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_recurrenceType'
)
    EXEC sys.sp_executesql N'
        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT WITH CHECK
            ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_recurrenceType
            CHECK (recurrenceType IS NULL OR recurrenceType IN (N''weekly'', N''biweekly'', N''monthly''));
    ';

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_recurrenceStatus'
)
    EXEC sys.sp_executesql N'
        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT WITH CHECK
            ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_recurrenceStatus
            CHECK (recurrenceStatus IS NULL OR recurrenceStatus IN (N''active'', N''paused'', N''ended''));
    ';

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_recurrenceShape'
)
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
        AND name = 'CK_JDT_DEMAND_MANAGEMENT_recurrenceNumbers'
)
    EXEC sys.sp_executesql N'
        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT WITH CHECK
            ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_recurrenceNumbers
            CHECK (
                (recurrenceSequence IS NULL OR recurrenceSequence > 0)
                AND (recurrenceMaxOccurrences IS NULL OR recurrenceMaxOccurrences > 0)
            );
    ';

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT')
        AND name = 'UX_JDT_DEMAND_MANAGEMENT_recurrence'
)
    EXEC sys.sp_executesql N'
        CREATE UNIQUE INDEX UX_JDT_DEMAND_MANAGEMENT_recurrence
            ON dbo.JDT_DEMAND_MANAGEMENT (recurrenceGroupId, recurrenceSequence)
            WHERE recurrenceGroupId IS NOT NULL;
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

COMMIT TRANSACTION;
