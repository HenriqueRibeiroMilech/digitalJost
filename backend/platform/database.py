"""Engine, modelos e sessões do TD, sem criação automática de tabelas."""

import atexit

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import QueuePool

from backend.config import BackendConfig


class Base(DeclarativeBase):
    """Metadados modernos, separados do db.Model e do create_all legados."""


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
    app.extensions["backend_td_sessions"] = sessionmaker(engine)
    # O pool vive com a aplicação; não descartá-lo no teardown de cada request.
    atexit.register(engine.dispose)
    return engine


def get_td_engine():
    """Obtém o engine já inicializado para a entrada HTTP, sem criar outro pool."""
    from flask import current_app

    return current_app.extensions["backend_td_engine"]


def get_td_session_factory():
    """A factory é compartilhada; cada operação abre e fecha sua própria sessão."""
    from flask import current_app

    return current_app.extensions["backend_td_sessions"]


def paginate(session, statement, query):
    """Pagina uma projeção de campos públicos, com contagem da mesma consulta."""
    total = session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    rows = session.execute(
        statement.offset((query.page - 1) * query.per_page).limit(query.per_page),
    ).mappings()
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": query.page,
        "per_page": query.per_page,
    }


def literal_contains(value):
    """Pesquisa literal com LIKE no SQL Server; o chamador usa escape='~'."""
    escaped = value.replace("~", "~~").replace("%", "~%").replace("_", "~_").replace("[", "~[")
    return f"%{escaped}%"
