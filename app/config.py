"""
Configuração principal do projeto Flask Digital JOST.

Este módulo inicializa o app Flask, configura extensões (SQLAlchemy, Mail, Login, Principal),
registra blueprints, handlers de erro e implementa o registro automático de logs de acesso.
"""

import warnings
import os
import json
from datetime import datetime, timedelta

from sqlalchemy.engine import URL

from flask import Flask, request, g
from flask_login import current_user, LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_principal import Principal, RoleNeed, UserNeed, Identity, identity_loaded
from flask_mail import Mail

from app.utils.security_utils import access_register
from app.utils.constants import CNNX_JDT
from app.utils.permissions import user_has_role
from app.errors import register_error_handlers

# DESLIGA OS AVISOS DE SCRIPT
warnings.filterwarnings('ignore')

mail = Mail()
db = SQLAlchemy()

class Config:
    """
    Classe de configuração do Flask.

    Define variáveis de ambiente, banco de dados, email, sessão, etc.
    """
    SQLALCHEMY_DATABASE_URI = URL.create("mssql+pyodbc", query={"odbc_connect": CNNX_JDT})
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 50,         # Aumente para um valor maior
        "max_overflow": 70,      # Aumente também o overflow
        "pool_timeout": 60,       # Aumente o timeout se necessário
        "pool_recycle": 3600      # Reciclar conexões após 1 hora
    }

    SECRET_KEY = "tdg_2022J0stW3B4pps!?AOIDUFYGOWIERHU5142LI54B12KNMTNRMlkasçodfjaslkjvn.,MSOçlkszjdg"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    MAIL_SERVER = 'mailapp.randon.com.br'
    MAIL_PORT = 25
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False

    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 100 MB


def create_app():

    """
    Cria e configura a aplicação Flask principal.

    - Inicializa extensões (db, mail, login, principal)
    - Registra blueprints
    - Registra handlers de erro
    - Implementa registro automático de logs de acesso

    Returns:
        app (Flask): Instância configurada do Flask
    """

    app = Flask(__name__)
    app.jinja_env.globals['user_has_role'] = user_has_role

    # DEFINIÇÃO DO DIRETÓRIO DE FUNCIONAMENTO DO CÓDIGO
    path = os.getcwd()

    # CONFIGURAÇÕES DE CAMINHOS PARA PASTAS DE DADOS E CSS (STATIC) E DOS ARQUIVOS HTML (TEMPLATES)
    app.static_folder = rf'{path}\app\static'
    app.template_folder = rf'{path}\app\templates'
    app.upload_folder = rf'{path}\app\static\uploads'

    # CONFIGURAÇÕES DO APLICATIVO PARA FUNCIONALIDADES ESPECÍFICAS (ENCERRAR SESSÃO, ENVIAR E-MAILS, CHAVE SECRETA)
    app.config.from_object(Config)

    # CRIAÇÃO DO OBJETO DE GERENCIAMENTO DE LOGIN
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Faça o Login para acessar essa página!'
    login_manager.init_app(app)

    # CRIAÇÃO DO OBJETO DE GERENCIAMENTO DE ROLES
    principals = Principal(app)

    @principals.identity_loader
    def load_identity():
        try:
            identity = Identity(current_user.id)
        except AttributeError:
            identity = Identity('Anon')

        return identity

    @app.before_request
    def before_log():
        g._log_error = False

    @app.after_request
    def capture_status_code(response):
        g.status_code = response.status_code
        return response
    
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """
        Remove a sessão do SQLAlchemy ao final de cada requisição.
        Garante que conexões sejam devolvidas ao pool.
        """
        try:
            db.session.remove()
        except Exception as e:
            print(f"Erro ao remover sessão: {e}", flush=True)

    @app.teardown_request
    def teardown_log(exc):

        """
        Registra log de acesso do usuário ao final de cada requisição.

        - Não registra logs para rotas estáticas.
        - Não registra logs para usuários com generic = '0'.
        - Salva: id do usuário, rota, argumentos, payload, método HTTP, erro, datetime.

        Args:
            exc (Exception | None): Exceção da requisição, se houver.
        """
        if not request.endpoint or request.endpoint == 'static':
            return

        if request.endpoint.startswith('auth.'):
            return
        
        user_id = getattr(current_user, 'id', None)
        route = request.path
        args = dict(request.args)
        method = request.method
        dt = datetime.now().replace(microsecond=0)

        status_code = getattr(g, 'status_code', None)
        if status_code is None:
            status_code = 200

        payload = request.get_json(silent=True)
        if payload is None:
            payload = request.form.to_dict()

        try:
            if not user_id or (hasattr(current_user, 'generic') and str(current_user.generic) == '0'):
                return
            
            access_register(user_id, route, args, payload, method, status_code, dt)
        except Exception as e:
            print(f"Erro ao registrar acesso: {e}")
        
        finally:
            # GARANTIR que a sessão seja removida mesmo se houver erro
            try:
                db.session.remove()
            except Exception as e:
                print(f"Erro ao remover sessão: {e}", flush=True)

    from app.models.user import User

    # CARREGADOR DE USUÁRIO (RETORNA MATRÍCULA) NO LOGIN
    @login_manager.user_loader
    def load_user(user_id):
        """
        Carrega o usuário do banco de dados.
        Implementa cache por requisição para evitar múltiplas queries.
        """
        try:
            # Cache do usuário no contexto da requisição (g)
            if not hasattr(g, '_user_cache'):
                g._user_cache = {}
            
            # Se já carregamos esse usuário nesta requisição, retorna do cache
            if user_id in g._user_cache:
                return g._user_cache[user_id]
            
            # Busca no banco apenas se não estiver em cache
            user = db.session.get(User, user_id)
            
            # Armazena no cache
            if user:
                g._user_cache[user_id] = user
            
            return user
            
        except Exception as e:
            print(f"Erro ao carregar usuário: {e}")
            return None

    # INICIA AS FUNÇÕES "db" (BASE DE DADOS), "mail" (ENVIO DE E-MAIL)
    db.init_app(app)
    mail.init_app(app)

    from app.routes.main_default_routes import main 
    from app.routes.auth_routes import auth 

    # EXECUTA AÇÕES DENTRO DO CONTEXTO DO APP (COMO SE ELE ESTIVESSE RODANDO)
    with app.app_context():
        # CRIA O ACESSO À BASE DE DADOS
        db.create_all()

        # REGISTRA AS ROTAS "main" (PARA FUNÇÕES GERAIS) E "auth" (PARA FUNÇÕES DE AUTENTICAÇÃO COMO LOGIN E LOGOUT)
        app.register_blueprint(main)
        app.register_blueprint(auth)

        @identity_loaded.connect_via(app)
        def on_identity_loaded(sender, identity):
            register = str(sender)
            identity.user = current_user
            if identity.id != 'Anon':
                identity.provides.add(UserNeed(current_user.id))
                for role in json.loads(current_user.role):
                    identity.provides.add(RoleNeed(role))

            return register


    # REGISTRA OS HANDLERS DE ERRO
    register_error_handlers(app)

    return app

# V1