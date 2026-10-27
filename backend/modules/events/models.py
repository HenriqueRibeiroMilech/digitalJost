"""Mapeamentos das tabelas de Eventos; não criam estruturas nem confirmam dados."""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, func
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database import Base


class EventType(Base):
    __tablename__ = "DJ_EVENT_TYPES"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(NVARCHAR(80, collation="Latin1_General_100_CI_AS"))
    created_by: Mapped[str] = mapped_column(NVARCHAR(128))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())


class Event(Base):
    __tablename__ = "DJ_EVENTS"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(NVARCHAR(120))
    description: Mapped[str] = mapped_column(NVARCHAR(2000))
    created_by: Mapped[str] = mapped_column(NVARCHAR(128))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())
    # O período do evento usa horário local; a data de criação acima é registrada em UTC.
    starts_at: Mapped[datetime | None] = mapped_column(DATETIME2(precision=3))
    ends_at: Mapped[datetime | None] = mapped_column(DATETIME2(precision=3))
    event_type_id: Mapped[int | None] = mapped_column(ForeignKey("dbo.DJ_EVENT_TYPES.id"))
    instructor: Mapped[str | None] = mapped_column(NVARCHAR(200))
    syllabus: Mapped[str | None] = mapped_column(NVARCHAR(4000))


class AttendanceList(Base):
    __tablename__ = "DJ_EVENT_ATTENDANCE_LISTS"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # A cascata é executada pelo banco ao excluir o evento, incluindo suas listas.
    event_id: Mapped[int] = mapped_column(ForeignKey("dbo.DJ_EVENTS.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(NVARCHAR(120))
    created_by: Mapped[str] = mapped_column(NVARCHAR(128))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())


class AttendanceEntry(Base):
    __tablename__ = "DJ_EVENT_ATTENDANCE_ENTRIES"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("dbo.DJ_EVENT_ATTENDANCE_LISTS.id", ondelete="CASCADE"))
    registration: Mapped[str] = mapped_column(VARCHAR(12))
    name: Mapped[str | None] = mapped_column(NVARCHAR(200))
    department: Mapped[str | None] = mapped_column(NVARCHAR(200))
    company: Mapped[str | None] = mapped_column(NVARCHAR(200))
    created_by: Mapped[str] = mapped_column(NVARCHAR(128))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())
