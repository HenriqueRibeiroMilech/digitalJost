from pydantic import BaseModel, ConfigDict, Field

from backend.platform.schemas import PaginatedResponse, PaginationQuery


class EventCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        strict=True,
    )

    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=1, max_length=2000)


class EventQuery(PaginationQuery):
    """Consulta paginada de Eventos."""


class EventOut(BaseModel):
    id: int
    name: str
    description: str


class EventCapabilities(BaseModel):
    can_create: bool


class EventList(PaginatedResponse[EventOut, EventCapabilities]):
    """Lista com as capacidades específicas de Eventos."""
