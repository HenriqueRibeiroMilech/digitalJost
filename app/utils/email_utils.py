from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr
import os
import smtplib


def _normalize_emails(value):
    if not value:
        return []

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [str(value)]

    emails = []

    for item in values:
        email = str(item or '').strip()

        if email and email not in emails:
            emails.append(email)

    return emails


def send_email_with_attachment(
    subject,
    body,
    to,
    attachment_path=None,
    sender_name='Transformação Digital JOST',
    sender_email='noreply.digitaljost@randon.com.br',
    cc=None
):
    to_emails = _normalize_emails(to)
    cc_emails = _normalize_emails(cc)

    if not to_emails:
        print("Erro ao enviar e-mail: nenhum destinatário informado.")
        return False

    msg = MIMEMultipart()

    msg['Subject'] = str(subject or '')
    msg['From'] = formataddr((sender_name, sender_email))
    msg['To'] = ', '.join(to_emails)

    if cc_emails:
        msg['Cc'] = ', '.join(cc_emails)

    msg.attach(
        MIMEText(
            str(body or ''),
            'html',
            'utf-8'
        )
    )

    if attachment_path:
        with open(attachment_path, 'rb') as file:
            part = MIMEBase(
                'application',
                'octet-stream'
            )

            part.set_payload(file.read())
            encoders.encode_base64(part)

            part.add_header(
                'Content-Disposition',
                'attachment; filename="{}"'.format(
                    os.path.basename(attachment_path)
                )
            )

            msg.attach(part)

    recipients = list(
        dict.fromkeys(
            to_emails + cc_emails
        )
    )

    try:
        with smtplib.SMTP(
            'mailapp.randon.com.br',
            25,
            timeout=30
        ) as server:
            server.sendmail(
                sender_email,
                recipients,
                msg.as_string()
            )

        return True

    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return False

# V1