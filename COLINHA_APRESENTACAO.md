# Digital JOST — colinha para apresentar o código

> Guia baseado na leitura do repositório em 16/10/2026. Explica o código atual; a disponibilidade das telas e integrações depende do ambiente da empresa.

## 1. Como explicar o projeto em 30 segundos

“O Digital JOST é um portal interno que reúne ferramentas para as áreas da empresa. Ele atende demandas, laboratório, desvios de processo, indicadores, monitoramento industrial, cadastros e gestão de usuários. O servidor usa Python com Flask e acessa bancos e sistemas corporativos. A interface tem telas antigas em HTML/Jinja e uma parte nova em Vue. A modernização acontece aos poucos, dentro da mesma aplicação.”

## 2. Tecnologias, sem complicar

| Tecnologia | Para que serve aqui |
|---|---|
| Python | Linguagem do servidor: processa requisições, regras, dados e integrações. |
| Flask / APIFlask | Organizam a aplicação web, as URLs e as respostas. APIFlask acrescenta recursos de API e validação. |
| Jinja + HTML | Montam as páginas antigas no servidor, preenchendo o HTML com dados. |
| CSS + JavaScript | Cuidam da aparência e das interações das telas antigas. Há uso de Bootstrap e bibliotecas de gráficos. |
| Vue 3 + TypeScript | Constroem as telas novas com componentes e dados recebidos da API. |
| Vite | Prepara o código Vue para publicação, gerando os arquivos que o navegador carrega. |
| Tailwind + PrimeVue/Volt | Estilos e componentes da interface nova, como botões, formulários e diálogos. |
| TanStack Query | Gerencia consultas, cache e atualização de dados na interface nova. |
| SQLAlchemy + pyodbc + pandas | Fazem a ponte com os bancos e ajudam a consultar e tratar dados. |
| Flask-Login / Flask-Principal | Mantêm a sessão do usuário e verificam seus perfis de acesso. |
| IIS + Windows | Ambiente de hospedagem e identificação corporativa do usuário. |
| APScheduler + serviços Windows | Executam tarefas automáticas nos horários programados. |

**Palavras que podem aparecer:** rota é uma URL tratada pelo servidor; blueprint é um grupo de rotas; API é a interface usada para trocar dados; JSON é um formato dessa troca; backend é o código do servidor; frontend é a interface do navegador.

## 3. Visão geral de como tudo se conecta

```text
Usuário no navegador
        ↓
IIS / identificação do Windows
        ↓
Aplicação Flask — main.py + app/config.py
        ├── Telas antigas: app/routes/ → app/templates/
        │                                  + CSS e JavaScript
        └── Telas novas: backend/ → APIs → interface Vue
                             ↓
                  Bancos e integrações corporativas

Em paralelo: serviços Windows → jobs automáticos
```

**Ponto principal:** `app/`, `backend/` e `frontend/` convivem. Hoje há uma aplicação Flask compartilhada; a parte nova ainda reaproveita o login e a sessão da antiga.

## 4. O que tem em cada pasta principal

| Pasta | O que guardar na cabeça |
|---|---|
| `app/` | Parte antiga do sistema e recursos compartilhados que continuam necessários. |
| `app/routes/` | Rotas organizadas por assunto: demandas, operação, laboratório, relatórios etc. Muitos arquivos antigos também concentram SQL e regras. |
| `app/templates/` | Páginas HTML/Jinja, layouts, e-mails e vários arquivos JavaScript incluídos pelo Jinja. |
| `app/static/` | Arquivos servidos ao navegador: CSS, JavaScript, imagens, vídeos e bibliotecas. |
| `app/static/CSS/` | Estilos das telas antigas e dos módulos Jinja mais recentes. |
| `app/static/js/` | Scripts de planejamento, demandas, solicitações, apontamentos por turno e outras telas. |
| `app/static/uploads/` | Arquivos operacionais enviados ou usados pelas funcionalidades. Contém dados reais. |
| `app/models/` | Modelo de usuário do SQLAlchemy, ligado à tabela `JDT_USER_DETAILS`. |
| `app/utils/` | Funções compartilhadas de banco, permissões, dados, paradas, arquivos e integrações. |
| `app/services/` | Agendadores executados como serviços Windows e lógica de recorrência de demandas. |
| `app/services/jobs/` | Tarefas chamadas pelos agendadores: monitoramento, alertas, prazos e atualizações. |
| `backend/` | Parte nova do servidor, separando infraestrutura, regras e acesso a dados. |
| `backend/modules/` | Funcionalidades modernas. O módulo implementado atualmente é Eventos. |
| `backend/platform/` | Base comum: banco TD, configuração de ambiente, identidade, HTTP, CSRF e carregamento do Vue. |
| `backend/compatibility/` | Ponte que permite à parte nova usar a sessão e os perfis antigos. |
| `backend/integrations/` | Integrações modernas, como consulta de funcionários no LDAP para presenças. |
| `backend/templates/` | HTML base que carrega a aplicação Vue. |
| `backend/static/app/` | Destino dos arquivos gerados pelo build do Vue. O build é ignorado pelo Git. |
| `frontend/` | Projeto da interface Vue: código, dependências e configuração de ferramentas. |
| `frontend/src/features/` | Telas e componentes específicos de cada funcionalidade; hoje, Eventos. |
| `frontend/src/shared/` | Componentes, estilos, paginação e cliente HTTP reutilizáveis. |
| `frontend/src/app/` e `frontend/src/router/` | Layout geral, página de rota inexistente e navegação da interface nova. |
| `frontend/src/volt/` | Componentes visuais locais: botão, tabela, diálogo, calendário e outros controles. |
| `database/` | Scripts SQL de migração, procedures, diagnóstico e orientações de reversão. |
| `scripts/` | Utilitários de manutenção, como tratamento de arquivos do laboratório. |
| `logs/` | Registros operacionais. Os serviços também têm configuração própria de logs. |
| `handbook/docs/` | Guias oficiais de arquitetura, padrão visual, ambiente/servidor e publicação no Azure. |
| `handbook/features/` | Documentação atual de Eventos, Demandas, base compartilhada e disponibilidade operacional. |
| `handbook/historico/` | Planos, estudos e versões anteriores dos guias, sem substituir o manual atual. |

Pastas de controle como `.git/` guardam o histórico do repositório. Não fazem parte das funcionalidades do portal.

## 5. Arquivos principais para mostrar

| Arquivo | Como explicar na apresentação |
|---|---|
| [`main.py`](main.py) | “É a entrada do portal. Chama a criação da aplicação e registra os módulos antigos.” |
| [`app/config.py`](app/config.py) | “Monta a aplicação: banco, e-mail, login, sessão, permissões, logs, erros e inicialização da parte nova.” |
| [`app/routes/main_default_routes.py`](app/routes/main_default_routes.py) | “Tem a rota inicial `/` e algumas rotas gerais.” |
| [`app/routes/auth_routes.py`](app/routes/auth_routes.py) | “Trata o login com a identidade recebida do IIS e consulta os dados corporativos quando necessário.” |
| [`app/models/user.py`](app/models/user.py) | “Representa o usuário no banco: identificação, área, perfis e outros dados.” |
| [`app/utils/permissions.py`](app/utils/permissions.py) | “Define os perfis usados para permitir ou negar acesso às funcionalidades.” |
| [`app/utils/db_utils.py`](app/utils/db_utils.py) | “Centraliza engines e consultas compartilhadas do legado.” |
| [`app/utils/constants.py`](app/utils/constants.py) | “Reúne constantes e referências de configuração usadas pelo legado.” |
| [`app/errors.py`](app/errors.py) | “Trata erros como acesso negado, página inexistente e falha do servidor, distinguindo páginas e APIs.” |
| [`app/templates/home.html`](app/templates/home.html) | “É a base visual e de navegação de várias telas antigas.” |
| [`backend/bootstrap.py`](backend/bootstrap.py) | “Monta as dependências da parte nova e registra seus módulos.” |
| [`backend/config.py`](backend/config.py) | “Define a configuração moderna do TD, do pool de conexões e da consulta LDAP.” |
| [`backend/platform/environment.py`](backend/platform/environment.py) | “Lê a configuração privada do ambiente e do arquivo opcional de configuração.” |
| [`frontend/src/main.ts`](frontend/src/main.ts) | “Inicializa o Vue e registra navegação, componentes e gerenciamento de consultas.” |
| [`frontend/src/router/index.ts`](frontend/src/router/index.ts) | “Define a navegação da interface nova, atualmente voltada para Eventos.” |
| [`frontend/vite.config.ts`](frontend/vite.config.ts) | “Configura a geração dos arquivos Vue dentro de `backend/static/app/`.” |
| [`web.config`](web.config) | “Configura a hospedagem do processo Python no IIS.” |
| [`requirements.txt`](requirements.txt) e [`frontend/package.json`](frontend/package.json) | “Declaram as dependências de Python e da interface.” |
| [`README.md`](README.md) | “É a referência inicial de ambiente e configuração.” |

## 6. Principais funcionalidades

Os caminhos de código abaixo partem de `app/routes/`, salvo quando indicado.

| Funcionalidade | O que faz | Onde está o backend |
|---|---|---|
| Demandas por área | Cadastro, acompanhamento, tarefas, responsáveis e painéis das áreas. | `demands/default.py` |
| Gerenciador de Demandas | Quadro de trabalho da Transformação Digital, análise de solicitações, tarefas, anexos, status, mural, agendamento e recorrência. | `demandManagement/` |
| Solicitações de demandas | Envio de pedidos para Transformação Digital, anexos, acompanhamento e gráficos. | `demandRequests/` |
| Eventos e presenças | Cadastro, consulta, edição e exclusão de eventos; filtros por título/status e listas de presença com leitura de crachá e identificação no LDAP. | `backend/modules/events/`, na raiz do projeto |
| Laboratório | Solicitações dimensionais e de materiais, quadros, detalhes, arquivos, equipamentos, agendamentos e indicadores. | `request/laboratory.py` |
| Desvios de processo | Abertura e renovação de desvios, aprovações por setor, acompanhamento, ações e anexos. | `request/processDeviation.py` |
| Alteração de paradas | Solicitação, aprovação e acompanhamento de mudanças em registros de paradas. | `request/workcentersLogChange.py` |
| Melhorias e projetos | Fluxos de solicitação, aprovação e acompanhamento existentes no código. | `request/improvements.py` |
| Operação | Indicadores de logística, SSMA, qualidade e produção; apontamentos por turno; planos de ação, metas e histórico. | `operation/` |
| Monitoramento industrial | Visões de máquinas, paradas, OEE, hardware e ocorrências. | `jdt/monitoring.py` |
| Relatórios | Consultas e exportações de paradas/sinais, manutenção e disponibilidade de máquinas, além de páginas de Power BI. | `reports/oee.py`, `maintenance.py` e `powerbi.py` |
| Cadastros de fábrica | Metas, fatores, 5S, matriz de versatilidade, montagem QR e plaquetas. Algumas páginas encaminham para ferramentas externas. | `factoryRegister/` |
| Biblioteca e comunicação | Gestão de conhecimentos e arquivos; conteúdo para cockpits e TVs. | `jdt/library.py` e `communication.py` |
| Usuários e acessos | Gestão de usuários, áreas, permissões, aprovadores de paradas e alertas. | `jdt/userManager.py` |

**Cuidado ao falar sobre o que está ativo:**

- `main.py` não registra os blueprints de `computers` e `temp`. `productiveHours` e `setup` também estão desativados, inclusive com imports comentados.
- O menu de produção diferencia o histórico local de KPIs e o acesso a outro sistema para dados mais recentes.
- A rota de IA do monitoramento retorna uma página de desenvolvimento. Sua existência no arquivo não significa uma funcionalidade entregue.
- Parte dos links do menu abre outros sistemas, como FTWeb, SSRS e Power BI.
- Arquivos com `Copy`, `BKP`, datas ou `NOT_ACTIVATED` podem ser históricos. Para identificar o código usado, confira registros de blueprint e referências.

## 7. O que acontece quando alguém usa uma tela

### Exemplo antigo: abrir o relatório de paradas

```text
Menu / URL /oee/paradas
    → blueprint registrado em main.py
    → verificação de login e permissão
    → app/routes/reports/oee.py
    → template em app/templates/reports.oee/
    → formulário ou JavaScript pede os dados
    → backend consulta e trata os dados
    → tela mostra o resultado ou recebe um arquivo exportado
```

O `GET` costuma abrir a página. Outras requisições consultam, gravam ou exportam conforme a rota. No legado, um `POST` também pode consultar dados; parâmetros como `type` e `cmd` podem escolher a operação.

O Jinja preenche dados no HTML antes de enviá-lo. Depois, o JavaScript pode atualizar partes da tela sem recarregar tudo. Por isso, para entender uma funcionalidade antiga, é preciso olhar **a rota, o template e o JavaScript usado por ele**.

### Exemplo novo: cadastrar um evento

```text
/app/eventos → HTML base → interface Vue
    → usuário preenche o formulário
    → frontend/src/features/events/api.ts
    → POST /api/v1/events
    → routes.py → schemas.py → services.py → repository.py
    → banco TD
    → resposta JSON → interface atualiza a listagem
```

No módulo moderno, as responsabilidades ficam mais claras:

| Arquivo | Responsabilidade |
|---|---|
| `routes.py` | Receber a requisição, aplicar contratos e chamar o serviço. |
| `schemas.py` | Definir campos, formatos e respostas da API. |
| `services.py` | Aplicar regras, exigir permissão e controlar transações. |
| `repository.py` | Executar SQL parametrizado para consultar ou gravar. |
| `EventsPage.vue` e componentes | Apresentar os dados, formulários e ações ao usuário. |
| `api.ts`, `attendanceApi.ts` e `types.ts` | Definir chamadas HTTP e tipos da funcionalidade na interface. |

Por exemplo, o serviço exige que o fim do evento seja posterior ao início. O status é calculado na consulta ao banco conforme o período. Na presença, o código do crachá é validado e o LDAP identifica a pessoa antes da gravação.

**Uma diferença útil:** `demandManagement/` e `demandRequests/` já separam rotas, serviços e repositório, mas suas telas continuam em Jinja com CSS/JavaScript próprios. Estar organizado em camadas não significa usar Vue.

## 8. Login e permissões

1. O IIS fornece a identidade do usuário Windows.
2. `auth_routes.py` procura o usuário no banco; se necessário, consulta o diretório corporativo LDAP e trata o cadastro/acesso.
3. O Flask-Login mantém a sessão usada nas próximas requisições.
4. Os perfis vêm do campo `role` da tabela `JDT_USER_DETAILS`, armazenado como texto JSON.
5. As rotas usam esses perfis para autorizar as operações. A parte nova reaproveita essa identidade por `backend/compatibility/identity.py`.

**Frase pronta:** “O login identifica quem está acessando; as permissões definem o que essa pessoa pode fazer.”

A interface também pode esconder ações, mas a autorização precisa acontecer no servidor. Nas APIs modernas, operações de escrita usam token CSRF, uma proteção adicional associada à sessão. Não presuma que todas as telas antigas tenham a mesma implementação.

## 9. Bancos e integrações

O sistema usa várias fontes. No legado, `get_engine()` oferece os nomes `jdt`, `ftm`, `plex` e `trace_qr`. O nome `jdt` corresponde à conexão principal do TD usada pelo portal.

| Recurso | Papel no sistema |
|---|---|
| TD / conexão `jdt` | Dados do portal, como usuários, demandas e registros das funcionalidades. A parte nova também usa o TD. |
| FTM, Plex e Trace QR | Fontes consultadas por funcionalidades industriais e de rastreabilidade. O uso depende do módulo. |
| SQLAlchemy / pyodbc | Engines e conexões com SQL Server. Boa parte do projeto usa SQL escrito diretamente. |
| pandas | Tratamento de tabelas e preparação de dados para telas, gráficos e exportações. |
| LDAP | Diretório corporativo usado no fluxo de usuários e na identificação de participantes de eventos. |
| SAP via SOAP | Consultas usadas na manutenção. |
| SMTP e Microsoft Graph/Teams | E-mails, mensagens e alertas conforme o fluxo. |
| Power BI, FTWeb e SSRS | Relatórios, páginas incorporadas ou links para ferramentas externas. |

Existe código Oracle em horas produtivas, mas esse módulo está desativado no registro atual.

**Detalhe para perguntas técnicas:** a parte nova tem uma engine e um pool geral do TD por instância da aplicação. Pool é um conjunto de conexões reutilizáveis. O legado mantém seus próprios mecanismos; compartilhar o banco não significa compartilhar a mesma transação.

## 10. Configuração e publicação

| Local | O que configura |
|---|---|
| `app/config.py` | Aplicação Flask, sessão, banco do legado, e-mail, caminhos e extensões. |
| `app/utils/constants.py` | Constantes e referências de configuração das integrações antigas. |
| `backend/config.py` | TD e pool modernos, além da configuração de consulta ao LDAP. |
| `backend/platform/environment.py` | Leitura comum de variáveis de ambiente e arquivo privado opcional. |
| `.env.example` | Modelo dos nomes de configuração, sem credenciais. |
| `.env` ou arquivo escolhido por `DJ_ENV_FILE` | Valores privados do ambiente. Não deve ser versionado nem exibido na apresentação. |
| `web.config` | Configuração de hospedagem no IIS. |
| `frontend/package.json` e `frontend/vite.config.ts` | Dependências, tarefas e saída de publicação da interface. |

Exemplos de nomes de configuração são `DJ_TD_ODBC_CONNECTION_STRING` e `DJ_SESSION_SECRET_KEY`. Para explicar, basta dizer “conexão do banco” e “chave da sessão”; os valores devem permanecer privados.

As variáveis já definidas no ambiente têm prioridade sobre o arquivo privado. O carregamento ocorre uma vez; mudanças exigem reinício do processo afetado.

Na publicação, o código Vue de `frontend/` é transformado em arquivos dentro de `backend/static/app/`. O Flask usa o manifest do build para localizar esses arquivos. **Atualizar o repositório não gera o build automaticamente.** O site IIS e os serviços Windows são processos separados e precisam ser considerados conforme a mudança.

Os scripts em `database/migrations/` registram mudanças de banco. Sua aplicação exige procedimento autorizado; a parte moderna não os executa automaticamente.

## 11. Rotinas que funcionam sem alguém abrir uma tela

Os quatro agendadores ficam em `app/services/`. Eles usam APScheduler dentro de serviços Windows.

| Arquivo | Frequência programada no código | Trabalho principal |
|---|---|---|
| `run_s_30_scheduler.py` | A cada 30 segundos | Consolidação do monitoramento geral. |
| `run_m_5_scheduler.py` | A cada 5 minutos | Alertas e monitoramento de apontamentos/relógio-ponto. |
| `run_h_24_scheduler.py` | Às 6h; parte diariamente e parte de segunda a sexta | Verificação de usuários, demandas, solicitações de alteração de paradas, laboratório e desvios. |
| `run_auto_scheduler.py` | A cada minuto | Agendamentos de equipamentos do laboratório e início/recorrência de demandas. |

**Frase pronta:** “As telas atendem as ações do usuário, enquanto os serviços executam verificações e atualizações periódicas.”

A programação acima é a que está no código. Confirmar quais serviços estão instalados e ativos depende do servidor.

## 12. Roteiro para apresentar em 5 a 10 minutos

1. **Contexto:** use a explicação de 30 segundos e cite três problemas que o portal atende: demandas, laboratório e monitoramento.
2. **Mapa das pastas:** mostre `app/`, `backend/`, `frontend/` e `database/` e explique a convivência das telas antigas e novas.
3. **Entrada:** abra `main.py` para mostrar os módulos e `app/config.py` para mostrar como a aplicação é montada.
4. **Fluxo antigo:** mostre uma rota em `app/routes/reports/oee.py` e o template correspondente em `app/templates/reports.oee/`.
5. **Fluxo novo:** mostre `backend/modules/events/` e `frontend/src/features/events/`. Explique rota → validação → serviço → repositório → resposta.
6. **Recursos compartilhados:** explique login/permissões, conexão com bancos e configuração privada, sem abrir os valores.
7. **Automação:** mostre os nomes dos quatro schedulers e explique que eles funcionam em processos separados do site.
8. **Evolução:** explique que novas funcionalidades estão sendo organizadas com responsabilidades separadas e componentes reutilizáveis.

Para uma apresentação curta, priorize as seções 1, 3, 5 e um dos exemplos da seção 7.

## 13. Perguntas prováveis e respostas rápidas

**“Onde começa o sistema?”** Em `main.py`, que chama `create_app()` de `app/config.py` e registra os módulos antigos. A factory também inicializa o backend novo.

**“Onde ficam as regras de negócio?”** No legado, muitas estão nos próprios arquivos de rotas e utilitários. Nos módulos separados em camadas, ficam principalmente em `services.py` e, quando existe, em `domain.py`.

**“Tudo usa SQLAlchemy como modelo de tabela?”** Não. Existe o modelo de usuário, mas boa parte do acesso é SQL textual com SQLAlchemy, pandas ou pyodbc.

**“São dois sistemas?”** Hoje é uma aplicação Flask compartilhada, com interfaces Jinja e Vue. A parte nova ainda depende de recursos da antiga.

**“Tudo está no mesmo banco?”** Não. O TD guarda dados do portal, e várias funcionalidades também consultam outras fontes. As duas arquiteturas acessam o TD com mecanismos próprios.

**“Como encontro o código de uma tela?”** Comece pela URL ou link do menu, localize a rota, confira o blueprint registrado e siga o template/JavaScript ou a página Vue e sua API.

**“Posso executar para mostrar?”** A apresentação pode ser feita lendo o código. A inicialização atual pode criar tabelas, iniciar threads e acessar serviços corporativos. Executar exige autorização explícita com comando, ambiente e escopo.

## 14. Referências para aprofundar

- [README principal](README.md): apresentação do projeto e acesso ao manual oficial.
- [Manual do projeto](handbook/README.md): índice da documentação atual.
- [Arquitetura modernizada](handbook/docs/arquitetura-modernizada.md): organização da parte nova e convivência com o legado.
- [Eventos e listas de presença](handbook/features/eventos.md): funcionamento dos eventos e da identificação dos participantes.
- [Servidor e publicação](handbook/docs/servidor-e-publicacao.md): IIS e serviços Windows.

**Limite desta colinha:** descreve o que foi identificado nos arquivos. Conectividade, permissões reais, conteúdo dos bancos e funcionamento das telas precisam ser conferidos em ambiente autorizado.

O sistema não foi executado; a validação foi somente estática.
