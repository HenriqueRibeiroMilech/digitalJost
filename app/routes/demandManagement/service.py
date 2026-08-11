"""Integração transacional entre solicitações e o gerenciador de demandas."""

from sqlalchemy import text


_STATUS_BY_REQUEST_STATUS = {
    1: 'in_progress',
    2: 'completed',
    4: 'paused',
}


def ensure_demand_management_record(
        cnnx,
        request_id,
        responsible_user_id,
        deadline=None,
        request_status=1,
        area_id=1):
    """Cria, de forma idempotente, o vínculo operacional da solicitação aprovada.

    A conexão é recebida do fluxo chamador para que a solicitação e o vínculo
    sejam confirmados (ou revertidos) na mesma transação.
    """
    management_status = _STATUS_BY_REQUEST_STATUS.get(int(request_status), 'in_progress')

    cnnx.execute(
        text("""
            INSERT INTO JDT_DEMAND_MANAGEMENT (
                requestId,
                responsibleUserId,
                status,
                deadline,
                startDate,
                createdAt,
                updatedAt
            )
            SELECT
                source.requestId,
                :responsible_user_id,
                :management_status,
                :deadline,
                COALESCE(source.startDate, GETDATE()),
                GETDATE(),
                GETDATE()
            FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS source
            WHERE source.requestId = :request_id
              AND source.areaId = :area_id
              AND source.status IN (1, 2, 4)
              AND NOT EXISTS (
                  SELECT 1
                  FROM JDT_DEMAND_MANAGEMENT WITH (UPDLOCK, HOLDLOCK)
                  WHERE requestId = :request_id
              )
        """),
        {
            'request_id': request_id,
            'responsible_user_id': responsible_user_id,
            'management_status': management_status,
            'deadline': deadline,
            'area_id': area_id,
        }
    )


def sync_demand_management_record(
        cnnx,
        request_id,
        status=None,
        deadline=None,
        update_deadline=False):
    """Sincroniza mudanças posteriores do fluxo de solicitação, sem commit."""
    updates = ['updatedAt = GETDATE()']
    params = {'request_id': request_id}

    if status is not None:
        updates.append('status = :status')
        params['status'] = status

    if update_deadline:
        updates.append('deadline = :deadline')
        params['deadline'] = deadline

    cnnx.execute(
        text(f"""
            UPDATE JDT_DEMAND_MANAGEMENT
            SET {', '.join(updates)}
            WHERE requestId = :request_id
        """),
        params
    )
