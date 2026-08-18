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

# Whitelist que relaciona o campo da API à coluna no banco.
MANAGEMENT_FIELDS = {
    'status': 'status',
    'deadline': 'deadline',
    'startDate': 'startDate',
    'estimatedHours': 'estimatedHours',
    'dailyHours': 'dailyHours',
    'completedHours': 'completedHours',
    'difficulty': 'difficulty',
    'observations': 'observations',
    'responsibleId': 'responsibleId'
}


class DemandManagementError(Exception):
    status_code = 400


class ValidationError(DemandManagementError):
    pass


class NotFoundError(DemandManagementError):
    status_code = 404


class ConflictError(DemandManagementError):
    status_code = 409


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


def validate_management_change(field, value):
    if field not in MANAGEMENT_FIELDS:
        raise ValidationError('Campo de gerenciamento inválido.')

    if field == 'status':
        if value not in STATUS_OPTIONS:
            raise ValidationError('Status inválido.')
        return value
    if field == 'difficulty':
        if value in (None, ''):
            return None
        if value not in DIFFICULTY_OPTIONS:
            raise ValidationError('Dificuldade inválida.')
        return value
    if field in ('deadline', 'startDate'):
        return _optional_date(value)
    if field in ('estimatedHours', 'dailyHours', 'completedHours'):
        return _optional_hours(value)
    if field == 'observations':
        return _optional_text(value, 4000)
    if field == 'responsibleId':
        return _optional_text(value, 100)

    raise ValidationError('Campo de gerenciamento inválido.')


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
        'deadline': _optional_date(payload.get('deadline')),
        'observations': _optional_text(payload.get('observations'), 2000),
        'completed': completed
    }


def parse_row_version(value):
    if not isinstance(value, str):
        raise ValidationError('Versão do registro não informada.')
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise ValidationError('Versão do registro inválida.') from error


def validate_review_approval(payload):
    if not isinstance(payload, dict):
        raise ValidationError('Dados da aprovação inválidos.')
    deadline = _optional_date(payload.get('deadline'))
    if deadline is None:
        raise ValidationError('Informe o prazo da demanda.')
    return deadline


def validate_review_decline(payload):
    if not isinstance(payload, dict):
        raise ValidationError('Dados da recusa inválidos.')
    reason = _optional_text(payload.get('reason'), 4000)
    if not reason:
        raise ValidationError('Informe o motivo da recusa.')
    return reason
