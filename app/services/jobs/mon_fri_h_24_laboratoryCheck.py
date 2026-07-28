import pyodbc
import pandas as pd
from datetime import datetime, timedelta

from app.services.run_h_24_scheduler import env
from app.utils.constants import CNNX_JDT
from app.utils.email_utils import send_email_with_attachment


def _count_business_days(start_date, end_date):
    """
    Conta dias úteis (sem sábado e domingo) entre duas datas.
    
    Args:
        start_date: Data de início
        end_date: Data de fim
        
    Returns:
        Número de dias úteis
    """
    current = start_date
    business_days = 0
    
    while current <= end_date:
        # 0-4 = segunda a sexta, 5-6 = sábado e domingo
        if current.weekday() < 5:
            business_days += 1
        current += timedelta(days=1)
    
    return business_days


def default(logger):

    cnnx = pyodbc.connect(CNNX_JDT)

    # Buscar SSLs com status "Aguardando Retirada" (status = 3)
    # que estão há mais de 5 dias úteis sem serem retiradas
    query = """
        SELECT 
            T1.requestId,
            T1.requesterId,
            T1.endDate,
            T1.areaId,
            CASE 
                WHEN T1.areaId = 1 THEN 'dimensional'
                WHEN T1.areaId = 2 THEN 'material'
                ELSE 'dimensional'
            END as areaName,
            T2.companyEmail as requester_email,
            T2.name as requester_name,
            T2.managerId,
            T3.companyEmail as manager_email,
            T3.name as manager_name
        FROM 
            JDT_REQUEST_LAB T1
            JOIN JDT_USER_DETAILS T2 ON T1.requesterId = T2.id
            LEFT JOIN JDT_USER_DETAILS T3 ON T2.managerId = T3.id
        WHERE 
            T1.status = 3
    """
    
    df = pd.read_sql(query, cnnx)
    
    if not df.empty:
        now = datetime.now()
        
        for _, row in df.iterrows():
            end_date = pd.to_datetime(row['endDate'])
            business_days = _count_business_days(end_date.date(), now.date())
            
            # Se passou mais de 5 dias úteis, enviar email
            if business_days >= 5:
                try:
                    # Email usando template email_pending_retrieval.html
                    template = env.get_template('request.laboratory/email_pending_retrieval.html')
                    msg_html = template.render(
                        requestId=row['requestId'],
                        areaName=row['areaName'],
                        business_days=business_days
                    )
                    
                    # Preparar destinatários: solicitante + líder em cópia (apenas a partir do 5º dia)
                    recipients = [row['requester_email']]
                    cc_recipients = []
                    
                    if business_days >= 5 and pd.notna(row['manager_email']):
                        cc_recipients.append(row['manager_email'])
                    
                    send_email_with_attachment(
                        subject=f'[URGENTE] Material SSL #{row["requestId"]} aguardando retirada há {business_days} dias úteis',
                        body=msg_html,
                        to=recipients[0],
                        cc=cc_recipients[0] if cc_recipients else None,
                        sender_name='Transformação Digital JOST',
                        sender_email='noreply.digitaljost@randon.com.br'
                    )
                    
                    logger.info(f"Email de pendência enviado para {row['requester_email']} (cc: {row.get('manager_email', 'N/A')}) - SSL {row['requestId']} ({business_days} dias úteis)")
                    
                except Exception as e:
                    print(e)
                    logger.error(f"Erro ao enviar email para SSL {row['requestId']}: {str(e)}")

    cnnx.close()
