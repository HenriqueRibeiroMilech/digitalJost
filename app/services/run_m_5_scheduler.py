
import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import time
import logging
from logging.handlers import RotatingFileHandler
import win32serviceutil
import win32service
import win32event

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.jobs import mon_mon_m_5_monitoringAlerts, mon_mon_m_5_monitoringClocking
from app.utils.teams_utils import send_system_teams_alert

class SchedulerService(win32serviceutil.ServiceFramework):
    _svc_name_ = "RunM5Scheduler"
    _svc_display_name_ = "Digital JOST M5 Scheduler"
    _svc_description_ = "Scheduler Python para jobs 24/7"

    def __init__(self, args):
        super().__init__(args)
        # Evento para parar o serviço
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

        # Configuração do logger
        log_dir = os.path.join(BASE_DIR, 'app', 'services', 'logs')
        log_path = os.path.join(log_dir, 'm_5_scheduler.log')

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        rotating_handler = RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=5)
        rotating_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s'))
        self.logger.addHandler(rotating_handler)

        # Scheduler
        self.scheduler = BackgroundScheduler()

    def SvcStop(self):
        # Evento de parada
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.running = False
        self.logger.info("Serviço parando...")
        self.scheduler.shutdown(wait=False)

    def SvcDoRun(self):
        self.logger.info("Serviço iniciado")
        try:
            # Adiciona jobs
            self.add_jobs()
            self.scheduler.start()
            while self.running:
                time.sleep(1)
        except Exception as e:
            self.logger.error(f"Erro no serviço: {e}", exc_info=True)
            send_system_teams_alert("Erro no serviço M5 Scheduler", e, "Digital JOST")

    def log_and_alert_job(self, job_name, func):
        try:
            self.logger.info(f'Job {job_name} iniciado.')
            func(self.logger)  # Passa o logger para a função
            self.logger.info(f'Job {job_name} finalizado com sucesso.')
        except Exception as e:
            self.logger.error(f'Job {job_name} falhou: {e}', exc_info=True)
            send_system_teams_alert(f'Erro no job {job_name}', e, 'Digital JOST')

    def add_jobs(self):
        trigger_mon_mon = CronTrigger(minute="*/5")
        self.scheduler.add_job(
            func=lambda: self.log_and_alert_job('Teams: Alerta de Paradas', mon_mon_m_5_monitoringAlerts.default),
            trigger=trigger_mon_mon
        )
        self.scheduler.add_job(
            func=lambda: self.log_and_alert_job('Tabela temporária: Relógio Ponto', mon_mon_m_5_monitoringClocking.default),
            trigger=trigger_mon_mon
        )


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(SchedulerService)
