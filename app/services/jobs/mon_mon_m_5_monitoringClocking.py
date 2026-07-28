
import oracledb
import pandas as pd
import urllib

from sqlalchemy import create_engine, text

from app.utils.constants import CNNX_JDT

oracledb.init_oracle_client(lib_dir=r"C:\Oracle\instantclient_21_13")

def default(logger):
    
    # String de conexão SQLAlchemy para Oracle
    oracle_url = "oracle+oracledb://JOST_ROCKWEL:RANDON2022@10.168.74.106:1521/?service_name=EMRA"
    oracle_engine = create_engine(oracle_url)

    ora_query = """
            SELECT 
                MATRICULA AS registration
                , CCUS AS costCenter
                , DATA_MARCACAO AS clockDate
                , HORA_E1 AS entry1
                , HORA_S1 AS exit1
                , HORA_E2 AS entry2
                , HORA_S2 AS exit2
                , HORA_E3 AS entry3
                , HORA_S3 AS exit3
            FROM
                table(ponto.pack_dados_frequencia_randon.busca_dados_atuais(PCOD_EMPRESA => '2300'))
        """
    
    with oracle_engine.connect() as cnnx:
        ora_df_day = pd.read_sql(ora_query, cnnx)

    sqlserver_url = f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(CNNX_JDT)}"
    sqlserver_engine = create_engine(sqlserver_url)

    with sqlserver_engine.connect() as cnnx:
        cnnx.execute(text("DELETE FROM TEMP_OPERATORS_CLOCKING"))
        cnnx.commit()

    ora_df_day.to_sql(
        name='TEMP_OPERATORS_CLOCKING',
        con=sqlserver_engine,
        if_exists='append',  # só insere os dados, não recria a tabela
        index=False
    )
