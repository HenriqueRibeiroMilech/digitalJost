-- Proposta para revisão/aplicação manual no TD; não executada pela aplicação.
-- Requer as migrations de DJ_DEMANDS, responsável, quadro e ações de 19/29-10-2026.
-- Executar integralmente na mesma conexão SSMS/sqlcmd, antes de publicar o código.
-- Ativar DJ_DEMAND_WORK_AUTOSTART_ENABLED somente após esta aplicação autorizada.
SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF COL_LENGTH('dbo.DJ_DEMAND_WORK', 'expected_return_on') IS NULL
    ALTER TABLE dbo.DJ_DEMAND_WORK ADD expected_return_on DATE NULL;
IF COL_LENGTH('dbo.DJ_DEMAND_WORK', 'hide_after_end') IS NULL
    ALTER TABLE dbo.DJ_DEMAND_WORK ADD hide_after_end BIT NOT NULL CONSTRAINT DF_DJ_DEMAND_WORK_hide_after_end DEFAULT 1 WITH VALUES;
IF COL_LENGTH('dbo.DJ_DEMAND_WORK', 'notice_finalized_at') IS NULL
    ALTER TABLE dbo.DJ_DEMAND_WORK ADD notice_finalized_at DATETIME2(3) NULL;
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE parent_object_id = OBJECT_ID('dbo.DJ_DEMAND_WORK') AND name = 'CK_DJ_DEMAND_WORK_return')
    ALTER TABLE dbo.DJ_DEMAND_WORK ADD CONSTRAINT CK_DJ_DEMAND_WORK_return CHECK (
        expected_return_on IS NULL OR (kind <> N'aviso' AND status = N'pausado' AND started_on IS NOT NULL AND expected_return_on >= started_on));
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE parent_object_id = OBJECT_ID('dbo.DJ_DEMAND_WORK') AND name = 'CK_DJ_DEMAND_WORK_notice_finalized')
    ALTER TABLE dbo.DJ_DEMAND_WORK ADD CONSTRAINT CK_DJ_DEMAND_WORK_notice_finalized CHECK (kind = N'aviso' OR notice_finalized_at IS NULL);

IF OBJECT_ID('dbo.DJ_DEMAND_WORK_TASKS', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.DJ_DEMAND_WORK_TASKS (
        id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_DJ_DEMAND_WORK_TASKS PRIMARY KEY,
        work_id INT NOT NULL,
        title NVARCHAR(250) NOT NULL,
        description NVARCHAR(4000) NULL,
        responsible_id NVARCHAR(128) NOT NULL,
        priority INT NULL,
        due_on DATE NULL,
        completed_at DATETIME2(3) NULL,
        created_by NVARCHAR(128) NOT NULL,
        submission_key CHAR(36) NOT NULL,
        submission_fingerprint CHAR(64) NOT NULL,
        created_at DATETIME2(3) NOT NULL CONSTRAINT DF_DJ_DEMAND_WORK_TASKS_created DEFAULT SYSUTCDATETIME(),
        updated_at DATETIME2(3) NOT NULL CONSTRAINT DF_DJ_DEMAND_WORK_TASKS_updated DEFAULT SYSUTCDATETIME(),
        row_version ROWVERSION NOT NULL,
        CONSTRAINT FK_DJ_DEMAND_WORK_TASKS_work FOREIGN KEY (work_id) REFERENCES dbo.DJ_DEMAND_WORK(id),
        CONSTRAINT CK_DJ_DEMAND_WORK_TASKS_title CHECK (LEN(LTRIM(RTRIM(title))) > 0),
        CONSTRAINT CK_DJ_DEMAND_WORK_TASKS_responsible CHECK (LEN(LTRIM(RTRIM(responsible_id))) > 0),
        CONSTRAINT CK_DJ_DEMAND_WORK_TASKS_priority CHECK (priority IS NULL OR priority BETWEEN 1 AND 10),
        CONSTRAINT UQ_DJ_DEMAND_WORK_TASKS_submission UNIQUE (work_id, created_by, submission_key)
    );
    CREATE INDEX IX_DJ_DEMAND_WORK_TASKS_work ON dbo.DJ_DEMAND_WORK_TASKS(work_id, completed_at, priority, due_on, id);
END;
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id = OBJECT_ID('dbo.DJ_DEMAND_WORK') AND name = 'IX_DJ_DEMAND_WORK_schedule')
    CREATE INDEX IX_DJ_DEMAND_WORK_schedule ON dbo.DJ_DEMAND_WORK(area_id, status, scheduled_start_on, id);

COMMIT TRANSACTION;
GO
