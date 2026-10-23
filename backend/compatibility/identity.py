"""Ponte temporária com a sessão e os perfis atuais, sem outro login ou LDAP."""

from flask_login import current_user

from backend.platform.identity import Actor


def is_authenticated():
    return current_user.is_authenticated


def current_actor():
    return Actor(id=current_user.id)


def can_access(role):
    from app.utils.permissions import get_permission

    permission = get_permission(role)
    return bool(
        permission is not None
        and callable(getattr(permission, "can", None))
        and permission.can()
    )
