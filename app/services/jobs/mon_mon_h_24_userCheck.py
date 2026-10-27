import pyodbc
import ldap3
import pandas as pd

from backend.shared.environment import required_env

from app.services.run_h_24_scheduler import env
from app.utils.constants import CNNX_JDT, COORD, LEADER
from app.utils.email_utils import send_email_with_attachment

def default(logger):
    
    cnnx = pyodbc.connect(CNNX_JDT)
    cursor = cnnx.cursor()

    query = f"""SELECT * FROM JDT_USER_DETAILS WHERE active = 1 and generic <> 1"""
    user_data = pd.read_sql(query, cnnx)

    base = 'ou=EmpresasRandon,dc=randon,dc=com,dc=br'
    ld = ldap3.Server('SVH-DC-21.randon.com.br', use_ssl=False)
    ld_conn = ldap3.Connection(ld, user=required_env("DJ_LDAP_USER"), password=required_env("DJ_LDAP_PASSWORD"),
                                authentication=ldap3.NTLM)
    ld_conn.bind()

    for index, row in user_data.iterrows():

        ld_conn.search(base, f'(&(objectCategory=Person)(mailNickname={row["id"]}))',
                        attributes=ldap3.ALL_ATTRIBUTES)

        if len(ld_conn.entries) == 0:
            query = f"""UPDATE JDT_USER_DETAILS SET active = 0, disableDay = GETDATE() WHERE id = '{row['id']}'"""
            cursor.execute(query)

        elif 'Fired Employees' in str(ld_conn.entries[0].entry_dn):
            query = f"""UPDATE JDT_USER_DETAILS SET active = 0, disableDay = GETDATE() WHERE id = '{row['id']}'"""
            cursor.execute(query)

        elif 'Jost' not in str(ld_conn.entries[0].physicalDeliveryOfficeName) and (
                'Jost' in str(row['companyName']) or
                str(row['companyName']) != str(ld_conn.entries[0].physicalDeliveryOfficeName)):

            query = f"""UPDATE JDT_USER_DETAILS SET active = 0, disableDay = GETDATE(), role = '["Externo"]' WHERE id = '{row['id']}'"""
            cursor.execute(query)

        else:
            
            user = ld_conn.entries[0]
            
            try:
                shift = str(user.info)
            except:
                shift = '-'

            try:
                position = str(user.title)
                department = str(user.department)

                manager = str(user.manager).split('CN=')[1].split(',')[0]

                companyName = str(user.physicalDeliveryOfficeName)

                ld_conn.search(base, f'(&(objectClass=organizationalPerson)(name={manager}))',
                                attributes=ldap3.ALL_ATTRIBUTES)

                user = ld_conn.entries[0]
                managerId = str(user.mailNickname)

                area = row['areaId']
                if str(row['areaId']) != '15':
                    query = f"""SELECT areaId FROM JDT_GENERAL_AREA WHERE managerId = '{row['id']}'"""
                    area = pd.read_sql(query, cnnx)['areaId']
                    if area.empty:

                        if row['id'] in COORD:
                            aux = f"AND managerId = '{row['id']}'"
                        elif managerId in COORD:
                            aux = f"AND managerId = '{managerId}'"
                        elif managerId in LEADER:
                            aux = f"AND leaderId LIKE '%{managerId}%'"
                        else:
                            aux = 'AND T1.areaId = 200'

                        query = f"""SELECT areaId FROM JDT_GENERAL_AREA WHERE leaderId LIKE '%{row['id']}%'"""
                        area = pd.read_sql(query, cnnx)['areaId']
                        if area.empty:
                            query = f"""SELECT 
                                                    T1.areaId 
                                                FROM JDT_GENERAL_DEPARTMENTS AS T1
                                                JOIN JDT_GENERAL_AREA AS T2 ON T1.areaId = T2.areaId
                                                WHERE departmentName = '{department}' {aux}"""
                            area = pd.read_sql(query, cnnx)['areaId']
                        else:
                            area = [area[0]]

                        if len(area) != 1:

                            query = f"""SELECT userId FROM JDT_USER_PENDING WHERE userId = '{row['id']}' AND status = 0"""
                            sql_data = pd.read_sql(query, cnnx)

                            if len(sql_data) == 0:

                                query = f"""INSERT INTO JDT_USER_PENDING VALUES (
                                                '{row['id']}', '{row['name']}',
                                                '{row['companyEmail']}', '{department}', 0, GETDATE(), NULL, NULL)"""
                                cursor.execute(query)

                                template = env.get_template('general_email_department.html')
                                msg_html = template.render(userName=row['name'], departament=department, bossName=manager)
                                send_email_with_attachment(
                                    subject='Novo departamento detectado',
                                    body=msg_html,
                                    to='JostTransformacaoDigital@empresasrandon.onmicrosoft.com',
                                    sender_name='Transformação Digital JOST',
                                    sender_email='noreply.digitaljost@randon.com.br'
                                )

                            area = str(row['areaId'])
                        else:
                            area = area[0]
                    else:
                        department = 'Gestão'
                        area = 14

                if str(row['shift']) != shift:
                    query = f"""UPDATE JDT_USER_DETAILS SET shift = '{shift}' WHERE id = '{row['id']}'"""
                    cursor.execute(query)
                if str(row['areaId']) != str(area):
                    query = f"""UPDATE JDT_USER_DETAILS SET areaId = '{area}' WHERE id = '{row['id']}'"""
                    cursor.execute(query)
                if str(row['department']) != str(department):
                    query = f"""UPDATE JDT_USER_DETAILS SET department = '{department}' WHERE id = '{row['id']}'"""
                    cursor.execute(query)
                if str(row['position']) != str(position):
                    query = f"""UPDATE JDT_USER_DETAILS SET position = '{position}' WHERE id = '{row['id']}'"""
                    cursor.execute(query)
                if str(row['companyName']) != str(companyName):
                    query = f"""UPDATE JDT_USER_DETAILS SET companyName = '{companyName}' WHERE id = '{row['id']}'"""
                    cursor.execute(query)
                if str(row['managerId']) != str(managerId):
                    query = f"""UPDATE JDT_USER_DETAILS SET managerId = '{managerId}' WHERE id = '{row['id']}'"""
                    cursor.execute(query)

            except Exception as e:
                
                # Loga o usuário que deu erro
                logger.error(
                    f"Erro ao processar usuário id={row['id']} nome={row['name']}: {e}", exc_info=True
                )
                
                raise
                

        cnnx.commit()

    cnnx.close()
