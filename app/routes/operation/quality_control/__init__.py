"""Controle de ocorrências do QSB, integrado às rotas Flask legadas."""

from .domain import OCCURRENCE_TYPES, PRODUCT_FAMILIES, QualityControlError
from .services import QualityControlService
