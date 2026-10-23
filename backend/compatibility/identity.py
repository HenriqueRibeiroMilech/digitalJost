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


def is_admin():
    return str(getattr(current_user, "admin", "")).strip().lower() in ("1", "true", "sim")


def can_access_area(area):
    import json
    from app.utils.permissions import user_has_role

    roles = getattr(current_user, "role", [])
    if isinstance(roles, str):
        try:
            roles = json.loads(roles)
        except (ValueError, TypeError):
            roles = [roles]
    return can_access("GENERAL") and (
        is_admin() or (isinstance(roles, (list, tuple, set)) and user_has_role(roles, area))
    )
