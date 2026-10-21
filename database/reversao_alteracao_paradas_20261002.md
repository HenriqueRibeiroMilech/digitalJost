# Reversão da alteração de paradas de 02/10/2026

Este roteiro reverte **somente** os commits `841096f`, `c7950b8` e
`e485494fa0c020a1a4e83d60bac1e482d6a076af`. A correção anterior de
duplicações (`068ab73`) permanece. O SQL desfaz apenas as sete colunas da
migração `20261002_stopchange_current_status_source.sql`.

## 1. Conferir os dados no SSMS antes de reverter o código

Execute esta consulta no SQL Server. O resultado precisa ser **zero**. Se for
maior que zero, ou se a consulta falhar, pare: existem solicitações ou um schema
que precisam ser analisados antes de voltar ao código antigo.

```sql
USE [TRANSFORMACAODIGITAL_JOST];
GO

SELECT COUNT_BIG(*) AS registros_com_dados_novos
FROM dbo.JDT_REQUEST_STOPCHANGES
WHERE stopSource IS NOT NULL
   OR plexLogKey IS NOT NULL
   OR currentStatusWorkcenter IS NOT NULL
   OR currentStatusStart IS NOT NULL
   OR currentStatusEnd IS NOT NULL
   OR currentStatusMinutes IS NOT NULL
   OR currentStatusReason IS NOT NULL;
```

## 2. Reverter o código no Git Bash

Abra o **Git Bash na pasta do repositório**. Os dois primeiros comandos devem
mostrar, respectivamente, nenhuma alteração e a branch `main`. Se não for
assim, pare. Execute os comandos seguintes um por vez. Se o pull ou o revert
falhar ou apresentar conflito, pare sem fazer commit.

```bash
git status --short
git branch --show-current
git -c core.hooksPath=/dev/null pull --ff-only origin main
git -c core.hooksPath=/dev/null revert --no-commit 841096f c7950b8 e485494fa0c020a1a4e83d60bac1e482d6a076af
git diff --cached --check
git -c core.hooksPath=/dev/null commit -m "Reverte alteracoes da solicitacao de paradas"
```

O commit acima é local. Para enviá-lo à `main` remota, execute separadamente:

```bash
git -c core.hooksPath=/dev/null push origin main
```

Confirme que a versão revertida está em uso antes do passo 3. O revert do Git
não desfaz automaticamente a alteração feita no SQL Server.

## 3. Desfazer as colunas no SSMS

Execute o bloco inteiro abaixo somente depois de publicar o código revertido.
Ele confere novamente se as sete colunas existem e se continuam vazias. Se
houver dados nelas, lança erro e faz rollback sem remover nenhuma coluna.

```sql
USE [TRANSFORMACAODIGITAL_JOST];
GO

SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF (
        SELECT COUNT(*)
        FROM sys.columns
        WHERE object_id = OBJECT_ID(N'dbo.JDT_REQUEST_STOPCHANGES')
          AND name IN (
              N'stopSource',
              N'plexLogKey',
              N'currentStatusWorkcenter',
              N'currentStatusStart',
              N'currentStatusEnd',
              N'currentStatusMinutes',
              N'currentStatusReason'
          )
    ) <> 7
        THROW 50001, 'As sete colunas esperadas nao estao presentes. Revise o schema.', 1;

    DECLARE @has_data bit = 0;

    EXEC sys.sp_executesql
        N'SELECT @has_data = CASE WHEN EXISTS (
            SELECT 1
            FROM dbo.JDT_REQUEST_STOPCHANGES WITH (TABLOCKX, HOLDLOCK)
            WHERE stopSource IS NOT NULL
               OR plexLogKey IS NOT NULL
               OR currentStatusWorkcenter IS NOT NULL
               OR currentStatusStart IS NOT NULL
               OR currentStatusEnd IS NOT NULL
               OR currentStatusMinutes IS NOT NULL
               OR currentStatusReason IS NOT NULL
        ) THEN 1 ELSE 0 END;',
        N'@has_data bit OUTPUT',
        @has_data = @has_data OUTPUT;

    IF @has_data = 1
        THROW 50002, 'Existem solicitacoes com dados nas colunas novas. Nenhuma coluna foi removida.', 1;

    ALTER TABLE dbo.JDT_REQUEST_STOPCHANGES
        DROP COLUMN
            stopSource,
            plexLogKey,
            currentStatusWorkcenter,
            currentStatusStart,
            currentStatusEnd,
            currentStatusMinutes,
            currentStatusReason;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO
```

Se houver erro `50002`, não force a exclusão: é preciso decidir o destino das
solicitações criadas pelo fluxo novo, especialmente as de origem `td`.
