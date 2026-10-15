# Digital JOST

Portal interno da JOST para demandas, operações industriais, laboratório, monitoramento e relatórios. Roda em Windows/IIS e está sendo modernizado sem interromper as telas antigas.

## Estrutura

| Local | Conteúdo |
|---|---|
| `main.py` e `app/config.py` | Entrada Flask, sessão, extensões e registro das partes antiga e nova. |
| `app/` | Rotas e páginas Jinja, usuários, integrações e serviços Windows do legado. |
| `backend/` | APIs modernas, módulos, banco compartilhado e shell que carrega o Vue. |
| `frontend/` | Interface Vue/TypeScript e componentes compartilhados. |
| `handbook/` | Documentação oficial. |

As duas arquiteturas usam o mesmo TD, com acessos separados. A nova mantém um pool geral de conexões e reaproveita o login e os perfis antigos. `app/` continua necessário.

## Preparar o computador

Requisitos:

- Windows e Python 3.13 de 64 bits, como referência do servidor.
- Node `^22.18.0` ou `>=24.12.0`, com npm, para gerar o Vue.
- Driver ODBC compatível e acesso autorizado aos recursos corporativos.
- IIS com autenticação Windows e `httpPlatformHandler` para conferir o login real.

Em ambiente novo e autorizado, abra o **CMD na raiz do projeto**, onde está `main.py`:

```bat
py -3.13 -m venv .venv
".venv\Scripts\python.exe" -m pip install -r requirements.txt
```

As versões Python estão em `requirements.txt` (UTF-16; preserve a codificação). A instalação completa em ambiente vazio ainda precisa ser validada. Para atualizar produção, use o guia do servidor.

## Configuração privada

1. Use `.env.example` como modelo e preencha somente o arquivo privado.
2. Salve como `.env` ao lado de `main.py`, ou defina `DJ_ENV_FILE` com o caminho absoluto antes de iniciar o processo.
3. Reinicie o processo após alterar a configuração. Variáveis do Windows têm prioridade, inclusive quando vazias.

O leitor `backend/platform/environment.py` atende as duas arquiteturas. TD e sessão usam `DJ_TD_ODBC_CONNECTION_STRING` e `DJ_SESSION_SECRET_KEY`; o legado também exige as variáveis das demais integrações. Preencha os grupos indicados no modelo e preserve a chave de sessão atual.

Nunca versione valores privados. A leitura do arquivo exige `python-dotenv==1.2.4` no Python de cada processo.

## Build e localhost

Na raiz, em ambiente autorizado:

```bat
cd frontend
npm ci
npm run build:local
cd ..
```

O build verifica os tipos e gera `backend/static/app/`. Publique a pasta inteira, incluindo `.vite/manifest.json`. O Git não inclui esses arquivos.

Para conferir a aplicação integrada, use o build servido pelo Flask e um IIS local configurado conforme o [guia do servidor](handbook/servidor-e-publicacao.md). Eventos fica em `/app/eventos` e usa sempre a API real. `npm run dev` serve apenas a interface; o Vite atual não encaminha `/api/v1/` ao Flask.

A inicialização pode criar tabelas, iniciar threads e acessar recursos corporativos. Localhost não isola esses recursos; valide login e permissões pelo IIS, sem usar a identidade de fallback. Cadastros e integrações precisam de dados de teste autorizados. Agentes seguem a análise estática definida em `AGENTS.md`.

## Guias

| Guia | Assunto |
|---|---|
| [Arquitetura modernizada](handbook/arquitetura-modernizada.md) | Criar features, reutilizar código e migrar o legado. |
| [Servidor e publicação](handbook/servidor-e-publicacao.md) | IIS, serviços, dependências offline, atualização e retorno. |
| [Publicação no Azure](handbook/publicacao-azure.md) | Levar a versão do código para o repositório oficial. |

Índice completo: [handbook/](handbook/README.md).
