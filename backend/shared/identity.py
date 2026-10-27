"""Identidade e permissões modernas, reutilizando a sessão do portal legado."""

from dataclasses import dataclass

from flask_login import current_user


@dataclass(frozen=True)
class Actor:
    id: str


def is_authenticated():
    return current_user.is_authenticated


def current_actor():
    return Actor(id=current_user.id)


def can_access(role):
    # O legado só é carregado ao conferir a permissão da requisição.
    from app.utils.permissions import get_permission

    permission = get_permission(role)
    return bool(
        permission is not None
        and callable(getattr(permission, "can", None))
        and permission.can()
    )


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
