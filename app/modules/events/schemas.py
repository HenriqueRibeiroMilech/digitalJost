from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        strict=True,
    )

    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=1, max_length=2000)


class EventQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=12, ge=1, le=100)


class EventOut(BaseModel):
    id: int
    name: str
    description: str


class EventCapabilities(BaseModel):
    can_create: bool


class EventList(BaseModel):
    items: list[EventOut]
    page: int
    per_page: int
    total: int
    capabilities: EventCapabilities