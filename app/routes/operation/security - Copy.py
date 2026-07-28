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
"""

import shutil
from datetime import datetime
from bisect import bisect_left
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
p_ssma = get_permission('SSMA')
operation_security_bp = Blueprint('operation_security', __name__)


@operation_security_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))

    if not get_permission('GENERAL').can():
        return abort(403)


# -----------------------------------------------------------------------------
# CONSTANTES / LISTAS FIXAS
# -----------------------------------------------------------------------------
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

_SECTOR = [
    'Pré-fabricação',
    'Pré-montagem 1',
    'Pré-montagem 2',
    'Montagem 1',
    'Montagem 2',
    'Movimentação interna'
]

_CONTACT = {
    "Vanessa dos Santos Dutra": ['00040019', 2902],
    "Edroaldo Rodrigues": ['edroaldo', 3470],
    "Guilherme de Carvalho Junior": ['00034055', 3470]
}


# -----------------------------------------------------------------------------
# Funções auxiliares (por mês/ano = dias marcados na cruz)
# -----------------------------------------------------------------------------
def get_available_ssma_dates_by_month(year: int, month: int, unit: str | None = None) -> list[str]:
    """
    Retorna lista ordenada de datas (YYYY-MM-DD) que possuem ocorrências SSMA
    dentro do mês/ano informado.
    """
    params = {"year": year, "month": month}
    unit_filter = ""

    if unit:
        unit_filter = "AND unit = :unit"
        params["unit"] = unit

    query = f"""
        SELECT DISTINCT CONVERT(date, [date]) AS d
        FROM JDT_VIEW_OPE_SSMA
        WHERE YEAR([date]) = :year
          AND MONTH([date]) = :month
          {unit_filter}
        ORDER BY d
    """

    df_dates = engine_run_query(query, "jdt", params)
    if df_dates.empty:
        return []

    return df_dates["d"].astype(str).tolist()


def pick_marked_date(requested_iso: str, available_dates: list[str], direction: str = "next") -> str | None:
    """
    requested_iso: 'YYYY-MM-DD'
    available_dates: lista ordenada ISO
    direction:
      - 'next' -> primeira data marcada >= requested
      - 'prev' -> última data marcada <= requested
    """
    if not available_dates:
        return None

    pos = bisect_left(available_dates, requested_iso)

    if direction == "next":
        return available_dates[pos] if pos < len(available_dates) else available_dates[-1]
    else:
        return available_dates[pos - 1] if pos > 0 else available_dates[0]


# -----------------------------------------------------------------------------
# ✅ NOVO: helpers globais (permite navegar para outro mês/ano) - CORRIGIDO
# -----------------------------------------------------------------------------
def get_next_marked_date_global(requested_iso: str, unit: str | None = None) -> str | None:
    """
    Retorna a PRÓXIMA data marcada (>) em TODO o histórico (qualquer mês/ano).
    Formato ISO 'YYYY-MM-DD'.
    """
    params = {"requested": requested_iso}
    unit_filter = ""

    if unit:
        unit_filter = "AND unit = :unit"
        params["unit"] = unit

    query = f"""
        SELECT TOP 1 CONVERT(date, [date]) AS d
        FROM JDT_VIEW_OPE_SSMA
        WHERE CONVERT(date, [date]) > :requested
          {unit_filter}
        ORDER BY d ASC
    """

    df = engine_run_query(query, "jdt", params)
    if df.empty:
        return None

    return str(df["d"].iloc[0])


def get_prev_marked_date_global(requested_iso: str, unit: str | None = None) -> str | None:
    """
    Retorna a data marcada ANTERIOR (<) em TODO o histórico (qualquer mês/ano).
    Formato ISO 'YYYY-MM-DD'.
    """
    params = {"requested": requested_iso}
    unit_filter = ""

    if unit:
        unit_filter = "AND unit = :unit"
        params["unit"] = unit

    query = f"""
        SELECT TOP 1 CONVERT(date, [date]) AS d
        FROM JDT_VIEW_OPE_SSMA
        WHERE CONVERT(date, [date]) < :requested
          {unit_filter}
        ORDER BY d DESC
    """

    df = engine_run_query(query, "jdt", params)
    if df.empty:
        return None

    return str(df["d"].iloc[0])


# -----------------------------------------------------------------------------
# ROTA: Painel principal SSMA (GET)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma', methods=['GET'])
def security_get():

    query = """
        SELECT 
            DATEDIFF(DAY, MAX(date), GETDATE()) AS dias_sem,
            CASE 
                WHEN MAX(date) IS NULL THEN 0
                ELSE CASE WHEN DATEDIFF(DAY, MAX(date), GETDATE()) > 365 THEN 0 ELSE 365 - DATEDIFF(DAY, MAX(date), GETDATE()) END
            END AS dias_ano
        FROM JDT_VIEW_OPE_SSMA
        WHERE definition = 'Acidente'
    """

    result = engine_run_query(query, 'jdt')

    dias_sem = int(result['dias_sem'][0]) if not result.empty else 0
    dias_ano = int(result['dias_ano'][0]) if not result.empty else 0

    # ✅ ALTERAÇÃO MÍNIMA: aceitar month/year/state via querystring (se existir)
    now = datetime.now()
    try:
        month = int(request.args.get("month", now.month))
        year = int(request.args.get("year", now.year))
    except ValueError:
        month = now.month
        year = now.year

    if month < 1 or month > 12:
        month = now.month

    state = request.args.get("state", "Geral")

    return render_template(
        'operation.ssma/op_sec_cross.html',
        month=month,
        year=year,      # ✅ novo
        state=state,    # ✅ novo
        dias_sem=dias_sem,
        dias_ano=dias_ano
    )


# -----------------------------------------------------------------------------
# ROTA: Carregar entradas do mês (POST)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma', methods=['POST'])
def security_post():

    try:
        year = int(request.args['year'])
        month = int(request.args['month'])
    except (KeyError, ValueError):
        return abort(400, "Ano ou mês inválido.")

    params = {'year': year, 'month': month}
    unit_filter = ""

    if 'state' in request.args:
        unit = request.args['state']
        unit_filter = "AND unit = :unit"
        params['unit'] = unit

    query = f"""
        SELECT DAY(date) AS day, definition
        FROM JDT_VIEW_OPE_SSMA
        WHERE YEAR(date) = :year AND MONTH(date) = :month {unit_filter}
        ORDER BY date
    """

    df = engine_run_query(query, 'jdt', params)
    entries = df[['day', 'definition']].values.tolist() if not df.empty else []

    return json.dumps(entries)


# -----------------------------------------------------------------------------
# ROTA: Formulário de adicionar ocorrência (GET)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma/add', methods=['GET'])
@p_ssma.require(403)
def security_add_get():

    query = """SELECT name, id FROM JDT_VIEW_COORD"""
    coord = engine_run_query(query, 'jdt').values.tolist()

    query = """
        SELECT 
            GRUPO AS Workcenter_Group
            , LEFT(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) - 1) AS Workcenter_Code
            , SUBSTRING(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) + 1, LEN(NOME_MAQUINA)) AS Name
            , 1 AS Workcenter_Key
        FROM CONFIG_TABLET WHERE CT_PLEX IS NULL
    """
    mic_workcenters = engine_run_query(query, 'ftm')
    mes_workcenters = getPlex('workcenters')[['Workcenter_Group', 'Workcenter_Code', 'Name', 'Workcenter_Key']]

    workcenters = pd.concat([
        mes_workcenters[~mes_workcenters['Workcenter_Code'].isin(mic_workcenters['Workcenter_Code'])],
        mic_workcenters
    ])

    return render_template(
        'operation.ssma/op_sec_add.html',
        damage=_DAMAGE,
        coord=coord,
        workcenters=workcenters,
        concact=list(_CONTACT.keys()),
        sector=_SECTOR
    )


# -----------------------------------------------------------------------------
# ROTA: Receber cadastro de ocorrência (POST)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma/add', methods=['POST'])
@p_ssma.require(403)
def security_add_post():

    form_data = json.loads(request.form['data'])

    query = """SELECT COALESCE(MAX(id), 0) as id FROM JDT_OPE_SSMA"""
    df = engine_run_query(query, 'jdt')
    val = int(df['id'][0]) + 1

    date_str = form_data['dataOcorr'].split('T')[0] + ' ' + form_data['dataOcorr'].split('T')[1]

    directory_path = os.path.join('app', 'static', 'uploads', 'operation', 'ssma', str(val))
    os.makedirs(directory_path, exist_ok=True)

    for file in request.files.getlist('fotos'):
        if file.filename != '':
            file.save(os.path.join(
                rf'{os.getcwd()}\app\static\uploads\operation\ssma\{val}',
                file.filename
            ))

    query = f"""
    INSERT INTO JDT_OPE_SSMA (
        id,
        event,
        [class],
        sector,
        section,
        equip,
        manager,
        userContact,
        ramalContact,
        local,
        coord,
        date,
        generalCondiction,
        rootCause,
        containment,
        solution,
        images,
        involved,
        type,
        realDamage,
        potencialDamage,
        definition,
        description,
        openDate,
        unit
    ) VALUES (
        {val},
        '{json.dumps(form_data['evento'])}',
        '{json.dumps(form_data['classificação'])}',
        '{form_data['setor']}',
        '--',
        '{form_data['equip']}',
        '{form_data['gerente']}',
        '{_CONTACT[form_data['ssmaContato']][0]}',
        '{_CONTACT[form_data['ssmaContato']][1]}',
        '{form_data['local']}',
        '{form_data['coordenador']}',
        '{date_str}',
        '{form_data['condicoesGeral']}',
        '{form_data['causaRaiz']}',
        '{form_data['contencao']}',
        '{form_data['correcao']}',
        '{json.dumps(form_data['imagens'])}',
        '{form_data['envolvido']}',
        '{form_data['ocorrencia']}',
        '{form_data['danoReal']}',
        '{form_data['danoPotencial']}',
        '{form_data['definicao']}',
        '{form_data['descricao']}',
        '{datetime.now().replace(microsecond=0)}',
        '{form_data['unidade']}'
    )
    """

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

    entry_id = request.args['id']

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        query = """SELECT name, id FROM JDT_VIEW_COORD"""
        coord = pd.read_sql(query, cnnx).values.tolist()

        query = f"""SELECT * FROM JDT_OPE_SSMA WHERE id = '{entry_id}'"""
        df = pd.read_sql(query, cnnx)

    df['userContact'] = df['userContact'].map({v[0]: k for k, v in _CONTACT.items()})
    df['involved'] = df['involved'].astype(int)
    df = df.astype(str)

    query = """
        SELECT 
            GRUPO AS Workcenter_Group
            , LEFT(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) - 1) AS Workcenter_Code
            , SUBSTRING(NOME_MAQUINA, CHARINDEX('-', NOME_MAQUINA) + 1, LEN(NOME_MAQUINA)) AS Name
            , 1 AS Workcenter_Key
        FROM CONFIG_TABLET WHERE CT_PLEX IS NULL
    """
    mic_workcenters = engine_run_query(query, 'ftm')

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
        concact=list(_CONTACT.keys()),
        damage=_DAMAGE
    )


# -----------------------------------------------------------------------------
# ROTA: Salvar edição de uma ocorrência (POST)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma/edit', methods=['POST'])
@p_ssma.require(403)
def security_detail_edit_post():

    entry_id = request.args['id']

    query = f"""SELECT images FROM JDT_OPE_SSMA WHERE id = {entry_id}"""
    images = json.loads(engine_run_query(query, 'jdt')['images'][0])

    form_data = json.loads(request.form['data'])

    for image in form_data['deletar']:
        if image != "":
            images.remove(image)
            image_path = rf'{os.getcwd()}\app\static\uploads\operation\ssma\{entry_id}\{image}'
            if os.path.exists(image_path):
                os.remove(image_path)

    for file in request.files.getlist('fotos'):
        if file.filename != '':
            file.save(os.path.join(
                rf'{os.getcwd()}\app\static\uploads\operation\ssma\{entry_id}',
                file.filename
            ))
            images.append(file.filename)

    date_str = form_data['dataOcorr'].split('T')[0] + ' ' + form_data['dataOcorr'].split('T')[1]

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
                    date = '{date_str}',
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
# ✅ ROTA /op/ssma/view (agora navega dentro do mês e entre meses/anos)
# -----------------------------------------------------------------------------
@operation_security_bp.route('/op/ssma/view')
def security_detail_view_get():

    unit = request.args.get("state")

    try:
        year = int(request.args['year'])
        month = int(request.args['month'])
        day = int(request.args['day'])
    except (KeyError, ValueError):
        return abort(400, "Parâmetros inválidos. Use day, month, year.")

    nav = request.args.get("nav")  # "next" | "prev" | None
    requested_iso = f"{year:04d}-{month:02d}-{day:02d}"

    # ✅ navegação GLOBAL (pode mudar mês/ano)
    if nav in ("next", "prev"):
        if nav == "next":
            best = get_next_marked_date_global(requested_iso, unit)
        else:
            best = get_prev_marked_date_global(requested_iso, unit)

        if best:
            y, m, d = best.split("-")
            args = {"year": int(y), "month": int(m), "day": int(d)}
            if unit:
                args["state"] = unit
            return redirect(url_for('operation_security.security_detail_view_get', **args))

    # ✅ lista de dias marcados do mês atual (igual cruz)
    available_dates = get_available_ssma_dates_by_month(year, month, unit)

    # ✅ se o dia não estiver marcado, redireciona para o próximo marcado (dentro do mês)
    if available_dates and requested_iso not in available_dates:
        best = pick_marked_date(requested_iso, available_dates, direction="next")
        if best:
            y, m, d = best.split("-")
            args = {"year": int(y), "month": int(m), "day": int(d)}
            if unit:
                args["state"] = unit
            return redirect(url_for('operation_security.security_detail_view_get', **args))

    # filtro unidade (mesmo comportamento)
    aux = ""
    if unit:
        aux = f"AND unit = '{unit}'"

    query = f"""SELECT * FROM JDT_VIEW_OPE_SSMA WHERE [date] >= 
    '{year}-{month:02d}-{day:02d} 00:00:00' and [date] <= 
    '{year}-{month:02d}-{day:02d} 23:59:59' {aux}"""

    df = engine_run_query(query, 'jdt').astype(str)

    return render_template(
        'operation.ssma/op_seg_view.html',
        day=day,
        month=month,
        year=year,
        df=df.to_json(),
        available_dates=available_dates
    )