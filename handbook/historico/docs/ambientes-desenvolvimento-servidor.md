> **Registro histórico.** Pode conter decisões, caminhos e comandos superados. Consulte o [manual atual](../../README.md); este arquivo não define o padrão vigente.

# Ambientes de desenvolvimento e servidor — Digital JOST

Registro atualizado em **09/10/2026**, com base nas informações fornecidas pelo responsável, no resultado da instalação de pacotes enviado e na leitura estática do repositório.

**Resultado informado pelo responsável:** o Digital Jost funcionou corretamente no servidor após instalar as dependências da integração com Vue/Eventos. Não foi informado um roteiro detalhado dos testes realizados.

Este documento registra o ambiente atual e o procedimento manual combinado. As restrições de execução por agentes continuam definidas em [AGENTS.md](../../../AGENTS.md).

**Publicação consolidada posterior:** para levar o servidor da base `c3838b0` ao código `6eeffa8`, usar [Publicação no servidor](publicacao-modernizacao-servidor.md). O roteiro reúne o backend completo, os 13 arquivos legados alterados, novo build, configuração privada, comandos incrementais offline e retorno. As listas históricas abaixo não incluem sozinhas toda essa entrega; a versão efetivamente instalada ainda precisa ser confirmada.

As informações do servidor são o relato da época. As instruções de build, os caminhos de recursos e a lista de arquivos da publicação foram atualizados para o código preparado na entrega 3b; isso não registra uma publicação nem uma verificação posterior no IIS.

**Evolução posterior do código:** Eventos foi transferido para `backend/modules/events/` e a chave `EVENTS_ENABLED` foi removida. A entrega 2 introduz configuração e engine/pool próprios do backend moderno, para o mesmo banco TD configurado na aplicação. O registro abaixo conserva o procedimento da época; seus caminhos `app/modules/` e instruções de ativação não descrevem o fluxo atual. Consulte o [registro da entrega 2](plano-separacao-backend-legado.md#10-registro-da-entrega-2) para a composição, as opções de pool e a publicação preparadas no código. Essa evolução ainda não foi verificada no servidor.

**Entrega 3a:** a leitura do manifesto e a renderização do shell Vue passaram para `backend/platform/vue_shell.py`. Os caminhos de template/assets foram preservados; o template recebe o título da funcionalidade. As rotas de Eventos, o renderizador e o template precisam ser publicados juntos, conforme o [registro da entrega 3a](plano-separacao-backend-legado.md#11-registro-da-entrega-3a). Esta extração ainda não foi verificada no servidor.

**Entrega 3b:** o template passa para `backend/templates/app/shell.html` e o build para `backend/static/app/`. O blueprint moderno mantém a URL `/static/app/`. Preparar o build inteiro no novo destino e publicar junto com o bootstrap e o renderizador, conforme o [registro da entrega 3b](plano-separacao-backend-legado.md#12-registro-da-entrega-3b). Essa versão ainda não foi verificada no servidor.

**Entrega S1:** TD e sessão passam a exigir `DJ_TD_ODBC_CONNECTION_STRING` e `DJ_SESSION_SECRET_KEY` no ambiente dos processos, preservando por decisão do responsável seus valores atuais. O backend lê o TD diretamente; o legado preserva `CNNX_JDT`. Preparar o ambiente do PC, IIS e consumidores dos quatro serviços antes de publicar os quatro arquivos Python relacionados, conforme o [guia de configuração externa](configuracao-externa-td-sessao.md). Nenhuma variável foi cadastrada e esta entrega não foi verificada no servidor. O modelo `.env.example` não é carregado pela aplicação.

**Entrega S1b:** a configuração atual lê um `.env` privado na raiz ou arquivo absoluto indicado por `DJ_ENV_FILE`, com prioridade para o ambiente Windows. As outras credenciais identificadas também são externas. O arquivo preenchido foi preparado apenas nesta cópia de trabalho, fora do Git; ele precisa de transferência privada para o PC. No servidor, usar variáveis dos processos ou arquivo fora da pasta publicada, com ACLs e dependência `python-dotenv==1.2.4` quando necessário. O IIS/Flask CLI deve receber `FLASK_SKIP_DOTENV=1` antes da inicialização para evitar a leitura antecipada pelo Flask. O [guia da S1b](configuracao-privada-integracoes.md) substitui o pacote de quatro arquivos da S1 e define a preparação dos serviços. Nada foi instalado, publicado ou verificado no servidor.

## 1. Ambiente de desenvolvimento

| Item | Informação conhecida |
|---|---|
| Computador | PC Windows da empresa |
| Projeto | Repositório Digital JOST, com `main.py`, `app/`, `frontend/` e `.venv/` |
| Execução habitual do backend | O responsável abre e executa `main.py` |
| Ambiente Python | `.venv` local; versão exata do Python local não informada |
| Banco | Banco corporativo também usado durante os testes em localhost, por decisão do responsável |
| Frontend | Vue 3, TypeScript, Vite, Tailwind CSS, PrimeVue/Volt e TanStack Vue Query |
| Node.js | Versão instalada no PC não informada; `frontend/package.json` declara `^22.18.0` ou `>=24.12.0` |
| Preparação de pacotes | Download no PC com internet, seguido de transferência de arquivos para o servidor |

O código-fonte Vue fica em `frontend/`. Para publicar pelo Flask, o responsável gera o build no computador de desenvolvimento, entrando em `frontend` e executando:

```cmd
npm run build:local
```

O script executa a verificação TypeScript e o build Vite. O destino definido em `frontend/vite.config.ts` é `backend/static/app/`, a partir da entrega 3b. A base dos arquivos no build é `/static/app/`; no servidor de desenvolvimento Vite, a base é `/app/`.

A pasta `backend/static/app/` está ignorada pelo Git. Ela precisa ser gerada e enviada inteira junto com os arquivos do backend. Um build existente compatível pode ser transferido inteiro para o novo destino; copiar somente os arquivos versionados não inclui o build. A pasta antiga `app/static/app/` continua ignorada como destino histórico, mas o shell moderno não a utiliza.

## 2. Servidor e acesso

| Item | Informação fornecida |
|---|---|
| Sistema | Windows Server; edição e versão não informadas |
| Servidor | `SVH-WEB-03` |
| Endereço interno | `10.0.0.28` |
| Acesso remoto | PAM Core, em `https://pam.randon.com.br/`, pela área Domain credentials |
| Hospedagem | IIS |
| Site no IIS | `Digital Jost` |
| Application Pool | `Digital Jost` |
| Pasta física | `I:\IIS\Digital_Jost` |
| URL da aplicação | `https://digitaljost.randon.com.br/` |
| Acesso à internet no servidor | Indisponível, conforme informado pelo responsável |
| Transferência de arquivos | Pasta pública acessível ao PC e ao servidor; caminho não informado |

O procedimento habitual de publicação é acessar o servidor pelo PAM, copiar arquivos pelo Explorador de Arquivos e usar o IIS Manager para parar e iniciar o site. O responsável acredita que o pool atende somente o Digital Jost; a exclusividade ainda não foi confirmada.

## 3. Python e configuração do IIS

O `web.config` informado usa `httpPlatformHandler` para iniciar o Python da `.venv` do site:

| Configuração | Valor informado |
|---|---|
| `processPath` | `I:\IIS\Digital_Jost\.venv\Scripts\python.exe` |
| `arguments` | `-m flask run --port %HTTP_PLATFORM_PORT%` |
| `FLASK_APP` | `I:\IIS\Digital_Jost\main.py` |
| `forwardWindowsAuthToken` | `true` |
| `startupTimeLimit` | `100` |
| `startupRetryCount` | `1` |
| `stdoutLogEnabled` | `true` |
| `stdoutLogFile` configurado | `I:\IIS\Digital_Jost\logs\stdout.log` |
| `maxAllowedContentLength` | `209715200` bytes |

Os handlers informados incluem o CGI para `*.py` e o `httpPlatformHandler` para `*`. A integração foi preparada para aproveitar esse site e esse processo Flask.

O `pyvenv.cfg` enviado informa:

- Python **3.13.2**.
- Python base em `C:\Python13`.
- `include-system-site-packages = false`.
- Comando histórico de criação apontando para `I:\IIS\Digital_Jost_Socket\.venv`.

O caminho histórico difere do caminho usado pelo IIS. A origem dessa diferença não foi confirmada. O resultado da instalação enviado mostra os pacotes instalados em `I:\IIS\Digital_Jost\.venv\Lib\site-packages`, que corresponde à pasta configurada para o site.

Os pacotes binários enviados na listagem, como `pyodbc.cp313-win_amd64.pyd`, indicam CPython 3.13 para Windows 64 bits. Esse foi o alvo usado no comando de download dos novos pacotes.

## 4. Convivência entre Flask/Jinja e Vue

| Caminho | Responsabilidade |
|---|---|
| `/` e rotas legadas | Páginas existentes do monólito Flask/Jinja |
| `/app/eventos` | Página Flask que carrega a interface Vue de Eventos |
| `/api/v1/events` | API de listagem e cadastro de Eventos |
| `/static/app/` | Arquivos JavaScript, CSS, fontes e outros recursos gerados pelo build |

O código-fonte de `frontend/` é transformado pelo build em arquivos servidos pelo Flask. Node e npm são usados no computador que prepara esse build; o procedimento adotado não inicia um processo Node no servidor.

O template `backend/templates/app/shell.html` contém o elemento onde o Vue monta a interface, o token CSRF e os links para os arquivos do build. No pacote preparado para o servidor, seu destino é:

```text
I:\IIS\Digital_Jost\backend\templates\app\shell.html
```

O backend lê `backend/static/app/.vite/manifest.json` e usa a entrada `index.html` para encontrar os arquivos. O blueprint `backend_vue` serve esse diretório em `/static/app/` e disponibiliza o template pelo nome `backend/app/shell.html`, distinguindo-o da cópia anterior no legado. É necessário copiar a pasta de build inteira, incluindo `.vite` e todos os recursos do mesmo build. As demais pastas de recursos do legado permanecem em `app/`.

### Configuração da aplicação registrada na época

A versão nova de `app/config.py`:

- Importa e cria `APIFlask`, com `json_errors=False`.
- Lê `EVENTS_ENABLED` do ambiente.
- Quando Eventos está habilitado, cria `EventsService` com `db.engine` e `GeneralEventsPermissions`.
- Chama `register_modules(app)` para registrar os blueprints novos.

A comparação dos arquivos local e do servidor fornecidos pelo responsável mostrou que as configurações de banco, sessão, e-mail, caminhos e pool de conexões eram iguais. As diferenças estavam na integração acima. Valores sensíveis não são reproduzidos neste documento.

Para habilitar Eventos pelo IIS, a entrada combinada deve ficar dentro de `<httpPlatform><environmentVariables>` no `web.config`, junto da variável `FLASK_APP` existente:

```xml
<environmentVariable name="EVENTS_ENABLED" value="1" />
```

Sem essa variável, Eventos fica desabilitado por padrão. APIFlask e Pydantic continuam necessários para carregar a versão nova do código, mesmo com Eventos desabilitado.

### Banco e acesso registrados na época

- O banco corporativo de referência foi informado como `TRANSFORMAÇÃODIGITAL_JOST`.
- A conexão reutilizada é `CNNX_JDT`, configurada em `SQLALCHEMY_DATABASE_URI`; Eventos recebe a engine existente `db.engine`.
- O responsável informou que a tabela `dbo.DJ_EVENTS` já foi criada.
- A estrutura esperada está em [20261007_create_dj_events.sql](../../../database/migrations/20261007_create_dj_events.sql): `id`, `name`, `description`, `created_by` e `created_at`.
- O cadastro usa uma transação e a listagem usa consultas parametrizadas.
- A aplicação reutiliza a sessão e o mecanismo de permissões existentes. Usuários autenticados com permissão `GENERAL` podem listar e cadastrar eventos.
- O cadastro também exige o token CSRF gerado pelo template e enviado pelo cliente HTTP.

Copiar o arquivo SQL não executa a criação da tabela. Não há uma etapa de recriação da tabela no procedimento de publicação descrito aqui.

## 5. Dependências observadas no servidor

Na listagem original enviada, já apareciam:

| Pacote | Versão |
|---|---|
| Flask | `3.1.1` |
| Werkzeug | `3.1.3` |
| Flask-Login | `0.6.3` |
| Flask-Principal | `0.4.0` |
| Flask-Mail | `0.10.0` |
| Flask-SQLAlchemy | `3.1.1` |
| SQLAlchemy | `2.0.41` |
| pyodbc | `5.2.0` |
| pip | `24.3.1` |

APIFlask e Pydantic não apareciam nessa listagem. O resultado posterior enviado pelo responsável confirmou a instalação de:

| Pacote | Versão instalada |
|---|---|
| APIFlask | `3.1.2` |
| pydantic | `2.13.5` |
| pydantic-core | `2.46.5` |
| typing-extensions | `4.16.0` |
| typing-inspection | `0.4.4` |
| annotated-types | `0.8.0` |
| apispec | `6.10.0` |
| marshmallow | `4.3.1` |
| webargs | `8.7.1` |
| flask-marshmallow | `1.5.0` |
| flask-httpauth | `4.8.1` |
| email-validator | `2.3.0` |
| dnspython | `2.8.0` |

O pip substituiu `typing-extensions` **4.14.1** por **4.16.0**. Os comandos usados fixam Flask em **3.1.1** e Werkzeug em **3.1.3**.

Essa lista registra o resultado daquela instalação; não é um inventário completo nem uma consulta atual ao ambiente. Não foi enviada confirmação de instalação de `pydantic-settings`, Ruff ou pytest no servidor, e eles não foram incluídos nos comandos preparados para Eventos.

## 6. Instalação sem internet no servidor

O fluxo utilizado foi:

```text
PC com internet
  → download dos arquivos .whl e dependências
  → pasta pública
  → I:\IIS\Digital_Jost\pacotes-eventos
  → instalação na .venv do servidor
```

Os comandos exatos ficam nestes arquivos:

- [baixar-dependencias-eventos-pc.txt](baixar-dependencias-eventos-pc.txt): executar no CMD do PC, na raiz do projeto. O comando usa `.venv\Scripts\python.exe` e cria a pasta `pacotes-eventos`, com os pacotes para Windows 64 bits e CPython 3.13.
- [instalar-dependencias-eventos-servidor.txt](instalar-dependencias-eventos-servidor.txt): executar no CMD do servidor depois de copiar a pasta inteira. O comando usa caminhos absolutos e instala com `--no-index --find-links`, sem consultar um índice de pacotes na internet.

Não é necessário ativar a `.venv` para esses comandos. No servidor, o comando pode ser executado de qualquer diretório do CMD. A pasta de pacotes precisa estar no caminho indicado no arquivo.

## 7. Arquivos da publicação

Lista geral do pacote da entrega 3b. A S1b exige também os nove arquivos Python e a preparação do [guia de configuração privada](configuracao-privada-integracoes.md); não publicar somente a lista resumida abaixo. Todos os caminhos são relativos a `I:\IIS\Digital_Jost`; essa orientação não comprova que os arquivos já foram copiados:

| Arquivo ou pasta | Ação |
|---|---|
| `app/config.py` | Na S1, publicar junto dos demais arquivos Python relacionados, após provisionar TD/sessão no ambiente dos processos |
| `app/utils/constants.py` | Na S1, publicar a leitura externa de `CNNX_JDT`; preservar as demais configurações legadas |
| `backend/` | Copiar o pacote completo, incluindo bootstrap, plataforma, módulos e templates |
| `backend/templates/app/shell.html` | Incluir o template no pacote moderno |
| `backend/static/app/` | Copiar o build inteiro, incluindo `.vite/manifest.json`; essa pasta é ignorada pelo Git |
| `web.config` | Preservar a configuração efetiva e incluir `FLASK_SKIP_DOTENV=1` na S1b; Eventos não exige variável de ativação |

`main.py` continua sendo o ponto de entrada e não precisou ser alterado para registrar Eventos: a integração é feita em `create_app()`.

A pasta `frontend/` pode acompanhar a publicação como código-fonte. O funcionamento depende também do build em `backend/static/app/`. Copiar `requirements.txt` apenas registra as dependências; não as instala. Guardar o pacote anterior, incluindo o build completo no destino anterior, para o retorno previsto no plano de separação.

Para novas atualizações, guardar uma cópia dos arquivos substituídos, parar o site durante a cópia, preservar a `.venv`, os uploads e as configurações corporativas, e reiniciar o processo da aplicação pelo IIS. Antes de reiniciar o pool, confirmar quais aplicações o utilizam.

As conferências combinadas foram: página inicial, uma funcionalidade legada, abertura de `/app/eventos`, atualização com F5, listagem e cadastro persistente de um evento autorizado. O relato de sucesso não detalhou quais dessas conferências foram realizadas.

## 8. Ocorrência e resultado da publicação

1. O responsável informou que o portal ficou indisponível quando substituiu `app/config.py` pela versão nova antes de instalar as dependências.
2. A falta de APIFlask/Pydantic foi apontada como causa provável, porque a inicialização nova importa essas bibliotecas. Não foi enviado um traceback para confirmar o erro exato daquela tentativa.
3. O responsável transferiu os pacotes e executou a instalação offline. O resultado terminou com `Successfully installed` na `.venv` do site.
4. Em **09/10/2026**, informou que a aplicação funcionou corretamente no servidor após instalar as dependências.

Esse resultado foi confirmado pelo responsável que acessa o ambiente. O agente não acessou o servidor, não iniciou a aplicação e não executou instalações, consultas ou testes.

## 9. Informações ainda não confirmadas

- Versões efetivas de Python, Node e npm no computador de desenvolvimento.
- Caminho da pasta pública usada na transferência.
- Edição e versão do Windows Server e versão do IIS.
- Exclusividade do Application Pool `Digital Jost`.
- Origem do caminho `Digital_Jost_Socket` no `pyvenv.cfg` enviado.
- Conteúdo completo do `web.config` após a publicação e roteiro detalhado dos testes realizados.

**O sistema não foi executado; a validação foi somente estática.** O funcionamento no servidor foi informado pelo responsável.
