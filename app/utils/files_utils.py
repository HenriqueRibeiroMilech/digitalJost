import openpyxl.utils.units
from openpyxl import load_workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Font, Side, Border, PatternFill
from openpyxl.styles.alignment import Alignment
import pandas as pd
import os
from datetime import datetime

from app.utils.db_utils import get_engine


def demands_file(id_proj):
    date = '_'.join([str(datetime.now().date()).split('-')[1], str(datetime.now().date()).split('-')[2]])

    query_01 = f"""SELECT 
                     areaName AS ÁREA, 
                     entryName AS ENTRADA,
                     userName AS LIDER,
                     title AS PROJETO,
                     status AS STATUS,
                     description AS DEMANDA, 
                     openDate AS DATA 
                FROM 
                    JDT_VIEW_DEMANDS
                WHERE 
                    projectId = '{id_proj}'"""
    query_02 = f"""SELECT 
                    taskId AS ID_TAREFA, 
                    text AS TAREFA, 
                    userName AS LIDER, 
                    areaName AS ÁREA, 
                    openDate AS DATA, 
                    finalDate AS PRAZO, 
                    conclusionDate AS CONCLUSÃO, 
                    observText AS OBSERVAÇÕES, 
                    status AS STATUS 
                FROM 
                    JDT_VIEW_DEMANDS_TASKS 
                WHERE 
                    projectId = '{id_proj}' 
                ORDER BY 
                    PRAZO DESC"""

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        df = pd.read_sql(query_01, cnnx)
        dx = pd.read_sql(query_02, cnnx)

    data = pd.to_datetime(df['DATA'][0]).strftime('%d/%m/%Y')

    formato = {"A": [],
               "B": [data, 'Área', 'Responsável', 'Entrada', 'Status', 'Descrição', df['DEMANDA'][0]],
               "C": [df['PROJETO'][0], df['ÁREA'][0], df['LIDER'][0], df['ENTRADA'][0], df['STATUS'][0],
                     'Descrição', df['DEMANDA'][0]],
               "D": [],
               'E': ['TAREFA'],
               'F': ['LIDER'],
               'G': ['ÁREA'],
               'H': ['PRAZO'],
               'I': ['CONCLUSÃO'],
               'J': ['OBSERVAÇÕES'],
               'K': ['STATUS']}

    formato['E'].extend(dx['TAREFA'].values.tolist())
    formato['F'].extend(dx['LIDER'].values.tolist())
    formato['G'].extend(dx['ÁREA'].values.tolist())
    formato['H'].extend(pd.to_datetime(dx['PRAZO']).dt.date.values.tolist())
    formato['I'].extend(pd.to_datetime(dx['PRAZO']).dt.date.values.tolist())
    formato['J'].extend(dx['OBSERVAÇÕES'].values.tolist())
    formato['K'].extend(dx['STATUS'].values.tolist())

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'DEMANDA'

    coluna = 1
    for chave, valores in formato.items():
        linha = 1
        for valor in valores:
            ws.cell(row=linha, column=coluna, value=valor)
            linha += 1

        coluna += 1

    borda_style = Side(style='thin')
    borda = Border(left=borda_style, right=borda_style, top=borda_style, bottom=borda_style)

    ws.insert_rows(1)
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 17
    ws.column_dimensions['C'].width = 40
    ws.column_dimensions['E'].width = 40
    ws.column_dimensions['F'].width = 30
    ws.column_dimensions['G'].width = 25
    ws.column_dimensions['G'].width = 25
    ws.column_dimensions['H'].width = 15
    ws.column_dimensions['I'].width = 20
    ws.column_dimensions['J'].width = 40
    ws.column_dimensions['k'].width = 15

    last_word = ''

    for line in range(1, ws.max_row + 1):
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row=line, column=col)
            cell.alignment = Alignment(horizontal="left")
            font = Font(name='Arial', size=14)
            cell.font = font

            if line != 1 and col != 1 and cell.value is not None:
                cell.border = borda
                ws.row_dimensions[line + 1].height = 19
                if last_word == cell.value and col < 4:
                    if last_word == df['DEMANDA'][0]:
                        ws.merge_cells(start_row=line, start_column=col - 1, end_row=line + 2, end_column=col)
                        cell = ws.cell(row=line, column=col - 1)
                    else:
                        ws.merge_cells(start_row=line, start_column=col - 1, end_row=line, end_column=col)
                        cell = ws.cell(row=line, column=col - 1)

            if (col > 4 and line != 2) or last_word == df['DEMANDA'][0]:
                font = Font(name='Arial', size=10)
                cell.font = font

            cell.alignment = Alignment(vertical='top', horizontal="left", wrap_text=True)

            last_word = cell.value

    wb.save(fr'{os.getcwd()}\app\static\uploads\default\{id_proj}_{date}.xlsx')

    return fr'{id_proj}_{date}.xlsx'

def print_label(requestId):

    requestId = str(requestId)

    date = '_'.join([str(datetime.now().date()).split('-')[1], str(datetime.now().date()).split('-')[2]])

    query = f"""SELECT 
                    T1.supplier
                    , T1.materId
                    , T1.drawId
                    , T1.qtd
                    , T1.descText
                    , FORMAT(T1.openDate, 'dd/MM/yyyy') AS openDate
                    , T1.prodFamily
                    , T1.obsText
                    , T5.name AS motive
                    , T6.name AS area
                    , T3.name
                    , T4.name AS areaName

                FROM JDT_REQUEST_LAB AS T1 
                    LEFT JOIN JDT_USER_DETAILS AS T3 ON T1.requesterId = T3.id 
                    LEFT JOIN JDT_GENERAL_AREA AS T4 ON T3.areaId = T4.areaId 
                    JOIN JDT_REQUEST_LAB_MOTIVES AS T5 ON T1.motive = T5.id
                    JOIN JDT_REQUEST_LAB_AREAS AS T6 ON T1.areaId = T6.id
                    
                WHERE T1.requestId = {requestId}"""

    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        df = pd.read_sql(query, cnnx)

    formato = {
        "JOST": ["Laboratório Controle e Experimental", "#_#_#Descrição conforme desenho:", df['descText'][0],
                 "#_#_#Código do Material:", df['materId'][0], "#_#_#Quantidade:",
                 df['qtd'][0], "#_#_#Área Responsável:", df['areaName'][0],
                 "#_#_#Solicitante:", df['name'][0], "#_#_#Área:", "#_#_#Motivo:",
                 "#_#_#Data de Solicitação:", df['openDate'][0], "#_#_#Observações:", df['obsText'][0]],
        "SSL" + str(requestId): ["Laboratório Controle e Experimental", "#_#_#Descrição conforme desenho:",
                                 df['descText'][0], "#_#_#Código do Desenho:",
                                 df['drawId'][0], "#_#_#Fornecedor:",
                                 df['supplier'][0], "#_#_#Área Responsável:", df['areaName'][0],
                                 "#_#_#Solicitante:",
                                 df['name'][0], df['area'][0], df['motive'][0],
                                 "#_#_#Data de Solicitação:", df['openDate'][0], "#_#_#Observações:",
                                 df['obsText'][0]]
    }
    arquivo_final = pd.DataFrame(formato)

    arquivo_final.to_excel(fr'{os.getcwd()}\app\static\uploads\default\{requestId}_{date}.xlsx', index=False,
                           header=True)

    wb = load_workbook(filename=fr'{os.getcwd()}\app\static\uploads\default\{requestId}_{date}.xlsx', data_only=True)
    ws = wb.worksheets[0]
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 30

    imagem = Image('app/static/images/new_jost_logo.jpg')
    imagem.anchor = 'A1'
    ws.row_dimensions[1].height = 40

    imagem.width = 100 * openpyxl.utils.units.points_to_pixels(1)
    imagem.height = 27 * openpyxl.utils.units.points_to_pixels(1)
    ws.add_image(imagem)

    borda_style = Side(style='thin')
    borda = Border(left=borda_style, right=borda_style, top=borda_style, bottom=borda_style)
    fill = PatternFill(fill_type="solid", fgColor="000000")
    last_word = ''

    for line in range(1, ws.max_row + 1):
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row=line, column=col)
            cell.alignment = Alignment(horizontal="left")
            font = Font(name='Arial', size=14)
            cell.font = font
            cell.border = borda
            ws.row_dimensions[line + 1].height = 19

            if "#_#_#" in str(cell.value):
                font = Font(name='Arial', b=True, size=13, color='ffffff')
                cell.font = font
                cell.fill = fill
                cell.value = str(cell.value).replace("#_#_#", "")

            if str(cell.value) == str("SSL" + requestId) or cell.value == 'JOST':
                font = Font(name='Arial', b=True, size=22, color='ffffff')
                cell.font = font
                cell.fill = fill
                cell.alignment = Alignment(horizontal="center", vertical='center')

            if (last_word == cell.value or cell.value is None) and col > 1:
                ws.merge_cells(start_row=line, start_column=col - 1, end_row=line, end_column=col)

                cell = ws.cell(row=line, column=col - 1)
                if last_word == "Laboratório Controle e Experimental":
                    font = Font(name='Arial', b=True, size=15)
                    cell.font = font
                    cell.alignment = Alignment(horizontal="center")
                if last_word == df['name'][0]:
                    font = Font(name='Arial', b=True, size=12)
                    cell.font = font
                    cell.alignment = Alignment(horizontal="left")
                if last_word == df['obsText'][0]:
                    font = Font(name='Arial', size=10)
                    cell.font = font
                    cell.alignment = Alignment(vertical='top', horizontal="left", wrap_text=True)

            last_word = cell.value

        ws.merge_cells("A18:B22")
    wb.save(fr'{os.getcwd()}\app\static\uploads\default\{requestId}_{date}.xlsx')

    return fr'{requestId}_{date}.xlsx'

def qsb_file():

    query = f"""SELECT 
                    type AS TIPO,
                    typeDesc AS LOCAL,
                    prodFamily AS FAMILIA,
                    CASE WHEN 
                        repeat = 0 
                        THEN 'Sim' 
                        ELSE 'Não'
                    END AS REINCIDENCIA,
                    shift as TURNO, 
                    description AS DESCRIÇÃO, 
                    prodCode AS 'CÓDIGO DE PRODUTO',
                    text1 AS CONTENÇÃO_1, text2 AS CONTENÇÃO_2, text3 AS CONTENÇÃO_3, 
                    CONCAT(DAY(openDate), '/', MONTH(openDate), '/', YEAR(openDate)) as DATA_ABERTURA
                FROM 
                    JDT_OPE_QUAL"""
    
    engine = get_engine('jdt')
    with engine.connect() as cnnx:
        df = pd.read_sql(query, cnnx)

    df.to_excel(fr'{os.getcwd()}\app\static\uploads\default\qsbDigital.xlsx', index=False, header=True)
    return fr'qsbDigital.xlsx'