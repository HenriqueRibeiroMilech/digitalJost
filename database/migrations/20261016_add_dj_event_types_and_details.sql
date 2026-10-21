-- Proposta: revisar e aplicar no TD somente em ambiente e janela autorizados.
-- Aplicar após 20261015_add_dj_events_schedule.sql e antes da API/build compatíveis.
-- A aplicação não executa esta migration. Eventos antigos mantêm os novos campos nulos.
SET XACT_ABORT ON;

BEGIN TRANSACTION;

CREATE TABLE dbo.DJ_EVENT_TYPES (
    id INT IDENTITY(1, 1) NOT NULL CONSTRAINT PK_DJ_EVENT_TYPES PRIMARY KEY,
    name NVARCHAR(80) COLLATE Latin1_General_100_CI_AS NOT NULL,
    created_by NVARCHAR(128) NOT NULL,
    created_at DATETIME2(3) NOT NULL
        CONSTRAINT DF_DJ_EVENT_TYPES_created_at DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_DJ_EVENT_TYPES_name UNIQUE (name),
    CONSTRAINT CK_DJ_EVENT_TYPES_name CHECK (LEN(LTRIM(RTRIM(name))) > 0)
);

ALTER TABLE dbo.DJ_EVENTS ADD
    event_type_id INT NULL,
    instructor NVARCHAR(200) NULL,
    syllabus NVARCHAR(4000) NULL;

-- SQL dinâmico permite referenciar a coluna criada no mesmo batch, sem GO.
EXEC(N'ALTER TABLE dbo.DJ_EVENTS WITH CHECK ADD CONSTRAINT FK_DJ_EVENTS_event_type
    FOREIGN KEY (event_type_id) REFERENCES dbo.DJ_EVENT_TYPES(id)');

COMMIT TRANSACTION;
