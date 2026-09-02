SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF COL_LENGTH(N'dbo.JDT_DEMAND_MANAGEMENT', N'priority') IS NULL
    BEGIN
        EXEC(N'
            ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT
            ADD priority TINYINT NULL;
        ');
    END;

    IF EXISTS (
        SELECT 1
        FROM sys.columns AS C
        JOIN sys.types AS T
            ON T.user_type_id = C.user_type_id
        WHERE C.object_id = OBJECT_ID(N'dbo.JDT_DEMAND_MANAGEMENT')
            AND C.name = N'priority'
            AND (
                T.name <> N'tinyint'
                OR C.is_nullable <> 1
            )
    )
    BEGIN
        THROW 50001, 'A coluna priority já existe com uma definição incompatível.', 1;
    END;

    EXEC(N'
        IF EXISTS (
            SELECT 1
            FROM dbo.JDT_DEMAND_MANAGEMENT
            WHERE priority IS NOT NULL
                AND priority NOT BETWEEN 1 AND 10
        )
        BEGIN
            THROW 50002, ''Há prioridades fora do intervalo de 1 a 10.'', 1;
        END;

        IF NOT EXISTS (
            SELECT 1
            FROM sys.check_constraints
            WHERE parent_object_id = OBJECT_ID(N''dbo.JDT_DEMAND_MANAGEMENT'')
                AND name = N''CK_JDT_DEMAND_MANAGEMENT_priority''
        )
        BEGIN
            ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT WITH CHECK
            ADD CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_priority
                CHECK (priority IS NULL OR priority BETWEEN 1 AND 10);
        END;

        ALTER TABLE dbo.JDT_DEMAND_MANAGEMENT WITH CHECK
        CHECK CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_priority;
    ');

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
