"""Diagnóstico LDAP manual e somente leitura; não inicializa a aplicação."""

import argparse
import getpass
import json
import re
import ssl
import sys
import warnings
from time import perf_counter


def _candidate_summary(entry, badge, directory):
    description = directory._text(entry, "description")
    fields = description.split(";") if description else []
    registration = badge[4:]
    return {
        "tipo_description": type(entry["description"].value).__name__,
        "quantidade_campos": len(fields),
        "primeiros_campos": [
            {
                "posicao": position,
                "tamanho": len(field.strip()),
                "igual_matricula": field.strip() == registration,
                "igual_cracha": field.strip() == badge,
                "igual_sem_zeros_iniciais": (
                    field.strip().isascii() and field.strip().isdecimal()
                    and field.strip().lstrip("0") == registration.lstrip("0")
                ),
            }
            for position, field in enumerate(fields[:8], start=1)
        ],
        "aceito_pelo_parser_atual": directory._matches_registration(entry, registration),
        "nome_utilizavel": bool(directory._text(entry, "displayName", max_length=200)),
        "setor_utilizavel": bool(directory._text(entry, "department", max_length=200)),
    }


def _lookup_status(result_code, candidates):
    if result_code == 4:
        return "ambiguous"
    if result_code != 0:
        return "unavailable"
    matches = [item for item in candidates if item["aceito_pelo_parser_atual"]]
    if len(matches) > 1:
        return "ambiguous"
    if not matches:
        return "not_found"
    return "complete" if matches[0]["nome_utilizavel"] and matches[0]["setor_utilizavel"] else "partial"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--by-login", action="store_true",
        help="Compara também com uma busca exata pelo login Windows da mesma pessoa.",
    )
    args = parser.parse_args()
    report = {"etapa": "dependencias"}
    connection = None
    try:
        # Estes módulos não importam app, bootstrap, engines ou schedulers.
        from ldap3 import NONE, NTLM, SUBTREE, Connection, Server, Tls
        from ldap3.utils.conv import escape_filter_chars

        from backend.config import LdapDirectoryConfig
        from backend.integrations.employee_directory import EmployeeDirectory

        report["etapa"] = "configuracao"
        config = LdapDirectoryConfig.from_env()
        if config is None:
            report["erro"] = "DJ_LDAP_USER ou DJ_LDAP_PASSWORD ausente ou vazio."
            return 1
        report["configuracao"] = {
            "credenciais_presentes": True,
            "ssl": config.use_ssl,
            "timeout_conexao_segundos": config.connect_timeout,
            "timeout_resposta_segundos": config.receive_timeout,
        }

        report["etapa"] = "entrada"
        if not sys.stdin.isatty():
            report["erro"] = "Execute em um terminal interativo, sem redirecionar a entrada."
            return 2
        with warnings.catch_warnings():
            # Não aceitar fallback que possa exibir o crachá no terminal.
            warnings.simplefilter("error", getpass.GetPassWarning)
            badge = getpass.getpass("Aproxime o crachá de 12 dígitos e pressione Enter (entrada oculta): ")
        if re.fullmatch(r"2300[0-9]{8}", badge) is None:
            report["erro"] = "Informe exatamente 12 dígitos com prefixo 2300; nenhuma consulta foi feita."
            return 2
        login = None
        if args.by_login:
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                login = getpass.getpass("Login Windows da MESMA pessoa, sem domínio ou @ (entrada oculta): ").strip()
            if not login or len(login) > 128 or not login.isprintable():
                report["erro"] = "Login vazio ou inválido; nenhuma consulta foi feita."
                return 2

        registration_filter = escape_filter_chars(badge[4:])
        queries = [
            ("atual_contem", f"(&(objectCategory=Person)(description=*{registration_filter}*))"),
            ("legado_termina_com", f"(&(objectCategory=Person)(description=*{registration_filter}))"),
        ]
        if login is not None:
            # Reproduz somente o filtro do login legado, sem importar sua rota.
            queries.append((
                "por_login",
                f"(&(objectCategory=Person)(mailNickname={escape_filter_chars(login)}))",
            ))

        report["etapa"] = "conexao_e_bind"
        server = Server(
            config.host, port=config.port, use_ssl=config.use_ssl,
            tls=Tls(validate=ssl.CERT_REQUIRED) if config.use_ssl else None,
            connect_timeout=config.connect_timeout, get_info=NONE,
        )
        connection = Connection(
            server, user=config.user, password=config.password,
            authentication=NTLM, receive_timeout=config.receive_timeout,
            auto_referrals=False, read_only=True, raise_exceptions=False,
        )
        started = perf_counter()
        bound = connection.bind()
        report["bind"] = {
            "sucesso": bound,
            "codigo_ldap": (connection.result or {}).get("result"),
            "duracao_ms": round((perf_counter() - started) * 1000),
        }
        if not bound:
            return 1

        report["consultas"] = {}
        for label, search_filter in queries:
            report["etapa"] = label
            started = perf_counter()
            connection.search(
                config.search_base,
                search_filter,
                search_scope=SUBTREE,
                attributes=["description", "displayName", "department"],
                size_limit=2, time_limit=config.receive_timeout,
            )
            result_code = (connection.result or {}).get("result")
            candidates = [
                _candidate_summary(entry, badge, EmployeeDirectory)
                for entry in connection.entries
            ]
            report["consultas"][label] = {
                "codigo_ldap": result_code,
                "duracao_ms": round((perf_counter() - started) * 1000),
                "candidatos_retornados": len(candidates),
                "resultado_pela_regra_atual": _lookup_status(result_code, candidates),
                "candidatos": candidates,
            }
            if result_code not in (0, 4):
                return 1
        report["etapa"] = "concluido"
        return 0
    except (KeyboardInterrupt, EOFError):
        report["erro"] = "Diagnóstico interrompido."
        return 2
    except Exception as error:
        # Nunca imprimir mensagem, traceback, objetos LDAP ou dados retornados.
        report["erro"] = "Falha na etapa indicada; detalhes privados foram omitidos."
        report["tipo_erro"] = type(error).__name__
        return 1
    finally:
        if connection is not None:
            try:
                connection.unbind()
            except Exception:
                report["aviso"] = "Não foi possível confirmar o encerramento da conexão."
        print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
