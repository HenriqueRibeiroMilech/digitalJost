"""
Handlers de erro para o aplicativo Flask.
Importe e registre no app principal.
"""
from datetime import datetime
import traceback
from flask import render_template, request
from flask_login import current_user

from app.utils.teams_utils import send_system_teams_alert
from app.utils.security_utils import access_register


def register_error_handlers(app):
    @app.errorhandler(400)
    def miss_data(e):
        return render_template('general_bad_request.html'), 400

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('general_error404.html'), 404

    @app.errorhandler(403)
    def access_denied(e):
        return render_template('general_role_denied.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        tb = traceback.format_exc()
        send_system_teams_alert(request.url, tb, getattr(current_user, 'name', 'Anon'))

        return render_template('general_server_error.html'), 500
