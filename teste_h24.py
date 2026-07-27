import logging

from app.services.jobs.mon_fri_h_24_processDeviationCheck import default


# Configuração do logger
logger = logging.getLogger("teste_h24")
logger.setLevel(logging.INFO)

console = logging.StreamHandler()
console.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

console.setFormatter(formatter)

logger.addHandler(console)


# Executa o job
logger.info("===== INICIANDO TESTE H24 =====")

try:
    default(logger)
    logger.info("===== TESTE H24 FINALIZADO =====")
except Exception as e:
    logger.exception(f"Erro durante execução do teste: {e}")