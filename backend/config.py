"""Configuração própria do backend, recebendo o destino do TD na composição."""

import os
from dataclasses import dataclass, field

from sqlalchemy.engine import URL


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        raise ValueError(f"{name} deve ser um número inteiro.") from None


@dataclass(frozen=True)
class BackendConfig:
    td_database_uri: str | URL = field(repr=False)
    td_pool_size: int = 5
    td_max_overflow: int = 0
    td_pool_timeout: int = 30
    td_pool_recycle: int = 1800

    def __post_init__(self):
        if not self.td_database_uri:
            raise ValueError("O destino do banco TD deve ser fornecido na composição.")
        for name, minimum in (
            ("td_pool_size", 1),
            ("td_max_overflow", 0),
            ("td_pool_timeout", 1),
            ("td_pool_recycle", 1),
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or value < minimum:
                raise ValueError(f"{name} deve ser um inteiro maior ou igual a {minimum}.")

    @classmethod
    def from_env(cls, *, td_database_uri):
        return cls(
            td_database_uri=td_database_uri,
            td_pool_size=_env_int("BACKEND_TD_POOL_SIZE", 5),
            td_max_overflow=_env_int("BACKEND_TD_MAX_OVERFLOW", 0),
            td_pool_timeout=_env_int("BACKEND_TD_POOL_TIMEOUT", 30),
            td_pool_recycle=_env_int("BACKEND_TD_POOL_RECYCLE", 1800),
        )
