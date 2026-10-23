"""Persistência do painel moderno; conexão e transação pertencem ao caso de uso."""

from sqlalchemy import text

from .domain import ACTIVE_STATUSES, AREA_ID, AREA_NAME
from . import repository

SELECT = repository._SELECT.replace(
    "D.expected_benefits,", """D.expected_benefits, D.origin, D.responsible_id,
    D.deadline, D.started_at, D.completed_at, D.completed_on, D.scheduled_start_date,
    D.estimated_hours, D.daily_hours, D.completed_hours, D.difficulty, D.priority,
    D.observations, D.expected_return, D.portal_url,
    Responsible.name AS responsible_name,
    CASE WHEN D.responsible_id = :actor_id THEN 1 ELSE 0 END AS is_owner,
    CASE WHEN D.entry_kind = N'erro' THEN N'erro' ELSE D.classification END AS demand_type,
    (SELECT COUNT(*) FROM dbo.DJ_DEMAND_TASKS T WHERE T.demand_id = D.id) AS total_tasks,
    (SELECT COUNT(*) FROM dbo.DJ_DEMAND_TASKS T WHERE T.demand_id = D.id AND T.completed_at IS NOT NULL) AS completed_tasks,""",
) + " LEFT JOIN dbo.JDT_USER_DETAILS Responsible ON Responsible.id = D.responsible_id "

FIELDS = frozenset({
    "title", "description", "responsible_id", "urgency", "assumptions", "current_problems", "expected_benefits",
    "estimated_hours", "daily_hours", "completed_hours", "difficulty", "priority", "observations",
    "classification", "status", "deadline", "started_at", "completed_at", "completed_on",
    "scheduled_start_date", "expected_return", "portal_url",
})


def clock(connection):
    return connection.execute(text("SELECT CAST(GETDATE() AS DATE) AS today, SYSUTCDATETIME() AS now")).mappings().one()


def get(connection, demand_id, actor_id, lock=False):
    select = SELECT.replace("dbo.DJ_DEMANDS AS D", "dbo.DJ_DEMANDS AS D WITH (UPDLOCK, HOLDLOCK)") if lock else SELECT
    row = connection.execute(text(select + " WHERE D.id = :id AND D.area_id = :area"),
                             {"id": demand_id, "area": AREA_ID, "actor_id": actor_id}).mappings().one_or_none()
    return dict(row) if row is not None else None


def list_board(connection, actor_id, query, today):
    active = ",".join(f":active_{i}" for i in range(len(ACTIVE_STATUSES)))
    parameters = {f"active_{i}": status for i, status in enumerate(ACTIVE_STATUSES)}
    parameters.update(area=AREA_ID, actor_id=actor_id)
    where = f"D.area_id = :area AND D.responsible_id IS NOT NULL AND (D.status IN ({active})"
    if query.completed_from:
        where += " OR (D.status = N'concluido' AND D.completed_on BETWEEN :date_from AND :date_to)"
        parameters.update(date_from=query.completed_from, date_to=query.completed_to or today)
    where += ")"
    if query.responsible_id:
        where += " AND D.responsible_id = :responsible"
        parameters["responsible"] = query.responsible_id
    if query.demand_type != "todos":
        where += " AND (CASE WHEN D.entry_kind = N'erro' THEN N'erro' ELSE D.classification END) = :kind"
        parameters["kind"] = query.demand_type
    if query.difficulty:
        where += " AND D.difficulty = :difficulty"
        parameters["difficulty"] = query.difficulty
    if query.status:
        statuses = query.status.split(",")
        where += " AND D.status IN (" + ",".join(f":status_{i}" for i in range(len(statuses))) + ")"
        parameters.update({f"status_{i}": value for i, value in enumerate(statuses)})
    if query.search:
        where += " AND (D.title LIKE :search ESCAPE N'~' OR CONVERT(NVARCHAR(20), D.id) = :identifier)"
        literal = query.search.replace("~", "~~").replace("%", "~%").replace("_", "~_").replace("[", "~[")
        parameters.update(search=f"%{literal}%", identifier=query.search.lstrip("#"))
    priority = "CASE WHEN D.priority IS NULL THEN 1 ELSE 0 END, D.priority"
    deadline = "CASE WHEN D.deadline IS NULL THEN 1 ELSE 0 END, D.deadline"
    ordering = priority + ", " + deadline if query.sort == "priority" else deadline + ", " + priority
    rows = connection.execute(text(SELECT + " WHERE " + where + " ORDER BY Responsible.name, " + ordering + ", D.id DESC"), parameters).mappings().all()
    return [dict(row) for row in rows]


def reviews(connection, actor_id):
    rows = connection.execute(text(SELECT + """
        WHERE D.area_id = :area AND D.origin = N'solicitacao' AND D.responsible_id IS NULL
            AND D.status IN (N'em_analise', N'aguardando_informacoes')
        ORDER BY D.id DESC
    """), {"area": AREA_ID, "actor_id": actor_id}).mappings().all()
    return [dict(row) for row in rows]


def responsibles(connection):
    rows = connection.execute(text("""
        SELECT CONVERT(NVARCHAR(128), U.id) AS id, U.name FROM dbo.JDT_USER_DETAILS U
        WHERE U.active = 1 AND U.generic = 0 AND U.name IS NOT NULL AND (
            EXISTS (SELECT 1 FROM OPENJSON(CASE WHEN ISJSON(U.role) = 1 THEN U.role ELSE N'[]' END) R WHERE R.value = :role)
            OR EXISTS (SELECT 1 FROM dbo.DJ_DEMANDS D WHERE D.area_id = :area AND D.responsible_id = U.id)
        ) ORDER BY U.name, U.id
    """), {"role": AREA_NAME, "area": AREA_ID}).mappings().all()
    return [dict(row) for row in rows]


def update(connection, demand_id, values, version=None):
    if not values or set(values) - FIELDS:
        raise ValueError("Campos de gerenciamento inválidos.")
    assignments = ", ".join(f"{key} = :{key}" for key in values)
    where = "id = :id AND area_id = :area" + (" AND row_version = :version" if version is not None else "")
    return connection.execute(text(f"UPDATE dbo.DJ_DEMANDS SET {assignments}, updated_at = SYSUTCDATETIME() OUTPUT inserted.id WHERE {where}"),
                              {**values, "id": demand_id, "area": AREA_ID, "version": version}).scalar_one_or_none()


def create_internal(connection, data, actor_id, fingerprint):
    values = data.model_dump(exclude={"demand_type"})
    demand_id = connection.execute(text("""
        INSERT INTO dbo.DJ_DEMANDS (area_id, requester_id, contributor_id, entry_kind, classification, origin,
            status, title, description, urgency, assumptions, current_problems, expected_benefits,
            submission_key, submission_fingerprint)
        OUTPUT inserted.id VALUES (:area, :actor_id, :contributor_id, :entry_kind, :classification, N'interna',
            N'a_fazer', :title, :description, :urgency, :assumptions, :current_problems, :expected_benefits,
            :submission_key, :fingerprint)
    """), {**values, "area": AREA_ID, "actor_id": actor_id, "fingerprint": fingerprint,
           "entry_kind": "erro" if data.demand_type == "erro" else "demanda",
           "classification": None if data.demand_type == "erro" else data.demand_type}).scalar_one()
    update(connection, demand_id, {key: values[key] for key in (
        "responsible_id", "estimated_hours", "daily_hours", "completed_hours", "difficulty", "priority", "observations",
    )})
    return demand_id


def information(connection, demand_id):
    rows = connection.execute(text("""
        SELECT I.*, U.name AS requested_by_name, R.name AS replied_by_name
        FROM dbo.DJ_DEMAND_INFORMATION_REQUESTS I
        LEFT JOIN dbo.JDT_USER_DETAILS U ON U.id = I.requested_by
        LEFT JOIN dbo.JDT_USER_DETAILS R ON R.id = I.replied_by
        WHERE I.demand_id = :id ORDER BY I.id DESC
    """), {"id": demand_id}).mappings().all()
    return [dict(row) for row in rows]


def ask_information(connection, demand_id, actor_id, kind, question, previous_status):
    connection.execute(text("""
        INSERT INTO dbo.DJ_DEMAND_INFORMATION_REQUESTS(demand_id, kind, question, previous_status, requested_by)
        VALUES (:id, :kind, :question, :previous_status, :actor_id)
    """), {"id": demand_id, "kind": kind, "question": question, "previous_status": previous_status, "actor_id": actor_id})


def close_information(connection, demand_id, reply=None, actor_id=None):
    connection.execute(text("""
        UPDATE dbo.DJ_DEMAND_INFORMATION_REQUESTS SET reply = :reply, replied_by = :actor_id, closed_at = SYSUTCDATETIME()
        WHERE demand_id = :id AND closed_at IS NULL
    """), {"id": demand_id, "reply": reply, "actor_id": actor_id})


def tasks(connection, demand_id):
    rows = connection.execute(text("""
        SELECT T.*, U.name AS responsible_name FROM dbo.DJ_DEMAND_TASKS T
        LEFT JOIN dbo.JDT_USER_DETAILS U ON U.id = T.responsible_id
        WHERE T.demand_id = :id ORDER BY CASE WHEN T.completed_at IS NULL THEN 0 ELSE 1 END, T.priority, T.id
    """), {"id": demand_id}).mappings().all()
    return [{**row, "row_version": bytes(row["row_version"]).hex()} for row in rows]


def save_task(connection, demand_id, data, task_id=None):
    values = data.model_dump(exclude={"row_version", "task_version", "completed"})
    values.update(demand_id=demand_id, task_id=task_id, completed=1 if data.completed else 0,
                  version=bytes.fromhex(data.task_version) if task_id else None)
    if task_id is None:
        sql = """INSERT INTO dbo.DJ_DEMAND_TASKS(demand_id, description, responsible_id, priority, deadline, observations, completed_at)
            OUTPUT inserted.id VALUES (:demand_id, :description, :responsible_id, :priority, :deadline, :observations,
                CASE WHEN :completed = 1 THEN SYSUTCDATETIME() END)"""
    else:
        sql = """UPDATE dbo.DJ_DEMAND_TASKS SET description = :description, responsible_id = :responsible_id,
            priority = :priority, deadline = :deadline, observations = :observations,
            completed_at = CASE WHEN :completed = 1 THEN COALESCE(completed_at, SYSUTCDATETIME()) END
            OUTPUT inserted.id WHERE id = :task_id AND demand_id = :demand_id AND row_version = :version"""
    return connection.execute(text(sql), values).scalar_one_or_none()


def delete_task(connection, demand_id, task_id):
    return connection.execute(text("DELETE FROM dbo.DJ_DEMAND_TASKS OUTPUT deleted.id WHERE id = :task_id AND demand_id = :id"),
                              {"id": demand_id, "task_id": task_id}).scalar_one_or_none()


def hide_attachment(connection, demand_id, attachment_id):
    return connection.execute(text("""UPDATE dbo.DJ_DEMAND_ATTACHMENTS SET deleted_at = SYSUTCDATETIME()
        OUTPUT inserted.id WHERE demand_id = :id AND id = :attachment_id AND deleted_at IS NULL"""),
        {"id": demand_id, "attachment_id": attachment_id}).scalar_one_or_none()


def notices(connection):
    rows = connection.execute(text("""
        SELECT N.*, U.name AS created_by_name FROM dbo.DJ_DEMAND_NOTICES N
        LEFT JOIN dbo.JDT_USER_DETAILS U ON U.id = N.created_by
        WHERE N.area_id = :area AND N.finalized_at IS NULL
            AND (N.hide_after_end = 0 OR N.ends_at > GETDATE()) ORDER BY N.id DESC
    """), {"area": AREA_ID}).mappings().all()
    return [dict(row) for row in rows]


def notice_submission(connection, actor_id, key):
    return connection.execute(text("""SELECT id, submission_fingerprint FROM dbo.DJ_DEMAND_NOTICES WITH (UPDLOCK, HOLDLOCK)
        WHERE area_id = :area AND created_by = :actor_id AND submission_key = :key"""),
        {"area": AREA_ID, "actor_id": actor_id, "key": key}).mappings().one_or_none()


def create_notice(connection, data, actor_id, fingerprint):
    return connection.execute(text("""INSERT INTO dbo.DJ_DEMAND_NOTICES
        (area_id, title, description, starts_at, ends_at, hide_after_end, created_by, submission_key, submission_fingerprint)
        OUTPUT inserted.id VALUES (:area, :title, :description, :starts_at, :ends_at, :hide_after_end, :actor_id, :submission_key, :fingerprint)"""),
        {**data.model_dump(), "area": AREA_ID, "actor_id": actor_id, "fingerprint": fingerprint}).scalar_one()


def edit_notice(connection, notice_id, data, actor_id, override, finalize=False):
    assignments = "finalized_at = SYSUTCDATETIME()" if finalize else "title = :title, description = :description, starts_at = :starts_at, ends_at = :ends_at, hide_after_end = :hide_after_end"
    return connection.execute(text(f"""UPDATE dbo.DJ_DEMAND_NOTICES SET {assignments} OUTPUT inserted.id
        WHERE id = :id AND area_id = :area AND finalized_at IS NULL AND row_version = :version
        AND (created_by = :actor_id OR :override = 1)"""),
        {**data.model_dump(), "id": notice_id, "area": AREA_ID, "version": bytes.fromhex(data.row_version),
         "actor_id": actor_id, "override": 1 if override else 0}).scalar_one_or_none()
