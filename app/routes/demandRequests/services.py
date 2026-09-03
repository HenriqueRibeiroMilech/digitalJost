from datetime import date, datetime
from decimal import Decimal

from .domain import ConflictError, NotFoundError, validate_new_request


_ACTIVE_STATUSES = ('A Fazer', 'Em Andamento', 'Pausado')
_STATUS_ORDER = (
    'Em análise', 'A Fazer', 'Em Andamento', 'Pausado',
    'Concluído', 'Cancelado', 'Recusada'
)
_TYPE_LABELS = (
    ('projeto', 'Projetos'),
    ('melhoria', 'Melhorias'),
    ('erro', 'Erros')
)
_MONTH_LABELS = (
    'jan', 'fev', 'mar', 'abr', 'mai', 'jun',
    'jul', 'ago', 'set', 'out', 'nov', 'dez'
)


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

    def get_area_analytics(self, area_id):
        with self.engine.connect() as connection:
            database_today, rows = self.repository.list_area_analytics(
                connection, area_id
            )

        today = self._as_date(database_today) or date.today()
        status_totals = {status: 0 for status in _STATUS_ORDER}
        type_totals = {demand_type: 0 for demand_type, _ in _TYPE_LABELS}
        months = self._analytics_months(today)
        months_by_key = {item['key']: item for item in months}
        active_count = 0
        overdue_count = 0
        completed_count = 0
        on_time_count = 0
        completed_with_deadline = 0

        for row in rows:
            status = row['status']
            if status in status_totals:
                status_totals[status] += 1
            demand_type = row['demandType']
            if demand_type in type_totals:
                type_totals[demand_type] += 1

            request_date = self._as_date(row['requestDate'])
            request_month = self._month_key(request_date)
            if request_month in months_by_key:
                months_by_key[request_month]['requested'] += 1

            if status in _ACTIVE_STATUSES:
                active_count += 1
                deadline = self._as_date(row['deadline'])
                if deadline and deadline < today:
                    overdue_count += 1

            if status == 'Concluído':
                completed_count += 1
                completed_at = self._as_date(row['completedAt'])
                completed_month = self._month_key(completed_at)
                if completed_month in months_by_key:
                    months_by_key[completed_month]['completed'] += 1
                deadline = self._as_date(row['deadline'])
                if completed_at and deadline:
                    completed_with_deadline += 1
                    if completed_at <= deadline:
                        on_time_count += 1

        late_completion_count = completed_with_deadline - on_time_count
        return {
            'summary': {
                'total': len(rows),
                'pending': status_totals['Em análise'],
                'active': active_count,
                'completed': completed_count,
                'overdue': overdue_count,
                'onTimeRate': (
                    round(on_time_count * 100 / completed_with_deadline)
                    if completed_with_deadline else None
                )
            },
            'status': [
                {'label': status, 'value': status_totals[status]}
                for status in _STATUS_ORDER
            ],
            'types': [
                {'label': label, 'value': type_totals[demand_type]}
                for demand_type, label in _TYPE_LABELS
            ],
            'monthly': months,
            'deadlines': [
                {'label': 'No prazo', 'value': on_time_count},
                {'label': 'Com atraso', 'value': late_completion_count}
            ],
            'deadlineSample': completed_with_deadline
        }

    @staticmethod
    def _as_date(value):
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        return None

    @staticmethod
    def _month_key(value):
        return f'{value.year:04d}-{value.month:02d}' if value else None

    @staticmethod
    def _analytics_months(today):
        current_index = today.year * 12 + today.month - 1
        result = []
        for month_index in range(current_index - 11, current_index + 1):
            year, zero_based_month = divmod(month_index, 12)
            month = zero_based_month + 1
            result.append({
                'key': f'{year:04d}-{month:02d}',
                'label': f'{_MONTH_LABELS[month - 1]}/{str(year)[-2:]}',
                'requested': 0,
                'completed': 0
            })
        return result

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
