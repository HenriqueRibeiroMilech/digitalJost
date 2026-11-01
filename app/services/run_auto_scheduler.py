import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import logging
from logging.handlers import RotatingFileHandler
import time
import win32serviceutil
import win32service
import win32event

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.jobs import mon_mon_auto_demandManagement, mon_mon_auto_laboratory, mon_mon_auto_modern_demands
from app.utils.teams_utils import send_system_teams_alert


class SchedulerService(win32serviceutil.ServiceFramework):
    _svc_name_ = "RunAutoScheduler"
    _svc_display_name_ = "Digital JOST Auto Scheduler"
    _svc_description_ = "Scheduler Python para jobs automáticos"

    def __init__(self, args):
        super().__init__(args)
        # Evento para parar o serviço
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

        # Configuração do logger
        log_dir = os.path.join(BASE_DIR, 'app', 'services', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, 'auto_scheduler.log')

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
            send_system_teams_alert("Erro no Auto Scheduler", e, "Digital JOST")

    def log_and_alert_job(self, job_name, func):
        try:
            self.logger.info(f'Job {job_name} iniciado.')
            func(self.logger)  # Passa o logger para a função
            self.logger.info(f'Job {job_name} finalizado com sucesso.')
        except Exception as e:
            self.logger.error(f'Job {job_name} falhou: {e}', exc_info=True)
            send_system_teams_alert(f'Erro no job {job_name}', e, 'Digital JOST')

    def add_jobs(self):
        # Job a cada minuto (segundo 0) - verifica agendamentos automáticos
        trigger_1min = CronTrigger(second='0')
        self.scheduler.add_job(
            func=lambda: self.log_and_alert_job('Agendamentos automáticos: Equipamentos', mon_mon_auto_laboratory.default),
            trigger=trigger_1min
        )
        self.scheduler.add_job(
            func=lambda: self.log_and_alert_job('Agendamentos automáticos: Demandas', mon_mon_auto_demandManagement.default),
            trigger=trigger_1min
        )
        self.scheduler.add_job(
            func=lambda: self.log_and_alert_job('Agendamentos automáticos: Demandas modernas', mon_mon_auto_modern_demands.default),
            trigger=trigger_1min, max_instances=1, coalesce=True
        )

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(SchedulerService)

# V1
