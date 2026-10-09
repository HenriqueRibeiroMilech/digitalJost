"""Engine geral do TD, criado explicitamente uma vez por aplicação."""

import atexit

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

from backend.config import BackendConfig


def init_td_database(app, config: BackendConfig):
    if "backend_td_engine" in app.extensions:
        raise RuntimeError("O acesso moderno ao TD já foi inicializado nesta aplicação.")

    engine = create_engine(
        config.td_database_uri,
        poolclass=QueuePool,
        pool_size=config.td_pool_size,
        max_overflow=config.td_max_overflow,
        pool_timeout=config.td_pool_timeout,
        pool_recycle=config.td_pool_recycle,
        pool_pre_ping=True,
        hide_parameters=True,
    )
    app.extensions["backend_td_engine"] = engine
    # O pool vive com a aplicação; não descartá-lo no teardown de cada request.
    atexit.register(engine.dispose)
    return engine
