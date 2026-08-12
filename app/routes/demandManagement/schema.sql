/*
    Gerenciador interno de demandas aprovadas.
    Execute manualmente no banco JDT antes de publicar o código.
    O script não é executado pela aplicação.
*/

SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF EXISTS (
    SELECT requestId
    FROM dbo.JDT_REQUEST_IMPROVEMENTS_SMALL
    GROUP BY requestId
    HAVING COUNT(*) > 1
)
    THROW 50001, 'Existem requestId duplicados em JDT_REQUEST_IMPROVEMENTS_SMALL.', 1;

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes AS I
    WHERE I.object_id = OBJECT_ID('dbo.JDT_REQUEST_IMPROVEMENTS_SMALL')
        AND I.is_unique = 1
        AND 1 = (
            SELECT COUNT(*)
            FROM sys.index_columns AS IC
            WHERE IC.object_id = I.object_id
                AND IC.index_id = I.index_id
                AND IC.key_ordinal > 0
        )
        AND EXISTS (
            SELECT 1
            FROM sys.index_columns AS IC
            JOIN sys.columns AS C
                ON C.object_id = IC.object_id AND C.column_id = IC.column_id
            WHERE IC.object_id = I.object_id
                AND IC.index_id = I.index_id
                AND IC.key_ordinal = 1
                AND C.name = 'requestId'
        )
)
BEGIN
    CREATE UNIQUE INDEX UX_JDT_REQUEST_IMPROVEMENTS_SMALL_requestId
        ON dbo.JDT_REQUEST_IMPROVEMENTS_SMALL (requestId);
END;

IF OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.JDT_DEMAND_MANAGEMENT (
        managementId INT IDENTITY(1, 1) NOT NULL,
        sourceRequestId INT NOT NULL,
        areaId INT NOT NULL,
        status NVARCHAR(30) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_status DEFAULT N'A Fazer',
        deadline DATE NULL,
        startDate DATE NULL,
        estimatedHours DECIMAL(10, 2) NULL,
        dailyHours DECIMAL(10, 2) NULL,
        completedHours DECIMAL(10, 2) NULL,
        difficulty NVARCHAR(10) NULL,
        observations NVARCHAR(4000) NULL,
        responsibleId VARCHAR(100) NULL,
        legacyProjectId VARCHAR(30) NULL,
        createdAt DATETIME2(0) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_createdAt DEFAULT SYSDATETIME(),
        updatedAt DATETIME2(0) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_updatedAt DEFAULT SYSDATETIME(),
        rowVersion ROWVERSION NOT NULL,

        CONSTRAINT PK_JDT_DEMAND_MANAGEMENT
            PRIMARY KEY (managementId),
        CONSTRAINT UQ_JDT_DEMAND_MANAGEMENT_sourceRequestId
            UNIQUE (sourceRequestId),
        CONSTRAINT FK_JDT_DEMAND_MANAGEMENT_sourceRequest
            FOREIGN KEY (sourceRequestId)
            REFERENCES dbo.JDT_REQUEST_IMPROVEMENTS_SMALL (requestId),
        CONSTRAINT FK_JDT_DEMAND_MANAGEMENT_area
            FOREIGN KEY (areaId)
            REFERENCES dbo.JDT_GENERAL_AREA (areaId),
        CONSTRAINT FK_JDT_DEMAND_MANAGEMENT_responsible
            FOREIGN KEY (responsibleId)
            REFERENCES dbo.JDT_USER_DETAILS (id),
        CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_status
            CHECK (status IN (N'A Fazer', N'Em Andamento', N'Pausado', N'Concluído', N'Cancelado')),
        CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_difficulty
            CHECK (difficulty IS NULL OR difficulty IN (N'Baixa', N'Média', N'Alta')),
        CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_hours
            CHECK (
                (estimatedHours IS NULL OR estimatedHours >= 0)
                AND (dailyHours IS NULL OR dailyHours >= 0)
                AND (completedHours IS NULL OR completedHours >= 0)
            )
    );

    CREATE INDEX IX_JDT_DEMAND_MANAGEMENT_area_responsible
        ON dbo.JDT_DEMAND_MANAGEMENT (areaId, responsibleId, status);
END;

IF OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS (
        taskId INT IDENTITY(1, 1) NOT NULL,
        managementId INT NOT NULL,
        description NVARCHAR(1000) NOT NULL,
        responsibleId VARCHAR(100) NULL,
        deadline DATE NULL,
        observations NVARCHAR(2000) NULL,
        completedAt DATETIME2(0) NULL,
        createdBy VARCHAR(100) NOT NULL,
        createdAt DATETIME2(0) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_TASKS_createdAt DEFAULT SYSDATETIME(),
        updatedAt DATETIME2(0) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_TASKS_updatedAt DEFAULT SYSDATETIME(),
        rowVersion ROWVERSION NOT NULL,

        CONSTRAINT PK_JDT_DEMAND_MANAGEMENT_TASKS
            PRIMARY KEY (taskId),
        CONSTRAINT FK_JDT_DEMAND_MANAGEMENT_TASKS_management
            FOREIGN KEY (managementId)
            REFERENCES dbo.JDT_DEMAND_MANAGEMENT (managementId)
            ON DELETE CASCADE,
        CONSTRAINT FK_JDT_DEMAND_MANAGEMENT_TASKS_responsible
            FOREIGN KEY (responsibleId)
            REFERENCES dbo.JDT_USER_DETAILS (id),
        CONSTRAINT FK_JDT_DEMAND_MANAGEMENT_TASKS_createdBy
            FOREIGN KEY (createdBy)
            REFERENCES dbo.JDT_USER_DETAILS (id)
    );

    CREATE INDEX IX_JDT_DEMAND_MANAGEMENT_TASKS_management
        ON dbo.JDT_DEMAND_MANAGEMENT_TASKS (managementId, completedAt, deadline);
END;

/* Carga inicial idempotente das demandas já iniciadas, pausadas ou concluídas. */
INSERT INTO dbo.JDT_DEMAND_MANAGEMENT (
    sourceRequestId,
    areaId,
    status,
    deadline,
    startDate,
    responsibleId,
    createdAt,
    updatedAt
)
SELECT
    R.requestId,
    R.areaId,
    CASE R.status
        WHEN 2 THEN N'Concluído'
        WHEN 4 THEN N'Pausado'
        ELSE N'Em Andamento'
    END,
    R.deliveryDate,
    R.startDate,
    R.respId,
    SYSDATETIME(),
    SYSDATETIME()
FROM dbo.JDT_REQUEST_IMPROVEMENTS_SMALL AS R
WHERE R.areaId = 1
    AND R.status IN (1, 2, 4)
    AND NOT EXISTS (
        SELECT 1
        FROM dbo.JDT_DEMAND_MANAGEMENT AS M
        WHERE M.sourceRequestId = R.requestId
    );

COMMIT TRANSACTION;
