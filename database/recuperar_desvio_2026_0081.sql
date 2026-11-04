/*
Recuperação pontual do desvio 2026-0081-2. Não executado pelo agente.
Aplicar somente após publicar a correção da aprovação e do job H24.

Por padrão, @Aplicar = 0 faz apenas a consulta de conferência e encerra.
Um responsável autorizado deve revisar o resultado e alterar @Aplicar para 1
para persistir a recuperação. Não altera setores, aprovadores ou datas.

Pré-condições: exatamente as três revisões informadas no diagnóstico;
revisão 01 ainda ativa (5/6); revisão 02 recusada (2), com exatamente
11 registros setoriais aprovados (1), todos sem justificativa de recusa.
O resultado esperado é revisão 02 aguardando liberação (0).
*/
SET NOCOUNT ON;

DECLARE @Aplicar bit = 0;
DECLARE @Base varchar(20) = '2026-0081';
DECLARE @Desvio varchar(20) = '2026-0081-2';
DECLARE @Anterior varchar(20) = '2026-0081-1';

IF @Aplicar = 0
BEGIN
    SELECT
        D.deviationId,
        D.revision AS revisao_exibida,
        D.status AS status_geral,
        COUNT(C.deviationId) AS total_setores,
        SUM(CASE WHEN C.status = 1 THEN 1 ELSE 0 END) AS aprovados,
        SUM(CASE WHEN C.textDenied IS NOT NULL THEN 1 ELSE 0 END) AS com_justificativa
    FROM JDT_REQUEST_DEV D
    LEFT JOIN JDT_REQUEST_DEV_CONFIG_STATUS C ON C.deviationId = D.deviationId
    WHERE D.deviationId LIKE @Base + '-%'
    GROUP BY D.deviationId, D.revision, D.status
    ORDER BY D.revision, D.deviationId;

    PRINT 'Somente conferência. Nenhum registro foi alterado.';
    RETURN;
END;

IF @@TRANCOUNT <> 0
BEGIN
    PRINT 'Operação cancelada: execute em uma sessão sem transação aberta.';
    RETURN;
END;

SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @TotalRevisoes int;
    SELECT @TotalRevisoes = COUNT(1)
    FROM JDT_REQUEST_DEV WITH (UPDLOCK, HOLDLOCK)
    WHERE deviationId LIKE @Base + '-%';

    IF @TotalRevisoes <> 3
        THROW 51001, 'As revisões mudaram desde o diagnóstico. Revisar antes de recuperar.', 1;

    IF NOT EXISTS (
        SELECT 1 FROM JDT_REQUEST_DEV
        WHERE deviationId = @Anterior AND status IN (5, 6)
    )
        THROW 51002, 'A revisão anterior não está ativa. Revisar a recuperação.', 1;

    DECLARE @TotalSetores int;
    SELECT @TotalSetores = COUNT(1)
    FROM JDT_REQUEST_DEV_CONFIG_STATUS WITH (UPDLOCK, HOLDLOCK)
    WHERE deviationId = @Desvio;

    IF @TotalSetores <> 11
        THROW 51003, 'A quantidade de registros setoriais difere do diagnóstico.', 1;

    IF EXISTS (
        SELECT 1 FROM JDT_REQUEST_DEV_CONFIG_STATUS
        WHERE deviationId = @Desvio
          AND (ISNULL(status, 0) <> 1 OR textDenied IS NOT NULL)
    )
        THROW 51004, 'Há setor não aprovado ou justificativa de recusa. Revisar o registro.', 1;

    UPDATE JDT_REQUEST_DEV
    SET status = 0
    WHERE deviationId = @Desvio AND status = 2;

    IF @@ROWCOUNT <> 1
        THROW 51005, 'A revisão 02 não está no estado recusado esperado.', 1;

    COMMIT TRANSACTION;

    SELECT deviationId, revision AS revisao_exibida, status AS status_geral
    FROM JDT_REQUEST_DEV
    WHERE deviationId = @Desvio;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
