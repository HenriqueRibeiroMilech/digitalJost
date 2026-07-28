# mon_fri_h_24_processDeviationCheck.py
from datetime import datetime
import pyodbc
import pandas as pd

from app.services.run_h_24_scheduler import env
from app.utils.constants import CNNX_JDT
from app.utils.email_utils import send_email_with_attachment


def base_dev(dev_id: str) -> str:
    """
    Retorna a base do desvio (AAAA-NNNN) sem a revisão; evita usar slicing [:-2].
    Ex.: 2026-0001-3 -> 2026-0001
    """
    try:
        a, n, *_ = str(dev_id).split("-")
        return f"{a}-{n}"
    except Exception:
        return str(dev_id)


def get_digital_user_id(cnnx) -> str:
    """
    Busca o id do usuário 'Digital JOST' por e-mail institucional.
    Caso não exista, retorna o fallback 'Digital.jost' para não quebrar a execução.
    """
    try:
        df = pd.read_sql(
            "SELECT TOP 1 id FROM JDT_USER_DETAILS WHERE companyEmail = ?",
            cnnx,
            params=['noreply.digitaljost@randon.com.br']
        )
        if not df.empty:
            return str(df['id'].iloc[0])
    except Exception:
        pass
    return 'Digital.jost'


def default(logger):
    # Conexão pyodbc
    cnnx = pyodbc.connect(CNNX_JDT)
    cursor = cnnx.cursor()

    # ------------- Helpers de atualização -----------------

    def deviation_automatic_start(row):
        cursor.execute(
            """
            UPDATE JDT_REQUEST_DEV
               SET initDate = GETDATE(),
                   status = 5
             WHERE deviationId = ?
            """,
            (row['deviationId'],)
        )

    def deviation_automatic_end(row):
        cursor.execute(
            """
            UPDATE JDT_REQUEST_DEV
               SET status = 6
             WHERE deviationId = ?
            """,
            (row['deviationId'],)
        )

    def deviation_automatic_refusal(row):
        cursor.execute(
            """
            UPDATE JDT_REQUEST_DEV
               SET status = 2
             WHERE deviationId = ?
            """,
            (row['deviationId'],)
        )

    def approvers_automatic_refusal(row, digital_id):
        """
        Marca como reprovado o setor sem retorno após 48h.
        """
        cursor.execute(
            """
            UPDATE JDT_REQUEST_DEV_CONFIG_STATUS
               SET approverId = ?,
                   status = 2,
                   textDenied = 'Reprovado automaticamente devido ao não retorno após 48h.'
             WHERE deviationId = ?
               AND sectorId = ?
            """,
            (digital_id, row['deviationId'], int(row['sectorId']))
        )

    # ------------- Envio de e-mails -----------------------

    def send_email_revision(row):
        # e-mail do solicitante
        user_mail = pd.read_sql(
            "SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = ?",
            cnnx,
            params=[row['userId']]
        )['companyEmail'].values.tolist()

        template = env.get_template('request.processDeviation/dev_email_revision.html')
        msg_html = template.render(id=base_dev(row['deviationId']))

        send_email_with_attachment(
            subject=f"Desvio de processo - Nº {row['deviationId']}",
            body=msg_html,
            to=user_mail,
            sender_name='Transformação Digital JOST',
            sender_email='noreply.digitaljost@randon.com.br'
        )

    def send_email_scheduled(row):
        # e-mails dos aprovadores do setor
        user_mail = pd.read_sql(
            "SELECT companyEmail FROM JDT_VIEW_REQUEST_DEV_APPROVERS WHERE sector = ?",
            cnnx,
            params=[row['approverSector']]
        )['companyEmail'].values.tolist()

        template = env.get_template('request.processDeviation/dev_email_scheduled.html')
        msg_html = template.render(id=base_dev(row['deviationId']), solicitante=row.get('name', ''))

        send_email_with_attachment(
            subject=f"Desvio de processo - Nº {row['deviationId']}",
            body=msg_html,
            to=user_mail,
            sender_name='Transformação Digital JOST',
            sender_email='noreply.digitaljost@randon.com.br'
        )

    # ------------- Relógio de referência ------------------
    now = datetime.now()

    # ------------- Pendências por setor (VIEW MANAGE) -----
    try:
        df_manage = pd.read_sql("SELECT * FROM JDT_VIEW_REQUEST_DEV_MANAGE", cnnx)
    except Exception as e:
        logger.error("Falha ao ler VIEW MANAGE: %s", e)
        df_manage = pd.DataFrame()

    if not df_manage.empty:
        # datas robustas
        df_manage['openDate'] = pd.to_datetime(df_manage.get('openDate'), errors='coerce', dayfirst=True)

        # máscaras
        mask_valid_date = df_manage['openDate'].notna()
        mask_over_48h = (now - df_manage['openDate']) >= pd.Timedelta(hours=48)
        mask_status_zero = df_manage.get('status', 0).eq(0)

        # reprova automaticamente setores sem retorno em 48h
        digital_id = get_digital_user_id(cnnx)
        df_manage[mask_valid_date & mask_over_48h & mask_status_zero] \
            .apply(lambda r: approvers_automatic_refusal(r, digital_id), axis=1)

        # lembrete aos aprovadores (somente após 4h para evitar spam básico)
        mask_over_4h = (now - df_manage['openDate']) >= pd.Timedelta(hours=4)
        # só para quem está sem 'approverName' e ainda pendente
        mask_no_approver_name = df_manage.get('approverName').isna() if 'approverName' in df_manage.columns else mask_status_zero

        df_manage[mask_valid_date & mask_over_4h & mask_no_approver_name] \
            .apply(send_email_scheduled, axis=1)

    # ------------- Atualizações por desvio (tabela principal) -------------
    try:
        df = pd.read_sql("SELECT * FROM JDT_REQUEST_DEV", cnnx)
    except Exception as e:
        logger.error("Falha ao ler JDT_REQUEST_DEV: %s", e)
        df = pd.DataFrame()

    if not df.empty:
        # datas robustas
        for col in ('initDate', 'finalDate', 'openDate'):
            df[col] = pd.to_datetime(df.get(col), errors='coerce', dayfirst=True)

        # e-mail de revisão (faltando 5 dias para vencer ou já vencido) — status 5/6
        mask_valid_final = df['finalDate'].notna()
        mask_within_5_days = (now - df['finalDate']) >= pd.Timedelta(days=-5)
        mask_status_56 = df['status'].isin([5, 6])

        df[mask_valid_final & mask_within_5_days & mask_status_56].apply(send_email_revision, axis=1)

        # recusa automática se aberto há 48h e status geral = 0
        mask_valid_open = df['openDate'].notna()
        mask_over_48h_general = (now - df['openDate']) >= pd.Timedelta(hours=48)
        mask_status_0 = df['status'].eq(0)

        df[mask_valid_open & mask_over_48h_general & mask_status_0].apply(deviation_automatic_refusal, axis=1)

        # aprovado (1) e com initDate já alcançada -> EM ANDAMENTO (5)
        mask_valid_init = df['initDate'].notna()
        df[df['status'].eq(1) & mask_valid_init & (df['initDate'] <= now)] \
            .apply(deviation_automatic_start, axis=1)

        # em andamento (5) e passou do finalDate -> VENCIDO (6)
        df[df['status'].eq(5) & mask_valid_final & (df['finalDate'] < now)] \
            .apply(deviation_automatic_end, axis=1)

    # ------------- Persistência ---------------------------
    try:
        cnnx.commit()
    except Exception as e:
        logger.error("Falha no commit do job h_24: %s", e)
    finally:
        try:
            cnnx.close()
        except Exception:
            pass