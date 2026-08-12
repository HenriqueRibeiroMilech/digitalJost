from app.utils.db_utils import get_engine

from .repository import DemandManagementRepository
from .services import DemandManagementService


def build_service():
    return DemandManagementService(
        engine=get_engine('jdt'),
        repository=DemandManagementRepository()
    )
