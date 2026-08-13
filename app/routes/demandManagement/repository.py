from sqlalchemy import text

from .constants import MANAGEMENT_FIELDS


class DemandManagementRepository:
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
            CASE
                WHEN Responsible.active = 1 THEN M.responsibleId
                ELSE NULL
            END AS responsibleId,
            M.createdAt,
            M.updatedAt,
            M.rowVersion,
            COALESCE(NULLIF(R.demandType, ''), 'melhoria') AS demandType,
            R.title,
            R.info AS initialDescription,
            R.assumptions,
            R.actualProblems,
            R.benefits,
            CASE WHEN R.urgency = 'Imediata' THEN 'Alta' ELSE R.urgency END AS urgency,
            R.openDate AS requestDate,
            R.startDate AS requestStartDate,
            R.deliveryDate AS requestDeadline,
            R.finalDate AS requestFinalDate,
            R.reprogs AS requestReprograms,
            CASE WHEN NULLIF(R.images, '') IS NULL THEN 0 ELSE 1 END AS hasAttachments,
            Requester.id AS requesterId,
            Requester.name AS requesterName,
            CASE
                WHEN Responsible.active = 1 THEN Responsible.name
                ELSE NULL
            END AS responsibleName,
            COALESCE(TaskCount.totalTasks, 0) AS totalTasks,
            COALESCE(TaskCount.completedTasks, 0) AS completedTasks
        FROM JDT_DEMAND_MANAGEMENT AS M
        JOIN JDT_REQUEST_IMPROVEMENTS_SMALL AS R
            ON R.requestId = M.sourceRequestId
        JOIN JDT_USER_DETAILS AS Requester
            ON Requester.id = R.requesterId
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

    def get_demand(self, connection, management_id, area_id):
        query = text(self._BASE_SELECT + """
            WHERE M.managementId = :management_id AND M.areaId = :area_id
        """)
        return connection.execute(query, {
            'management_id': management_id,
            'area_id': area_id
        }).mappings().first()

    def list_responsibles(self, connection, area_id):
        query = text("""
            SELECT id, name
            FROM JDT_USER_DETAILS
            WHERE areaId = :area_id AND active = 1 AND generic = 0
            ORDER BY name
        """)
        return connection.execute(query, {'area_id': area_id}).mappings().all()

    def responsible_belongs_to_area(self, connection, responsible_id, area_id):
        query = text("""
            SELECT 1
            FROM JDT_USER_DETAILS
            WHERE id = :responsible_id
                AND areaId = :area_id
                AND active = 1
                AND generic = 0
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
