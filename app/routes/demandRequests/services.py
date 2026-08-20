from datetime import date, datetime
from decimal import Decimal

from .domain import ConflictError, NotFoundError, validate_new_request


def _serialize_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


class DemandRequestsService:
    def __init__(self, engine, repository, storage):
        self.engine = engine
        self.repository = repository
        self.storage = storage

    def list_user_requests(self, area_id, user_id):
        with self.engine.connect() as connection:
            rows = self.repository.list_user_requests(connection, area_id, user_id)

        return [
            {key: _serialize_value(value) for key, value in dict(row).items()}
            for row in rows
        ]

    def create_request(self, area_id, user_id, form_data, files):
        demand = validate_new_request(form_data)
        request_id = None
        stored_names = []

        try:
            with self.engine.begin() as connection:
                request_id = self.repository.next_request_id(connection)
                stored_names = self.storage.save(request_id, files)
                images = ''.join(f'{name}||' for name in stored_names)

                created = self.repository.create_request(
                    connection, request_id, area_id, user_id, demand, images
                )
                if not created:
                    raise ConflictError('Não foi possível cadastrar a solicitação.')
        except Exception:
            if stored_names and request_id is not None:
                self.storage.remove_files(request_id, stored_names)
            raise

        return self.get_request(request_id, area_id, user_id, False)

    def get_request(self, request_id, area_id, user_id, allow_area_access):
        with self.engine.connect() as connection:
            row = self.repository.get_request(connection, request_id, area_id)
            if not row:
                raise NotFoundError('Solicitação não encontrada.')
            if not allow_area_access and str(row['requesterId']) != str(user_id):
                raise NotFoundError('Solicitação não encontrada.')
            pauses = self.repository.list_pauses(connection, request_id)

        result = {key: _serialize_value(value) for key, value in dict(row).items()}
        result.pop('requesterId', None)
        images = result.pop('images', '') or ''
        stored_names = [name for name in images.split('||') if name]
        result['attachments'] = [
            {'index': index, 'name': name}
            for index, name in enumerate(stored_names)
            if self.storage.is_safe_stored_name(name)
        ]
        result['pauses'] = [
            {key: _serialize_value(value) for key, value in dict(pause).items()}
            for pause in pauses
        ]
        return result

    def get_attachment(self, request_id, attachment_index, area_id, user_id, allow_area_access):
        detail = self.get_request(request_id, area_id, user_id, allow_area_access)
        attachment = next(
            (
                item for item in detail['attachments']
                if item['index'] == attachment_index
            ),
            None
        )
        if not attachment:
            raise NotFoundError('Anexo não encontrado.')
        return self.storage.request_directory(request_id), attachment['name']
