"""SQL parametrizado das tabelas modernas; nenhuma escrita nas tabelas legadas."""

import json

from sqlalchemy import text


_VISIBLE = """
    D.area_id = :area_id
    AND (D.requester_id = :actor_id OR D.contributor_id = :actor_id)
"""
_SELECT = """
    SELECT D.id, D.entry_kind, D.classification, D.title, D.description, D.urgency, D.status,
        D.requester_id, D.contributor_id, D.assumptions, D.current_problems,
        D.expected_benefits, D.created_at, D.updated_at, D.row_version,
        Requester.name AS requester_name, Contributor.name AS contributor_name,
        CASE WHEN D.requester_id = :actor_id THEN 'requester' ELSE 'contributor' END AS relationship
    FROM dbo.DJ_DEMANDS AS D
    LEFT JOIN dbo.JDT_USER_DETAILS AS Requester ON Requester.id = D.requester_id
    LEFT JOIN dbo.JDT_USER_DETAILS AS Contributor ON Contributor.id = D.contributor_id
"""


def list_requests(connection, area_id, actor_id, query):
    parameters = {"area_id": area_id, "actor_id": actor_id}
    where = _VISIBLE
    if query.entry_kind != "todos":
        where += " AND D.entry_kind = :entry_kind"
        parameters["entry_kind"] = query.entry_kind
    if query.search:
        where += " AND (D.title LIKE :search ESCAPE N'~' OR CONVERT(NVARCHAR(20), D.id) = :identifier)"
        literal = query.search.replace("~", "~~").replace("%", "~%").replace("_", "~_").replace("[", "~[")
        parameters.update(search=f"%{literal}%", identifier=query.search.lstrip("#"))
    total = connection.execute(text("SELECT COUNT(*) FROM dbo.DJ_DEMANDS AS D WHERE " + where), parameters).scalar_one()
    rows = connection.execute(text(_SELECT + " WHERE " + where + """
        ORDER BY D.id DESC OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """), {**parameters, "offset": (query.page - 1) * query.per_page, "limit": query.per_page}).mappings().all()
    return [dict(row) for row in rows], total


def get_request(connection, demand_id, area_id, actor_id, *, lock=False):
    select = _SELECT.replace("dbo.DJ_DEMANDS AS D", "dbo.DJ_DEMANDS AS D WITH (UPDLOCK, HOLDLOCK)") if lock else _SELECT
    row = connection.execute(text(select + " WHERE D.id = :demand_id AND " + _VISIBLE), {
        "demand_id": demand_id, "area_id": area_id, "actor_id": actor_id,
    }).mappings().one_or_none()
    return dict(row) if row is not None else None


def get_submission(connection, area_id, actor_id, submission_key):
    return connection.execute(text("""
        SELECT id, submission_fingerprint FROM dbo.DJ_DEMANDS WITH (UPDLOCK, HOLDLOCK)
        WHERE area_id = :area_id AND requester_id = :actor_id AND submission_key = :submission_key
    """), {"area_id": area_id, "actor_id": actor_id, "submission_key": submission_key}).mappings().one_or_none()


def create_request(connection, area_id, actor_id, data, fingerprint):
    return connection.execute(text("""
        INSERT INTO dbo.DJ_DEMANDS (
            area_id, requester_id, contributor_id, entry_kind, title, description,
            urgency, assumptions, current_problems, expected_benefits,
            submission_key, submission_fingerprint
        ) OUTPUT inserted.id VALUES (
            :area_id, :actor_id, :contributor_id, :entry_kind, :title, :description,
            :urgency, :assumptions, :current_problems, :expected_benefits,
            :submission_key, :fingerprint
        )
    """), {**data.model_dump(), "area_id": area_id, "actor_id": actor_id, "fingerprint": fingerprint}).scalar_one()


def update_request(connection, demand_id, area_id, actor_id, data):
    return connection.execute(text("""
        UPDATE dbo.DJ_DEMANDS SET contributor_id = :contributor_id, entry_kind = :entry_kind,
            title = :title, description = :description, urgency = :urgency,
            assumptions = :assumptions, current_problems = :current_problems,
            expected_benefits = :expected_benefits, updated_at = SYSUTCDATETIME()
        OUTPUT inserted.id
        WHERE id = :demand_id AND area_id = :area_id AND requester_id = :actor_id
            AND status = N'em_analise' AND row_version = :expected_version AND classification IS NULL
    """), {**data.model_dump(), "demand_id": demand_id, "area_id": area_id,
           "actor_id": actor_id, "expected_version": bytes.fromhex(data.row_version)}).scalar_one_or_none()


def list_contributors(connection, actor_id):
    rows = connection.execute(text("""
        SELECT CONVERT(NVARCHAR(128), id) AS id, name FROM dbo.JDT_USER_DETAILS
        WHERE active = 1 AND generic = 0 AND id <> :actor_id
            AND name IS NOT NULL AND NULLIF(LTRIM(RTRIM(companyEmail)), '') IS NOT NULL
        ORDER BY name, id
    """), {"actor_id": actor_id}).mappings().all()
    return [dict(row) for row in rows]


def contributor_exists(connection, contributor_id, actor_id):
    return connection.execute(text("""
        SELECT id FROM dbo.JDT_USER_DETAILS WHERE id = :contributor_id AND id <> :actor_id AND active = 1
            AND generic = 0 AND name IS NOT NULL AND NULLIF(LTRIM(RTRIM(companyEmail)), '') IS NOT NULL
    """), {"contributor_id": contributor_id, "actor_id": actor_id}).scalar_one_or_none() is not None


def add_attachment(connection, demand_id, actor_id, item):
    connection.execute(text("""
        INSERT INTO dbo.DJ_DEMAND_ATTACHMENTS
            (demand_id, original_name, storage_key, size_bytes, sha256, created_by)
        VALUES (:demand_id, :original_name, :storage_key, :size_bytes, :sha256, :actor_id)
    """), {**item, "demand_id": demand_id, "actor_id": actor_id})


def list_attachments(connection, demand_id):
    rows = connection.execute(text("""
        SELECT id, original_name, size_bytes FROM dbo.DJ_DEMAND_ATTACHMENTS
        WHERE demand_id = :demand_id ORDER BY id
    """), {"demand_id": demand_id}).mappings().all()
    return [dict(row) for row in rows]


def get_attachment(connection, demand_id, attachment_id):
    return connection.execute(text("""
        SELECT original_name, storage_key FROM dbo.DJ_DEMAND_ATTACHMENTS
        WHERE demand_id = :demand_id AND id = :attachment_id
    """), {"demand_id": demand_id, "attachment_id": attachment_id}).mappings().one_or_none()


def add_history(connection, demand_id, actor_id, event_type, changes=None):
    connection.execute(text("""
        INSERT INTO dbo.DJ_DEMAND_HISTORY (demand_id, event_type, actor_id, changes)
        VALUES (:demand_id, :event_type, :actor_id, :changes)
    """), {"demand_id": demand_id, "actor_id": actor_id, "event_type": event_type,
           "changes": json.dumps(changes, ensure_ascii=False) if changes else None})


def list_history(connection, demand_id):
    rows = connection.execute(text("""
        SELECT H.id, H.event_type, U.name AS actor_name, H.created_at
        FROM dbo.DJ_DEMAND_HISTORY AS H
        LEFT JOIN dbo.JDT_USER_DETAILS AS U ON U.id = H.actor_id
        WHERE H.demand_id = :demand_id ORDER BY H.id DESC
    """), {"demand_id": demand_id}).mappings().all()
    return [dict(row) for row in rows]
