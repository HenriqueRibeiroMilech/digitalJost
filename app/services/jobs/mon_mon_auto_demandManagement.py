"""Inicia automaticamente demandas cujo agendamento já venceu."""

from sqlalchemy import text

from app.utils.db_utils import get_engine


def default(logger):
    engine = get_engine('jdt')
    query = text("""
        SET NOCOUNT ON;

        DECLARE @Started TABLE (
            managementId INT NOT NULL,
            sourceRequestId INT NULL,
            responsibleId NVARCHAR(100) NULL,
            previousStatus NVARCHAR(50) NULL,
            newDeadline DATE NULL,
            scheduledStartAt DATETIME2(0) NOT NULL
        );

        UPDATE M WITH (UPDLOCK, READPAST, ROWLOCK)
        SET
            status = N'Em Andamento',
            startDate = M.scheduledStartAt,
            deadline = DATEADD(
                DAY,
                M.scheduledDeadlineDays,
                CAST(M.scheduledStartAt AS DATE)
            ),
            updatedAt = GETDATE()
        OUTPUT
            INSERTED.managementId,
            INSERTED.sourceRequestId,
            INSERTED.responsibleId,
            DELETED.status,
            INSERTED.deadline,
            INSERTED.scheduledStartAt
        INTO @Started (
            managementId, sourceRequestId, responsibleId,
            previousStatus, newDeadline, scheduledStartAt
        )
        FROM dbo.JDT_DEMAND_MANAGEMENT AS M
        WHERE M.status = N'A Fazer'
            AND M.scheduledStartAt IS NOT NULL
            AND M.scheduledDeadlineDays IS NOT NULL
            AND M.scheduledStartAt <= GETDATE()
            AND (
                M.recurrenceAvailableDate IS NULL
                OR M.recurrenceAvailableDate <= GETDATE()
            );

        UPDATE R
        SET
            status = 1,
            startDate = Started.scheduledStartAt,
            deliveryDate = Started.newDeadline,
            finalDate = NULL
        FROM dbo.JDT_REQUEST_IMPROVEMENTS_SMALL AS R
        JOIN @Started AS Started
            ON Started.sourceRequestId = R.requestId;

        INSERT INTO dbo.JDT_DEMAND_MANAGEMENT_HISTORY (
            managementId, eventType, previousStatus, newStatus,
            previousDeadline, newDeadline, reason, expectedReturn,
            actorId, actorName, createdAt
        )
        SELECT
            Started.managementId, N'status_start', Started.previousStatus,
            N'Em Andamento', NULL, Started.newDeadline, NULL, NULL,
            Started.responsibleId, N'Sistema (agendamento)', GETDATE()
        FROM @Started AS Started;

        SELECT COUNT(*) AS startedCount FROM @Started;
    """)

    with engine.begin() as connection:
        started_count = connection.execute(query).scalar() or 0

    if started_count:
        logger.info(
            '%s demanda(s) iniciada(s) automaticamente.', started_count
        )
    else:
        logger.debug('Nenhuma demanda com início agendado pendente.')
