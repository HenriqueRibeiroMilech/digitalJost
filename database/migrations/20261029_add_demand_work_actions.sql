-- Proposta para revisão/aplicação manual; não executada pela aplicação.
-- Requer 20261029_create_demand_work.sql. Não altera tabelas nem jobs legados.
-- Executar integralmente no SSMS/sqlcmd, na mesma conexão, antes da publicação.
SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF COL_LENGTH('dbo.DJ_DEMAND_WORK', 'scheduled_start_on') IS NULL
    ALTER TABLE dbo.DJ_DEMAND_WORK ADD scheduled_start_on DATE NULL;
IF COL_LENGTH('dbo.DJ_DEMAND_WORK', 'started_on') IS NULL
    ALTER TABLE dbo.DJ_DEMAND_WORK ADD started_on DATE NULL;
IF COL_LENGTH('dbo.DJ_DEMAND_WORK', 'due_on') IS NULL
    ALTER TABLE dbo.DJ_DEMAND_WORK ADD due_on DATE NULL;
IF COL_LENGTH('dbo.DJ_DEMAND_WORK', 'closed_at') IS NULL
    ALTER TABLE dbo.DJ_DEMAND_WORK ADD closed_at DATETIME2(3) NULL;
GO

-- Separar lotes evita compilar os CHECKs antes da criação das colunas.
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints
               WHERE parent_object_id = OBJECT_ID('dbo.DJ_DEMAND_WORK') AND name = 'CK_DJ_DEMAND_WORK_execution_status')
    ALTER TABLE dbo.DJ_DEMAND_WORK ADD CONSTRAINT CK_DJ_DEMAND_WORK_execution_status CHECK (
        status IN (N'a_fazer', N'agendado', N'em_andamento', N'aguardando_informacoes',
                   N'em_validacao', N'pausado', N'aguardando_terceiros', N'concluido', N'cancelado')
    );

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints
               WHERE parent_object_id = OBJECT_ID('dbo.DJ_DEMAND_WORK') AND name = 'CK_DJ_DEMAND_WORK_execution_dates')
    ALTER TABLE dbo.DJ_DEMAND_WORK ADD CONSTRAINT CK_DJ_DEMAND_WORK_execution_dates CHECK (
        (kind = N'aviso' AND scheduled_start_on IS NULL AND started_on IS NULL AND due_on IS NULL AND closed_at IS NULL)
        OR (kind <> N'aviso'
            AND (scheduled_start_on IS NULL OR started_on IS NULL)
            AND (due_on IS NULL OR due_on >= COALESCE(started_on, scheduled_start_on))
            AND (status <> N'agendado' OR (scheduled_start_on IS NOT NULL AND due_on IS NOT NULL))
            AND (status NOT IN (N'em_andamento', N'em_validacao', N'pausado', N'aguardando_terceiros')
                 OR (started_on IS NOT NULL AND due_on IS NOT NULL))
            AND (status NOT IN (N'concluido', N'cancelado') OR closed_at IS NOT NULL))
    );

COMMIT TRANSACTION;
GO
