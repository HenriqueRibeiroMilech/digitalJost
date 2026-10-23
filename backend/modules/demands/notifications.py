"""E-mail após commit; falhas de transporte não desfazem o fluxo da demanda."""

from html import escape
from sqlalchemy import text


def queue(connection, demand_id, history_id, target_id, message, portal_url):
    return connection.execute(text("""
        INSERT INTO dbo.DJ_DEMAND_NOTIFICATIONS(demand_id, history_id, target_id, message, portal_url)
        OUTPUT inserted.id VALUES (:demand_id, :history_id, :target_id, :message, :portal_url)
    """), dict(demand_id=demand_id, history_id=history_id, target_id=target_id,
               message=message, portal_url=portal_url)).scalar_one()


def deliver(engine, notification_id, sender):
    with engine.begin() as connection:
        claimed = connection.execute(text("""
            UPDATE dbo.DJ_DEMAND_NOTIFICATIONS WITH (UPDLOCK, READPAST, ROWLOCK)
            SET state = N'sending', attempts = attempts + 1, claimed_at = SYSUTCDATETIME()
            OUTPUT inserted.id WHERE id = :id AND state IN (N'pending', N'failed') AND attempts < 5
                AND (claimed_at IS NULL OR claimed_at < DATEADD(MINUTE, -5, SYSUTCDATETIME()))
        """), {"id": notification_id}).scalar_one_or_none()
        if claimed is None:
            return False
        row = connection.execute(text("""
            SELECT N.*, D.title, U.companyEmail AS recipient_email, C.companyEmail AS contributor_email,
                R.companyEmail AS responsible_email
            FROM dbo.DJ_DEMAND_NOTIFICATIONS N JOIN dbo.DJ_DEMANDS D ON D.id = N.demand_id
            LEFT JOIN dbo.JDT_USER_DETAILS U ON U.id = N.target_id AND U.active = 1 AND U.generic = 0
            LEFT JOIN dbo.JDT_USER_DETAILS C ON C.id = D.contributor_id AND C.active = 1 AND C.generic = 0
            LEFT JOIN dbo.JDT_USER_DETAILS R ON R.id = D.responsible_id AND R.active = 1 AND R.generic = 0
            WHERE N.id = :id
        """), {"id": notification_id}).mappings().one()
    target = (row["recipient_email"] or "").strip()
    cc = list(dict.fromkeys(value.strip() for value in (row["contributor_email"], row["responsible_email"])
                           if value and value.strip() and value.strip() != target))
    body = (
        '<div style="font-family:Arial,sans-serif;max-width:720px">'
        '<h2 style="color:#005596">Digital JOST · Demandas</h2>'
        f'<h3>Solicitação #{row["demand_id"]}: {escape(row["title"])}</h3>'
        f'<p style="white-space:pre-wrap">{escape(row["message"])}</p>'
        f'<p><a href="{escape(row["portal_url"], quote=True)}">Abrir no Digital JOST</a></p></div>'
    )
    try:
        success = bool(target and sender(subject=f"Atualização da solicitação #{row['demand_id']}",
                                        body=body, to=[target], cc=cc))
    except Exception:
        success = False
    with engine.begin() as connection:
        connection.execute(text("""
            UPDATE dbo.DJ_DEMAND_NOTIFICATIONS SET state = :state,
                sent_at = CASE WHEN :state = N'sent' THEN SYSUTCDATETIME() END
            WHERE id = :id AND state = N'sending'
        """), {"id": notification_id, "state": "sent" if success else "failed"})
    return success


def flush(engine, sender):
    with engine.connect() as connection:
        ids = connection.execute(text("""SELECT TOP (25) id FROM dbo.DJ_DEMAND_NOTIFICATIONS
            WHERE state IN (N'pending', N'failed') AND attempts < 5
                AND (claimed_at IS NULL OR claimed_at < DATEADD(MINUTE, -5, SYSUTCDATETIME())) ORDER BY id""")).scalars().all()
    return sum(deliver(engine, item, sender) for item in ids)
