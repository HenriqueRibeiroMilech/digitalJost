# NÃO ALTERAR OS VALORES ABAIXO. PERMISSÕES FIXAS DO SISTEMA.
from flask_principal import RoleNeed, Permission
import json


# Permissões privadas
_ADMIN = RoleNeed('Transformação Digital')
_GENERAL = Permission(RoleNeed('Jost - Geral'), _ADMIN)
_PROCESS = Permission(RoleNeed('Engenharia de Processo'), _ADMIN)
_SSMA = Permission(RoleNeed('SSMA'), _ADMIN)
_MAINTENANCE = Permission(RoleNeed('Manutenção'), _ADMIN)
_QUALITY = Permission(RoleNeed('Engenharia de Qualidade'), _ADMIN)
_LABORATORY = Permission(RoleNeed('Laboratório'), _ADMIN)
_LOGISTIC = Permission(RoleNeed('Logistica'), _ADMIN)
_PRODUCTION = Permission(RoleNeed('Produção'), _ADMIN)
_DEVIATION = Permission(RoleNeed('Desvios'), _ADMIN)
_T_ASSEMBLY = Permission(RoleNeed('Rastreabilidade - Montagem'), _ADMIN)
_T_ASSEMBLY_PLATES = Permission(RoleNeed('Rastreabilidade - Montagem'), RoleNeed('Rastreabilidade - Montagem Plaqueta'), _ADMIN)
_MATRIX = Permission(RoleNeed('Matriz'), _ADMIN)
_GOAL_OP_M = Permission(RoleNeed('Metas - Operation Meeting'), _ADMIN)
_COMMS = Permission(RoleNeed('Comunicação Interna'), _ADMIN)

_SYSADMIN = Permission(_ADMIN)

def get_permission(name):
	_permissions = {
		"ADMIN": _ADMIN
		, "GENERAL": _GENERAL
		, "PROCESS": _PROCESS
		, "SSMA": _SSMA
		, "MAINTENANCE": _MAINTENANCE
		, "QUALITY": _QUALITY
		, "LABORATORY": _LABORATORY
		, "LOGISTIC": _LOGISTIC
		, "PRODUCTION": _PRODUCTION
		, "DEVIATION": _DEVIATION
		, "T_ASSEMBLY": _T_ASSEMBLY
		, "T_ASSEMBLY_PLATES": _T_ASSEMBLY_PLATES
		, "MATRIX": _MATRIX
		, "GOAL_OP_M": _GOAL_OP_M
		, "COMMS": _COMMS
		, "SYSADMIN": _SYSADMIN
	}
	return _permissions.get(name)

def list_permissions():
	return {
		"ADMIN": _ADMIN
		, "GENERAL": _GENERAL
		, "PROCESS": _PROCESS
		, "SSMA": _SSMA
		, "MAINTENANCE": _MAINTENANCE
		, "QUALITY": _QUALITY
		, "LABORATORY": _LABORATORY
		, "LOGISTIC": _LOGISTIC
		, "PRODUCTION": _PRODUCTION
		, "DEVIATION": _DEVIATION
		, "T_ASSEMBLY": _T_ASSEMBLY
		, "T_ASSEMBLY_PLATES": _T_ASSEMBLY_PLATES
		, "MATRIX": _MATRIX
		, "GOAL_OP_M": _GOAL_OP_M
		, "COMMS": _COMMS
		, "SYSADMIN": _SYSADMIN
	}

def user_has_role(roles, role_name):
	"""
	Verifica se o usuário possui o role especificado ou é admin.

	Args:
		roles: lista de roles do usuário (ou JSON string).
		role_name (str): Nome do role a verificar.
		Se for admin, sempre retorna True.

	Returns:
		bool: True se o usuário possui o role ou é admin, False caso contrário.
	"""
	if isinstance(roles, str):
		try:
			roles = json.loads(roles)
		except Exception:
			roles = [roles]
	return role_name in roles