# Base compartilhada para novas features

Esta entrega prepara os cinco pontos de simplificação e adapta Eventos como consumidor real. Não registra uma segunda feature nem altera tabelas. Código revisado somente como texto; funcionamento no PC/IIS e compilação Vue permanecem pendentes de verificação autorizada.

## 1. O que reutilizar

| Necessidade | Local | Responsabilidade da feature |
|---|---|---|
| Usuário e perfis atuais | `backend/compatibility/identity.py` | Definir o perfil e as ações permitidas |
| Identidade e autorização por ação | `backend/platform/identity.py` | Exigir a ação no serviço e, quando necessário, restringir registros |
| Sessão, permissão, CSRF e erros HTTP | `backend/platform/http.py`, `csrf.py` | Usar `configure_api` em cada API e `page_access` em cada página |
| Banco geral do TD | `backend/platform/database.py`, `bootstrap.py` | Receber o engine na composição, sem conexão própria por módulo |
| Paginação | `backend/platform/schemas.py` | Definir os modelos do item e das capacidades |
| Página Vue e assets | `backend/platform/vue_shell.py` | Fornecer título e mensagem de indisponibilidade |
| Cabeçalho, campo, estados e paginação | `frontend/src/shared/components/` | Fornecer textos, controles e conteúdo pelos slots |
| HTTP, consulta paginada e erros de campos | `frontend/src/shared/api/` | Definir endpoint, payload e tipos específicos |
| Estado de página | `frontend/src/shared/composables/usePagination.ts` | Escolher tamanho e momento de voltar à primeira página |

`RolePermissions` usa o perfil da sessão corrente por meio de um callback. O parâmetro `actor` mantém o contrato dos serviços e fornece o identificador do usuário; ele não consulta permissões de qualquer usuário arbitrário. Ações desconhecidas são negadas. Para autorização por registro, implemente uma política específica e verificações no serviço/repositório: `can_create` na interface é somente uma indicação.

A ponte reutiliza Flask-Login e Flask-Principal. Ela não adiciona autenticação, LDAP ou um segundo cadastro de usuários. Nenhum módulo moderno importa diretamente `app.utils.permissions`. A infraestrutura não cria conexões ou jobs ao ser importada; o engine continua sendo composto durante a inicialização existente.

## 2. Contratos preservados e transição

- Eventos mantém `/app/`, `/app/eventos`, `/api/v1/events`, os nomes dos blueprints/endpoints, acesso `GENERAL` e ações `events.read`/`events.create`.
- GET recebe `page` a partir de 1 e `per_page` entre 1 e 100, com padrão 12. A resposta mantém `items`, `page`, `per_page`, `total` e `capabilities`.
- POST recebe nome e descrição, mantém validação estrita, devolve 201 e usa a transação existente. Consultas, ordenação e tabela de Eventos não mudaram.
- Erros modernos usam `{ "message": "...", "detail": {} }`. Validação 422 preserva `detail.json`/`detail.query` fornecidos pelo APIFlask. Falhas 500 recebem mensagem genérica; `Allow` de 405 é preservado.
- A API verifica autenticação, perfil e CSRF nessa ordem. Escritas POST/PUT/PATCH/DELETE exigem `X-CSRF-Token`; GET não emite token. O shell só emite o token depois de localizar o build.
- O token comum fica em `backend_csrf`. Sessões existentes podem fornecer `events_csrf`; ambos são aceitos durante a transição. A chave antiga é mantida para compatibilidade com abas e retorno ao backend anterior. Não rotacionar a chave de sessão nesta entrega.
- A meta tag `csrf-token` e o cliente HTTP permanecem iguais. Não há chave de ativação de Eventos ou configuração de banco por feature.

Erros de roteamento 404/405 podem ocorrer antes de o Flask conhecer um blueprint. Por isso `app/errors.py` possui uma ponte limitada a `/api/v1` e `/api/v1/…`. Fora desse prefixo, os handlers HTML e a notificação de erro 500 do legado permanecem. A auditoria global existente não foi reformulada. Referência: [tratamento de erros e blueprints no Flask](https://flask.palletsprojects.com/en/stable/errorhandling/).

O handler moderno conserva o detalhe de validação utilizado pelos campos do formulário, conforme o [contrato de erros do APIFlask](https://apiflask.com/error-handling/). `PaginatedResponse` usa modelos genéricos do [Pydantic](https://docs.pydantic.dev/latest/concepts/models/#generic-models); os modelos concretos de Eventos continuam nomeados.

## 3. Passo a passo para outra feature

1. Definir URL, métodos, entrada/saída, perfis, ações e escopo dos registros. Confirmar tabelas existentes, jobs escritores e integrações. Criar/alterar schema exige autorização separada.
2. Criar `backend/modules/<feature>/` com `__init__.py`, `routes.py`, `schemas.py`, `services.py` e `repository.py` quando necessários. SQL parametrizado fica no repositório; regras e transações ficam no serviço; HTTP fica nas rotas.
3. Em `bootstrap.py`, compor o serviço com o mesmo `td_engine` e uma política de permissões. Guardá-lo em `app.extensions` com um nome próprio. Registrar explicitamente os blueprints em `backend/modules/__init__.py`.
4. Aplicar `configure_api` e `page_access`. Usar o shell comum, sem copiar configuração, geração de token ou leitura do manifest.
5. Criar `frontend/src/features/<feature>/` com API, tipos e página. Reutilizar os componentes conforme a necessidade. Registrar a rota Vue; para acesso direto e F5, registrar também a rota Flask correspondente e autorizar cada rota de entrada.
6. Usar o cliente HTTP existente. Preservar `retry: false` nas gravações e confirmar o POST antes de atualizar a lista; uma falha posterior na consulta não deve convidar a repetir uma gravação já concluída.
7. Revisar referências e diff estaticamente. Preparar build, publicação e validação funcional somente no ambiente e escopo explicitamente autorizados.

Não copiar `app/config.py`, credenciais, pool ou autenticação para a feature. Não criar classe base de CRUD, formulário gerado por schema ou arquivos vazios. Os componentes compartilhados cuidam da apresentação; as regras continuam explícitas.

## 4. Exemplo mínimo usando Eventos

Estes trechos documentam uma parte da feature já existente. Não acrescentar outro registro de Eventos ou substituir o módulo completo por este recorte de leitura.

### Backend: contrato e rota de leitura

```python
from apiflask import APIBlueprint
from backend.compatibility import identity
from backend.platform.http import configure_api, get_service
from .schemas import EventList, EventQuery

events_bp = APIBlueprint("events", __name__, url_prefix="/api/v1/events")
configure_api(events_bp, identity=identity, permission="GENERAL")

@events_bp.get("")
@events_bp.input(EventQuery, location="query")
@events_bp.output(EventList)
def list_events(query_data):
    return get_service("events_service").list(query_data, identity.current_actor())
```

O contrato usa `EventQuery(PaginationQuery)` e `EventList(PaginatedResponse[EventOut, EventCapabilities])`. O serviço concreto recebe o engine e `RolePermissions(identity.can_access, {"events.read": "GENERAL", "events.create": "GENERAL"})` na composição. A implementação completa está em [rotas](../backend/modules/events/routes.py), [schemas](../backend/modules/events/schemas.py), [serviço](../backend/modules/events/services.py), [repositório](../backend/modules/events/repository.py) e [bootstrap](../backend/bootstrap.py).

### Frontend: tela mínima de leitura

```vue
<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { usePagination } from '@/shared/composables/usePagination'
import PageHeader from '@/shared/components/PageHeader.vue'
import RequestState from '@/shared/components/RequestState.vue'
import ListPagination from '@/shared/components/ListPagination.vue'
import { eventsApi } from '../api'

const { page, perPage } = usePagination()
const { data, isPending, isError, error, refetch } = useQuery({
  queryKey: ['events', page],
  queryFn: () => eventsApi.list(page.value, perPage),
  retry: false,
})
</script>

<template>
  <section aria-labelledby="events-title">
    <PageHeader id="events-title" title="Eventos" />
    <RequestState :loading="isPending" :failed="isError" :error="error"
      :empty="data?.items.length === 0" loading-label="Carregando eventos…"
      empty-title="Nenhum evento cadastrado" empty-description="Os eventos aparecerão aqui."
      error-message="Não foi possível carregar os eventos."
      forbidden-message="Você não tem permissão para ver os eventos."
      not-found-message="Eventos não está disponível para seu acesso." @retry="refetch()">
      <ul><li v-for="item in data?.items ?? []" :key="item.id">{{ item.name }}</li></ul>
    </RequestState>
    <ListPagination v-if="!isPending && !isError && data" v-model:page="page"
      :per-page="perPage" :total="data.total" label="Páginas de eventos" />
  </section>
</template>
```

`RequestState` oferece textos padrão, que a feature pode substituir; o exemplo explicita os textos de Eventos. O slot `loading` permite personalizar o carregamento sem duplicar as decisões de sessão, erro e lista vazia.

Para campos, usar `FormField` com `id`, `label`, `error` e o slot `v-slot="{ controlProps }"`; aplicar `v-bind="controlProps"` ao InputText/Textarea. Isso associa label, controle e mensagem com os IDs corretos. `validationMessages(error.detail, ['name', 'description'] as const)` converte erros 422 para os campos conhecidos. Validação de tamanho, valores iniciais, foco e envio continuam na feature. Veja [EventForm](../frontend/src/features/events/components/EventForm.vue) e [EventsPage](../frontend/src/features/events/pages/EventsPage.vue), incluindo escrita, diálogo e carregamento customizado. Referência: [slots do Vue](https://vuejs.org/guide/components/slots.html).

## 5. Arquivos e publicação desta entrega

Publicar a versão compatível do backend e frontend como conjunto, sobre a configuração privada já provisionada. Não é necessário novo pacote de dependências; os manifests de dependências não foram alterados.

Arquivos Python novos:

- `backend/compatibility/__init__.py`
- `backend/compatibility/identity.py`
- `backend/platform/identity.py`
- `backend/platform/csrf.py`
- `backend/platform/http.py`
- `backend/platform/schemas.py`

Arquivos Python adaptados:

- `app/errors.py`
- `backend/bootstrap.py`
- `backend/platform/vue_shell.py`
- `backend/modules/events/routes.py`
- `backend/modules/events/schemas.py`

Fonte Vue/TypeScript nova:

- `frontend/src/shared/api/pagination.ts`
- `frontend/src/shared/api/validation.ts`
- `frontend/src/shared/composables/usePagination.ts`
- `frontend/src/shared/components/PageHeader.vue`
- `frontend/src/shared/components/FormField.vue`
- `frontend/src/shared/components/RequestState.vue`
- `frontend/src/shared/components/ListPagination.vue`

Fonte Vue/TypeScript adaptada:

- `frontend/src/features/events/api.ts`
- `frontend/src/features/events/types.ts`
- `frontend/src/features/events/pages/EventsPage.vue`
- `frontend/src/features/events/components/EventForm.vue`

Documentação: este guia, `README.md` e seção 16 de `docs/plano-separacao-backend-legado.md`.

**Esta entrega precisa de novo build Vue.** No procedimento autorizado do PC, o comando habitual `npm run build:local` em `frontend/` produz `backend/static/app/`. Copiar o diretório inteiro, inclusive `.vite/manifest.json` e assets correspondentes, junto com os arquivos Python acima. Git não transfere os assets ignorados. O agente não executou esse comando nem publicou arquivos no servidor.

Riscos principais: arquivo novo ausente no pacote, backend/frontend de versões diferentes ou incompatibilidade que a análise textual não detecte. Preparar retorno ao pacote anterior completo, incluindo seu build. O alias `events_csrf` é mantido para compatibilidade de sessão; não exige alteração do banco ou das credenciais.

## 6. Conferências funcionais pendentes

Somente o responsável, em ambiente e escopo autorizados, pode executar os casos abaixo; cadastros usam o TD corporativo e precisam de dados aprovados.

| Caso | Resultado esperado |
|---|---|
| Portal/Jinja e login existentes | Mesma navegação e respostas HTML de erro |
| Entrada e F5 em `/app/eventos` | Shell autorizado, assets completos e formulário utilizável |
| API sem sessão / sem GENERAL | 401 / 403 JSON, antes de consultar o banco |
| Escrita sem token / token incorreto | 400 JSON antes da gravação |
| Sessão anterior, abas existentes e novo shell | Token anterior e comum aceitos durante a transição |
| Payload inválido com token válido | 422; mensagens nos campos correspondentes |
| Query com página 0 ou tamanho maior que 100 | 422 de validação, sem consulta |
| API desconhecida / método não registrado | 404 / 405 JSON; 405 preserva Allow |
| Lista vazia, carregando, falha e várias páginas | Textos, estados, repetição manual e índice correto |
| Cadastro autorizado | 201, feedback, retorno à página 1 e atualização da lista |
| Erro ao atualizar a lista depois de salvar | Gravação não repetida automaticamente |
| Diálogo e formulário | Foco, labels, erros, bloqueio durante envio e retorno do foco |

CSRF aqui cobre as APIs modernas configuradas. Proteção dos formulários antigos, correções de autenticação/flags, correlação, revisão da auditoria e demais itens de [segurança](revisao-seguranca-modernizacao.md) continuam pendentes; mudar a organização não elimina esses riscos.

**O sistema não foi executado; a validação foi somente estática.**
