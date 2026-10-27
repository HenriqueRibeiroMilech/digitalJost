"""Tabelas de solicitações e projeção de leitura do cadastro compartilhado."""

from datetime import datetime

from sqlalchemy import FetchedValue, ForeignKey, Integer, func
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


class Demand(Base):
    __tablename__ = "DJ_DEMANDS"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    area_id: Mapped[int] = mapped_column(Integer)
    requester_id: Mapped[str] = mapped_column(NVARCHAR(128))
    contributor_id: Mapped[str | None] = mapped_column(NVARCHAR(128))
    entry_kind: Mapped[str] = mapped_column(NVARCHAR(10))
    classification: Mapped[str | None] = mapped_column(NVARCHAR(16))
    status: Mapped[str] = mapped_column(NVARCHAR(32), server_default="em_analise")
    title: Mapped[str] = mapped_column(NVARCHAR(250))
    description: Mapped[str] = mapped_column(NVARCHAR(4000))
    urgency: Mapped[str] = mapped_column(NVARCHAR(10))
    assumptions: Mapped[str | None] = mapped_column(NVARCHAR(4000))
    current_problems: Mapped[str | None] = mapped_column(NVARCHAR(4000))
    expected_benefits: Mapped[str | None] = mapped_column(NVARCHAR(4000))
    submission_key: Mapped[str] = mapped_column(CHAR(36))
    submission_fingerprint: Mapped[str] = mapped_column(CHAR(64))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())
    updated_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())
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
