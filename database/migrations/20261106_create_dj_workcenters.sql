-- Cadastro moderno no banco TRANSFORMACAODIGITAL_JOST.
-- Proposta para revisão e aplicação manual autorizada; não executada pelo sistema.
-- Aplicar antes de habilitar DJ_WORKCENTERS_SYNC_ENABLED no serviço H24.
SET XACT_ABORT ON;

IF DB_NAME() <> N'TRANSFORMACAODIGITAL_JOST'
    THROW 50001, 'Selecionar o banco TRANSFORMACAODIGITAL_JOST antes de aplicar a migration.', 1;

BEGIN TRANSACTION;

IF OBJECT_ID('dbo.DJ_WORKCENTERS', 'U') IS NOT NULL
    THROW 50001, 'DJ_WORKCENTERS já existe. Conferir a estrutura antes de continuar.', 1;

CREATE TABLE dbo.DJ_WORKCENTERS (
    id INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_DJ_WORKCENTERS PRIMARY KEY,
    plex_workcenter_key INT NOT NULL,
    workcenter_code NVARCHAR(50) COLLATE Latin1_General_100_CI_AS NOT NULL,
    name NVARCHAR(200) NOT NULL,
    workcenter_group NVARCHAR(100) NULL,
    created_at DATETIME2(3) NOT NULL CONSTRAINT DF_DJ_WORKCENTERS_created DEFAULT SYSUTCDATETIME(),
    last_synced_at DATETIME2(3) NOT NULL,
    CONSTRAINT UQ_DJ_WORKCENTERS_plex_key UNIQUE (plex_workcenter_key),
    CONSTRAINT UQ_DJ_WORKCENTERS_code UNIQUE (workcenter_code),
    CONSTRAINT CK_DJ_WORKCENTERS_plex_key CHECK (plex_workcenter_key > 0),
    CONSTRAINT CK_DJ_WORKCENTERS_code CHECK (LEN(LTRIM(RTRIM(workcenter_code))) > 0),
    CONSTRAINT CK_DJ_WORKCENTERS_name CHECK (LEN(LTRIM(RTRIM(name))) > 0)
);

COMMIT TRANSACTION;
