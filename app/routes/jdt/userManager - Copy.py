import pandas as pd
import json
import requests

from flask import Blueprint, abort, jsonify, render_template, request, redirect, url_for
from flask_login import current_user
from sqlalchemy import text

from app.utils.azure_utils import get_azure_header
from app.utils.constants import COORD, LEADER
from app.utils.db_utils import engine_run_query, get_engine
from app.utils.dynamic_constants import getPlex
from app.utils.permissions import get_permission
from app.utils.security_utils import create_external_user

p_admin = get_permission('SYSADMIN')

jdt_userManager_bp = Blueprint('jdt_userManager', __name__)

@jdt_userManager_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)
    

def _check_area_permission(areaId):
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"SELECT managerId, leaderId FROM JDT_GENERAL_AREA WHERE areaId = '{areaId}'"
        result = pd.read_sql(query, cnnx)
        managerId = result['managerId'][0]
        leaderIds = result['leaderId'][0] if isinstance(result['leaderId'][0], list) else [result['leaderId'][0]]

    not_allowed = managerId != current_user.id and current_user.id not in leaderIds and not current_user.admin

    if (current_user.areaId != areaId or 'Responsável' not in eval(current_user.role)) and not_allowed:
        abort(403)

def _update_role(user_role, user, new_role, action):

    role_changed = False

    if action == 'assign':
        if new_role not in user_role:
            user_role.append(new_role)
            role_changed = True
            _update_logs(user, None, new_role, 'role')
    else:
        if new_role in user_role:
            user_role.remove(new_role)
            role_changed = True
            _update_logs(user, new_role, None, 'role')


    if role_changed:
        def update_user_role(user_role, user):
            engine = get_engine('jdt')
            query = "UPDATE JDT_USER_DETAILS SET role = :role WHERE id = :id"
            with engine.begin() as cnnx:
                cnnx.execute(text(query), {"role": json.dumps(user_role), "id": user})

        update_user_role(user_role, user)

def _update_logs(userId, old, new, extra):

    extra = f"'{extra}'" if extra is not None else 'NULL'
    old = "'" + str(old) + "'" if str(old) != 'None' else 'NULL'
    new = "'" + str(new) + "'" if str(new) != 'None' else 'NULL'

    query = f"""INSERT INTO JDT_USER_PERMISSION_LOGS VALUES ('{current_user.id}', '{userId}', {old}, {new}, {extra}, GETDATE())"""

    engine = get_engine('jdt')
    with engine.begin() as cnnx:    
        cnnx.execute(text(query))


# PAGINA PRINCIPAL DA APLICAÇÃO
@jdt_userManager_bp.route('/usuarios', methods=['GET'])
def userManager_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT name, areaId FROM JDT_GENERAL_AREA"""
        areas = pd.read_sql(query, cnnx)

        query = f"""SELECT role FROM JDT_USER_DETAILS WHERE id = '{current_user.id}'"""
        userRoles = eval(pd.read_sql(query, cnnx)['role'][0])

        query = f"""SELECT name, description, areaId FROM JDT_ROLES"""
        allRoles = pd.read_sql(query, cnnx)

    userRoles = allRoles[allRoles['name'].isin(userRoles)].to_json(orient='records')

    notShow = []
    if not current_user.admin:
        notShow.append("b1")

    if not 'Responsável' in eval(current_user.role) and current_user.id not in COORD and current_user.id not in LEADER and not current_user.admin:
        notShow.append("b2")
        notShow.append("b4")

    return render_template('jdt.permission/permission_main.html', notShow=notShow
                           , areas=areas.to_dict(orient='records') 
                            , userName=current_user.name
                            , userPosition=current_user.position
                            , userRoles=userRoles
                            , user=current_user.id
                            , userArea=areas[areas['areaId'] == current_user.areaId].reset_index()['name'][0])


# PAGINA QUE VERIFICA TODOS OS USUÁRIOS DEPENDENTES DO SETOR
@jdt_userManager_bp.route('/usuarios/area', methods=['GET'])
def userManager_area_get():

    areaId = int(request.args['id'])
    _check_area_permission(areaId)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT 
                        T1.id,
                        T1.name,
                        T2.name AS areaName,
                        T1.position,
                        T1.role,
                        T1.areaId 
                    FROM 
                        JDT_USER_DETAILS AS T1 
                        JOIN JDT_GENERAL_AREA AS T2 ON T1.areaId = T2.areaId
                    WHERE active = 1
                    ORDER BY CASE WHEN T1.areaId = {areaId} THEN 0 ELSE 1 END, T1.areaId DESC;"""
        sql_data = pd.read_sql(query, cnnx)

    sql_data['role'] = sql_data.apply(lambda row: 'Responsável' in eval(row['role']) and row['areaId'] == int(areaId), axis=1)

    return render_template('jdt.permission/permission_manage.html'
                           , table=sql_data.to_json(orient='records')
                           , areaId=areaId, areaName=sql_data['areaName'][0])
    
@jdt_userManager_bp.route('/usuarios/area', methods=['POST'])
def userManager_area_post():
    
    areaId = int(request.args['id'])
    _check_area_permission(areaId)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        user = request.args['user']
        query = f"""SELECT role FROM JDT_USER_DETAILS WHERE id = '{user}' AND areaId = '{areaId}'"""
        sql_data = pd.read_sql(query, cnnx)['role']

    if len(sql_data) > 0:
        _update_role(eval(sql_data[0]), user, "Responsável", request.args['type'])
    
    return 'COMMITED'


# PAGINA PARA VISUALIZAÇÃO/EDIÇÃO DAS PERMISSÕES DO USUÁRIO
@jdt_userManager_bp.route('/usuarios/area/permissao', methods=['GET'])
def userManager_area_admin_get():

    user = request.args['user']
    areaId = int(request.args['id'])
    _check_area_permission(areaId)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT 
                        T1.id,
                        T1.name,
                        T1.position, 
                        T1.role,
                        T2.name AS areaName,
                        T2.areaID AS areaId   
                    FROM 
                        JDT_USER_DETAILS AS T1 
                        JOIN JDT_GENERAL_AREA AS T2 ON T1.areaId = T2.areaId
                    WHERE 
                        T1.id = '{user}'"""
        sql_data = pd.read_sql(query, cnnx)

        query = f"""SELECT name FROM JDT_GENERAL_AREA WHERE areaId = '{areaId}'"""
        areaName = pd.read_sql(query, cnnx)['name'][0]

        if sql_data.empty:
            return redirect('/denied')

        if current_user.admin:
            condition = "LIKE '%%'"
        else:
            condition = f"= {areaId}"

        query2 = f"""SELECT name, description FROM JDT_ROLES WHERE areaId {condition} ORDER BY name DESC;"""
        allRoles = pd.read_sql(query2, cnnx).to_json(orient='records')

        userRoles = eval(sql_data['role'][0])

    return render_template('jdt.permission/permission_manage_user.html'
                            , userRoles=userRoles, allRoles=allRoles, areaId=areaId
                            , areaName=areaName, userName=sql_data['name'][0]
                            , user=sql_data['id'][0], userArea=sql_data['areaName'][0]
                            , userPosition=sql_data['position'][0])

@jdt_userManager_bp.route('/usuarios/area/permissao', methods=['POST'])
def userManager_area_admin_post():
        
    areaId = int(request.args['id'])
    user = request.args['user']

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"SELECT areaId FROM JDT_ROLES WHERE name = '{request.get_json()['accessName']}'"
        sql_data = pd.read_sql(query, cnnx)
        areaId_db = sql_data['areaId'][0]

        if not (areaId == areaId_db or current_user.admin):
            abort(403)

        query = f"SELECT role FROM JDT_USER_DETAILS WHERE id = '{user}'"
        sql_data = pd.read_sql(query, cnnx)
        _update_role(eval(sql_data['role'][0]), user, request.get_json()['accessName'], request.get_json()['action'])
        return 'COMMITED'


# PAGINA QUE VERIFICA TODOS OS USUÁRIOS DEPENDENTES DO SETOR
@jdt_userManager_bp.route('/usuarios/paradas', methods=['GET'])
def userManager_eventsChange_approvers_get():

    areaId = int(request.args['area'])
    _check_area_permission(areaId)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT 
                        T1.id,
                        T1.name,
                        T1.position,
                        T2.areaId, 
                        T2.name AS areaName 
                    FROM 
                        JDT_USER_DETAILS AS T1 
                        JOIN JDT_GENERAL_AREA AS T2 ON T1.areaId = T2.areaId
                    WHERE 
                        T1.areaId = {areaId} AND T1.active = 1"""
        sql_data = pd.read_sql(query, cnnx)

        query = f"""SELECT userId, shift FROM JDT_USER_STOPCHANGES WHERE areaId = '{areaId}' ORDER BY shift"""
        approvers = pd.read_sql(query, cnnx).to_json(orient='records')

    areaName = sql_data['areaName'][0]
    table = sql_data[['id', 'name', 'position']].to_json(orient='records')
    users = sql_data[['id']].to_dict(orient='records')

    return render_template('jdt.permission/permission_stopChanges.html'
                           , table=table, areaName=areaName
                           , areaId=areaId, users=users, approvers=approvers)

@jdt_userManager_bp.route('/usuarios/paradas', methods=['POST'])
def userManager_eventsChange_approvers_post():

    userIds = request.get_json()['userIds']
    areaId = int(request.args['area'])
    _check_area_permission(areaId)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        def execut(user, shift):
            query = f"SELECT userId FROM JDT_USER_STOPCHANGES WHERE areaId = {areaId} AND shift = {shift}"
            data_to_compare = pd.read_sql(query, cnnx)['userId'][0]
            if data_to_compare != user:
                query = f"UPDATE JDT_USER_STOPCHANGES SET userId = '{user}' WHERE areaId = {areaId} AND shift = {shift}"
                cnnx.execute(text(query))

                # PASSA OS PROCESSOS DE ALTERAÇÕES ATIVOS PARA O USUÁRIO NOVO
                query = f"UPDATE JDT_REQUEST_STOPCHANGES SET approver1 = '{user}' WHERE approver1 = '{data_to_compare}' AND approverStatus1 = 0"
                cnnx.execute(text(query))

                query = f"UPDATE JDT_REQUEST_STOPCHANGES SET approver2 = '{user}' WHERE approver2 = '{data_to_compare}' AND approverStatus2 = 0"
                cnnx.execute(text(query))

                cnnx.commit()

                _update_logs(user, data_to_compare, user, 'stopChanges_' + str(shift))

        if len(userIds) == 3:
            for i in range(3):
                execut(userIds[i]['user'], userIds[i]['shift'])
        else:
            execut(userIds[0]['user'], userIds[0]['shift'])

    return 'COMMITED'


# PAGINA AUTORIZAÇÃO DE USUÁRIOS EXTERNOS E CADASTRO DE DEPARTAMENTOS NOVOS
@jdt_userManager_bp.route('/usuarios/configurar', methods=['GET'])
@p_admin.require(403)
def userManager_config_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT
                        userId,
                        name,
                        companyEmail,
                        type,
                        FORMAT(requestDate, 'dd/MM/yyyy HH:mm') as requestDate,
                        status
                    FROM JDT_USER_PENDING"""
        table = pd.read_sql(query, cnnx)

        query = f"""SELECT * FROM JDT_GENERAL_AREA"""
        area = pd.read_sql(query, cnnx)

    areas = area[['areaId', 'name']]
    areasBoss = area[['name', 'managerId', 'leaderId']]

    return render_template('jdt.permission/permission_config.html'
                           , table=table.to_json(orient='records')
                           , areas=areas.to_dict(orient='records')
                           , areasBoss=areasBoss.to_dict(orient='records'))

@jdt_userManager_bp.route('/usuarios/configurar', methods=['POST'])
@p_admin.require(403)
def userManager_config_post():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""UPDATE JDT_USER_PENDING SET
                        answerDate = GETDATE(),
                        status = {request.get_json()['info']},
                        approverId = '{current_user.id}' 
                    WHERE userId = '{request.get_json()['userId']}' and status = 0"""
        cnnx.execute(text(query))

        if request.args['type'] == 'allow' and request.get_json()['info'] == 1:

            data = create_external_user(request.get_json()['userId'])
            query = f"""INSERT INTO JDT_USER_DETAILS VALUES (
                            '{data[0]}', '{data[1]}',
                            '{data[2]}', '{data[3]}',
                            '{data[4]}', '{data[5]}',
                            '{data[6]}', '{data[7]}',
                            '{data[8]}', '{data[9]}',
                            '{data[10]}', '{data[11]}',
                            0, 1, GETDATE(), NULL, 0, 1)"""

        elif request.args['type'] == 'department':

            query = f"""SELECT MAX(id) as id FROM JDT_GENERAL_DEPARTMENTS"""
            max_id = pd.read_sql(query, cnnx)['id'][0]
            
            query = f"""INSERT INTO JDT_GENERAL_DEPARTMENTS VALUES ({int(max_id) + 1}, '{request.get_json()['departmentName']}', {request.get_json()['areaId']})"""
        
        cnnx.execute(text(query))
        cnnx.commit()

    return 'COMMITED'


# PAGINA PRINCIPAL DA APLICAÇÃO
@jdt_userManager_bp.route('/usuarios/alertas', methods=['GET'])
def userManager_downtimeAlerts_get():

    user_url = f"https://graph.microsoft.com/v1.0/users/{current_user.groupEmail}"
    user_response = requests.get(user_url, headers=get_azure_header(), verify=False)

    if user_response.status_code != 200:
        return jsonify({
            "error": "Usuário Teams não encontrado"
        }), 404
        
    user_id = user_response.json().get("id")

    query = f"""SELECT downtimeId, area, workcenter FROM JDT_DOWNTIME_ALERTS WHERE userId = '{user_id}'"""
    userData = engine_run_query(query, 'jdt')

    userData['area'] = userData['area'].apply(json.loads)
    userData['workcenter'] = userData['workcenter'].apply(json.loads)

    query = f"""SELECT NOME_MAQUINA as Name, CT as Workcenter_Code, GRUPO as Workcenter_Group FROM CONFIG_TABLET WHERE FL_ATIVO = 1"""
    mic_workcenters = engine_run_query(query, 'ftm').drop_duplicates(subset='Workcenter_Code')
    plex_workcenters = getPlex('workcenters')[['Workcenter_Code', 'Workcenter_Group', 'Name', 'Active']]

    workcenters = pd.concat([mic_workcenters, plex_workcenters], axis=0)

    groups = plex_workcenters[['Workcenter_Group']].drop_duplicates().dropna().sort_values(by='Workcenter_Group')
    
    events = getPlex('events')
    events['Code'] = events['Code'].astype(int)
    events = events.sort_values(by='Code')


    back = 'usuarios'
    if 'origin' in request.args:
        back = 'monitoramento/paradas'

    return render_template('jdt.permission/permission_alerts.html', back=back
                            , groups=groups.to_dict(orient='records')
                            , workCenters=workcenters[workcenters['Active'] == 1].sort_values(by='Workcenter_Group').to_dict(orient='records')
                            , status=events[events['Active'] == 1].to_json(orient='records')
                            , userData=userData.to_json(orient='records'))

@jdt_userManager_bp.route('/usuarios/alertas', methods=['POST'])
def userManager_downtimeAlerts_post():

    data_to_send = request.get_json()

    user_url = f"https://graph.microsoft.com/v1.0/users/{current_user.groupEmail}"
    user_response = requests.get(user_url, headers=get_azure_header(), verify=False)

    if user_response.status_code != 200:
        return jsonify({
            "error": "Usuário Teams não encontrado"
        }), 404       
        
    user_id = user_response.json().get("id")

    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        query = f"""SELECT * FROM JDT_DOWNTIME_ALERTS WHERE userId = '{user_id}' and downtimeId = '{data_to_send['event']}'"""
        if len(pd.read_sql(query, cnnx)) > 0:

            if len(data_to_send['area']) == 0 and len(data_to_send['workcenter']) == 0:
                query = f"""DELETE FROM JDT_DOWNTIME_ALERTS WHERE userId = '{user_id}' AND downtimeId = '{data_to_send['event']}'"""
            else:
                query = f"""UPDATE JDT_DOWNTIME_ALERTS SET
                                area = '{json.dumps(data_to_send['area'])}',
                                workcenter = '{json.dumps(data_to_send['workcenter'])}'
                            WHERE userId = '{user_id}' AND downtimeId = '{data_to_send['event']}'"""
        else:
            query = f"""INSERT INTO JDT_DOWNTIME_ALERTS VALUES (
                                '{user_id}',
                                '{data_to_send['event']}',
                                '{json.dumps(data_to_send['area'])}',
                                '{json.dumps(data_to_send['workcenter'])}')"""
            
        cnnx.execute(text(query))

    return 'COMMITED'