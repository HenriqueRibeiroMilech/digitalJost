-- Proposta para revisão e aplicação manual no banco jdt, em janela autorizada.
-- Aplicar ANTES de publicar o código QSB correspondente. Não executado pelo agente.
-- As tabelas complementares preservam as 16 colunas do legado JDT_OPE_QUAL.
-- entry_id é a representação textual do ID legado. Não presumir/refletir seu tipo.
-- Confirmar chave, unicidade e os tipos/tamanhos das 16 colunas existentes na revisão.
-- Nenhum registro antigo é alterado ou removido por este script.
SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.JDT_OPE_QUAL', N'U') IS NULL
    THROW 50000, 'Tabela de origem do QSB não encontrada neste banco.', 1;

IF EXISTS (
    SELECT 1 FROM dbo.JDT_OPE_QUAL
    WHERE id IS NULL OR TRY_CONVERT(BIGINT, id) IS NULL
       OR LEN(CONVERT(NVARCHAR(4000), id)) > 32
)
    THROW 50001, 'Revisar identificadores legados inválidos antes de aplicar o controle.', 1;

IF EXISTS (
    SELECT CONVERT(VARCHAR(32), id) FROM dbo.JDT_OPE_QUAL
    GROUP BY CONVERT(VARCHAR(32), id) HAVING COUNT_BIG(*) > 1
)
    THROW 50002, 'Revisar identificadores legados duplicados antes de aplicar o controle.', 1;

IF OBJECT_ID(N'dbo.JDT_OPE_QUAL_CONTROL', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.JDT_OPE_QUAL_CONTROL (
        entry_id VARCHAR(32) NOT NULL CONSTRAINT PK_JDT_OPE_QUAL_CONTROL PRIMARY KEY,
        stop_time TIME(0) NULL,
        stop_reason NVARCHAR(150) NULL,
        stop_minutes DECIMAL(12, 2) NULL,
        stop_count INT NULL,
        location_detail NVARCHAR(500) NULL,
        publish_qsb BIT NOT NULL CONSTRAINT DF_QSB_CONTROL_publish DEFAULT 1,
        created_by NVARCHAR(128) NULL,
        created_at DATETIME2(3) NULL,
        updated_by NVARCHAR(128) NOT NULL,
        updated_at DATETIME2(3) NOT NULL,
        deleted_by NVARCHAR(128) NULL,
        deleted_at DATETIME2(3) NULL,
        submission_key CHAR(36) NULL,
        submission_fingerprint CHAR(64) NULL,
        CONSTRAINT CK_QSB_CONTROL_stop CHECK (
            (stop_time IS NULL AND stop_reason IS NULL AND stop_minutes IS NULL AND stop_count IS NULL)
            OR (stop_time IS NOT NULL AND stop_reason IS NOT NULL
                AND LEN(LTRIM(RTRIM(stop_reason))) > 0
                AND stop_minutes IS NOT NULL AND stop_minutes > 0
                AND stop_count IS NOT NULL AND stop_count > 0)
        ),
        CONSTRAINT CK_QSB_CONTROL_deleted CHECK (
            (deleted_at IS NULL AND deleted_by IS NULL)
            OR (deleted_at IS NOT NULL AND deleted_by IS NOT NULL)
        )
    );
    CREATE UNIQUE INDEX UQ_QSB_CONTROL_submission
        ON dbo.JDT_OPE_QUAL_CONTROL (created_by, submission_key)
        WHERE submission_key IS NOT NULL;
END;

IF OBJECT_ID(N'dbo.JDT_OPE_QUAL_HISTORY', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.JDT_OPE_QUAL_HISTORY (
        id BIGINT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_JDT_OPE_QUAL_HISTORY PRIMARY KEY,
        entry_id VARCHAR(32) NOT NULL,
        action NVARCHAR(16) NOT NULL,
        actor_id NVARCHAR(128) NOT NULL,
        occurred_at DATETIME2(3) NOT NULL CONSTRAINT DF_QSB_HISTORY_date DEFAULT SYSUTCDATETIME(),
        before_json NVARCHAR(MAX) NULL,
        after_json NVARCHAR(MAX) NOT NULL,
        CONSTRAINT CK_QSB_HISTORY_action CHECK (action IN (N'create', N'update', N'delete')),
        CONSTRAINT CK_QSB_HISTORY_before CHECK (before_json IS NULL OR ISJSON(before_json) = 1),
        CONSTRAINT CK_QSB_HISTORY_after CHECK (ISJSON(after_json) = 1)
    );
    CREATE INDEX IX_QSB_HISTORY_entry ON dbo.JDT_OPE_QUAL_HISTORY (entry_id, id DESC);
END;
COMMIT TRANSACTION;
