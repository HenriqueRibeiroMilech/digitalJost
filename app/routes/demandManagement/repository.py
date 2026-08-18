from sqlalchemy import text

from .domain import DIRECT_DEMAND_FIELDS, MANAGEMENT_FIELDS


class DemandManagementRepository:
    _REVIEW_SELECT = """
        SELECT
            R.requestId,
            R.areaId,
            COALESCE(NULLIF(R.demandType, ''), 'melhoria') AS demandType,
            R.title,
            R.info AS initialDescription,
            R.assumptions,
            R.actualProblems,
            R.benefits,
            CASE WHEN R.urgency = 'Imediata' THEN 'Alta' ELSE R.urgency END AS urgency,
            R.openDate AS requestDate,
            R.startDate,
            R.deliveryDate AS deadline,
            R.finalDate,
            R.status,
            R.deniedText,
            R.reprogs,
            CASE WHEN NULLIF(R.images, '') IS NULL THEN 0 ELSE 1 END AS hasAttachments,
            Requester.id AS requesterId,
            Requester.name AS requesterName,
            Requester.companyEmail AS requesterEmail,
            Responsible.id AS responsibleId,
            Responsible.name AS responsibleName
        FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R
        JOIN JDT_USER_DETAILS AS Requester ON Requester.id = R.requesterId
        LEFT JOIN JDT_USER_DETAILS AS Responsible ON Responsible.id = R.respId
    """

    _BASE_SELECT = """
        SELECT
            M.managementId,
            M.sourceRequestId,
            M.areaId,
            M.status,
            M.deadline,
            M.startDate,
            M.estimatedHours,
            M.dailyHours,
            M.completedHours,
            M.difficulty,
            M.observations,
            M.createdBy AS directCreatorId,
            CASE
                WHEN Responsible.active = 1 THEN M.responsibleId
                ELSE NULL
            END AS responsibleId,
            M.createdAt,
            M.updatedAt,
            M.rowVersion,
            COALESCE(NULLIF(M.demandType, ''), NULLIF(R.demandType, ''), 'melhoria') AS demandType,
            COALESCE(M.title, R.title) AS title,
            COALESCE(M.initialDescription, R.info) AS initialDescription,
            COALESCE(M.assumptions, R.assumptions) AS assumptions,
            COALESCE(M.actualProblems, R.actualProblems) AS actualProblems,
            COALESCE(M.benefits, R.benefits) AS benefits,
            CASE WHEN R.urgency = 'Imediata' THEN 'Alta' ELSE R.urgency END AS urgency,
            COALESCE(R.openDate, M.createdAt) AS requestDate,
            R.startDate AS requestStartDate,
            R.deliveryDate AS requestDeadline,
            R.finalDate AS requestFinalDate,
            R.reprogs AS requestReprograms,
            CASE WHEN NULLIF(R.images, '') IS NULL THEN 0 ELSE 1 END AS hasAttachments,
            COALESCE(Requester.id, Creator.id) AS requesterId,
            COALESCE(Requester.name, Creator.name) AS requesterName,
            Creator.name AS createdByName,
            CASE
                WHEN Responsible.active = 1 THEN Responsible.name
                ELSE NULL
            END AS responsibleName,
            COALESCE(TaskCount.totalTasks, 0) AS totalTasks,
            COALESCE(TaskCount.completedTasks, 0) AS completedTasks
        FROM JDT_DEMAND_MANAGEMENT AS M
        LEFT JOIN JDT_REQUEST_IMPROVEMENTS_SMALL AS R
            ON R.requestId = M.sourceRequestId
        LEFT JOIN JDT_USER_DETAILS AS Requester
            ON Requester.id = R.requesterId
        LEFT JOIN JDT_USER_DETAILS AS Creator
            ON Creator.id = M.createdBy
        LEFT JOIN JDT_USER_DETAILS AS Responsible
            ON Responsible.id = M.responsibleId
            AND Responsible.active = 1
        OUTER APPLY (
            SELECT
                COUNT(*) AS totalTasks,
                SUM(CASE WHEN T.completedAt IS NOT NULL THEN 1 ELSE 0 END) AS completedTasks
            FROM JDT_DEMAND_MANAGEMENT_TASKS AS T
            WHERE T.managementId = M.managementId
        ) AS TaskCount
    """

    def list_demands(self, connection, area_id):
        query = text(self._BASE_SELECT + """
            WHERE M.areaId = :area_id
            ORDER BY
                CASE WHEN Responsible.name IS NULL THEN 1 ELSE 0 END,
                Responsible.name,
                M.deadline,
                M.managementId
        """)
        return connection.execute(query, {'area_id': area_id}).mappings().all()

    def list_review_requests(self, connection, area_id):
        query = text(self._REVIEW_SELECT + """
            WHERE R.areaId = :area_id AND R.status IN (0, 3)
            ORDER BY R.status, R.openDate DESC, R.requestId DESC
        """)
        return connection.execute(query, {'area_id': area_id}).mappings().all()

    def get_review_request(self, connection, request_id, area_id, lock=False):
        lock_hint = ' WITH (UPDLOCK, HOLDLOCK)' if lock else ''
        query = text(self._REVIEW_SELECT.replace(
            'FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R',
            f'FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R{lock_hint}'
        ) + """
            WHERE R.requestId = :request_id AND R.areaId = :area_id
        """)
        return connection.execute(query, {
            'request_id': request_id,
            'area_id': area_id
        }).mappings().first()

    def approve_review_request(self, connection, request_id, area_id, deadline, responsible_id):
        query = text("""
            UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL
            SET
                startDate = GETDATE(),
                deliveryDate = :deadline,
                status = 1,
                respId = :responsible_id
            WHERE requestId = :request_id
                AND areaId = :area_id
                AND status = 0
        """)
        result = connection.execute(query, {
            'request_id': request_id,
            'area_id': area_id,
            'deadline': deadline,
            'responsible_id': responsible_id
        })
        return result.rowcount == 1

    def decline_review_request(self, connection, request_id, area_id, reason, responsible_id):
        query = text("""
            UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL
            SET
                finalDate = GETDATE(),
                status = 3,
                respId = :responsible_id,
                deniedText = :reason
            WHERE requestId = :request_id
                AND areaId = :area_id
                AND status = 0
        """)
        result = connection.execute(query, {
            'request_id': request_id,
            'area_id': area_id,
            'reason': reason,
            'responsible_id': responsible_id
        })
        return result.rowcount == 1

    def get_demand(self, connection, management_id, area_id):
        query = text(self._BASE_SELECT + """
            WHERE M.managementId = :management_id AND M.areaId = :area_id
        """)
        return connection.execute(query, {
            'management_id': management_id,
            'area_id': area_id
        }).mappings().first()

    def create_personal_demand(self, connection, area_id, demand, user_id):
        query = text("""
            INSERT INTO JDT_DEMAND_MANAGEMENT (
                sourceRequestId, areaId, status, deadline, startDate,
                estimatedHours, dailyHours, completedHours, difficulty,
                observations, responsibleId, createdBy, demandType, title,
                initialDescription, assumptions, actualProblems, benefits,
                createdAt, updatedAt
            )
            OUTPUT INSERTED.managementId
            VALUES (
                NULL, :area_id, :status, :deadline, :start_date,
                :estimated_hours, :daily_hours, :completed_hours, :difficulty,
                :observations, :user_id, :user_id, :demand_type, :title,
                :initial_description, :assumptions, :actual_problems, :benefits,
                GETDATE(), GETDATE()
            )
        """)
        row = connection.execute(query, {
            'area_id': area_id,
            'status': demand['status'],
            'deadline': demand['deadline'],
            'start_date': demand['startDate'],
            'estimated_hours': demand['estimatedHours'],
            'daily_hours': demand['dailyHours'],
            'completed_hours': demand['completedHours'],
            'difficulty': demand['difficulty'],
            'observations': demand['observations'],
            'user_id': user_id,
            'demand_type': demand['demandType'],
            'title': demand['title'],
            'initial_description': demand['initialDescription'],
            'assumptions': demand['assumptions'],
            'actual_problems': demand['actualProblems'],
            'benefits': demand['benefits']
        }).first()
        return row[0] if row else None

    # def list_responsibles(self, connection, area_id):
    #     query = text("""
    #         SELECT id, name
    #         FROM JDT_USER_DETAILS
    #         WHERE areaId = :area_id AND active = 1 AND generic = 0
    #         ORDER BY name
    #     """)
    #     return connection.execute(query, {'area_id': area_id}).mappings().all()

    def list_responsibles(self, connection, area_id):
        query = text("""
            SELECT DISTINCT
                U.id,
                U.name
            FROM JDT_USER_DETAILS AS U
            JOIN JDT_DEMAND_MANAGEMENT AS M
                ON M.responsibleId = U.id
            WHERE M.areaId = :area_id
                AND U.active = 1
                AND U.generic = 0
            ORDER BY U.name
        """)
        return connection.execute(query, {
            'area_id': area_id
        }).mappings().all()

    # def responsible_belongs_to_area(self, connection, responsible_id, area_id):
    #     query = text("""
    #         SELECT 1
    #         FROM JDT_USER_DETAILS
    #         WHERE id = :responsible_id
    #             AND areaId = :area_id
    #             AND active = 1
    #             AND generic = 0
    #     """)
    #     return connection.execute(query, {
    #         'responsible_id': responsible_id,
    #         'area_id': area_id
    #     }).first() is not None

    def responsible_belongs_to_area(self, connection, responsible_id, area_id):
        query = text("""
            SELECT 1
            FROM JDT_USER_DETAILS AS U
            WHERE U.id = :responsible_id
                AND U.active = 1
                AND U.generic = 0
                AND EXISTS (
                    SELECT 1
                    FROM JDT_DEMAND_MANAGEMENT AS M
                    WHERE M.responsibleId = U.id
                        AND M.areaId = :area_id
                )
        """)
        return connection.execute(query, {
            'responsible_id': responsible_id,
            'area_id': area_id
        }).first() is not None

    def update_field(self, connection, management_id, area_id, field, value, row_version):
        column = MANAGEMENT_FIELDS[field]
        query = text(f"""
            UPDATE JDT_DEMAND_MANAGEMENT
            SET {column} = :value, updatedAt = GETDATE()
            WHERE managementId = :management_id
                AND areaId = :area_id
                AND rowVersion = :row_version
        """)
        result = connection.execute(query, {
            'value': value,
            'management_id': management_id,
            'area_id': area_id,
            'row_version': row_version
        })
        return result.rowcount == 1

    def update_direct_field(
        self, connection, management_id, area_id, field, value, row_version, user_id
    ):
        column = DIRECT_DEMAND_FIELDS[field]
        query = text(f"""
            UPDATE JDT_DEMAND_MANAGEMENT
            SET {column} = :value, updatedAt = GETDATE()
            WHERE managementId = :management_id
                AND areaId = :area_id
                AND sourceRequestId IS NULL
                AND createdBy = :user_id
                AND rowVersion = :row_version
        """)
        result = connection.execute(query, {
            'value': value,
            'management_id': management_id,
            'area_id': area_id,
            'user_id': user_id,
            'row_version': row_version
        })
        return result.rowcount == 1

    def list_tasks(self, connection, management_id, area_id):
        query = text("""
            SELECT
                T.taskId,
                T.description,
                T.responsibleId,
                U.name AS responsibleName,
                T.deadline,
                T.observations,
                T.completedAt,
                T.createdAt,
                T.updatedAt,
                T.rowVersion
            FROM JDT_DEMAND_MANAGEMENT_TASKS AS T
            JOIN JDT_DEMAND_MANAGEMENT AS M ON M.managementId = T.managementId
            LEFT JOIN JDT_USER_DETAILS AS U ON U.id = T.responsibleId
            WHERE T.managementId = :management_id AND M.areaId = :area_id
            ORDER BY
                CASE WHEN T.completedAt IS NULL THEN 0 ELSE 1 END,
                T.deadline,
                T.taskId
        """)
        return connection.execute(query, {
            'management_id': management_id,
            'area_id': area_id
        }).mappings().all()

    def create_task(self, connection, management_id, area_id, task, created_by):
        query = text("""
            INSERT INTO JDT_DEMAND_MANAGEMENT_TASKS (
                managementId, description, responsibleId, deadline,
                observations, completedAt, createdBy, createdAt, updatedAt
            )
            OUTPUT INSERTED.taskId
            SELECT
                M.managementId, :description, :responsible_id, :deadline,
                :observations, CASE WHEN :completed = 1 THEN GETDATE() ELSE NULL END,
                :created_by, GETDATE(), GETDATE()
            FROM JDT_DEMAND_MANAGEMENT AS M
            WHERE M.managementId = :management_id AND M.areaId = :area_id
        """)
        row = connection.execute(query, {
            'management_id': management_id,
            'area_id': area_id,
            'description': task['description'],
            'responsible_id': task['responsibleId'],
            'deadline': task['deadline'],
            'observations': task['observations'],
            'completed': 1 if task['completed'] else 0,
            'created_by': created_by
        }).first()
        return row[0] if row else None

    def update_task(self, connection, management_id, task_id, area_id, task, row_version):
        query = text("""
            UPDATE T
            SET
                description = :description,
                responsibleId = :responsible_id,
                deadline = :deadline,
                observations = :observations,
                completedAt = CASE
                    WHEN :completed = 1 THEN COALESCE(T.completedAt, GETDATE())
                    ELSE NULL
                END,
                updatedAt = GETDATE()
            FROM JDT_DEMAND_MANAGEMENT_TASKS AS T
            JOIN JDT_DEMAND_MANAGEMENT AS M ON M.managementId = T.managementId
            WHERE T.taskId = :task_id
                AND T.managementId = :management_id
                AND M.areaId = :area_id
                AND T.rowVersion = :row_version
        """)
        result = connection.execute(query, {
            'task_id': task_id,
            'management_id': management_id,
            'area_id': area_id,
            'description': task['description'],
            'responsible_id': task['responsibleId'],
            'deadline': task['deadline'],
            'observations': task['observations'],
            'completed': 1 if task['completed'] else 0,
            'row_version': row_version
        })
        return result.rowcount == 1

    def delete_task(self, connection, management_id, task_id, area_id, row_version):
        query = text("""
            DELETE T
            FROM JDT_DEMAND_MANAGEMENT_TASKS AS T
            JOIN JDT_DEMAND_MANAGEMENT AS M ON M.managementId = T.managementId
            WHERE T.taskId = :task_id
                AND T.managementId = :management_id
                AND M.areaId = :area_id
                AND T.rowVersion = :row_version
        """)
        result = connection.execute(query, {
            'task_id': task_id,
            'management_id': management_id,
            'area_id': area_id,
            'row_version': row_version
        })
        return result.rowcount == 1
