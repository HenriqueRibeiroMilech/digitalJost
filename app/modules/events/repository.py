from sqlalchemy import text


def list_events(connection, *, page, per_page):
    total = connection.execute(
        text("SELECT COUNT(*) FROM dbo.DJ_EVENTS")
    ).scalar_one()
    rows = connection.execute(
        text("""
            SELECT id, name, description
            FROM dbo.DJ_EVENTS
            ORDER BY id DESC
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
        """),
        {"offset": (page - 1) * per_page, "limit": per_page},
    ).mappings().all()
    return [dict(row) for row in rows], total


def create_event(connection, *, name, description, created_by):
    row = connection.execute(
        text("""
            INSERT INTO dbo.DJ_EVENTS (name, description, created_by)
            OUTPUT inserted.id, inserted.name, inserted.description
            VALUES (:name, :description, :created_by)
        """),
        {
            "name": name,
            "description": description,
            "created_by": created_by,
        },
    ).mappings().one()
    return dict(row)