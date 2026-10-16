-- Proposta: revisar e aplicar no TD somente em ambiente e janela autorizados.
-- Requer 20261016_add_dj_event_attendance_company_shift.sql.
-- Em ambiente existente, publicar primeiro a API que não usa mais shift.
-- Remove a coluna de turno e seus valores. A aplicação não executa este script.
SET XACT_ABORT ON;

BEGIN TRANSACTION;

ALTER TABLE dbo.DJ_EVENT_ATTENDANCE_ENTRIES DROP COLUMN [shift];

COMMIT TRANSACTION;
