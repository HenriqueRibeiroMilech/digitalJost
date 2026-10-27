"""
Handlers de erro para o aplicativo Flask.
Importe e registre no app principal.
"""
from datetime import datetime
import traceback
from flask import render_template, request
from flask_login import current_user
from werkzeug.exceptions import HTTPException

from backend.shared.http import http_exception_response, is_api_request

from app.utils.teams_utils import send_system_teams_alert
from app.utils.security_utils import access_register


def register_error_handlers(app):
    @app.errorhandler(400)
    def miss_data(e):
        if is_api_request():
            return http_exception_response(e)
        return render_template('general_bad_request.html'), 400

    @app.errorhandler(404)
    def page_not_found(e):
        if is_api_request():
            return http_exception_response(e)
        return render_template('general_error404.html'), 404

    @app.errorhandler(403)
    def access_denied(e):
        if is_api_request():
            return http_exception_response(e)
        return render_template('general_role_denied.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        if is_api_request():
            return http_exception_response(e)
        tb = traceback.format_exc()
        send_system_teams_alert(request.url, tb, getattr(current_user, 'name', 'Anon'))

        return render_template('general_server_error.html'), 500

    @app.errorhandler(HTTPException)
    def routing_error(e):
        if is_api_request():
            return http_exception_response(e)
        return e
