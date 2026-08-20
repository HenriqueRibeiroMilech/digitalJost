import os

from werkzeug.utils import secure_filename

from .domain import ValidationError


class DemandRequestStorage:
    ALLOWED_EXTENSIONS = {
        'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'
    }
    MAX_FILES = 10

    def __init__(self, app_root):
        self.base_directory = os.path.abspath(os.path.join(
            app_root, 'static', 'uploads', 'improvements'
        ))

    def save(self, request_id, files):
        prepared_files = self._prepare_files(files)
        directory = self.request_directory(request_id)

        os.makedirs(self.base_directory, exist_ok=True)
        try:
            os.mkdir(directory)
        except FileExistsError as error:
            raise ValidationError(
                'Não foi possível reservar o diretório dos anexos. Tente novamente.'
            ) from error

        saved_names = []
        try:
            for uploaded_file, stored_name in prepared_files:
                saved_names.append(stored_name)
                uploaded_file.save(os.path.join(directory, stored_name))
        except Exception:
            self.remove_files(request_id, saved_names)
            raise

        return [stored_name for _, stored_name in prepared_files]

    def remove_files(self, request_id, stored_names):
        directory = self.request_directory(request_id)
        for stored_name in stored_names:
            if not self.is_safe_stored_name(stored_name):
                continue
            file_path = os.path.join(directory, stored_name)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        try:
            os.rmdir(directory)
        except OSError:
            pass

    def request_directory(self, request_id):
        directory = os.path.abspath(os.path.join(
            self.base_directory, str(int(request_id))
        ))
        if os.path.commonpath([self.base_directory, directory]) != self.base_directory:
            raise ValidationError('Diretório de anexos inválido.')
        return directory

    @staticmethod
    def is_safe_stored_name(file_name):
        return (
            bool(file_name)
            and file_name not in ('.', '..')
            and os.path.basename(file_name) == file_name
        )

    def _prepare_files(self, files):
        uploaded_files = [file for file in files if file and file.filename]
        if not uploaded_files:
            raise ValidationError('Adicione pelo menos um documento à solicitação.')
        if len(uploaded_files) > self.MAX_FILES:
            raise ValidationError(f'Envie no máximo {self.MAX_FILES} documentos por solicitação.')

        prepared = []
        used_names = set()
        for uploaded_file in uploaded_files:
            stored_name = secure_filename(uploaded_file.filename)
            extension = os.path.splitext(stored_name)[1].lower().lstrip('.')
            if not stored_name or extension not in self.ALLOWED_EXTENSIONS:
                raise ValidationError(f'O arquivo "{uploaded_file.filename}" não é permitido.')

            root, file_extension = os.path.splitext(stored_name)
            stored_name = f'{root[:160]}{file_extension}'
            stored_name = self._unique_name(stored_name, used_names)
            used_names.add(stored_name.lower())
            prepared.append((uploaded_file, stored_name))

        return prepared

    @staticmethod
    def _unique_name(file_name, used_names):
        root, extension = os.path.splitext(file_name)
        candidate = file_name
        counter = 2
        while candidate.lower() in used_names:
            candidate = f'{root}_{counter}{extension}'
            counter += 1
        return candidate
