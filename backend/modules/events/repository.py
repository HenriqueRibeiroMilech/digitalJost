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
