from datetime import date, datetime
from decimal import Decimal


def _serialize_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


class DemandRequestsService:
    def __init__(self, engine, repository):
        self.engine = engine
        self.repository = repository

    def list_user_requests(self, area_id, user_id):
        with self.engine.connect() as connection:
            rows = self.repository.list_user_requests(connection, area_id, user_id)

        return [
            {key: _serialize_value(value) for key, value in dict(row).items()}
            for row in rows
        ]
