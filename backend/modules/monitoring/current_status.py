"""Consulta das fontes locais, sem tabela intermediária ou inicialização de clientes."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from threading import Lock
from time import monotonic

from sqlalchemy import bindparam, select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.modules.workcenters.models import Workcenter, WorkcenterEvent


STATUS_COLUMNS = (
    "Workcenter_Key", "Workcenter_Code", "Name", "Workcenter", "Workcenter_Group",
    "Log_Date", "Log_Duration", "Responsible", "Status", "Event", "Event_Code",
    "Performance", "Availability", "Quality", "OEE", "GoodParts", "TotalParts",
    "ExpectedParts", "TotalRun", "TotalAvail", "TotalStopped", "Goal",
)

# Cache curto sob demanda, por processo. Não cria thread nem consulta no import.
# Evita repetir a seleção FTM de 30 dias para cada tela aberta no mesmo instante.
_snapshot_cache = {}
_snapshot_lock = Lock()
_SNAPSHOT_TTL = 5

_RESPONSIBLE_BY_EVENT = {
    "20-Troca de Insumo": "Processos",
    "31-Processo": "Processos",
    "37-Centralizacao de Bico": "Processos",
    "32-Troca de Graxa": "Processos",
    "43-Falta de Ferramenta de Usinagem": "Processos",
    "100-Setup": "Processos",
    "44-Sistema Indisponivel": "Transformação Digital",
    "3-Medicao": "Qualidade",
    "4-Problema de Qualidade": "Qualidade",
    "65-Problema de Qualidade - @1": "Qualidade",
    "19-Aguardando Inspecao": "Qualidade",
    "42-Retrabalho": "Qualidade",
    "-Falta de Saldo": "Material",
}

_MACH2_QUERY = text("""
    WITH current_status AS (
        SELECT ID, Workcenter, WcStatus, WcReason, CanRunProduction, StatusBegin,
            DATEDIFF_BIG(SECOND, StatusBegin, GETDATE()) AS duration_seconds,
            ROW_NUMBER() OVER (
                PARTITION BY Workcenter ORDER BY StatusBegin DESC, ID DESC
            ) AS rn
        FROM [JOST_INTEGRATION_PRD].[dbo].[Mach_2_Current_Status]
        WHERE StatusEnd IS NULL AND StatusBegin <= GETDATE()
            AND Workcenter IN :workcenters
    )
    SELECT Workcenter, WcStatus, WcReason, CanRunProduction, StatusBegin, duration_seconds
    FROM current_status WHERE rn = 1
""").bindparams(bindparam("workcenters", expanding=True))

# Mantém a seleção FTM já utilizada pela consolidação antiga. Cada consulta usa
# sua conexão, porque FTM e Mach2 não precisam estar na mesma instância SQL.
_FTM_QUERY = text("""
    WITH mic_stops AS (
        SELECT T1.sDescription AS Workcenter_Name, T3.GRUPO AS Workcenter_Group,
            T1.tStart AS Log_Date, T1.dDuration AS Raw_Duration,
            CONCAT(T2.COD_PARADA, '-', T2.DESC_PARADA) AS Event,
            T1.sEventDescription, COALESCE(T2.CATEGORIA, 'Sem Justificativa') AS Status,
            ROW_NUMBER() OVER (
                PARTITION BY T1.sDescription ORDER BY T1.tStart DESC
            ) AS rn
        FROM OEEQEventDetail T1
        LEFT JOIN CADASTRO_PARADA T2 ON T1.sReasonCode = T2.MOTIVO
        INNER JOIN CONFIG_TABLET T3 ON T1.sDescription = T3.NOME_MAQUINA
        WHERE T1.tStart >= DATEADD(DAY, -30, GETDATE())
            AND T1.dDuration > '00:00:01'
            AND T1.sEventDescription <> 'Fim Produção'
            AND T3.FL_ATIVO = 1
            AND EXISTS (
                SELECT 1 FROM OEEQEventDetail T4
                WHERE T4.sDescription = T1.sDescription
                    AND T4.sEventDescription = 'Parada'
                    AND T4.tStart >= DATEADD(DAY, -30, GETDATE())
            )
    )
    SELECT Workcenter_Name, Workcenter_Group, Log_Date, Raw_Duration, Event, Status
    FROM mic_stops WHERE sEventDescription = 'Parada' AND rn = 1
""")


class CurrentStatusError(RuntimeError):
    """Falha pública de leitura, sem SQL, parâmetros ou configuração privada."""


def _normalize_description(value):
    return " ".join((value or "").strip().casefold().split())


def _event_code(value):
    code = str(value).strip() if value is not None else ""
    if code.endswith(".0") and code[:-2].isdigit():
        code = code[:-2]
    return code


def _normalize_status(value):
    value = (value or "").strip()
    if value in ("Manutenção Parada", "Manutenção Produtiva"):
        return "Manutenção"
    return value or "Sem Justificativa"


def _duration(seconds):
    hours, remainder = divmod(max(0, int(seconds)), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _ftm_seconds(value):
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, (time, datetime)):
        return value.hour * 3600 + value.minute * 60 + value.second
    try:
        hours, minutes, seconds = str(value).split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (ValueError, TypeError):
        raise CurrentStatusError("O FTM retornou uma duração de parada inválida.") from None


def _read_rows(engine, query, params=None):
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(query, params or {}).mappings()]


def _result(*, key, code, name, group, started_at, seconds, status, event, event_code, goal):
    return {
        "Workcenter_Key": key, "Workcenter_Code": code, "Name": name,
        "Workcenter": f"{code}-{name}".upper(), "Workcenter_Group": group,
        "Log_Date": started_at.strftime("%d/%m/%Y %H:%M:%S"),
        "Log_Duration": _duration(seconds), "Status": status, "Event": event,
        "Event_Code": event_code,
        "Responsible": _RESPONSIBLE_BY_EVENT.get(event, status),
        # A consolidação S30 ativa já publicava estes indicadores como zero.
        "Performance": 0, "Availability": 0, "Quality": 0, "OEE": 0,
        "GoodParts": 0, "TotalParts": 0, "ExpectedParts": 0,
        "TotalRun": 0, "TotalAvail": 0, "TotalStopped": 0, "Goal": goal,
    }


def _read_snapshot(sessions, mach2_engine, ftm_engine):
    cache_key = (sessions, mach2_engine, ftm_engine)
    with _snapshot_lock:
        cached = _snapshot_cache.get(cache_key)
        if cached is not None and monotonic() < cached[0]:
            return cached[1]
        with sessions() as session:
            statement = select(
                Workcenter.plex_workcenter_key, Workcenter.workcenter_code,
                Workcenter.name, Workcenter.workcenter_group,
            )
            catalog = [dict(row) for row in session.execute(statement).mappings()]
            if not catalog:
                raise CurrentStatusError("DJ_WORKCENTERS está vazio; sincronize o catálogo antes de consultar.")
            goals = dict(session.execute(text(
                "SELECT workcenter, Goal1 FROM PLEX_REGISTER_GOAL"
            )).all())
            event_catalog = [dict(row) for row in session.execute(select(
                WorkcenterEvent.description.label("Description"),
                WorkcenterEvent.code.label("Code"),
                WorkcenterEvent.workcenter_event_group.label("Workcenter_Event_Group"),
            )).mappings()]
            if not event_catalog:
                raise CurrentStatusError("DJ_WORKCENTER_EVENTS está vazio; importe os motivos ativos antes de consultar.")

        codes = [row["workcenter_code"] for row in catalog if row["workcenter_group"]]
        with ThreadPoolExecutor(max_workers=2) as executor:
            mach2_future = executor.submit(
                _read_rows, mach2_engine, _MACH2_QUERY, {"workcenters": codes},
            ) if codes else None
            ftm_future = executor.submit(_read_rows, ftm_engine, _FTM_QUERY)
            mach2_rows = mach2_future.result() if mach2_future else []
            ftm_rows = ftm_future.result()
        snapshot = (catalog, goals, event_catalog, mach2_rows, ftm_rows)
        _snapshot_cache[cache_key] = (monotonic() + _SNAPSHOT_TTL, snapshot)
        return snapshot


def read_current_status(
    sessions, *, mach2_engine, ftm_engine, workcenter=None,
    stops_only=False, exclude_s18=False,
):
    """Lê TD/Mach2/FTM; devolve novos registros no contrato legado, sem escrita.

    Motivo ausente do catálogo continua visível com a classificação Mach2, mas
    sem inventar Event_Code. Código vazio cadastrado também é preservado.
    Falhas de fonte não são convertidas em ausência de paradas ou cache vencido.
    """
    try:
        catalog, goals, event_catalog, mach2_rows, ftm_rows = _read_snapshot(
            sessions, mach2_engine, ftm_engine,
        )

        # Os centros sem grupo continuam no cadastro, mas não participavam do S30.
        centers = {
            row["workcenter_code"].casefold(): row for row in catalog
            if row["workcenter_group"] and (workcenter is None or row["workcenter_code"] == workcenter)
            and (not exclude_s18 or row["workcenter_code"] != "S18")
        }
        events = {}
        for item in event_catalog:
            description = _normalize_description(item.get("Description"))
            if not description:
                continue
            events.setdefault(description, set()).add((
                _event_code(item.get("Code")),
                _normalize_status(item["Workcenter_Event_Group"]) if item.get("Workcenter_Event_Group") else None,
            ))

        result, current_codes = [], set()
        for row in mach2_rows:
            center = centers.get(row["Workcenter"].strip().casefold())
            if center is None:
                continue
            code = center["workcenter_code"]
            current_codes.add(code.casefold())
            if row["CanRunProduction"] not in (0, 1):
                raise CurrentStatusError("O Mach2 retornou uma situação de produção inválida.")
            stopped = row["CanRunProduction"] == 0
            seconds = row["duration_seconds"]
            if stops_only and (not stopped or seconds <= 30):
                continue
            reason = (row["WcReason"] or "").strip() if stopped else ""
            status = _normalize_status(row["WcStatus"])
            matches = events.get(_normalize_description(reason), set()) if reason else set()
            event_code = ""
            if len(matches) == 1:
                event_code, event_status = next(iter(matches))
                status = event_status or status
            elif matches:
                raise CurrentStatusError("O catálogo contém motivos ambíguos para uma parada atual.")
            event = f"{event_code}-{reason or 'Sem Justificativa'}" if stopped else "-"
            result.append(_result(
                key=center["plex_workcenter_key"], code=code, name=center["name"],
                group=center["workcenter_group"], started_at=row["StatusBegin"], seconds=seconds,
                status=status, event=event, event_code=event_code,
                goal=goals.get(center["plex_workcenter_key"], 0) or 0,
            ))

        # Mach2 prevalece quando ambos os sistemas têm dados para o mesmo centro.
        for row in ftm_rows:
            code, separator, name = row["Workcenter_Name"].partition("-")
            code = code.strip()
            if not separator or not code:
                raise CurrentStatusError("O FTM retornou um nome de centro fora do formato esperado.")
            if code.casefold() in current_codes or (workcenter is not None and code != workcenter):
                continue
            if exclude_s18 and code == "S18":
                continue
            event = row["Event"] or "-"
            event_code = event.partition("-")[0].strip()
            result.append(_result(
                key=0, code=code, name=name, group=row["Workcenter_Group"],
                started_at=row["Log_Date"], seconds=_ftm_seconds(row["Raw_Duration"]),
                status=_normalize_status(row["Status"]), event=event,
                event_code=event_code, goal=goals.get(0, 0) or 0,
            ))
        return sorted(result, key=lambda row: (row["Workcenter_Group"] or "", row["Workcenter_Code"]))
    except SQLAlchemyError:
        raise CurrentStatusError("Não foi possível consultar uma das fontes locais do monitoramento.") from None
