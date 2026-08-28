from datetime import date, datetime
from decimal import Decimal

from .domain import (
    DEMAND_TYPE_OPTIONS,
    DIFFICULTY_OPTIONS,
    DIRECT_DEMAND_FIELDS,
    STATUS_OPTIONS,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    parse_row_version,
    validate_deadline_reason,
    validate_management_change,
    validate_personal_demand,
    validate_review_approval,
    validate_review_decline,
    validate_status_transition,
    validate_task
)
from .integration import sync_approved_request


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
    def __init__(self, engine, repository, attachment_storage, review_notifier=None):
        self.engine = engine
        self.repository = repository
        self.attachment_storage = attachment_storage
        self.review_notifier = review_notifier

    def list_board(self, area_id, user_id):
        with self.engine.connect() as connection:
            demands = [
                self._serialize_demand(row, user_id)
                for row in self.repository.list_demands(connection, area_id)
            ]
            responsibles = [_serialize_row(row) for row in self.repository.list_responsibles(connection, area_id)]
        return {
            'demands': demands,
            'responsibles': responsibles,
            'options': {
                'status': list(STATUS_OPTIONS),
                'difficulty': list(DIFFICULTY_OPTIONS),
                'type': list(DEMAND_TYPE_OPTIONS)
            }
        }

    def list_review_requests(self, area_id):
        with self.engine.connect() as connection:
            rows = self.repository.list_review_requests(connection, area_id)
        return {'requests': [self._serialize_review(row) for row in rows]}

    def get_review_request(self, request_id, area_id):
        with self.engine.connect() as connection:
            row = self.repository.get_review_request(connection, request_id, area_id)
        if not row:
            raise NotFoundError('Solicitação não encontrada.')
        return self._serialize_review(row, include_attachments=True)

    def get_request_attachment(self, request_id, attachment_index, area_id):
        with self.engine.connect() as connection:
            row = self.repository.get_review_request(connection, request_id, area_id)
        if not row:
            raise NotFoundError('Solicitação não encontrada.')

        detail = self._serialize_review(row, include_attachments=True)
        attachment = next((
            item for item in detail['attachments']
            if item['index'] == attachment_index
        ), None)
        if not attachment:
            raise NotFoundError('Anexo não encontrado.')
        return self.attachment_storage.request_directory(request_id), attachment['name']

    def approve_review_request(self, request_id, area_id, payload, reviewer, area_name):
        responsible_id = validate_review_approval(payload)
        with self.engine.begin() as connection:
            review = self._pending_review(connection, request_id, area_id, reviewer['id'])
            responsible = self.repository.get_responsible(
                connection, responsible_id, area_id
            )
            if not responsible:
                raise ValidationError('O responsável deve ser um usuário ativo da área.')
            updated = self.repository.approve_review_request(
                connection, request_id, area_id, responsible_id
            )
            if not updated:
                raise ConflictError('A solicitação já foi analisada por outra pessoa.')

            # Cria o card na mesma transação e impede vínculos duplicados.
            sync_approved_request(connection, request_id)
            if self.review_notifier:
                self.review_notifier.approved(
                    review, dict(responsible), reviewer, area_name
                )

        return self.get_review_request(request_id, area_id)

    def decline_review_request(self, request_id, area_id, payload, reviewer, area_name):
        reason = validate_review_decline(payload)
        with self.engine.begin() as connection:
            review = self._pending_review(connection, request_id, area_id, reviewer['id'])
            updated = self.repository.decline_review_request(
                connection, request_id, area_id, reason, reviewer['id']
            )
            if not updated:
                raise ConflictError('A solicitação já foi analisada por outra pessoa.')
            if self.review_notifier:
                self.review_notifier.declined(review, reviewer, area_name, reason)

        return self.get_review_request(request_id, area_id)

    def get_detail(self, management_id, area_id, user_id):
        with self.engine.connect() as connection:
            demand = self.repository.get_demand(connection, management_id, area_id)
            if not demand:
                raise NotFoundError('Demanda não encontrada.')
            tasks = self.repository.list_tasks(connection, management_id, area_id)
            history = self.repository.list_history(
                connection, management_id, area_id
            )
        result = self._serialize_demand(demand, user_id, include_attachments=True)
        result['tasks'] = [_serialize_row(row) for row in tasks]
        result['history'] = [_serialize_row(row) for row in history]
        return result

    def create_personal_demand(self, area_id, payload, user_id):
        demand = validate_personal_demand(payload)
        with self.engine.begin() as connection:
            management_id = self.repository.create_personal_demand(
                connection, area_id, demand, user_id
            )
            if management_id is None:
                raise ConflictError('Não foi possível criar a demanda.')
        return self.get_detail(management_id, area_id, user_id)

    def update_demand(self, management_id, area_id, payload, actor, area_name):
        if not isinstance(payload, dict):
            raise ValidationError('Dados da alteração inválidos.')
        field = payload.get('field')
        value = validate_management_change(field, payload.get('value'))
        row_version = parse_row_version(payload.get('rowVersion'))
        user_id = actor['id']

        with self.engine.begin() as connection:
            current = self._require_owned_demand(
                connection,
                management_id,
                area_id,
                user_id,
                lock=True,
                allow_reassignment=field == 'responsibleId'
            )
            if field == 'deadline':
                if current['status'] == 'A Fazer':
                    raise ConflictError(
                        'O prazo inicial deve ser informado ao iniciar a demanda.'
                    )
                if current['status'] not in ('Em Andamento', 'Pausado'):
                    raise ConflictError(
                        'O prazo não pode ser alterado no status atual da demanda.'
                    )
                if value is None:
                    raise ValidationError('Informe o novo prazo da demanda.')

                current_deadline = current['deadline']
                if isinstance(current_deadline, datetime):
                    current_deadline = current_deadline.date()
                if current_deadline == value:
                    raise ValidationError('O prazo informado é igual ao prazo atual.')

                reason = validate_deadline_reason(payload)
                updated = self.repository.update_deadline(
                    connection,
                    management_id,
                    area_id,
                    value,
                    row_version
                )
                if updated and current['sourceRequestId'] is not None:
                    source_updated = self.repository.update_source_deadline(
                        connection, current['sourceRequestId'], value
                    )
                    if not source_updated:
                        raise ConflictError('A solicitação original não pôde ser atualizada.')
                if updated:
                    self.repository.insert_history(
                        connection,
                        management_id,
                        'deadline_changed',
                        actor,
                        previous_status=current['status'],
                        new_status=current['status'],
                        previous_deadline=current_deadline,
                        new_deadline=value,
                        reason=reason
                    )
                if (
                    updated
                    and self.review_notifier
                    and current['requesterEmail']
                ):
                    self.review_notifier.deadline_changed(
                        dict(current), actor, area_name,
                        current_deadline, value, reason
                    )
            elif field in DIRECT_DEMAND_FIELDS:
                updated = self.repository.update_direct_field(
                    connection, management_id, area_id, field, value,
                    row_version, user_id
                )
            else:
                if field == 'responsibleId':
                    if not value:
                        raise ValidationError('Selecione o novo responsável da demanda.')
                    if not self.repository.responsible_belongs_to_area(connection, value, area_id):
                        raise ValidationError('O responsável deve ser um usuário ativo da área.')
                updated = self.repository.update_field(
                    connection, management_id, area_id, field, value, row_version
                )

            if not updated:
                if field in DIRECT_DEMAND_FIELDS:
                    if current['sourceRequestId'] is not None:
                        raise ForbiddenError('Os dados da solicitação original são somente leitura.')
                raise ConflictError('A demanda foi alterada por outra pessoa. Atualize a tela e tente novamente.')
        return self.get_detail(management_id, area_id, user_id)

    def transition_status(self, management_id, area_id, payload, actor, area_name):
        with self.engine.begin() as connection:
            demand = self._require_owned_demand(
                connection, management_id, area_id, actor['id'], lock=True
            )

            transition = validate_status_transition(demand['status'], payload)
            updated = self.repository.transition_demand(
                connection,
                management_id,
                area_id,
                demand['status'],
                transition
            )
            if not updated:
                raise ConflictError(
                    'A demanda foi alterada por outra pessoa. Atualize a tela e tente novamente.'
                )

            if demand['sourceRequestId'] is not None:
                source_updated = self.repository.transition_source_request(
                    connection, demand['sourceRequestId'], transition
                )
                if not source_updated:
                    raise ConflictError('A solicitação original não pôde ser atualizada.')

            previous_deadline = demand['deadline']
            if isinstance(previous_deadline, datetime):
                previous_deadline = previous_deadline.date()
            self.repository.insert_history(
                connection,
                management_id,
                f"status_{transition['action']}",
                actor,
                previous_status=demand['status'],
                new_status=transition['targetStatus'],
                previous_deadline=previous_deadline,
                new_deadline=transition['deadline'] or previous_deadline,
                reason=transition['reason'],
                expected_return=transition['expectedReturn']
            )
            if (
                demand['sourceRequestId'] is not None
                and self.review_notifier
                and demand['requesterEmail']
            ):
                self.review_notifier.status_changed(
                    dict(demand), actor, area_name, transition
                )

        return self.get_detail(management_id, area_id, actor['id'])

    def create_task(self, management_id, area_id, payload, created_by):
        task = validate_task(payload)
        with self.engine.begin() as connection:
            self._require_owned_demand(
                connection, management_id, area_id, created_by, lock=True
            )
            self._validate_task_responsible(connection, task, area_id)
            task_id = self.repository.create_task(
                connection, management_id, area_id, task, created_by
            )
            if task_id is None:
                raise NotFoundError('Demanda não encontrada.')
        return self.get_detail(management_id, area_id, created_by)

    def update_task(self, management_id, task_id, area_id, payload, user_id):
        task = validate_task(payload)
        row_version = parse_row_version(payload.get('rowVersion'))
        with self.engine.begin() as connection:
            self._require_owned_demand(
                connection, management_id, area_id, user_id, lock=True
            )
            self._validate_task_responsible(connection, task, area_id)
            updated = self.repository.update_task(
                connection, management_id, task_id, area_id, task, row_version
            )
            if not updated:
                raise ConflictError('A tarefa foi alterada ou não existe mais. Reabra a demanda.')
        return self.get_detail(management_id, area_id, user_id)

    def delete_task(self, management_id, task_id, area_id, row_version_value, user_id):
        row_version = parse_row_version(row_version_value)
        with self.engine.begin() as connection:
            self._require_owned_demand(
                connection, management_id, area_id, user_id, lock=True
            )
            deleted = self.repository.delete_task(
                connection, management_id, task_id, area_id, row_version
            )
            if not deleted:
                raise ConflictError('A tarefa foi alterada ou não existe mais. Reabra a demanda.')
        return self.get_detail(management_id, area_id, user_id)

    def _validate_task_responsible(self, connection, task, area_id):
        responsible_id = task['responsibleId']
        if responsible_id and not self.repository.responsible_belongs_to_area(
            connection, responsible_id, area_id
        ):
            raise ValidationError('O responsável da tarefa deve ser um usuário ativo da área.')

    def _require_owned_demand(
        self, connection, management_id, area_id, user_id, lock=False,
        allow_reassignment=False
    ):
        demand = self.repository.get_demand(
            connection, management_id, area_id, lock=lock
        )
        if not demand:
            raise NotFoundError('Demanda não encontrada.')
        if (
            str(demand['responsibleId']) != str(user_id)
            and not allow_reassignment
        ):
            raise ForbiddenError(
                'Somente o responsável atual pode editar esta demanda.'
            )
        return demand

    def _pending_review(self, connection, request_id, area_id, reviewer_id):
        review = self.repository.get_review_request(
            connection, request_id, area_id, lock=True
        )
        if not review:
            raise NotFoundError('Solicitação não encontrada.')
        if review['status'] != 0:
            raise ConflictError('Esta solicitação já foi analisada.')
        if review['responsibleId'] and str(review['responsibleId']) != str(reviewer_id):
            raise ConflictError('Esta solicitação está atribuída a outro responsável.')
        return dict(review)

    def _serialize_demand(self, row, user_id, include_attachments=False):
        result = _serialize_row(row)
        images = result.pop('images', '') or ''
        result.pop('requesterEmail', None)
        if include_attachments:
            result['attachments'] = self._serialize_attachments(images)
        result.pop('directCreatorId', None)
        is_direct = result.get('sourceRequestId') is None
        result['isDirectDemand'] = is_direct
        result['isOwnedByCurrentUser'] = (
            str(result.get('responsibleId')) == str(user_id)
        )
        return result

    def _serialize_review(self, row, include_attachments=False):
        result = _serialize_row(row)
        images = result.pop('images', '') or ''
        if include_attachments:
            result['attachments'] = self._serialize_attachments(images)
        # O e-mail é necessário somente no servidor para enviar a notificação.
        result.pop('requesterEmail', None)
        return result

    def _serialize_attachments(self, images):
        stored_names = [name for name in images.split('||') if name]
        return [
            {'index': index, 'name': name}
            for index, name in enumerate(stored_names)
            if self.attachment_storage.is_safe_stored_name(name)
        ]
