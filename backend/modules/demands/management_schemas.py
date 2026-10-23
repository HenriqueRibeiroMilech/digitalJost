from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from .schemas import AttachmentOut, ContributorOut, HistoryOut


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="after")
    @classmethod
    def valid_text(cls, value, info: ValidationInfo):
        if isinstance(value, str):
            try:
                units = len(value.encode("utf-16-le")) // 2
            except UnicodeEncodeError:
                raise ValueError("Informe texto válido.") from None
            limit = next((item.max_length for item in cls.model_fields[info.field_name].metadata if hasattr(item, "max_length")), 4000)
            if "\x00" in value or units > limit:
                raise ValueError(f"Use até {limit} caracteres válidos.")
        return value


class Version(Input):
    row_version: str = Field(pattern=r"^[0-9a-fA-F]{16}$")


class BoardQuery(Input):
    search: str = Field(default="", max_length=250)
    responsible_id: str = Field(default="", max_length=128)
    demand_type: Literal["todos", "projeto", "melhoria", "erro", "atividade"] = "todos"
    status: str = Field(default="", max_length=200)
    difficulty: Literal["", "Baixa", "Média", "Alta"] = ""
    sort: Literal["deadline", "priority"] = "deadline"
    completed_from: date | None = None
    completed_to: date | None = None


class Review(Version):
    action: Literal["accept", "decline", "information"]
    responsible_id: str | None = Field(default=None, max_length=128)
    classification: Literal["melhoria", "projeto"] | None = None
    reason: str | None = Field(default=None, max_length=4000)
    information_kind: Literal["informacoes", "reuniao"] = "informacoes"


class ManagementFields(Input):
    title: str = Field(min_length=1, max_length=250)
    description: str = Field(min_length=1, max_length=4000)
    responsible_id: str = Field(min_length=1, max_length=128)
    urgency: Literal["Alta", "Média", "Baixa"] = "Média"
    assumptions: str | None = Field(default=None, max_length=4000)
    current_problems: str | None = Field(default=None, max_length=4000)
    expected_benefits: str | None = Field(default=None, max_length=4000)
    estimated_hours: Decimal | None = Field(default=None, ge=0, le=99999.99, decimal_places=2)
    daily_hours: Decimal | None = Field(default=None, ge=0, le=99999.99, decimal_places=2)
    completed_hours: Decimal | None = Field(default=None, ge=0, le=99999.99, decimal_places=2)
    difficulty: Literal["Baixa", "Média", "Alta"] | None = None
    priority: int | None = Field(default=None, ge=1, le=10)
    observations: str | None = Field(default=None, max_length=4000)


class InternalCreate(ManagementFields):
    demand_type: Literal["projeto", "melhoria", "erro", "atividade"]
    contributor_id: str | None = Field(default=None, max_length=128)
    submission_key: str = Field(pattern=r"^[0-9a-f-]{36}$")

    @model_validator(mode="after")
    def details(self):
        if self.demand_type in ("projeto", "melhoria"):
            if not all((self.assumptions, self.current_problems, self.expected_benefits)):
                raise ValueError("Preencha premissas, problemas atuais e ganhos esperados.")
        return self


class ManagementUpdate(ManagementFields, Version):
    pass


class FlowAction(Version):
    action: Literal["start", "complete", "cancel", "schedule", "unschedule", "information", "validate", "pause", "third_party", "resume"]
    reason: str | None = Field(default=None, max_length=4000)
    expected_return: date | None = None
    scheduled_start_date: date | None = None
    initial_deadline: date | None = None
    information_kind: Literal["informacoes", "reuniao"] = "informacoes"

    @model_validator(mode="after")
    def initial_deadline_only(self):
        if self.initial_deadline is not None and self.action not in ("start", "schedule"):
            raise ValueError("O prazo só pode ser alterado pela ação própria, com justificativa.")
        return self


class DeadlineChange(Version):
    deadline: date
    reason: str = Field(min_length=1, max_length=4000)


class TaskCreate(Version):
    description: str = Field(min_length=1, max_length=1000)
    responsible_id: str | None = Field(default=None, max_length=128)
    priority: int | None = Field(default=None, ge=1, le=10)
    deadline: date | None = None
    observations: str | None = Field(default=None, max_length=2000)
    completed: bool = False


class TaskUpdate(TaskCreate):
    task_version: str = Field(pattern=r"^[0-9a-fA-F]{16}$")


class InformationReply(Version):
    information_id: int = Field(gt=0)
    reply: str = Field(min_length=1, max_length=4000)


class NoticeFields(Input):
    title: str = Field(min_length=1, max_length=250)
    description: str = Field(min_length=1, max_length=4000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    hide_after_end: bool = False

    @model_validator(mode="after")
    def period(self):
        for value in (self.starts_at, self.ends_at):
            if value and value.tzinfo is not None:
                raise ValueError("Informe o horário local do aviso, sem fuso.")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("O fim deve ser posterior ao início.")
        if self.hide_after_end and not self.ends_at:
            raise ValueError("Informe o fim para finalizar automaticamente.")
        return self


class NoticeUpdate(NoticeFields, Version):
    pass


class NoticeCreate(NoticeFields):
    submission_key: str = Field(pattern=r"^[0-9a-f-]{36}$")


class ManagementItem(BaseModel):
    id: int
    entry_kind: str
    demand_type: str | None
    origin: str
    title: str
    description: str
    status: str
    urgency: str
    requester_name: str | None
    responsible_id: str | None
    responsible_name: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    deadline: date | None
    scheduled_start_date: date | None
    estimated_hours: float | None
    daily_hours: float | None
    completed_hours: float | None
    difficulty: str | None
    priority: int | None
    observations: str | None
    expected_return: date | None
    total_tasks: int
    completed_tasks: int
    row_version: str
    can_edit: bool


class ManagementDetail(ManagementItem):
    contributor_name: str | None
    assumptions: str | None
    current_problems: str | None
    expected_benefits: str | None
    attachments: list[AttachmentOut]
    history: list[HistoryOut]
    tasks: list[dict[str, Any]]
    information_requests: list[dict[str, Any]]
    notification_warning: str | None = None


class NoticeOut(NoticeFields):
    model_config = ConfigDict(extra="ignore")
    id: int
    created_by_name: str | None
    row_version: str
    can_edit: bool


class BoardOut(BaseModel):
    items: list[ManagementItem]
    notices: list[NoticeOut]
    today: date


class ManagementOptions(BaseModel):
    responsibles: list[ContributorOut]
    contributors: list[ContributorOut]
    current_user_id: str
    today: date


class ReviewsOut(BaseModel):
    items: list[ManagementItem]
