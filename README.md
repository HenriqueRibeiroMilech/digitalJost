# Digital JOST

Portal interno da JOST para demandas, operações industriais, laboratório, desvios, monitoramento, relatórios e gestão de usuários. O sistema funciona em Windows/IIS e está sendo modernizado aos poucos, mantendo as telas antigas em operação.

Este README apresenta o projeto e reúne a preparação inicial do ambiente. Os procedimentos detalhados de arquitetura, servidor e publicação ficam na documentação oficial em `handbook/`.

A documentação oficial fica em [handbook/](handbook/README.md). Comece pelo guia de [arquitetura modernizada](handbook/arquitetura-modernizada.md) para entender a base atual, criar novas features e acompanhar as propostas de evolução.

## 1. Como as duas arquiteturas convivem

```text
Navegador → IIS / autenticação Windows → aplicação Flask
                                         ├─ app/: páginas Jinja e rotas antigas
                                         └─ backend/: APIs e página base do Vue
                                                           ↑
                                              build gerado por frontend/
```

| Parte | Responsabilidade atual |
|---|---|
| `main.py` e `app/config.py` | Criam a aplicação, registram módulos e mantêm extensões, sessão e ciclo global. |
| `app/` | Arquitetura antiga: rotas, templates, usuários, permissões, integrações, arquivos e schedulers. Continua necessária. |
| `backend/` | Arquitetura nova: módulos Python, configuração própria, acesso geral ao TD, infraestrutura HTTP e shell Vue. |
| `frontend/` | Código Vue/TypeScript, navegação e componentes. Seu build é publicado dentro de `backend/`. |

**Banco:** as duas arquiteturas acessam o mesmo banco TD. Cada uma mantém seus mecanismos de conexão; a nova tem uma engine e um pool compartilhados por todos os seus módulos, por instância da aplicação. Pool é um conjunto de conexões reutilizáveis. Não existe um banco ou uma conexão exclusiva de Eventos. Transações antigas e novas continuam independentes.

**Identidade:** a nova arquitetura reaproveita o login, a sessão e os perfis antigos por uma ponte em `backend/compatibility/`. Ela ainda não é uma aplicação independente de `app/`.

## 2. Onde encontrar cada coisa

```text
Digital_Jost/                       ← raiz: pasta que contém main.py
├── main.py                         # Entrada da aplicação e blueprints antigos
├── web.config                      # Hospedagem no IIS
├── requirements.txt                # Versões das dependências Python
├── .env.example                    # Modelo sem credenciais
├── .env                            # Arquivo privado opcional; nunca versionar
├── app/
│   ├── config.py                   # Factory, extensões e sessão compartilhada
│   ├── routes/                     # Backend antigo por domínio
│   ├── templates/                  # Jinja, includes JavaScript e e-mails
│   ├── static/                     # CSS/JS/imagens e uploads operacionais
│   ├── services/                   # Serviços Windows e jobs
│   └── utils/                      # Banco, segurança e integrações antigas
├── backend/
│   ├── bootstrap.py                # Composição da arquitetura nova
│   ├── config.py                   # Configuração do TD e do pool moderno
│   ├── compatibility/              # Ponte com identidade antiga
│   ├── platform/                   # Banco, ambiente, HTTP, CSRF e shell Vue
│   ├── modules/events/             # Rotas, schemas, serviços e repositório
│   ├── templates/app/shell.html    # Página que carrega o Vue
│   └── static/app/                 # Build gerado; não acompanha o Git
├── frontend/
│   ├── package.json / package-lock.json
│   └── src/                        # Features Vue e recursos compartilhados
└── handbook/                      # Documentação oficial
```

`main.py` é a referência dos blueprints antigos registrados; `backend/modules/__init__.py`, dos novos. Computadores, temporário, horas produtivas e setup estão sem registro ativo no estado atual. Arquivos `Copy`, `BKP` e similares podem ser históricos.

## 3. Dependências e preparação do computador

| Requisito | Uso |
|---|---|
| Windows e Python 3.13 de 64 bits | Referência do servidor; há dependências específicas de Windows. |
| Driver ODBC compatível com as conexões configuradas | Acesso ao SQL Server; instalar `pyodbc` não instala o driver do Windows. |
| Acesso corporativo e permissões | TD, FTM, Plex, Trace QR, LDAP e demais integrações necessárias. |
| Node `^22.18.0` ou `>=24.12.0`, com npm | Instalação e build do Vue no computador de desenvolvimento. |
| IIS, autenticação Windows e `httpPlatformHandler` | Hospedagem atual e validação da identidade real. |

O Python usa Flask/APIFlask, SQLAlchemy, pyodbc, pandas, Flask-Login/Principal/Mail, APScheduler e pywin32, além de clientes LDAP, Microsoft Graph, SAP SOAP e Oracle. O frontend usa Vue 3, TypeScript, Vite, Vue Router, Tailwind, PrimeVue/Volt e TanStack Query.

As versões estão em `requirements.txt` e nos manifests de `frontend/`. O arquivo Python está em UTF-16; preserve sua codificação ao editá-lo. Ele é um inventário de versões e a instalação completa em ambiente vazio ainda precisa ser validada; não force versões incompatíveis para concluir uma instalação.

Em um **ambiente novo e autorizado**, abra o **Command Prompt (CMD)** na raiz do projeto:

```bat
py -3.13 -m venv .venv
".venv\Scripts\python.exe" -m pip install -r requirements.txt
```

Esses comandos não são o procedimento de atualização de um servidor já funcionando. Usar o caminho completo do Python evita instalar pacotes no interpretador errado. O isolamento da `.venv` é descrito na [documentação do Python](https://docs.python.org/3.13/library/venv.html).

## 4. Configuração privada: vale para as duas arquiteturas

O leitor comum está em `backend/platform/environment.py`. Ele atende o backend novo e os pontos adaptados do antigo, inclusive serviços Windows.

1. Copie `.env.example` para um arquivo privado e preencha os valores existentes pelo canal seguro da empresa. Não publique credenciais no modelo.
2. Sem `DJ_ENV_FILE`, o leitor procura **`.env` na raiz, ao lado de `main.py`**.
3. Para outro nome/local, defina `DJ_ENV_FILE` no ambiente do processo, com o caminho absoluto. O seletor precisa existir antes da inicialização.
4. Variáveis já existentes no ambiente do Windows têm prioridade sobre o arquivo, inclusive valores vazios. O arquivo é lido uma vez; alterações exigem reiniciar o processo afetado.

| Grupo | Variáveis e finalidade |
|---|---|
| Compartilhado | `DJ_TD_ODBC_CONNECTION_STRING`: conexão geral do TD; `DJ_SESSION_SECRET_KEY`: assinatura da sessão Flask. |
| Bancos antigos | `DJ_FTM_ODBC_CONNECTION_STRING`, `DJ_PLEX_ODBC_CONNECTION_STRING`, `DJ_TRACE_QR_ODBC_CONNECTION_STRING`. |
| MES e LDAP | Pares `DJ_MES_USER`/`DJ_MES_PASSWORD` e `DJ_LDAP_USER`/`DJ_LDAP_PASSWORD`. |
| Microsoft/Teams | `DJ_MICROSOFT_TENANT_ID`, `DJ_MICROSOFT_CLIENT_ID`, `DJ_MICROSOFT_CLIENT_SECRET`, `DJ_MICROSOFT_USERNAME`, `DJ_MICROSOFT_PASSWORD`. |
| SAP | `DJ_SAP_USER` e `DJ_SAP_PASSWORD`. |
| Legado sem uso ativo confirmado | `DJ_PLEX_TEST_ODBC_CONNECTION_STRING` ainda é exigida no import das constantes. `DJ_ORACLE_USER`/`DJ_ORACLE_PASSWORD` são referenciadas em horas produtivas, atualmente desativado. |

Várias constantes e integrações antigas são carregadas já na inicialização. Por isso, preencher somente TD e sessão não basta para subir o portal inteiro. Preserve a chave de sessão atual para evitar invalidar as sessões existentes.

## 5. Frontend e teste em localhost

No computador autorizado, a partir da raiz, instale pelo lockfile e gere o build:

```bat
cd frontend
npm ci
npm run build:local
cd ..
```

O comando verifica os tipos e gera **`backend/static/app/`**, incluindo **`.vite/manifest.json`**. O backend encontra o build nesse local automaticamente. Publique a pasta inteira, com manifest e assets da mesma compilação. Ela é ignorada pelo Git: um pull não produz esses arquivos. O comportamento de instalação pelo lockfile está na [documentação do npm](https://docs.npmjs.com/cli/v11/commands/npm-ci/).

Para conferir o fluxo completo em localhost, prepare um IIS local com autenticação Windows, os caminhos locais do Python/`main.py` e o ambiente privado, seguindo a estrutura do [guia de servidor](handbook/servidor-e-publicacao.md#1-como-o-servidor-funciona-hoje). Use dados e acessos autorizados para esse ambiente. **Ainda não há isolamento automático dos bancos corporativos nem um procedimento de testes sem efeitos externos.** Executar `main.py` fora do IIS usa fallback de identidade e não comprova login ou permissões reais.

Eventos usa diretamente a API real do Flask, inclusive durante o desenvolvimento. `npm run dev` inicia apenas o servidor da interface; a configuração atual do Vite não encaminha `/api/v1/` ao Flask. Para conferir o fluxo integrado, use o build servido pelo backend, com sessão e token CSRF fornecidos pelo portal.

Após a preparação autorizada, confira pela web: uma tela antiga, `/app/eventos`, atualização da página com F5, paginação e perfis de acesso. Cadastros e testes de integrações precisam de registros de teste aprovados, pois podem gravar dados ou enviar notificações.

## 6. Servidor e publicação

O portal é hospedado em Windows/IIS e possui schedulers separados, executados como serviços Windows. O site e os serviços podem usar interpretadores Python diferentes; mudanças em configuração, código ou dependências compartilhadas precisam considerar os processos afetados.

Consulte o guia de [servidor e publicação](handbook/servidor-e-publicacao.md) para configurar o IIS, conferir os serviços, instalar dependências offline, publicar mudanças e retornar à versão anterior.

O [guia de publicação no Azure](handbook/publicacao-azure.md) explica como transferir a versão do código para o repositório oficial. A atualização do servidor segue o procedimento próprio acima.
