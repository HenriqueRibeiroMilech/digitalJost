"""Leitura da configuração externa: ambiente e arquivo privado opcional."""

import os
from pathlib import Path


_environment_loaded = False


def load_environment() -> None:
    """Carrega uma vez, sem sobrescrever o ambiente ou interpolar credenciais."""
    global _environment_loaded
    if _environment_loaded:
        return

    configured_path = os.environ.get("DJ_ENV_FILE")
    if configured_path is not None:
        if not configured_path.strip() or not Path(configured_path).is_absolute():
            raise RuntimeError("DJ_ENV_FILE deve indicar um caminho absoluto não vazio.")
        dotenv_path = Path(configured_path)
    else:
        dotenv_path = Path(__file__).resolve().parents[2] / ".env"

    try:
        if not dotenv_path.exists():
            if configured_path is not None:
                raise RuntimeError("O arquivo indicado por DJ_ENV_FILE não foi encontrado.")
            _environment_loaded = True
            return
        if not dotenv_path.is_file():
            raise RuntimeError("A configuração privada deve ser um arquivo regular.")

        # O ambiente do Windows funciona sem este pacote quando não há arquivo.
        try:
            from dotenv import load_dotenv
        except ImportError:
            raise RuntimeError("Para ler o arquivo privado, instale python-dotenv==1.2.4.") from None

        load_dotenv(
            dotenv_path=dotenv_path,
            override=False,
            interpolate=False,
            encoding="utf-8-sig",
        )
    except (OSError, UnicodeError):
        raise RuntimeError("Não foi possível ler o arquivo privado de configuração.") from None

    _environment_loaded = True


def required_env(name: str) -> str:
    load_environment()
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Variável de ambiente obrigatória ausente ou vazia: {name}.")
    # Validar espaços em branco sem alterar o valor das credenciais.
    return value
