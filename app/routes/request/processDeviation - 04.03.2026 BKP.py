"""
    STATUS DE DESVIOS (LABEL ENCODING):
        0 : AGUARDANDO APROVAÇÃO
        1 : APROVADO
        2 : RECUSADO
        3 : CANCELADO
        4 : FINALIZADO
        5 : EM ANDAMENTO
        6 : VENCIDO

    OBS: QUALQUER ALTERAÇÃO NAS BASES DE DESVIOS ATIVOS DEVE SER REALIZADA NA BASE DE DESVIOS RECUSADOS
"""

import os
import pandas as pd
from datetime import datetime, timedelta

from datetime import datetime
from flask_mail import Message

from flask import Blueprint, abort, jsonify, render_template, request, redirect, send_file, url_for
from flask_login import  current_user
from sqlalchemy import text

from app.utils.constants import APP_PATH
from app.utils.data_utils import config_table, return_options
from app.utils.db_utils import engine_run_query, get_engine
from app.utils.permissions import get_permission
from app.config import mail
from app.utils.teams_utils import send_system_teams_alert

_STATUS_DICT = {
    0: 'Aguardando aprovação'
    , 1: 'Aprovado'
    , 2: 'Recusado'
    , 3: 'Cancelado'
    , 4: 'Finalizado'
    , 5: 'Em andamento'
    , 6: 'Vencido'
}

_APPROVERS_TEAMS = [[0, 'Compras'],
            [1, 'Eng. Fornecedores'],
            [2, 'Eng. Processo'],
            [3, 'Eng. Produto'],
            [4, 'Logística'],
            [5, 'Manutenção'],
            [6, 'Produção'],
            [7, 'Qualidade Cliente'],
            [8, 'Qualidade de Fábrica'],
            [9, 'SSMA'],
            [10, 'Sistemas de Qualidade'],
            [11, 'Campinas']]

request_processDeviation_bp = Blueprint('request_processDeviation', __name__)

@request_processDeviation_bp.before_request
def route_auth():
    # Verifica se o usuário está autenticado
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))

    # Verifica permissão geral
    if not get_permission('GENERAL').can():
        return abort(403)

p_admin = get_permission('DEVIATION')

# FORMATA LISTA EM STRING EX: ["randon", "jost", "conexo"] = "randon, jost e conexo"
def _LIST_UPDATE(lista):
    lista = eval(lista)
    if len(lista) > 1:
        return ', '.join(lista[:-1]) + ' e ' + lista[-1]
    else:
        return lista[0]


@request_processDeviation_bp.route('/desvios', methods=['GET'])
def dev_get():
    return render_template('request.processDeviation/dev_home.html')

@request_processDeviation_bp.route('/desvios/aprovadores', methods=['GET'])
def dev_approvers_get():

    admin = '0'
    if p_admin.can():
        admin = '1'

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = "SELECT id, name FROM JDT_USER_DETAILS WHERE generic = 0 AND active = 1 ORDER BY name ASC"
        users = pd.read_sql(query, cnnx)

        query = "SELECT sector, id FROM JDT_REQUEST_DEV_SECTORS"
        sectors = pd.read_sql(query, cnnx)

    return render_template('request.processDeviation/dev_approvers.html', admin=admin, users=users.to_dict(orient="records"), sectors=sectors.to_dict(orient='records'))


@request_processDeviation_bp.route('/desvios/aprovadores', methods=['POST'])
def dev_approvers_post():

    query = "SELECT * FROM JDT_VIEW_REQUEST_DEV_APPROVERS"
    data = engine_run_query(query, 'jdt')

    if request.args.get('excel'):

        data = data.rename(columns={'name': 'NOME FUNCIONÁRIO', 'companyName': 'UNIDADE JOST', 'sector': 'SETOR', 'id': 'USUÁRIO', 'companyEmail': 'E-MAIL'})
        
        path = fr'{os.getcwd()}\app\static\uploads\default'
        excel_filename = f'{path}\desvios.xlsx'
        if os.path.exists(excel_filename):
            os.remove(excel_filename)

        with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name='GERAL', index=False)

        return send_file(
            excel_filename,
            as_attachment=True,
            download_name='desvios.xlsx'
        )


    return data.to_dict(orient='records')


@request_processDeviation_bp.route('/desvios/aprovadores/<string:userId>/<int:sectorId>', methods=['POST'])
@p_admin.require(403)
def dev_approvers_db_post(userId, sectorId):

    try:
        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            query = """INSERT INTO JDT_REQUEST_DEV_APPROVERS (userId, sectorId, active) VALUES (:userId, :sectorId, :active)"""
            params = {"userId": userId, "sectorId": sectorId, "active": 1}
            cnnx.execute(text(query), params)

            query = """SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = :userId"""
            requesterEmail = pd.read_sql(query, cnnx, params={"userId": userId})

            if requesterEmail.empty:
                abort(404, description="Email do solicitante não encontrado")

            msg = Message(f'ATENÇÃO! NOVO APROVADOR DE DESVIOS.',
                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                    recipients=[requesterEmail['companyEmail'][0]])

            msg.html = render_template('request.processDeviation/dev_register_email.html',
                                    userName=current_user.name,
                                    sector=_APPROVERS_TEAMS[sectorId][1])

            mail.send(msg)

            cnnx.commit()
            return jsonify({"message": "Sucesso"}), 200

    except Exception as e:
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError):
            return jsonify({"message": "Aprovador já registrado para este setor."}), 400
        print("Erro inesperado:", e)
        return jsonify({"message": "Erro ao registrar aprovador."}), 500
        

@request_processDeviation_bp.route('/desvios/aprovadores/<string:userId>/<int:sectorId>', methods=['PATCH'])
@p_admin.require(403)
def dev_approvers_db_patch(userId, sectorId):

    try:
        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            query = """
                UPDATE JDT_REQUEST_DEV_APPROVERS
                SET active = CASE WHEN active = 1 THEN 0 ELSE 1 END
                WHERE userId = :userId AND sectorId = :sectorId
            """
            params = {"userId": userId, "sectorId": sectorId}
            cnnx.execute(text(query), params)
            cnnx.commit()
        return jsonify({"message": "Status atualizado."}), 200

    except Exception as e:
        print("Erro inesperado:", e)
        return jsonify({"message": "Erro ao atualizar aprovador."}), 500


@request_processDeviation_bp.route('/desvios/aprovadores/<string:userId>/<int:sectorId>', methods=['PUT'])
@p_admin.require(403)
def dev_approvers_db_put(userId, sectorId):
    try:
        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            query = """
                UPDATE JDT_REQUEST_DEV_APPROVERS
                SET sectorId = :new_sectorId
                WHERE userId = :userId AND sectorId = :old_sectorId
            """
            params = {"new_sectorId": sectorId, "userId": userId, "old_sectorId": sectorId}
            cnnx.execute(text(query), params)
            cnnx.commit()
        return jsonify({"message": "Status atualizado."}), 200
    except Exception as e:
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError):
            return jsonify({"message": "Aprovador já registrado para este setor."}), 400
        print("Erro inesperado:", e)
        return jsonify({"message": "Erro ao registrar aprovador."}), 500


@request_processDeviation_bp.route('/desvios/pop', methods=['GET'])
def dev_pop_get():
    return render_template('request.processDeviation/dev_pop.html')

@request_processDeviation_bp.route('/desvios/pop', methods=['POST'])
def dev_pop_post():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""INSERT INTO JDT_REQUEST_DEV_ALLOWED VALUES ('{current_user.id}')"""
        cnnx.execute(text(query))
        cnnx.commit()
    
    return redirect('/desvios/gerar')

@request_processDeviation_bp.route('/desvios/gerar', methods=['GET', 'POST'])
def dev_create():
    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        def insert_data():

            currentDateTime = datetime.now()
            data = currentDateTime.date()
            ano = data.strftime("%Y")  # funcoes para pegar o ano em que o usuario está

            if 'editar' not in request.args:
                query = f"""SELECT 
                                MAX(CAST(SUBSTRING(deviationId, 6, 4) AS INT)) AS lastId 
                            FROM JDT_REQUEST_DEV
                            WHERE deviationId LIKE '{ano}%'"""

                id = pd.read_sql(query, cnnx)
                last_id = id['lastId'][0] + 1 if id['lastId'][0] is not None else 1

                final_id = ano + "-" + str(last_id).zfill(4) + '-' + str(request.form['lote']) if int(
                    last_id) < 1000 else ano + "-" + str(last_id) + '-' + str(request.form['lote'])
            else:
                query = f"""SELECT deviationId FROM JDT_REQUEST_DEV WHERE deviationId = '{request.args['editar']}'"""
                count = len(pd.read_sql(query, cnnx))
                if count == 0:
                    final_id = request.args['editar']
                else:
                    return redirect ('/denied')

            if not os.path.exists('app/static/uploads/deviation/request/' + final_id + '/'):
                os.mkdir('app/static/uploads/deviation/request/' + final_id + '/')
                os.mkdir('app/static/uploads/deviation/request/' + final_id + '/motive/')
                os.mkdir('app/static/uploads/deviation/request/' + final_id + '/procedure/')
                os.mkdir('app/static/uploads/deviation/request/' + final_id + '/attachment/')

            def saveFiles(filesList, folder, dev_id):
                filesListString = ""
                acum = 0
                for file in filesList:
                    if file.filename != "":
                        newName = f"img_{acum}.{file.filename.rsplit('.', 1)[1].lower()}"
                        file.save(os.path.join(rf'{os.getcwd()}\app\static\uploads\deviation\request\{dev_id}\{folder}',
                                            newName))
                        filesListString += f'{newName}||'
                        acum += 1
                    
                return filesListString
            
            motiveImages = saveFiles(request.files.getlist('imagens1'), 'motive', final_id)
            procedureImages = saveFiles(request.files.getlist('imagens2'), 'procedure', final_id)

            query = f"""INSERT INTO JDT_REQUEST_DEV VALUES ('{final_id}', '{current_user.id}', 
                            '{request.form['equipe']}', '{request.form['unidade']}', 
                            '{request.form['ct_send']}', '{request.form['produto_send']}', 
                            '{request.form['familia_send']}', '{request.form['desc']}', 
                            '{request.form['instrucao_send']}', '{request.form['doc']}', 
                            '{request.form['data_inicio']}', '{request.form['data_fim']}', 
                            '{request.form['lote']}', '{request.form['rast']}', 
                            '{request.form['motivo']}', '{motiveImages}', 
                            '{request.form['riscos']}', '{request.form['proced']}', 
                            '{procedureImages}', GETDATE(), 0, NULL, NULL, '', 
                            '{request.form['especial1']}', '{request.form['especial2']}', '{request.form['ssma']}')"""
            cnnx.execute(text(query))

            acum = 0
            plan_mails = {}
            for keys in list(request.form.keys()):
                if 'acao_' in keys:
                    query = f"""INSERT INTO JDT_REQUEST_DEV_PLAN VALUES (
                                    '{final_id}', 
                                    '{request.form[keys]}', 
                                    '{request.form[list(request.form.keys())[acum + 1]]}',
                                    '{request.form[list(request.form.keys())[acum + 2]]}')"""
                    cnnx.execute(text(query))

                    if request.form[list(request.form.keys())[acum + 1]] in plan_mails:
                        plan_mails[request.form[list(request.form.keys())[acum + 1]]].append(request.form[keys])  
                    else:
                        plan_mails[request.form[list(request.form.keys())[acum + 1]]] = [request.form[keys]]

                acum += 1
            
            for i in plan_mails.keys():
                msg = Message(f'Desvio de processo - Nº {final_id}',
                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                    recipients=[i])

                msg.html = render_template('request.processDeviation/dev_email_plan_included.html', final_id=final_id,
                                            solicitante=current_user.name,
                                            acoes=plan_mails[i])
                mail.send(msg)

            aux = ''
            loop = _APPROVERS_TEAMS
            if str(request.form['unidade']) == "0":
                loop = _APPROVERS_TEAMS[:-1]
                aux = "WHERE sector <> 'Campinas'"

            for sector in loop:
                query = f"""INSERT INTO JDT_REQUEST_DEV_CONFIG_STATUS VALUES (
                                    '{final_id}', '{sector[0]}', NULL, 0, NULL)"""
                cnnx.execute(text(query))
            cnnx.commit()

            query = f"SELECT companyEmail FROM JDT_VIEW_REQUEST_DEV_APPROVERS {aux}"
            aprovadores_email = pd.read_sql(query, cnnx)['companyEmail'].values.tolist()

            # Loop através dos aprovadores e envia e-mails
            for email in aprovadores_email:
                # Chama a função para enviar o e-mail
                msg = Message(f'Desvio de processo - Nº {final_id}',
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=[email])

                msg.html = render_template('request.processDeviation/dev_email_avaliate.html', final_id=final_id,
                                            solicitante=current_user.name,
                                            motivo=request.form['motivo'])
                mail.send(msg)
            
        query = f"""SELECT userId FROM JDT_REQUEST_DEV_ALLOWED WHERE userId = '{current_user.id}'"""
        test = pd.read_sql(query, cnnx)

        if len(test) == 0:
            return redirect('/desvios/pop')

        if request.method == 'POST':
            if request.args['cmd'] == '1':
                insert_data()
                return redirect('/desvios')

            elif request.args['cmd'] == '2':

                query = f"SELECT MIN(status) as status FROM JDT_REQUEST_DEV_CONFIG_STATUS WHERE deviationId = '{request.args['editar']}'"
                df = pd.read_sql(query, cnnx)['status']

                if len(df) == 0:
                    return redirect('/denied')
                elif df[0] == 0:
                    return redirect('/denied')

                query = f"SELECT * FROM JDT_REQUEST_DEV WHERE deviationId = '{request.args['editar']}'"
                df = pd.read_sql(query, cnnx).astype(str)
                if df['userId'][0] != current_user.id and not current_user.admin:
                    return redirect('/denied')

                try:
                    # Inicia a transação
                    trans = cnnx.begin()
                    query = f"""
                        INSERT INTO JDT_REQUEST_DEV_REFUSED
                        SELECT *, GETDATE()
                        FROM JDT_REQUEST_DEV
                        WHERE deviationId = '{request.args['editar']}';

                        DELETE FROM JDT_REQUEST_DEV
                        WHERE deviationId = '{request.args['editar']}';

                        INSERT INTO JDT_REQUEST_DEV_REFUSED_CONFIG_STATUS
                        SELECT *, GETDATE()
                        FROM JDT_REQUEST_DEV_CONFIG_STATUS
                        WHERE deviationId = '{request.args['editar']}';

                        DELETE FROM JDT_REQUEST_DEV_CONFIG_STATUS
                        WHERE deviationId = '{request.args['editar']}';

                        INSERT INTO JDT_REQUEST_DEV_REFUSED_PLAN
                        SELECT *, GETDATE()
                        FROM JDT_REQUEST_DEV_PLAN
                        WHERE deviationId = '{request.args['editar']}';

                        DELETE FROM JDT_REQUEST_DEV_PLAN
                        WHERE deviationId = '{request.args['editar']}';
                    """
                    for stmt in query.strip().split(';'):
                        if stmt.strip():
                            cnnx.execute(text(stmt))
                    trans.commit()
                except Exception as e:
                    trans.rollback()
                    send_system_teams_alert('Desvios de Processo - Recriar desvio Negado', e, current_user.name)
                    print(e)
                    return redirect('/denied')
                else:
                    insert_data()
                    return redirect('/desvios')

        query = "SELECT NOME_MAQUINA FROM CONFIG_TABLET"
        cts = return_options(query, 'NOME_MAQUINA', 'ftm')

        query = "SELECT DISTINCT(ID_MATER) AS ID_MATER FROM WORK_CELL_OP WHERE ID_WORK_UNIT = '' ORDER BY ID_MATER"
        products = return_options(query, 'ID_MATER', 'ftm')

        query = "SELECT DISTINCT(companyEmail) AS MAIL FROM JDT_USER_DETAILS WHERE generic = 0 AND active = 1 AND companyName LIKE '%JOST%'"
        mails = return_options(query, 'MAIL', 'jdt')

        edit = ''
        cmd = 1
        revisao = 0
        if 'editar' in request.args:

            query = f"""SELECT * 
                        FROM 
                            JDT_REQUEST_DEV 
                        WHERE 
                            deviationId = '{request.args['editar']}' and
                            status = 2
            """
            
            query_plan = f"""SELECT * 
                                FROM 
                                JDT_REQUEST_DEV_PLAN 
                                WHERE 
                                deviationId = '{request.args['editar']}' and 
                                (SELECT 
                                    status 
                                FROM 
                                    JDT_REQUEST_DEV 
                                where 
                                    deviationId = '{request.args['editar']}') = 2"""

            df = pd.read_sql(query, cnnx).astype(str)
            df_plan = pd.read_sql(query_plan, cnnx).astype(str).to_json()

            revisao = int(df['deviationId'][0].split('-')[2]) + 1
            if df['status'][0] == '2':
                edit = '&editar=' + str(df['deviationId'][0])
                cmd = 2
                revisao -= 1

            if df['userId'][0] != current_user.id and not current_user.admin:
                return redirect('/denied')

            df = df.to_json()

        else:
            df = False
            df_plan = False

        return render_template(
            'request.processDeviation/dev_create.html'
            , equipes=_APPROVERS_TEAMS
            , solicitante=current_user.name
            , revisao=revisao
            , cts=cts
            , produtos=products
            , df=df
            , df_plan=df_plan
            , edit=edit
            , cmd=cmd
            , mails=mails
        )

# RENOVAR DESVIO OBS: COPIA TODOS OS DADOS PARA UM NOVO ID
# DADOS QUE DEVEM SER ATUALIZADOS: deviationId, initDate, finalDate, revision, openDate, status, notifyCostumer, notifySupplier
@request_processDeviation_bp.route('/desvios/renovar', methods=['GET', 'POST'])
def dev_renew():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT *, DATEDIFF(day, GETDATE(), finalDate) AS renew 
                    FROM JDT_REQUEST_DEV 
                    WHERE deviationId LIKE '{request.args['id']}%'"""
        data = pd.read_sql(query, cnnx)

        if len(data) == 0:
            
            return redirect('/denied')
        
        onapproving = None
        dev_to_new_revision = data.loc[[data['deviationId'].idxmax()]].reset_index()
        if dev_to_new_revision['status'][0] == 2:
            onapproving = dev_to_new_revision.copy()
            data = data.drop(data['deviationId'].idxmax())
            dev_to_new_revision = data.loc[[data['deviationId'].idxmax()]].reset_index()
        
        if dev_to_new_revision['status'][0] not in (5, 6) or dev_to_new_revision['renew'][0] >= 5:
            
            return redirect ('/denied')
        

        if str(current_user.id) != str(dev_to_new_revision['userId'][0]) and (not current_user.admin and not p_admin.can()):
            
            return redirect ('/denied')
        
        if request.method == 'POST':

            new_id = dev_to_new_revision['deviationId'][0][:-1] + str(int(dev_to_new_revision['deviationId'][0][-1]) + 1)

            if onapproving is not None:

                query = f"""BEGIN TRANSACTION;
                            INSERT INTO JDT_REQUEST_DEV_REFUSED
                            SELECT *, GETDATE()
                            FROM JDT_REQUEST_DEV
                            WHERE deviationId = '{onapproving['deviationId'][0]}';
                            
                            DELETE FROM JDT_REQUEST_DEV
                            WHERE deviationId = '{onapproving['deviationId'][0]}';
                            
                            INSERT INTO JDT_REQUEST_DEV_REFUSED_CONFIG_STATUS
                            SELECT *, GETDATE()
                            FROM JDT_REQUEST_DEV_CONFIG_STATUS
                            WHERE deviationId = '{onapproving['deviationId'][0]}';
                            
                            DELETE FROM JDT_REQUEST_DEV_CONFIG_STATUS
                            WHERE deviationId = '{onapproving['deviationId'][0]}';
                            
                            INSERT INTO JDT_REQUEST_DEV_REFUSED_PLAN
                            SELECT *, GETDATE()
                            FROM JDT_REQUEST_DEV_PLAN
                            WHERE deviationId = '{onapproving['deviationId'][0]}';
                            
                            DELETE FROM JDT_REQUEST_DEV_PLAN
                            WHERE deviationId = '{onapproving['deviationId'][0]}';"""
                cnnx.execute(text(query))
                cnnx.commit()

            else: 
                os.mkdir('app/static/uploads/deviation/request/' + new_id + '/')
                os.mkdir('app/static/uploads/deviation/request/' + new_id + '/attachment/')

            query = f"""INSERT INTO JDT_REQUEST_DEV VALUES (
                        '{new_id}',
                        '{dev_to_new_revision['userId'][0]}',
                        '{dev_to_new_revision['sectorId'][0]}',
                        '{dev_to_new_revision['unit'][0]}',
                        '{dev_to_new_revision['workCenter'][0]}',
                        '{dev_to_new_revision['prodCode'][0]}',
                        '{dev_to_new_revision['families'][0]}',
                        '{dev_to_new_revision['prodDescription'][0]}',
                        '{dev_to_new_revision['workInstruction'][0]}',
                        '{dev_to_new_revision['documents'][0]}',
                        '{request.form['initDate']}',
                        '{request.form['finalDate']}',
                        '{int(dev_to_new_revision['revision'][0]) + 1}',
                        '{dev_to_new_revision['traceability'][0]}',
                        '{dev_to_new_revision['motive'][0]}',
                        '{dev_to_new_revision['imagesMotive'][0]}',
                        '{dev_to_new_revision['riskAnalisys'][0]}',
                        '{dev_to_new_revision['procedures'][0]}',
                        '{dev_to_new_revision['imagesProcedures'][0]}',
                        GETDATE(), 0, NULL, NULL, '',
                        '{dev_to_new_revision['special1'][0]}',
                        '{dev_to_new_revision['special2'][0]}',
                        '{dev_to_new_revision['ssma'][0]}');"""
            
            cnnx.execute(text(query))
            cnnx.commit()


            def new_plan(row):
                query = f"INSERT INTO JDT_REQUEST_DEV_PLAN VALUES ('{new_id}', '{row['text']}', '{row['userId']}', '{row['deadline']}')"
                cnnx.execute(text(query))
            


            query = f"""SELECT * 
                        FROM JDT_REQUEST_DEV_PLAN 
                        WHERE deviationId = '{request.args['id']}-0'"""
            plan_to_new_revision = pd.read_sql(query, cnnx)

            plan_to_new_revision['deviationId'] = new_id
            plan_to_new_revision.apply(new_plan, axis=1)
            cnnx.commit()

            aux = ""
            loop = _APPROVERS_TEAMS
            if str(dev_to_new_revision['unit'][0]) == "0":
                loop = _APPROVERS_TEAMS[:-1]
                aux = "WHERE sector <> 'Campinas'"

            for sector in loop:
                query = f"""INSERT INTO JDT_REQUEST_DEV_CONFIG_STATUS VALUES (
                                    '{new_id}', '{sector[0]}', NULL, 0, NULL)"""
                cnnx.execute(text(query))
            cnnx.commit()

                        
            query = f"SELECT companyEmail FROM JDT_VIEW_REQUEST_DEV_APPROVERS {aux}"
            approvers_mail = pd.read_sql(query, cnnx)['companyEmail'].values.tolist()
            for a_mail in approvers_mail:
                
                msg = Message(f'Desvio de processo - Nº {new_id}',
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=[a_mail])

                msg.html = render_template('request.processDeviation/dev_email_avaliate_revision.html', 
                                            final_id=new_id[:-2], solicitante=current_user.name)
                # mail.send(msg)

            

            return redirect('/desvios/detalhes?id=' + "-".join(new_id.split('-')[:2]))
        
        else:

            data = pd.to_datetime(dev_to_new_revision['finalDate']).max()

            nova_data = (data + timedelta(days=1)).strftime('%Y-%m-%d')

            
            return render_template('request.processDeviation/dev_renew.html', id=request.args['id'], lastDate=nova_data)


@request_processDeviation_bp.route('/desvios/atualizar', methods=['GET', 'POST'])
def dev_status_update():
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT status, companyEmail FROM JDT_VIEW_REQUEST_DEV_DETAILS WHERE deviationId = '{request.args['id']}'"""
        dev_status = pd.read_sql(query, cnnx)['status'][0]
        if dev_status == 0 or dev_status == 2:

            requesterEmail = pd.read_sql(query, cnnx)['companyEmail'][0]

            query = f"""SELECT sectorId FROM JDT_REQUEST_DEV_APPROVERS WHERE userId = '{current_user.id}'"""
            userSector = pd.read_sql(query, cnnx)['sectorId'][0]

            if "aprovar" in request.args:
                
                if request.method == "GET":

                    return render_template('request.processDeviation/dev_sector_approve_share.html', id=request.args['id'], type=request.args['tipo'])
                    
                else:

                    if 'tipo' in request.args:
                        if request.args['tipo'] == 'fornecedor':
                            query = f"""UPDATE JDT_REQUEST_DEV SET notifySupplier = '{request.args['aprovar']}' WHERE deviationId = '{request.args['id']}'"""
                            cnnx.execute(text(query))
                        else:
                            query = f"""UPDATE JDT_REQUEST_DEV SET notifyCostumer = '{request.args['aprovar']}' WHERE deviationId = '{request.args['id']}'"""
                            cnnx.execute(text(query))


                    query = f"""UPDATE JDT_REQUEST_DEV_CONFIG_STATUS SET 
                                    status = 1, approverId = '{current_user.id}' 
                                WHERE deviationId = '{request.args['id']}' AND sectorId = '{userSector}'"""

                    cnnx.execute(text(query))
                    cnnx.commit()

                    query = f"""SELECT MIN(status) AS status FROM JDT_REQUEST_DEV_CONFIG_STATUS WHERE deviationId = '{request.args['id']}'"""
                    dev_status = pd.read_sql(query, cnnx)['status'][0]
                    if dev_status == 1:

                        query = f"""SELECT approverEmail FROM JDT_VIEW_REQUEST_DEV_MANAGE WHERE deviationId = '{request.args['id']}'"""
                        approvers = pd.read_sql(query, cnnx)['approverEmail'].values.tolist()

                        query = f"""UPDATE JDT_REQUEST_DEV SET
                                        status = 1
                                    WHERE deviationId = '{request.args['id']}'"""
                        cnnx.execute(text(query))

                        query = f"""UPDATE JDT_REQUEST_DEV SET
                                        status = 5,
                                        initDate = CONVERT(DATE, GETDATE()) 
                                    WHERE deviationId = '{request.args['id']}' AND initDate <= CAST(GETDATE() AS DATE)"""
                        cnnx.execute(text(query))

                        cnnx.commit()

                        msg = Message(f"Pedido de desvio - ID {request.args['id']}",
                                        sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                        recipients=['jost_lideres@empresasrandon.com.br', 'Jost_Qualidade@randon.com.br', requesterEmail] + approvers)

                        msg.html = render_template('request.processDeviation/dev_email_approved.html', id=request.args['id'][:-2])

                        mail.send(msg)

                    query = f"""SELECT companyEmail FROM JDT_VIEW_REQUEST_DEV_APPROVERS WHERE sector = '{_APPROVERS_TEAMS[userSector][1]}'"""
                    area_email = pd.read_sql(query, cnnx)['companyEmail'].values.tolist()

                    msg = Message(f"Pedido de desvio - ID {request.args['id']}",
                                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                    recipients=area_email)

                    msg.html = render_template('request.processDeviation/dev_email_sector.html', id=request.args['id'][:-2],
                                                approverName=current_user.name)

                    mail.send(msg)

                    

                return render_template('request.processDeviation/dev_sector_approved.html', id=request.args['id'],
                                            sector=_APPROVERS_TEAMS[userSector][1])

            else:
                if request.method == "GET":

                    return render_template('request.processDeviation/dev_sector_refuse.html', id=request.args['id'])

                else:

                    query = f"""UPDATE JDT_REQUEST_DEV_CONFIG_STATUS SET 
                                    status = 2, approverId = '{current_user.id}', textDenied = '{request.form['justificativa']}'
                                WHERE deviationId = '{request.args['id']}' AND sectorId = '{userSector}'"""
                    cnnx.execute(text(query))

                    query = f"""UPDATE JDT_REQUEST_DEV SET status = 2 WHERE deviationId = '{request.args['id']}'"""
                    cnnx.execute(text(query))

                    cnnx.commit()
                    

                    msg = Message(f"Pedido de desvio - ID {request.args['id']}",
                                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                    recipients=[requesterEmail])

                    msg.html = render_template('request.processDeviation/dev_email_refused.html', just=request.form['justificativa'],
                                                id=request.args['id'][:-2], approverName=current_user.name)

                    mail.send(msg)

                    return render_template('request.processDeviation/dev_sector_refused.html', id=request.args['id'],
                                            sector=_APPROVERS_TEAMS[userSector][1], just=request.form['justificativa'])
        else:

            return redirect('/denied')  # criar pagina de que o desvio ja foi aprovado


# ROTAS PARA CONSULTAR DESVIOS

@request_processDeviation_bp.route('/desvios/consultar', methods=['GET'])
def dev_view_get():

    end_date = datetime.now().date()
    start_date = f"{end_date.year}-01-01"

    return render_template('request.processDeviation/dev_view.html', end_date=end_date, start_date=start_date)

@request_processDeviation_bp.route('/desvios/consultar', methods=['POST'])
def dev_view_post():

    payload = request.get_json()

    if 'start_date' not in payload and 'end_date' not in payload:
        abort(400, description="Missing 'start_date' or 'end_date'")

    query = """
        SELECT 
            LEFT(T1.deviationId, 9) AS deviationId,
            T1.revision,
            T1.name AS requesterName,
            T1.motive,
            T1.workCenter,
            T1.families,
            T1.finalDate,
            T1.status
        FROM JDT_VIEW_REQUEST_DEV_DETAILS AS T1
        WHERE T1.deviationId = (
            SELECT MAX(T2.deviationId)
            FROM JDT_VIEW_REQUEST_DEV_DETAILS AS T2
            WHERE LEFT(T1.deviationId, 10) = LEFT(T2.deviationId, 10)
        )
        AND T1.openDate BETWEEN :start_date AND :end_date
        ORDER BY T1.deviationId DESC
    """

    params = {
        "start_date": payload['start_date'] + ' 00:00',
        "end_date": payload['end_date'] + ' 23:59'
    }

    data = engine_run_query(query, 'jdt', params=params)

    if request.args.get('excel'):
        data['status'] = data['status'].map(_STATUS_DICT)

        data = data.rename(columns={'deviationId': 'Desvio', 'revision': 'Revisão', 'requesterName' : 'Solicitante', 'motive': 'Motivo', 'workCenter': 'Centro de Trabalho', 'families': 'Família', 'finalDate': 'Data Fim'})
        
        path = fr'{os.getcwd()}\app\static\uploads\default'
        excel_filename = f'{path}\desvios.xlsx'
        if os.path.exists(excel_filename):
            os.remove(excel_filename)

        with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name='GERAL', index=False)

        return send_file(
            excel_filename,
            as_attachment=True,
            download_name='desvios.xlsx'
        )


    return data.to_dict(orient='records')

@request_processDeviation_bp.route('/desvios/aprovacoes', methods=['GET'])
def dev_approvals_get():

    end_date = datetime.now().date()
    start_date = f"{end_date.year}-01-01"

    return render_template('request.processDeviation/dev_approvals.html', end_date=end_date, start_date=start_date)


@request_processDeviation_bp.route('/desvios/aprovacoes', methods=['POST'])
def dev_approvals_post():

    if p_admin.can():
        aux = ""
    else:  
        query = f"""SELECT sectorId FROM JDT_REQUEST_DEV_APPROVERS WHERE userId = '{current_user.id}'"""

        sectorId = engine_run_query(query, 'jdt')

        if len(sectorId) == 0:
            abort(404)
    
        aux = f"AND sectorId = '{sectorId['sectorId'][0]}'"


    payload = request.get_json()
    if 'start_date' not in payload and 'end_date' not in payload:
        abort(400, description="Missing 'start_date' or 'end_date'")

    query = f"""SELECT 
                    LEFT(T1.deviationId, 9) AS deviationId
                    , T1.revision
                    , T1.name AS requesterName
                    , T1.motive
                    , T1.workCenter
                    , T1.families
                    , T1.finalDate
                    , T1.status
                    , T3.sector
                    , T2.status AS approvalStatus
                    , T4.name AS approverName
                FROM JDT_VIEW_REQUEST_DEV_DETAILS AS T1 
                    JOIN JDT_REQUEST_DEV_CONFIG_STATUS AS T2 ON T1.deviationId = T2.deviationId
                    JOIN JDT_REQUEST_DEV_SECTORS AS T3 ON T2.sectorId = T3.id
                    LEFT JOIN JDT_USER_DETAILS AS T4 ON T2.approverId = T4.id
                
                WHERE 
                    T1.openDate BETWEEN :start_date AND :end_date
                    {aux}

                ORDER BY T1.deviationId DESC"""
    params = {
        "start_date": payload['start_date'] + ' 00:00',
        "end_date": payload['end_date'] + ' 23:59'
    }

    data = engine_run_query(query, 'jdt', params=params)

    if request.args.get('excel'):
        data['status'] = data['status'].map(_STATUS_DICT)
        data['approvalStatus'] = data['approvalStatus'].map({0: 'Aguardando aprovação', 1: 'Aprovado', 2: 'Reprovado'})

        data = data.rename(columns={'deviationId': 'Desvio', 'revision': 'Revisão', 'requesterName' : 'Solicitante', 'motive': 'Motivo', 'workCenter': 'Centro de Trabalho', 'families': 'Família', 'finalDate': 'Data Fim', 'sector': 'Setor', 'approvalStatus': 'Status de Aprovação', 'approverName': 'Aprovador'})
        
        path = fr'{os.getcwd()}\app\static\uploads\default'
        excel_filename = f'{path}\desvios.xlsx'
        if os.path.exists(excel_filename):
            os.remove(excel_filename)

        with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name='GERAL', index=False)

        return send_file(
            excel_filename,
            as_attachment=True,
            download_name='desvios.xlsx'
        )


    return data.to_dict(orient='records')


@request_processDeviation_bp.route('/desvios/detalhes', methods=['GET', 'POST'])
def dev_detail():

    if 'id' in request.args:
        requestId = request.args['id']
    elif 'anexo' in request.args:
        requestId = request.args['anexo']
    elif 'finalizar' in request.args:
        requestId = request.args['finalizar']
    else:
        requestId = request.args['cancelar']
    
    query = f"""SELECT userId FROM JDT_REQUEST_DEV WHERE deviationId like '{requestId}%'"""
    if len(engine_run_query(query, 'jdt')['userId']) == 0:
        return redirect ('/denied')
    

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        resp = str(pd.read_sql(query, cnnx)['userId'][0]) == current_user.id or current_user.admin or p_admin.can()

        admin = '0'
        if current_user.admin or p_admin.can():
            admin = '1'

        if request.method == 'GET':

            if 'cancelar' in request.args:
                if admin == '1':

                    query = f"""SELECT status FROM JDT_REQUEST_DEV WHERE deviationId = '{request.args['cancelar']}'"""
                    data = pd.read_sql(query, cnnx)['status'][0]
                    
                    if data == 0:
                        return render_template('request.processDeviation/dev_sector_cancel.html', id=request.args['cancelar'])
                    return redirect ('/denied')
                
                else:
                    
                    return redirect ('/denied')
            
            elif 'anexo' in request.args:
                if admin == '1':

                    query = f"""SELECT attachment FROM JDT_REQUEST_DEV WHERE deviationId = '{request.args['id']}'"""
                    oldImages = pd.read_sql(query, cnnx)['attachment'][0]

                    if request.args["anexo"] in oldImages:
                        newImages = oldImages.replace(str(request.args["anexo"] + '||'), "")

                        file = rf'app\static\uploads\deviation\request\{request.args["id"]}\attachment\{request.args["anexo"]}'
                        if os.path.exists(rf'{APP_PATH}\{file}'):
                            os.remove(rf'{APP_PATH}\{file}')

                        query = f"""UPDATE JDT_REQUEST_DEV SET attachment = '{newImages}'
                                    WHERE deviationId = '{request.args['id']}'"""
                        
                        cnnx.execute(text(query))
                        cnnx.commit()

                
                return redirect('/desvios/detalhes?id=' + request.args['id'][:-2])
            
            query = f"""SELECT 
                            deviationId AS 'DETALHES REVISÃO', 
                            revision AS 'REVISÃO', 
                            motive AS 'MOTIVO',
                            workCenter AS 'CENTRO DE TRABALHO',
                            families AS 'FAMÍLIA',
                            initDate AS 'DATA DE INICIO', 
                            finalDate AS 'DATA FIM', 
                            status AS 'STATUS',
                            sector, name, openDate, DATEDIFF(day, GETDATE(), CONVERT(DATE, finalDate, 103)) AS diff_days, attachment,
                            (SELECT MIN(T2.status) FROM JDT_REQUEST_DEV_CONFIG_STATUS AS T2 WHERE T2.deviationId = T1.deviationId) AS min_status 
                        FROM JDT_VIEW_REQUEST_DEV_DETAILS AS T1 WHERE deviationId LIKE '{request.args['id']}%' ORDER BY deviationId DESC"""

            user_data = pd.read_sql(query, cnnx)

            sector = user_data['sector'][0]
            userName = user_data['name'][0]
            firstDate = pd.to_datetime(user_data['openDate']).min().strftime('%d/%m/%Y')
            min_status = user_data['min_status'][0]

            user_data = user_data[['DETALHES REVISÃO', 'REVISÃO', 'MOTIVO', 'CENTRO DE TRABALHO', 'FAMÍLIA', 'DATA DE INICIO', 'DATA FIM', 'STATUS', 'diff_days', 'attachment']]
            user_data['CENTRO DE TRABALHO'] = user_data['CENTRO DE TRABALHO'].apply(_LIST_UPDATE)
            user_data['FAMÍLIA'] = user_data['FAMÍLIA'].apply(_LIST_UPDATE)

            table = config_table(user_data)

            return render_template(
                'request.processDeviation/dev_detail.html'
                , table=table
                , userName=userName
                , min_status=min_status
                , idReq=request.args['id']
                , admin=admin
                , sector=sector
                , firstDate=firstDate
                , resp=str(int(resp))
            )
        
        else:

            if resp == True:

                if 'anexo' in request.args:

                    query = f"""SELECT attachment FROM JDT_REQUEST_DEV WHERE deviationId = '{request.args['anexo']}'"""
                    oldImages = pd.read_sql(query, cnnx)['attachment'][0]

                    for file in request.files.getlist('anexos'):
                        if file.filename != '': 
                            if oldImages.upper().count(file.filename.upper()) == 0:
                                file.save(os.path.join(rf'{os.getcwd()}\app\static\uploads\deviation\request\{request.args["anexo"]}\attachment',
                                                    file.filename))
                                oldImages += f'{file.filename}||'
                            else:
                                acum = oldImages.upper().count(file.filename.rsplit(".", 1)[0].upper())
                                thisName = file.filename.rsplit(".", 1)[0] + "_(" + str(acum) + ")." + \
                                        file.filename.split('.')[-1]
                                file.save(os.path.join(rf'{os.getcwd()}\app\static\uploads\deviation\request\{request.args["anexo"]}\attachment', thisName))
                                oldImages += f'{thisName}||'

                    query = f"""UPDATE JDT_REQUEST_DEV SET attachment = '{oldImages}'
                                WHERE deviationId = '{request.args['anexo']}'"""
                    cnnx.execute(text(query))

                    cnnx.commit()

                    return redirect('/desvios/detalhes?id=' + request.args['anexo'][:-2])

                elif 'cancelar' in request.args and admin == '1':

                    query = f"""SELECT userId, status FROM JDT_REQUEST_DEV WHERE deviationId = '{request.args['cancelar']}'"""
                    data = pd.read_sql(query, cnnx)
                    if data['status'][0] == 0 and (admin == 'True' or data['userId'][0] == current_user.id):

                        query = f"""UPDATE JDT_REQUEST_DEV SET 
                                        status = 3
                                    WHERE deviationId = '{request.args['cancelar']}'"""
                        cnnx.execute(text(query))

                        query = f"""UPDATE JDT_REQUEST_DEV_CONFIG_STATUS SET
                                                approverId = '{current_user.id}', status = 3, textDenied = '{request.form['justificativa']}'
                                            WHERE deviationId = '{request.args['cancelar']}'"""
                        cnnx.execute(text(query))

                        cnnx.commit()

                        return redirect ('/desvios/detalhes?id=' + request.args['cancelar'])
                    
                    
                    return 'ACCESS DENIED'
                
                elif admin == '1':

                    query = f"""SELECT status, companyEmail FROM JDT_VIEW_REQUEST_DEV_DETAILS WHERE deviationId = '{request.args['finalizar']}'"""
                    data = pd.read_sql(query, cnnx)
                    if data['status'][0] == 5 or data['status'][0] == 6:
                        
                        query = f"""UPDATE JDT_REQUEST_DEV SET 
                                        status = 4
                                    WHERE deviationId = '{request.args['finalizar']}'"""
                        cnnx.execute(text(query))

                        cnnx.commit()

                        query = f"""SELECT approverEmail FROM JDT_VIEW_REQUEST_DEV_MANAGE WHERE deviationId = '{request.args['finalizar']}'"""
                        approvers = pd.read_sql(query, cnnx)['approverEmail'].values.tolist()

                        

                        msg = Message(f"Pedido de desvio - ID {request.args['finalizar']}",
                                        sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                        recipients=['jost_lideres@empresasrandon.com.br', 'Jost_Qualidade@randon.com.br', data['companyEmail'][0]] + approvers)

                        msg.html = render_template('request.processDeviation/dev_email_finished.html', id=request.args['finalizar'][:-2])

                        mail.send(msg)

                        return redirect ('/desvios/detalhes?id=' + request.args['finalizar'])


                    
                    return 'ACCESS DENIED'
                    
        return 'ACCESS DENIED'

@request_processDeviation_bp.route('/desvios/detalhes/fisico', methods=['GET', 'POST'])
def dev_detail_physical():
    
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT * FROM JDT_VIEW_REQUEST_DEV_DETAILS WHERE deviationId = '{request.args['id']}'"""
        df = pd.read_sql(query, cnnx)

        query = f"""SELECT T1.text, T2.name, FORMAT(T1.deadline, 'dd/MM/yyyy') AS deadline
                    FROM JDT_REQUEST_DEV_PLAN AS T1
                    JOIN JDT_USER_DETAILS AS T2 ON T1.userId = T2.companyEmail
                    WHERE deviationId = '{request.args['id']}'"""
        df_plan = pd.read_sql(query, cnnx).astype(str)

        query = f"""SELECT * FROM JDT_VIEW_REQUEST_DEV_MANAGE WHERE deviationId = '{request.args['id']}' ORDER BY approverSector"""
        aprovadores = pd.read_sql(query, cnnx)

    df['workCenter'] = df['workCenter'].apply(_LIST_UPDATE)
    df['families'] = df['families'].apply(_LIST_UPDATE)
    df['prodCode'] = df['prodCode'].apply(_LIST_UPDATE)
    df['workInstruction'] = df['workInstruction'].apply(_LIST_UPDATE)

    return render_template(
        'request.processDeviation/dev_detail_physical.html'
        , dataframe=df.to_json()
        , df_plan=df_plan.to_json()
        , idReq=request.args['id']
        , df_result=aprovadores.to_json()
    )

@request_processDeviation_bp.route('/desvios/detalhes/anexo/download', methods=['GET'])
def dev_detail_attachment_download():
    
    file = rf'app\static\uploads\deviation\request\{request.args["id"]}\attachment\{request.args["anexo"]}'
    if os.path.exists(rf'{APP_PATH}\{file}'):
        return send_file(rf'{APP_PATH}\{file}', as_attachment=True, download_name=request.args["anexo"])
    else:
        return 'FILE DOES NOT EXISTS'
    