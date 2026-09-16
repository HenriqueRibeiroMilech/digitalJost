import ast
import json
import requests
import pandas as pd

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
_TRANSFORMATION_DIGITAL_ROLE = 'Transformação Digital'

jdt_userManager_bp = Blueprint('jdt_userManager', __name__)


# =========================================================
# HELPERS
# =========================================================
def _current_user_is_admin():
    admin_value = str(getattr(current_user, 'admin', '')).strip().lower()
    return admin_value in {'1', 'true', 'yes'} or p_admin.can()


def _parse_role(value):
    """
    Faz parse seguro do campo role.
    Aceita JSON string, string estilo lista Python e lista já pronta.
    """
    if isinstance(value, list):
        return value

    if value is None:
        return []

    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return []

        try:
            return json.loads(value)
        except Exception:
            pass

        try:
            return ast.literal_eval(value)
        except Exception:
            return []

    return []


def _user_exists(cnnx, user_id):
    df = pd.read_sql(
        text("SELECT TOP 1 id FROM JDT_USER_DETAILS WHERE id = :user_id"),
        cnnx,
        params={"user_id": user_id}
    )
    return not df.empty


def _get_pending_status(cnnx, user_id):
    df = pd.read_sql(
        text("""
            SELECT TOP 1 status
            FROM JDT_USER_PENDING
            WHERE userId = :user_id
            ORDER BY requestDate DESC
        """),
        cnnx,
        params={"user_id": user_id}
    )

    if df.empty:
        return None

    return int(df.iloc[0]["status"])


def _insert_user_details_if_missing(cnnx, user_id):
    """
    Recria o usuário em JDT_USER_DETAILS caso ele não exista.
    """
    if _user_exists(cnnx, user_id):
        return False

    data = create_external_user(user_id)

    params = {f"p{i}": data[i] for i in range(12)}

    cnnx.execute(text("""
        INSERT INTO JDT_USER_DETAILS
        VALUES (
            :p0, :p1, :p2, :p3,
            :p4, :p5, :p6, :p7,
            :p8, :p9, :p10, :p11,
            0, 1, GETDATE(), NULL, 0, 1
        )
    """), params)

    return True


def _create_pending_if_missing(cnnx, user_id):
    """
    Se o usuário não estiver em JDT_USER_PENDING, cria uma solicitação nova.
    """
    existing = pd.read_sql(
        text("""
            SELECT TOP 1 userId, status
            FROM JDT_USER_PENDING
            WHERE userId = :user_id
            ORDER BY requestDate DESC
        """),
        cnnx,
        params={"user_id": user_id}
    )

    if not existing.empty:
        return int(existing.iloc[0]["status"])

    cnnx.execute(text("""
        INSERT INTO JDT_USER_PENDING
            (userId, name, companyEmail, type, requestDate, status, answerDate, approverId)
        VALUES
            (:user_id, :name, :companyEmail, :type, GETDATE(), 0, NULL, NULL)
    """), {
        "user_id": user_id,
        "name": getattr(current_user, "name", user_id),
        "companyEmail": getattr(current_user, "groupEmail", None),
        "type": getattr(current_user, "type", "EXTERNAL")
    })

    return 0


def _ensure_current_user_registration():
    """
    Garante que o usuário autenticado esteja em estado válido:

    1) Se já existe em JDT_USER_DETAILS -> OK
    2) Se foi aprovado em JDT_USER_PENDING mas não existe em DETAILS -> recria
    3) Se não existe em nenhuma tabela -> cria pendência
    4) Se pendente -> manda para tela de aguardando aprovação
    """
    user_id = current_user.id
    engine = get_engine('jdt')

    with engine.begin() as cnnx:
        if _user_exists(cnnx, user_id):
            return None

        pending_status = _get_pending_status(cnnx, user_id)

        if pending_status == 1:
            _insert_user_details_if_missing(cnnx, user_id)
            return None

        if pending_status is None:
            _create_pending_if_missing(cnnx, user_id)

    return redirect(url_for('jdt_userManager.userManager_pending_get'))


def _check_area_permission(areaId):
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        result = pd.read_sql(
            text("""
                SELECT managerId, leaderId
                FROM JDT_GENERAL_AREA
                WHERE areaId = :area_id
            """),
            cnnx,
            params={"area_id": areaId}
        )

        if result.empty:
            abort(404)

        managerId = result['managerId'][0]
        leader_value = result['leaderId'][0]

        if isinstance(leader_value, list):
            leaderIds = leader_value
        else:
            try:
                leaderIds = json.loads(leader_value) if isinstance(leader_value, str) else [leader_value]
                if not isinstance(leaderIds, list):
                    leaderIds = [leaderIds]
            except Exception:
                leaderIds = [leader_value]

    current_roles = _parse_role(getattr(current_user, "role", "[]"))

    not_allowed = managerId != current_user.id and current_user.id not in leaderIds and not _current_user_is_admin()

    if (current_user.areaId != areaId or 'Responsável' not in current_roles) and not_allowed:
        abort(403)


def _update_logs(userId, old, new, extra):
    query = text("""
        INSERT INTO JDT_USER_PERMISSION_LOGS
        VALUES (:current_id, :user_id, :old_value, :new_value, :extra_value, GETDATE())
    """)

    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        cnnx.execute(query, {
            "current_id": current_user.id,
            "user_id": userId,
            "old_value": None if old is None else str(old),
            "new_value": None if new is None else str(new),
            "extra_value": None if extra is None else str(extra)
        })


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
        engine = get_engine('jdt')
        with engine.begin() as cnnx:
            cnnx.execute(
                text("UPDATE JDT_USER_DETAILS SET role = :role WHERE id = :id"),
                {"role": json.dumps(user_role), "id": user}
            )


# =========================================================
# AUTH GATE
# =========================================================
@jdt_userManager_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))

    exempt_endpoints = {
        'jdt_userManager.userManager_pending_get'
    }

    if request.endpoint not in exempt_endpoints:
        recovery = _ensure_current_user_registration()
        if recovery is not None:
            return recovery

        if not get_permission('GENERAL').can():
            return abort(403)


# =========================================================
# TELA DE AGUARDANDO APROVAÇÃO
# =========================================================
@jdt_userManager_bp.route('/usuarios/aguardando', methods=['GET'])
def userManager_pending_get():
    engine = get_engine('jdt')

    with engine.connect() as cnnx:
        if _user_exists(cnnx, current_user.id):
            return redirect(url_for('jdt_userManager.userManager_get'))

        pending = pd.read_sql(
            text("""
                SELECT TOP 1
                    userId,
                    name,
                    companyEmail,
                    type,
                    FORMAT(requestDate, 'dd/MM/yyyy HH:mm') AS requestDate,
                    status
                FROM JDT_USER_PENDING
                WHERE userId = :user_id
                ORDER BY requestDate DESC
            """),
            cnnx,
            params={"user_id": current_user.id}
        )

    if pending.empty:
        with engine.begin() as cnnx:
            _create_pending_if_missing(cnnx, current_user.id)

        return redirect(url_for('jdt_userManager.userManager_pending_get'))

    status = int(pending.iloc[0]['status'])

    if status == 1:
        with engine.begin() as cnnx:
            _insert_user_details_if_missing(cnnx, current_user.id)
        return redirect(url_for('jdt_userManager.userManager_get'))

    return render_template(
        'jdt.permission/permission_pending.html',
        userName=getattr(current_user, 'name', current_user.id),
        requestDate=pending.iloc[0]['requestDate'],
        companyEmail=pending.iloc[0]['companyEmail'],
        requestType=pending.iloc[0]['type']
    )


# =========================================================
# PAGINA PRINCIPAL DA APLICAÇÃO
# =========================================================
@jdt_userManager_bp.route('/usuarios', methods=['GET'])
def userManager_get():
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        areas = pd.read_sql(
            text("SELECT name, areaId FROM JDT_GENERAL_AREA"),
            cnnx
        )

        user_roles_df = pd.read_sql(
            text("SELECT role FROM JDT_USER_DETAILS WHERE id = :user_id"),
            cnnx,
            params={"user_id": current_user.id}
        )

        if user_roles_df.empty:
            return redirect(url_for('jdt_userManager.userManager_pending_get'))

        userRoles = _parse_role(user_roles_df['role'][0])

        allRoles = pd.read_sql(
            text("SELECT name, description, areaId FROM JDT_ROLES"),
            cnnx
        )

    userRoles = allRoles[allRoles['name'].isin(userRoles)].to_json(orient='records')

    notShow = []
    if not _current_user_is_admin():
        notShow.append("b1")

    current_roles = _parse_role(getattr(current_user, "role", "[]"))
    if 'Responsável' not in current_roles and current_user.id not in COORD and current_user.id not in LEADER and not _current_user_is_admin():
        notShow.append("b2")
        notShow.append("b4")

    area_row = areas[areas['areaId'] == current_user.areaId]

    return render_template(
        'jdt.permission/permission_main.html',
        notShow=notShow,
        areas=areas.to_dict(orient='records'),
        userName=current_user.name,
        userPosition=current_user.position,
        userRoles=userRoles,
        user=current_user.id,
        userArea=area_row.reset_index()['name'][0] if not area_row.empty else ''
    )


# =========================================================
# PAGINA QUE VERIFICA TODOS OS USUÁRIOS DEPENDENTES DO SETOR
# =========================================================
@jdt_userManager_bp.route('/usuarios/area', methods=['GET'])
def userManager_area_get():
    areaId = int(request.args['id'])
    _check_area_permission(areaId)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        sql_data = pd.read_sql(
            text(f"""
                SELECT 
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
                ORDER BY CASE WHEN T1.areaId = {areaId} THEN 0 ELSE 1 END, T1.areaId DESC;
            """),
            cnnx
        )

    sql_data['role'] = sql_data.apply(
        lambda row: 'Responsável' in _parse_role(row['role']) and row['areaId'] == int(areaId),
        axis=1
    )

    return render_template(
        'jdt.permission/permission_manage.html',
        table=sql_data.to_json(orient='records'),
        areaId=areaId,
        areaName=sql_data['areaName'][0] if not sql_data.empty else ''
    )


@jdt_userManager_bp.route('/usuarios/area', methods=['POST'])
def userManager_area_post():
    areaId = int(request.args['id'])
    _check_area_permission(areaId)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        user = request.args['user']
        sql_data = pd.read_sql(
            text("""
                SELECT role
                FROM JDT_USER_DETAILS
                WHERE id = :user_id AND areaId = :area_id
            """),
            cnnx,
            params={"user_id": user, "area_id": areaId}
        )['role']

    if len(sql_data) > 0:
        _update_role(_parse_role(sql_data.iloc[0]), user, "Responsável", request.args['type'])

    return 'COMMITED'


# =========================================================
# PAGINA PARA VISUALIZAÇÃO/EDIÇÃO DAS PERMISSÕES DO USUÁRIO
# =========================================================
@jdt_userManager_bp.route('/usuarios/area/permissao', methods=['GET'])
def userManager_area_admin_get():
    user = request.args['user']
    areaId = int(request.args['id'])
    _check_area_permission(areaId)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        sql_data = pd.read_sql(
            text("""
                SELECT 
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
                    T1.id = :user_id
            """),
            cnnx,
            params={"user_id": user}
        )

        areaName_df = pd.read_sql(
            text("SELECT name FROM JDT_GENERAL_AREA WHERE areaId = :area_id"),
            cnnx,
            params={"area_id": areaId}
        )

        areaName = areaName_df['name'][0] if not areaName_df.empty else ''

        if sql_data.empty:
            return redirect('/denied')

        if current_user.admin:
            query2 = text("SELECT name, description FROM JDT_ROLES ORDER BY name DESC")
            allRoles = pd.read_sql(query2, cnnx).to_json(orient='records')
        else:
            query2 = text("""
                SELECT name, description
                FROM JDT_ROLES
                WHERE areaId = :area_id
                ORDER BY name DESC
            """)
            allRoles = pd.read_sql(query2, cnnx, params={"area_id": areaId}).to_json(orient='records')

        userRoles = _parse_role(sql_data['role'][0])

    return render_template(
        'jdt.permission/permission_manage_user.html',
        userRoles=userRoles,
        allRoles=allRoles,
        areaId=areaId,
        areaName=areaName,
        userName=sql_data['name'][0],
        user=sql_data['id'][0],
        userArea=sql_data['areaName'][0],
        userPosition=sql_data['position'][0]
    )


@jdt_userManager_bp.route('/usuarios/area/permissao', methods=['POST'])
def userManager_area_admin_post():
    areaId = int(request.args['id'])
    user = request.args['user']
    payload = request.get_json()

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        sql_data = pd.read_sql(
            text("SELECT areaId FROM JDT_ROLES WHERE name = :role_name"),
            cnnx,
            params={"role_name": payload['accessName']}
        )

        if sql_data.empty:
            abort(404)

        areaId_db = int(sql_data['areaId'][0])

        if not (areaId == areaId_db or current_user.admin):
            abort(403)

        user_role_df = pd.read_sql(
            text("SELECT role FROM JDT_USER_DETAILS WHERE id = :user_id"),
            cnnx,
            params={"user_id": user}
        )

        if user_role_df.empty:
            abort(404)

        _update_role(_parse_role(user_role_df['role'][0]), user, payload['accessName'], payload['action'])

    return 'COMMITED'


# =========================================================
# PAGINA QUE VERIFICA TODOS OS USUÁRIOS DEPENDENTES DO SETOR
# =========================================================
@jdt_userManager_bp.route('/usuarios/paradas', methods=['GET'])
def userManager_eventsChange_approvers_get():
    areaId = int(request.args['area'])
    _check_area_permission(areaId)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        area = pd.read_sql(
            text("""
                SELECT name
                FROM JDT_GENERAL_AREA
                WHERE areaId = :area_id
            """),
            cnnx,
            params={"area_id": areaId}
        )
        areaName = area.iloc[0]['name']

        if areaName == _TRANSFORMATION_DIGITAL_ROLE:
            sql_data = pd.read_sql(
                text("""
                    SELECT id, name, position, role
                    FROM JDT_USER_DETAILS
                    WHERE active = 1
                """),
                cnnx
            )
            sql_data = sql_data[
                sql_data['role'].apply(
                    lambda roles: _TRANSFORMATION_DIGITAL_ROLE in _parse_role(roles)
                )
            ]
        else:
            sql_data = pd.read_sql(
                text("""
                    SELECT id, name, position
                    FROM JDT_USER_DETAILS
                    WHERE areaId = :area_id AND active = 1
                """),
                cnnx,
                params={"area_id": areaId}
            )

        approvers = pd.read_sql(
            text("""
                SELECT userId, shift
                FROM JDT_USER_STOPCHANGES
                WHERE areaId = :area_id
                ORDER BY shift
            """),
            cnnx,
            params={"area_id": areaId}
        ).to_json(orient='records')

    table = sql_data[['id', 'name', 'position']].to_json(orient='records')
    users = sql_data[['id']].to_dict(orient='records')

    return render_template(
        'jdt.permission/permission_stopChanges.html',
        table=table,
        areaName=areaName,
        areaId=areaId,
        users=users,
        approvers=approvers
    )


@jdt_userManager_bp.route('/usuarios/paradas', methods=['POST'])
def userManager_eventsChange_approvers_post():
    userIds = request.get_json()['userIds']
    areaId = int(request.args['area'])
    _check_area_permission(areaId)

    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        def execut(user, shift):
            compare_df = pd.read_sql(
                text("""
                    SELECT userId
                    FROM JDT_USER_STOPCHANGES
                    WHERE areaId = :area_id AND shift = :shift
                """),
                cnnx,
                params={"area_id": areaId, "shift": shift}
            )

            if compare_df.empty:
                cnnx.execute(text("""
                    INSERT INTO JDT_USER_STOPCHANGES (userId, areaId, shift)
                    VALUES (:user_id, :area_id, :shift)
                """), {
                    "user_id": user,
                    "area_id": areaId,
                    "shift": shift
                })

                _update_logs(user, None, user, 'stopChanges_' + str(shift))
                return

            data_to_compare = compare_df['userId'][0]

            if data_to_compare != user:
                cnnx.execute(text("""
                    UPDATE JDT_USER_STOPCHANGES
                    SET userId = :user_id
                    WHERE areaId = :area_id AND shift = :shift
                """), {
                    "user_id": user,
                    "area_id": areaId,
                    "shift": shift
                })

                cnnx.execute(text("""
                    UPDATE JDT_REQUEST_STOPCHANGES
                    SET approver1 = :new_user
                    WHERE approver1 = :old_user AND approverStatus1 = 0
                """), {
                    "new_user": user,
                    "old_user": data_to_compare
                })

                cnnx.execute(text("""
                    UPDATE JDT_REQUEST_STOPCHANGES
                    SET approver2 = :new_user
                    WHERE approver2 = :old_user AND approverStatus2 = 0
                """), {
                    "new_user": user,
                    "old_user": data_to_compare
                })

                _update_logs(user, data_to_compare, user, 'stopChanges_' + str(shift))

        if len(userIds) == 3:
            for i in range(3):
                execut(userIds[i]['user'], userIds[i]['shift'])
        else:
            execut(userIds[0]['user'], userIds[0]['shift'])

    return 'COMMITED'


# =========================================================
# PAGINA AUTORIZAÇÃO DE USUÁRIOS EXTERNOS E CADASTRO DE DEPARTAMENTOS NOVOS
# =========================================================
@jdt_userManager_bp.route('/usuarios/configurar', methods=['GET'])
@p_admin.require(403)
def userManager_config_get():
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        table = pd.read_sql(
            text("""
                SELECT
                    userId,
                    name,
                    companyEmail,
                    type,
                    FORMAT(requestDate, 'dd/MM/yyyy HH:mm') as requestDate,
                    status
                FROM JDT_USER_PENDING
            """),
            cnnx
        )

        area = pd.read_sql(
            text("SELECT * FROM JDT_GENERAL_AREA"),
            cnnx
        )

    areas = area[['areaId', 'name']]
    areasBoss = area[['name', 'managerId', 'leaderId']]

    return render_template(
        'jdt.permission/permission_config.html',
        table=table.to_json(orient='records'),
        areas=areas.to_dict(orient='records'),
        areasBoss=areasBoss.to_dict(orient='records')
    )


@jdt_userManager_bp.route('/usuarios/configurar', methods=['POST'])
@p_admin.require(403)
def userManager_config_post():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        data_request = request.get_json()

        query = f"""UPDATE JDT_USER_PENDING SET
                        answerDate = GETDATE(),
                        status = {data_request['info']},
                        approverId = '{current_user.id}' 
                    WHERE userId = '{data_request['userId']}' and status = 0"""
        cnnx.execute(text(query))

        if request.args['type'] == 'allow' and data_request['info'] == 1:

            data = create_external_user(data_request['userId'])
            query = f"""INSERT INTO JDT_USER_DETAILS VALUES (
                            '{data[0]}', '{data[1]}',
                            '{data[2]}', '{data[3]}',
                            '{data[4]}', '{data[5]}',
                            '{data[6]}', '{data[7]}',
                            '{data[8]}', '{data[9]}',
                            '{data[10]}', '{data[11]}',
                            0, 1, GETDATE(), NULL, 0, 1)"""
            cnnx.execute(text(query))

        elif request.args['type'] == 'department':

            query = f"""SELECT MAX(id) as id FROM JDT_GENERAL_DEPARTMENTS"""
            max_id = pd.read_sql(query, cnnx)['id'][0]

            new_department_id = int(max_id) + 1
            
            query = f"""INSERT INTO JDT_GENERAL_DEPARTMENTS VALUES ({new_department_id}, '{data_request['departmentName']}', {data_request['areaId']})"""
            cnnx.execute(text(query))

            query = f"""SELECT id FROM JDT_USER_DETAILS WHERE id = '{data_request['userId']}'"""
            user_details = pd.read_sql(query, cnnx)

            if user_details.empty:

                data = create_external_user(data_request['userId'])

                query = f"""INSERT INTO JDT_USER_DETAILS VALUES (
                                '{data[0]}', '{data[1]}',
                                '{data[2]}', '{data[3]}',
                                '{data[4]}', '{data[5]}',
                                '{data[6]}', '{data[7]}',
                                '{data[8]}', '{data[9]}',
                                '{data[10]}', '{data[11]}',
                                0, 1, GETDATE(), NULL, 0, 1)"""
                cnnx.execute(text(query))

            query = f"""UPDATE JDT_USER_DETAILS SET
                            areaId = {data_request['areaId']}
                        WHERE id = '{data_request['userId']}'"""
            cnnx.execute(text(query))
        
        cnnx.commit()

    return 'COMMITED'


# =========================================================
# PAGINA PRINCIPAL DE ALERTAS
# =========================================================
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

    if not userData.empty:
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

    return render_template(
        'jdt.permission/permission_alerts.html',
        back=back,
        groups=groups.to_dict(orient='records'),
        workCenters=workcenters[workcenters['Active'] == 1].sort_values(by='Workcenter_Group').to_dict(orient='records'),
        status=events[events['Active'] == 1].to_json(orient='records'),
        userData=userData.to_json(orient='records')
    )


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
        existing = pd.read_sql(
            text("""
                SELECT *
                FROM JDT_DOWNTIME_ALERTS
                WHERE userId = :user_id AND downtimeId = :downtime_id
            """),
            cnnx,
            params={
                "user_id": user_id,
                "downtime_id": data_to_send['event']
            }
        )

        if len(existing) > 0:
            if len(data_to_send['area']) == 0 and len(data_to_send['workcenter']) == 0:
                query = text("""
                    DELETE FROM JDT_DOWNTIME_ALERTS
                    WHERE userId = :user_id AND downtimeId = :downtime_id
                """)
            else:
                query = text("""
                    UPDATE JDT_DOWNTIME_ALERTS SET
                        area = :area,
                        workcenter = :workcenter
                    WHERE userId = :user_id AND downtimeId = :downtime_id
                """)
        else:
            query = text("""
                INSERT INTO JDT_DOWNTIME_ALERTS
                VALUES (:user_id, :downtime_id, :area, :workcenter)
            """)

        cnnx.execute(query, {
            "user_id": user_id,
            "downtime_id": data_to_send['event'],
            "area": json.dumps(data_to_send['area']),
            "workcenter": json.dumps(data_to_send['workcenter'])
        })

    return 'COMMITED'
