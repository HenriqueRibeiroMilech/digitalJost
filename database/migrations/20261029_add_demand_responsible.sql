-- Proposta para revisão e aplicação manual no TD, em janela autorizada.
-- Não executada pela aplicação. Aplicar após 20261019_create_dj_demands.sql
-- e antes de publicar esta versão do módulo moderno de demandas.

-- Executar integralmente no SSMS/sqlcmd, na mesma conexão: GO separa lotes,
-- mas a transação continua aberta até o COMMIT.
SET XACT_ABORT ON;

BEGIN TRANSACTION;

-- Permite repetir o script se a coluna já tiver sido criada em outra tentativa.
IF COL_LENGTH(N'dbo.DJ_DEMANDS', N'responsible_id') IS NULL
    ALTER TABLE dbo.DJ_DEMANDS ADD responsible_id NVARCHAR(128) NULL;
GO

-- O CHECK precisa ser compilado em outro lote, após a criação da coluna.
IF NOT EXISTS (
    SELECT 1
    FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.DJ_DEMANDS')
        AND name = N'CK_DJ_DEMANDS_responsible'
)
    ALTER TABLE dbo.DJ_DEMANDS ADD CONSTRAINT CK_DJ_DEMANDS_responsible CHECK (
        responsible_id IS NULL OR LEN(LTRIM(RTRIM(responsible_id))) > 0
    );

-- Referência lógica ao cadastro compartilhado; não altera JDT_USER_DETAILS.
-- Classificação e mensagens utilizam os campos existentes e o histórico JSON.
COMMIT TRANSACTION;
GO
