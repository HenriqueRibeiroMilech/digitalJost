"""Importação manual do CSV Plex: somente motivos Active=true, sem acesso ao Plex."""

import argparse
import csv
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from backend.config import BackendConfig

from .models import WorkcenterEvent


class EventImportError(RuntimeError):
    """Erro de importação sem dados de linha, SQL ou configuração privada."""


def read_active_events(path):
    """Valida o arquivo completo antes de permitir qualquer escrita no TD."""
    expected = {"Description", "Code", "Workcenter Event Group", "Active"}
    records, descriptions = [], set()
    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source, strict=True)
            if not reader.fieldnames or len(reader.fieldnames) != 4 or set(reader.fieldnames) != expected:
                raise EventImportError("O CSV precisa das quatro colunas originais do cadastro de motivos.")
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise EventImportError("O CSV contém uma linha com quantidade de campos inválida.")
                active = row["Active"].strip().lower()
                if active not in ("true", "false"):
                    raise EventImportError("A coluna Active deve conter somente true ou false.")
                if active == "false":
                    continue
                record = {
                    "description": row["Description"].strip(),
                    "code": row["Code"].strip(),
                    "workcenter_event_group": row["Workcenter Event Group"].strip(),
                }
                for field, limit in (("description", 300), ("code", 50), ("workcenter_event_group", 100)):
                    value = record[field]
                    if (field != "code" and not value) or len(value.encode("utf-16-le")) // 2 > limit:
                        raise EventImportError("Um campo de motivo ativo está vazio ou excede o tamanho local.")
                normalized = " ".join(record["description"].casefold().split())
                if normalized in descriptions:
                    raise EventImportError("O CSV contém descrições ativas duplicadas; revisar o cadastro.")
                descriptions.add(normalized)
                records.append(record)
                if len(records) > 1000:
                    raise EventImportError("O catálogo excede o tamanho previsto; revisar a importação.")
    except (OSError, UnicodeError, csv.Error):
        raise EventImportError("Não foi possível ler o CSV original em UTF-8.") from None
    if not records:
        raise EventImportError("Nenhum motivo ativo foi encontrado; o catálogo anterior será preservado.")
    return records


def import_events_csv(sessions, path):
    records = read_active_events(path)
    synced_at = datetime.now(timezone.utc).replace(tzinfo=None)
    incoming = {" ".join(row["description"].casefold().split()) for row in records}
    try:
        with sessions.begin() as session:
            existing = {
                " ".join(row.description.casefold().split()): row
                for row in session.scalars(select(WorkcenterEvent).with_hint(
                    WorkcenterEvent, "WITH (TABLOCKX, HOLDLOCK)", "mssql",
                ))
            }
            for description, row in existing.items():
                if description not in incoming:
                    session.delete(row)
            session.flush()
            for record in records:
                normalized = " ".join(record["description"].casefold().split())
                stored = existing.get(normalized)
                if stored is None:
                    stored = WorkcenterEvent()
                    session.add(stored)
                stored.description = record["description"]
                stored.code = record["code"]
                stored.workcenter_event_group = record["workcenter_event_group"]
                stored.last_synced_at = synced_at
        return len(records)
    except SQLAlchemyError:
        raise EventImportError("A importação no TD falhou; a transação foi revertida.") from None


def main():
    parser = argparse.ArgumentParser(description="Importa os motivos ativos do CSV Plex no TD.")
    parser.add_argument("--file", required=True, type=Path, help="Caminho do CSV original exportado do Plex.")
    parser.add_argument("--apply", action="store_true", help="Publica no TD; sem esta opção, apenas valida o CSV.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    logger = logging.getLogger("workcenter-events-import")
    engine = None
    try:
        records = read_active_events(args.file)
        if not args.apply:
            logger.info("CSV válido: %s motivo(s) ativo(s). Nenhuma conexão com o banco foi aberta.", len(records))
            return 0
        config = BackendConfig.from_env()
        engine = create_engine(
            config.td_database_uri, pool_size=1, max_overflow=0,
            pool_timeout=config.td_pool_timeout, pool_recycle=config.td_pool_recycle,
            pool_pre_ping=True, hide_parameters=True,
        )
        count = import_events_csv(sessionmaker(engine), args.file)
        logger.info("DJ_WORKCENTER_EVENTS: %s motivo(s) ativo(s) publicados.", count)
        return 0
    except EventImportError as error:
        logger.error("%s", error)
        return 1
    except Exception:
        logger.error("Falha de configuração da importação; conferir o ambiente TD e as permissões.")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
