"""Casos de uso do QSB: transações, concorrência, histórico e anexos."""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from .domain import (
    QualityControlError, SNAPSHOT_FIELDS, is_flag_set, is_legacy,
    submission_key, validate_entry, validate_stop_reason_name,
)
from .repository import QualityControlRepository, json_snapshot


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_TOTAL_BYTES = 40 * 1024 * 1024
MAX_FILES = 20


def revision(entry):
    content = {
        'data': json_snapshot(entry),
        'updated_at': str(entry.get('updated_at') or ''),
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode('utf-8')).hexdigest()


def image_names(value):
    if not isinstance(value, str):
        return []
    return list(dict.fromkeys(name for name in value.split('||') if name))


def safe_name(value):
    return bool(value) and value not in ('.', '..') and '/' not in value and '\\' not in value and '\x00' not in value


def image_kind(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png', 'image/png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpg', 'image/jpeg'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'gif', 'image/gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp', 'image/webp'
    if data.startswith(b'BM'):
        return 'bmp', 'image/bmp'
    raise QualityControlError('Use imagens PNG, JPEG, GIF, WEBP ou BMP.')


def serialize_entry(entry):
    result = {key: entry.get(key) for key in SNAPSHOT_FIELDS if key != 'deleted_at'}
    result['id'] = str(entry['id']).strip()
    result['unit'] = int(entry['unit'])
    result['repeat'] = is_flag_set(entry['repeat'])
    result['publish_qsb'] = is_flag_set(entry['publish_qsb'])
    result['openDate'] = str(entry['openDate'])[:10]
    result['date_iso'] = result['openDate']
    result['date_label'] = datetime.strptime(result['openDate'], '%Y-%m-%d').strftime('%d/%m/%Y')
    result['stop_time'] = str(entry['stop_time'])[:5] if entry.get('stop_time') is not None else ''
    result['stop_minutes'] = float(entry['stop_minutes']) if entry.get('stop_minutes') is not None else None
    result['stop_count'] = int(entry['stop_count']) if entry.get('stop_count') is not None else None
    result['stop_reason'] = entry.get('stop_reason') or ''
    result['location_detail'] = entry.get('location_detail') or ''
    result['shift'] = str(entry.get('shift') or '')
    result['is_legacy'] = is_legacy(entry)
    result['revision'] = revision(entry)
    for field in ('created_by', 'updated_by'):
        result[field] = entry.get(field)
    for field in ('created_at', 'updated_at'):
        value = entry.get(field)
        result[field] = value.isoformat() + 'Z' if value is not None else None
    for category, column in (('nok', 'imgNOK'), ('ok', 'imgOK')):
        result[f'images_{category}'] = [
            {'name': name, 'label': name[33:] if len(name) > 33 and name[32] == '_' else name}
            for name in image_names(entry.get(column)) if safe_name(name)
        ]
    return result


class QualityControlService:
    def __init__(self, engine, upload_root):
        self.engine = engine
        self.upload_root = Path(upload_root).resolve()
        self.repository = QualityControlRepository()

    def list_entries(self):
        with self.engine.connect() as connection:
            return [serialize_entry(entry) for entry in self.repository.list_entries(connection)]

    def list_stop_reasons(self):
        with self.engine.connect() as connection:
            return self.repository.list_stop_reasons(connection)

    def create_stop_reason(self, name, actor_id):
        name = validate_stop_reason_name(name)
        try:
            with self.engine.begin() as connection:
                self.repository.insert_stop_reason(connection, name, actor_id)
        except IntegrityError:
            raise QualityControlError('Este motivo já está cadastrado.', 409)
        return name

    def detail(self, entry_id):
        with self.engine.connect() as connection:
            entry = self.repository.get_entry(connection, entry_id)
            result = serialize_entry(entry)
            history = self.repository.history(connection, entry_id)
        result['history'] = []
        for event in history:
            before = json.loads(event['before_json']) if event['before_json'] else {}
            after = json.loads(event['after_json'])
            changes = [
                {'field': field, 'before': before.get(field), 'after': after.get(field)}
                for field in SNAPSHOT_FIELDS
                if before.get(field) != after.get(field) and field != 'id'
            ]
            result['history'].append({
                'action': event['action'], 'actor_id': event['actor_id'],
                'occurred_at': event['occurred_at'].isoformat() + 'Z', 'changes': changes,
            })
        return result

    def _read_uploads(self, files):
        uploads = []
        total = 0
        for category in ('nok', 'ok'):
            for upload in files.getlist(f'file_{category}'):
                if not upload.filename:
                    continue
                if len(uploads) >= MAX_FILES:
                    raise QualityControlError('Selecione até 20 imagens por envio.')
                data = upload.read(MAX_IMAGE_BYTES + 1)
                if not data or len(data) > MAX_IMAGE_BYTES:
                    raise QualityControlError('Cada imagem deve ter conteúdo e no máximo 10 MB.')
                total += len(data)
                if total > MAX_TOTAL_BYTES:
                    raise QualityControlError('O total de imagens por envio deve ser de até 40 MB.')
                extension, _ = image_kind(data)
                stem = Path(secure_filename(upload.filename)).stem[:80] or 'imagem'
                uploads.append({
                    'category': category, 'data': data, 'extension': extension, 'stem': stem,
                    'hash': hashlib.sha256(data).hexdigest(),
                })
        return uploads

    def _directory(self, category, entry_id=None):
        if category not in ('nok', 'ok'):
            raise QualityControlError('Categoria de imagem inválida.', 404)
        path = self.upload_root / f'img_{category}'
        if entry_id is not None:
            if not str(entry_id).isascii() or not str(entry_id).isdigit():
                raise QualityControlError('Ocorrência inválida.', 404)
            path /= str(entry_id)
        resolved = path.resolve()
        if self.upload_root not in resolved.parents:
            raise QualityControlError('Caminho de imagem inválido.', 404)
        return resolved

    def _save_uploads(self, uploads, entry_id, names, created_paths):
        for upload in uploads:
            directory = self._directory(upload['category'], entry_id)
            directory.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid4().hex}_{upload['stem']}.{upload['extension']}"
            path = (directory / filename).resolve()
            if path.parent != directory:
                raise QualityControlError('Nome de imagem inválido.')
            with path.open('xb') as output:
                created_paths.append(path)
                output.write(upload['data'])
            names[upload['category']].append(filename)

    def save(self, form, files, actor_id, caxias_locations, workcenters, entry_id=None):
        entry_id = str(entry_id) if entry_id is not None else None
        uploads = self._read_uploads(files)
        created_paths = []
        ready_to_commit = False
        try:
            with self.engine.begin() as connection:
                previous = None
                if entry_id is None:
                    self.repository.acquire_creation_lock(connection)
                else:
                    previous = self.repository.get_entry(connection, entry_id, lock=True)
                    if not form.get('revision') or form['revision'] != revision(previous):
                        raise QualityControlError('Esta ocorrência foi alterada por outra pessoa. Reabra o registro antes de salvar.', 409)
                values = validate_entry(
                    form, caxias_locations, workcenters, previous,
                    stop_reasons=self.repository.list_stop_reasons(connection),
                )
                if previous is None:
                    key = submission_key(form.get('submission_key'))
                    fingerprint = hashlib.sha256(json.dumps({
                        'values': values,
                        'files': [(item['category'], item['stem'], item['hash']) for item in uploads],
                    }, sort_keys=True, default=str).encode('utf-8')).hexdigest()
                    duplicate = self.repository.find_submission(connection, actor_id, key)
                    if duplicate:
                        if duplicate['submission_fingerprint'] != fingerprint:
                            raise QualityControlError('Este cadastro já foi enviado com outros dados. Inicie um novo cadastro.', 409)
                        return serialize_entry(self.repository.get_entry(connection, duplicate['entry_id']))
                    entry_id = self.repository.next_id(connection)
                    names = {'nok': [], 'ok': []}
                else:
                    names = {
                        category: image_names(previous.get(column))
                        for category, column in (('nok', 'imgNOK'), ('ok', 'imgOK'))
                    }
                    for category in names:
                        removed = form.getlist(f'remove_{category}')
                        if any(name not in names[category] for name in removed):
                            raise QualityControlError('A lista de imagens foi alterada. Reabra o registro.', 409)
                        names[category] = [name for name in names[category] if name not in removed]
                self._save_uploads(uploads, entry_id, names, created_paths)
                values.update(
                    id=entry_id,
                    imgNOK=''.join(f'{name}||' for name in names['nok']),
                    imgOK=''.join(f'{name}||' for name in names['ok']),
                )
                if previous is None:
                    self.repository.insert_entry(connection, values)
                    self.repository.ensure_control(connection, entry_id, actor_id, True, key, fingerprint)
                else:
                    self.repository.update_entry(connection, values)
                    self.repository.ensure_control(connection, entry_id, actor_id)
                self.repository.update_control(connection, entry_id, values, actor_id)
                after = self.repository.get_entry(connection, entry_id)
                self.repository.audit(connection, entry_id, actor_id, 'create' if previous is None else 'update', previous, after)
                ready_to_commit = True
            return serialize_entry(after)
        except Exception:
            # Somente arquivos criados por esta tentativa, nunca anexos anteriores.
            # Se a confirmação do commit falhar, ele pode ter sido efetivado no
            # servidor. Preservar arquivos potencialmente referenciados nesse caso.
            for path in (() if ready_to_commit else created_paths):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    logging.getLogger(__name__).warning('Não foi possível limpar uma imagem de cadastro QSB revertido.')
            raise

    def delete(self, entry_id, expected_revision, actor_id):
        entry_id = str(entry_id)
        with self.engine.begin() as connection:
            previous = self.repository.get_entry(connection, entry_id, lock=True, include_deleted=True)
            if previous['deleted_at'] is not None:
                return
            if not expected_revision or expected_revision != revision(previous):
                raise QualityControlError('Esta ocorrência foi alterada. Reabra o registro antes de excluir.', 409)
            self.repository.ensure_control(connection, entry_id, actor_id)
            self.repository.mark_deleted(connection, entry_id, actor_id)
            after = self.repository.get_entry(connection, entry_id, include_deleted=True)
            self.repository.audit(connection, entry_id, actor_id, 'delete', previous, after)
        # Exclusão lógica: histórico e imagens são preservados para rastreabilidade.

    def image_path(self, entry_id, category, filename, allow_unpublished=False):
        if not safe_name(filename):
            raise QualityControlError('Imagem não encontrada.', 404)
        with self.engine.connect() as connection:
            entry = self.repository.get_entry(connection, entry_id)
        if not entry['publish_qsb'] and not allow_unpublished:
            raise QualityControlError('Você não tem permissão para esta imagem.', 403)
        column = {'nok': 'imgNOK', 'ok': 'imgOK'}.get(category)
        if column is None or filename not in image_names(entry.get(column)):
            raise QualityControlError('Imagem não encontrada.', 404)
        for directory in (self._directory(category, entry_id), self._directory(category)):
            path = (directory / filename).resolve()
            if path.parent == directory and path.is_file():
                with path.open('rb') as image:
                    _, mimetype = image_kind(image.read(16))
                return path, mimetype
        raise QualityControlError('Imagem não encontrada.', 404)
