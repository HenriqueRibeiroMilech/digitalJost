# mon_fri_h_24_processDeviationCheck.py
from datetime import datetime
from typing import Optional, List
import pyodbc
import pandas as pd

from app.services.run_h_24_scheduler import env
from app.utils.constants import CNNX_JDT
from app.utils.email_utils import send_email_with_attachment


# ====================== Utilidades existentes ======================

def base_dev(dev_id: str) -> str:
    """
    Retorna a base do desvio (AAAA-NNNN) sem a revisão; evita usar slicing[:-2].
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


# ====================== NOVOS HELPERS — FILTRAGEM DE DESTINATÁRIOS ======================

def _filter_active_emails(cnnx, emails: List[str]) -> List[str]:
    """
    Retorna apenas e-mails de usuários ATIVOS (JDT_USER_DETAILS.active=1).
    Remove duplicados e vazios.
    """
    emails = [e for e in (emails or []) if e]
    if not emails:
        return []
    placeholders = ",".join(["?"] * len(emails))
    try:
        df = pd.read_sql(
            f"""
            SELECT companyEmail
            FROM JDT_USER_DETAILS
            WHERE companyEmail IN ({placeholders})
              AND ISNULL(active, 1) = 1
            """,
            cnnx, params=emails
        )
        return df['companyEmail'].dropna().astype(str).tolist()
    except Exception:
        # fallback conservador
        return list(dict.fromkeys(emails))


def get_active_approver_emails_for_deviation_sector(cnnx, deviation_id: str, approver_sector: str) -> List[str]:
    """
    Retorna e-mails dos aprovadores ATIVOS vinculados ao SETOR (e opcionalmente à UNIDADE) do desvio.
    1) Tenta via VIEW JDT_VIEW_REQUEST_DEV_APPROVERS (mais simples).
    2) Caso falhe/ausente, tenta via JOIN direto (ajustar nomes conforme o seu schema).
    """
    emails: List[str] = []

    # (A) Usando VIEW de aprovadores
    try:
        df = pd.read_sql(
            """
            SELECT U.companyEmail
            FROM JDT_VIEW_REQUEST_DEV_APPROVERS A
            JOIN JDT_USER_DETAILS U       ON U.companyEmail = A.companyEmail
            JOIN JDT_REQUEST_DEV     D    ON D.deviationId  = ?
            WHERE A.sector = ?
              AND ISNULL(U.active, 1) = 1
              -- Se a VIEW tiver coluna de unidade e você quiser filtrar pela mesma unidade do desvio, descomente:
              -- AND (A.unit IS NULL OR A.unit = D.unit)
            """,
            cnnx, params=[deviation_id, approver_sector]
        )
        if not df.empty:
            emails = df['companyEmail'].dropna().astype(str).tolist()
    except Exception:
        emails = []

    # (B) Fallback por JOINs diretos (ajuste o nome da tabela de aprovadores se for diferente no seu schema)
    if not emails:
        try:
            df = pd.read_sql(
                """
                SELECT U.companyEmail
                FROM JDT_REQUEST_DEV D
                JOIN JDT_REQUEST_DEV_SECTORS S    ON S.id = D.sectorId
                JOIN JDT_REQUEST_DEV_APPROVERS A  ON A.sectorId = S.id          -- ajuste se necessário
                JOIN JDT_USER_DETAILS U           ON U.id = A.userId
                WHERE D.deviationId = ?
                  AND S.sector = ?
                  AND ISNULL(U.active, 1) = 1
                """,
                cnnx, params=[deviation_id, approver_sector]
            )
            if not df.empty:
                emails = df['companyEmail'].dropna().astype(str).tolist()
        except Exception:
            emails = []

    return [e for e in dict.fromkeys(emails) if e]


# ====================== Helpers de gestores (AJUSTADOS p/ ATIVOS) ======================

def get_manager_email_by_person(cnnx, responsible_email: str) -> Optional[str]:
    """
    Gestor direto da pessoa (apenas se o gestor estiver ATIVO).
    """
    if not responsible_email:
        return None
    try:
        df = pd.read_sql(
            """
            SELECT TOP 1 M.companyEmail AS managerEmail
            FROM JDT_USER_DETAILS U
            JOIN JDT_USER_DETAILS M ON M.companyEmail = U.managerEmail
            WHERE U.companyEmail = ?
              AND M.companyEmail IS NOT NULL
              AND LEN(M.companyEmail) > 3
              AND ISNULL(M.active, 1) = 1
            """,
            cnnx, params=[responsible_email]
        )
        if not df.empty:
            return df['managerEmail'].iloc[0]
    except Exception:
        pass
    return None


def get_manager_email_by_sector_of_deviation(cnnx, deviation_id: str) -> Optional[str]:
    """
    Gestor do SETOR do desvio (apenas se o gestor estiver ATIVO).
    """
    try:
        df = pd.read_sql(
            """
            SELECT TOP 1 M.companyEmail AS managerEmail
            FROM JDT_REQUEST_DEV D
            JOIN JDT_REQUEST_DEV_SECTORS S ON S.id = D.sectorId
            LEFT JOIN JDT_USER_DETAILS M ON M.companyEmail = S.managerEmail
            WHERE D.deviationId = ?
              AND S.managerEmail IS NOT NULL
              AND LEN(S.managerEmail) > 3
              AND ISNULL(M.active, 1) = 1
            """,
            cnnx, params=[deviation_id]
        )
        if not df.empty:
            return df['managerEmail'].iloc[0]
    except Exception:
        pass
    return None


def resolve_manager_for_action(cnnx, responsible_email: str, deviation_id: str) -> List[str]:
    """
    Opção C (misto): retorna a lista de destinatários de escalonamento de atraso.
    - responsável SEMPRE (se ativo)
    - gestor da pessoa (se houver e ativo)
    - gestor do setor do desvio (se houver e ativo)
    Sem duplicações e sem vazios.
    """
    emails: List[str] = []
    if responsible_email:
        emails.append(responsible_email)
    # gestor direto da pessoa (ativo)
    mgr_person = get_manager_email_by_person(cnnx, responsible_email)
    if mgr_person:
        emails.append(mgr_person)
    # gestor do setor do desvio (ativo)
    mgr_sector = get_manager_email_by_sector_of_deviation(cnnx, deviation_id)
    if mgr_sector:
        emails.append(mgr_sector)

    # Somente ativos e sem duplicidade
    emails = _filter_active_emails(cnnx, list(dict.fromkeys(emails)))
    return emails


# ============================== JOB ==============================

def default(logger):
    # Conexão pyodbc
    cnnx = pyodbc.connect(CNNX_JDT)
    cursor = cnnx.cursor()

    # I NEW CODE
    cursor.execute("SELECT DB_NAME(), @@SERVERNAME")    
    db_info = cursor.fetchone()
    logger.info(
        f"Conectado em Banco={db_info[0]} | Servidor={db_info[1]}"
    )
    # F NEW CODE

    # ------------- Helpers de atualização -----------------
    '''
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
    '''
    # I NEW CODE
    def deviation_automatic_start(row):

        logger.info(
            f"Iniciando UPDATE 1->5 para {row['deviationId']}"
        )

        cursor.execute(
            """
            UPDATE JDT_REQUEST_DEV
            SET initDate = GETDATE(),
                status = 5
            WHERE deviationId = ?
            """,
            (row['deviationId'],)
        )

        logger.info(
            f"Rows afetadas 1->5: {cursor.rowcount}"
        )
    # F NEW CODE

    '''
    def deviation_automatic_end(row):
        cursor.execute(
            """
            UPDATE JDT_REQUEST_DEV
            SET status = 6
            WHERE deviationId = ?
            """,
            (row['deviationId'],)
        )

    OU

    def deviation_automatic_end(row):

        logger.info(
            f"Iniciando UPDATE 5->6 para {row['deviationId']}"
        )

        cursor.execute(
            """
            UPDATE JDT_REQUEST_DEV
            SET status = 6
            WHERE deviationId = ?
            """,
            (row['deviationId'],)
        )

        logger.info(
            f"Rows afetadas 5->6: {cursor.rowcount}"
        )
    '''

    # I NEW CODE
    def deviation_automatic_end(row):

        logger.info(
            f"Iniciando UPDATE 5->6 para {row['deviationId']}"
        )

        cursor.execute(
            """
            UPDATE JDT_REQUEST_DEV
            SET status = 6
            WHERE deviationId = ?
            """,
            (row['deviationId'],)
        )

        logger.info(
            f"Rows afetadas 5->6: {cursor.rowcount}"
        )

        cursor.execute(
            """
            SELECT status
            FROM JDT_REQUEST_DEV
            WHERE deviationId = ?
            """,
            (row['deviationId'],)
        )

        result = cursor.fetchone()

        logger.info(
            f"Status após UPDATE de {row['deviationId']}: {result[0]}"
        )
        cnnx.commit()

        cursor.execute("""
            SELECT status
            FROM JDT_REQUEST_DEV
            WHERE deviationId = ?
        """, (row['deviationId'],))

        logger.info(
            f"Status após COMMIT IMEDIATO de {row['deviationId']}: {cursor.fetchone()[0]}"
        )
    # F NEW CODE

    def deviation_automatic_refusal(row):
        cursor.execute(
            """
            UPDATE JDT_REQUEST_DEV
            SET status = 2
            WHERE deviationId = ?
            AND status = 0
            """,
            (row['deviationId'],)
        )

        affected_rows = cursor.rowcount

        if affected_rows != 1:
            logger.warning(
                "Recusa automática não alterou o desvio %s. Rows=%s",
                row['deviationId'],
                affected_rows
            )
            return

        # Confirma a recusa do desvio e as recusas dos setores
        # executadas anteriormente na mesma conexão.
        cnnx.commit()

        logger.info(
            "Desvio %s recusado automaticamente após 48h úteis.",
            row['deviationId']
        )

        try:
            df_user = pd.read_sql(
                """
                SELECT companyEmail
                FROM JDT_USER_DETAILS
                WHERE id = ?
                AND ISNULL(active, 1) = 1
                """,
                cnnx,
                params=[row['userId']]
            )

            user_mail = (
                df_user['companyEmail']
                .dropna()
                .astype(str)
                .tolist()
            )

        except Exception as e:
            logger.error(
                "Falha ao localizar solicitante do desvio %s: %s",
                row['deviationId'],
                e
            )
            user_mail = []

        if not user_mail:
            return

        template = env.get_template(
            'request.processDeviation/dev_email_refused.html'
        )

        msg_html = template.render(
            just=(
                'Reprovado automaticamente devido ao '
                'não retorno após 48h.'
            ),
            id=base_dev(row['deviationId']),
            approverName='Digital JOST'
        )

        email_sent = send_email_with_attachment(
            subject=f"Pedido de desvio - ID {row['deviationId']}",
            body=msg_html,
            to=user_mail,
            sender_name='Transformação Digital JOST',
            sender_email='noreply.digitaljost@randon.com.br'
        )

        if not email_sent:
            logger.error(
                "Desvio %s foi recusado, mas o e-mail não foi enviado.",
                row['deviationId']
            )

    def approvers_automatic_refusal(row, digital_id):
        """
        Marca como reprovado o setor sem retorno após 48h.
        """
        approver_sector = str(row.get('approverSector') or row.get('sector') or row.get('sectorId') or '')

        cursor.execute(
            """
            UPDATE JDT_REQUEST_DEV_CONFIG_STATUS
            SET approverId = ?,
                status = 2,
                textDenied = ?
            WHERE deviationId = ?
            AND sectorId = ?
            AND ISNULL(status, 0) = 0
            """,
            (
                digital_id,
                (
                    f"Reprovado automaticamente pela área "
                    f"{approver_sector} devido ao não retorno "
                    f"após 48h úteis."
                ),
                row['deviationId'],
                int(row['sectorId'])
            )
        )


    # ------------- Envio de e-mails -----------------------

    def send_email_revision(row):
        # e-mail do solicitante (somente se ATIVO)
        try:
            df_user = pd.read_sql(
                """
                SELECT companyEmail
                FROM JDT_USER_DETAILS
                WHERE id = ?
                  AND ISNULL(active,1) = 1
                """,
                cnnx, params=[row['userId']]
            )
            user_mail = df_user['companyEmail'].dropna().astype(str).tolist()
        except Exception:
            user_mail = []

        if not user_mail:
            return  # solicitante inativo/ausente -> sem envio
        
        try:
            final_date = pd.to_datetime(row['finalDate'], errors='coerce')
            if pd.notna(final_date) and final_date.date() == now.date():
                manager_mail = get_manager_email_by_person(cnnx, user_mail[0])
                if manager_mail:
                    user_mail.append(manager_mail)
                user_mail = list(dict.fromkeys(user_mail))
        except Exception:
            pass


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
        """
        Lembrete aos APROVADORES do setor do desvio (apenas ATIVOS e pertinentes).
        """
        approver_sector = str(row.get('approverSector') or row.get('sector') or '')
        user_mail = get_active_approver_emails_for_deviation_sector(
            cnnx,
            str(row['deviationId']),
            approver_sector
        )
        if not user_mail:
            return

        template = env.get_template('request.processDeviation/dev_email_scheduled.html')
        msg_html = template.render(id=base_dev(row['deviationId']), solicitante=row.get('name', ''))

        send_email_with_attachment(
            subject=f"Desvio de processo - Nº {row['deviationId']}",
            body=msg_html,
            to=user_mail,  # já filtrado
            sender_name='Transformação Digital JOST',
            sender_email='noreply.digitaljost@randon.com.br'
        )

    # ------------- Relógio de referência ------------------
# ------------- Relógio de referência ------------------
    now = datetime.now()

    # ------------- Cálculo de horas úteis -----------------
    def business_hours_between(start_date, end_date):
        """
        Calcula horas úteis considerando apenas segunda a sexta.
        Não considera feriados.
        """
        try:
            start = pd.to_datetime(start_date, errors='coerce')
            end = pd.to_datetime(end_date, errors='coerce')

            if pd.isna(start) or pd.isna(end):
                return 0

            if end <= start:
                return 0

            total_hours = 0
            current = start

            while current < end:
                next_day = current.normalize() + pd.Timedelta(days=1)
                chunk_end = min(end, next_day)

                if current.weekday() < 5:
                    total_hours += (chunk_end - current).total_seconds() / 3600

                current = chunk_end

            return total_hours

        except Exception:
            return 0


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
        mask_over_48h   = df_manage['openDate'].apply(lambda d: business_hours_between(d, now) >= 48)
        mask_status_zero = df_manage.get('status', 0).eq(0)

        # reprova automaticamente setores sem retorno em 48h
        digital_id = get_digital_user_id(cnnx)
        df_manage[mask_valid_date & mask_over_48h & mask_status_zero] \
            .apply(lambda r: approvers_automatic_refusal(r, digital_id), axis=1)

        # lembrete aos aprovadores (somente após 4h para evitar spam básico)
        mask_over_4h = (now - df_manage['openDate']) >= pd.Timedelta(hours=4)

        mask_under_48h = df_manage['openDate'].apply(lambda d: business_hours_between(d, now) < 48)

        # só para quem está sem 'approverName' e ainda pendente
        mask_no_approver_name = df_manage.get('approverName').isna() if 'approverName' in df_manage.columns else mask_status_zero

        df_manage[
            mask_valid_date
            & mask_over_4h
            & mask_under_48h
            & mask_status_zero
            & mask_no_approver_name
        ].apply(send_email_scheduled, axis=1)

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

        # I NEW CODE
        logger.info(f"Total de desvios carregados: {len(df)}")

        try:
            logger.info(
                f"Distribuição de status: {df['status'].value_counts(dropna=False).to_dict()}"
            )
        except Exception as e:
            logger.error(f"Erro ao analisar status: {e}")
        # F NEW CODE

        # e-mail de revisão (faltando 5 dias para vencer ou já vencido) — status 5/6
        mask_valid_final   = df['finalDate'].notna()
        mask_within_5_days = (now - df['finalDate']) >= pd.Timedelta(days=-5)
        mask_status_56     = df['status'].isin([5, 6])

        df[mask_valid_final & mask_within_5_days & mask_status_56].apply(send_email_revision, axis=1)

        # recusa automática se aberto há 48h e status geral = 0
        mask_valid_open     = df['openDate'].notna()
        mask_over_48h_gen   = df['openDate'].apply(lambda d: business_hours_between(d, now) >= 48)
        mask_status_0       = df['status'].eq(0)

        df[mask_valid_open & mask_over_48h_gen & mask_status_0].apply(deviation_automatic_refusal, axis=1)

        '''
        # aprovado (1) e com initDate já alcançada -> EM ANDAMENTO (5)
        mask_valid_init = df['initDate'].notna()
        df[df['status'].eq(1) & mask_valid_init & (df['initDate'] <= now)] \
            .apply(deviation_automatic_start, axis=1)
        '''
        # I NEW CODE
        # aprovado (1) e com initDate já alcançada -> EM ANDAMENTO (5)

        mask_valid_init = df['initDate'].notna()

        status1 = df[
            df['status'].eq(1)
            & mask_valid_init
            & (df['initDate'] <= now)
        ]

        logger.info(f"Elegíveis 1->5: {len(status1)}")

        for _, r in status1.iterrows():
            logger.info(
                f"1->5 | {r['deviationId']} | "
                f"status={r['status']} | "
                f"initDate={r['initDate']}"
            )

        if not status1.empty:
            status1.apply(
                deviation_automatic_start,
                axis=1
            )
        # F NEW CODE

        '''
        # em andamento (5) e passou do finalDate -> VENCIDO (6)
        df[df['status'].eq(5) & mask_valid_final & (df['finalDate'] < now)] \
            .apply(deviation_automatic_end, axis=1)
        '''
        # I NEW CODE
        status5 = df[
            df['status'].eq(5)
            & mask_valid_final
            & (df['finalDate'] < now)
        ]

        logger.info(f"Elegíveis 5->6: {len(status5)}")

        for _, r in status5.iterrows():
            logger.info(
                f"5->6 | {r['deviationId']} | "
                f"status={r['status']} | "
                f"finalDate={r['finalDate']}"
            )

        if not status5.empty:
            status5.apply(
                deviation_automatic_end,
                axis=1
            )
        # F NEW CODE

    # ------------- AÇÕES DO PLANO (lembretes e atraso) -------------
    try:
        df_actions = pd.read_sql(
            """
            SELECT
                P.actionId,
                P.deviationId,
                P.[text],
                P.userId AS responsibleEmail,
                P.deadline,
                ISNULL(P.status, 0) AS status,
                P.lastReminderAt,
                P.overdueNotifiedAt,
                D.status AS deviationStatus
            FROM JDT_REQUEST_DEV_PLAN P
            INNER JOIN JDT_REQUEST_DEV D
                ON D.deviationId = P.deviationId
            WHERE ISNULL(P.status, 0) <> 1
            AND D.status IN (5, 6)
            """,
            cnnx
        )
    except Exception as e:
        logger.error("Falha ao ler JDT_REQUEST_DEV_PLAN: %s", e)
        df_actions = pd.DataFrame()

    if not df_actions.empty:
        # datas robustas
        df_actions['deadline']        = pd.to_datetime(df_actions['deadline'], errors='coerce', dayfirst=True)
        df_actions['lastReminderAt']  = pd.to_datetime(df_actions['lastReminderAt'], errors='coerce')
        df_actions['overdueNotifiedAt'] = pd.to_datetime(df_actions['overdueNotifiedAt'], errors='coerce')

        def render_template_html(name: str, **kwargs):
            tpl = env.get_template(f'request.processDeviation/{name}.html')
            return tpl.render(**kwargs)

        def send_to(recipients: List[str], subject: str, html: str) -> bool:
            if not recipients:
                return False

            recipients = _filter_active_emails(
                cnnx,
                list(dict.fromkeys(recipients))
            )

            if not recipients:
                return False

            return send_email_with_attachment(
                subject=subject,
                body=html,
                to=recipients,
                sender_name='Transformação Digital JOST',
                sender_email='noreply.digitaljost@randon.com.br'
            )

        for _, r in df_actions.iterrows():
            # Ignora registros sem deadline válido
            if pd.isna(r['deadline']):
                continue

            base = base_dev(r['deviationId'])
            prazo_fmt = r['deadline'].strftime('%d/%m/%Y')

            # =====================================================
            # REGRAS DE LEMBRETE DE AÇÃO
            #
            # Antes:
            # - D-5 era uma faixa entre 5 e 1 dias, podendo enviar
            #   lembrete diariamente.
            #
            # Agora:
            # - D-5 envia somente quando faltam exatamente 5 dias;
            # - D-1 envia somente quando falta exatamente 1 dia;
            # - HOJE envia somente no dia do prazo;
            # - ATRASO só considera atrasado a partir do dia seguinte.
            # =====================================================
            deadline_date = r['deadline'].date()
            today_date = now.date()
            days_until_deadline = (deadline_date - today_date).days

            is_d5 = days_until_deadline == 5
            is_d1 = days_until_deadline == 1
            is_today = days_until_deadline == 0

            # Anti-spam: 1 lembrete por dia
            already_reminded_today = (
                pd.notna(r['lastReminderAt'])
                and r['lastReminderAt'].date() == today_date
            )

            try:
                if (
                    (is_d5 or is_d1 or is_today)
                    and not already_reminded_today
                ):
                    email_sent = False

                    if is_today:
                        html = render_template_html(
                            'dev_email_action_today',
                            id=base,
                            acao=r['text'],
                            prazo=prazo_fmt
                        )

                        email_sent = send_to(
                            [r['responsibleEmail']],
                            f"Prazo HOJE - Desvio {base}",
                            html
                        )

                    else:
                        html = render_template_html(
                            'dev_email_action_reminder',
                            id=base,
                            acao=r['text'],
                            prazo=prazo_fmt
                        )

                        assunto = (
                            f"Lembrete (D-5) - Desvio {base}"
                            if is_d5
                            else f"Lembrete (D-1) - Desvio {base}"
                        )

                        email_sent = send_to(
                            [r['responsibleEmail']],
                            assunto,
                            html
                        )

                    if email_sent:
                        cursor.execute(
                            """
                            UPDATE JDT_REQUEST_DEV_PLAN
                            SET lastReminderAt = GETDATE()
                            WHERE actionId = ?
                            """,
                            (int(r['actionId']),)
                        )

                        logger.info(
                            "Lembrete enviado | actionId=%s",
                            r['actionId']
                        )

                    else:
                        logger.warning(
                            "Lembrete não enviado | actionId=%s",
                            r['actionId']
                        )

            except Exception as e:
                logger.error(
                    "Falha ao enviar lembrete de ação actionId=%s: %s",
                    r['actionId'],
                    e,
                    exc_info=True
                )

            # Atraso:
            # Só considera atraso a partir do dia seguinte ao prazo.
            # Exemplo:
            # - prazo 22/05
            # - no dia 22/05 ainda é HOJE
            # - a partir de 23/05 vira ATRASO
            is_late = deadline_date < today_date
            already_overdue_notified = pd.notna(r['overdueNotifiedAt'])

            if is_late and not already_overdue_notified:
                try:
                    recipients = resolve_manager_for_action(
                        cnnx,
                        r['responsibleEmail'],
                        r['deviationId']
                    )

                    if recipients:
                        html = render_template_html(
                            'dev_email_action_overdue',
                            id=base,
                            acao=r['text'],
                            prazo=prazo_fmt,
                            responsavel=r['responsibleEmail']
                        )

                        email_sent = send_to(
                            recipients,
                            f"ACAO EM ATRASO - Desvio {base}",
                            html
                        )

                        if email_sent:
                            cursor.execute(
                                """
                                UPDATE JDT_REQUEST_DEV_PLAN
                                SET overdueNotifiedAt = GETDATE()
                                WHERE actionId = ?
                                """,
                                (int(r['actionId']),)
                            )

                            logger.info(
                                "Aviso de atraso enviado | actionId=%s",
                                r['actionId']
                            )

                        else:
                            logger.warning(
                                "Aviso de atraso não enviado | actionId=%s",
                                r['actionId']
                            )

                    else:
                        logger.warning(
                            "Ação atrasada sem destinatário ativo | actionId=%s",
                            r['actionId']
                        )

                except Exception as e:
                    logger.error(
                        "Falha ao notificar atraso da ação actionId=%s: %s",
                        r['actionId'],
                        e,
                        exc_info=True
                    )


    '''
    # ------------- Persistência ---------------------------
    try:
        logger.info("Executando COMMIT")
        cnnx.commit()
        logger.info("COMMIT executado com sucesso")
    except Exception as e:
        logger.error("Falha no commit do job h_24: %s", e)
    finally:
        try:
            cnnx.close()
        except Exception:
            pass
    '''

    # ------------- Persistência ---------------------------
    try:
        logger.info("Executando COMMIT")
        cnnx.commit()
        logger.info("COMMIT executado com sucesso")

    except Exception as e:
        logger.error("Falha no commit do job h_24: %s", e)

    finally:
        try:
            cursor.close()
        except Exception:
            pass

        try:
            cnnx.close()
        except Exception:
            pass

# V2