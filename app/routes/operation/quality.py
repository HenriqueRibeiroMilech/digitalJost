import shutil
from datetime import datetime
import pandas as pd
import json
import os

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from flask import Blueprint, abort, jsonify, render_template, request, redirect, send_file, url_for
from flask_login import current_user

from app.utils.constants import APP_PATH
from app.utils.db_utils import engine_run_query, get_engine
from app.utils.dynamic_constants import getPlex
from app.utils.files_utils import qsb_file
from app.utils.permissions import get_permission


p_quality = get_permission('QUALITY')

operation_quality_bp = Blueprint('operation_quality', __name__)

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
        aux = "AND unit = :unit"
        params['unit'] = request.args['unit']

    query = f"SELECT * FROM JDT_OPE_QUAL WHERE openDate = :day {aux}"
    df = engine_run_query(query, 'jdt', params)

    file = []
    for _, row in df.iterrows():
        repeat = 'Sim' if row.get('repeat') else 'Não'
        file_info = {
            'Local da Ocorrencia': [str(row.get('type', '')), str(row.get('typeDesc', ''))]
            , 'Imagens NOK': [item for item in str(row.get('imgNOK', '')).split('||') if item]
            , 'Imagens OK': [item for item in str(row.get('imgOK', '')).split('||') if item]
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
            unit_filter = "AND unit = :unit"
            params['unit'] = unit
        except ValueError:
            return abort(400, "Unidade inválida.")

    query = f"""
        SELECT DAY(openDate) AS day, type
        FROM JDT_OPE_QUAL
        WHERE YEAR(openDate) = :year AND MONTH(openDate) = :month {unit_filter}
        ORDER BY openDate
    """
    df = engine_run_query(query, 'jdt', params)
    
    # Converte o resultado para lista de listas
    entries = df[['day', 'type']].values.tolist() if not df.empty else []
    return json.dumps(entries)


# PÁGINA DA VISUALIZAÇÃO DOS DETALHES DO INFORMATIVO DA QUALIDADE - OPERATION MEETING
@operation_quality_bp.route('/op/qualidade/view', methods=['GET'])
def quality_detail_get():
    day = request.args['day'].split('/')
    day = f'{day[2]}-{day[1]}-{day[0]}'

    file = _QUALITY_DETAIL(day)

    aux = ""
    if 'unit' in request.args:
        aux = "&unit=" + request.args['unit']

    return render_template('operation.qual/op_qual_view.html', file=file, day=request.args['day'], unit=aux)

# ROTA DE POST, QUE PASSA OS DADOS E ARQUIVOS RECEBIDOS PELO FORMULÁRIO AO BANCO DE DADOS SQL E AOS DIRETÓRIOS
@operation_quality_bp.route('/op/qualidade/update', methods=['POST'])
@p_quality.require(403)
def quality_detail_post():

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
        query = f"""SELECT 
                        imgNOK, imgOK 
                    FROM 
                        JDT_OPE_QUAL WHERE id = '{request.args['entryID']}'"""  # query para selecionar as imagens da ocorrencia

        sql_data = engine_run_query(query, 'jdt')

        img_nok = sql_data['imgNOK'][0]  # armazena os nomes dos arquivos NOK
        img_ok = sql_data['imgOK'][0]  # amazena os nomes dos arquivos OK

        caminho = request.args['entryID']  # redefini o ID da ocorrencia

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

        query = f"""SELECT MAX(id) as last_id FROM JDT_OPE_QUAL"""
        data = engine_run_query(query, 'jdt')['last_id'][0]

        year = data[:4]
        last_id = int(data[-5:])

        if year != str(datetime.now().year):
            last_id = 10000

        caminho = str(datetime.now().year) + str(last_id + 1)

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
                if os.path.exists(rf'{APP_PATH}\app\static\uploads\operation\img_nok\{request.args["entryID"]}\{image}'):
                    os.remove(rf'{APP_PATH}\app\static\uploads\operation\img_nok\{request.args["entryID"]}\{image}')

        for image in request.form['deletar2'].split("__,"):
            if image != "":
                img_ok = img_ok.replace(image + '||', "")
                if os.path.exists(rf'{APP_PATH}\app\static\uploads\operation\img_ok\{request.args["entryID"]}\{image}'):
                    os.remove(rf'{APP_PATH}\app\static\uploads\operation\img_ok\{request.args["entryID"]}\{image}')

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

    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        cnnx.execute(query, query_params)

    return redirect("/op/qualidade/edit_select")


# PÁGINA PARA IMPRESSÃO DO INFORMATIVO DA QUALIDADE - OPERATION MEETING
@operation_quality_bp.route('/op/qualidade/printer', methods=['GET'])
def quality_printer_get():
    day = request.args['day'].split('/')
    day = f'{day[2]}-{day[1]}-{day[0]}'

    file = _QUALITY_DETAIL(day)
    return render_template('operation.qual/op_qual_print.html', file=file, day=request.args['day'])


# PÁGINA DA ADIÇÃO DE ENTRADAS AO INFORMATIVO DA QUALIDADE - OPERATION MEETING
@operation_quality_bp.route('/op/qualidade/add', methods=['GET'])
def quality_add_get():
    workcenters = _get_quality_workcenters()

    return render_template('operation.qual/op_qual_add.html'
                           , workcenters=workcenters.to_dict(orient="records")
                           , caxias_locations=_get_caxias_qsb_locations(workcenters)
                           , can_manage_locations=_can_manage_qsb_locations())

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

    query = "SELECT type, typeDesc, description, FORMAT(openDate, 'dd/MM/yyyy') AS openDate, prodFamily, id, unit FROM JDT_OPE_QUAL ORDER BY openDate DESC"
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
            
        query = f'SELECT * FROM JDT_OPE_QUAL WHERE id = {request.args["entryID"]}'
        data = engine_run_query(query, 'jdt')
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

        engine = get_engine('jdt')
        with engine.begin() as cnnx:
            query = f"""DELETE FROM JDT_OPE_QUAL WHERE id = {request.args["entryID"]}"""
            cnnx.execute(text(query))

        # deleta todos os arquivos da ocorrencia
        shutil.rmtree(rf'{APP_PATH}\app\static\uploads\operation\img_nok\{request.args["entryID"]}')
        shutil.rmtree(rf'{APP_PATH}\app\static\uploads\operation\img_ok\{request.args["entryID"]}')

        return redirect('/op/qualidade/edit_select')
