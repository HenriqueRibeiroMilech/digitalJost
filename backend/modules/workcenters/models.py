"""Mapeamento do catálogo no TD; a criação depende da migration manual."""

from datetime import datetime

from sqlalchemy import CheckConstraint, Integer, UniqueConstraint, func
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database import Base


class Workcenter(Base):
    __tablename__ = "DJ_WORKCENTERS"
    __table_args__ = (
        UniqueConstraint("plex_workcenter_key", name="UQ_DJ_WORKCENTERS_plex_key"),
        UniqueConstraint("workcenter_code", name="UQ_DJ_WORKCENTERS_code"),
        CheckConstraint("plex_workcenter_key > 0", name="CK_DJ_WORKCENTERS_plex_key"),
        CheckConstraint("LEN(LTRIM(RTRIM(workcenter_code))) > 0", name="CK_DJ_WORKCENTERS_code"),
        CheckConstraint("LEN(LTRIM(RTRIM(name))) > 0", name="CK_DJ_WORKCENTERS_name"),
        {"schema": "dbo"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plex_workcenter_key: Mapped[int] = mapped_column(Integer)
    workcenter_code: Mapped[str] = mapped_column(NVARCHAR(50, collation="Latin1_General_100_CI_AS"))
    name: Mapped[str] = mapped_column(NVARCHAR(200))
    workcenter_group: Mapped[str | None] = mapped_column(NVARCHAR(100))
    created_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3), server_default=func.sysutcdatetime())
    last_synced_at: Mapped[datetime] = mapped_column(DATETIME2(precision=3))
