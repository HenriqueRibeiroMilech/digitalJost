from datetime import date

from flask import render_template, url_for
from flask_mail import Message
from sqlalchemy import text

from app.config import mail
from app.utils.data_utils import format_date


class RequestReviewNotifier:
    """Envia as notificações do fluxo de análise das solicitações."""

    @staticmethod
    def _message(subject, review, reviewer):
        return Message(
            subject,
            sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
            recipients=[review['requesterEmail']],
            cc=[reviewer['email']] if reviewer.get('email') else []
        )

    def approved(self, review, reviewer, area_name, deadline):
        message = self._message(
            f'Sua demanda - "{review["title"]}" - foi iniciada!',
            review,
            reviewer
        )
        message.html = render_template(
            'demandRequests/emails/approved.html',
            respName=reviewer['name'],
            title=review['title'],
            desc=review['initialDescription'],
            date=format_date(date.today()),
            deliveryDate=format_date(deadline),
            requestsUrl=url_for(
                'demand_requests.requests_page',
                area=area_name,
                tab='minhas',
                _external=True
            )
        )
        mail.send(message)

    def declined(self, review, reviewer, area_name, reason):
        message = self._message(
            f'A sua solicitação - "{review["title"]}" - foi recusada!',
            review,
            reviewer
        )
        message.html = render_template(
            'demandRequests/emails/declined.html',
            respName=reviewer['name'],
            just=reason,
            title=review['title'],
            desc=review['initialDescription'],
            requestsUrl=url_for(
                'demand_requests.requests_page',
                area=area_name,
                tab='minhas',
                _external=True
            )
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
                    ELSE 'Em Andamento'
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
                    ELSE 'Em Andamento'
                END,
                deadline = R.deliveryDate,
                startDate = COALESCE(M.startDate, R.startDate),
                updatedAt = GETDATE()
            FROM JDT_DEMAND_MANAGEMENT AS M
            JOIN JDT_REQUEST_IMPROVEMENTS_SMALL AS R
                ON R.requestId = M.sourceRequestId
            WHERE R.requestId = :request_id AND R.status IN (1, 2, 4)
        END
    """)
    connection.execute(query, {'request_id': request_id})
