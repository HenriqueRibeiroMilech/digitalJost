"""
    CONDIÇÕES DE STATUS PARA MELHORIAS:
    0 = NÃO INICIADO
    1 = INICIADO
    2 = FINALIZADO
    3 = RECUSADO
    4 = PAUSADO

    CONDIÇÕES DE STATUS PARA PROJETOS:
    0 = AGUARDANDO APROVAÇÃO COORDENADOR
    1 = AGUARDANDO APROVAÇÃO ÁREA
    2 = APROVADO
    3 = NEGADO APROVAÇÃO COORDENADOR
    4 = NEGADO APROVAÇÃO ÁREA
"""

import os
from datetime import datetime
import numpy as np
import pandas as pd

from sqlalchemy import text

from flask import Blueprint, abort, render_template, request, redirect, url_for, send_file
from flask_login import current_user
from flask_mail import Message

from app.utils.data_utils import format_date
from app.utils.db_utils import engine_run_query, get_engine
from app.utils.permissions import get_permission, user_has_role
from app.config import mail


_AREA_REQUIRED_ROUTES = [
    'request_improvements.improvements_small_new_get',
    'request_improvements.improvements_small_new_post',
    'request_improvements.improvements_big_new_get',
    'request_improvements.improvements_big_new_post',
    'request_improvements.improvements_view_get',
    'request_improvements.improvements_manage_get',
    'request_improvements.improvements_manage_form_get',
    'request_improvements.improvements_manage_form_post'
]

_AREAS = {'Transformação Digital': [1, 'JostTransformacaoDigital@empresasrandon.onmicrosoft.com']}
_DEMAND_TYPES = {'melhoria', 'projeto', 'erro'}
_URGENCY_OPTIONS = ['Alta', 'Média', 'Baixa']

request_improvements_bp = Blueprint('request_improvements', __name__)


@request_improvements_bp.before_request
def route_auth():
    # Verifica se o usuário está autenticado
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))

    # Verifica permissão geral
    if not get_permission('GENERAL').can():
        return abort(403)

    # Verifica se a rota exige área e se ela é válida
    endpoint = request.endpoint
    if endpoint in _AREA_REQUIRED_ROUTES:
        area = request.args.get('area')
        if not area or area not in _AREAS:
            return abort(400, description='Área inválida ou não informada')


@request_improvements_bp.route('/solicitar', methods=['GET'])
def improvements_get():
    return render_template('request.improvements/improvements_home.html')


@request_improvements_bp.route('/solicitar/melhorias', methods=['GET'])
def improvements_small_new_get():
    return render_template(
        'request.improvements/improvements_small_new.html',
        options=_URGENCY_OPTIONS,
        area=request.args['area']
    )


@request_improvements_bp.route('/solicitar/melhorias', methods=['POST'])
def improvements_small_new_post():

    demand_type = request.form.get('demandType', '').strip()
    title = request.form.get('titulo', '').strip()
    info = request.form.get('objetivo', '').strip()
    urgency = request.form.get('options', '').strip()

    if demand_type not in _DEMAND_TYPES:
        return abort(400, description='Tipo de demanda inválido ou não informado')

    if not title or not info or urgency not in _URGENCY_OPTIONS:
        return abort(400, description='Campos obrigatórios da demanda inválidos ou não informados')

    if demand_type == 'erro':
        assumptions = None
        actual_problems = None
        benefits = None
    else:
        assumptions = request.form.get('premissas', '').strip()
        actual_problems = request.form.get('problemas', '').strip()
        benefits = request.form.get('beneficios', '').strip()

        if not assumptions or not actual_problems or not benefits:
            return abort(400, description='Os quatro campos descritivos são obrigatórios para melhorias e projetos')

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        req_query = 'SELECT MAX(requestId) + 1 AS id FROM JDT_REQUEST_IMPROVEMENTS_SMALL'
        req_id = pd.read_sql(req_query, cnnx)['id']
        req_id = req_id[0] if req_id[0] is not None else 1

        files = [file for file in request.files.getlist('docs') if file.filename]

        if files:

            if not os.path.exists('app/static/uploads/improvements/' + str(req_id) + '/'):
                os.mkdir('app/static/uploads/improvements/' + str(req_id) + '/')

            filesListString = ''
            for file in files:
                file.save(os.path.join(
                    rf'{os.getcwd()}\app\static\uploads\improvements\{str(req_id)}',
                    file.filename
                ))
                filesListString += f'{file.filename}||'

        else:
            filesListString = None

        query = text("""INSERT INTO JDT_REQUEST_IMPROVEMENTS_SMALL (
                            requestId, requesterId, areaId, title, info, urgency,
                            openDate, images, status, respId, startDate, deliveryDate,
                            finalDate, reprogs, deniedText, assumptions, actualProblems,
                            benefits, demandType
                        ) VALUES (
                            :request_id, :requester_id, :area_id, :title, :info, :urgency,
                            GETDATE(), :images, 0, NULL, NULL, NULL,
                            NULL, 0, NULL, :assumptions, :actual_problems,
                            :benefits, :demand_type
                        )""")

        cnnx.execute(query, {
            'request_id': int(req_id),
            'requester_id': current_user.id,
            'area_id': _AREAS[request.args['area']][0],
            'title': title,
            'info': info,
            'urgency': urgency,
            'images': filesListString,
            'assumptions': assumptions,
            'actual_problems': actual_problems,
            'benefits': benefits,
            'demand_type': demand_type
        })
        cnnx.commit()

    # ✅ MODIFICAÇÃO: NÃO enviar mais para o e-mail da área (onmicrosoft)
    # Antes: recipients=[_AREAS[request.args['area']][1]]
    # Agora: não envia (recipients vazio) -> simplesmente não chama mail.send
    msg = Message(
        'Uma demanda foi solicitada!',
        sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
        recipients=[]  # <- sem destinatário, não envia
    )

    msg.html = render_template(
        'request.improvements/improvements_email_new_small.html',
        id_sol=current_user.id,
        titulo=title,
        desc=info,
        demand_type=demand_type,
        area=_AREAS[request.args['area']][0]
    )

    # ✅ Como recipients está vazio, não faz sentido tentar enviar
    # Se você quiser enviar para outro e-mail, basta colocar aqui o destinatário.
    # mail.send(msg)  # removido

    return render_template('request.improvements/improvements_sent.html', area=request.args['area'])


@request_improvements_bp.route('/solicitar/projetos', methods=['GET'])
def improvements_big_new_get():

    query = """SELECT name, id FROM JDT_VIEW_COORD"""
    coord = engine_run_query(query, 'jdt').values.tolist()

    return render_template(
        'request.improvements/improvements_big_new.html',
        coord=coord,
        area=request.args['area']
    )


@request_improvements_bp.route('/solicitar/projetos', methods=['POST'])
def improvements_big_new_post():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        req_query = 'SELECT MAX(requestId) + 1 AS id FROM JDT_REQUEST_IMPROVEMENTS_BIG'
        req_id = pd.read_sql(req_query, cnnx)['id']
        req_id = req_id[0] if req_id[0] is not None else 1

        query = f"""INSERT INTO JDT_REQUEST_IMPROVEMENTS_BIG VALUES (
                        '{req_id}', '{current_user.id}', '{request.form['titulo']}',
                        '{request.form['objetivo']}', '{request.form['premissas']}', '{request.form['problemas']}', 
                        '{request.form['melhorias']}', '{request.form['verba']}', 
                        '{request.form['coord']}', NULL, GETDATE(), '{request.form['data']}', NULL,
                        '{_AREAS[request.args['area']][0]}', 0, NULL)"""

        cnnx.execute(text(query))
        cnnx.commit()

        query = 'SELECT companyEmail FROM JDT_USER_DETAILS'
        bossEmail = pd.read_sql(query, cnnx)['companyEmail']

    msg = Message(
        'Um projeto foi solicitado!',
        sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
        recipients=[bossEmail],
        cc=[current_user.companyEmail]
    )

    msg.html = render_template(
        'request.improvements/improvements_email_new_big_boss.html',
        requesterName=current_user.name,
        title=request.form['titulo'],
        desc=request.form['objetivo'],
        area=request.args['area'],
        req_id=req_id
    )

    # Mantém envio do projeto como estava
    try:
        mail.send(msg)
    except Exception as e:
        print(f"[ERRO EMAIL] Falha ao enviar e-mail do projeto: {e}")

    return render_template('request.improvements/improvements_sent.html', area=request.args['area'])


@request_improvements_bp.route('/solicitar/view', methods=['GET'])
def improvements_view_get():

    if 'tipo' not in request.args:
        return abort(400)

    if request.args['tipo'] == 'melhorias':
        database = 'JDT_REQUEST_IMPROVEMENTS_SMALL'
        requestTypeDesc = 'Minhas demandas'
        bossCondition = ''

    else:
        # return render_template('general_maintenance.html')
        database = 'JDT_REQUEST_IMPROVEMENTS_BIG'
        requestTypeDesc = 'Meus projetos'
        bossCondition = f" OR requesterBossId = '{current_user.id}'"

    demand_type_column = "" if database == 'JDT_REQUEST_IMPROVEMENTS_BIG' else """
                    CASE COALESCE(NULLIF(demandType, ''), 'melhoria')
                        WHEN 'projeto' THEN 'Projeto'
                        WHEN 'erro' THEN 'Erro/Defeito em aplicação'
                        ELSE 'Melhoria'
                    END AS TIPO,"""

    query = f"""SELECT 
                    title AS TÍTULO, 
                    info AS 'OBJETIVO / DESCRIÇÃO DO PROBLEMA',
                    FORMAT(openDate, 'dd/MM/yyyy HH:mm:ss') AS 'DATA SOLICITAÇÃO', 
                    status AS STATUS,
                    {demand_type_column}
                    requestId  
            FROM {database} 
            WHERE 
                requesterId = '{current_user.id}' {bossCondition} 
                and areaId = {_AREAS[request.args['area']][0]}"""

    df = engine_run_query(query, 'jdt').astype(str)

    return render_template(
        'request.improvements/improvements_view.html'
        , df=df.to_json()
        , requestTypeDesc=requestTypeDesc
        , area=request.args['area']
        , requestType=request.args['tipo']
    )

@request_improvements_bp.route('/solicitar/manage', methods=['GET'])
def improvements_manage_get():

    if 'tipo' not in request.args:
        return abort(400)

    if not current_user.admin and not user_has_role(current_user.role, request.args['area']):
        return abort(404)

    if request.args['tipo'] == 'melhorias':

        query = f"""SELECT 
                        T2.name AS SOLICITANTE, 
                        T1.title AS TÍTULO, 
                        T1.info AS 'OBJETIVO / DESCRIÇÃO DO PROBLEMA',
                        CASE WHEN T1.urgency = 'Imediata' THEN 'Alta' ELSE T1.urgency END AS URGÊNCIA,
                        FORMAT(T1.deliveryDate, 'dd/MM/yyyy') AS PRAZO, 
                        FORMAT(T1.openDate, 'dd/MM/yyyy HH:mm:ss') AS 'DATA SOLICITAÇÃO', 
                        T1.status AS STATUS, 
                        CASE COALESCE(NULLIF(T1.demandType, ''), 'melhoria')
                            WHEN 'projeto' THEN 'Projeto'
                            WHEN 'erro' THEN 'Erro/Defeito em aplicação'
                            ELSE 'Melhoria'
                        END AS TIPO,
                        T1.requestId as idSolicitacao
                    FROM 
                        JDT_REQUEST_IMPROVEMENTS_SMALL AS T1 
                        JOIN JDT_USER_DETAILS AS T2 ON T1.requesterId = T2.id
                    
                    """
        aux = "ORDER BY STATUS, T1.openDate DESC"

    else:
        # return render_template('general_maintenance.html')
        query = f"""SELECT 
                        T2.name AS SOLICITANTE, 
                        T1.title AS TÍTULO, 
                        T1.objective AS OBJETIVO, 
                        T1.info AS PREMISSAS, 
                        FORMAT(T1.openDate, 'dd/MM/yyyy HH:mm:ss') AS 'DATA SOLICITAÇÃO', 
                        T1.status AS STATUS, 
                        T1.requestId as idSolicitacao 
                    FROM 
                        JDT_REQUEST_IMPROVEMENTS_BIG AS T1 
                        JOIN JDT_USER_DETAILS AS T2 ON T1.requesterId = T2.id """
        aux = "ORDER BY STATUS, 'DATA SOLICITAÇÃO'"

    df = engine_run_query(query + aux, 'jdt').astype(str)

    count = [0, 0, 0, 0, 0, len(df)]
    for n in range(len(df)):
        if df['STATUS'][n] == '0':
            count[0] += 1
        elif df['STATUS'][n] == '1':
            count[1] += 1
        elif df['STATUS'][n] == '2':
            count[2] += 1
        elif df['STATUS'][n] == '3':
            count[3] += 1
        elif df['STATUS'][n] == '4':
            count[4] += 1

    return render_template(
        'request.improvements/improvements_manage.html'
        , df=df.to_json()
        , area=request.args['area']
        , requestType=request.args['tipo']
        , counts=count
    )


@request_improvements_bp.route('/solicitar/manage/def', methods=['GET'])
def improvements_manage_form_get():

    if 'tipo' not in request.args:
        return abort(400)

    return render_template(
        'request.improvements/improvements_manage_form.html'
        , cmd=request.args['cmd']
        , reqId=request.args['id']
        , area=request.args['area']
        , requestType=request.args['tipo']
    )


@request_improvements_bp.route('/solicitar/manage/def', methods=['POST'])
def improvements_manage_form_post():

    if 'tipo' not in request.args:
        return abort(400)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        if request.args['tipo'] == 'melhorias':

            query = f"SELECT * FROM JDT_REQUEST_IMPROVEMENTS_SMALL WHERE requestId = '{request.args['id']}'"
            requestData = pd.read_sql(query, cnnx)

            query = f"SELECT initDate, finalDate FROM JDT_REQUEST_PAUSES WHERE requestId = '{request.args['id']}'"
            requestPauses = pd.read_sql(query, cnnx)[['initDate', 'finalDate']].values.tolist()


            query = f"""SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = '{requestData['requesterId'][0]}'"""
            requesterEmail = pd.read_sql(query, cnnx)['companyEmail'][0]

            respEmail = current_user.companyEmail
            requestTitle = requestData['title'][0]

            area = False
            for role in eval(current_user.role):
                if request.args['area'].lower() in role.lower():
                    area = True

            if current_user.id == requestData['respId'][0] or (not requestData['respId'][0] and area):

                # CONDIÇÃO PARA DAR INÍCIO A UMA DEMANDA, DEFINE UM RESPONSÁVEL
                if request.args['cmd'] == 'start' and requestData['status'][0] == 0:
                    query = f"""UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL SET 
                                    startDate = GETDATE(), 
                                    deliveryDate = '{request.form['prazoEntrega']} 00:00:00.000', 
                                    status = 1, 
                                    respId = '{current_user.id}' 
                                WHERE 
                                    requestId = {request.args['id']}"""
                    cnnx.execute(text(query))

                    date = format_date(datetime.now().date())
                    deliveryDate = format_date(request.form['prazoEntrega'])

                    msg = Message(f'Sua demanda - "{requestTitle}" - foi iniciada!',
                                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                    recipients=[requesterEmail], cc=[respEmail])

                    msg.html = render_template('request.improvements/improvements_email_new_small_start.html',
                                                respName=current_user.name, title=requestTitle,
                                                desc=requestData['info'][0], date=date,
                                                area=request.args['area'], requestType=request.args['tipo'],
                                                deliveryDate=deliveryDate)

                    mail.send(msg)
                    cnnx.commit()

                    return render_template('request.improvements/improvements_notify.html',
                                            area=request.args['area'], requestType=request.args['tipo'])

                # CONDIÇÃO PARA PAUSAR O ANDAMENTO DE UMA DEMANDA
                elif request.args['cmd'] == 'pause' and requestData['status'][0] == 1:
                    query = f"""UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL SET 
                                    deliveryDate = NULL, 
                                    status = 4 
                                WHERE 
                                    requestId = {request.args['id']}"""
                    cnnx.execute(text(query))
                    query = f"""INSERT JDT_REQUEST_PAUSES VALUES( 
                                    GETDATE(), '{request.form['dataUnpause']}', 
                                    NULL, '{request.args['id']}', '{request.form['justificativa']}')"""
                    cnnx.execute(text(query))

                    msg = Message(f'Sua solicitação - "{requestTitle}" - foi pausada!',
                                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                    recipients=[requesterEmail], cc=[respEmail])

                    date = format_date(requestData['startDate'][0])
                    pause = format_date(datetime.now().date())
                    unpause = format_date(request.form['dataUnpause'])

                    msg.html = render_template('request.improvements/improvements_email_new_small_pause.html',
                                                respName=current_user.name,
                                                just=request.form['justificativa'],
                                                title=requestData['title'][0],
                                                desc=requestData['info'][0],
                                                date=date,
                                                pause=pause,
                                                unpause=unpause,
                                                area=request.args['area'],
                                                requestType=request.args['tipo'])

                    mail.send(msg)
                    cnnx.commit()

                    return render_template('request.improvements/improvements_notify.html')

                # CONDIÇÃO PARA RETOMAR UMA DEMANDA
                elif request.args['cmd'] == 'unpause' and requestData['status'][0] == 4:
                    query = f"""UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL SET 
                                    deliveryDate = '{request.form['prazoEntrega']}', 
                                    status = 1, 
                                    reprogs = {requestData['reprogs'][0] + 1} 
                                WHERE 
                                    requestId = {request.args['id']}"""
                    cnnx.execute(text(query))

                    query = f"""SELECT  
                                    FORMAT(initDate, 'dd/MM/yyyy HH:mm:ss') AS initDate,
                                    FORMAT(GETDATE(), 'dd/MM/yyyy HH:mm:ss') AS finalDate 
                                FROM 
                                    JDT_REQUEST_PAUSES 
                                WHERE 
                                    requestId = {request.args['id']} AND finalDate IS NULL"""

                    initPause = pd.read_sql(query, cnnx)['initDate'][0]
                    finalDate = pd.read_sql(query, cnnx)['finalDate'][0]

                    query = f"""UPDATE JDT_REQUEST_PAUSES SET 
                                    finalDate = GETDATE() 
                                WHERE 
                                    requestId = {request.args['id']} AND finalDate IS NULL"""
                    cnnx.execute(text(query))

                    msg = Message(f'O desenvolvimento da sua demanda - "{requestTitle}" - foi retomado!',
                                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                    recipients=[requesterEmail], cc=[respEmail])

                    deliveryDate = format_date(request.form['prazoEntrega'])

                    msg.html = render_template('request.improvements/improvements_email_new_small_unpause.html',
                                                respName=current_user.name,
                                                deliveryDate=deliveryDate,
                                                title=requestData['title'][0],
                                                desc=requestData['info'][0],
                                                pause=initPause,
                                                unpause=finalDate,
                                                area=request.args['area'],
                                                requestType=request.args['tipo'])

                    mail.send(msg)
                    cnnx.commit()

                    return render_template('request.improvements/improvements_notify.html')

                # CONDIÇÃO PARA REPROGRAMAR O PRAZO DE UMA DEMANDA
                elif request.args['cmd'] == 'reprogram' and requestData['status'][0] == 1:
                    query = f"""UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL SET 
                                    deliveryDate = '{request.form['prazoEntrega']}', 
                                    status = 1,
                                    reprogs = {requestData['reprogs'][0] + 1} 
                                WHERE 
                                    requestId = {request.args['id']}"""
                    cnnx.execute(text(query))

                    msg = Message(f'O prazo da sua demanda - "{requestTitle}" - foi redefinido!',
                                    sender=(
                                    'Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                    recipients=[requesterEmail], cc=[respEmail])

                    inicialDeliveryDate = format_date(requestData['deliveryDate'][0])
                    deliveryDate = format_date(request.form['prazoEntrega'])
                    date = format_date(requestData['startDate'][0])

                    msg.html = render_template(
                        'request.improvements/improvements_email_new_small_reprogram.html',
                        respName=current_user.name,
                        inicialDeliveryDate=inicialDeliveryDate,
                        deliveryDate=deliveryDate,
                        date=date,
                        title=requestData['title'][0],
                        desc=requestData['info'][0],
                        area=request.args['area'],
                        requestType=request.args['tipo'])

                    mail.send(msg)
                    cnnx.commit()

                    return render_template('request.improvements/improvements_notify.html')

                # CONDIÇÃO PARA FINALIZAR UMA DEMANDA
                elif request.args['cmd'] == 'finish' and requestData['status'][0] == 1:
                    query = f"""UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL SET 
                                    finalDate = GETDATE(), 
                                    status = 2 
                                WHERE 
                                    requestId = {request.args['id']}"""
                    cnnx.execute(text(query))

                    msg = Message(f'A sua demanda - "{requestTitle}" - foi finalizada!',
                                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                    recipients=[requesterEmail], cc=[respEmail])

                    startDate = format_date(requestData['startDate'][0])
                    finalDate = format_date(datetime.now().replace(microsecond=0))
                    deliveryDate = format_date(requestData['deliveryDate'][0])

                    msg.html = render_template('request.improvements/improvements_email_new_small_finish.html',
                                                respName=current_user.name,
                                                startDate=startDate,
                                                finalDate=finalDate,
                                                deliveryDate=deliveryDate,
                                                pauses=len(requestPauses) + 1,
                                                reprogs=requestData['reprogs'][0],
                                                title=requestData['title'][0],
                                                desc=requestData['info'][0],
                                                area=request.args['area'],
                                                requestType=request.args['tipo'])

                    mail.send(msg)
                    cnnx.commit()

                    return render_template('request.improvements/improvements_notify.html')

                # CONDIÇÃO PARA RECUSAR UMA DEMANDA
                elif request.args['cmd'] == 'decline' and requestData['status'][0] == 0:
                    query = f"""UPDATE JDT_REQUEST_IMPROVEMENTS_SMALL SET 
                                    finalDate = GETDATE(), 
                                    status = 3,
                                    respId = '{current_user.id}',
                                    deniedText = '{request.form['justificativa']}' 
                                WHERE 
                                    requestId = {request.args['id']}"""

                    cnnx.execute(text(query))

                    msg = Message(f'A sua solicitação - "{requestTitle}" - foi recusada!',
                                    sender=(
                                    'Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                    recipients=[requesterEmail], cc=[respEmail])

                    msg.html = render_template('request.improvements/improvements_email_new_small_decline.html',
                                                respName=current_user.name,
                                                just=request.form['justificativa'],
                                                title=requestData['title'][0],
                                                desc=requestData['info'][0],
                                                area=request.args['area'],
                                                requestType=request.args['tipo'])

                    mail.send(msg)
                    cnnx.commit()

                    return render_template('request.improvements/improvements_notify.html')

                # CONDIÇÃO EM CASO DE UM VALOR DE ARGUMENTO CMD INVALIDO, NESTE CASO VOLTA PARA O /MANAGE
                else:
                    args_dict = {'area': request.args['area'], 'tipo': request.args['tipo']}
                    return redirect(url_for('main.improvements_manage_get', **args_dict))

            else:
                return render_template('general_denied.html')

        else:

            query = f"""SELECT T1.title, T1.info, T1.requesterBossId, T1.status, T1.areaId, T2.companyEmail, T2.name 
                        FROM JDT_REQUEST_IMPROVEMENTS_BIG AS T1
                            JOIN JDT_USER_DETAILS AS T2 ON T1.requesterId = T2.id 
                        WHERE 
                            requestId = '{request.args['id']}'"""
            requestData = pd.read_sql(query, cnnx)

            area = False
            for role in eval(current_user.role):
                if request.args['area'].lower() in role.lower():
                    area = True

            # CONDICAO DE APROVAÇÃO DO COORDENADOR
            if requestData['status'][0] == 0 and current_user.id == requestData['requesterBossId'][0] and request.args['cmd'] == 'approveBoss':
                query = f"""UPDATE JDT_REQUEST_IMPROVEMENTS_BIG SET 
                                status = 1 
                            WHERE 
                                requestId = '{request.args['id']}'"""

                cnnx.execute(text(query))
                cnnx.commit()

                msg = Message(f'Um projeto foi solicitado!',
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=[_AREAS[request.args['area']][0]],
                                cc=[requestData['companyEmail'][0]])

                msg.html = render_template('request.improvements/improvements_email_new_big_area.html',
                                            requesterName=requestData['name'][0],
                                            title=requestData['title'][0],
                                            desc=requestData['info'][0],
                                            area=request.args['area'],
                                            requestType=request.args['tipo'])

                mail.send(msg)

                return render_template('request.improvements/improvements_notify.html',
                                        area=request.args['area'], requestType=request.args['tipo'])

            # CONDICAO DE RECUSAR DO COORDENADOR
            elif requestData['status'][0] == 0 and current_user.id == requestData['requesterBossId'][0] and request.args['cmd'] == 'deniedBoss':
                query = f"""UPDATE JDT_REQUEST_IMPROVEMENTS_BIG SET 
                                deniedText = '{request.form['just']}',
                                status = 3,
                                finalDate = GETDATE()  
                            WHERE 
                                requestId = '{request.args['id']}'"""

                cnnx.execute(text(query))
                cnnx.commit()

                msg = Message(f'Projeto recusado pelo coordenador aprovador!',
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=[requestData['companyEmail'][0]])

                msg.html = render_template('request.improvements/improvements_email_new_big_boss_decline.html',
                                            title=requestData['title'][0],
                                            area=request.args['area'],
                                            just=request.form['justificativa'],
                                            requestType=request.args['tipo'])

                mail.send(msg)

                return render_template('request.improvements/improvements_notify.html',
                                        area=request.args['area'], requestType=request.args['tipo'])

            # CONDIÇÃO DE APROVAÇÃO DA AREA, OBS: O PROJETO É APROVADO
            elif requestData['status'][0] == 1 and area and request.args['cmd'] == 'approveArea':
                query = f"""UPDATE JDT_REQUEST_IMPROVEMENTS_BIG SET 
                                status = 2,
                                approverArea = '{current_user.id}',
                                finalDate = GETDATE()  
                            WHERE 
                                requestId = '{request.args['id']}'"""

                cnnx.execute(text(query))
                cnnx.commit()

                msg = Message(f'Projeto aprovado!',
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=[_AREAS[request.args['area']][0]],
                                cc=[requestData['companyEmail'][0]])

                msg.html = render_template('request.improvements/improvements_email_new_big_approve.html',
                                            respName=current_user.name,
                                            title=requestData['title'][0],
                                            desc=requestData['info'][0],
                                            area=request.args['area'],
                                            requestType=request.args['tipo'])

                mail.send(msg)

                return render_template('request.improvements/improvements_notify.html',
                                        area=request.args['area'], requestType=request.args['tipo'])

            # CONDIÇÃO DE RECUSAR DA ÁREA
            elif requestData['status'][0] == 1 and area and request.args['cmd'] == 'deniedArea':
                query = f"""UPDATE JDT_REQUEST_IMPROVEMENTS_BIG SET 
                                deniedText = '{request.form['just']}',
                                status = 4,
                                approverArea = '{current_user.id}',
                                finalDate = GETDATE()  
                            WHERE 
                                requestId = '{request.args['id']}'"""

                cnnx.execute(text(query))
                cnnx.commit()

                msg = Message(f'Projeto recusado pela área -' + request.args['area'],
                                sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                recipients=[_AREAS[request.args['area']][0]],
                                cc=[requestData['companyEmail'][0]])

                msg.html = render_template('request.improvements/improvements_email_new_big_area_decline.html',
                                            id_sol=requestData['name'][0],
                                            titulo=requestData['title'][0],
                                            desc=requestData['info'][0],
                                            area=request.args['area'],
                                            requestType=request.args['tipo'])

                mail.send(msg)

                return render_template('request.improvements/improvements_notify.html',
                                        area=request.args['area'], requestType=request.args['tipo'])

            # CONDIÇÃO EM CASO DE UM VALOR DE ARGUMENTO CMD INVALIDO, NESTE CASO VOLTA PARA O /MANAGE
            else:
                args_dict = {'area': request.args['area'], 'tipo': request.args['tipo']}
                return redirect(url_for('main.improvements_manage_get', **args_dict))



@request_improvements_bp.route('/solicitar/detail', methods=['GET'])
def improvements_detail_get():

    if 'tipo' not in request.args:
        return abort(400)

    if request.args['tipo'] == 'melhorias':

        query = f"""SELECT 
                        T1.requestId,
                        T2.name AS requesterName,
                        T1.title,
                        T1.info,
                        COALESCE(T1.assumptions, '') AS assumptions,
                        COALESCE(T1.actualProblems, '') AS actualProblems,
                        COALESCE(T1.benefits, '') AS benefits,
                        COALESCE(NULLIF(T1.demandType, ''), 'melhoria') AS demandType,
                        CASE WHEN T1.urgency = 'Imediata' THEN 'Alta' ELSE T1.urgency END AS urgency,
                        FORMAT(T1.openDate, 'dd/MM/yyyy HH:mm:ss') AS openDate, 
                        CASE WHEN T1.images IS NULL THEN '' ELSE T1.images END AS images,
                        T1.status,
                        T3.name AS respName,
                        FORMAT(T1.startDate, 'dd/MM/yyyy') AS startDate, 
                        FORMAT(T1.deliveryDate, 'dd/MM/yyyy') AS deliveryDate, 
                        FORMAT(T1.finalDate, 'dd/MM/yyyy HH:mm:ss') AS finalDate,
                        T1.reprogs,
                        T1.requesterId,
                        T1.deniedText   
                    FROM 
                        JDT_REQUEST_IMPROVEMENTS_SMALL AS T1 
                        JOIN JDT_USER_DETAILS AS T2 ON T1.requesterId = T2.id
                        LEFT JOIN JDT_USER_DETAILS AS T3 ON T1.respId = T3.id
                    WHERE 
                        T1.requestId = '{request.args['id']}'"""

        queryPauses = f"""SELECT
                            FORMAT(initDate, 'dd/MM/yyyy HH:mm:ss') AS initDate, 
                            FORMAT(expectDate, 'dd/MM/yyyy') AS expectDate, 
                            FORMAT(finalDate, 'dd/MM/yyyy HH:mm:ss') AS finalDate,
                            text 
                        FROM JDT_REQUEST_PAUSES WHERE requestId = '{request.args['id']}'"""

        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            df = pd.read_sql(query, cnnx)
            dfPause = pd.read_sql(queryPauses, cnnx).astype(str)[['initDate', 'expectDate', 'finalDate', 'text']]

        if not current_user.admin and request.args['area'] not in eval(current_user.role) and df['requesterId'][0] != current_user.id:
            return redirect('/denied')

        if len(dfPause) == 0:
            dfPause = [['A DEMANDA NÃO SOFREU PAUSAS']]
        else:
            dfPause = [['INICIO DA PAUSA', 'PREVISÃO DE TERMINO DA PAUSA', 'TERMINO REAL DA PAUSA', 'JUSTIFICATIVA']] \
                        + dfPause.values.tolist()

        area = True
        if not current_user.admin or current_user.name != df['respName'][0]:
            area = False
            for role in eval(current_user.role):
                if request.args['area'].lower() in role.lower():
                    area = True
                    break

        return render_template(
            'request.improvements/improvements_small_detail.html'
            , df=df.to_json()
            , area=request.args['area']
            , requestType=request.args['tipo']
            , dfPause=dfPause
            , admin=area
        )

    else:

        query = f"""SELECT 
                        T1.requestId,
                        T2.name AS requesterName,
                        T1.title,
                        T1.objective,
                        T1.info,
                        T1.actualProblems,
                        T1.benefits,
                        T1.budget,
                        T3.name AS bossName,
                        T1.deniedText,
                        FORMAT(T1.openDate, 'dd/MM/yyyy HH:mm:ss') AS openDate, 
                        FORMAT(T1.clientExpectDate, 'dd/MM/yyyy') AS clientExpectDate, 
                        FORMAT(T1.finalDate, 'dd/MM/yyyy HH:mm:ss') AS finalDate, 
                        T1.status,
                        T1.requesterId,
                        T1.requesterBossId,
                        T4.name AS approverAreaName  
                    FROM 
                        JDT_REQUEST_IMPROVEMENTS_BIG AS T1 
                        JOIN JDT_USER_DETAILS AS T2 ON T1.requesterId = T2.id
                        LEFT JOIN JDT_USER_DETAILS AS T3 ON T1.requesterBossId = T3.id
                        LEFT JOIN JDT_USER_DETAILS AS T4 ON T1.approverArea = T4.id
                    WHERE 
                        T1.requestId = '{request.args['id']}'"""
        df = engine_run_query(query, 'jdt')

        if not current_user.admin and request.args['area'] not in eval(current_user.role) and df['requesterId'][0] != current_user.id and current_user.id != df['requesterBossId'][0]:
            return redirect('/denied')

        if df['status'][0] == 0 and current_user.id == df['requesterBossId'][0]:
            area = True
        elif df['status'][0] == 1:
            area = False
            for role in eval(current_user.role):
                if request.args['area'].lower() in role.lower():
                    area = True
                    break
        else:
            area = False

        return render_template(
            'request.improvements/improvements_big_detail.html'
            , df=df.to_json()
            , area=request.args['area']
            , requestType=request.args['tipo']
            , admin=area
        )


@request_improvements_bp.route('/solicitar/detail/download/image', methods=['GET'])
def improvements_image_download():
    file = rf'app\static\uploads\improvements\{request.args["id"]}\{request.args["arq"]}'
    return send_file(rf'{os.getcwd()}\{file}', as_attachment=True)


@request_improvements_bp.route('/solicitar/dash', methods=['GET', 'POST'])
def improvements_dash():

    # -------------------------
    # GET → abre a página
    # -------------------------
    if request.method == 'GET':
        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            query = "SELECT name, id FROM JDT_USER_DETAILS WHERE admin = 1"
            responsible = pd.read_sql(query, cnnx)
            responsible = responsible[responsible['name'] != 'Digital JOST'].sort_values(by='name')

            query = """
                SELECT DISTINCT T2.name, T2.id
                FROM JDT_REQUEST_IMPROVEMENTS_SMALL T1
                JOIN JDT_USER_DETAILS T2 ON T1.requesterId = T2.id
            """
            requester = pd.read_sql(query, cnnx).sort_values(by='name')

        return render_template(
            'request.improvements/improvements_dash.html',
            responsible=responsible.to_dict(orient='records'),
            requester=requester.to_dict(orient='records')
        )

    # -------------------------
    # POST → BUSCA DADOS
    # -------------------------
    received_data = request.get_json()

    def format_tuple(data):
        has_null = 'NULL' in data
        formatted = f"('{data[0]}')" if len(data) == 1 else tuple(data) if data else ""
        if has_null:
            return f"{formatted} OR respId IS NULL"
        return formatted

    filters = [
        f"AND [status] IN {format_tuple(received_data['status'])}" if received_data.get('status') else "",
        f"AND CASE WHEN urgency = 'Imediata' THEN 'Alta' ELSE urgency END IN {format_tuple(received_data['urgency'])}" if received_data.get('urgency') else "",
        f"AND (respId IN {format_tuple(received_data['responsible'])})" if received_data.get('responsible') else "",
        f"AND requesterId IN {format_tuple(received_data['requester'])}" if received_data.get('requester') else "",
    ]

    filter_string = " ".join(filters)

    # ------------------------------------------------------
    # BARCHART2 – criação OU finalizado (com parênteses)
    # ------------------------------------------------------
    query = f"""
        DECLARE @today datetime;
        SET @today = GETDATE();

        SELECT 
            CASE WHEN 
                deliveryDate > @today AND [status] = 1 THEN 5 
                ELSE [status] 
            END AS [status], 
            finalDate, 
            deliveryDate,
            CASE WHEN urgency = 'Imediata' THEN 'Alta' ELSE urgency END AS urgency,
            openDate 
        FROM JDT_REQUEST_IMPROVEMENTS_SMALL 
        WHERE
            (
                openDate BETWEEN '{received_data['start_date']}' AND '{received_data['end_date']}'
                OR
                finalDate BETWEEN '{received_data['start_date']}' AND '{received_data['end_date']}'
            )
            {filter_string}
    """

    data = engine_run_query(query, 'jdt')

    if len(data) > 0:
        data['openDate'] = pd.to_datetime(data['openDate'])
        data['finalDate'] = pd.to_datetime(data['finalDate'], errors='coerce')

        workday_duration_in_hours = 8 + 48 / 60  # 8h48

        def calculate_business_days(row):
            final_date = row['finalDate'] if pd.notna(row['finalDate']) else pd.Timestamp(datetime.now())
            business_days = np.busday_count(
                row['openDate'].date().strftime('%Y-%m-%d'),
                final_date.date().strftime('%Y-%m-%d')
            )
            return business_days * workday_duration_in_hours

        data['duration'] = data.apply(calculate_business_days, axis=1)

        average_duration_by_urgency = (
            data.groupby('urgency')['duration']
                .mean()
                .reset_index()
                .rename(columns={'urgency': 'label', 'duration': 'count'})
        )
    else:
        average_duration_by_urgency = pd.DataFrame(columns=['label', 'count'])

    # ------------------------------------------------------
    # BARCHART1 – agora COM bimestres vazios (Nov/Dez etc.)
    # ✅ mudança mínima: adiciona calendário de bimestres e LEFT JOIN
    # ------------------------------------------------------
    query = f"""
        DECLARE @today datetime;
        SET @today = GETDATE();

        DECLARE @limitDate date = '{received_data['end_date']}';

        -- início do bimestre atual (para garantir que aparece até o momento)
        DECLARE @bimEnd date = DATEFROMPARTS(
            YEAR(@today),
            ((MONTH(@today) - 1) / 2) * 2 + 1,
            1
        );

        WITH BaseData AS (
            SELECT
                CASE
                    WHEN [status] = 2 AND finalDate IS NOT NULL THEN CAST(finalDate AS date)
                    ELSE CAST(startDate AS date)
                END AS refDate,
                deliveryDate,
                finalDate,
                [status]
            FROM JDT_REQUEST_IMPROVEMENTS_SMALL
            WHERE
                CASE
                    WHEN [status] = 2 AND finalDate IS NOT NULL THEN CAST(finalDate AS date)
                    ELSE CAST(startDate AS date)
                END <= @limitDate
                {filter_string}
        ),

        -- ✅ pega o primeiro bimestre existente para começar o calendário
        Bounds AS (
            SELECT MIN(refDate) AS minRef
            FROM BaseData
        ),

        BimRange AS (
            SELECT
                DATEFROMPARTS(
                    YEAR(COALESCE(minRef, @bimEnd)),
                    ((MONTH(COALESCE(minRef, @bimEnd)) - 1) / 2) * 2 + 1,
                    1
                ) AS bim_start,
                @bimEnd AS bim_end
            FROM Bounds
        ),

        -- ✅ gera todos os bimestres até o bimestre atual (mesmo sem dados)
        Bimestres AS (
            SELECT bim_start
            FROM BimRange
            UNION ALL
            SELECT DATEADD(MONTH, 2, b.bim_start)
            FROM Bimestres b
            CROSS JOIN BimRange r
            WHERE b.bim_start < r.bim_end
        ),

        -- ✅ seus dados agrupados por bimestre (igual já era)
        Grouped AS (
            SELECT
                DATEFROMPARTS(YEAR(refDate), ((MONTH(refDate) - 1) / 2) * 2 + 1, 1) AS bim_start,

                SUM(
                    CASE
                        WHEN (deliveryDate > @today AND [status] = 1)
                          OR (deliveryDate > CAST(finalDate AS DATE) AND [status] = 2)
                        THEN 1 ELSE 0
                    END
                ) AS qtt0,

                SUM(
                    CASE
                        WHEN deliveryDate <= CAST(finalDate AS DATE)
                         AND [status] = 2
                        THEN 1 ELSE 0
                    END
                ) AS qtt1
            FROM BaseData
            GROUP BY DATEFROMPARTS(YEAR(refDate), ((MONTH(refDate) - 1) / 2) * 2 + 1, 1)
        ),

        -- ✅ aqui entra a mágica: calendário + left join para preencher vazios
        Joined AS (
            SELECT
                b.bim_start,
                CONCAT(
                    CASE
                        WHEN MONTH(b.bim_start) = 1  THEN 'Jan/Fev'
                        WHEN MONTH(b.bim_start) = 3  THEN 'Mar/Abr'
                        WHEN MONTH(b.bim_start) = 5  THEN 'Mai/Jun'
                        WHEN MONTH(b.bim_start) = 7  THEN 'Jul/Ago'
                        WHEN MONTH(b.bim_start) = 9  THEN 'Set/Out'
                        WHEN MONTH(b.bim_start) = 11 THEN 'Nov/Dez'
                    END,
                    ' ', YEAR(b.bim_start)
                ) AS label,
                YEAR(b.bim_start) AS year,
                CASE
                    WHEN MONTH(b.bim_start) = 1  THEN 1
                    WHEN MONTH(b.bim_start) = 3  THEN 2
                    WHEN MONTH(b.bim_start) = 5  THEN 3
                    WHEN MONTH(b.bim_start) = 7  THEN 4
                    WHEN MONTH(b.bim_start) = 9  THEN 5
                    WHEN MONTH(b.bim_start) = 11 THEN 6
                END AS period_order,
                COALESCE(g.qtt0, 0) AS qtt0,
                COALESCE(g.qtt1, 0) AS qtt1
            FROM Bimestres b
            LEFT JOIN Grouped g ON g.bim_start = b.bim_start
        ),

        CumulativeData AS (
            SELECT
                label,
                year,
                period_order,
                SUM(qtt0) OVER (ORDER BY year, period_order ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS qtt0_final,
                SUM(qtt1) OVER (ORDER BY year, period_order ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS qtt1_final
            FROM Joined
        )

        SELECT
            label,
            qtt0_final,
            qtt1_final
        FROM CumulativeData
        ORDER BY year, period_order
        OPTION (MAXRECURSION 1200);
    """

    data2 = engine_run_query(query, 'jdt')

    data_to_send = {
        'barchart1': data2.to_json(orient='records'),
        'barchart2': average_duration_by_urgency.to_json(orient='records')
    }

    return data_to_send

# V1