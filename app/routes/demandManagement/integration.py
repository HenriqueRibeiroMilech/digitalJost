import os
from datetime import date

from flask import render_template, url_for
from flask_mail import Message
from sqlalchemy import text

from app.config import mail


class RequestAttachmentStorage:
    """Resolve anexos existentes sem alterar os arquivos operacionais."""

    def __init__(self, app_root):
        self.base_directory = os.path.abspath(os.path.join(
            app_root, 'static', 'uploads', 'improvements'
        ))

    def request_directory(self, request_id):
        directory = os.path.abspath(os.path.join(
            self.base_directory, str(int(request_id))
        ))
        if os.path.commonpath([self.base_directory, directory]) != self.base_directory:
            raise ValueError('Diretório de anexos inválido.')
        return directory

    @staticmethod
    def is_safe_stored_name(file_name):
        return (
            bool(file_name)
            and file_name not in ('.', '..')
            and os.path.basename(file_name) == file_name
        )


class RequestReviewNotifier:
    """Envia as notificações do fluxo de análise das solicitações."""

    @staticmethod
    def _format_date(value):
        return value.strftime('%d/%m/%Y')

    @staticmethod
    def _message(subject, review, copied_users):
        copied_emails = []
        for user in copied_users:
            email = user.get('email')
            if email and email != review['requesterEmail'] and email not in copied_emails:
                copied_emails.append(email)
        return Message(
            subject,
            sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
            recipients=[review['requesterEmail']],
            cc=copied_emails
        )

    @staticmethod
    def _requests_url(area_name):
        return url_for(
            'demand_requests.requests_page',
            area=area_name,
            tab='minhas',
            _external=True
        )

    def approved(self, review, responsible, reviewer, area_name):
        message = self._message(
            f'Sua demanda - "{review["title"]}" - foi aceita!',
            review,
            [responsible, reviewer]
        )
        message.html = render_template(
            'demandRequests/emails/approved.html',
            respName=responsible['name'],
            reviewerName=reviewer['name'],
            title=review['title'],
            desc=review['initialDescription'],
            requestsUrl=self._requests_url(area_name)
        )
        mail.send(message)

    def declined(self, review, reviewer, area_name, reason):
        message = self._message(
            f'A sua solicitação - "{review["title"]}" - foi recusada!',
            review,
            [reviewer]
        )
        message.html = render_template(
            'demandRequests/emails/declined.html',
            respName=reviewer['name'],
            just=reason,
            title=review['title'],
            desc=review['initialDescription'],
            requestsUrl=self._requests_url(area_name)
        )
        mail.send(message)

    def status_changed(self, demand, actor, area_name, transition):
        action = transition['action']
        # Monta somente o conteúdo da ação atual, pois os demais campos são opcionais.
        if action == 'start':
            content = (
                'foi iniciada',
                'O desenvolvimento da sua demanda foi iniciado.',
                [('Prazo de entrega', self._format_date(transition['deadline']))]
            )
        elif action == 'pause':
            content = (
                'foi pausada',
                'O desenvolvimento da sua demanda foi pausado.',
                [
                    ('Justificativa', transition['reason']),
                    ('Previsão de retorno', self._format_date(transition['expectedReturn']))
                ]
            )
        elif action == 'resume':
            content = (
                'foi retomada',
                'O desenvolvimento da sua demanda foi retomado.',
                [('Novo prazo de entrega', self._format_date(transition['deadline']))]
            )
        elif action == 'complete':
            content = (
                'foi concluída',
                'O desenvolvimento da sua demanda foi concluído.',
                [('Conclusão', self._format_date(date.today()))]
            )
        elif action == 'cancel':
            content = (
                'foi cancelada',
                'O desenvolvimento da sua demanda foi cancelado.',
                [('Justificativa', transition['reason'])]
            )
        elif action == 'reopen':
            content = (
                'foi reaberta',
                'A sua demanda foi reaberta e voltou para desenvolvimento.',
                [('Novo prazo de entrega', self._format_date(transition['deadline']))]
            )
        else:
            raise ValueError('Ação de status sem notificação configurada.')

        message = self._message(
            f'A sua demanda - "{demand["title"]}" - {content[0]}!',
            demand,
            [actor]
        )
        message.html = render_template(
            'demandRequests/emails/status_update.html',
            heading=content[0].upper(),
            messageText=content[1],
            details=content[2],
            respName=actor['name'],
            title=demand['title'],
            desc=demand['initialDescription'],
            requestsUrl=self._requests_url(area_name)
        )
        mail.send(message)


def sync_approved_request(connection, request_id):
    """Cria ou atualiza o vínculo operacional sem duplicar a solicitação."""
    query = text("""
        IF NOT EXISTS (
            SELECT 1
            FROM JDT_DEMAND_MANAGEMENT WITH (UPDLOCK, HOLDLOCK)
            WHERE sourceRequestId = :request_id
        )
        BEGIN
            INSERT INTO JDT_DEMAND_MANAGEMENT (
                sourceRequestId, areaId, status, deadline, startDate,
                responsibleId, createdAt, updatedAt
            )
            SELECT
                R.requestId,
                R.areaId,
                CASE R.status
                    WHEN 2 THEN 'Concluído'
                    WHEN 4 THEN 'Pausado'
                    ELSE CASE WHEN R.startDate IS NULL THEN 'A Fazer' ELSE 'Em Andamento' END
                END,
                R.deliveryDate,
                R.startDate,
                R.respId,
                GETDATE(),
                GETDATE()
            FROM JDT_REQUEST_IMPROVEMENTS_SMALL AS R
            WHERE R.requestId = :request_id AND R.status IN (1, 2, 4)
        END
        ELSE
        BEGIN
            UPDATE M
            SET
                status = CASE R.status
                    WHEN 2 THEN 'Concluído'
                    WHEN 4 THEN 'Pausado'
                    ELSE CASE WHEN R.startDate IS NULL THEN 'A Fazer' ELSE 'Em Andamento' END
                END,
                deadline = R.deliveryDate,
                startDate = COALESCE(M.startDate, R.startDate),
                responsibleId = R.respId,
                updatedAt = GETDATE()
            FROM JDT_DEMAND_MANAGEMENT AS M
            JOIN JDT_REQUEST_IMPROVEMENTS_SMALL AS R
                ON R.requestId = M.sourceRequestId
            WHERE R.requestId = :request_id AND R.status IN (1, 2, 4)
        END
    """)
    connection.execute(query, {'request_id': request_id})
