"""
    FactoryRegisterAssembly
    Rotas e métodos para rastreabilidade e registro de montagem de quinta roda.

    Métodos
    -------
    _update_logs(key, old, new, extra, register)
        Registra alterações de rastreabilidade no banco de logs.

    traceability_qr()
        Exibe página principal de rastreabilidade QR, controlando acesso por permissão/admin.

    traceability_qr_register_get(types)
        Consulta dados de rastreabilidade para o tipo informado e retorna JSON para renderização.

    traceability_qr_register_post(types)
        Realiza cadastro, atualização ou alteração de status de rastreabilidade QR, com tratamento de erros e logs.

    traceability_qr_excel(types=None)
        Exporta dados de rastreabilidade para Excel, conforme tipo selecionado.

    traceability_qr_plate_get()
        Exibe página de consulta/cadastro de plaquetas, listando clientes, responsáveis e motivos.

    traceability_qr_plate_post()
        Realiza cadastro, busca ou download de plaquetas/anexos, com tratamento de erros e logs.

    Notas
    -----
    - Todas as rotas exigem autenticação e permissões específicas.
    - Utiliza SQLAlchemy para acesso ao banco.
    - Funções auxiliares internas iniciam com '_'.
    - Dados retornados são preparados para visualização, cadastro e exportação.

    LABEL ENCONDING
    -----
    1: M01
    2: M02
    6: M06
"""

import io
import json
import os
import pandas as pd
import zipfile
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user
from flask_mail import Message

from app.config import mail
from app.utils.db_utils import get_engine
from app.utils.permissions import get_permission
from app.utils.teams_utils import send_system_teams_alert
from app.utils.security_utils import update_logs

t_assembly = get_permission('T_ASSEMBLY')
t_assembly_plates = get_permission('T_ASSEMBLY_PLATES')

factoryRegister_assembly_bp = Blueprint('factoryRegister_assembly', __name__)

@factoryRegister_assembly_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return os.abort(403)


@factoryRegister_assembly_bp.route('/rastreabilidade/qr', methods=['GET', 'POST'])
def traceability_qr():

    show = "0"
    if current_user.admin or t_assembly.can():
        show = "1"

    return render_template('factoryRegister.assembly/assembly_main.html', show=show)

@factoryRegister_assembly_bp.route('/rastreabilidade/qr/cadastro/<int:types>', methods=['GET'])
@t_assembly.require(403)
def traceability_qr_register_get(types):

    engine = get_engine('trace_qr')
    with engine.connect() as cnnx:

        query = f"""SELECT 
                            COD_MATERIAL
                            , COD_MATERIAL_QR
                            , CODE_QR
                            , ALTURA_SAPATA
                            , MOD_SAPATA_RAST
                            , MODELO_CONF_RASTREAB
                            , FORNECEDOR_SAPATA
                            , PINTURA
                            , DESC_MATERIAL
                            , PLAQUETA_CAMPO1
                            , PLAQUETA_CAMPO2
                            , PLAQUETA_CAMPO3
                            , PLAQUETA_CAMPO4
                            , PLAQUETA_CAMPO5
                            , PLAQUETA_CAMPO6
                            , PLAQUETA_CAMPO7
                            , MANUAL_CLIENTE
                            , ETIQUETA_CLIENTE

                            , CONFIG_STATUS

                        FROM 
                            CAD_RECEITA_INSP_QR
                            
                        WHERE CT = '{types}'"""
        data = pd.read_sql(query, cnnx)
        
    return render_template(f'factoryRegister.assembly/assembly_{types}.html', types=types, data=data.to_json(orient='records'))

@factoryRegister_assembly_bp.route('/rastreabilidade/qr/cadastro/<int:types>', methods=['POST'])
@t_assembly.require(403)
def traceability_qr_register_post(types):

    engine = get_engine('trace_qr')
    with engine.connect() as cnnx:

        payload = request.get_json()

        if request.args['type'] == 'status':

            query = f"""UPDATE CAD_RECEITA_INSP_QR SET 
                            CONFIG_STATUS = {payload['STATUS']}
                        WHERE COD_MATERIAL = '{payload['COD_MATERIAL']}'"""
            
            cnnx.execute(text(query))

            old_status = "1" if payload['STATUS'] == 0 else "1"
            update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', payload['COD_MATERIAL'], old_status, payload['STATUS'], 'CONFIG_STATUS', f"assembly_{types}")
        
        else:

            if types == 2:

                payload['MANUAL_CLIENTE'] = "NULL" if payload['MANUAL_CLIENTE'] == '' else "'" + payload['MANUAL_CLIENTE'] + "'"
                payload['ETIQUETA_CLIENTE'] = "NULL" if payload['ETIQUETA_CLIENTE'] == '' else "'" + payload['ETIQUETA_CLIENTE'] + "'"

            else:

                payload['FORNECEDOR_SAPATA'] = "NULL" if payload['FORNECEDOR_SAPATA'] == '' else "'" + payload['FORNECEDOR_SAPATA'] + "'"


            if request.args['type'] == 'new':

                if types != 2:

                    query = f"""INSERT INTO CAD_RECEITA_INSP_QR VALUES (
                        '{payload['COD_MATERIAL']}', '{payload['COD_MATERIAL_QR']}', 0, 0, '{payload['CODE_QR']}', 0, '{payload['MODELO_CONF_RASTREAB']}', 0, 0, 0, 0, 0, 0,
                        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                        0, 0, 0, 0, 0, 0, 0, '{payload['ALTURA_SAPATA']}', '{payload['MOD_SAPATA_RAST']}', 0, 0, 0, 0, 0, 0, 0, 0,
                        0, 0, 0, '{payload['PINTURA']}', '{payload['DESC_MATERIAL']}', '{types}', 0, NULL, NULL, '{payload['PLAQUETA_CAMPO1']}', '{payload['PLAQUETA_CAMPO2']}', '{payload['PLAQUETA_CAMPO3']}', '{payload['PLAQUETA_CAMPO4']}', '{payload['PLAQUETA_CAMPO5']}', '{payload['PLAQUETA_CAMPO6']}', NULL, NULL, NULL, {payload['FORNECEDOR_SAPATA']})"""
                else:

                    query = f"""INSERT INTO CAD_RECEITA_INSP_QR VALUES (
                        '{payload['COD_MATERIAL']}', '{payload['COD_MATERIAL_QR']}', 0, 0, '{payload['CODE_QR']}', 0, '{payload['MODELO_CONF_RASTREAB']}', 0, 0, 0, 0, 0, 0,
                        0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                        0, 0, 0, 0, 0, 0, 0, '{payload['ALTURA_SAPATA']}', '{payload['MOD_SAPATA_RAST']}', 0, 0, 0, 0, 0, 0, 0, 0,
                        0, 0, 0, '{payload['PINTURA']}', '{payload['DESC_MATERIAL']}', '{types}', 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, {payload['MANUAL_CLIENTE']}, {payload['ETIQUETA_CLIENTE']}, NULL)"""
            
                try:
                    cnnx.execute(text(query))
                    update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', payload['COD_MATERIAL'], "", "", "new", f"assembly_{types}")
                except IntegrityError as e:
                    # Verifica se é violação de chave primária
                    if hasattr(e.orig, 'args') and e.orig.args and '2627' in str(e.orig.args):
                        return jsonify({"error": "Chave primária duplicada."}), 409
                    else:
                        return jsonify({"error": "Erro de integridade no banco de dados."}), 400
                except SQLAlchemyError as e:
                    send_system_teams_alert(f'Cadastro de Rastreabilidade - M0{types}', e, current_user.name)
                    return jsonify({"error": str(e)}), 500
                            
            elif request.args['type'] == 'old':

                query = f"""SELECT * FROM CAD_RECEITA_INSP_QR WHERE COD_MATERIAL = '{payload['COD_MATERIAL']}'"""
                data_to_compare = pd.read_sql(query, cnnx)
                data_to_compare = data_to_compare.applymap(lambda x: int(x) if isinstance(x, float) and x.is_integer() else x).fillna("").astype(str)

                if types != 2:

                    query = f"""UPDATE CAD_RECEITA_INSP_QR SET 
                                    COD_MATERIAL = '{payload['COD_MATERIAL']}',
                                    COD_MATERIAL_QR = '{payload['COD_MATERIAL_QR']}',
                                    CODE_QR = '{payload['CODE_QR']}',
                                    MODELO_CONF_RASTREAB = '{payload['MODELO_CONF_RASTREAB']}',
                                    ALTURA_SAPATA = '{payload['ALTURA_SAPATA']}',
                                    MOD_SAPATA_RAST = '{payload['MOD_SAPATA_RAST']}',
                                    PINTURA = '{payload['PINTURA']}',
                                    DESC_MATERIAL = '{payload['DESC_MATERIAL']}',
                                    PLAQUETA_CAMPO1 = '{payload['PLAQUETA_CAMPO1']}',
                                    PLAQUETA_CAMPO2 = '{payload['PLAQUETA_CAMPO2']}',
                                    PLAQUETA_CAMPO3 = '{payload['PLAQUETA_CAMPO3']}',
                                    PLAQUETA_CAMPO4 = '{payload['PLAQUETA_CAMPO4']}',
                                    PLAQUETA_CAMPO5 = '{payload['PLAQUETA_CAMPO5']}',
                                    PLAQUETA_CAMPO6 = '{payload['PLAQUETA_CAMPO6']}',
                                    FORNECEDOR_SAPATA = {payload['FORNECEDOR_SAPATA']}

                                WHERE COD_MATERIAL = '{payload['COD_MATERIAL']}'"""
                    
                else:
                    query = f"""UPDATE CAD_RECEITA_INSP_QR SET 
                                    COD_MATERIAL = '{payload['COD_MATERIAL']}',
                                    COD_MATERIAL_QR = '{payload['COD_MATERIAL_QR']}',
                                    CODE_QR = '{payload['CODE_QR']}',
                                    MODELO_CONF_RASTREAB = '{payload['MODELO_CONF_RASTREAB']}',
                                    ALTURA_SAPATA = '{payload['ALTURA_SAPATA']}',
                                    MOD_SAPATA_RAST = '{payload['MOD_SAPATA_RAST']}',
                                    PINTURA = '{payload['PINTURA']}',
                                    DESC_MATERIAL = '{payload['DESC_MATERIAL']}',
                                    MANUAL_CLIENTE = {payload['MANUAL_CLIENTE']},
                                    ETIQUETA_CLIENTE = {payload['ETIQUETA_CLIENTE']}

                                WHERE COD_MATERIAL = '{payload['COD_MATERIAL']}'"""
                
                cnnx.execute(text(query))

                if types == 2:
                    payload['MANUAL_CLIENTE'] = "" if payload['MANUAL_CLIENTE'] == 'NULL' else payload['MANUAL_CLIENTE'].replace("'", "")
                    payload['ETIQUETA_CLIENTE'] = "" if payload['ETIQUETA_CLIENTE'] == 'NULL' else payload['ETIQUETA_CLIENTE'].replace("'", "")

                else:

                    payload['FORNECEDOR_SAPATA'] = "" if payload['FORNECEDOR_SAPATA'] == 'NULL' else payload['FORNECEDOR_SAPATA'].replace("'", "")


                for key, value in payload.items():
                    if data_to_compare[key][0] != str(value):
                        update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', payload['COD_MATERIAL'], data_to_compare[key][0], str(value), key, f"assembly_{types}")

        cnnx.commit()

    return 'COMMITED'

@factoryRegister_assembly_bp.route('/rastreabilidade/qr/excel/', methods=['POST'])
@factoryRegister_assembly_bp.route('/rastreabilidade/qr/excel/<int:types>', methods=['POST'])
def traceability_qr_excel(types=None):

    path = fr'{os.getcwd()}\app\static\uploads\default'
    excel_filename = f'{path}\quinta_roda.xlsx'
    if os.path.exists(excel_filename):
        os.remove(excel_filename)
    
    if types is None:
        query = f"""
                SELECT 
                    COALESCE(T3.name, T1.extraMotive) AS motive
                    , T1.treaceabilityId
                    , FORMAT(T1.expectedDate, 'dd/MM/yyyy') AS expectedDate
                    , T2.name AS clientName
                    , T4.name AS responsibleName
                    , FORMAT(T1.createDate, 'dd/MM/yyyy') AS createDate
                FROM JDT_FAC_ASSEMBLY_PLATES T1
                    JOIN JDT_FAC_ASSEMBLY_CLIENTS T2 ON T1.clientId = T2.id
                    LEFT JOIN JDT_FAC_ASSEMBLY_PLATES_MOTIVES T3 ON T1.motive = T3.id
                    JOIN JDT_USER_DETAILS T4 ON T1.requesterId = T4.id

                    """

    elif types != 2:
        query = f"""SELECT 
                            COD_MATERIAL, 
                            COD_MATERIAL_QR, 
                            CODE_QR, 
                            ALTURA_SAPATA, 
                            MOD_SAPATA_RAST, 
                            PINTURA, 
                            MODELO_CONF_RASTREAB,
                            FORNECEDOR_SAPATA,
                            DESC_MATERIAL,
                            PLAQUETA_CAMPO1,
                            PLAQUETA_CAMPO2,
                            PLAQUETA_CAMPO3,
                            PLAQUETA_CAMPO4,
                            PLAQUETA_CAMPO5,
                            PLAQUETA_CAMPO6
                        FROM 
                            CAD_RECEITA_INSP_QR
                            
                        WHERE CT = '{types}'"""
    
    else:
        query = f"""SELECT 
                                COD_MATERIAL, 
                                COD_MATERIAL_QR, 
                                CODE_QR, 
                                ALTURA_SAPATA, 
                                MOD_SAPATA_RAST, 
                                PINTURA, 
                                MODELO_CONF_RASTREAB, 
                                DESC_MATERIAL,
                                MANUAL_CLIENTE,
                                ETIQUETA_CLIENTE
                            FROM 
                                CAD_RECEITA_INSP_QR
                                
                            WHERE CT = '{types}'"""

    engine = get_engine('jdt' if types is None else 'trace_qr')
    with engine.connect() as cnnx:    
        data = pd.read_sql(query, cnnx)

    data = data.rename(columns={
        'COD_MATERIAL': 'Cód. Material', 'COD_MATERIAL_QR': 'Cód. Material QR', 
        'CODE_QR': 'Cód. QR', 'ALTURA_SAPATA': 'Altura Sapata', 
        'MOD_SAPATA_RAST': 'Modelo Sapata Rast.', 'PINTURA': 'Pintura', 
        'MODELO_CONF_RASTREAB': 'Modelo Conf. Rast.', 'DESC_MATERIAL' : 'Desc Material',

        'motive': 'Motivo do Registro', 'treaceabilityId': 'Cód. Rastreabilidade', 
        'expectedDate': 'Data de Envio', 'clientName': 'Cliente', 
        'responsibleName': 'Criador Por', 'createDate': 'Data de Registro'})
    data.to_excel(excel_filename, index=False, header=True)

    return send_file(excel_filename, as_attachment=True)

@factoryRegister_assembly_bp.route('/rastreabilidade/qr/plaquetas', methods=['GET'])
def traceability_qr_plate_get():

    show = "0"
    if t_assembly_plates.can():
        show = "1"

    engine = get_engine('jdt')
    with engine.connect() as cnnx:  

        query = f"""
                SELECT 
                    T1.id
                    , COALESCE(T3.name, T1.extraMotive) AS motive
                    , T1.treaceabilityId
                    , FORMAT(T1.expectedDate, 'dd/MM/yyyy') AS expectedDate
                    , T2.name AS clientName
                    , T4.name AS responsibleName
                    , FORMAT(T1.createDate, 'dd/MM/yyyy') AS createDate
                FROM JDT_FAC_ASSEMBLY_PLATES T1
                    JOIN JDT_FAC_ASSEMBLY_CLIENTS T2 ON T1.clientId = T2.id
                    LEFT JOIN JDT_FAC_ASSEMBLY_PLATES_MOTIVES T3 ON T1.motive = T3.id
                    JOIN JDT_USER_DETAILS T4 ON T1.requesterId = T4.id
        """
        plates = pd.read_sql(query, cnnx)

        query = f"""
                SELECT 
                    T1.id
                    , T1.name as clientName
                    , T1.responsible AS clientResponsible
                    , T2.name as creatorName
                    , T1.status
                    , FORMAT(T1.changeDate, 'dd/MM/yyyy') AS changeDate
                FROM JDT_FAC_ASSEMBLY_CLIENTS T1
                    JOIN JDT_USER_DETAILS T2 ON T1.userId = T2.id
        """                
        clients = pd.read_sql(query, cnnx)

        query = f"""SELECT 
                        id, name 
                    FROM JDT_USER_DETAILS 
                    WHERE role LIKE '%Rastreabilidade - Montagem Plaqueta%'"""
        responsibles = pd.read_sql(query, cnnx)

        query = f""" SELECT * FROM JDT_FAC_ASSEMBLY_PLATES_MOTIVES"""
        motives = pd.read_sql(query, cnnx)

    return render_template(f'factoryRegister.assembly/assembly_plates.html', show=show
                            , motives=motives.to_dict(orient='records')
                            , clients=clients.to_dict(orient='records')
                            , responsibles=responsibles.to_dict(orient='records')
                            , plates=plates.to_dict(orient='records'))

@factoryRegister_assembly_bp.route('/rastreabilidade/qr/plaquetas', methods=['POST'])
def traceability_qr_plate_post():

    if not t_assembly_plates.can():
        abort(403)

    payload = request.get_json(silent=True) or {}


    engine = get_engine('jdt')
    with engine.connect() as cnnx:  

        if request.args['type'] == 'plate':

            if request.args['extra'] == 'insert':

                files = request.files.getlist("attachments")
                filesToSave = []
                filesList = []
                for file in files:
                    original_name = file.filename
                    group_folder = os.path.join('app', 'static', 'uploads', 'assembly')
                    file_path = os.path.join(group_folder, original_name)


                    if os.path.exists(file_path):
                        counter = 1
                        while os.path.exists(file_path):
                            name, ext = os.path.splitext(original_name)
                            original_name = f"{name}_{counter}{ext}"
                            file_path = os.path.join(group_folder, original_name)
                            counter += 1

                    filesList.append(original_name)
                    filesToSave.append((file, file_path))

                motive = request.form.get('motiveId')
                if motive.isdigit():
                    motive_id = motive
                    motive_extra = 'NULL'
                else:
                    motive_id = 'NULL'
                    motive_extra = f"'{motive}'"

                query = f"""
                    INSERT INTO JDT_FAC_ASSEMBLY_PLATES VALUES (
                        '{current_user.id}'
                        , '{request.form.get('treaceabilityId')}'
                        , '{request.form.get('clientId')}'
                        , '{request.form.get('internalResponsibleId')}'
                        , '{request.form.get('expectedDate')}'
                        , '{json.dumps(filesList, ensure_ascii=False)}'
                        , GETDATE()
                        , {motive_id}
                        , {motive_extra}
                    )
                """

                try:
                    cnnx.execute(text(query))

                    for file, path in filesToSave:
                        file.save(path)

                    query = f"""SELECT 
                                    companyEmail 
                                FROM JDT_USER_DETAILS 
                                WHERE role LIKE '%Rastreabilidade - Montagem Plaqueta%'"""
                    internalResponsibles = pd.read_sql(query, cnnx)['companyEmail'].to_list()

                    query = f"""SELECT name FROM JDT_FAC_ASSEMBLY_CLIENTS WHERE id = {request.form.get('clientId')}"""
                    clientName = pd.read_sql(query, cnnx)['name'][0]

                    query = f"""SELECT name FROM JDT_USER_DETAILS WHERE id = '{request.form.get('internalResponsibleId')}'"""
                    clientResponsible = pd.read_sql(query, cnnx)['name'][0]

                    query = f"""SELECT name FROM JDT_FAC_ASSEMBLY_PLATES_MOTIVES WHERE id = '{request.form.get('motiveId')}'"""
                    motive = pd.read_sql(query, cnnx)['name'][0] if motive.isdigit() else motive

                    msg = Message(f'Rastreabilidade QR - Nova Plaqueta',
                        sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                        recipients=internalResponsibles)
                    
                    msg.html = render_template('factoryRegister.assembly/assembly_plates_email.html',
                                                    userName=current_user.name,
                                                    treaceabilityId=request.form.get('treaceabilityId'),
                                                    clientName=clientName,
                                                    clientResponsible=clientResponsible,
                                                    motive=motive,
                                                    expectedDate=datetime.strptime(request.form.get('expectedDate'), '%Y-%m-%d').strftime('%d/%m/%Y'))
                    
                    for file, path in filesToSave:
                        with open(path, 'rb') as f:
                            msg.attach(filename=os.path.basename(path),
                                    content_type='application/octet-stream',
                                    data=f.read())
                            
                    mail.send(msg)

                except IntegrityError as e:
                    return jsonify({"error": "Erro de integridade no banco de dados."}), 400
                except SQLAlchemyError as e:
                    send_system_teams_alert(f'Rastreabilidade QR - Plaquetas', e, current_user.name)
                    return jsonify({"error": str(e)}), 500

            elif request.args['extra'] == 'search':

                query = """
                    SELECT 
                        T2.PLAQUETA_CAMPO1,
                        T2.PLAQUETA_CAMPO2,
                        T2.PLAQUETA_CAMPO3,
                        T2.PLAQUETA_CAMPO4,
                        T2.PLAQUETA_CAMPO5,
                        T2.PLAQUETA_CAMPO6
                    FROM RASTREABILIDADE T1
                    JOIN CAD_RECEITA_INSP_QR T2 ON T1.MATERIAL COLLATE Latin1_General_CI_AS = T2.COD_MATERIAL
                    WHERE T1.CODIGO = ?
                """

                engine = get_engine('trace_qr')
                with engine.connect() as cnnx: 
                    data = pd.read_sql(query, cnnx, params=(payload['id'],))

                if data.empty:
                    return 'TREACEBILITY NOT EXISTS', 404

                return jsonify(data.to_dict(orient='records')), 200

            elif request.args['extra'] == 'attachments':
                
                query = f"""SELECT attachments FROM JDT_FAC_ASSEMBLY_PLATES WHERE id = {payload['id']}"""
                files = pd.read_sql(query, cnnx)

                if files.empty:
                    return 'TREACEBILITY NOT EXISTS', 404
                
                files = json.loads(files['attachments'][0])
                upload_folder = os.path.join('app', 'static', 'uploads', 'assembly')

                if len(files) == 1:
                    return send_file(
                        os.path.join(upload_folder, files[0]),
                        download_name=files[0],
                        as_attachment=True
                    )
                
                else:

                    memory_file = io.BytesIO()
                    
                    with zipfile.ZipFile(memory_file, 'w') as zf:
                        for filename in files:
                            file_path = os.path.join(upload_folder, filename)
                            if os.path.exists(file_path):
                                zf.write(file_path, arcname=filename)

                    memory_file.seek(0)

                    return send_file(
                        memory_file,
                        mimetype='application/zip',
                        download_name='arquivos.zip',
                        as_attachment=True
                    )

        elif request.args['type'] == 'client':
            
            if request.args['extra'] == 'insert':
                query = f"""
                    INSERT INTO JDT_FAC_ASSEMBLY_CLIENTS VALUES (
                        '{payload['name']}'
                        , '{payload['responsible']}'
                        , '{current_user.id}'
                        , 1
                        , GETDATE()
                    )    
                """
            
            else:
                query = f"""
                    UPDATE JDT_FAC_ASSEMBLY_CLIENTS SET
                        name = '{payload['name']}'
                        , responsible = '{payload['responsible']}'
                        , userId = '{current_user.id}'
                        , changeDate = GETDATE()
                        , status = {payload['status']}

                    WHERE id = '{payload['id']}'"""

                try:
                    cnnx.execute(text(query))
                except IntegrityError as e:
                    # Verifica se é violação de chave primária
                    if hasattr(e.orig, 'args') and e.orig.args and '2627' in str(e.orig.args):
                        return jsonify({"error": "Cliente já registrado."}), 409
                    else:
                        return jsonify({"error": "Erro de integridade no banco de dados."}), 400
                except SQLAlchemyError as e:
                    send_system_teams_alert(f'Rastreabilidade QR - Plaquetas', e, current_user.name)
                    return jsonify({"error": str(e)}), 500

        cnnx.commit()

    return 'COMMITED'
