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

# Somente estes campos operacionais podem ser alterados pela API.
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
