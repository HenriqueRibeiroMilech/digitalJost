-- Proposta para revisão e aplicação manual no banco jdt, em janela autorizada.
-- Aplicar após 20261028_create_qsb_control.sql e ANTES de publicar este cadastro.
-- Não executado pelo agente. Não altera os motivos das ocorrências existentes.
SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.JDT_OPE_QUAL_CONTROL', N'U') IS NULL
    THROW 50000, 'Aplicar o controle QSB antes do catálogo de motivos de parada.', 1;

IF OBJECT_ID(N'dbo.JDT_OPE_QUAL_STOP_REASONS', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.JDT_OPE_QUAL_STOP_REASONS (
        name NVARCHAR(150) COLLATE Latin1_General_100_CI_AS NOT NULL
            CONSTRAINT PK_JDT_OPE_QUAL_STOP_REASONS PRIMARY KEY,
        created_by NVARCHAR(128) NULL,
        created_at DATETIME2(3) NOT NULL
            CONSTRAINT DF_QSB_STOP_REASONS_date DEFAULT SYSUTCDATETIME(),
        CONSTRAINT CK_QSB_STOP_REASONS_name CHECK (LEN(LTRIM(RTRIM(name))) > 0)
    );
END;

IF NOT EXISTS (
    SELECT 1 FROM dbo.JDT_OPE_QUAL_STOP_REASONS WITH (UPDLOCK, HOLDLOCK)
    WHERE name = N'Problema de Qualidade'
)
    INSERT INTO dbo.JDT_OPE_QUAL_STOP_REASONS (name, created_by)
    VALUES (N'Problema de Qualidade', NULL);

COMMIT TRANSACTION;
