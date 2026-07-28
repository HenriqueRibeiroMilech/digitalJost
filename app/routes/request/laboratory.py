from datetime import datetime, timedelta
from tkinter import END
import traceback
import pandas as pd
import json
import os

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import text, exc

from flask import Blueprint, abort, jsonify, render_template, request, redirect, send_file, url_for
from flask_login import current_user
from flask_mail import Message

from app.utils.constants import APP_PATH, COORD, LEADER
from app.utils.db_utils import engine_run_query, get_engine
from app.utils.files_utils import print_label
from app.utils.permissions import get_permission, user_has_role
from app.config import mail


_AREA_NOT_REQUIRED_ROUTES = [
    'request_laboratory.laboratory_get'
    , 'request_laboratory.laboratory_motives_get'
    , 'request_laboratory.laboratory_motives_post'
    , 'request_laboratory.laboratory_search_get'
    , 'request_laboratory.laboratory_search_post'
]

_AREAS = {'dimensional': 1, 'material': 2}

_FAMILIES = sorted([
    'Aparelho de Levantamento', 'Articulação de Ônibus', 'CH', 'Engate Automático',
    'Engate Container', 'Engate Esférico', 'Hubodometro', 'Porta Estepe', 'Pino Rei', 'Quinta Roda',
    'Suspensor de Cabine', 'Rala', 'Roda de Alumínio', 'Suspensor Pneumárico', 'Veículo Trator'
])


p_laboratory = get_permission('LABORATORY')

request_laboratory_bp = Blueprint('request_laboratory', __name__)

@request_laboratory_bp.before_request
def route_auth():
    # Verifica se o usuário está autenticado
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))

    # Verifica permissão geral
    if not get_permission('GENERAL').can():
        return abort(403)
    
    # Verifica se a rota exige área e se ela é válida
    endpoint = request.endpoint

    if endpoint not in _AREA_NOT_REQUIRED_ROUTES:
        area = None
        # Tenta pegar de args (query string)
        if 'area' in request.args:
            area = request.args.get('area')
        # Se não veio, tenta pegar de view_args (URL)
        elif request.view_args and 'area' in request.view_args:
            area = request.view_args.get('area')

        if area == 'experimental':
            return render_template('general_development.html')

        if not area or area not in _AREAS:
            return abort(400, description='Área inválida ou não informada')



# ========================================
# HELPERS
# ========================================

# Atualizar logs
def _UPDATE_LOGS(requestId, old, new, extra, cnnx=None):

    extra = f"'{extra}'" if extra is not None else 'NULL'
    old = "'" + str(old) + "'" if str(old) != 'None' else 'NULL'
    new = "'" + str(new) + "'" if str(new) != 'None' else 'NULL'

    query = f"""INSERT INTO JDT_REQUEST_LAB_LOGS VALUES ('{requestId}', '{current_user.id}', {old}, {new}, {extra}, GETDATE())"""

    if not cnnx:
        engine = get_engine('jdt')
        with engine.begin() as cnnx:
            cnnx.execute(text(query))
    else:
        cnnx.execute(text(query))

# Converter dias da semana
def parse_days_of_week(days_str):
    """
    Converte string de dias em lista legível.
    
    Args:
        days_str: '0,1,2,3,4' ou '*' ou None
    
    Returns:
        Lista de nomes de dias: ['Segunda', 'Terça', ...]
    """
    if not days_str or days_str == '*':
        return ['Todos os dias']
    
    day_names = {
        '0': 'Segunda',
        '1': 'Terça',
        '2': 'Quarta',
        '3': 'Quinta',
        '4': 'Sexta',
        '5': 'Sábado',
        '6': 'Domingo'
    }
    
    days = [d.strip() for d in days_str.split(',')]
    return [day_names.get(d, d) for d in days]



# ========================================
# PÁGINAS GERAIS
# ========================================

@request_laboratory_bp.route('/lab', methods=['GET'])
def laboratory_get():
    # Obter estatísticas de SSLs do usuário atual
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        # Consulta para obter contagem de SSLs por status
        query = f"""
            SELECT 
                status,
                COUNT(*) as count
            FROM 
                JDT_REQUEST_LAB
            WHERE 
                requesterId = :user_id
            GROUP BY 
                status
        """
        stats_df = pd.read_sql(text(query), cnnx, params={'user_id': current_user.id})
        
        # Inicializar dicionário de estatísticas
        stats = {
            'total': 0,
            'status_0': 0,
            'status_1': 0,
            'status_2': 0,
            'status_3': 0,
            'status_4': 0,
            'status_5': 0
        }
        
        # Preencher contagens de status
        total = 0
        for _, row in stats_df.iterrows():
            status = int(row['status'])
            count = int(row['count'])
            stats[f'status_{status}'] = count
            total += count
        
        stats['total'] = total

    return render_template('request.laboratory/default.html', stats=stats)

@request_laboratory_bp.route('/lab/motivos', methods=['GET'])
@p_laboratory.require(403)
def laboratory_motives_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = """SELECT * FROM JDT_REQUEST_LAB_AREAS"""
        areas = pd.read_sql(query, cnnx)

        query = """SELECT * FROM JDT_REQUEST_LAB_MOTIVES"""
        motives = pd.read_sql(query, cnnx)

        query = """SELECT * FROM JDT_REQUEST_LAB_MOTIVES_AREA"""
        motives_area = pd.read_sql(query, cnnx)
        
        # Adicionar contador de SSLs para cada relação motivo-área
        relations_with_count = []
        for index, relation in motives_area.iterrows():
            # Contar quantas SSLs usam esta relação
            count_query = """
                SELECT COUNT(*) as count FROM JDT_REQUEST_LAB 
                WHERE motive = :motive_id AND areaId = :area_id
            """
            count_result = pd.read_sql(text(count_query), cnnx, params={
                'motive_id': relation['motiveId'],
                'area_id': relation['areaId']
            })
            
            relation_dict = relation.to_dict()
            relation_dict['ssl_count'] = int(count_result['count'][0])
            relations_with_count.append(relation_dict)
    
    return render_template(
        'request.laboratory/motives.html'
        , areas=areas.to_dict(orient='records')
        , motives=motives.to_dict(orient='records')
        , motives_area=relations_with_count
    )

@request_laboratory_bp.route('/lab/motivos', methods=['POST'])
@p_laboratory.require(403)
def laboratory_motives_post():
    data = request.get_json()
    action = data.get('action')
    
    try:
        engine = get_engine('jdt')
        
        if action == 'create_motive':
            name = data.get('name')
            if not name:
                return jsonify({"error": "Nome do motivo é obrigatório"}), 400
                
            with engine.begin() as cnnx:
                # Inserir na tabela de motivos
                query = "INSERT INTO JDT_REQUEST_LAB_MOTIVES (name) VALUES (:name); SELECT SCOPE_IDENTITY() AS id;"
                result = cnnx.execute(text(query), {'name': name})
                
                # Obter o ID gerado
                new_id = result.fetchone()[0]
                
                return jsonify({"id": new_id, "message": "Motivo criado com sucesso"})
                
        elif action == 'create_relation':
            motive_id = data.get('motiveId')
            area_id = data.get('areaId')
            active = data.get('active', '1')
            
            if not motive_id or not area_id:
                return jsonify({"error": "Motivo e área são obrigatórios"}), 400
                
            with engine.begin() as cnnx:
                # Verificar se a relação já existe
                check_query = """
                    SELECT COUNT(*) as count FROM JDT_REQUEST_LAB_MOTIVES_AREA 
                    WHERE motiveId = :motive_id AND areaId = :area_id
                """
                result = pd.read_sql(text(check_query), cnnx, params={
                    'motive_id': motive_id,
                    'area_id': area_id
                })
                
                if result['count'][0] > 0:
                    return jsonify({"error": "Esta relação já existe"}), 400
                
                # Inserir na tabela de relações
                insert_query = """
                    INSERT INTO JDT_REQUEST_LAB_MOTIVES_AREA (motiveId, areaId, active)
                    VALUES (:motive_id, :area_id, :active)
                """
                cnnx.execute(text(insert_query), {
                    'motive_id': motive_id,
                    'area_id': area_id,
                    'active': active
                })
                
                return jsonify({"message": "Relação criada com sucesso"})
                
        elif action == 'update_relation':
            motive_id = data.get('motiveId')
            area_id = data.get('areaId')
            active = data.get('active')
            
            if not motive_id or not area_id or active is None:
                return jsonify({"error": "Todos os campos são obrigatórios"}), 400
                
            with engine.begin() as cnnx:
                # Atualizar o status da relação
                update_query = """
                    UPDATE JDT_REQUEST_LAB_MOTIVES_AREA
                    SET active = :active
                    WHERE motiveId = :motive_id AND areaId = :area_id
                """
                cnnx.execute(text(update_query), {
                    'motive_id': motive_id,
                    'area_id': area_id,
                    'active': active
                })
                
                return jsonify({"message": "Relação atualizada com sucesso"})
        
        elif action == 'delete_relation':
            motive_id = data.get('motiveId')
            area_id = data.get('areaId')
            
            if not motive_id or not area_id:
                return jsonify({"error": "Motivo e área são obrigatórios"}), 400
                
            with engine.begin() as cnnx:
                # Verificar se existem SSLs usando esta relação
                check_query = """
                    SELECT COUNT(*) as count FROM JDT_REQUEST_LAB 
                    WHERE motive = :motive_id AND areaId = :area_id
                """
                result = pd.read_sql(text(check_query), cnnx, params={
                    'motive_id': motive_id,
                    'area_id': area_id
                })
                
                if result['count'][0] > 0:
                    return jsonify({"error": "Não é possível excluir uma relação que está sendo utilizada por solicitações"}), 400
                
                # Excluir a relação
                delete_query = """
                    DELETE FROM JDT_REQUEST_LAB_MOTIVES_AREA
                    WHERE motiveId = :motive_id AND areaId = :area_id
                """
                cnnx.execute(text(delete_query), {
                    'motive_id': motive_id,
                    'area_id': area_id
                })
                
                return jsonify({"message": "Relação excluída com sucesso"})
        
        elif action == 'delete_motive':
            motive_id = data.get('motiveId')
            
            if not motive_id:
                return jsonify({"error": "ID do motivo é obrigatório"}), 400
                
            with engine.begin() as cnnx:
                # Verificar se o motivo tem áreas relacionadas
                check_query = """
                    SELECT COUNT(*) as count FROM JDT_REQUEST_LAB_MOTIVES_AREA 
                    WHERE motiveId = :motive_id
                """
                result = pd.read_sql(text(check_query), cnnx, params={'motive_id': motive_id})
                
                if result['count'][0] > 0:
                    return jsonify({"error": "Não é possível excluir um motivo que possui áreas relacionadas"}), 400
                
                # Verificar se o motivo está sendo usado em alguma solicitação
                check_ssl_query = """
                    SELECT COUNT(*) as count FROM JDT_REQUEST_LAB 
                    WHERE motive = :motive_id
                """
                result = pd.read_sql(text(check_ssl_query), cnnx, params={'motive_id': motive_id})
                
                if result['count'][0] > 0:
                    return jsonify({"error": "Não é possível excluir um motivo que está sendo usado em solicitações"}), 400
                
                # Excluir o motivo
                delete_query = """
                    DELETE FROM JDT_REQUEST_LAB_MOTIVES WHERE id = :motive_id
                """
                cnnx.execute(text(delete_query), {'motive_id': motive_id})
                
                return jsonify({"message": "Motivo excluído com sucesso"})
        
        else:
            return jsonify({"error": "Ação inválida"}), 400
            
    except Exception as e:
        print(f"Erro ao processar solicitação: {str(e)}", flush=True)
        return jsonify({"error": f"Erro ao processar solicitação: {str(e)}"}), 500

@request_laboratory_bp.route('/lab/consultar', methods=['GET'])
def laboratory_search_get():

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT 
                        DISTINCT T1.requesterId, T2.name
                    FROM
                        JDT_REQUEST_LAB AS T1
                        JOIN JDT_USER_DETAILS AS T2 ON T1.requesterId = T2.id
                    ORDER BY T2.name"""
        requesters = pd.read_sql(text(query), cnnx)

        query = f"""SELECT 
                        COALESCE(SUM(CASE WHEN status = 3 THEN 1 ELSE NULL END), 0) AS status 
                    FROM JDT_REQUEST_LAB 
                    WHERE requesterId = :requesterId"""
        userBlocked = pd.read_sql(text(query), cnnx, params={'requesterId': current_user.id})

        query = f"""SELECT * FROM JDT_REQUEST_LAB_MOTIVES"""
        motives = pd.read_sql(text(query), cnnx)

        query = f"""SELECT * FROM JDT_REQUEST_LAB_AREAS"""
        areas = pd.read_sql(text(query), cnnx)

        query = f"""SELECT * FROM JDT_REQUEST_LAB_STATUS"""
        status = pd.read_sql(text(query), cnnx)


    filter_2 = datetime.now().date()
    filter_1 = filter_2 - timedelta(weeks=36)

    admin = '0'
    if p_laboratory.can():
        admin = '1'

    preload = {}
    if 'preload' in request.args:
        preload['area'] = request.args['preload']
        preload['status'] = request.args.get('status', '')


    return render_template(
        'request.laboratory/search.html'
        , filter_1=filter_1
        , filter_2=filter_2
        , requesters=requesters.to_dict(orient='records')
        , motives=motives.to_dict(orient='records')
        , areas=areas.to_dict(orient='records')
        , status=status.to_dict(orient='records')
        , userBlocked=userBlocked['status'][0]
        , preload=preload
        , admin=admin
    )

@request_laboratory_bp.route('/lab/consultar', methods=['POST'])
def laboratory_search_post():

    payload = request.get_json()

    payload['filter_1'] = payload['filter_1'] + ' 00:00:00.000'
    payload['filter_2'] = payload['filter_2'] + ' 23:59:59.999'

    query = f"""SELECT 
                    requestId
                    , T2.name
                    , materId
                    , descText
                    , T5.name AS motive
                    , T1.motive AS motiveId
                    , FORMAT(deadLine, 'dd/MM/yyyy') AS deadline
                    , T1.status AS statusId
                    , T4.name AS statusName
                    , T1.areaId
                    , T3.name AS areaName
                FROM 
                    JDT_REQUEST_LAB AS T1
                    LEFT JOIN JDT_USER_DETAILS AS T2 ON T1.requesterId = T2.id
                    JOIN JDT_REQUEST_LAB_AREAS AS T3 ON T1.areaId = T3.id
                    JOIN JDT_REQUEST_LAB_STATUS AS T4 ON T1.status = T4.id
                    JOIN JDT_REQUEST_LAB_MOTIVES AS T5 ON T1.motive = T5.id

                WHERE T1.openDate BETWEEN :filter_1 AND :filter_2

                ORDER BY requestId DESC"""
    data = engine_run_query(query, 'jdt', params={'filter_1': payload['filter_1'], 'filter_2': payload['filter_2']})

    if request.args.get('type', '') == 'excel':

        data = data.drop(columns=['areaId', 'motiveId', 'areaName', 'statusId'])
        data = data.rename(
                columns={
                    'requestId': 'ID da Solicitação'
                    , 'name': 'Solicitante'
                    , 'materId': 'Código do Material'
                    , 'motive': 'Motivo da Solicitação'
                    , 'descText': 'Observação'
                    , 'deadline': 'Prazo do Laboratório'
                    , 'statusName': 'Status da Solicitação'
        })

        path = fr'{os.getcwd()}\app\static\uploads\default'
        excel_filename = f'{path}\laboratorio.xlsx'
        if os.path.exists(excel_filename):
            os.remove(excel_filename)
        
        data.to_excel(excel_filename, index=False, header=True)

        return send_file(excel_filename, as_attachment=True)

    return data.to_dict(orient='records')

@request_laboratory_bp.route('/lab/<string:area>/solicitar', methods=['GET'])
def laboratory_form_get(area):

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT T2.* FROM JDT_REQUEST_LAB_MOTIVES_AREA T1 JOIN JDT_REQUEST_LAB_MOTIVES T2 ON T1.motiveId = T2.id WHERE areaId = {_AREAS[area]}"""
        motives = pd.read_sql(text(query), cnnx)

        query = f"""SELECT 
                        COALESCE(SUM(CASE WHEN status = 3 THEN 1 ELSE NULL END), 0) AS status 
                    FROM JDT_REQUEST_LAB 
                    WHERE requesterId = :requesterId"""
        userBlocked = pd.read_sql(text(query), cnnx, params={'requesterId': current_user.id})

    return render_template(
        f'request.laboratory/new_{area}.html'
        , options=_FAMILIES
        , area=area
        , motives=motives.to_dict(orient='records')
        , userBlocked=userBlocked['status'][0]
    )
    
@request_laboratory_bp.route('/lab/<string:area>/solicitar', methods=['POST'])
def laboratory_form_post(area):

    try:

        # Check if user is blocked due to pending requests
        query = f"""SELECT count(*) as count FROM JDT_REQUEST_LAB WHERE requesterId = '{current_user.id}' and status = 3"""
        if engine_run_query(query, 'jdt')['count'][0] > 0:
            return jsonify({
                "status": "error", 
                "message": "Você possui solicitações aguardando retirada."
            }), 403

        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            try:
                # Generate new request ID
                query = f"""SELECT 
                            MAX(requestId) AS id 
                        FROM 
                            JDT_REQUEST_LAB 
                        WHERE LEFT(requestId, 4) = YEAR(GETDATE())"""
                last_id = pd.read_sql(query, cnnx)['id'][0]

                if last_id is None:
                    requestId = int(f'{datetime.now().year}00000') + 1
                else:
                    requestId = int(last_id) + 1
                
                # Create directories for uploads
                base_dir = 'app/static/uploads/lab/' + str(requestId)
                draw_dir = base_dir + '/draw'
                reports_dir = base_dir + '/reports'
                
                try:
                    os.makedirs(draw_dir, exist_ok=True)
                    os.makedirs(reports_dir, exist_ok=True)
                except OSError as e:
                    return jsonify({
                        "status": "error", 
                        "message": f"Erro ao criar diretórios: {str(e)}"
                    }), 500

                # Process file uploads - save to draw directory
                uploaded_files = request.files.getlist("draw_file")
                saved_files = []
                
                if not uploaded_files or all(not f.filename for f in uploaded_files):
                    return jsonify({
                        "status": "error", 
                        "message": "Nenhum arquivo enviado"
                    }), 400
                
                for file in uploaded_files:
                    if file and file.filename:
                        filename = file.filename
                        file_path = os.path.join(draw_dir, filename)
                        
                        # Handle duplicate filenames
                        counter = 1
                        name, ext = os.path.splitext(filename)
                        while os.path.exists(file_path):
                            filename = f"{name}_{counter}{ext}"
                            file_path = os.path.join(draw_dir, filename)
                            counter += 1
                        
                        file.save(file_path)
                        saved_files.append(filename)
                
                # Insert request data into database
                query = f"""INSERT INTO JDT_REQUEST_LAB VALUES ({requestId}, '{current_user.id}',
                            '{_AREAS[area]}', '{request.form['id_mater']}', 
                            '{request.form['id_draw']}', {request.form['qtd']}, '{request.form['supplier']}', 
                            '{request.form['rev']}', '{request.form['id_proj']}', '{request.form['acc_proj']}', 
                            '{request.form['fam']}', '{request.form['desc']}', 
                            '{request.form['obs']}', GETDATE(), NULL, NULL,  NULL, 0, NULL, NULL, 
                            0, NULL, '{request.form['motive']}', 0, 0)"""
                cnnx.execute(text(query))

                if area == 'dimensional':
                    query = f"""INSERT INTO JDT_REQUEST_LAB_DIMENSIONAL VALUES (
                                {requestId}, '{request.form['interest']}')"""
                    cnnx.execute(text(query))
                else:
                    analysys = []
                    for key, value in request.form.items():
                        if 'analysis' in key:
                            analysys.append(value)

                    query = f"""INSERT INTO JDT_REQUEST_LAB_MATERIAL VALUES (
                                {requestId}, '{json.dumps(analysys)}', '{request.form['rule']}')"""
                    cnnx.execute(text(query))

                _UPDATE_LOGS(requestId, None, 0, "status", cnnx)

                cnnx.commit()

                # Send notification email if needed
                if request.form.get('motive') == 'Capabilidade' and request.form.get('logis') == '1':
                    try:
                        msg = Message(f"'Solicitação de SSL concluída - ID {requestId}'",
                                    sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                    recipients=['LPROGRAMACAO@randon.com.br'], cc=[current_user.companyEmail])

                        msg.html = render_template(
                            'request.laboratory/email_capability.html'
                            , requestId=requestId
                            , name=current_user.name
                            , areaName=area)
                        
                        with open(rf'app/static/images/POP0273_R06.docx', 'rb') as f:
                            msg.attach(filename='POP0273_R06.docx',
                            content_type='application/octet-stream',
                            data=f.read())

                        mail.send(msg)
                    except Exception as email_error:
                        print(f"Email sending error: {str(email_error)}")
                        # Continue execution even if email fails

                return jsonify({
                    "status": "success"
                    , "message": "Solicitação criada com sucesso"
                    , "requestId": requestId
                    , "files": saved_files
                }), 201
                
            except Exception as db_error:
                cnnx.rollback()
                print(f"Database error: {str(db_error)}", flush=True)
                return jsonify({
                    "status": "error",
                    "message": f"Erro ao processar solicitação: {str(db_error)}"
                }), 500
                
    except Exception as e:
        print(f"Unexpected error: {str(e)}", flush=True)
        return jsonify({
            "status": "error",
            "message": f"Erro inesperado: {str(e)}"
        }), 500

@request_laboratory_bp.route('/lab/<string:area>/quadro', methods=['GET'])
def laboratory_dash_get(area):

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""
                WITH LastestRequestPause AS (
                    SELECT 
                        requestId
                        , COALESCE(new, 'False') AS paused
                    FROM (
                        SELECT requestId, new, date,
                            ROW_NUMBER() OVER (PARTITION BY requestId ORDER BY date DESC, requestId DESC) AS rn
                        FROM JDT_REQUEST_LAB_LOGS
                        WHERE extra = 'pause'
                    ) t
                    WHERE rn = 1 
                ),
                -- CTE para calcular períodos de pausa
                PauseIntervals AS (
                    SELECT 
                        L.requestId,
                        L.[date] AS pause_start,
                        LEAD(L.[date]) OVER (PARTITION BY L.requestId ORDER BY L.[date]) AS pause_end
                    FROM JDT_REQUEST_LAB_LOGS L
                    WHERE L.extra = 'pause' 
                        AND L.[new] = 'True'
                ),
                -- CTE para períodos de execução (status 2)
                ExecutionPeriods AS (
                    SELECT 
                        L.requestId,
                        L.[date] AS exec_start,
                        LEAD(L.[date]) OVER (PARTITION BY L.requestId ORDER BY L.[date]) AS exec_end,
                        R.status AS current_status
                    FROM JDT_REQUEST_LAB_LOGS L
                    JOIN JDT_REQUEST_LAB R ON L.requestId = R.requestId
                    WHERE L.extra = 'status' 
                        AND L.[new] = '2'
                        AND R.areaId = '{_AREAS[area]}'
                ),
                -- CTE para calcular tempo pausado em cada período de execução (em MINUTOS)
                PauseDurations AS (
                    SELECT 
                        EP.requestId,
                        EP.exec_start,
                        EP.exec_end,
                        EP.current_status,
                        COALESCE(SUM(
                            DATEDIFF(MINUTE, 
                                P.pause_start, 
                                CASE 
                                    WHEN P.pause_end IS NULL AND EP.exec_end IS NULL THEN GETDATE()
                                    WHEN P.pause_end IS NULL THEN EP.exec_end
                                    WHEN EP.exec_end IS NULL THEN P.pause_end
                                    ELSE CASE WHEN P.pause_end < EP.exec_end THEN P.pause_end ELSE EP.exec_end END
                                END
                            )
                        ), 0) AS pause_minutes
                    FROM ExecutionPeriods EP
                    LEFT JOIN PauseIntervals P 
                        ON EP.requestId = P.requestId
                        AND P.pause_start >= EP.exec_start
                        AND (EP.exec_end IS NULL OR P.pause_start < EP.exec_end)
                    GROUP BY EP.requestId, EP.exec_start, EP.exec_end, EP.current_status
                ),
                -- CTE para calcular tempo total em execução EXCLUINDO pausas (em MINUTOS)
                ExecutionTime AS (
                    SELECT 
                        requestId,
                        SUM(
                            CASE 
                                -- Período completo (com próximo evento)
                                WHEN exec_end IS NOT NULL 
                                THEN DATEDIFF(MINUTE, exec_start, exec_end) - pause_minutes
                                
                                -- Período atual (ainda em execução - status 2)
                                WHEN exec_end IS NULL AND current_status = 2
                                THEN DATEDIFF(MINUTE, exec_start, GETDATE()) - pause_minutes
                                
                                -- Outros casos
                                ELSE 0
                            END
                        ) AS total_execution_minutes
                    FROM PauseDurations
                    GROUP BY requestId
                )
        
                SELECT 
                    CAST(FORMAT(T1.deadLine, 'yyyy-MM-dd') AS VARCHAR) AS deadLine
                    , T1.requestId
                    , T4.name as requesterName
                    , T1.descText
                    , T1.drawId
                    , CASE WHEN T3.paused = 'True' THEN 'CONTINUAR' ELSE 'PAUSAR' end AS paused
                    , T1.status
                    , T1.execArea
                    , CAST(FORMAT(T1.initDate, 'yyyy-MM-dd') AS VARCHAR) AS initDate
                    , 0 as timePaused 
                    , T1.prioritize
                    , COALESCE(ET.total_execution_minutes, 0) AS executionTimeMinutes
                FROM 
                    JDT_REQUEST_LAB AS T1
                    LEFT JOIN LastestRequestPause AS T3 ON T1.requestId = T3.requestId 
                    LEFT JOIN JDT_USER_DETAILS AS T4 ON T1.requesterId = T4.id
                    LEFT JOIN ExecutionTime AS ET ON T1.requestId = ET.requestId
                WHERE
                    T1.areaId = '{_AREAS[area]}' AND status <> 4 AND status <> 5

                ORDER BY 
                T1.status
                , T1.prioritize DESC
                , CASE 
                    WHEN T1.status = 1 THEN T1.deadLine 
                    ELSE NULL
                END
                , CASE 
                    WHEN T1.status != 1 THEN T1.requestId 
                    ELSE NULL
                END
            """
        df = pd.read_sql(query, cnnx)

        query = f"""SELECT * FROM JDT_REQUEST_LAB_EQUIPMENTS WHERE area = '{_AREAS[area]}'"""
        exec_types = pd.read_sql(query, cnnx)

    return render_template(
        'request.laboratory/frame.html'
        , dataframe=df.to_dict(orient='records')
        , areaId=_AREAS[area]
        , areaName = area
        , exec_types=exec_types.to_dict(orient='records')
    )



# ========================================
# DETALHES DE SOLICITAÇÕES
# ========================================

@request_laboratory_bp.route('/lab/<string:area>/detalhes/<int:idReq>', methods=['GET'])
def laboratory_detail_get(area, idReq):

    check = 0
    if p_laboratory.can():
        check = 1

    query = f"""SELECT * FROM JDT_REQUEST_LAB_EQUIPMENTS WHERE area = :area"""
    equipments = engine_run_query(query, 'jdt', params={'area': _AREAS[area]})

    return render_template(
        f'request.laboratory/detail_{area}.html'
        , area=area
        , check=check
        , idReq=idReq
        , equipments=equipments.to_dict(orient='records')
    )

@request_laboratory_bp.route('/lab/<string:area>/detalhes/<int:idReq>/dados', methods=['GET'])
def laboratory_detail_data_get(area, idReq):
    
    try:
        # Get basic request information
        if area == 'dimensional':
            join_clause = "JOIN JDT_REQUEST_LAB_DIMENSIONAL T2 ON T1.requestId = T2.requestId"
            specific_field = "T2.interestCotas as interest"
        else:  # material
            join_clause = "JOIN JDT_REQUEST_LAB_MATERIAL T2 ON T1.requestId = T2.requestId"
            specific_field = "T2.analysis, T2.rules"
   
        engine = get_engine('jdt')
        with engine.connect() as conn:
                        
            query = f"""
                SELECT 
                    T1.requestId
                    , T1.requesterId
                    , T5.name as requester
                    , T1.status as statusCode
                    , T3.name as status
                    , T1.materId
                    , T1.drawId
                    , T1.qtd
                    , T1.descText
                    , T1.supplier
                    , T1.revId
                    , T1.projId
                    , T1.accProj
                    , T1.execArea
                    , FORMAT(T1.deadLine, 'dd/MM/yyyy') as deadline
                    , T1.prodFamily
                    , T1.obsText as obs
                    , T4.name AS motive
                    , T1.motive AS motiveId
                    , T1.prioritize
                    , T1.qualityProblem
                    , {specific_field}
                FROM 
                    JDT_REQUEST_LAB T1
                    {join_clause}
                    JOIN JDT_REQUEST_LAB_STATUS T3 ON T1.status = T3.id
                    JOIN JDT_REQUEST_LAB_MOTIVES T4 ON T1.motive = T4.id
                    JOIN JDT_USER_DETAILS T5 ON T1.requesterId = T5.id

                WHERE 
                    T1.requestId = :requestId
            """
            data = pd.read_sql(text(query), conn, params={"requestId": idReq})
            
            if data.empty:
                return jsonify({"error": "Solicitação não encontrada"}), 404
                
            # Convert to dict and add extra information
            result = data.iloc[0].to_dict()
            
            # Add user permissions info
            result["currentUserId"] = current_user.id
            result["isLabUser"] = user_has_role(current_user.role, "Laboratório") or current_user.admin
            
            return jsonify(result)
    except Exception as e:
        print(f"Error fetching request details: {str(e)}")
        return jsonify({"error": f"Erro ao obter detalhes: {str(e)}"}), 500

@request_laboratory_bp.route('/lab/<string:area>/detalhes/<int:idReq>/etiqueta', methods=['GET'])
def lab_download_ticket_get(area, idReq):
    excel_file = print_label(idReq)
    caminho = rf'{os.getcwd()}\app\static\uploads\default'
    return send_file(rf'{caminho}\{excel_file}', as_attachment=True)

@request_laboratory_bp.route('/lab/<string:area>/detalhes/<int:idReq>/arquivos', methods=['GET'])
def laboratory_detail_files_get(area, idReq):
    """
    Gerencia arquivos anexados a solicitações de laboratório.
    GET: Lista arquivos na pasta especificada
    """
    file_type = request.args.get('type', 'draw')
    if file_type not in ('draw', 'reports'):
        return jsonify({"error": "Tipo inválido"}), 400

    folder = 'draw' if file_type == 'draw' else 'reports'
    base_dir = os.path.join(APP_PATH, 'app', 'static', 'uploads', 'lab', str(idReq), folder)

    # Garantir que o diretório existe
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)

    try:
        files = []
        if os.path.exists(base_dir):
            for file_name in os.listdir(base_dir):
                file_path = os.path.join(base_dir, file_name)
                if os.path.isfile(file_path):
                    files.append({
                        "name": file_name,
                        "size": round(os.path.getsize(file_path) / 1024, 2),  # Tamanho em KB
                        "url": f"/lab/download/image?id={idReq}&arq={folder}/{file_name}"
                    })

        return jsonify(files)
    except Exception as e:
        print(f"Error fetching files: {str(e)}")
        return jsonify({"error": f"Erro ao obter arquivos: {str(e)}"}), 500

@request_laboratory_bp.route('/lab/<string:area>/detalhes/<int:idReq>/arquivos', methods=['POST'])
def laboratory_detail_files_post(area, idReq):
    """
    Gerencia arquivos anexados a solicitações de laboratório.
    POST: Upload, download ou exclusão de arquivos
        - type=download: Para baixar um arquivo específico
        - type=delete: Para excluir um arquivo (requer permissões)
        - (sem type): Para fazer upload de arquivos
    """
    file_type = request.args.get('type', 'draw')
    if file_type not in ('draw', 'reports'):
        return jsonify({"error": "Tipo inválido"}), 400

    folder = 'draw' if file_type == 'draw' else 'reports'
    base_dir = os.path.join(APP_PATH, 'app', 'static', 'uploads', 'lab', str(idReq), folder)

    # Garantir que o diretório existe
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)

    if request.args.get('extra') == 'download':
        data = request.get_json()
        if 'file' not in data:
            return "Nome do arquivo é obrigatório", 400

        file_path = os.path.join(base_dir, data['file'])
        if not os.path.exists(file_path):
            return "Arquivo não encontrado", 404

        return send_file(file_path, as_attachment=True)

    elif request.args.get('extra') == 'delete':
        # Verificar permissões (apenas usuários do lab ou o próprio solicitante)
        is_lab_user = user_has_role(current_user.role, "Laboratório") or current_user.admin
        
        if not is_lab_user:
            query = f"""SELECT requesterId FROM JDT_REQUEST_LAB WHERE requestId = '{idReq}'"""
            requester_id = engine_run_query(query, 'jdt')['requesterId'][0]
            
            if requester_id != current_user.id:
                return abort(403)

        data = request.get_json()
        if 'file' not in data:
            return "Nome do arquivo é obrigatório", 400

        file_path = os.path.join(base_dir, data['file'])
        if not os.path.exists(file_path):
            return "Arquivo não encontrado", 404

        os.remove(file_path)
        return "Arquivo excluído com sucesso", 200
    
    else:

        # Verificar permissões (apenas usuários do lab ou o próprio solicitante)
        is_lab_user = user_has_role(current_user.role, "Laboratório") or current_user.admin
        
        if not is_lab_user:
            query = f"""SELECT requesterId FROM JDT_REQUEST_LAB WHERE requestId = '{idReq}'"""
            requester_id = engine_run_query(query, 'jdt')['requesterId'][0]
            
            if requester_id != current_user.id:
                return abort(403)

        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        files = request.files.getlist("files")
        for file in files:
            original_name = file.filename
            file_path = os.path.join(base_dir, original_name)

            # Verifica se o arquivo já existe
            if os.path.exists(file_path):
                name, ext = os.path.splitext(original_name)
                counter = 1

                while os.path.exists(file_path):
                    file_path = os.path.join(base_dir, f"{name}_{counter}{ext}")
                    counter += 1

            file.save(file_path)

        return "Upload realizado com sucesso", 200

@request_laboratory_bp.route('/lab/<string:area>/detalhes/<int:idReq>/logs', methods=['GET'])
def laboratory_detail_logs_get(area, idReq):

    query = f"""SELECT 
                    T2.name
                    , T1.old
                    , T1.new
                    , T1.extra
                    , FORMAT(T1.date, 'dd/MM/yyyy HH:mm') as logDate
                FROM JDT_REQUEST_LAB_LOGS T1
                    JOIN JDT_USER_DETAILS T2 ON T1.userId = T2.id
                WHERE requestId = :requestId 
                ORDER BY date DESC"""
    data = engine_run_query(query, 'jdt', params={'requestId': idReq})

    query = f"""SELECT cancelText as text FROM JDT_REQUEST_LAB_CANCEL_TEXT WHERE requestId = :requestId ORDER BY id DESC"""
    cancel_text = engine_run_query(query, 'jdt', params={'requestId': idReq})

    data['new'] = data.apply(
        lambda row: cancel_text['text'][0] if row['extra'] == 'cancelText' and not cancel_text.empty else row['new'], axis=1
    )
    
    return jsonify(data.to_dict(orient='records'))

@request_laboratory_bp.route('/lab/<string:area>/detalhes/<int:idReq>/comentarios', methods=['GET'])
def laboratory_detail_comments_get(area, idReq):
 
    try:
        query = """
            SELECT 
                T1.commentText as text, 
                FORMAT(T1.commentDate, 'dd/MM/yyyy HH:mm') as date,
                T2.name as author
            FROM 
                JDT_REQUEST_LAB_COMMENTS T1
                JOIN JDT_USER_DETAILS T2 ON T1.userId = T2.id
            WHERE 
                T1.requestId = :requestId
            ORDER BY 
                T1.commentDate DESC
        """
        
        engine = get_engine('jdt')
        with engine.connect() as conn:
            comments = pd.read_sql(text(query), conn, params={"requestId": idReq})
            return jsonify(comments.to_dict(orient="records"))
    except Exception as e:
        print(f"Error fetching comments: {str(e)}")
        return jsonify({"error": f"Erro ao obter comentários: {str(e)}"}), 500

@request_laboratory_bp.route('/lab/<string:area>/detalhes/<int:idReq>/comentarios', methods=['POST'])
@p_laboratory.require(403)
def laboratory_detail_comments_post(area, idReq):
    data = request.get_json()

    if 'text' not in data:
        return jsonify({"error": "Dados incompletos"}), 400
    
    try:
        query = """
            INSERT INTO JDT_REQUEST_LAB_COMMENTS (requestId, userId, commentText, commentDate)
            VALUES (:requestId, :userId, :text, GETDATE())
        """
        
        engine = get_engine('jdt')
        with engine.begin() as conn:
            conn.execute(text(query), {
                "requestId": idReq,
                "userId": current_user.id,
                "text": data['text']
            })
            
        return jsonify({"message": "Comentário adicionado com sucesso!"})
    except Exception as e:
        print(f"Error adding comment: {str(e)}")
        return jsonify({"error": f"Erro ao adicionar comentário: {str(e)}"}), 500

@request_laboratory_bp.route('/lab/<string:area>/detalhes/<int:idReq>/qualidade', methods=['POST'])
@p_laboratory.require(403)
def laboratory_detail_quality_post(area, idReq):
    """Endpoint para salvar problema de qualidade (cotas não conformes)."""
    try:
        data = request.get_json()
        
        if 'qualityProblem' not in data:
            return jsonify({"error": "Dados incompletos"}), 400
        
        quality_problem = 1 if data['qualityProblem'] else 0
        
        engine = get_engine('jdt')
        with engine.begin() as conn:

            old_value = conn.execute(text("SELECT qualityProblem FROM JDT_REQUEST_LAB WHERE requestId = :request_id"), {'request_id': idReq}).scalar()
            
            # Atualizar o campo qualityProblem
            update_query = """
                UPDATE JDT_REQUEST_LAB
                SET qualityProblem = :quality_problem
                WHERE requestId = :request_id
            """
            conn.execute(text(update_query), {
                'quality_problem': bool(quality_problem),
                'request_id': idReq
            })
            
            # Registrar no log
            _UPDATE_LOGS(idReq, old_value, bool(quality_problem), 'qualityProblem', conn)
            
        return jsonify({
            "success": True,
            "message": "Problema de qualidade salvo com sucesso",
            "qualityProblem": quality_problem
        })
            
    except Exception as e:
        print(f"Erro ao salvar problema de qualidade: {str(e)}", flush=True)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



# ========================================
# GERENCIAMENTO DE SOLICITAÇÕES
# ========================================

@request_laboratory_bp.route('/lab/<string:area>/gerenciar', methods=['GET'])
@p_laboratory.require(403)
def laboratory_manage_get(area):

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""
                WITH LastestRequestPause AS (
                    SELECT 
                        requestId
                        , COALESCE(new, 'False') AS paused
                    FROM (
                        SELECT requestId, new, date,
                            ROW_NUMBER() OVER (PARTITION BY requestId ORDER BY date DESC, requestId DESC) AS rn
                        FROM JDT_REQUEST_LAB_LOGS
                        WHERE extra = 'pause'
                    ) t
                    WHERE rn = 1 
                ),
                -- CTE para calcular períodos de pausa
                PauseIntervals AS (
                    SELECT 
                        L.requestId,
                        L.[date] AS pause_start,
                        LEAD(L.[date]) OVER (PARTITION BY L.requestId ORDER BY L.[date]) AS pause_end
                    FROM JDT_REQUEST_LAB_LOGS L
                    WHERE L.extra = 'pause' 
                        AND L.[new] = 'True'
                ),
                -- CTE para períodos de execução (status 2)
                ExecutionPeriods AS (
                    SELECT 
                        L.requestId,
                        L.[date] AS exec_start,
                        LEAD(L.[date]) OVER (PARTITION BY L.requestId ORDER BY L.[date]) AS exec_end,
                        R.status AS current_status
                    FROM JDT_REQUEST_LAB_LOGS L
                    JOIN JDT_REQUEST_LAB R ON L.requestId = R.requestId
                    WHERE L.extra = 'status' 
                        AND L.[new] = '2'
                        AND R.areaId = '{_AREAS[area]}'
                ),
                -- CTE para calcular tempo pausado em cada período de execução (em MINUTOS)
                PauseDurations AS (
                    SELECT 
                        EP.requestId,
                        EP.exec_start,
                        EP.exec_end,
                        EP.current_status,
                        COALESCE(SUM(
                            DATEDIFF(MINUTE, 
                                P.pause_start, 
                                CASE 
                                    WHEN P.pause_end IS NULL AND EP.exec_end IS NULL THEN GETDATE()
                                    WHEN P.pause_end IS NULL THEN EP.exec_end
                                    WHEN EP.exec_end IS NULL THEN P.pause_end
                                    ELSE CASE WHEN P.pause_end < EP.exec_end THEN P.pause_end ELSE EP.exec_end END
                                END
                            )
                        ), 0) AS pause_minutes
                    FROM ExecutionPeriods EP
                    LEFT JOIN PauseIntervals P 
                        ON EP.requestId = P.requestId
                        AND P.pause_start >= EP.exec_start
                        AND (EP.exec_end IS NULL OR P.pause_start < EP.exec_end)
                    GROUP BY EP.requestId, EP.exec_start, EP.exec_end, EP.current_status
                ),
                -- CTE para calcular tempo total em execução EXCLUINDO pausas (em MINUTOS)
                ExecutionTime AS (
                    SELECT 
                        requestId,
                        SUM(
                            CASE 
                                -- Período completo (com próximo evento)
                                WHEN exec_end IS NOT NULL 
                                THEN DATEDIFF(MINUTE, exec_start, exec_end) - pause_minutes
                                
                                -- Período atual (ainda em execução - status 2)
                                WHEN exec_end IS NULL AND current_status = 2
                                THEN DATEDIFF(MINUTE, exec_start, GETDATE()) - pause_minutes
                                
                                -- Outros casos
                                ELSE 0
                            END
                        ) AS total_execution_minutes
                    FROM PauseDurations
                    GROUP BY requestId
                )
        
                SELECT 
                    CAST(FORMAT(T1.deadLine, 'yyyy-MM-dd') AS VARCHAR) AS deadLine
                    , T1.requestId
                    , T4.name as requesterName
                    , T1.descText
                    , T1.drawId
                    , CASE WHEN T3.paused = 'True' THEN 'CONTINUAR' ELSE 'PAUSAR' end AS paused
                    , T1.status
                    , T1.execArea
                    , CAST(FORMAT(T1.initDate, 'yyyy-MM-dd') AS VARCHAR) AS initDate
                    , 0 as timePaused 
                    , T1.prioritize
                    , COALESCE(ET.total_execution_minutes, 0) AS executionTimeMinutes
                FROM 
                    JDT_REQUEST_LAB AS T1
                    LEFT JOIN LastestRequestPause AS T3 ON T1.requestId = T3.requestId 
                    LEFT JOIN JDT_USER_DETAILS AS T4 ON T1.requesterId = T4.id
                    LEFT JOIN ExecutionTime AS ET ON T1.requestId = ET.requestId
                WHERE
                    T1.areaId = '{_AREAS[area]}' AND status <> 4 AND status <> 5

                ORDER BY 
                T1.status
                , T1.prioritize DESC
                , CASE 
                    WHEN T1.status = 1 THEN T1.deadLine 
                    ELSE NULL
                END
                , CASE 
                    WHEN T1.status != 1 THEN T1.requestId 
                    ELSE NULL
                END
            """
        df = pd.read_sql(query, cnnx) 

        query = f"""SELECT * FROM JDT_REQUEST_LAB_EQUIPMENTS WHERE area = '{_AREAS[area]}'"""
        exec_types = pd.read_sql(query, cnnx)

        
    return render_template(
        'request.laboratory/frame_manage.html'
        , dataframe=df.to_dict(orient='records')
        , areaId=_AREAS[area]
        , areaName = area
        , id=current_user.id
        , exec_types=exec_types.to_dict(orient='records')
    )

@request_laboratory_bp.route('/lab/<string:area>/gerenciar', methods=['PATCH'])
@p_laboratory.require(403)
def laboratory_manage_patch(area):
    """
    Endpoint para gerenciar alterações em solicitações de laboratório.
    Processa apenas os itens alterados
    """

    # CONDIÇÕES DE STATUS:
    # 0 = AGUARDANDO AMOSTRA
    # 1 = FILA DE ESPERA
    # 2 = EM DESENVOLVIMENTO
    # 3 = AGUARDANDO RETIRADA

    changes_dict = request.get_json()
    
    # Se não houver alterações, retorna
    if not changes_dict or 'requestId' not in changes_dict or not changes_dict['requestId']:
        return jsonify({"message": "Nenhuma alteração recebida"}), 400
    
    # Converte para listas se receber apenas um item
    for key in changes_dict:
        if not isinstance(changes_dict[key], list):
            changes_dict[key] = [changes_dict[key]]
    
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        # Obtém os dados atuais dos itens a serem alterados
        ssls_ids = tuple(changes_dict['requestId'])
        if len(ssls_ids) == 1:
            ssls_clause = f"('{ssls_ids[0]}')"
        else:
            ssls_clause = str(ssls_ids)
        
        status_query = f"""
            SELECT requestId, status, deadLine, execArea, qualityProblem, materId, areaId, prioritize
            FROM JDT_REQUEST_LAB 
            WHERE requestId IN {ssls_clause}
        """
        status_last = pd.read_sql(text(status_query), cnnx).astype(str)
        changes_df = pd.DataFrame(changes_dict).astype(str)
        
        # Combinando os DataFrames com base na coluna requestId
        merged_df = pd.merge(status_last, changes_df, on='requestId', how='inner', suffixes=('_db', '_new'))

        # Lista para processamento de alterações
        
        # Iterando sobre as linhas do DataFrame combinado
        for index, row in merged_df.iterrows():
            dataChanges = []
            equipment_operations = []  # Lista para armazenar operações de equipamentos

            if row['status_db'] != row['status_new']:

                if row['status_new'] == '0' and row['status_db'] == '1':

                    dataChanges.append('status = 0, deadLine = NULL')

                    if row['deadLine_db'] == 'None':
                      _UPDATE_LOGS(row['requestId'], row['deadLine_db'], None, "status", cnnx)

                    _UPDATE_LOGS(row['requestId'], row['status_db'], row['status_new'], "status", cnnx)

                elif row['status_new'] == '1' and row['status_db'] in ['0', '2']:

                    dataChanges.append('status = 1')
                        
                    # Se havia pausa ativa, finaliza (verificar pelo log)
                    pause_check_query = """
                        SELECT TOP 1 COALESCE(new, 'False') AS is_paused
                        FROM JDT_REQUEST_LAB_LOGS
                        WHERE requestId = :id_req AND extra = 'pause'
                        ORDER BY date DESC
                    """
                    pause_status = pd.read_sql(text(pause_check_query), cnnx, params={'id_req': row['requestId']})
                    
                    if not pause_status.empty and pause_status['is_paused'].iloc[0] == 'True':
                        # Registrar despausar no log
                        _UPDATE_LOGS(row['requestId'], True, False, "pause", cnnx)

                    
                    if row['status_db'] == '2':
                        _UPDATE_LOGS(row['requestId'], row['execArea_db'], None, "execArea", cnnx)
                        dataChanges.append('execArea = NULL')

                        equipment_check_query = f"""
                            WITH LatestEquipmentStatus AS (
                                SELECT TOP 1 status
                                FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS
                                WHERE equipmentId = :exec_area_id
                                ORDER BY id DESC
                            ), LastestRequestPause AS (
                                SELECT requestId,
                                    COALESCE([new], 'False') AS [new]
                                FROM (
                                    SELECT requestId, [new], date,
                                        ROW_NUMBER() OVER (PARTITION BY requestId ORDER BY date DESC, requestId DESC) AS rn
                                    FROM JDT_REQUEST_LAB_LOGS
                                    WHERE extra = 'pause'
                                ) t
                                WHERE rn = 1
                            )
                            SELECT 
                                T.requestId
                            FROM JDT_REQUEST_LAB T
                            CROSS APPLY LatestEquipmentStatus E
                            JOIN LastestRequestPause P ON P.requestId = T.requestId

                            WHERE 
                            T.execArea = :exec_area_id
                            AND T.status = 2
                            AND E.status = 'Disponível'
                            AND P.new = 'False'
                        """
                        
                        equipment_in_use = pd.read_sql(text(equipment_check_query), cnnx, params={'exec_area_id': row['execArea_db']})

                        # Verifica se o DataFrame não está vazio e se o requestId está presente de forma robusta
                        if not equipment_in_use.empty and equipment_in_use['requestId'].astype(int).isin([int(row['requestId'])]).any():
                            # Armazenar operação de equipamento para executar depois
                            equipment_operations.append({
                                'type': 'update_and_insert',
                                'equipment_id': row['execArea_db'],
                                'status': 'Disponível',
                                'event': 'Sem Uso',
                                'comments': 'Alterado via painel de controle.'
                            })

                    _UPDATE_LOGS(row['requestId'], row['status_db'], row['status_new'], "status", cnnx)
                
                elif row['status_new'] == '2' and row['status_db'] in ['1', '3']:
                    dataChanges.append('initDate = GETDATE(), endDate = NULL, status = 2')

                elif row['status_new'] == '3' and row['status_db'] == '2':
                    dataChanges.append('execArea = NULL')

                    # Se havia pausa ativa, finaliza (verificar pelo log)
                    pause_check_query = """
                        SELECT TOP 1 COALESCE(new, 'False') AS is_paused
                        FROM JDT_REQUEST_LAB_LOGS
                        WHERE requestId = :id_req AND extra = 'pause'
                        ORDER BY date DESC
                    """
                    pause_status = pd.read_sql(text(pause_check_query), cnnx, params={'id_req': row['requestId']})
                    
                    if not pause_status.empty and pause_status['is_paused'].iloc[0] == 'True':
                        # Registrar despausar no log
                        _UPDATE_LOGS(row['requestId'], True, False, "pause", cnnx)

                    if row['execArea_db'] != 'None':
                        
                        equipment_check_query = f"""
                            WITH LatestEquipmentStatus AS (
                                SELECT TOP 1 status
                                FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS
                                WHERE equipmentId = :exec_area_id
                                ORDER BY id DESC
                            ), LastestRequestPause AS (
                                SELECT requestId,
                                    COALESCE([new], 'False') AS [new]
                                FROM (
                                    SELECT requestId, [new], date,
                                        ROW_NUMBER() OVER (PARTITION BY requestId ORDER BY date DESC, requestId DESC) AS rn
                                    FROM JDT_REQUEST_LAB_LOGS
                                    WHERE extra = 'pause'
                                ) t
                                WHERE rn = 1
                            )
                            SELECT 
                                T.requestId
                            FROM JDT_REQUEST_LAB T
                            CROSS APPLY LatestEquipmentStatus E
                            JOIN LastestRequestPause P ON P.requestId = T.requestId

                            WHERE 
                            T.execArea = :exec_area_id
                            AND T.status = 2
                            AND E.status = 'Disponível'
                            AND P.new = 'False'
                        """
                        
                        equipment_in_use = pd.read_sql(text(equipment_check_query), cnnx, params={'exec_area_id': row['execArea_db']})

                        # Verifica se o DataFrame não está vazio e se o requestId está presente de forma robusta
                        if not equipment_in_use.empty and equipment_in_use['requestId'].astype(int).isin([int(row['requestId'])]).any():
                            # Armazenar operação de equipamento para executar depois
                            equipment_operations.append({
                                'type': 'update_and_insert',
                                'equipment_id': row['execArea_db'],
                                'status': 'Disponível',
                                'event': 'Sem Uso',
                                'comments': 'Alterado via painel de controle.'
                            })

                    _UPDATE_LOGS(row['requestId'], row['execArea_db'], None, "execArea", cnnx)
                    _UPDATE_LOGS(row['requestId'], row['status_db'], row['status_new'], "status", cnnx)

                    dataChanges.append('endDate = GETDATE(), status = ' + row['status_new'])
                    
                    # Envia email quando o status muda para "aguardando retirada"
                    query = """
                        SELECT T2.companyEmail, T3.companyEmail AS managerEmail
                        FROM JDT_REQUEST_LAB AS T1 
                            JOIN JDT_USER_DETAILS AS T2 ON T1.requesterId = T2.id
                            JOIN JDT_USER_DETAILS AS T3 ON T2.managerId = T3.id
                        WHERE requestId = :id_req
                    """
                    mails = pd.read_sql(text(query), cnnx, params={'id_req': row['requestId']})
                    
                    if row['qualityProblem'] == 'True':
                        msg = Message(
                            f"Solicitação de SSL qualidade - ID {row['requestId']}",
                            sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                            recipients=[mails['companyEmail'][0], mails['managerEmail'][0]],
                            cc=['ana.comacchio@jost.com.br', 'JostLaboratorioDimensional@randon.com.br', 'Jost_Qualidade_Fabril@randon.com.br']
                        )
                        msg.html = render_template(
                            'request.laboratory/email_quality.html'
                            , part=row['materId']
                            , requestId=row['requestId']
                            , areaName=area
                        )
                        mail.send(msg)
                    
                    msg = Message(
                        f"Solicitação de SSL concluída - ID {row['requestId']}",
                        sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                        recipients=[mails['companyEmail'][0]]
                    )
                    msg.html = render_template(
                        'request.laboratory/email_finished.html'
                        , requestId=row['requestId']
                        , areaName=area
                    )
                    mail.send(msg)
            
            # Verifica mudança em deadline
            if row['deadLine_db'] != row['deadLine_new'] and row['status_new'] not in ('3', '4', '5'):
                _UPDATE_LOGS(row['requestId'], row['deadLine_db'], row['deadLine_new'], 'deadLine', cnnx)
                
                if row['deadLine_new'] == 'None':
                    dataChanges.append("deadLine = NULL")
                else:
                    dataChanges.append(f"deadLine = '{row['deadLine_new']}'")
                    
                    # Envia email quando o prazo é definido ou alterado
                    query = """
                        SELECT companyEmail 
                        FROM JDT_REQUEST_LAB AS T1 
                        JOIN JDT_USER_DETAILS AS T2 ON T1.requesterId = T2.id
                        WHERE requestId = :id_req
                    """
                    user_mail = pd.read_sql(text(query), cnnx, params={'id_req': row['requestId']})['companyEmail'][0]
                    
                    msg = Message(
                        f"Solicitação de SSL com prazo definido - ID {row['requestId']}",
                        sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                        recipients=[user_mail]
                    )
                    
                    deadline_parts = row['deadLine_new'].split('-')
                    formatted_deadline = f"{deadline_parts[2]}/{deadline_parts[1]}/{deadline_parts[0]}"
                    
                    msg.html = render_template(
                        'request.laboratory/email_deadline.html'
                        , requestId=row['requestId']
                        , deadline=formatted_deadline
                        , areaName=area
                    )
                    mail.send(msg)
            
            # Verifica mudança em execArea
            if row['execArea_db'] != row['execArea_new'] and row['status_new'] == '2':

                if row['execArea_db'] != 'None':
                    
                    equipment_check_query = f"""
                        WITH LatestEquipmentStatus AS (
                            SELECT TOP 1 status
                            FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS
                            WHERE equipmentId = :exec_area_id
                            ORDER BY id DESC
                        ), LastestRequestPause AS (
                            SELECT requestId,
                                COALESCE([new], 'False') AS [new]
                            FROM (
                                SELECT requestId, [new], date,
                                    ROW_NUMBER() OVER (PARTITION BY requestId ORDER BY date DESC, requestId DESC) AS rn
                                FROM JDT_REQUEST_LAB_LOGS
                                WHERE extra = 'pause'
                            ) t
                            WHERE rn = 1
                        )
                        SELECT 
                            T.requestId
                        FROM JDT_REQUEST_LAB T
                        CROSS APPLY LatestEquipmentStatus E
                        JOIN LastestRequestPause P ON P.requestId = T.requestId

                        WHERE 
                        T.execArea = :exec_area_id
                        AND T.status = 2
                        AND E.status = 'Disponível'
                        AND P.new = 'False'
                    """
                    
                    equipment_in_use = pd.read_sql(text(equipment_check_query), cnnx, params={'exec_area_id': row['execArea_db']})

                    # Verifica se o DataFrame não está vazio e se o requestId está presente de forma robusta
                    if not equipment_in_use.empty and equipment_in_use['requestId'].astype(int).isin([int(row['requestId'])]).any():
                        # Armazenar operação de equipamento para executar depois
                        equipment_operations.append({
                            'type': 'update_and_insert',
                            'equipment_id': row['execArea_db'],
                            'status': 'Disponível',
                            'event': 'Sem Uso',
                            'comments': 'Alterado via painel de controle.'
                        })


                # Verificar disponibilidade do novo equipamento
                query = f"""SELECT TOP 1 
                                status, event
                            FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS
                            WHERE equipmentId = :exec_area_id 
                            ORDER BY start_date DESC"""
                exec_status = pd.read_sql(text(query), cnnx, params={'exec_area_id': row['execArea_new']})

                if not exec_status.empty and exec_status['status'][0] != 'Disponível':
                    return jsonify({
                        "error": f"Equipamento com status '{exec_status['status'][0]}', não pode ser alocado."
                    }), 400
                
                if not exec_status.empty and exec_status['event'][0] == 'Sem Uso':

                    query = """
                            SELECT requestId,
                                COALESCE([new], 'False') AS [new]
                            FROM (
                                SELECT requestId, [new], date,
                                    ROW_NUMBER() OVER (PARTITION BY requestId ORDER BY date DESC, requestId DESC) AS rn
                                FROM JDT_REQUEST_LAB_LOGS
                                WHERE extra = 'pause' and requestId = :requestId
                            ) t
                            WHERE rn = 1"""
                    paused = pd.read_sql(text(query), cnnx, params={'requestId': row['requestId']})

                    event = 'Em Uso' if paused.empty or paused['new'][0] == 'False' else 'Sem Uso'

                    # Armazenar operação de equipamento para executar depois
                    equipment_operations.append({
                        'type': 'update_and_insert',
                        'equipment_id': row['execArea_new'],
                        'status': 'Disponível',
                        'event': event,
                        'comments': 'Alterado via painel de controle.'
                    })
                    
                if row['status_db'] != '2':
                    _UPDATE_LOGS(row['requestId'], row['status_db'], row['status_new'], "status", cnnx)
                
                _UPDATE_LOGS(row['requestId'], row['execArea_db'], row['execArea_new'], 'execArea', cnnx)

                if row['execArea_new'] == 'None':
                    dataChanges.append("execArea = NULL")
                else:
                    dataChanges.append(f"execArea = '{row['execArea_new']}'")
            
            # Verifica mudança no campo prioritize
            if row['prioritize_db'] != row['prioritize_new'] and row['status_new'] not in ('3', '4', '5'):
                _UPDATE_LOGS(row['requestId'], row['prioritize_db'], row['prioritize_new'], 'prioritize', cnnx)

                # Convert boolean string to integer (1 for true, 0 for false)
                priority_bit = 1 if str(row['prioritize_new']).lower() == 'true' else 0
                dataChanges.append(f"prioritize = {priority_bit}")


            # Aplica as alterações para este item (UPDATE na tabela principal)
            if dataChanges:
                query = f"""
                    UPDATE JDT_REQUEST_LAB SET
                    {', '.join(dataChanges)}
                    WHERE requestId = '{row['requestId']}'
                """
                cnnx.execute(text(query))
            
            # AGORA executar as operações de equipamentos APÓS o UPDATE principal
            for eq_op in equipment_operations:
                # Primeiro, atualizar o último registro do equipamento
                update_last_query = """
                    UPDATE JDT_REQUEST_LAB_EQUIPMENTS_LOGS 
                    SET end_date = GETDATE(),
                        duration = DATEDIFF(SECOND, start_date, GETDATE())
                    WHERE equipmentId = :equipment_id 
                    AND id = (
                        SELECT TOP 1 id 
                        FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS 
                        WHERE equipmentId = :equipment_id 
                        ORDER BY start_date DESC
                    )
                """
                cnnx.execute(text(update_last_query), {
                    'equipment_id': eq_op['equipment_id']
                })

                # Depois, inserir novo registro
                insert_query = """
                    INSERT INTO JDT_REQUEST_LAB_EQUIPMENTS_LOGS (
                        equipmentId, register, status, event, start_date, duration, comments
                    ) VALUES (
                        :equipment_id, :register, :status, :event, GETDATE(), NULL, :comments
                    )
                """
                cnnx.execute(text(insert_query), {
                    'equipment_id': eq_op['equipment_id'],
                    'register': current_user.id,
                    'status': eq_op['status'],
                    'event': eq_op['event'],
                    'comments': eq_op['comments']
                })
        
        # Commit das alterações
        cnnx.commit()
        
    return jsonify({"message": "Alterações aplicadas com sucesso"})

@request_laboratory_bp.route('/lab/<string:area>/gerenciar/<int:id_req>/pausar', methods=['POST'])
@p_laboratory.require(403)
def laboratory_manage_pause_post(area, id_req):

    try:

        if not (user_has_role(current_user.role, "Laboratório") or current_user.admin):
            return {"error": "Acesso negado"}, 403

        engine = get_engine('jdt')
        with engine.connect() as cnnx:

            query = f"""SELECT COUNT(*) AS qtt, execArea FROM JDT_REQUEST_LAB WHERE requestId = :requestId AND status = 2 GROUP BY execArea"""
            check = pd.read_sql(text(query), cnnx, params={'requestId': id_req})

            if check['qtt'][0] == 0:
                return {"error": "A solicitação deve estar em desenvolvimento para ser pausada"}, 400

            query = """SELECT TOP 1 COALESCE(new, 'False') AS active_pauses
                             FROM JDT_REQUEST_LAB_LOGS
                             WHERE requestId = :id_req AND extra = 'pause'
                        ORDER BY date DESC"""
            pause_check = pd.read_sql(text(query), cnnx, params={'id_req': id_req})
            active_pauses = pause_check['active_pauses'][0] if not pause_check.empty else 'False'

            if active_pauses == 'True':  
                return {"error": "A solicitação já está pausada."}, 400

            _UPDATE_LOGS(id_req, False, True, "pause", cnnx)
        
            check_equipment_id = int(check['execArea'][0])
            
            equipment_check_query = f"""
                WITH LatestEquipmentStatus AS (
                    SELECT TOP 1 status
                    FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS
                    WHERE equipmentId = :exec_area_id
                    ORDER BY id DESC
                ), LastestRequestPause AS (
                    SELECT requestId,
                        COALESCE([new], 'False') AS [new]
                    FROM (
                        SELECT requestId, [new], date,
                            ROW_NUMBER() OVER (PARTITION BY requestId ORDER BY date DESC, requestId DESC) AS rn
                        FROM JDT_REQUEST_LAB_LOGS
                        WHERE extra = 'pause'
                    ) t
                    WHERE rn = 1

                    UNION ALL

                    SELECT K.requestId, 'False' AS new
                    FROM JDT_REQUEST_LAB K 
                    WHERE K.requestId NOT IN (SELECT X.requestId FROM JDT_REQUEST_LAB_LOGS X WHERE X.extra = 'pause')
                )
                SELECT 
                    COUNT(*) as qtt
                FROM JDT_REQUEST_LAB T
                CROSS APPLY LatestEquipmentStatus E
                JOIN LastestRequestPause P ON P.requestId = T.requestId

                WHERE 
                T.execArea = :exec_area_id
                AND T.status = 2
                AND E.status = 'Disponível'
                AND P.new = 'False'
            """
            equipment_in_use = pd.read_sql(text(equipment_check_query), cnnx, params={'exec_area_id': check_equipment_id})

            if equipment_in_use['qtt'][0] == 0:
                
                # Primeiro, atualizar o último registro do equipamento
                update_last_query = """
                    UPDATE JDT_REQUEST_LAB_EQUIPMENTS_LOGS 
                    SET end_date = GETDATE(),
                        duration = DATEDIFF(SECOND, start_date, GETDATE())
                    WHERE equipmentId = :equipment_id 
                    AND id = (
                        SELECT TOP 1 id 
                        FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS 
                        WHERE equipmentId = :equipment_id 
                        ORDER BY start_date DESC
                    )
                """
                cnnx.execute(text(update_last_query), {
                    'equipment_id': check_equipment_id
                })

                insert_query = """
                    INSERT INTO JDT_REQUEST_LAB_EQUIPMENTS_LOGS (
                        equipmentId, register, status, event, start_date, duration, comments
                    ) VALUES (
                        :equipment_id, :register, :status, :event, GETDATE(), NULL, :comments
                    )
                """
                cnnx.execute(text(insert_query), {
                    'equipment_id': check_equipment_id
                    , 'register': current_user.id
                    , 'status': 'Disponível'
                    , 'event': 'Sem Uso'
                    , 'comments': 'Alterado via Painel de Controle.'
                })

            cnnx.commit()

        return {"message": "Pausa criada com sucesso"}, 201
    except Exception as e:
        print(f"Erro ao criar pausa", flush=True)
        traceback.print_exc()
        return {"error": f"Erro ao criar pausa: {str(e)}"}, 500

@request_laboratory_bp.route('/lab/<string:area>/gerenciar/<int:id_req>/pausar', methods=['PATCH'])
@p_laboratory.require(403)
def laboratory_manage_pause_patch(area, id_req):

    try:
        if not (user_has_role(current_user.role, "Laboratório") or current_user.admin):
            return {"error": "Acesso negado"}, 403

        engine = get_engine('jdt')
        with engine.connect() as cnnx:

            query = """
                    SELECT TOP 1 
                        COALESCE(T.new, 'False') AS active_pauses
                        , K.execArea
                    FROM JDT_REQUEST_LAB_LOGS T
                        JOIN JDT_REQUEST_LAB K ON T.requestId = K.requestId
                    WHERE T.requestId = :id_req AND T.extra = 'pause'
                    ORDER BY T.date DESC"""
            check = pd.read_sql(text(query), cnnx, params={'id_req': id_req})

            if check.empty or check['active_pauses'][0] == 'False':
                return {"error": "A solicitação deve estar pausada."}, 400

            # Verificar se o equipamento está Disponível antes de despausar
            check_equipment_id = int(check['execArea'][0])
            
            equipment_status_query = """
                SELECT TOP 1 status
                FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS
                WHERE equipmentId = :equipment_id
                ORDER BY start_date DESC
            """
            equipment_status = pd.read_sql(text(equipment_status_query), cnnx, params={'equipment_id': check_equipment_id})
            
            if not equipment_status.empty and equipment_status['status'][0] != 'Disponível':
                return {"error": f"Não é possível despausar. Equipamento está {equipment_status['status'][0]}."}, 400

            _UPDATE_LOGS(id_req, True, False, "pause", cnnx)
            
            check_equipment_id = int(check['execArea'][0])

            equipment_check_query = f"""
                WITH LatestEquipmentStatus AS (
                    SELECT TOP 1 status
                    FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS
                    WHERE equipmentId = :exec_area_id
                    ORDER BY id DESC
                ), LastestRequestPause AS (
                    SELECT requestId,
                        COALESCE([new], 'False') AS [new]
                    FROM (
                        SELECT requestId, [new], date,
                            ROW_NUMBER() OVER (PARTITION BY requestId ORDER BY date DESC, requestId DESC) AS rn
                        FROM JDT_REQUEST_LAB_LOGS
                        WHERE extra = 'pause'
                    ) t
                    WHERE rn = 1

                    UNION ALL

                    SELECT K.requestId, 'False' AS new
                    FROM JDT_REQUEST_LAB K 
                    WHERE K.requestId NOT IN (SELECT X.requestId FROM JDT_REQUEST_LAB_LOGS X WHERE X.extra = 'pause')
                )
                SELECT 
                    count(*) as qtt
                FROM JDT_REQUEST_LAB T
                CROSS APPLY LatestEquipmentStatus E
                JOIN LastestRequestPause P ON P.requestId = T.requestId

                WHERE 
                T.execArea = :exec_area_id
                AND T.status = 2
                AND E.status = 'Disponível'
                AND P.new = 'False'
            """
            equipment_in_use = pd.read_sql(text(equipment_check_query), cnnx, params={'exec_area_id': check_equipment_id})

            if equipment_in_use['qtt'][0] == 1:

                # Primeiro, atualizar o último registro do equipamento
                update_last_query = """
                    UPDATE JDT_REQUEST_LAB_EQUIPMENTS_LOGS 
                    SET end_date = GETDATE(),
                        duration = DATEDIFF(SECOND, start_date, GETDATE())
                    WHERE equipmentId = :equipment_id 
                    AND id = (
                        SELECT TOP 1 id 
                        FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS 
                        WHERE equipmentId = :equipment_id 
                        ORDER BY start_date DESC
                    )
                """
                cnnx.execute(text(update_last_query), {
                    'equipment_id': check_equipment_id
                })

                insert_query = """
                    INSERT INTO JDT_REQUEST_LAB_EQUIPMENTS_LOGS (
                        equipmentId, register, status, event, start_date, duration, comments
                    ) VALUES (
                        :equipment_id, :register, :status, :event, GETDATE(), NULL, :comments
                    )
                """
                cnnx.execute(text(insert_query), {
                    'equipment_id': check_equipment_id
                    , 'register': current_user.id
                    , 'status': 'Disponível'
                    , 'event': 'Em Uso'
                    , 'comments': 'Alterado via Painel de Controle.'
                })

            cnnx.commit()

        return {"message": "Pausa finalizada com sucesso"}, 200
    except Exception as e:
        print(f"Erro ao finalizar pausa: {str(e)}", flush=True)
        return {"error": f"Erro ao finalizar pausa: {str(e)}"}, 500

@request_laboratory_bp.route('/lab/<string:area>/gerenciar/<int:id_req>/cancelar', methods=['PATCH'])
def laboratory_manage_cancel_patch(area, id_req):
    
    query = "SELECT requesterId FROM JDT_REQUEST_LAB WHERE requestId = :id_req AND status NOT IN (2, 3, 4, 5)"
    requester = engine_run_query(query, 'jdt', params={'id_req': id_req})

    if requester.empty:
        return {"error": "Solicitação não encontrada ou já está em andamento/concluída/cancelada"}, 404
        
    requester = requester['requesterId'][0]

    if not p_laboratory.can() and current_user.id != requester:
        return {"error": "Acesso negado"}, 403

    try:
        data = request.get_json()
        if not data or data.get('cancelText') is None:
            return jsonify({"error": "Dados insuficientes"}), 400

        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            # Obter o status atual antes de atualizar
            query = """SELECT status FROM JDT_REQUEST_LAB WHERE requestId = :id_req"""
            result = pd.read_sql(text(query), cnnx, params={'id_req': id_req})
            oldStatus = result['status'][0] if not result.empty else None

            # Atualizar para status cancelado
            query = """
                UPDATE JDT_REQUEST_LAB SET 
                    status = 5, execArea = NULL, endDate = GETDATE()
                WHERE requestId = :id_req
            """
            cnnx.execute(text(query), {'id_req': id_req})
            
            # Inserir texto de cancelamento (sem tentar obter ID na mesma consulta)
            query = """
                INSERT INTO JDT_REQUEST_LAB_CANCEL_TEXT (requestId, cancelText) 
                VALUES (:id_req, :cancelText)
            """
            cnnx.execute(text(query), {'id_req': id_req, 'cancelText': data['cancelText']})
            
            # Obter o ID em uma consulta separada
            query = """
                SELECT TOP 1 id FROM JDT_REQUEST_LAB_CANCEL_TEXT 
                WHERE requestId = :id_req 
                ORDER BY id DESC
            """
            result = pd.read_sql(text(query), cnnx, params={'id_req': id_req})
            cancel_id = result['id'][0] if not result.empty else None

            # Registrar logs após o commit
            _UPDATE_LOGS(id_req, oldStatus, 5, 'status', cnnx)
            _UPDATE_LOGS(id_req, None, cancel_id, 'cancelText', cnnx)

            cnnx.commit()

        return jsonify({"message": "Solicitação cancelada com sucesso"})
    except Exception as e:
        print(f"Erro ao cancelar solicitação: {str(e)}", flush=True)
        return jsonify({"error": f"Erro ao cancelar: {str(e)}"}), 500

@request_laboratory_bp.route('/lab/<string:area>/gerenciar/<int:id_req>/concluir', methods=['PATCH'])
@p_laboratory.require(403)
def laboratory_manage_conclude_patch(area, id_req):

    query = "SELECT requesterId FROM JDT_REQUEST_LAB WHERE requestId = :id_req AND status = 3"
    requester = engine_run_query(query, 'jdt', params={'id_req': id_req})

    if requester.empty:
        return {"error": "Solicitação não encontrada ou não está aguardando retirada."}, 404

    try:
        engine = get_engine('jdt')
        with engine.connect() as cnnx:
            update_query = f"""UPDATE JDT_REQUEST_LAB SET status = 4 WHERE requestId = :id_req"""
            cnnx.execute(text(update_query), {'id_req': id_req})
            _UPDATE_LOGS(id_req, 3, 4, 'status', cnnx)

            cnnx.commit()

        return jsonify({"message": "Solicitação concluída com sucesso"})
    except Exception as e:
        return jsonify({"error": f"Erro ao concluir: {str(e)}"}), 500

@request_laboratory_bp.route('/lab/<string:area>/gerenciar/<int:id_req>/reativar', methods=['PATCH'])
@p_laboratory.require(403)
def laboratory_manage_reactivate_patch(area, id_req):

    try:
        engine = get_engine('jdt')
        with engine.connect() as cnnx:

            # Obter o status atual antes de atualizar
            query = """SELECT status FROM JDT_REQUEST_LAB WHERE requestId = :id_req"""
            result = pd.read_sql(text(query), cnnx, params={'id_req': id_req})
            oldStatus = result['status'][0] if not result.empty else None

            # Atualiza o status para aguardando amostra e limpa campos relacionados
            query = """
                UPDATE JDT_REQUEST_LAB SET 
                    status = 0, endDate = NULL, deadLine = NULL
                WHERE requestId = :id_req
            """
            cnnx.execute(text(query), {'id_req': id_req})
            _UPDATE_LOGS(id_req, oldStatus, 0, 'status', cnnx)

            cnnx.commit()

        return jsonify({"message": "Solicitação reativada com sucesso"}), 200
    except Exception as e:
        print(f"Erro ao reativar solicitação: {str(e)}", flush=True)
        return jsonify({"error": f"Erro ao reativar solicitação: {str(e)}"}), 500



# ========================================
# GERENCIAMENTO DE EQUIPAMENTOS
# ========================================

@request_laboratory_bp.route('/lab/<string:area>/equipamentos', methods=['GET'])
@p_laboratory.require(403)
def laboratory_availability_get(area):
    """Renderiza a página de disponibilidade dos equipamentos."""

    return render_template(
        'request.laboratory/equipments.html'
        , area=area
        , areaId=_AREAS[area]
        , areaName=area.capitalize()
    )

@request_laboratory_bp.route('/lab/<string:area>/equipamentos/status', methods=['GET'])
@p_laboratory.require(403)
def laboratory_equipment_status_get(area):
    """Endpoint para obter o status de todos os equipamentos de uma área."""
    try:
        
        area_id = _AREAS[area]
        
        engine = get_engine('jdt')
        with engine.connect() as conn:
            # Buscar todos os equipamentos da área
            equip_query = """
                SELECT id, name, description, area as area_id FROM JDT_REQUEST_LAB_EQUIPMENTS 
                WHERE area = :area_id
            """
            equipments_df = pd.read_sql(text(equip_query), conn, params={'area_id': area_id})
            
            # Para cada equipamento, buscar o status atual
            result = []
            for _, equip in equipments_df.iterrows():
                # Buscar o status mais recente
                status_query = """
                    SELECT TOP 1 
                        E.status, E.event, E.start_date, E.duration, E.comments,
                        U.name as updated_by
                    FROM 
                        JDT_REQUEST_LAB_EQUIPMENTS_LOGS E
                        LEFT JOIN JDT_USER_DETAILS U ON E.register = U.id
                    WHERE 
                        E.equipmentId = :equip_id
                    ORDER BY 
                        E.start_date DESC
                """
                status_df = pd.read_sql(text(status_query), conn, params={'equip_id': equip['id']})
                
                # Contar SSLs em execução no equipamento
                ssl_query = """
                    SELECT COUNT(*) as ssl_count
                    FROM JDT_REQUEST_LAB
                    WHERE 
                        status = 2
                        AND execArea = :equip_id
                """
                ssl_df = pd.read_sql(text(ssl_query), conn, params={'equip_id': equip['id']})
                
                # Montar objeto do equipamento - convertendo tipos para Python nativos
                equipment_data = {
                    'id': int(equip['id']),
                    'name': equip['name'],
                    'description': equip['description'],
                    'area_id': int(equip['area_id']),
                    'status': 'Disponível',  # Default
                    'ssl_count': int(ssl_df['ssl_count'].iloc[0]) if not ssl_df.empty else 0,
                    'last_update': datetime.now().isoformat()
                }
                
                # Adicionar dados do status se existirem
                if not status_df.empty:
                    status_row = status_df.iloc[0]
                    equipment_data.update({
                        'status': status_row['status'],
                        'event': status_row['event'],
                        'duration': int(status_row['duration']) if pd.notnull(status_row['duration']) else None,
                        'comments': status_row['comments'],
                        'updated_by': status_row['updated_by'],
                        'last_update': status_row['start_date'].isoformat() if pd.notnull(status_row['start_date']) else None
                    })
                
                result.append(equipment_data)
                
        return jsonify(result)
    except Exception as e:
        print(f"Erro ao buscar status dos equipamentos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@request_laboratory_bp.route('/lab/<string:area>/equipamentos/atualizar', methods=['POST'])
@p_laboratory.require(403)
def laboratory_equipment_update_status_post(area):
    """Endpoint para atualizar o status de um equipamento."""
    try:
        if area not in _AREAS:
            return jsonify({"error": "Área não encontrada"}), 404
            
        data = request.get_json()
        
        if not data or 'equipmentId' not in data or 'status' not in data:
            return jsonify({"error": "Dados incompletos"}), 400
            
        # Validar status
        valid_statuses = ['Disponível', 'Indisponível', 'Parado']
        if data['status'] not in valid_statuses:
            return jsonify({"error": "Status inválido"}), 400
        
        # Validar evento obrigatório para status Indisponível, Parado
        if data['status'] in ['Indisponível', 'Parado']:
            if not data.get('event'):
                return jsonify({"error": "Evento é obrigatório para este status"}), 400
            
        # Verificar restrição de horário para status indisponível
        # Só impede COLOCAR como Indisponível durante horário comercial
        # Permite SAIR de Indisponível a qualquer momento
        if data['status'] == 'Indisponível':
            now = datetime.now()
            is_weekday = now.weekday() < 5  # 0-4 são seg-sex
            current_time = now.hour * 60 + now.minute
            work_start = 7 * 60 + 12  # 07:12
            work_end = 17 * 60  # 17:00
            
            if is_weekday and work_start <= current_time <= work_end:
                # Verificar se há agendamento ativo no momento
                check_schedule_query = """
                    SELECT COUNT(*) as has_schedule
                    FROM JDT_REQUEST_LAB_EQUIPMENTS_SCHEDULE
                    WHERE equipmentId = :equipment_id
                        AND active = 1
                        AND status = 'Indisponível'
                        AND (valid_until IS NULL OR valid_until >= CAST(GETDATE() AS DATE))
                        AND (
                            -- Verifica se o horário atual está no intervalo do agendamento
                            (CONVERT(VARCHAR(5), GETDATE(), 108) >= CONVERT(VARCHAR(5), start_time, 108) 
                             AND CONVERT(VARCHAR(5), GETDATE(), 108) < CONVERT(VARCHAR(5), end_time, 108))
                            OR
                            -- Cruza meia-noite: start > end e horário atual >= start OU < end
                            (CONVERT(VARCHAR(5), start_time, 108) > CONVERT(VARCHAR(5), end_time, 108)
                             AND (CONVERT(VARCHAR(5), GETDATE(), 108) >= CONVERT(VARCHAR(5), start_time, 108)
                                  OR CONVERT(VARCHAR(5), GETDATE(), 108) < CONVERT(VARCHAR(5), end_time, 108)))
                        )
                """
                
                engine_temp = get_engine('jdt')
                with engine_temp.connect() as cnnx_check:
                    schedule_check = pd.read_sql(text(check_schedule_query), cnnx_check, 
                                                 params={'equipment_id': data['equipmentId']})
                
                # Se não há agendamento ativo, bloqueia
                if schedule_check.empty or schedule_check['has_schedule'].iloc[0] == 0:
                    return jsonify({
                        "error": "Não é permitido definir um equipamento como Indisponível durante o horário de trabalho (Segunda a Sexta, das 07:12 às 17:00) sem um agendamento ativo. Por favor, utilize o status Parado com o motivo apropriado ou aguarde o término do horário de trabalho."
                    }), 400
        
        engine = get_engine('jdt')
        with engine.begin() as cnnx:
            # Primeiro, atualizar o último registro do mesmo equipamento (definir end_date e calcular duration)
            update_last_query = """
                UPDATE JDT_REQUEST_LAB_EQUIPMENTS_LOGS 
                SET end_date = GETDATE(),
                    duration = DATEDIFF(MINUTE, start_date, GETDATE())
                WHERE equipmentId = :equipment_id 
                AND id = (
                    SELECT TOP 1 id 
                    FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS 
                    WHERE equipmentId = :equipment_id 
                    ORDER BY start_date DESC
                )
            """
            cnnx.execute(text(update_last_query), {
                'equipment_id': data['equipmentId']
            })
            
            # Inserir novo status (sem duration e sem end_date - serão preenchidos na próxima atualização)
            insert_query = """
                INSERT INTO JDT_REQUEST_LAB_EQUIPMENTS_LOGS (
                    equipmentId, register, status, event, start_date, comments
                ) VALUES (
                    :equipment_id, :register, :status, :event, GETDATE(), :comments
                )
            """
            cnnx.execute(text(insert_query), {
                'equipment_id': data['equipmentId'],
                'register': current_user.id,
                'status': data['status'],
                'event': data.get('event') if data['status'] != 'Disponível' else 'Sem Uso',
                'comments': data.get('comments')
            })
            
            # Se o status é indisponível ou Parado, pausar todas as SSLs em execução
            if data['status'] in ['Indisponível', 'Parado']:
                # Buscar SSLs em execução no equipamento
                ssl_query = """
                    SELECT requestId FROM JDT_REQUEST_LAB
                    WHERE status = 2 AND execArea = :equipment_id
                """
                ssl_df = pd.read_sql(text(ssl_query), cnnx, params={'equipment_id': data['equipmentId']})
                
                # Para cada SSL, criar registro de pausa
                for _, row in ssl_df.iterrows():
                    # Verificar se já existe uma pausa ativa (pelo log)
                    check_query = """
                        SELECT TOP 1 COALESCE(new, 'False') AS is_paused
                        FROM JDT_REQUEST_LAB_LOGS
                        WHERE requestId = :request_id AND extra = 'pause'
                        ORDER BY date DESC
                    """
                    check_df = pd.read_sql(text(check_query), cnnx, params={'request_id': int(row['requestId'])})
                    
                    # Se não há pausa ativa, criar uma
                    if check_df.empty or check_df['is_paused'].iloc[0] == 'False':
                        # Registrar log da pausa
                        _UPDATE_LOGS(int(row['requestId']), False, True, "pause", cnnx)
            

        return jsonify({"success": True, "message": "Status do equipamento atualizado com sucesso"})
        
    except Exception as e:
        print(f"Erro ao atualizar status do equipamento: {str(e)}")
        return jsonify({"error": str(e)}), 500

@request_laboratory_bp.route('/lab/<string:area>/equipamentos/novo', methods=['POST'])
@p_laboratory.require(403)
def laboratory_equipment_create_post(area):
    """Endpoint para criar um novo equipamento."""
    try:
        if area not in _AREAS:
            return jsonify({"error": "Área não encontrada"}), 404
            
        data = request.get_json()
        
        if not data or 'name' not in data or 'area_id' not in data or 'status' not in data:
            return jsonify({"error": "Dados incompletos"}), 400
        
        # Validar status
        valid_statuses = ['Disponível', 'Indisponível', 'Parado']
        if data['status'] not in valid_statuses:
            return jsonify({"error": "Status inválido"}), 400
            
        engine = get_engine('jdt')
        with engine.begin() as conn:
            # Inserir o novo equipamento
            insert_query = """
                INSERT INTO JDT_REQUEST_LAB_EQUIPMENTS (
                    name, description, area
                ) OUTPUT INSERTED.id
                VALUES (
                    :name, :description, :area_id
                )
            """
            
            result = conn.execute(text(insert_query), {
                'name': data['name'],
                'description': data.get('description', ''),
                'area_id': data['area_id']
            })
            
            equipment_id = None
            for row in result:
                equipment_id = row[0]
                
            if not equipment_id:
                return jsonify({"error": "Falha ao criar equipamento"}), 500
                
            # Inserir o status inicial do equipamento (sem duration e sem end_date)
            status_query = """
                INSERT INTO JDT_REQUEST_LAB_EQUIPMENTS_LOGS (
                    equipmentId, register, status, event, start_date, comments
                ) VALUES (
                    :equipment_id, :register, :status, :event, GETDATE(), :comments
                )
            """
            
            event = data.get('event') if data['status'] != 'Disponível' else None
            
            conn.execute(text(status_query), {
                'equipment_id': equipment_id,
                'register': current_user.id,
                'status': data['status'],
                'event': event,
                'comments': data.get('comments', 'Criação do equipamento')
            })
            
        return jsonify({"success": True, "id": equipment_id, "message": "Equipamento criado com sucesso"})
            
    except Exception as e:
        print(f"Erro ao criar equipamento: {str(e)}")
        return jsonify({"error": str(e)}), 500

@request_laboratory_bp.route('/lab/<string:area>/equipamentos/<int:equipment_id>', methods=['GET'])
@p_laboratory.require(403)
def laboratory_equipment_get(area, equipment_id):
    """Endpoint para obter detalhes de um equipamento específico."""
    try:
        if area not in _AREAS:
            return jsonify({"error": "Área não encontrada"}), 404
            
        engine = get_engine('jdt')
        with engine.connect() as conn:
            query = """
                SELECT 
                    E.id, 
                    E.name, 
                    E.description,
                    E.area as area_id,
                    COALESCE(S.status, 'Disponível') as status
                FROM 
                    JDT_REQUEST_LAB_EQUIPMENTS E
                    LEFT JOIN (
                        SELECT TOP 1 equipmentId, status 
                        FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS 
                        WHERE equipmentId = :equipment_id 
                        ORDER BY start_date DESC
                    ) S ON E.id = S.equipmentId
                WHERE 
                    E.id = :equipment_id
            """
            equipment_df = pd.read_sql(text(query), conn, params={'equipment_id': equipment_id})
            
            if equipment_df.empty:
                return jsonify({"error": "Equipamento não encontrado"}), 404
                
            # Converter para dicionário e garantir tipos nativos Python
            row = equipment_df.iloc[0]
            equipment = {
                'id': int(row['id']),
                'name': row['name'],
                'description': row['description'] if pd.notnull(row['description']) else None,
                'area_id': int(row['area_id']),
                'status': row['status']
            }
                
        return jsonify(equipment)
    except Exception as e:
        print(f"Erro ao buscar detalhes do equipamento: {str(e)}")
        return jsonify({"error": str(e)}), 500

@request_laboratory_bp.route('/lab/<string:area>/equipamentos/<int:equipment_id>/ssls', methods=['GET'])
@p_laboratory.require(403)
def laboratory_equipment_ssls_get(area, equipment_id):
    """Endpoint para listar SSLs em execução em um equipamento específico."""
    try:
        engine = get_engine('jdt')
        with engine.connect() as conn:
            query = """
                SELECT 
                    requestId, 
                    materId, 
                    drawId, 
                    descText as description
                FROM 
                    JDT_REQUEST_LAB
                WHERE 
                    status = 2
                    AND execArea = :equipment_id
                ORDER BY
                    requestId
            """
            ssls_df = pd.read_sql(text(query), conn, params={'equipment_id': equipment_id})
            
        return jsonify(ssls_df.to_dict(orient='records'))
    except Exception as e:
        print(f"Erro ao buscar SSLs do equipamento: {str(e)}")
        return jsonify({"error": str(e)}), 500

@request_laboratory_bp.route('/lab/<string:area>/equipamentos/<int:equipment_id>/historico', methods=['GET'])
@p_laboratory.require(403)
def laboratory_equipment_history_get(area, equipment_id):
    """Endpoint para listar o histórico de status de um equipamento."""
    try:
        engine = get_engine('jdt')
        with engine.connect() as conn:
            query = """
                SELECT TOP 5
                    S.status, 
                    S.event, 
                    S.start_date,
                    S.end_date, 
                    S.duration, 
                    S.comments,
                    U.name as register,
                    CASE
                        WHEN S.duration IS NOT NULL THEN S.duration
                        WHEN S.end_date IS NOT NULL THEN DATEDIFF(MINUTE, S.start_date, S.end_date)
                        ELSE DATEDIFF(MINUTE, S.start_date, GETDATE())
                    END as calculated_duration
                FROM 
                    JDT_REQUEST_LAB_EQUIPMENTS_LOGS S
                    LEFT JOIN JDT_USER_DETAILS U ON S.register = U.id
                WHERE 
                    S.equipmentId = :equipment_id
                ORDER BY
                    S.start_date DESC
            """
            history_df = pd.read_sql(text(query), conn, params={'equipment_id': equipment_id})
            
            # Converter datas para string ISO
            result = []
            for _, row in history_df.iterrows():
                item = {
                    'status': row['status'],
                    'event': row['event'] if pd.notnull(row['event']) else None,
                    'start_date': row['start_date'].isoformat() if pd.notnull(row['start_date']) else None,
                    'end_date': row['end_date'].isoformat() if pd.notnull(row['end_date']) else None,
                    'duration': int(row['calculated_duration']) if pd.notnull(row['calculated_duration']) else None,
                    'comments': row['comments'] if pd.notnull(row['comments']) else None,
                    'register': row['register'] if pd.notnull(row['register']) else None
                }
                result.append(item)

        return jsonify(result)
    except Exception as e:
        print(f"Erro ao buscar histórico do equipamento: {str(e)}")
        return jsonify({"error": str(e)}), 500

@request_laboratory_bp.route('/lab/<string:area>/equipamentos/<int:equipment_id>/atualizar', methods=['POST'])
@p_laboratory.require(403)
def laboratory_equipment_update_post(area, equipment_id):
    """Endpoint para atualizar um equipamento existente."""
    try:
        if area not in _AREAS:
            return jsonify({"error": "Área não encontrada"}), 404
            
        data = request.get_json()
        
        if not data or 'name' not in data or 'area_id' not in data:
            return jsonify({"error": "Dados incompletos"}), 400
            
        engine = get_engine('jdt')
        with engine.begin() as conn:
            # Verificar se o equipamento existe e pertence à área correta
            check_query = """
                SELECT COUNT(*) as count FROM JDT_REQUEST_LAB_EQUIPMENTS
                WHERE id = :equipment_id
            """
            check_df = pd.read_sql(text(check_query), conn, params={'equipment_id': equipment_id})
            
            if check_df['count'].iloc[0] == 0:
                return jsonify({"error": "Equipamento não encontrado"}), 404
                
            # Atualizar o equipamento
            update_query = """
                UPDATE JDT_REQUEST_LAB_EQUIPMENTS
                SET name = :name,
                    description = :description,
                    area = :area_id
                WHERE id = :equipment_id
            """
            
            conn.execute(text(update_query), {
                'name': data['name'],
                'description': data.get('description', ''),
                'area_id': data['area_id'],
                'equipment_id': equipment_id
            })
            
            # Se o status foi fornecido, criar um novo registro de status
            if 'status' in data:
                # Validar status
                valid_statuses = ['Disponível', 'Indisponível', 'Parado']
                if data['status'] not in valid_statuses:
                    return jsonify({"error": "Status inválido"}), 400
                    
                status_query = """
                    INSERT INTO JDT_REQUEST_LAB_EQUIPMENTS_LOGS (
                        equipmentId, register, status, event, start_date, duration, comments
                    ) VALUES (
                        :equipment_id, :register, :status, :event, GETDATE(), :duration, :comments
                    )
                """
                
                event = data.get('event') if data['status'] != 'Disponível' else None
                duration = data.get('duration') if data['status'] != 'Disponível' else None
                
                conn.execute(text(status_query), {
                    'equipment_id': equipment_id,
                    'register': current_user.id,
                    'status': data['status'],
                    'event': event,
                    'duration': duration,
                    'comments': data.get('comments', 'Atualização do equipamento')
                })
            
        return jsonify({"success": True, "message": "Equipamento atualizado com sucesso"})
            
    except Exception as e:
        print(f"Erro ao atualizar equipamento: {str(e)}")
        return jsonify({"error": str(e)}), 500

@request_laboratory_bp.route('/lab/<string:area>/equipamentos/<int:equipment_id>/excluir', methods=['POST'])
@p_laboratory.require(403)
def laboratory_equipment_delete_post(area, equipment_id):
    """Endpoint para excluir um equipamento."""
    try:
        if area not in _AREAS:
            return jsonify({"error": "Área não encontrada"}), 404
            
        engine = get_engine('jdt')
        with engine.begin() as conn:
            # Verificar se o equipamento existe
            check_query = """
                SELECT COUNT(*) as count FROM JDT_REQUEST_LAB_EQUIPMENTS
                WHERE id = :equipment_id
            """
            check_df = pd.read_sql(text(check_query), conn, params={'equipment_id': equipment_id})
            
            if check_df['count'].iloc[0] == 0:
                return jsonify({"error": "Equipamento não encontrado"}), 404
                
            # Verificar se há SSLs em execução neste equipamento
            ssl_query = """
                SELECT COUNT(*) as count FROM JDT_REQUEST_LAB
                WHERE status = 2 AND execArea = :equipment_id
            """
            ssl_df = pd.read_sql(text(ssl_query), conn, params={'equipment_id': equipment_id})
            
            if ssl_df['count'].iloc[0] > 0:
                return jsonify({
                    "error": "Não é possível excluir o equipamento pois há SSLs em execução nele."
                }), 400
                
            # Excluir registros de status primeiro (integridade referencial)
            delete_status_query = """
                DELETE FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS
                WHERE equipmentId = :equipment_id
            """
            conn.execute(text(delete_status_query), {'equipment_id': equipment_id})
            
            # Excluir o equipamento
            delete_query = """
                DELETE FROM JDT_REQUEST_LAB_EQUIPMENTS
                WHERE id = :equipment_id
            """
            conn.execute(text(delete_query), {'equipment_id': equipment_id})
            
        return jsonify({"success": True, "message": "Equipamento excluído com sucesso"})
            
    except exc.IntegrityError:
        return jsonify({
            "error": "Não é possível excluir o equipamento pois há referências a ele no sistema."
        }), 400
    except Exception as e:
        print(f"Erro ao excluir equipamento: {str(e)}")
        return jsonify({"error": str(e)}), 500



# ========================================
# GERENCIAMENTO DE EVENTOS
# ========================================

@request_laboratory_bp.route('/lab/<string:area>/paradas/tipos', methods=['GET'])
@p_laboratory.require(403)
def laboratory_pause_types_get(area):
    """Endpoint para listar todos os tipos de parada disponíveis."""
    try:
        engine = get_engine('jdt')
        with engine.connect() as conn:
            query = """
                SELECT id, status, name, description, active
                FROM JDT_REQUEST_LAB_PAUSE_TYPES
                ORDER BY name
            """
            types_df = pd.read_sql(text(query), conn)
            
            # Converter para lista de dicionários e garantir tipos nativos Python
            result = []
            for _, row in types_df.iterrows():
                result.append({
                    'id': int(row['id']),
                    'status': row['status'],
                    'name': row['name'],
                    'description': row['description'] if pd.notnull(row['description']) else None,
                    'active': bool(row['active'])
                })
                
        return jsonify(result)
    except Exception as e:
        print(f"Erro ao buscar tipos de parada: {str(e)}")
        return jsonify({"error": str(e)}), 500

@request_laboratory_bp.route('/lab/<string:area>/paradas/tipos', methods=['POST'])
@p_laboratory.require(403)
def laboratory_pause_type_create_post(area):
    """Endpoint para criar um novo tipo de parada."""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'status' not in data:
            return jsonify({"error": "Nome e status do tipo de parada são obrigatórios"}), 400
        
        # Validar status
        valid_statuses = ['Indisponível', 'Parado']
        if data['status'] not in valid_statuses:
            return jsonify({"error": f"Status inválido. Use: {', '.join(valid_statuses)}"}), 400
            
        area_id = _AREAS.get(area)
        if not area_id:
            return jsonify({"error": "Área inválida"}), 400
            
        engine = get_engine('jdt')
        with engine.begin() as conn:
            # Verificar se já existe um tipo com esse nome na mesma área
            check_query = """
                SELECT COUNT(*) as count 
                FROM JDT_REQUEST_LAB_PAUSE_TYPES 
                WHERE name = :name
            """
            check_df = pd.read_sql(text(check_query), conn, params={'name': data['name'], 'area_id': area_id})
            
            if check_df['count'].iloc[0] > 0:
                return jsonify({"error": "Já existe um tipo de parada com esse nome nesta área"}), 400
                
            # Inserir novo tipo de parada
            insert_query = """
                INSERT INTO JDT_REQUEST_LAB_PAUSE_TYPES (
                    status, name, description, created_by
                ) OUTPUT INSERTED.id
                VALUES (
                    :status, :name, :description, :created_by
                )
            """
            
            result = conn.execute(text(insert_query), {
                'status': data['status'],
                'name': data['name'],
                'description': data.get('description'),
                'created_by': current_user.id
            })
            
            type_id = None
            for row in result:
                type_id = row[0]
            
            if not type_id:
                return jsonify({"error": "Falha ao criar tipo de parada"}), 500
            
        return jsonify({
            "success": True, 
            "id": type_id, 
            "message": "Tipo de parada criado com sucesso"
        })
            
    except Exception as e:
        print(f"Erro ao criar tipo de parada: {str(e)}")
        return jsonify({"error": str(e)}), 500

@request_laboratory_bp.route('/lab/<string:area>/paradas/tipos/<int:type_id>/atualizar', methods=['POST'])
@p_laboratory.require(403)
def laboratory_pause_type_update_post(area, type_id):
    """Endpoint para atualizar um tipo de parada existente."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Dados incompletos"}), 400
        
        area_id = _AREAS.get(area)
        if not area_id:
            return jsonify({"error": "Área inválida"}), 400
            
        update_fields = []
        params = {'type_id': type_id, 'area_id': area_id}
        
        if 'name' in data:
            update_fields.append("name = :name")
            params['name'] = data['name']
            
            # Verificar se já existe outro tipo com esse nome na mesma área
            engine = get_engine('jdt')
            with engine.connect() as conn:
                check_query = """
                    SELECT COUNT(*) as count 
                    FROM JDT_REQUEST_LAB_PAUSE_TYPES 
                    WHERE name = :name AND id != :type_id
                """
                check_df = pd.read_sql(text(check_query), conn, params={
                    'name': data['name'],
                    'type_id': type_id
                })
                
                if check_df['count'].iloc[0] > 0:
                    return jsonify({"error": "Já existe um tipo de parada com esse nome nesta área"}), 400
        
        if 'status' in data:
            valid_statuses = ['Indisponível', 'Parado']
            if data['status'] not in valid_statuses:
                return jsonify({"error": f"Status inválido. Use: {', '.join(valid_statuses)}"}), 400
            update_fields.append("status = :status")
            params['status'] = data['status']
        
        if 'description' in data:
            update_fields.append("description = :description")
            params['description'] = data['description']
            
        if 'active' in data:
            update_fields.append("active = :active")
            params['active'] = 1 if data['active'] else 0
            
        if not update_fields:
            return jsonify({"message": "Nenhum dado para atualizar"}), 200
            
        engine = get_engine('jdt')
        with engine.begin() as conn:
            # Atualizar o tipo de parada
            update_query = f"""
                UPDATE JDT_REQUEST_LAB_PAUSE_TYPES
                SET {', '.join(update_fields)}
                WHERE id = :type_id
            """
            
            conn.execute(text(update_query), params)
            
        return jsonify({
            "success": True,
            "message": "Tipo de parada atualizado com sucesso"
        })
            
    except Exception as e:
        print(f"Erro ao atualizar tipo de parada: {str(e)}")
        return jsonify({"error": str(e)}), 500

@request_laboratory_bp.route('/lab/<string:area>/paradas/tipos/<int:type_id>/excluir', methods=['POST'])
@p_laboratory.require(403)
def laboratory_pause_type_delete_post(area, type_id):
    """Endpoint para excluir um tipo de parada."""
    try:
        engine = get_engine('jdt')
        with engine.begin() as conn:
            # Verificar se o tipo está sendo usado
            check_query = """
                SELECT COUNT(*) as count FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS
                WHERE event = (SELECT name FROM JDT_REQUEST_LAB_PAUSE_TYPES WHERE id = :type_id)
            """
            check_df = pd.read_sql(text(check_query), conn, params={'type_id': type_id})
            
            if check_df['count'].iloc[0] > 0:
                return jsonify({
                    "error": "Não é possível excluir um tipo de parada que está sendo usado"
                }), 400
                
            # Excluir o tipo de parada
            delete_query = """
                DELETE FROM JDT_REQUEST_LAB_PAUSE_TYPES
                WHERE id = :type_id
            """
            conn.execute(text(delete_query), {'type_id': type_id})
            
        return jsonify({
            "success": True, 
            "message": "Tipo de parada excluído com sucesso"
        })
            
    except Exception as e:
        print(f"Erro ao excluir tipo de parada: {str(e)}")
        return jsonify({"error": str(e)}), 500



# ========================================
# AGENDAMENTOS DE EVENTOS
# ========================================

@request_laboratory_bp.route('/lab/<string:area>/agendamentos/gerenciar', methods=['GET'])
@p_laboratory.require(403)
def laboratory_schedules_page_get(area):
    """Renderiza a página de gerenciamento de agendamentos automáticos."""
    
    # Buscar tipos de eventos (pause types) para popular o dropdown
    # Cada evento está vinculado a um status específico
    engine = get_engine('jdt')
    with engine.connect() as conn:
        query = """
            SELECT id, name, status 
            FROM JDT_REQUEST_LAB_PAUSE_TYPES 
            WHERE active = 1
            ORDER BY status, name
        """
        pause_types = pd.read_sql(text(query), conn, params={'area_id': _AREAS[area]})
    
    return render_template(
        'request.laboratory/equipments_schedule.html',
        area=area,
        areaId=_AREAS[area],
        areaName=area.capitalize(),
        pause_types=pause_types.to_dict(orient='records')
    )

@request_laboratory_bp.route('/lab/<string:area>/agendamentos', methods=['GET'])
@p_laboratory.require(403)
def laboratory_schedules_get(area):
    """Endpoint para listar todos os agendamentos de uma área."""
    try:
        engine = get_engine('jdt')
        
        query = """
            SELECT 
                S.id,
                S.equipmentId,
                E.name as equipmentName,
                S.status,
                S.event,
                CONVERT(VARCHAR(5), S.start_time, 108) as startTime,
                CONVERT(VARCHAR(5), S.end_time, 108) as endTime,
                S.days_of_week as daysOfWeek,
                S.valid_until as validUntil,
                S.active,
                S.comments,
                FORMAT(S.created_at, 'dd/MM/yyyy HH:mm') as createdAt,
                U.name as createdBy
            FROM 
                JDT_REQUEST_LAB_EQUIPMENTS_SCHEDULE S
                JOIN JDT_REQUEST_LAB_EQUIPMENTS E ON S.equipmentId = E.id
                LEFT JOIN JDT_USER_DETAILS U ON S.created_by = U.id
            WHERE 
                S.areaId = :area_id
            ORDER BY 
                E.name, S.start_time
        """
        
        with engine.connect() as conn:
            df = pd.read_sql(
                text(query), 
                conn, 
                params={'area_id': _AREAS[area]}
            )
        
        return jsonify(df.to_dict(orient='records'))
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# CRIAR AGENDAMENTO
@request_laboratory_bp.route('/lab/<string:area>/agendamentos', methods=['POST'])
@p_laboratory.require(403)
def laboratory_schedule_create_post(area):
    """Endpoint para criar agendamentos automáticos (único ou múltiplos equipamentos)."""
    try:
        data = request.get_json()
        
        # Validações
        required_fields = ['equipmentIds', 'status', 'event', 'startTime', 'endTime', 'days']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Campo obrigatório: {field}"}), 400
        
        # equipmentIds deve ser array
        if not isinstance(data['equipmentIds'], list) or len(data['equipmentIds']) == 0:
            return jsonify({"error": "equipmentIds deve ser um array com pelo menos um ID"}), 400
        
        # Validar formato de horário (HH:MM)
        import re
        time_pattern = r'^([01]\d|2[0-3]):([0-5]\d)$'
        if not re.match(time_pattern, data['startTime']):
            return jsonify({"error": "startTime deve estar no formato HH:MM"}), 400
        if not re.match(time_pattern, data['endTime']):
            return jsonify({"error": "endTime deve estar no formato HH:MM"}), 400
        
        # Validar dias da semana
        if data['days'] not in ['*', '']:
            valid_days = ['0', '1', '2', '3', '4', '5', '6']
            days_list = data['days'].split(',')
            for day in days_list:
                if day.strip() not in valid_days:
                    return jsonify({"error": f"Dia inválido: {day}. Use 0-6 ou '*'"}), 400
        
        # Validar data de validade (se fornecida)
        valid_until = data.get('validUntil')
        if valid_until:
            try:
                from datetime import datetime
                valid_date = datetime.strptime(valid_until, '%Y-%m-%d').date()
                today = datetime.now().date()
                if valid_date < today:
                    return jsonify({"error": "Data de validade não pode ser anterior a hoje"}), 400
            except ValueError:
                return jsonify({"error": "validUntil deve estar no formato YYYY-MM-DD"}), 400
        
        engine = get_engine('jdt')
        
        query = """
            INSERT INTO JDT_REQUEST_LAB_EQUIPMENTS_SCHEDULE 
            (equipmentId, areaId, status, event, start_time, end_time, days_of_week, valid_until, comments, created_by, created_at)
            VALUES 
            (:equipment_id, :area_id, :status, :event, :start_time, :end_time, :days_of_week, :valid_until, :comments, :user_id, GETDATE())
        """
        
        created_count = 0
        with engine.begin() as conn:
            # Criar um agendamento para cada equipamento
            for equipment_id in data['equipmentIds']:
                conn.execute(text(query), {
                    'equipment_id': int(equipment_id),
                    'area_id': _AREAS[area],
                    'status': data['status'],
                    'event': data['event'],
                    'start_time': data['startTime'],
                    'end_time': data['endTime'],
                    'days_of_week': data['days'] if data['days'] else None,
                    'valid_until': valid_until,
                    'comments': data.get('comments'),
                    'user_id': current_user.id
                })
                created_count += 1
        
        return jsonify({
            "message": f"{created_count} agendamento(s) criado(s) com sucesso",
            "info": "As mudanças serão aplicadas automaticamente pelo serviço",
            "count": created_count
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ATUALIZAR AGENDAMENTO
@request_laboratory_bp.route('/lab/<string:area>/agendamentos/<int:schedule_id>', methods=['PATCH'])
@p_laboratory.require(403)
def laboratory_schedule_update_patch(area, schedule_id):
    """Endpoint para atualizar um agendamento existente."""
    try:
        data = request.get_json()
        
        # Validar formato de horário se fornecido
        import re
        time_pattern = r'^([01]\d|2[0-3]):([0-5]\d)$'
        if 'startTime' in data and not re.match(time_pattern, data['startTime']):
            return jsonify({"error": "startTime deve estar no formato HH:MM"}), 400
        if 'endTime' in data and not re.match(time_pattern, data['endTime']):
            return jsonify({"error": "endTime deve estar no formato HH:MM"}), 400
        
        # Validar data de validade se fornecida
        if 'validUntil' in data:
            valid_until = data['validUntil']
            if valid_until:  # Se não for None/vazio
                try:

                    valid_date = datetime.strptime(valid_until, '%Y-%m-%d').date()
                    today = datetime.now().date()
                    if valid_date < today:
                        return jsonify({"error": "Data de validade não pode ser anterior a hoje"}), 400
                except ValueError:
                    return jsonify({"error": "validUntil deve estar no formato YYYY-MM-DD"}), 400
        
        # Construir query dinâmica baseada nos campos fornecidos
        updates = []
        params = {'schedule_id': schedule_id}
        
        if 'startTime' in data:
            updates.append("start_time = :start_time")
            params['start_time'] = data['startTime']
        
        if 'endTime' in data:
            updates.append("end_time = :end_time")
            params['end_time'] = data['endTime']
        
        if 'days' in data:
            updates.append("days_of_week = :days_of_week")
            params['days_of_week'] = data['days'] if data['days'] else None
        
        if 'status' in data:
            updates.append("status = :status")
            params['status'] = data['status']
        
        if 'event' in data:
            updates.append("event = :event")
            params['event'] = data['event']
        
        if 'comments' in data:
            updates.append("comments = :comments")
            params['comments'] = data['comments']
        
        if 'validUntil' in data:
            updates.append("valid_until = :valid_until")
            params['valid_until'] = data['validUntil'] if data['validUntil'] else None
        
        if not updates:
            return jsonify({"error": "Nenhum campo para atualizar"}), 400
        
        query = f"""
            UPDATE JDT_REQUEST_LAB_EQUIPMENTS_SCHEDULE 
            SET {', '.join(updates)}
            WHERE id = :schedule_id
        """
        
        engine = get_engine('jdt')
        with engine.begin() as conn:
            result = conn.execute(text(query), params)
            
            if result.rowcount == 0:
                return jsonify({"error": "Agendamento não encontrado"}), 404
        
        return jsonify({
            "message": "Agendamento atualizado com sucesso",
            "info": "As mudanças serão detectadas automaticamente pelo serviço"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ATIVAR/DESATIVAR AGENDAMENTO
@request_laboratory_bp.route('/lab/<string:area>/agendamentos/<int:schedule_id>/toggle', methods=['POST'])
@p_laboratory.require(403)
def laboratory_schedule_toggle_post(area, schedule_id):
    """Endpoint para ativar ou desativar um agendamento."""
    try:
        data = request.get_json()
        active = data.get('active', True)
        
        query = """
            UPDATE JDT_REQUEST_LAB_EQUIPMENTS_SCHEDULE 
            SET active = :active
            WHERE id = :schedule_id
        """
        
        engine = get_engine('jdt')
        with engine.begin() as conn:
            result = conn.execute(text(query), {
                'schedule_id': schedule_id,
                'active': 1 if active else 0
            })
            
            if result.rowcount == 0:
                return jsonify({"error": "Agendamento não encontrado"}), 404
        
        status = "ativado" if active else "desativado"
        return jsonify({
            "message": f"Agendamento {status} com sucesso",
            "info": "As mudanças terão efeito na próxima execução do serviço"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# EXCLUIR AGENDAMENTO
@request_laboratory_bp.route('/lab/<string:area>/agendamentos/<int:schedule_id>', methods=['DELETE'])
@p_laboratory.require(403)
def laboratory_schedule_delete(area, schedule_id):
    """Endpoint para excluir um agendamento."""
    try:
        query = """
            DELETE FROM JDT_REQUEST_LAB_EQUIPMENTS_SCHEDULE 
            WHERE id = :schedule_id
        """
        
        engine = get_engine('jdt')
        with engine.begin() as conn:
            result = conn.execute(text(query), {'schedule_id': schedule_id})
            
            if result.rowcount == 0:
                return jsonify({"error": "Agendamento não encontrado"}), 404
        
        return jsonify({"message": "Agendamento excluído com sucesso"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ========================================
# RELATÓRIOS
# ========================================

@request_laboratory_bp.route('/lab/<string:area>/indicadores', methods=['GET'])
@p_laboratory.require(403)
def laboratory_manage_dashboard_get(area):

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT T2.* FROM JDT_REQUEST_LAB_MOTIVES_AREA T1 JOIN JDT_REQUEST_LAB_MOTIVES T2 ON T1.motiveId = T2.id WHERE areaId = {_AREAS[area]}"""
        motives = pd.read_sql(text(query), cnnx)
        
        query = f"""SELECT * FROM JDT_REQUEST_LAB_EQUIPMENTS WHERE area = '{_AREAS[area]}'"""
        exec_types = pd.read_sql(text(query), cnnx)

    return render_template(
        'request.laboratory/manage_kpis.html'
        , area=area
        , families=_FAMILIES
        , motives=motives.sort_values(by='name').to_dict(orient='records')
        , exec_types=exec_types.sort_values(by='name').to_dict(orient='records')
    )

@request_laboratory_bp.route('/lab/<string:area>/indicadores', methods=['POST'])
@p_laboratory.require(403)
def laboratory_manage_dashboard_post(area):

    payload = request.get_json()

    families_values = {f"family_{i}": payload['families'][i] for i in range(len(payload.get('families', [])))}
    families_sql = ', '.join([f":{key}" for key in families_values.keys()])

    equipments_values = {f"equipment_{i}": payload['equipments'][i] for i in range(len(payload.get('equipments', [])))}
    equipments_sql = ', '.join([f":{key}" for key in equipments_values.keys()])

    motives_values = {f"motive_{i}": payload['motives'][i] for i in range(len(payload.get('motives', [])))}
    motives_sql = ', '.join([f":{key}" for key in motives_values.keys()])

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        # Query para uso individual dos equipamentos
        equipment_usage_percentage_query = f"""
            SELECT 
                T1.equipmentId,
                T2.name,
                SUM(CASE WHEN T1.event = 'Em Uso' THEN T1.duration ELSE 0 END) * 100.0 / NULLIF(SUM(T1.duration), 0) AS usage_percentage
            FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS T1
                JOIN JDT_REQUEST_LAB_EQUIPMENTS T2 ON T1.equipmentId = T2.id
            WHERE 
                T2.area = {_AREAS[area]}
                AND T1.start_date BETWEEN :start_date AND :end_date
                AND T2.id IN ({equipments_sql})
            GROUP BY T1.equipmentId, T2.name
        """
        
        # Query para uso total (média de todos os equipamentos)
        equipment_total_usage_query = f"""
            SELECT 
                'TOTAL' as name,
                SUM(CASE WHEN T1.event = 'Em Uso' THEN T1.duration ELSE 0 END) * 100.0 / NULLIF(SUM(T1.duration), 0) AS usage_percentage
            FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS T1
                JOIN JDT_REQUEST_LAB_EQUIPMENTS T2 ON T1.equipmentId = T2.id
            WHERE 
                T2.area = {_AREAS[area]}
                AND T1.start_date BETWEEN :start_date AND :end_date
                AND T2.id IN ({equipments_sql})
        """

        request_status_lifetime_query = f"""
            WITH StatusEvents AS (
                -- Pega todos os eventos de mudança de status
                SELECT 
                    L.requestId,
                    L.[new] as status,
                    L.[date],
                    ROW_NUMBER() OVER (PARTITION BY L.requestId ORDER BY L.[date]) as event_order
                FROM JDT_REQUEST_LAB_LOGS L
                JOIN JDT_REQUEST_LAB R ON R.requestId = L.requestId
                WHERE L.extra = 'status' AND R.areaId = {_AREAS[area]}
                    AND R.motive IN ({motives_sql})
                    AND R.prodFamily IN ({families_sql})
            ),
            -- Para cada evento, pega a data do próximo evento (qualquer status)
            StatusDurations AS (
                SELECT 
                    curr.requestId,
                    curr.status,
                    curr.[date] AS start_date,
                    next_event.[date] AS end_date
                FROM StatusEvents curr
                LEFT JOIN StatusEvents next_event 
                    ON curr.requestId = next_event.requestId 
                    AND next_event.event_order = curr.event_order + 1
            ),
            -- Adiciona status atuais (SSLs que ainda estão em andamento)
            CurrentStatus AS (
                SELECT 
                    R.requestId,
                    CAST(R.status AS VARCHAR) as status,
                    -- Pega a data do último evento de status
                    (SELECT TOP 1 [date] 
                    FROM JDT_REQUEST_LAB_LOGS 
                    WHERE requestId = R.requestId 
                    AND extra = 'status'
                    ORDER BY [date] DESC) AS start_date,
                    NULL AS end_date
                FROM JDT_REQUEST_LAB R
                WHERE R.areaId = {_AREAS[area]}
                AND R.status IN (0, 1, 2, 3) -- Apenas status "em andamento"
                AND R.motive IN ({motives_sql})
                AND R.prodFamily IN ({families_sql})
            ),
            -- Combina todas as durações (históricas + atuais)
            AllStatusDurations AS (
                -- Todas as transições de status (incluindo revisitas ao mesmo status)
                SELECT requestId, status, start_date, end_date
                FROM StatusDurations
                
                UNION ALL
                
                -- Apenas status atuais que NÃO têm end_date em StatusDurations
                SELECT cs.requestId, cs.status, cs.start_date, cs.end_date
                FROM CurrentStatus cs
                WHERE NOT EXISTS (
                    SELECT 1 FROM StatusDurations sd 
                    WHERE sd.requestId = cs.requestId 
                    AND sd.status = cs.status 
                    AND sd.end_date IS NULL
                )
            ),
            -- Calcula tempo em dias (com precisão de horas, não apenas dias completos)
            BusinessDays AS (
                SELECT 
                requestId,
                status,
                start_date,
                end_date,
                CASE 
                    WHEN end_date IS NULL THEN 
                        -- Para status atual, calcula até agora em horas, depois converte para dias
                        CAST(DATEDIFF(HOUR, start_date, GETDATE()) AS FLOAT)
                    ELSE 
                        -- Para transições completas, calcula em horas, depois converte para dias
                        CAST(DATEDIFF(HOUR, start_date, end_date) AS FLOAT)
                END AS business_days
                FROM AllStatusDurations
            )
            SELECT 
                CASE 
                WHEN status = '0' THEN 'Aguardando Amostra'
                WHEN status = '1' THEN 'Fila de Espera'
                WHEN status = '2' THEN 'Em Desenvolvimento'
                WHEN status = '3' THEN 'Aguardando Retirada'
                WHEN status = '4' THEN 'Concluído'
                WHEN status = '5' THEN 'Cancelado'
                ELSE status
                END AS status_name,
                COUNT(*) AS transition_count,
                AVG(CAST(business_days AS FLOAT)) AS avg_business_days,
                MIN(business_days) AS min_business_days,
                MAX(business_days) AS max_business_days
            FROM BusinessDays
            WHERE start_date BETWEEN :start_date AND :end_date
            GROUP BY status
            ORDER BY status
        """

        request_deadline_reached_percentage_query = f"""
            SELECT 
                SUM(CASE WHEN CAST(endDate AS DATE) <= deadLine THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0) AS deadline_reached_percentage
            FROM JDT_REQUEST_LAB T1
            WHERE 
                T1.areaId = {_AREAS[area]}
                AND T1.openDate BETWEEN :start_date AND :end_date
                AND T1.status = 4
                AND T1.motive IN ({motives_sql})
                AND T1.prodFamily IN ({families_sql})
        """

        request_by_motive_query = f""" 
            SELECT 
                T1.motive,
                T2.name,
                COUNT(*) AS request_count
            FROM JDT_REQUEST_LAB T1
                JOIN JDT_REQUEST_LAB_MOTIVES T2 ON T1.motive = T2.id
            WHERE 
                T1.areaId = {_AREAS[area]}
                AND T1.openDate BETWEEN :start_date AND :end_date
                AND T1.motive IN ({motives_sql})
                AND T1.prodFamily IN ({families_sql})
            GROUP BY T1.motive, T2.name
        
        """

        request_closed_by_user_query = f"""
            SELECT
                COUNT(*) AS closed_requests_count
                , T3.name AS closed_by_user
            FROM JDT_REQUEST_LAB_LOGS T1
                JOIN JDT_REQUEST_LAB T2 ON T1.requestId = T2.requestId
                JOIN JDT_USER_DETAILS T3 ON T1.userId = T3.id
            WHERE 
                T2.areaId = {_AREAS[area]}
                AND T1.[new] = '4' -- Status 'Concluído'
                AND T1.[date] BETWEEN :start_date AND :end_date
                AND T2.motive IN ({motives_sql})
                AND T2.prodFamily IN ({families_sql})
            GROUP BY
                T3.name
        """

        # Executar todas as queries em paralelo
        
        def execute_query(query, params):
            """Helper function to execute a query and return the result."""
            engine = get_engine('jdt')
            with engine.connect() as conn:
                return pd.read_sql(text(query), conn, params=params)
        
        # Preparar todas as queries e seus parâmetros
        queries = [
            (equipment_usage_percentage_query, {
                'start_date': payload['start_date'],
                'end_date': payload['end_date'],
                **equipments_values
            }),
            (equipment_total_usage_query, {
                'start_date': payload['start_date'],
                'end_date': payload['end_date'],
                **equipments_values
            }),
            (request_status_lifetime_query, {
            'start_date': payload['start_date'],
            'end_date': payload['end_date'],
            **motives_values,
            **families_values
            }),
            (request_deadline_reached_percentage_query, {
            'start_date': payload['start_date'],
            'end_date': payload['end_date'],
            **motives_values,
            **families_values
            }),
            (request_by_motive_query, {
            'start_date': payload['start_date'],
            'end_date': payload['end_date'],
            **motives_values,
            **families_values
            }),
            (request_closed_by_user_query, {
            'start_date': payload['start_date'],
            'end_date': payload['end_date'],
            **motives_values,
            **families_values
            })
        ]
        
        # Executar queries em paralelo
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(executor.map(lambda q: execute_query(q[0], q[1]), queries))
        
        # Atribuir resultados
        equipment_usage_percentage_data = results[0]
        equipment_total_usage_data = results[1]
        request_status_lifetime_data = results[2]
        request_deadline_reached_percentage_data = results[3]
        request_by_motive_query_data = results[4]
        request_closed_by_user_data = results[5]

    return {
        'barchart1': equipment_usage_percentage_data.to_dict(orient='records')
        , 'barchart1_total': equipment_total_usage_data.to_dict(orient='records')
        , 'barchart2': request_status_lifetime_data.to_dict(orient='records')
        , 'barchart3': request_deadline_reached_percentage_data.to_dict(orient='records')
        , 'barchart4': request_by_motive_query_data.to_dict(orient='records')
        , 'barchart5': request_closed_by_user_data.to_dict(orient='records') if current_user.id in LEADER or current_user.id in COORD or current_user.admin else {}
    }
