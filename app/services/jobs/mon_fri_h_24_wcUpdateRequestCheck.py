import pyodbc
import pandas as pd

from app.services.run_h_24_scheduler import env
from app.utils.constants import CNNX_JDT
from app.utils.email_utils import send_email_with_attachment


def default(logger):
    cnnx = pyodbc.connect(CNNX_JDT)

    def call_mail_function(row):

        query_mail = f"SELECT companyEmail FROM JDT_USER_DETAILS WHERE id = '{row['approver']}'"
        user_mail = pd.read_sql(query_mail, cnnx)['companyEmail'][0]
        if row['counts'] > 0:
            template = env.get_template('request.stopChanges/stopChanges_email_pending.html')
            msg_html = template.render(num=row['counts'])
            send_email_with_attachment(
                subject=f'{row["counts"]} solicitações de alteração de paradas aguardam sua avaliação!',
                body=msg_html,
                to=user_mail,
                sender_name='Transformação Digital JOST',
                sender_email='noreply.digitaljost@randon.com.br'
            )

    query = """SELECT T4.approverWaiting AS approver, COUNT(T4.approverWaiting) AS counts FROM
        (SELECT approverWaiting FROM 
            (SELECT 
            (CASE WHEN approver1 != approver2 AND approverStatus1 = 0 THEN approver1 ELSE NULL 
            END) 
            AS approverWaiting FROM JDT_REQUEST_STOPCHANGES WHERE finalDate IS NULL) T1
        WHERE approverWaiting IS NOT NULL
        UNION ALL
        SELECT approverWaiting FROM 
            (SELECT 
            (CASE WHEN approver1 != approver2 AND approverStatus2 = 0 THEN approver2 ELSE NULL 
            END) 
            AS approverWaiting FROM JDT_REQUEST_STOPCHANGES WHERE finalDate IS NULL) T2
        WHERE approverWaiting IS NOT NULL
        UNION ALL
        SELECT approverWaiting FROM 
            (SELECT 
            (CASE WHEN approver1 = approver2 AND (approverStatus1 = 0 OR approverStatus2 = 0) THEN 
            approver2 ELSE NULL END) AS approverWaiting FROM JDT_REQUEST_STOPCHANGES WHERE 
            finalDate IS NULL) T3
        WHERE approverWaiting IS NOT NULL) T4
    GROUP BY T4.approverWaiting"""

    df = pd.read_sql(query, cnnx)
    df.apply(call_mail_function, axis=1)

    cnnx.close()