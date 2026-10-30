"""Validação dos dados do controle QSB, sem dependências de Flask ou banco."""

from datetime import date, time, timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID


OCCURRENCE_TYPES = (
    'Interno', 'Cliente (Não Formal)', 'Fornecedor',
    'Cliente (Formal)', 'Cliente (Logística)',
)
PRODUCT_FAMILIES = (
    'QR', 'QR + MESA', 'AO', 'SP 3° EIXO', 'SP SR', 'SP - Suporte',
    'EE', 'PR', 'AL', 'VT', 'EA', 'PE', 'EC',
)
CAMPINAS_WORKCENTERS = (
    'M101-Montagem Articulação De Onibus',
    'M102-Montagem Trava De Quinta Roda',
    'S101-Solda Robotizada Articulação De Onibus',
)
STOP_FIELDS = ('stop_time', 'stop_reason', 'stop_minutes', 'stop_count')
BASE_FIELDS = (
    'type', 'typeDesc', 'description', 'workCenter', 'prodCode', 'repeat',
    'text1', 'text2', 'text3', 'imgOK', 'imgNOK', 'openDate', 'prodFamily',
    'id', 'shift', 'unit',
)
EXTRA_FIELDS = (*STOP_FIELDS, 'location_detail', 'publish_qsb')
SNAPSHOT_FIELDS = (*BASE_FIELDS, *EXTRA_FIELDS, 'deleted_at')


class QualityControlError(Exception):
    def __init__(self, message, status_code=400, field=None):
        super().__init__(message)
        self.status_code = status_code
        self.field = field


def is_flag_set(value):
    if isinstance(value, (int, float, Decimal)):
        return value == 1
    return str(value).strip().casefold() in ('1', 'true')


def required_text(form, name, label):
    value = str(form.get(name, '') or '').strip()
    if not value or value.casefold() in ('aguardando seleção...', 'selecione uma opção...'):
        raise QualityControlError(f'Informe {label}.', field=name)
    if '\x00' in value:
        raise QualityControlError(f'Valor inválido em {label}.', field=name)
    return value


def is_legacy(entry):
    return entry is not None and all(entry.get(field) is None for field in STOP_FIELDS)


def submission_key(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise QualityControlError('Identificação do cadastro inválida. Atualize a página.')


def validate_stop_reason_name(value):
    name = ' '.join(str(value or '').split())
    if not name:
        raise QualityControlError('Informe o motivo da parada.', field='name')
    if len(name) > 150 or '\x00' in name:
        raise QualityControlError('O motivo deve ter até 150 caracteres e não conter caracteres inválidos.', field='name')
    return name


def entry_period(date_from=None, date_until=None):
    if date_from is None and date_until is None:
        today = date.today()
        return today - timedelta(days=14), today
    dates = []
    for field, raw in (('date_from', date_from), ('date_until', date_until)):
        if not raw:
            dates.append(None)
            continue
        try:
            value = date.fromisoformat(raw)
            if value.isoformat() != raw:
                raise ValueError
        except (ValueError, TypeError):
            raise QualityControlError('Informe um período com datas válidas.', field=field)
        dates.append(value)
    start, end = dates
    if start and end and start > end:
        raise QualityControlError('A data inicial não pode ser posterior à final.', field='date_from')
    return start, end


def validate_entry(form, caxias_locations, workcenters, previous=None, *, stop_reasons):
    try:
        unit = int(form.get('unidade', ''))
    except (TypeError, ValueError):
        unit = -1
    if unit not in (0, 1):
        raise QualityControlError('Selecione uma unidade válida.', field='unidade')

    occurrence_type = required_text(form, 'op_local_ocorr', 'o local da ocorrência')
    if occurrence_type not in OCCURRENCE_TYPES:
        raise QualityControlError('Local da ocorrência inválido.', field='op_local_ocorr')
    location = required_text(form, 'op_local_info', 'o local específico')
    if unit == 0:
        locations = {item.casefold(): item for item in caxias_locations}
        canonical = locations.get(location.casefold())
        unchanged = previous and int(previous['unit']) == unit and previous['typeDesc'] == location
        if canonical is None and not unchanged:
            raise QualityControlError('Selecione um local específico cadastrado.', field='op_local_info')
        location = canonical or location

    center = required_text(form, 'ct', 'o centro de trabalho')
    allowed_centers = CAMPINAS_WORKCENTERS if unit == 1 else workcenters
    unchanged_center = previous and int(previous['unit']) == unit and previous['workCenter'] == center
    if center not in allowed_centers and not unchanged_center:
        raise QualityControlError('Selecione um centro de trabalho da unidade.', field='ct')
    try:
        open_date = date.fromisoformat(str(form.get('op_date', '')))
    except ValueError:
        raise QualityControlError('Informe uma data válida.', field='op_date')

    shifts = [value for value in ('1', '2', '3') if f'turno{value}' in form]
    if 'NA' in form:
        if shifts:
            raise QualityControlError('Escolha turnos ou Não aplicável, sem combinar as opções.', field='NA')
        shifts = ['NA']
    if not shifts:
        raise QualityControlError('Selecione um turno ou Não aplicável.', field='turno1')
    for field in ('op_reincidente', 'publish_qsb'):
        if form.get(field) not in ('0', '1'):
            raise QualityControlError('Selecione Sim ou Não.', field=field)

    detail = str(form.get('location_detail', '') or '').strip()
    if len(detail) > 500 or '\x00' in detail:
        raise QualityControlError('Detalhamento do local deve ter até 500 caracteres.', field='location_detail')
    result = {
        'unit': unit, 'type': occurrence_type, 'typeDesc': location,
        'workCenter': center, 'prodCode': required_text(form, 'id_mater', 'o código do produto'),
        'prodFamily': required_text(form, 'op_familia', 'a família de produtos'),
        'description': required_text(form, 'op_problema', 'a descrição do problema'),
        'repeat': int(form['op_reincidente']),
        'text1': required_text(form, 'op_cont_1', 'o que foi feito'),
        'text2': required_text(form, 'op_cont_2', 'como foi feito'),
        'text3': required_text(form, 'op_cont_3', 'quem fez'),
        'openDate': open_date, 'shift': ','.join(shifts),
        'location_detail': detail, 'publish_qsb': int(form['publish_qsb']),
    }
    stop_values = {field: str(form.get(field, '') or '').strip() for field in STOP_FIELDS}
    # Um registro antigo pode ser corrigido sem inventar dados históricos de parada.
    if is_legacy(previous) and not any(stop_values.values()):
        result.update({field: None for field in STOP_FIELDS})
        return result
    for field, value in stop_values.items():
        if not value:
            raise QualityControlError('Preencha todos os dados da parada.', field=field)
    try:
        stop_time = time.fromisoformat(stop_values['stop_time'])
        if stop_time.second or stop_time.microsecond or stop_time.tzinfo:
            raise ValueError
    except ValueError:
        raise QualityControlError('Informe o horário no formato HH:MM.', field='stop_time')
    reason = stop_values['stop_reason']
    canonical_reason = {item.casefold(): item for item in stop_reasons}.get(reason.casefold())
    if canonical_reason is None and not (previous and previous.get('stop_reason') == reason):
        raise QualityControlError('Selecione um motivo de parada válido.', field='stop_reason')
    reason = canonical_reason or reason
    try:
        minutes = Decimal(stop_values['stop_minutes'].replace(',', '.'))
        if not minutes.is_finite() or minutes <= 0 or minutes > Decimal('9999999999.99'):
            raise InvalidOperation
        if minutes != minutes.quantize(Decimal('.01')):
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        raise QualityControlError('Informe o tempo total em minutos, positivo e com até duas casas decimais.', field='stop_minutes')
    try:
        numeric_count = Decimal(stop_values['stop_count'].replace(',', '.'))
        if not numeric_count.is_finite() or numeric_count != numeric_count.to_integral_value():
            raise InvalidOperation
        if numeric_count <= 0 or numeric_count > 2147483647:
            raise InvalidOperation
        count = int(numeric_count)
    except (InvalidOperation, ValueError):
        raise QualityControlError('Quantidade de paradas deve ser um número inteiro positivo.', field='stop_count')
    result.update(stop_time=stop_time, stop_reason=reason, stop_minutes=minutes, stop_count=count)
    return result
