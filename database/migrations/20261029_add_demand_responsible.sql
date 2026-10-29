-- Proposta para revisão e aplicação manual no TD, em janela autorizada.
-- Não executada pela aplicação. Aplicar após 20261019_create_dj_demands.sql
-- e antes de publicar esta versão do módulo moderno de demandas.
SET XACT_ABORT ON;

BEGIN TRANSACTION;

ALTER TABLE dbo.DJ_DEMANDS ADD responsible_id NVARCHAR(128) NULL;

ALTER TABLE dbo.DJ_DEMANDS ADD CONSTRAINT CK_DJ_DEMANDS_responsible CHECK (
    responsible_id IS NULL OR LEN(LTRIM(RTRIM(responsible_id))) > 0
);

-- Referência lógica ao cadastro compartilhado; não altera JDT_USER_DETAILS.
-- Classificação e mensagens utilizam os campos existentes e o histórico JSON.
COMMIT TRANSACTION;
