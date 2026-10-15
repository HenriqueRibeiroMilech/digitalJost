# Arquitetura modernizada do Digital JOST

Este documento explica a organização atual e o caminho para criar e migrar funcionalidades com menos repetição e menor risco.

## 1. Objetivo e direção

A modernização deve facilitar o desenvolvimento sem interromper o Digital JOST. A ideia é entregar uma funcionalidade por vez, com responsabilidades claras e uma base comum pequena, que possa crescer conforme necessidades reais.

As decisões que orientam o trabalho são:

- Manter o legado funcionando enquanto novas telas e regras são entregues.
- Concentrar o Python moderno em `backend/` e a interface Vue em `frontend/`.
- Compartilhar banco, segurança HTTP e elementos de interface quando houver uma responsabilidade comum.
- Manter regras específicas próximas da feature, para que uma alteração seja fácil de localizar.
- Reutilizar algo existente antes de criar outra implementação; extrair novas abstrações quando elas simplificarem usos concretos.
- Revisar segurança e comportamento ao migrar, preservando os contratos ainda necessários.
- Aproveitar alterações em partes antigas para migrar os componentes relacionados quando houver benefício, baixo/moderado risco e autorização para esse escopo.

O resultado esperado é que uma feature nova precise principalmente de seus dados, regras e interface. Login, conexão geral ao TD, CSRF, tratamento básico de erros e componentes comuns já têm uma base para reaproveitar.

## 2. Como está hoje

```text
Navegador
  → IIS e autenticação Windows
  → aplicação Flask criada por app/config.py
      ├─ app/: rotas e páginas antigas, usuários, integrações e jobs
      └─ backend/: shell Vue e APIs modernas
          → serviço da feature → repositório → banco TD

frontend/: código Vue → build → backend/static/app/
```

Ainda existe **uma aplicação Flask compartilhada**. A separação em pastas permite evoluir as partes aos poucos; não representa dois sistemas independentes em produção.

| Área | Estado implementado |
|---|---|
| Entrada e aplicação | `main.py` e `app/config.py` continuam responsáveis pelo app e pelo ciclo global. A factory chama `backend/bootstrap.py`. |
| Backend moderno | `backend/modules/` reúne os módulos; Eventos é o primeiro. O registro dos blueprints é explícito. |
| Frontend moderno | Vue/TypeScript com Vue Router, TanStack Query, Tailwind e componentes PrimeVue/Volt. |
| Shell compartilhado | `backend/platform/vue_shell.py` carrega o manifest do build e entrega o template base com o token CSRF. O layout visual fica em `frontend/src/app/layouts/AppShell.vue`. |
| Banco | Engine/pool geral do TD em `backend/platform/database.py`, separado dos mecanismos antigos. |
| Identidade | A ponte `backend/compatibility/identity.py` usa a sessão e os perfis antigos. Não há outro login ou cliente LDAP moderno. |
| Infraestrutura HTTP | Guardas de acesso, CSRF e erros JSON em `backend/platform/`, aplicados à API de Eventos. |
| Interface compartilhada | Cabeçalho, grade e cards de registros, campos, estados de requisição, paginação, cliente HTTP e mensagens de validação em `frontend/src/shared/`. |

Eventos oferece listagem paginada com pesquisa por título e filtro de status, cadastro, detalhes, edição e exclusão: página `/app/eventos`, API `/api/v1/events` e tabela `dbo.DJ_EVENTS`. Clicar no cartão abre os detalhes em um diálogo composto sobre Volt; as ações de editar e excluir ficam no topo, e a exclusão pede confirmação. A interface usa diretamente essa API em desenvolvimento e no build publicado, pelo cliente HTTP compartilhado. Ele serve como exemplo concreto de organização; suas regras e seus campos não são um modelo obrigatório para todo módulo.

O cadastro e a edição exigem `name`, `description`, `starts_at` e `ends_at`. As datas são strings ISO 8601 com data e hora, sem fuso (`2026-10-15T14:30:00.000`), representando o horário local informado para o evento. O serviço exige fim posterior ao início. O DatePicker Volt usa formato brasileiro e relógio de 24 horas, sem converter o valor para UTC. Eventos antigos podem ter ambas as datas nulas e aparecem com “Não informado”; ao editar, é necessário preencher o período.

Além de `GET`/`POST /api/v1/events`, o módulo expõe `GET`, `PUT` (edição completa) e `DELETE /api/v1/events/<id>`. Os detalhes retornam as capacidades da sessão; o DELETE retorna JSON com o `id` excluído. Eventos ausentes retornam 404. Escritas reaproveitam o CSRF comum e transações da engine TD. Não há novas integrações ou jobs neste fluxo.

A listagem aceita `search` (trecho literal do título, até 120 caracteres) e `status` (valores separados por vírgulas). O padrão da API e da tela é `upcoming,ongoing`. Para consultar todos, envie `upcoming,ongoing,completed,unscheduled`; na interface, desmarcar todos os status equivale a essa seleção. Pesquisa e status são combinados antes de contar e paginar, mantendo a ordenação por ID decrescente. A busca respeita a collation existente do TD; `%`, `_` e `[` digitados são tratados como texto. Status inválidos ou vazios retornam 422.

`EventOut` retorna `status`, calculado no repositório por um único `CASE` compartilhado entre lista, detalhes e retorno das escritas. A referência de horário vem de `SYSDATETIME()` do SQL Server TD, lida uma vez por operação e reaproveitada na contagem e nos itens. As datas locais cadastradas precisam usar essa mesma referência. Os valores são `upcoming` (antes do início), `ongoing` (início inclusivo até fim exclusivo), `completed` (fim atingido) e `unscheduled` (período ausente). O status não é armazenado nem editado manualmente e não exige migration ou job adicional. A interface apresenta o status retornado, sem recalculá-lo pelo relógio do navegador.

Lista e detalhes são atualizados a cada 60 segundos enquanto a aba está ativa; a lista pausa com o modal aberto, e os detalhes pausam durante edição, confirmação de exclusão ou uso da aba de presença. Alterar filtros reinicia a página, e a paginação se ajusta quando o total diminui. Salvar mantém os filtros atuais: um evento pode sair da seleção ao mudar de período. API e build precisam ser publicados juntos para entregar o campo `status` e os novos filtros.

**Publicação desta evolução:** o responsável pelo banco precisa revisar e aplicar `database/migrations/20261015_add_dj_events_schedule.sql` após a criação de `DJ_EVENTS` e antes de publicar a API e o build compatíveis. O arquivo adiciona as duas colunas anuláveis e a restrição do período, sem inventar datas para registros antigos. A aplicação não executa a migração. O retorno de código pode manter essas colunas, pois o código anterior não as utiliza.

Eventos também possui a aba **Listas de presença**, com várias listas por evento e registro de matrícula pelo leitor. A implementação permanece no módulo de Eventos, com contratos e validação em `schemas.py`, autorização/transações no serviço e SQL no repositório. `attendanceApi.ts` e os componentes locais de presença compõem Tabs, DataTable e Dialog Volt existentes. A aba de presença é carregada sob demanda; os componentes Volt instalados não foram modificados.

As rotas ficam sob `/api/v1/events/<event_id>/attendance-lists`: GET/POST na coleção, GET em `/<list_id>` e GET/POST em `/<list_id>/entries`. Consultas são paginadas; o serviço verifica o vínculo evento/lista. As ações `events.attendance.read`, `.create` e `.register` usam o perfil GENERAL nesta etapa e são verificadas no backend. A tela para convidados usa a sessão autenticada do responsável, com o mesmo CSRF das demais escritas.

A matrícula é uma string de exatamente 12 dígitos ASCII, preservando zeros à esquerda. A API devolve `{item, created}` somente após o commit; uma repetição na mesma lista retorna o registro existente com `created: false`. Uma trava da lista na transação serializa registros concorrentes; a restrição UNIQUE também protege `(list_id, registration)`. Nome e setor são anuláveis, ficam vazios no cadastro e não têm integração externa nesta etapa. As novas tabelas e sua publicação estão documentadas em [Listas de presença](listas-de-presenca.md); o script SQL é uma proposta e não foi executado pelo agente ou pelo startup da aplicação.

### O que ainda depende do legado

Login, usuários, perfis, sessão, extensões Flask, handlers globais e serviços Windows continuam ligados a `app/`. A criação da aplicação ainda chama `db.create_all()`, e há imports antigos com threads e acesso externo. Essas dependências também podem afetar uma tela Vue.

Por isso, novas regras de negócio devem evitar imports diretos de rotas e utilitários antigos. Quando a dependência for necessária, use uma ponte explícita, como a de identidade atual, e registre o que ela precisa fornecer.

## 3. Organização e responsabilidade dos arquivos

Estrutura inicial recomendada para uma feature moderna:

```text
backend/modules/<feature>/
├── __init__.py              # Exporta os blueprints
├── routes.py                # HTTP, schemas, acesso e chamada do serviço
├── schemas.py               # Contratos de entrada e saída
├── services.py              # Casos de uso, regras, autorização e transações
└── repository.py            # SQL e acesso aos dados

frontend/src/features/<feature>/
├── pages/                   # Composição da tela e carregamento de dados
├── components/              # Componentes específicos desta feature
├── api.ts                   # Operações HTTP do domínio
└── types.ts                 # Tipos usados pela interface
```

| Responsabilidade | Onde fica e como deve funcionar |
|---|---|
| Receber uma requisição | `routes.py` traduz HTTP, aplica os recursos comuns e chama o serviço. Não concentra SQL ou regras extensas. |
| Validar o contrato | `schemas.py` define tipos, campos, limites e formatos. Regras dependentes do estado do negócio ficam no serviço. |
| Executar uma ação | `services.py` decide o que pode acontecer, exige a permissão da ação e controla a transação. Recebe dependências pela composição. |
| Consultar ou gravar | `repository.py` recebe a conexão, usa SQL parametrizado e devolve dados. Não conhece Flask, sessão ou interface. |
| Mostrar a tela | A página Vue coordena consulta, formulário e feedback. Componentes locais representam partes específicas do domínio. |
| Compartilhar infraestrutura | `backend/platform/`, `frontend/src/shared/`, layout e componentes Volt existentes. |
| Adaptar o legado | `backend/compatibility/`, com uma dependência delimitada e visível. |

Crie `domain.py`, `integration.py` ou composables locais somente quando houver conteúdo que justifique essa separação. Não é necessário criar arquivos vazios, classes para toda função ou uma camada adicional para apenas repassar argumentos.

## 4. O que já podemos reutilizar

### Backend

| Recurso existente | Como aproveitar |
|---|---|
| `BackendConfig` e engine TD | A composição entrega a engine ao serviço. O módulo não cria outra configuração ou outro pool para o mesmo TD. |
| `Actor` e `RolePermissions` | Identificam o usuário da sessão e mapeiam ações do domínio para perfis existentes. |
| `configure_api` e `page_access` | Aplicam acesso à API e à página. O serviço também exige a permissão específica da operação. |
| `get_csrf_token` e `has_valid_csrf` | Mantêm a proteção comum das operações de escrita; o shell fornece o token e o cliente HTTP o envia. |
| `api_error` e validação APIFlask/Pydantic | Mantêm respostas JSON e detalhes de validação por campo. |
| `PaginationQuery` e `PaginatedResponse` | Padronizam paginação; cada módulo define seus itens e capacidades. |
| `render_vue_shell` | Entrega a página base e os assets. A feature informa título e mensagem de indisponibilidade após autorizar o acesso. |

Hoje `RolePermissions` consulta as permissões da **sessão corrente**. O `Actor` contém o identificador do usuário; não permite consultar ou representar livremente outro usuário. Em Eventos, `events.read`, `events.create`, `events.update` e `events.delete` estão mapeadas para `GENERAL`; cada nova feature precisa escolher seus próprios critérios de acesso. As capacidades orientam a interface, e cada ação também exige a respectiva permissão no serviço.

### Frontend

| Recurso existente | Como aproveitar |
|---|---|
| `requestJson` e `ApiError` | Centralizam JSON, sessão, envio de CSRF, timeout e erros HTTP. `api.ts` da feature continua definindo as operações e seus caminhos. |
| `PageHeader` | Título, descrição, identificação opcional da área (`eyebrow`) e ações da página. |
| `CardGrid` e `RecordCard` | Grade responsiva de até quatro colunas e apresentação comum dos registros, composta sobre o Card Volt. A feature fornece seus dados e ações. |
| `AppDialog` | Diálogo composto sobre Volt, com título acessível, subtítulo, ícone, tom visual, rodapé e bloqueio de fechamento durante gravações. |
| `FormField` | Rótulo, erro e atributos de acessibilidade; o controle recebe os atributos fornecidos pelo componente. |
| `RequestState` | Estados de carregamento, erro e lista vazia. |
| `ListPagination` e `usePagination` | Controle e estado da página; API e estado usam páginas começando em 1. |
| `paginationQuery` e `PaginatedResponse` | Parâmetros e tipo da listagem. |
| `validationMessages` | Converte os detalhes de validação recebidos em mensagens de campo. |
| `src/volt/`, `shared/styles/tokens.css` e `shared/styles/layout.css` | Controles Volt, cores, tipografia, bordas, sombras, largura e grade comuns. |

Os tipos TypeScript e schemas Python são mantidos manualmente; não há geração automática entre eles. A validação na interface ajuda o usuário, mas a validação e a autorização do backend continuam obrigatórias.

O [padrão visual](padrao-visual.md) documenta a base aplicada em Eventos: conteúdo até 1.760 px, margens laterais adaptáveis e quatro cards por linha em janelas a partir de 1.200 px. Novas telas devem compor essa base, mantendo informações e regras de cada domínio na respectiva feature. A aplicação desse padrão ao Gerenciador de Demandas ainda é uma etapa futura.

Os tons `brand`, `success`, `neutral` e `danger` em `shared/styles/layout.css` fornecem cores consistentes para superfícies. `RecordCard` recebe somente um tom visual; a feature de Eventos escolhe esse tom a partir do status da API, por `statuses.ts` e `EventStatusBadge`. Os componentes compartilhados não calculam status de negócio.

Para adicionar um componente Volt em um computador de desenvolvimento autorizado, execute na pasta `frontend/` o comando `npx volt-vue add NomeDoComponente`; por exemplo, `npx volt-vue add DatePicker`. Revise os arquivos gerados em `frontend/src/volt/` e reutilize-os na feature. Consulte a [documentação do Volt](https://volt.primevue.org/datepicker/) para as opções do componente. Esse procedimento não autoriza agentes a instalar dependências ou executar o projeto.

O DatePicker local aceita `inputProps` para associar erros e atributos de acessibilidade ao input interno, preservando as classes do Volt. Use `input-id` para ligar o controle ao rótulo de `FormField`.

### Banco e configuração compartilhados

O TD moderno usa `DJ_TD_ODBC_CONNECTION_STRING`. Cada instância da aplicação tem uma engine com pool reutilizado pelos módulos: por padrão, até 5 conexões, sem conexões extras, espera de 30 segundos e reciclagem de 1.800 segundos. São limites por instância; mais processos significam mais pools. As opções ficam em `backend/config.py`.

O legado mantém seus próprios acessos ao TD e a outros bancos. Essa duplicidade temporária permite migrar sem trocar toda a infraestrutura de uma vez. Não há transação única que englobe automaticamente conexões antigas e novas.

O leitor `backend/platform/environment.py` é usado pelas duas arquiteturas. Ele lê o `.env` da raiz ou o arquivo absoluto selecionado por `DJ_ENV_FILE`, preservando a prioridade do ambiente do processo. Não copie credenciais para módulos, documentação ou variáveis frontend. A preparação local e a configuração privada estão no [README principal](../README.md); as particularidades dos serviços, no guia de [servidor e publicação](servidor-e-publicacao.md).

## 5. Quando compartilhar e quando manter local

**Reutilização deve reduzir o trabalho de entender e alterar o sistema.** Antes de criar uma implementação, procure se a base atual já atende. Se o comportamento for específico da feature, comece dentro dela.

| Situação | Decisão recomendada |
|---|---|
| Nova tela precisa de loading, campo com erro ou paginação | Reutilize os recursos compartilhados existentes. |
| Formulário tem campos e regras próprios de um domínio | Mantenha-o na feature, compondo controles comuns. |
| Uma segunda feature repete o mesmo comportamento | Compare os usos e extraia a parte comum quando a interface ficar mais simples. |
| Duas regras parecem semelhantes, mas mudam por motivos diferentes | Mantenha-as separadas; semelhança de código não significa a mesma responsabilidade. |
| Componente exige muitas opções para atender casos muito diferentes | Preserve um componente menor ou mantenha implementações locais. |
| Surge uma integração real com outro sistema | Crie um adaptador com responsabilidade clara; compartilhe-o quando houver consumidores concretos. |

Por exemplo: `FormField` é compartilhável porque a associação entre rótulo, controle e erro se repete. `EventForm` permanece local porque seus campos e regras pertencem a Eventos.

Não precisamos de um CRUD universal, repositório genérico, sistema automático de plugins ou biblioteca própria para cada utilitário. A infraestrutura comum pode existir desde o início, como o pool geral do TD; as abstrações de negócio devem nascer dos casos reais.

## 6. Passo a passo para criar uma feature

### 1. Definir a primeira entrega

Descreva quem usa a funcionalidade, quais ações existem, quais dados entram e saem, permissões e critérios de conclusão. Identifique tabelas, arquivos, integrações e jobs envolvidos. Para uma migração, rastreie também os métodos e comportamentos da tela antiga.

Se o trabalho tocar uma parte antiga, avalie a oportunidade de migração descrita na seção 7 antes de ampliar sua implementação no legado.

Comece com um fluxo pequeno que possa ser entregue e conferido de ponta a ponta. Não adicione edição, exclusão, filtros ou exportações apenas porque poderão ser úteis depois.

### 2. Desenhar o contrato

Escolha as URLs da página e da API, os schemas e o formato das respostas. No padrão atual, a página fica em `/app/<pagina>` e a API em `/api/v1/<recurso>`.

Para listas paginadas, use `page` e `per_page`, com resposta `items`, `page`, `per_page`, `total` e `capabilities`. O padrão atual começa na página 1, usa 12 itens e limita `per_page` a 100. Defina uma ordenação estável e aplique os mesmos filtros e limites de acesso na contagem e nos itens.

As capacidades, como `can_create`, orientam os botões da interface. Elas não substituem a verificação no serviço. O autor de uma gravação vem da identidade validada no servidor, não de um identificador enviado pelo navegador.

### 3. Implementar dados e regras

Crie o módulo seguindo a divisão da seção 3. Use a conexão entregue ao repositório e parâmetros para os valores SQL. No serviço, uma escrita pode usar o padrão atual `with engine.begin()`: a transação agrupa a operação e é revertida se ocorrer exceção.

Quando houver várias gravações que precisem ser atômicas, mantenha-as na mesma conexão/transação. E-mail ou chamada externa não fazem parte da transação SQL; defina o tratamento de falha e repetição antes de automatizá-los. Alterações de tabela exigem planejamento e autorização próprios, sem DDL durante imports.

### 4. Compor e registrar o backend

Em `backend/bootstrap.py`, construa o serviço com a engine geral e o mapa de ações/perfis; registre-o em `app.extensions` com nome próprio. Em `routes.py`, reutilize `configure_api`, os schemas, `get_service` e a ponte de identidade.

Exporte os blueprints em `__init__.py` e registre-os em `backend/modules/__init__.py`. Para a página, use `page_access` e `render_vue_shell`. Não crie outro shell, login ou seletor de ambiente para cada módulo.

### 5. Construir a interface

Crie `types.ts`, `api.ts`, página e os componentes necessários dentro da feature. Use `requestJson` para as chamadas e os componentes comuns para os comportamentos já cobertos. Prefira TanStack Query para dados remotos e estado local Vue para formulário e interação.

A chave de uma consulta deve incluir os parâmetros que alteram o resultado, como página e filtros. Após uma escrita confirmada, atualize ou invalide a consulta correspondente. Uma falha ao atualizar a lista não transforma a gravação concluída em falha; não repita um cadastro automaticamente quando o resultado estiver incerto.

Trate carregamento, vazio, falha, salvamento e validação de campos. Preserve rótulos, foco, navegação por teclado, feedback e bloqueio de envio duplicado enquanto a operação estiver em andamento. Não exiba SQL, traceback ou detalhes internos ao usuário.

### 6. Integrar a navegação

Adicione a rota em `frontend/src/router/index.ts`, cuja base é `/app/`. Adicione também a rota Flask que entrega o shell no caminho completo, para abrir diretamente e atualizar com F5. A rota Vue sozinha não fornece essa resposta do servidor.

Defina o ponto de entrada no portal ou na navegação necessária e mantenha a autorização no backend. O registro dos módulos não gera menus automaticamente. Preserve as URLs antigas enquanto houver consumidores que dependam delas.

### 7. Revisar e preparar a validação

Confira o fluxo completo: entrada na tela, acesso, contrato, regras, transação, SQL, resposta e atualização da interface. Inclua falhas e usuários sem permissão; não confira apenas o caminho de sucesso.

Neste repositório, agentes fazem somente validação estática, conforme `AGENTS.md`. Testes, imports, builds e execução exigem autorização explícita de comando, ambiente e escopo. Não use o fallback de identidade fora do IIS como prova de autorização.

### 8. Publicar uma entrega pequena

Quando autorizado, gere o build Vue e publique o conjunto compatível de backend e assets em `backend/static/app/`, incluindo `.vite/manifest.json`. O Git não leva o build automaticamente. Planeje dependências offline, processos afetados, conferência e retorno conforme o guia de [servidor e publicação](servidor-e-publicacao.md).

Registre o que foi implementado e confira se este manual precisa de atualização pelos critérios da seção 10. Não publique uma ideia como funcionalidade existente.

## 7. Como migrar uma parte antiga

Escolha um domínio pequeno e mapeie todos os consumidores antes de substituir o fluxo. Uma tela pode compartilhar tabelas com jobs, relatórios, exports, notificações e outras rotas.

### Aproveitar oportunidades durante outras mudanças

Ao alterar uma conexão, integração, rotina, configuração ou regra antiga, a preferência é levar a parte relacionada para a arquitetura nova quando a migração for pequena, útil e de baixo/moderado risco. Essa orientação vale para qualquer componente; não é necessário esperar uma reescrita completa do domínio.

Antes de incluir a migração, delimite o componente, identifique seus consumidores, avalie o impacto na publicação e defina como preservar o funcionamento antigo e retornar se necessário. A mudança deve reaproveitar a base moderna e permanecer próxima do trabalho solicitado. Dependências fora desse escopo podem continuar temporariamente no legado.

Por exemplo: se uma tarefa exigir mexer no acesso ao banco Jost Integration, avalie migrar a configuração e o acesso para a camada moderna adequada a esse destino, compartilhada pelos consumidores que precisarem dela. Se telas ou jobs antigos ainda dependerem desse acesso, preserve uma ponte de compatibilidade durante a transição. Isso não significa mudar o banco, suas tabelas ou credenciais, nem usar a engine do TD para um destino diferente.

**Para trabalho por IA, a migração precisa estar no escopo solicitado ou já autorizado pelo usuário.** Se a oportunidade ampliar esse escopo, apresente a mudança, o benefício e os impactos e obtenha autorização antes de implementá-la. Uma sugestão registrada neste documento não é autorização para executar a migração.

Se houver impacto alto, dependências desconhecidas ou falta de condições para validar, mantenha o funcionamento necessário no legado e registre a oportunidade na seção 8, com o motivo do adiamento. Isso permite concluir a tarefa autorizada e planejar a migração separadamente.

### Concluir uma migração

1. Registre o comportamento e as permissões que precisam continuar funcionando.
2. Implemente a nova parte usando a base comum, preservando as dependências ainda necessárias por adaptadores claros.
3. Defina qual fluxo é responsável por cada escrita durante a transição; evite duas rotinas automáticas executando a mesma ação.
4. Confira o caminho novo e os consumidores antigos em ambiente autorizado, com uma forma de retornar.
5. Retire a implementação antiga apenas após buscar referências e confirmar que seus consumidores foram atendidos.

A migração pode usar as tabelas existentes. Separar pastas não exige mudar schema, credenciais, serviços ou bancos corporativos na mesma entrega. Cada mudança deve ter seu próprio motivo, escopo e validação.

## 8. Melhorias futuras e ideias

**Os itens abaixo são propostas; este documento não os implementa.** A ordem favorece entregas pequenas que reduzam dependências e facilitem a próxima feature.

| Ordem sugerida | Melhoria | Benefício e limite inicial |
|---|---|---|
| 1 | Entregar uma segunda feature com a base atual | Verificar o que realmente se repete e ajustar componentes/contratos a partir de dois usos reais. |
| 2 | Preparar testes isolados e configuração de desenvolvimento | Testar regras com dependências substituídas, sem inicializar o portal nem atingir recursos corporativos. A base atual ainda não garante esse isolamento. |
| 3 | Controlar os efeitos de inicialização | Retirar gradualmente consultas/threads de imports e planejar mudanças de schema fora do startup. Exige revisar factory, integrações e serviços. |
| 4 | Evoluir permissões e pontes com o legado | Reduzir a dependência da sessão corrente nos serviços e explicitar regras por ação e, quando necessário, por registro. Preservar os perfis existentes durante a transição. |
| 5 | Melhorar diagnóstico e publicação | Padronizar logs sem segredos, identificar a versão publicada e tornar o pacote offline e o retorno mais previsíveis. |
| 6 | Migrar componentes relacionados às partes que forem alteradas | Aproveitar mudanças em conexões, integrações, rotinas e configurações para levar o acesso ou comportamento à base moderna, com baixo/moderado risco e escopo autorizado. Preservar consumidores antigos e tratar migrações maiores separadamente. |
| 7 | Revisar segurança em cada domínio migrado | SQL parametrizado, acesso a arquivos, CSRF, autorização e tratamento de erros. Externalização não substitui rotação de segredos e tratamento de histórico/backups. |
| 8 | Avaliar automações que economizem trabalho | Geração de tipos a partir de contratos, modelo de feature ou catálogo de navegação somente quando a repetição justificar o custo de manter a ferramenta. |

Separar totalmente a criação do app, a identidade e a hospedagem do legado pode ser um objetivo posterior. Isso depende das migrações anteriores; não é requisito para continuar entregando features agora.

## 9. O que uma entrega deve deixar claro

- Quais comportamentos foram entregues e quais continuam pendentes.
- Onde ficam página, API, regras, dados e permissões.
- Quais recursos existentes foram reaproveitados e por que algo novo virou compartilhado.
- Quais tabelas, arquivos, integrações e serviços foram afetados.
- Como foi validada, o que depende do ambiente e como publicar ou retornar.
- Quais decisões precisam ser atualizadas neste manual.

O código ativo é a referência para o estado implementado. A preparação local fica no README principal; a operação, no guia de servidor e publicação. Este documento concentra organização, desenvolvimento e evolução da arquitetura.

## 10. Quando e como atualizar este documento

Ao concluir uma mudança na arquitetura nova, confira se ela altera algo descrito aqui. **Atualize o documento quando necessário para que continue representando a arquitetura e suas orientações.**

- Atualize as seções afetadas quando mudarem responsabilidades, organização, dependências com o legado, conexões, contratos compartilhados, permissões, recursos reutilizáveis ou o processo de desenvolvimento.
- Preserve os trechos que continuam corretos. Uma correção local ou detalhe interno de uma feature não exige alterar o guia se a descrição arquitetural permanecer válida. Evite reescrever ou reorganizar o arquivo inteiro sem necessidade.
- Acrescente novas propostas pertinentes à lista da seção 8, com objetivo, benefício e limite inicial. Se o assunto já estiver na lista, complemente o item existente para evitar duplicação. Uma ideia continua identificada como proposta até ser implementada.
- Quando uma proposta for entregue, atualize a descrição do estado atual e retire da lista futura somente o que foi concluído. Preserve as partes ainda pendentes e ajuste a prioridade quando houver motivo.

Este guia acompanha as decisões e a evolução da arquitetura; detalhes de cada alteração ficam no histórico do Git. A revisão deve ser proporcional à mudança, mantendo o documento claro e útil para a próxima pessoa que for desenvolver.
