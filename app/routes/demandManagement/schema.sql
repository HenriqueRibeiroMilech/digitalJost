/*
    Gerenciador de Demandas - Transformação Digital

    Ordem de implantação:
    1. Executar este script no banco do Digital JOST.
    2. Publicar o código da aplicação.

    O bloco de carga inicial é idempotente e pode ser executado novamente.
*/

SET XACT_ABORT ON;
BEGIN TRY
BEGIN TRANSACTION;

IF OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.JDT_DEMAND_MANAGEMENT (
        managementId INT IDENTITY(1, 1) NOT NULL,
        requestId INT NOT NULL,
        responsibleUserId VARCHAR(30) NOT NULL,
        status VARCHAR(20) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_status DEFAULT ('todo'),
        deadline DATE NULL,
        startDate DATE NULL,
        estimatedHours DECIMAL(10, 2) NULL,
        dailyHours DECIMAL(10, 2) NULL,
        actualHours DECIMAL(10, 2) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_actualHours DEFAULT (0),
        difficulty VARCHAR(10) NULL,
        observations VARCHAR(MAX) NULL,
        legacyProjectId VARCHAR(30) NULL,
        createdAt DATETIME2(0) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_createdAt DEFAULT (GETDATE()),
        updatedAt DATETIME2(0) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_updatedAt DEFAULT (GETDATE()),
        rowVersion ROWVERSION NOT NULL,

        CONSTRAINT PK_JDT_DEMAND_MANAGEMENT
            PRIMARY KEY CLUSTERED (managementId),
        CONSTRAINT UQ_JDT_DEMAND_MANAGEMENT_requestId
            UNIQUE (requestId),
        CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_status
            CHECK (status IN ('todo', 'in_progress', 'paused', 'completed', 'cancelled')),
        CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_difficulty
            CHECK (difficulty IS NULL OR difficulty IN ('low', 'medium', 'high')),
        CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_estimatedHours
            CHECK (estimatedHours IS NULL OR estimatedHours >= 0),
        CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_dailyHours
            CHECK (dailyHours IS NULL OR dailyHours >= 0),
        CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_actualHours
            CHECK (actualHours >= 0)
    );

    CREATE INDEX IX_JDT_DEMAND_MANAGEMENT_responsible_status
        ON dbo.JDT_DEMAND_MANAGEMENT (responsibleUserId, status)
        INCLUDE (deadline, difficulty);
END;

IF OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_TASKS', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.JDT_DEMAND_MANAGEMENT_TASKS (
        taskId INT IDENTITY(1, 1) NOT NULL,
        managementId INT NOT NULL,
        description VARCHAR(MAX) NOT NULL,
        responsibleUserId VARCHAR(30) NULL,
        deadline DATE NULL,
        completed BIT NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_TASKS_completed DEFAULT (0),
        sortOrder INT NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_TASKS_sortOrder DEFAULT (0),
        createdAt DATETIME2(0) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_TASKS_createdAt DEFAULT (GETDATE()),
        updatedAt DATETIME2(0) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_TASKS_updatedAt DEFAULT (GETDATE()),
        rowVersion ROWVERSION NOT NULL,

        CONSTRAINT PK_JDT_DEMAND_MANAGEMENT_TASKS
            PRIMARY KEY CLUSTERED (taskId),
        CONSTRAINT FK_JDT_DEMAND_MANAGEMENT_TASKS_management
            FOREIGN KEY (managementId)
            REFERENCES dbo.JDT_DEMAND_MANAGEMENT (managementId)
            ON DELETE CASCADE,
        CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_TASKS_sortOrder
            CHECK (sortOrder >= 0)
    );

    CREATE INDEX IX_JDT_DEMAND_MANAGEMENT_TASKS_management
        ON dbo.JDT_DEMAND_MANAGEMENT_TASKS (managementId, completed, sortOrder);
END;

IF OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_ATTACHMENTS', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.JDT_DEMAND_MANAGEMENT_ATTACHMENTS (
        attachmentId VARCHAR(36) NOT NULL,
        managementId INT NOT NULL,
        originalName NVARCHAR(255) NOT NULL,
        storedName VARCHAR(255) NOT NULL,
        mimeType VARCHAR(150) NOT NULL,
        sizeBytes BIGINT NOT NULL,
        uploadedBy VARCHAR(30) NOT NULL,
        uploadedAt DATETIME2(0) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_ATTACHMENTS_uploadedAt DEFAULT (GETDATE()),

        CONSTRAINT PK_JDT_DEMAND_MANAGEMENT_ATTACHMENTS
            PRIMARY KEY CLUSTERED (attachmentId),
        CONSTRAINT UQ_JDT_DEMAND_MANAGEMENT_ATTACHMENTS_storedName
            UNIQUE (storedName),
        CONSTRAINT FK_JDT_DEMAND_MANAGEMENT_ATTACHMENTS_management
            FOREIGN KEY (managementId)
            REFERENCES dbo.JDT_DEMAND_MANAGEMENT (managementId)
            ON DELETE CASCADE,
        CONSTRAINT CK_JDT_DEMAND_MANAGEMENT_ATTACHMENTS_sizeBytes
            CHECK (sizeBytes >= 0 AND sizeBytes <= 20971520)
    );

    CREATE INDEX IX_JDT_DEMAND_MANAGEMENT_ATTACHMENTS_management
        ON dbo.JDT_DEMAND_MANAGEMENT_ATTACHMENTS (managementId, uploadedAt DESC);
END;

IF OBJECT_ID('dbo.JDT_DEMAND_MANAGEMENT_HISTORY', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.JDT_DEMAND_MANAGEMENT_HISTORY (
        historyId BIGINT IDENTITY(1, 1) NOT NULL,
        managementId INT NOT NULL,
        fieldName VARCHAR(50) NOT NULL,
        oldValue VARCHAR(MAX) NULL,
        newValue VARCHAR(MAX) NULL,
        changedBy VARCHAR(30) NOT NULL,
        changedAt DATETIME2(0) NOT NULL
            CONSTRAINT DF_JDT_DEMAND_MANAGEMENT_HISTORY_changedAt DEFAULT (GETDATE()),

        CONSTRAINT PK_JDT_DEMAND_MANAGEMENT_HISTORY
            PRIMARY KEY CLUSTERED (historyId),
        CONSTRAINT FK_JDT_DEMAND_MANAGEMENT_HISTORY_management
            FOREIGN KEY (managementId)
            REFERENCES dbo.JDT_DEMAND_MANAGEMENT (managementId)
    );

    CREATE INDEX IX_JDT_DEMAND_MANAGEMENT_HISTORY_management
        ON dbo.JDT_DEMAND_MANAGEMENT_HISTORY (managementId, changedAt DESC);
END;

/*
    Carga inicial das demandas já aprovadas/iniciadas da Transformação Digital.
    Mapeamento do fluxo atual: 1 iniciada, 2 finalizada e 4 pausada.
*/
INSERT INTO dbo.JDT_DEMAND_MANAGEMENT (
    requestId,
    responsibleUserId,
    status,
    deadline,
    startDate,
    actualHours,
    createdAt,
    updatedAt
)
SELECT
    source.requestId,
    source.respId,
    CASE source.status
        WHEN 1 THEN 'in_progress'
        WHEN 2 THEN 'completed'
        WHEN 4 THEN 'paused'
    END,
    CAST(source.deliveryDate AS DATE),
    CAST(source.startDate AS DATE),
    0,
    COALESCE(source.startDate, source.openDate, GETDATE()),
    GETDATE()
FROM dbo.JDT_REQUEST_IMPROVEMENTS_SMALL AS source
WHERE source.areaId = 1
  AND source.status IN (1, 2, 4)
  AND NULLIF(LTRIM(RTRIM(source.respId)), '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM dbo.JDT_DEMAND_MANAGEMENT AS management WITH (UPDLOCK, HOLDLOCK)
      WHERE management.requestId = source.requestId
  );

COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
