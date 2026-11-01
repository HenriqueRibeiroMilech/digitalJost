from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from backend.shared.schemas import PaginatedResponse, PaginationQuery


class RequestFields(BaseModel):
    # Valida defaults para cobrar os detalhes da demanda mesmo quando forem omitidos.
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, strict=True, validate_default=True,
    )

    entry_kind: Literal["demanda", "erro"]
    title: str = Field(min_length=1, max_length=250)
    description: str = Field(min_length=1, max_length=4000)
    urgency: Literal["Alta", "Média", "Baixa"]
    contributor_id: str | None = Field(default=None, max_length=128)
    assumptions: str | None = Field(default=None, max_length=4000)
    current_problems: str | None = Field(default=None, max_length=4000)
    expected_benefits: str | None = Field(default=None, max_length=4000)

    @field_validator("title", "description", "contributor_id", "assumptions", "current_problems", "expected_benefits")
    @classmethod
    def validate_text(cls, value, info: ValidationInfo):
        if value is None:
            return None
        limit = 250 if info.field_name == "title" else 128 if info.field_name in ("contributor_id", "responsible_id") else 4000
        try:
            # O limite de NVARCHAR conta unidades UTF-16; alguns símbolos ocupam duas.
            units = len(value.encode("utf-16-le")) // 2
        except UnicodeEncodeError:
            raise ValueError("Informe um texto válido.") from None
        if "\x00" in value or units > limit:
            raise ValueError(f"Use até {limit} caracteres válidos.")
        return value or None

    @field_validator("assumptions", "current_problems", "expected_benefits")
    @classmethod
    def require_demand_details(cls, value, info: ValidationInfo):
        # Relatos de erro descartam os detalhes exclusivos de uma solicitação de demanda.
        if info.data.get("entry_kind") == "erro":
            return None
        if info.data.get("entry_kind") == "demanda" and not value:
            raise ValueError("Preencha este campo para solicitar uma demanda.")
        return value


class RequestCreate(RequestFields):
    submission_key: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class RequestUpdate(RequestFields):
    row_version: str = Field(pattern=r"^[0-9a-fA-F]{16}$")


class RequestQuery(PaginationQuery):
    area: Literal["Transformação Digital"] = "Transformação Digital"
    search: str = Field(default="", max_length=250)
    entry_kind: Literal["todos", "demanda", "erro"] = "todos"

    @field_validator("search")
    @classmethod
    def validate_search(cls, value):
        if "\x00" in value:
            raise ValueError("Informe uma pesquisa válida.")
        return value.strip()


class ManagementQuery(RequestQuery):
    status: Literal["pendentes", "todos", "em_analise", "aguardando_informacoes", "a_fazer", "recusado"] = "pendentes"


class RequestReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    action: Literal["accept", "reject", "request_information"]
    row_version: str = Field(pattern=r"^[0-9a-fA-F]{16}$")
    responsible_id: str | None = Field(default=None, min_length=1, max_length=128)
    classification: Literal["melhoria", "projeto"] | None = None
    message: str | None = Field(default=None, min_length=1, max_length=4000)

    @field_validator("responsible_id", "message")
    @classmethod
    def validate_text(cls, value, info: ValidationInfo):
        return RequestFields.validate_text(value, info)

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.action == "accept":
            if not self.responsible_id or self.message is not None:
                raise ValueError("Selecione o responsável para aceitar a solicitação.")
        elif not self.message or self.responsible_id is not None or self.classification is not None:
            raise ValueError("Informe o motivo sem responsável ou classificação para esta ação.")
        return self


class RequestCapabilities(BaseModel):
    can_create: bool


class RequestItem(BaseModel):
    id: int
    entry_kind: Literal["demanda", "erro"]
    title: str
    description: str
    urgency: str
    status: str
    created_at: datetime
    requester_name: str | None
    relationship: Literal["requester", "contributor", "manager"]


class AttachmentOut(BaseModel):
    id: int
    original_name: str
    size_bytes: int


class HistoryOut(BaseModel):
    id: int
    event_type: str
    actor_name: str | None
    created_at: datetime
    message: str | None


class RequestDetail(RequestItem):
    contributor_id: str | None
    contributor_name: str | None
    responsible_id: str | None
    responsible_name: str | None
    classification: str | None
    assumptions: str | None
    current_problems: str | None
    expected_benefits: str | None
    updated_at: datetime
    row_version: str
    can_update: bool
    can_review: bool
    attachments: list[AttachmentOut]
    history: list[HistoryOut]


class RequestList(PaginatedResponse[RequestItem, RequestCapabilities]):
    pass


class ContributorOut(BaseModel):
    id: str
    name: str


class ContributorsOut(BaseModel):
    items: list[ContributorOut]


WorkKind = Literal["projeto", "melhoria", "erro", "atividade", "aviso"]


class WorkFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    kind: WorkKind
    title: str = Field(min_length=1, max_length=250)
    description: str = Field(min_length=1, max_length=4000)
    responsible_id: str = Field(min_length=1, max_length=128)
    contributor_id: str | None = Field(default=None, max_length=128)
    urgency: Literal["Alta", "Média", "Baixa"] | None = None
    assumptions: str | None = Field(default=None, max_length=4000)
    current_problems: str | None = Field(default=None, max_length=4000)
    expected_benefits: str | None = Field(default=None, max_length=4000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    hide_after_end: bool = True

    @field_validator("title", "description", "responsible_id", "contributor_id", "assumptions", "current_problems", "expected_benefits")
    @classmethod
    def validate_text(cls, value, info: ValidationInfo):
        return RequestFields.validate_text(value, info)

    @field_validator("starts_at", "ends_at", mode="before")
    @classmethod
    def parse_notice_time(cls, value):
        if value is None:
            return None
        if not isinstance(value, str) or len(value) < 20 or value[10] != "T":
            raise ValueError("Informe a data e hora com fuso horário.")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            raise ValueError("Informe uma data e hora válidas.") from None
        if parsed.tzinfo is None or parsed.microsecond % 1000:
            raise ValueError("Informe o fuso horário e precisão de até milissegundos.")
        try:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        except (ValueError, OverflowError):
            raise ValueError("Informe uma data e hora dentro do intervalo válido.") from None

    @model_validator(mode="after")
    def validate_kind(self):
        if self.kind == "aviso":
            if self.starts_at is None or self.ends_at is None or self.ends_at <= self.starts_at:
                raise ValueError("Informe início e fim do aviso; o fim deve ser posterior ao início.")
        elif self.starts_at is not None or self.ends_at is not None:
            raise ValueError("Datas de início e fim pertencem somente aos avisos.")
        if self.kind in ("projeto", "melhoria"):
            if not all((self.assumptions, self.current_problems, self.expected_benefits)):
                raise ValueError("Preencha premissas, problemas atuais e ganhos esperados.")
        elif any((self.assumptions, self.current_problems, self.expected_benefits)):
            raise ValueError("Os campos de contexto pertencem somente a projetos e melhorias.")
        if self.kind in ("atividade", "aviso"):
            if self.urgency is not None or self.contributor_id is not None:
                raise ValueError("Atividade e aviso usam título, descrição e responsável.")
        elif self.urgency is None:
            raise ValueError("Informe a urgência da demanda.")
        if self.kind != "aviso":
            self.hide_after_end = False
        return self


class WorkCreate(WorkFields):
    submission_key: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class WorkVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)
    row_version: str = Field(pattern=r"^[0-9a-fA-F]{16}$")


class WorkContent(WorkFields, WorkVersion):
    pass


class WorkPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    row_version: str = Field(pattern=r"^[0-9a-fA-F]{16}$")
    difficulty: Literal["Baixa", "Média", "Alta"] | None = None
    priority: int | None = Field(default=None, ge=1, le=10)
    estimated_hours: float | None = Field(default=None, ge=0, le=99999.99, allow_inf_nan=False)
    daily_hours: float | None = Field(default=None, ge=0, le=99999.99, allow_inf_nan=False)
    completed_hours: float = Field(ge=0, le=99999.99, allow_inf_nan=False)
    observations: str | None = Field(default=None, max_length=4000)

    @field_validator("estimated_hours", "daily_hours", "completed_hours")
    @classmethod
    def validate_hours(cls, value):
        if value is not None and Decimal(str(value)) != Decimal(str(value)).quantize(Decimal("0.01")):
            raise ValueError("Use até duas casas decimais para as horas.")
        return value

    @field_validator("observations")
    @classmethod
    def validate_text(cls, value, info: ValidationInfo):
        return RequestFields.validate_text(value, info)


WorkActionName = Literal[
    "start", "cancel", "schedule", "request_information", "complete", "validate",
    "pause", "wait_third_party", "resume", "change_deadline", "reopen", "cancel_schedule",
]


class WorkAction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    action: WorkActionName
    row_version: str = Field(pattern=r"^[0-9a-fA-F]{16}$")
    scheduled_start_on: date | None = None
    due_on: date | None = None
    expected_return_on: date | None = None
    message: str | None = Field(default=None, min_length=1, max_length=4000)

    @field_validator("scheduled_start_on", "due_on", "expected_return_on", mode="before")
    @classmethod
    def parse_day(cls, value):
        if value is None:
            return None
        if not isinstance(value, str) or len(value) != 10 or value[4] != "-" or value[7] != "-":
            raise ValueError("Informe uma data no formato AAAA-MM-DD.")
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise ValueError("Informe uma data válida.") from None

    @field_validator("message")
    @classmethod
    def validate_text(cls, value, info: ValidationInfo):
        return RequestFields.validate_text(value, info)

    @model_validator(mode="after")
    def validate_action(self):
        needs_message = self.action in ("cancel", "request_information", "validate", "pause", "wait_third_party", "reopen", "change_deadline")
        if needs_message != (self.message is not None):
            raise ValueError("Informe a mensagem obrigatória somente nas ações que a solicitam.")
        if (self.action in ("start", "schedule", "change_deadline", "reopen")) != (self.due_on is not None):
            raise ValueError("Informe o prazo somente ao iniciar, agendar, reabrir ou alterar prazo.")
        if (self.action == "schedule") != (self.scheduled_start_on is not None):
            raise ValueError("Informe a data de início somente ao agendar.")
        if (self.action == "pause") != (self.expected_return_on is not None):
            raise ValueError("Informe a previsão de retorno somente ao pausar.")
        return self


class WorkQuery(PaginationQuery):
    area: Literal["Transformação Digital"] = "Transformação Digital"
    view: Literal["users", "notices"] = "users"
    owner_id: str | None = Field(default=None, min_length=1, max_length=128)
    search: str = Field(default="", max_length=250)
    kind: Literal["todos", "projeto", "melhoria", "erro", "atividade"] = "todos"
    status: Literal["todos", "ativos", "atrasados", "a_fazer", "agendado", "em_andamento", "aguardando_informacoes",
                    "em_validacao", "pausado", "aguardando_terceiros", "concluido", "cancelado"] = "ativos"
    difficulty: Literal["todas", "Baixa", "Média", "Alta"] = "todas"
    sort: Literal["priority", "deadline", "newest"] = "priority"
    notice_state: Literal["visible", "all", "active", "upcoming", "expired", "finalized"] = "visible"

    @field_validator("owner_id", "search")
    @classmethod
    def validate_text(cls, value):
        if value is not None and "\x00" in value:
            raise ValueError("Informe um filtro válido.")
        return value.strip() if value is not None else None


class WorkOwner(ContributorOut):
    total: int


class WorkBoard(BaseModel):
    owners: list[WorkOwner]
    notice_total: int
    actor_id: str
    can_create: bool


class WorkItemOut(BaseModel):
    id: int
    source_request_id: int | None
    kind: WorkKind
    title: str
    description: str
    responsible_id: str
    requester_id: str
    contributor_id: str | None
    responsible_name: str | None
    requester_name: str | None
    contributor_name: str | None
    urgency: str | None
    assumptions: str | None
    current_problems: str | None
    expected_benefits: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    hide_after_end: bool
    notice_finalized_at: datetime | None
    notice_state: str | None
    status: str
    scheduled_start_on: date | None
    started_on: date | None
    due_on: date | None
    expected_return_on: date | None
    is_overdue: bool
    closed_at: datetime | None
    difficulty: str | None
    priority: int | None
    estimated_hours: float | None
    daily_hours: float | None
    completed_hours: float
    observations: str | None
    created_at: datetime
    updated_at: datetime


class WorkHistoryChange(BaseModel):
    field: str
    before: str | None
    after: str | None


class WorkHistoryOut(BaseModel):
    id: int
    event_type: str
    actor_name: str | None
    created_at: datetime
    fields: list[str]
    message: str | None
    transitions: list[WorkHistoryChange]


class WorkDetail(WorkItemOut):
    row_version: str
    can_update: bool
    can_edit_content: bool
    can_manage_tasks: bool
    available_actions: list[WorkActionName]
    attachments: list[AttachmentOut]
    history: list[WorkHistoryOut]


class WorkCapabilities(BaseModel):
    can_create: bool


class WorkList(PaginatedResponse[WorkItemOut, WorkCapabilities]):
    pass


class TaskFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)
    title: str = Field(min_length=1, max_length=250)
    description: str | None = Field(default=None, max_length=4000)
    responsible_id: str = Field(min_length=1, max_length=128)
    priority: int | None = Field(default=None, ge=1, le=10)
    due_on: date | None = None
    completed: bool = False

    @field_validator("title", "description", "responsible_id")
    @classmethod
    def validate_text(cls, value, info: ValidationInfo):
        return RequestFields.validate_text(value, info)

    @field_validator("due_on", mode="before")
    @classmethod
    def parse_day(cls, value):
        return WorkAction.parse_day(value)


class TaskCreate(TaskFields, WorkVersion):
    submission_key: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class TaskUpdate(TaskFields, WorkVersion):
    task_row_version: str = Field(pattern=r"^[0-9a-fA-F]{16}$")


class TaskDelete(WorkVersion):
    task_row_version: str = Field(pattern=r"^[0-9a-fA-F]{16}$")


class TaskQuery(PaginationQuery):
    status: Literal["all", "pending", "completed"] = "pending"


class TaskOut(BaseModel):
    id: int
    title: str
    description: str | None
    responsible_id: str
    responsible_name: str | None
    priority: int | None
    due_on: date | None
    completed_at: datetime | None
    row_version: str


class TaskCapabilities(BaseModel):
    can_update: bool


class TaskList(PaginatedResponse[TaskOut, TaskCapabilities]):
    pass
