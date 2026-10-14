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
| Interface compartilhada | Cabeçalho, campos, estados de requisição, paginação, cliente HTTP e mensagens de validação em `frontend/src/shared/`. |

Eventos oferece listagem paginada e cadastro: página `/app/eventos`, API `/api/v1/events` e tabela `dbo.DJ_EVENTS`. Ele serve como exemplo concreto de organização; suas regras e seus campos não são um modelo obrigatório para todo módulo.

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

Hoje `RolePermissions` consulta as permissões da **sessão corrente**. O `Actor` contém o identificador do usuário; não permite consultar ou representar livremente outro usuário. Em Eventos, `events.read` e `events.create` estão mapeadas para `GENERAL`; cada nova feature precisa escolher seus próprios critérios de acesso.

### Frontend

| Recurso existente | Como aproveitar |
|---|---|
| `requestJson` e `ApiError` | Centralizam JSON, sessão, envio de CSRF, timeout e erros HTTP. `api.ts` da feature continua definindo as operações e seus caminhos. |
| `PageHeader` | Título, descrição e ações da página. |
| `FormField` | Rótulo, erro e atributos de acessibilidade; o controle recebe os atributos fornecidos pelo componente. |
| `RequestState` | Estados de carregamento, erro e lista vazia. |
| `ListPagination` e `usePagination` | Controle e estado da página; API e estado usam páginas começando em 1. |
| `paginationQuery` e `PaginatedResponse` | Parâmetros e tipo da listagem. |
| `validationMessages` | Converte os detalhes de validação recebidos em mensagens de campo. |
| `src/volt/` e `shared/styles/tokens.css` | Controles visuais e estilos comuns já adotados. |

Os tipos TypeScript e schemas Python são mantidos manualmente; não há geração automática entre eles. A validação na interface ajuda o usuário, mas a validação e a autorização do backend continuam obrigatórias.

### Banco e configuração compartilhados

O TD moderno usa `DJ_TD_ODBC_CONNECTION_STRING`. Cada instância da aplicação tem uma engine com pool reutilizado pelos módulos: por padrão, até 5 conexões, sem conexões extras, espera de 30 segundos e reciclagem de 1.800 segundos. São limites por instância; mais processos significam mais pools. As opções ficam em `backend/config.py`.

O legado mantém seus próprios acessos ao TD e a outros bancos. Essa duplicidade temporária permite migrar sem trocar toda a infraestrutura de uma vez. Não há transação única que englobe automaticamente conexões antigas e novas.

O leitor `backend/platform/environment.py` é usado pelas duas arquiteturas. Ele lê o `.env` da raiz ou o arquivo absoluto selecionado por `DJ_ENV_FILE`, preservando a prioridade do ambiente do processo. Não copie credenciais para módulos, documentação ou variáveis frontend. Instalação, configuração e particularidades dos serviços estão no [README principal](../README.md).

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

Neste repositório, agentes fazem somente validação estática, conforme `AGENTS.md`. Testes, imports, builds e execução exigem autorização explícita de comando, ambiente e escopo. Não use o fallback de identidade fora do IIS como prova de autorização. Os mocks de Eventos ajudam na interface e não comprovam banco, sessão ou integrações.

### 8. Publicar uma entrega pequena

Quando autorizado, gere o build Vue e publique o conjunto compatível de backend e assets em `backend/static/app/`, incluindo `.vite/manifest.json`. O Git não leva o build automaticamente. Planeje dependências offline, processos afetados, conferência e retorno conforme o [README principal](../README.md).

Registre o que foi implementado e atualize este manual quando a base comum ou o processo mudar. Não publique uma ideia como funcionalidade existente.

## 7. Como migrar uma parte antiga

Escolha um domínio pequeno e mapeie todos os consumidores antes de substituir o fluxo. Uma tela pode compartilhar tabelas com jobs, relatórios, exports, notificações e outras rotas.

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
| 6 | Organizar integrações e rotinas conforme forem migradas | Criar adaptadores e casos de uso claros para integrações realmente utilizadas, sem reconfigurar todos os bancos corporativos agora. |
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

O código ativo é a referência para o estado implementado. Instalação e operação ficam no README principal; este documento concentra organização, desenvolvimento e evolução da arquitetura.
