-- Proposta: revisar e aplicar no TD somente em ambiente e janela autorizados.
-- Aplicar após 20261007_create_dj_events.sql e antes de publicar a nova API.
-- Não é executado pela aplicação. Não preencher datas fictícias nos eventos antigos.
-- Horários locais do evento, sem fuso/UTC, com precisão de milissegundos.
SET XACT_ABORT ON;

BEGIN TRANSACTION;

ALTER TABLE dbo.DJ_EVENTS ADD
    starts_at DATETIME2(3) NULL,
    ends_at DATETIME2(3) NULL;

-- SQL dinâmico permite referenciar as colunas novas no mesmo batch, sem GO.
EXEC(N'ALTER TABLE dbo.DJ_EVENTS WITH CHECK ADD CONSTRAINT CK_DJ_EVENTS_schedule
    CHECK (
        (starts_at IS NULL AND ends_at IS NULL)
        OR (starts_at IS NOT NULL AND ends_at IS NOT NULL AND ends_at > starts_at)
    )');

COMMIT TRANSACTION;
