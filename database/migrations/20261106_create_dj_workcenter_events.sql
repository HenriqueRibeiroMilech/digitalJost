-- Catálogo local de motivos ativos em TRANSFORMACAODIGITAL_JOST.
-- Revisão/aplicação manual autorizada, antes de publicar a leitura direta.
-- A carga dos dados é feita separadamente pelo importador CSV, sem create_all().
SET XACT_ABORT ON;

IF DB_NAME() <> N'TRANSFORMACAODIGITAL_JOST'
    THROW 50001, 'Selecionar TRANSFORMACAODIGITAL_JOST antes de aplicar a migration.', 1;

BEGIN TRANSACTION;

IF OBJECT_ID('dbo.DJ_WORKCENTER_EVENTS', 'U') IS NOT NULL
    THROW 50001, 'DJ_WORKCENTER_EVENTS já existe. Conferir a estrutura antes de continuar.', 1;

CREATE TABLE dbo.DJ_WORKCENTER_EVENTS (
    id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_DJ_WORKCENTER_EVENTS PRIMARY KEY,
    description NVARCHAR(300) COLLATE Latin1_General_100_CI_AS NOT NULL,
    code NVARCHAR(50) NOT NULL,
    workcenter_event_group NVARCHAR(100) NOT NULL,
    created_at DATETIME2(3) NOT NULL CONSTRAINT DF_DJ_WORKCENTER_EVENTS_created DEFAULT SYSUTCDATETIME(),
    last_synced_at DATETIME2(3) NOT NULL,
    CONSTRAINT UQ_DJ_WORKCENTER_EVENTS_description UNIQUE (description),
    CONSTRAINT CK_DJ_WORKCENTER_EVENTS_description CHECK (LEN(LTRIM(RTRIM(description))) > 0),
    CONSTRAINT CK_DJ_WORKCENTER_EVENTS_group CHECK (LEN(LTRIM(RTRIM(workcenter_event_group))) > 0)
);

COMMIT TRANSACTION;
