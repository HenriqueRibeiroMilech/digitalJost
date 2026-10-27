"""Configuração própria do backend para TD e consulta ao diretório corporativo."""

import os
from dataclasses import dataclass, field

from sqlalchemy.engine import URL

from .shared.environment import load_environment, required_env


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        raise ValueError(f"{name} deve ser um número inteiro.") from None


@dataclass(frozen=True)
class LdapDirectoryConfig:
    user: str = field(repr=False)
    password: str = field(repr=False)
    host: str = "SVH-DC-21.randon.com.br"
    search_base: str = "ou=EmpresasRandon,dc=randon,dc=com,dc=br"
    port: int = 389
    use_ssl: bool = False
    connect_timeout: int = 2
    receive_timeout: int = 2

    def __post_init__(self):
        if any(not value.strip() for value in (self.user, self.password, self.host, self.search_base)):
            raise ValueError("A configuração do diretório corporativo está incompleta.")
        if not 1 <= self.port <= 65535:
            raise ValueError("A porta LDAP deve estar entre 1 e 65535.")
        if self.connect_timeout < 1 or self.receive_timeout < 1:
            raise ValueError("Os tempos limite LDAP devem ser positivos.")

    @classmethod
    def from_env(cls):
        # Reutiliza somente os valores privados; não importa clientes do legado.
        load_environment()
        user = os.environ.get("DJ_LDAP_USER", "")
        password = os.environ.get("DJ_LDAP_PASSWORD", "")
        # A identificação é complementar: sua ausência não impede o startup ou a presença.
        if not user.strip() or not password.strip():
            return None
        ssl_value = os.environ.get("DJ_LDAP_USE_SSL", "false").strip().lower()
        if ssl_value not in ("true", "false", "1", "0"):
            raise ValueError("DJ_LDAP_USE_SSL deve ser true, false, 1 ou 0.")
        use_ssl = ssl_value in ("true", "1")
        return cls(
            user=user,
            password=password,
            host=os.environ.get("DJ_LDAP_HOST", cls.host),
            search_base=os.environ.get("DJ_LDAP_SEARCH_BASE", cls.search_base),
            port=_env_int("DJ_LDAP_PORT", 636 if use_ssl else 389),
            use_ssl=use_ssl,
            connect_timeout=_env_int("DJ_LDAP_CONNECT_TIMEOUT", 2),
            receive_timeout=_env_int("DJ_LDAP_RECEIVE_TIMEOUT", 2),
        )


@dataclass(frozen=True)
class BackendConfig:
    td_database_uri: str | URL = field(repr=False)
    td_pool_size: int = 5
    td_max_overflow: int = 0
    td_pool_timeout: int = 30
    td_pool_recycle: int = 1800
    employee_directory: LdapDirectoryConfig | None = field(default=None, repr=False)

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
    def from_env(cls):
        return cls(
            td_database_uri=URL.create(
                "mssql+pyodbc",
                query={"odbc_connect": required_env("DJ_TD_ODBC_CONNECTION_STRING")},
            ),
            td_pool_size=_env_int("BACKEND_TD_POOL_SIZE", 5),
            td_max_overflow=_env_int("BACKEND_TD_MAX_OVERFLOW", 0),
            td_pool_timeout=_env_int("BACKEND_TD_POOL_TIMEOUT", 30),
            td_pool_recycle=_env_int("BACKEND_TD_POOL_RECYCLE", 1800),
            employee_directory=LdapDirectoryConfig.from_env(),
        )
