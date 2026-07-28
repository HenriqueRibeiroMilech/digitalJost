"""
    JDT Communication
    Rotas e métodos para gerenciamento do cockpit digital, TVs, painéis e barra de comunicação.

    Métodos
    -------
    route_auth()
        Verifica autenticação e permissão do usuário antes de acessar as rotas do blueprint.
    close_file_if_open(filepath)
        Encerra processos que estejam utilizando determinado arquivo (para upload/substituição).
    cockpit_get()
        Exibe página principal do cockpit digital, mostrando dispositivos e programação.
    cockpit_post()
        Realiza atualização de programação ou upload de vídeos/imagens para o cockpit.
    cockpit_tvs_get()
        Exibe página de visualização individual das TVs do cockpit.
    cockpit_tvs_post()
        Realiza atualização dinâmica da página exibida na TV, conforme programação e horário.
    cockpit_factory_get()
        Exibe painel geral do cockpit da fábrica.
    cockpit_factory_post()
        Realiza atualização dinâmica do painel do cockpit da fábrica, conforme programação e horário.
    cockpit_bar()
        Exibe ou atualiza barra de comunicação do cockpit, conforme ID e método.

    Notas
    -----
    - Todas as rotas exigem autenticação e permissões específicas.
    - Utiliza SQLAlchemy para acesso ao banco.
    - Funções auxiliares internas iniciam com '_'.

    Dados retornados são preparados para visualização, cadastro e exportação.
"""

from datetime import datetime
import os
import psutil
import pandas as pd

from sqlalchemy import text

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.utils.db_utils import get_engine
from app.utils.permissions import get_permission


comms = get_permission('COMMS')

jdt_communication_bp = Blueprint('jdt_communication', __name__)

@jdt_communication_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)

def close_file_if_open(filepath):
    for proc in psutil.process_iter():
        try:
            for item in proc.open_files():
                if filepath == item.path:
                    proc.terminate()
        except Exception as e:
            continue

@jdt_communication_bp.route('/cockpit', methods=['GET'])
@comms.require(403)
def cockpit_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT device, page FROM JDT_MAIN_COCKPIT WHERE device IN ('1', '2', '3', '4', '5', '6')"""
        cockpit_values = pd.read_sql(query, cnnx)[['device', 'page']].values.tolist()

        query = f"""SELECT * FROM JDT_MAIN_COCKPIT_SCHEDULE"""
        schedule_values = pd.read_sql(query, cnnx).astype(str)

    schedule_values['timeStart'] = schedule_values['timeStart'].str.slice(0, 8)
    schedule_values['timeEnd'] = schedule_values['timeEnd'].str.slice(0, 8)
    schedule_values = schedule_values.values.tolist()

    return render_template('jdt.communication/tv_cockpit_upload.html', cockpit_values=cockpit_values, schedule_values=schedule_values)
        
@jdt_communication_bp.route('/cockpit', methods=['POST'])
@comms.require(403)
def cockpit_post():

    def format_list_from_request(prefix, request):
        result_list = []
        for key, value in request.form.items():
            if key.startswith(prefix):
                result_list.append(value)
        
        if result_list:
            return '["' + '", "'.join(result_list) + '"]'
        else:
            return '[]'

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        if 'id' in request.args:

            weekDay = format_list_from_request('date_', request)
            page = format_list_from_request('page_', request)

            query = f"""UPDATE JDT_MAIN_COCKPIT_SCHEDULE SET 
                            weekDay = '{weekDay}',
                            timeStart = '{request.form["prog_1"][:5]}:00',
                            timeEnd = '{request.form["prog_2"][:5]}:00',
                            page = '{page}',
                            activated = '{1 if 'activated' in request.form else 0}'

                        WHERE id = '{request.args["id"]}'"""
            cnnx.execute(text(query))

        else:

            tipo = request.args['tipo']

            if tipo == '0':
                
                for key, value in request.form.items():

                    query = f"""UPDATE JDT_MAIN_COCKPIT SET page = '{value}' WHERE device = '{key.split('_')[1]}'"""
                    cnnx.execute(text(query))
            else:
                
                filepath = rf'{os.getcwd()}\app\static\uploads\cockpit\video{int(tipo) + 6}.mp4'
                if os.path.exists(filepath):
                    close_file_if_open(filepath)
                    os.remove(filepath)

                filepath = rf'{os.getcwd()}\app\static\uploads\cockpit\video{int(tipo) + 6}.jpg'
                if os.path.exists(filepath):
                    close_file_if_open(filepath)
                    os.remove(filepath)

                video = request.files[f'video_{tipo}']
                name = f"video{int(tipo) + 6}.{video.filename.split('.')[-1]}"

                query = f"""UPDATE JDT_MAIN_COCKPIT SET page = '{name}' WHERE device = {int(tipo) + 6}"""
                cnnx.execute(text(query))

                video.save(os.path.join(rf'{os.getcwd()}\app\static\uploads\cockpit', name))

        cnnx.commit()
        return redirect("/cockpit")


# TELA DE VISUALIZAÇÃO TVs INDIVIDUAIS
@jdt_communication_bp.route('/cockpit/tv', methods=['GET'])
def cockpit_tvs_get():

    tv = request.args['id']

    arg = ''
    if tv == '0':
        arg = '?ct=' + request.args['ct']

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT page FROM JDT_MAIN_COCKPIT WHERE device = {tv}"""
        toShow = pd.read_sql(query, cnnx)['page'][0] + arg
    
    toShow = toShow if toShow[-3:] not in ['mp4', 'jpg'] else ''.join(filter(str.isdigit, toShow.split('.')[0]))

    return render_template('jdt.communication/tv_cockpit.html', toShow=toShow, tv=tv, workCenter=request.args['ct'] if 'ct' in request.args else "x", group=request.args['group'])

@jdt_communication_bp.route('/cockpit/tv', methods=['POST'])
def cockpit_tvs_post():

    tv = request.args['id']

    arg = ''
    if tv == '0':
        arg = '?ct=' + request.get_json()['workCenter']

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT page FROM JDT_MAIN_COCKPIT WHERE device = {tv}"""
        toShow = pd.read_sql(query, cnnx)['page'][0] + arg
    
        toShow = toShow if toShow[-3:] not in ['mp4', 'jpg'] else ''.join(filter(str.isdigit, toShow.split('.')[0]))
            
        query = f"""SELECT * FROM JDT_MAIN_COCKPIT_SCHEDULE WHERE timeEnd >= CAST(GETDATE() AS TIME) AND timeStart <= CAST(GETDATE() AS TIME) AND activated = 1 AND groupId = {request.args['group']} ORDER BY timeStart DESC"""
        toShowSchedule = pd.read_sql(query, cnnx)

    weekDay = datetime.now().isoweekday()
    toShowSchedule = toShowSchedule[toShowSchedule['weekDay'].astype(str).str.contains(str(weekDay))]

    if len(toShowSchedule) > 0:
        toShowSchedule = toShowSchedule.explode('page').reset_index()
        toShowSchedule['device'] = toShowSchedule.index + 1

        if len(eval(toShowSchedule["page"][0])) == 2 and int(tv) % 2 == 1:
            return f'CHANGE PAGE {eval(toShowSchedule["page"][0])[1]}'
        
        return f'CHANGE PAGE {eval(toShowSchedule["page"][0])[0]}'

    toShowOld = request.get_json()['test']
    
    if toShow != toShowOld:
        return 'UPDATE ' + toShow
    else:
        return 'NOT UPDATE'

# TELA DE VISUALIZAÇÃO DO COCKPIT  
@jdt_communication_bp.route('/cockpit/fabrica', methods=['GET'])
def cockpit_factory_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT page, device FROM JDT_MAIN_COCKPIT WHERE device IN ('1', '2', '3', '4', '5', '6')"""
        toShow = pd.read_sql(query, cnnx)

    return render_template('jdt.communication/tv_cockpit_factory.html', toShow=toShow.to_json(orient='records'))

@jdt_communication_bp.route('/cockpit/fabrica', methods=['POST'])
def cockpit_factory_post():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT page, device FROM JDT_MAIN_COCKPIT WHERE device IN ('1', '2', '3', '4', '5', '6')"""
        toShow = pd.read_sql(query, cnnx)
            
        query = f"""SELECT * FROM JDT_MAIN_COCKPIT_SCHEDULE WHERE timeEnd >= CAST(GETDATE() AS TIME) AND timeStart <= CAST(GETDATE() AS TIME) AND activated = 1 AND groupId = 1 ORDER BY timeStart DESC"""

        toShowSchedule = pd.read_sql(query, cnnx)

    weekDay = datetime.now().isoweekday()
    toShowSchedule = toShowSchedule[toShowSchedule['weekDay'].astype(str).str.contains(str(weekDay))]

    if len(toShowSchedule) > 0:
        toShowSchedule = toShowSchedule.explode('page').reset_index()
        toShowSchedule['device'] = toShowSchedule.index + 1
        return f'CHANGE PAGE {eval(toShowSchedule["page"][0])[0]}'

    toShowOld = request.get_json()
    
    for value in toShowOld:
        device = str(value['device'])
        old_page = str(value['page'])
        new_page = toShow[toShow['device'] == device]['page'].values[0]
        
        # Verificar se a página mudou
        if new_page != old_page:
            return f'UPDATE PAGE {new_page} {device}'
        
    return 'NOT UPDATE'


# BARRA DA TV DO COCKPIT, NECESSITA ID DE ARGUMENTO PARA FUNCIONAR (0, 1, 2)
@jdt_communication_bp.route('/cockpit/fabrica_barra', methods=['GET'])
def cockpit_bar_get():

    return render_template('jdt.communication/tv_cockpit_factory_bar.html', id=request.args['id'])


@jdt_communication_bp.route('/cockpit/fabrica_barra', methods=['POST'])
def cockpit_bar_post():

    novo_texto = f"Cockpit Digital JOST"
    response = {
        'novoTexto': novo_texto
    }
    return jsonify(response)
