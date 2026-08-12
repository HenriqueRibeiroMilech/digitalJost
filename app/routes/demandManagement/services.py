from datetime import date, datetime
from decimal import Decimal

from .constants import DIFFICULTY_OPTIONS, STATUS_OPTIONS
from .errors import ConflictError, NotFoundError, ValidationError
from .validation import parse_row_version, validate_management_change, validate_task


def _serialize_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


def _serialize_row(row):
    return {key: _serialize_value(value) for key, value in dict(row).items()}


class DemandManagementService:
    def __init__(self, engine, repository):
        self.engine = engine
        self.repository = repository

    def list_board(self, area_id):
        with self.engine.connect() as connection:
            demands = [_serialize_row(row) for row in self.repository.list_demands(connection, area_id)]
            responsibles = [_serialize_row(row) for row in self.repository.list_responsibles(connection, area_id)]
        return {
            'demands': demands,
            'responsibles': responsibles,
            'options': {
                'status': list(STATUS_OPTIONS),
                'difficulty': list(DIFFICULTY_OPTIONS)
            }
        }

    def get_detail(self, management_id, area_id):
        with self.engine.connect() as connection:
            demand = self.repository.get_demand(connection, management_id, area_id)
            if not demand:
                raise NotFoundError('Demanda não encontrada.')
            tasks = self.repository.list_tasks(connection, management_id, area_id)
        result = _serialize_row(demand)
        result['tasks'] = [_serialize_row(row) for row in tasks]
        return result

    def update_demand(self, management_id, area_id, payload):
        if not isinstance(payload, dict):
            raise ValidationError('Dados da alteração inválidos.')
        field = payload.get('field')
        value = validate_management_change(field, payload.get('value'))
        row_version = parse_row_version(payload.get('rowVersion'))

        with self.engine.begin() as connection:
            if field == 'responsibleId' and value:
                if not self.repository.responsible_belongs_to_area(connection, value, area_id):
                    raise ValidationError('O responsável deve ser um usuário ativo da área.')
            updated = self.repository.update_field(
                connection, management_id, area_id, field, value, row_version
            )
            if not updated:
                if not self.repository.get_demand(connection, management_id, area_id):
                    raise NotFoundError('Demanda não encontrada.')
                raise ConflictError('A demanda foi alterada por outra pessoa. Atualize a tela e tente novamente.')
        return self.get_detail(management_id, area_id)

    def create_task(self, management_id, area_id, payload, created_by):
        task = validate_task(payload)
        with self.engine.begin() as connection:
            self._validate_task_responsible(connection, task, area_id)
            task_id = self.repository.create_task(
                connection, management_id, area_id, task, created_by
            )
            if task_id is None:
                raise NotFoundError('Demanda não encontrada.')
        return self.get_detail(management_id, area_id)

    def update_task(self, management_id, task_id, area_id, payload):
        task = validate_task(payload)
        row_version = parse_row_version(payload.get('rowVersion'))
        with self.engine.begin() as connection:
            self._validate_task_responsible(connection, task, area_id)
            updated = self.repository.update_task(
                connection, management_id, task_id, area_id, task, row_version
            )
            if not updated:
                raise ConflictError('A tarefa foi alterada ou não existe mais. Reabra a demanda.')
        return self.get_detail(management_id, area_id)

    def delete_task(self, management_id, task_id, area_id, row_version_value):
        row_version = parse_row_version(row_version_value)
        with self.engine.begin() as connection:
            deleted = self.repository.delete_task(
                connection, management_id, task_id, area_id, row_version
            )
            if not deleted:
                raise ConflictError('A tarefa foi alterada ou não existe mais. Reabra a demanda.')
        return self.get_detail(management_id, area_id)

    def _validate_task_responsible(self, connection, task, area_id):
        responsible_id = task['responsibleId']
        if responsible_id and not self.repository.responsible_belongs_to_area(
            connection, responsible_id, area_id
        ):
            raise ValidationError('O responsável da tarefa deve ser um usuário ativo da área.')
