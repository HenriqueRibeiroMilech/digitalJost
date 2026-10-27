"""Contratos comuns de paginação; modelos e capacidades continuam por domínio."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


Item = TypeVar("Item")
Capabilities = TypeVar("Capabilities")


class PaginationQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=12, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[Item, Capabilities]):
    items: list[Item]
    page: int
    per_page: int
    total: int
    capabilities: Capabilities
