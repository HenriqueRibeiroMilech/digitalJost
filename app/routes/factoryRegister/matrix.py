"""
    FactoryRegisterMatrix
    Rotas e métodos para cadastro, consulta e painel de matriz de operações, centros de trabalho e operadores.

    Métodos
    -------
    matrix_get()
        Exibe página principal da matriz.
    matrix_wc_get()
        Exibe página de cadastro/consulta de workcenters, operações e processos.
    matrix_wc_post()
        Realiza cadastro, atualização, ordenação e exclusão de workcenters, operações e processos.
    matrix_workers_get()
        Exibe página de cadastro/consulta de operadores e posições.
    matrix_workers_post()
        Realiza cadastro, atualização e exclusão de operadores e posições.
    matrix_panel_get()
        Exibe painel de versatilidade da matriz, mesclando dados de usuários, processos e workcenters.
    matrix_panel_post()
        Realiza cadastro, atualização ou exclusão de versatilidade de operadores.

    Notas
    -----
    - Todas as rotas exigem autenticação e permissões específicas.
    - Utiliza SQLAlchemy para acesso ao banco.
    - Funções auxiliares internas iniciam com '_'.
    - Dados retornados são preparados para visualização, cadastro e exportação.
"""

import pandas as pd

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user

from app.utils.db_utils import get_engine
from app.utils.dynamic_constants import getPlex
from app.utils.permissions import get_permission

general = get_permission('GENERAL')
matrix = get_permission('MATRIX')

factoryRegister_matrix_bp = Blueprint('factoryRegister_matrix', __name__)

@factoryRegister_matrix_bp.route('/matriz', methods=['GET'])
@general.require(403)
def matrix_get():
    return render_template('factoryRegister.matrix/matrix_main.html')

@factoryRegister_matrix_bp.route('/matriz/ct', methods=['GET'])
@matrix.require(403)
def matrix_wc_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx: 
        query = f"""SELECT * FROM PLEX_MATRIX_WORKCENTER"""
        matrix_workcenter = pd.read_sql(query, cnnx)

        query = f"""SELECT * FROM PLEX_MATRIX_OPERATION"""
        matrix_operation = pd.read_sql(query, cnnx)

        query = f"""SELECT * FROM PLEX_MATRIX_PROCESS"""
        matrix_process= pd.read_sql(query, cnnx)

    return render_template('factoryRegister.matrix/matrix_wc.html'
                            , workcenters=getPlex('workcenters').to_dict(orient='records')
                            , matrix_operation=matrix_operation.to_dict(orient='records')
                            , matrix_workcenter=matrix_workcenter.to_json(orient='records')
                            , matrix_process=matrix_process.to_json(orient='records'))

@factoryRegister_matrix_bp.route('/matriz/ct', methods=['POST'])
@matrix.require(403)
def matrix_wc_post():

    payload = request.get_json()
    workcenters = getPlex('workcenters')

    engine = get_engine('jdt')
    with engine.connect() as cnnx: 

        try:

            if request.args['type'] == 'ct':

                if int(payload['workcenter']) in workcenters['Workcenter_Key'].values:


                    query = f"""INSERT INTO PLEX_MATRIX_WORKCENTER VALUES (
                            {payload['workcenter']}, '{payload['description']}', 1
                    )"""

                    cnnx.execute(text(query))

                    query = f"""SELECT * FROM PLEX_MATRIX_WORKCENTER"""

            elif request.args['type'] == 'op':

                query = f"""INSERT INTO PLEX_MATRIX_OPERATION VALUES (
                        '{payload['name']}', 1
                )"""

                cnnx.execute(text(query))

                query = f"""SELECT * FROM PLEX_MATRIX_OPERATION"""

            elif request.args['type'] == 'relate':
                
                query = f"""SELECT count(*) AS id FROM PLEX_MATRIX_PROCESS WHERE workcenter = {payload['workcenter']}"""
                order = pd.read_sql(query, cnnx)['id'][0]

                query = f"""INSERT INTO PLEX_MATRIX_PROCESS VALUES (
                        {payload['workcenter']},
                        {payload['operation']},
                        {order},
                        {payload['special']},
                        1
                )"""

                cnnx.execute(text(query))

                query = f"""SELECT * FROM PLEX_MATRIX_PROCESS"""
            
            elif request.args['type'] == 'detach':

                query = f"""SELECT [order] FROM PLEX_MATRIX_PROCESS WHERE workcenter = {payload['workcenter']} AND operation = {payload['operation']}"""
                order = pd.read_sql(query, cnnx)['order'][0]
                
                query_delete = """
                DELETE FROM PLEX_MATRIX_PROCESS
                WHERE workcenter = :workcenter AND operation = :operation;
                """

                query_update = """
                UPDATE PLEX_MATRIX_PROCESS SET 
                    [order] = [order] - 1
                WHERE workcenter = :workcenter AND [order] > :order;
                """

                cnnx.execute(text(query_delete), {'workcenter': payload['workcenter'], 'operation': payload['operation']})
                cnnx.execute(text(query_update), {'workcenter': payload['workcenter'], 'order': int(order)})

                query = f"""SELECT * FROM PLEX_MATRIX_PROCESS"""
            
            elif request.args['type'] == 'change':

                field_to_update = "[status]" if payload['field'] == 1 else "special"

                query = f"""
                    UPDATE PLEX_MATRIX_PROCESS 
                    SET {field_to_update} = {payload['value']} 
                    WHERE workcenter = {payload['workcenter']} 
                    AND operation = {payload['operation']}
                """
                cnnx.execute(text(query))

                query = f"""SELECT * FROM PLEX_MATRIX_PROCESS"""

            elif request.args['type'] == 'order':

                query = f"""SELECT MAX([order]) AS max 
                            FROM PLEX_MATRIX_PROCESS 
                            WHERE workcenter = {payload['workcenter']}"""
                info = pd.read_sql(query, cnnx)

                query = f"""SELECT [order]
                            FROM PLEX_MATRIX_PROCESS 
                            WHERE workcenter = {payload['workcenter']} 
                            AND operation = {payload['operation']}"""
                order = pd.read_sql(query, cnnx)['order'][0]

                # Mover para cima
                if payload['where'] == 'up' and order < info['max'][0]:
                    query = f"""
                        WITH swapped AS (
                            SELECT operation, [order]
                            FROM PLEX_MATRIX_PROCESS
                            WHERE workcenter = {payload['workcenter']}
                            AND [order] IN ({order}, {order} + 1)
                        )
                        UPDATE PLEX_MATRIX_PROCESS
                        SET [order] = CASE 
                            WHEN [order] = {order} THEN {order} + 1
                            WHEN [order] = {order} + 1 THEN {order}
                        END
                        WHERE workcenter = {payload['workcenter']} 
                        AND operation IN (SELECT operation FROM swapped)
                    """
                    cnnx.execute(text(query))

                # Mover para baixo
                elif payload['where'] == 'down' and order > 0:
                    query = f"""
                        WITH swapped AS (
                            SELECT operation, [order]
                            FROM PLEX_MATRIX_PROCESS
                            WHERE workcenter = {payload['workcenter']}
                            AND [order] IN ({order}, {order} - 1)
                        )
                        UPDATE PLEX_MATRIX_PROCESS
                        SET [order] = CASE 
                            WHEN [order] = {order} THEN {order} - 1
                            WHEN [order] = {order} - 1 THEN {order}
                        END
                        WHERE workcenter = {payload['workcenter']} 
                        AND operation IN (SELECT operation FROM swapped)
                    """
                    cnnx.execute(text(query))

                query = f"""SELECT * FROM PLEX_MATRIX_PROCESS"""
            
            else:

                query = f"""UPDATE PLEX_MATRIX_WORKCENTER SET status = {payload['status']} WHERE id = {payload['workcenter']} """

                cnnx.execute(text(query))

                query = f"""SELECT * FROM PLEX_MATRIX_WORKCENTER"""

            cnnx.commit()
            response_data = pd.read_sql(query, cnnx)


            return jsonify(response_data.to_dict(orient='records')), 200
        
        
        except IntegrityError as e:
            if hasattr(e.orig, 'args') and e.orig.args and '2627' in str(e.orig.args):
                return jsonify({"error": "Este registro já foi inserido."}), 409
            else:
                return jsonify({"error": "Erro de integridade no banco de dados."}), 400
        
        except SQLAlchemyError as e:

            return jsonify({"error": str(e)}), 500


@factoryRegister_matrix_bp.route('/matriz/operadores', methods=['GET'])
@matrix.require(403)
def matrix_workers_get():
        
    engine = get_engine('jdt')
    with engine.connect() as cnnx: 

        query = f"""SELECT 
                        T1.id,
                        T1.bossId,
                        T3.name AS bossName,
                        T1.name,
                        T1.shift,
                        T1.position as positionId,
                        T2.name AS positionName,
                        T1.status                           

                    FROM PLEX_MATRIX_USER T1 
                    JOIN PLEX_MATRIX_POSITION T2 ON T1.position = T2.id
                    JOIN JDT_USER_DETAILS T3 ON T1.bossId = T3.id"""
        users = pd.read_sql(query, cnnx)
        users['id'] = users['id'].str[4:]

        query = f"""
                    WITH CTE AS (
                        SELECT 
                            [position],
                            COUNT(*) AS qtt
                        FROM PLEX_MATRIX_USER
                        GROUP BY [position]
                    )

                    SELECT 
                        T1.id,
                        T1.name,
                        COALESCE(CTE.qtt, 0) AS qtt,
                        T1.status 
                    FROM PLEX_MATRIX_POSITION T1
                        LEFT JOIN CTE ON T1.id = CTE.[position]
                    WHERE T1.status = 1"""
        position = pd.read_sql(query, cnnx)
        
        query = f"""SELECT id, name FROM JDT_USER_DETAILS WHERE position = 'Líder de Processos Operacionais' """
        boss = pd.read_sql(query, cnnx).astype(str)


    return render_template('factoryRegister.matrix/matrix_workers.html'
                            , users=users.to_dict(orient='records')
                            , position=position.to_dict(orient='records')
                            , boss=boss.to_dict(orient='records'))

@factoryRegister_matrix_bp.route('/matriz/operadores', methods=['POST'])
@matrix.require(403)
def matrix_workers_post():

    payload = request.get_json()
        
    engine = get_engine('jdt')
    with engine.connect() as cnnx: 

        try:
            if request.args['type'] == 'new':

                query = f"""INSERT INTO PLEX_MATRIX_USER VALUES (
                                '2300{payload['id']}', '{payload['bossId']}', '{payload['name']}', {payload['shift']}, '{payload['position']}', {payload['status']}
                            )"""
                
            elif request.args['type'] == 'old':

                query = f"""UPDATE PLEX_MATRIX_USER SET
                                bossId = '{payload['bossId']}',
                                name = '{payload['name']}',
                                shift = {payload['shift']},
                                status = {payload['status']},
                                position = '{payload['position']}'
                            WHERE id = '2300{payload['id']}'"""
                
            elif request.args['type'] == 'position':

                query = f"""INSERT INTO PLEX_MATRIX_POSITION VALUES (
                                '{payload['name']}', 1
                            )"""
            
            else:

                query = f"""UPDATE PLEX_MATRIX_POSITION SET
                                status = {payload['status']}
                            WHERE id = {payload['id']}"""
  
            cnnx.execute(text(query))
            cnnx.commit()

            query = f"""SELECT 
                        T1.id,
                        T1.bossId,
                        T3.name AS bossName,
                        T1.name,
                        T1.shift,
                        T1.position as positionId,
                        T2.name AS positionName,
                        T1.status                           

                    FROM PLEX_MATRIX_USER T1 
                    JOIN PLEX_MATRIX_POSITION T2 ON T1.position = T2.id
                    JOIN JDT_USER_DETAILS T3 ON T1.bossId = T3.id"""
            users = pd.read_sql(query, cnnx)
            users['id'] = users['id'].str[4:]

            query = f"""
                    WITH CTE AS (
                        SELECT 
                            [position],
                            COUNT(*) AS qtt
                        FROM PLEX_MATRIX_USER
                        GROUP BY [position]
                    )

                    SELECT 
                        T1.id,
                        T1.name,
                        COALESCE(CTE.qtt, 0) AS qtt,
                        T1.status 
                    FROM PLEX_MATRIX_POSITION T1
                        LEFT JOIN CTE ON T1.id = CTE.[position]"""
            position = pd.read_sql(query, cnnx)

            return jsonify({
                "users": users.to_dict(orient='records'),
                "position": position.to_dict(orient='records')
            }), 200
        
        except IntegrityError as e:
            if hasattr(e.orig, 'args') and e.orig.args and '2627' in str(e.orig.args):
                return jsonify({"error": "Este registro já foi inserido."}), 409
            else:
                return jsonify({"error": "Erro de integridade no banco de dados."}), 400
        
        except SQLAlchemyError as e:
            return jsonify({"error": str(e)}), 500

@factoryRegister_matrix_bp.route('/matriz/painel', methods=['GET'])
@general.require(403)
def matrix_panel_get():

    workcenters = getPlex('workcenters')

    engine = get_engine('jdt')
    with engine.connect() as cnnx: 

        query = f"""SELECT * FROM PLEX_MATRIX_VERSATILITY"""
        versatility = pd.read_sql(query, cnnx)

        query = f"""SELECT * FROM PLEX_MATRIX_USER"""
        users = pd.read_sql(query, cnnx)

        query = f"""SELECT 
                        T1.*,
                        T2.name AS operationName
                    FROM PLEX_MATRIX_PROCESS T1
                        JOIN PLEX_MATRIX_OPERATION T2 ON T1.operation = T2.id
                    ORDER by T1.workcenter, T1.operation, T1.[order] ASC"""
        process = pd.read_sql(query, cnnx)

        query = f"""SELECT * FROM PLEX_MATRIX_WORKCENTER"""
        matrix_workcenters = pd.read_sql(query, cnnx)

    workcenters = pd.merge(left=matrix_workcenters, right=workcenters, how='left', left_on='id', right_on='Workcenter_Key')

    admin = '0'
    if current_user.admin or matrix.can():
        admin = '1'

    return render_template('factoryRegister.matrix/matrix_panel.html', admin=admin
                        , versatility=versatility.to_dict(orient='records')
                        , users=users.to_dict(orient='records')
                        , process=process.to_dict(orient='records')
                        , workcenters=workcenters.to_dict(orient='records'))

@factoryRegister_matrix_bp.route('/matriz/painel', methods=['POST'])
@matrix.require(403)
def matrix_panel_post():

    payload = request.get_json()

    engine = get_engine('jdt')
    with engine.connect() as cnnx: 

        try:

            if payload['status'] == 0:
                query = f"""DELETE FROM PLEX_MATRIX_VERSATILITY 
                            WHERE 
                                [user] = '{payload['user']}' 
                                AND workcenter = {payload['workcenter']} 
                                AND [operation] = {payload['operation']}"""
            
            elif payload['status'] == 1:
                query = f"""INSERT INTO PLEX_MATRIX_VERSATILITY VALUES (
                                {payload['workcenter']}, {payload['operation']}, '{payload['user']}', {payload['status']}
                            )"""
            
            else:
                query = f"""UPDATE PLEX_MATRIX_VERSATILITY SET 
                                [status] = {payload['status']}
                                WHERE 
                                [user] = '{payload['user']}' 
                                AND workcenter = {payload['workcenter']} 
                                AND [operation] = {payload['operation']}"""

            cnnx.execute(text(query))
            cnnx.commit()

            return 'COMMITED', 200
        
        except IntegrityError as e:
            if hasattr(e.orig, 'args') and e.orig.args and '2627' in str(e.orig.args):
                return jsonify({"error": "Este registro já foi inserido."}), 409
            else:
                return jsonify({"error": "Erro de integridade no banco de dados."}), 400
        
        except SQLAlchemyError as e:
            return jsonify({"error": str(e)}), 500
