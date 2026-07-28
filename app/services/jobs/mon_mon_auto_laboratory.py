"""
Job: Verifica agendamentos de equipamentos e aplica mudanças de status quando chega o horário.
Executado periodicamente pelo run_auto_scheduler.
"""

import traceback
from datetime import datetime
import pandas as pd
from sqlalchemy import text

from app.utils.db_utils import get_engine


def _apply_change(conn, equipment_id, status, event, comments, logger):
    """
    Atualiza último log do equipamento (fecha) e insere novo registro com status/event.
    
    Args:
        conn: Conexão do banco de dados
        equipment_id: ID do equipamento
        status: Novo status
        event: Novo evento
        comments: Comentários
        logger: Logger para registrar ações
    """
    try:
        equipment_id = int(equipment_id)
        
        # Fechar último registro
        update_query = """
            UPDATE JDT_REQUEST_LAB_EQUIPMENTS_LOGS
            SET end_date = GETDATE(),
                duration = DATEDIFF(MINUTE, start_date, GETDATE())
            WHERE equipmentId = :equipment_id
            AND id = (
                SELECT TOP 1 id
                FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS
                WHERE equipmentId = :equipment_id
                ORDER BY start_date DESC
            )
        """
        conn.execute(text(update_query), {'equipment_id': equipment_id})

        # Inserir novo registro
        insert_query = """
            INSERT INTO JDT_REQUEST_LAB_EQUIPMENTS_LOGS (
                equipmentId, register, status, event, start_date, comments
            ) VALUES (
                :equipment_id, :register, :status, :event, GETDATE(), :comments
            )
        """
        conn.execute(text(insert_query), {
            'equipment_id': equipment_id,
            'register': 1,  # Sistema
            'status': status,
            'event': event,
            'comments': comments
        })
        
        logger.info(f"Equipment {equipment_id} -> status '{status}' / event '{event}' aplicado")
        
    except Exception as exc:
        logger.exception(f"Erro aplicando mudança para equipment {equipment_id}: {exc}")
        traceback.print_exc()


def _pause_equipment_ssls(equipment_id, conn, reason, logger):
    """
    Pausa todas as SSLs em execução em um equipamento.
    
    Args:
        equipment_id: ID do equipamento
        conn: Conexão do banco de dados
        reason: Motivo da pausa
        logger: Logger para registrar ações
    """
    try:
        equipment_id = int(equipment_id)
        
        # Buscar SSLs em execução
        ssl_query = """
            SELECT requestId FROM JDT_REQUEST_LAB
            WHERE status = 2 AND execArea = :equipment_id
        """
        ssl_df = pd.read_sql(text(ssl_query), conn, params={'equipment_id': equipment_id})
        
        if ssl_df.empty:
            return
        
        for _, row in ssl_df.iterrows():
            request_id = int(row['requestId'])
            
            # Verificar se já existe pausa ativa (pelo log)
            check_query = """
                SELECT TOP 1 COALESCE(new, 'False') AS is_paused
                FROM JDT_REQUEST_LAB_LOGS
                WHERE requestId = :request_id AND extra = 'pause'
                ORDER BY date DESC
            """
            check_df = pd.read_sql(text(check_query), conn, params={'request_id': request_id})
            
            # Se não há pausa ativa, criar uma
            if check_df.empty or check_df['is_paused'].iloc[0] == 'False':
                # Registrar log da pausa
                log_query = """
                    INSERT INTO JDT_REQUEST_LAB_LOGS 
                    (requestId, userId, old, new, extra, date)
                    VALUES (:request_id, 1, 'False', 'True', 'pause', GETDATE())
                """
                conn.execute(text(log_query), {'request_id': request_id})
                logger.info(f"SSL {request_id} pausada automaticamente devido a: {reason}")
    
    except Exception as e:
        logger.exception(f"Erro ao pausar SSLs do equipamento {equipment_id}: {e}")
        traceback.print_exc()


def _time_in_range(current_time, start_time, end_time):
    """
    Verifica se o horário atual está dentro do intervalo, considerando cruzamento de meia-noite.
    
    Args:
        current_time: Horário atual em formato HH:MM
        start_time: Horário de início em formato HH:MM
        end_time: Horário de término em formato HH:MM
    
    Returns:
        tuple: (is_start_time, is_end_time, is_in_range)
            - is_start_time: True se é exatamente o horário de início
            - is_end_time: True se é exatamente o horário de término
            - is_in_range: True se está dentro do intervalo (para agendamentos que cruzam meia-noite)
    
    Exemplos:
        17:00 às 07:00 (cruza meia-noite):
            - Às 17:00 → (True, False, True)
            - Às 22:00 → (False, False, True)
            - Às 02:00 → (False, False, True)
            - Às 07:00 → (False, True, False)
            - Às 10:00 → (False, False, False)
        
        08:00 às 17:00 (não cruza):
            - Às 08:00 → (True, False, True)
            - Às 12:00 → (False, False, True)
            - Às 17:00 → (False, True, False)
            - Às 20:00 → (False, False, False)
    """
    is_start = (current_time == start_time)
    is_end = (current_time == end_time)
    
    # Detectar se cruza meia-noite (end_time < start_time)
    crosses_midnight = (end_time < start_time)
    
    if crosses_midnight:
        # Está no intervalo se for >= start OU < end
        in_range = (current_time >= start_time or current_time < end_time)
    else:
        # Intervalo normal: entre start e end (não inclui end)
        in_range = (start_time <= current_time < end_time)
    
    return is_start, is_end, in_range


def default(logger):
    """
    Executa uma checagem única: busca agendamentos ativos e, para cada um
    cujo start_time OR end_time coincide com o horário atual (HH:MM), aplica a mudança.
    
    ⚙️ PADRÃO ORM - DETECÇÃO AUTOMÁTICA DE MUDANÇAS:
    - A cada execução, busca dados frescos do banco (JDT_REQUEST_LAB_EQUIPMENTS_SCHEDULE)
    - Qualquer INSERT/UPDATE/DELETE feito pelo Flask será detectado automaticamente
    - Não usa cache - sempre reflete o estado atual da tabela
    
    🕐 HORÁRIOS EM MINUTOS FECHADOS:
    - Comparação em formato HH:MM (ex: 19:03, 14:30)
    - Executado a cada minuto pelo scheduler (segundo 0)
    - ⭐ SUPORTE A CRUZAMENTO DE MEIA-NOITE:
      - Agendamentos como 17:00 às 07:00 funcionam automaticamente
      - Sistema detecta quando end_time < start_time
      - Equipamento fica no status agendado durante todo o período (17h-23h59 + 00h-07h)
    
    📅 DIAS DA SEMANA:
    - Formato: string "0,1,2,3,4" onde 0=segunda, 6=domingo
    - Aceita '*' ou NULL para todos os dias
    - Valida se hoje está nos dias configurados antes de aplicar
    
    Args:
        logger: Logger para registrar ações e erros
    """
    try:
        engine = get_engine('jdt')
        now = datetime.now()
        current_hm = now.strftime('%H:%M')
        weekday = str(now.weekday())  # 0=segunda ... 6=domingo

        with engine.begin() as conn:
            # 🔄 BUSCA DADOS ATUALIZADOS DO BANCO (padrão ORM)
            # Qualquer mudança feita pelo Flask será detectada aqui
            query = """
                SELECT
                    S.id,
                    S.equipmentId,
                    S.areaId,
                    S.status,
                    S.event,
                    CONVERT(VARCHAR(5), S.start_time, 108) as start_time,
                    CONVERT(VARCHAR(5), S.end_time, 108) as end_time,
                    COALESCE(S.days_of_week, '0,1,2,3,4,5,6') as days_of_week,
                    S.comments,
                    S.valid_until,
                    E.name as equipment_name
                FROM 
                    JDT_REQUEST_LAB_EQUIPMENTS_SCHEDULE S
                    JOIN JDT_REQUEST_LAB_EQUIPMENTS E ON S.equipmentId = E.id
                WHERE 
                    S.active = 1
                    AND (S.valid_until IS NULL OR S.valid_until >= CAST(GETDATE() AS DATE))
            """
            schedules = pd.read_sql(text(query), conn)
            
            if schedules.empty:
                logger.debug("Nenhum agendamento ativo encontrado")
                return

            # Processar cada agendamento
            for _, row in schedules.iterrows():
                try:
                    days = str(row['days_of_week']).strip()
                    
                    # Verificar se hoje é um dia válido para este agendamento
                    # Aceitar '*' ou lista '0,1,2' ou vazio => todos os dias
                    if days and days != '*':
                        valid_days = [d.strip() for d in days.split(',')]
                        if weekday not in valid_days:
                            continue

                    equipment_id = int(row['equipmentId'])
                    equipment_name = row['equipment_name']
                    start_time = str(row['start_time'])
                    end_time = str(row['end_time'])

                    # Verificar situação do horário atual em relação ao agendamento
                    is_start, is_end, is_in_range = _time_in_range(current_hm, start_time, end_time)

                    # Buscar status atual do equipamento
                    check_query = """
                        SELECT TOP 1 status, event
                        FROM JDT_REQUEST_LAB_EQUIPMENTS_LOGS
                        WHERE equipmentId = :equipment_id
                        ORDER BY start_date DESC
                    """
                    current_status_df = pd.read_sql(text(check_query), conn, 
                                                    params={'equipment_id': equipment_id})
                    
                    current_status = None
                    current_event = None
                    if not current_status_df.empty:
                        current_status = current_status_df.iloc[0]['status']
                        current_event = current_status_df.iloc[0]['event']

                    # Se chegou horário de INÍCIO do agendamento
                    if is_start:
                        # Aplicar somente se estiver Disponível / Sem Uso
                        if current_status == 'Disponível' and (current_event == 'Sem Uso' or current_event is None):
                            # Pausar SSLs se necessário
                            if row['status'] in ['Indisponível', 'Parado']:
                                _pause_equipment_ssls(equipment_id, conn, row.get('comments', 'Agendamento automático'), logger)
                            
                            # Aplicar mudança de status
                            _apply_change(
                                conn, 
                                equipment_id, 
                                row['status'], 
                                row['event'], 
                                row.get('comments', 'Agendamento automático'),
                                logger
                            )
                            
                            # Indicar se cruza meia-noite
                            crosses_msg = " (cruza meia-noite)" if end_time < start_time else ""
                            logger.info(f"[INÍCIO{crosses_msg}] {equipment_name}: {row['status']} - {row['event']}")
                        else:
                            logger.debug(f"{equipment_name} não disponível para iniciar agendamento "
                                       f"(status={current_status}, event={current_event})")

                    # Se chegou horário de FIM do agendamento
                    elif is_end:
                        # Aplicar somente se NÃO estiver Disponível/Sem Uso
                        if current_status != 'Disponível' or (current_event != 'Sem Uso' and current_event is not None):
                            _apply_change(
                                conn, 
                                equipment_id, 
                                'Disponível', 
                                'Sem Uso', 
                                'Fim de agendamento automático',
                                logger
                            )
                            logger.info(f"[FIM] {equipment_name}: Disponível - Sem Uso")
                        else:
                            logger.debug(f"{equipment_name} já disponível no horário de término")
                            
                except Exception as row_exc:
                    logger.exception(f"Erro processando agendamento id={row.get('id')}: {row_exc}")
                    traceback.print_exc()

    except Exception as e:
        logger.exception(f"Erro no job mon_mon_auto_laboratory: {e}")
        traceback.print_exc()