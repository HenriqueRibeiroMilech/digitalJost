"""Leitura HTTPS do Data Source 790, sem cookies ou dependências de app/."""

from dataclasses import dataclass

import requests
from requests.auth import HTTPBasicAuth


WORKCENTERS_URL = "https://jost.on.plex.com/api/datasources/790/execute"
READ_ROW_LIMIT = 1000


class WorkcenterSyncError(RuntimeError):
    """Erro público da sincronização; não contém corpo, credenciais ou SQL."""


@dataclass(frozen=True)
class SourceWorkcenter:
    plex_workcenter_key: int
    workcenter_code: str
    name: str
    workcenter_group: str | None


def _text(value, limit, *, nullable=False):
    if value is None and nullable:
        return None
    if not isinstance(value, str):
        raise WorkcenterSyncError("O Data Source 790 retornou um campo de texto inválido.")
    value = value.strip()
    if nullable and not value:
        return None
    if not value or len(value.encode("utf-16-le")) // 2 > limit:
        raise WorkcenterSyncError("Um texto do Data Source 790 está vazio ou excede o tamanho local.")
    return value


def _parse_catalog(payload):
    # Contrato Data Source: tables[0].columns/rows, diferente de Data.Rows da tela.
    if not isinstance(payload, dict) or payload.get("errors"):
        raise WorkcenterSyncError("O Data Source 790 retornou erro ou resposta inválida.")
    tables = payload.get("tables")
    if not isinstance(tables, list) or len(tables) != 1 or not isinstance(tables[0], dict):
        raise WorkcenterSyncError("O Data Source 790 não retornou a tabela esperada.")
    table = tables[0]
    if table.get("rowLimitExceeded") is not False:
        raise WorkcenterSyncError("A completude do Data Source 790 não foi confirmada; catálogo anterior preservado.")
    columns, rows = table.get("columns"), table.get("rows")
    if not isinstance(columns, list) or not isinstance(rows, list) or not 0 < len(rows) < READ_ROW_LIMIT:
        raise WorkcenterSyncError("O catálogo está vazio, inválido ou atingiu o limite de leitura.")
    names = [column.get("name") if isinstance(column, dict) else column for column in columns]
    if any(not isinstance(name, str) for name in names) or len(set(names)) != len(names):
        raise WorkcenterSyncError("As colunas do Data Source 790 são inválidas ou duplicadas.")
    required = {"Workcenter_Key", "Workcenter_Code", "Name", "Workcenter_Group"}
    if not required.issubset(names):
        raise WorkcenterSyncError("O Data Source 790 não retornou todas as colunas do catálogo.")

    catalog, keys, codes = [], set(), set()
    for row in rows:
        if not isinstance(row, list) or len(row) != len(names):
            raise WorkcenterSyncError("Uma linha do Data Source 790 não corresponde às colunas.")
        item = dict(zip(names, row))
        key = item["Workcenter_Key"]
        if type(key) is not int or not 0 < key <= 2147483647:
            raise WorkcenterSyncError("O Data Source 790 retornou uma chave de centro inválida.")
        code = _text(item["Workcenter_Code"], 50)
        if key in keys or code.casefold() in codes:
            raise WorkcenterSyncError("O Data Source 790 retornou centros duplicados.")
        keys.add(key)
        codes.add(code.casefold())
        catalog.append(SourceWorkcenter(
            plex_workcenter_key=key,
            workcenter_code=code,
            name=_text(item["Name"], 200),
            workcenter_group=_text(item["Workcenter_Group"], 100, nullable=True),
        ))
    return catalog


def fetch_active_workcenters(*, username, password):
    """Busca e valida o catálogo inteiro antes de permitir qualquer escrita local."""
    try:
        with requests.Session() as client:
            response = client.post(
                WORKCENTERS_URL,
                json={"inputs": {"Active": 1}},
                auth=HTTPBasicAuth(username, password),
                headers={"Accept": "application/json"},
                timeout=(5, 30),
                allow_redirects=False,
                verify=True,
            )
            if response.status_code != 200:
                raise WorkcenterSyncError(
                    f"A leitura do Data Source 790 falhou (HTTP {response.status_code})."
                )
            payload = response.json()
    except (requests.RequestException, ValueError):
        raise WorkcenterSyncError("Não foi possível obter JSON válido do Data Source 790 por HTTPS.") from None
    return _parse_catalog(payload)
