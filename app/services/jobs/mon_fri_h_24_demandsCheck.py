from datetime import datetime
import pyodbc
import pandas as pd

from app.services.run_h_24_scheduler import env
from app.utils.constants import CNNX_JDT
from app.utils.email_utils import send_email_with_attachment


def default(logger):
    cnnx = pyodbc.connect(CNNX_JDT)

    # UPDATE NOTAS E STATUS DAS DEMANDAS
    query = f"""SELECT
                    projectId,
                    finalDate, 
                    status, 
                    firstGrade 
                FROM JDT_DEMANDS WHERE status <> 'Concluído'"""

    df = pd.read_sql(query, cnnx)
    df['finalDate'] = pd.to_datetime(df['finalDate']).dt.date

    for i in df.index:

        if not pd.isna(df['finalDate'][i]):

            prazo = df['finalDate'][i]

            diferenca = min(max((prazo - datetime.now().date()).days, 1), 14)
            valor_dif = 1 + (3 - 1) * (1 - (diferenca - 1) / 13)

            if diferenca < 0:
                query = f"""UPDATE JDT_DEMANDS SET status = 'Atrasado' WHERE projectId = '{df['projectId'][i]}'"""
                cnnx.execute(query)

            if pd.notna(df['firstGrade'][i]):
                nota = "'" + str((valor_dif * int(df['firstGrade'][i]) * 100) / 300) + "'"
            else:
                nota = 'NULL'

            query = f"UPDATE JDT_DEMANDS SET finalGrade = {nota} WHERE projectId = '{df['projectId'][i]}'"
            cnnx.execute(query)

    # UPDATE DOS STATUS DAS TAREFAS
    # EMAILS SÃO ENVIADOS EM CASO DE PRAZO ATRASADO
    query = f"""SELECT 
                    T1.taskId, 
                    T1.text, 
                    T1.userId, 
                    T1.openDate, 
                    T1.finalDate, 
                    T1.status,
                    T1.projectId, 
                    T2.title, 
                    T2.aplicationArea 
                FROM JDT_DEMANDS_TASKS AS T1 
                JOIN JDT_DEMANDS AS T2 ON T1.projectId = T2.projectId"""
    
    df = pd.read_sql(query, cnnx)
    df['finalDate'] = pd.to_datetime(df['finalDate'])

    for i in df.index:

        query_area = f"""SELECT name FROM JDT_ROLES WHERE roleId = '{df["aplicationArea"][i]}'"""
        area = pd.read_sql(query_area, cnnx)['name'][0]

        if df['status'][i] != 'Concluído' and df['userId'][i] is not None:

            prazo = df['finalDate'][i]
            diferenca = prazo - pd.Timestamp(datetime.now().date())
            if diferenca.days == 3:
                query = f"SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = '{df['userId'][i]}'"
                user_mail = pd.read_sql(query, cnnx)['companyEmail']
                if len(user_mail) != 0:
                    template = env.get_template('demands/gestao_demandas_email_prazo.html')
                    msg_html = template.render(
                        demanda=df["title"][i], area=area,
                        projeto=df["projectId"][i],
                        tarefa=df['text'][i]
                    )
                    send_email_with_attachment(
                        subject=f'Tarefa com prazo com vencimento próximo - ID {df["taskId"][i]}',
                        body=msg_html,
                        to=user_mail[0],
                        sender_name='Transformação Digital JOST',
                        sender_email='noreply.digitaljost@randon.com.br'
                    )

            elif diferenca.days < 0:
                query = f"""UPDATE JDT_DEMANDS_TASKS SET 
                                status = 'Atrasado'
                            WHERE taskId = '{df['taskId'][i]}'"""
                cnnx.execute(query)

                query = f"SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = '{df['userId'][i]}'"
                user_mail = pd.read_sql(query, cnnx)['companyEmail']

                if len(user_mail) != 0:
                    template = env.get_template('demands/gestao_demandas_email_atrasado.html')
                    msg_html = template.render(
                        demanda=df["title"][i], area=area,
                        projeto=df["projectId"][i],
                        tarefa=df['text'][i]
                    )
                    send_email_with_attachment(
                        subject=f'Tarefa com prazo vencido - ID {df["taskId"][i]}',
                        body=msg_html,
                        to=user_mail[0],
                        sender_name='Transformação Digital JOST',
                        sender_email='noreply.digitaljost@randon.com.br'
                    )

    cnnx.commit()
    cnnx.close()
