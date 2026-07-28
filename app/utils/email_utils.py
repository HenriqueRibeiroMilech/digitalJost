from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr
import smtplib

def send_email_with_attachment(subject, body, to, attachment_path=None, sender_name='Transformação Digital JOST', sender_email='noreply.digitaljost@randon.com.br'):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = formataddr((sender_name, sender_email))
    msg['To'] = to

    msg.attach(MIMEText(body, 'html'))

    # Anexo (opcional)
    if attachment_path:
        with open(attachment_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename=\"{attachment_path.split('/')[-1]}\"')
            msg.attach(part)

    try:
        with smtplib.SMTP('mailapp.randon.com.br', 25) as server:
            server.sendmail(sender_email, [to], msg.as_string())
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return False