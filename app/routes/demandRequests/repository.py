from sqlalchemy import text


class DemandRequestsRepository:
    _DETAIL_SELECT = """
        SELECT
            R.requestId,
            R.areaId,
            R.requesterId,
            Requester.name AS requesterName,
            R.contributorId,
            Contributor.name AS contributorName,
            R.title,
            R.info AS initialDescription,
            COALESCE(R.assumptions, '') AS assumptions,
            COALESCE(R.actualProblems, '') AS actualProblems,
            COALESCE(R.benefits, '') AS benefits,
            COALESCE(NULLIF(R.demandType, ''), 'melhoria') AS demandType,
            CASE WHEN R.urgency = 'Imediata' THEN 'Alta' ELSE R.urgency END AS urgency,
            R.openDate AS requestDate,
            R.images,
            CASE M.status
                WHEN 'A Fazer' THEN 5
                WHEN 'Em Andamento' THEN 1
                WHEN 'Pausado' THEN 4
                WHEN 'Concluído' THEN 2
                WHEN 'Cancelado' THEN 6
                ELSE R.status
            END AS status,
            Responsible.name AS responsibleName,
            R.startDate,
            R.deliveryDate AS deadline,
            R.finalDate,
            R.reprogs,
            R.deniedText,
            CASE
                WHEN R.status = 0 AND M.managementId IS NULL THEN 1
                ELSE 0
            END AS pendingEditable
        FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R
        LEFT JOIN JDT_DEMAND_MANAGEMENT AS M
            ON M.sourceRequestId = R.requestId
        JOIN JDT_USER_DETAILS AS Requester
            ON Requester.id = R.requesterId
        LEFT JOIN JDT_USER_DETAILS AS Responsible
            ON Responsible.id = R.respId
        LEFT JOIN JDT_USER_DETAILS AS Contributor
            ON Contributor.id = R.contributorId
    """

    def list_user_requests(self, connection, area_id, user_id):
        query = text("""
            SELECT
                R.requestId,
                Requester.name AS requesterName,
                R.title,
                R.info AS initialDescription,
                COALESCE(NULLIF(R.demandType, ''), 'melhoria') AS demandType,
                CASE WHEN R.urgency = 'Imediata' THEN 'Alta' ELSE R.urgency END AS urgency,
                R.openDate AS requestDate,
                R.deliveryDate AS deadline,
                R.finalDate,
                CASE
                    WHEN R.requesterId = :user_id THEN 'requester'
                    ELSE 'contributor'
                END AS userRelationship,
                CASE M.status
                    WHEN 'A Fazer' THEN 5
                    WHEN 'Em Andamento' THEN 1
                    WHEN 'Pausado' THEN 4
                    WHEN 'Concluído' THEN 2
                    WHEN 'Cancelado' THEN 6
                    ELSE R.status
                END AS status
            FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R
            LEFT JOIN JDT_DEMAND_MANAGEMENT AS M
                ON M.sourceRequestId = R.requestId
            JOIN JDT_USER_DETAILS AS Requester
                ON Requester.id = R.requesterId
            WHERE R.areaId = :area_id
                AND (
                    R.requesterId = :user_id
                    OR R.contributorId = :user_id
                )
            ORDER BY R.openDate DESC, R.requestId DESC
        """)
        return connection.execute(query, {
            'area_id': area_id,
            'user_id': user_id
        }).mappings().all()

    def list_contributors(self, connection, user_id):
        query = text("""
            SELECT U.id, U.name
            FROM JDT_USER_DETAILS AS U
            WHERE U.active = 1
                AND U.generic = 0
                AND U.id <> :user_id
                AND NULLIF(LTRIM(RTRIM(U.companyEmail)), '') IS NOT NULL
            ORDER BY U.name
        """)
        return connection.execute(
            query, {'user_id': user_id}
        ).mappings().all()

    def get_contributor(self, connection, contributor_id):
        query = text("""
            SELECT U.id
            FROM JDT_USER_DETAILS AS U
            WHERE U.id = :contributor_id
                AND U.active = 1
                AND U.generic = 0
                AND NULLIF(LTRIM(RTRIM(U.companyEmail)), '') IS NOT NULL
        """)
        return connection.execute(query, {
            'contributor_id': contributor_id
        }).first()

    def list_area_analytics(self, connection, area_id):
        database_today = connection.execute(text("""
            SELECT CAST(GETDATE() AS DATE)
        """)).scalar()
        query = text("""
            SELECT
                R.requestId,
                COALESCE(NULLIF(R.demandType, ''), N'melhoria') AS demandType,
                R.openDate AS requestDate,
                COALESCE(Completion.completedAt, R.finalDate) AS completedAt,
                Responsible.name AS responsibleName,
                CASE WHEN Responsible.active = 1 THEN 1 ELSE 0 END AS responsibleActive,
                CASE
                    WHEN M.status IS NOT NULL THEN M.status
                    WHEN R.status = 0 THEN N'Em análise'
                    WHEN R.status = 1 AND R.startDate IS NULL THEN N'A Fazer'
                    WHEN R.status = 1 THEN N'Em Andamento'
                    WHEN R.status = 2 THEN N'Concluído'
                    WHEN R.status = 3 THEN N'Recusada'
                    WHEN R.status = 4 THEN N'Pausado'
                    ELSE N'Outro'
                END AS status
            FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R
            LEFT JOIN JDT_DEMAND_MANAGEMENT AS M
                ON M.sourceRequestId = R.requestId
            LEFT JOIN JDT_USER_DETAILS AS Responsible
                ON Responsible.id = CASE
                    WHEN M.managementId IS NULL THEN R.respId
                    ELSE M.responsibleId
                END
            OUTER APPLY (
                SELECT MAX(H.createdAt) AS completedAt
                FROM JDT_DEMAND_MANAGEMENT_HISTORY AS H
                WHERE H.managementId = M.managementId
                    AND H.eventType = 'status_complete'
            ) AS Completion
            WHERE R.areaId = :area_id
        """)
        rows = connection.execute(
            query, {'area_id': area_id}
        ).mappings().all()
        return database_today, rows

    def next_request_id(self, connection):
        query = text("""
            SELECT ISNULL(MAX(requestId), 0) + 1
            FROM JDT_REQUEST_IMPROVEMENTS_SMALL WITH (UPDLOCK, HOLDLOCK)
        """)
        row = connection.execute(query).first()
        return int(row[0])

    def create_request(self, connection, request_id, area_id, user_id, demand, images):
        query = text("""
            INSERT INTO JDT_REQUEST_IMPROVEMENTS_SMALL (
                requestId, requesterId, contributorId, areaId, title, info, urgency,
                openDate, images, status, respId, startDate, deliveryDate,
                finalDate, reprogs, deniedText, assumptions, actualProblems,
                benefits, demandType
            ) VALUES (
                :request_id, :requester_id, :contributor_id, :area_id, :title,
                :initial_description, :urgency, GETDATE(), :images,
                0, NULL, NULL, NULL, NULL, 0, NULL, :assumptions,
                :actual_problems, :benefits, :demand_type
            )
        """)
        result = connection.execute(query, {
            'request_id': request_id,
            'requester_id': user_id,
            'contributor_id': demand['contributorId'],
            'area_id': area_id,
            'title': demand['title'],
            'initial_description': demand['initialDescription'],
            'urgency': demand['urgency'],
            'images': images,
            'assumptions': demand['assumptions'],
            'actual_problems': demand['actualProblems'],
            'benefits': demand['benefits'],
            'demand_type': demand['demandType']
        })
        return result.rowcount == 1

    def update_pending_request(self, connection, request_id, area_id, user_id, demand):
        query = text("""
            UPDATE R
            SET
                title = :title,
                info = :initial_description,
                urgency = :urgency,
                assumptions = :assumptions,
                actualProblems = :actual_problems,
                benefits = :benefits,
                demandType = :demand_type,
                contributorId = :contributor_id
            FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R
            WHERE R.requestId = :request_id
                AND R.areaId = :area_id
                AND R.requesterId = :user_id
                AND R.status = 0
                AND NOT EXISTS (
                    SELECT 1
                    FROM JDT_DEMAND_MANAGEMENT AS M
                    WHERE M.sourceRequestId = R.requestId
                )
        """)
        result = connection.execute(query, {
            'request_id': request_id,
            'area_id': area_id,
            'user_id': user_id,
            'title': demand['title'],
            'initial_description': demand['initialDescription'],
            'urgency': demand['urgency'],
            'assumptions': demand['assumptions'],
            'actual_problems': demand['actualProblems'],
            'benefits': demand['benefits'],
            'demand_type': demand['demandType'],
            'contributor_id': demand['contributorId']
        })
        return result.rowcount == 1

    def get_request(self, connection, request_id, area_id, lock=False):
        lock_hint = ' WITH (UPDLOCK, HOLDLOCK)' if lock else ''
        detail_select = self._DETAIL_SELECT.replace(
            'FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R',
            f'FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R{lock_hint}',
            1
        )
        query = text(detail_select + """
            WHERE R.requestId = :request_id
                AND R.areaId = :area_id
        """)
        return connection.execute(query, {
            'request_id': request_id,
            'area_id': area_id
        }).mappings().first()

    def list_history(self, connection, request_id, area_id):
        query = text("""
            SELECT
                H.historyId,
                H.eventType,
                H.previousStatus,
                H.newStatus,
                H.previousDeadline,
                H.newDeadline,
                H.reason,
                H.expectedReturn,
                H.actorName,
                H.createdAt
            FROM JDT_DEMAND_MANAGEMENT_HISTORY AS H
            JOIN JDT_DEMAND_MANAGEMENT AS M
                ON M.managementId = H.managementId
            WHERE M.sourceRequestId = :request_id
                AND M.areaId = :area_id
            ORDER BY H.createdAt DESC, H.historyId DESC
        """)
        return connection.execute(query, {
            'request_id': request_id,
            'area_id': area_id
        }).mappings().all()

# V3
