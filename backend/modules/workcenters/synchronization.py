"""Publicação transacional do catálogo ativo, sem inicializar Flask ou o legado."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .integration import WorkcenterSyncError, fetch_active_workcenters
from .models import Workcenter


_EXCLUDED_WORKCENTER_CODES = frozenset({
    "LABORAT", "AUT_01", "MACH2_BACKUP", "MACH2_BACKUP2", "SUBCON",
})


def synchronize_workcenters(sessions, *, username, password):
    # A chamada externa termina antes de abrir a transação de publicação no TD.
    catalog = fetch_active_workcenters(username=username, password=password)
    # Validar a resposta completa antes de aplicar as exclusões do catálogo local.
    catalog = [
        item for item in catalog
        if item.workcenter_code.upper() not in _EXCLUDED_WORKCENTER_CODES
    ]
    if not catalog:
        raise WorkcenterSyncError("O catálogo ficou vazio após as exclusões; catálogo anterior preservado.")
    synced_at = datetime.now(timezone.utc).replace(tzinfo=None)
    incoming_keys = {item.plex_workcenter_key for item in catalog}
    try:
        with sessions.begin() as session:
            # Catálogo pequeno, escrito somente pelo job. Serializa a publicação
            # inclusive quando houver mais de um processo do serviço por engano.
            existing = {item.plex_workcenter_key: item for item in session.scalars(
                select(Workcenter).with_hint(Workcenter, "WITH (TABLOCKX, HOLDLOCK)", "mssql")
            )}
            for key, item in existing.items():
                if key not in incoming_keys:
                    session.delete(item)
            session.flush()
            for item in catalog:
                stored = existing.get(item.plex_workcenter_key)
                if stored is None:
                    stored = Workcenter(plex_workcenter_key=item.plex_workcenter_key)
                    session.add(stored)
                stored.workcenter_code = item.workcenter_code
                stored.name = item.name
                stored.workcenter_group = item.workcenter_group
                stored.last_synced_at = synced_at
        return len(catalog)
    except SQLAlchemyError:
        raise WorkcenterSyncError("A publicação de DJ_WORKCENTERS falhou; a transação foi revertida.") from None
