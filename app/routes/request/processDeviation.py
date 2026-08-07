"""
 STATUS DE DESVIOS (LABEL ENCODING):
 0 : AGUARDANDO APROVAÇÃO
 1 : APROVADO
 2 : RECUSADO
 3 : CANCELADO
 4 : FINALIZADO
 5 : EM ANDAMENTO
 6 : VENCIDO
 OBS: QUALQUER ALTERAÇÃO NAS BASES DE DESVIOS ATIVOS DEVE SER REALIZADA NA BASE DE DESVIOS RECUSADOS
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional
from weakref import ref
import pandas as pd
from flask import Blueprint, abort, jsonify, render_template, request, redirect, send_file, url_for
from flask_login import current_user
from flask_mail import Message
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, DBAPIError  # <-- ADIÇÃO
from werkzeug.utils import secure_filename
from app.config import mail
from app.utils.constants import APP_PATH
from app.utils.data_utils import config_table, return_options
from app.utils.db_utils import engine_run_query, get_engine
from app.utils.permissions import get_permission
from app.utils.teams_utils import send_system_teams_alert
import traceback

_STATUS_DICT = {
    0: 'Aguardando aprovação',
    1: 'Aprovado',
    2: 'Recusado',
    3: 'Cancelado',
    4: 'Finalizado',
    5: 'Em andamento',
    6: 'Vencido'
}

_APPROVERS_TEAMS = [
    [0, 'Compras'],
    [1, 'Eng. Fornecedores'],
    [2, 'Eng. Processo'],
    [3, 'Eng. Produto'],
    [4, 'Logística'],
    [5, 'Manutenção'],
    [6, 'Produção'],
    [7, 'Qualidade Cliente'],
    [8, 'Qualidade de Fábrica'],
    [9, 'SSMA'],
    [10, 'Sistemas de Qualidade'],
    [11, 'Campinas']
]

request_processDeviation_bp = Blueprint('request_processDeviation', __name__)

# ------------------------- Helpers -------------------------
def _safe_list_from_str(s):
    """Converte string em lista sem usar eval."""
    if isinstance(s, list):
        return s
    if not s:
        return []
    try:
        return json.loads(s)
    except Exception:
        # fallback para strings como "['a','b']"
        s = s.strip()
        if s.startswith('[') and s.endswith(']'):
            items = s[1:-1].split(',')
            return [i.strip().strip("'").strip('"') for i in items if i.strip()]
        # caso venha simples "abc"
        return [s]

# FORMATA LISTA EM STRING EX: ["randon", "jost", "conexo"] = "randon, jost e conexo"
def _LIST_UPDATE(lista):
    lista = _safe_list_from_str(lista)
    if not lista:
        return ""
    return ', '.join(lista[:-1]) + ' e ' + lista[-1] if len(lista) > 1 else lista[0]

def base_dev(dev_id: str) -> str:
    """Retorna o ID base (AAAA-NNNN) sem a revisão; evita usar [: -2]."""
    parts = str(dev_id).split('-')
    if len(parts) >= 2:
        return f"{parts[0]}-{parts[1]}"
    return str(dev_id)

def next_revision(dev_id: str) -> str:
    """Incrementa a revisão de AAAA-NNNN-R de forma segura."""
    parts = str(dev_id).split('-')
    if len(parts) != 3:
        raise ValueError(f"deviationId inválido: {dev_id}")
    return f"{parts[0]}-{parts[1]}-{int(parts[2]) + 1}"

def ensure_request_folders(dev_id, *subfolders):
    base = os.path.join(APP_PATH, "app", "static", "uploads", "deviation", "request", dev_id)
    os.makedirs(base, exist_ok=True)
    for s in subfolders:
        os.makedirs(os.path.join(base, s), exist_ok=True)
    return base

def _excel_path(filename: str) -> str:
    path = os.path.join(APP_PATH, "app", "static", "uploads", "default")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, filename)

def _deviation_pop_pdf_dir():
    """
    Pasta onde fica armazenado o POP vigente de Desvio de Processo.
    """
    path = os.path.join(
        APP_PATH,
        "app",
        "static",
        "uploads",
        "deviation",
        "pop"
    )
    os.makedirs(path, exist_ok=True)
    return path


def _deviation_pop_pdf_filename():
    """
    Nome fixo do arquivo POP vigente.
    Mantém sempre um único PDF ativo.
    """
    return "POP_DESVIO_PROCESSO.pdf"


def _deviation_pop_pdf_path():
    """
    Caminho físico completo do POP vigente.
    """
    return os.path.join(
        _deviation_pop_pdf_dir(),
        _deviation_pop_pdf_filename()
    )


def _deviation_pop_pdf_url():
    """
    URL pública do POP vigente com cache-buster baseado na data de alteração.
    Assim, quando o admin trocar o POP, o navegador carrega o PDF novo.
    """
    pdf_path = _deviation_pop_pdf_path()

    try:
        version = int(os.path.getmtime(pdf_path)) if os.path.exists(pdf_path) else int(datetime.now().timestamp())
    except Exception:
        version = int(datetime.now().timestamp())

    return url_for(
        'static',
        filename='app/static/uploads/deviation/pop/' + _deviation_pop_pdf_filename()
    ) + f"?v={version}"    

# ------------------------- Auth -------------------------
@request_processDeviation_bp.before_request
def route_auth():
    # Verifica se o usuário está autenticado
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    # Verifica permissão geral
    if not get_permission('GENERAL').can():
        return abort(403)

p_admin = get_permission('DEVIATION')

# --------- HELPERS DE AUTORIZAÇÃO E REGRAS DE NEGÓCIO ---------
def _is_active_approver_for_sector(cnnx, user_id: str, sector_id: int) -> bool:
    """True se user_id consta como aprovador ATIVO no setor informado (SQL Server usa TOP 1)."""
    r = cnnx.execute(
        text("""
        SELECT TOP 1 1
        FROM JDT_REQUEST_DEV_APPROVERS
        WHERE userId = :uid
          AND sectorId = :sid
          AND active = 1
        """),
        {"uid": user_id, "sid": sector_id}
    ).fetchone()
    return r is not None

def _is_active_approver_for_deviation(cnnx, user_id: str, deviation_id_or_base: str) -> bool:
    """True se user_id é aprovador ATIVO do setor do desvio (aceita base ou revisão)."""
    prefix = base_dev(deviation_id_or_base)
    r = cnnx.execute(
        text("""
        SELECT TOP 1 1
        FROM JDT_REQUEST_DEV d
        JOIN JDT_REQUEST_DEV_APPROVERS a
          ON a.sectorId = d.sectorId
         AND a.userId = :uid
         AND a.active = 1
        WHERE d.deviationId LIKE :prefix
        """),
        {"uid": user_id, "prefix": f"{prefix}%"}
    ).fetchone()
    return r is not None

def _latest_deviation_id_for_base(cnnx, base_id: str) -> Optional[str]:
    """Retorna o deviationId mais recente (maior) para a base AAAA-NNNN."""
    row = cnnx.execute(
        text("""
        SELECT TOP 1 deviationId
        FROM JDT_REQUEST_DEV
        WHERE deviationId LIKE :prefix
        ORDER BY deviationId DESC
        """),
        {"prefix": f"{base_dev(base_id)}%"}
    ).fetchone()
    return row[0] if row else None

def _has_open_actions_for_deviation(cnnx, base_id: str) -> bool:
    """
    True se existir pelo menos UMA ação em aberto na revisão vigente.
    - Se a coluna 'status' existir: considera aberta quando ISNULL(status,0)=0.
    - Se a coluna 'status' NÃO existir: fallback conservador (qualquer ação existente conta como aberta).
    """
    latest_id = _latest_deviation_id_for_base(cnnx, base_id)
    if not latest_id:
        return False

    try:
        # Caminho normal (quando a coluna status existe)
        r = cnnx.execute(
            text("""
                SELECT TOP 1 1
                FROM JDT_REQUEST_DEV_PLAN
                WHERE deviationId = :did
                  AND ISNULL(status, 0) <> 1
            """),
            {"did": latest_id}
        ).fetchone()
        return r is not None

    except (ProgrammingError, DBAPIError):
        # Fallback: coluna 'status' não existe => considera abertas se houver qualquer registro
        r = cnnx.execute(
            text("""
                SELECT CASE WHEN COUNT(1) > 0 THEN 1 ELSE 0 END AS has_any
                FROM JDT_REQUEST_DEV_PLAN
                WHERE deviationId = :did
            """),
            {"did": latest_id}
        ).scalar()
        return bool(r)

def _has_any_attachment_for_deviation(cnnx, deviation_id: str) -> bool:
    """
    True se o desvio (revisão informada) possui ao menos 1 anexo em JDT_REQUEST_DEV.attachment.
    Padrão atual de armazenamento: 'arquivo1\n\narquivo2\n\n'
    """
    df = pd.read_sql(
        text("SELECT attachment FROM JDT_REQUEST_DEV WHERE deviationId = :did"),
        cnnx, params={"did": deviation_id}
    )
    if df.empty:
        return False
    raw = (df['attachment'].iloc[0] or '').strip()
    files = [x for x in raw.split('\n\n') if x.strip()]
    return len(files) > 0


def _get_table_columns(table_name: str):
    """
    Retorna a lista de colunas da tabela informada.
    """
    df_cols = engine_run_query(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = :table_name
        ORDER BY ORDINAL_POSITION
        """,
        'jdt',
        params={"table_name": table_name}
    )

    if df_cols.empty:
        return []

    return [str(c).strip() for c in df_cols["COLUMN_NAME"].tolist()]


def _get_plan_pk_col():
    """
    Tenta descobrir a PK da tabela JDT_REQUEST_DEV_PLAN.
    """
    cols = _get_table_columns("JDT_REQUEST_DEV_PLAN")

    pk_candidates = [
        "id", "ID", "Id",
        "actionId", "ActionId",
        "planId", "PlanId",
        "sequence", "Sequence",
        "seq", "Seq"
    ]

    return next((c for c in pk_candidates if c in cols), None)


def _get_plan_status_col():
    """
    Tenta descobrir a coluna de status da tabela JDT_REQUEST_DEV_PLAN.
    """
    cols = _get_table_columns("JDT_REQUEST_DEV_PLAN")

    status_candidates = [
        "status", "Status",
        "actionStatus", "ActionStatus",
        "planStatus", "PlanStatus",
        "state", "State",
        "situation", "Situation"
    ]

    return next((c for c in status_candidates if c in cols), None)


def _get_action_effective_status(
    dev_status,
    action_plan_status,
    deadline
):
    """
    Status efetivo da ação:

    0 = pendente
    1 = concluído
    2 = cancelado
    3 = finalizado
    4 = recusado
    5 = atrasado

    Status persistido da ação:
    0 = pendente
    1 = concluído
    5 = já ficou atrasada
    """

    try:
        dev_status = (
            int(dev_status)
            if dev_status is not None
            else None
        )
    except Exception:
        dev_status = None

    try:
        action_plan_status = int(action_plan_status or 0)
    except Exception:
        action_plan_status = 0

    # =====================================================
    # HERANÇA DO DESVIO
    # =====================================================
    if dev_status == 2:
        return 4  # recusado

    if dev_status == 3:
        return 2  # cancelado

    if dev_status == 4:
        return 3  # finalizado

    # =====================================================
    # STATUS PRÓPRIO DA AÇÃO
    # =====================================================
    if action_plan_status == 1:
        return 1  # concluído

    # A ação já ficou atrasada em algum momento.
    if action_plan_status == 5:
        return 5  # atrasado

    if dev_status == 6:
        return 5  # atrasado

    # =====================================================
    # PRAZO ATUAL VENCIDO
    # =====================================================
    try:
        if deadline is not None and pd.notna(deadline):
            deadline_dt = pd.to_datetime(
                deadline,
                errors='coerce'
            )

            today = pd.Timestamp(datetime.now().date())

            if (
                pd.notna(deadline_dt)
                and deadline_dt.normalize() < today
            ):
                return 5
    except Exception:
        pass

    return 0  # pendente


# I NEW CODE
def _get_action_by_id(cnnx, action_id: int):
    """
    Busca uma ação pelo actionId persistente da JDT_REQUEST_DEV_PLAN.

    O actionId é uma coluna IDENTITY e não depende mais da posição
    da ação em uma consulta ou do filtro aplicado ao usuário.
    """

    status_col = _get_plan_status_col()

    if status_col:
        action_status_select = (
            f"ISNULL(P.[{status_col}], 0) AS actionPlanStatus,"
        )
    else:
        action_status_select = (
            "CAST(0 AS INT) AS actionPlanStatus,"
        )

    df = pd.read_sql(
        text(f"""
            WITH ActionData AS (
                SELECT
                    P.actionId,

                    ROW_NUMBER() OVER (
                        PARTITION BY P.deviationId
                        ORDER BY
                            P.deadline,
                            P.[text],
                            P.actionId
                    ) AS actionNumber,

                    LEFT(P.deviationId, 9) AS deviationBase,

                    P.deviationId,
                    P.[text] AS actionText,
                    P.userId AS responsibleEmail,

                    {action_status_select}

                    COALESCE(R.name, P.userId) AS responsibleName,
                    COALESCE(
                        C.name,
                        CONVERT(varchar(255), D.userId)
                    ) AS creatorName,

                    D.userId AS creatorUserId,

                    P.deadlineHistory,
                    D.openDate AS creationDate,
                    P.deadline,
                    D.status AS devStatus,
                    D.workCenter,
                    D.families

                FROM JDT_REQUEST_DEV_PLAN P

                JOIN JDT_REQUEST_DEV D
                  ON D.deviationId = P.deviationId

                OUTER APPLY (
                    SELECT TOP 1 U.name
                    FROM JDT_USER_DETAILS U
                    WHERE
                        U.companyEmail = P.userId
                        OR CONVERT(varchar(255), U.id) =
                           CONVERT(varchar(255), P.userId)
                ) R

                OUTER APPLY (
                    SELECT TOP 1 U.name
                    FROM JDT_USER_DETAILS U
                    WHERE
                        U.companyEmail =
                            CONVERT(varchar(255), D.userId)
                        OR CONVERT(varchar(255), U.id) =
                           CONVERT(varchar(255), D.userId)
                ) C
            )

            SELECT *
            FROM ActionData
            WHERE actionId = :aid
        """),
        cnnx,
        params={"aid": action_id}
    )

    if df.empty:
        return None

    return df.iloc[0]
# F NEW CODE

def _get_actions_summary_for_deviation(cnnx, base_id: str):
    """
    Retorna resumo efetivo das ações do desvio.

    Regra:
    - Considera a base inteira do desvio.
    - Para cada ação, considera a ocorrência mais recente por texto + responsável.
    - Ação concluída em revisão anterior continua valendo como concluída,
      mesmo sem ser copiada para a nova revisão.
    - Ação pendente copiada para nova revisão passa a valer pela nova revisão.
    """

    prefix = f"{base_dev(base_id)}-%"
    latest_id = _latest_deviation_id_for_base(cnnx, base_id)
    status_col = _get_plan_status_col()

    if status_col:
        df = pd.read_sql(
            text(f"""
                WITH A AS (
                    SELECT
                        P.deviationId,
                        P.[text],
                        P.userId,
                        P.deadline,
                        ISNULL(P.[{status_col}], 0) AS actionStatus,

                        TRY_CONVERT(
                            INT,
                            PARSENAME(REPLACE(P.deviationId, '-', '.'), 1)
                        ) AS revisionNumber,

                        ROW_NUMBER() OVER (
                            PARTITION BY P.[text], P.userId
                            ORDER BY
                                TRY_CONVERT(
                                    INT,
                                    PARSENAME(REPLACE(P.deviationId, '-', '.'), 1)
                                ) DESC,
                                P.deadline DESC,
                                P.[text]
                        ) AS rn
                    FROM JDT_REQUEST_DEV_PLAN P
                    WHERE P.deviationId LIKE :prefix
                )
                SELECT
                    COUNT(1) AS total,
                    SUM(CASE WHEN actionStatus = 1 THEN 1 ELSE 0 END) AS done
                FROM A
                WHERE rn = 1
            """),
            cnnx,
            params={"prefix": prefix}
        )
    else:
        df = pd.read_sql(
            text("""
                WITH A AS (
                    SELECT
                        P.deviationId,
                        P.[text],
                        P.userId,
                        P.deadline,

                        TRY_CONVERT(
                            INT,
                            PARSENAME(REPLACE(P.deviationId, '-', '.'), 1)
                        ) AS revisionNumber,

                        ROW_NUMBER() OVER (
                            PARTITION BY P.[text], P.userId
                            ORDER BY
                                TRY_CONVERT(
                                    INT,
                                    PARSENAME(REPLACE(P.deviationId, '-', '.'), 1)
                                ) DESC,
                                P.deadline DESC,
                                P.[text]
                        ) AS rn
                    FROM JDT_REQUEST_DEV_PLAN P
                    WHERE P.deviationId LIKE :prefix
                )
                SELECT
                    COUNT(1) AS total,
                    CAST(0 AS INT) AS done
                FROM A
                WHERE rn = 1
            """),
            cnnx,
            params={"prefix": prefix}
        )

    total = int(df["total"].iloc[0] or 0)
    done = int(df["done"].iloc[0] or 0)
    pending = max(total - done, 0)

    percent = 100 if total == 0 else round((done / total) * 100)
    can_finalize = pending == 0

    if total == 0:
        status_text = "Sem ações cadastradas"
    elif can_finalize:
        status_text = "Todas as ações concluídas"
    else:
        status_text = f"{pending} ação(ões) pendente(s)"

    return {
        "latestDeviationId": latest_id,
        "total": total,
        "done": done,
        "pending": pending,
        "percent": percent,
        "canFinalize": can_finalize,
        "statusText": status_text
    }

def _deviation_request_upload_root():
    """
    Pasta raiz real dos uploads de desvios.

    Mantém possibilidade de sobrescrever por variável de ambiente,
    mas por padrão usa o caminho do servidor informado.
    """
    custom_root = os.environ.get("DEVIATION_UPLOAD_ROOT")

    if custom_root:
        return custom_root

    return r"I:\IIS\Digital_Jost\app\static\uploads\deviation\request"

def _release_waiting_revision_if_ready(cnnx, deviation_id_or_base: str) -> bool:
    """
    Libera revisão aguardando para "Em andamento" quando:
    - existe uma revisão em status 0;
    - a revisão anterior imediata está finalizada;
    - todos os setores da revisão em status 0 estão aprovados;
    - não existe outra revisão em andamento/atrasada da mesma base.
    """

    base_id = base_dev(deviation_id_or_base)

    revisions = pd.read_sql(
        text("""
            SELECT deviationId, status
            FROM JDT_REQUEST_DEV
            WHERE deviationId LIKE :prefix
        """),
        cnnx,
        params={"prefix": f"{base_id}-%"}
    )

    if revisions.empty:
        return False

    def get_revision_number(value):
        try:
            parts = str(value).split('-')
            return int(parts[2]) if len(parts) == 3 else -1
        except Exception:
            return -1

    revisions['revisionNumber'] = revisions['deviationId'].apply(get_revision_number)
    revisions['status'] = pd.to_numeric(revisions['status'], errors='coerce').fillna(-1).astype(int)

    # Se já existe alguma revisão ativa, não libera outra.
    if revisions['status'].isin([5, 6]).any():
        return False

    waiting_revisions = revisions[
        revisions['status'].eq(0)
    ].sort_values('revisionNumber')

    for _, row in waiting_revisions.iterrows():
        current_id = row['deviationId']
        current_revision = int(row['revisionNumber'])

        if current_revision <= 0:
            continue

        previous_id = f"{base_id}-{current_revision - 1}"

        previous_df = revisions[
            revisions['deviationId'].astype(str).eq(previous_id)
        ]

        if previous_df.empty:
            continue

        # Só libera se a revisão anterior imediata estiver finalizada.
        if int(previous_df['status'].iloc[0]) != 4:
            continue

        approvals = pd.read_sql(
            text("""
                SELECT
                    COUNT(1) AS total,
                    SUM(CASE WHEN ISNULL(status, 0) = 1 THEN 1 ELSE 0 END) AS approved
                FROM JDT_REQUEST_DEV_CONFIG_STATUS
                WHERE deviationId = :did
            """),
            cnnx,
            params={"did": current_id}
        )

        total = int(approvals['total'].iloc[0] or 0)
        approved = int(approvals['approved'].iloc[0] or 0)

        if total > 0 and total == approved:
            cnnx.execute(
                text("""
                    UPDATE JDT_REQUEST_DEV
                       SET status = 5,
                           initDate = CASE
                               WHEN initDate <= CAST(GETDATE() AS DATE)
                               THEN CONVERT(DATE, GETDATE())
                               ELSE initDate
                           END
                     WHERE deviationId = :did
                       AND status = 0
                """),
                {"did": current_id}
            )
            return True

    return False

def _can_user_edit_deviation(cnnx, deviation_id: str) -> bool:
    """
    Regra de edição:
    - ADM/p_admin pode editar desvios de qualquer solicitante, exceto cancelado/finalizado.
    - Solicitante comum só pode editar quando o desvio estiver recusado.
    - Aprovador comum não ganha permissão de edição por ser aprovador.
    """

    df = pd.read_sql(
        text("""
            SELECT userId, status
            FROM JDT_REQUEST_DEV
            WHERE deviationId = :did
        """),
        cnnx,
        params={"did": deviation_id}
    )

    if df.empty:
        return False

    owner_id = str(df['userId'].iloc[0])
    status = int(df['status'].iloc[0])

    is_admin = current_user.admin or p_admin.can()
    is_owner = owner_id == str(current_user.id)

    # ADM pode editar todos, exceto cancelado/finalizado
    if is_admin and status not in (3, 4):
        return True

    # Solicitante comum só edita recusado
    if is_owner and status == 2:
        return True

    return False

def _release_waiting_revision_if_ready(cnnx, deviation_id_or_base: str) -> bool:
    """
    Libera revisão aguardando para "Em andamento" quando:
    - não existir nenhuma revisão ativa da mesma base em status 5 ou 6;
    - existir revisão aguardando aprovação/liberação em status 0;
    - essa revisão estiver aprovada por todas as áreas.

    Resolve os dois fluxos:
    1. Revisão nova foi aprovada antes da anterior ser finalizada:
       fica aguardando até finalizar a anterior.
    2. Revisão anterior foi finalizada antes da nova ser totalmente aprovada:
       libera assim que a última área aprovar.
    """

    base_id = base_dev(deviation_id_or_base)

    revisions = pd.read_sql(
        text("""
            SELECT deviationId, status
            FROM JDT_REQUEST_DEV
            WHERE deviationId LIKE :prefix
        """),
        cnnx,
        params={"prefix": f"{base_id}-%"}
    )

    if revisions.empty:
        return False

    try:
        revisions['status'] = pd.to_numeric(revisions['status'], errors='coerce').fillna(-1).astype(int)
    except Exception:
        return False

    # Se ainda existe revisão ativa, não libera nenhuma outra.
    if revisions['status'].isin([5, 6]).any():
        return False

    def get_revision_number(value):
        try:
            parts = str(value).split('-')
            return int(parts[2]) if len(parts) == 3 else -1
        except Exception:
            return -1

    revisions['revisionNumber'] = revisions['deviationId'].apply(get_revision_number)

    waiting_revisions = revisions[
        revisions['status'].eq(0)
    ].sort_values('revisionNumber')

    for _, row in waiting_revisions.iterrows():
        waiting_id = row['deviationId']

        approvals = pd.read_sql(
            text("""
                SELECT
                    COUNT(1) AS total,
                    SUM(CASE WHEN ISNULL(status, 0) = 1 THEN 1 ELSE 0 END) AS approved
                FROM JDT_REQUEST_DEV_CONFIG_STATUS
                WHERE deviationId = :did
            """),
            cnnx,
            params={"did": waiting_id}
        )

        total = int(approvals['total'].iloc[0] or 0)
        approved = int(approvals['approved'].iloc[0] or 0)

        if total > 0 and total == approved:
            cnnx.execute(
                text("""
                    UPDATE JDT_REQUEST_DEV
                       SET status = 5,
                           initDate = CASE
                               WHEN initDate <= CAST(GETDATE() AS DATE)
                               THEN CONVERT(DATE, GETDATE())
                               ELSE initDate
                           END
                     WHERE deviationId = :did
                       AND status = 0
                """),
                {"did": waiting_id}
            )
            return True

    return False

# ------------------------- Rotas -------------------------

@request_processDeviation_bp.route('/desvios', methods=['GET'])
def dev_get():
    admin = '1' if (current_user.admin or p_admin.can()) else '0'

    return render_template(
        'request.processDeviation/dev_home.html',
        admin=admin
    )

@request_processDeviation_bp.route('/desvios/aprovadores', methods=['GET'])
def dev_approvers_get():
    admin = '1' if p_admin.can() else '0'
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        users = pd.read_sql(
            text("SELECT id, name FROM JDT_USER_DETAILS WHERE generic = 0 AND active = 1 ORDER BY name ASC"),
            cnnx
        )
        sectors = pd.read_sql(
            text("SELECT sector, id FROM JDT_REQUEST_DEV_SECTORS"),
            cnnx
        )
        return render_template(
            'request.processDeviation/dev_approvers.html',
            admin=admin,
            users=users.to_dict(orient="records"),
            sectors=sectors.to_dict(orient='records')
        )

@request_processDeviation_bp.route('/desvios/aprovadores', methods=['POST'])
def dev_approvers_post():
    query = "SELECT * FROM JDT_VIEW_REQUEST_DEV_APPROVERS"
    data = engine_run_query(query, 'jdt')

    if request.args.get('excel'):
        data = data.rename(columns={
            'name': 'NOME FUNCIONÁRIO',
            'companyName': 'UNIDADE JOST',
            'sector': 'SETOR',
            'id': 'USUÁRIO',
            'companyEmail': 'E-MAIL'
        })
        excel_filename = _excel_path('desvios.xlsx')
        if os.path.exists(excel_filename):
            os.remove(excel_filename)
        with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name='GERAL', index=False)
        return send_file(excel_filename, as_attachment=True, download_name='desvios.xlsx')

    return data.to_dict(orient='records')

@request_processDeviation_bp.route('/desvios/aprovadores/<string:userId>/<int:sectorId>', methods=['POST'])
@p_admin.require(403)
def dev_approvers_db_post(userId, sectorId):
    try:
        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            cnnx.execute(
                text("""INSERT INTO JDT_REQUEST_DEV_APPROVERS (userId, sectorId, active)
                        VALUES (:userId, :sectorId, :active)"""),
                {"userId": userId, "sectorId": sectorId, "active": 1}
            )
            requesterEmail = pd.read_sql(
                text("""SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = :userId"""),
                cnnx,
                params={"userId": userId}
            )
            if requesterEmail.empty:
                abort(404, description="Email do solicitante não encontrado")

            msg = Message(
                'ATENÇÃO! NOVO APROVADOR DE DESVIOS.',
                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                recipients=[requesterEmail['companyEmail'][0]]
            )
            msg.html = render_template(
                'request.processDeviation/dev_register_email.html',
                userName=current_user.name,
                sector=_APPROVERS_TEAMS[sectorId][1]
            )

            # e-mail após commit
            cnnx.commit()
            mail.send(msg)

        return jsonify({"message": "Sucesso"}), 200

    except Exception as e:
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError):
            return jsonify({"message": "Aprovador já registrado para este setor."}), 400
        print("Erro inesperado:", e)
        return jsonify({"message": "Erro ao registrar aprovador."}), 500

@request_processDeviation_bp.route('/desvios/aprovadores/<string:userId>/<int:sectorId>', methods=['PATCH'])
@p_admin.require(403)
def dev_approvers_db_patch(userId, sectorId):
    try:
        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            cnnx.execute(
                text("""
                UPDATE JDT_REQUEST_DEV_APPROVERS
                   SET active = CASE WHEN active = 1 THEN 0 ELSE 1 END
                 WHERE userId = :userId AND sectorId = :sectorId
                """),
                {"userId": userId, "sectorId": sectorId}
            )
            cnnx.commit()
        return jsonify({"message": "Status atualizado."}), 200
    except Exception as e:
        print("Erro inesperado:", e)
        return jsonify({"message": "Erro ao atualizar aprovador."}), 500

# Correção: usar oldSectorId na URL e newSectorId no body
@request_processDeviation_bp.route('/desvios/aprovadores/<string:userId>/<int:oldSectorId>', methods=['PUT'])
@p_admin.require(403)
def dev_approvers_db_put(userId, oldSectorId):
    try:
        payload = request.get_json(silent=True) or {}
        newSectorId = payload.get("newSectorId")
        if newSectorId is None:
            return jsonify({"message": "newSectorId é obrigatório"}), 400

        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            cnnx.execute(
                text("""
                UPDATE JDT_REQUEST_DEV_APPROVERS
                   SET sectorId = :new_sectorId
                 WHERE userId = :userId AND sectorId = :old_sectorId
                """),
                {"new_sectorId": newSectorId, "userId": userId, "old_sectorId": oldSectorId}
            )
            cnnx.commit()
        return jsonify({"message": "Status atualizado."}), 200
    except Exception as e:
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError):
            return jsonify({"message": "Aprovador já registrado para este setor."}), 400
        print("Erro inesperado:", e)
        return jsonify({"message": "Erro ao registrar aprovador."}), 500

@request_processDeviation_bp.route('/desvios/pop', methods=['GET'])
def dev_pop_get():
    return render_template(
        'request.processDeviation/dev_pop.html',
        pop_pdf_url=_deviation_pop_pdf_url()
    )

@request_processDeviation_bp.route('/desvios/pop', methods=['POST'])
def dev_pop_post():
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        cnnx.execute(
            text("""INSERT INTO JDT_REQUEST_DEV_ALLOWED (userId) VALUES (:uid)"""),
            {"uid": current_user.id}
        )
        cnnx.commit()
    return redirect('/desvios/gerar')

@request_processDeviation_bp.route('/desvios/pop/alterar', methods=['POST'])
@p_admin.require(403)
def dev_pop_change_post():
    """
    Altera o PDF do POP vigente.

    Regras:
    - Somente admin/p_admin.
    - Aceita apenas PDF.
    - Salva sempre com nome fixo.
    - Faz backup do POP anterior.
    - Reseta os aceites em JDT_REQUEST_DEV_ALLOWED.
    - Assim todos os usuários precisarão ler/aceitar novamente.
    """

    file = request.files.get('pop_pdf')

    if not file or not file.filename:
        return jsonify({
            "message": "Nenhum arquivo PDF foi enviado."
        }), 400

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext != 'pdf':
        return jsonify({
            "message": "Arquivo inválido. Envie apenas PDF."
        }), 400

    mime = str(file.mimetype or '').lower()

    if mime not in ('application/pdf', 'application/octet-stream', ''):
        return jsonify({
            "message": "Arquivo inválido. O arquivo enviado não parece ser um PDF."
        }), 400

    target_dir = _deviation_pop_pdf_dir()
    target_path = _deviation_pop_pdf_path()

    try:
        # =====================================================
        # BACKUP DO POP ANTERIOR
        # =====================================================
        if os.path.exists(target_path):
            backup_name = "backup_POP_DESVIO_PROCESSO_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".pdf"
            backup_path = os.path.join(target_dir, backup_name)

            try:
                import shutil
                shutil.copy2(target_path, backup_path)
            except Exception:
                pass

        # =====================================================
        # SALVA NOVO PDF EM ARQUIVO TEMPORÁRIO E SUBSTITUI
        # =====================================================
        temp_path = os.path.join(
            target_dir,
            "tmp_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".pdf"
        )

        file.save(temp_path)

        os.replace(temp_path, target_path)

        # =====================================================
        # RESET DOS ACEITES
        # Todos os usuários precisarão aceitar novamente.
        # =====================================================
        engine = get_engine('jdt')

        with engine.connect() as cnnx:
            cnnx.execute(
                text("""
                    DELETE FROM JDT_REQUEST_DEV_ALLOWED
                """)
            )
            cnnx.commit()

        return jsonify({
            "message": "POP atualizado com sucesso. Todos os usuários precisarão aceitar novamente."
        }), 200

    except Exception as e:
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass

        return jsonify({
            "message": f"Erro ao atualizar POP: {e}"
        }), 500

@request_processDeviation_bp.route('/desvios/gerar', methods=['GET', 'POST'])
def dev_create():
    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        # =====================================================
        # Helper: resolve id OU email -> email ATIVO
        # =====================================================
        def resolve_active_email(value):
            if not value:
                return None

            df = pd.read_sql(
                text("""
                    SELECT companyEmail
                    FROM JDT_USER_DETAILS
                    WHERE (companyEmail = :v OR id = :v)
                      AND ISNULL(active,1) = 1
                """),
                cnnx,
                params={"v": value}
            )

            if df.empty:
                return None

            return df['companyEmail'].iloc[0]

        # =====================================================
        # INSERT (somente criação)
        # =====================================================
        def insert_data():
            currentDateTime = datetime.now()
            ano = currentDateTime.strftime("%Y")

            id_df = pd.read_sql(
                text("""
                    SELECT MAX(CAST(SUBSTRING(deviationId, 6, 4) AS INT)) AS lastId
                    FROM JDT_REQUEST_DEV
                    WHERE deviationId LIKE :prefix
                """),
                cnnx,
                params={"prefix": f"{ano}%"}
            )

            last_id = int(id_df['lastId'][0]) + 1 if id_df['lastId'][0] is not None else 1
            seq = str(last_id).zfill(4)
            final_id = f"{ano}-{seq}-{request.form['lote']}"

            ensure_request_folders(final_id, "motive", "procedure", "attachment")

            # =====================================================
            # SAVE DAS IMAGENS
            # =====================================================
            def saveFiles(filesList, folder):
                files = []
                target = os.path.join(
                    APP_PATH, "app", "static", "uploads",
                    "deviation", "request", final_id, folder
                )

                for i, f in enumerate(filesList):
                    if f and f.filename:
                        ext = f.filename.rsplit('.', 1)[-1].lower()
                        name = f"img_{i}.{ext}"
                        f.save(os.path.join(target, name))
                        files.append(name)

                return "\n\n".join(files) + ("\n\n" if files else "")

            motiveImages = saveFiles(request.files.getlist('imagens1'), 'motive')
            procedureImages = saveFiles(request.files.getlist('imagens2'), 'procedure')

            cnnx.execute(
                text("""
                    INSERT INTO JDT_REQUEST_DEV (
                        deviationId, userId, sectorId, unit, workCenter, prodCode, families,
                        prodDescription, workInstruction, documents, initDate, finalDate,
                        revision, traceability, motive, imagesMotive, riskAnalisys,
                        procedures, imagesProcedures, openDate, status,
                        notifyCostumer, notifySupplier, attachment,
                        special1, special2, ssma
                    )
                    VALUES (
                        :deviationId, :userId, :sectorId, :unit, :workCenter,
                        :prodCode, :families, :prodDescription, :workInstruction,
                        :documents, :initDate, :finalDate,
                        :revision, :traceability, :motive, :imagesMotive,
                        :riskAnalisys, :procedures, :imagesProcedures,
                        GETDATE(), 0, NULL, NULL, '',
                        :special1, :special2, :ssma
                    )
                """),
                {
                    "deviationId": final_id,
                    "userId": current_user.id,
                    "sectorId": request.form['equipe'],
                    "unit": request.form['unidade'],
                    "workCenter": request.form['ct_send'],
                    "prodCode": request.form['produto_send'],
                    "families": request.form['familia_send'],
                    "prodDescription": request.form['desc'],
                    "workInstruction": request.form['instrucao_send'],
                    "documents": request.form['doc'],
                    "initDate": request.form['data_inicio'],
                    "finalDate": request.form['data_fim'],
                    "revision": request.form['lote'],
                    "traceability": request.form['rast'],
                    "motive": request.form['motivo'],
                    "imagesMotive": motiveImages,
                    "riskAnalisys": request.form['riscos'],
                    "procedures": request.form['proced'],
                    "imagesProcedures": procedureImages,
                    "special1": request.form['especial1'],
                    "special2": request.form['especial2'],
                    "ssma": request.form['ssma']
                }
            )

            # =====================================================
            # PLANO DE AÇÕES
            # =====================================================
            plan_mails = {}
            for key in [k for k in request.form.keys() if k.startswith('acao_')]:
                idx = key.replace('acao_', '')
                resp_raw = request.form.get(f"resp_{idx}")

                cnnx.execute(
                    text("""
                        INSERT INTO JDT_REQUEST_DEV_PLAN
                            (deviationId, text, userId, deadline)
                        VALUES (:d, :t, :u, :p)
                    """),
                    {
                        "d": final_id,
                        "t": request.form[key],
                        "u": resp_raw,
                        "p": request.form.get(f"prazo_{idx}")
                    }
                )

                email = resolve_active_email(resp_raw)
                if email:
                    plan_mails.setdefault(email, []).append(request.form[key])

            # =====================================================
            # STATUS POR SETOR
            # CORREÇÃO:
            # Se unidade = 0 (Caxias do Sul), Campinas NÃO entra no fluxo
            # =====================================================
            loop = _APPROVERS_TEAMS

            if str(request.form['unidade']) == "0":
                loop = _APPROVERS_TEAMS[:-1]

            for sector in loop:
                cnnx.execute(
                    text("""
                        INSERT INTO JDT_REQUEST_DEV_CONFIG_STATUS
                            (deviationId, sectorId, approverId, status, textDenied)
                        VALUES (:d, :s, NULL, 0, NULL)
                    """),
                    {"d": final_id, "s": sector[0]}
                )

            # =====================================================
            # APROVADORES ATIVOS
            # Também filtra Campinas no envio do e-mail se unidade = 0
            # =====================================================
            aux = ""
            if str(request.form['unidade']) == "0":
                aux = "WHERE A.sector <> 'Campinas'"

            aprovadores_email = pd.read_sql(
                text(f"""
                    SELECT DISTINCT U.companyEmail
                    FROM JDT_VIEW_REQUEST_DEV_APPROVERS A
                    JOIN JDT_USER_DETAILS U
                      ON U.companyEmail = A.companyEmail
                    {aux}
                    AND ISNULL(U.active,1) = 1
                """ if aux else """
                    SELECT DISTINCT U.companyEmail
                    FROM JDT_VIEW_REQUEST_DEV_APPROVERS A
                    JOIN JDT_USER_DETAILS U
                      ON U.companyEmail = A.companyEmail
                    WHERE ISNULL(U.active,1) = 1
                """),
                cnnx
            )['companyEmail'].tolist()

            cnnx.commit()

            # =====================================================
            # EMAILS
            # =====================================================
            for email, acoes in plan_mails.items():
                msg = Message(
                    f'Desvio de processo - Nº {final_id}',
                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                    recipients=[email]
                )
                msg.html = render_template(
                    'request.processDeviation/dev_email_plan_included.html',
                    final_id=final_id,
                    solicitante=current_user.name,
                    acoes=acoes
                )
                mail.send(msg)

            for email in aprovadores_email:
                msg = Message(
                    f'Desvio de processo - Nº {final_id}',
                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                    recipients=[email]
                )
                msg.html = render_template(
                    'request.processDeviation/dev_email_avaliate.html',
                    final_id=final_id,
                    solicitante=current_user.name,
                    motivo=request.form['motivo']
                )
                mail.send(msg)

        # =====================================================
        # CONTROLE DE ACESSO
        # =====================================================
        test = pd.read_sql(
            text("SELECT userId FROM JDT_REQUEST_DEV_ALLOWED WHERE userId = :uid"),
            cnnx, params={"uid": current_user.id}
        )
        if test.empty:
            return redirect('/desvios/pop')

        # =====================================================
        # POST
        # =====================================================
        if request.method == 'POST':
            cmd = request.args.get('cmd')

            if cmd == '1':
                insert_data()
                return redirect('/desvios')

            elif cmd == '2':
                did = request.args['editar']

                # =====================================================
                # PROTEÇÃO DE BACKEND - REGRA DE EDIÇÃO ADM:
                # ADM/p_admin pode editar desvios de qualquer solicitante,
                # exceto quando o desvio estiver cancelado ou finalizado.
                # Esta validação bloqueia tentativa manual pela URL.
                # =====================================================
                if not _can_user_edit_deviation(cnnx, did):
                    return redirect('/denied')

                cnnx.execute(
                    text("""
                        UPDATE JDT_REQUEST_DEV
                        SET
                            unit = :unit,
                            workCenter = :workCenter,
                            prodCode = :prodCode,
                            families = :families,
                            prodDescription = :prodDescription,
                            workInstruction = :workInstruction,
                            documents = :documents,
                            initDate = :initDate,
                            finalDate = :finalDate,
                            revision = :revision,
                            traceability = :traceability,
                            motive = :motive,
                            riskAnalisys = :riskAnalisys,
                            procedures = :procedures,
                            special1 = :special1,
                            special2 = :special2,
                            ssma = :ssma,
                            status = 0,
                            openDate = GETDATE()
                        WHERE deviationId = :did
                    """),
                    {
                        "did": did,
                        "unit": request.form['unidade'],
                        "workCenter": request.form['ct_send'],
                        "prodCode": request.form['produto_send'],
                        "families": request.form['familia_send'],
                        "prodDescription": request.form['desc'],
                        "workInstruction": request.form['instrucao_send'],
                        "documents": request.form['doc'],
                        "initDate": request.form['data_inicio'],
                        "finalDate": request.form['data_fim'],
                        "revision": request.form['lote'],
                        "traceability": request.form['rast'],
                        "motive": request.form['motivo'],
                        "riskAnalisys": request.form['riscos'],
                        "procedures": request.form['proced'],
                        "special1": request.form['especial1'],
                        "special2": request.form['especial2'],
                        "ssma": request.form['ssma'],
                    }
                )

                cnnx.execute(
                    text("""
                        UPDATE JDT_REQUEST_DEV_CONFIG_STATUS
                        SET status = 0, approverId = NULL, textDenied = NULL
                        WHERE deviationId = :did
                    """),
                    {"did": did}
                )

                # =====================================================
                # CORREÇÃO:
                # recria o fluxo de aprovação conforme a unidade editada
                # =====================================================
                cnnx.execute(
                    text("""
                        DELETE FROM JDT_REQUEST_DEV_CONFIG_STATUS
                        WHERE deviationId = :did
                    """),
                    {"did": did}
                )

                loop = _APPROVERS_TEAMS
                if str(request.form['unidade']) == "0":
                    loop = _APPROVERS_TEAMS[:-1]

                for sector in loop:
                    cnnx.execute(
                        text("""
                            INSERT INTO JDT_REQUEST_DEV_CONFIG_STATUS
                                (deviationId, sectorId, approverId, status, textDenied)
                            VALUES (:d, :s, NULL, 0, NULL)
                        """),
                        {"d": did, "s": sector[0]}
                    )

                cnnx.commit()
                return redirect('/desvios')

        # =====================================================
        # GET - SELECTS AUXILIARES
        # =====================================================
        cts = return_options("SELECT NOME_MAQUINA FROM CONFIG_TABLET", 'NOME_MAQUINA', 'ftm')
        products = return_options(
            "SELECT DISTINCT(ID_MATER) AS ID_MATER FROM WORK_CELL_OP WHERE ID_WORK_UNIT = '' ORDER BY ID_MATER",
            'ID_MATER', 'ftm'
        )
        mails = return_options(
            "SELECT DISTINCT(companyEmail) AS MAIL FROM JDT_USER_DETAILS WHERE generic = 0 AND active = 1 AND companyName LIKE '%JOST%'",
            'MAIL', 'jdt'
        )

        edit = ''
        cmd = 1
        revisao = 0

        # =====================================================
        # INICIALIZAÇÃO SEGURA
        # =====================================================
        df = None
        df_plan = None

        if 'editar' in request.args:

            # =====================================================
            # PROTEÇÃO DE BACKEND - REGRA DE EDIÇÃO ADM:
            # ADM/p_admin pode carregar edição de desvios de qualquer
            # solicitante, exceto cancelado/finalizado.
            # Solicitante comum continua dependendo do helper.
            # =====================================================
            if not _can_user_edit_deviation(cnnx, request.args['editar']):
                return redirect('/denied')

            df = pd.read_sql(
                text("""
                    SELECT *
                    FROM JDT_REQUEST_DEV
                    WHERE deviationId = :did
                """),
                cnnx, params={"did": request.args['editar']}
            ).astype(str)

            df_plan = pd.read_sql(
                text("""
                    SELECT
                        deviationId,
                        [text],
                        userId,
                        deadline
                    FROM JDT_REQUEST_DEV_PLAN
                    WHERE deviationId = :did
                    ORDER BY actionId
                """),
                cnnx,
                params={"did": request.args['editar']}
            ).astype(str).to_json()

        if df is not None and not df.empty:
            revisao = int(df['deviationId'].iloc[0].split('-')[2]) + 1

            # =====================================================
            # REGRA DE EDIÇÃO ADM:
            # Quando o backend já validou permissão pelo helper,
            # a tela deve abrir em modo edição para ADM ou solicitante permitido.
            # Mantém a revisão atual e não cria nova estrutura.
            # =====================================================
            edit = '&editar=' + str(df['deviationId'].iloc[0])
            cmd = 2
            revisao -= 1

            df = df.to_json()
        else:
            revisao = 0
            df = False
            df_plan = False

        return render_template(
            'request.processDeviation/dev_create.html',
            equipes=_APPROVERS_TEAMS,
            solicitante=current_user.name,
            revisao=revisao,
            cts=cts,
            produtos=products,
            df=df,
            df_plan=df_plan,
            edit=edit,
            cmd=cmd,
            mails=mails
        )

# RENOVAR DESVIO
@request_processDeviation_bp.route('/desvios/renovar', methods=['GET', 'POST'])
def dev_renew():
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        data = pd.read_sql(
            text("""SELECT *, DATEDIFF(day, GETDATE(), finalDate) AS renew
                    FROM JDT_REQUEST_DEV
                    WHERE deviationId LIKE :prefix"""),
            cnnx, params={"prefix": f"{request.args['id']}%"}
        )

        if len(data) == 0:
            return redirect('/denied')

        # =====================================================
        # REGRA DE REVISÃO PENDENTE:
        # Se já existir qualquer revisão aguardando aprovação
        # para o mesmo desvio, não permite criar nova revisão.
        # =====================================================
        try:
            if pd.to_numeric(data['status'], errors='coerce').fillna(-1).astype(int).eq(0).any():
                return redirect('/denied')
        except Exception:
            return redirect('/denied')

        onapproving = None
        dev_to_new_revision = data.loc[[data['deviationId'].idxmax()]].reset_index(drop=True)
        if int(dev_to_new_revision['status'][0]) == 2:
            onapproving = dev_to_new_revision.copy()
            data = data.drop(data['deviationId'].idxmax())
            dev_to_new_revision = data.loc[[data['deviationId'].idxmax()]].reset_index(drop=True)

        if int(dev_to_new_revision['status'][0]) not in (5, 6) or int(dev_to_new_revision['renew'][0]) >= 5:
            return redirect('/denied')

        # NOVA REGRA: dono OU admin OU p_admin OU aprovador ATIVO do MESMO SETOR
        try:
            is_sector_approver = _is_active_approver_for_sector(
                cnnx, current_user.id, int(dev_to_new_revision['sectorId'][0])
            )
        except Exception:
            is_sector_approver = False

        if not (
            str(current_user.id) == str(dev_to_new_revision['userId'][0]) or
            current_user.admin or
            p_admin.can() or
            is_sector_approver
        ):
            return redirect('/denied')

        if request.method == 'POST':
            new_id = next_revision(dev_to_new_revision['deviationId'][0])

            if onapproving is not None:
                # move o "em aprovação" para refused
                cnnx.execute(
                    text("""INSERT INTO JDT_REQUEST_DEV_REFUSED
                            SELECT *, GETDATE()
                            FROM JDT_REQUEST_DEV
                            WHERE deviationId = :did"""),
                    {"did": onapproving['deviationId'][0]}
                )
                cnnx.execute(
                    text("""DELETE FROM JDT_REQUEST_DEV WHERE deviationId = :did"""),
                    {"did": onapproving['deviationId'][0]}
                )
                cnnx.execute(
                    text("""INSERT INTO JDT_REQUEST_DEV_REFUSED_CONFIG_STATUS
                            SELECT *, GETDATE()
                            FROM JDT_REQUEST_DEV_CONFIG_STATUS
                            WHERE deviationId = :did"""),
                    {"did": onapproving['deviationId'][0]}
                )
                cnnx.execute(
                    text("""DELETE FROM JDT_REQUEST_DEV_CONFIG_STATUS WHERE deviationId = :did"""),
                    {"did": onapproving['deviationId'][0]}
                )
                cnnx.execute(
                    text("""
                        INSERT INTO JDT_REQUEST_DEV_REFUSED_PLAN (
                            deviationId,
                            [text],
                            userId,
                            deadline,
                            to_refused_Date
                        )
                        SELECT
                            deviationId,
                            [text],
                            userId,
                            deadline,
                            GETDATE()
                        FROM JDT_REQUEST_DEV_PLAN
                        WHERE deviationId = :did
                    """),
                    {
                        "did": onapproving['deviationId'][0]
                    }
                )
                cnnx.execute(
                    text("""DELETE FROM JDT_REQUEST_DEV_PLAN WHERE deviationId = :did"""),
                    {"did": onapproving['deviationId'][0]}
                )
                cnnx.commit()
            else:
                ensure_request_folders(new_id, "attachment")

            # cria novo registro (nova revisão)
            cnnx.execute(
                text("""INSERT INTO JDT_REQUEST_DEV (
                            deviationId, userId, sectorId, unit, workCenter, prodCode, families,
                            prodDescription, workInstruction, documents, initDate, finalDate, revision,
                            traceability, motive, imagesMotive, riskAnalisys, procedures, imagesProcedures,
                            openDate, status, notifyCostumer, notifySupplier, attachment, special1, special2, ssma
                        ) VALUES (
                            :deviationId, :userId, :sectorId, :unit, :workCenter, :prodCode, :families,
                            :prodDescription, :workInstruction, :documents, :initDate, :finalDate, :revision,
                            :traceability, :motive, :imagesMotive, :riskAnalisys, :procedures, :imagesProcedures,
                            GETDATE(), 0, NULL, NULL, '', :special1, :special2, :ssma
                        )"""),
                {
                    "deviationId": new_id,
                    "userId": str(dev_to_new_revision['userId'][0]),
                    "sectorId": int(dev_to_new_revision['sectorId'][0]),
                    "unit": int(dev_to_new_revision['unit'][0]),
                    "workCenter": dev_to_new_revision['workCenter'][0],
                    "prodCode": dev_to_new_revision['prodCode'][0],
                    "families": dev_to_new_revision['families'][0],
                    "prodDescription": dev_to_new_revision['prodDescription'][0],
                    "workInstruction": dev_to_new_revision['workInstruction'][0],
                    "documents": dev_to_new_revision['documents'][0],
                    "initDate": request.form['initDate'],
                    "finalDate": request.form['finalDate'],
                    "revision": int(dev_to_new_revision['revision'][0]) + 1,
                    "traceability": None if pd.isna(dev_to_new_revision['traceability'][0]) else int(dev_to_new_revision['traceability'][0]),
                    "motive": dev_to_new_revision['motive'][0],
                    "imagesMotive": dev_to_new_revision['imagesMotive'][0],
                    "riskAnalisys": dev_to_new_revision['riskAnalisys'][0],
                    "procedures": dev_to_new_revision['procedures'][0],
                    "imagesProcedures": dev_to_new_revision['imagesProcedures'][0],
                    "special1": bool(dev_to_new_revision['special1'][0]),
                    "special2": bool(dev_to_new_revision['special2'][0]),
                    "ssma": bool(dev_to_new_revision['ssma'][0]),
                }
            )
            cnnx.commit()

            # =====================================================
            # PLANO DE AÇÕES DA NOVA REVISÃO
            #
            # REGRA:
            # - ação concluída na revisão anterior NÃO é copiada;
            # - ação pendente na revisão anterior É copiada para a
            #   nova revisão como pendente;
            # - a ação concluída continua valendo no resumo, pois o
            #   resumo considera a base inteira do desvio.
            #
            # IMPORTANTE:
            # Mantém a estrutura original da rota. A alteração fica
            # restrita à seleção das ações que serão copiadas.
            # =====================================================
            source_id = str(dev_to_new_revision['deviationId'][0])
            status_col = _get_plan_status_col()

            if status_col:
                plan_to_new_revision = pd.read_sql(
                    text(f"""
                        SELECT *
                        FROM JDT_REQUEST_DEV_PLAN
                        WHERE deviationId = :did
                          AND ISNULL([{status_col}], 0) <> 1
                    """),
                    cnnx,
                    params={"did": source_id}
                )
            else:
                # Sem coluna de status, não tem como identificar concluídas.
                # Mantém comportamento conservador: copia todas.
                plan_to_new_revision = pd.read_sql(
                    text("""
                        SELECT *
                        FROM JDT_REQUEST_DEV_PLAN
                        WHERE deviationId = :did
                    """),
                    cnnx,
                    params={"did": source_id}
                )

            for _, row in plan_to_new_revision.iterrows():
                if status_col:
                    cnnx.execute(
                        text(f"""
                            INSERT INTO JDT_REQUEST_DEV_PLAN
                                (deviationId, [text], userId, deadline, [{status_col}])
                            VALUES
                                (:dev, :txt, :uid, :dl, 0)
                        """),
                        {
                            "dev": new_id,
                            "txt": row['text'],
                            "uid": row['userId'],
                            "dl": row['deadline']
                        }
                    )
                else:
                    cnnx.execute(
                        text("""
                            INSERT INTO JDT_REQUEST_DEV_PLAN
                                (deviationId, [text], userId, deadline)
                            VALUES
                                (:dev, :txt, :uid, :dl)
                        """),
                        {
                            "dev": new_id,
                            "txt": row['text'],
                            "uid": row['userId'],
                            "dl": row['deadline']
                        }
                    )

            cnnx.commit()

            aux = ""
            loop = _APPROVERS_TEAMS
            if str(dev_to_new_revision['unit'][0]) == "0":
                loop = _APPROVERS_TEAMS[:-1]
                aux = "WHERE sector <> 'Campinas'"

            for sector in loop:
                cnnx.execute(
                    text("""INSERT INTO JDT_REQUEST_DEV_CONFIG_STATUS (deviationId, sectorId, approverId, status, textDenied)
                            VALUES (:dev, :sid, NULL, 0, NULL)"""),
                    {"dev": new_id, "sid": sector[0]}
                )
            cnnx.commit()

            approvers_mail = pd.read_sql(
                text(f"""SELECT companyEmail FROM JDT_VIEW_REQUEST_DEV_APPROVERS {aux}"""),
                cnnx
            )['companyEmail'].values.tolist()

            for a_mail in approvers_mail:
                msg = Message(
                    f'Desvio de processo - Nº {new_id}',
                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                    recipients=[a_mail]
                )
                msg.html = render_template(
                    'request.processDeviation/dev_email_avaliate_revision.html',
                    final_id=base_dev(new_id), solicitante=current_user.name
                )
                # mail.send(msg)

            return redirect('/desvios/detalhes?id=' + base_dev(new_id))

        else:
            data_max_final = pd.to_datetime(dev_to_new_revision['finalDate']).max()
            nova_data = (data_max_final + timedelta(days=1)).strftime('%Y-%m-%d')

            return render_template('request.processDeviation/dev_renew.html', id=request.args['id'], lastDate=nova_data)


@request_processDeviation_bp.route('/desvios/atualizar', methods=['GET', 'POST'])
def dev_status_update():
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        dev_row = pd.read_sql(
            text("""SELECT status, companyEmail FROM JDT_VIEW_REQUEST_DEV_DETAILS WHERE deviationId = :did"""),
            cnnx, params={"did": request.args['id']}
        )
        if dev_row.empty:
            return redirect('/denied')

        dev_status = dev_row['status'][0]

        if dev_status == 0 or dev_status == 2:
            requesterEmail = dev_row['companyEmail'][0]

            # =====================================================
            # REGRA ADM:
            # ADM/p_admin pode aprovar/reprovar qualquer setor,
            # linha por linha, usando o sectorId enviado pela tela.
            #
            # Usuário comum continua dependendo de ser aprovador
            # ativo do setor informado.
            # =====================================================
            is_admin = current_user.admin or p_admin.can()
            sector_id_arg = request.args.get('sectorId')

            if is_admin:
                if not sector_id_arg:
                    return redirect('/denied')

                userSector = int(sector_id_arg)

            else:
                if sector_id_arg:
                    try:
                        userSector = int(sector_id_arg)
                    except Exception:
                        return redirect('/denied')

                    if not _is_active_approver_for_sector(cnnx, current_user.id, userSector):
                        return redirect('/denied')

                else:
                    # setor do aprovador atual
                    userSector_df = pd.read_sql(
                        text("""SELECT TOP 1 sectorId FROM JDT_REQUEST_DEV_APPROVERS WHERE userId = :uid"""),
                        cnnx, params={"uid": current_user.id}
                    )
                    if userSector_df.empty:
                        return redirect('/denied')

                    # >> CAST para tipo Python nativo (evita numpy.int64 no bind do pyodbc)
                    userSector = int(userSector_df['sectorId'].iloc[0])

            if "aprovar" in request.args:
                if request.method == "GET":
                    return render_template(
                        'request.processDeviation/dev_sector_approve_share.html',
                        id=request.args['id'],
                        type=request.args.get('tipo'),
                        sectorId=request.args.get('sectorId')
                    )
                else:
                    # marca compartilhamento com fornecedor/cliente, se aplicável
                    tipo = request.args.get('tipo')
                    if tipo == 'fornecedor':
                        cnnx.execute(
                            text("""UPDATE JDT_REQUEST_DEV SET notifySupplier = :val WHERE deviationId = :did"""),
                            {"val": request.args['aprovar'], "did": request.args['id']}
                        )
                    elif tipo == 'cliente':
                        cnnx.execute(
                            text("""UPDATE JDT_REQUEST_DEV SET notifyCostumer = :val WHERE deviationId = :did"""),
                            {"val": request.args['aprovar'], "did": request.args['id']}
                        )

                    # aprova o setor atual
                    cnnx.execute(
                        text("""UPDATE JDT_REQUEST_DEV_CONFIG_STATUS
                                   SET status = 1, approverId = :uid
                                 WHERE deviationId = :did AND sectorId = :sid"""),
                        {"uid": current_user.id, "did": request.args['id'], "sid": int(userSector)}
                    )
                    cnnx.commit()

                    # se todos setores aprovaram -> status geral = 5
                    dev_min_status = pd.read_sql(
                        text("""SELECT MIN(status) AS status
                                FROM JDT_REQUEST_DEV_CONFIG_STATUS
                                WHERE deviationId = :did"""),
                        cnnx, params={"did": request.args['id']}
                    )['status'][0]

                    if dev_min_status == 1:

                        # =====================================================
                        # REGRA DE REVISÃO:
                        # Se for revisão nova e a revisão anterior ainda estiver
                        # ativa, mantém esta revisão aguardando liberação.
                        #
                        # Ativa = status 5 (Em andamento) ou 6 (Atrasado).
                        # =====================================================
                        hold_new_revision = False

                        try:
                            revision_number = int(str(request.args['id']).split('-')[-1])

                            if revision_number > 0:
                                previous_id = f"{base_dev(request.args['id'])}-{revision_number - 1}"

                                previous_df = pd.read_sql(
                                    text("""
                                        SELECT status
                                        FROM JDT_REQUEST_DEV
                                        WHERE deviationId = :did
                                    """),
                                    cnnx,
                                    params={"did": previous_id}
                                )

                                if not previous_df.empty and int(previous_df['status'].iloc[0]) in (5, 6):
                                    hold_new_revision = True

                        except Exception:
                            hold_new_revision = False

                        if not hold_new_revision:
                            requester_mail = pd.read_sql(
                                text("""
                                    SELECT companyEmail
                                    FROM JDT_USER_DETAILS
                                    WHERE companyEmail = :email
                                      AND ISNULL(active,1) = 1
                                """),
                                cnnx,
                                params={"email": requesterEmail}
                            )['companyEmail'].dropna().astype(str).tolist()

                            approvers = pd.read_sql(
                                text("""
                                    SELECT DISTINCT M.approverEmail
                                    FROM JDT_VIEW_REQUEST_DEV_MANAGE M
                                    JOIN JDT_USER_DETAILS U
                                      ON U.companyEmail = M.approverEmail
                                    WHERE M.deviationId = :did
                                      AND M.approverEmail IS NOT NULL
                                      AND ISNULL(U.active,1) = 1
                                """),
                                cnnx, params={"did": request.args['id']}
                            )['approverEmail'].dropna().astype(str).tolist()

                            cnnx.execute(
                                text("""UPDATE JDT_REQUEST_DEV SET status = 5 WHERE deviationId = :did"""),
                                {"did": request.args['id']}
                            )
                            cnnx.execute(
                                text("""UPDATE JDT_REQUEST_DEV
                                           SET initDate = CONVERT(DATE, GETDATE())
                                         WHERE deviationId = :did AND initDate <= CAST(GETDATE() AS DATE)"""),
                                {"did": request.args['id']}
                            )
                            cnnx.commit()

                            msg = Message(
                                f"Pedido de desvio - ID {request.args['id']}",
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=['jost_lideres@empresasrandon.com.br', 'Jost_Qualidade@randon.com.br'] + requester_mail + approvers
                            )
                            msg.html = render_template('request.processDeviation/dev_email_approved.html', id=base_dev(request.args['id']))
                            mail.send(msg)

                            # e-mail para área do setor aprovado
                            area_email = pd.read_sql(
                                text("""
                                    SELECT DISTINCT U.companyEmail
                                    FROM JDT_VIEW_REQUEST_DEV_APPROVERS A
                                    JOIN JDT_USER_DETAILS U
                                      ON U.companyEmail = A.companyEmail
                                    WHERE A.sector = :sector
                                      AND ISNULL(A.active,1) = 1
                                      AND ISNULL(U.active,1) = 1
                                """),
                                cnnx, params={"sector": _APPROVERS_TEAMS[userSector][1]}
                            )['companyEmail'].dropna().astype(str).tolist()

                            msg = Message(
                                f"Pedido de desvio - ID {request.args['id']}",
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=area_email
                            )
                            msg.html = render_template(
                                'request.processDeviation/dev_email_sector.html',
                                id=base_dev(request.args['id']),
                                approverName=current_user.name
                            )
                            mail.send(msg)

                    return render_template(
                        'request.processDeviation/dev_sector_approved.html',
                        id=request.args['id'],
                        sector=_APPROVERS_TEAMS[userSector][1]
                    )

            else:
                # RECUSAR
                if request.method == "GET":
                    return render_template(
                        'request.processDeviation/dev_sector_refuse.html',
                        id=request.args['id'],
                        sectorId=userSector
                    )
                else:
                    cnnx.execute(
                        text("""UPDATE JDT_REQUEST_DEV_CONFIG_STATUS
                                   SET status = 2, approverId = :uid, textDenied = :just
                                 WHERE deviationId = :did AND sectorId = :sid"""),
                        {"uid": current_user.id, "just": request.form['justificativa'],
                         "did": request.args['id'], "sid": int(userSector)}
                    )
                    cnnx.execute(
                        text("""UPDATE JDT_REQUEST_DEV SET status = 2 WHERE deviationId = :did"""),
                        {"did": request.args['id']}
                    )
                    cnnx.commit()

                    msg = Message(
                        f"Pedido de desvio - ID {request.args['id']}",
                        sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                        recipients=[requesterEmail]
                    )
                    msg.html = render_template(
                        'request.processDeviation/dev_email_refused.html',
                        just=request.form['justificativa'],
                        id=base_dev(request.args['id']),
                        approverName=current_user.name
                    )
                    mail.send(msg)

                    return render_template(
                        'request.processDeviation/dev_sector_refused.html',
                        id=request.args['id'],
                        sector=_APPROVERS_TEAMS[userSector][1],
                        just=request.form['justificativa']
                    )
        else:
            # criar pagina de que o desvio ja foi aprovado
            return redirect('/denied')
        
# ROTAS PARA CONSULTAR DESVIOS
@request_processDeviation_bp.route('/desvios/consultar', methods=['GET'])
def dev_view_get():
    end_date = datetime.now().date()
    start_date = f"{end_date.year}-01-01"
    return render_template('request.processDeviation/dev_view.html', end_date=end_date, start_date=start_date)

@request_processDeviation_bp.route('/desvios/consultar', methods=['POST'])
def dev_view_post():
    payload = request.get_json() or {}
    if 'start_date' not in payload or 'end_date' not in payload:
        abort(400, description="Missing 'start_date' or 'end_date'")

    query = """
    SELECT
        LEFT(T1.deviationId, 9) AS deviationId,
        T1.revision,
        T1.name AS requesterName,
        T1.motive,
        T1.workCenter,
        T1.families,
        T1.finalDate,
        T1.status
    FROM JDT_VIEW_REQUEST_DEV_DETAILS AS T1
    WHERE T1.deviationId = (
        SELECT MAX(T2.deviationId)
        FROM JDT_VIEW_REQUEST_DEV_DETAILS AS T2
        WHERE LEFT(T1.deviationId, 10) = LEFT(T2.deviationId, 10)
    )
      AND T1.openDate BETWEEN :start_date AND :end_date
    ORDER BY T1.deviationId DESC
    """
    params = {
        "start_date": payload['start_date'] + ' 00:00',
        "end_date": payload['end_date'] + ' 23:59'
    }
    data = engine_run_query(query, 'jdt', params=params)

    if request.args.get('excel'):
        data['status'] = data['status'].map(_STATUS_DICT)
        data = data.rename(columns={
            'deviationId': 'Desvio',
            'revision': 'Revisão',
            'requesterName': 'Solicitante',
            'motive': 'Motivo',
            'workCenter': 'Centro de Trabalho',
            'families': 'Família',
            'finalDate': 'Data Fim'
        })
        excel_filename = _excel_path('desvios.xlsx')
        if os.path.exists(excel_filename):
            os.remove(excel_filename)
        with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name='GERAL', index=False)
        return send_file(excel_filename, as_attachment=True, download_name='desvios.xlsx')

    return data.to_dict(orient='records')

@request_processDeviation_bp.route('/desvios/aprovacoes', methods=['GET'])
def dev_approvals_get():
    end_date = datetime.now().date()
    start_date = f"{end_date.year}-01-01"
    return render_template('request.processDeviation/dev_approvals.html', end_date=end_date, start_date=start_date)

@request_processDeviation_bp.route('/desvios/aprovacoes', methods=['POST'])
def dev_approvals_post():
    # monta filtro por setor apenas se não for admin
    payload = request.get_json() or {}
    if 'start_date' not in payload or 'end_date' not in payload:
        abort(400, description="Missing 'start_date' or 'end_date'")

    filter_sql = ""
    filter_params = {}
    if current_user.admin or p_admin.can():
        # Admin/p_admin: sem filtro (comportamento original)
        pass
    else:
        # Busca TODOS os setores ATIVOS do usuário (pode haver vários)
        sectorId_df = engine_run_query(
            "SELECT sectorId FROM JDT_REQUEST_DEV_APPROVERS WHERE userId = :uid AND active = 1",
            'jdt', params={"uid": current_user.id}
        )
        if sectorId_df.empty:
            # Retorna mensagem amigável (evita 404/500)
            return jsonify({
                "message": "Você não possui setores configurados para aprovação. Solicite seu cadastro como aprovador."
            }), 403

        # Converte para tipos Python nativos (evita numpy.int64 no bind do pyodbc)
        user_sectors = [int(x) for x in sectorId_df['sectorId'].tolist()]
        # Monta placeholders IN dinamicamente: IN (:s0, :s1, ...)
        placeholders = ", ".join([f":s{i}" for i, _ in enumerate(user_sectors)])
        filter_sql = f" AND T2.sectorId IN ({placeholders}) "
        filter_params = {f"s{i}": s for i, s in enumerate(user_sectors)}

    query = f"""
    SELECT
        LEFT(T1.deviationId, 9) AS deviationId,
        T1.revision,
        T1.name AS requesterName,
        T1.motive,
        T1.workCenter,
        T1.families,
        T1.finalDate,
        T1.status,
        T3.sector,
        T2.sectorId,
        T2.status AS approvalStatus,
        T4.name AS approverName
    FROM JDT_VIEW_REQUEST_DEV_DETAILS AS T1
    JOIN JDT_REQUEST_DEV_CONFIG_STATUS AS T2 ON T1.deviationId = T2.deviationId
    JOIN JDT_REQUEST_DEV_SECTORS AS T3 ON T2.sectorId = T3.id
    LEFT JOIN JDT_USER_DETAILS AS T4 ON T2.approverId = T4.id
    WHERE
      T1.openDate BETWEEN :start_date AND :end_date
      {filter_sql}
    ORDER BY T1.deviationId DESC
    """
    params = {
        "start_date": payload['start_date'] + ' 00:00',
        "end_date": payload['end_date'] + ' 23:59',
        **filter_params
    }
    data = engine_run_query(query, 'jdt', params=params)

    if request.args.get('excel'):
        data['status'] = data['status'].map(_STATUS_DICT)
        data['approvalStatus'] = data['approvalStatus'].map({0: 'Aguardando aprovação', 1: 'Aprovado', 2: 'Reprovado'})
        data = data.rename(columns={
            'deviationId': 'Desvio',
            'revision': 'Revisão',
            'requesterName': 'Solicitante',
            'motive': 'Motivo',
            'workCenter': 'Centro de Trabalho',
            'families': 'Família',
            'finalDate': 'Data Fim',
            'sector': 'Setor',
            'approvalStatus': 'Status de Aprovação',
            'approverName': 'Aprovador'
        })
        excel_filename = _excel_path('desvios.xlsx')
        if os.path.exists(excel_filename):
            os.remove(excel_filename)
        with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name='GERAL', index=False)
        return send_file(excel_filename, as_attachment=True, download_name='desvios.xlsx')

    return data.to_dict(orient='records')

@request_processDeviation_bp.route('/desvios/detalhes', methods=['GET', 'POST'])
def dev_detail():
    if 'id' in request.args:
        requestId = request.args['id']
    elif 'anexo' in request.args:
        requestId = request.args['anexo']
    elif 'finalizar' in request.args:
        requestId = request.args['finalizar']
    elif 'nova_acao' in request.args:
        requestId = request.args['nova_acao']
    else:
        requestId = request.args['cancelar']

    # valida existência
    check = engine_run_query(
        "SELECT userId FROM JDT_REQUEST_DEV WHERE deviationId LIKE :prefix",
        'jdt', params={"prefix": f"{requestId}%"}
    )
    if len(check.get('userId', [])) == 0:
        return redirect('/denied')

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        # =====================================================
        # REGRA DE EDIÇÃO:
        # owner identifica somente o solicitante/dono do desvio.
        # resp continua preservado para anexos/ações conforme regra existente.
        # ADM continua identificado separadamente por admin.
        # =====================================================
        request_owner_df = pd.read_sql(
            text("SELECT userId FROM JDT_REQUEST_DEV WHERE deviationId LIKE :prefix"),
            cnnx, params={"prefix": f"{requestId}%"}
        )

        owner = '1' if str(request_owner_df['userId'][0]) == str(current_user.id) else '0'

        # NOVA REGRA para permissão de edição (resp):
        # dono OU admin OU p_admin OU aprovador ATIVO do setor do desvio
        owner_or_admin = (
            owner == '1'
            or current_user.admin
            or p_admin.can()
        )
        allowed_active_approver = _is_active_approver_for_deviation(cnnx, current_user.id, requestId)
        resp = owner_or_admin or allowed_active_approver
        admin = '1' if (current_user.admin or p_admin.can()) else '0'
        
        if request.method == 'GET' and 'id' in request.args:
            try:
                if _release_waiting_revision_if_ready(cnnx, requestId):
                    cnnx.commit()
            except Exception:
                pass


        if request.method == 'GET':
            if 'cancelar' in request.args:
                if admin == '1':
                    data = pd.read_sql(
                        text("""SELECT status FROM JDT_REQUEST_DEV WHERE deviationId = :did"""),
                        cnnx, params={"did": request.args['cancelar']}
                    )['status'][0]
                    if data == 0:
                        return render_template('request.processDeviation/dev_sector_cancel.html', id=request.args['cancelar'])
                    return redirect('/denied')
                else:
                    return redirect('/denied')

            elif 'anexo' in request.args:
                if admin == '1':
                    oldImages = pd.read_sql(
                        text("""SELECT attachment FROM JDT_REQUEST_DEV WHERE deviationId = :did"""),
                        cnnx, params={"did": request.args['id']}
                    )['attachment'][0] or ""
                    anexo = request.args["anexo"]
                    if anexo in oldImages:
                        newImages = oldImages.replace(f"{anexo}\n\n", "")
                        file_path = os.path.join(
                            APP_PATH, "app", "static", "uploads", "deviation", "request",
                            request.args["id"], "attachment", anexo
                        )
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        cnnx.execute(
                            text("""UPDATE JDT_REQUEST_DEV SET attachment = :att WHERE deviationId = :did"""),
                            {"att": newImages, "did": request.args['id']}
                        )
                        cnnx.commit()
                    return redirect('/desvios/detalhes?id=' + base_dev(request.args['id']))

            user_data = pd.read_sql(
                text("""
                SELECT
                    deviationId AS 'DETALHES REVISÃO',
                    revision AS 'REVISÃO',
                    motive AS 'MOTIVO',
                    workCenter AS 'CENTRO DE TRABALHO',
                    families AS 'FAMÍLIA',
                    initDate AS 'DATA DE INICIO',
                    finalDate AS 'DATA FIM',
                    status AS 'STATUS',
                    sector, name, openDate,
                    DATEDIFF(day, GETDATE(), CONVERT(DATE, finalDate, 103)) AS diff_days, attachment,
                    (SELECT MIN(T2.status) FROM JDT_REQUEST_DEV_CONFIG_STATUS AS T2 WHERE T2.deviationId = T1.deviationId) AS min_status
                FROM JDT_VIEW_REQUEST_DEV_DETAILS AS T1
                WHERE deviationId LIKE :prefix
                ORDER BY deviationId DESC
                """),
                cnnx, params={"prefix": f"{requestId}%"}
            )

            sector = user_data['sector'][0]
            userName = user_data['name'][0]
            firstDate = pd.to_datetime(user_data['openDate']).min().strftime('%d/%m/%Y')
            min_status = user_data['min_status'][0]

            user_data = user_data[['DETALHES REVISÃO', 'REVISÃO', 'MOTIVO', 'CENTRO DE TRABALHO', 'FAMÍLIA', 'DATA DE INICIO', 'DATA FIM', 'STATUS', 'diff_days', 'attachment']]
            user_data['CENTRO DE TRABALHO'] = user_data['CENTRO DE TRABALHO'].apply(_LIST_UPDATE)
            user_data['FAMÍLIA'] = user_data['FAMÍLIA'].apply(_LIST_UPDATE)

            table = config_table(user_data)

            # ----- ANEXOS -----
            raw_att = (user_data['attachment'].iloc[0] or "").strip()
            attachments = [x for x in raw_att.split('\n\n') if x.strip()]

            # IMPORTANTE!!:
            # não travar mais a finalização por falta de anexo no front!!!
            has_attachments = True

            # ----- STATUS DAS AÇÕES -----
            actions_summary = _get_actions_summary_for_deviation(cnnx, requestId)

            if actions_summary["pending"] == 1:
                actions_pending_text = "1 ação pendente"
            elif actions_summary["pending"] > 1:
                actions_pending_text = f"{actions_summary['pending']} ações pendentes"
            else:
                actions_pending_text = "0 ações pendentes"

            
            mails = return_options(
                "SELECT DISTINCT(companyEmail) AS MAIL FROM JDT_USER_DETAILS WHERE generic = 0 AND active = 1 AND companyName LIKE '%JOST%'",
                'MAIL',
            )


            return render_template(
                'request.processDeviation/dev_detail.html',
                table=table,
                userName=userName,
                min_status=min_status,
                idReq=requestId,
                admin=admin,
                sector=sector,
                firstDate=firstDate,
                resp=str(int(resp)),
                owner=owner,
                attachments=attachments,
                has_attachments=has_attachments,
                actions_summary=actions_summary,
                actions_pending_text=actions_pending_text,
                mails=mails
            )

        else:
            # =====================================================
            # NOVA AÇÃO EM UMA REVISÃO
            # Regra:
            # - ADM/p_admin ou solicitante dono do desvio.
            # - Não permite em desvio cancelado/finalizado.
            # - Nova ação nasce com status = 0.
            # =====================================================
            if 'nova_acao' in request.args:
                did = request.args['nova_acao']

                data_dev = pd.read_sql(
                    text("""
                        SELECT userId, status
                        FROM JDT_REQUEST_DEV
                        WHERE deviationId = :did
                    """),
                    cnnx,
                    params={"did": did}
                )

                if data_dev.empty:
                    return jsonify({"message": "Desvio/revisão não encontrado."}), 404

                dev_owner = str(data_dev['userId'].iloc[0])
                dev_status = int(data_dev['status'].iloc[0])

                is_admin = current_user.admin or p_admin.can()
                is_owner = dev_owner == str(current_user.id)

                if not (is_admin or is_owner):
                    return jsonify({
                        "message": "Você não possui permissão para adicionar ação nesta revisão."
                    }), 403

                if dev_status in (3, 4):
                    return jsonify({
                        "message": "Não é possível adicionar ação em desvio cancelado ou finalizado."
                    }), 400

                payload = request.get_json(silent=True) or {}

                action_text = (payload.get("text") or "").strip()
                action_user = (payload.get("userId") or "").strip()
                action_deadline = (payload.get("deadline") or "").strip()

                if not action_text:
                    return jsonify({"message": "Informe a descrição da ação."}), 400

                if not action_user:
                    return jsonify({"message": "Informe o responsável pela ação."}), 400

                if not action_deadline:
                    return jsonify({"message": "Informe o prazo da ação."}), 400

                try:
                    action_deadline = pd.to_datetime(action_deadline, errors='raise').strftime('%Y-%m-%d')
                except Exception:
                    return jsonify({"message": "Prazo inválido. Informe uma data válida."}), 400

                # =====================================================
                # VALIDA RESPONSÁVEL ATIVO:
                # aceita companyEmail ou id, mas grava companyEmail
                # para manter o padrão das ações existentes.
                # =====================================================
                resp_df = pd.read_sql(
                    text("""
                        SELECT TOP 1 companyEmail
                        FROM JDT_USER_DETAILS
                        WHERE (companyEmail = :v OR CONVERT(varchar(255), id) = :v)
                          AND ISNULL(active,1) = 1
                    """),
                    cnnx,
                    params={"v": action_user}
                )

                if resp_df.empty:
                    return jsonify({
                        "message": "Responsável não encontrado ou inativo na base de usuários."
                    }), 400

                action_user_email = resp_df['companyEmail'].iloc[0]

                status_col = _get_plan_status_col()

                if status_col:
                    cnnx.execute(
                        text(f"""
                            INSERT INTO JDT_REQUEST_DEV_PLAN
                                (deviationId, [text], userId, deadline, [{status_col}])
                            VALUES
                                (:did, :txt, :uid, :deadline, 0)
                        """),
                        {
                            "did": did,
                            "txt": action_text,
                            "uid": action_user_email,
                            "deadline": action_deadline
                        }
                    )
                else:
                    cnnx.execute(
                        text("""
                            INSERT INTO JDT_REQUEST_DEV_PLAN
                                (deviationId, [text], userId, deadline)
                            VALUES
                                (:did, :txt, :uid, :deadline)
                        """),
                        {
                            "did": did,
                            "txt": action_text,
                            "uid": action_user_email,
                            "deadline": action_deadline
                        }
                    )

                cnnx.commit()

                # =====================================================
                # EMAIL - NOVA AÇÃO CRIADA
                # Envia imediatamente ao responsável da ação.
                # Não bloqueia a criação da ação caso o envio falhe.
                # =====================================================
                try:
                    prazo_fmt = pd.to_datetime(action_deadline, errors='coerce').strftime('%d/%m/%Y')

                    msg = Message(
                        f"Nova ação atribuída - Desvio {base_dev(did)}",
                        sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                        recipients=[action_user_email]
                    )

                    msg.html = render_template(
                        'request.processDeviation/dev_email_action_created.html',
                        id=base_dev(did),
                        acao=action_text,
                        prazo=prazo_fmt
                    )

                    mail.send(msg)

                except Exception as e:
                    print("Erro ao enviar e-mail de nova ação:", e)

                return jsonify({
                    "message": "Nova ação adicionada com sucesso."
                }), 200

            if resp is True:
                if 'anexo' in request.args:
                    oldImages = pd.read_sql(
                        text("""SELECT attachment FROM JDT_REQUEST_DEV WHERE deviationId = :did"""),
                        cnnx, params={"did": request.args['anexo']}
                    )['attachment'][0] or ""

                    upload_dir = os.path.join(
                        APP_PATH, "app", "static", "uploads", "deviation", "request", request.args["anexo"], "attachment"
                    )
                    os.makedirs(upload_dir, exist_ok=True)

                    for file in request.files.getlist('anexos'):
                        if file and file.filename:
                            filename = secure_filename(file.filename)
                            name, ext = os.path.splitext(filename)
                            fn_upper = filename.upper()
                            if oldImages.upper().count(fn_upper) == 0:
                                file.save(os.path.join(upload_dir, filename))
                                oldImages += f'{filename}\n\n'
                            else:
                                acum = oldImages.upper().count(name.upper())
                                thisName = f"{name}_({acum}){ext}"
                                file.save(os.path.join(upload_dir, thisName))
                                oldImages += f'{thisName}\n\n'

                    cnnx.execute(
                        text("""UPDATE JDT_REQUEST_DEV SET attachment = :att WHERE deviationId = :did"""),
                        {"att": oldImages, "did": request.args['anexo']}
                    )
                    cnnx.commit()
                    return redirect('/desvios/detalhes?id=' + base_dev(request.args['anexo']))

                elif 'cancelar' in request.args:
                    data = pd.read_sql(
                        text("""SELECT userId, status FROM JDT_REQUEST_DEV WHERE deviationId = :did"""),
                        cnnx, params={"did": request.args['cancelar']}
                    )
                    is_admin = current_user.admin or p_admin.can()
                    if data['status'][0] == 0 and is_admin:
                        cnnx.execute(
                            text("""UPDATE JDT_REQUEST_DEV SET status = 3 WHERE deviationId = :did"""),
                            {"did": request.args['cancelar']}
                        )
                        cnnx.execute(
                            text("""UPDATE JDT_REQUEST_DEV_CONFIG_STATUS
                                       SET approverId = :uid, status = 3, textDenied = :just
                                     WHERE deviationId = :did"""),
                            {"uid": current_user.id, "just": request.form['justificativa'], "did": request.args['cancelar']}
                        )
                        cnnx.commit()
                        return redirect('/desvios/detalhes?id=' + request.args['cancelar'])
                    return 'ACCESS DENIED'

                elif admin == '1' and 'finalizar' in request.args:
                    did = request.args['finalizar']
                    data = pd.read_sql(
                        text("""SELECT status, companyEmail FROM JDT_VIEW_REQUEST_DEV_DETAILS WHERE deviationId = :did"""),
                        cnnx, params={"did": did}
                    )
                    if data.empty:
                        return 'ACCESS DENIED'

                    # REMOVIDO:
                    # não exigir mais anexo para finalizar

                    # =====================================================
                    # REGRA ADM:
                    # ADM pode finalizar mesmo havendo ações pendentes.
                    # Portanto, não retorna mais ACTIONS_PENDING aqui.
                    # =====================================================
                    actions_summary = _get_actions_summary_for_deviation(cnnx, did)

                    if int(data['status'][0]) in (5, 6):
                        cnnx.execute(
                            text("""UPDATE JDT_REQUEST_DEV SET status = 4 WHERE deviationId = :did"""),
                            {"did": did}
                        )

                        # =====================================================
                        # REGRA DE REVISÃO:
                        # Após finalizar a revisão atual, tenta liberar a próxima
                        # revisão aguardando, caso ela já esteja aprovada por
                        # todas as áreas e não exista outra revisão ativa.
                        # =====================================================
                        _release_waiting_revision_if_ready(cnnx, did)

                        cnnx.commit()

                        approvers = pd.read_sql(
                            text("""SELECT approverEmail FROM JDT_VIEW_REQUEST_DEV_MANAGE WHERE deviationId = :did"""),
                            cnnx, params={"did": did}
                        )['approverEmail'].values.tolist()

                        msg = Message(
                            f"Pedido de desvio - ID {did}",
                            sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                            recipients=['jost_lideres@empresasrandon.com.br', 'Jost_Qualidade@randon.com.br', data['companyEmail'][0]] + approvers
                        )
                        msg.html = render_template('request.processDeviation/dev_email_finished.html', id=base_dev(did))
                        mail.send(msg)

                        return redirect('/desvios/detalhes?id=' + did)

                return 'ACCESS DENIED'

        return 'ACCESS DENIED'



@request_processDeviation_bp.route('/desvios/detalhes/fisico', methods=['GET', 'POST'])
def dev_detail_physical():
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        df = pd.read_sql(
            text("""SELECT * FROM JDT_VIEW_REQUEST_DEV_DETAILS WHERE deviationId = :did"""),
            cnnx, params={"did": request.args['id']}
        )
        df_plan = pd.read_sql(
            text("""SELECT T1.text, T2.name, FORMAT(T1.deadline, 'dd/MM/yyyy') AS deadline
                    FROM JDT_REQUEST_DEV_PLAN AS T1
                    JOIN JDT_USER_DETAILS AS T2 ON T1.userId = T2.companyEmail
                    WHERE deviationId = :did"""),
            cnnx, params={"did": request.args['id']}
        ).astype(str)

        aprovadores = pd.read_sql(
            text("""SELECT * FROM JDT_VIEW_REQUEST_DEV_MANAGE WHERE deviationId = :did ORDER BY approverSector"""),
            cnnx, params={"did": request.args['id']}
        )

        df['workCenter'] = df['workCenter'].apply(_LIST_UPDATE)
        df['families'] = df['families'].apply(_LIST_UPDATE)
        df['prodCode'] = df['prodCode'].apply(_LIST_UPDATE)
        df['workInstruction'] = df['workInstruction'].apply(_LIST_UPDATE)

        # =====================================================
        # ADIÇÃO SEGURA:
        # Evita que imagesMotive/imagesProcedures cheguem como NaN/null no JS.
        # Não altera estrutura, não altera banco e não altera nomes salvos.
        # =====================================================
        for col in ['imagesMotive', 'imagesProcedures']:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)

        return render_template(
            'request.processDeviation/dev_detail_physical.html',
            dataframe=df.to_json(),
            df_plan=df_plan.to_json(),
            idReq=request.args['id'],
            df_result=aprovadores.to_json()
        )

@request_processDeviation_bp.route('/desvios/detalhes/fisico/arquivo', methods=['GET'])
def dev_detail_physical_file():
    """
    Abre arquivos da ficha física diretamente da pasta real do servidor.

    Suporta:
    - imagens: jpg, jpeg, png, gif, webp, bmp, svg
    - pdf

    Procura:
    1. revisão informada;
    2. revisão 0;
    3. demais revisões da mesma base.
    """

    dev_id = (request.args.get('id') or '').strip()
    folder = (request.args.get('folder') or '').strip()
    file_name = (request.args.get('file') or '').strip()

    # =====================================================
    # ADIÇÃO DEFENSIVA:
    # Caso a URL venha com &amp; em vez de &, tenta recuperar.
    # Exemplo problemático:
    # ?id=2026-0041-0&amp;folder=motive&amp;file=img_0.jpg
    # =====================================================
    if '&amp;' in dev_id and (not folder or not file_name):
        try:
            raw = dev_id.replace('&amp;', '&')
            parts = raw.split('&')

            dev_id = parts[0]

            for p in parts[1:]:
                if p.startswith('folder='):
                    folder = p.replace('folder=', '', 1)
                elif p.startswith('file='):
                    file_name = p.replace('file=', '', 1)
        except Exception:
            pass

    if not dev_id or not folder or not file_name:
        return 'PARAMS REQUIRED', 400

    if folder not in ['motive', 'procedure']:
        return 'INVALID FOLDER', 400

    # Evita path traversal
    file_name = secure_filename(file_name)

    allowed_ext = {
        'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg',
        'pdf'
    }

    ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else ''

    if ext not in allowed_ext:
        return 'FILE TYPE NOT ALLOWED', 415

    uploads_root = _deviation_request_upload_root()
    base_id = base_dev(dev_id)

    candidate_dirs = []

    # 1. Revisão informada
    candidate_dirs.append(dev_id)

    # 2. Revisão 0
    candidate_dirs.append(f"{base_id}-0")

    # 3. Todas as revisões existentes da base
    try:
        if os.path.exists(uploads_root):
            for d in os.listdir(uploads_root):
                full_d = os.path.join(uploads_root, d)
                if os.path.isdir(full_d) and str(d).startswith(base_id):
                    candidate_dirs.append(d)
    except Exception:
        pass

    # Remove duplicados mantendo ordem
    candidate_dirs = list(dict.fromkeys(candidate_dirs))

    for candidate in candidate_dirs:
        file_path = os.path.join(
            uploads_root,
            candidate,
            folder,
            file_name
        )

        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=False,
                download_name=file_name
            )

    return 'FILE NOT FOUND', 404
    
# ======== EXCLUIR DESVIO (ADMIN ONLY) ========
@request_processDeviation_bp.route('/desvios/excluir', methods=['POST'])
@p_admin.require(403)
def dev_delete_post():
    """
    Exclui TODAS as revisões do desvio informado (base AAAA-NNNN), incluindo
    plano, status por setor e registros principais. Também remove os arquivos de upload.
    Body JSON: { "id": "2026-0005" }  # base do desvio
    """
    payload = request.get_json(silent=True) or {}
    base_id = (payload.get('id') or '').strip()
    if not base_id or len(base_id.split('-')) < 2:
        return jsonify({"message": "ID base inválido (formato AAAA-NNNN)."}), 400

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        try:
            # apaga plano e status de TODAS as revisões da base
            cnnx.execute(
                text("""DELETE FROM JDT_REQUEST_DEV_PLAN WHERE deviationId LIKE :prefix"""),
                {"prefix": f"{base_id}%"}
            )
            cnnx.execute(
                text("""DELETE FROM JDT_REQUEST_DEV_CONFIG_STATUS WHERE deviationId LIKE :prefix"""),
                {"prefix": f"{base_id}%"}
            )
            # apaga registros principais
            cnnx.execute(
                text("""DELETE FROM JDT_REQUEST_DEV WHERE deviationId LIKE :prefix"""),
                {"prefix": f"{base_id}%"}
            )
            cnnx.commit()

            # remove uploads (pasta de request)
            try:
                import shutil, os
                base_path = os.path.join(APP_PATH, "app", "static", "uploads", "deviation", "request", base_id)
                if os.path.exists(base_path):
                    shutil.rmtree(base_path, ignore_errors=True)
            except Exception:
                # não falha o endpoint por falha de limpeza de disco
                pass

            return jsonify({"message": f"Desvio {base_id} excluído com sucesso."}), 200

        except Exception as e:
            cnnx.rollback()
            return jsonify({"message": f"Erro ao excluir desvio: {e}"}), 500


@request_processDeviation_bp.route('/desvios/detalhes/anexo/download', methods=['GET'])
def dev_detail_attachment_download():
    file_path = os.path.join(
        APP_PATH, "app", "static", "uploads", "deviation", "request",
        request.args["id"], "attachment", request.args["anexo"]
    )
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=request.args["anexo"])
    else:
        return 'FILE DOES NOT EXISTS'

@request_processDeviation_bp.route('/desvios/acoes/anexo/download', methods=['GET'])
def dev_action_attachment_download():
    try:
        action_id = int(request.args["action_id"])
    except (TypeError, ValueError):
        return 'INVALID ACTION ID', 400

    anexo = secure_filename(request.args.get("anexo", ""))

    if not anexo:
        return 'FILE DOES NOT EXISTS', 404

    engine = get_engine('jdt')

    with engine.connect() as cnnx:
        action = _get_action_by_id(cnnx, action_id)

        if action is None:
            return 'FILE DOES NOT EXISTS', 404

        is_admin = current_user.admin or p_admin.can()

        current_user_id = str(
            current_user.id or ""
        ).strip()

        current_email = str(
            current_user.companyEmail or ""
        ).strip().lower()

        creator_user_id = str(
            action['creatorUserId'] or ""
        ).strip()

        responsible_email = str(
            action['responsibleEmail'] or ""
        ).strip().lower()

        is_creator = (
            current_user_id != ""
            and current_user_id == creator_user_id
        )

        is_responsible = (
            current_email != ""
            and current_email == responsible_email
        )

        can_view_action = (
            is_admin
            or is_creator
            or is_responsible
        )

        if not can_view_action:
            return 'ACCESS DENIED', 403

        deviation_id = str(action['deviationId'])

        file_path = os.path.join(
            APP_PATH,
            "app",
            "static",
            "uploads",
            "deviation",
            "request",
            deviation_id,
            "action_attachment",
            str(action_id),
            anexo
        )

        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=anexo
            )

        return 'FILE DOES NOT EXISTS', 404



@request_processDeviation_bp.route('/desvios/acoes', methods=['GET', 'POST'])
def dev_actions():

    # ===== GET =====
    if request.method == 'GET':
        end_date = datetime.now().date()
        start_date = f"{end_date.year}-01-01"

        return render_template(
            'request.processDeviation/dev_actions.html',
            start_date=start_date,
            end_date=end_date
        )

    # ===== POST =====
    try:
        payload = request.get_json(silent=True) or {}

        start_date = payload.get('start_date')
        end_date = payload.get('end_date')

        params = {}
        date_filter_sql = ""

        if start_date and end_date:
            params["start"] = f"{start_date} 00:00"
            params["end"] = f"{end_date} 23:59"
            date_filter_sql = "AND D.openDate BETWEEN :start AND :end"

        is_admin = current_user.admin or p_admin.can()

        filtro_sql = ""

        if not is_admin:
            filtro_sql = """
                WHERE (
                    CONVERT(varchar(255), creatorUserId) = :uid
                    OR LOWER(LTRIM(RTRIM(responsibleEmail))) =
                    LOWER(LTRIM(RTRIM(:email)))
                )
            """

            params["uid"] = str(current_user.id)
            params["email"] = str(current_user.companyEmail or "")

        status_col = _get_plan_status_col()

        if status_col:
            action_status_select = (
                f"ISNULL(P.[{status_col}], 0) AS actionPlanStatus,"
            )
        else:
            action_status_select = (
                "CAST(0 AS INT) AS actionPlanStatus,"
            )

        query = f"""
            WITH ActionList AS (
                SELECT
                    P.actionId AS actionId,

                    ROW_NUMBER() OVER (
                        PARTITION BY P.deviationId
                        ORDER BY
                            P.deadline,
                            P.[text],
                            P.actionId
                    ) AS actionNumber,

                    LEFT(D.deviationId, 9) AS deviationId,
                    D.deviationId AS fullDeviationId,

                    P.[text] AS actionText,
                    P.userId AS responsibleEmail,

                    {action_status_select}

                    COALESCE(U.name, P.userId) AS responsibleName,

                    D.userId AS creatorUserId,
                    D.workCenter AS workCenter,
                    D.families AS families,

                    CONVERT(varchar(10), P.deadline, 103) AS finalDate,

                    P.deadline AS deadline,
                    P.deadlineHistory AS deadlineHistory,
                    D.status AS devStatus,
                    D.openDate AS devOpenDate

                FROM JDT_REQUEST_DEV D

                JOIN JDT_REQUEST_DEV_PLAN P
                ON P.deviationId = D.deviationId

                LEFT JOIN JDT_USER_DETAILS U
                ON U.companyEmail = P.userId
                OR CONVERT(varchar(255), U.id) =
                    CONVERT(varchar(255), P.userId)

                WHERE 1 = 1
                    {date_filter_sql}
            )

            SELECT
                actionId,
                actionNumber,
                deviationId,
                fullDeviationId,
                actionText,
                responsibleEmail,
                actionPlanStatus,
                responsibleName,
                creatorUserId,
                workCenter,
                families,
                finalDate,
                deadline,
                deadlineHistory,
                devStatus

            FROM ActionList

            {filtro_sql}

            ORDER BY
                devOpenDate DESC,
                deadline,
                actionText,
                actionId
        """

        df = engine_run_query(query, 'jdt', params=params)
        
        if df.empty:
            if request.args.get('excel'):
                excel_filename = _excel_path('acoes_desvios.xlsx')

                if os.path.exists(excel_filename):
                    os.remove(excel_filename)

                empty_df = pd.DataFrame(columns=[
                    'ID Ação',
                    'Nº Ação',
                    'Nº Desvio',
                    'Descrição da Ação',
                    'Responsável',
                    'Centro de Trabalho',
                    'Família',
                    'Prazo da Ação',
                    'Status'
                ])

                with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
                    empty_df.to_excel(writer, sheet_name='AÇÕES', index=False)

                return send_file(
                    excel_filename,
                    as_attachment=True,
                    download_name='acoes_desvios.xlsx'
                )

            return jsonify([]), 200

        df["devStatus"] = pd.to_numeric(df["devStatus"], errors="coerce").fillna(0).astype(int)
        df["actionPlanStatus"] = pd.to_numeric(df["actionPlanStatus"], errors="coerce").fillna(0).astype(int)

        df["status"] = df.apply(
            lambda r: _get_action_effective_status(
                r.get("devStatus"),
                r.get("actionPlanStatus", 0),
                r.get("deadline")
            ),
            axis=1
        )

    
        df_result = df[[
            "actionId",
            "actionNumber",
            "deviationId",
            "actionText",
            "responsibleName",
            "workCenter",
            "families",
            "finalDate",
            "deadlineHistory",
            "status"
        ]].copy()

        # =====================================================
        # EXPORTAÇÃO EXCEL DAS AÇÕES
        # =====================================================
        if request.args.get('excel'):

            def _format_list_for_excel(value):
                try:
                    return _LIST_UPDATE(value)
                except Exception:
                    return value

            status_map = {
                0: 'Ação pendente',
                1: 'Concluído',
                2: 'Cancelado',
                3: 'Finalizado',
                4: 'Recusado',
                5: 'Atrasado'
            }

            excel_df = df_result.copy()

            excel_df = excel_df[[
                "actionId",
                "actionNumber",
                "deviationId",
                "actionText",
                "responsibleName",
                "workCenter",
                "families",
                "finalDate",
                "status"
            ]].copy()

            excel_df["workCenter"] = excel_df["workCenter"].apply(_format_list_for_excel)
            excel_df["families"] = excel_df["families"].apply(_format_list_for_excel)
            excel_df["status"] = excel_df["status"].map(status_map).fillna('Indefinido')

            excel_df = excel_df.rename(columns={
                "actionId": "ID Ação",
                "actionNumber": "Nº Ação",
                "deviationId": "Nº Desvio",
                "actionText": "Descrição da Ação",
                "responsibleName": "Responsável",
                "workCenter": "Centro de Trabalho",
                "families": "Família",
                "finalDate": "Prazo da Ação",
                "status": "Status"
            })

            excel_filename = _excel_path('acoes_desvios.xlsx')

            if os.path.exists(excel_filename):
                os.remove(excel_filename)

            with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
                excel_df.to_excel(writer, sheet_name='AÇÕES', index=False)

            return send_file(
                excel_filename,
                as_attachment=True,
                download_name='acoes_desvios.xlsx'
            )

        return jsonify(df_result.to_dict(orient='records')), 200
    

    except Exception as e:
        print("ERRO /desvios/acoes:", e)
        traceback.print_exc()

        return jsonify({
            "message": f"Erro ao consultar ações: {str(e)}"
        }), 500

@request_processDeviation_bp.route('/desvios/acoes/<int:action_id>', methods=['GET', 'POST'])
def dev_action_detail(action_id):
    """
    Detalhe da ação do desvio.

    Objetivo:
    - deixar o detalhe da ação visualmente igual ao detalhe do desvio;
    - mostrar responsável da ação;
    - mostrar criador do desvio;
    - mostrar data de criação do desvio;
    - numerar ação dentro do próprio desvio;
    - finalizar a ação gravando status real, se a coluna existir;
    - permitir alterar a data da ação sem abrir novo desvio;
    - exibir histórico de datas antigas riscadas na DATA FIM.
    """

    engine = get_engine('jdt')

    with engine.connect() as cnnx:

        action = _get_action_by_id(cnnx, action_id)

        if action is None:
            return redirect('/denied')

        deviation_id = str(action['deviationId'])
        deviation_base = str(action['deviationBase'])
        action_number = int(action['actionNumber'])
        action_id_db = int(action['actionId'])

        check = engine_run_query(
            "SELECT userId FROM JDT_REQUEST_DEV WHERE deviationId = :did",
            'jdt',
            params={"did": deviation_id}
        )

        if len(check.get('userId', [])) == 0:
            return redirect('/denied')

        # =====================================================
        # PERMISSÕES DA AÇÃO
        #
        # Visualizar:
        # - administrador;
        # - criador do desvio;
        # - responsável pela ação.
        #
        # Executar/finalizar/anexar:
        # - administrador;
        # - responsável pela ação.
        #
        # Alterar prazo:
        # - administrador;
        # - criador do desvio.
        # =====================================================
        is_admin = current_user.admin or p_admin.can()

        current_user_id = str(
            current_user.id or ""
        ).strip()

        current_email = str(
            current_user.companyEmail or ""
        ).strip().lower()

        creator_user_id = str(
            action['creatorUserId'] or ""
        ).strip()

        responsible_email = str(
            action['responsibleEmail'] or ""
        ).strip().lower()

        is_creator = (
            current_user_id != ""
            and current_user_id == creator_user_id
        )

        is_responsible = (
            current_email != ""
            and current_email == responsible_email
        )

        can_view_action = (
            is_admin
            or is_creator
            or is_responsible
        )

        if not can_view_action:
            return redirect('/denied')

        can_execute_action = (
            is_admin
            or is_responsible
        )

        can_edit_deadline = (
            is_admin
            or is_creator
        )

        resp = can_execute_action
        admin = '1' if is_admin else '0'

        dev_status = int(action['devStatus']) if pd.notna(action['devStatus']) else 0

        creation_date = action['creationDate']
        deadline = action['deadline']

        # =====================================================
        # HISTÓRICO DE PRAZO:
        # Texto enviado ao JS para mostrar datas antigas riscadas.
        # =====================================================
        deadline_history = ''
        try:
            if pd.notna(action['deadlineHistory']):
                deadline_history = str(action['deadlineHistory'] or '')
        except Exception:
            deadline_history = ''

        creation_date_fmt = (
            pd.to_datetime(creation_date).strftime('%d/%m/%Y')
            if pd.notna(creation_date) else ''
        )

        deadline_fmt = (
            pd.to_datetime(deadline).strftime('%d/%m/%Y')
            if pd.notna(deadline) else ''
        )

        responsible_name = (
            str(action['responsibleName'])
            if pd.notna(action['responsibleName']) else ''
        )

        creator_name = (
            str(action['creatorName'])
            if pd.notna(action['creatorName']) else ''
        )

        action_plan_status = (
            int(action['actionPlanStatus'])
            if pd.notna(action['actionPlanStatus'])
            else 0
        )

        action_status = _get_action_effective_status(
            dev_status,
            action_plan_status,
            deadline
        )

        action_upload_dir = os.path.join(
            APP_PATH,
            "app",
            "static",
            "uploads",
            "deviation",
            "request",
            deviation_id,
            "action_attachment",
            str(action_id_db)
        )
        attachments = []
        if os.path.exists(action_upload_dir):
            attachments = [
                f for f in os.listdir(action_upload_dir)
                if os.path.isfile(os.path.join(action_upload_dir, f))
            ]

        raw_att = "\n\n".join(attachments) + ("\n\n" if attachments else "")

        # =====================================================
        # GET
        # =====================================================
        if request.method == 'GET':

            if 'anexo' in request.args:
                if resp is True:
                    anexo = secure_filename(request.args["anexo"])

                    file_path = os.path.join(
                        APP_PATH, "app", "static", "uploads",
                        "deviation", "request", deviation_id,
                        "action_attachment", str(action_id_db), anexo
                    )

                    if os.path.exists(file_path):
                        os.remove(file_path)

                    return redirect(f'/desvios/acoes/{action_id}')

                return 'ACCESS DENIED'

            diff_days = None

            try:
                if pd.notna(deadline):
                    diff_days = (
                        pd.to_datetime(deadline).normalize()
                        - pd.Timestamp(datetime.now().date())
                    ).days
            except Exception:
                diff_days = None

            user_data = pd.DataFrame([{
                'DETALHES REVISÃO': deviation_id,
                'REVISÃO': action_number,
                'MOTIVO': action['actionText'],
                'CENTRO DE TRABALHO': action['workCenter'],
                'FAMÍLIA': action['families'],
                'DATA DE INICIO': creation_date_fmt,
                'DATA FIM': deadline_fmt,
                'STATUS': action_status,
                'diff_days': diff_days,
                'attachment': raw_att
            }])

            user_data['CENTRO DE TRABALHO'] = user_data['CENTRO DE TRABALHO'].apply(_LIST_UPDATE)
            user_data['FAMÍLIA'] = user_data['FAMÍLIA'].apply(_LIST_UPDATE)

            table = config_table(user_data)

            return render_template(
                'request.processDeviation/dev_action_detail.html',

                table=table,
                userName=responsible_name,
                min_status=action_status,
                idReq=action_id,
                admin=admin,
                sector='AÇÃO',
                firstDate=creation_date_fmt,
                resp=str(int(resp)),
                attachments=attachments,
                has_attachments=bool(attachments),

                actionId=action_id,
                actionNumber=action_number,
                deviationId=deviation_id,
                deviationBase=deviation_base,

                responsibleName=responsible_name,
                creatorName=creator_name,

                initDate=creation_date_fmt,
                deadline=deadline_fmt,

                # =====================================================
                # REGRA DE ALTERAÇÃO DE PRAZO:
                # Envia permissão para o JS mostrar/esconder botão.
                # Proteção principal também existe no POST do backend.
                # =====================================================
                can_edit_deadline=str(int(can_edit_deadline)),

                # =====================================================
                # HISTÓRICO DE PRAZO:
                # Envia datas antigas para o JS exibir riscadas/apagadas.
                # =====================================================
                deadlineHistory=deadline_history
            )

        # =====================================================
        # POST
        # =====================================================
        else:

            payload = request.get_json(silent=True) or {}

            # -------------------------------------------------
            # ALTERAR PRAZO DA AÇÃO
            # -------------------------------------------------
            if payload.get('cmd') == 'alterar_prazo':

                # =====================================================
                # PROTEÇÃO DE BACKEND - ALTERAÇÃO DE PRAZO:
                # Somente ADM/p_admin ou solicitante dono do desvio
                # podem alterar a data da ação sem abrir novo desvio.
                # Responsável pela ação e aprovador comum não podem
                # alterar a data apenas por estes papéis.
                # =====================================================
                if not can_edit_deadline:
                    return jsonify({
                        "message": "Você não possui permissão para alterar o prazo desta ação."
                    }), 403

                new_deadline_raw = payload.get('deadline')

                if not new_deadline_raw:
                    return jsonify({
                        "message": "Informe a nova data da ação."
                    }), 400

                try:
                    new_deadline = pd.to_datetime(new_deadline_raw, errors='raise').strftime('%Y-%m-%d')
                except Exception:
                    return jsonify({
                        "message": "Data inválida. Informe uma data válida."
                    }), 400

                # =====================================================
                # VALIDAÇÃO:
                # Se a nova data for igual à atual, não grava histórico
                # duplicado e não faz update desnecessário.
                # =====================================================
                try:
                    current_deadline_compare = (
                        pd.to_datetime(deadline).strftime('%Y-%m-%d')
                        if pd.notna(deadline) else ''
                    )
                except Exception:
                    current_deadline_compare = ''

                if current_deadline_compare == new_deadline:
                    return jsonify({
                        "message": "A nova data informada é igual ao prazo atual."
                    }), 400

                # =====================================================
                # HISTÓRICO DE PRAZO:
                # Antes de atualizar deadline, grava a data antiga em
                # deadlineHistory no formato dd/MM/yyyy, acumulando com
                # separador de linha dupla.
                # =====================================================
                result = cnnx.execute(
                    text("""
                        UPDATE JDT_REQUEST_DEV_PLAN
                        SET
                            deadlineHistory =
                                ISNULL(deadlineHistory, '') +
                                CASE
                                    WHEN deadline IS NULL THEN ''
                                    ELSE
                                        CONVERT(varchar(10), deadline, 103) +
                                        CHAR(10) + CHAR(10)
                                END,

                            status =
                                CASE
                                    WHEN status = 1 THEN 1

                                    WHEN deadline < CAST(GETDATE() AS DATE)
                                    THEN 5

                                    WHEN status = 5
                                    THEN 5

                                    ELSE status
                                END,

                            deadline = :new_deadline

                        WHERE actionId = :action_id
                    """),
                    {
                        "new_deadline": new_deadline,
                        "action_id": action_id_db
                    }
                )

                if result.rowcount != 1:
                    cnnx.rollback()

                    return jsonify({
                        "message": "A ação não foi encontrada ou mais de uma linha seria alterada."
                    }), 409

                cnnx.commit()

                # =====================================================
                # EMAIL - PRAZO ALTERADO
                # Envia imediatamente ao responsável da ação.
                # Não bloqueia a alteração caso o envio falhe.
                # =====================================================
                try:
                    prazo_antigo_fmt = deadline_fmt

                    prazo_novo_dt = pd.to_datetime(new_deadline, errors='coerce')
                    prazo_novo_fmt = prazo_novo_dt.strftime('%d/%m/%Y') if pd.notna(prazo_novo_dt) else str(new_deadline)

                    msg = Message(
                        f"Prazo de ação alterado - Desvio {deviation_base}",
                        sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                        recipients=[str(action['responsibleEmail'])]
                    )

                    msg.html = render_template(
                        'request.processDeviation/dev_email_action_changed_deadline.html',
                        id=deviation_base,
                        acao=action['actionText'],
                        prazo_antigo=prazo_antigo_fmt,
                        prazo_novo=prazo_novo_fmt
                    )

                    mail.send(msg)

                except Exception as e:
                    print("Erro ao enviar e-mail de prazo alterado:", e)

                return jsonify({
                    "message": "Prazo da ação alterado com sucesso."
                }), 200

            if resp is True:

                # -------------------------------------------------
                # UPLOAD DE ANEXOS
                # -------------------------------------------------
                if request.files.getlist('anexos'):

                    os.makedirs(action_upload_dir, exist_ok=True)

                    oldImages = ""
                    if os.path.exists(action_upload_dir):
                        oldImages = "\n\n".join([
                            f for f in os.listdir(action_upload_dir)
                            if os.path.isfile(os.path.join(action_upload_dir, f))
                        ]) + "\n\n"

                    for file in request.files.getlist('anexos'):
                        if file and file.filename:
                            filename = secure_filename(file.filename)
                            name, ext = os.path.splitext(filename)
                            fn_upper = filename.upper()

                            if oldImages.upper().count(fn_upper) == 0:
                                file.save(os.path.join(action_upload_dir, filename))
                                oldImages += f'{filename}\n\n'
                            else:
                                acum = oldImages.upper().count(name.upper())
                                thisName = f"{name}_({acum}){ext}"
                                file.save(os.path.join(action_upload_dir, thisName))
                                oldImages += f'{thisName}\n\n'

                    return redirect(f'/desvios/acoes/{action_id}')

                # -------------------------------------------------
                # FINALIZAR AÇÃO
                # -------------------------------------------------
                if payload.get('cmd') != 'finalizar':
                    return jsonify({"message": "Comando inválido"}), 400

                has_attachment_now = False

                if os.path.exists(action_upload_dir):
                    has_attachment_now = len([
                        f for f in os.listdir(action_upload_dir)
                        if os.path.isfile(os.path.join(action_upload_dir, f))
                    ]) > 0

                if not has_attachment_now:
                    return jsonify({
                        "message": "É obrigatório anexar pelo menos 1 documento para finalizar a ação."
                    }), 400

                status_col = _get_plan_status_col()

                if not status_col:
                    return jsonify({
                        "message": "Não existe coluna de status na tabela JDT_REQUEST_DEV_PLAN. Não é possível concluir a ação de forma persistente."
                    }), 400

                # Atualiza exclusivamente a ação identificada pelo actionId persistente.
                result = cnnx.execute(
                    text(f"""
                        UPDATE JDT_REQUEST_DEV_PLAN
                        SET [{status_col}] = 1
                        WHERE actionId = :action_id
                    """),
                    {
                        "action_id": action_id_db
                    }
                )

                if result.rowcount != 1:
                    cnnx.rollback()

                    return jsonify({
                        "message": "A ação não foi encontrada ou não pôde ser concluída."
                    }), 409

                cnnx.commit()


                # =====================================================
                # EMAIL - AÇÃO FINALIZADA
                # Envia imediatamente ao solicitante/criador do desvio.
                # Não bloqueia a finalização caso o envio falhe.
                # =====================================================
                try:
                    creator_email_df = pd.read_sql(
                        text("""
                            SELECT TOP 1 companyEmail
                            FROM JDT_USER_DETAILS
                            WHERE (
                                CONVERT(varchar(255), id) = :creator_id
                                OR companyEmail = :creator_id
                            )
                              AND ISNULL(active,1) = 1
                        """),
                        cnnx,
                        params={"creator_id": str(action['creatorUserId'])}
                    )

                    creator_recipients = creator_email_df['companyEmail'].dropna().astype(str).tolist()

                    if creator_recipients:
                        msg = Message(
                            f"Ação finalizada - Desvio {deviation_base}",
                            sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                            recipients=creator_recipients
                        )

                        msg.html = render_template(
                            'request.processDeviation/dev_email_action_finished.html',
                            id=deviation_base,
                            acao=action['actionText'],
                            responsavel=responsible_name
                        )

                        mail.send(msg)

                except Exception as e:
                    print("Erro ao enviar e-mail de ação finalizada:", e)

                return jsonify({
                    "message": "Ação finalizada com sucesso."
                }), 200

            return 'ACCESS DENIED'


@request_processDeviation_bp.route('/desvios/pop/pdf')
def dev_pop_pdf():
    path = _deviation_pop_pdf_path()

    if not os.path.exists(path):
        abort(404)

    return send_file(path)


# V2