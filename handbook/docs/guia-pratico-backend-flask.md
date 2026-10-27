# Backend Flask na prática: entender e desenvolver no Digital JOST

## Objetivo

Este guia explica o backend moderno no formato das anotações de `curso_notion`: primeiro o conceito, depois o código e, em seguida, o que cada parte faz.

Ao terminar, você deve conseguir:

- Localizar a implementação de uma funcionalidade.
- Distinguir um schema Pydantic de um modelo ORM.
- Entender uma rota que consulta ou grava no banco.
- Acrescentar um endpoint usando os recursos existentes.
- Saber quais cuidados preservar ao modificar Demandas ou Eventos.

Os exemplos identificados como **implementação atual** vêm do código do projeto, com ajustes de formatação para leitura. O **exercício** é uma sugestão de implementação; sua rota não foi adicionada ao sistema por este documento.

O guia trata de `backend/` e de sua ligação com o Vue. O legado em `app/` continua existindo. Preparação do ambiente e publicação ficam no [guia de servidor](servidor-e-publicacao.md). Os exemplos são material de estudo; não autorizam executar o sistema ou consultar o banco. As regras operacionais estão em [AGENTS.md](../../AGENTS.md).

---

## 1. Ligando o curso ao nosso projeto

No curso, uma função Flask recebe a requisição, valida os dados, aplica as regras e acessa o MongoDB. No backend moderno, essa sequência continua visível na rota. O acesso ao SQL Server é feito principalmente com o ORM do SQLAlchemy.

**ORM** significa mapeamento entre objetos e tabelas: escrevemos operações usando classes Python, e o SQLAlchemy produz as instruções SQL correspondentes.

| O que você viu no curso | Como aparece aqui |
|---|---|
| `create_app()` monta a aplicação | A factory está em `app/config.py` e chama o bootstrap moderno. |
| Blueprint agrupa as rotas | Cada feature exporta seus blueprints e os registra explicitamente. |
| Classes Pydantic validam dados | Essas classes ficam em `schemas.py`. |
| `find()`, `find_one()` e inserções do MongoDB | Usamos `select()`, `session.execute()`, `session.add()` e outras operações ORM. |
| A rota contém a sequência da operação | `routes.py` reúne HTTP, regras, autorização e acesso ORM. |
| Autenticação com JWT no exemplo do curso | Reutilizamos a sessão e a identidade do portal, com proteção CSRF nas escritas. |

Não precisamos recriar login, conexão de banco ou uma aplicação Flask para cada funcionalidade. Essa base já está preparada.

### Uma diferença importante no nome “model”

No curso, `Product` era um modelo **Pydantic**. Aqui usamos nomes de arquivos diferentes para duas responsabilidades:

| Arquivo | Pergunta que responde | Exemplo |
|---|---|---|
| `schemas.py` | Quais dados esta API recebe ou devolve? | O cadastro recebe `name`; a resposta devolve `id` e `name`. |
| `models.py` | Como os dados estão armazenados no SQL Server? | A tabela também guarda `created_by` e `created_at`. |

Uma classe Pydantic não grava no banco. Uma classe ORM não define sozinha o que o navegador pode enviar ou receber.

---

## 2. Como a aplicação está montada

### 2.1. Organização atual

```text
backend/
├── __init__.py              # prepara recursos e registra os módulos
├── config.py                # contratos de configuração do backend
├── shared/
│   ├── database.py          # Base ORM, sessões, paginação e pesquisa
│   ├── http.py              # permissões HTTP, CSRF e respostas de erro
│   ├── identity.py          # sessão do portal, Actor e RolePermissions
│   ├── schemas.py           # contratos comuns de paginação
│   ├── environment.py       # leitura da configuração privada
│   ├── employee_directory.py # consulta de funcionários
│   └── vue_shell.py         # entrega a página que carrega o Vue
├── web/
│   ├── templates/app/shell.html # HTML processado pelo Flask
│   └── static/app/          # destino do build Vue; ignorado pelo Git
└── modules/
    ├── events/
    │   ├── __init__.py
    │   ├── routes.py
    │   ├── schemas.py
    │   ├── models.py
    │   └── attendance_pdf.py
    └── demands/
        ├── __init__.py
        ├── routes.py
        ├── schemas.py
        ├── models.py
        └── storage.py
```

**Feature** é uma funcionalidade ou área do sistema, como Eventos ou Demandas. A ideia é encontrar os arquivos relacionados dentro da mesma pasta.

A regra para localizar o código é: funcionalidades em `modules/`, recursos comuns em `shared/` e arquivos para entregar a interface em `web/`. `__init__.py` e `config.py` ficam na raiz como pontos de inicialização e configuração. As funções de identidade reutilizam a sessão do portal, e as funções de CSRF ficam junto da proteção HTTP.

| Arquivo de uma feature | Responsabilidade |
|---|---|
| `__init__.py` | Disponibilizar os blueprints para o registro. |
| `routes.py` | Receber a requisição, conferir acesso, aplicar regras, consultar/gravar e preparar a resposta. |
| `schemas.py` | Declarar entradas, saídas, tipos e validações dos campos. |
| `models.py` | Representar tabelas existentes com SQLAlchemy. |
| `storage.py`, em Demandas | Validar e guardar anexos privados, localizar arquivos e compensar falhas previstas. |
| `attendance_pdf.py`, em Eventos | Gerar o documento de presença. |

Os quatro primeiros são a base para uma feature com persistência. Arquivos extras surgem quando há uma responsabilidade concreta. Não há obrigação de criar `services.py`, `repository.py` ou `domain.py`.

### 2.2. Quem registra as rotas?

O fluxo de composição pode ser lido assim:

```text
main.py
  → create_app(), em app/config.py
    → init_backend(), em backend/__init__.py
      → prepara banco, integrações e shell Vue
      → register_modules(), em backend/modules/__init__.py
        → registra os blueprints modernos
```

Em [backend/modules/__init__.py](../../backend/modules/__init__.py), o registro atual é explícito:

```python
def register_modules(app):
    from .events import events_bp, events_shell_bp
    from .demands import demands_bp, demands_shell_bp

    app.register_blueprint(events_bp)
    app.register_blueprint(events_shell_bp)
    app.register_blueprint(demands_bp)
    app.register_blueprint(demands_shell_bp)
```

Criar um arquivo com rotas não basta. O blueprint precisa chegar a esse registro. Para os módulos modernos, esse é o ponto a alterar; o registro legado em `main.py` permanece separado.

### 2.3. Página e API têm funções diferentes

| Endereço atual | O que entrega |
|---|---|
| `/app/eventos` | Página que carrega a aplicação Vue. |
| `/api/v1/events` | JSON da API de Eventos. |
| `/app/demandas/solicitacoes` | Página de solicitações no Vue. |
| `/api/v1/demands` | JSON da API de solicitações. |

A rota Flask da página permite abrir o endereço diretamente ou atualizar com F5. O Vue Router escolhe a tela, e a tela busca os dados na API.

---

## 3. Schemas: definindo o que entra e o que sai

Vamos usar **tipos de evento** como exemplo. São opções usadas no cadastro dos eventos.

**Implementação atual**, em [events/schemas.py](../../backend/modules/events/schemas.py):

```python
from pydantic import BaseModel, ConfigDict, Field


class EventTypeCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, strict=True,
    )

    name: str = Field(min_length=1, max_length=80)


class EventTypeOut(BaseModel):
    id: int
    name: str
```

### Entendendo cada parte

- `BaseModel`: base do Pydantic, como no curso.
- `name: str`: o nome precisa ser um texto.
- `Field(...)`: estabelece os limites do campo.
- `str_strip_whitespace=True`: remove espaços nas pontas antes da validação.
- `extra="forbid"`: rejeita campos que não pertencem à entrada.
- `strict=True`: exige os tipos previstos, evitando conversões permissivas.
- `EventTypeCreate`: descreve a entrada do cadastro.
- `EventTypeOut`: descreve os campos públicos da resposta.

Exemplo ilustrativo de entrada:

```json
{"name": "Treinamento"}
```

Exemplo ilustrativo de saída:

```json
{"id": 7, "name": "Treinamento"}
```

O navegador não escolhe `id`, `created_by` ou `created_at` nessa operação. ID e data vêm do banco; a autoria vem da identidade autenticada.

---

## 4. Models: representando uma tabela existente

**Implementação atual**, em [events/models.py](../../backend/modules/events/models.py):

```python
from datetime import datetime

from sqlalchemy import Integer, func
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from backend.shared.database import Base


class EventType(Base):
    __tablename__ = "DJ_EVENT_TYPES"
    __table_args__ = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        NVARCHAR(80, collation="Latin1_General_100_CI_AS"),
    )
    created_by: Mapped[str] = mapped_column(NVARCHAR(128))
    created_at: Mapped[datetime] = mapped_column(
        DATETIME2(precision=3), server_default=func.sysutcdatetime(),
    )
```

### Entendendo cada parte

| Trecho | Significado |
|---|---|
| `EventType(Base)` | Usa a base ORM moderna, separada do legado. |
| `__tablename__` | Nome real da tabela. |
| `schema="dbo"` | Schema ao qual a tabela pertence. |
| `Mapped[str]` | Atributo Python mapeado como texto. |
| `mapped_column(...)` | Detalhes da coluna no banco. |
| `primary_key=True` | Identifica a chave primária. |
| `autoincrement=True` | O banco gera o ID. |
| `NVARCHAR(80)` | Texto Unicode com o tamanho declarado no banco. |
| `collation=...` | Mantém as regras de comparação reais dessa coluna. |
| `server_default=...` | Informa o default aplicado pelo banco na inserção. |

`Mapped[str | None]` representa um atributo que pode ser nulo nos mapeamentos atuais. Os tipos e a nulabilidade precisam acompanhar a estrutura real do banco.

**Mapear uma tabela não cria nem modifica essa tabela.** Não usamos `create_all()` nem reflexão automática no backend moderno. Uma mudança de estrutura requer um trabalho separado de banco, com revisão e autorização.

---

## 5. Preparando o Blueprint e suas permissões

Este é um **recorte da implementação atual** de [events/routes.py](../../backend/modules/events/routes.py). O mapa completo contém outras ações:

```python
from apiflask import APIBlueprint

from backend.shared import identity
from backend.shared.http import action_access, configure_api
from backend.shared.identity import RolePermissions


ACTION_ROLES = {
    "events.read": "GENERAL",
    "events.types.create": "GENERAL",
    "events.types.delete": "GENERAL",
}

permissions = RolePermissions(identity.can_access, ACTION_ROLES)
require_action = action_access(identity=identity, permissions=permissions)

events_bp = APIBlueprint("events", __name__, url_prefix="/api/v1/events")
configure_api(events_bp, identity=identity, permission="GENERAL")
```

- `APIBlueprint`: agrupa rotas e oferece a integração de entrada/saída usada aqui.
- `url_prefix`: início comum dos endereços desse blueprint.
- `configure_api`: aplica autenticação, perfil, CSRF e tratamento comum de erros.
- `ACTION_ROLES`: relaciona uma ação da funcionalidade com o perfil necessário.
- `require_action`: produz o decorator que confere a ação em cada requisição.

O mapa não guarda o usuário atual. A identidade é consultada durante a requisição. Uma ação ausente do mapa é negada.

O perfil responde “pode usar esta ação?”. A regra por registro responde “pode acessar esta solicitação específica?”. Em Demandas, essa segunda conferência também considera área e vínculo de solicitante ou contribuinte.

---

## 6. Consultando dados na rota

### 6.1. Listagem real de tipos de evento

**Implementação atual**, com os imports usados pelo exemplo:

```python
from sqlalchemy import select

from backend.shared.database import get_td_session_factory

from .models import EventType
from .schemas import EventTypes


@events_bp.get("/types")
@require_action("events.read")
@events_bp.output(EventTypes)
def list_event_types():
    sessions = get_td_session_factory()
    with sessions() as session:
        items = session.execute(
            select(EventType.id, EventType.name)
            .order_by(EventType.name, EventType.id)
        )
        result = {"items": [dict(row) for row in items.mappings()]}
    actor = identity.current_actor()
    return {
        **result,
        "can_create": permissions.can(actor, "events.types.create"),
        "can_delete": permissions.can(actor, "events.types.delete"),
    }
```

O endereço completo é `GET /api/v1/events/types`: prefixo do blueprint mais caminho da rota.

### 6.2. Entendendo a consulta

1. `get_td_session_factory()` obtém a fábrica de sessões já preparada pela aplicação.
2. `with sessions() as session` abre uma sessão para essa consulta e a fecha ao sair do bloco.
3. `select(EventType.id, EventType.name)` descreve os campos desejados.
4. `order_by(...)` estabelece a ordem dos resultados.
5. `session.execute(...)` executa a consulta.
6. `.mappings()` permite acessar cada linha pelos nomes dos campos.
7. `dict(row)` transforma a linha em um dicionário comum.
8. A resposta é preparada dentro do bloco e devolvida depois de fechar a sessão.

Esta expressão:

```python
{"items": [dict(row) for row in items.mappings()]}
```

equivale, na construção da lista, a:

```python
public_items = []
for row in items.mappings():
    public_items.append(dict(row))
result = {"items": public_items}
```

As capacidades `can_create` e `can_delete` ajudam a tela a mostrar suas ações. O backend continua conferindo a permissão quando a ação é chamada.

### 6.3. Pesquisa e paginação

Nas listagens paginadas, reutilizamos os recursos de [shared/database.py](../../backend/shared/database.py):

```python
# Fragmento para uma consulta de tipos: pressupõe session e query_data.
statement = select(EventType.id, EventType.name).where(
    EventType.name.like(literal_contains(query_data.search), escape="~"),
).order_by(EventType.id.desc())

result = paginate(session, statement, query_data)
```

Esse fragmento precisa dos imports de `literal_contains` e `paginate`. O schema de `query_data` deve fornecer `search`, `page` e `per_page`; pode herdar de `PaginationQuery`, como `EventQuery` faz hoje.

`literal_contains` trata `%`, `_` e outros caracteres de pesquisa como texto literal. O `escape="~"` faz parte do uso do helper. `paginate` retorna `items`, `total`, `page` e `per_page`; a feature acrescenta as capacidades exigidas pelo seu schema de saída.

A consulta entregue ao helper já deve conter os filtros de acesso e uma ordenação estável. O helper espera uma seleção de campos ou projeção, como a do exemplo.

---

## 7. Gravando dados sem Service e Repository

### 7.1. Cadastro real de um tipo

**Implementação atual**; utiliza o blueprint e os recursos apresentados acima, além dos schemas `EventTypeCreate` e `EventTypeOut`:

```python
@events_bp.post("/types")
@require_action("events.types.create")
@events_bp.input(EventTypeCreate)
@events_bp.output(EventTypeOut)
def create_event_type(json_data):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        existing = session.execute(
            select(EventType.id, EventType.name)
            .where(EventType.name == json_data.name)
            .with_hint(EventType, "WITH (UPDLOCK, HOLDLOCK)", "mssql")
        ).mappings().one_or_none()
        if existing is not None:
            result = dict(existing)
        else:
            event_type = EventType(
                name=json_data.name,
                created_by=str(identity.current_actor().id),
            )
            session.add(event_type)
            session.flush()
            result = EventTypeOut.model_validate(
                event_type, from_attributes=True,
            ).model_dump()
    return result
```

### 7.2. O que os decorators fazem?

| Decorator | Responsabilidade |
|---|---|
| `@events_bp.post("/types")` | Define método e caminho. |
| `@require_action(...)` | Confere a permissão da ação. |
| `@events_bp.input(EventTypeCreate)` | Valida o JSON e fornece `json_data` à função. |
| `@events_bp.output(EventTypeOut)` | Serializa a resposta conforme o contrato público. |

Em uma entrada por query string, usamos `location="query"` e recebemos `query_data`. Para multipart, como no cadastro de Demandas, o código valida explicitamente o JSON do campo `payload`.

### 7.3. Entendendo a gravação

1. `sessions.begin()` abre a sessão e delimita a transação.
2. A consulta verifica se o nome já existe.
3. `UPDLOCK, HOLDLOCK` preserva a coordenação entre cadastros concorrentes, junto da chave única do banco.
4. Se já existir, devolvemos a opção existente. Esse comportamento é intencional.
5. Caso contrário, criamos um objeto `EventType` e obtemos a autoria da sessão autenticada.
6. `session.add()` coloca o objeto sob controle da sessão.
7. `session.flush()` envia a inserção ao banco e disponibiliza o ID gerado.
8. `model_validate(..., from_attributes=True)` lê os atributos da entidade ORM usando o schema público.
9. `model_dump()` prepara um dicionário antes de encerrar a sessão.
10. A saída bem-sucedida do bloco confirma a transação; depois devolvemos o resultado.

### Flush não é commit

| Operação | Efeito |
|---|---|
| `session.add(objeto)` | Registra uma entidade para persistência. |
| `session.flush()` | Envia alterações pendentes, ainda sujeitas a rollback. |
| Saída normal de `sessions.begin()` | Confirma a transação. |
| Exceção em `sessions.begin()` | Desfaz a transação SQL. |

Os auxiliares recebem a mesma sessão e não fazem commits próprios. Não precisamos criar outra classe apenas para repassar a chamada da rota ao banco.

---

## 8. Atualização, exclusão e erros

### 8.1. Atualização real de uma lista de presença

**Implementação atual** em Eventos. Os imports e a configuração do blueprint já existem em `routes.py`; `update` vem de `sqlalchemy`:

```python
@events_bp.put("/<int:event_id>/attendance-lists/<int:list_id>")
@require_action("events.attendance.update")
@events_bp.input(AttendanceListCreate)
@events_bp.output(AttendanceListOut)
def update_attendance_list(event_id, list_id, json_data):
    sessions = get_td_session_factory()
    with sessions.begin() as session:
        _attendance_list(session, event_id, list_id, lock=True)
        session.execute(update(AttendanceList).where(
            AttendanceList.id == list_id,
            AttendanceList.event_id == event_id,
        ).values(name=json_data.name))
        result = _attendance_list(session, event_id, list_id)
    return result
```

`_attendance_list` é um auxiliar local: confere o vínculo com o evento, prepara a projeção da lista e pode aplicar trava. A atualização também filtra pelo evento. O helper usa a sessão recebida, mantendo consulta e alteração na mesma transação.

### 8.2. Exclusão também tem regras

Na exclusão atual de um tipo de evento, a rota confere a existência sob trava, verifica se algum evento o utiliza e só então executa `delete(...).returning(EventType.id)`. Tipo em uso retorna `409`.

Não basta trocar uma consulta por `delete()`: é necessário conservar os vínculos, as regras e as consequências das FKs. Veja a função `delete_event_type` em [events/routes.py](../../backend/modules/events/routes.py).

### 8.3. Erros esperados com ApiProblem

```python
from backend.shared.http import ApiProblem

# Exemplos de falhas esperadas dentro de uma operação.
raise ApiProblem(404, "Tipo de evento não encontrado.")
```

`configure_api` traduz esse erro para status `404` e corpo:

```json
{"message": "Tipo de evento não encontrado.", "detail": {}}
```

Para indicar um campo específico, usamos o formato já consumido pela interface:

```python
raise ApiProblem(422, detail={"json": {
    "contributor_id": ["Selecione outra pessoa ativa com e-mail corporativo."],
}})
```

| Status | Situação típica no backend moderno |
|---|---|
| 400 | Requisição inválida ou falha de CSRF. |
| 401 | Sessão ausente ou expirada. |
| 403 | Ação sem permissão. |
| 404 | Recurso inexistente ou fora do acesso permitido. |
| 409 | Conflito, como versão desatualizada ou tipo em uso. |
| 422 | Dados inválidos. |
| 413 / 503 | Envio excedido / dependência indisponível, conforme a operação. |

Erros inesperados não devem ser transformados em sucesso nem ter SQL, parâmetros ou detalhes internos devolvidos ao navegador.

---

## 9. Exercício: acrescentar uma consulta de tipo por ID

**Este endpoint é apenas uma proposta didática; não está implementado no código atual.** Ele serve para mostrar uma alteração pequena usando tabela, modelo, schema e permissões existentes.

### 9.1. Definindo o requisito

“O usuário com acesso à leitura de Eventos pode consultar um tipo pelo ID. A resposta contém `id` e `name`; um ID inexistente retorna 404.”

| Item | Escolha |
|---|---|
| Método e URL | `GET /api/v1/events/types/<int:event_type_id>` |
| Permissão | `events.read`, já presente no mapa. |
| Modelo | `EventType`, já mapeado. |
| Saída | `EventTypeOut`, já declarado. |
| Alteração de banco | Nenhuma. |

### 9.2. Código a acrescentar em events/routes.py

Todos os nomes usados abaixo já são importados ou definidos no arquivo atual. Acrescente a função junto das rotas de tipos; não substitua o arquivo inteiro:

```python
@events_bp.get("/types/<int:event_type_id>")
@require_action("events.read")
@events_bp.output(EventTypeOut)
def get_event_type(event_type_id):
    sessions = get_td_session_factory()
    with sessions() as session:
        row = session.execute(
            select(EventType.id, EventType.name)
            .where(EventType.id == event_type_id)
        ).mappings().one_or_none()
        if row is None:
            raise ApiProblem(404, "Tipo de evento não encontrado.")
        result = dict(row)
    return result
```

### 9.3. Entendendo o caminho completo

```text
GET /api/v1/events/types/7
  → configure_api confere sessão e perfil
  → require_action confere events.read
  → Flask fornece event_type_id = 7
  → a rota abre uma sessão de leitura
  → a consulta procura o tipo no banco
  → ausência gera ApiProblem(404)
  → existência gera {id, name}
  → a sessão fecha e a resposta é serializada por EventTypeOut
```

`one_or_none()` representa a expectativa de encontrar uma linha ou nenhuma. O ID é chave primária. A entrada vai para a expressão ORM como parâmetro; não montamos SQL com texto vindo da URL.

Não é preciso alterar `models.py`, `schemas.py`, bootstrap ou registro de módulos nesse exercício. O blueprint já está registrado e oferece a nova rota quando a alteração for implementada e publicada.

### 9.4. Ligação com o frontend

Se uma tela precisar dessa consulta, uma função adicional em `frontend/src/features/events/api.ts` poderia ser:

```typescript
// Exemplo proposto; usa os imports de requestJson e EventType já existentes.
export function getEventType(id: number): Promise<EventType> {
  return requestJson<EventType>(`/api/v1/events/types/${id}`)
}
```

Esse exemplo é uma função exportada separadamente. Caso prefira um método no objeto `eventsApi`, atualize também o contrato `EventsApi` em `types.ts`.

O cliente comum preserva a sessão, trata erros e envia o token CSRF nas escritas. O tipo TypeScript ajuda durante o desenvolvimento; a validação da entrada continua no backend.

### 9.5. Como revisar a alteração

Na revisão estática, confira o caminho, o nome da função, os imports, a ação, os campos da saída e o tratamento de ausência. Pesquise se já existe uma rota com a mesma combinação de método e URL.

Em ambiente com execução explicitamente autorizada, os cenários funcionais seriam: ID existente, ID inexistente, usuário sem sessão e usuário sem o perfil. Eles são cenários planejados, não testes executados por este guia.

---

## 10. Como começar uma feature nova

Quando a operação pertence a Eventos ou Demandas, comece na pasta correspondente. Uma pasta nova faz sentido quando existe outra funcionalidade com responsabilidade própria.

### Passo 1 — Escrever o comportamento

Defina o que a pessoa pode fazer, quais dados entram e saem, quem pode acessar cada registro e quais tabelas ou integrações participam. Isso evita implementar um CRUD antes de entender suas regras.

### Passo 2 — Conferir a estrutura do banco

Se houver persistência, obtenha a definição real das tabelas: tipos, PK, FKs, defaults, índices únicos, triggers e versão de concorrência quando existir. Um modelo ORM acompanha essa estrutura; um campo novo no Python não altera a tabela.

### Passo 3 — Criar os arquivos necessários

Use `backend/modules/<feature>/`. Defina os contratos em `schemas.py`, os mapeamentos necessários em `models.py` e a sequência das operações em `routes.py`. Não crie um modelo se a funcionalidade não acessa tabelas por ORM.

### Passo 4 — Configurar acesso e transações

Crie um `APIBlueprint` com nome exclusivo e prefixo `/api/v1/...`, aplique `configure_api` e defina as ações em `ACTION_ROLES`. Reutilize a identidade do portal e a factory de sessões. Aplique os filtros por registro em todas as entradas que acessam os dados, incluindo downloads.

### Passo 5 — Exportar e registrar o blueprint

Exemplo de exportação para uma feature chamada `minha_feature`, depois de definir o blueprint em `routes.py`:

```python
# backend/modules/minha_feature/__init__.py
from .routes import minha_feature_bp
```

Dentro da função existente `register_modules(app)`, acrescente o import e o registro, preservando os demais:

```python
from .minha_feature import minha_feature_bp
app.register_blueprint(minha_feature_bp)
```

Se também houver uma página Vue, exporte e registre seu blueprint de shell. Não precisamos registrar um Service por feature no bootstrap. Um recurso externo novo pode precisar de composição explícita ali.

### Passo 6 — Conectar uma página, se houver interface

1. Crie a tela em `frontend/src/features/<feature>/`, reutilizando os componentes compartilhados.
2. Declare os tipos e as chamadas da API com `requestJson`.
3. Acrescente a rota em [frontend/src/router/index.ts](../../frontend/src/router/index.ts).
4. Crie a rota Flask `/app/...`, com `page_access` e `render_vue_shell`, para entrada direta.
5. Ajuste [AppShell.vue](../../frontend/src/app/layouts/AppShell.vue) se a tela precisar aparecer no menu.

O Router atual usa `createWebHistory('/app/')`; por isso a rota Vue `/eventos` corresponde à entrada Flask `/app/eventos`. Uma API sem tela não precisa desse passo.

### Passo 7 — Revisar e preparar a validação

Confira contratos, autorização, referências e diff. Separe os cenários funcionais que dependem do ambiente autorizado. A publicação deve seguir o guia de servidor; editar arquivos ou fazer pull não gera o build Vue.

---

## 11. O que significa “mais lógica nas rotas” em Demandas?

Significa que conseguimos ler a sequência do caso de uso dentro da função da rota, usando auxiliares locais quando ajudam. Isso não elimina as regras existentes.

### 11.1. Cadastro atual de uma solicitação

Leia `create_request` em [demands/routes.py](../../backend/modules/demands/routes.py) nesta ordem:

1. Confere o multipart com os campos `payload` e `files`.
2. Valida o JSON com `RequestCreate.model_validate_json(...)`.
3. Obtém o solicitante pela identidade autenticada.
4. Pede ao `storage` que valide e prepare os anexos.
5. Calcula a impressão do conteúdo e dos arquivos para identificar repetições.
6. Abre a transação SQL e procura a chave de envio sob trava.
7. Em uma repetição equivalente, devolve a solicitação existente; conteúdo diferente com a mesma chave gera conflito.
8. Em um envio novo, valida o contribuinte, insere a solicitação e obtém seu ID com `flush()`.
9. Salva os arquivos e insere os metadados dos anexos e o histórico na mesma sessão SQL.
10. Prepara o detalhe, confirma a transação e devolve a resposta.

A **idempotência** permite reconhecer um envio repetido sem criar outra solicitação. Ela depende da chave, da impressão do conteúdo, da trava e da constraint do banco.

O rollback SQL não desfaz arquivos. O código compensa arquivos novos nas falhas previstas ao inserir os metadados/histórico ou preparar o detalhe. Uma falha ao confirmar o commit preserva os arquivos, pois o resultado da confirmação pode ser incerto. A sequência precisa ser mantida.

### 11.2. Edição atual

`update_request` confere vínculo e estado sob trava. Somente o solicitante pode editar enquanto a solicitação está em análise e sem classificação.

A atualização compara o `row_version` enviado pela tela. Se a versão mudou, retorna `409`; o histórico é inserido na mesma transação da alteração. A versão representa concorrência, não uma data escolhida pelo navegador.

### 11.3. Por que storage.py continua separado?

Ele reúne os limites e o tratamento dos anexos: quantidade, tamanho, extensão, nome seguro, chave de armazenamento, caminho privado e compensação. As rotas coordenam quando essas operações acontecem.

Em Demandas, área e permissões ficam em `routes.py`; contratos em `schemas.py`; tabelas em `models.py`; arquivos e limites em `storage.py`. Os erros usam `ApiProblem`, sem um `domain.py` próprio.

O backend moderno de Demandas cobre **solicitações**. A existência de colunas para classificação ou estados futuros não significa que o painel moderno de gestão esteja implementado.

---

## 12. Onde mexer em cada situação

| Quero fazer… | Por onde começo? |
|---|---|
| Alterar um campo recebido pela API | `schemas.py`; conferir banco, rota e contrato TypeScript. |
| Alterar quem pode executar uma ação | `ACTION_ROLES` e decorator em `routes.py`. |
| Alterar quais registros uma pessoa vê | Filtros e auxiliares de autorização em `routes.py`. |
| Criar uma consulta ou gravação | Rota e ORM da feature, com a sessão adequada. |
| Mapear uma coluna já existente | `models.py`, conferindo a definição real do banco. |
| Criar uma coluna ou tabela | Trabalho separado de banco; não chamar `create_all()`. |
| Ajustar anexos de Demandas | `storage.py` e os pontos de composição na rota. |
| Ajustar o PDF de presença | `events/attendance_pdf.py` e a rota de exportação. |
| Acrescentar uma tela | Feature Vue, Router, shell Flask e menu quando necessário. |
| Reutilizar algo entre features | Conferir primeiro os recursos de `backend/shared/`. |

### Referências para continuar

- [Base compartilhada](../features/base-compartilhada.md): contratos e recursos comuns.
- [Arquitetura moderna](arquitetura-modernizada.md): critérios de organização.
- [Eventos](../features/eventos.md): comportamento completo, presença e PDF.
- [Demandas](../features/demandas.md): solicitações, concorrência, histórico e anexos.
- [Decisões de aproximação ao curso](proposta-arquitetura-proxima-ao-curso.md): motivos das escolhas adotadas.
- [Curso original](../../curso_notion/): material usado como referência didática.
