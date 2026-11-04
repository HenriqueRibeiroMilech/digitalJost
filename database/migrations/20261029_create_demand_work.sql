-- Proposta para revisão/aplicação manual no TD. Não executada pela aplicação.
-- Requer 20261019_create_dj_demands.sql e 20261029_add_demand_responsible.sql.
-- Executar integralmente no SSMS/sqlcmd, na mesma conexão, antes da publicação.
-- Usar janela com cadastros e aceites interrompidos durante o preenchimento inicial.
SET XACT_ABORT ON;
BEGIN TRANSACTION;

CREATE TABLE dbo.DJ_DEMAND_WORK (
    id INT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_DJ_DEMAND_WORK PRIMARY KEY,
    area_id INT NOT NULL,
    source_request_id INT NULL,
    kind NVARCHAR(16) NOT NULL,
    title NVARCHAR(250) NOT NULL,
    description NVARCHAR(4000) NOT NULL,
    responsible_id NVARCHAR(128) NOT NULL,
    requester_id NVARCHAR(128) NOT NULL,
    contributor_id NVARCHAR(128) NULL,
    urgency NVARCHAR(10) NULL,
    assumptions NVARCHAR(4000) NULL,
    current_problems NVARCHAR(4000) NULL,
    expected_benefits NVARCHAR(4000) NULL,
    starts_at DATETIME2(3) NULL,
    ends_at DATETIME2(3) NULL,
    status NVARCHAR(32) NOT NULL CONSTRAINT DF_DJ_DEMAND_WORK_status DEFAULT N'a_fazer',
    difficulty NVARCHAR(10) NULL,
    priority INT NULL,
    estimated_hours DECIMAL(10, 2) NULL,
    daily_hours DECIMAL(10, 2) NULL,
    completed_hours DECIMAL(10, 2) NOT NULL CONSTRAINT DF_DJ_DEMAND_WORK_completed DEFAULT 0,
    observations NVARCHAR(4000) NULL,
    created_by NVARCHAR(128) NOT NULL,
    submission_key CHAR(36) NULL,
    submission_fingerprint CHAR(64) NULL,
    created_at DATETIME2(3) NOT NULL CONSTRAINT DF_DJ_DEMAND_WORK_created DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2(3) NOT NULL CONSTRAINT DF_DJ_DEMAND_WORK_updated DEFAULT SYSUTCDATETIME(),
    row_version ROWVERSION NOT NULL,
    CONSTRAINT FK_DJ_DEMAND_WORK_request FOREIGN KEY (source_request_id) REFERENCES dbo.DJ_DEMANDS(id),
    CONSTRAINT CK_DJ_DEMAND_WORK_area CHECK (area_id > 0),
    CONSTRAINT CK_DJ_DEMAND_WORK_kind CHECK (kind IN (N'projeto', N'melhoria', N'erro', N'atividade', N'aviso')),
    CONSTRAINT CK_DJ_DEMAND_WORK_title CHECK (LEN(LTRIM(RTRIM(title))) > 0),
    CONSTRAINT CK_DJ_DEMAND_WORK_description CHECK (LEN(LTRIM(RTRIM(description))) > 0),
    CONSTRAINT CK_DJ_DEMAND_WORK_responsible CHECK (LEN(LTRIM(RTRIM(responsible_id))) > 0),
    CONSTRAINT CK_DJ_DEMAND_WORK_details CHECK (
        (kind IN (N'projeto', N'melhoria') AND
            assumptions IS NOT NULL AND LEN(LTRIM(RTRIM(assumptions))) > 0 AND
            current_problems IS NOT NULL AND LEN(LTRIM(RTRIM(current_problems))) > 0 AND
            expected_benefits IS NOT NULL AND LEN(LTRIM(RTRIM(expected_benefits))) > 0)
        OR (kind NOT IN (N'projeto', N'melhoria') AND assumptions IS NULL
            AND current_problems IS NULL AND expected_benefits IS NULL)
    ),
    CONSTRAINT CK_DJ_DEMAND_WORK_period CHECK (
        (kind = N'aviso' AND starts_at IS NOT NULL AND ends_at IS NOT NULL AND ends_at > starts_at)
        OR (kind <> N'aviso' AND starts_at IS NULL AND ends_at IS NULL)
    ),
    CONSTRAINT CK_DJ_DEMAND_WORK_urgency CHECK (
        (kind IN (N'atividade', N'aviso') AND urgency IS NULL AND contributor_id IS NULL)
        OR (kind NOT IN (N'atividade', N'aviso') AND urgency IS NOT NULL AND urgency IN (N'Alta', N'Média', N'Baixa'))
    ),
    CONSTRAINT CK_DJ_DEMAND_WORK_difficulty CHECK (difficulty IS NULL OR difficulty IN (N'Baixa', N'Média', N'Alta')),
    CONSTRAINT CK_DJ_DEMAND_WORK_priority CHECK (priority IS NULL OR priority BETWEEN 1 AND 10),
    CONSTRAINT CK_DJ_DEMAND_WORK_hours CHECK (
        (estimated_hours IS NULL OR estimated_hours BETWEEN 0 AND 99999.99)
        AND (daily_hours IS NULL OR daily_hours BETWEEN 0 AND 99999.99)
        AND completed_hours BETWEEN 0 AND 99999.99
    ),
    CONSTRAINT CK_DJ_DEMAND_WORK_submission CHECK (
        (source_request_id IS NULL AND submission_key IS NOT NULL AND submission_fingerprint IS NOT NULL)
        OR (source_request_id IS NOT NULL AND submission_key IS NULL AND submission_fingerprint IS NULL)
    )
);

CREATE UNIQUE INDEX UQ_DJ_DEMAND_WORK_source ON dbo.DJ_DEMAND_WORK (source_request_id)
    WHERE source_request_id IS NOT NULL;
CREATE UNIQUE INDEX UQ_DJ_DEMAND_WORK_submission ON dbo.DJ_DEMAND_WORK (area_id, created_by, submission_key)
    WHERE submission_key IS NOT NULL;
CREATE INDEX IX_DJ_DEMAND_WORK_owner ON dbo.DJ_DEMAND_WORK (area_id, responsible_id, kind, id DESC);

CREATE TABLE dbo.DJ_DEMAND_WORK_HISTORY (
    id INT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_DJ_DEMAND_WORK_HISTORY PRIMARY KEY,
    work_id INT NOT NULL,
    event_type NVARCHAR(40) NOT NULL,
    actor_id NVARCHAR(128) NOT NULL,
    changes NVARCHAR(MAX) NULL,
    created_at DATETIME2(3) NOT NULL CONSTRAINT DF_DJ_DEMAND_WORK_HISTORY_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_DJ_DEMAND_WORK_HISTORY_work FOREIGN KEY (work_id) REFERENCES dbo.DJ_DEMAND_WORK(id),
    CONSTRAINT CK_DJ_DEMAND_WORK_HISTORY_changes CHECK (changes IS NULL OR ISJSON(changes) = 1)
);
CREATE INDEX IX_DJ_DEMAND_WORK_HISTORY_work ON dbo.DJ_DEMAND_WORK_HISTORY (work_id, id DESC);

CREATE TABLE dbo.DJ_DEMAND_WORK_ATTACHMENTS (
    id INT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_DJ_DEMAND_WORK_ATTACHMENTS PRIMARY KEY,
    work_id INT NOT NULL,
    original_name NVARCHAR(200) NOT NULL,
    storage_key CHAR(32) NOT NULL,
    size_bytes INT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    created_by NVARCHAR(128) NOT NULL,
    created_at DATETIME2(3) NOT NULL CONSTRAINT DF_DJ_DEMAND_WORK_ATTACHMENTS_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_DJ_DEMAND_WORK_ATTACHMENTS_work FOREIGN KEY (work_id) REFERENCES dbo.DJ_DEMAND_WORK(id),
    CONSTRAINT UQ_DJ_DEMAND_WORK_ATTACHMENTS_storage UNIQUE (storage_key),
    CONSTRAINT CK_DJ_DEMAND_WORK_ATTACHMENTS_size CHECK (size_bytes > 0 AND size_bytes <= 10485760)
);
CREATE INDEX IX_DJ_DEMAND_WORK_ATTACHMENTS_work ON dbo.DJ_DEMAND_WORK_ATTACHMENTS (work_id, id);
GO

-- Inclui somente solicitações modernas já aceitas na etapa anterior.
-- Não importa tabelas JDT_*, não move anexos nem altera dados da solicitação.
INSERT INTO dbo.DJ_DEMAND_WORK (
    area_id, source_request_id, kind, title, description, responsible_id, requester_id,
    contributor_id, urgency, assumptions, current_problems, expected_benefits,
    created_by, created_at, updated_at
)
SELECT D.area_id, D.id, CASE WHEN D.entry_kind = N'erro' THEN N'erro' ELSE D.classification END,
    D.title, D.description, D.responsible_id, D.requester_id, D.contributor_id, D.urgency,
    D.assumptions, D.current_problems, D.expected_benefits,
    COALESCE(H.actor_id, D.requester_id), D.updated_at, D.updated_at
FROM dbo.DJ_DEMANDS AS D
OUTER APPLY (
    SELECT TOP (1) actor_id FROM dbo.DJ_DEMAND_HISTORY
    WHERE demand_id = D.id AND event_type = N'accepted' ORDER BY id DESC
) AS H
WHERE D.area_id = 1 AND D.status = N'a_fazer' AND D.responsible_id IS NOT NULL
    AND (D.entry_kind = N'erro' OR D.classification IN (N'projeto', N'melhoria'));

INSERT INTO dbo.DJ_DEMAND_WORK_HISTORY (work_id, event_type, actor_id, created_at)
SELECT id, N'request_accepted', created_by, created_at
FROM dbo.DJ_DEMAND_WORK WHERE source_request_id IS NOT NULL;

COMMIT TRANSACTION;
GO
