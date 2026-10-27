import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, session, g
from flask_login import login_user
from flask_mail import Message
import pyodbc
import ldap3
import win32security
import win32api

from backend.shared.environment import required_env

from app.config import mail, db
from app.models.user import User
from app.utils.constants import LEADER, COORD, CNNX_JDT
from flask_login import current_user

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if 'X-Iis-Windowsauthtoken' in request.headers.keys():
        handle_str = request.headers['X-Iis-Windowsauthtoken']
        handle = int(handle_str, 16)
        win32security.ImpersonateLoggedOnUser(handle)
        username = win32api.GetUserName()
        win32security.RevertToSelf()
        win32api.CloseHandle(handle)
    else:
        username = '00063689'

    # Usa db.session.get() ao invés de User.query.filter_by()
    user = db.session.get(User, username)

    if not user:
        base = 'ou=EmpresasRandon,dc=randon,dc=com,dc=br'
        ld = ldap3.Server('SVH-DC-21.randon.com.br', use_ssl=False)
        ld_conn = ldap3.Connection(ld, user=required_env("DJ_LDAP_USER"), password=required_env("DJ_LDAP_PASSWORD"),
                                   authentication=ldap3.NTLM)
        ld_conn.bind()
        ld_conn.search(base, f'(&(objectCategory=Person)(mailNickname={username}))',
                       attributes=ldap3.ALL_ATTRIBUTES)

        if ld_conn.entries:
            cnnx = pyodbc.connect(CNNX_JDT)
            cursor = cnnx.cursor()
            user_data = ld_conn.entries[0]

            if 'Jost' not in str(user_data.physicalDeliveryOfficeName):
                query = f"""SELECT userId FROM JDT_USER_PENDING WHERE userId = '{username}' AND status <> 0"""
                sql_data = pd.read_sql(query, cnnx)
                if len(sql_data) == 0:
                    query = f"""INSERT INTO JDT_USER_PENDING VALUES (
                                    '{username}', '{str(user_data.displayName)}',
                                    '{str(user_data.mail)}', '0', 0, GETDATE(), NULL, NULL)"""
                    cursor.execute(query)
                    cnnx.commit()
                    msg = Message(f'USUÁRIO EXTERNO DETECTADO',
                                  sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                  recipients=['JostTransformacaoDigital@empresasrandon.onmicrosoft.com'])
                    msg.html = render_template('general_email_external.html',
                                               user=username,
                                               userName=str(user_data.displayName),
                                               userMail=str(user_data.mail))
                    mail.send(msg)
                cnnx.close()
                return redirect('/denied/external')

            name = str(user_data.displayName)
            companyEmail = str(user_data.mail)
            groupEmail = str(user_data.userPrincipalName)
            registration = str(user_data.description).split('; ')[1]
            try:
                shift = str(user_data.info)
            except:
                shift = '-'
            position = str(user_data.title)
            department = str(user_data.department)
            companyName = str(user_data.physicalDeliveryOfficeName)
            manager = str(user_data.manager).split('CN=')[1].split(',')[0]
            if ' - ' in manager:
                manager = manager.split(' - ')[0]
            ld_conn.search(base, f'(&(objectClass=organizationalPerson)(name={manager}*))',
                           attributes=ldap3.ALL_ATTRIBUTES)
            user_data = ld_conn.entries[0]
            managerId = str(user_data.mailNickname)
            query = f"""SELECT areaId FROM JDT_GENERAL_AREA WHERE managerId = '{username}'"""
            area = pd.read_sql(query, cnnx)['areaId']
            if area.empty:
                if username in COORD:
                    aux = f"AND managerId = '{username}'"
                elif managerId in COORD:
                    aux = f"AND managerId = '{managerId}'"
                elif managerId in LEADER:
                    aux = f"AND leaderId LIKE '%{managerId}%'"
                else:
                    aux = 'AND T1.areaId = 200'
                query = f"""SELECT areaId FROM JDT_GENERAL_AREA WHERE leaderId LIKE '%{username}%'"""
                area = pd.read_sql(query, cnnx)['areaId']
                if len(area) == 0:
                    query = f"""SELECT 
                                    T1.areaId 
                                FROM JDT_GENERAL_DEPARTMENTS AS T1
                                JOIN JDT_GENERAL_AREA AS T2 ON T1.areaId = T2.areaId
                                WHERE departmentName = '{department}' {aux}"""
                    area = pd.read_sql(query, cnnx)['areaId']
                else:
                    area = [area[0]]
                if len(area) != 1:
                    query = f"""SELECT userId FROM JDT_USER_PENDING WHERE userId = '{username}' AND status = 0"""
                    sql_data = pd.read_sql(query, cnnx)
                    if len(sql_data) == 0:
                        query = f"""INSERT INTO JDT_USER_PENDING VALUES (
                                        '{username}', '{name}',
                                        '{companyEmail}', '{department}', 0, GETDATE(), NULL, NULL)"""
                        cursor.execute(query)
                        cnnx.commit()
                        msg = Message(f'Novo departamento detectado',
                                      sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                      recipients=['JostTransformacaoDigital@empresasrandon.onmicrosoft.com'])
                        msg.html = render_template('general_email_department.html',
                                                   userName=username,
                                                   departament=department,
                                                   bossName=manager)
                        mail.send(msg)
                    cnnx.close()
                    return redirect('/denied/department')
                else:
                    area = area[0]
            else:
                department = 'Gestão'
                area = 14
            new_user = User(id=username,
                            registration=registration,
                            name=name,
                            companyEmail=companyEmail,
                            groupEmail=groupEmail,
                            shift=shift,
                            areaId=str(area),
                            role='["Jost - Geral"]',
                            position=position,
                            department=department,
                            companyName=companyName,
                            managerId=managerId,
                            admin='0',
                            active='1',
                            generic='0',
                            temp='0')
            new_user.save()
            
            # Busca o usuário novamente e adiciona ao cache
            user = db.session.get(User, username)
            
            # Adiciona ao cache da requisição
            if not hasattr(g, '_user_cache'):
                g._user_cache = {}
            g._user_cache[username] = user
            
            query = f"""UPDATE JDT_USER_DETAILS SET activateDay = GETDATE() WHERE id = '{username}'"""
            cursor.execute(query)
            cnnx.commit()
            cnnx.close()
        else:
            return redirect('/denied')
    
    # Adiciona usuário ao cache se ainda não estiver
    if not hasattr(g, '_user_cache'):
        g._user_cache = {}
    g._user_cache[username] = user
    
    if not user.active:
        return redirect('/denied')
    # if not user.temp:
    #     return redirect('/research')
    login_user(user)
    session.permanent = False
    if not request.args.get('next') or request.args.get('next') == '/':
        next_page = url_for('main.landing_page_get')
    else:
        next_page = request.args.get('next')
    return redirect(next_page)

@auth.route('/denied', methods=['GET'])
def denied_get():
    return render_template('general_role_denied.html')

@auth.route('/denied/external', methods=['GET'])
def denied_external_user_get():
    return render_template('general_external_user.html')

@auth.route('/denied/department', methods=['GET'])
def denied_department_get():

    user_id = session.get('_user_id')

    # sessão ativa, mas usuário não existe mais no banco
    if user_id:
        user = db.session.get(User, user_id)
        if user is None:
            return redirect(url_for('auth.login'))

    return render_template('general_not_department.html')