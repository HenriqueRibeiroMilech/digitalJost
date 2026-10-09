# Plano de separação gradual entre backend moderno e legado

## 1. Objetivo

Simplificar o desenvolvimento de novas funcionalidades e a revisão das existentes, separando o Python moderno em `backend/` e mantendo o código antigo em `app/` durante a transição. A migração deve preservar os fluxos operacionais do Digital JOST e acontecer em entregas pequenas, com critérios de passagem e retorno definidos.

A proposta mantém inicialmente uma aplicação Flask/APIFlask no Windows/IIS, a autenticação e a sessão atuais, o frontend Vue em `frontend/` e um acesso compartilhado ao banco da Transformação Digital (TD).

Este arquivo registra o plano discutido; não implementa a separação nem autoriza execução, publicação, consultas ou alterações de banco. As regras de [AGENTS.md](../AGENTS.md) continuam aplicáveis.

## 2. Decisões que orientam a implementação

| Tema | Decisão inicial |
| --- | --- |
| Python antigo | Permanece em `app/`, com mudanças localizadas nas pontes necessárias. |
| Python novo | Passa a ficar em `backend/`, organizado por funcionalidade. |
| Frontend novo | Permanece em `frontend/`, com Vue. |
| Aplicação em produção | Uma aplicação no IIS, registrando módulos antigos e modernos. |
| Banco TD na primeira entrega | Transferir Eventos reutilizando `db.engine`, sem criar outro pool durante a mudança de localização. |
| Banco TD como destino da arquitetura | Dar ao `backend/` configuração e um engine/pool próprios em uma entrega posterior, compartilhados por todos os módulos modernos e apontando inicialmente para o mesmo banco TD do legado. |
| Banco no desenvolvimento | Manter por enquanto o banco corporativo atualmente utilizado, por decisão do responsável. O isolamento fica como trabalho futuro, sem bloquear a separação do código. |
| Autenticação | Reutilizar a identidade corporativa e a sessão atuais por uma ponte explícita. |
| Migração | Transferir e revisar uma fatia por vez; retirar o caminho antigo quando seus consumidores tiverem migrado. |
| Recursos compartilhados | Criar somente os fundamentos necessários ou recursos com reutilização comprovada. |

Este plano atualiza a localização proposta para o código moderno em [Arquitetura e modernização](arquitetura-modernizacao.md): o destino passa de `app/modules/` para `backend/modules/`. Os princípios de módulos verticais, complexidade progressiva e migração gradual permanecem. Os exemplos do [curso de Eventos](curso-pratico-primeira-feature-eventos.md) ainda retratam os caminhos anteriores; seus imports devem ser adaptados na entrega de implementação correspondente.

### 2.1. Referência do ambiente e decisões desta fase

O documento [Ambientes de desenvolvimento e servidor](ambientes-desenvolvimento-servidor.md) registra a configuração e o procedimento informados em 09/10/2026. Ele é uma referência da época, não uma consulta atual ao PC ou ao servidor. Antes de cada publicação, confirmar apenas os itens relevantes para aquela entrega e registrar as mudanças conhecidas.

| Informação registrada | Consequência para o plano |
| --- | --- |
| O backend local utiliza banco corporativo. | Preservar esse acesso nesta fase; localhost não representa um ambiente isolado. |
| O responsável informou que o portal funcionou após instalar as dependências de Eventos. | Usar esse relato como histórico de funcionamento; a cobertura das verificações não foi detalhada. |
| O responsável informou que `DJ_EVENTS` já foi criada. | A transferência de Eventos não prevê recriar a tabela nem executar o script SQL. |
| A publicação acontece por cópia manual de arquivos no servidor Windows/IIS. | Preparar um pacote completo e copiar os arquivos relacionados na mesma janela, com o site parado. |
| O build Vue é preparado no PC e entregue em `app/static/app/`. | Preservar esse destino inicialmente; a pasta é ignorada pelo Git e precisa acompanhar publicações que alterem o frontend. |
| A configuração publicada pode diferir da versionada. | Conferir as opções relevantes no servidor, especialmente `EVENTS_ENABLED`, preservando as demais configurações. |

Na consulta estática que embasou esta revisão, o `web.config` versionado não continha `EVENTS_ENABLED`, enquanto o documento de ambientes descrevia a entrada combinada para o servidor. Isso indica um ponto a confirmar, sem comprovar qual configuração está efetivamente publicada.

O isolamento de desenvolvimento e homologação continua sendo uma melhoria futura, mas não é pré-requisito desta fase de separação. A utilização atual do banco corporativo foi mantida explicitamente pelo responsável. Essa decisão não autoriza agentes a executar o sistema, consultar o banco ou cadastrar dados: as autorizações de comando, ambiente e escopo exigidas em `AGENTS.md` continuam necessárias.

## 3. O que significa acesso compartilhado ao banco

Um engine/pool gerencia as conexões necessárias ao banco TD. Todos os módulos modernos compartilham um acesso geral; cada operação utiliza uma conexão e controla sua transação. O compartilhamento entre módulos modernos é permanente. O compartilhamento desse engine com o legado é uma ponte da primeira entrega.

```text
Primeira entrega
    acesso atual ao TD → legado e Eventos em backend/

Entrega posterior
    app/ → infraestrutura atual de acesso ──────┐
                                               ├── mesmo banco TD
    backend/ → engine/pool moderno compartilhado┘
                   ├── Eventos
                   └── demais módulos modernos
```

Cada funcionalidade continua tendo seu repositório, porque suas consultas e seus dados precisam de um responsável. Repositórios separados não significam conexões ou pools separados.

O ponto de partida já permite esse começo: `EventsService` recebe um engine, e `app/config.py` fornece `db.engine`. O repositório de Eventos recebe a conexão; o serviço controla a transação de escrita com `engine.begin()`. A transferência preserva essa dependência, fornecida explicitamente ao bootstrap moderno.

O legado também contém outros mecanismos de acesso em `app/utils/db_utils.py`, além de acessos a FTM, Plex e Trace QR. Portanto, reutilizar `db.engine` inicialmente não significa que todo o sistema já tenha um único pool. Na entrega posterior, acrescentar o acesso moderno exige dimensionar o conjunto de pools existentes. As outras fontes de dados continuam distintas.

A duplicidade temporária é da infraestrutura de acesso, mantendo o mesmo banco e os mesmos dados. Ela permite revisar a base moderna sem alterar todos os consumidores antigos juntos. Os acessos antigos só serão retirados após a migração dos respectivos consumidores.

Não compartilhar uma conexão permanentemente aberta entre requisições, nem tratar conexões diferentes como uma única transação. A infraestrutura é compartilhada; o limite de cada operação continua explícito.

## 4. Estrutura inicial e direção de dependências

A primeira entrega precisa apenas da estrutura utilizada por Eventos:

```text
digitalJost/
├── main.py                       # entrada atual do IIS e registro do legado
├── app/                          # código antigo e recursos atuais
├── backend/
│   ├── __init__.py
│   ├── bootstrap.py              # composição e registro explícitos do moderno
│   └── modules/
│       ├── __init__.py
│       └── events/
│           ├── __init__.py
│           ├── routes.py
│           ├── schemas.py
│           ├── services.py
│           └── repository.py
└── frontend/                     # aplicação Vue existente
```

Depois, conforme as responsabilidades forem extraídas, `backend/platform/` recebe mecanismos de identidade, CSRF, banco e entrega do shell Vue. `backend/compatibility/` concentra os adaptadores temporários do legado. Não criar essas pastas com arquivos vazios apenas para completar uma árvore.

Regras de dependência:

- A composição fornece o engine e os mecanismos de autorização aos serviços modernos.
- Serviços e repositórios modernos não importam `app/config.py`, handlers antigos ou engines globais do legado.
- Uma dependência inevitável do legado fica em um adaptador identificado, com seus consumidores e condição de retirada registrados.
- O registro é explícito e acontece uma única vez; não usar descoberta automática de módulos.
- Imports do código moderno não iniciam conexões, threads, jobs ou notificações.
- Regras de negócio pertencem à funcionalidade; a plataforma oferece mecanismos compartilhados.

Na primeira transferência de Eventos, dependências HTTP ainda existentes podem permanecer temporariamente como estão. Elas devem ser registradas para a etapa de adaptadores, sem ampliar seu uso para novos módulos.

## 5. Passo a passo

### Etapa 0 — registrar a situação atual e preparar a entrega

**Objetivo:** saber o que precisa continuar funcionando e limitar o alcance da mudança.

1. Rastrear Eventos desde o registro na factory até shell, API, serviço, repositório e frontend.
2. Registrar URLs, nomes dos blueprints e endpoints, contratos JSON, token CSRF, permissões, configuração `EVENTS_ENABLED`, template e caminhos dos assets.
3. Identificar os imports de Eventos em `app/config.py`, `app/modules/` e demais consumidores por busca textual.
4. Registrar os fluxos principais do legado que serão conferidos no ambiente autorizado: login, home e operações representativas dos módulos ativos.
5. Usar o registro de ambientes para definir o ambiente e o escopo das verificações autorizadas, o pacote anterior e o procedimento de retorno antes da publicação. Registrar que o banco continua corporativo nesta fase.

**Critério de passagem:** referências e dependências conhecidas; escopo sem mudanças de schema, dados, autenticação ou hospedagem. A preparação pode avançar por análise estática, sem exigir a criação de um banco de desenvolvimento. Qualquer execução futura requer autorização explícita para o ambiente e o escopo definidos; a configuração desligada não comprova isolamento da inicialização.

### Etapa 1 — transferir Eventos para `backend/`

**Objetivo:** estabelecer a fronteira física com o menor alcance possível.

1. Transferir os arquivos ativos de Eventos para `backend/modules/events/`, preservando contratos e regras.
2. Criar um bootstrap explícito para compor o serviço e registrar seus blueprints.
3. Fazer o ponto atual de composição delegar ao bootstrap moderno e fornecer o `db.engine` existente no momento apropriado, com o contexto da aplicação quando necessário.
4. Atualizar os imports conhecidos. Se um encaminhamento temporário em `app/modules/` for necessário, ele apenas delega; não mantém outra implementação nem registra Eventos novamente.
5. Preservar a condição de disponibilidade de Eventos, incluindo a composição do serviço quando habilitado e as respostas de indisponibilidade quando desligado.
6. Manter nomes dos blueprints, endpoints, URLs e os caminhos atuais de template e assets. A mudança de pacote não deve mudar a resolução desses recursos.
7. Preparar o pacote de publicação com `backend/` completo e todos os arquivos cujos imports ou pontos de composição mudaram. Seguir o procedimento da seção 6.1.

Nesta entrega, o registro dos blueprints antigos permanece em `main.py`. O Vue, a tabela `DJ_EVENTS`, o engine/pool atual, os handlers globais e a autenticação mantêm seus contratos atuais.

A primeira transferência deve preservar as bibliotecas e versões já utilizadas por Eventos. Instalação ou atualização de dependências não faz parte dessa mudança de localização.

**Critério de passagem:** uma implementação e um registro de Eventos, referências atualizadas, pacote completo e nenhuma alteração de contrato. Antes da liberação, conferir no ambiente e na janela autorizados shell, GET, sessão, permissões, CSRF e fluxos representativos do legado. Verificações de POST precisam de escopo próprio para eventuais gravações no banco corporativo; a transferência não exige criar cadastros adicionais por iniciativa do agente.

**Retorno:** restaurar o pacote anterior aprovado, sem necessidade de converter dados, pois esta entrega não altera o schema nem o contrato de persistência.

### Etapa 2 — introduzir o acesso geral próprio do backend ao TD

**Objetivo:** separar a infraestrutura de banco da arquitetura nova, depois de verificar a transferência de Eventos.

1. Definir a configuração efetiva do TD para o backend moderno, preservando inicialmente o destino corporativo aprovado e sem copiar segredos para o código.
2. Criar um engine SQLAlchemy próprio em um ponto central da plataforma moderna, inicializado explicitamente na composição e compartilhado por todos os seus módulos. Não registrar uma segunda instância de Flask-SQLAlchemy na mesma aplicação.
3. Dimensionar o pool adicional considerando o acesso antigo e os processos da aplicação. Não criar engines por request ou por funcionalidade.
4. Trocar a dependência fornecida a Eventos pelo engine moderno, preservando consultas, contratos e limites de transação.
5. Manter os consumidores antigos em seus mecanismos atuais. Uma operação que precise de atomicidade deve utilizar a mesma conexão/transação, mesmo durante a convivência.
6. Documentar o ciclo de vida do engine, a configuração utilizada e o retorno para a composição anterior.

**Critério de passagem:** os módulos modernos têm um acesso geral próprio, com configuração explícita e pool dimensionado; o legado preserva seus acessos e os dois lados continuam no banco TD aprovado. Essa etapa não faz parte da primeira transferência de arquivos.

### Etapa 3 — organizar as pontes e a base compartilhada

**Objetivo:** evitar que cada próxima funcionalidade precise conhecer detalhes do legado.

1. Criar um adaptador de identidade e permissões atuais, mantendo o comportamento de acesso existente. Mudanças no mapeamento de quem pode criar ou participar do piloto são entregas específicas.
2. Expor uma identidade normalizada ao serviço; não fornecer objetos de request ou aceitar identidade enviada pelo navegador.
3. Extrair o mecanismo moderno de CSRF, preservando o contrato utilizado pelo cliente HTTP e a compatibilidade das sessões durante a transição.
4. Separar leitura do manifesto Vite e entrega do shell da lógica de Eventos. Manter a lista explícita de rotas Vue reconhecidas no servidor.
5. Oferecer acesso ao engine compartilhado por composição. Um módulo novo não precisa importar a configuração antiga para acessar o banco.
6. Padronizar os erros da API moderna, incluindo validação e erros de roteamento, preservando o comportamento HTML das páginas antigas.

Dividir estes itens em mudanças focadas; eles não precisam entrar na mesma publicação. A disponibilidade de uma funcionalidade e a política de acesso continuam pertencendo ao módulo, mesmo quando usam mecanismos compartilhados.

**Critério de passagem:** Eventos usa mecanismos com responsabilidades claras; um segundo módulo pode reutilizá-los sem copiar sua lógica ou importar os detalhes antigos diretamente.

### Etapa 4 — consolidar configuração e inicialização

**Objetivo:** consolidar as opções e o ciclo de vida modernos, aproveitando o acesso geral definido na etapa 2.

1. Definir as opções próprias do backend moderno, começando pelas funcionalidades habilitadas e pelos recursos que ele realmente utiliza.
2. Manter fontes explícitas para as opções de banco do backend e para a sessão compartilhada da aplicação. Separar configuração não exige copiar credenciais nem mudar cookies e chaves de sessão.
3. Organizar as opções para permitir configuração por ambiente no futuro, mantendo agora o banco corporativo aprovado. Reutilizar o engine moderno central da etapa 2, sem acrescentar engines por módulo.
4. Mapear os imports de `db` e `mail` antes de decidir se sua definição muda de lugar. Uma eventual transferência precisa preservar a mesma instância e a compatibilidade dos consumidores antigos.
5. Planejar separadamente o controle de `db.create_all()`, integrações no import, auditoria e demais efeitos globais da inicialização.

Enquanto a aplicação continuar carregando o legado, seus efeitos globais podem atingir as requisições modernas. A separação de pastas, por si só, não torna o backend isolado. Uma futura composição somente moderna deverá receber dependências próprias do ambiente autorizado, sem carregar a inicialização antiga.

**Critério de passagem:** configurações e dependências explícitas, um acesso geral para os módulos modernos e preservação dos consumidores antigos. Isolamento de banco, identidade, arquivos e integrações fica registrado como trabalho futuro; execuções continuam limitadas às autorizações específicas do ambiente escolhido.

### Etapa 5 — desenvolver uma segunda funcionalidade pequena

**Objetivo:** comprovar que a base simplifica o trabalho cotidiano.

1. Escolher um cadastro ou leitura com poucas integrações e regras conhecidas.
2. Definir comportamento, contrato, permissões e dados antes dos arquivos.
3. Criar o módulo em `backend/modules/` e a interface em `frontend/src/features/`.
4. Reutilizar o acesso ao TD, a identidade, o CSRF, o shell e o cliente HTTP disponíveis.
5. Manter consultas no repositório e, nas escritas, regras e transações no serviço. Leituras triviais podem dispensar serviço quando não houver responsabilidade que o justifique.
6. Registrar o módulo no ponto único de composição.

**Critério de passagem:** para criar a funcionalidade, foi necessário escrever principalmente seu contrato, consultas, regras e interface. Não foi necessário copiar autenticação, configuração de banco ou a inicialização de Eventos.

### Etapa 6 — migrar uma fatia do legado por vez

**Objetivo:** reduzir gradualmente o código antigo sem duplicar regras operacionais.

1. Escolher uma fatia limitada por uma mudança útil, custo de manutenção ou risco conhecido.
2. Mapear todos os métodos HTTP, leitores, escritores, permissões, arquivos, integrações e jobs ligados aos mesmos dados.
3. Registrar o comportamento esperado, incluindo casos de acesso permitido e negado.
4. Extrair o caso de uso para o backend moderno. Durante a convivência, a entrada antiga e a nova convergem para a mesma regra; jobs relacionados também precisam ser considerados.
5. Construir a interface Vue e liberar o caminho novo de forma controlada.
6. Conferir equivalência funcional e o retorno previsto antes de retirar o caminho antigo.
7. Remover código substituído e adaptadores somente após confirmar a ausência de consumidores.

Manter um inventário com situação `LEGACY`, `HYBRID` ou `MODERN`, rotas, dados, jobs, dependências temporárias e próxima ação. A classificação acompanha responsabilidades e evidências, não apenas a pasta do arquivo.

**Critério de passagem:** a fatia tem um responsável pelas regras e gravações; os consumidores relacionados foram considerados e a retirada do caminho antigo tem evidência suficiente.

## 6. Como controlar o risco em cada entrega

| Mudança | Controle principal |
| --- | --- |
| Transferência de pacote | Atualizar referências e preservar endpoints, contratos e resolução de recursos. |
| Composição e registro | Manter um registro por blueprint e dependências fornecidas explicitamente. |
| Banco TD | Reutilizar o engine atual, preservar transações e evitar mudança de schema na primeira entrega. |
| Sessão e permissões | Preservar contratos; revisar adaptações separadamente. |
| Inicialização e hooks globais | Mapear efeitos e tratá-los em entregas específicas, pois atingem o portal inteiro. |
| Publicação | Pacote revisado, verificação autorizada e retorno ao pacote anterior preparado. |

Os controles reduzem o alcance das falhas, mas não garantem ausência de regressões. `EVENTS_ENABLED` bloqueia o uso da funcionalidade conforme seu código; não desfaz mudanças de imports, inicialização ou schema e não substitui o retorno ao pacote anterior.

Evitar combinar na primeira entrega transferência de Eventos, reescrita do login, alteração dos schedulers, mudança da home, substituição de engines antigos ou limpeza ampla do legado. Correções urgentes nesses pontos têm escopo e validação próprios.

### 6.1. Preparar e publicar pelo procedimento manual atual

Esta seção orienta uma publicação futura pelo responsável; não autoriza o agente a copiar arquivos no servidor, instalar dependências ou reiniciar o IIS.

1. Revisar o pacote e guardar os arquivos correspondentes da versão anterior. Incluir `backend/` inteiro, os arquivos de composição/imports alterados e eventuais encaminhamentos temporários. Evitar misturar arquivos de entregas diferentes.
2. Manter inicialmente `main.py`, o template `app/templates/app/shell.html` e o destino de assets `app/static/app/` nos caminhos atuais. Preservar `.venv`, uploads e configurações corporativas durante a cópia.
3. Quando a entrega alterar o frontend, preparar o build no PC pelo procedimento autorizado já registrado e incluir a pasta gerada inteira, com `.vite/manifest.json` e todos os assets do mesmo build. Uma mudança apenas de localização do Python pode reutilizar o build compatível já publicado.
4. Conferir a configuração efetiva relevante no servidor, especialmente `EVENTS_ENABLED`. Preservar o restante do `web.config`; não substituí-lo indiscriminadamente pela versão do repositório.
5. Se uma entrega futura exigir novas dependências, tratar sua instalação previamente em escopo específico e confirmar disponibilidade na `.venv` usada pelo IIS antes de ativar o código que as importa. O registro de ambientes descreve instalação offline; copiar `requirements.txt` não instala pacotes.
6. Na janela autorizada, parar o site, copiar o pacote completo e reiniciar a aplicação pelo procedimento do IIS. Confirmar as aplicações atendidas pelo Application Pool antes de qualquer reinício do pool, pois sua exclusividade não foi confirmada.
7. Realizar as verificações autorizadas e registrar resultados. Se houver falha que impeça a liberação, aplicar o retorno preparado; desligar Eventos não corrige necessariamente um erro de inicialização.

O registro de ambientes relata indisponibilidade após a atualização de `app/config.py` antes da instalação das dependências. A causa foi considerada provável, sem traceback que confirmasse o erro exato. Esse histórico reforça a preparação do pacote e das dependências antes da ativação.

## 7. Validação e evidências

No trabalho estático, conferir referências, contratos entre frontend e backend, composição, transações como texto, diff completo e `git diff --check`. Não executar imports, testes, builds, linters ou consultas por iniciativa própria.

Nesta fase, o banco corporativo permanece em uso. As verificações futuras devem indicar os recursos e operações envolvidos; eventuais gravações precisam estar explicitamente dentro do escopo autorizado. A criação de ambiente isolado fica como trabalho futuro e não bloqueia a revisão textual ou a preparação da transferência de Eventos.

Em uma etapa futura, com autorização explícita para comandos, ambiente e escopo, registrar evidências de:

- Login, home e operações representativas do legado.
- Carregamento direto de `/app/eventos`, assets e retorno ao portal.
- GET paginado e comportamento do POST de Eventos no ambiente aprovado, respeitando o escopo de gravações autorizado.
- Sessão ausente, acesso negado, CSRF inválido e dados inválidos.
- Funcionalidade desligada e ausência de registro duplicado.
- Erros JSON na API e respostas próprias das páginas antigas.
- Persistência e rollback de transação no ambiente autorizado.
- Retorno ao pacote anterior, considerando dados e jobs quando uma entrega passar a alterá-los.

Registrar separadamente o que existe no código e o que foi verificado em cada ambiente. Nenhuma etapa deve ser considerada publicada ou funcionalmente validada apenas pela inspeção textual.

## 8. Primeira entrega recomendada

**Separar Eventos em `backend/`, mantendo o acesso compartilhado ao TD e os contratos atuais.**

Essa entrega estabelece a fronteira do Python moderno e preserva o funcionamento esperado sem exigir um novo pool, outro servidor ou uma nova autenticação. Depois da verificação autorizada, introduzir o acesso geral próprio do backend ao mesmo TD, seguido de adaptadores, consolidação da configuração e reuso por uma segunda funcionalidade.

## 9. Registro da primeira entrega

**Situação:** transferência implementada no código e conferida estaticamente. A verificação funcional e a publicação no IIS permanecem pendentes de ambiente, janela e escopo autorizados.

| Parte | Resultado da implementação |
| --- | --- |
| Módulo Eventos | Transferido de `app/modules/events/` para `backend/modules/events/`, preservando o texto das rotas, schemas, consultas e serviços. |
| Registro moderno | Transferido para `backend/modules/__init__.py`, com a lista explícita dos dois blueprints de Eventos. |
| Composição | Centralizada em `backend/bootstrap.py`, pela função `init_backend(app, td_engine=...)`. |
| Ponte da factory | `app/config.py` resolve `db.engine` no contexto já existente, apenas quando Eventos está habilitado, e fornece essa dependência ao bootstrap antes de devolver a aplicação. |
| Disponibilidade | Com Eventos desligado, o bootstrap registra os blueprints e mantém as respostas de indisponibilidade, sem compor o serviço nem solicitar o engine. |
| Dependências temporárias | As rotas ainda usam a sessão atual e `app.utils.permissions`; a extração de adaptadores fica para a etapa correspondente. |
| Banco | A primeira entrega mantém o engine atual e as mesmas operações em `DJ_EVENTS`. O acesso próprio do backend será implementado na etapa 2. |

As referências Python ativas aos caminhos antigos foram atualizadas. Nenhum encaminhamento temporário foi necessário em `app/modules/`. Os guias e o registro de ambientes mantêm seus exemplos históricos; o fluxo atual é o descrito nesta seção.

O bootstrap fornece o serviço em `app.extensions["events_service"]`, mantendo o contrato que as rotas já utilizam. O registro dos módulos antigos em `main.py`, os caminhos de template/assets, o frontend, as dependências, as permissões, o token de sessão CSRF e os limites de transação permanecem com seu desenho anterior.

Para a publicação desta entrega, preparar `backend/` inteiro e o `app/config.py` atualizado juntos. O build Vue compatível já publicado e `app/templates/app/shell.html` continuam sendo necessários, sem exigir um novo build por causa da transferência do Python. O README e este plano acompanham o pacote como documentação.

Para retornar, restaurar o `app/config.py` e o pacote `app/modules/` da versão anterior aprovada. O retorno deve restaurar os arquivos de composição e o módulo correspondente juntos, sem conversão de schema ou dados.

A validação desta entrega inclui busca de referências, inspeção da composição, comparação textual dos seis arquivos transferidos com a versão anterior e revisão do diff. Não houve imports, execução, instalação, build, consulta ao banco ou publicação. O funcionamento no IIS ainda precisa ser confirmado pelo responsável no escopo autorizado.

O sistema não foi executado; a validação foi somente estática. Este documento não comprova funcionamento no IIS, isolamento dos ambientes, persistência ou equivalência funcional do legado.
