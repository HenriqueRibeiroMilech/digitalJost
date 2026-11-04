-- Proposta para revisão/aplicação manual no TD, em janela autorizada.
-- Não executada pela aplicação. Não altera nem importa tabelas JDT_*.
-- Aplicar antes de publicar a API e o build das solicitações modernas.
SET XACT_ABORT ON;

BEGIN TRANSACTION;

CREATE TABLE dbo.DJ_DEMANDS (
    id INT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_DJ_DEMANDS PRIMARY KEY,
    area_id INT NOT NULL,
    requester_id NVARCHAR(128) NOT NULL,
    contributor_id NVARCHAR(128) NULL,
    entry_kind NVARCHAR(10) NOT NULL,
    classification NVARCHAR(16) NULL,
    status NVARCHAR(32) NOT NULL
        CONSTRAINT DF_DJ_DEMANDS_status DEFAULT N'em_analise',
    title NVARCHAR(250) NOT NULL,
    description NVARCHAR(4000) NOT NULL,
    urgency NVARCHAR(10) NOT NULL,
    assumptions NVARCHAR(4000) NULL,
    current_problems NVARCHAR(4000) NULL,
    expected_benefits NVARCHAR(4000) NULL,
    submission_key CHAR(36) NOT NULL,
    submission_fingerprint CHAR(64) NOT NULL,
    created_at DATETIME2(3) NOT NULL
        CONSTRAINT DF_DJ_DEMANDS_created_at DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2(3) NOT NULL
        CONSTRAINT DF_DJ_DEMANDS_updated_at DEFAULT SYSUTCDATETIME(),
    row_version ROWVERSION NOT NULL,
    CONSTRAINT UQ_DJ_DEMANDS_submission UNIQUE (area_id, requester_id, submission_key),
    CONSTRAINT CK_DJ_DEMANDS_area CHECK (area_id > 0),
    CONSTRAINT CK_DJ_DEMANDS_requester CHECK (LEN(LTRIM(RTRIM(requester_id))) > 0),
    CONSTRAINT CK_DJ_DEMANDS_contributor CHECK (
        contributor_id IS NULL OR
        (LEN(LTRIM(RTRIM(contributor_id))) > 0 AND contributor_id <> requester_id)
    ),
    CONSTRAINT CK_DJ_DEMANDS_kind CHECK (entry_kind IN (N'demanda', N'erro')),
    CONSTRAINT CK_DJ_DEMANDS_classification CHECK (
        classification IS NULL OR
        (entry_kind = N'demanda' AND classification IN (N'melhoria', N'projeto', N'atividade'))
    ),
    CONSTRAINT CK_DJ_DEMANDS_status CHECK (LEN(LTRIM(RTRIM(status))) > 0),
    CONSTRAINT CK_DJ_DEMANDS_title CHECK (LEN(LTRIM(RTRIM(title))) > 0),
    CONSTRAINT CK_DJ_DEMANDS_description CHECK (LEN(LTRIM(RTRIM(description))) > 0),
    CONSTRAINT CK_DJ_DEMANDS_urgency CHECK (urgency IN (N'Alta', N'Média', N'Baixa')),
    CONSTRAINT CK_DJ_DEMANDS_details CHECK (
        entry_kind = N'erro' OR (
            assumptions IS NOT NULL AND LEN(LTRIM(RTRIM(assumptions))) > 0 AND
            current_problems IS NOT NULL AND LEN(LTRIM(RTRIM(current_problems))) > 0 AND
            expected_benefits IS NOT NULL AND LEN(LTRIM(RTRIM(expected_benefits))) > 0
        )
    )
);

CREATE INDEX IX_DJ_DEMANDS_requester ON dbo.DJ_DEMANDS (area_id, requester_id, id DESC);
CREATE INDEX IX_DJ_DEMANDS_contributor ON dbo.DJ_DEMANDS (area_id, contributor_id, id DESC)
    WHERE contributor_id IS NOT NULL;

CREATE TABLE dbo.DJ_DEMAND_ATTACHMENTS (
    id INT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_DJ_DEMAND_ATTACHMENTS PRIMARY KEY,
    demand_id INT NOT NULL,
    original_name NVARCHAR(200) NOT NULL,
    storage_key CHAR(32) NOT NULL,
    size_bytes INT NOT NULL,
    sha256 CHAR(64) NOT NULL,
    created_by NVARCHAR(128) NOT NULL,
    created_at DATETIME2(3) NOT NULL
        CONSTRAINT DF_DJ_DEMAND_ATTACHMENTS_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_DJ_DEMAND_ATTACHMENTS_demand FOREIGN KEY (demand_id)
        REFERENCES dbo.DJ_DEMANDS(id),
    CONSTRAINT UQ_DJ_DEMAND_ATTACHMENTS_storage UNIQUE (storage_key),
    CONSTRAINT CK_DJ_DEMAND_ATTACHMENTS_size CHECK (size_bytes > 0 AND size_bytes <= 10485760)
);
CREATE INDEX IX_DJ_DEMAND_ATTACHMENTS_demand ON dbo.DJ_DEMAND_ATTACHMENTS (demand_id, id);

CREATE TABLE dbo.DJ_DEMAND_HISTORY (
    id INT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_DJ_DEMAND_HISTORY PRIMARY KEY,
    demand_id INT NOT NULL,
    event_type NVARCHAR(40) NOT NULL,
    actor_id NVARCHAR(128) NOT NULL,
    changes NVARCHAR(MAX) NULL,
    created_at DATETIME2(3) NOT NULL
        CONSTRAINT DF_DJ_DEMAND_HISTORY_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_DJ_DEMAND_HISTORY_demand FOREIGN KEY (demand_id)
        REFERENCES dbo.DJ_DEMANDS(id),
    CONSTRAINT CK_DJ_DEMAND_HISTORY_changes CHECK (changes IS NULL OR ISJSON(changes) = 1)
);
CREATE INDEX IX_DJ_DEMAND_HISTORY_demand ON dbo.DJ_DEMAND_HISTORY (demand_id, id DESC);

-- IDs de usuários são referências lógicas ao cadastro compartilhado existente.
-- Uma FK para JDT_USER_DETAILS depende de confirmar tipo, tamanho e chave reais.
-- Nenhuma tarefa, pausa, classificação ou automação de gerenciamento é criada nesta etapa.
COMMIT TRANSACTION;
