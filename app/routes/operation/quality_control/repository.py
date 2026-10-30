"""SQL parametrizado. A conexão e a transação são controladas pelo coordenador."""

import json
from datetime import datetime

from sqlalchemy import text

from .domain import BASE_FIELDS, QualityControlError, SNAPSHOT_FIELDS


PROJECTION = """q.*,
    c.stop_time, c.stop_reason, c.stop_minutes, c.stop_count, c.location_detail,
    COALESCE(c.publish_qsb, 1) AS publish_qsb, c.deleted_at,
    c.created_by, c.created_at, c.updated_by, c.updated_at"""
JOIN = "LEFT JOIN dbo.JDT_OPE_QUAL_CONTROL c ON CONVERT(VARCHAR(32), q.id) = c.entry_id"
VISIBLE = "c.deleted_at IS NULL"
PUBLISHED = "c.deleted_at IS NULL AND COALESCE(c.publish_qsb, 1) = 1"


def snapshot(entry):
    if entry is None:
        return None
    return {key: entry.get(key) for key in SNAPSHOT_FIELDS}


def json_snapshot(entry):
    value = snapshot(entry)
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str) if value is not None else None


class QualityControlRepository:
    def list_stop_reasons(self, connection):
        return list(connection.execute(text(
            "SELECT name FROM dbo.JDT_OPE_QUAL_STOP_REASONS ORDER BY name"
        )).scalars())

    def insert_stop_reason(self, connection, name, actor_id):
        connection.execute(text("""
            INSERT INTO dbo.JDT_OPE_QUAL_STOP_REASONS (name, created_by)
            VALUES (:name, :actor)
        """), {'name': name, 'actor': actor_id})

    def product_options(self, connection, product, center):
        if product:
            return list(connection.execute(text("""
                SELECT TOP (1) DS_MATER FROM WORK_CELL_OP WHERE ID_MATER = :product
            """), {'product': product}).scalars())
        if center:
            return list(connection.execute(text("""
                SELECT DISTINCT ID_MATER FROM WORK_CELL_OP WHERE ID_WORK_UNIT = :center
            """), {'center': center.split('-')[0]}).scalars())
        return []

    def list_entries(self, connection):
        return [dict(row) for row in connection.execute(text(
            f"SELECT {PROJECTION} FROM dbo.JDT_OPE_QUAL q {JOIN} WHERE {VISIBLE} ORDER BY TRY_CONVERT(BIGINT, q.id) DESC, q.id DESC"
        )).mappings()]

    def get_entry(self, connection, entry_id, lock=False, include_deleted=False):
        hint = ' WITH (UPDLOCK, HOLDLOCK)' if lock else ''
        row = connection.execute(text(
            f"SELECT {PROJECTION} FROM dbo.JDT_OPE_QUAL q{hint} {JOIN} WHERE q.id = :id"
        ), {'id': str(entry_id)}).mappings().first()
        if row is None or (row['deleted_at'] is not None and not include_deleted):
            raise QualityControlError('Ocorrência não encontrada.', 404)
        return dict(row)

    def acquire_creation_lock(self, connection):
        result = connection.execute(text("""
            SET NOCOUNT ON;
            DECLARE @result INT;
            EXEC @result = sys.sp_getapplock
                @Resource = N'DigitalJost.QSB.Create', @LockMode = 'Exclusive',
                @LockOwner = 'Transaction', @LockTimeout = 10000;
            SELECT @result;
        """)).scalar_one()
        if result < 0:
            raise QualityControlError('Outro cadastro está em andamento. Tente novamente.', 409)

    def next_id(self, connection):
        year = datetime.now().year
        value = connection.execute(text("""
            SELECT MAX(TRY_CONVERT(BIGINT, id)) FROM dbo.JDT_OPE_QUAL
            WHERE TRY_CONVERT(BIGINT, id) BETWEEN :first AND :last
        """), {'first': year * 100000, 'last': year * 100000 + 99999}).scalar_one()
        next_id = max(int(value or 0) + 1, year * 100000 + 10001)
        if next_id > year * 100000 + 99999:
            raise QualityControlError('Faixa de identificação anual esgotada.', 409)
        return str(next_id)

    def find_submission(self, connection, actor_id, key):
        return connection.execute(text("""
            SELECT entry_id, submission_fingerprint FROM dbo.JDT_OPE_QUAL_CONTROL
            WHERE created_by = :actor AND submission_key = :key
        """), {'actor': actor_id, 'key': key}).mappings().first()

    def ensure_control(self, connection, entry_id, actor_id, is_new=False, key=None, fingerprint=None):
        connection.execute(text("""
            IF NOT EXISTS (
                SELECT 1 FROM dbo.JDT_OPE_QUAL_CONTROL WITH (UPDLOCK, HOLDLOCK)
                WHERE entry_id = :id
            )
                INSERT INTO dbo.JDT_OPE_QUAL_CONTROL
                    (entry_id, created_by, created_at, updated_by, updated_at,
                     submission_key, submission_fingerprint)
                VALUES (:id, :creator, CASE WHEN CAST(:creator AS NVARCHAR(128)) IS NULL THEN NULL ELSE SYSUTCDATETIME() END,
                        :actor, SYSUTCDATETIME(), :key, :fingerprint);
        """), {
            'id': entry_id, 'creator': actor_id if is_new else None, 'actor': actor_id,
            'key': key, 'fingerprint': fingerprint,
        })

    def insert_entry(self, connection, values):
        columns = ', '.join(f'[{field}]' for field in BASE_FIELDS)
        parameters = ', '.join(f':{field}' for field in BASE_FIELDS)
        connection.execute(text(
            f"INSERT INTO dbo.JDT_OPE_QUAL ({columns}) VALUES ({parameters})"
        ), values)

    def update_entry(self, connection, values):
        assignments = ', '.join(f'[{field}] = :{field}' for field in BASE_FIELDS if field != 'id')
        connection.execute(text(
            f"UPDATE dbo.JDT_OPE_QUAL SET {assignments} WHERE id = :id"
        ), values)

    def update_control(self, connection, entry_id, values, actor_id):
        connection.execute(text("""
            UPDATE dbo.JDT_OPE_QUAL_CONTROL SET
                stop_time = :stop_time, stop_reason = :stop_reason,
                stop_minutes = :stop_minutes, stop_count = :stop_count,
                location_detail = :location_detail, publish_qsb = :publish_qsb,
                updated_by = :actor, updated_at = SYSUTCDATETIME()
            WHERE entry_id = :id
        """), {**values, 'id': entry_id, 'actor': actor_id})

    def mark_deleted(self, connection, entry_id, actor_id):
        connection.execute(text("""
            UPDATE dbo.JDT_OPE_QUAL_CONTROL SET
                deleted_at = SYSUTCDATETIME(), deleted_by = :actor,
                updated_by = :actor, updated_at = SYSUTCDATETIME()
            WHERE entry_id = :id
        """), {'id': entry_id, 'actor': actor_id})

    def touch_control(self, connection, entry_id, actor_id):
        connection.execute(text("""
            UPDATE dbo.JDT_OPE_QUAL_CONTROL
            SET updated_by = :actor, updated_at = SYSUTCDATETIME() WHERE entry_id = :id
        """), {'id': entry_id, 'actor': actor_id})

    def audit(self, connection, entry_id, actor_id, action, before, after):
        connection.execute(text("""
            INSERT INTO dbo.JDT_OPE_QUAL_HISTORY
                (entry_id, action, actor_id, before_json, after_json)
            VALUES (:id, :action, :actor, :before, :after)
        """), {
            'id': entry_id, 'actor': actor_id, 'action': action,
            'before': json_snapshot(before), 'after': json_snapshot(after),
        })

    def history(self, connection, entry_id):
        return [dict(row) for row in connection.execute(text("""
            SELECT TOP (30) action, actor_id, occurred_at, before_json, after_json
            FROM dbo.JDT_OPE_QUAL_HISTORY WHERE entry_id = :id ORDER BY id DESC
        """), {'id': entry_id}).mappings()]
