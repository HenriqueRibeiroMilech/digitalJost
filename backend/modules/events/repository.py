from sqlalchemy import bindparam, text


# Um único CASE atende listagem, detalhes e retorno das gravações.
_EVENT_SELECT = """
    SELECT id, name, description, starts_at, ends_at,
        CASE
            WHEN starts_at IS NULL OR ends_at IS NULL THEN 'unscheduled'
            WHEN ends_at <= :now THEN 'completed'
            WHEN starts_at <= :now THEN 'ongoing'
            ELSE 'upcoming'
        END AS status
    FROM dbo.DJ_EVENTS
"""
_LIST_FILTER = "WHERE status IN :statuses AND name LIKE :search ESCAPE '~'"


def current_time(connection):
    # As datas dos eventos são locais, sem fuso; use a mesma referência do TD.
    return connection.execute(text("SELECT SYSDATETIME()")).scalar_one()


def list_events(connection, *, page, per_page, search, statuses, now):
    # LIKE literal: %, _ e [ digitados pelo usuário não viram curingas.
    escaped_search = (
        search.replace("~", "~~")
        .replace("%", "~%")
        .replace("_", "~_")
        .replace("[", "~[")
    )
    parameters = {"now": now, "statuses": statuses, "search": f"%{escaped_search}%"}
    # Somente fragmentos SQL constantes entram na composição. Valores são parâmetros.
    count_query = text(f"""
        WITH event_state AS ({_EVENT_SELECT})
        SELECT COUNT(*) FROM event_state {_LIST_FILTER}
    """).bindparams(bindparam("statuses", expanding=True))
    total = connection.execute(
        count_query, parameters,
    ).scalar_one()
    items_query = text(f"""
        WITH event_state AS ({_EVENT_SELECT})
        SELECT id, name, description, starts_at, ends_at, status
        FROM event_state {_LIST_FILTER}
        ORDER BY id DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """).bindparams(bindparam("statuses", expanding=True))
    rows = connection.execute(
        items_query,
        {**parameters, "offset": (page - 1) * per_page, "limit": per_page},
    ).mappings().all()
    return [dict(row) for row in rows], total


def get_event(connection, event_id, *, now):
    row = connection.execute(
        text(_EVENT_SELECT + " WHERE id = :event_id"),
        {"event_id": event_id, "now": now},
    ).mappings().one_or_none()
    return dict(row) if row is not None else None


def create_event(connection, *, name, description, starts_at, ends_at, created_by, now):
    event_id = connection.execute(
        text("""
            INSERT INTO dbo.DJ_EVENTS (name, description, starts_at, ends_at, created_by)
            OUTPUT inserted.id
            VALUES (:name, :description, :starts_at, :ends_at, :created_by)
        """),
        {
            "name": name,
            "description": description,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "created_by": created_by,
        },
    ).scalar_one()
    return get_event(connection, event_id, now=now)


def update_event(connection, event_id, *, name, description, starts_at, ends_at, now):
    updated_id = connection.execute(
        text("""
            UPDATE dbo.DJ_EVENTS
            SET name = :name, description = :description,
                starts_at = :starts_at, ends_at = :ends_at
            OUTPUT inserted.id
            WHERE id = :event_id
        """),
        {
            "event_id": event_id,
            "name": name,
            "description": description,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
    ).scalar_one_or_none()
    return get_event(connection, updated_id, now=now) if updated_id is not None else None


def delete_event(connection, event_id):
    return connection.execute(
        text("""
            DELETE FROM dbo.DJ_EVENTS
            OUTPUT deleted.id
            WHERE id = :event_id
        """),
        {"event_id": event_id},
    ).scalar_one_or_none()


def event_exists(connection, event_id, *, lock=False):
    # A trava mantém o evento existente durante a criação de uma lista.
    locking = " WITH (HOLDLOCK)" if lock else ""
    return connection.execute(
        text(f"SELECT id FROM dbo.DJ_EVENTS{locking} WHERE id = :event_id"),
        {"event_id": event_id},
    ).scalar_one_or_none() is not None


def list_attendance_lists(connection, event_id, *, page, per_page):
    total = connection.execute(
        text("SELECT COUNT(*) FROM dbo.DJ_EVENT_ATTENDANCE_LISTS WHERE event_id = :event_id"),
        {"event_id": event_id},
    ).scalar_one()
    rows = connection.execute(
        text("""
            SELECT lists.id, lists.event_id, lists.name,
                (SELECT COUNT(*) FROM dbo.DJ_EVENT_ATTENDANCE_ENTRIES AS entries
                 WHERE entries.list_id = lists.id) AS total
            FROM dbo.DJ_EVENT_ATTENDANCE_LISTS AS lists
            WHERE lists.event_id = :event_id
            ORDER BY lists.id DESC
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
        """),
        {"event_id": event_id, "offset": (page - 1) * per_page, "limit": per_page},
    ).mappings().all()
    return [dict(row) for row in rows], total


def get_attendance_list(connection, event_id, list_id, *, lock=False):
    # Serializa registros na mesma lista e impede sua remoção durante a escrita.
    locking = " WITH (UPDLOCK, HOLDLOCK)" if lock else ""
    row = connection.execute(
        text(f"""
            SELECT lists.id, lists.event_id, lists.name,
                (SELECT COUNT(*) FROM dbo.DJ_EVENT_ATTENDANCE_ENTRIES AS entries
                 WHERE entries.list_id = lists.id) AS total
            FROM dbo.DJ_EVENT_ATTENDANCE_LISTS AS lists{locking}
            WHERE lists.id = :list_id AND lists.event_id = :event_id
        """),
        {"event_id": event_id, "list_id": list_id},
    ).mappings().one_or_none()
    return dict(row) if row is not None else None


def create_attendance_list(connection, event_id, *, name, created_by):
    row = connection.execute(
        text("""
            INSERT INTO dbo.DJ_EVENT_ATTENDANCE_LISTS (event_id, name, created_by)
            OUTPUT inserted.id, inserted.event_id, inserted.name
            VALUES (:event_id, :name, :created_by)
        """),
        {"event_id": event_id, "name": name, "created_by": created_by},
    ).mappings().one()
    return {**row, "total": 0}


def list_attendance_entries(connection, list_id, *, page, per_page):
    total = connection.execute(
        text("SELECT COUNT(*) FROM dbo.DJ_EVENT_ATTENDANCE_ENTRIES WHERE list_id = :list_id"),
        {"list_id": list_id},
    ).scalar_one()
    rows = connection.execute(
        text("""
            SELECT id, registration, name, department
            FROM dbo.DJ_EVENT_ATTENDANCE_ENTRIES
            WHERE list_id = :list_id
            ORDER BY id DESC
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
        """),
        {"list_id": list_id, "offset": (page - 1) * per_page, "limit": per_page},
    ).mappings().all()
    return [dict(row) for row in rows], total


def register_attendance(connection, list_id, *, registration, created_by):
    # O serviço já travou a lista na transação; a constraint UNIQUE é a última defesa.
    parameters = {"list_id": list_id, "registration": registration}
    existing = connection.execute(
        text("""
            SELECT id, registration, name, department
            FROM dbo.DJ_EVENT_ATTENDANCE_ENTRIES
            WHERE list_id = :list_id AND registration = :registration
        """), parameters,
    ).mappings().one_or_none()
    if existing is not None:
        return {"item": dict(existing), "created": False}
    row = connection.execute(
        text("""
            INSERT INTO dbo.DJ_EVENT_ATTENDANCE_ENTRIES (list_id, registration, created_by)
            OUTPUT inserted.id, inserted.registration, inserted.name, inserted.department
            VALUES (:list_id, :registration, :created_by)
        """), {**parameters, "created_by": created_by},
    ).mappings().one()
    return {"item": dict(row), "created": True}
