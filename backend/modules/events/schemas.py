from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.platform.schemas import PaginatedResponse, PaginationQuery


class EventCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        strict=True,
    )

    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
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


class EventOut(BaseModel):
    id: int
    name: str
    description: str
    starts_at: datetime | None
    ends_at: datetime | None


class EventCapabilities(BaseModel):
    can_create: bool
    can_update: bool
    can_delete: bool


class EventDetail(EventOut):
    capabilities: EventCapabilities


class EventDeleted(BaseModel):
    id: int


class EventList(PaginatedResponse[EventOut, EventCapabilities]):
    """Lista com as capacidades específicas de Eventos."""
