from datetime import datetime
from decimal import Decimal, InvalidOperation


AREA_CONFIG = {
    'Transformação Digital': {
        'id': 1,
        'role': 'Transformação Digital'
    }
}

DEFAULT_AREA = 'Transformação Digital'

STATUS_OPTIONS = (
    'A Fazer',
    'Em Andamento',
    'Pausado',
    'Concluído',
    'Cancelado'
)

DIFFICULTY_OPTIONS = ('Baixa', 'Média', 'Alta')

PRIORITY_OPTIONS = tuple(range(1, 11))

DEMAND_TYPE_OPTIONS = ('atividade', 'projeto', 'melhoria', 'erro')

ACTIVITY_RECURRENCE_OPTIONS = ('daily', 'weekly', 'monthly')

ACTIVITY_RECURRENCE_ACTIONS = ('end',)

# Whitelist que relaciona o campo da API à coluna no banco.
MANAGEMENT_FIELDS = {
    'deadline': 'deadline',
    'estimatedHours': 'estimatedHours',
    'dailyHours': 'dailyHours',
    'completedHours': 'completedHours',
    'difficulty': 'difficulty',
    'priority': 'priority',
    'observations': 'observations',
    'responsibleId': 'responsibleId'
}

STATUS_TRANSITIONS = {
    'start': {'from': ('A Fazer',), 'to': 'Em Andamento'},
    'pause': {'from': ('Em Andamento',), 'to': 'Pausado'},
    'resume': {'from': ('Pausado',), 'to': 'Em Andamento'},
    'complete': {'from': ('Em Andamento',), 'to': 'Concluído'},
    'cancel': {'from': ('A Fazer', 'Em Andamento', 'Pausado'), 'to': 'Cancelado'},
    'reopen': {'from': ('Concluído',), 'to': 'Em Andamento'}
}

# Estes campos existem somente em demandas criadas no gerenciador.
DIRECT_DEMAND_FIELDS = {
    'title': 'title',
    'initialDescription': 'initialDescription',
    'assumptions': 'assumptions',
    'actualProblems': 'actualProblems',
    'benefits': 'benefits'
}


class DemandManagementError(Exception):
    status_code = 400


class ValidationError(DemandManagementError):
    pass


class NotFoundError(DemandManagementError):
    status_code = 404


class ConflictError(DemandManagementError):
    status_code = 409


class ForbiddenError(DemandManagementError):
    status_code = 403


def _optional_text(value, max_length):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if len(value) > max_length:
        raise ValidationError(f'O texto deve ter no máximo {max_length} caracteres.')
    return value


def _optional_date(value):
    value = _optional_text(value, 10)
    if value is None:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError as error:
        raise ValidationError('A data informada é inválida.') from error


def _optional_hours(value):
    if value in (None, ''):
        return None
    try:
        hours = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ValidationError('A quantidade de horas é inválida.') from error
    if hours < 0 or hours > Decimal('99999.99'):
        raise ValidationError('As horas devem estar entre 0 e 99999,99.')
    return hours.quantize(Decimal('0.01'))


def _optional_positive_integer(value, field_label, maximum=1000):
    if value in (None, ''):
        return None
    if isinstance(value, bool):
        raise ValidationError(f'{field_label} deve ser um número inteiro.')
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise ValidationError(f'{field_label} deve ser um número inteiro.') from error
    if str(value).strip() != str(number) or number < 1 or number > maximum:
        raise ValidationError(
            f'{field_label} deve estar entre 1 e {maximum}.'
        )
    return number


def validate_management_change(field, value):
    if field in DIRECT_DEMAND_FIELDS:
        if field == 'title':
            title = _optional_text(value, 250)
            if not title:
                raise ValidationError('Informe o título da demanda.')
            return title
        if field == 'initialDescription':
            description = _optional_text(value, 4000)
            if not description:
                raise ValidationError('Informe a descrição da demanda.')
            return description
        return _optional_text(value, 4000)

    if field not in MANAGEMENT_FIELDS:
        raise ValidationError('Campo de gerenciamento inválido.')

    if field == 'difficulty':
        if value in (None, ''):
            return None
        if value not in DIFFICULTY_OPTIONS:
            raise ValidationError('Dificuldade inválida.')
        return value
    if field == 'priority':
        return _optional_positive_integer(value, 'A prioridade', maximum=10)
    if field == 'deadline':
        return _optional_date(value)
    if field in ('estimatedHours', 'dailyHours', 'completedHours'):
        return _optional_hours(value)
    if field == 'observations':
        return _optional_text(value, 4000)
    if field == 'responsibleId':
        return _optional_text(value, 100)

    raise ValidationError('Campo de gerenciamento inválido.')


def validate_personal_demand(payload):
    if not isinstance(payload, dict):
        raise ValidationError('Dados da demanda inválidos.')

    # Demandas abertas diretamente no gerenciador são sempre atividades.
    requested_type = payload.get('demandType')
    if requested_type not in (None, '', 'atividade'):
        raise ValidationError(
            'Somente atividades podem ser criadas diretamente no gerenciador.'
        )

    title = _optional_text(payload.get('title'), 250)
    description = _optional_text(payload.get('initialDescription'), 4000)
    if not title:
        raise ValidationError('Informe o título da demanda.')
    if not description:
        raise ValidationError('Informe a descrição da demanda.')

    recurrence_type = _optional_text(payload.get('recurrenceType'), 20)
    if recurrence_type and recurrence_type not in ACTIVITY_RECURRENCE_OPTIONS:
        raise ValidationError('Frequência da recorrência inválida.')
    recurrence_max_occurrences = _optional_positive_integer(
        payload.get('recurrenceMaxOccurrences'),
        'A quantidade de ocorrências'
    )

    return {
        'demandType': 'atividade',
        'title': title,
        'initialDescription': description,
        'assumptions': None,
        'actualProblems': None,
        'benefits': None,
        'status': 'A Fazer',
        # O primeiro prazo pertence ao ato de iniciar a demanda.
        'deadline': None,
        'startDate': None,
        'estimatedHours': validate_management_change('estimatedHours', payload.get('estimatedHours')),
        'dailyHours': validate_management_change('dailyHours', payload.get('dailyHours')),
        'completedHours': validate_management_change('completedHours', payload.get('completedHours')),
        'difficulty': validate_management_change('difficulty', payload.get('difficulty')),
        'observations': validate_management_change('observations', payload.get('observations')),
        'recurrenceType': recurrence_type,
        'recurrenceMaxOccurrences': recurrence_max_occurrences if recurrence_type else None
    }


def validate_task(payload):
    if not isinstance(payload, dict):
        raise ValidationError('Dados da tarefa inválidos.')

    description = _optional_text(payload.get('description'), 1000)
    if not description:
        raise ValidationError('Informe a descrição da tarefa.')

    completed = payload.get('completed', False)
    if not isinstance(completed, bool):
        raise ValidationError('O estado da tarefa é inválido.')

    return {
        'description': description,
        'responsibleId': _optional_text(payload.get('responsibleId'), 100),
        'priority': _optional_positive_integer(
            payload.get('priority'), 'A prioridade', maximum=10
        ),
        'deadline': _optional_date(payload.get('deadline')),
        'observations': _optional_text(payload.get('observations'), 2000),
        'completed': completed
    }


def validate_activity_recurrence(payload):
    if not isinstance(payload, dict):
        raise ValidationError('Dados da recorrência inválidos.')

    recurrence_type = _optional_text(payload.get('recurrenceType'), 20)
    if recurrence_type not in ACTIVITY_RECURRENCE_OPTIONS:
        raise ValidationError('Frequência da recorrência inválida.')
    recurrence_max_occurrences = _optional_positive_integer(
        payload.get('recurrenceMaxOccurrences'),
        'A quantidade de ocorrências'
    )
    recurrence_action = _optional_text(payload.get('recurrenceAction'), 20)
    if recurrence_action and recurrence_action not in ACTIVITY_RECURRENCE_ACTIONS:
        raise ValidationError('Ação da recorrência inválida.')

    return {
        'recurrenceType': recurrence_type,
        'recurrenceMaxOccurrences': recurrence_max_occurrences,
        'recurrenceAction': recurrence_action
    }


def validate_start_schedule(
    payload, deadline_required=True, business_days_only=False
):
    if not isinstance(payload, dict):
        raise ValidationError('Dados do agendamento inválidos.')

    action = _optional_text(payload.get('scheduleAction'), 20)
    if action not in (None, 'cancel'):
        raise ValidationError('Ação de agendamento inválida.')
    if action == 'cancel':
        return {
            'scheduledStartAt': None,
            'scheduledDeadlineDays': None,
            'rowVersion': parse_row_version(payload.get('rowVersion'))
        }

    start_value = _optional_text(payload.get('scheduledStartAt'), 30)
    if not start_value:
        raise ValidationError('Informe a data de início.')
    scheduled_date = _optional_date(start_value)
    if scheduled_date <= datetime.now().date():
        raise ValidationError('A data de início deve estar no futuro.')
    if business_days_only and scheduled_date.weekday() >= 5:
        raise ValidationError(
            'Atividades devem ser agendadas de segunda a sexta-feira.'
        )
    scheduled_start = datetime.combine(
        scheduled_date, datetime.min.time()
    ).replace(minute=1)

    deadline = _optional_date(payload.get('deadline'))
    if deadline_required and deadline is None:
        raise ValidationError('Informe o prazo que a demanda terá ao iniciar.')
    if deadline is not None and deadline < scheduled_date:
        raise ValidationError('O prazo não pode ser anterior ao início agendado.')

    return {
        'scheduledStartAt': scheduled_start,
        'scheduledDeadlineDays': (
            (deadline - scheduled_date).days if deadline is not None else None
        ),
        'deadline': deadline,
        'rowVersion': parse_row_version(payload.get('rowVersion'))
    }


def parse_row_version(value):
    if not isinstance(value, str):
        raise ValidationError('Versão do registro não informada.')
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise ValidationError('Versão do registro inválida.') from error


def validate_deadline_reason(payload):
    if not isinstance(payload, dict):
        raise ValidationError('Dados da alteração inválidos.')
    reason = _optional_text(payload.get('reason'), 4000)
    if not reason:
        raise ValidationError('Informe a justificativa da alteração do prazo.')
    return reason


def validate_review_approval(payload):
    if not isinstance(payload, dict):
        raise ValidationError('Dados da aprovação inválidos.')
    responsible_id = _optional_text(payload.get('responsibleId'), 100)
    if not responsible_id:
        raise ValidationError('Selecione o responsável pela demanda.')
    return responsible_id


def validate_review_decline(payload):
    if not isinstance(payload, dict):
        raise ValidationError('Dados da recusa inválidos.')
    reason = _optional_text(payload.get('reason'), 4000)
    if not reason:
        raise ValidationError('Informe o motivo da recusa.')
    return reason


def validate_status_transition(current_status, payload, deadline_required=True):
    if not isinstance(payload, dict):
        raise ValidationError('Dados da alteração de status inválidos.')

    action = _optional_text(payload.get('action'), 20)
    transition = STATUS_TRANSITIONS.get(action)
    if not transition or current_status not in transition['from']:
        raise ConflictError('Esta ação não está disponível para o status atual da demanda.')

    deadline = None
    if action in ('start', 'reopen'):
        deadline = _optional_date(payload.get('deadline'))
        if deadline_required and deadline is None:
            raise ValidationError('Informe o prazo da demanda.')

    reason = None
    expected_return = None
    if action in ('pause', 'cancel', 'reopen'):
        reason = _optional_text(payload.get('reason'), 4000)
        if not reason:
            raise ValidationError('Informe a justificativa desta alteração.')

    if action == 'pause':
        expected_return = _optional_date(payload.get('expectedReturn'))
        if expected_return is None:
            raise ValidationError('Informe a previsão para retomar a demanda.')

    return {
        'action': action,
        'targetStatus': transition['to'],
        'deadline': deadline,
        'reason': reason,
        'expectedReturn': expected_return,
        'rowVersion': parse_row_version(payload.get('rowVersion'))
    }

# V4
