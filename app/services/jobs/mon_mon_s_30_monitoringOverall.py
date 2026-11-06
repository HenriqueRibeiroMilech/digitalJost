"""Entrada antiga preservada, sem consultas ou escrita da tabela intermediária.

As telas e o M5 utilizam backend.modules.monitoring.current_status.
O serviço RunS30Scheduler pode ser desativado após publicar esses consumidores.
"""


def default(logger):
    logger.info('Consolidação S30 desativada. Nenhuma consulta ou atualização realizada.')
