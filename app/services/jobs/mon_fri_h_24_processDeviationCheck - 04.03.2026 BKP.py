from datetime import datetime
import pyodbc
import pandas as pd

from app.services.run_h_24_scheduler import env
from app.utils.constants import CNNX_JDT
from app.utils.email_utils import send_email_with_attachment

def default(logger):

    cnnx = pyodbc.connect(CNNX_JDT)
    cursor = cnnx.cursor()

    # ATUALIZA O DESVIO COMO EM ANDAMENTO
    def deviation_automatic_start(row):
        query_update = f"""UPDATE JDT_REQUEST_DEV SET
                                initDate = GETDATE(), 
                                status = 5
                            WHERE deviationId = '{row['deviationId']}'"""
        
        cursor.execute(query_update)

    # ATUALIZA O DESVIO COMO VENCIDO
    def deviation_automatic_end(row):
        query_update = f"""UPDATE JDT_REQUEST_DEV SET
                                status = 6
                            WHERE deviationId = '{row['deviationId']}'"""
        cursor.execute(query_update)

    # ATUALIZA O DESVIO COMO RECUSADO
    def deviation_automatic_refusal(row):
        query_update = f"""UPDATE JDT_REQUEST_DEV SET
                                status = 2
                            WHERE deviationId = '{row['deviationId']}'"""
        cursor.execute(query_update)


    # ATUALIZA AS APROVAÇÕES NULAS COMO RECUSADO, OBS: UTILIZA O USUÁRIO DO DIGITAL JOST
    def approvers_automatic_refusal(row):
        query_update = f"""UPDATE JDT_REQUEST_DEV_CONFIG_STATUS SET
                                approverId = 'Digital.jost', status = 2, textDenied = 'Reprovado automaticamente devido ao não retorno após 48h.'
                            WHERE deviationId = '{row['deviationId']}' and sectorId = {row['sectorId']}"""
        cursor.execute(query_update)

    # ENVIA UM E-MAIL PARA CADA DESVIO INFORMANDO QUE JÁ PODE SER RENOVADO
    def send_email_revision(row):
        query_mail = f"SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = '{row['userId']}'"
        user_mail = pd.read_sql(query_mail, cnnx)['companyEmail'].values.tolist()
        template = env.get_template('request.processDeviation/dev_email_revision.html')
        msg_html = template.render(id=row['deviationId'][:-2])
        send_email_with_attachment(
            subject=f'Desvio de processo - Nº {row["deviationId"]}',
            body=msg_html,
            to=user_mail,
            sender_name='Transformação Digital JOST',
            sender_email='noreply.digitaljost@randon.com.br'
        )   

    # ENVIA UM E-MAIL PARA CADA DESVIO PENDENTE DE APROVAÇÃO POR ÁREA
    def send_email_scheduled(row):
        query_mail = f"SELECT companyEmail FROM JDT_VIEW_REQUEST_DEV_APPROVERS WHERE sector = '{row['approverSector']}'"
        user_mail = pd.read_sql(query_mail, cnnx)['companyEmail'].values.tolist()
        template = env.get_template('request.processDeviation/dev_email_scheduled.html')
        msg_html = template.render(id=row['deviationId'][:-2], solicitante=row['name'])
        send_email_with_attachment(
            subject=f'Desvio de processo - Nº {row["deviationId"]}',
            body=msg_html,
            to=user_mail,
            sender_name='Transformação Digital JOST',
            sender_email='noreply.digitaljost@randon.com.br'
        )


    # VARIAVEL UTILIZADA PARA COMPARAR DATAS, PEGA O DATETIME ATUAL
    realTime = datetime.now()

    # ATUALIZA E ENVIA INFORMAÇÕES COM BASE NOS APROVADORES
    query = f"""SELECT * FROM JDT_VIEW_REQUEST_DEV_MANAGE"""

    df_manage = pd.read_sql(query, cnnx)
    df_manage['openDate'] = pd.to_datetime(df_manage['openDate'], format='%d/%m/%Y %H:%M:%S')

    # CONDIÇÃO - VERIFICA SE O DESVIO FOI APROVADO EM PELO MENOS 48H
    df_manage[((realTime - df_manage['openDate']).dt.days >= 2) & (df_manage['status'] == 0)].apply(approvers_automatic_refusal, axis=1)

    df_manage[df_manage['approverName'].isnull()].apply(send_email_scheduled, axis=1)

    # ATUALIZA AS INFORMAÇÕES COM BASE NO DESVIO E APROVADOR
    query = f"""SELECT * FROM JDT_REQUEST_DEV"""

    df = pd.read_sql(query, cnnx)
    df['initDate'] = pd.to_datetime(df['initDate'])
    df['finalDate'] = pd.to_datetime(df['finalDate'])
    df['openDate'] = pd.to_datetime(df['openDate'])

    # CONDIÇÃO - PRAZO DE FIM DE CONCESSAO SER DE 5 DIAS E ESTAR EM ANDAMENTO
    df[((datetime.now() - df['finalDate']).dt.days > -5)  & (df['status'].isin([5, 6]))].apply(send_email_revision, axis=1)

    # CONDIÇÃO - VERIFICA SE O DESVIO FOI APROVADO EM PELO MENOS 48H
    df[((realTime - df['openDate']).dt.days >= 2)  & (df['status'] == 0)].apply(deviation_automatic_refusal, axis=1)

    # CONDIÇÃO - VERIFICA SE O DESVIO JÁ FOI APROVADO
    df[(df['status'] == 1) & (df['initDate'] <= realTime)].apply(deviation_automatic_start, axis=1)    

    # CONDIÇÃO - VERIFICA SE O DESVIO ESTÁ EM ANDAMENTO
    df[(df['status'] == 5) & (df['finalDate'] < realTime)].apply(deviation_automatic_end, axis=1)

    cnnx.commit()
    cnnx.close()