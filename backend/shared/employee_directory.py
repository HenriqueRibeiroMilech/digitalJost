"""Consulta compartilhada de funcionários por matrícula, independente do login."""

import re
import ssl
from dataclasses import dataclass
from typing import Literal

from ldap3 import NONE, NTLM, SUBTREE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars

from backend.config import LdapDirectoryConfig


_MAX_LOOKUP_CANDIDATES = 200


EmployeeLookupStatus = Literal[
    "complete", "partial", "not_found", "unavailable", "ambiguous", "unsupported_badge",
]


@dataclass(frozen=True)
class EmployeeLookup:
    status: EmployeeLookupStatus
    name: str | None = None
    department: str | None = None
    company: str | None = None


class EmployeeDirectory:
    def __init__(self, config: LdapDirectoryConfig | None):
        # Apenas guarda configuração. Nenhuma conexão, thread ou busca no startup.
        self.config = config

    def find_by_badge(self, badge: str) -> EmployeeLookup:
        if not isinstance(badge, str) or re.fullmatch(r"[0-9]{12}", badge) is None:
            return EmployeeLookup("unsupported_badge")
        if self.config is None:
            return EmployeeLookup("unavailable")
        # A matrícula é única no grupo; os quatro primeiros dígitos variam por empresa.
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
                self._registration_filter(registration),
                search_scope=SUBTREE,
                attributes=[
                    "description", "displayName", "department", "physicalDeliveryOfficeName",
                ],
                # O limite conta candidatos; a unicidade usa a matrícula exata abaixo.
                size_limit=_MAX_LOOKUP_CANDIDATES, time_limit=self.config.receive_timeout,
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
            company = self._text(entry, "physicalDeliveryOfficeName", max_length=200)
            status: EmployeeLookupStatus = "complete" if all((name, department, company)) else "partial"
            return EmployeeLookup(status, name=name, department=department, company=company)
        except (LDAPException, OSError, ValueError):
            # Não propagar dados do diretório, credenciais ou erros internos à API.
            return EmployeeLookup("unavailable")
        finally:
            if connection is not None:
                try:
                    connection.unbind()
                except (LDAPException, OSError):
                    pass

    @staticmethod
    def _registration_filter(registration):
        # O LDAP pode guardar a matrícula sem os zeros de preenchimento do crachá.
        # Mantém um dígito para que uma matrícula zerada não gere um filtro vazio.
        value = escape_filter_chars(registration.lstrip("0") or "0")
        # Com separadores, a matrícula precisa ocorrer depois de um ';'. Sem eles,
        # preserva o atributo contendo somente a matrícula, inclusive com espaços.
        # Os candidatos ainda passam pela comparação exata do segundo campo.
        return (
            "(&(objectCategory=Person)(|"
            f"(description=*;*{value}*)"
            f"(&(description=*{value}*)(!(description=*;*)))"
            "))"
        )

    @classmethod
    def _matches_registration(cls, entry, registration):
        description = cls._text(entry, "description")
        if not description:
            return False
        fields = description.split(";")
        # Mesmo campo usado em auth_routes/create_external_user, tolerando espaços.
        # Mantém suporte ao atributo contendo somente a matrícula.
        value = fields[1].strip() if len(fields) > 1 else description
        # Aceita somente a diferença de zeros à esquerda, nunca uma substring,
        # número maior, sinal ou dígitos Unicode. O crachá original não é alterado.
        return re.fullmatch(r"[0-9]{1,8}", value) is not None and value.zfill(8) == registration

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
