import calendar
from datetime import date, datetime, timedelta
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
        result['tasks'] = self._serialize_tasks(tasks)
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
        if task['recurrenceAction']:
            raise ValidationError('Ação de recorrência inválida para uma nova atividade.')
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
            current_task = self.repository.get_task(
                connection, management_id, task_id, area_id, lock=True
            )
            if not current_task:
                raise ConflictError(
                    'A tarefa foi alterada ou não existe mais. Reabra a demanda.'
                )
            self._validate_task_responsible(connection, task, area_id)
            has_later_task = self.repository.recurrence_has_later_task(
                connection,
                current_task['recurrenceGroupId'],
                current_task['recurrenceSequence']
            )
            self._prepare_task_recurrence(task, current_task, has_later_task)
            updated = self.repository.update_task(
                connection, management_id, task_id, area_id, task, row_version
            )
            if not updated:
                raise ConflictError('A tarefa foi alterada ou não existe mais. Reabra a demanda.')
            updated_task = self.repository.get_task(
                connection, management_id, task_id, area_id, lock=True
            )
            should_create_next = (
                updated_task['completedAt'] is not None
                and updated_task['recurrenceStatus'] == 'active'
                and not has_later_task
                and (
                    current_task['completedAt'] is None
                    or current_task['recurrenceGroupId'] is None
                    or task['recurrenceAction'] == 'resume'
                )
            )
            if should_create_next:
                anchor_day = self.repository.get_recurrence_anchor_day(
                    connection, updated_task['recurrenceGroupId']
                )
                next_occurrence = self._next_task_occurrence(
                    updated_task, anchor_day
                )
                if next_occurrence is None:
                    self.repository.end_task_recurrence(connection, task_id)
                else:
                    next_deadline, next_sequence = next_occurrence
                    created = self.repository.create_next_recurring_task(
                        connection,
                        updated_task,
                        next_deadline,
                        next_sequence,
                        user_id
                    )
                    if not created:
                        raise ConflictError(
                            'A próxima ocorrência já foi criada. Reabra a demanda.'
                        )
        return self.get_detail(management_id, area_id, user_id)

    def delete_task(self, management_id, task_id, area_id, row_version_value, user_id):
        row_version = parse_row_version(row_version_value)
        with self.engine.begin() as connection:
            self._require_owned_demand(
                connection, management_id, area_id, user_id, lock=True
            )
            current_task = self.repository.get_task(
                connection, management_id, task_id, area_id, lock=True
            )
            if not current_task:
                raise ConflictError(
                    'A tarefa foi alterada ou não existe mais. Reabra a demanda.'
                )
            has_later_task = self.repository.recurrence_has_later_task(
                connection,
                current_task['recurrenceGroupId'],
                current_task['recurrenceSequence']
            )
            if (
                current_task['recurrenceGroupId'] is not None
                and not has_later_task
                and current_task['recurrenceStatus'] != 'ended'
            ):
                raise ConflictError(
                    'Encerre a recorrência antes de excluir a ocorrência atual.'
                )
            if current_task['recurrenceGroupId'] is not None and not has_later_task:
                self.repository.end_recurrence_group(
                    connection, current_task['recurrenceGroupId']
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

    def _prepare_task_recurrence(self, task, current_task, has_later_task):
        action = task['recurrenceAction']
        current_type = current_task['recurrenceType']
        current_status = current_task['recurrenceStatus']
        current_group = current_task['recurrenceGroupId']

        if has_later_task:
            if action:
                raise ConflictError(
                    'A recorrência deve ser alterada na ocorrência mais recente.'
                )
            task['recurrenceType'] = current_type
            task['recurrenceEndDate'] = current_task['recurrenceEndDate']
            task['recurrenceMaxOccurrences'] = current_task['recurrenceMaxOccurrences']
            task['recurrenceStatus'] = current_status
            task['skipNextOccurrence'] = bool(current_task['skipNextOccurrence'])
            return

        if current_group is not None and task['recurrenceType'] is None:
            task['recurrenceType'] = current_type
            task['recurrenceEndDate'] = current_task['recurrenceEndDate']
            task['recurrenceMaxOccurrences'] = current_task['recurrenceMaxOccurrences']
            if not action:
                task['recurrenceStatus'] = 'ended'
                task['skipNextOccurrence'] = bool(current_task['skipNextOccurrence'])
                return

        if task['recurrenceType'] is None:
            if action:
                raise ConflictError('Esta atividade não possui recorrência.')
            task['recurrenceStatus'] = None
            task['skipNextOccurrence'] = False
            return

        status = current_status or 'active'
        skip_next = bool(current_task['skipNextOccurrence'])
        if action == 'pause':
            if status != 'active':
                raise ConflictError('Somente uma recorrência ativa pode ser pausada.')
            status = 'paused'
        elif action == 'resume':
            if status != 'paused':
                raise ConflictError('Somente uma recorrência pausada pode ser retomada.')
            status = 'active'
        elif action == 'end':
            if status == 'ended':
                raise ConflictError('Esta recorrência já foi encerrada.')
            status = 'ended'
        elif action == 'skip':
            if status != 'active':
                raise ConflictError('Somente uma recorrência ativa pode pular a próxima ocorrência.')
            if skip_next:
                raise ConflictError('A próxima ocorrência já está marcada para ser pulada.')
            skip_next = True

        task['recurrenceStatus'] = status
        task['skipNextOccurrence'] = skip_next

    def _next_task_occurrence(self, task, anchor_day):
        deadline = task['deadline']
        if isinstance(deadline, datetime):
            deadline = deadline.date()
        if deadline is None:
            return None

        periods = 2 if task['skipNextOccurrence'] else 1
        next_deadline = deadline
        next_sequence = (task['recurrenceSequence'] or 1)
        for _ in range(periods):
            next_deadline = self._advance_recurrence_date(
                next_deadline, task['recurrenceType'], anchor_day
            )
            next_sequence += 1

        while next_deadline <= date.today():
            next_deadline = self._advance_recurrence_date(
                next_deadline, task['recurrenceType'], anchor_day
            )
            next_sequence += 1

        end_date = task['recurrenceEndDate']
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        if end_date and next_deadline > end_date:
            return None

        max_occurrences = task['recurrenceMaxOccurrences']
        if max_occurrences and next_sequence > max_occurrences:
            return None
        return next_deadline, next_sequence

    @staticmethod
    def _advance_recurrence_date(current_date, recurrence_type, anchor_day=None):
        if recurrence_type == 'weekly':
            return current_date + timedelta(days=7)
        if recurrence_type == 'biweekly':
            return current_date + timedelta(days=14)
        if recurrence_type == 'monthly':
            month_index = current_date.month
            year = current_date.year + month_index // 12
            month = month_index % 12 + 1
            day = min(
                anchor_day or current_date.day,
                calendar.monthrange(year, month)[1]
            )
            return date(year, month, day)
        raise ValidationError('Frequência da recorrência inválida.')

    @staticmethod
    def _serialize_tasks(rows):
        tasks = [_serialize_row(row) for row in rows]
        groups = {}
        for task in tasks:
            group_id = task.get('recurrenceGroupId')
            if group_id is None:
                task['isRecurrenceCurrent'] = False
                continue
            group_id = str(group_id)
            task['recurrenceGroupId'] = group_id
            groups.setdefault(group_id, []).append(task)

        for group_tasks in groups.values():
            current = max(
                group_tasks,
                key=lambda item: (
                    item.get('recurrenceSequence') or 0,
                    item.get('taskId') or 0
                )
            )
            completed = [item for item in group_tasks if item.get('completedAt')]
            on_time = [
                item for item in completed
                if item.get('deadline')
                and str(item['completedAt'])[:10] <= str(item['deadline'])[:10]
            ]
            summary = {
                'totalOccurrences': len(group_tasks),
                'completedOccurrences': len(completed),
                'onTimeOccurrences': len(on_time)
            }
            for task in group_tasks:
                task['isRecurrenceCurrent'] = task is current
                task['recurrenceHistory'] = summary
        return tasks

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
