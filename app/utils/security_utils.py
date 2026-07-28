import ldap3
import json

from sqlalchemy import text

from app.utils.db_utils import get_engine

def access_register(user_id, route, args, payload, method, status_code, dt):
    """
    Registra o acesso do usuário autenticado, salvando o status da resposta.
    Só registra se user_id não for None ou 'Anon'.
    """
    if not user_id or user_id == 'Anon':
        return None
    args_json = json.dumps(args, ensure_ascii=False)
    payload_json = json.dumps(payload, ensure_ascii=False)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = """
            INSERT INTO JDT_USER_LOGS (userId, route, args, payload, method, statusCode, accessTime)
            VALUES (:userId, :route, :args, :payload, :method, :statusCode, :accessTime)
        """
        cnnx.execute(text(query), {
            'userId': user_id,
            'route': route,
            'args': args_json,
            'payload': payload_json,
            'method': method,
            'statusCode': int(status_code),
            'accessTime': str(dt)
        })
        cnnx.commit()

    return f'\nSERVER LOG [{dt}] - {user_id} acessou "{route}" args={args_json} method={method} status={status_code}\n'

def update_logs(cnnx_str, userId, table, key, old, new, extra, register):

    extra = extra if extra != '' else None
    old = old if old != '' else None
    new = new if new != '' else None

    engine = get_engine(cnnx_str)
    with engine.connect() as cnnx:
        query = f"""
            INSERT INTO {table} (id, userId, old, new, extra, register, date)
            VALUES (:id, :userId, :old, :new, :extra, :register, GETDATE())
        """
        cnnx.execute(text(query), {
            'id': key,
            'userId': userId,
            'old': old,
            'new': new,
            'extra': extra,
            'register': register
        })
        cnnx.commit()


def create_external_user(username):

    base = 'ou=EmpresasRandon,dc=randon,dc=com,dc=br'
    ld = ldap3.Server('SVH-DC-21.randon.com.br', use_ssl=False)
    ld_conn = ldap3.Connection(ld, user=r"randon.com.br\Fabrica_Jost", password='Empresasrandon@2018',
                               authentication=ldap3.NTLM)
    ld_conn.bind()
    ld_conn.search(base, f'(&(objectCategory=Person)(mailNickname={username}))',
                   attributes=ldap3.ALL_ATTRIBUTES)

    if ld_conn.entries:

        user_data = ld_conn.entries[0]

        name = str(user_data.displayName)
        companyEmail = str(user_data.mail)
        groupEmail = str(user_data.userPrincipalName)
        shift = str(user_data.info)
        position = str(user_data.title)
        department = str(user_data.department)
        companyName = str(user_data.physicalDeliveryOfficeName)
        manager = str(user_data.manager).split('CN=')[1].split(',')[0]
        registration = str(user_data.description).split('; ')[1]

        ld_conn.search(base, f'(&(objectClass=organizationalPerson)(name={manager}))',
                       attributes=ldap3.ALL_ATTRIBUTES)

        user_data = ld_conn.entries[0]
        managerId = str(user_data.mailNickname)

        return [username,
                registration,
                name,
                companyEmail,
                groupEmail,
                shift,
                15,
                '["Externo"]',
                position,
                department,
                companyName,
                managerId,
                ]
