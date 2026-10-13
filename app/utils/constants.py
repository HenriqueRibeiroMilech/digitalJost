# VARIAVEIS GLOBAIS FIXAS
# REGRA: VARIAVEIS GLOBAIS DEVEM TER NOME TOTALMENTE MAISCULO

import os

from backend.platform.environment import required_env


ENV = 'prod'

# LISTAS DE GESTORES PARA CONFIGURAÇÃO AUTOMATICA DOS USUÁRIOS
# ALERTA DE DESATUALIZAÇÃO -> VERIFICAR CÓDIGO PEGANDO DADOS DO BANCO
COORD = ['tobias', 'leonidas', 'tborelli', 'alexande', 'mtmolon', '00040721', 'jonesb', '00044247', '00029227']
LEADER = ['eliasg', '00028107','richer','santos','00039148','00023851','00040129']

# LISTA DAS APLICAÇÕES E DAS PERMISSÕES DESATIVADAS, OS DADOS SÃO PREENCHIDOS VIRTUALMENTE
# DIGITAL.JOST/ADMIN
OFF_APLICATIONS = []
OFF_ROLES = []

# VARIAVEIS DE CONEXÃO COM O PLEX
MES_MAIN_USER = 'JostBrasilDigitalWs@plex.com'
MES_MAIN_PASSWORD = '508c9ad-73a6-4'

# CONEXÃO PRINCIPAL - BASE DA TRANSFORMAÇÃO DIGITAL
CNNX_JDT = required_env("DJ_TD_ODBC_CONNECTION_STRING")

# CONEXÃO PARA BASE DE DADOS DA FÁBRICA MIC
CNNX_FTM = (r"Driver={ODBC Driver 18 for SQL Server};"
            r"Server=clt-sql-03\inssql03;"
            r"Database=FTMETRICS_JOST;"
            r"UID=transformacaodigital_jost;"
            r"PWD=E7B?giz@KB&28n01;"
            r"TrustServerCertificate=yes;")

# CONEXÃO PARA BASE DE DADOS PLEX
CNNX_PLEX = (r"Driver={ODBC Driver 18 for SQL Server};"
            r"Server=CLT-SQL-01\INSSQL01;"
            r"Database=JOST_INTEGRATION_PRD;"
            r"UID=JOST_INTEGRATION_PRD;"
            r"PWD=L2OGiEaY2OScB7Wg;"
            r"TrustServerCertificate=yes;")

# CONEXÃO PARA BASE DE DADOS QAS PLEX
CNNX_PLEX_TEST = (r"Driver={ODBC Driver 18 for SQL Server};"
            r"Server=VQW-CSL-SQL01A\INSSQL01;"
            r"Database=JOST_INTEGRATION_QAS;"
            r"UID=JOSTINTEGRATIONQASUser;"
            r"PWD=gdpHNxX6UajbMMtl;"
            r"TrustServerCertificate=yes;")

# CONEXÃO PARA BASE DE DADOS DA RASTREABILIDADE DA QUINTA RODA
CNNX_TRACE_QR = (r"Driver={ODBC Driver 18 for SQL Server};"
            r"Server=CLT-SQL-01\INSSQL01;"
            r"Database=Rastreabilidade;"
            r"UID=rastreabilidade;"
            r"PWD=m7Rkek&$G$XsIN;"
            r"TrustServerCertificate=yes;")

APP_PATH = os.getcwd()