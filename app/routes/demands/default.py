"""
    DemandsDefault
    Rotas e métodos para gestão de demandas, entradas, tarefas e dashboards.

    Métodos
    -------
    _get_entries(area)
        Retorna todas as entradas de uma área específica.

    demands_main()
        Página principal da aplicação de demandas, exibe demandas e entradas filtradas por área.

    demands_admin_get(), demands_admin_post()
        Rotas para administração das demandas, incluindo ordenação, edição e visualização.

    demands_presentation_get()
        Página para apresentação de demandas específicas.

    demands_entries_get(), demands_entries_post()
        Rotas para gestão de entradas (inserção, exclusão) de demandas.

    demands_create_get(), demands_create_post()
        Rotas para criação e edição de demandas, com cálculo de priorização e regras específicas por área.

    demands_detail_get(), demands_detail_post(), demands_detail_excel_get()
        Rotas para visualização, edição, exclusão e download de detalhes de demandas.

    demands_config_get()
        Página de gerenciamento das informações base da demanda.

    demands_task_create_get(), demands_task_create_post(), demands_task_config_get(), demands_task_get()
        Rotas para criação, edição, visualização e gerenciamento de tarefas vinculadas às demandas.

    demands_detail_support_get(), demands_detail_support_post(), demands_detail_support_download()
        Rotas para upload, download e exclusão de materiais de apoio das demandas.

    area_dash(), area_dash_callback()
        Rotas para dashboards e gráficos das demandas, incluindo métodos auxiliares para geração de gráficos.

    Notas
    -----
    - Todas as rotas exigem autenticação e permissões específicas.
    - Utiliza SQLAlchemy para acesso ao banco.
    - Funções auxiliares internas iniciam com '_'.
    - Dados retornados são preparados para visualização, cadastro, edição e exportação.
"""

import shutil
from datetime import datetime, date, timedelta
import pandas as pd
import json
import plotly.graph_objects as go
import plotly
import os

from sqlalchemy import text

from flask import Blueprint, abort, render_template, request, redirect, send_file, url_for
from flask_login import current_user
from flask_mail import Message

from app.utils.db_utils import get_engine
from app.utils.permissions import get_permission, user_has_role
from app.utils.files_utils import demands_file
from app.config import mail
from app.utils.data_utils import config_table, format_date

demands_default_bp = Blueprint('demands', __name__)

@demands_default_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)


def _get_entries(area):
    """
    Retorna todas as entradas de uma área específica.

    Args:
        area (str): Nome da área para filtrar entradas.
    Returns:
        DataFrame pandas com entradas da área.
    """

    query = f"""SELECT 
                    entryId AS ID,
                    name AS ENTRADA, 
                    link AS LINK, 
                    data AS DATA
                FROM 
                    JDT_DEMANDS_ENTRY 
                WHERE 
                    roleId = (SELECT roleId FROM JDT_ROLES WHERE name = '{area}')
                ORDER BY data"""

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        df = pd.read_sql(query, cnnx)

    return df

@demands_default_bp.route('/demandas', methods=['GET', 'POST'])
def demands_main():

    area = request.args['area']
  
    engine = get_engine('jdt')
    with engine.connect() as cnnx:  

        if area == 'Engenharia de Dev. de Fornecedores':
            
            query = f"""SELECT
                            title AS DEMANDA,
                            status AS STATUS,
                            userName AS RESPONSÁVEL,
                            SUBSTRING(extra, CHARINDEX(',', extra) + 1, LEN(extra) - CHARINDEX(',', extra)) AS 'FORNECEDOR',
                            FORMAT(finalDate, 'dd/MM/yyyy') AS 'PRAZO FINAL',
                            entryLink AS LINK,
                            finalGrade AS PRIORIZAÇÃO,
                            description AS DESCRIÇÃO_DA_DEMANDA, 
                            projectId AS ID
                        FROM 
                            JDT_VIEW_DEMANDS
                        WHERE
                            areaName = '{area}'
                        ORDER BY
                            CASE WHEN status LIKE 'C%' THEN 2 ELSE 1 END, finalGrade DESC;"""
            sql_data = pd.read_sql(query, cnnx)
            
            sql_data = sql_data[
                ['PRIORIZAÇÃO', 'DEMANDA', 'DESCRIÇÃO_DA_DEMANDA', 'PRAZO FINAL', 'FORNECEDOR', 'RESPONSÁVEL', 'STATUS','ID', 'LINK']]
        else:

            query = f"""SELECT
                            title AS DEMANDA,
                            status AS STATUS,
                            userName AS RESPONSÁVEL,
                            extra AS PROCESSO,
                            entryName AS ENTRADA,
                            entryLink AS LINK,
                            finalGrade AS PRIORIZAÇÃO,
                            description AS DESCRIÇÃO_DA_DEMANDA, 
                            projectId AS ID
                        FROM 
                            JDT_VIEW_DEMANDS
                        WHERE
                            areaName = '{area}'
                        ORDER BY
                            CASE WHEN status LIKE 'C%' THEN 2 ELSE 1 END, finalGrade DESC;"""

            sql_data = pd.read_sql(query, cnnx)

            sql_data = sql_data[
                ['PRIORIZAÇÃO', 'DEMANDA', 'DESCRIÇÃO_DA_DEMANDA', 'ENTRADA', 'PROCESSO', 'RESPONSÁVEL', 'STATUS', 'ID',
                    'LINK']]

    table = config_table(sql_data)

    sql_data = _get_entries(area)

    entries = sql_data[['ENTRADA', 'LINK', 'DATA']].values.tolist()

    f_title = request.form['title'] if "title" in request.form else ""
    f_desc = request.form['description'] if "description" in request.form else ""
    f_entry = request.form['entry'] if "entry" in request.form else ""
    f_process = request.form['process'] if "process" in request.form else ""
    f_leader = request.form['leader'] if "leader" in request.form else ""
    f_going = request.form['going'] if "going" in request.form else ""
    f_late = request.form['late'] if "late" in request.form else ""
    f_finished = request.form['finished'] if "finished" in request.form else ""

    return render_template('demands/demands_principal.html', area=area, table=table,
                            entries=entries, f_title=f_title, f_desc=f_desc,
                            f_entry=f_entry, f_process=f_process, f_leader=f_leader,
                            f_going=f_going, f_late=f_late, f_finished=f_finished)


@demands_default_bp.route('/demandas/admin', methods=['GET'])
def demands_admin_get():

    area = request.args['area']

    if not user_has_role(current_user.role, area) and not current_user.admin:
        return abort(403)

    query = f"""SELECT 
                    title AS DEMANDA,
                    status AS STATUS,
                    description AS DESCRIÇÃO,
                    projectId AS ID, 
                    managment AS GESTAO 
                FROM 
                    JDT_VIEW_DEMANDS 
                WHERE 
                    areaName = '{area}' 
                    AND status NOT LIKE 'c%' 
                
                ORDER BY managment DESC, finalGrade DESC"""

    engine = get_engine('jdt')
    with engine.connect() as cnnx:  
        sql_data = pd.read_sql(query, cnnx)

    sql_data = sql_data[['DEMANDA', 'DESCRIÇÃO', 'STATUS', 'ID', 'GESTAO']]

    table = config_table(sql_data)

    f_title = request.form['title'] if "title" in request.form else ""
    f_desc = request.form['description'] if "description" in request.form else ""
    f_entry = request.form['entry'] if "entry" in request.form else ""
    f_process = request.form['process'] if "process" in request.form else ""
    f_leader = request.form['leader'] if "leader" in request.form else ""
    f_going = request.form['going'] if "going" in request.form else ""
    f_late = request.form['late'] if "late" in request.form else ""
    f_finished = request.form['finished'] if "finished" in request.form else ""

    return render_template('demands/demands_admin.html', area=area, table=table,
                            f_title=f_title, f_desc=f_desc, f_entry=f_entry,
                            f_process=f_process, f_leader=f_leader, f_going=f_going,
                            f_late=f_late, f_finished=f_finished)

@demands_default_bp.route('/demandas/admin', methods=['POST'])
def demands_admin_post():

    area = request.args['area']

    if not user_has_role(current_user.role, area) and not current_user.admin:
        return abort(403)

    # CONDICAO PARA SELECIONAR OS DADOS DE UMA DEMANDA
    if 'alt' not in request.args:
        query = f"""SELECT 
                        title AS DEMANDA,
                        userName AS RESPONSÁVEL,
                        entryName AS ENTRADA,
                        extra AS PROCESSO, 
                        finalGrade AS PRAZO, 
                        status AS STATUS,
                        description AS DESCRIÇÃO_DA_DEMANDA 
                    FROM 
                        JDT_VIEW_DEMANDS
                    WHERE 
                        projectId = '{request.args['proj']}'"""

        sql_data = pd.read_sql(query, cnnx).astype(str)
        data_info = json.dumps(sql_data.values.tolist()[0]) if not len(sql_data) == 0 \
            else ['Procure uma demanda valida'] * 7

        return data_info

    # CONDICAO PARA ATUALIZAR A ORDEM DE APRESENTACAO E RECARREGAR A PÁGINA
    else:

        engine = get_engine('jdt')
        with engine.connect() as cnnx:

            if request.args['alt'] != 'Resetar':

                query = f"""SELECT 
                                projectId AS ID,
                                managment AS GESTAO 
                            FROM 
                                JDT_VIEW_DEMANDS 
                            WHERE 
                                managment IS NOT NULL AND areaName = '{area}'
                            ORDER BY 
                                managment DESC"""

                sql_data = pd.read_sql(query, cnnx)

                order = int(request.args['alt'])
                i = 0

                while i < sql_data.shape[0]:
                    if int(sql_data['GESTAO'][i]) <= order:
                        order -= 1
                        query = f"""UPDATE JDT_DEMANDS SET 
                                        managment = '{11 - order}' 
                                    WHERE 
                                        projectId = '{sql_data['ID'][i]}'"""

                        cnnx.execute(text(query))


                    i += 1

                if order == 0 and '10' in sql_data['GESTAO'].values:
                    query = f"""UPDATE JDT_DEMANDS SET 
                                    managment = NULL 
                                WHERE 
                                    projectId = '{sql_data['ID'].iloc[-1]}'"""

                    cnnx.execute(text(query))

                query = f"""UPDATE JDT_DEMANDS SET 
                                managment = '{11 - int(request.args['alt'])}' 
                            WHERE 
                                projectId = '{request.args['proj']}'"""

                cnnx.execute(text(query))

            else:

                query = f"""UPDATE JDT_DEMANDS SET 
                                managment = NULL 
                            WHERE 
                                projectId = '{request.args['proj']}'"""

                cnnx.execute(text(query))

            cnnx.commit()

    return redirect(url_for('demands_admin_get'))

@demands_default_bp.route('/demandas/admin/apresentacao', methods=['GET'])
def demands_presentation_get():

    area = request.args['area']

    if not user_has_role(current_user.role, area) and not current_user.admin:
        return abort(403)

    query = f"""SELECT
                    title AS DEMANDA,
                    status AS STATUS,
                    userName AS RESPONSÁVEL,
                    extra AS PROCESSO,
                    entryName AS ENTRADA,
                    entryLink AS LINK,
                    finalGrade AS PRIORIZAÇÃO,
                    description AS DESCRIÇÃO_DA_DEMANDA, 
                    projectId AS ID
                FROM 
                    JDT_VIEW_DEMANDS
                WHERE
                    areaName = '{area}' AND managment IS NOT NULL 
                ORDER BY
                    CASE WHEN status LIKE 'C%' THEN 2 ELSE 1 END, managment DESC;"""
    
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        sql_data = pd.read_sql(query, cnnx)

    sql_data = sql_data[
        ['DEMANDA', 'DESCRIÇÃO_DA_DEMANDA', 'ENTRADA', 'PROCESSO', 'RESPONSÁVEL', 'STATUS', 'ID', 'LINK']]

    table = config_table(sql_data)

    return render_template('demands/demands_presentation.html', area=area, table=table)


@demands_default_bp.route('/demandas/entrada', methods=['GET'])
def demands_entries_get():
    area = request.args['area']

    if not user_has_role(current_user.role, area) and not current_user.admin:
        return abort(403)

    sql_data = _get_entries(area)

    sql_data = sql_data[['ENTRADA', 'LINK', 'DATA', 'ID']]

    table = config_table(sql_data)

    return render_template('demands/demands_entries.html', area=area, table=table)

@demands_default_bp.route('/demandas/entrada', methods=['POST'])
def demands_entries_post():

    area = request.args['area']
    if not user_has_role(current_user.role, area) and not current_user.admin:
        return abort(403)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        if not 'id' in request.args:
            query = f"""INSERT INTO JDT_DEMANDS_ENTRY VALUES (
                        (SELECT roleId FROM JDT_ROLES WHERE name = '{area}'),
                        '{request.form.getlist('col_0').pop()}', 
                        '{request.form.getlist('col_1').pop()}', 
                        '{request.form.getlist('col_2').pop()}')"""
            cnnx.execute(text(query))
        else:
            query = f"""DELETE FROM JDT_DEMANDS_ENTRY WHERE entryId = '{request.args['id']}'"""
            cnnx.execute(text(query))

        cnnx.commit()

    return 'COMMITED'


@demands_default_bp.route('/demandas/criar', methods=['GET'])
def demands_create_get():

    area = request.args['area']

    if not user_has_role(current_user.role, area) and not current_user.admin:
        return abort(403)

    sql_data = _get_entries(area)

    entries = sql_data[['ID', 'ENTRADA']].values.tolist()

    surname = current_user.name.split(' ')[-1]
    name = current_user.name.split(' ')[0]

    return render_template('demands/demands_create.html', area=area, entries=entries,
                            user=name + " " + surname)

@demands_default_bp.route('/demandas/criar', methods=['POST'])
def demands_create_post():

    area = request.args['area']

    if not user_has_role(current_user.role, area) and not current_user.admin:
        return abort(403)


    deadline = datetime.strptime(request.form.get("prazo"), "%Y-%m-%d")
    
    diff = min(max((deadline - datetime.now()).days, 1), 14)
    diff_value = 1 + (3 - 1) * (1 - (diff - 1) / 13)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        if area == "Engenharia de Processo":
            families = list(filter(None, request.form.get('enviar_familia').split(',')))
            grades = list(filter(None, request.form.get('enviar_prior').split(',')))
            estrategic = 1 if request.form.get('estrategico') == "ok" else 0
            capex = 1 if request.form.get('poa') == "ok" else 0

            if "QR" in families or "QR + MESA" in families:
                family = 10
            elif "AL" in families or "SP 3° EIXO" in families or "SP SR" in families:
                family = 8
            elif "PR" in families or "PE" in families:
                family = 6
            else:
                family = 4

            firstGrade = 3 * float(grades[0]) + 2 * float(grades[1]) + 2.4 * float(grades[2]) + 3 * float(
                grades[3]) + 1.6 * float(grades[4]) + 12 * estrategic + 12 * capex + family
            firstGrade = firstGrade * 100 / 94
            finalGrade = (diff_value * firstGrade * 100) / 300

        elif area == "SSMA":
            families = list(filter(None, request.form.get('enviar_familia').split(',')))
            estrategic = 1 if request.form.get('estrategico') == "ok" else 0
            capex = 1 if request.form.get('poa') == "ok" else 0
            legislacao = '2' if request.form.get('legislacao') == "ok" else '1'
            grades = [request.form.get('enviar_prior'), legislacao]

            if "Saúde" in families:
                family = 8
            elif "Segurança" in families:
                family = 10
            else:
                family = 9

            firstGrade = 3 * float(grades[0]) + 10 * estrategic + 8 * capex + 5 * float(legislacao) + family
            firstGrade = firstGrade * 100 / 53
            finalGrade = (diff_value * firstGrade * 100) / 30

        elif area == "Engenharia de Dev. de Fornecedores":

            finalGrade = (diff_value * 100) / 3
        
        query = f"""SELECT roleId FROM JDT_ROLES WHERE name = '{area}'"""
        area_id = pd.read_sql(query, cnnx)['roleId'][0]

        if request.args['att'] == "0":

            currentYear = str(datetime.now().year)

            # SUBSTRING PARA OS PRIMEIROS 4 DIGITOS DO ID, CAST TRANSFORMA EM INTEIRO E MAX PEGA O MAIOR VALOR NA COLUNA
            query = f"""SELECT 
                            COALESCE(MAX(CAST(RIGHT(projectId, 4) AS INT)), 0) AS lastId 
                        FROM 
                            JDT_DEMANDS 
                        WHERE 
                            projectId LIKE '{currentYear}%'"""

            count = pd.read_sql(query, cnnx)['lastId']

            last_id = int(count[0]) + 1

            # FINAL_ID DEVE SER NO FORMATO "INDICE-ANO" "0000-0000"
            # zfill, preenche a quantidade restante de letras com zeros
            final_id = currentYear + "-" + str(last_id).zfill(4) if last_id < 1000 else currentYear + "-" + str(
                last_id)

            link = "'" + request.form.get('url_entrada') + "'" if not request.form.get(
                'url_entrada') == "" else 'NULL'

            if area == "Engenharia de Processo" or area == "SSMA":

                if area == "Engenharia de Processo":
                    new_families = [0 if item == 'x' else 1 for item in families]
                    new_families.insert(0, final_id)

                    # Monta os parâmetros nomeados dinamicamente
                    param_names = ['projectId'] + [f'fam{i}' for i in range(1, len(new_families))]
                    values_dict = {name: value for name, value in zip(param_names, new_families)}

                    # Monta a query com :param para cada valor
                    query = "INSERT INTO JDT_FAMILIES_PROD VALUES (:projectId" + "".join([f", :fam{i}" for i in range(1, len(new_families))]) + ")"
                    cnnx.execute(text(query), values_dict)

                query = f"""INSERT INTO JDT_DEMANDS VALUES (
                                '{final_id}', '{area_id}',
                                '{current_user.id}', 'Sem Ações',
                                '{request.form.get('descricao')}',
                                '{datetime.now().replace(microsecond=0)}',
                                '{deadline}', '{request.form.get('projeto')}',
                                NULL, NULL, '{request.form.get('entrada')}',
                                {link}, NULL, '{firstGrade}', '{finalGrade}',
                                '{','.join(grades)}', '{estrategic}',
                                '{capex}', '', '{request.form.get('enviar_processo')}')"""

            elif area == "Engenharia de Dev. de Fornecedores":

                query = f"""INSERT INTO JDT_DEMANDS VALUES (
                                '{final_id}', '{area_id}',
                                '{current_user.id}', 'Sem Ações',
                                '{request.form.get('descricao')}',
                                '{datetime.now().replace(microsecond=0)}',
                                '{deadline}', '{request.form.get('projeto')}',
                                NULL, NULL, '{request.form.get('entrada')}',
                                {link}, NULL, '100', '{finalGrade}',
                                NULL, NULL, NULL, '', '{request.form.get('inicio')},{request.form.get('fornecedorTexto')}')"""

            else:

                query = f"""INSERT INTO JDT_DEMANDS VALUES (
                                '{final_id}', '{area_id}',
                                '{current_user.id}', 'Sem Ações',
                                '{request.form.get('descricao')}',
                                '{datetime.now().replace(microsecond=0)}',
                                '{deadline}', '{request.form.get('projeto')}',
                                NULL, NULL, '{request.form.get('entrada')}',
                                {link}, NULL, NULL, NULL, NULL, NULL, NULL, '', NULL)"""

        else:

            proj = request.args['projeto']

            query = f"""SELECT userId FROM JDT_DEMANDS WHERE projectId = '{proj}'"""

            data_info = pd.read_sql(query, cnnx)

            if current_user.admin or data_info['userId'][0] == current_user.id:

                query = f"""SELECT 
                                count(*)
                            FROM 
                                JDT_DEMANDS_TASKS
                            WHERE 
                                projectId = '{proj}'"""

                count = pd.read_sql(query, cnnx).iloc[0, 0]

                if count == 0:
                    status = 'Sem Ações'
                else:
                    if diff < -2:
                        status = 'Atrasado'
                    else:
                        status = 'Em Andamento'

                link = "'" + request.form.get('url_entrada') + "'" if not request.form.get('url_entrada') == "" else 'NULL'

                if area == "Engenharia de Processo" or area == "SSMA":

                    if area == "Engenharia de Processo":
                        ins = [0 if item == 'x' else 1 for item in families]

                        query = f"""UPDATE JDT_FAMILIES_PROD SET 
                                        QR = {ins[0]}, QR_MESA = {ins[1]}, AO = {ins[2]},
                                        SP_3_EIXO = {ins[3]}, SP_SR = {ins[4]}, EE = {ins[5]},
                                        PR = {ins[6]}, AL = {ins[7]}, VT = {ins[8]},
                                        EA = {ins[9]}, PE = {ins[10]}, EC = {ins[11]}
                                    WHERE
                                        projectId = '{proj}'"""

                        cnnx.execute(text(query))

                    query = f"""UPDATE JDT_DEMANDS SET 
                                    status = '{status}', description = '{request.form.get('descricao')}',
                                    finalDate = '{deadline}', title = '{request.form.get('projeto')}',
                                    entryId = '{request.form.get('entrada')}', 
                                    entryLink = {link},
                                    firstGrade = '{firstGrade}', finalGrade = '{finalGrade}',
                                    grades = '{','.join(grades)}', estrategic = '{estrategic}', capex = '{capex}' 
                                WHERE 
                                    projectId = '{proj}'"""

                elif area == "Engenharia de Dev. de Fornecedores":

                    query = f"""UPDATE JDT_DEMANDS SET 
                                    status = '{status}', description = '{request.form.get('descricao')}',
                                    finalDate = '{deadline}', title = '{request.form.get('projeto')}',
                                    entryId = '{request.form.get('entrada')}', 
                                    entryLink = {link},
                                    firstGrade = '100', finalGrade = '{finalGrade}',
                                    extra = '{request.form.get('inicio')}, {request.form.get('fornecedorTexto')}'
                                WHERE 
                                    projectId = '{proj}'"""

                else:

                    query = f"""UPDATE JDT_DEMANDS SET 
                                    status = '{status}', description = '{request.form.get('descricao')}',
                                    finalDate = '{deadline}', title = '{request.form.get('projeto')}',
                                    entryId = '{request.form.get('entrada')}', 
                                    entryLink = {link}
                                WHERE 
                                    projectId = '{proj}'"""

        cnnx.execute(text(query))
        cnnx.commit()

    return redirect(f'/demandas?area={request.args["area"]}')


@demands_default_bp.route('/demandas/detalhes', methods=['GET'])
def demands_detail_get():

    area = request.args['area']
    proj = request.args['projeto']

    query_data = f"""SELECT
                    title, userName, finalDate,
                    description, entryName, entryLink,
                    grades, status, userId, extra 
                FROM 
                    JDT_VIEW_DEMANDS
                WHERE
                    projectId = '{proj}'"""

    query_sql = f"""SELECT 
                    taskId AS ID_TAREFA, 
                    text AS TAREFA, 
                    userName AS RESPONSÁVEL, 
                    areaName AS ÁREA, 
                    openDate AS DATA, 
                    finalDate AS PRAZO, 
                    conclusionDate AS CONCLUSÃO, 
                    observText AS OBSERVAÇÕES, 
                    status AS STATUS, 
                    projectId AS ID, 
                    finalDatesList AS PRAZOS 
                FROM
                    JDT_VIEW_DEMANDS_TASKS 
                WHERE 
                    projectId = '{proj}' 
                ORDER BY 
                    finalDate DESC"""

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        data_info = pd.read_sql(query_data, cnnx)
        sql_data = pd.read_sql(query_sql, cnnx)

    leader = data_info['userName'][0]
    grades = data_info['grades'][0].split(',')[1] if data_info['grades'][0] is not None else "Não Aplicavel"

    if grades == 'Não Aplicavel' and '-' in str(data_info['extra'][0]):
        grades = format_date(data_info['extra'][0].split(',')[0])

    deadline = data_info['finalDate'][0].strftime('%Y-%m-%d') if data_info['finalDate'][
                                                                        0] is not None else ""  # condicao para demandas antigas
    title = data_info['title'][0]
    desc = data_info['description'][0]
    entry = data_info['entryName'][0]
    entriesLink = data_info['entryLink'][0]
    status = data_info['status'][0]

    f_title = request.form['title'] if "title" in request.form else ""
    f_desc = request.form['description'] if "description" in request.form else ""
    f_entry = request.form['entry'] if "entry" in request.form else ""
    f_process = request.form['process'] if "process" in request.form else ""
    f_leader = request.form['leader'] if "leader" in request.form else ""
    f_going = request.form['going'] if "going" in request.form else ""
    f_late = request.form['late'] if "late" in request.form else ""
    f_finished = request.form['finished'] if "finished" in request.form else ""

    json_data = sql_data[
        ['TAREFA', 'RESPONSÁVEL', 'ÁREA', 'DATA', 'PRAZO', 'CONCLUSÃO', 'OBSERVAÇÕES', 'STATUS',
            'ID_TAREFA', 'PRAZOS']]

    table = config_table(json_data)

    if current_user.admin or data_info['userId'][0] == current_user.id:
        admin = "True"
    else:
        admin = "False"

    return render_template('demands/demands_detail.html', area=area, title=title, desc=desc, table=table,
                            idproj=proj, entriesLink=entriesLink, grades=grades, entry=entry, admin=admin,
                            status=status, f_title=f_title, deadline=deadline, f_desc=f_desc, f_entry=f_entry,
                            f_process=f_process, leader=leader, f_leader=f_leader, f_going=f_going,
                            f_late=f_late, f_finished=f_finished)

@demands_default_bp.route('/demandas/detalhes', methods=['POST'])
def demands_detail_post():

    query = f"""SELECT userId, finalDate FROM JDT_DEMANDS WHERE projectId = '{request.args["projeto"]}'"""
    
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        userId = pd.read_sql(query, cnnx).values.tolist()[0]

        if userId[0] == current_user.id or current_user.admin:

            # CONDIÇÃO PARA DELETAR UMA DEMANDA
            if 'remove' in request.args:
                query = f"""DELETE FROM JDT_DEMANDS 
                        WHERE projectId = '{request.args["projeto"]}'"""
                cnnx.execute(text(query))

                query = f"""DELETE FROM JDT_DEMANDS_TASKS 
                        WHERE projectId = '{request.args["projeto"]}'"""
                cnnx.execute(text(query))

                query = f"""DELETE FROM JDT_FAMILIES_PROD 
                        WHERE projectId = '{request.args["projeto"]}'"""

                if os.path.exists(rf'{os.getcwd()}\app\static\uploads\demands\{request.args["area"]}\{request.args["projeto"]}'):
                    shutil.rmtree(rf'{os.getcwd()}\app\static\uploads\demands\{request.args["area"]}\{request.args["projeto"]}')

            # CONDICAO PARA CONCLUIR OU RETOMAR UMA DEMANDA
            elif 'conc' in request.args:
                if request.args['conc'] == '1':
                    query = f"""UPDATE JDT_DEMANDS SET 
                                        status = 'Concluído', 
                                        managment = NULL 
                                WHERE 
                                    projectId = '{request.args['projeto']}'"""
                else:
                    deadLine = userId[1].to_pydatetime()
                    diff = deadLine - datetime.now()

                    if diff.days < -2:
                        status = 'Atrasado'
                    else:
                        status = 'Em Andamento'

                    query = f"""UPDATE JDT_DEMANDS SET 
                                    status = '{status}' 
                                WHERE 
                                    projectId = '{request.args['projeto']}'"""

            cnnx.execute(text(query))
            cnnx.commit()

    return redirect(f'/demandas?area={request.args["area"]}')

@demands_default_bp.route('/demandas/detalhes/download', methods=['GET'])
def demands_detail_excel_get():

    # DELETA OS ARQUIVOS QUE FORAM BAIXADOS POR USUÁRIO (CADA DOWNLOAD GERA UM ARQUIVO NO SISTEMA)
    path = fr'{os.getcwd()}\app\static\uploads\default'
    for excel_file in os.listdir(path):
        os.remove(fr'{path}\{excel_file}')

    excel_file = demands_file(request.args['projeto'])

    return send_file(rf'{path}\{excel_file}', as_attachment=True)


@demands_default_bp.route('/demandas/gerenciar', methods=['GET'])
def demands_config_get():
            
    area = request.args['area']
    proj = request.args['projeto']


    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT userId FROM JDT_DEMANDS WHERE projectId = '{proj}'"""
        data_info = pd.read_sql(query, cnnx)

        if current_user.admin or data_info['userId'][0] == current_user.id:


            query = f"""SELECT 
                            title AS TITULO, 
                            userName AS RESPONSAVEL, 
                            finalDate AS PRAZO, 
                            entryName AS ENTRADA, 
                            CASE WHEN entryLink IS NULL THEN '' ELSE entryLink END AS LINK, 
                            description AS DESCRICAO, 
                            extra AS PROCESSOS, 
                            grades AS NOTAS, 
                            estrategic AS ESTRATEGICO, 
                            capex AS CAPEX 
                        FROM 
                            JDT_VIEW_DEMANDS 
                        WHERE 
                            projectId = '{proj}'"""

            sql_data = pd.read_sql(query, cnnx)

            if area == 'Engenharia de Processos':
                query = f"""SELECT 
                                *
                            FROM 
                                JDT_FAMILIES_PROD 
                            WHERE 
                                projectId = '{proj}'"""

                sql_family = pd.read_sql(query, cnnx).astype(str).values.tolist()[0][1:]
            else:
                sql_family = []


            sql_data['PRAZO'] = sql_data['PRAZO'].dt.strftime('%Y-%m-%d') if not pd.isnull(
                sql_data['PRAZO']).all() else sql_data['PRAZO']
            data = json.dumps(sql_data.to_dict("records"))

            sql_data = _get_entries(area)
            entries = sql_data[['ID', 'ENTRADA']].values.tolist()

            return render_template('demands/demands_manage.html', area=area, data=data,
                                    entries=entries, project=proj, family=sql_family)

        else:

            return abort(403)


@demands_default_bp.route('/demandas/tarefa/criar', methods=['GET'])
def demands_task_create_get():

    area = request.args['area']
    proj = request.args['projeto']

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT userId FROM JDT_DEMANDS WHERE projectId = '{proj}'"""
        data_info = pd.read_sql(query, cnnx)

        if current_user.admin or data_info['userId'][0] == current_user.id:

            query = f"""SELECT 
                            T1.name AS NOME, 
                            T2.areaId as DEPT 
                        FROM 
                            JDT_USER_DETAILS AS T1 
                            JOIN JDT_GENERAL_AREA AS T2 ON T1.areaId = T2.areaId 
                        WHERE 
                            T1.active = 1 AND T1.generic = 0
                        ORDER BY 
                            DEPT"""

            sql_data = pd.read_sql(query, cnnx)
            people = json.dumps(sql_data.to_dict("records"))

            return render_template('demands/demands_task_new.html', area=area, project=proj,
                                    people=people)

        else:

            return abort(403)

@demands_default_bp.route('/demandas/tarefa/criar', methods=['POST'])
def demands_task_create_post():

    def get_userArea():
        query = f"""SELECT 
                        id, 
                        areaId,
                        companyEmail   
                    FROM 
                        JDT_USER_DETAILS 
                    WHERE 
                        name = '{request.form.get('responsavel')}'"""

        area = pd.read_sql(query, cnnx)

        return area['areaId'][0], area['id'][0], area['companyEmail'][0],

    area = request.args['area']
    proj = request.args['projeto']

    if not user_has_role(current_user.role, area) and not current_user.admin:
        return abort(403)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT userId, status FROM JDT_DEMANDS WHERE projectId = '{proj}'"""
        sql_data = pd.read_sql(query, cnnx)

        if current_user.admin or sql_data['userId'][0] == current_user.id:

            # CONDIDAO PARA DELETAR
            if 'delete' in request.args:
                taskId = request.args['tarefa']
                query = f"""DELETE FROM 
                                JDT_DEMANDS_TASKS 
                            WHERE 
                                taskId = '{taskId}'"""
            else:

                data = str(date.today())
                deadline = request.form.get('prazo')

                conclusion = "'" + request.form.get('conclusao') + "'" if request.form.get('conclusao') else 'NULL'
                status = ""

                if conclusion == "NULL":
                    if deadline < data:
                        status = 'Atrasado'

                    elif deadline >= data:
                        status = 'Em Andamento'

                else:
                    status = 'Concluído'

                # CONDIDAO PARA ATUALIZAR
                if 'tarefa' in request.args:
                    taskId = request.args['tarefa']

                    if 'externo' not in request.form:
                        area, resp, resp_email = get_userArea()

                    else:
                        area = 15
                        resp = request.form.get('responsavel')

                    query = f"""SELECT 
                                    finalDatesList, finalDate 
                                FROM 
                                    JDT_DEMANDS_TASKS WHERE taskId = '{taskId}'"""

                    df = pd.read_sql(query, cnnx)

                    if str(df['finalDate'][0]) != str(deadline):
                        if pd.isna(df['finalDatesList'][0]):
                            finalDatesList = "'" + str(df['finalDate'][0]) + "'"
                        else:
                            finalDatesList = "'" + str(df['finalDatesList'][0]) + "," + str(df['finalDate'][0]) + "'"
                    else:
                        if pd.isna(df['finalDatesList'][0]):
                            finalDatesList = 'NULL'
                        else:
                            finalDatesList = "'" + str(df['finalDatesList'][0]) + "'"

                    observText = request.form.get('observacoes') or 'Sem observações'

                    query = f"""UPDATE JDT_DEMANDS_TASKS SET 
                                text = '{request.form.get('tarefa')}', 
                                userId = '{resp}', 
                                areaId = '{area}', 
                                finalDate = '{deadline}', 
                                conclusionDate = {conclusion}, 
                                observText = '{observText}', 
                                status = '{status}',
                                finalDatesList = {finalDatesList} 
                            WHERE taskId = '{taskId}'"""

                # CONDIDAO PARA ADICIONAR
                else:

                    currentYear = str(datetime.now().year)

                    query = f"""SELECT 
                                    MAX(CAST(RIGHT(taskId, 4) AS INT)) AS lastId 
                                FROM 
                                    JDT_DEMANDS_TASKS 
                                WHERE 
                                    taskId LIKE '{currentYear}%'"""

                    count = pd.read_sql(query, cnnx)
                    last_id = int(count['lastId'][0]) + 1 if count['lastId'][0] is not None else 1

                    # FINAL_ID DEVE SER NO FORMATO "INDICE-ANO" "0000-0000"
                    # zfill, preenche a quantidade restante de letras com zeros
                    final_id = currentYear + "-" + str(last_id).zfill(4) if last_id < 1000 else currentYear + "-" + str(last_id)

                    if 'externo' not in request.form:

                        area, resp, resp_email = get_userArea()
                    else:
                        area = 15
                        resp = request.form.get('responsavel')

                    observText = request.form.get('observacoes') or 'Sem observações'

                    query = f"""INSERT INTO JDT_DEMANDS_TASKS VALUES 
                                    ('{final_id}', '{proj}', 
                                    '{area}', '{resp}', '{request.form.get('tarefa')}',
                                    '{observText}', GETDATE(), '{deadline}', {conclusion}, 
                                    NULL, '{status}')"""

                    if resp != current_user.id and len(conclusion) == 4:
                        msg = Message(f'Tarefa adicionada - ID {final_id}',
                                        sender=('Transformação Digital JOST', 'noreply.digitaljost@randon.com.br'),
                                        recipients=[resp_email])

                        msg.html = render_template('demands/demands_email_new_task.html',
                                                    task=request.form.get('tarefa'), area=area, proj=proj, createdBy=current_user.name)

                        mail.send(msg)

                    if sql_data['status'][0] == 'Sem Ações':
                        query2 = f"""UPDATE JDT_DEMANDS SET 
                                        status = 'Em Andamento' 
                                    WHERE 
                                        projectId = '{proj}'"""
                        cnnx.execute(text(query2))

            cnnx.execute(text(query))

            cnnx.commit()

    return redirect(f'/demandas/detalhes?area={request.args["area"]}&projeto={request.args["projeto"]}')

@demands_default_bp.route('/demandas/tarefa/gerenciar', methods=['GET'])
def demands_task_config_get():

    proj = request.args['projeto']

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = f"""SELECT userId FROM JDT_DEMANDS WHERE projectId = '{proj}'"""
        data_info = pd.read_sql(query, cnnx)

        if current_user.admin or data_info['userId'][0] == current_user.id:

            area = request.args['area']  # pega a area que o usuario está acessando

            query = f"""SELECT 
                            text AS TAREFA, 
                            userName AS RESPONSÁVEL, 
                            areaName AS ÁREA, 
                            CONVERT(VARCHAR, openDate, 120) AS DATA, 
                            CONVERT(VARCHAR, finalDate, 120) AS PRAZO, 
                            CONVERT(VARCHAR, conclusionDate, 120) AS CONCLUSÃO, 
                            observText AS OBSERVACOES, 
                            status AS STATUS, 
                            taskId AS ID 
                        FROM 
                            JDT_VIEW_DEMANDS_TASKS
                        WHERE 
                            taskId = '{request.args['id']}'"""

            sql_data = pd.read_sql(query, cnnx)  # seleciona os dados no banco
            data = json.dumps(sql_data.to_dict("records"))

            query = f"""SELECT 
                            T1.name AS NOME, 
                            T2.name as DEPARTAMENTO 
                        FROM 
                            JDT_USER_DETAILS AS T1
                            JOIN JDT_GENERAL_AREA AS T2 ON T1.areaId = T2.areaId 
                        WHERE
                            T1.active = 1 AND T1.generic = 0
                        ORDER BY 
                            DEPARTAMENTO"""

            sql_data = pd.read_sql(query, cnnx)
            people = json.dumps(sql_data.to_dict("records"))
            sql_data = sql_data.drop_duplicates(subset='DEPARTAMENTO')
            department = json.dumps(sql_data.to_dict("records"))

            return render_template('demands/demands_task_manage.html', area=area, data=data,
                                    tarefa=request.args['id'], projeto=proj, people=people, department=department)

        else:

            return abort(403)

@demands_default_bp.route('/demandas/tarefas', methods=['GET'])
def demands_task_get():

    area = request.args['area']

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT 
                        T2.title AS TITULO, 
                        T1.text AS TAREFA, 
                        T3.name AS RESPONSAVEL, 
                        T1.finalDate AS PRAZO, 
                        T1.conclusionDate AS CONCLUSÃO, 
                        T1.observText AS OBSERVACOES, 
                        T1.status AS STATUS, 
                        T2.projectId AS ID, 
                        T1.finalDatesList AS PRAZOS 
                    FROM 
                        JDT_DEMANDS_TASKS AS T1 
                        JOIN JDT_DEMANDS AS T2 ON T1.projectId = T2.projectId 
                        JOIN JDT_USER_DETAILS AS T3 ON T1.userId = T3.id 
                    WHERE 
                        T2.aplicationArea = (SELECT roleId FROM JDT_ROLES WHERE name = '{area}') """

        sql_data = pd.read_sql(query, cnnx)

        table = config_table(sql_data)

        query = f"""SELECT 
                        DISTINCT T2.Name 
                    FROM 
                        JDT_DEMANDS_TASKS AS T1
                        JOIN JDT_USER_DETAILS AS T2 ON T1.userId = T2.id 
                    WHERE 
                        T1.areaId = (SELECT roleId FROM JDT_ROLES WHERE name = '{area}') """

        resp = pd.read_sql(query, cnnx).values.tolist()

        return render_template('demands/demands_task_principal.html', area=area, table=table, resp=resp)


@demands_default_bp.route('/demandas/detalhes/apoio', methods=['GET'])
def demands_detail_support_get():

    area = request.args['area']
    proj = request.args['projeto']

    if not user_has_role(current_user.role, area) and not current_user.admin:
        return abort(403)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT
                            title, userName, FORMAT(finalDate, 'dd/MM/yyyy') AS finalDate, images,
                            description, status, userId 
                        FROM 
                            JDT_VIEW_DEMANDS
                        WHERE
                            projectId = '{proj}'"""
        df = pd.read_sql(query, cnnx)

        if current_user.admin or df['userId'][0] == current_user.id:
            admin = "1"
        else:
            admin = '0'

        df['images'][0] = df['images'][0].split('||')[:-1]

        return render_template('demands/demands_detail_support.html', area=area, projeto=proj,
                                admin=admin, df=df.to_json())

@demands_default_bp.route('/demandas/detalhes/apoio', methods=['POST'])
def demands_detail_support_post():

    area = request.args['area']
    proj = request.args['projeto']

    if not user_has_role(current_user.role, area) and not current_user.admin:
        return abort(403)

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT
                            title, userName, FORMAT(finalDate, 'dd/MM/yyyy') AS finalDate, images,
                            description, status, userId 
                        FROM 
                            JDT_VIEW_DEMANDS
                        WHERE
                            projectId = '{proj}'"""
        df = pd.read_sql(query, cnnx)

        if current_user.admin or df['userId'][0] == current_user.id:

            thisPath = area + '/' + proj

            if "arq" in request.args:
                if request.args["arq"] in df['images'][0]:

                    thisFile = request.args['arq']

                    df['images'][0] = df['images'][0].replace(str(request.args["arq"] + '||'), "")

                    if os.path.exists(rf'{os.getcwd()}\app\static\uploads\demands\{thisPath}\{thisFile}'):
                        os.remove(rf'{os.getcwd()}\app\static\uploads\demands\{thisPath}\{thisFile}')

                    query = f"""UPDATE JDT_DEMANDS SET 
                                images = '{df['images'][0]}' WHERE projectId = '{proj}'"""

                    cnnx.execute(text(query))

            else:

                if not os.path.exists(
                        'static/uploads/demands/' + thisPath + '/'):
                    os.mkdir('static/uploads/demands/' + thisPath + '/')

                for file in request.files.getlist('documentos'):  # percorre os arquivos enviados pela API
                    if file.filename != '':  # se o nome do arquivo não for vazio
                        if df['images'][0].upper().count(file.filename.upper()) == 0:
                            file.save(os.path.join(rf'{os.getcwd()}\app\static\uploads\demands\{thisPath}',
                                                    file.filename))
                            df['images'][0] += f'{file.filename}||'
                        else:
                            acum = str(df['images'][0].upper().count(file.filename.upper().rsplit(".", 1)[0]))
                            thisName = file.filename.rsplit(".", 1)[0] + "_(" + str(acum) + ")." + \
                                        file.filename.split('.')[-1]
                            file.save(os.path.join(rf'{os.getcwd()}\app\static\uploads\demands\{thisPath}', thisName))
                            df['images'][0] += f'{thisName}||'

                query = f"""UPDATE JDT_DEMANDS SET images = '{df['images'][0]}' WHERE projectId = '{proj}'"""

                cnnx.execute(text(query))

            cnnx.commit()

    return redirect(url_for('demands_detail_support_get'))

@demands_default_bp.route('/demandas/detalhes/apoio/download')
def demands_detail_support_download():
    file = rf'static\uploads\demands\{request.args["area"]}\{request.args["projeto"]}\{request.args["arq"]}'
    return send_file(rf'{os.getcwd()}\{file}', as_attachment=True)


@demands_default_bp.route('/demandas/dashboards', methods=['GET', 'POST'])
def area_dash():

    area = request.args["area"]

    engine = get_engine('jdt')
    with engine.connect() as cnnx:

        query = f"""SELECT 
                            DISTINCT userName 
                    FROM 
                        JDT_VIEW_DEMANDS 
                    WHERE
                        areaName = '{area}'"""
        names = pd.read_sql(query, cnnx)['userName'].values.tolist()

    return render_template('demands/demands_dashboards.html', area=area, names=names)

@demands_default_bp.route('/demandas/dashboards/dash_callback', methods=['POST'])
def area_dash_callback():

    # FUNÇÃO PARA CRIAR GRAFICOS DE PIZZA
    def graph_pizza(lbls, vals, ttl, colors, template):
        if colors:
            fig = go.Figure(data=[
                go.Pie(labels=lbls, values=vals, hole=.3, pull=0.05,
                        textfont_color="white", sort=False,
                        name=ttl,
                        marker={'colors': ('rgb(181, 10, 10)', 'rgb(13, 55, 13)',
                                            'rgb(221, 141, 0)', 'rgb(70, 48, 255)')},
                        hovertemplate=template)])


        else:
            fig = go.Figure(data=[
                go.Pie(labels=lbls, values=vals, hole=.3, pull=0.05,
                        textfont_color="white", sort=False,
                        name=ttl,
                        hovertemplate=template)])

        fig.update_layout(title=dict(text=ttl, x=0.5))
        fig.update_layout(
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5, x=-0.5,
                xanchor="center",
                itemsizing="constant",
                itemdoubleclick=False,
                itemclick=False),
            uniformtext_minsize=11,
            uniformtext_mode='hide',
            font=dict(size=1),
            title=dict(y=0.95,
                        yanchor='top',
                        font=dict(size=1)),
            margin=dict(t=40, r=10))

        fig.update_traces(textposition='inside',
                            textinfo='value+percent')

        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(
                family="Montserrat, monospace",
                color="rgba(22,58,138,1)")
        )

        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False)

        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        graphJSON = json.loads(graphJSON)
        graphJSON['config'] = {'responsive': True, 'displayModeBar': False}
        graphJSON = json.dumps(graphJSON)

        return graphJSON

    # FUNÇÃO PARA CRIAR GRAFICOS DE BARRA
    def graph_bars(lbls, andam, atras, aco, conc, nome_barra):

        fig = go.Figure(data=[go.Bar(
            x=lbls,
            y=round(andam, 2),
            name=nome_barra,
            marker=dict(color='rgb(221, 141, 0)'),
            text=andam,
            textposition="inside",
            insidetextanchor='middle',
            textfont=dict(color="white"),
            insidetextfont=dict(size=16),
            hovertemplate='<b>%{x} <br><br>Em Andamento</b>'),

            go.Bar(x=lbls,
                    y=round(atras, 2),
                    name=nome_barra,
                    marker=dict(color='rgb(181, 10, 10)'),
                    text=atras,
                    textposition="inside",
                    insidetextanchor='middle',
                    textfont=dict(color="white"),
                    insidetextfont=dict(size=16),
                    hovertemplate='<b>%{x} <br><br>Atrasado</b>'),

            go.Bar(x=lbls,
                    y=round(aco, 2),
                    name=nome_barra,
                    marker=dict(color='rgb(70, 48, 255)'),
                    text=aco,
                    textposition="inside",
                    insidetextanchor='middle',
                    textfont=dict(color="white"),
                    insidetextfont=dict(size=16),
                    hovertemplate='<b>%{x} <br><br>Sem Ações</b>'),

            go.Bar(x=lbls,
                    y=round(conc, 2),
                    name=nome_barra,
                    marker=dict(color='rgb(80, 196, 80)'),
                    text=conc,
                    textposition="inside",
                    insidetextanchor='middle',
                    textfont=dict(color="white"),
                    insidetextfont=dict(size=16),
                    hovertemplate='<b>%{x} <br><br>Concluído</b>'),
        ])

        fig.update_layout(title=dict(
            text=nome_barra,
            x=0.5, y=0.96,
            yanchor='top',
            font=dict(size=1)),

            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(
                family="Montserrat, monospace",
                color="rgba(22,58,138,1)",
                size=1),
            xaxis=dict(tickfont=dict(size=1)),
            barmode='stack')
        fig.update_xaxes(showgrid=False, tickangle=35, showticklabels=True)
        fig.update_yaxes(showgrid=True, showticklabels=True)
        fig.update_traces(showlegend=False)

        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        graph_json = json.loads(graph_json)
        graph_json['config'] = {'responsive': True, 'displayModeBar': False}
        graph_json = json.dumps(graph_json)

        return graph_json

    # FUNÇÃO PARA CRIAR O GRÁFICO DE PPRIORIZAÇÃO
    def graph_priority(dados):

        fig = go.Figure()

        cores = []
        for dia in dados['finalDate']:
            if dia + timedelta(days=1) < datetime.now():
                cores.append('rgb(181, 10, 10)')
            else:
                cores.append('rgb(221, 141, 0)')

        fig.add_trace(go.Scatter(x=[datetime.now().date(), datetime.now().date()], y=[0, 100], mode='lines',
                                    line=dict(color='black', dash='dash'), name='Hoje'))

        fig.add_trace(go.Scatter(
            name="Matriz de <br>Prioridade",
            x=dados['finalDate'], y=dados['firstGrade'],
            text=dados['title'],
            mode='markers',
            customdata="http://digitaljost.randon.com.br/demandas/detalhes?area=" + dados['AREA'] +
                        "&projeto=" + dados['projectId'],
            hovertemplate='<b>%{text}</b><br><br>Prazo: %{x}<br>Criticidade: %{y}',
            marker=dict(size=22, color=cores)  # Ajuste o tamanho dos pontos aumentando o valor
        ))

        fig.update_layout(title=dict(
            text="Matriz de Prioridade: Criticidade X Prazo",
            x=0.5,
            y=0.96,
            yanchor='top',
            font=dict(size=1)
        ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(
                family="Montserrat, monospace",
                color="rgba(22,58,138,1)",
                size=1),
            hoverlabel=dict(
                font_size=16
            ), showlegend=False, hovermode='closest')

        # Criação da figura
        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        graph_json = json.loads(graph_json)
        graph_json['config'] = {'responsive': True, 'displayModeBar': False}
        graph_json = json.dumps(graph_json)

        return graph_json

    # FUNÇÃO PARA FORMATAR FILTROS COM MULTIPLOS VALORES
    def format_condition(list_values):
        if list_values:
            condition = "IN ("
            for val in list_values:
                condition += f"'{val}', "
            condition = condition.rstrip(", ") + ")"
        else:
            condition = "LIKE '%%'"

        return condition

    # FUNÇÃO PARA RETORNAR A QUANTIDADE DE DEMANDAS/TAREFAS POR STATUS
    def create_count_column(spe_df, target_status):
        return spe_df.apply(lambda row: row['count'] if row['status'] == target_status else 0, axis=1)

    # INICIALIZA OS FILTROS E DADOS DO MÉTODO
    area = request.args['area']
    graphs = []
    data = request.get_json()

    going = data['andamento'][0]
    late = data['atrasado'][0]
    fisished = data['concluido'][0]
    families = data['familia']

    lider = format_condition(data['responsavel'])
    processo = format_condition(data['processo'])

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query_proj = f"""SELECT 
                        entryName, status, count, extra, name, QR, QR_MESA, AO, SP_3_EIXO, SP_SR, EE, PR, 
                        AL, VT, EA, PE, EC, finalDate, firstGrade, title, AREA, projectId    
                    FROM 
                        JDT_VIEW_DEMANDS_GRAPH
                    WHERE 
                        AREA = '{area}' AND name {lider} AND extra {processo} 
                        AND status IN ('{going}', '{late}', '{fisished}', 'Sem Ações')"""

        query_task = f"""SELECT 
                            entryName, status, count, extra, name, QR, QR_MESA, AO, SP_3_EIXO, SP_SR, EE, PR, AL, 
                            VT, EA, PE, EC, finalDate, firstGrade, title, AREA, projectId    
                        FROM 
                            JDT_VIEW_DEMANDS_TASKS_GRAPH
                        WHERE 
                            AREA = '{area}' AND name {lider} AND extra {processo} 
                            AND status IN ('{going}', '{late}', '{fisished}', 'Sem Ações')"""

        dProj = pd.read_sql(query_proj, cnnx)
        dTask = pd.read_sql(query_task, cnnx)

    if area == 'Engenharia de Dev. de Fornecedores':
        dProj['extra'] = dProj['entryName']
        dTask['extra'] = dTask['entryName']

    condition = dProj[families].eq(1).any(axis=1)
    dProj = dProj.drop(dProj[condition].index)
    condition = dTask[families].eq(1).any(axis=1)
    dTask = dTask.drop(dTask[condition].index)

    # GRÁFICO DE PIZZA DE STATUS DE DEMANDAS GERAL
    status = {'count': [0, 0, 0, 0], 'status': ['Atrasado', 'Concluído', 'Em Andamento', 'Sem Ações']}
    dStatus = pd.DataFrame(status)

    status_df = pd.concat([dProj, dStatus]).groupby('status')['count'].sum().reset_index()
    labels = status_df['status']
    values = status_df['count']

    title = 'Status das Demandas'
    template = '<b>%{label} <br><br>%{value} demandas<br>%{percent} do total</b>'
    graphs.append(graph_pizza(labels, values, title, True, template))

    # GRÁFICO DE PIZZA DE STATUS DE DEMANDAS POR PROCESSO
    dados = {'count': [0] * len(dProj['extra'].unique()), 'extra': dProj['extra'].unique().tolist()}
    dFamilie = pd.DataFrame(dados)

    status_df = pd.concat([dProj, dFamilie]).groupby('extra')['count'].sum().reset_index()
    labels = status_df['extra']
    values = status_df['count']

    title = 'Demandas por Processo'
    if area == 'Engenharia de Dev. de Fornecedores':
        title = 'Demandas por Entrada'

    template = '<b>%{label} <br><br>%{value} demandas<br>%{percent} do total</b>'
    graphs.append(graph_pizza(labels, values, title, False, template))

    # GRÁFICO DE BARRAS DE PROJETOS POR RESPONSÁVEL, MOSTRANDO OS STATUS DOS PROJETOS
    status_df = dProj.groupby(['name', 'status'])['count'].sum().reset_index()

    labels = status_df['name']
    val_going = create_count_column(status_df, "Em Andamento")
    val_late = create_count_column(status_df, "Atrasado")
    val_actions = create_count_column(status_df, "Sem Ações")
    val_finished = create_count_column(status_df, "Concluído")

    title = 'Projetos por Responsável'
    graphs.append(graph_bars(labels, val_going, val_late, val_actions, val_finished, title))

    # GRÁFICO DE BARRAS DE PROJETOS POR FAMILIA, MOSTRANDO OS STATUS DOS PROJETOS
    status_df = dProj[['QR', 'QR_MESA', 'AO', 'SP_3_EIXO', 'SP_SR', 'EE', 'PR', 'AL', 'VT', 'EA', 'PE', 'EC',
                        'status']].melt(id_vars=['status'], value_name='count').loc[lambda x: x['count'] == 1]
    status_df['count'] = status_df['count'].astype(int)
    status_df = status_df.groupby(['variable', 'status'])['count'].sum().reset_index()

    labels = status_df['variable']
    val_going = create_count_column(status_df, "Em Andamento")
    val_late = create_count_column(status_df, "Atrasado")
    val_actions = create_count_column(status_df, "Sem Ações")
    val_finished = create_count_column(status_df, "Concluído")

    title = 'Projetos por Familia'
    graphs.append(graph_bars(labels, val_going, val_late, val_actions, val_finished, title))

    # GRÁFICO MATRIZ PRIORIZAÇÃO X PRAZO
    dProj['finalDate'] = pd.to_datetime(dProj['finalDate'])
    graphs.append(graph_priority(dProj))

    # GRÁFICO DE PIZZA DE STATUS DAS TAREFAS GERAL
    status_df = pd.concat([dTask, dStatus]).groupby('status')['count'].sum().reset_index()
    labels = status_df['status']
    values = status_df['count']

    title = 'Status das Tarefas'
    template = '<b>%{label} <br><br>%{value} tarefas<br>%{percent} do total</b>'
    graphs.append(graph_pizza(labels, values, title, True, template))

    # GRÁFICO DE PIZZA DE STATUS DAS TAREFAS POR PROCESSO
    status_df = pd.concat([dTask, dFamilie]).groupby('extra')['count'].sum().reset_index()
    labels = status_df['extra']
    values = status_df['count']

    title = 'Tarefas por Processo'
    if area == 'Engenharia de Dev. de Fornecedores':
        title = 'Tarefas por Entrada'

    template = '<b>%{label} <br><br>%{value} tarefas<br>%{percent} do total</b>'
    graphs.append(graph_pizza(labels, values, title, False, template))

    # GRÁFICO DE BARRAS DE TAREFA POR RESPONSÁVEL, MOSTRANDO OS STATUS DOS PROJETOS
    status_df = dTask[['name', 'status', 'count']]
    status_df = status_df.groupby(['name', 'status'])['count'].sum().reset_index()

    labels = status_df['name']
    val_going = create_count_column(status_df, "Em Andamento")
    val_late = create_count_column(status_df, "Atrasado")
    val_actions = create_count_column(status_df, "Sem Ações")
    val_finished = create_count_column(status_df, "Concluído")

    title = 'Tarefas por Pessoa'
    graphs.append(graph_bars(labels, val_going, val_late, val_actions, val_finished, title))

    return json.dumps(graphs)
