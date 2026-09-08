DEMAND_TYPES = ('melhoria', 'projeto', 'erro')
URGENCY_OPTIONS = ('Alta', 'Média', 'Baixa')


class DemandRequestsError(Exception):
    status_code = 400


class ValidationError(DemandRequestsError):
    pass


class NotFoundError(DemandRequestsError):
    status_code = 404


class ConflictError(DemandRequestsError):
    status_code = 409


def _required_text(data, key, label, max_length):
    raw_value = data.get(key, '')
    value = '' if raw_value is None else str(raw_value).strip()
    if not value:
        raise ValidationError(f'Informe {label}.')
    if len(value) > max_length:
        raise ValidationError(f'{label.capitalize()} deve ter no máximo {max_length} caracteres.')
    return value


def _optional_user_id(data, key):
    raw_value = data.get(key, '')
    value = '' if raw_value is None else str(raw_value).strip()
    if len(value) > 20:
        raise ValidationError('Contribuinte inválido.')
    return value or None


def validate_new_request(data):
    if not hasattr(data, 'get'):
        raise ValidationError('Dados da solicitação inválidos.')

    demand_type = str(data.get('demandType', '')).strip()
    urgency = str(data.get('options', '')).strip()
    if demand_type not in DEMAND_TYPES:
        raise ValidationError('Tipo de demanda inválido ou não informado.')
    if urgency not in URGENCY_OPTIONS:
        raise ValidationError('Nível de urgência inválido ou não informado.')

    result = {
        'demandType': demand_type,
        'title': _required_text(data, 'titulo', 'o título da demanda', 250),
        'initialDescription': _required_text(
            data, 'objetivo', 'a descrição ou objetivo da demanda', 4000
        ),
        'urgency': urgency,
        'contributorId': _optional_user_id(data, 'contributorId'),
        'assumptions': None,
        'actualProblems': None,
        'benefits': None
    }

    if demand_type != 'erro':
        result['assumptions'] = _required_text(data, 'premissas', 'as premissas', 4000)
        result['actualProblems'] = _required_text(
            data, 'problemas', 'os problemas atuais', 4000
        )
        result['benefits'] = _required_text(
            data, 'beneficios', 'os ganhos esperados', 4000
        )

    return result
