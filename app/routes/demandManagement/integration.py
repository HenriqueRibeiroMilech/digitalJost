import os
from datetime import date
from uuid import uuid4

from flask import render_template, url_for
from flask_mail import Message
from sqlalchemy import text
from werkzeug.utils import secure_filename

from app.config import mail

from .domain import NotFoundError, ValidationError


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


class InternalDemandAttachmentStorage:
    """Mantém anexos do gerenciador fora da pasta pública da aplicação."""

    ALLOWED_EXTENSIONS = {
        'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'txt', 'csv', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp',
        'zip', '7z', 'rar', 'msg', 'eml'
    }
    MAX_FILES_PER_UPLOAD = 10
    MAX_FILES_PER_DEMAND = 30

    def __init__(self, instance_path):
        self.base_directory = os.path.abspath(os.path.join(
            instance_path, 'demand_management_attachments'
        ))

    def list(self, management_id):
        directory = self.demand_directory(management_id)
        try:
            entries = list(os.scandir(directory))
        except FileNotFoundError:
            return []

        attachments = []
        for entry in entries:
            if not entry.is_file(follow_symlinks=False):
                continue
            parsed = self._parse_stored_name(entry.name)
            if parsed:
                attachment_id, original_name = parsed
                attachments.append({
                    'id': attachment_id,
                    'name': original_name,
                    'size': entry.stat(follow_symlinks=False).st_size
                })
        return sorted(attachments, key=lambda item: item['name'].lower())

    def save(self, management_id, files):
        prepared_files = self._prepare_files(files)
        existing = self.list(management_id)
        if len(existing) + len(prepared_files) > self.MAX_FILES_PER_DEMAND:
            raise ValidationError(
                f'Cada demanda pode ter no máximo {self.MAX_FILES_PER_DEMAND} anexos internos.'
            )

        directory = self.demand_directory(management_id)
        os.makedirs(directory, exist_ok=True)
        saved_names = []
        try:
            for uploaded_file, original_name in prepared_files:
                stored_name = f'{uuid4().hex}--{original_name}'
                uploaded_file.save(os.path.join(directory, stored_name))
                saved_names.append(stored_name)
        except Exception:
            for stored_name in saved_names:
                try:
                    os.remove(os.path.join(directory, stored_name))
                except OSError:
                    pass
            raise
        return self.list(management_id)

    def resolve(self, management_id, attachment_id):
        if not self._is_attachment_id(attachment_id):
            raise NotFoundError('Anexo interno não encontrado.')
        directory = self.demand_directory(management_id)
        try:
            entries = os.scandir(directory)
        except FileNotFoundError as error:
            raise NotFoundError('Anexo interno não encontrado.') from error

        with entries:
            for entry in entries:
                parsed = self._parse_stored_name(entry.name)
                if (
                    entry.is_file(follow_symlinks=False)
                    and parsed
                    and parsed[0] == attachment_id
                ):
                    return directory, entry.name, parsed[1]
        raise NotFoundError('Anexo interno não encontrado.')

    def delete(self, management_id, attachment_id):
        directory, stored_name, _ = self.resolve(management_id, attachment_id)
        try:
            os.remove(os.path.join(directory, stored_name))
        except FileNotFoundError as error:
            raise NotFoundError('Anexo interno não encontrado.') from error
        try:
            os.rmdir(directory)
        except OSError:
            pass

    def demand_directory(self, management_id):
        directory = os.path.abspath(os.path.join(
            self.base_directory, str(int(management_id))
        ))
        if os.path.commonpath([self.base_directory, directory]) != self.base_directory:
            raise ValidationError('Diretório de anexos internos inválido.')
        return directory

    def _prepare_files(self, files):
        uploaded_files = [item for item in files if item and item.filename]
        if not uploaded_files:
            raise ValidationError('Selecione pelo menos um arquivo.')
        if len(uploaded_files) > self.MAX_FILES_PER_UPLOAD:
            raise ValidationError(
                f'Envie no máximo {self.MAX_FILES_PER_UPLOAD} arquivos por vez.'
            )

        prepared = []
        for uploaded_file in uploaded_files:
            original_name = secure_filename(uploaded_file.filename)
            extension = os.path.splitext(original_name)[1].lower().lstrip('.')
            if not original_name or extension not in self.ALLOWED_EXTENSIONS:
                raise ValidationError(
                    f'O arquivo "{uploaded_file.filename}" não é permitido.'
                )
            root, file_extension = os.path.splitext(original_name)
            prepared.append((uploaded_file, f'{root[:160]}{file_extension}'))
        return prepared

    @classmethod
    def _parse_stored_name(cls, stored_name):
        attachment_id, separator, original_name = stored_name.partition('--')
        if (
            not separator
            or not cls._is_attachment_id(attachment_id)
            or not RequestAttachmentStorage.is_safe_stored_name(original_name)
        ):
            return None
        return attachment_id, original_name

    @staticmethod
    def _is_attachment_id(value):
        if not isinstance(value, str) or len(value) != 32:
            return False
        try:
            int(value, 16)
        except ValueError:
            return False
        return True


class RequestReviewNotifier:
    """Envia as notificações do fluxo de análise das solicitações."""

    @staticmethod
    def _format_date(value):
        return value.strftime('%d/%m/%Y')

    @staticmethod
    def _message(subject, review, copied_users):
        copied_emails = []
        contributor_email = review.get('contributorEmail')
        if contributor_email and contributor_email != review['requesterEmail']:
            copied_emails.append(contributor_email)
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
                'O desenvolvimento da sua demanda foi retomado sem alteração do prazo.',
                []
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
                [
                    ('Novo prazo de entrega', self._format_date(transition['deadline'])),
                    ('Justificativa', transition['reason'])
                ]
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

    def start_scheduled(self, demand, actor, area_name, schedule):
        message = self._message(
            f'A sua demanda - "{demand["title"]}" - teve o início agendado!',
            demand,
            [actor]
        )
        message.html = render_template(
            'demandRequests/emails/status_update.html',
            heading='TEVE O INÍCIO AGENDADO',
            messageText='O desenvolvimento da sua demanda teve o início agendado.',
            details=[
                (
                    'Início agendado',
                    self._format_date(schedule['scheduledStartAt'])
                ),
                ('Prazo de entrega', self._format_date(schedule['deadline']))
            ],
            respName=actor['name'],
            title=demand['title'],
            desc=demand['initialDescription'],
            requestsUrl=self._requests_url(area_name)
        )
        mail.send(message)

    def deadline_changed(
        self, demand, actor, area_name, previous_deadline, deadline, reason
    ):
        previous_label = (
            self._format_date(previous_deadline)
            if previous_deadline else 'Não definido'
        )
        deadline_label = self._format_date(deadline) if deadline else 'Não definido'
        demand_title = demand['title']
        message = self._message(
            f'O prazo da sua demanda - "{demand_title}" - foi alterado!',
            demand,
            [actor]
        )
        message.html = render_template(
            'demandRequests/emails/status_update.html',
            heading='TEVE O PRAZO ALTERADO',
            messageText='O prazo de entrega da sua demanda foi alterado.',
            details=[
                ('Prazo anterior', previous_label),
                ('Novo prazo de entrega', deadline_label),
                ('Justificativa', reason)
            ],
            respName=actor['name'],
            title=demand_title,
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

# V3
