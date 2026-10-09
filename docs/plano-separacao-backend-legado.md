# Plano de separação gradual entre backend moderno e legado

## 1. Objetivo

Simplificar o desenvolvimento de novas funcionalidades e a revisão das existentes, separando o Python moderno em `backend/` e mantendo o código antigo em `app/` durante a transição. A migração deve preservar os fluxos operacionais do Digital JOST e acontecer em entregas pequenas, com critérios de passagem e retorno definidos.

A proposta mantém inicialmente uma aplicação Flask/APIFlask no Windows/IIS, a autenticação e a sessão atuais, o frontend Vue em `frontend/` e um acesso ao banco da Transformação Digital (TD) compartilhado entre os módulos modernos.

Este arquivo registra o plano discutido e as entregas implementadas nas seções 9 a 11; não autoriza execução, publicação, consultas ou alterações de banco. As regras de [AGENTS.md](../AGENTS.md) continuam aplicáveis.

## 2. Decisões que orientam a implementação

| Tema | Decisão inicial |
| --- | --- |
| Python antigo | Permanece em `app/`, com mudanças localizadas nas pontes necessárias. |
| Python novo | Passa a ficar em `backend/`, organizado por funcionalidade. |
| Frontend novo | Permanece em `frontend/`, com Vue. |
| Aplicação em produção | Uma aplicação no IIS, registrando módulos antigos e modernos. |
| Banco TD na primeira entrega | Transferir Eventos reutilizando `db.engine`, sem criar outro pool durante a mudança de localização. |
| Banco TD na entrega 2 | Configuração e engine/pool próprios em `backend/`, compartilhados por todos os módulos modernos e apontando para o mesmo banco TD do legado. Implementado no código; verificação funcional pendente. |
| Banco no desenvolvimento | Manter por enquanto o banco corporativo atualmente utilizado, por decisão do responsável. O isolamento fica como trabalho futuro, sem bloquear a separação do código. |
| Autenticação | Reutilizar a identidade corporativa e a sessão atuais por uma ponte explícita. |
| Eventos | Funcionalidade normal, registrada e composta na inicialização. O acesso é controlado pela sessão e pelas permissões existentes, sem chave específica de ativação. |
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
| A configuração publicada pode diferir da versionada. | Conferir as opções de inicialização relevantes no servidor, preservando as demais configurações. |

A chave `EVENTS_ENABLED` descrita no registro de ambientes e nos guias anteriores foi retirada do código ativo por decisão do responsável. Eventos é uma funcionalidade normal, sem tratamento de piloto. Uma entrada antiga dessa variável no ambiente deixa de ser consultada pela aplicação; a configuração atual não exige adicionar essa entrada no IIS.

O isolamento de desenvolvimento e homologação continua sendo uma melhoria futura, mas não é pré-requisito desta fase de separação. A utilização atual do banco corporativo foi mantida explicitamente pelo responsável. Essa decisão não autoriza agentes a executar o sistema, consultar o banco ou cadastrar dados: as autorizações de comando, ambiente e escopo exigidas em `AGENTS.md` continuam necessárias.

## 3. O que significa acesso compartilhado ao banco

Um engine/pool gerencia as conexões necessárias ao banco TD. Todos os módulos modernos compartilham um acesso geral; cada operação utiliza uma conexão e controla sua transação. O compartilhamento entre módulos modernos é permanente. O compartilhamento desse engine com o legado é uma ponte da primeira entrega.

```text
Primeira entrega
    acesso atual ao TD → legado e Eventos em backend/

Entrega 2 (implementada no código)
    app/ → infraestrutura atual de acesso ──────┐
                                               ├── mesmo banco TD
    backend/ → engine/pool moderno compartilhado┘
                   ├── Eventos
                   └── demais módulos modernos
```

Cada funcionalidade continua tendo seu repositório, porque suas consultas e seus dados precisam de um responsável. Repositórios separados não significam conexões ou pools separados.

Na primeira entrega, `EventsService` recebeu o `db.engine` fornecido por `app/config.py`. Na entrega 2, a factory fornece apenas a configuração efetiva de destino do TD; `backend/bootstrap.py` cria o engine moderno pelo ponto central da plataforma e o injeta no serviço. O repositório continua recebendo a conexão e o serviço controla a transação de escrita com `engine.begin()`.

O legado também contém outros mecanismos de acesso em `app/utils/db_utils.py`, além de acessos a FTM, Plex e Trace QR. Portanto, reutilizar `db.engine` inicialmente não significa que todo o sistema já tenha um único pool. A entrega 2 acrescenta um pool moderno limitado por padrão a cinco conexões por instância da aplicação; dimensionar o conjunto de pools e processos ainda exige verificação no ambiente autorizado. As outras fontes de dados continuam distintas.

A duplicidade temporária é da infraestrutura de acesso, mantendo o mesmo banco e os mesmos dados. Ela permite revisar a base moderna sem alterar todos os consumidores antigos juntos. Os acessos antigos só serão retirados após a migração dos respectivos consumidores.

Não compartilhar uma conexão permanentemente aberta entre requisições, nem tratar conexões diferentes como uma única transação. A infraestrutura é compartilhada; o limite de cada operação continua explícito.

## 4. Estrutura inicial e direção de dependências

A estrutura após a entrega 3a inclui o acesso geral ao TD e o carregamento do shell Vue utilizados por Eventos e disponíveis para os próximos módulos:

```text
digitalJost/
├── main.py                       # entrada atual do IIS e registro do legado
├── app/                          # código antigo e recursos atuais
├── backend/
│   ├── __init__.py
│   ├── bootstrap.py              # composição e registro explícitos do moderno
│   ├── config.py                 # configuração própria do pool; destino recebido
│   ├── platform/
│   │   ├── __init__.py
│   │   ├── database.py           # engine geral do TD e ciclo de vida
│   │   └── vue_shell.py          # manifesto Vite e renderização do shell Vue
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

O banco e o carregamento do shell Vue já estão em `backend/platform/`. Depois, conforme as responsabilidades forem extraídas, essa pasta recebe mecanismos de identidade e CSRF. `backend/compatibility/` concentrará os adaptadores temporários do legado. Não criar essas pastas com arquivos vazios apenas para completar uma árvore.

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
2. Registrar URLs, nomes dos blueprints e endpoints, contratos JSON, token CSRF, permissões, template e caminhos dos assets.
3. Identificar os imports de Eventos em `app/config.py`, `app/modules/` e demais consumidores por busca textual.
4. Registrar os fluxos principais do legado que serão conferidos no ambiente autorizado: login, home e operações representativas dos módulos ativos.
5. Usar o registro de ambientes para definir o ambiente e o escopo das verificações autorizadas, o pacote anterior e o procedimento de retorno antes da publicação. Registrar que o banco continua corporativo nesta fase.

**Critério de passagem:** referências e dependências conhecidas; escopo sem mudanças de schema, dados, autenticação ou hospedagem. A preparação pode avançar por análise estática, sem exigir a criação de um banco de desenvolvimento. Qualquer execução futura requer autorização explícita para o ambiente e o escopo definidos.

### Etapa 1 — transferir Eventos para `backend/`

**Objetivo:** estabelecer a fronteira física com o menor alcance possível.

1. Transferir os arquivos ativos de Eventos para `backend/modules/events/`, preservando contratos e regras.
2. Criar um bootstrap explícito para compor o serviço e registrar seus blueprints.
3. Fazer o ponto atual de composição delegar ao bootstrap moderno e fornecer o `db.engine` existente no momento apropriado, com o contexto da aplicação quando necessário.
4. Atualizar os imports conhecidos. Se um encaminhamento temporário em `app/modules/` for necessário, ele apenas delega; não mantém outra implementação nem registra Eventos novamente.
5. Compor o serviço e registrar Eventos como funcionalidade normal, preservando a autenticação, as permissões e o CSRF existentes.
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

**Situação da entrega 2:** implementada e revisada estaticamente, conforme a seção 10. O limite inicial está definido no código; sua adequação à carga e ao número de processos do IIS ainda não foi verificada. A implementação não significa aprovação da publicação nem conclusão da verificação funcional.

### Etapa 3 — organizar as pontes e a base compartilhada

**Objetivo:** evitar que cada próxima funcionalidade precise conhecer detalhes do legado.

1. Criar um adaptador de identidade e permissões atuais, mantendo o comportamento de acesso existente. Mudanças no mapeamento de quem pode consultar ou criar são entregas específicas.
2. Expor uma identidade normalizada ao serviço; não fornecer objetos de request ou aceitar identidade enviada pelo navegador.
3. Extrair o mecanismo moderno de CSRF, preservando o contrato utilizado pelo cliente HTTP e a compatibilidade das sessões durante a transição.
4. Separar leitura do manifesto Vite e entrega do shell da lógica de Eventos. Manter a lista explícita de rotas Vue reconhecidas no servidor.
5. Oferecer acesso ao engine compartilhado por composição. Um módulo novo não precisa importar a configuração antiga para acessar o banco.
6. Padronizar os erros da API moderna, incluindo validação e erros de roteamento, preservando o comportamento HTML das páginas antigas.

Dividir estes itens em mudanças focadas; eles não precisam entrar na mesma publicação. A disponibilidade de uma funcionalidade e a política de acesso continuam pertencendo ao módulo, mesmo quando usam mecanismos compartilhados.

**Situação da entrega 3a:** a leitura do manifesto e a renderização do shell foram extraídas para `backend/platform/vue_shell.py`, conforme a seção 11. O acesso geral ao TD já foi implementado na entrega 2. Identidade, permissões, CSRF e padronização de erros da API permanecem como próximos trabalhos desta etapa.

**Critério de passagem:** Eventos usa mecanismos com responsabilidades claras; um segundo módulo pode reutilizá-los sem copiar sua lógica ou importar os detalhes antigos diretamente.

### Etapa 4 — consolidar configuração e inicialização

**Objetivo:** consolidar as opções e o ciclo de vida modernos, aproveitando o acesso geral definido na etapa 2.

1. Definir as opções próprias do backend moderno para os recursos que ele realmente utiliza. Chaves de ativação por funcionalidade não são um requisito da arquitetura.
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

Os controles reduzem o alcance das falhas, mas não garantem ausência de regressões. O retorno ao pacote anterior precisa restaurar os arquivos relacionados; uma mudança de configuração não desfaz mudanças de imports, inicialização ou schema.

Evitar combinar na primeira entrega transferência de Eventos, reescrita do login, alteração dos schedulers, mudança da home, substituição de engines antigos ou limpeza ampla do legado. Correções urgentes nesses pontos têm escopo e validação próprios.

### 6.1. Preparar e publicar pelo procedimento manual atual

Esta seção orienta uma publicação futura pelo responsável; não autoriza o agente a copiar arquivos no servidor, instalar dependências ou reiniciar o IIS.

1. Revisar o pacote e guardar os arquivos correspondentes da versão anterior. Incluir `backend/` inteiro, os arquivos de composição/imports alterados e eventuais encaminhamentos temporários. Evitar misturar arquivos de entregas diferentes.
2. Manter inicialmente `main.py`, o template `app/templates/app/shell.html` e o destino de assets `app/static/app/` nos caminhos atuais. Preservar `.venv`, uploads e configurações corporativas durante a cópia.
3. Quando a entrega alterar o frontend, preparar o build no PC pelo procedimento autorizado já registrado e incluir a pasta gerada inteira, com `.vite/manifest.json` e todos os assets do mesmo build. Uma mudança apenas de localização do Python pode reutilizar o build compatível já publicado.
4. Conferir a configuração efetiva de inicialização no servidor. Preservar o restante do `web.config`; não substituí-lo indiscriminadamente pela versão do repositório. Eventos não exige uma variável de ativação.
5. Se uma entrega futura exigir novas dependências, tratar sua instalação previamente em escopo específico e confirmar disponibilidade na `.venv` usada pelo IIS antes de ativar o código que as importa. O registro de ambientes descreve instalação offline; copiar `requirements.txt` não instala pacotes.
6. Na janela autorizada, parar o site, copiar o pacote completo e reiniciar a aplicação pelo procedimento do IIS. Confirmar as aplicações atendidas pelo Application Pool antes de qualquer reinício do pool, pois sua exclusividade não foi confirmada.
7. Realizar as verificações autorizadas e registrar resultados. Se houver falha que impeça a liberação, aplicar o retorno preparado.

O registro de ambientes relata indisponibilidade após a atualização de `app/config.py` antes da instalação das dependências. A causa foi considerada provável, sem traceback que confirmasse o erro exato. Esse histórico reforça a preparação do pacote e das dependências antes da ativação.

## 7. Validação e evidências

No trabalho estático, conferir referências, contratos entre frontend e backend, composição, transações como texto, diff completo e `git diff --check`. Não executar imports, testes, builds, linters ou consultas por iniciativa própria.

Nesta fase, o banco corporativo permanece em uso. As verificações futuras devem indicar os recursos e operações envolvidos; eventuais gravações precisam estar explicitamente dentro do escopo autorizado. A criação de ambiente isolado fica como trabalho futuro e não bloqueia a revisão textual ou a preparação da transferência de Eventos.

Em uma etapa futura, com autorização explícita para comandos, ambiente e escopo, registrar evidências de:

- Login, home e operações representativas do legado.
- Carregamento direto de `/app/eventos`, assets e retorno ao portal.
- GET paginado e comportamento do POST de Eventos no ambiente aprovado, respeitando o escopo de gravações autorizado.
- Sessão ausente, acesso negado, CSRF inválido e dados inválidos.
- Registro e composição de Eventos sem variável de ativação, sem duplicidade de blueprints.
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
| Ponte da factory | `app/config.py` resolve `db.engine` no contexto já existente e fornece essa dependência ao bootstrap antes de devolver a aplicação. |
| Disponibilidade | O bootstrap compõe o serviço e registra Eventos em toda inicialização. Shell e API verificam a sessão e as permissões, sem chave de ativação. |
| Dependências temporárias | As rotas ainda usam a sessão atual e `app.utils.permissions`; a extração de adaptadores fica para a etapa correspondente. |
| Banco | A primeira entrega mantém o engine atual e as mesmas operações em `DJ_EVENTS`. O acesso próprio do backend será implementado na etapa 2. |

As referências Python ativas aos caminhos antigos foram atualizadas. Nenhum encaminhamento temporário foi necessário em `app/modules/`. Os guias e o registro de ambientes mantêm seus exemplos históricos. Esta seção registra a primeira entrega; a composição atual de banco está na seção 10.

O bootstrap fornece o serviço em `app.extensions["events_service"]`, mantendo o contrato que as rotas já utilizam. O registro dos módulos antigos em `main.py`, os caminhos de template/assets, o frontend, as dependências, as permissões, o token de sessão CSRF e os limites de transação permanecem com seu desenho anterior.

Após a transferência, a chave de ativação foi removida da configuração, da composição e dos handlers. As verificações de sessão, permissão `GENERAL` e CSRF continuam no backend. Os trechos dos guias que ensinam a habilitar Eventos por variável retratam a proposta anterior e não são necessários para o fluxo atual.

Para a publicação desta entrega, preparar `backend/` inteiro e o `app/config.py` atualizado juntos. O build Vue compatível já publicado e `app/templates/app/shell.html` continuam sendo necessários, sem exigir um novo build por causa da transferência do Python. O README e este plano acompanham o pacote como documentação.

Para retornar, restaurar o `app/config.py` e o pacote `app/modules/` da versão anterior aprovada. O retorno deve restaurar os arquivos de composição e o módulo correspondente juntos, sem conversão de schema ou dados.

A validação desta entrega inclui busca de referências, inspeção da composição, comparação textual dos seis arquivos transferidos com a versão anterior e revisão do diff. Não houve imports, execução, instalação, build, consulta ao banco ou publicação. O funcionamento no IIS ainda precisa ser confirmado pelo responsável no escopo autorizado.

O sistema não foi executado; a validação foi somente estática. Este documento não comprova funcionamento no IIS, isolamento dos ambientes, persistência ou equivalência funcional do legado.

## 10. Registro da entrega 2

**Situação:** acesso geral próprio do backend ao TD implementado e conferido estaticamente. O banco corporativo aprovado é mantido. A verificação funcional, a capacidade do pool e a publicação no IIS permanecem pendentes de ambiente, janela e escopo autorizados.

### Composição e responsabilidades

```text
app/config.py
    ├── mantém Flask-SQLAlchemy e demais acessos antigos
    └── fornece o destino efetivo do TD para BackendConfig
            → backend/bootstrap.py
                → backend/platform/database.py
                    → engine/pool moderno único na aplicação
                        → EventsService
                        → próximos serviços modernos
```

| Arquivo | Responsabilidade |
| --- | --- |
| `backend/config.py` | `BackendConfig` recebe o destino do TD explicitamente e lê as opções próprias de pool do ambiente durante a composição. |
| `backend/platform/database.py` | `init_td_database(app, config)` cria o engine uma vez e o mantém em `app.extensions["backend_td_engine"]`. Uma segunda inicialização na mesma aplicação é recusada. |
| `backend/bootstrap.py` | `init_backend(app, config=...)` obtém o engine central, fornece-o ao serviço e registra os módulos. |
| `app/config.py` | Fornece `app.config["SQLALCHEMY_DATABASE_URI"]` ao backend; deixa de fornecer `db.engine` a Eventos. |

A origem do destino e das credenciais ainda é a configuração atual da aplicação, por uma ponte explícita. Essa dependência temporária evita copiar segredos ou alterar o banco aprovado; a configuração do pool e a criação do engine já pertencem ao backend. `backend/config.py` e a plataforma de banco não importam `app/config.py`, constantes de credenciais ou engines antigos. O destino não aparece na representação textual de `BackendConfig`.

Eventos continua sendo uma funcionalidade normal. Nenhuma configuração de banco é específica de Eventos. Para acrescentar outro módulo, seu serviço recebe o mesmo `td_engine` na composição; não se cria um engine dentro de suas rotas, serviço ou repositório.

### Opções do pool moderno

Todas as variáveis abaixo são opcionais e afetam somente o engine moderno. Sem defini-las, a configuração utiliza os padrões:

| Variável de ambiente | Padrão | Significado |
| --- | --- | --- |
| `BACKEND_TD_POOL_SIZE` | `5` | Máximo de conexões mantidas pelo pool; inteiro positivo. |
| `BACKEND_TD_MAX_OVERFLOW` | `0` | Conexões extras simultâneas; inteiro maior ou igual a zero. |
| `BACKEND_TD_POOL_TIMEOUT` | `30` | Segundos de espera por uma conexão disponível; inteiro positivo. |
| `BACKEND_TD_POOL_RECYCLE` | `1800` | Idade em segundos a partir da qual uma conexão é reciclada no próximo uso; inteiro positivo. |

O limite de conexões simultâneas do `QueuePool` é `POOL_SIZE + MAX_OVERFLOW`. O padrão permite até cinco por instância da aplicação, criadas conforme o uso; não abre cinco conexões na inicialização. Com uma instância por processo, quatro processos poderiam acrescentar até vinte conexões aos pools antigos. O número real de processos e a capacidade total não foram confirmados. Esse limite se refere ao pool SQLAlchemy; o pooling interno do driver pyodbc não foi alterado. Referência: [configuração de pools do SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/pooling.html#connection-pool-configuration).

Valores inválidos impedem a composição da aplicação com uma mensagem que identifica a opção, sem reproduzir seu valor. Não são aceitas opções que liberem um pool ilimitado. Como legado e moderno ainda compartilham a aplicação, uma configuração moderna inválida também impede a inicialização do portal; conferir as variáveis antes da publicação. Com todas ausentes, os padrões são utilizados.

`pool_pre_ping=True` permite verificar a conexão ao retirá-la do pool. `hide_parameters=True` oculta parâmetros SQL nas mensagens geradas pelo engine, mas não substitui cuidados com credenciais, URLs e logs da aplicação.

### Ciclo de vida e transações

Os módulos de configuração e banco definem classes e funções; não criam engines ao serem importados. A criação ocorre explicitamente no bootstrap e não faz consulta, migration ou `create_all()`. A conexão efetiva acontece quando o serviço utiliza `engine.connect()` ou `engine.begin()`, conforme o [contrato de `create_engine()`](https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.create_engine).

O engine permanece durante a vida da aplicação e não é descartado em cada request. As operações devolvem suas conexões ao pool ao sair dos contextos existentes. Na composição, registra-se `engine.dispose()` via `atexit` para liberar conexões ociosas no encerramento normal do processo; encerramentos forçados do IIS podem não executar esse callback. Esse mecanismo não controla o reinício do IIS e não fecha à força operações ainda em uso.

As consultas, URLs, contratos, sessão, permissões e CSRF de Eventos permanecem como antes. A leitura continua em `engine.connect()` e a criação em `engine.begin()`, com commit ou rollback no limite da operação. Conexões dos engines antigo e moderno não formam uma transação conjunta. Quando uma operação exigir atomicidade, seus repositórios devem receber a mesma conexão/transação.

O `db.create_all()` e os efeitos globais existentes da factory legada permanecem fora desta entrega. Separar o engine moderno não torna a inicialização completa da aplicação isolada dos recursos corporativos.

### Publicação e retorno

Preparar `backend/` completo, com `config.py` e `platform/`, e o `app/config.py` atualizado no mesmo pacote. As bibliotecas SQLAlchemy e pyodbc já são dependências existentes; esta entrega não altera `requirements.txt`. O frontend compatível, o shell, `main.py` e `web.config` mantêm os caminhos atuais. Não é necessário um novo build Vue nem definir variáveis para aceitar os padrões do pool.

Seguir a janela e o procedimento manual da seção 6.1. Antes da liberação, o responsável precisa verificar no ambiente autorizado o destino efetivo do TD, os processos do IIS, a disponibilidade do driver, os fluxos de Eventos e do legado e a adequação do limite adicional. Gravações e verificações de rollback exigem escopo explícito. Nenhuma dessas verificações foi executada pelo agente.

Para retornar especificamente da entrega 2, restaurar juntos `app/config.py` e o pacote `backend/` da versão anterior à entrega 2. Essa versão mantém Eventos em `backend/modules/events/`, mas volta a fornecer `db.engine` pela composição anterior, sem restaurar a chave de ativação removida. Não há conversão de schema ou dados.

### Validação desta entrega

A revisão estática confere a criação central do engine, os limites de configuração, a injeção em Eventos, a ausência de inicialização no import e de descarte por request, a preservação textual dos serviços/repositórios/rotas e o diff completo. Não houve instalação, import, execução, consulta, alteração de dados ou publicação.

**O sistema não foi executado; a validação foi somente estática.** O funcionamento e o dimensionamento no IIS dependem de verificação em ambiente autorizado.

## 11. Registro da entrega 3a

**Situação:** shell Vue compartilhado implementado no código e revisado estaticamente. Esta é uma parte da etapa 3; a verificação funcional e a publicação no IIS continuam pendentes de ambiente, janela e escopo autorizados.

### Responsabilidades e uso

`backend/platform/vue_shell.py` concentra a leitura de `app/static/app/.vite/manifest.json`, a resolução do JavaScript de entrada, a coleta dos estilos dos chunks importados e a renderização de `app/templates/app/shell.html`. Esses mecanismos saíram das rotas de Eventos e podem ser usados pelas próximas funcionalidades Vue.

Cada módulo continua responsável por registrar suas URLs, verificar sessão e permissões e fornecer seu mecanismo de token CSRF. Após essas verificações, chama `render_vue_shell(...)` com o título, a função que fornece o token e a mensagem de indisponibilidade. A plataforma não importa Eventos nem os mecanismos de permissão do legado.

Em Eventos, o fluxo fica:

```text
GET /app/eventos
    → events_shell.events_page
        → verifica sessão e permissão GENERAL
        → render_vue_shell(...)
            → lê manifesto e resolve assets
            → chama o provedor de token CSRF de Eventos
            → renderiza app/shell.html
                → navegador carrega o Vue e apresenta Eventos
```

O título passa a ser um parâmetro do template. Eventos fornece `Eventos | Digital JOST`, preservando o título anterior. A função de token é chamada somente depois de resolver os assets, como antes; uma falha na leitura do manifesto não cria um token de sessão adicional.

O contrato de CSRF permanece com `events_csrf` na sessão, a meta tag `csrf-token` no HTML e o cabeçalho `X-CSRF-Token` nas escritas da API. A extração do mecanismo de CSRF compartilhado será uma entrega própria. Não copiar esse mecanismo para o próximo módulo sem definir o contrato comum.

### Contratos preservados e limites

- `/app/` continua redirecionando para `/app/eventos` após as mesmas verificações de acesso.
- Os nomes `events`, `events_shell`, `events_shell.app_home` e `events_shell.events_page` e a API `/api/v1/events` permanecem iguais.
- O shell preserva a meta tag de CSRF, o ponto de montagem `#app`, a ordem dos estilos, o script de entrada e `Cache-Control: private, no-store` na resposta de sucesso.
- Falhas de manifesto tratadas anteriormente continuam retornando status 503 com `Aplicação de Eventos indisponível.`.
- O template e os assets permanecem nos caminhos atuais; a extração não altera o frontend, o banco, o pool, a inicialização legada ou os serviços e consultas de Eventos.
- O novo módulo não lê o manifesto nem renderiza templates durante o import; isso ocorre somente na chamada explícita da rota autorizada.

O shell oferece a renderização comum; as rotas do servidor continuam explícitas. Uma nova tela precisa de sua rota registrada no Flask, com sua autorização, e da rota correspondente no Vue. Esta entrega não cria um encaminhamento genérico para qualquer caminho `/app/`. O layout visual Vue em `frontend/src/app/layouts/AppShell.vue` já é compartilhado e permanece como está; ele é uma responsabilidade distinta do HTML inicial entregue pelo Flask.

### Publicação, retorno e validação

Preparar juntos `backend/platform/vue_shell.py`, `backend/modules/events/routes.py` e `app/templates/app/shell.html`, além do pacote completo previsto na seção 6.1. O título agora depende do valor fornecido pelo novo renderizador; misturar o template atualizado com as rotas anteriores pode produzir um título vazio. Não há nova dependência nem necessidade de novo build Vue por esta extração.

Para retornar desta entrega, restaurar juntos as rotas de Eventos e o template da versão anterior e o pacote `backend/` correspondente. O retorno mantém a infraestrutura de banco da entrega 2 e não exige alterações de schema ou dados.

A validação estática inclui comparação textual da função de leitura do manifesto antes/depois, conferência da ordem de autorização e geração de CSRF, busca dos consumidores do template e dos endpoints, comparação com o router e o cliente HTTP Vue, inspeção do diff e `git diff --check`. Não houve execução, build, import, conexão, consulta ou publicação.

No ambiente autorizado, confirmar acesso direto e redirecionamento de Eventos, carregamento de JavaScript/CSS, título, sessão e permissões, CSRF e comportamento diante de indisponibilidade do build. Qualquer gravação depende do escopo autorizado. A extração ainda não foi verificada no IIS.

**O sistema não foi executado; a validação foi somente estática.**
