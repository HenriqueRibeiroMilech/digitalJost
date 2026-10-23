"""Rotina explícita do Auto para as tabelas novas; nenhum trabalho durante import."""


def default(logger):
    from sqlalchemy import text
    from app.utils.db_utils import get_engine
    from backend.compatibility.demand_notifications import send_notification
    from backend.modules.demands import management_repository as store, repository, notifications

    engine = get_engine("jdt")
    with engine.begin() as connection:
        if connection.execute(text("SELECT OBJECT_ID(N'dbo.DJ_DEMAND_NOTIFICATIONS', N'U')")).scalar() is None:
            return
        now = store.clock(connection)
        rows = connection.execute(text("""SELECT TOP (100) id, responsible_id FROM dbo.DJ_DEMANDS WITH (UPDLOCK, READPAST, ROWLOCK)
            WHERE area_id = :area AND status = N'a_fazer' AND scheduled_start_date <= :today ORDER BY id"""),
            {"area": 1, "today": now["today"]}).mappings().all()
        for row in rows:
            store.update(connection, row["id"], {"status": "em_andamento", "started_at": now["now"], "scheduled_start_date": None})
            repository.add_history(connection, row["id"], "system:demands-auto", "scheduled_start", None)
    sent = notifications.flush(engine, send_notification)
    logger.info("Demandas modernas: %s início(s) automático(s), %s notificação(ões) enviada(s).", len(rows), sent)
