from sqlalchemy import text


class DemandRequestsRepository:
    def list_user_requests(self, connection, area_id, user_id):
        query = text("""
            SELECT
                R.requestId,
                R.title,
                R.info AS initialDescription,
                COALESCE(NULLIF(R.demandType, ''), 'melhoria') AS demandType,
                CASE WHEN R.urgency = 'Imediata' THEN 'Alta' ELSE R.urgency END AS urgency,
                R.openDate AS requestDate,
                R.deliveryDate AS deadline,
                R.finalDate,
                R.status
            FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R
            WHERE R.requesterId = :user_id
                AND R.areaId = :area_id
            ORDER BY R.openDate DESC, R.requestId DESC
        """)
        return connection.execute(query, {
            'area_id': area_id,
            'user_id': user_id
        }).mappings().all()
