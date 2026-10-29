"""Tabelas de solicitações e projeção de leitura do cadastro compartilhado."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, FetchedValue, ForeignKey, Integer, Numeric, func
from sqlalchemy.dialects.mssql import BIT, CHAR, DATETIME2, NVARCHAR, ROWVERSION, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database import Base


class SharedUser(Base):
    """Somente os campos consultados; o módulo não grava no cadastro de usuários."""

    __tablename__ = "JDT_USER_DETAILS"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[str] = mapped_column(VARCHAR(20), primary_key=True)
    name: Mapped[str] = mapped_column(VARCHAR(50))
    company_email: Mapped[str] = mapped_column("companyEmail", VARCHAR(50))
    active: Mapped[bool | None] = mapped_column(BIT)
    generic: Mapped[bool | None] = mapped_column(BIT)
    role: Mapped[str | None] = mapped_column(VARCHAR(100))


class Demand(Base):
    __tablename__ = "DJ_DEMANDS"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    area_id: Mapped[int] = mapped_column(Integer)
    requester_id: Mapped[str] = mapped_column(NVARCHAR(128))
    contributor_id: Mapped[str | None] = mapped_column(NVARCHAR(128))
    responsible_id: Mapped[str | None] = mapped_column(NVARCHAR(128))
    entry_kind: Mapped[str] = mapped_column(NVARCHAR(10))
    classification: Mapped[str | None] = mapped_column(NVARCHAR(16))
    status: Mapped[str] = mapped_column(NVARCHAR(32), server_default="em_analise")
    title: Mapped[str] = mapped_column(NVARCHAR(250))
    description: Mapped[str] = mapped_column(NVARCHAR(4000))
    urgency: Mapped[str] = mapped_column(NVARCHAR(10))
    assumptions: Mapped[str | None] = mapped_column(NVARCHAR(4000))
    current_problems: Mapped[str | None] = mapped_column(NVARCHAR(4000))
    expected_benefits: Mapped[str | None] = mapped_column(NVARCHAR(4000))
    # A chave identifica o envio; a impressão permite conferir se seu conteúdo é o mesmo.
    submission_key: Mapped[str] = mapped_column(CHAR(36))
    submission_fingerprint: Mapped[str] = mapped_column(CHAR(64))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())
    updated_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())
    # O SQL Server gera esta versão binária; a rota a compara ao editar o registro.
    row_version: Mapped[bytes] = mapped_column(
        ROWVERSION, server_default=FetchedValue(), server_onupdate=FetchedValue(),
    )


class DemandAttachment(Base):
    __tablename__ = "DJ_DEMAND_ATTACHMENTS"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    demand_id: Mapped[int] = mapped_column(ForeignKey("dbo.DJ_DEMANDS.id"))
    original_name: Mapped[str] = mapped_column(NVARCHAR(200))
    storage_key: Mapped[str] = mapped_column(CHAR(32))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(CHAR(64))
    created_by: Mapped[str] = mapped_column(NVARCHAR(128))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())


class DemandHistory(Base):
    __tablename__ = "DJ_DEMAND_HISTORY"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    demand_id: Mapped[int] = mapped_column(ForeignKey("dbo.DJ_DEMANDS.id"))
    event_type: Mapped[str] = mapped_column(NVARCHAR(40))
    actor_id: Mapped[str] = mapped_column(NVARCHAR(128))
    changes: Mapped[str | None] = mapped_column(NVARCHAR(None))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())


class WorkItem(Base):
    """Execução moderna: cadastro direto ou fotografia de uma solicitação aceita."""

    __tablename__ = "DJ_DEMAND_WORK"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    area_id: Mapped[int] = mapped_column(Integer)
    source_request_id: Mapped[int | None] = mapped_column(ForeignKey("dbo.DJ_DEMANDS.id"))
    kind: Mapped[str] = mapped_column(NVARCHAR(16))
    title: Mapped[str] = mapped_column(NVARCHAR(250))
    description: Mapped[str] = mapped_column(NVARCHAR(4000))
    responsible_id: Mapped[str] = mapped_column(NVARCHAR(128))
    requester_id: Mapped[str] = mapped_column(NVARCHAR(128))
    contributor_id: Mapped[str | None] = mapped_column(NVARCHAR(128))
    urgency: Mapped[str | None] = mapped_column(NVARCHAR(10))
    assumptions: Mapped[str | None] = mapped_column(NVARCHAR(4000))
    current_problems: Mapped[str | None] = mapped_column(NVARCHAR(4000))
    expected_benefits: Mapped[str | None] = mapped_column(NVARCHAR(4000))
    starts_at: Mapped[datetime | None] = mapped_column(DATETIME2(precision=3))
    ends_at: Mapped[datetime | None] = mapped_column(DATETIME2(precision=3))
    status: Mapped[str] = mapped_column(NVARCHAR(32), server_default="a_fazer")
    scheduled_start_on: Mapped[date | None] = mapped_column(Date)
    started_on: Mapped[date | None] = mapped_column(Date)
    due_on: Mapped[date | None] = mapped_column(Date)
    closed_at: Mapped[datetime | None] = mapped_column(DATETIME2(precision=3))
    difficulty: Mapped[str | None] = mapped_column(NVARCHAR(10))
    priority: Mapped[int | None] = mapped_column(Integer)
    estimated_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    daily_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    completed_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    observations: Mapped[str | None] = mapped_column(NVARCHAR(4000))
    created_by: Mapped[str] = mapped_column(NVARCHAR(128))
    submission_key: Mapped[str | None] = mapped_column(CHAR(36))
    submission_fingerprint: Mapped[str | None] = mapped_column(CHAR(64))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())
    updated_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())
    row_version: Mapped[bytes] = mapped_column(
        ROWVERSION, server_default=FetchedValue(), server_onupdate=FetchedValue(),
    )


class WorkHistory(Base):
    __tablename__ = "DJ_DEMAND_WORK_HISTORY"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("dbo.DJ_DEMAND_WORK.id"))
    event_type: Mapped[str] = mapped_column(NVARCHAR(40))
    actor_id: Mapped[str] = mapped_column(NVARCHAR(128))
    changes: Mapped[str | None] = mapped_column(NVARCHAR(None))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())


class WorkAttachment(Base):
    __tablename__ = "DJ_DEMAND_WORK_ATTACHMENTS"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("dbo.DJ_DEMAND_WORK.id"))
    original_name: Mapped[str] = mapped_column(NVARCHAR(200))
    storage_key: Mapped[str] = mapped_column(CHAR(32))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(CHAR(64))
    created_by: Mapped[str] = mapped_column(NVARCHAR(128))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())
