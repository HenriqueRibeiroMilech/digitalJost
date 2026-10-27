"""
    Classe _TokenManager
    --------------------
    Gerencia tokens de autenticação do Azure AD utilizando MSAL para aplicações confidenciais.

    - O token é renovado automaticamente em background por um thread a cada 25 minutos.
    - Todos os acessos usam o token do cache, garantindo alta eficiência para múltiplos acessos simultâneos.
    - O acesso é thread-safe e nunca dispara múltiplas requisições ao Azure AD em paralelo.

    Atributos:
        TENANT_ID (str): ID do tenant do Azure AD.
        CLIENT_ID (str): ID do aplicativo (cliente) do Azure AD.
        CLIENT_SECRET (str): Segredo do cliente do aplicativo Azure AD.
        USERNAME (str): Nome de usuário para o fluxo de credenciais de proprietário de recurso.
        PASSWORD (str): Senha para o fluxo de credenciais de proprietário de recurso.
        _app (msal.ConfidentialClientApplication): Instância do cliente MSAL.
        _token_data (dict): Cache interno do token atual.
        _token_lock (threading.Lock): Lock para acesso thread-safe ao token.
        _thread (threading.Thread): Thread de renovação automática do token.
    Métodos:
        get_header(): Retorna um dicionário contendo o cabeçalho Authorization com o token Bearer
        e o Content-Type definido como "application/json". Sempre usa o token do cache.
"""

import time
import msal
import threading

from backend.shared.environment import required_env

class _TokenManager:

    def __init__(self):
        self.TENANT_ID = required_env("DJ_MICROSOFT_TENANT_ID")
        self.CLIENT_ID = required_env("DJ_MICROSOFT_CLIENT_ID")
        self.CLIENT_SECRET = required_env("DJ_MICROSOFT_CLIENT_SECRET")
        self.USERNAME = required_env("DJ_MICROSOFT_USERNAME")
        self.PASSWORD = required_env("DJ_MICROSOFT_PASSWORD")

        self._app = msal.ConfidentialClientApplication(
            client_id=self.CLIENT_ID,
            authority=f'https://login.microsoftonline.com/{self.TENANT_ID}',
            client_credential=self.CLIENT_SECRET
        )

        self._token_data = None
        self._token_lock = threading.Lock()
        self._interval = 600  # 10 minutos em segundos
        self._thread = threading.Thread(target=self._scheduler, daemon=True)
        self._thread.start()

    def _scheduler(self):
        while True:
            try:
                with self._token_lock:
                    self._token_data = self._get_token()
            except Exception as e:
                print(f"Erro ao atualizar token Azure: {e}")
            time.sleep(self._interval)

    def _get_token(self):
        # Tenta obter o token do cache da MSAL primeiro
        accounts = self._app.get_accounts(username=self.USERNAME)
        if accounts:
            result = self._app.acquire_token_silent(scopes=[], account=accounts[0])
            if result and 'access_token' in result:
                return result

        # Se não houver token válido no cache, adquire um novo
        result = self._app.acquire_token_by_username_password(
            self.USERNAME, self.PASSWORD, scopes=[]
        )
        if "access_token" not in result:
            raise Exception(f"Could not acquire token: {result.get('error_description')}")
        return result

    def get_header(self):
        with self._token_lock:
            if self._token_data is None:
                self._token_data = self._get_token()
            return {
                "Authorization": f"Bearer {self._token_data['access_token']}",
                "Content-Type": "application/json"
            }

# Instância única do gerenciador de token
_token_manager = _TokenManager()

def get_azure_header():
    """
    Função pública para obter o cabeçalho de autorização do Azure.
    Retorna sempre o token do cache, que é renovado automaticamente em background a cada 25 minutos.
    Ideal para cenários de alta demanda e múltiplos acessos simultâneos.
    """
    return _token_manager.get_header()
