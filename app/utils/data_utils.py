import pandas as pd
from datetime import datetime, time
import requests

from app.utils.db_utils import get_engine

# PEGA OS DADOS DE UM DATAFRAME E TRANSFORMA EM UMA LISTA DAS LINHAS DAS TABELAS,
# CADA LINHA TAMBÉM CORRESPONDE A OUTRA LISTA EX; [['VALOR_COL1_LIN1'], ['VALOR_COL1_LIN2'], ['VALOR_COL1_LIN2']]
def config_table(sql_data):
    table = [
        sql_data.columns.tolist()]

    index = 0
    for line in sql_data.values.tolist():
        for n in range(len(line)):
            line[n] = ''.join([char for char in str(line[n]) if char != "'"])

        index += 1
        table.append(line)

    return table

# FUNÇÃO DE FORMATAÇÃO DE STRING DE DATA - DE yyyy-mm-dd PARA dd-mm-yyyy.
def format_date(date_str):
    date_str = str(date_str)
    print(date_str)
    if ':' in date_str:
        date_str = date_str.split(' ')[0]

    formatted_date = date_str.split('-')[2] + '/' + date_str.split('-')[1] + '/' + date_str.split('-')[0]

    return formatted_date

# FUNÇÃO GLOBAL QUE RETORNA OS VALORES ÚNICOS EM UMA COLUNA DE UMA TABELA DO SQL
def return_options(query_str, col, engine_name="jdt"):
    engine = get_engine(engine_name)
    with engine.connect() as cnnx:
        options_data = pd.read_sql(query_str, cnnx)
    options = list(dict.fromkeys(options_data[col]).keys())
    options.sort()

    return options

def get_current_shift():
    day_time = datetime.now().time().replace(microsecond=0)
    week_day = datetime.now().weekday()
    t1 = time(7, 12, 0)
    t2 = time(17, 0, 0)
    t3 = time(2, 12, 0)

    if week_day == 0:
        t3 = time(0, 0, 0)

    if t2 > day_time >= t1:
        curr_shift = [t1, 'TURNO 1']
    elif day_time >= t2:
        curr_shift = [t2, 'TURNO 2']
    else:
        curr_shift = [t3, 'TURNO 3']

    return curr_shift


def POST_WITH_AUTH(url, auth, json_data):
    response = requests.post(url, auth=auth, json=json_data, verify=False)
    return response.json()