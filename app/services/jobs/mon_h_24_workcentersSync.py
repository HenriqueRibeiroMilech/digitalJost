"""Adaptador semanal do H24 para o catálogo da arquitetura moderna."""

import atexit
import os
from functools import lru_cache
from time import perf_counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import BackendConfig
from backend.modules.workcenters.integration import WorkcenterSyncError
from backend.modules.workcenters.synchronization import synchronize_workcenters
from backend.shared.environment import load_environment, required_env


@lru_cache(maxsize=1)
def _sessions():
    config = BackendConfig.from_env()
    engine = create_engine(
        config.td_database_uri, pool_size=1, max_overflow=0,
        pool_timeout=config.td_pool_timeout, pool_recycle=config.td_pool_recycle,
        pool_pre_ping=True, hide_parameters=True,
    )
    atexit.register(engine.dispose)
    return sessionmaker(engine)


def default(logger):
    try:
        load_environment()
        enabled = os.environ.get("DJ_WORKCENTERS_SYNC_ENABLED", "false").strip().lower()
        if enabled not in ("true", "false", "1", "0"):
            raise WorkcenterSyncError("DJ_WORKCENTERS_SYNC_ENABLED deve ser true, false, 1 ou 0.")
        if enabled not in ("true", "1"):
            return
        started_at = perf_counter()
        count = synchronize_workcenters(
            _sessions(), username=required_env("DJ_MES_USER"), password=required_env("DJ_MES_PASSWORD"),
        )
    except WorkcenterSyncError:
        raise
    except Exception:
        # O H24 registra traceback e encaminha o erro. Não propagar detalhes de
        # configuração, conexão ou bibliotecas que possam carregar dados privados.
        raise WorkcenterSyncError("Falha na configuração ou sincronização semanal de centros.") from None
    logger.info(
        "DJ_WORKCENTERS: catálogo ativo sincronizado; %s centro(s) em %.2f segundo(s).",
        count, perf_counter() - started_at,
    )
