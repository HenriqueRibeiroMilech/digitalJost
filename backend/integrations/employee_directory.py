"""Consulta de funcionários por matrícula, independente do login e do legado."""

import re
import ssl
from dataclasses import dataclass
from typing import Literal

from ldap3 import NONE, NTLM, SUBTREE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars

from backend.config import LdapDirectoryConfig


EmployeeLookupStatus = Literal[
    "complete", "partial", "not_found", "unavailable", "ambiguous", "unsupported_badge",
]


@dataclass(frozen=True)
class EmployeeLookup:
    status: EmployeeLookupStatus
    name: str | None = None
    department: str | None = None


class EmployeeDirectory:
    def __init__(self, config: LdapDirectoryConfig | None):
        # Apenas guarda configuração. Nenhuma conexão, thread ou busca no startup.
        self.config = config

    def find_by_badge(self, badge: str) -> EmployeeLookup:
        if not isinstance(badge, str) or re.fullmatch(r"2300[0-9]{8}", badge) is None:
            return EmployeeLookup("unsupported_badge")
        if self.config is None:
            return EmployeeLookup("unavailable")
        registration = badge[4:]
        connection = None
        try:
            server = Server(
                self.config.host,
                port=self.config.port,
                use_ssl=self.config.use_ssl,
                tls=Tls(validate=ssl.CERT_REQUIRED) if self.config.use_ssl else None,
                connect_timeout=self.config.connect_timeout,
                get_info=NONE,
            )
            connection = Connection(
                server, user=self.config.user, password=self.config.password,
                authentication=NTLM, receive_timeout=self.config.receive_timeout,
                auto_referrals=False, read_only=True, raise_exceptions=False,
            )
            if not connection.bind():
                return EmployeeLookup("unavailable")
            connection.search(
                self.config.search_base,
                # O legado lê a matrícula do segundo campo de description, que
                # pode ter outros campos depois. A busca não pode exigir um sufixo.
                f"(&(objectCategory=Person)(description=*{escape_filter_chars(registration)}*))",
                search_scope=SUBTREE,
                attributes=["description", "displayName", "department"],
                size_limit=2, time_limit=self.config.receive_timeout,
            )
            result_code = connection.result.get("result")
            # Não selecionar a primeira pessoa quando há mais de uma ou truncamento.
            if result_code == 4:
                return EmployeeLookup("ambiguous")
            if result_code != 0:
                return EmployeeLookup("unavailable")
            matches = [
                entry for entry in connection.entries
                if self._matches_registration(entry, registration)
            ]
            if len(matches) > 1:
                return EmployeeLookup("ambiguous")
            if not matches:
                return EmployeeLookup("not_found")
            entry = matches[0]
            name = self._text(entry, "displayName", max_length=200)
            department = self._text(entry, "department", max_length=200)
            status: EmployeeLookupStatus = "complete" if name and department else "partial"
            return EmployeeLookup(status, name=name, department=department)
        except (LDAPException, OSError, ValueError):
            # Não propagar dados do diretório, credenciais ou erros internos à API.
            return EmployeeLookup("unavailable")
        finally:
            if connection is not None:
                try:
                    connection.unbind()
                except (LDAPException, OSError):
                    pass

    @classmethod
    def _matches_registration(cls, entry, registration):
        description = cls._text(entry, "description")
        if not description:
            return False
        fields = description.split(";")
        # Mesmo campo usado em auth_routes/create_external_user, tolerando espaços.
        # Mantém suporte ao atributo que contém somente os oito dígitos.
        value = fields[1].strip() if len(fields) > 1 else description
        return value == registration

    @staticmethod
    def _text(entry, attribute, *, max_length=None):
        value = entry[attribute].value
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8")
            except UnicodeError:
                return None
        if not isinstance(value, str):
            return None
        value = value.strip()
        if not value or (max_length is not None and len(value.encode("utf-16-le")) > max_length * 2):
            return None
        return value
