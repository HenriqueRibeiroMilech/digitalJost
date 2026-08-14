from datetime import date

from flask import render_template
from flask_mail import Message

from app.config import mail
from app.utils.data_utils import format_date


class RequestReviewNotifier:
    """Mantém as notificações usadas pelo fluxo antigo de análise."""

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
            'request.improvements/improvements_email_new_small_start.html',
            respName=reviewer['name'],
            title=review['title'],
            desc=review['initialDescription'],
            date=format_date(date.today()),
            area=area_name,
            requestType='melhorias',
            deliveryDate=format_date(deadline)
        )
        mail.send(message)

    def declined(self, review, reviewer, area_name, reason):
        message = self._message(
            f'A sua solicitação - "{review["title"]}" - foi recusada!',
            review,
            reviewer
        )
        message.html = render_template(
            'request.improvements/improvements_email_new_small_decline.html',
            respName=reviewer['name'],
            just=reason,
            title=review['title'],
            desc=review['initialDescription'],
            area=area_name,
            requestType='melhorias'
        )
        mail.send(message)
