from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.platform.schemas import PaginatedResponse, PaginationQuery


EventStatus = Literal["upcoming", "ongoing", "completed", "unscheduled"]


class EventCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        strict=True,
    )

    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    event_type_id: int = Field(gt=0, le=2147483647)
    instructor: str | None = Field(default=None, max_length=200)
    syllabus: str | None = Field(default=None, max_length=4000)
    starts_at: datetime
    ends_at: datetime

    @field_validator("starts_at", "ends_at", mode="before")
    @classmethod
    def parse_event_datetime(cls, value):
        # Horário local do evento, sem conversão para UTC ou fuso do navegador.
        if not isinstance(value, str) or len(value) < 16 or value[10] != "T":
            raise ValueError("Informe a data e a hora no formato AAAA-MM-DDTHH:MM.")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            raise ValueError("Informe uma data e hora válidas.") from None
        if parsed.tzinfo is not None:
            raise ValueError("Informe o horário local do evento, sem fuso horário.")
        if parsed.microsecond % 1000:
            raise ValueError("Use precisão de até milissegundos para o horário.")
        return parsed


class EventQuery(PaginationQuery):
    """Consulta paginada de Eventos."""

    search: str = Field(default="", max_length=120)
    status: str = Field(default="upcoming,ongoing", min_length=1, max_length=80)

    @field_validator("search", mode="before")
    @classmethod
    def strip_search(cls, value):
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("Informe um título sem caracteres nulos.")
        return value.strip() if isinstance(value, str) else value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        statuses = [status.strip() for status in value.split(",")]
        if any(status not in get_args(EventStatus) for status in statuses):
            raise ValueError("Selecione status válidos para os eventos.")
        return ",".join(dict.fromkeys(statuses))


class EventOut(BaseModel):
    id: int
    name: str
    description: str
    event_type_id: int | None
    event_type_name: str | None
    instructor: str | None
    syllabus: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    status: EventStatus


class EventCapabilities(BaseModel):
    can_create: bool
    can_update: bool
    can_delete: bool


class EventDetail(EventOut):
    capabilities: EventCapabilities


class EventDeleted(BaseModel):
    id: int


class EventTypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    name: str = Field(min_length=1, max_length=80)


class EventTypeOut(BaseModel):
    id: int
    name: str


class EventTypes(BaseModel):
    items: list[EventTypeOut]
    can_create: bool


class EventList(PaginatedResponse[EventOut, EventCapabilities]):
    """Lista com as capacidades específicas de Eventos."""


class AttendanceListCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    name: str = Field(min_length=1, max_length=120)


class AttendanceCreate(BaseModel):
    # Matrícula é texto: não converter em número nem retirar zeros à esquerda.
    model_config = ConfigDict(extra="forbid", strict=True)

    registration: str = Field(min_length=12, max_length=12, pattern=r"^[0-9]{12}$")


class AttendanceCapabilities(BaseModel):
    can_export: bool
    can_create: bool
    can_register: bool
    can_update: bool
    can_delete: bool
    can_delete_entry: bool


class AttendanceListOut(BaseModel):
    id: int
    event_id: int
    name: str
    total: int


class AttendanceListDetail(AttendanceListOut):
    capabilities: AttendanceCapabilities


class AttendanceLists(PaginatedResponse[AttendanceListOut, AttendanceCapabilities]):
    """Listas de presença de um único evento."""


class AttendanceOut(BaseModel):
    id: int
    registration: str
    name: str | None
    department: str | None
    company: str | None


class AttendanceEntries(PaginatedResponse[AttendanceOut, AttendanceCapabilities]):
    """Presenças paginadas de uma lista."""


class AttendanceRegistered(BaseModel):
    item: AttendanceOut
    created: bool
    lookup_status: Literal["complete", "partial"]


class AttendanceDeleted(BaseModel):
    id: int
