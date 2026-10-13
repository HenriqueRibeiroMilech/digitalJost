"""Leitura de configuração externa, sem carregar arquivos ou abrir recursos."""

import os


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Variável de ambiente obrigatória ausente ou vazia: {name}.")
    # Validar espaços em branco sem alterar o valor das credenciais.
    return value
