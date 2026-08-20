from app.config import create_app

from app.routes.demands.default import demands_default_bp
from app.routes.demandManagement import demand_management_bp
from app.routes.demandRequests import demand_requests_bp

from app.routes.factoryRegister.assembly import factoryRegister_assembly_bp
from app.routes.factoryRegister.default import factoryRegister_default_bp
from app.routes.factoryRegister.external import factoryRegister_external_bp
from app.routes.factoryRegister.matrix import factoryRegister_matrix_bp

from app.routes.jdt.communication import jdt_communication_bp
from app.routes.jdt.computers import jdt_computers_bp
from app.routes.jdt.library import jdt_library_bp
from app.routes.jdt.monitoring import jdt_monitoring_bp
from app.routes.jdt.temp import jdt_extra_bp
from app.routes.jdt.userManager import jdt_userManager_bp

from app.routes.operation.logistic import operation_logistic_bp
from app.routes.operation.planning import operation_planning_bp
from app.routes.operation.production import operation_production_bp
from app.routes.operation.quality import operation_quality_bp
from app.routes.operation.security import operation_security_bp

from app.routes.reports.maintenance import reports_maintenance_bp
from app.routes.reports.oee import reports_oee_bp
from app.routes.reports.powerbi import reports_powerbi_bp
# from app.routes.reports.productiveHours import reports_productiveHours_bp -- importar a rota corromperá o sistema, necessário atualização para o Plex
# from app.routes.reports.setup import reports_setup_bp -- importar a rota corromperá o sistema, necessário atualização para o Plex

from app.routes.request.improvements import request_improvements_bp
from app.routes.request.laboratory import request_laboratory_bp
from app.routes.request.processDeviation import request_processDeviation_bp
from app.routes.request.workcentersLogChange import request_workcentersLogChange_bp

# CHAMA A FUNÇÃO QUE RETORNA AS CONFIGURAÇÕES DO FRAMEWORK
app = create_app()

# INVOKE DAS CLASSES DE CADA ROTA DO WEBSITE
# (CTRL + BTN ESQUERDO MOUSE PARA ACESSAR)
app.register_blueprint(demands_default_bp)
app.register_blueprint(demand_management_bp)
app.register_blueprint(demand_requests_bp)

app.register_blueprint(factoryRegister_assembly_bp)
app.register_blueprint(factoryRegister_default_bp)
app.register_blueprint(factoryRegister_external_bp)
app.register_blueprint(factoryRegister_matrix_bp)

app.register_blueprint(jdt_communication_bp)
# app.register_blueprint(jdt_computers_bp) -- temporariamente desativada
app.register_blueprint(jdt_library_bp)
app.register_blueprint(jdt_monitoring_bp)
# app.register_blueprint(jdt_extra_bp) -- temporariamente desativada
app.register_blueprint(jdt_userManager_bp)

app.register_blueprint(operation_logistic_bp)
app.register_blueprint(operation_planning_bp)
app.register_blueprint(operation_production_bp)
app.register_blueprint(operation_quality_bp)
app.register_blueprint(operation_security_bp)

app.register_blueprint(reports_maintenance_bp)
app.register_blueprint(reports_oee_bp)
app.register_blueprint(reports_powerbi_bp)
# app.register_blueprint(reports_productiveHours_bp) -- desativada devido a não integração com Plex e tabela TEMP_OPERATORS_CLOCKING
# app.register_blueprint(reports_setup_bp) -- desativada devido a não integração com Plex

app.register_blueprint(request_improvements_bp)
app.register_blueprint(request_laboratory_bp)
app.register_blueprint(request_processDeviation_bp)
app.register_blueprint(request_workcentersLogChange_bp)

if __name__ == '__main__':

    app.run(debug=False)
