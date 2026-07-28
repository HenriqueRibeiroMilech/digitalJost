"""
Arquivo: security.py
Módulo: Operation / SSMA

Objetivo:
    Este módulo contém as rotas Flask (Blueprint) responsáveis por:
      - Exibir o painel de SSMA (cruz/calendário)
      - Carregar eventos por mês/ano (endpoint POST para o front)
      - Adicionar uma nova ocorrência SSMA (GET/POST)
      - Listar ocorrências para edição (GET)
      - Editar ocorrência (GET/POST)
      - Remover ocorrência (POST)
      - Visualizar detalhe (view) de ocorrências em uma data (GET)

Autora:
    Dyevelenn de Oliveira Gomes

Data:
    2026-02-23

Observações importantes:
    - Algumas queries são montadas com f-string usando request.args diretamente.
      Isso pode abrir risco de SQL injection. Como a solicitação foi "não mudar o
      funcionamento", as queries foram mantidas iguais, mas o ponto está sinalizado.
"""

import shutil
from datetime import datetime
import pandas as pd
import json
import os

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import text

from app.utils.db_utils import engine_run_query, get_engine
from app.utils.dynamic_constants import getPlex
from app.utils.permissions import get_permission


# -----------------------------------------------------------------------------
# PERMISSÕES
# -----------------------------------------------------------------------------
# Permissão necessária para operar as rotas de SSMA que alteram dados (add/edit/remove).
p_ssma = get_permission('SSMA')

# Blueprint para agrupar rotas de Security/SSMA
operation_security_bp = Blueprint('operation_security', __name__)


@operation_security_bp.before_request
def route_auth():
    """
    Middleware executado antes de cada request do blueprint.

    Regras:
      1) Se o usuário não estiver logado, redireciona para login.
      2) Se não possuir permissão geral ('GENERAL'), retorna 403.

    Observação:
      - Isso protege todas as rotas desse blueprint.
    """
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))

    if not get_permission('GENERAL').can():
        return abort(403)


# -----------------------------------------------------------------------------
# CONSTANTES / LISTAS FIXAS
# -----------------------------------------------------------------------------
# Lista de danos possíveis (id, descrição) usada em telas de cadastro/edição.
_DAMAGE = [
    [0, 'Nenhum - sem lesão'],
    [1, 'Amputação de perna/mão, perda parcial da audição ou visão'],
    [2, 'Arranhão/Escoriação'],
    [3, 'Corte/enfermidade leve'],
    [4, 'Enfermidade permanente ou crítica'],
    [5, 'Fatalidade'],
    [6, 'Fratura grave de osso - mão/braço/perna'],
    [7, 'Fratura leve de ossos - dedos das mãos/dedos dos pés'],
    [8, 'Lesão significativa na cabeça'],
    [9, 'Lesão na coluna cervical'],
    [10, 'Paralisia'],
    [11, 'Perda de 1 ou mais dedos das mãos/dedos dos pés'],
    [12, 'Queimaduras graves']
]

# Lista de setores fixos (usada em formulários)
_SECTOR = [
    'Pré-fabricação',
    'Pré-montagem 1',
    'Pré-montagem 2',
    'Montagem 1',
    'Montagem 2',
    'Movimentação interna'
]

# Lista de contatos SSMA:
# chave = nome exibido, valor = [userContact, ramalContact]
_CONTACT = {
    "Vanessa dos Santos Dutra": ['00040019', 2902],
    "Edroaldo Rodrigues": ['edroaldo', 3470],
    "Guilherme de Carvalho Junior": ['00034055', 3470]
}


# -----------------------------------------------------------------------------
# ROTA: Painel principal SSMA (GET)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma', methods=['GET'])
def security_get():
    """
    Exibe a página principal (cruz/painel) do SSMA.

    O que faz:
      - Busca no banco a data do último acidente (definition = 'Acidente')
      - Calcula:
          dias_sem = dias desde o último acidente
          dias_ano = dias restantes (contagem regressiva de 365 dias)
      - Renderiza a página 'op_sec_cross.html' com dados do mês atual e contadores.
    """

    # Query calcula dias desde o último acidente e dias restantes do ano (até 365).
    query = """
        
        SELECT 
            ISNULL(DATEDIFF(DAY, MAX(date), GETDATE()), 0) AS dias_sem,
            CASE 
                WHEN MAX(date) IS NULL THEN 365
                WHEN DATEDIFF(DAY, MAX(date), GETDATE()) > 365 THEN 0
                ELSE 365 - DATEDIFF(DAY, MAX(date), GETDATE())
            END AS dias_ano
        FROM JDT_VIEW_OPE_SSMA
        WHERE definition = 'Acidente com Afastamento'

    """

    result = engine_run_query(query, 'jdt')

    # Caso a query não retorne linhas, define 0.
    dias_sem = int(result['dias_sem'][0]) if not result.empty else 0
    dias_ano = int(result['dias_ano'][0]) if not result.empty else 0

    return render_template(
        'operation.ssma/op_sec_cross.html',
        month=datetime.now().month,
        dias_sem=dias_sem,
        dias_ano=dias_ano
    )


# -----------------------------------------------------------------------------
# ROTA: Carregar entradas do mês (POST)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma', methods=['POST'])
def security_post():
    """
    Endpoint para retornar, via POST, a lista de ocorrências do mês/ano.

    Parâmetros esperados (query string):
      - year: ano (int)
      - month: mês (int)
      - state: (opcional) filtro por unidade (unit)

    Retorno:
      - JSON (string) contendo lista no formato:
        [[day, definition], [day, definition], ...]
    """

    # Validação básica dos parâmetros
    try:
        year = int(request.args['year'])
        month = int(request.args['month'])
    except (KeyError, ValueError):
        return abort(400, "Ano ou mês inválido.")

    # Parâmetros para query parametrizada (evita problemas no SQL)
    params = {'year': year, 'month': month}
    unit_filter = ""

    # Filtro opcional por unidade (state)
    if 'state' in request.args:
        try:
            unit = request.args['state']
            unit_filter = "AND unit = :unit"
            params['unit'] = unit
        except ValueError:
            return abort(400, "Unidade inválida.")

    query = f"""
        SELECT DAY(date) AS day, definition
        FROM JDT_VIEW_OPE_SSMA
        WHERE YEAR(date) = :year AND MONTH(date) = :month {unit_filter}
        ORDER BY date
    """

    df = engine_run_query(query, 'jdt', params)

    # Converte para lista simples para o front consumir
    entries = df[['day', 'definition']].values.tolist() if not df.empty else []

    return json.dumps(entries)


# -----------------------------------------------------------------------------
# ROTA: Formulário de adicionar ocorrência (GET)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma/add', methods=['GET'])
@p_ssma.require(403)
def security_add_get():
    """
    Exibe a tela de cadastro de ocorrência SSMA.

    O que carrega:
      - Coordenadores (JDT_VIEW_COORD)
      - Workcenters (mes + mic) para o combo de seleção
      - Listas fixas: danos, setor, contatos SSMA
    """

    # Lista de coordenadores
    query = """SELECT name, id FROM JDT_VIEW_COORD"""
    coord = engine_run_query(query, 'jdt').values.tolist()

    # Workcenters do MIC (local)
    query = """
        SELECT 
            GRUPO AS Workcenter_Group
            , LEFT(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) - 1) AS Workcenter_Code
            , SUBSTRING(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) + 1, LEN(NOME_MAQUINA)) AS Name
            , 1 AS Workcenter_Key
        FROM CONFIG_TABLET WHERE CT_PLEX IS NULL
    """
    mic_workcenters = engine_run_query(query, 'ftm')

    # Workcenters do MES (Plex)
    mes_workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]

    # Junta as listas, evitando duplicidade pelo Workcenter_Code
    workcenters = pd.concat([
        mes_workcenters[~mes_workcenters['Workcenter_Code'].isin(mic_workcenters['Workcenter_Code'])],
        mic_workcenters
    ])

    return render_template(
        'operation.ssma/op_sec_add.html',
        damage=_DAMAGE,
        coord=coord,
        workcenters=workcenters,
        concact=list(_CONTACT.keys()),   # obs: "concact" parece typo, mas mantido para não quebrar template
        sector=_SECTOR
    )


# -----------------------------------------------------------------------------
# ROTA: Receber cadastro de ocorrência (POST)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma/add', methods=['POST'])
@p_ssma.require(403)
def security_add_post():
    """
    Recebe dados do formulário (JSON) e arquivos de fotos para inserir uma ocorrência SSMA.

    Fluxo:
      1) Lê JSON do campo request.form['data'].
      2) Busca o próximo ID (MAX(id) + 1).
      3) Cria diretório para upload de imagens.
      4) Salva fotos enviadas.
      5) Insere registro na tabela JDT_OPE_SSMA.
      6) Redireciona para a tela principal.
    """

    # Formulário enviado pelo front em formato JSON dentro de request.form['data']
    form_data = json.loads(request.form['data'])

    # Próximo ID = MAX(id) + 1
    query = """SELECT MAX(id) as id FROM JDT_OPE_SSMA"""
    df = engine_run_query(query, 'jdt')
    val = int(df['id'][0]) + 1

    # Converte data do formato "YYYY-MM-DDTHH:MM" para "YYYY-MM-DD HH:MM"
    date = form_data['dataOcorr'].split('T')[0] + ' ' + form_data['dataOcorr'].split('T')[1]

    # Cria diretório para armazenar as imagens do ID
    directory_path = os.path.join('app', 'static', 'uploads', 'operation', 'ssma', str(val))
    if not os.path.exists(directory_path):
        os.mkdir(directory_path)

    # Salva imagens enviadas via multipart/form-data no campo "fotos"
    for file in request.files.getlist('fotos'):
        if file.filename != '':
            file.save(os.path.join(
                rf'{os.getcwd()}\app\static\uploads\operation\ssma\{val}',
                file.filename
            ))

    # Monta query de INSERT
    # ATENÇÃO: aqui existe SQL com interpolação de strings (risco de SQL injection).
    # Mantido para preservar funcionamento atual.
    query = f"""INSERT INTO JDT_OPE_SSMA VALUES ({val},
                '{json.dumps(form_data['evento'])}',
                '{json.dumps(form_data['classificação'])}',
                '{form_data['setor']}',
                '{form_data['equip']}',
                '{form_data['gerente']}',
                '{_CONTACT[form_data['ssmaContato']][0]}',
                '{_CONTACT[form_data['ssmaContato']][1]}',
                '--',
                '{form_data['local']}',
                '{form_data['coordenador']}',
                '{date}',
                '{form_data['condicoesGeral']}',
                '{form_data['causaRaiz']}',
                '{form_data['contencao']}',
                '{form_data['correcao']}',
                '--',
                '{json.dumps(form_data['imagens'])}',
                '{form_data['envolvido']}',
                '{form_data['ocorrencia']}',
                '{form_data['danoReal']}',
                '{form_data['danoPotencial']}',
                '{form_data['definicao']}',
                '{form_data['descricao']}',
                '{datetime.now().replace(microsecond=0)}',
                '{form_data['unidade']}')"""

    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        cnnx.execute(text(query))

    return redirect(url_for('operation_security.security_get'))


# -----------------------------------------------------------------------------
# ROTA: Selecionar ocorrência para edição (GET)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma/edit_select', methods=['GET'])
@p_ssma.require(403)
def security_select_get():
    """
    Exibe a tela de seleção de ocorrências para edição.

    Carrega:
      - lista de ocorrências (id, sector, local, date, definition, unit)
      - envia ao template em JSON para o front montar listagem/tabela
    """
    query = """SELECT id, sector, local, date, definition, unit as UNIDADE 
               FROM JDT_VIEW_OPE_SSMA 
               ORDER BY ID DESC"""
    df = engine_run_query(query, 'jdt').astype(str)

    return render_template('operation.ssma/op_seg_select.html', df=df.to_json())


# -----------------------------------------------------------------------------
# ROTA: Abrir edição de uma ocorrência (GET)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma/edit', methods=['GET'])
@p_ssma.require(403)
def security_detail_edit_get():
    """
    Exibe a tela de edição de uma ocorrência específica.

    Parâmetro esperado:
      - id: identificador do registro

    O que faz:
      - Busca coordenadores
      - Busca registro pelo id na tabela JDT_OPE_SSMA
      - Converte userContact para nome (com _CONTACT)
      - Converte involved para int
      - Monta workcenters (mes + mic)
      - Renderiza template de edição com dados e listas auxiliares
    """
    entry_id = request.args['id']

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = """SELECT name, id FROM JDT_VIEW_COORD"""
        coord = pd.read_sql(query, cnnx).values.tolist()

        query = f"""SELECT * FROM JDT_OPE_SSMA WHERE id = '{entry_id}'"""
        df = pd.read_sql(query, cnnx)

    # Mapeia código de userContact para nome exibido
    df['userContact'] = df['userContact'].map({v[0]: k for k, v in _CONTACT.items()})

    # involved como int para padronizar (ex.: 0/1)
    df['involved'] = df['involved'].astype(int)

    # Converte tudo em string (para facilitar serialização e preencher campos no template)
    df = df.astype(str)

    # Workcenters do MIC
    query = """
        SELECT 
            GRUPO AS Workcenter_Group
            , LEFT(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) - 1) AS Workcenter_Code
            , SUBSTRING(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) + 1, LEN(NOME_MAQUINA)) AS Name
            , 1 AS Workcenter_Key
        FROM CONFIG_TABLET WHERE CT_PLEX IS NULL
    """
    mic_workcenters = engine_run_query(query, 'ftm')

    # Workcenters do MES
    mes_workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]
    workcenters = pd.concat([
        mes_workcenters[~mes_workcenters['Workcenter_Code'].isin(mic_workcenters['Workcenter_Code'])],
        mic_workcenters
    ])

    return render_template(
        'operation.ssma/op_seg_edit.html',
        data=df.to_json(),
        id=entry_id,
        coord=coord,
        workcenters=workcenters,
        concact=list(_CONTACT.keys()),  # mantido para não quebrar template
        damage=_DAMAGE
    )


# -----------------------------------------------------------------------------
# ROTA: Salvar edição de uma ocorrência (POST)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma/edit', methods=['POST'])
@p_ssma.require(403)
def security_detail_edit_post():
    """
    Recebe dados do formulário de edição e atualiza a ocorrência.

    Fluxo:
      1) Carrega lista atual de imagens da ocorrência.
      2) Remove imagens marcadas para deletar (no disco e na lista).
      3) Salva novas fotos enviadas e adiciona à lista.
      4) Atualiza registro no banco (UPDATE).
      5) Redireciona para tela de seleção.
    """
    entry_id = request.args['id']

    # Obtém imagens atuais do banco
    query = f"""SELECT images FROM JDT_OPE_SSMA WHERE id = {entry_id}"""
    images = json.loads(engine_run_query(query, 'jdt')['images'][0])

    # Dados do formulário (JSON)
    form_data = json.loads(request.form['data'])

    # Remove imagens marcadas para deletar
    for image in form_data['deletar']:
        if image != "":
            images.remove(image)
            image_path = rf'{os.getcwd()}\app\static\uploads\operation\ssma\{entry_id}\{image}'
            if os.path.exists(image_path):
                os.remove(image_path)

    # Salva novas imagens enviadas
    for file in request.files.getlist('fotos'):
        if file.filename != '':
            file.save(os.path.join(
                rf'{os.getcwd()}\app\static\uploads\operation\ssma\{entry_id}',
                file.filename
            ))
            images.append(file.filename)

    # Ajusta data para o formato do banco
    date = form_data['dataOcorr'].split('T')[0] + ' ' + form_data['dataOcorr'].split('T')[1]

    # UPDATE no banco
    # ATENÇÃO: interpolação de strings em SQL (risco).
    # Mantido para preservar funcionamento atual.
    query = f"""UPDATE JDT_OPE_SSMA SET
                    event = '{json.dumps(form_data['evento'])}',
                    class = '{json.dumps(form_data['classificação'])}',
                    sector = '{form_data['setor']}',
                    equip = '{form_data['equip']}',
                    manager = '{form_data['gerente']}',
                    userContact = '{_CONTACT[form_data['ssmaContato']][0]}',
                    ramalContact = '{_CONTACT[form_data['ssmaContato']][1]}',
                    local = '{form_data['local']}',
                    coord = '{form_data['coordenador']}',
                    date = '{date}',
                    generalCondiction = '{form_data['condicoesGeral']}',
                    rootCause = '{form_data['causaRaiz']}',
                    containment = '{form_data['contencao']}',
                    solution = '{form_data['correcao']}',
                    images = '{json.dumps(images)}',
                    involved = '{form_data['envolvido']}',
                    type = '{form_data['ocorrencia']}',
                    realDamage = '{form_data['danoReal']}',
                    potencialDamage = '{form_data['danoPotencial']}',
                    definition = '{form_data['definicao']}',
                    description = '{form_data['descricao']}',
                    openDate = '{datetime.now().replace(microsecond=0)}',
                    unit = '{form_data['unidade']}'
                WHERE id = '{entry_id}'"""

    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        cnnx.execute(text(query))

    return redirect(url_for('operation_security.security_select_get'))


# -----------------------------------------------------------------------------
# ROTA: Remover uma ocorrência (POST)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma/remove', methods=['POST'])
@p_ssma.require(403)
def security_detail_remove_post():
    """
    Remove uma ocorrência do banco e apaga o diretório de imagens.

    Parâmetro esperado:
      - id (query string)

    Fluxo:
      1) DELETE no banco
      2) Remove diretório de uploads do ID
      3) Retorna mensagem simples
    """
    entry_id = request.args['id']

    query = f"""DELETE FROM JDT_OPE_SSMA WHERE id = '{entry_id}'"""
    engine = get_engine('jdt')
    with engine.begin() as cnnx:
        cnnx.execute(text(query))

    directory_path = os.path.join(
        os.getcwd(), 'app', 'static', 'uploads', 'operation', 'ssma', str(entry_id)
    )
    if os.path.exists(directory_path):
        shutil.rmtree(directory_path)

    return f'Deleted entry with ID = {entry_id}'


# -----------------------------------------------------------------------------
# ROTA: Visualizar detalhe (view) das ocorrências em uma data (GET)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma/view')
def security_detail_view_get():
    """
    Renderiza a tela de visualização (alerta) para uma data específica.

    Parâmetros esperados (query string):
      - year
      - month
      - day
      - state (opcional): filtro por unidade

    Fluxo:
      1) Monta filtro de unidade se existir.
      2) Ajusta day para dois dígitos quando menor que 10 (ex.: 09).
      3) Faz SELECT na view por intervalo de data daquele dia.
      4) Envia df.to_json() para o template, e a data separada.
    """

    aux = ""
    if 'state' in request.args:
        # ATENÇÃO: interpolação direta no SQL (risco). Mantido para não mudar.
        aux = f"AND unit = '{request.args['state']}'"

    year = request.args['year']
    month = request.args['month']
    day = int(request.args['day'])

    # Padroniza dia com zero à esquerda (ex.: 09)
    if day < 10:
        day = '0' + str(day)

    # ATENÇÃO: year/month/day inseridos diretamente no SQL.
    # Mantido para preservar o mesmo comportamento.
    query = f"""SELECT * FROM JDT_VIEW_OPE_SSMA WHERE date >= 
    '{year}-{month}-{day} 00:00:00' and date <= 
    '{year}-{month}-{day} 23:59:59' {aux}"""

    df = engine_run_query(query, 'jdt').astype(str)

    return render_template(
        'operation.ssma/op_seg_view.html',
        day=day,
        month=request.args['month'],
        year=request.args['year'],
        df=df.to_json()
    )