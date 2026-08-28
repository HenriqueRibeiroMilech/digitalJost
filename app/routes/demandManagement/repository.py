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
            R.images,
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
            R.images,
            CASE WHEN NULLIF(R.images, '') IS NULL THEN 0 ELSE 1 END AS hasAttachments,
            COALESCE(Requester.id, Creator.id) AS requesterId,
            COALESCE(Requester.name, Creator.name) AS requesterName,
            COALESCE(Requester.companyEmail, Creator.companyEmail) AS requesterEmail,
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
            WHERE R.areaId = :area_id
                AND (
                    R.status = 0
                    OR (
                        R.status = 3
                        AND NOT EXISTS (
                            SELECT 1
                            FROM JDT_DEMAND_MANAGEMENT AS M
                            WHERE M.sourceRequestId = R.requestId
                        )
                    )
                )
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

    def approve_review_request(self, connection, request_id, area_id, responsible_id):
        query = text("""
            UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL
            SET
                startDate = NULL,
                deliveryDate = NULL,
                finalDate = NULL,
                status = 1,
                respId = :responsible_id
            WHERE requestId = :request_id
                AND areaId = :area_id
                AND status = 0
        """)
        result = connection.execute(query, {
            'request_id': request_id,
            'area_id': area_id,
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

    def get_demand(self, connection, management_id, area_id, lock=False):
        lock_hint = ' WITH (UPDLOCK, HOLDLOCK)' if lock else ''
        base_select = self._BASE_SELECT.replace(
            'FROM JDT_DEMAND_MANAGEMENT AS M',
            f'FROM JDT_DEMAND_MANAGEMENT AS M{lock_hint}',
            1
        )
        query = text(base_select + """
            WHERE M.managementId = :management_id AND M.areaId = :area_id
        """)
        return connection.execute(query, {
            'management_id': management_id,
            'area_id': area_id
        }).mappings().first()

    def list_history(self, connection, management_id, area_id):
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
            WHERE H.managementId = :management_id
                AND M.areaId = :area_id
            ORDER BY H.createdAt DESC, H.historyId DESC
        """)
        return connection.execute(query, {
            'management_id': management_id,
            'area_id': area_id
        }).mappings().all()

    def insert_history(
        self, connection, management_id, event_type, actor,
        previous_status=None, new_status=None, previous_deadline=None,
        new_deadline=None, reason=None, expected_return=None
    ):
        query = text("""
            INSERT INTO JDT_DEMAND_MANAGEMENT_HISTORY (
                managementId, eventType, previousStatus, newStatus,
                previousDeadline, newDeadline, reason, expectedReturn,
                actorId, actorName, createdAt
            ) VALUES (
                :management_id, :event_type, :previous_status, :new_status,
                :previous_deadline, :new_deadline, :reason, :expected_return,
                :actor_id, :actor_name, GETDATE()
            )
        """)
        connection.execute(query, {
            'management_id': management_id,
            'event_type': event_type,
            'previous_status': previous_status,
            'new_status': new_status,
            'previous_deadline': previous_deadline,
            'new_deadline': new_deadline,
            'reason': reason,
            'expected_return': expected_return,
            'actor_id': actor['id'],
            'actor_name': actor['name']
        })

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
            WHERE U.active = 1
                AND U.generic = 0
                AND (
                    U.areaId = :area_id
                    OR EXISTS (
                        SELECT 1
                        FROM JDT_DEMAND_MANAGEMENT AS M
                        WHERE M.responsibleId = U.id
                            AND M.areaId = :area_id
                    )
                )
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
                AND (
                    U.areaId = :area_id
                    OR EXISTS (
                        SELECT 1
                        FROM JDT_DEMAND_MANAGEMENT AS M
                        WHERE M.responsibleId = U.id
                            AND M.areaId = :area_id
                    )
                )
        """)
        return connection.execute(query, {
            'responsible_id': responsible_id,
            'area_id': area_id
        }).first() is not None

    def get_responsible(self, connection, responsible_id, area_id):
        query = text("""
            SELECT U.id, U.name, U.companyEmail AS email
            FROM JDT_USER_DETAILS AS U
            WHERE U.id = :responsible_id
                AND U.active = 1
                AND U.generic = 0
                AND (
                    U.areaId = :area_id
                    OR EXISTS (
                        SELECT 1
                        FROM JDT_DEMAND_MANAGEMENT AS M
                        WHERE M.responsibleId = U.id
                            AND M.areaId = :area_id
                    )
                )
        """)
        return connection.execute(query, {
            'responsible_id': responsible_id,
            'area_id': area_id
        }).mappings().first()

    def transition_demand(
        self, connection, management_id, area_id, current_status, transition
    ):
        action = transition['action']
        query = text("""
            UPDATE JDT_DEMAND_MANAGEMENT
            SET
                status = :target_status,
                deadline = CASE
                    WHEN :deadline IS NOT NULL THEN :deadline
                    ELSE deadline
                END,
                startDate = CASE
                    WHEN :set_start_date = 1 THEN GETDATE()
                    ELSE startDate
                END,
                updatedAt = GETDATE()
            WHERE managementId = :management_id
                AND areaId = :area_id
                AND status = :current_status
                AND rowVersion = :row_version
        """)
        result = connection.execute(query, {
            'management_id': management_id,
            'area_id': area_id,
            'current_status': current_status,
            'target_status': transition['targetStatus'],
            'deadline': transition['deadline'],
            'set_start_date': 1 if action == 'start' else 0,
            'row_version': transition['rowVersion']
        })
        return result.rowcount == 1

    def transition_source_request(self, connection, request_id, transition):
        action = transition['action']
        if action == 'start':
            query = text("""
                UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL
                SET status = 1, startDate = GETDATE(), deliveryDate = :deadline,
                    finalDate = NULL
                WHERE requestId = :request_id
            """)
        elif action == 'pause':
            query = text("""
                UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL
                SET status = 4
                WHERE requestId = :request_id
            """)
        elif action == 'resume':
            query = text("""
                UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL
                SET status = 1, finalDate = NULL
                WHERE requestId = :request_id
            """)
        elif action == 'reopen':
            query = text("""
                UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL
                SET status = 1, deliveryDate = :deadline, finalDate = NULL,
                    reprogs = ISNULL(reprogs, 0) + 1
                WHERE requestId = :request_id
            """)
        elif action == 'complete':
            query = text("""
                UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL
                SET status = 2, finalDate = GETDATE()
                WHERE requestId = :request_id
            """)
        elif action == 'cancel':
            query = text("""
                UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL
                SET status = 3, finalDate = GETDATE(), deniedText = :reason
                WHERE requestId = :request_id
            """)
        else:
            return False

        parameters = {'request_id': request_id}
        if action in ('start', 'reopen'):
            parameters['deadline'] = transition['deadline']
        elif action == 'cancel':
            parameters['reason'] = transition['reason']

        result = connection.execute(query, parameters)

        if action == 'pause':
            connection.execute(text("""
                INSERT INTO JDT_REQUEST_PAUSES (
                    initDate, expectDate, finalDate, requestId, [text]
                ) VALUES (
                    GETDATE(), :expected_return, NULL, :request_id, :reason
                )
            """), {
                'request_id': request_id,
                'expected_return': transition['expectedReturn'],
                'reason': transition['reason']
            })
        elif action in ('resume', 'cancel'):
            connection.execute(text("""
                UPDATE JDT_REQUEST_PAUSES
                SET finalDate = GETDATE()
                WHERE requestId = :request_id AND finalDate IS NULL
            """), {'request_id': request_id})

        return result.rowcount == 1

    def update_deadline(self, connection, management_id, area_id, deadline, row_version):
        query = text("""
            UPDATE JDT_DEMAND_MANAGEMENT
            SET
                deadline = :deadline,
                updatedAt = GETDATE()
            WHERE managementId = :management_id
                AND areaId = :area_id
                AND rowVersion = :row_version
        """)
        result = connection.execute(query, {
            'deadline': deadline,
            'management_id': management_id,
            'area_id': area_id,
            'row_version': row_version
        })
        return result.rowcount == 1

    def update_source_deadline(self, connection, request_id, deadline):
        query = text("""
            UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL
            SET
                reprogs = ISNULL(reprogs, 0) + CASE
                    WHEN deliveryDate IS NULL OR deliveryDate = :deadline THEN 0
                    ELSE 1
                END,
                deliveryDate = :deadline
            WHERE requestId = :request_id
        """)
        result = connection.execute(query, {
            'request_id': request_id,
            'deadline': deadline
        })
        return result.rowcount == 1

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
                AND responsibleId = :user_id
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
                T.recurrenceGroupId,
                T.recurrenceType,
                T.recurrenceEndDate,
                T.recurrenceMaxOccurrences,
                T.recurrenceSequence,
                T.recurrenceStatus,
                T.skipNextOccurrence,
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

    def get_task(self, connection, management_id, task_id, area_id, lock=False):
        lock_hint = ' WITH (UPDLOCK, HOLDLOCK)' if lock else ''
        query = text(f"""
            SELECT
                T.taskId,
                T.managementId,
                T.description,
                T.responsibleId,
                T.deadline,
                T.observations,
                T.completedAt,
                T.createdBy,
                T.recurrenceGroupId,
                T.recurrenceType,
                T.recurrenceEndDate,
                T.recurrenceMaxOccurrences,
                T.recurrenceSequence,
                T.recurrenceStatus,
                T.skipNextOccurrence,
                T.rowVersion
            FROM JDT_DEMAND_MANAGEMENT_TASKS AS T{lock_hint}
            JOIN JDT_DEMAND_MANAGEMENT AS M ON M.managementId = T.managementId
            WHERE T.taskId = :task_id
                AND T.managementId = :management_id
                AND M.areaId = :area_id
        """)
        return connection.execute(query, {
            'task_id': task_id,
            'management_id': management_id,
            'area_id': area_id
        }).mappings().first()

    def create_task(self, connection, management_id, area_id, task, created_by):
        query = text("""
            INSERT INTO JDT_DEMAND_MANAGEMENT_TASKS (
                managementId, description, responsibleId, deadline,
                observations, completedAt, createdBy, recurrenceGroupId,
                recurrenceType, recurrenceEndDate, recurrenceMaxOccurrences,
                recurrenceSequence, recurrenceStatus, skipNextOccurrence,
                createdAt, updatedAt
            )
            OUTPUT INSERTED.taskId
            SELECT
                M.managementId, :description, :responsible_id, :deadline,
                :observations, CASE WHEN :completed = 1 THEN GETDATE() ELSE NULL END,
                :created_by,
                CASE WHEN :recurrence_type IS NULL THEN NULL ELSE NEWID() END,
                :recurrence_type, :recurrence_end_date,
                :recurrence_max_occurrences,
                CASE WHEN :recurrence_type IS NULL THEN NULL ELSE 1 END,
                CASE WHEN :recurrence_type IS NULL THEN NULL ELSE N'active' END,
                0, GETDATE(), GETDATE()
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
            'recurrence_type': task['recurrenceType'],
            'recurrence_end_date': task['recurrenceEndDate'],
            'recurrence_max_occurrences': task['recurrenceMaxOccurrences'],
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
                recurrenceGroupId = CASE
                    WHEN :recurrence_type IS NULL THEN T.recurrenceGroupId
                    ELSE COALESCE(T.recurrenceGroupId, NEWID())
                END,
                recurrenceType = :recurrence_type,
                recurrenceEndDate = :recurrence_end_date,
                recurrenceMaxOccurrences = :recurrence_max_occurrences,
                recurrenceSequence = CASE
                    WHEN :recurrence_type IS NULL THEN T.recurrenceSequence
                    ELSE COALESCE(T.recurrenceSequence, 1)
                END,
                recurrenceStatus = :recurrence_status,
                skipNextOccurrence = :skip_next_occurrence,
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
            'recurrence_type': task['recurrenceType'],
            'recurrence_end_date': task['recurrenceEndDate'],
            'recurrence_max_occurrences': task['recurrenceMaxOccurrences'],
            'recurrence_status': task['recurrenceStatus'],
            'skip_next_occurrence': 1 if task['skipNextOccurrence'] else 0,
            'row_version': row_version
        })
        return result.rowcount == 1

    def recurrence_has_later_task(
        self, connection, recurrence_group_id, recurrence_sequence
    ):
        if recurrence_group_id is None:
            return False
        query = text("""
            SELECT 1
            FROM JDT_DEMAND_MANAGEMENT_TASKS
            WHERE recurrenceGroupId = :recurrence_group_id
                AND recurrenceSequence > :recurrence_sequence
        """)
        return connection.execute(query, {
            'recurrence_group_id': recurrence_group_id,
            'recurrence_sequence': recurrence_sequence or 0
        }).first() is not None

    def get_recurrence_anchor_day(self, connection, recurrence_group_id):
        query = text("""
            SELECT TOP 1 DAY(deadline) AS anchorDay
            FROM JDT_DEMAND_MANAGEMENT_TASKS
            WHERE recurrenceGroupId = :recurrence_group_id
                AND deadline IS NOT NULL
            ORDER BY recurrenceSequence, taskId
        """)
        row = connection.execute(query, {
            'recurrence_group_id': recurrence_group_id
        }).first()
        return row[0] if row else None

    def create_next_recurring_task(
        self, connection, current_task, deadline, recurrence_sequence, created_by
    ):
        query = text("""
            INSERT INTO JDT_DEMAND_MANAGEMENT_TASKS (
                managementId, description, responsibleId, deadline,
                observations, completedAt, createdBy, recurrenceGroupId,
                recurrenceType, recurrenceEndDate, recurrenceMaxOccurrences,
                recurrenceSequence, recurrenceStatus, skipNextOccurrence,
                createdAt, updatedAt
            )
            SELECT
                T.managementId, T.description, T.responsibleId, :deadline,
                NULL, NULL, :created_by, T.recurrenceGroupId,
                T.recurrenceType, T.recurrenceEndDate,
                T.recurrenceMaxOccurrences, :recurrence_sequence,
                N'active', 0, GETDATE(), GETDATE()
            FROM JDT_DEMAND_MANAGEMENT_TASKS AS T
            WHERE T.taskId = :task_id
                AND T.recurrenceGroupId IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1
                    FROM JDT_DEMAND_MANAGEMENT_TASKS AS NextTask
                    WHERE NextTask.recurrenceGroupId = T.recurrenceGroupId
                        AND NextTask.recurrenceSequence >= :recurrence_sequence
                )
        """)
        result = connection.execute(query, {
            'task_id': current_task['taskId'],
            'deadline': deadline,
            'recurrence_sequence': recurrence_sequence,
            'created_by': created_by
        })
        return result.rowcount == 1

    def end_task_recurrence(self, connection, task_id):
        query = text("""
            UPDATE JDT_DEMAND_MANAGEMENT_TASKS
            SET recurrenceStatus = N'ended', updatedAt = GETDATE()
            WHERE taskId = :task_id
                AND recurrenceStatus <> N'ended'
        """)
        connection.execute(query, {'task_id': task_id})

    def end_recurrence_group(self, connection, recurrence_group_id):
        query = text("""
            UPDATE JDT_DEMAND_MANAGEMENT_TASKS
            SET recurrenceStatus = N'ended', updatedAt = GETDATE()
            WHERE recurrenceGroupId = :recurrence_group_id
                AND recurrenceStatus <> N'ended'
        """)
        connection.execute(query, {
            'recurrence_group_id': recurrence_group_id
        })

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
