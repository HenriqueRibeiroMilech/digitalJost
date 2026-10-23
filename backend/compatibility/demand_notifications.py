"""Ponte explícita com o transporte SMTP existente, também usado pelos serviços Windows."""


def send_notification(*, subject, body, to, cc):
    from app.utils.email_utils import send_email_with_attachment

    return send_email_with_attachment(subject=subject, body=body, to=to, cc=cc)
