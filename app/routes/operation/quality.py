import shutil
from datetime import datetime, timedelta
import pandas as pd
import json
import os
import hmac
import secrets
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from flask import Blueprint, abort, current_app, jsonify, render_template, request, redirect, send_file, session, url_for
from flask_login import current_user

from app.utils.constants import APP_PATH
from app.utils.db_utils import engine_run_query, get_engine
from app.utils.dynamic_constants import getPlex
from app.utils.files_utils import qsb_file
from app.utils.permissions import get_permission
from .quality_control import (
    OCCURRENCE_TYPES, PRODUCT_FAMILIES, QualityControlError,
    QualityControlService,
)
from .quality_control.domain import CAMPINAS_WORKCENTERS, entry_period, is_flag_set
from .quality_control.repository import JOIN, PROJECTION, PUBLISHED, VISIBLE
from .quality_control.services import image_names, safe_name


p_quality = get_permission('QUALITY')

operation_quality_bp = Blueprint('operation_quality', __name__)


def _quality_control():
    return QualityControlService(
        get_engine('jdt'), Path(current_app.root_path) / 'static' / 'uploads' / 'operation'
    )


def _quality_csrf_token():
    if not session.get('quality_control_csrf'):
        session['quality_control_csrf'] = secrets.token_urlsafe(32)
    return session['quality_control_csrf']


def _validate_quality_csrf():
    expected = session.get('quality_control_csrf', '')
    received = request.headers.get('X-CSRF-Token', '')
    if not expected or not received or not hmac.compare_digest(expected.encode('utf-8'), received.encode('utf-8')):
        raise QualityControlError('Sessão de segurança inválida. Atualize a página.', 400)


def _quality_entry_id():
    try:
        entry_id = int(request.args.get('entryID', ''))
        if entry_id <= 0:
            raise ValueError
        return entry_id
    except (ValueError, TypeError):
        abort(400, 'Identificação da ocorrência inválida.')


def _quality_record_urls(record):
    record['permissions'] = {'edit': p_quality.can(), 'delete': p_quality.can()}
    for category in ('nok', 'ok'):
        for photo in record[f'images_{category}']:
            photo['url'] = url_for(
                'operation_quality.quality_table_image', entry_id=record['id'],
                category=category, filename=photo['name'],
            )
    return record


@operation_quality_bp.errorhandler(QualityControlError)
def quality_control_error(error):
    return jsonify({'error': str(error), 'field': error.field}), error.status_code


@operation_quality_bp.errorhandler(SQLAlchemyError)
def quality_database_error(error):
    # Não expor SQL, parâmetros ou dados de conexão ao usuário ou aos logs.
    current_app.logger.error('Falha de banco no controle QSB.')
    return jsonify({'error': 'Controle de Qualidade indisponível. Contate o responsável pelo sistema.'}), 503

_QSB_LOCATION_MANAGER_REGISTRATIONS = {
    '00023485',
    '00019945',
    '00029754',
    '00028755',
    '00039285',
    '00040893',
    '00063689'
}


def _can_manage_qsb_locations():
    registration = str(getattr(current_user, 'registration', '') or '').strip().zfill(8)
    return registration in _QSB_LOCATION_MANAGER_REGISTRATIONS


def _get_quality_workcenters():
    query = """SELECT
                    GRUPO AS Workcenter_Group
                    , LEFT(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) - 1) AS Workcenter_Code
                    , SUBSTRING(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) + 1, LEN(NOME_MAQUINA)) AS Name
                    , 1 AS Workcenter_Key
                FROM CONFIG_TABLET WHERE CT_PLEX IS NULL"""
    mic_workcenters = engine_run_query(query, 'ftm')

    mes_workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]
    return pd.concat([
        mes_workcenters[~mes_workcenters['Workcenter_Code'].isin(mic_workcenters['Workcenter_Code'])],
        mic_workcenters,
    ]).sort_values(by='Workcenter_Code')


def _get_registered_qsb_locations():
    query = "SELECT name FROM dbo.JDT_OPE_QUAL_LOCATIONS ORDER BY name"
    locations = engine_run_query(query, 'jdt')
    return [str(name).strip() for name in locations['name'].tolist() if str(name).strip()]


def _get_caxias_qsb_locations(workcenters=None):
    if workcenters is None:
        workcenters = _get_quality_workcenters()

    locations = [
        f"{row['Workcenter_Code']}-{row['Name']}"
        for _, row in workcenters.iterrows()
    ]
    locations.extend(_get_registered_qsb_locations())

    unique_locations = {}
    for location in locations:
        normalized_location = str(location).strip()
        if normalized_location:
            unique_locations.setdefault(normalized_location.casefold(), normalized_location)

    return sorted(unique_locations.values(), key=str.casefold)


@operation_quality_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)

# FUNÇÃO LOCAL DO MÉTODO, PARA GERAR UM JSON COM OS DADOS DA ENTRADA DO INFORMATIVO DA QUALIDADE
def _QUALITY_DETAIL(day):

    aux = ""
    params = {'day': day}

    if 'unit' in request.args:
        aux = "AND q.unit = :unit"
        params['unit'] = request.args['unit']

    query = f"SELECT {PROJECTION} FROM JDT_OPE_QUAL q {JOIN} WHERE q.openDate = :day AND {PUBLISHED} {aux}"
    df = engine_run_query(query, 'jdt', params)

    file = []
    for _, row in df.iterrows():
        repeat = 'Sim' if is_flag_set(row.get('repeat')) else 'Não'
        photos_nok = [name for name in image_names(row.get('imgNOK')) if safe_name(name)]
        photos_ok = [name for name in image_names(row.get('imgOK')) if safe_name(name)]
        file_info = {
            'Local da Ocorrencia': [str(row.get('type', '')), str(row.get('typeDesc', ''))]
            , 'Imagens NOK': photos_nok
            , 'Imagens OK': photos_ok
            , 'URLs Imagens NOK': [url_for('operation_quality.quality_table_image', entry_id=row['id'], category='nok', filename=name) for name in photos_nok]
            , 'URLs Imagens OK': [url_for('operation_quality.quality_table_image', entry_id=row['id'], category='ok', filename=name) for name in photos_ok]
            , 'Centro de Trabalho': str(row.get('workCenter', ''))
            , 'Familia do Produto': str(row.get('prodFamily', ''))
            , 'Problema': str(row.get('description', ''))
            , 'Reincidente': repeat
            , 'Contencao': {
                'O que': str(row.get('text1', ''))
                , 'Como': str(row.get('text2', ''))
                , 'Quem': str(row.get('text3', ''))
                }
            , 'Turno': str(row.get('shift', ''))
            , 'ID': str(row.get('id', ''))
            , 'workCenter': str(row.get('workCenter', ''))
            , 'prodCode': str(row.get('prodCode', ''))
            , 'unit': str(int(row.get('unit', 0))) if 'unit' in row else ''
            , 'Horário da parada': str(row['stop_time'])[:5] if pd.notna(row['stop_time']) else ''
            , 'Motivo da parada': str(row['stop_reason']) if pd.notna(row['stop_reason']) else ''
            , 'Tempo total de parada': float(row['stop_minutes']) if pd.notna(row['stop_minutes']) else None
            , 'Quantidade de paradas': int(row['stop_count']) if pd.notna(row['stop_count']) else None
            , 'Detalhamento do local': str(row['location_detail']) if pd.notna(row['location_detail']) else ''
        }
        file.append(file_info)

    return file


# PÁGINA DA SELEÇÃO PARA VISUALIZAÇÃO DO INFORMATIVO DA QUALIDADE - OPERATION MEETING
@operation_quality_bp.route('/op/qualidade', methods=['GET'])
def quality_get():
    return render_template('operation.qual/op_qual_pyramid.html', month=datetime.now().month)

@operation_quality_bp.route('/op/qualidade', methods=['POST'])
def quality_post():

    try:
        year = int(request.args['year'])
        month = int(request.args['month'])
    except (KeyError, ValueError):
        return abort(400, "Ano ou mês inválido.")

    params = {'year': year, 'month': month}
    unit_filter = ""
    if 'unit' in request.args:
        try:
            unit = int(request.args['unit'])
            unit_filter = "AND q.unit = :unit"
            params['unit'] = unit
        except ValueError:
            return abort(400, "Unidade inválida.")

    query = f"""
        SELECT DAY(q.openDate) AS day, q.type
        FROM JDT_OPE_QUAL q {JOIN}
        WHERE YEAR(q.openDate) = :year AND MONTH(q.openDate) = :month
          AND {PUBLISHED} {unit_filter}
        ORDER BY q.openDate
    """
    df = engine_run_query(query, 'jdt', params)
    
    # Converte o resultado para lista de listas
    entries = df[['day', 'type']].values.tolist() if not df.empty else []
    return json.dumps(entries)


def _quality_document_context():
    try:
        current_day = datetime.strptime(request.args.get('day', ''), '%d/%m/%Y').date()
        # Preserva os intervalos de navegação usados pelo informativo legado.
        previous_day = current_day - timedelta(days=2 if current_day.weekday() == 0 else 1)
        next_day = current_day + timedelta(days=2 if current_day.weekday() == 5 else 1)
    except (ValueError, OverflowError):
        abort(400, 'Informe uma data válida no formato DD/MM/AAAA.')
    selected_unit = None
    if 'unit' in request.args:
        try:
            selected_unit = int(request.args['unit'])
        except ValueError:
            abort(400, 'Unidade inválida.')
        if selected_unit not in (0, 1):
            abort(400, 'Unidade inválida.')
    filters = {'day': current_day.strftime('%d/%m/%Y')}
    if selected_unit is not None:
        filters['unit'] = selected_unit
    return {
        'file': _QUALITY_DETAIL(current_day.isoformat()), 'day': filters['day'],
        'selected_unit': selected_unit, 'can_edit': p_quality.can(),
        'view_url': url_for('operation_quality.quality_detail_get', **filters),
        'print_url': url_for('operation_quality.quality_printer_get', **filters),
        'previous_url': url_for('operation_quality.quality_detail_get', **{**filters, 'day': previous_day.strftime('%d/%m/%Y')}),
        'next_url': url_for('operation_quality.quality_detail_get', **{**filters, 'day': next_day.strftime('%d/%m/%Y')}),
    }


# PÁGINA DA VISUALIZAÇÃO DOS DETALHES DO INFORMATIVO DA QUALIDADE - OPERATION MEETING
@operation_quality_bp.route('/op/qualidade/view', methods=['GET'])
def quality_detail_get():
    return render_template('operation.qual/op_qual_view.html', print_mode=False, **_quality_document_context())

# ROTA DE POST, QUE PASSA OS DADOS E ARQUIVOS RECEBIDOS PELO FORMULÁRIO AO BANCO DE DADOS SQL E AOS DIRETÓRIOS
@operation_quality_bp.route('/op/qualidade/update', methods=['POST'])
@p_quality.require(403)
def quality_detail_post():
    command = request.args.get('command')
    if command not in ('add', 'edit') or (command == 'add' and 'entryID' in request.args):
        abort(400, 'Operação inválida.')
    service = _quality_control()
    repository = service.repository
    actor_id = str(current_user.id)
    with service.engine.begin() as connection:
        before = None
        if command == 'add':
            repository.acquire_creation_lock(connection)
        else:
            before = repository.get_entry(connection, _quality_entry_id(), lock=True)
        entry_id = _save_legacy_quality_form(connection)
        repository.ensure_control(connection, entry_id, actor_id, is_new=command == 'add')
        repository.touch_control(connection, entry_id, actor_id)
        after = repository.get_entry(connection, entry_id)
        repository.audit(connection, entry_id, actor_id, 'create' if command == 'add' else 'update', before, after)
    return redirect(url_for('operation_quality.quality_list_get'))


def _save_legacy_quality_form(connection):
    try:
        unit = int(request.form.get('unidade', ''))
    except (TypeError, ValueError):
        return abort(400, 'Unidade inválida.')

    if unit not in (0, 1):
        return abort(400, 'Unidade inválida.')

    specific_location = str(request.form.get('op_local_info', '') or '').strip()
    if not specific_location:
        return abort(400, 'Local específico é obrigatório.')

    if unit == 0:
        allowed_locations = {
            location.casefold(): location
            for location in _get_caxias_qsb_locations()
        }
        specific_location = allowed_locations.get(specific_location.casefold())
        if specific_location is None:
            return abort(400, 'Selecione um local específico cadastrado para Caxias do Sul.')

    repeat = 0
    if 'op_reincidente' in request.form:
        repeat = 1

    if 'entryID' in request.args:  # caso a URL apresente um ID valido, sera executado
        caminho = str(_quality_entry_id())
        sql_data = connection.execute(text(
            "SELECT imgNOK, imgOK FROM JDT_OPE_QUAL WHERE id = :id"
        ), {'id': caminho}).mappings().one()
        img_nok = sql_data['imgNOK'] or ''
        img_ok = sql_data['imgOK'] or ''

        # CONDICAO DEVIDO A ATUALIZACAO NA FORMA DE SALVAR, PARA O QUE JÁ FOR SALVO, NÃO SE PERDER
        if not os.path.exists('app/static/uploads/operation/img_nok/' + caminho + '/'):
            os.mkdir('app/static/uploads/operation/img_nok/' + caminho + '/')
            if img_nok != "":
                lista = img_nok.split("||")[:-1]
                for arq in lista:  # defini a string como uma lista
                    shutil.copy(rf'{APP_PATH}\app\static\uploads\operation\img_nok\{arq}',
                                rf'{APP_PATH}\app\static\uploads\operation\img_nok\{caminho}\{arq}')
                    # copia e cola os arquivos que já existiam na nova pasta

        # CONDICAO DEVIDO A ATUALIZACAO NA FORMA DE SALVAR, PARA O QUE JÁ FOR SALVO, NÃO SE PERDER
        if not os.path.exists('app/static/uploads/operation/img_ok/' + caminho + '/'):
            os.mkdir('app/static/uploads/operation/img_ok/' + caminho + '/')  # a pasta da ocorrencia é salva
            if img_ok != "":
                lista = img_ok.split("||")[:-1]
                for arq in lista:  # defini a string como uma lista
                    shutil.copy(rf'{APP_PATH}\app\static\uploads\operation\img_ok\{arq}',
                                rf'{APP_PATH}\app\static\uploads\operation\img_ok\{caminho}\{arq}')

    else:

        caminho = _quality_control().repository.next_id(connection)

        # CONDICAO NOVA, PARA CRIAR UMA PASTA DE ARQUIVOS P/ CADA OCORRÊNCIA
        if not os.path.exists('app/static/uploads/operation/img_nok/' + caminho + '/'):
            os.mkdir('app/static/uploads/operation/img_nok/' + caminho + '/')

        # CONDICAO NOVA, PARA CRIAR UMA PASTA DE ARQUIVOS P/ CADA OCORRÊNCIA
        if not os.path.exists('app/static/uploads/operation/img_ok/' + caminho + '/'):
            os.mkdir('app/static/uploads/operation/img_ok/' + caminho + '/')

        img_nok = ""
        img_ok = ""

    for file in request.files.getlist('file_nok'):  # percorre os arquivos enviados pela API
        if file.filename != '':  # se o nome do arquivo não for vazio
            if img_nok.upper().count(file.filename.upper()) == 0:  # se o arquivo existir somente uma vez na lista
                file.save(os.path.join(rf'{APP_PATH}\app\static\uploads\operation\img_nok\{caminho}', file.filename))
                img_nok += f'{file.filename}||'  # o arquivo é salvo na pasta e a string do banco é atualizada
            else:
                acum = str(img_nok.upper().count(file.filename.upper().rsplit(".", 1)[0]))
                nome = file.filename.rsplit(".", 1)[0] + "_(" + acum + ")." + file.filename.split('.')[-1]
                file.save(os.path.join(rf'{APP_PATH}\app\static\uploads\operation\img_nok\{caminho}', nome))
                img_nok += f'{nome}||'

    for file in request.files.getlist("file_ok"):  # percorre os arquivos enviados pela API
        if file.filename != '':  # se o nome do arquivo não for vazio

            if img_ok.upper().count(file.filename.upper()) == 0:  # se o arquivo existir somente uma vez na lista
                file.save(os.path.join(rf'{APP_PATH}\app\static\uploads\operation\img_ok\{caminho}', file.filename))
                img_ok += f'{file.filename}||'  # o arquivo é salvo na pasta e a string do banco é atualizada
            else:
                acum = str(img_ok.upper().count(file.filename.upper().rsplit(".", 1)[0]))
                nome = file.filename.rsplit(".", 1)[0] + "_(" + acum + ")." + file.filename.split('.')[-1]
                file.save(os.path.join(rf'{APP_PATH}\app\static\uploads\operation\img_ok\{caminho}', nome))
                img_ok += f'{nome}||'

    turno = ""
    if "turno1" in request.form:
        turno += '1'

    if "turno2" in request.form:
        turno += ',2' if turno else '2'

    if "turno3" in request.form:
        turno += ',3' if turno else '3'

    if "NA" in request.form:
        turno = 'NA'

    if request.args['command'] == 'add':  # condição caso o usuario queira criar uma ocorrencia

        query = text("""INSERT INTO JDT_OPE_QUAL VALUES
                    (:occurrence_type,
                    :specific_location,
                    :problem,
                    :workcenter,
                    :product_code,
                    :repeat,
                    :containment_what,
                    :containment_how,
                    :containment_who,
                    :images_ok,
                    :images_nok,
                    :open_date,
                    :product_family,
                    :entry_id,
                    :shift,
                    :unit)""")  # query para criar a ocorrencia

    else:  # condicao caso o usuario queria atualizar uma ocorrencia
        for image in request.form['deletar1'].split("__,"):
            if image != "":
                img_nok = img_nok.replace(image + '||', "")

        for image in request.form['deletar2'].split("__,"):
            if image != "":
                img_ok = img_ok.replace(image + '||', "")

        query = text("""UPDATE JDT_OPE_QUAL SET
                            type = :occurrence_type,
                            typeDesc = :specific_location,
                            description = :problem,
                            workCenter = :workcenter,
                            prodCode = :product_code,
                            repeat = :repeat,
                            text1 = :containment_what,
                            text2 = :containment_how,
                            text3 = :containment_who,
                            imgNOK = :images_nok,
                            imgOK = :images_ok,
                            openDate = :open_date,
                            prodFamily = :product_family,
                            shift = :shift,
                            unit = :unit
                    WHERE
                        id = :entry_id""")

    query_params = {
        'occurrence_type': request.form['op_local_ocorr'],
        'specific_location': specific_location,
        'problem': request.form['op_problema'],
        'workcenter': request.form['ct'],
        'product_code': request.form['id_mater'],
        'repeat': repeat,
        'containment_what': request.form['op_cont_1'],
        'containment_how': request.form['op_cont_2'],
        'containment_who': request.form['op_cont_3'],
        'images_nok': img_nok,
        'images_ok': img_ok,
        'open_date': request.form['op_date'],
        'product_family': request.form['op_familia'],
        'entry_id': int(request.args['entryID']) if 'entryID' in request.args else caminho,
        'shift': turno,
        'unit': unit,
    }

    connection.execute(query, query_params)
    return caminho


# PÁGINA PARA IMPRESSÃO DO INFORMATIVO DA QUALIDADE - OPERATION MEETING
@operation_quality_bp.route('/op/qualidade/printer', methods=['GET'])
def quality_printer_get():
    return render_template('operation.qual/op_qual_print.html', print_mode=True, **_quality_document_context())


# PÁGINA DA ADIÇÃO DE ENTRADAS AO INFORMATIVO DA QUALIDADE - OPERATION MEETING
@operation_quality_bp.route('/op/qualidade/add', methods=['GET'])
def quality_add_get():
    workcenters = _get_quality_workcenters()

    return render_template('operation.qual/op_qual_add.html'
                           , workcenters=workcenters.to_dict(orient="records")
                           , caxias_locations=_get_caxias_qsb_locations(workcenters)
                           , can_manage_locations=_can_manage_qsb_locations())


@operation_quality_bp.route('/op/qualidade/tabela', methods=['GET'])
@p_quality.require(403)
def quality_table_get():
    date_from, date_until = entry_period(request.args.get('date_from'), request.args.get('date_until'))
    default_from, default_until = entry_period()
    workcenters = _get_quality_workcenters()
    entries = [_quality_record_urls(entry) for entry in _quality_control().list_entries(date_from, date_until)]

    return render_template(
        'operation.qual/op_qual_table.html',
        entries=entries,
        workcenters=workcenters.to_dict(orient='records'),
        caxias_locations=_get_caxias_qsb_locations(workcenters),
        can_manage_locations=_can_manage_qsb_locations(),
        occurrence_types=OCCURRENCE_TYPES, product_families=PRODUCT_FAMILIES,
        stop_reasons=_quality_control().list_stop_reasons(), campinas_workcenters=CAMPINAS_WORKCENTERS,
        csrf_token=_quality_csrf_token(), submission_key=str(uuid4()),
        filter_from=date_from.isoformat() if date_from else '',
        filter_until=date_until.isoformat() if date_until else '',
        default_from=default_from.isoformat(), default_until=default_until.isoformat(),
    )


@operation_quality_bp.route('/op/qualidade/tabela/registros', methods=['GET'])
@p_quality.require(403)
def quality_table_entries():
    date_from, date_until = entry_period(request.args.get('date_from'), request.args.get('date_until'))
    entries = [_quality_record_urls(entry) for entry in _quality_control().list_entries(date_from, date_until)]
    response = jsonify({
        'entries': entries,
        'date_from': date_from.isoformat() if date_from else '',
        'date_until': date_until.isoformat() if date_until else '',
    })
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@operation_quality_bp.route('/op/qualidade/tabela/registros', methods=['POST'])
@p_quality.require(403)
def quality_table_create():
    if request.content_length and request.content_length > 42 * 1024 * 1024:
        raise QualityControlError('O envio excede o limite de 40 MB de imagens.', 413)
    _validate_quality_csrf()
    workcenters = _get_quality_workcenters()
    entry = _quality_control().save(
        request.form, request.files, str(current_user.id),
        _get_caxias_qsb_locations(workcenters),
        [f"{row['Workcenter_Code']}-{row['Name']}" for _, row in workcenters.iterrows()],
    )
    return jsonify(_quality_record_urls(entry)), 201


@operation_quality_bp.route('/op/qualidade/tabela/registros/<int:entry_id>', methods=['GET', 'PATCH', 'DELETE'])
@p_quality.require(403)
def quality_table_record(entry_id):
    service = _quality_control()
    if request.method == 'GET':
        return jsonify(_quality_record_urls(service.detail(entry_id)))
    _validate_quality_csrf()
    if request.method == 'DELETE':
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            raise QualityControlError('Dados de exclusão inválidos.')
        service.delete(entry_id, payload.get('revision'), str(current_user.id))
        return '', 204
    if request.content_length and request.content_length > 42 * 1024 * 1024:
        raise QualityControlError('O envio excede o limite de 40 MB de imagens.', 413)
    workcenters = _get_quality_workcenters()
    entry = service.save(
        request.form, request.files, str(current_user.id),
        _get_caxias_qsb_locations(workcenters),
        [f"{row['Workcenter_Code']}-{row['Name']}" for _, row in workcenters.iterrows()],
        entry_id=entry_id,
    )
    return jsonify(_quality_record_urls(entry))


@operation_quality_bp.route('/op/qualidade/tabela/registros/<int:entry_id>/imagens/<category>/<filename>', methods=['GET'])
def quality_table_image(entry_id, category, filename):
    path, mimetype = _quality_control().image_path(
        entry_id, category, filename, allow_unpublished=p_quality.can()
    )
    response = send_file(path, mimetype=mimetype, conditional=True)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@operation_quality_bp.route('/op/qualidade/tabela/produtos', methods=['GET'])
@p_quality.require(403)
def quality_table_products():
    product = request.args.get('searchProd', '').strip()
    center = request.args.get('searchCt', '').strip()
    if len(product) > 150 or len(center) > 250:
        raise QualityControlError('Filtro de produto inválido.')
    with get_engine('ftm').connect() as connection:
        data = _quality_control().repository.product_options(connection, product, center)
    return jsonify(data)


@operation_quality_bp.route('/op/qualidade/tabela/locais', methods=['POST'])
@p_quality.require(403)
def quality_table_location():
    _validate_quality_csrf()
    if not isinstance(request.get_json(silent=True), dict):
        raise QualityControlError('Dados do local inválidos.')
    return quality_location_post()


@operation_quality_bp.route('/op/qualidade/tabela/motivos-parada', methods=['POST'])
@p_quality.require(403)
def quality_table_stop_reason():
    if not _can_manage_qsb_locations():
        return abort(403)
    _validate_quality_csrf()
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get('name'), str):
        raise QualityControlError('Dados do motivo de parada inválidos.')
    reason = _quality_control().create_stop_reason(payload['name'], str(current_user.id))
    return jsonify({'reason': reason}), 201


@operation_quality_bp.route('/op/qualidade/add', methods=['POST'])
def quality_add_post():

    if 'searchProd' in request.args:
        query = f"""SELECT TOP(1) DS_MATER FROM WORK_CELL_OP 
                    WHERE ID_MATER = '{request.args["searchProd"]}'"""
        df = engine_run_query(query, 'ftm')
        data = [item[0] for item in df.values.tolist()]

        return json.dumps(data)

    elif 'searchCt' in request.args:
        query = f"""SELECT DISTINCT(ID_MATER) FROM WORK_CELL_OP
                    WHERE ID_WORK_UNIT = '{request.args["searchCt"].split('-')[0]}'"""
        df = engine_run_query(query, 'ftm')
        data = [item[0] for item in df.values.tolist()]

        return json.dumps(data)


@operation_quality_bp.route('/op/qualidade/locations', methods=['POST'])
def quality_location_post():
    if not _can_manage_qsb_locations():
        return abort(403)

    payload = request.get_json(silent=True) or {}
    location = ' '.join(str(payload.get('name', '') or '').split())

    if not location:
        return jsonify({'error': 'Informe o nome do local.'}), 400

    if len(location) > 150:
        return jsonify({'error': 'O local deve ter no máximo 150 caracteres.'}), 400

    existing_locations = {
        existing_location.casefold()
        for existing_location in _get_caxias_qsb_locations()
    }
    if location.casefold() in existing_locations:
        return jsonify({'error': 'Este local já está disponível para seleção.'}), 409

    query = text("""INSERT INTO dbo.JDT_OPE_QUAL_LOCATIONS (name, createdBy)
                    VALUES (:name, :created_by)""")
    params = {
        'name': location,
        'created_by': current_user.id,
    }

    try:
        engine = get_engine('jdt')
        with engine.begin() as cnnx:
            cnnx.execute(query, params)
    except IntegrityError:
        return jsonify({'error': 'Este local já está cadastrado.'}), 409

    return jsonify({'location': location}), 201


# PÁGINA DA SELEÇÃO PARA EDIÇÃO DE ENTRADAS AO INFORMATIVO DA QUALIDADE - OPERATION MEETING
@operation_quality_bp.route('/op/qualidade/edit_select', methods=['GET'])
@p_quality.require(403)
def quality_list_get():

    query = f"""SELECT q.type, q.typeDesc, q.description, FORMAT(q.openDate, 'dd/MM/yyyy') AS openDate,
                       q.prodFamily, q.id, q.unit FROM JDT_OPE_QUAL q {JOIN}
                WHERE {VISIBLE} ORDER BY q.openDate DESC"""
    data = engine_run_query(query, 'jdt')

    if data.empty:
        entries = [['Nenhuma entrada disponível ainda', '-']]

    else:
        entries = data.astype(str).values.tolist()
        for line in entries:
            line.extend(['Editar', 'Remover'])

    return render_template('operation.qual/op_qual_select.html', entries=entries, header='edição')

@operation_quality_bp.route('/op/qualidade/download', methods=['GET'])
def quality_list_download_get():

    # DELETA OS ARQUIVOS QUE FORAM BAIXADOS POR USUÁRIO (CADA DOWNLOAD GERA UM ARQUIVO NO SISTEMA)
    path = fr'{APP_PATH}\app\static\uploads\default'
    for excel_file in os.listdir(path):
        os.remove(fr'{path}\{excel_file}')

    excel_file = qsb_file()

    return send_file(rf'{path}\{excel_file}', as_attachment=True)

# FUNÇÃO QUE PASSA OS DADOS DA EDIÇÃO DE ENTRADAS AO INFORMATIVO DA QUALIDADE - OPERATION MEETING
@operation_quality_bp.route('/op/qualidade/edit', methods=['GET'])
@p_quality.require(403)
def quality_edit_get():

    if request.args['command'] == 'edit':
            
        query = f"SELECT q.* FROM JDT_OPE_QUAL q {JOIN} WHERE q.id = :id AND {VISIBLE}"
        data = engine_run_query(query, 'jdt', {'id': _quality_entry_id()})
        if data.empty:
            abort(404)
        data['unit'] = data['unit'].astype(int)
        data = data.astype(str)

        photos_ok = data['imgOK'][0].split('||')[:-1]
        photos_nok = data['imgNOK'][0].split('||')[:-1]
            
        workcenters = _get_quality_workcenters()

        day = str(data.values.tolist()[0][9]).split(' ')[0]

        return render_template('operation.qual/op_qual_edit.html'
                               , values=data.to_json()
                               , photos_nok=photos_nok
                               , photos_ok=photos_ok
                               , day=day, comm='edit'
                               , entry=request.args["entryID"]
                               , workcenters=workcenters.to_dict(orient="records")
                               , caxias_locations=_get_caxias_qsb_locations(workcenters)
                               , can_manage_locations=_can_manage_qsb_locations())

    elif request.args['command'] == 'remove':

        service = _quality_control()
        entry_id = _quality_entry_id()
        entry = service.detail(entry_id)
        service.delete(entry_id, entry['revision'], str(current_user.id))

        return redirect('/op/qualidade/edit_select')

# V2
