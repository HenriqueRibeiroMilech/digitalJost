> **Registro histórico.** Pode conter decisões, caminhos e comandos superados. Consulte o [manual atual](../../README.md); este arquivo não define o padrão vigente.

# Base compartilhada para novas features

Guia atual para desenvolver módulos modernos com consultas diretas, gravações simples na rota e Services funcionais quando necessários. Eventos e Demandas consomem a mesma base. A simplificação foi aplicada no código sem mudar tabelas ou contratos; a equivalência funcional no PC/IIS permanece pendente de verificação autorizada. O [plano consolidado](plano-simplificacao-arquitetura.md) registra critérios, adaptação e limites.

## 1. O que reutilizar

| Necessidade | Local | Responsabilidade da feature |
|---|---|---|
| Usuário e perfis atuais | `backend/compatibility/identity.py` | Definir o perfil e as ações permitidas |
| Identidade e autorização por ação | `backend/platform/identity.py` | Exigir a ação no Service ou na rota simples; restringir registros nos casos de uso |
| Sessão, permissão, CSRF e erros HTTP | `backend/platform/http.py`, `csrf.py` | Usar `configure_api` em cada API e `page_access` em cada página |
| Banco geral do TD | `backend/platform/database.py`, `bootstrap.py` | Obter `get_td_engine()` na rota e fornecer o engine ao Service quando existir |
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
- POST de Eventos recebe nome, descrição, tipo, início e fim, com instrutor e conteúdo programático opcionais; mantém validação estrita, devolve 201 e usa a transação existente. Consultas, ordenação e tabelas não mudaram nesta simplificação.
- Tipos de Eventos e colaboradores elegíveis de Demandas são consultados diretamente nas rotas, preservando respectivamente `events.read` e `demands.create`. As demais operações usam Services funcionais com dependências explícitas.
- Erros modernos usam `{ "message": "...", "detail": {} }`. Validação 422 preserva `detail.json`/`detail.query` fornecidos pelo APIFlask. Falhas 500 recebem mensagem genérica; `Allow` de 405 é preservado.
- A API verifica autenticação, perfil e CSRF nessa ordem. Escritas POST/PUT/PATCH/DELETE exigem `X-CSRF-Token`; GET não emite token. O shell só emite o token depois de localizar o build.
- O token comum fica em `backend_csrf`. Sessões existentes podem fornecer `events_csrf`; ambos são aceitos durante a transição. A chave antiga é mantida para compatibilidade com abas e retorno ao backend anterior. Não rotacionar a chave de sessão nesta entrega.
- A meta tag `csrf-token` e o cliente HTTP permanecem iguais. Não há chave de ativação de Eventos ou configuração de banco por feature.

Erros de roteamento 404/405 podem ocorrer antes de o Flask conhecer um blueprint. Por isso `app/errors.py` possui uma ponte limitada a `/api/v1` e `/api/v1/…`. Fora desse prefixo, os handlers HTML e a notificação de erro 500 do legado permanecem. A auditoria global existente não foi reformulada. Referência: [tratamento de erros e blueprints no Flask](https://flask.palletsprojects.com/en/stable/errorhandling/).

O handler moderno conserva o detalhe de validação utilizado pelos campos do formulário, conforme o [contrato de erros do APIFlask](https://apiflask.com/error-handling/). `PaginatedResponse` usa modelos genéricos do [Pydantic](https://docs.pydantic.dev/latest/concepts/models/#generic-models); os modelos concretos de Eventos continuam nomeados.

## 3. Passo a passo para outra feature

1. Definir URL, métodos, entrada/saída, perfis, ações e escopo dos registros. Confirmar tabelas existentes, jobs escritores e integrações. Criar/alterar schema exige autorização separada.
2. Criar `backend/modules/<feature>/` com `__init__.py`, `routes.py`, `schemas.py` e `repository.py` quando necessários. Classificar cada operação: consulta simples, gravação simples ou caso de uso. Acrescentar `services.py` somente para casos de uso.
3. Manter o mapa de ações no módulo, compor `RolePermissions` na entrada HTTP e obter o engine por `get_td_engine()`. Registrar os blueprints em `backend/modules/__init__.py`. Não criar nem registrar objetos de Service no bootstrap; integrações novas podem exigir composição explícita própria.
4. Aplicar `configure_api` e `page_access`. Usar o shell comum, sem copiar configuração, geração de token ou leitura do manifest.
5. Criar `frontend/src/features/<feature>/` com API, tipos e página. Reutilizar os componentes conforme a necessidade. Registrar a rota Vue; para acesso direto e F5, registrar também a rota Flask correspondente e autorizar cada rota de entrada.
6. Usar o cliente HTTP existente. Preservar `retry: false` nas gravações e confirmar o POST antes de atualizar a lista; uma falha posterior na consulta não deve convidar a repetir uma gravação já concluída.
7. Revisar referências e diff estaticamente. Preparar build, publicação e validação funcional somente no ambiente e escopo explicitamente autorizados.

Gravação simples não coordena várias gravações, arquivos, integrações, transições ou regras de negócio além dos campos e da ação; não exige autorização por registro, concorrência especial ou idempotência; e não precisa ser reutilizada por outra entrada. A rota abre a transação. Se algum critério não for atendido, usar Service funcional com a transação e as verificações do caso de uso. GET também pode precisar de Service.

SQL fica sempre no Repository, recebendo a conexão da operação, sem Flask ou commit próprio. Não copiar `app/config.py`, credenciais, pool ou autenticação para a feature. Não criar classe base de CRUD, formulário gerado por schema ou arquivos vazios. Os componentes compartilhados cuidam da apresentação; as regras continuam explícitas.

Quando várias rotas repetirem as mesmas dependências de Service, usar um helper local e opcional `_service_deps()` em `routes.py`. Ele retorna somente as dependências comuns daquele módulo; `**_service_deps()` as passa como argumentos nomeados. Manter `identity.current_actor()` visível na chamada e fornecer LDAP, armazenamento e outras dependências especiais separadamente, apenas onde necessários. Chamar o helper durante a requisição, sem guardar seu resultado globalmente. Consultas diretas ao Repository continuam usando seus recursos diretamente; não criar um helper compartilhado ou um executor genérico de Services.

## 4. Exemplo mínimo usando Eventos

Estes trechos documentam uma parte da feature já existente. Não acrescentar outro registro de Eventos ou substituir o módulo completo por este recorte de leitura.

### Backend: contrato e rota de leitura

```python
from apiflask import APIBlueprint
from backend.compatibility import identity
from backend.platform.database import get_td_engine
from backend.platform.http import configure_api
from backend.platform.identity import RolePermissions
from . import services
from .schemas import EventList, EventQuery

events_bp = APIBlueprint("events", __name__, url_prefix="/api/v1/events")
configure_api(events_bp, identity=identity, permission="GENERAL")

# Recorte do mapa completo existente em routes.py.
ACTION_ROLES = {
    "events.read": "GENERAL", "events.create": "GENERAL",
    "events.update": "GENERAL", "events.delete": "GENERAL",
}

def _permissions():
    return RolePermissions(identity.can_access, ACTION_ROLES)

def _service_deps():
    return {"engine": get_td_engine(), "permissions": _permissions()}

@events_bp.get("")
@events_bp.input(EventQuery, location="query")
@events_bp.output(EventList)
def list_events(query_data):
    return services.list_events(
        query_data, identity.current_actor(), **_service_deps(),
    )
```

O contrato usa `EventQuery(PaginationQuery)` e `EventList(PaginatedResponse[EventOut, EventCapabilities])`. O mapa completo de Eventos, inclusive update/delete e presença, permanece em `routes.py`; não substituir esse mapa pelo recorte. A listagem de tipos é uma consulta direta ao Repository na mesma rota, sem Service. A implementação completa está em [rotas](../../../backend/modules/events/routes.py), [schemas](../../../backend/modules/events/schemas.py), [Services funcionais](../../../backend/modules/events/services.py), [repositório](../../../backend/modules/events/repository.py) e [bootstrap](../../../backend/bootstrap.py).

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
  queryFn: () => eventsApi.list(page.value, perPage, { search: '', statuses: ['upcoming', 'ongoing'] }),
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

Para campos, usar `FormField` com `id`, `label`, `error` e o slot `v-slot="{ controlProps }"`; aplicar `v-bind="controlProps"` ao InputText/Textarea. Isso associa label, controle e mensagem com os IDs corretos. `validationMessages(error.detail, ['name', 'description'] as const)` converte erros 422 para os campos conhecidos. Validação de tamanho, valores iniciais, foco e envio continuam na feature. Veja [EventForm](../../../frontend/src/features/events/components/EventForm.vue) e [EventsPage](../../../frontend/src/features/events/pages/EventsPage.vue), incluindo escrita, diálogo e carregamento customizado. Referência: [slots do Vue](https://vuejs.org/guide/components/slots.html).

## 5. Registro histórico da entrega da base compartilhada

A lista abaixo registra a entrega original da base, que modificou o Vue e exigiu build. Para a simplificação atual, a relação de arquivos e o procedimento estão no registro da seção 17 do [plano de separação](plano-separacao-backend-legado.md). A conversão dos Services não altera o frontend nem exige novo build por si só.

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

## 7. Exemplo mínimo completo de consulta e gravação simples

Este exemplo é somente documentação. Não existe um módulo ativo `equipment` nem a tabela fictícia `dbo.EXAMPLE_EQUIPMENT`. Não copiar o registro para a aplicação nem criar objetos no banco como parte da simplificação. Uma funcionalidade real exige definição e autorização próprias para dados, permissões e eventual schema.

O exemplo pressupõe uma tabela independente com identificador gerado pelo banco, nome e autoria, sem validação de vínculos, unicidade de nome, histórico transacional, arquivos, integrações ou regra de estado. Não haverá outro consumidor do cadastro. O campo de nome deve caber na coluna definida para a funcionalidade, inclusive considerando a representação Unicode do SQL Server. Essas condições permitem mostrar a gravação direta; se mudarem, reavaliar o uso de Service.

### Arquivos do exemplo

```text
backend/modules/equipment/
├── __init__.py
├── routes.py
├── schemas.py
└── repository.py
```

Em `schemas.py`, declarar o contrato público e reaproveitar a paginação:

```python
from pydantic import BaseModel, ConfigDict, Field
from backend.platform.schemas import PaginatedResponse


class EquipmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)
    name: str = Field(min_length=1, max_length=80, pattern=r"^[^\x00]+$")


class EquipmentOut(BaseModel):
    id: int
    name: str


class EquipmentCapabilities(BaseModel):
    can_create: bool


class EquipmentList(PaginatedResponse[EquipmentOut, EquipmentCapabilities]):
    pass
```

Em `repository.py`, receber a conexão, parametrizar valores e retornar somente os campos necessários:

```python
from sqlalchemy import text


def list_equipment(connection, *, page, per_page):
    total = connection.execute(
        text("SELECT COUNT(*) FROM dbo.EXAMPLE_EQUIPMENT")
    ).scalar_one()
    rows = connection.execute(text("""
        SELECT id, name FROM dbo.EXAMPLE_EQUIPMENT
        ORDER BY id DESC OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """), {"offset": (page - 1) * per_page, "limit": per_page}).mappings().all()
    return [dict(row) for row in rows], total


def create_equipment(connection, *, name, created_by):
    row = connection.execute(text("""
        INSERT INTO dbo.EXAMPLE_EQUIPMENT (name, created_by)
        OUTPUT inserted.id, inserted.name
        VALUES (:name, :created_by)
    """), {"name": name, "created_by": created_by}).mappings().one()
    return dict(row)
```

Em `routes.py`, configurar a segurança uma vez no blueprint. `GENERAL` é o perfil ilustrativo usado aqui; uma feature real deve definir o acesso adequado. As ações desconhecidas continuam negadas:

```python
from apiflask import APIBlueprint
from backend.compatibility import identity
from backend.platform.database import get_td_engine
from backend.platform.http import configure_api
from backend.platform.identity import RolePermissions
from backend.platform.schemas import PaginationQuery
from . import repository
from .schemas import EquipmentCreate, EquipmentList, EquipmentOut


ACTION_ROLES = {"equipment.read": "GENERAL", "equipment.create": "GENERAL"}
equipment_bp = APIBlueprint("equipment", __name__, url_prefix="/api/v1/equipment")
configure_api(equipment_bp, identity=identity, permission="GENERAL")


def _permissions():
    return RolePermissions(identity.can_access, ACTION_ROLES)


@equipment_bp.get("")
@equipment_bp.input(PaginationQuery, location="query")
@equipment_bp.output(EquipmentList)
def list_equipment(query_data):
    actor = identity.current_actor()
    permissions = _permissions()
    permissions.require(actor, "equipment.read")
    with get_td_engine().connect() as connection:
        items, total = repository.list_equipment(
            connection, page=query_data.page, per_page=query_data.per_page,
        )
    return {
        "items": items, "total": total,
        "page": query_data.page, "per_page": query_data.per_page,
        "capabilities": {"can_create": permissions.can(actor, "equipment.create")},
    }


@equipment_bp.post("")
@equipment_bp.input(EquipmentCreate)
@equipment_bp.output(EquipmentOut, status_code=201)
def create_equipment(json_data):
    actor = identity.current_actor()
    _permissions().require(actor, "equipment.create")
    # Uma gravação independente; o Repository não faz commit próprio.
    with get_td_engine().begin() as connection:
        item = repository.create_equipment(
            connection, name=json_data.name, created_by=str(actor.id),
        )
    return item
```

Em `__init__.py`, exportar apenas o blueprint:

```python
from .routes import equipment_bp
```

O ponto único de registro seria `backend/modules/__init__.py`. Dentro de `register_modules(app)`, acrescentar o import e o registro abaixo, preservando Eventos e Demandas. Este registro também é somente ilustrativo:

```python
from .equipment import equipment_bp
app.register_blueprint(equipment_bp)
```

Não há objeto de Service para construir ou registrar no bootstrap. O engine já existe; `configure_api` fornece autenticação, perfil, CSRF e tratamento HTTP. Os schemas validam entradas e saídas, e a rota continua exigindo a ação. O exemplo não converte automaticamente falhas SQL em conflitos: constraints e regras adicionais de uma feature real precisam de tratamento explícito, com Service quando os critérios exigirem.

Uma tela Vue reutilizaria o cliente HTTP para GET/POST e o shell já existente para obter o token CSRF. Para entrada direta, a feature acrescentaria sua rota Flask com `page_access` e `render_vue_shell`, além da rota Vue. O cadastro mostrado é uma API documentada, sem tela ou tabela criadas por esta entrega.

## 8. Quando acrescentar Service

Se o cadastro passar a conferir vínculos, alterar vários registros, guardar histórico na mesma transação, tratar anexos ou atender um job, mover o caso de uso para uma função de `services.py`. A rota fornece identidade e dependências; não chama outra rota para reaproveitar regras.

Eventos já exemplifica esse caminho. O cadastro valida horário e existência do tipo, usa o horário do TD e devolve o evento na transação. A rota chama:

```python
return services.create_event(
    json_data, identity.current_actor(), **_service_deps(),
)
```

Eventos e Demandas reúnem engine e permissões em `_service_deps()` local. Demandas acrescenta armazenamento somente à criação e ao download; Eventos acrescenta o diretório somente ao registro de presença. Esses adaptadores são compostos uma vez no bootstrap e recuperados na entrada HTTP, sem entrar no dicionário de dependências comuns. Os Services não importam contexto Flask, e classes dos adaptadores continuam existindo.

**O sistema não foi executado; a validação foi somente estática.**
