"""
    FactoryRegisterDefault
    Rotas e métodos para cadastro de metas, fatores, auditorias 5S e exportação de dados.

    Métodos
    -------
    registerDefault_goal_get()
        Exibe página de metas cadastradas, mesclando dados do banco e workcenters.
    registerDefault_goal_post()
        Realiza cadastro, atualização ou exclusão de metas, com logs e tratamento de erros.
    registerDefault_factor_get()
        Exibe página de fatores cadastrados, mesclando dados do banco e workcenters.
    registerDefault_factor_post()
        Realiza cadastro, atualização ou exclusão de fatores, com logs e tratamento de erros.
    registerDefault_5s_get()
        Exibe página de auditorias 5S, mesclando dados do banco e workcenters.
    registerDefault_5s_post()
        Realiza cadastro, atualização ou exclusão de auditorias 5S e grades, com logs e tratamento de erros.
    registerDefault_to_excel(types)
        Exporta dados de cadastros para Excel conforme tipo selecionado.
        
    Notas
    -----
    - Todas as rotas exigem autenticação e permissões específicas.
    - Utiliza SQLAlchemy para acesso ao banco.
    - Funções auxiliares internas iniciam com '_'.
    - Dados retornados são preparados para visualização, cadastro e exportação.
"""

import os
import pandas as pd

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from flask import Blueprint, abort, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from app.utils.db_utils import get_engine
from app.utils.permissions import get_permission
from app.utils.dynamic_constants import getPlex
from app.utils.security_utils import update_logs
from app.utils.teams_utils import send_system_teams_alert

process = get_permission('PROCESS')

factoryRegister_default_bp = Blueprint('factoryRegister_default', __name__)

@factoryRegister_default_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
        
    if not get_permission('GENERAL').can():
        return abort(403)

@factoryRegister_default_bp.route('/cadastros/metas', methods=['GET'])
def registerDefault_goal_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT * FROM PLEX_REGISTER_GOAL"""
        data = pd.read_sql(query, cnnx)
    
    workcenters = getPlex('workcenters')
    data = pd.merge(left=data, right=workcenters, left_on="workcenter", right_on="Workcenter_Key")

    admin = "0"
    if process.can():
        admin = "1"

    return render_template(f'factoryRegister.default/default_goal.html', data=data.to_dict(orient='records'), workcenters=workcenters.to_dict(orient='records'), admin=admin)

@factoryRegister_default_bp.route('/cadastros/metas', methods=['POST'])
@process.require()
def registerDefault_goal_post():

    payload = request.get_json()

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        if request.args['type'] == 'new':

            query = f"""INSERT INTO PLEX_REGISTER_GOAL VALUES (
                            {payload['workcenter']}, 
                            {payload['goal1']}, 
                            {payload['goal2']}, 
                            {payload['goal3']}, 
                            {payload['goalExtra']})"""

            try:
                cnnx.execute(text(query))
                update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', payload['workcenter'], "", "", "new", "goal")

            except IntegrityError as e:
                if hasattr(e.orig, 'args') and e.orig.args and '2627' in str(e.orig.args):
                    return jsonify({"error": "Chave primária duplicada."}), 409
                else:
                    return jsonify({"error": "Erro de integridade no banco de dados."}), 400

            except SQLAlchemyError as e:
                send_system_teams_alert(f'Cadastro de Metas - CT', e, current_user.name)
                return jsonify({"error": str(e)}), 500
                        
        elif request.args['type'] == 'old':

            query = f"""SELECT * FROM PLEX_REGISTER_GOAL WHERE workcenter = '{payload['workcenter']}'"""
            data_to_compare = pd.read_sql(query, cnnx)
            data_to_compare = data_to_compare.applymap(lambda x: int(x) if isinstance(x, float) and x.is_integer() else x).fillna("").astype(str)

            query = f"""UPDATE PLEX_REGISTER_GOAL SET 
                            goal1 = '{payload['goal1']}',
                            goal2 = '{payload['goal2']}',
                            goal3 = '{payload['goal3']}',
                            goalExtra = '{payload['goalExtra']}'

                        WHERE workcenter = '{payload['workcenter']}'"""
                
            cnnx.execute(text(query))

            for key, value in payload.items():
                if data_to_compare[key][0] != str(value):
                    update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', payload['workcenter'], data_to_compare[key][0], str(value), key, f"goal")
                
        else:

            query = f"""DELETE FROM PLEX_REGISTER_GOAL WHERE workcenter = {payload['workcenter']}"""
            cnnx.execute(text(query))
            update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', payload['workcenter'], "", "", "delete", "goal")

        cnnx.commit()

    return 'COMMITED'


@factoryRegister_default_bp.route('/cadastros/fatores', methods=['GET'])
def registerDefault_factor_get():

    engine = get_engine('plex')
    with engine.connect() as cnnx:

        query = f"""SELECT * FROM Mach_2_Multiple_Factor"""
        data = pd.read_sql(query, cnnx)

    workcenters = getPlex('workcenters')
    data = pd.merge(left=data, right=workcenters, left_on="workcenter", right_on="Workcenter_Code")

    admin = "0"
    if process.can():
        admin = "1"
    
    return render_template(f'factoryRegister.default/default_factor.html', data=data.to_dict(orient='records'), workcenters=workcenters.to_dict(orient='records'), admin=admin)

@factoryRegister_default_bp.route('/cadastros/fatores', methods=['POST'])
@process.require()
def registerDefault_factor_post():

    payload = request.get_json()

    engine = get_engine('plex')
    with engine.connect() as cnnx:

        if request.args['type'] == 'new':

            query = f"""INSERT INTO Mach_2_Multiple_Factor VALUES (
                            '{payload['workcenter']}', 
                            '{payload['material']}', 
                            {payload['signals']}, 
                            {payload['pieces']})"""
    
            try:
                cnnx.execute(text(query))
                update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{payload['workcenter']}-{payload['material']}", "", "", "new", "factor")

            except IntegrityError as e:
                if hasattr(e.orig, 'args') and e.orig.args and '2627' in str(e.orig.args):
                    return jsonify({"error": "Ja existe fator cadastrado para este centro e material."}), 409
                else:
                    return jsonify({"error": "Erro de integridade no banco de dados."}), 400

            except SQLAlchemyError as e:
                send_system_teams_alert(f'Cadastro de Fatores', e, current_user.name)
                return jsonify({"error": str(e)}), 500
                        
        elif request.args['type'] == 'old':

            query = f"""SELECT * FROM Mach_2_Multiple_Factor WHERE workcenter = '{payload['workcenter']}' AND part_no = '{payload['material']}'"""
            data_to_compare = pd.read_sql(query, cnnx)
            data_to_compare = data_to_compare.applymap(lambda x: int(x) if isinstance(x, float) and x.is_integer() else x).fillna("").astype(str)

            query = f"""UPDATE Mach_2_Multiple_Factor SET 
                            signals = '{payload['signals']}',
                            parts_produced = '{payload['pieces']}'

                        WHERE workcenter = '{payload['workcenter']}' AND part_no = '{payload['material']}'"""
                
            cnnx.execute(text(query))

            if data_to_compare["signals"][0] != str(payload["signals"]):
                update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{payload['workcenter']}-{payload['material']}", data_to_compare["signals"][0], str(payload["signals"]), "signals", f"factor")
            
            if data_to_compare["parts_produced"][0] != str(payload["pieces"]):
                update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{payload['workcenter']}-{payload['material']}", data_to_compare["parts_produced"][0], str(payload["pieces"]), "parts_produced", f"factor")
            
        else:

            query = f"""DELETE FROM Mach_2_Multiple_Factor WHERE workcenter = '{payload['workcenter']}' AND part_no = '{payload['material']}'"""
            cnnx.execute(text(query))
            update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{payload['workcenter']}-{payload['material']}", "", "", "delete", "factor")

        cnnx.commit()

    return 'COMMITED'


@factoryRegister_default_bp.route('/cadastros/5s', methods=['GET'])
def registerDefault_5s_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT * FROM JDT_REGISTER_5S_PLACE"""
        data_place = pd.read_sql(query, cnnx)
        
        workcenters = getPlex('workcenters')
        data_place = pd.merge(left=data_place, right=workcenters, left_on="place", right_on="Workcenter_Code", how="left").replace({pd.NA: None, float('nan'): None})
        
        query = f"""SELECT * FROM JDT_REGISTER_5S_AUDIT ORDER BY id DESC"""
        data_audit = pd.read_sql(query, cnnx)

        query = f"""SELECT * FROM JDT_REGISTER_5S_GRADE"""
        data_grade = pd.read_sql(query, cnnx)

    admin = "0"
    if current_user.areaId == 5 or current_user.admin:
        admin = "1"

    return render_template(f'factoryRegister.default/default_5s.html', admin=admin, 
                                data_place=data_place.to_dict(orient='records'), 
                                data_audit=data_audit.to_dict(orient='records'), 
                                data_grade=data_grade.to_dict(orient='records'), 
                                workcenters=workcenters.to_dict(orient='records'))

@factoryRegister_default_bp.route('/cadastros/5s', methods=['POST'])
def registerDefault_5s_post():

    if current_user.areaId != 5 and not current_user.admin:
        return jsonify({"error": "Acesso negado!"}), 403

    payload = request.get_json()

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        if request.args['type'] == 'place':

            if request.args['func'] == 'new':

                query = f"""INSERT INTO JDT_REGISTER_5S_PLACE VALUES (
                                '{payload['workcenter']}' 
                                , '{payload['industrial']}'
                                , GETDATE()
                                , '{current_user.id}');
                        """
                
                try:
                    cnnx.execute(text(query))
                    new_id = cnnx.execute(text('SELECT SCOPE_IDENTITY();')).fetchone()[0]

                    update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{new_id}", "", "", "new", "5s")

                except IntegrityError as e:
                    if hasattr(e.orig, 'args') and e.orig.args and '2627' in str(e.orig.args):
                        return jsonify({"error": "Ja existe fator cadastrado para este centro e material."}), 409
                    else:
                        return jsonify({"error": "Erro de integridade no banco de dados."}), 400

                except SQLAlchemyError as e:
                    send_system_teams_alert(f'Cadastro de Fatores', e, current_user.name)
                    return jsonify({"error": str(e)}), 500
                            
            elif request.args['func'] == 'edit':

                query = f"""SELECT * FROM JDT_REGISTER_5S_PLACE WHERE id = '{payload['id']}'"""
                data_to_compare = pd.read_sql(query, cnnx)
                data_to_compare = data_to_compare.applymap(lambda x: int(x) if isinstance(x, float) and x.is_integer() else x).fillna("").astype(str)

                query = f"""UPDATE JDT_REGISTER_5S_PLACE SET 
                                place = '{payload['workcenter']}'
                                , industrial = '{payload['industrial']}'
                                , registerDate = GETDATE()
                                , userId = '{current_user.id}'

                            WHERE id = '{payload['id']}'"""
                    
                cnnx.execute(text(query))

                if str(data_to_compare["place"][0]) != str(payload["workcenter"]):
                    update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{payload['id']}", str(data_to_compare["place"][0]), str(payload["workcenter"]), "workcenter", f"5s")
                
                if int(data_to_compare["industrial"][0] == 'True') != int(payload["industrial"]):
                    update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{payload['id']}", int(data_to_compare["industrial"][0] == 'True'), str(payload["industrial"]), "industrial", f"5s")
                
            else:

                query = f"""DELETE FROM JDT_REGISTER_5S_PLACE WHERE id = '{payload['id']}'"""
                cnnx.execute(text(query))
                update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{payload['id']}", "", "", "delete", "5s")
        
        else:

            if request.args['func'] == 'new':

                query_audit = f"""INSERT INTO JDT_REGISTER_5S_AUDIT VALUES (
                                '{payload['name']}' 
                                , GETDATE()
                                , '{current_user.id}');"""
                
                try:
                    cnnx.execute(text(query_audit))
                    new_id = cnnx.execute(text('SELECT SCOPE_IDENTITY();')).fetchone()[0]

                    update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{new_id}", "", "", "new", "5s")

                    for key, value in payload["grades"].items():
                        
                        query_grades = f"""INSERT INTO JDT_REGISTER_5S_GRADE VALUES (
                                    '{key.split("_")[1]}' 
                                    , '{new_id}'
                                    , '{value}'
                                    , GETDATE()
                                    , '{current_user.id}')"""

                        cnnx.execute(text(query_grades))
                        update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{new_id}-{key.split("_")[1]}", "", "", "new", "5s")
                    
                    cnnx.commit()

                except IntegrityError as e:
                    if hasattr(e.orig, 'args') and e.orig.args and '2627' in str(e.orig.args):
                        return jsonify({"error": "Ja existe fator cadastrado para este centro e material."}), 409
                    else:
                        return jsonify({"error": "Erro de integridade no banco de dados."}), 400

                except SQLAlchemyError as e:
                    send_system_teams_alert(f'Cadastro de Fatores', e, current_user.name)
                    return jsonify({"error": str(e)}), 500
                            
            elif request.args['func'] == 'edit':

                try:

                    for key, value in payload["grades"].items():

                        query = f"""SELECT grade FROM JDT_REGISTER_5S_GRADE WHERE placeId = '{key.split("_")[1]}' and auditId = '{payload['id']}'"""
                        data_to_compare = pd.read_sql(query, cnnx)

                        if not data_to_compare.empty:

                            data_to_compare = data_to_compare.applymap(lambda x: int(x) if isinstance(x, float) and x.is_integer() else x).fillna("").astype(str)

                            if str(data_to_compare["grade"][0]) != str(value):
                                update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{key.split("_")[1]}-{payload['id']}", str(data_to_compare["grade"][0]), str(value), "grade", f"5s")

                                query = f"""UPDATE JDT_REGISTER_5S_GRADE SET 
                                                grade = '{value}'
                                                , registerDate = GETDATE()
                                                , userId = '{current_user.id}'

                                            WHERE placeId = '{key.split("_")[1]}' and auditId = '{payload['id']}'"""
                                cnnx.execute(text(query))

                        else:

                            query = f"""INSERT INTO JDT_REGISTER_5S_GRADE VALUES (
                                        '{key.split("_")[1]}' 
                                        , '{payload['id']}'
                                        , '{value}'
                                        , GETDATE()
                                        , '{current_user.id}')"""
                            
                            cnnx.execute(text(query))
                            update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{key.split("_")[1]}-{payload['id']}", "", value, "grade", "5s")
                    
                except IntegrityError as e:
                    if hasattr(e.orig, 'args') and e.orig.args and '2627' in str(e.orig.args):
                        return jsonify({"error": "Ja existe fator cadastrado para este centro e material."}), 409
                    else:
                        return jsonify({"error": "Erro de integridade no banco de dados."}), 400

                except SQLAlchemyError as e:
                    send_system_teams_alert(f'Cadastro de Fatores', e, current_user.name)
                    return jsonify({"error": str(e)}), 500
                    
            else:

                query = f"""DELETE FROM JDT_REGISTER_5S_AUDIT WHERE id = '{payload['id']}'"""
                cnnx.execute(text(query))
                update_logs('jdt', current_user.id, 'JDT_FAC_LOGS', f"{payload['id']}", "", "", "delete", "5s")

        cnnx.commit()

        return 'COMMITED'

@factoryRegister_default_bp.route('/cadastros/excel/<string:types>', methods=['POST'])
def registerDefault_to_excel(types):

    path = fr'{os.getcwd()}\app\static\uploads\default'
    excel_filename = f'{path}\cadastros.xlsx'
    if os.path.exists(excel_filename):
        os.remove(excel_filename)

    if types == 'metas':

        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            query = f"""SELECT 
                        workcenter
                        ,goal1 AS 'Turno 1'
                        ,goal2 AS 'Turno 2'
                        ,goal3 AS 'Turno 3'
                        ,goalExtra AS 'Hora Extra'

                        FROM 
                            PLEX_REGISTER_GOAL"""
            data = pd.read_sql(query, cnnx)

        workcenters = getPlex('workcenters')[["Name", "Workcenter_Key", "Workcenter_Group"]]
        data = pd.merge(left=data, right=workcenters, left_on="workcenter", right_on="Workcenter_Key").rename(columns={"Name" : "Centro de Trabalho", "Workcenter_Group": "Grupo"}).drop(columns=["workcenter", "Workcenter_Key"])

    elif types == "fatores":

        engine = get_engine('plex')
        with engine.connect() as cnnx:
            query = f"""SELECT 
                        workcenter
                        , part_no AS 'MATERIAL'
                        , signals AS 'QTD. Sinais de Coleta'
                        , parts_produced AS 'QTD. Peças Produzidas'

                        FROM 
                            Mach_2_Multiple_Factor"""
            data = pd.read_sql(query, cnnx)

        workcenters = getPlex('workcenters')[["Name", "Workcenter_Code", "Workcenter_Group"]]
        data = pd.merge(left=data, right=workcenters, left_on="workcenter", right_on="Workcenter_Code").rename(columns={"Name" : "Centro de Trabalho", "Workcenter_Group": "Grupo", "Workcenter_Code" : "Código"}).drop(columns=["workcenter"])

    elif types == "5s":

        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            query = f"""SELECT 
                        T1.grade AS Nota
                        , T2.place AS 'Centro de Trabalho'
                        , CASE WHEN T2.industrial = 1 THEN 'Sim' ELSE 'Não' END AS 'TV OEE'
                        , T3.name AS 'Auditoria'
                FROM JDT_REGISTER_5S_GRADE T1
                JOIN JDT_REGISTER_5S_PLACE T2 ON T1.placeId = T2.id
                JOIN JDT_REGISTER_5S_AUDIT T3 ON T1.auditId = T3.id
            """
            data = pd.read_sql(query, cnnx)

    data.to_excel(excel_filename, index=False, header=True)
    return send_file(excel_filename, as_attachment=True)
