"""Gera recorrências e inicia demandas cujo agendamento já venceu."""

from sqlalchemy import text

from app.services.demand_recurrence import next_activity_occurrence
from app.utils.db_utils import get_engine


MAX_RECURRENCE_BACKFILL = 1000


def _list_latest_active_recurrences(connection):
    return connection.execute(text("""
        SELECT
            M.managementId,
            M.sourceRequestId,
            M.demandType,
            M.recurrenceGroupId,
            M.recurrenceType,
            M.recurrenceMaxOccurrences,
            M.recurrenceSequence,
            M.recurrenceStatus,
            M.recurrenceAvailableDate,
            M.scheduledStartAt,
            M.createdBy,
            M.createdAt,
            M.updatedAt,
            GETDATE() AS databaseNow
        FROM dbo.JDT_DEMAND_MANAGEMENT AS M WITH (
            UPDLOCK, READPAST, ROWLOCK
        )
        WHERE M.sourceRequestId IS NULL
            AND M.demandType = N'atividade'
            AND M.recurrenceGroupId IS NOT NULL
            AND M.recurrenceStatus = N'active'
            AND NOT EXISTS (
                SELECT 1
                FROM dbo.JDT_DEMAND_MANAGEMENT AS Later
                WHERE Later.recurrenceGroupId = M.recurrenceGroupId
                    AND Later.recurrenceSequence > M.recurrenceSequence
            )
    """)).mappings().all()


def _get_scheduled_anchor(connection, recurrence_group_id):
    return connection.execute(text("""
        SELECT TOP 1 scheduledStartAt, recurrenceSequence
        FROM dbo.JDT_DEMAND_MANAGEMENT
        WHERE recurrenceGroupId = :recurrence_group_id
            AND scheduledStartAt IS NOT NULL
        ORDER BY recurrenceSequence, managementId
    """), {
        'recurrence_group_id': recurrence_group_id
    }).mappings().first()


def _end_recurrence(connection, management_id):
    result = connection.execute(text("""
        UPDATE dbo.JDT_DEMAND_MANAGEMENT
        SET recurrenceStatus = N'ended', updatedAt = GETDATE()
        WHERE managementId = :management_id
            AND recurrenceGroupId IS NOT NULL
            AND recurrenceStatus <> N'ended'
    """), {'management_id': management_id})
    return result.rowcount == 1


def _create_next_recurrence(
    connection, current, available_at, scheduled_start_at, next_sequence
):
    result = connection.execute(text("""
        INSERT INTO dbo.JDT_DEMAND_MANAGEMENT (
            sourceRequestId, areaId, status, deadline, startDate,
            estimatedHours, dailyHours, completedHours, difficulty, priority,
            observations, responsibleId, createdBy, demandType, title,
            initialDescription, assumptions, actualProblems, benefits,
            recurrenceGroupId, recurrenceType, recurrenceEndDate,
            recurrenceMaxOccurrences, recurrenceSequence,
            recurrenceStatus, recurrenceAvailableDate,
            skipNextOccurrence, scheduledStartAt,
            scheduledDeadlineDays, createdAt, updatedAt
        )
        SELECT
            NULL, M.areaId, N'A Fazer', NULL, NULL,
            M.estimatedHours, M.dailyHours, NULL, M.difficulty, M.priority,
            NULL, M.responsibleId, M.createdBy, N'atividade', M.title,
            M.initialDescription, M.assumptions, M.actualProblems, M.benefits,
            M.recurrenceGroupId, M.recurrenceType, NULL,
            M.recurrenceMaxOccurrences, :next_sequence,
            N'active', :available_at, 0, :scheduled_start_at,
            M.scheduledDeadlineDays, GETDATE(), GETDATE()
        FROM dbo.JDT_DEMAND_MANAGEMENT AS M
        WHERE M.managementId = :management_id
            AND M.sourceRequestId IS NULL
            AND M.demandType = N'atividade'
            AND M.recurrenceGroupId IS NOT NULL
            AND NOT EXISTS (
                SELECT 1
                FROM dbo.JDT_DEMAND_MANAGEMENT AS NextDemand WITH (
                    UPDLOCK, HOLDLOCK
                )
                WHERE NextDemand.recurrenceGroupId = M.recurrenceGroupId
                    AND NextDemand.recurrenceSequence >= :next_sequence
            )
    """), {
        'management_id': current['managementId'],
        'available_at': available_at,
        'scheduled_start_at': scheduled_start_at,
        'next_sequence': next_sequence
    })
    return result.rowcount == 1


def _create_due_recurrences(connection):
    created_count = 0
    ended_count = 0

    # Cada rodada cria no máximo uma ocorrência por série. A repetição recupera
    # ciclos vencidos durante uma eventual indisponibilidade do serviço.
    for _ in range(MAX_RECURRENCE_BACKFILL):
        progressed = False
        for current in _list_latest_active_recurrences(connection):
            scheduled_anchor = _get_scheduled_anchor(
                connection, current['recurrenceGroupId']
            )
            next_occurrence = next_activity_occurrence(
                current, scheduled_anchor
            )
            if next_occurrence is None:
                if _end_recurrence(
                    connection, current['managementId']
                ):
                    ended_count += 1
                    progressed = True
                continue

            available_at, scheduled_start_at, next_sequence = next_occurrence
            if available_at > current['databaseNow']:
                continue
            if _create_next_recurrence(
                connection,
                current,
                available_at,
                scheduled_start_at,
                next_sequence
            ):
                created_count += 1
                progressed = True

        if not progressed:
            break

    return created_count, ended_count


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
            startDate = CAST(M.scheduledStartAt AS DATE),
            deadline = CASE
                WHEN M.scheduledDeadlineDays IS NULL THEN NULL
                ELSE DATEADD(
                    DAY,
                    M.scheduledDeadlineDays,
                    CAST(M.scheduledStartAt AS DATE)
                )
            END,
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
            AND DATEADD(
                MINUTE,
                1,
                CAST(CAST(M.scheduledStartAt AS DATE) AS DATETIME2)
            ) <= GETDATE()
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
        recurrence_count, ended_recurrence_count = _create_due_recurrences(
            connection
        )
        started_count = connection.execute(query).scalar() or 0

    if recurrence_count:
        logger.info(
            '%s ocorrência(s) recorrente(s) criada(s).', recurrence_count
        )
    if ended_recurrence_count:
        logger.info(
            '%s recorrência(s) encerrada(s) pelo limite de ocorrências.',
            ended_recurrence_count
        )
    if started_count:
        logger.info(
            '%s demanda(s) iniciada(s) automaticamente.', started_count
        )
    else:
        logger.debug('Nenhuma demanda com início agendado pendente.')

# V2
