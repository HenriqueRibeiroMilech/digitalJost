-- Proposta: revisar e aplicar no TD somente em ambiente e janela autorizados.
-- Aplicar após 20261015_create_dj_event_attendance.sql e antes de publicar API/build.
-- A aplicação não executa este script. Não preenche nem exclui presenças existentes.
SET XACT_ABORT ON;

BEGIN TRANSACTION;

ALTER TABLE dbo.DJ_EVENT_ATTENDANCE_ENTRIES ADD
    company NVARCHAR(200) NULL,
    [shift] NVARCHAR(200) NULL;

COMMIT TRANSACTION;
