from app.utils.db_utils import get_engine

from .repository import DemandManagementRepository
from .review_notifications import RequestReviewNotifier
from .services import DemandManagementService


def build_service():
    return DemandManagementService(
        engine=get_engine('jdt'),
        repository=DemandManagementRepository(),
        review_notifier=RequestReviewNotifier()
    )
