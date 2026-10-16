from sqlalchemy import bindparam, text


# Um único CASE atende listagem, detalhes e retorno das gravações.
_EVENT_SELECT = """
    SELECT events.id, events.name, events.description, events.starts_at, events.ends_at,
        events.event_type_id, types.name AS event_type_name, events.instructor, events.syllabus,
        CASE
            WHEN starts_at IS NULL OR ends_at IS NULL THEN 'unscheduled'
            WHEN ends_at <= :now THEN 'completed'
            WHEN starts_at <= :now THEN 'ongoing'
            ELSE 'upcoming'
        END AS status
    FROM dbo.DJ_EVENTS AS events
    LEFT JOIN dbo.DJ_EVENT_TYPES AS types ON types.id = events.event_type_id
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
        SELECT id, name, description, starts_at, ends_at, status,
            event_type_id, event_type_name, instructor, syllabus
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
        text(_EVENT_SELECT + " WHERE events.id = :event_id"),
        {"event_id": event_id, "now": now},
    ).mappings().one_or_none()
    return dict(row) if row is not None else None


def create_event(connection, *, name, description, event_type_id, instructor, syllabus,
                 starts_at, ends_at, created_by, now):
    event_id = connection.execute(
        text("""
            INSERT INTO dbo.DJ_EVENTS
                (name, description, event_type_id, instructor, syllabus, starts_at, ends_at, created_by)
            OUTPUT inserted.id
            VALUES (:name, :description, :event_type_id, :instructor, :syllabus, :starts_at, :ends_at, :created_by)
        """),
        {
            "name": name,
            "description": description,
            "event_type_id": event_type_id,
            "instructor": instructor,
            "syllabus": syllabus,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "created_by": created_by,
        },
    ).scalar_one()
    return get_event(connection, event_id, now=now)


def update_event(connection, event_id, *, name, description, event_type_id, instructor, syllabus,
                 starts_at, ends_at, now):
    updated_id = connection.execute(
        text("""
            UPDATE dbo.DJ_EVENTS
            SET name = :name, description = :description,
                event_type_id = :event_type_id, instructor = :instructor, syllabus = :syllabus,
                starts_at = :starts_at, ends_at = :ends_at
            OUTPUT inserted.id
            WHERE id = :event_id
        """),
        {
            "event_id": event_id,
            "name": name,
            "description": description,
            "event_type_id": event_type_id,
            "instructor": instructor,
            "syllabus": syllabus,
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


def list_event_types(connection):
    rows = connection.execute(
        text("SELECT id, name FROM dbo.DJ_EVENT_TYPES ORDER BY name, id"),
    ).mappings().all()
    return [dict(row) for row in rows]


def event_type_exists(connection, event_type_id):
    return connection.execute(
        text("SELECT id FROM dbo.DJ_EVENT_TYPES WITH (HOLDLOCK) WHERE id = :event_type_id"),
        {"event_type_id": event_type_id},
    ).scalar_one_or_none() is not None


def create_event_type(connection, *, name, created_by):
    # A chave única e a trava de intervalo serializam cadastros do mesmo nome.
    existing = connection.execute(
        text("SELECT id, name FROM dbo.DJ_EVENT_TYPES WITH (UPDLOCK, HOLDLOCK) WHERE name = :name"),
        {"name": name},
    ).mappings().one_or_none()
    if existing is not None:
        return dict(existing)
    row = connection.execute(
        text("""
            INSERT INTO dbo.DJ_EVENT_TYPES (name, created_by)
            OUTPUT inserted.id, inserted.name
            VALUES (:name, :created_by)
        """), {"name": name, "created_by": created_by},
    ).mappings().one()
    return dict(row)


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


def update_attendance_list(connection, event_id, list_id, *, name):
    updated_id = connection.execute(
        text("""
            UPDATE dbo.DJ_EVENT_ATTENDANCE_LISTS
            SET name = :name
            OUTPUT inserted.id
            WHERE id = :list_id AND event_id = :event_id
        """), {"event_id": event_id, "list_id": list_id, "name": name},
    ).scalar_one_or_none()
    return get_attendance_list(connection, event_id, list_id) if updated_id is not None else None


def delete_attendance_list(connection, event_id, list_id):
    # A FK existente remove somente as presenças desta lista por ON DELETE CASCADE.
    return connection.execute(
        text("""
            DELETE FROM dbo.DJ_EVENT_ATTENDANCE_LISTS
            OUTPUT deleted.id
            WHERE id = :list_id AND event_id = :event_id
        """), {"event_id": event_id, "list_id": list_id},
    ).scalar_one_or_none()


def delete_attendance_entry(connection, list_id, entry_id):
    return connection.execute(
        text("""
            DELETE FROM dbo.DJ_EVENT_ATTENDANCE_ENTRIES
            OUTPUT deleted.id
            WHERE id = :entry_id AND list_id = :list_id
        """), {"list_id": list_id, "entry_id": entry_id},
    ).scalar_one_or_none()


def list_attendance_entries(connection, list_id, *, page, per_page):
    total = connection.execute(
        text("SELECT COUNT(*) FROM dbo.DJ_EVENT_ATTENDANCE_ENTRIES WHERE list_id = :list_id"),
        {"list_id": list_id},
    ).scalar_one()
    rows = connection.execute(
        text("""
            SELECT id, registration, name, department, company
            FROM dbo.DJ_EVENT_ATTENDANCE_ENTRIES
            WHERE list_id = :list_id
            ORDER BY id DESC
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
        """),
        {"list_id": list_id, "offset": (page - 1) * per_page, "limit": per_page},
    ).mappings().all()
    return [dict(row) for row in rows], total


def get_attendance_entry(connection, list_id, registration):
    row = connection.execute(
        text("""
            SELECT TOP (1) id, registration, name, department, company
            FROM dbo.DJ_EVENT_ATTENDANCE_ENTRIES
            WHERE list_id = :list_id AND RIGHT(registration, 8) = :employee_registration
            ORDER BY id
        """), {"list_id": list_id, "employee_registration": registration[4:]},
    ).mappings().one_or_none()
    return dict(row) if row is not None else None


def register_attendance(connection, list_id, *, registration, created_by, name, department, company):
    # O serviço já travou a lista. A matrícula é única no grupo, independentemente do prefixo.
    parameters = {
        "list_id": list_id, "registration": registration,
        "name": name, "department": department, "company": company,
    }
    existing = get_attendance_entry(connection, list_id, registration)
    if existing is not None:
        if any(parameters[field] and not existing[field] for field in ("name", "department", "company")):
            existing = dict(connection.execute(
                text("""
                    UPDATE dbo.DJ_EVENT_ATTENDANCE_ENTRIES
                    SET name = COALESCE(NULLIF(name, ''), :name),
                        department = COALESCE(NULLIF(department, ''), :department),
                        company = COALESCE(NULLIF(company, ''), :company)
                    OUTPUT inserted.id, inserted.registration, inserted.name, inserted.department, inserted.company
                    WHERE id = :entry_id AND list_id = :list_id
                """), {**parameters, "entry_id": existing["id"]},
            ).mappings().one())
        return {"item": existing, "created": False}
    row = connection.execute(
        text("""
            INSERT INTO dbo.DJ_EVENT_ATTENDANCE_ENTRIES (list_id, registration, name, department, company, created_by)
            OUTPUT inserted.id, inserted.registration, inserted.name, inserted.department, inserted.company
            VALUES (:list_id, :registration, :name, :department, :company, :created_by)
        """), {**parameters, "created_by": created_by},
    ).mappings().one()
    return {"item": dict(row), "created": True}
