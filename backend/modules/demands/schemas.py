from datetime import datetime
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
