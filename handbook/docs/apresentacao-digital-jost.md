# Digital JOST — apresentação, arquitetura e mapa de conexões

Material de apoio para apresentação a público misto, com duração de 15–20 minutos. O roteiro principal está nas seções 1–8; o mapa detalhado de conexões e as perguntas servem como consulta durante a preparação e a conversa final.

Este material descreve o código disponível no repositório. Código implementado, schema aplicado, serviços habilitados e versão publicada são estados diferentes. A análise não confirma o ambiente corporativo.

Os caminhos citados partem da raiz do projeto; os links são relativos à localização deste documento. São citados nomes de variáveis de configuração, sem valores de credenciais, tokens, strings de conexão ou dados operacionais.

## 1. Abertura: o projeto em 30 segundos

> “O Digital JOST é um portal interno que reúne ferramentas de demandas, laboratório, desvios de processo, planejamento, monitoramento e relatórios. O servidor utiliza Python com Flask. As telas antigas usam HTML/Jinja e JavaScript, enquanto as modernas usam Vue e APIs. A modernização ocorre gradualmente, preservando os fluxos operacionais.”

Três ideias para apresentar primeiro:

- O sistema centraliza ferramentas de várias áreas.
- O legado e o moderno convivem na mesma aplicação Flask.
- Além das páginas, existem automações executadas em serviços Windows.

## 2. Roteiro de 15–20 minutos

| Parte | Tempo sugerido | O que explicar |
|---|---|---|
| Objetivo do portal | 1 min | Problemas atendidos e principais áreas. |
| Arquitetura geral | 2 min | Navegador, IIS, Flask, bancos e serviços. |
| Antigo e moderno | 3 min | Jinja versus Vue/API e organização do código. |
| Um fluxo de código | 3 min | Criar um evento, da interface ao banco. |
| Conexões e identidade | 2 min | Principais fontes, onde estão e por que são usadas. |
| Automações | 1 min | S30, M5, H24 e Auto. |
| Migração e novas funcionalidades | 4 min | Mapear comportamento, implementar, validar e publicar. |
| Perguntas | 2 min | Consultar o mapa de conexões e os arquivos de referência. |

O mapa detalhado da seção 9 é material de apoio. Na apresentação, escolha dois exemplos: o TD utilizado por Eventos e o fluxo de alteração de paradas, que envolve TD, Plex ou FTM.

## 3. Arquitetura geral

```text
Pessoa no navegador
        ↓
IIS no Windows — hospedagem e encaminhamento da identidade Windows
        ↓
Aplicação Flask/APIFlask — main.py + app/config.py
        ├── Legado: rotas → HTML/Jinja + JavaScript
        ├── Moderno: shell HTML → Vue ↔ APIs JSON
        └── Bancos, arquivos e integrações

Em processos separados:
Serviços Windows → jobs → bancos, arquivos e notificações
```

É um **monólito em modernização gradual**: os módulos pertencem à mesma aplicação web. O backend moderno ainda reutiliza identidade, sessão e perfis do legado; não é um backend totalmente independente.

| Local | Responsabilidade |
|---|---|
| [main.py](../../main.py) | Chama a factory e registra os blueprints legados. |
| [app/config.py](../../app/config.py) | Cria a aplicação; configura banco, login, permissões, e-mail e ciclos globais; inicializa o backend moderno. |
| [backend/__init__.py](../../backend/__init__.py) | Compõe banco moderno, diretório LDAP, armazenamento de anexos, shell e módulos. |
| [backend/modules/__init__.py](../../backend/modules/__init__.py) | Registra explicitamente os módulos modernos. |
| [frontend/src/router/index.ts](../../frontend/src/router/index.ts) | Associa endereços às páginas Vue. |
| [web.config](../../web.config) | Configuração versionada da hospedagem IIS e do processo Flask. |

Uma rota Vue também precisa de uma entrada Flask autorizada para abertura direta e atualização com F5. O Router usa a base `/app/`; as APIs modernas ficam em `/api/v1/`.

## 4. Arquitetura antiga e moderna

| Aspecto | Legado | Moderno |
|---|---|---|
| Interface | HTML/Jinja, CSS e JavaScript. | Vue 3 e TypeScript. |
| Renderização | Jinja monta HTML no servidor; JavaScript complementa a interação. | Vue monta a interface e consulta APIs JSON. |
| Backend | `app/routes/`, com organização variável. | `backend/modules/<feature>/`. |
| Validação | Implementação específica por fluxo. | Schemas Pydantic e regras na operação. |
| Persistência | Muito SQL textual, pandas, SQLAlchemy e pyodbc. | ORM SQLAlchemy como primeira opção; SQL excepcional parametrizado. |
| Identidade | Windows/IIS, Flask-Login e perfis existentes. | Ponte que reaproveita a identidade e os perfis do portal. |
| Recursos comuns | Principalmente `app/utils/`. | Principalmente `backend/shared/`. |

### 4.1. O legado não tem uma estrutura única

Algumas rotas antigas concentram HTTP, regras e SQL. Outras funcionalidades já estão organizadas em camadas, como o Gerenciador de Demandas:

```text
app/routes/demandManagement/
    routes.py → services.py → repository.py → banco
    domain.py: opções, validações e erros
    integration.py: arquivos e notificações

app/templates/demandManagement/: HTML/Jinja
app/static/: CSS e JavaScript da tela
```

| Arquivo | O que explicar |
|---|---|
| [routes.py](../../app/routes/demandManagement/routes.py) | Recebe a requisição, verifica acesso/CSRF e chama o serviço. |
| [services.py](../../app/routes/demandManagement/services.py) | Coordena casos de uso, validações e transações. |
| [repository.py](../../app/routes/demandManagement/repository.py) | Executa SQL com a conexão recebida. |
| [integration.py](../../app/routes/demandManagement/integration.py) | Encapsula armazenamento e notificações do módulo. |

Exemplo: `create_personal_demand()` valida os dados e o responsável, abre `self.engine.begin()`, chama o repositório e obtém os detalhes depois da confirmação.

### 4.2. Estrutura moderna por funcionalidade

```text
backend/modules/<feature>/
├── __init__.py       exportação dos blueprints
├── routes.py         HTTP, autorização, regras e operações ORM
├── schemas.py        contratos de entrada e saída
├── models.py         representação das tabelas
└── domain.py         definições e erros, quando necessário

frontend/src/features/<feature>/
├── pages/            coordenação das páginas
├── components/       formulários, cards e detalhes da feature
├── api.ts            chamadas HTTP
└── types.ts          contratos TypeScript
```

> “O schema define os dados, o model representa a tabela e a rota coordena a operação com ORM.”

Service e Repository não são camadas obrigatórias no backend moderno. Funções ou arquivos adicionais entram quando há responsabilidade, volume ou reutilização que justifiquem a extração. Modelos não fazem commits nem chamam integrações.

O frontend reutiliza o cliente HTTP em [client.ts](../../frontend/src/shared/api/client.ts), os controles locais de `volt/` e componentes como `PageHeader`, `RecordCard`, `RequestState`, `ListPagination`, `FormField` e `AppDialog`. TanStack Query organiza consultas, cache e atualização de dados.

## 5. Exemplo para mostrar o código: criar um evento

```text
Formulário Vue
    → events/api.ts
    → POST /api/v1/events
    → sessão + perfil + CSRF
    → permissão events.create + schema EventCreate
    → regras de período e tipo do evento
    → transação ORM no TD
    → resposta JSON com status 201
    → atualização da listagem Vue
```

Ordem sugerida para abrir os arquivos:

| Ordem | Arquivo | O que mostrar |
|---|---|---|
| 1 | [EventsPage.vue](../../frontend/src/features/events/pages/EventsPage.vue) | Listagem, filtros, carregamento e atualização das consultas. |
| 2 | [EventForm.vue](../../frontend/src/features/events/components/EventForm.vue) | Campos e interação do formulário. |
| 3 | [api.ts](../../frontend/src/features/events/api.ts) | `create()` envia o POST pelo cliente compartilhado. |
| 4 | [routes.py](../../backend/modules/events/routes.py#L120) | Decorators, regras, sessão e transação da criação. |
| 5 | [schemas.py](../../backend/modules/events/schemas.py) | Campos, tipos e limites de `EventCreate`. |
| 6 | [models.py](../../backend/modules/events/models.py) | Modelos de eventos, tipos, listas e presenças. |

Na rota `create_event`, explique:

- `@events_bp.post("")`: define o método e a rota dentro do prefixo do blueprint.
- `@require_action("events.create")`: exige permissão para a ação.
- `@events_bp.input(EventCreate)`: valida a entrada pelo schema.
- `@events_bp.output(EventOut, status_code=201)`: define a resposta pública.
- `get_td_session_factory()`: obtém a factory compartilhada do TD moderno.
- `with sessions.begin() as session`: delimita a transação; a saída bem-sucedida confirma as alterações, e uma exceção provoca rollback.
- `session.add(event)`: inclui o objeto na sessão ORM.
- `session.flush()`: envia alterações ao banco e obtém valores gerados, como o ID, sem confirmar a transação.
- O retorno de sucesso fica depois do bloco transacional.

Regras concretas para comentar: o fim deve ser posterior ao início e o tipo informado precisa existir. O schema valida formato e limites; as regras que dependem de dados persistidos continuam no backend.

## 6. Identidade, permissões e integridade

> “Autenticação identifica quem é a pessoa. Autorização define o que ela pode fazer e quais registros pode acessar.”

O IIS encaminha o token Windows. O legado estabelece a sessão com Flask-Login e utiliza perfis resolvidos com Flask-Principal. O moderno reaproveita essa identidade por [backend/shared/identity.py](../../backend/shared/identity.py).

Em [backend/shared/http.py](../../backend/shared/http.py), `configure_api()` aplica autenticação, perfil geral e CSRF. A permissão da ação e a autorização por registro continuam nas operações. Esconder um botão no Vue não autoriza nem protege uma escrita.

Conceitos de banco para explicar:

| Termo | Significado neste projeto |
|---|---|
| Engine/pool | Recurso que administra e reutiliza conexões. |
| Factory de sessões | Recurso compartilhado que cria sessões ORM por operação. |
| Sessão ORM | Unidade de trabalho que consulta e acompanha alterações. |
| Transação | Alterações que precisam ser confirmadas ou desfeitas juntas. |

Conexões ou sessões diferentes não formam automaticamente uma única transação. Um commit SQL não torna arquivos, LDAP, e-mails ou chamadas HTTP atômicos. Operações coordenadas precisam preservar seus tratamentos de falha, histórico, idempotência e concorrência.

## 7. Como migrar uma funcionalidade antiga

### 7.1. Mapear antes de reconstruir

```text
Menu/URL
    → registro do blueprint
    → guardas e permissões
    → todos os métodos HTTP e seletores de operação
    → templates/JavaScript ou componentes
    → filtros e payloads
    → tabelas e transações
    → anexos, downloads e exports
    → integrações e notificações
    → jobs e outros leitores/escritores
```

Não analisar apenas o GET. No legado, POST também pode consultar, exportar ou selecionar operações por `type`, `cmd`, `area` e `id`.

### 7.2. Definir um recorte de entrega

Exemplo proposto, sem afirmar que já foi implementado: modernizar primeiro uma consulta de laboratório, preservando filtros e permissões; migrar aprovações, anexos e equipamentos em entregas posteriores.

Antes da implementação, decidir:

- Quais comportamentos serão preservados ou alterados intencionalmente.
- Se as tabelas existentes serão reutilizadas ou se haverá evolução de dados explicitamente revisada.
- Quem continuará escrevendo nos mesmos registros durante a convivência.
- Como impedir processamento e notificações em duplicidade.
- Quais versões de backend, frontend, schema e jobs precisam ser compatíveis.
- Como retornar de versão preservando dados já gravados.

### 7.3. Implementar e validar a convivência

Criar o módulo moderno e a interface Vue, reutilizar os recursos compartilhados e registrar as entradas. Conferir permissões, contratos, transações e consumidores antigos. A verificação funcional e a publicação dependem de ambiente autorizado.

Uma migração de tela não migra automaticamente os dados. Em Demandas, por exemplo, o legado usa `JDT_DEMAND_MANAGEMENT` e o moderno possui `DJ_DEMANDS` e `DJ_DEMAND_WORK`. O gerenciador antigo continua separado; não há importação ou sincronização automática dos registros legados.

> “Migrar uma feature exige tratar seu comportamento completo: interface, regras, dados, permissões, arquivos, integrações e automações.”

## 8. Desenvolvimento de novas funcionalidades e publicação

1. **Definir o caso de uso:** usuários, ações, estados, regras e critérios de aceitação.
2. **Definir contratos e dados:** schemas de entrada/saída, filtros, paginação, tabelas e alterações de banco quando necessárias e autorizadas.
3. **Implementar o backend:** módulo em `backend/modules/`, ORM sobre a base moderna, identidade e proteção HTTP compartilhadas; leituras com `sessions()` e escritas com `sessions.begin()`.
4. **Implementar o Vue:** feature em `frontend/src/features/`, usando cliente HTTP, tipos, componentes e estilos compartilhados.
5. **Registrar acessos:** blueprints, entrada Flask, rota Vue e navegação, com autorização no servidor.
6. **Conferir efeitos além da tela:** jobs, arquivos, integrações, histórico, versão do registro e repetição de envios.
7. **Revisar e verificar:** comparar frontend/backend e diff; testes, build, conexões e uso do navegador exigem autorização explícita conforme as regras do projeto.
8. **Preparar a entrega:** código, build compatível, dependências quando necessárias, configuração privada e scripts SQL revisados/aplicados separadamente pelo responsável.
9. **Publicar e acompanhar em ambiente autorizado:** conferir sessão, permissões, F5, assets, operações, jobs e procedimento de retorno.

O build Vue é gerado em `backend/web/static/app/` e servido em `/static/app/`. Essa pasta é ignorada pelo Git. Pull e push não geram o build nem implantam automaticamente o IIS. Retornar o código não desfaz gravações ou anexos.

No estado observado, o código moderno inclui Eventos, Solicitações e Gerenciador de Demandas. Demandas modernas atendem Transformação Digital. A documentação específica de [Demandas](../../handbook/features/demandas.md) já descreve o gerenciador, enquanto alguns textos gerais ainda registram um estágio anterior.

## 9. Mapa detalhado das conexões

### 9.1. Onde ficam os valores privados

O leitor comum está em [backend/shared/environment.py](../../backend/shared/environment.py):

- `load_environment()` usa o arquivo indicado por `DJ_ENV_FILE`, quando configurado, ou `.env` na raiz do repositório.
- Variáveis já definidas no ambiente têm precedência; o carregamento usa `override=False`.
- `required_env()` obtém uma variável obrigatória e rejeita ausência ou valor vazio.
- Ler a configuração como texto não comprova que o destino exista ou aceite conexões.

As configurações efetivas pertencem ao ambiente privado do site e dos serviços. O arquivo privado não foi aberto para elaborar este documento. Não é necessário mostrar valores de conexão para explicar a arquitetura.

### 9.2. Visão rápida: fonte, localização e uso

| Conexão/integração | Onde é configurada ou construída | Onde é usada e para quê |
|---|---|---|
| TD/JDT legado | `app/utils/constants.py`, `app/utils/db_utils.py` e `app/config.py`. | Usuários, demandas, laboratório, desvios, planejamento, logs e jobs. |
| TD moderno | `backend/config.py`, `backend/shared/database.py` e `backend/__init__.py`. | Eventos, solicitações, gerenciador, tarefas e históricos modernos. |
| FTM | `app/utils/constants.py` e `app/utils/db_utils.py`. | Dados industriais, OEE, centros de trabalho e alteração de motivos de parada em fluxo específico. |
| Plex via SQL/ODBC | `app/utils/constants.py`, `app/utils/db_utils.py` e SQL com `OPENQUERY`. | Produção, paradas, OEE, catálogos e monitoramento; também atualização de status em fluxo específico. |
| Plex via API HTTP | Credenciais em `constants.py`; helper em `data_utils.py`; chamada em `request/workcentersLogChange.py`. | Aplicação de alteração de parada no Plex. |
| Trace QR | `app/utils/constants.py` e `app/utils/db_utils.py`. | Cadastro, consulta e exportação de rastreabilidade e apoio a plaquetas. |
| LDAP legado | `app/routes/auth_routes.py` e `app/utils/security_utils.py`. | Identificação/cadastro de usuários no diretório corporativo. |
| LDAP moderno | `backend/config.py`, `backend/shared/employee_directory.py` e composição em `backend/__init__.py`. | Identificar funcionário pelo crachá na presença de Eventos. |
| SMTP | `app/config.py` e `app/utils/email_utils.py`. | E-mails de funcionalidades e verificações agendadas. |
| Identidade Microsoft + Graph/Teams | `app/utils/azure_utils.py`, `teams_utils.py` e `app/routes/jdt/userManager.py`. | Token de integração, alertas Teams e consulta de usuário Graph. |
| SAP SOAP | `app/routes/reports/maintenance.py`. | Consultas usadas nos relatórios de manutenção. |
| Oracle | `app/routes/reports/productiveHours.py`. | Consulta de ponto/frequência em módulo desativado no registro atual. |
| Power BI, FTWeb e SSRS | Rotas/templates de relatórios, cadastros externos e `app/templates/home.html`. | Painéis incorporados e links para aplicações externas. |
| Rede: DNS/ICMP | `app/utils/ping_utils.py`, consumido por `app/routes/jdt/monitoring.py`. | Verificações de disponibilidade e configuração de equipamentos. |

### 9.3. TD/JDT legado: dados do portal

**Configuração:** em [app/utils/constants.py](../../app/utils/constants.py), `CNNX_JDT` recebe `DJ_TD_ODBC_CONNECTION_STRING`.

**Construção do acesso:** [app/utils/db_utils.py](../../app/utils/db_utils.py) cria `_JDT_ENGINE`; `get_engine('jdt')` seleciona esse engine e `engine_run_query(..., 'jdt', ...)` é um helper de consulta.

Existe também o engine administrado por Flask-SQLAlchemy em [app/config.py](../../app/config.py), configurado por `SQLALCHEMY_DATABASE_URI` com `CNNX_JDT`. Alguns jobs e o login abrem acessos próprios por pyodbc ou SQLAlchemy. Portanto, o legado não utiliza um único pool global para todos os acessos ao TD.

| Consumidor concreto | Uso observado |
|---|---|
| [demandManagement/routes.py](../../app/routes/demandManagement/routes.py) | `_build_service()` passa `get_engine('jdt')` ao serviço do gerenciador antigo. |
| [demandManagement/repository.py](../../app/routes/demandManagement/repository.py) | Lê/grava demandas e consulta solicitações e usuários; referências como `JDT_DEMAND_MANAGEMENT`, `JDT_REQUEST_IMPROVEMENTS_SMALL` e `JDT_USER_DETAILS`. |
| [demandRequests/routes.py](../../app/routes/demandRequests/routes.py) | Compõe o serviço das solicitações legadas com TD. |
| [request/laboratory.py](../../app/routes/request/laboratory.py) | Solicitações, equipamentos e registros do laboratório. |
| [security_utils.py](../../app/utils/security_utils.py) | `access_register()` grava acessos em `JDT_USER_LOGS`. |
| [mon_mon_auto_laboratory.py](../../app/services/jobs/mon_mon_auto_laboratory.py) | Atualiza estados/logs de equipamentos e solicitações conforme agendamentos. |
| [mon_mon_auto_demandManagement.py](../../app/services/jobs/mon_mon_auto_demandManagement.py) | Início agendado e recorrência de demandas legadas. |

**Frase para apresentar:** “O TD é a base dos dados do portal, mas o legado possui mais de uma forma de acessar essa mesma fonte.”

### 9.4. TD moderno: mesmo recurso lógico, outro mecanismo de sessão

**Configuração:** [backend/config.py](../../backend/config.py), em `BackendConfig.from_env()`, lê `DJ_TD_ODBC_CONNECTION_STRING` e parâmetros de pool `BACKEND_TD_*`.

**Construção:** [backend/shared/database.py](../../backend/shared/database.py), em `init_td_database()`, cria engine/pool e `sessionmaker`. O bootstrap [backend/__init__.py](../../backend/__init__.py) chama essa inicialização.

**Armazenamento por aplicação:** `app.extensions['backend_td_engine']` e `app.extensions['backend_td_sessions']`. As rotas recuperam a factory com `get_td_session_factory()`.

| Consumidor concreto | Uso observado |
|---|---|
| [events/routes.py](../../backend/modules/events/routes.py) | Eventos, tipos, listas de presença e registros de presença. |
| [events/models.py](../../backend/modules/events/models.py) | Mapeia `DJ_EVENTS`, `DJ_EVENT_TYPES`, `DJ_EVENT_ATTENDANCE_LISTS` e `DJ_EVENT_ATTENDANCE_ENTRIES`. |
| [demands/routes.py](../../backend/modules/demands/routes.py) | Solicitações, edição, análise, anexos e histórico. |
| [demands/work_routes.py](../../backend/modules/demands/work_routes.py) | Quadro, cadastro, planejamento e ações do trabalho. |
| [demands/task_routes.py](../../backend/modules/demands/task_routes.py) | Criação, consulta, edição e exclusão de tarefas. |
| [demands/models.py](../../backend/modules/demands/models.py) | Modelos de solicitações/trabalho e relacionados; projeção de usuários compartilhados somente para leitura. |

**Exceção por processo:** o job [mon_mon_auto_modern_demands.py](../../app/services/jobs/mon_mon_auto_modern_demands.py) cria um pool próprio de uma conexão, sem iniciar Flask. Ele chama [scheduling.py](../../backend/modules/demands/scheduling.py), passando a factory explicitamente. O início automático depende de `DJ_DEMAND_WORK_AUTOSTART_ENABLED`, desabilitado por padrão.

**Frase para apresentar:** “O moderno compartilha um pool TD por aplicação web e abre uma sessão curta por operação. O processo de automação tem seu próprio pool.”

### 9.5. FTM: dados industriais e OEE

**Configuração:** `CNNX_FTM` recebe `DJ_FTM_ODBC_CONNECTION_STRING` em [constants.py](../../app/utils/constants.py).

**Construção:** `_FTM_ENGINE`, `get_engine('ftm')` e `engine_run_query(..., 'ftm', ...)` em [db_utils.py](../../app/utils/db_utils.py).

| Consumidor concreto | Uso observado |
|---|---|
| [reports/oee.py](../../app/routes/reports/oee.py) | Consulta sinais de produção, tempos e centros de trabalho; há referências a `OEEQWorkCell`, `JOST_OEEventDetail` e `CADASTRO_SINAIS_COLETA`. |
| [operation/production.py](../../app/routes/operation/production.py) | Consulta de centros de trabalho utilizada no fluxo de produção. |
| [operation/quality.py](../../app/routes/operation/quality.py) | Consultas industriais e cadastros usados pela qualidade. |
| [mon_mon_s_30_monitoringOverall.py](../../app/services/jobs/mon_mon_s_30_monitoringOverall.py) | Cria engine próprio a partir de `CNNX_FTM`, lê paradas e combina dados industriais para monitoramento. |
| [request/workcentersLogChange.py](../../app/routes/request/workcentersLogChange.py) | No ramo FTM da aprovação, atualiza o motivo em `OEEQEventHistory`. |

**Atenção para a explicação:** o uso observado inclui leitura e escrita; a fonte não serve apenas para relatórios.

### 9.6. Plex por SQL/ODBC e acesso remoto pelo SQL Server

**Configuração:** `CNNX_PLEX` recebe `DJ_PLEX_ODBC_CONNECTION_STRING` em [constants.py](../../app/utils/constants.py).

**Construção:** `_PLEX_ENGINE` e `get_engine('plex')` em [db_utils.py](../../app/utils/db_utils.py). Alguns jobs também criam engines próprios.

O código acessa tabelas SQL da integração, como `Mach_2_OEE_v2` e `Mach_2_Current_Status`. Certas consultas usam `OPENQUERY` com o linked server `PLEX_DSN_JOST`. Nesse caminho, a aplicação se conecta por ODBC ao SQL Server, e o SQL Server executa a consulta remota; a configuração desse linked server não é definida pelo engine Python e depende do ambiente.

| Consumidor concreto | Uso observado |
|---|---|
| [dynamic_constants.py](../../app/utils/dynamic_constants.py) | Cache de centros de trabalho e motivos/eventos, consultando `Part_v_Workcenter` e `Part_v_Workcenter_Event` via `OPENQUERY`; `getPlex()` entrega esses catálogos. |
| [reports/oee.py](../../app/routes/reports/oee.py) | Produção, sinais e eventos para OEE. |
| [planning_availability.py](../../app/utils/planning_availability.py) e [maintenance_availability.py](../../app/utils/maintenance_availability.py) | Disponibilidade, paradas e bases de planejamento/manutenção. |
| [operation/shift_handoffs_repository.py](../../app/routes/operation/shift_handoffs_repository.py) | Consulta de dados de passagem de turno. |
| [factoryRegister/default.py](../../app/routes/factoryRegister/default.py) | Consultas usadas em cadastros e informações de fábrica. |
| [request/workcentersLogChange.py](../../app/routes/request/workcentersLogChange.py) | Consulta paradas e pode atualizar `Mach_2_Current_Status` no fluxo de aprovação. |
| [mon_mon_s_30_monitoringOverall.py](../../app/services/jobs/mon_mon_s_30_monitoringOverall.py) | Combina dados Plex/FTM e grava consolidação no TD, em `TEMP_WORKCENTER_STATUS`. |

**Separação importante:** `getPlex('events')` entrega um catálogo industrial de motivos/eventos de trabalho; isso não é o cadastro moderno de Eventos de treinamento/presença em `DJ_EVENTS`.

### 9.7. Plex por API HTTP: caminho diferente do ODBC

**Configuração das credenciais:** `MES_MAIN_USER` e `MES_MAIN_PASSWORD` recebem `DJ_MES_USER` e `DJ_MES_PASSWORD` em [constants.py](../../app/utils/constants.py).

**Cliente/helper:** `POST_WITH_AUTH()` em [app/utils/data_utils.py](../../app/utils/data_utils.py) utiliza `requests.post()`.

**Uso concreto:** [request/workcentersLogChange.py](../../app/routes/request/workcentersLogChange.py) chama uma datasource da API Plex com `HTTPBasicAuth` durante a aprovação de alteração de parada. O endereço da operação está na própria rota.

Nesse fluxo, existem etapas envolvendo API externa, atualização do status SQL e confirmação do pedido no TD. Não se deve apresentar isso como uma única transação entre todos os sistemas.

**Frase para apresentar:** “O Plex aparece por dois caminhos: consulta e atualização na integração SQL, e chamada HTTP para uma operação no próprio Plex.”

### 9.8. Configuração Plex de teste

`CNNX_PLEX_TEST` recebe `DJ_PLEX_TEST_ODBC_CONNECTION_STRING` em [constants.py](../../app/utils/constants.py). A busca textual nos arquivos Python encontrou a definição, sem outro consumidor identificado. O seletor `get_engine()` não possui um ramo `plex_test`.

Isso permite afirmar que a variável é exigida quando esse módulo de constantes é carregado; não permite afirmar que haja um fluxo ativo utilizando a conexão de teste. Também não comprova isolamento do ambiente local.

### 9.9. Trace QR: rastreabilidade e plaquetas

**Configuração:** `CNNX_TRACE_QR` recebe `DJ_TRACE_QR_ODBC_CONNECTION_STRING` em [constants.py](../../app/utils/constants.py).

**Construção:** `_TRACE_QR_ENGINE` e `get_engine('trace_qr')` em [db_utils.py](../../app/utils/db_utils.py).

**Uso principal:** [factoryRegister/assembly.py](../../app/routes/factoryRegister/assembly.py), nas rotas de rastreabilidade QR e plaquetas.

Exemplos observados: consulta e manutenção de cadastros, exportação por tipo e busca que cruza `RASTREABILIDADE` com `CAD_RECEITA_INSP_QR`. O mesmo arquivo também usa TD para metadados/solicitações de plaquetas, incluindo `JDT_FAC_ASSEMBLY_PLATES`.

**Frase para apresentar:** “Rastreabilidade utiliza o Trace QR, mas parte do fluxo administrativo de plaquetas também passa pelo TD.”

### 9.10. Windows/IIS e LDAP

| Caminho | Onde está | Para que serve |
|---|---|---|
| Identidade Windows | [web.config](../../web.config) e [auth_routes.py](../../app/routes/auth_routes.py) | IIS encaminha o token; `/login` resolve a identidade e estabelece a sessão. |
| LDAP legado | [auth_routes.py](../../app/routes/auth_routes.py) e `create_external_user()` em [security_utils.py](../../app/utils/security_utils.py) | Consulta dados do diretório para identificar/cadastrar usuários. |
| Configuração LDAP moderna | `LdapDirectoryConfig` em [backend/config.py](../../backend/config.py) | Lê credenciais e opções de host, porta, SSL, base de busca e timeout. |
| Cliente LDAP moderno | `EmployeeDirectory.find_by_badge()` em [employee_directory.py](../../backend/shared/employee_directory.py) | Consulta funcionário por matrícula/crachá e devolve nome, departamento, empresa e estado da identificação. |
| Consumidor moderno | `register_attendance()` em [events/routes.py](../../backend/modules/events/routes.py) | Complementa a identificação da presença em um evento. |

O LDAP legado usa `DJ_LDAP_USER` e `DJ_LDAP_PASSWORD`, com destino/base definidos nas funções. O moderno reaproveita essas credenciais e admite opções `DJ_LDAP_HOST`, `DJ_LDAP_PORT`, `DJ_LDAP_USE_SSL`, `DJ_LDAP_SEARCH_BASE`, `DJ_LDAP_CONNECT_TIMEOUT` e `DJ_LDAP_RECEIVE_TIMEOUT`.

O adaptador moderno é composto em [backend/__init__.py](../../backend/__init__.py) e armazenado em `app.extensions['backend_employee_directory']`. Ele abre e encerra a conexão durante a consulta, sem consultar LDAP no construtor. Essa identificação complementar não é um novo login para o Vue.

### 9.11. E-mail SMTP: dois caminhos de envio

| Caminho | Configuração e cliente | Exemplos de uso |
|---|---|---|
| Flask-Mail | Servidor, porta e opções em [app/config.py](../../app/config.py); objeto `mail` e chamadas `mail.send()`. | Laboratório, demandas legadas, biblioteca, planejamento, desvios e plaquetas. |
| SMTP direto | `send_email_with_attachment()` em [email_utils.py](../../app/utils/email_utils.py), com `smtplib.SMTP()` e destino/porta definidos no helper. | Jobs H24 de laboratório, usuários, demandas, desvios e alteração de paradas. |

O Gerenciador legado possui notificações em [demandManagement/integration.py](../../app/routes/demandManagement/integration.py). Portanto, alterar apenas a configuração Flask-Mail não muda necessariamente todo envio feito por SMTP direto.

A existência desse recurso no portal não significa que todos os módulos o utilizem. Os fluxos modernos de Demandas descritos no documento específico não enviam notificações de e-mail nas decisões e ações de execução.

### 9.12. Identidade Microsoft, Graph e Teams

**Token:** [_TokenManager e get_azure_header()](../../app/utils/azure_utils.py) utilizam MSAL. A configuração vem de `DJ_MICROSOFT_TENANT_ID`, `DJ_MICROSOFT_CLIENT_ID`, `DJ_MICROSOFT_CLIENT_SECRET`, `DJ_MICROSOFT_USERNAME` e `DJ_MICROSOFT_PASSWORD`.

**Chamadas de integração:** [teams_utils.py](../../app/utils/teams_utils.py) utiliza o cabeçalho para criar/obter chat e enviar mensagens pelo Microsoft Graph. `send_system_teams_alert()` compõe alertas; `send_teams_message()` efetua as chamadas.

**Consumidores concretos:**

- [app/errors.py](../../app/errors.py): alerta de falhas no tratamento global de erros.
- Schedulers em `app/services/run_*_scheduler.py`: alerta de falha do serviço ou de job.
- [mon_mon_m_5_monitoringAlerts.py](../../app/services/jobs/mon_mon_m_5_monitoringAlerts.py): mensagens de monitoramento.
- [jdt/userManager.py](../../app/routes/jdt/userManager.py): consulta do usuário Graph nas rotas `/usuarios/alertas`.

Isso autentica chamadas da integração Microsoft; não substitui a autenticação Windows do portal. O módulo de token inicia uma thread durante o import, motivo para não utilizá-lo como demonstração dinâmica.

### 9.13. SAP SOAP: relatório de manutenção

**Local:** [app/routes/reports/maintenance.py](../../app/routes/reports/maintenance.py).

**Construção:** `_CREATE_CONNECTION()` lê `DJ_SAP_USER` e `DJ_SAP_PASSWORD`, cria `requests.Session` com `HTTPBasicAuth`, monta `zeep.Transport` e cria o cliente do WSDL. O endereço WSDL está nessa função.

**Uso:** `_GET_WEB_SERVICE_DATA()` chama `BbpRfcReadTable`; `_TRANSFORM_WEB_SERVICE_DATA()` organiza consultas e transforma os resultados em tabelas usadas pelo relatório. Há consulta de notificações e ordens de manutenção, incluindo referência a `VIQMEL`.

O mesmo arquivo também consulta TD e utiliza auxiliares de disponibilidade/catálogos Plex. O relatório combina fontes; não depende apenas do SAP.

### 9.14. Oracle: implementação em módulo desativado

**Local:** [app/routes/reports/productiveHours.py](../../app/routes/reports/productiveHours.py), em `_OPERS_PERIODIC()`.

**Construção:** `oracledb.makedsn()` define o destino e `oracledb.connect()` usa `DJ_ORACLE_USER` e `DJ_ORACLE_PASSWORD`.

**Uso previsto pelo código:** consultar dados de frequência/ponto, cruzando matrículas e períodos com as horas dos operadores.

**Estado do registro:** a importação e o registro de `productiveHours` estão comentados em [main.py](../../main.py). Portanto, essa referência documenta uma integração existente no código de um módulo desativado; não confirma acesso Oracle ativo na aplicação web atual.

### 9.15. Power BI, FTWeb e SSRS: navegador acessando outro sistema

| Recurso | Onde está | Como é usado |
|---|---|---|
| Power BI | [reports/powerbi.py](../../app/routes/reports/powerbi.py) e templates em `app/templates/reports.powerbi/`. | Rotas renderizam páginas com painéis incorporados, como qualidade, trilhos e sistemas indisponíveis. |
| FTWeb incorporado | [factoryRegister/external.py](../../app/routes/factoryRegister/external.py) e templates `factoryRegister.external/`, como [cadastro_paradas.html](../../app/templates/factoryRegister.external/cadastro_paradas.html). | Iframes de cadastros externos, incluindo paradas, agenda, tablets e qualidade. |
| FTWeb e SSRS por links | [app/templates/home.html](../../app/templates/home.html). | Navegação para consultas de eficiência, produção, montagem, ordens e outros recursos. |

Nesses exemplos, o navegador carrega ou abre o sistema externo. Isso é diferente de o backend Python abrir uma conexão SQL para executar a consulta. Os endereços ficam nos templates, mas as credenciais de banco do serviço externo não são demonstradas por esses links.

### 9.16. DNS e ICMP para monitoramento

**Local:** [app/utils/ping_utils.py](../../app/utils/ping_utils.py).

**Operações:** resolução de hostname com `socket.gethostbyname()` e execução do comando de ping, com funções como `ping_lote()`, `ping_info_cached()` e `verificar_config_lote()`.

**Consumidor identificado:** [app/routes/jdt/monitoring.py](../../app/routes/jdt/monitoring.py).

**Uso:** disponibilidade, latência e conferência de configuração de equipamentos. Isso é tráfego de rede para monitoramento, sem equivaler a conexão de banco ou autenticação de usuário.

## 10. Automações e conexões fora da aplicação web

| Agendador | Frequência prevista no código | Exemplos de trabalho e dependências |
|---|---|---|
| [run_s_30_scheduler.py](../../app/services/run_s_30_scheduler.py) | 30 segundos. | Consolidação de monitoramento; job cruza FTM/Plex e grava TD. |
| [run_m_5_scheduler.py](../../app/services/run_m_5_scheduler.py) | 5 minutos. | Alertas e apontamentos; há consumidores TD e Teams. |
| [run_h_24_scheduler.py](../../app/services/run_h_24_scheduler.py) | Programação às 6h, com tarefas diárias ou de segunda a sexta. | Verificações de usuários, demandas, laboratório, desvios e alterações de paradas; TD e e-mails. |
| [run_auto_scheduler.py](../../app/services/run_auto_scheduler.py) | 1 minuto. | Agendamentos de laboratório, início/recorrência de demandas legadas e adaptador de início moderno condicionado à configuração. |

São processos separados. Reiniciar o site não reinicia os serviços; cada processo precisa ter sua configuração, permissões de arquivos e dependências. A configuração do IIS não é automaticamente herdada pelos serviços Windows.

O total de conexões depende também do número de processos e dos pools próprios do legado e dos jobs. A existência de um pool compartilhado moderno não significa que o portal inteiro use apenas um pool.

## 11. Perguntas e respostas para a apresentação

| Pergunta | Resposta curta |
|---|---|
| Onde o sistema começa? | Em `main.py`; a factory em `app/config.py` monta a aplicação e inicializa o backend moderno. |
| São dois sistemas independentes? | É uma aplicação Flask com módulos legados e modernos. |
| O Vue acessa o banco? | No fluxo moderno, ele chama a API; o backend autoriza e acessa o banco. |
| Onde encontro uma conexão? | Primeiro a variável/configuração; depois o engine ou cliente; por fim a rota, auxiliar ou job consumidor. |
| Tudo passa por `db_utils.py`? | Não. Flask-SQLAlchemy, o backend moderno e alguns jobs possuem mecanismos próprios. |
| Plex é uma única conexão? | Há acesso SQL/ODBC, consultas remotas por linked server e chamada HTTP em fluxo específico. |
| Todas as integrações estão ativas? | Não é possível concluir isso apenas pelo repositório; Oracle aparece em módulo desativado, por exemplo. |
| Onde ficam as regras modernas? | Nas operações do módulo, principalmente rotas e auxiliares; schemas validam contratos e modelos representam tabelas. |
| Toda feature precisa de Service e Repository? | Essas camadas não são obrigatórias no moderno. O legado organizado em camadas preserva seu padrão. |
| Como preservar segurança? | Reutilizar identidade e CSRF, autorizar ações e registros no servidor e controlar os contratos públicos. |
| Uma transação desfaz tudo? | Ela cobre as alterações na mesma transação SQL; não desfaz automaticamente arquivos ou serviços externos. |
| Fazer push publica o sistema? | Enviar código ao Git e implantar no IIS são procedimentos distintos; o build também precisa acompanhar a entrega. |
| O gerenciador antigo foi substituído? | Existe gerenciador moderno para Transformação Digital; o antigo continua separado, sem migração automática. |

## 12. Documentação de referência e limites

- [Colinha do projeto](../../handbook/docs/colinha-do-projeto.md): introdução e mapa de arquivos; alguns trechos ainda descrevem o escopo anterior de Demandas.
- [Arquitetura e modernização](../../handbook/docs/arquitetura-modernizada.md): organização e critérios de desenvolvimento/migração; confrontar o escopo atual com o documento específico.
- [Base compartilhada](../../handbook/features/base-compartilhada.md): identidade, banco, contratos HTTP e recursos comuns.
- [Demandas](../../handbook/features/demandas.md): solicitações, gerenciador, tarefas, anexos e início automático modernos.
- [Eventos](../../handbook/features/eventos.md): cadastro, tipos, presenças e PDF.
- [Frontend](../../frontend/README.md): organização Vue e componentes.
- [Servidor e publicação](../../handbook/docs/servidor-e-publicacao.md): configuração, build, IIS, dependências e retorno.
- [AGENTS.md](../../AGENTS.md): restrições operacionais para agentes.

A análise foi feita pela leitura de arquivos e busca de referências. Não houve importação de módulos, conexão, consulta SQL, envio de mensagens, execução de jobs, build ou abertura do portal. Servidores efetivos, schema, permissões, linked server, serviços ativos e comportamento precisam ser confirmados em ambiente autorizado.

**O sistema não foi executado; a validação foi somente estática.**
