"""Tela e API do Gerenciador de Demandas da Transformação Digital."""

import os
import secrets
from hmac import compare_digest
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_login import current_user
from sqlalchemy import text
from werkzeug.utils import secure_filename

from app.utils.db_utils import get_engine
from app.utils.permissions import get_permission, user_has_role


demand_management_bp = Blueprint('demand_management', __name__)

_AREAS = {
    'Transformação Digital': {
        'source_area_id': 1,
        'role': 'Transformação Digital',
    },
}

_STATUS_OPTIONS = {'todo', 'in_progress', 'paused', 'completed', 'cancelled'}
_DIFFICULTY_OPTIONS = {'low', 'medium', 'high'}
_UPDATABLE_FIELDS = {
    'responsibleUserId': 'responsibleUserId',
    'status': 'status',
    'deadline': 'deadline',
    'startDate': 'startDate',
    'estimatedHours': 'estimatedHours',
    'dailyHours': 'dailyHours',
    'actualHours': 'actualHours',
    'difficulty': 'difficulty',
    'observations': 'observations',
}
_MAX_OBSERVATIONS_LENGTH = 20000
_MAX_TASK_LENGTH = 2000
_MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
_ALLOWED_ATTACHMENT_EXTENSIONS = {
    'csv', 'doc', 'docx', 'gif', 'jpeg', 'jpg', 'pdf', 'png', 'ppt', 'pptx',
    'txt', 'webp', 'xls', 'xlsx', 'zip',
}
_UPLOAD_ROOT = Path(__file__).resolve().parents[2] / 'private_uploads' / 'demand_management'


def _is_admin_account():
    return str(getattr(current_user, 'admin', '')).strip().lower() in {'1', 'true'}


def _area_config():
    return _AREAS.get(request.args.get('area', '').strip())


def _can_access_area(config):
    roles = getattr(current_user, 'role', None) or []
    return _is_admin_account() or user_has_role(roles, config['role'])


@demand_management_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))

    if not get_permission('GENERAL').can() and not _is_admin_account():
        return abort(403)

    config = _area_config()
    if config is None:
        return abort(400, description='Área inválida ou não informada')

    if not _can_access_area(config):
        return abort(403)

    if request.method in {'POST', 'PATCH', 'DELETE'}:
        expected_token = session.get('demand_management_csrf')
        provided_token = request.headers.get('X-CSRF-Token', '')
        if not expected_token or not compare_digest(expected_token, provided_token):
            return jsonify({'ok': False, 'message': 'Sessão inválida. Recarregue a página e tente novamente.'}), 403


@demand_management_bp.after_request
def secure_management_response(response):
    response.headers['Cache-Control'] = 'no-store, private'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _row_to_dict(row):
    return {key: _json_value(value) for key, value in dict(row).items()}


def _api_error(message, status=400):
    return jsonify({'ok': False, 'message': message}), status


def _normalize_version(raw_version):
    if not isinstance(raw_version, str) or not raw_version.startswith('0x'):
        raise ValueError('Versão do registro ausente ou inválida.')
    try:
        return bytes.fromhex(raw_version[2:])
    except ValueError as exc:
        raise ValueError('Versão do registro inválida.') from exc


def _normalize_date(value, label):
    if value in (None, ''):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f'{label} deve estar no formato AAAA-MM-DD.') from exc


def _normalize_hours(value, label):
    if value in (None, ''):
        return None
    try:
        normalized = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'{label} deve ser um número válido.') from exc
    if normalized < 0 or normalized > Decimal('999999.99'):
        raise ValueError(f'{label} deve estar entre 0 e 999999,99.')
    return normalized.quantize(Decimal('0.01'))


def _role_pattern(config):
    return f'%"{config["role"]}"%'


def _is_assignable_user(cnnx, user_id, config):
    if not user_id:
        return False
    return cnnx.execute(
        text("""
            SELECT 1
            FROM JDT_USER_DETAILS
            WHERE id = :user_id
              AND active = 1
              AND generic = 0
              AND role LIKE :role_pattern
        """),
        {'user_id': user_id, 'role_pattern': _role_pattern(config)}
    ).first() is not None


def _fetch_users(cnnx, config):
    rows = cnnx.execute(
        text("""
            SELECT
                users.id,
                users.name,
                CASE
                    WHEN users.active = 1
                     AND users.generic = 0
                     AND users.role LIKE :role_pattern THEN 1
                    ELSE 0
                END AS assignable
            FROM JDT_USER_DETAILS AS users
            WHERE (
                users.active = 1
                AND users.generic = 0
                AND users.role LIKE :role_pattern
            ) OR users.id IN (
                SELECT management.responsibleUserId
                FROM JDT_DEMAND_MANAGEMENT AS management
                INNER JOIN JDT_REQUEST_IMPROVEMENTS_SMALL AS source
                    ON source.requestId = management.requestId
                WHERE source.areaId = :source_area_id
            )
            ORDER BY users.name
        """),
        {
            'role_pattern': _role_pattern(config),
            'source_area_id': config['source_area_id'],
        }
    ).mappings().all()
    return [_row_to_dict(row) for row in rows]


_MANAGEMENT_SELECT = """
    SELECT
        management.managementId,
        management.requestId,
        COALESCE(NULLIF(LTRIM(RTRIM(source.demandType)), ''), 'melhoria') AS demandType,
        source.title,
        source.info AS initialDescription,
        management.responsibleUserId,
        COALESCE(responsible.name, management.responsibleUserId) AS responsibleName,
        management.status,
        CONVERT(VARCHAR(10), management.deadline, 23) AS deadline,
        CONVERT(VARCHAR(10), management.startDate, 23) AS startDate,
        management.estimatedHours,
        management.dailyHours,
        management.actualHours,
        management.difficulty,
        management.observations,
        (SELECT COUNT(*)
         FROM JDT_DEMAND_MANAGEMENT_TASKS AS task
         WHERE task.managementId = management.managementId) AS taskTotal,
        (SELECT COUNT(*)
         FROM JDT_DEMAND_MANAGEMENT_TASKS AS task
         WHERE task.managementId = management.managementId
           AND task.completed = 1) AS taskCompleted,
        (SELECT COUNT(*)
         FROM JDT_DEMAND_MANAGEMENT_ATTACHMENTS AS attachment
         WHERE attachment.managementId = management.managementId) AS attachmentCount,
        CONVERT(VARCHAR(18), management.rowVersion, 1) AS version
    FROM JDT_DEMAND_MANAGEMENT AS management
    INNER JOIN JDT_REQUEST_IMPROVEMENTS_SMALL AS source
        ON source.requestId = management.requestId
    LEFT JOIN JDT_USER_DETAILS AS responsible
        ON responsible.id = management.responsibleUserId
"""


def _fetch_management(cnnx, management_id, config):
    row = cnnx.execute(
        text(_MANAGEMENT_SELECT + """
            WHERE management.managementId = :management_id
              AND source.areaId = :source_area_id
        """),
        {
            'management_id': management_id,
            'source_area_id': config['source_area_id'],
        }
    ).mappings().first()
    return _row_to_dict(row) if row else None


def _fetch_management_source_details(cnnx, management_id, config):
    row = cnnx.execute(
        text("""
            SELECT
                management.managementId,
                management.requestId,
                COALESCE(NULLIF(LTRIM(RTRIM(source.demandType)), ''), 'melhoria') AS demandType,
                source.title,
                source.info AS objective,
                source.assumptions,
                source.actualProblems,
                source.benefits,
                CASE
                    WHEN source.urgency = 'Imediata' THEN 'Alta'
                    ELSE source.urgency
                END AS urgency,
                CONVERT(VARCHAR(19), source.openDate, 126) AS requestDate,
                source.requesterId,
                COALESCE(requester.name, source.requesterId) AS requesterName
            FROM JDT_DEMAND_MANAGEMENT AS management
            INNER JOIN JDT_REQUEST_IMPROVEMENTS_SMALL AS source
                ON source.requestId = management.requestId
            LEFT JOIN JDT_USER_DETAILS AS requester
                ON requester.id = source.requesterId
            WHERE management.managementId = :management_id
              AND source.areaId = :source_area_id
        """),
        {
            'management_id': management_id,
            'source_area_id': config['source_area_id'],
        }
    ).mappings().first()
    return _row_to_dict(row) if row else None


def _fetch_tasks(cnnx, management_id):
    rows = cnnx.execute(
        text("""
            SELECT
                task.taskId,
                task.description,
                task.responsibleUserId,
                COALESCE(responsible.name, task.responsibleUserId) AS responsibleName,
                CONVERT(VARCHAR(10), task.deadline, 23) AS deadline,
                task.completed,
                task.sortOrder,
                CONVERT(VARCHAR(19), task.createdAt, 126) AS createdAt,
                CONVERT(VARCHAR(19), task.updatedAt, 126) AS updatedAt,
                CONVERT(VARCHAR(18), task.rowVersion, 1) AS version
            FROM JDT_DEMAND_MANAGEMENT_TASKS AS task
            LEFT JOIN JDT_USER_DETAILS AS responsible
                ON responsible.id = task.responsibleUserId
            WHERE task.managementId = :management_id
            ORDER BY task.completed, task.sortOrder, task.taskId
        """),
        {'management_id': management_id}
    ).mappings().all()
    return [_row_to_dict(row) for row in rows]


def _fetch_attachments(cnnx, management_id):
    rows = cnnx.execute(
        text("""
            SELECT
                attachment.attachmentId,
                attachment.originalName,
                attachment.mimeType,
                attachment.sizeBytes,
                attachment.uploadedBy,
                COALESCE(uploader.name, attachment.uploadedBy) AS uploadedByName,
                CONVERT(VARCHAR(19), attachment.uploadedAt, 126) AS uploadedAt
            FROM JDT_DEMAND_MANAGEMENT_ATTACHMENTS AS attachment
            LEFT JOIN JDT_USER_DETAILS AS uploader
                ON uploader.id = attachment.uploadedBy
            WHERE attachment.managementId = :management_id
            ORDER BY attachment.uploadedAt DESC
        """),
        {'management_id': management_id}
    ).mappings().all()
    return [_row_to_dict(row) for row in rows]


def _validate_management_value(cnnx, field, value, config):
    if field == 'responsibleUserId':
        normalized = str(value or '').strip()
        if not _is_assignable_user(cnnx, normalized, config):
            raise ValueError('O responsável selecionado não está ativo na área.')
        return normalized
    if field == 'status':
        normalized = str(value or '').strip()
        if normalized not in _STATUS_OPTIONS:
            raise ValueError('Status inválido.')
        return normalized
    if field in {'deadline', 'startDate'}:
        return _normalize_date(value, 'A data')
    if field in {'estimatedHours', 'dailyHours', 'actualHours'}:
        if field == 'actualHours' and value in (None, ''):
            return Decimal('0.00')
        return _normalize_hours(value, 'O tempo')
    if field == 'difficulty':
        if value in (None, ''):
            return None
        normalized = str(value).strip()
        if normalized not in _DIFFICULTY_OPTIONS:
            raise ValueError('Dificuldade inválida.')
        return normalized
    if field == 'observations':
        normalized = str(value or '').strip()
        if len(normalized) > _MAX_OBSERVATIONS_LENGTH:
            raise ValueError('As observações excedem o limite permitido.')
        return normalized or None
    raise ValueError('Campo não permitido para edição.')


def _history_value(value):
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _storage_directory(management_id):
    return _UPLOAD_ROOT / str(int(management_id))


def _attachment_path(management_id, stored_name):
    directory = _storage_directory(management_id).resolve()
    target = (directory / stored_name).resolve()
    if target.parent != directory:
        raise ValueError('Caminho de anexo inválido.')
    return target


def _remove_file_safely(target):
    try:
        target.unlink(missing_ok=True)
        return True
    except OSError:
        return False


@demand_management_bp.route('/demandas/gerenciador', methods=['GET'])
def management_page():
    csrf_token = session.get('demand_management_csrf')
    if not csrf_token:
        csrf_token = secrets.token_urlsafe(32)
        session['demand_management_csrf'] = csrf_token
    return render_template(
        'demandManagement/management.html',
        area=request.args['area'],
        csrf_token=csrf_token,
    )


@demand_management_bp.route('/demandas/gerenciador/api', methods=['GET'])
def management_list_api():
    config = _area_config()
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        rows = cnnx.execute(
            text(_MANAGEMENT_SELECT + """
                WHERE source.areaId = :source_area_id
                ORDER BY responsible.name, source.title, management.managementId
            """),
            {'source_area_id': config['source_area_id']}
        ).mappings().all()
        demands = [_row_to_dict(row) for row in rows]
        users = _fetch_users(cnnx, config)

    return jsonify({'ok': True, 'demands': demands, 'users': users})


@demand_management_bp.route('/demandas/gerenciador/api/<int:management_id>', methods=['GET'])
def management_detail_api(management_id):
    config = _area_config()
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        demand = _fetch_management(cnnx, management_id, config)
        if demand is None:
            return _api_error('Demanda não encontrada.', 404)
        source = _fetch_management_source_details(cnnx, management_id, config)
        tasks = _fetch_tasks(cnnx, management_id)
        attachments = _fetch_attachments(cnnx, management_id)
        users = _fetch_users(cnnx, config)

    return jsonify({
        'ok': True,
        'demand': demand,
        'source': source,
        'tasks': tasks,
        'attachments': attachments,
        'users': users,
    })


@demand_management_bp.route('/demandas/gerenciador/api/<int:management_id>', methods=['PATCH'])
def management_update_api(management_id):
    payload = request.get_json(silent=True) or {}
    field = payload.get('field')
    if field not in _UPDATABLE_FIELDS:
        return _api_error('Campo não permitido para edição.')

    try:
        expected_version = _normalize_version(payload.get('version'))
    except ValueError as exc:
        return _api_error(str(exc))

    config = _area_config()
    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        current = _fetch_management(cnnx, management_id, config)
        if current is None:
            return _api_error('Demanda não encontrada.', 404)

        try:
            normalized_value = _validate_management_value(
                cnnx,
                field,
                payload.get('value'),
                config,
            )
        except ValueError as exc:
            return _api_error(str(exc))

        column = _UPDATABLE_FIELDS[field]
        result = cnnx.execute(
            text(f"""
                UPDATE JDT_DEMAND_MANAGEMENT
                SET {column} = :value,
                    updatedAt = GETDATE()
                WHERE managementId = :management_id
                  AND rowVersion = :expected_version
            """),
            {
                'value': normalized_value,
                'management_id': management_id,
                'expected_version': expected_version,
            }
        )

        if result.rowcount != 1:
            return _api_error(
                'Esta demanda foi alterada por outra pessoa. Atualize os dados e tente novamente.',
                409,
            )

        cnnx.execute(
            text("""
                INSERT INTO JDT_DEMAND_MANAGEMENT_HISTORY (
                    managementId,
                    fieldName,
                    oldValue,
                    newValue,
                    changedBy,
                    changedAt
                ) VALUES (
                    :management_id,
                    :field_name,
                    :old_value,
                    :new_value,
                    :changed_by,
                    GETDATE()
                )
            """),
            {
                'management_id': management_id,
                'field_name': field,
                'old_value': _history_value(current.get(field)),
                'new_value': _history_value(normalized_value),
                'changed_by': current_user.id,
            }
        )
        updated = _fetch_management(cnnx, management_id, config)

    return jsonify({'ok': True, 'demand': updated})


@demand_management_bp.route('/demandas/gerenciador/api/<int:management_id>/tasks', methods=['POST'])
def task_create_api(management_id):
    payload = request.get_json(silent=True) or {}
    description = str(payload.get('description') or '').strip()
    if not description:
        return _api_error('Informe a descrição da tarefa.')
    if len(description) > _MAX_TASK_LENGTH:
        return _api_error('A descrição da tarefa excede o limite permitido.')

    config = _area_config()
    try:
        deadline = _normalize_date(payload.get('deadline'), 'O prazo da tarefa')
    except ValueError as exc:
        return _api_error(str(exc))

    responsible_user_id = str(payload.get('responsibleUserId') or '').strip() or None
    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        if _fetch_management(cnnx, management_id, config) is None:
            return _api_error('Demanda não encontrada.', 404)
        if responsible_user_id and not _is_assignable_user(cnnx, responsible_user_id, config):
            return _api_error('O responsável da tarefa não está ativo na área.')

        next_order = cnnx.execute(
            text("""
                SELECT COALESCE(MAX(sortOrder), 0) + 1
                FROM JDT_DEMAND_MANAGEMENT_TASKS WITH (UPDLOCK, HOLDLOCK)
                WHERE managementId = :management_id
            """),
            {'management_id': management_id}
        ).scalar_one()
        cnnx.execute(
            text("""
                INSERT INTO JDT_DEMAND_MANAGEMENT_TASKS (
                    managementId,
                    description,
                    responsibleUserId,
                    deadline,
                    completed,
                    sortOrder,
                    createdAt,
                    updatedAt
                ) VALUES (
                    :management_id,
                    :description,
                    :responsible_user_id,
                    :deadline,
                    0,
                    :sort_order,
                    GETDATE(),
                    GETDATE()
                )
            """),
            {
                'management_id': management_id,
                'description': description,
                'responsible_user_id': responsible_user_id,
                'deadline': deadline,
                'sort_order': next_order,
            }
        )
        tasks = _fetch_tasks(cnnx, management_id)

    return jsonify({'ok': True, 'tasks': tasks}), 201


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/tasks/<int:task_id>',
    methods=['PATCH'],
)
def task_update_api(management_id, task_id):
    payload = request.get_json(silent=True) or {}
    allowed_fields = {'description', 'responsibleUserId', 'deadline', 'completed'}
    requested_fields = allowed_fields.intersection(payload.keys())
    if not requested_fields:
        return _api_error('Nenhum campo válido foi informado.')

    try:
        expected_version = _normalize_version(payload.get('version'))
    except ValueError as exc:
        return _api_error(str(exc))

    config = _area_config()
    updates = []
    params = {
        'management_id': management_id,
        'task_id': task_id,
        'expected_version': expected_version,
    }

    try:
        if 'description' in requested_fields:
            description = str(payload.get('description') or '').strip()
            if not description:
                raise ValueError('Informe a descrição da tarefa.')
            if len(description) > _MAX_TASK_LENGTH:
                raise ValueError('A descrição da tarefa excede o limite permitido.')
            updates.append('description = :description')
            params['description'] = description

        if 'deadline' in requested_fields:
            updates.append('deadline = :deadline')
            params['deadline'] = _normalize_date(payload.get('deadline'), 'O prazo da tarefa')

        if 'completed' in requested_fields:
            completed = payload.get('completed')
            if not isinstance(completed, bool):
                raise ValueError('O estado da tarefa deve ser verdadeiro ou falso.')
            updates.append('completed = :completed')
            params['completed'] = completed
    except ValueError as exc:
        return _api_error(str(exc))

    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        if _fetch_management(cnnx, management_id, config) is None:
            return _api_error('Demanda não encontrada.', 404)

        if 'responsibleUserId' in requested_fields:
            responsible_user_id = str(payload.get('responsibleUserId') or '').strip() or None
            if responsible_user_id and not _is_assignable_user(cnnx, responsible_user_id, config):
                return _api_error('O responsável da tarefa não está ativo na área.')
            updates.append('responsibleUserId = :responsible_user_id')
            params['responsible_user_id'] = responsible_user_id

        result = cnnx.execute(
            text(f"""
                UPDATE JDT_DEMAND_MANAGEMENT_TASKS
                SET {', '.join(updates)},
                    updatedAt = GETDATE()
                WHERE taskId = :task_id
                  AND managementId = :management_id
                  AND rowVersion = :expected_version
            """),
            params
        )
        if result.rowcount != 1:
            exists = cnnx.execute(
                text("""
                    SELECT 1
                    FROM JDT_DEMAND_MANAGEMENT_TASKS
                    WHERE taskId = :task_id
                      AND managementId = :management_id
                """),
                {'task_id': task_id, 'management_id': management_id}
            ).first()
            if exists:
                return _api_error(
                    'Esta tarefa foi alterada por outra pessoa. Os dados serão atualizados.',
                    409,
                )
            return _api_error('Tarefa não encontrada.', 404)
        tasks = _fetch_tasks(cnnx, management_id)

    return jsonify({'ok': True, 'tasks': tasks})


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/tasks/<int:task_id>',
    methods=['DELETE'],
)
def task_delete_api(management_id, task_id):
    payload = request.get_json(silent=True) or {}
    try:
        expected_version = _normalize_version(payload.get('version'))
    except ValueError as exc:
        return _api_error(str(exc))

    config = _area_config()
    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        if _fetch_management(cnnx, management_id, config) is None:
            return _api_error('Demanda não encontrada.', 404)
        result = cnnx.execute(
            text("""
                DELETE FROM JDT_DEMAND_MANAGEMENT_TASKS
                WHERE taskId = :task_id
                  AND managementId = :management_id
                  AND rowVersion = :expected_version
            """),
            {
                'task_id': task_id,
                'management_id': management_id,
                'expected_version': expected_version,
            }
        )
        if result.rowcount != 1:
            exists = cnnx.execute(
                text("""
                    SELECT 1
                    FROM JDT_DEMAND_MANAGEMENT_TASKS
                    WHERE taskId = :task_id
                      AND managementId = :management_id
                """),
                {'task_id': task_id, 'management_id': management_id}
            ).first()
            if exists:
                return _api_error(
                    'Esta tarefa foi alterada por outra pessoa. Os dados serão atualizados.',
                    409,
                )
            return _api_error('Tarefa não encontrada.', 404)
        tasks = _fetch_tasks(cnnx, management_id)

    return jsonify({'ok': True, 'tasks': tasks})


@demand_management_bp.route('/demandas/gerenciador/api/<int:management_id>/attachments', methods=['POST'])
def attachment_create_api(management_id):
    if request.content_length and request.content_length > _MAX_ATTACHMENT_BYTES:
        return _api_error('O anexo excede o limite de 20 MB.', 413)

    uploaded_file = request.files.get('file')
    if uploaded_file is None or not uploaded_file.filename:
        return _api_error('Selecione um arquivo para anexar.')

    original_name = os.path.basename(uploaded_file.filename.replace('\\', '/')).strip()
    safe_name = secure_filename(original_name)
    extension = safe_name.rsplit('.', 1)[-1].lower() if '.' in safe_name else ''
    if not safe_name or extension not in _ALLOWED_ATTACHMENT_EXTENSIONS:
        return _api_error('Tipo de arquivo não permitido.')

    original_name = original_name[:255]
    attachment_id = str(uuid4())
    stored_name = f'{uuid4().hex}_{safe_name[:180]}'
    config = _area_config()
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        if _fetch_management(cnnx, management_id, config) is None:
            return _api_error('Demanda não encontrada.', 404)

    directory = _storage_directory(management_id)
    directory.mkdir(parents=True, exist_ok=True)
    target = _attachment_path(management_id, stored_name)
    uploaded_file.save(target)
    file_size = target.stat().st_size
    if file_size > _MAX_ATTACHMENT_BYTES:
        _remove_file_safely(target)
        return _api_error('O anexo excede o limite de 20 MB.', 413)

    try:
        with engine.begin() as cnnx:
            if _fetch_management(cnnx, management_id, config) is None:
                _remove_file_safely(target)
                return _api_error('Demanda não encontrada.', 404)
            cnnx.execute(
                text("""
                    INSERT INTO JDT_DEMAND_MANAGEMENT_ATTACHMENTS (
                        attachmentId,
                        managementId,
                        originalName,
                        storedName,
                        mimeType,
                        sizeBytes,
                        uploadedBy,
                        uploadedAt
                    ) VALUES (
                        :attachment_id,
                        :management_id,
                        :original_name,
                        :stored_name,
                        :mime_type,
                        :size_bytes,
                        :uploaded_by,
                        GETDATE()
                    )
                """),
                {
                    'attachment_id': attachment_id,
                    'management_id': management_id,
                    'original_name': original_name,
                    'stored_name': stored_name,
                    'mime_type': (uploaded_file.mimetype or 'application/octet-stream')[:150],
                    'size_bytes': file_size,
                    'uploaded_by': current_user.id,
                }
            )
            attachments = _fetch_attachments(cnnx, management_id)
    except Exception:
        _remove_file_safely(target)
        raise

    return jsonify({'ok': True, 'attachments': attachments}), 201


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/attachments/<attachment_id>',
    methods=['GET'],
)
def attachment_download_api(management_id, attachment_id):
    config = _area_config()
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        if _fetch_management(cnnx, management_id, config) is None:
            return _api_error('Demanda não encontrada.', 404)
        attachment = cnnx.execute(
            text("""
                SELECT originalName, storedName, mimeType
                FROM JDT_DEMAND_MANAGEMENT_ATTACHMENTS
                WHERE attachmentId = :attachment_id
                  AND managementId = :management_id
            """),
            {'attachment_id': attachment_id, 'management_id': management_id}
        ).mappings().first()
    if attachment is None:
        return _api_error('Anexo não encontrado.', 404)

    try:
        target = _attachment_path(management_id, attachment['storedName'])
    except ValueError:
        return _api_error('Anexo inválido.', 404)
    if not target.is_file():
        return _api_error('Arquivo do anexo não encontrado.', 404)

    return send_file(
        target,
        as_attachment=True,
        download_name=attachment['originalName'],
        mimetype=attachment['mimeType'],
    )


@demand_management_bp.route(
    '/demandas/gerenciador/api/<int:management_id>/attachments/<attachment_id>',
    methods=['DELETE'],
)
def attachment_delete_api(management_id, attachment_id):
    config = _area_config()
    engine = get_engine('jdt')
    target = None
    with engine.begin() as cnnx:
        if _fetch_management(cnnx, management_id, config) is None:
            return _api_error('Demanda não encontrada.', 404)
        attachment = cnnx.execute(
            text("""
                SELECT storedName
                FROM JDT_DEMAND_MANAGEMENT_ATTACHMENTS
                WHERE attachmentId = :attachment_id
                  AND managementId = :management_id
            """),
            {'attachment_id': attachment_id, 'management_id': management_id}
        ).mappings().first()
        if attachment is None:
            return _api_error('Anexo não encontrado.', 404)

        target = _attachment_path(management_id, attachment['storedName'])
        cnnx.execute(
            text("""
                DELETE FROM JDT_DEMAND_MANAGEMENT_ATTACHMENTS
                WHERE attachmentId = :attachment_id
                  AND managementId = :management_id
            """),
            {'attachment_id': attachment_id, 'management_id': management_id}
        )
        attachments = _fetch_attachments(cnnx, management_id)

    warning = None
    if target is not None and not _remove_file_safely(target):
        warning = 'O registro foi removido, mas o arquivo físico deverá ser verificado pelo administrador.'
    return jsonify({'ok': True, 'attachments': attachments, 'warning': warning})
