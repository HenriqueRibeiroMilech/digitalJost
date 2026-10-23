-- Revisar/aplicar manualmente no TD após 20261019_create_dj_demands.sql.
-- Não executado pela aplicação. Sem cópia, alteração ou exclusão de tabelas JDT_*.
SET XACT_ABORT ON;
BEGIN TRANSACTION;

ALTER TABLE dbo.DJ_DEMANDS ADD
    origin NVARCHAR(16) NOT NULL CONSTRAINT DF_DJ_DEMANDS_origin DEFAULT N'solicitacao',
    responsible_id NVARCHAR(128) NULL,
    deadline DATE NULL,
    started_at DATETIME2(3) NULL,
    completed_at DATETIME2(3) NULL,
    completed_on DATE NULL,
    scheduled_start_date DATE NULL,
    estimated_hours DECIMAL(10,2) NULL,
    daily_hours DECIMAL(10,2) NULL,
    completed_hours DECIMAL(10,2) NULL,
    difficulty NVARCHAR(10) NULL,
    priority INT NULL,
    observations NVARCHAR(4000) NULL,
    expected_return DATE NULL,
    portal_url NVARCHAR(1000) NULL;
ALTER TABLE dbo.DJ_DEMAND_ATTACHMENTS ADD deleted_at DATETIME2(3) NULL;
ALTER TABLE dbo.DJ_DEMANDS DROP CONSTRAINT CK_DJ_DEMANDS_details;
EXEC(N'ALTER TABLE dbo.DJ_DEMANDS ADD CONSTRAINT CK_DJ_DEMANDS_details CHECK (
    entry_kind = N''erro'' OR (classification IS NOT NULL AND classification = N''atividade'') OR (
        assumptions IS NOT NULL AND LEN(LTRIM(RTRIM(assumptions))) > 0 AND
        current_problems IS NOT NULL AND LEN(LTRIM(RTRIM(current_problems))) > 0 AND
        expected_benefits IS NOT NULL AND LEN(LTRIM(RTRIM(expected_benefits))) > 0))');
-- Constraints em batch separado para as colunas acrescentadas.
EXEC(N'ALTER TABLE dbo.DJ_DEMANDS ADD
    CONSTRAINT CK_DJ_DEMANDS_origin CHECK (origin IN (N''solicitacao'', N''interna'')),
    CONSTRAINT CK_DJ_DEMANDS_hours CHECK (
        (estimated_hours IS NULL OR estimated_hours BETWEEN 0 AND 99999.99) AND
        (daily_hours IS NULL OR daily_hours BETWEEN 0 AND 99999.99) AND
        (completed_hours IS NULL OR completed_hours BETWEEN 0 AND 99999.99)),
    CONSTRAINT CK_DJ_DEMANDS_priority CHECK (priority IS NULL OR priority BETWEEN 1 AND 10),
    CONSTRAINT CK_DJ_DEMANDS_difficulty CHECK (difficulty IS NULL OR difficulty IN (N''Baixa'', N''Média'', N''Alta''))');
EXEC(N'CREATE INDEX IX_DJ_DEMANDS_management ON dbo.DJ_DEMANDS(area_id, status, completed_on)');

CREATE TABLE dbo.DJ_DEMAND_TASKS (
    id INT IDENTITY PRIMARY KEY,
    demand_id INT NOT NULL REFERENCES dbo.DJ_DEMANDS(id),
    description NVARCHAR(1000) NOT NULL,
    responsible_id NVARCHAR(128) NULL,
    priority INT NULL CHECK (priority BETWEEN 1 AND 10),
    deadline DATE NULL,
    observations NVARCHAR(2000) NULL,
    completed_at DATETIME2(3) NULL,
    created_at DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    row_version ROWVERSION NOT NULL
);
CREATE INDEX IX_DJ_DEMAND_TASKS_demand ON dbo.DJ_DEMAND_TASKS(demand_id, id);

CREATE TABLE dbo.DJ_DEMAND_INFORMATION_REQUESTS (
    id INT IDENTITY PRIMARY KEY,
    demand_id INT NOT NULL REFERENCES dbo.DJ_DEMANDS(id),
    kind NVARCHAR(16) NOT NULL CHECK (kind IN (N'informacoes', N'reuniao')),
    question NVARCHAR(4000) NOT NULL,
    previous_status NVARCHAR(32) NOT NULL,
    requested_by NVARCHAR(128) NOT NULL,
    requested_at DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    reply NVARCHAR(4000) NULL,
    replied_by NVARCHAR(128) NULL,
    closed_at DATETIME2(3) NULL
);
CREATE UNIQUE INDEX UQ_DJ_DEMAND_INFORMATION_open
    ON dbo.DJ_DEMAND_INFORMATION_REQUESTS(demand_id) WHERE closed_at IS NULL;

CREATE TABLE dbo.DJ_DEMAND_NOTICES (
    id INT IDENTITY PRIMARY KEY,
    area_id INT NOT NULL,
    title NVARCHAR(250) NOT NULL,
    description NVARCHAR(4000) NOT NULL,
    starts_at DATETIME2(3) NULL,
    ends_at DATETIME2(3) NULL,
    hide_after_end BIT NOT NULL DEFAULT 0,
    created_by NVARCHAR(128) NOT NULL,
    submission_key CHAR(36) NOT NULL,
    submission_fingerprint CHAR(64) NOT NULL,
    created_at DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
    finalized_at DATETIME2(3) NULL,
    row_version ROWVERSION NOT NULL,
    CONSTRAINT CK_DJ_DEMAND_NOTICES_period CHECK (starts_at IS NULL OR ends_at IS NULL OR ends_at > starts_at),
    CONSTRAINT CK_DJ_DEMAND_NOTICES_end CHECK (hide_after_end = 0 OR ends_at IS NOT NULL)
);
CREATE INDEX IX_DJ_DEMAND_NOTICES_area ON dbo.DJ_DEMAND_NOTICES(area_id, finalized_at);
CREATE UNIQUE INDEX UQ_DJ_DEMAND_NOTICES_submission ON dbo.DJ_DEMAND_NOTICES(area_id, created_by, submission_key);

CREATE TABLE dbo.DJ_DEMAND_NOTIFICATIONS (
    id INT IDENTITY PRIMARY KEY,
    demand_id INT NOT NULL REFERENCES dbo.DJ_DEMANDS(id),
    history_id INT NOT NULL UNIQUE REFERENCES dbo.DJ_DEMAND_HISTORY(id),
    target_id NVARCHAR(128) NOT NULL,
    message NVARCHAR(MAX) NOT NULL,
    portal_url NVARCHAR(1000) NOT NULL,
    state NVARCHAR(16) NOT NULL DEFAULT N'pending'
        CHECK (state IN (N'pending', N'sending', N'sent', N'failed')),
    attempts INT NOT NULL DEFAULT 0,
    claimed_at DATETIME2(3) NULL,
    sent_at DATETIME2(3) NULL
);
CREATE INDEX IX_DJ_DEMAND_NOTIFICATIONS_pending ON dbo.DJ_DEMAND_NOTIFICATIONS(state, claimed_at);
CREATE INDEX IX_DJ_DEMAND_NOTIFICATIONS_demand ON dbo.DJ_DEMAND_NOTIFICATIONS(demand_id, state);
COMMIT TRANSACTION;
