"""
    JDT Library
    Rotas e métodos para gerenciamento da biblioteca de conhecimentos, incluindo cadastro, consulta, atualização, download e permissões.

    Métodos
    -------
    route_auth()
        Verifica autenticação e permissão do usuário antes de acessar as rotas do blueprint.
    library_get()
        Exibe página principal da biblioteca, listando títulos e e-mails.
    library_create_post()
        Realiza cadastro de novo item na biblioteca e envia notificação por e-mail.
    library_manage_get()
        Exibe página de gerenciamento dos itens da biblioteca.
    library_manage_post()
        Atualiza status, observações e envia notificação ao criador.
    library_search_get()
        Exibe detalhes de um item da biblioteca, permissões e áreas impactadas.
    library_search_post()
        Retorna histórico de versões de um item da biblioteca.
    library_knowledge()
        Gerencia inserção, atualização e versão de arquivos de conhecimento, respeitando permissões.
    library_knowledge_download()
        Realiza download de arquivos da biblioteca.

    Notas
    -----
    - Todas as rotas exigem autenticação e permissões específicas.
    - Utiliza SQLAlchemy para acesso ao banco.
    - Funções auxiliares internas iniciam com '_'.

    - Dados retornados são preparados para visualização, cadastro e exportação.
"""

import json
import os
import pandas as pd

from sqlalchemy import text

from flask import Blueprint, abort, redirect, render_template, request, send_file, url_for
from flask_mail import Message
from flask_login import current_user

from app.utils.db_utils import get_engine
from app.utils.permissions import get_permission
from app.config import mail

jdt_library_bp = Blueprint('jdt_library', __name__)

@jdt_library_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)
        

@jdt_library_bp.route('/biblioteca')
def library_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT id, title FROM JDT_MAIN_LIBRARY WHERE status = 1"""
        libraries = pd.read_sql(query, cnnx).to_dict(orient='records')

        query = f"""SELECT companyEmail FROM JDT_USER_DETAILS WHERE active = 1 and generic = 0"""
        mails = pd.read_sql(query, cnnx)['companyEmail'].tolist()
    
    return render_template('jdt.library/library_main.html', libraries=libraries, mails=mails)

@jdt_library_bp.route('/biblioteca/criar', methods=['POST'])
def library_create_post():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT count(*) AS QTT FROM JDT_MAIN_LIBRARY"""
        library_id = pd.read_sql(query, cnnx)['QTT'][0]

        data_to_insert = request.get_json()
        query = f"""INSERT INTO JDT_MAIN_LIBRARY VALUES (
                    {library_id}, 
                    '{data_to_insert['title']}',
                    '{data_to_insert['description']}',
                    '{json.dumps(data_to_insert['impactedAreas'])}',
                    '{json.dumps(data_to_insert['permission'])}',
                    0, '{current_user.id}', NULL, NULL, NULL)"""

        cnnx.execute(text(query))

        msg = Message(f'Biblioteca de Conhecimentos',
                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                recipients=['JostTransformacaoDigital@empresasrandon.onmicrosoft.com'],
                cc=[current_user.companyEmail])

        msg.html = render_template('jdt.library/library_email_avaliate.html', librarytTitle=data_to_insert['title'],
                                    userName=current_user.name, description=data_to_insert['description'])
        mail.send(msg)

        cnnx.commit()

    return 'SENDED'

@jdt_library_bp.route('/biblioteca/gerenciar', methods=['GET'])
def library_manage_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT 

                        T1.title,
                        T1.description,
                        T1.impactedAreas,
                        T1.permission,
                        T2.name AS createdBy,
                        CASE WHEN T3.name IS NULL THEN 'Aguardando resposta' ELSE T3.name END AS answeredBy,
                        CASE WHEN answeredDate IS NULL THEN 'Aguardando resposta' ELSE FORMAT(answeredDate, 'dd/MM/yyyy HH:mm:ss') END AS answeredDate,
                        T1.status, T1.id

                    FROM JDT_MAIN_LIBRARY AS T1
                        JOIN JDT_USER_DETAILS AS T2 ON T1.createdBy = T2.id
                        LEFT JOIN JDT_USER_DETAILS AS T3 ON T1.answeredBy = T3.id"""
        libraries = pd.read_sql(query, cnnx).astype(str)

    return render_template('jdt.library/library_manage.html', libraries=json.dumps(libraries.to_dict(orient='records')), admin=str(current_user.admin))

@jdt_library_bp.route('/biblioteca/gerenciar', methods=['POST'])
def library_manage_post():
    
    if current_user.admin:

        data_to_update = request.get_json()

        engine = get_engine('jdt')
        with engine.connect() as cnnx:
    
            query = f"""SELECT T2.companyEmail FROM JDT_MAIN_LIBRARY AS T1 JOIN JDT_USER_DETAILS AS T2 ON T2.id = T1.createdBy WHERE T1.id = {data_to_update['id']}"""
            user_mail = pd.read_sql(query, cnnx)['companyEmail'][0]


            query = f"""UPDATE JDT_MAIN_LIBRARY SET 
                            status = {1 if data_to_update['status'] == 1 else 2},
                            obsText = {"'" + data_to_update['obsText'] + "'" if len(data_to_update['obsText']) > 0 else 'NULL'},
                            answeredDate = GETDATE(),
                            answeredBy = '{current_user.id}'
                        WHERE id = {data_to_update['id']}
                        """
            cnnx.execute(text(query))

            msg = Message(f'Biblioteca de Conhecimentos',
                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                recipients=[user_mail])


            msg.html = render_template('jdt.library/library_email_answered.html')
            mail.send(msg)

            cnnx.commit()
    
        return 'UPDATED'

    return 'DENIED'


@jdt_library_bp.route('/biblioteca/consultar', methods=['GET'])
def library_search_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT title, description, impactedAreas, permission FROM JDT_MAIN_LIBRARY WHERE id = {request.args['id']} AND status = 1"""
        data_to_show = pd.read_sql(query, cnnx)

        query = f"""SELECT companyEmail FROM JDT_USER_DETAILS WHERE active = 1 and generic = 0"""
        mails = pd.read_sql(query, cnnx)['companyEmail'].tolist()

        query = f"""SELECT id, title, version, midiaType FROM JDT_MAIN_LIBRARY_BOOK WHERE libraryId = {request.args['id']}"""
        knowledge_to_show = pd.read_sql(query, cnnx)

    knowledge_to_show = knowledge_to_show.loc[knowledge_to_show.groupby('id')['version'].idxmax()].reset_index(drop=True).astype(str)

    admin = '0'
    if current_user.companyEmail in eval(data_to_show['permission'][0]) or current_user.admin:
        admin = '1'

    return render_template('jdt.library/library_search.html', mails=mails, admin=admin
                           , title=data_to_show['title'][0]
                           , knowledges=knowledge_to_show.to_dict(orient='records')
                           , permission=data_to_show['permission'][0]
                           , description=data_to_show['description'][0]
                           , id=request.args['id']
                           , areas=data_to_show['impactedAreas'][0])
    
@jdt_library_bp.route('/biblioteca/consultar', methods=['POST'])
def library_search_post():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT 
                        FORMAT(createDate, 'dd/MM/yyyy HH:mm:ss') AS createDate, 
                        T2.name as createdBy, 
                        CONCAT(T1.id, '_', version, '.', midiaType) as url, 
                        title 
                    FROM JDT_MAIN_LIBRARY_BOOK AS T1
                        JOIN JDT_USER_DETAILS AS T2 ON T1.createdBy = T2.id
                    
                    WHERE T1.id = {request.args['id']}"""
        history_Data = pd.read_sql(query, cnnx)

    return json.dumps(history_Data.astype(str).to_dict(orient='records'))



@jdt_library_bp.route('/biblioteca/conhecimentos', methods=['POST'])
def library_knowledge():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT permission FROM JDT_MAIN_LIBRARY WHERE id = '{request.args['id']}'"""
        permission = eval(pd.read_sql(query, cnnx)['permission'][0])

        if current_user.companyEmail in permission or current_user.admin:

            if request.args['action'] == 'insert':

                query = f"""SELECT MAX(id) AS QTT FROM JDT_MAIN_LIBRARY_BOOK"""
                bookId = pd.read_sql(query, cnnx)['QTT'].fillna(0).iloc[0] + 1

                for file in request.files.getlist('pdf'):
                    if file.filename != '':
                        query = f"""INSERT INTO JDT_MAIN_LIBRARY_BOOK VALUES (
                                        {bookId}, {request.args['id']},
                                        '{request.form['title']}', GETDATE(),
                                        '{current_user.id}', 0, '{file.filename.split('.')[-1]}')"""
                        
                        cnnx.execute(text(query))
                        file.save(os.path.join(rf'{os.getcwd()}\static\uploads\library', f"{bookId}_0.{file.filename.split('.')[-1]}"))

                cnnx.commit()   

                return 'INSERTED'

            elif request.args['action'] == 'library':

                    data_to_update = request.get_json()

                    query = f"""UPDATE JDT_MAIN_LIBRARY SET 
                                    title = '{data_to_update['title']}',
                                    description = '{data_to_update['description']}',
                                    impactedAreas = '{json.dumps(data_to_update['impactedAreas'])}',
                                    permission = '{json.dumps(data_to_update['permission'])}'
                                WHERE id = {data_to_update['id']}"""

                    cnnx.execute(text(query))
                    cnnx.commit()

                    return 'UPDATED'

            else:

                query = f"""SELECT MAX(version) as version FROM JDT_MAIN_LIBRARY_BOOK WHERE id = '{request.args['book']}'"""
                version = pd.read_sql(query, cnnx)['version'][0] + 1



                for file in request.files.getlist('pdf'):
                    if file.filename != '':
                        query = f"""INSERT INTO JDT_MAIN_LIBRARY_BOOK VALUES (
                                {request.args['book']}, {request.args['id']},
                                '{request.form['update-title']}', GETDATE(),
                                '{current_user.id}', {version}, '{file.filename.split('.')[-1]}')"""
                        cnnx.execute(text(query))
                        file.save(os.path.join(rf'{os.getcwd()}\static\uploads\library', f"{request.args['book']}_{version}.{file.filename.split('.')[-1]}"))

                cnnx.commit()   

                return 'UPDATED'
            
        return 'DENIED', 403
    

@jdt_library_bp.route('/biblioteca/conhecimentos/download')
def library_knowledge_download():

    file = rf'app\static\uploads\library\{request.args["arq"]}'
    if os.path.exists(rf'{os.getcwd()}\{file}'):
        return send_file(rf'{os.getcwd()}\{file}', as_attachment=True, download_name=request.args["arq"])
    else:
        return 'FILE DOES NOT EXISTS'