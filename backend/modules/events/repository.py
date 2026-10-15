from sqlalchemy import text


def list_events(connection, *, page, per_page):
    total = connection.execute(
        text("SELECT COUNT(*) FROM dbo.DJ_EVENTS")
    ).scalar_one()
    rows = connection.execute(
        text("""
            SELECT id, name, description, starts_at, ends_at
            FROM dbo.DJ_EVENTS
            ORDER BY id DESC
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
        """),
        {"offset": (page - 1) * per_page, "limit": per_page},
    ).mappings().all()
    return [dict(row) for row in rows], total


def get_event(connection, event_id):
    row = connection.execute(
        text("""
            SELECT id, name, description, starts_at, ends_at
            FROM dbo.DJ_EVENTS
            WHERE id = :event_id
        """),
        {"event_id": event_id},
    ).mappings().one_or_none()
    return dict(row) if row is not None else None


def create_event(connection, *, name, description, starts_at, ends_at, created_by):
    row = connection.execute(
        text("""
            INSERT INTO dbo.DJ_EVENTS (name, description, starts_at, ends_at, created_by)
            OUTPUT inserted.id, inserted.name, inserted.description,
                   inserted.starts_at, inserted.ends_at
            VALUES (:name, :description, :starts_at, :ends_at, :created_by)
        """),
        {
            "name": name,
            "description": description,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "created_by": created_by,
        },
    ).mappings().one()
    return dict(row)


def update_event(connection, event_id, *, name, description, starts_at, ends_at):
    row = connection.execute(
        text("""
            UPDATE dbo.DJ_EVENTS
            SET name = :name, description = :description,
                starts_at = :starts_at, ends_at = :ends_at
            OUTPUT inserted.id, inserted.name, inserted.description,
                   inserted.starts_at, inserted.ends_at
            WHERE id = :event_id
        """),
        {
            "event_id": event_id,
            "name": name,
            "description": description,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
    ).mappings().one_or_none()
    return dict(row) if row is not None else None


def delete_event(connection, event_id):
    return connection.execute(
        text("""
            DELETE FROM dbo.DJ_EVENTS
            OUTPUT deleted.id
            WHERE id = :event_id
        """),
        {"event_id": event_id},
    ).scalar_one_or_none()
