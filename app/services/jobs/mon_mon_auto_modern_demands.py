"""Adaptador do Auto Scheduler para o início agendado das demandas modernas."""

import atexit
import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import BackendConfig
from backend.shared.environment import load_environment
from backend.modules.demands.scheduling import start_scheduled_work


@lru_cache(maxsize=1)
def _sessions():
    # Pool próprio do processo Windows; não cria Flask nem importa app.config.
    config = BackendConfig.from_env()
    engine = create_engine(config.td_database_uri, pool_size=1, max_overflow=0,
        pool_timeout=config.td_pool_timeout, pool_recycle=config.td_pool_recycle,
        pool_pre_ping=True, hide_parameters=True)
    atexit.register(engine.dispose)
    return sessionmaker(engine)


def default(logger):
    load_environment()
    enabled = os.environ.get("DJ_DEMAND_WORK_AUTOSTART_ENABLED", "false").strip().lower()
    if enabled not in ("true", "false", "1", "0"):
        raise ValueError("DJ_DEMAND_WORK_AUTOSTART_ENABLED deve ser true, false, 1 ou 0.")
    if enabled not in ("true", "1"):
        return
    count = start_scheduled_work(_sessions())
    if count:
        logger.info("%s demanda(s) moderna(s) iniciada(s) conforme agendamento.", count)
