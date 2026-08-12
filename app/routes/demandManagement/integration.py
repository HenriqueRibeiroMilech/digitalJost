from sqlalchemy import text


def sync_approved_request(connection, request_id):
    """Cria ou atualiza o vínculo operacional sem duplicar a solicitação."""
    query = text("""
        IF NOT EXISTS (
            SELECT 1
            FROM JDT_DEMAND_MANAGEMENT WITH (UPDLOCK, HOLDLOCK)
            WHERE sourceRequestId = :request_id
        )
        BEGIN
            INSERT INTO JDT_DEMAND_MANAGEMENT (
                sourceRequestId, areaId, status, deadline, startDate,
                responsibleId, createdAt, updatedAt
            )
            SELECT
                R.requestId,
                R.areaId,
                CASE R.status
                    WHEN 2 THEN 'Concluído'
                    WHEN 4 THEN 'Pausado'
                    ELSE 'Em Andamento'
                END,
                R.deliveryDate,
                R.startDate,
                R.respId,
                GETDATE(),
                GETDATE()
            FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R
            WHERE R.requestId = :request_id AND R.status IN (1, 2, 4)
        END
        ELSE
        BEGIN
            UPDATE M
            SET
                status = CASE R.status
                    WHEN 2 THEN 'Concluído'
                    WHEN 4 THEN 'Pausado'
                    ELSE 'Em Andamento'
                END,
                deadline = R.deliveryDate,
                startDate = COALESCE(M.startDate, R.startDate),
                updatedAt = GETDATE()
            FROM JDT_DEMAND_MANAGEMENT AS M
            JOIN JDT_REQUEST_IMPROVEMENTS_SMALL AS R
                ON R.requestId = M.sourceRequestId
            WHERE R.requestId = :request_id AND R.status IN (1, 2, 4)
        END
    """)
    connection.execute(query, {'request_id': request_id})
