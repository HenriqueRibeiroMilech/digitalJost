"""Identidade mínima e autorização por ação usadas pelos serviços modernos."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    id: str


class RolePermissions:
    """Política de ações para a sessão corrente; não consulta outros usuários."""

    def __init__(self, can_access, action_roles):
        self._can_access = can_access
        self._action_roles = dict(action_roles)

    def can(self, actor, action):
        role = self._action_roles.get(action)
        return bool(role is not None and self._can_access(role))

    def require(self, actor, action):
        if not self.can(actor, action):
            raise PermissionError("Acesso negado")
