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
