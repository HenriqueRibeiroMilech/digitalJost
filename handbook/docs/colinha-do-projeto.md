# Digital JOST — colinha para entender e apresentar o projeto

Este guia é uma introdução ao código: explica a arquitetura, as pastas, os arquivos principais e um roteiro de apresentação. Para detalhes de implementação, consulte a [arquitetura](arquitetura-modernizada.md) e os [guias das funcionalidades](../README.md).

O conteúdo descreve o código do repositório. A presença de uma funcionalidade no código não confirma que ela esteja publicada ou funcionando no servidor da empresa.

## 1. O projeto em 30 segundos

> “O Digital JOST é um portal interno que centraliza demandas, laboratório, desvios de processo, indicadores, monitoramento industrial e outras ferramentas da empresa. O servidor usa Python com Flask. Existem telas antigas em HTML/Jinja e telas novas em Vue. A modernização acontece gradualmente, separando melhor as regras, o acesso aos dados e a interface.”

Guarde três ideias:

- O portal reúne ferramentas de várias áreas da empresa.
- As telas antigas e novas convivem na mesma aplicação Flask.
- Além das telas, existem tarefas automáticas executadas por serviços Windows.

## 2. Tradução dos nomes técnicos

| Nome | Explicação simples |
|---|---|
| Frontend | A interface que a pessoa vê e utiliza no navegador. |
| Backend | O código no servidor que verifica acesso, aplica regras e acessa os dados. |
| Banco de dados | Onde ficam informações como usuários, solicitações e eventos. |
| Rota | Um endereço atendido pelo sistema, como `/app/eventos`. |
| Blueprint | Um grupo de rotas de uma funcionalidade no Flask. |
| API | O meio pelo qual a interface pede ou envia dados ao servidor. |
| JSON | Um formato usado para transportar dados, com campos e valores. |
| Regra de negócio | Uma condição do funcionamento, como impedir um evento de terminar antes de começar. |
| Legado | A parte mais antiga do sistema, que continua sendo utilizada. |
| Monólito | Uma aplicação que reúne vários módulos no mesmo sistema. |
| Componente | Uma parte da interface, como um formulário ou cartão, que pode ser reutilizada. |
| Transação | Um conjunto de alterações no banco que deve ser confirmado ou desfeito em conjunto. |
| Build | A preparação do código do frontend em arquivos que o navegador consegue carregar. |

## 3. Arquitetura: como tudo se conecta

```text
Usuário no navegador
        ↓
IIS — hospedagem no Windows e identidade corporativa
        ↓
Aplicação Flask — main.py + app/config.py
        ├── Parte antiga: rotas → HTML/Jinja + JavaScript
        └── Parte moderna: APIs ↔ interface Vue
                         ↓
                 Bancos e integrações

Separadamente: serviços Windows → tarefas automáticas
```

O projeto é um **monólito em modernização gradual**. A parte moderna ainda reaproveita a sessão e os perfis de acesso do legado.

As três pastas mais importantes para memorizar são:

- **`app/`:** parte antiga e recursos compartilhados que continuam necessários.
- **`backend/`:** organização moderna do servidor e suas APIs.
- **`frontend/`:** interface moderna em Vue.

### Tecnologias e seus papéis

| Tecnologia | Para que serve aqui |
|---|---|
| Python + Flask/APIFlask | Atender requisições e organizar o backend e as APIs. |
| HTML + Jinja | Montar páginas antigas no servidor com os dados recebidos. |
| CSS + JavaScript | Definir aparência e interação das telas antigas. |
| Vue 3 + TypeScript | Construir as telas modernas com componentes e estruturas de dados definidas. |
| Vite | Preparar os arquivos do frontend para publicação. |
| Tailwind + PrimeVue/Volt | Fornecer estilos e componentes visuais para a interface moderna. |
| TanStack Query | Gerenciar consultas, cache e atualização de dados no Vue. |
| SQLAlchemy + pyodbc | Ajudar no acesso aos bancos; boa parte das consultas usa SQL escrito diretamente. |
| pandas | Tratar dados em tabelas e preparar informações para telas e exportações. |
| Flask-Login + Flask-Principal | Manter a sessão e verificar perfis de acesso. |
| APScheduler + serviços Windows | Programar e executar tarefas automáticas. |

## 4. Mapa das pastas

Os caminhos abaixo partem da raiz do repositório.

| Pasta | O que faz |
|---|---|
| `app/routes/` | Atende as URLs das funcionalidades antigas. Alguns arquivos também concentram regras e SQL. |
| `app/templates/` | Guarda páginas HTML/Jinja, layouts e modelos de e-mail. Também contém JavaScript antigo incluído pelo Jinja. |
| `app/static/` | Guarda arquivos servidos ao navegador: estilos, scripts, imagens e bibliotecas. |
| `app/static/CSS/` | Estilos das telas antigas. |
| `app/static/js/` | JavaScript das telas que usam arquivos estáticos separados. |
| `app/static/uploads/` | Arquivos operacionais utilizados pelas funcionalidades; são dados reais. |
| `app/models/` | Representação do usuário no banco pelo SQLAlchemy. |
| `app/utils/` | Funções compartilhadas de banco, permissões, arquivos, dados e integrações. |
| `app/services/` | Agendadores Windows e recursos de automação, incluindo recorrência de demandas. |
| `app/services/jobs/` | Tarefas chamadas pelos agendadores. |
| `backend/modules/` | Funcionalidades modernas: Eventos e Demandas. |
| `backend/shared/` | Recursos modernos compartilhados: banco, HTTP/CSRF, identidade do portal, carregamento do Vue e consulta de funcionários. |
| `backend/web/templates/` | HTML base que carrega a aplicação Vue. |
| `backend/web/static/app/` | Destino dos arquivos gerados pelo build do Vue; o build é ignorado pelo Git. |
| `frontend/src/features/` | Páginas e componentes de cada funcionalidade moderna. |
| `frontend/src/shared/` | Componentes, estilos e comunicação HTTP compartilhados. |
| `frontend/src/router/` | Define qual página Vue corresponde a cada endereço. |
| `frontend/src/app/` | Layout geral e página de endereço inexistente da interface moderna. |
| `frontend/src/volt/` | Componentes visuais locais, como botões, tabelas e diálogos. |
| `frontend/src/assets/` | Recursos visuais e estilos da interface moderna. |
| `database/` | Scripts SQL, alterações de banco e orientações de diagnóstico ou reversão. |
| `scripts/` | Utilitários de manutenção, como tratamento de arquivos do laboratório. |
| `logs/` | Registros operacionais. |
| `handbook/docs/` | Guias gerais do projeto. |
| `handbook/features/` | Documentação das funcionalidades e dos recursos compartilhados. |
| `handbook/historico/` | Estudos, planos e documentos anteriores. |
| `.git/` | Histórico e controle de versões do repositório. |

## 5. Arquivos principais para mostrar

| Arquivo | Como explicar na apresentação |
|---|---|
| [main.py](../../main.py) | “É o ponto de entrada. Chama a criação da aplicação e registra os módulos antigos.” |
| [app/config.py](../../app/config.py) | “Monta a aplicação: configura banco, login, sessão, e-mail, permissões e inicializa a parte moderna.” |
| [app/routes/main_default_routes.py](../../app/routes/main_default_routes.py) | “Contém a rota inicial e rotas gerais do portal.” |
| [app/routes/auth_routes.py](../../app/routes/auth_routes.py) | “Cuida do fluxo de login usando a identidade corporativa.” |
| [app/models/user.py](../../app/models/user.py) | “Representa os dados do usuário no banco.” |
| [app/utils/permissions.py](../../app/utils/permissions.py) | “Define os perfis de acesso utilizados pelo sistema.” |
| [app/utils/db_utils.py](../../app/utils/db_utils.py) | “Reúne engines e funções de banco compartilhadas pelo legado.” |
| [app/utils/constants.py](../../app/utils/constants.py) | “Reúne constantes e referências de configuração do legado.” |
| [app/errors.py](../../app/errors.py) | “Trata erros, como acesso negado e página inexistente.” |
| [backend/__init__.py](../../backend/__init__.py) | “Prepara os recursos compartilhados e inicializa a parte moderna.” |
| [backend/modules/__init__.py](../../backend/modules/__init__.py) | “Registra os módulos modernos na aplicação.” |
| [backend/config.py](../../backend/config.py) | “Define configurações modernas de banco e diretório de funcionários.” |
| [frontend/src/main.ts](../../frontend/src/main.ts) | “Inicializa o Vue e suas ferramentas.” |
| [frontend/src/router/index.ts](../../frontend/src/router/index.ts) | “Liga os endereços às páginas Vue.” |
| [frontend/src/shared/api/client.ts](../../frontend/src/shared/api/client.ts) | “Centraliza chamadas HTTP, tratamento de erros e envio do token de segurança.” |
| [frontend/vite.config.ts](../../frontend/vite.config.ts) | “Configura a preparação do frontend para publicação.” |
| [requirements.txt](../../requirements.txt) | “Lista as dependências Python.” |
| [frontend/package.json](../../frontend/package.json) | “Lista dependências e tarefas do frontend.” |
| [web.config](../../web.config) | “Configura a hospedagem no IIS.” |
| [README.md](../../README.md) | “Apresenta o projeto e aponta para o manual.” |
| [AGENTS.md](../../AGENTS.md) | “Define as regras operacionais para agentes que trabalham no repositório.” |

O arquivo `.env` guarda configurações privadas do ambiente e não deve ser exibido na apresentação. O `.env.example` apresenta o modelo de configuração.

## 6. Como as responsabilidades são separadas

### No backend moderno

Dentro de uma funcionalidade em `backend/modules/`, os nomes ajudam a encontrar a responsabilidade:

| Arquivo | Pergunta que ele responde |
|---|---|
| `routes.py` | O que a interface pediu, quais regras aplicar e como consultar/gravar com ORM? |
| `schemas.py` | Quais campos, formatos e respostas são aceitos? |
| `models.py` | Quais tabelas, campos e relacionamentos o ORM representa? |
| `domain.py`, quando existe | Quais definições, opções e erros pertencem à funcionalidade? |
| `__init__.py` | O que esse pacote disponibiliza ao restante do projeto? |

Existem arquivos específicos: em Demandas, `storage.py` cuida dos anexos; em Eventos, `attendance_pdf.py` gera o documento de presença.

As rotas mostram a sequência das operações, com funções auxiliares quando ajudam a leitura. Service e Repository não são camadas obrigatórias no backend moderno. A sessão ORM é criada por operação; gravações relacionadas usam a mesma transação, sem commits individuais nos modelos ou auxiliares.

**Frase para decorar:** “O schema define os dados, o model representa a tabela e a rota coordena a operação com ORM.”

### No frontend moderno

| Arquivo ou pasta | Responsabilidade |
|---|---|
| `pages/` | Organizar a página principal da funcionalidade. |
| `components/` | Mostrar partes da tela: formulário, cartão, filtro ou detalhe. |
| `api.ts` | Fazer as chamadas da funcionalidade ao backend. |
| `types.ts` | Definir a estrutura dos dados no TypeScript. |
| Arquivos auxiliares, como `presentation.ts` | Concentrar transformações e textos de apresentação da funcionalidade. |

### No legado

O caminho costuma ser **rota Python → template HTML/Jinja → JavaScript da tela**. O Jinja monta o HTML no servidor antes de enviá-lo ao navegador; depois, o JavaScript pode consultar dados e atualizar partes da tela.

Alguns módulos antigos concentram regras e SQL na rota. Outros, como `demandManagement/` e `demandRequests/`, já separam rotas, serviços e repositórios, mantendo a interface Jinja.

## 7. Exemplo completo: enviar uma solicitação

```text
Usuário preenche o formulário Vue
        ↓
api.ts envia os dados e anexos
        ↓
POST /api/v1/demands
        ↓
Backend confere sessão, segurança e campos
        ↓
Rota verifica permissões e aplica as regras
        ↓
Sessão ORM grava no banco + armazenamento salva anexos
        ↓
API devolve o resultado
        ↓
Interface atualiza “Minhas solicitações”
```

Arquivos para acompanhar:

1. [RequestsPage.vue](../../frontend/src/features/demands/pages/RequestsPage.vue): organiza a página.
2. [RequestForm.vue](../../frontend/src/features/demands/components/RequestForm.vue): apresenta o formulário.
3. [api.ts](../../frontend/src/features/demands/api.ts): envia a requisição.
4. [routes.py](../../backend/modules/demands/routes.py) e [schemas.py](../../backend/modules/demands/schemas.py): recebem e validam a entrada.
5. [models.py](../../backend/modules/demands/models.py): representa as tabelas; as regras e transações ficam nas rotas.
6. [storage.py](../../backend/modules/demands/storage.py): trata o armazenamento dos anexos.

Exemplos de regras dessa funcionalidade: somente o solicitante pode editar, enquanto a solicitação está em análise e sem classificação; repetições do mesmo envio são reconhecidas para evitar duplicação.

**Limite atual:** as solicitações modernas atendem Transformação Digital. O gerenciador antigo continua separado, sem sincronização automática com elas. Consulte [Demandas](../features/demandas.md) para o escopo completo.

## 8. Principais funcionalidades

| Funcionalidade | O que faz | Onde começar a leitura |
|---|---|---|
| Demandas antigas por área | Cadastro, tarefas, acompanhamento e painéis. | `app/routes/demands/` |
| Gerenciador antigo de Demandas | Gestão do trabalho, solicitações, tarefas, status e recorrência. | `app/routes/demandManagement/` |
| Solicitações antigas | Envio e acompanhamento de pedidos. | `app/routes/demandRequests/` |
| Solicitações modernas | Cadastro de demandas ou erros, acompanhamento, edição e anexos. | `backend/modules/demands/` e `frontend/src/features/demands/` |
| Eventos | Eventos, tipos, listas de presença, leitura de crachá e PDF. | `backend/modules/events/` e `frontend/src/features/events/` |
| Laboratório | Solicitações, análises, arquivos, equipamentos e agendamentos. | `app/routes/request/laboratory.py` |
| Desvios de processo | Abertura, aprovações, ações e acompanhamento. | `app/routes/request/processDeviation.py` |
| Alterações de paradas | Solicitação e aprovação de mudanças em registros. | `app/routes/request/workcentersLogChange.py` |
| Operação | Indicadores, apontamentos e planejamento das áreas. | `app/routes/operation/` |
| Monitoramento | Informações de máquinas, paradas e indicadores industriais. | `app/routes/jdt/monitoring.py` |
| Relatórios | Consultas, exportações e acesso a painéis. | `app/routes/reports/` |
| Cadastros de fábrica | Dados de apoio e ferramentas relacionadas à fábrica. | `app/routes/factoryRegister/` |
| Usuários | Gestão de usuários e acessos. | `app/routes/jdt/userManager.py` |

Para saber se um módulo está registrado, confira `main.py` e `backend/modules/__init__.py`. No registro atual, `computers`, `temp`, `productiveHours` e `setup` estão desativados. Cópias com `Copy`, `BKP`, datas ou `NOT_ACTIVATED` não devem ser usadas como referência do código ativo sem conferir as referências.

## 9. Login, dados e integrações

**Login:** o IIS fornece a identidade Windows. O fluxo de autenticação consulta o cadastro e usa o LDAP quando necessário. O Flask-Login mantém a sessão, e os perfis determinam o acesso. A parte moderna reutiliza essa identidade pela ponte em `backend/shared/`.

> “Autenticação identifica quem é a pessoa. Autorização define o que ela pode fazer.”

**Dados:** no legado aparecem conexões chamadas `jdt`, `ftm`, `plex` e `trace_qr`. A conexão `jdt` corresponde ao TD utilizado pelo portal; a parte moderna também utiliza o TD, com seu próprio mecanismo de conexão. Compartilhar o banco não significa compartilhar a mesma transação.

**Integrações:** conforme a funcionalidade, o código utiliza LDAP, e-mail SMTP, Microsoft Graph/Teams, SAP e ferramentas como Power BI, FTWeb e SSRS. Alguns itens do menu encaminham para outros sistemas.

**Publicação:** o Vue é preparado em arquivos dentro de `backend/web/static/app/`, que a aplicação disponibiliza ao navegador. Atualizar o código no Git não gera esse build automaticamente. Os scripts SQL em `database/` dependem de revisão e aplicação explícita. Consulte o [guia de servidor e publicação](servidor-e-publicacao.md).

## 10. Tarefas automáticas

| Agendador em `app/services/` | Programação no código | Trabalho principal |
|---|---|---|
| `run_s_30_scheduler.py` | A cada 30 segundos. | Consolidação do monitoramento. |
| `run_m_5_scheduler.py` | A cada 5 minutos. | Alertas e monitoramento de apontamentos/relógio-ponto. |
| `run_h_24_scheduler.py` | Às 6h; algumas tarefas diariamente, outras de segunda a sexta. | Verificações de usuários, demandas, laboratório, desvios e solicitações de alteração de paradas. |
| `run_auto_scheduler.py` | A cada minuto. | Agendamentos do laboratório e início/recorrência de demandas. |

Esses serviços são processos separados do site. Confirmar quais estão instalados e ativos exige verificar o ambiente autorizado.

**Atenção aos nomes:** `app/services/` contém automações; no legado, `services.py` de uma funcionalidade contém regras e operações. No backend moderno, as rotas coordenam as operações e usam ORM, sem camada obrigatória de Service.

## 11. Roteiro para apresentar em 5 a 10 minutos

1. **Objetivo:** explique o portal usando o texto de 30 segundos.
2. **Estrutura:** mostre `app/`, `backend/` e `frontend/`.
3. **Entrada:** abra `main.py` e explique que `create_app()` monta a aplicação.
4. **Uma funcionalidade:** escolha Demandas ou Eventos e siga uma ação da tela até o banco.
5. **Responsabilidades:** explique rota, schema, serviço, repositório e componentes Vue.
6. **Recursos comuns:** cite login, permissões, bancos e tarefas automáticas.
7. **Evolução:** explique a modernização gradual e a reutilização dos recursos compartilhados.

Para uma apresentação curta, priorize o objetivo, as três pastas principais e um fluxo completo.

## 12. Perguntas comuns e respostas rápidas

**Onde começa o sistema?** Em `main.py`, que chama `create_app()` de `app/config.py` e registra os módulos antigos. A criação da aplicação também inicializa a parte moderna.

**Por que existem `app/` e `backend/`?** Porque o projeto está sendo modernizado aos poucos. O legado continua necessário, e os módulos modernos recebem uma organização própria.

**São dois sistemas independentes?** Hoje há uma aplicação Flask compartilhada. A parte moderna ainda depende da sessão e de recursos do legado.

**Onde ficam as regras?** Nos módulos organizados em camadas, principalmente em `services.py` e, quando existe, `domain.py`. No legado, também podem estar nas rotas e nos utilitários.

**Tudo usa modelos SQLAlchemy?** Não. Existe o modelo de usuário, mas boa parte do acesso usa SQL textual com SQLAlchemy, pyodbc ou pandas.

**Como encontro o código de uma tela?** Comece pela URL, encontre a rota e confirme o registro do blueprint. Depois siga o template e JavaScript, ou a página Vue e suas chamadas de API.

**Qual é a arquitetura?** “Um monólito Flask em modernização gradual, com telas Jinja no legado e APIs com frontend Vue na parte moderna.”

**O que preciso decorar?** “O frontend apresenta; o backend valida o acesso e as regras; o repositório acessa os dados; os jobs fazem tarefas automáticas.”

## 13. Onde aprofundar

- [Arquitetura e modernização](arquitetura-modernizada.md): organização e critérios de camadas.
- [Base compartilhada](../features/base-compartilhada.md): identidade, permissões, segurança e banco.
- [Demandas](../features/demandas.md): solicitações modernas e seus limites.
- [Eventos](../features/eventos.md): eventos, presenças e exportação.
- [Manual do projeto](../README.md): índice dos demais assuntos.

Este guia foi conferido por leitura de código e documentação. Publicação, conectividade, permissões reais, dados e funcionamento das telas dependem de validação em ambiente autorizado.

**O sistema não foi executado; a validação foi somente estática.**
