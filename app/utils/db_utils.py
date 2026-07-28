# Pool de conexões SQLAlchemy para CNNX_JDT
import pandas as pd
import urllib
import time

from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

from app.utils.constants import CNNX_FTM, CNNX_PLEX, CNNX_JDT, CNNX_TRACE_QR, ENV

if ENV == "test":
    _pool_size = 5
    _max_overflow = 8
else:
    _pool_size = 50
    _max_overflow = 70


_JDT_ENGINE = create_engine(
    f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_JDT)}",
    poolclass=QueuePool,
    pool_size=_pool_size,
    max_overflow=_max_overflow,
    pool_timeout=30,
    pool_recycle=1800
)

_PLEX_ENGINE = create_engine(
    f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_PLEX)}",
    poolclass=QueuePool,
    pool_size=_pool_size,
    max_overflow=_max_overflow,
    pool_timeout=30,
    pool_recycle=1800
)

_FTM_ENGINE = create_engine(
    f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_FTM)}",
    poolclass=QueuePool,
    pool_size=_pool_size,
    max_overflow=_max_overflow,
    pool_timeout=30,
    pool_recycle=1800
)


_TRACE_QR_ENGINE = create_engine(
    f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_TRACE_QR)}",
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=1800
)

# Função utilitária para retornar a engine pelo nome
def get_engine(name="jdt"):
    """
    Retorna a engine de conexão pelo nome.
    """
    if name.lower() == "jdt":
        return _JDT_ENGINE
    elif name.lower() == "plex":
        return _PLEX_ENGINE
    elif name.lower() == "ftm":
        return _FTM_ENGINE
    elif name.lower() == "trace_qr":
        return _TRACE_QR_ENGINE
    else:
        raise ValueError(f"Engine desconhecida: {name}")

def engine_run_query(query, engine_name, params=None):
    
    engine = get_engine(engine_name)
    with engine.connect() as cnnx:
        return pd.read_sql(text(query), cnnx, params=params) if params else pd.read_sql(text(query), cnnx)
    
    
def timed_query(label, func, *args, **kwargs):
    start = time.time()
    result = func(*args, **kwargs)
    duration = time.time() - start
    print(f"Query '{label}' executed in {duration:.2f} seconds.")
    return result