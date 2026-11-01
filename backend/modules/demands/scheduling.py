"""Início automático moderno: recebe sessões explicitamente, sem contexto Flask."""

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from .models import WorkHistory, WorkItem


def start_scheduled_work(sessions, *, now=None, limit=100):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("O instante do início automático deve informar o fuso horário.")
    today = now.astimezone(ZoneInfo("America/Sao_Paulo")).date()
    count = 0
    with sessions.begin() as session:
        rows = session.scalars(select(WorkItem).where(WorkItem.area_id == 1, WorkItem.kind != "aviso",
            WorkItem.status == "agendado", WorkItem.started_on.is_(None),
            WorkItem.scheduled_start_on <= today, WorkItem.due_on.is_not(None))
            .with_hint(WorkItem, "WITH (UPDLOCK, READPAST, ROWLOCK)", "mssql")
            .order_by(WorkItem.scheduled_start_on, WorkItem.id).limit(limit)).all()
        for work in rows:
            planned = work.scheduled_start_on
            changes = {"status": {"before": work.status, "after": "em_andamento"},
                "scheduled_start_on": {"before": planned, "after": None},
                "started_on": {"before": None, "after": planned},
                "message": "Início automático conforme o agendamento."}
            work.status = "em_andamento"
            work.started_on = planned
            work.scheduled_start_on = None
            work.expected_return_on = None
            work.updated_at = now.astimezone(timezone.utc).replace(tzinfo=None)
            session.add(WorkHistory(work_id=work.id, actor_id="system:scheduled-start", event_type="auto_started",
                changes=json.dumps(changes, ensure_ascii=False, default=str)))
            count += 1
    return count
