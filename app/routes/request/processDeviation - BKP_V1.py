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
                  AND ISNULL(status, 0) = 0
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

# ------------------------- Rotas -------------------------
@request_processDeviation_bp.route('/desvios', methods=['GET'])
def dev_get():
    return render_template('request.processDeviation/dev_home.html')

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
    return render_template('request.processDeviation/dev_pop.html')

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
            df = pd.read_sql(
                text("""
                    SELECT *
                    FROM JDT_REQUEST_DEV
                    WHERE deviationId = :did AND status = 2
                """),
                cnnx, params={"did": request.args['editar']}
            ).astype(str)

            df_plan = pd.read_sql(
                text("""
                    SELECT *
                    FROM JDT_REQUEST_DEV_PLAN
                    WHERE deviationId = :did
                      AND (SELECT status FROM JDT_REQUEST_DEV WHERE deviationId = :did) = 2
                """),
                cnnx, params={"did": request.args['editar']}
            ).astype(str).to_json()

        if df is not None and not df.empty:
            revisao = int(df['deviationId'].iloc[0].split('-')[2]) + 1

            if df['status'].iloc[0] == '2':
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
                    text("""INSERT INTO JDT_REQUEST_DEV_REFUSED_PLAN
                            SELECT *, GETDATE()
                            FROM JDT_REQUEST_DEV_PLAN
                            WHERE deviationId = :did"""),
                    {"did": onapproving['deviationId'][0]}
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

            # copia plano da revisão -0 para a nova revisão
            plan_to_new_revision = pd.read_sql(
                text("""SELECT * FROM JDT_REQUEST_DEV_PLAN WHERE deviationId = :did"""),
                cnnx, params={"did": f"{request.args['id']}-0"}
            )

            for _, row in plan_to_new_revision.iterrows():
                cnnx.execute(
                    text("""INSERT INTO JDT_REQUEST_DEV_PLAN (deviationId, text, userId, deadline)
                            VALUES (:dev, :txt, :uid, :dl)"""),
                    {"dev": new_id, "txt": row['text'], "uid": row['userId'], "dl": row['deadline']}
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
                        type=request.args.get('tipo')
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

                    # se todos setores aprovaram -> status geral = 1; se já passou data de início -> 5
                    dev_min_status = pd.read_sql(
                        text("""SELECT MIN(status) AS status
                                FROM JDT_REQUEST_DEV_CONFIG_STATUS
                                WHERE deviationId = :did"""),
                        cnnx, params={"did": request.args['id']}
                    )['status'][0]

                    if dev_min_status == 1:
                        approvers = pd.read_sql(
                            text("""SELECT approverEmail FROM JDT_VIEW_REQUEST_DEV_MANAGE WHERE deviationId = :did"""),
                            cnnx, params={"did": request.args['id']}
                        )['approverEmail'].values.tolist()

                        cnnx.execute(
                            text("""UPDATE JDT_REQUEST_DEV SET status = 1 WHERE deviationId = :did"""),
                            {"did": request.args['id']}
                        )
                        cnnx.execute(
                            text("""UPDATE JDT_REQUEST_DEV
                                       SET status = 5, initDate = CONVERT(DATE, GETDATE())
                                     WHERE deviationId = :did AND initDate <= CAST(GETDATE() AS DATE)"""),
                            {"did": request.args['id']}
                        )
                        cnnx.commit()

                        msg = Message(
                            f"Pedido de desvio - ID {request.args['id']}",
                            sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                            recipients=['jost_lideres@empresasrandon.com.br', 'Jost_Qualidade@randon.com.br', requesterEmail] + approvers
                        )
                        msg.html = render_template('request.processDeviation/dev_email_approved.html', id=base_dev(request.args['id']))
                        mail.send(msg)

                        # e-mail para área do setor aprovado
                        area_email = pd.read_sql(
                            text("""SELECT companyEmail FROM JDT_VIEW_REQUEST_DEV_APPROVERS WHERE sector = :sector"""),
                            cnnx, params={"sector": _APPROVERS_TEAMS[userSector][1]}
                        )['companyEmail'].values.tolist()
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
                    return render_template('request.processDeviation/dev_sector_refuse.html', id=request.args['id'])
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
    if p_admin.can():
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
        # NOVA REGRA para permissão de edição (resp):
        # dono OU admin OU p_admin OU aprovador ATIVO do setor do desvio
        owner_or_admin = (
            str(pd.read_sql(
                text("SELECT userId FROM JDT_REQUEST_DEV WHERE deviationId LIKE :prefix"),
                cnnx, params={"prefix": f"{requestId}%"}
            )['userId'][0]) == str(current_user.id)
            or current_user.admin
            or p_admin.can()
        )
        allowed_active_approver = _is_active_approver_for_deviation(cnnx, current_user.id, requestId)
        resp = owner_or_admin or allowed_active_approver
        admin = '1' if (current_user.admin or p_admin.can()) else '0'

        if request.method == 'GET':
            if 'cancelar' in request.args:
                if owner_or_admin:
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

            # IMPORTANTE:
            # não travar mais a finalização por falta de anexo no front
            has_attachments = True

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
                attachments=attachments,
                has_attachments=has_attachments
            )

        else:
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
                    if data['status'][0] == 0 and (is_admin or str(data['userId'][0]) == str(current_user.id)):
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

                    if int(data['status'][0]) in (5, 6):
                        cnnx.execute(
                            text("""UPDATE JDT_REQUEST_DEV SET status = 4 WHERE deviationId = :did"""),
                            {"did": did}
                        )
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
        
        

        return render_template(
            'request.processDeviation/dev_detail_physical.html',
            dataframe=df.to_json(),
            df_plan=df_plan.to_json(),
            idReq=request.args['id'],
            df_result=aprovadores.to_json()
        )
    
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