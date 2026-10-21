# Base compartilhada da arquitetura moderna

Referência prática dos recursos que Eventos, Demandas e próximas funcionalidades podem reutilizar. Revisada em **20/10/2026** contra os arquivos citados e a [base anterior](../historico/docs/base-compartilhada-novas-features.md). As regras de organização ficam em [Arquitetura](../docs/arquitetura-modernizada.md); comportamento de negócio pertence à feature.

## 1. Recursos existentes

| Necessidade | Fonte e uso |
|---|---|
| Identidade atual | [compatibility/identity.py](../../backend/compatibility/identity.py): sessão autenticada e `current_actor()`. |
| Permissões por ação | [platform/identity.py](../../backend/platform/identity.py): `RolePermissions`; mapa junto da feature, ação desconhecida negada. |
| Segurança HTTP e erros | [http.py](../../backend/platform/http.py): `configure_api`, `page_access` e `api_error`. |
| CSRF | [csrf.py](../../backend/platform/csrf.py): token comum e validação das escritas. |
| Banco TD | [database.py](../../backend/platform/database.py): engine por aplicação, recuperado por `get_td_engine()` na rota. |
| Contratos paginados | [schemas.py](../../backend/platform/schemas.py): `PaginationQuery` e `PaginatedResponse`. |
| Shell Vue | [vue_shell.py](../../backend/platform/vue_shell.py): manifest, assets, título e token após autorizar a página. |
| Cliente e apresentação | [shared](../../frontend/src/shared/): HTTP, paginação, validação, componentes e estilos. |

O bootstrap compõe os recursos com ciclo de vida da aplicação; não registra objetos de Service. As chaves atuais são `backend_td_engine`, `backend_employee_directory` e `demands_attachment_storage`. Uma integração nova pode precisar de composição explícita, sem recriar banco/login por módulo.

`Actor` é um contrato mínimo, imutável, contendo `id`; não carrega perfis, área ou e-mail. A ponte obtém o ID de Flask-Login e consulta os perfis via Flask-Principal. `RolePermissions.can(actor, action)` nega ações fora do mapa; a implementação atual consulta a sessão e não utiliza o ID para resolver outro usuário. A política por registro pertence ao caso de uso/SQL, não ao helper de dependências.

Os construtores de `EmployeeDirectory` e `DemandAttachmentStorage` guardam configuração/caminho. O primeiro abre LDAP apenas em `find_by_badge`; o segundo cria a pasta apenas ao salvar arquivos. Isso não elimina os efeitos dos imports e da factory legados que hospedam esses recursos.

## 2. Criar uma funcionalidade

1. Definir URL, métodos, entradas/saídas, ação, escopo dos registros e fontes; considerar integrações, anexos e jobs.
2. Criar `backend/modules/<feature>/` com `__init__.py`, `routes.py`, schemas e Repository necessários. Acrescentar Service somente pelos critérios de complexidade da arquitetura.
3. Aplicar `configure_api` no blueprint de API e `page_access` na entrada da página; definir mapa de ações e schemas públicos.
4. Exportar os blueprints em `__init__.py` e registrá-los em `backend/modules/__init__.py`. Não copiar o bootstrap ou criar engine por request.
5. Criar `frontend/src/features/<feature>/` com API, tipos, página e componentes locais. Registrar Vue Router e a rota Flask para entrada direta/F5.
6. Usar o cliente comum, estados de consulta, validação e componentes do [padrão visual](../docs/padrao-visual.md).
7. Revisar referências, contratos e diff; preparar verificações e publicação conforme [Servidor](../docs/servidor-e-publicacao.md).

Uma feature simples pode ter quatro arquivos Python; uma feature sem persistência não precisa inventar Repository. Não criar tabela, camada, classe ou componente para preencher uma estrutura.

### Registro e entrada direta

O `__init__.py` de cada módulo exporta seus blueprints. O registro atual é explícito:

```python
# backend/modules/__init__.py — recorte da implementação atual
def register_modules(app):
    from .events import events_bp, events_shell_bp
    from .demands import demands_bp, demands_shell_bp
    app.register_blueprint(events_bp)
    app.register_blueprint(events_shell_bp)
    app.register_blueprint(demands_bp)
    app.register_blueprint(demands_shell_bp)
```

Uma feature nova acrescenta seus blueprints nesse arquivo, sem registrar outro Service no bootstrap. Para uma página, o padrão real de Eventos é:

```python
@events_shell_bp.get("/app/eventos")
@page_access(identity=identity, permission="GENERAL")
def events_page():
    return render_vue_shell(
        title="Eventos | Digital JOST",
        unavailable_message="Aplicação de Eventos indisponível.",
    )
```

Os imports e a criação de `events_shell_bp = Blueprint(...)` permanecem no módulo. No Vue, a rota correspondente é `/eventos`, pois `createWebHistory('/app/')` fornece a base. Atualizar a navegação em `frontend/src/app/layouts/AppShell.vue` quando a tela precisar de acesso pelo menu. Não copiar os nomes de blueprint dos exemplos para uma segunda feature.

## 3. Dependências dos Services

Services são funções com dependências explícitas. Nas rotas que repetem engine e permissões, usar o helper local e opcional abaixo; `ACTION_ROLES` é o mapa específico do módulo:

```python
def _permissions():
    return RolePermissions(identity.can_access, ACTION_ROLES)


def _service_deps():
    return {"engine": get_td_engine(), "permissions": _permissions()}


@events_bp.post("")
@events_bp.input(EventCreate)
@events_bp.output(EventOut, status_code=201)
def create_event(json_data):
    return services.create_event(
        json_data, identity.current_actor(), **_service_deps(),
    )
```

É um recorte de [Eventos](../../backend/modules/events/routes.py), cujos imports, schemas e guardas completam o módulo. `**` expande o dicionário em argumentos nomeados. O usuário permanece visível; o resultado do helper não é global nem cacheado. Não criar um executor genérico ou helper compartilhado obrigatório.

LDAP é fornecido separadamente somente a `register_attendance`; armazenamento, somente à criação e ao download de Demandas. Services não buscam contexto Flask internamente. `RolePermissions` usa a sessão corrente, mesmo recebendo um `Actor`; reutilização em jobs exige política adequada.

Exemplos de dependências especiais nas [rotas reais](../../backend/modules/events/routes.py):

```python
return services.register_attendance(
    event_id, list_id, json_data, identity.current_actor(),
    **_service_deps(),
    employee_directory=current_app.extensions["backend_employee_directory"],
)
```

O acesso ao contexto está na entrada HTTP; a função recebe o adaptador pronto. Em Demandas, a mesma composição usa `storage=current_app.extensions["demands_attachment_storage"]`. Não incluir LDAP e armazenamento no helper de todas as features ou em operações que não os utilizam. As chaves extras não podem repetir argumentos já fornecidos pelo helper.

## 4. Consultas e gravações simples

Uma consulta simples pode chamar o Repository diretamente. Exemplo existente, com `configure_api` e schema de saída no blueprint:

```python
def list_event_types():
    actor = identity.current_actor()
    permissions = _permissions()
    permissions.require(actor, "events.read")
    with get_td_engine().connect() as connection:
        items = repository.list_event_types(connection)
    return {
        "items": items,
        "can_create": permissions.can(actor, "events.types.create"),
        "can_delete": permissions.can(actor, "events.types.delete"),
    }
```

Gravações simples podem abrir `get_td_engine().begin()` na rota, após exigir a ação, e fornecer a conexão ao Repository. Isso só vale sem várias gravações coordenadas, arquivos/integrações, transições/regras de negócio além dos campos e da ação, autorização por registro, idempotência, concorrência especial ou reutilização por outra entrada. Caso contrário, usar Service funcional, inclusive em GET.

O Repository usa parâmetros SQL, retorna os campos necessários e não faz commit próprio. O responsável pela operação define autoria, área e metadados; o cliente não escolhe seus privilégios. Escrever menos linhas não justifica retirar verificações.

Na consulta acima, a sequência é: guarda do blueprint → ação `events.read` → conexão emprestada → SQL → fechamento → modelo de saída. Acrescentar autorização por registro ou coordenação de outras fontes pode justificar transferir a composição para Service.

Para uma gravação trivial, o limite da transação é `with get_td_engine().begin() as connection:` na rota. O retorno de sucesso deve depender da saída bem-sucedida desse contexto. É uma opção do padrão; os exemplos atuais de cadastro de Eventos e Demandas têm regras que justificam Service.

## 5. Casos de uso e transações

O Service exige a ação, aplica regras e abre `with engine.begin()`. Todas as gravações que precisam confirmar juntas usam essa conexão, inclusive histórico. Preservar travas e condições de versão no SQL; não substituir controle de concorrência por uma conferência apenas no navegador.

Eventos verifica período/tipo, vínculos e presença; Demandas coordena visibilidade, idempotência, arquivos, edição e histórico. Consultar [Services de Eventos](../../backend/modules/events/services.py) e [Services de Demandas](../../backend/modules/demands/services.py) antes de reutilizar um fluxo.

Filesystem e integrações não entram automaticamente no rollback SQL. Falha depois do commit não desfaz dados; falha durante commit pode deixar resultado incerto. Manter a estratégia do caso de uso, sem repetir escritas ou excluir arquivos automaticamente por suposição.

### Exemplo de Service com regra e transação

Este é o fluxo real de criação de tipo, separado da rota que recebe `EventTypeCreate`:

```python
def create_event_type(data, actor, *, engine, permissions):
    permissions.require(actor, "events.types.create")
    with engine.begin() as connection:
        event_type = repository.create_event_type(
            connection, name=data.name, created_by=str(actor.id),
        )
    return event_type
```

O Repository verifica nome existente com `UPDLOCK, HOLDLOCK`, protegido pela chave única, e cadastra ou reutiliza a opção. Valores de nome/autor são parâmetros; a transação continua pertencendo ao Service. Esse cadastro não é um INSERT irrestrito: remover o caso de uso só para economizar uma função não é objetivo da arquitetura.

No [Repository](../../backend/modules/events/repository.py), uma consulta simples ilustra o contrato:

```python
from sqlalchemy import text


def list_event_types(connection):
    rows = connection.execute(
        text("SELECT id, name FROM dbo.DJ_EVENT_TYPES ORDER BY name, id"),
    ).mappings().all()
    return [dict(row) for row in rows]
```

Quando houver entrada, usar parâmetros como `WHERE id = :event_id` com o dicionário separado. A composição de fragmentos SQL constantes observada em alguns repositórios não autoriza interpolar valores de request ou nomes arbitrários de coluna/tabela.

### Garantias e limites

- Exceção dentro de `engine.begin()` provoca rollback SQL; confirmar o contexto antes de devolver sucesso.
- `connect()` não confirma gravações automaticamente. Não usar uma conexão de leitura para esconder escrita sem commit.
- Várias conexões/engines não pertencem à mesma transação. Não abrir outra no Repository.
- Verificar e gravar em comandos separados exige constraint/trava/versão quando houver disputa; uma validação prévia sozinha pode ficar desatualizada.
- Demandas compensa arquivos novos em falhas específicas, preservando-os se o commit for incerto. Eventos consulta LDAP sem segurar conexão SQL e revalida o vínculo depois.
- Auditoria de acesso global e histórico de negócio são responsabilidades distintas. Acrescentar o histórico necessário dentro da mesma transação do caso de uso.

## 6. Contratos HTTP, sessão e CSRF

As APIs modernas usam `/api/v1/`. `configure_api` verifica autenticação, perfil e CSRF nessa ordem; a ação e as regras por registro continuam na operação. `page_access` protege o shell e pode redirecionar ao login. A ponte em `app/errors.py` preserva JSON também nos erros de roteamento sob o prefixo moderno.

| Resposta | Uso atual |
|---|---|
| `{message, detail}` | Erros; detalhes internos não são expostos em falhas genéricas. |
| 401 / 403 | Sem sessão / acesso negado. |
| 400 / 422 | Requisição malformada ou CSRF / validação, com `detail.json` ou `detail.query`. |
| 404 / 409 | Recurso ausente/inacessível / conflito definido pelo domínio. |
| 413 / 503 | Limite de envio / dependência indisponível quando tratado pela feature. |

O shell entrega a meta `csrf-token`, criando o token se necessário; POST/PUT/PATCH/DELETE enviam `X-CSRF-Token`. As chaves de sessão `backend_csrf` e o alias anterior `events_csrf` são aceitas durante a compatibilidade atual. GETs da API não renovam o token. Não trocar a chave de sessão como efeito de uma refatoração.

Os erros de domínio são traduzidos nas rotas: por exemplo, tipo em uso vira 409, recurso fora do vínculo vira 404 e identificação LDAP usa 422/503 com `detail.lookup_status`. `PermissionError` vira 403. Falhas inesperadas não devem expor SQL, parâmetros ou traceback. O handler HTTP preserva cabeçalhos úteis, como `Allow` de 405, sem substituir o tipo JSON.

Para um erro de campo, o formato consumido pelo frontend é:

```json
{
  "message": "Dados inválidos.",
  "detail": {"json": {"ends_at": ["O fim deve ser posterior ao início do evento."]}}
}
```

É um exemplo contratual, sem dados operacionais. A origem `query` é usada para filtros; não colocar toda falha em `detail.json`. Erros de vínculo e conflitos não são necessariamente erros de campo. No POST multipart de Demandas, o parsing Pydantic é explícito e o módulo traduz seus erros para o mesmo contrato.

Paginação comum: página inicial 1, tamanho padrão 12, limite de 100; retorno `items`, `page`, `per_page`, `total` e `capabilities`. A feature pode escolher outro tamanho dentro do limite. Schemas de saída não devem expor colunas indiscriminadamente.

`PaginationQuery` rejeita argumentos extras, mas aceita a conversão necessária de query strings para números. Os schemas de escrita de Eventos/Demandas acrescentam validação estrita e rejeição de campos extras. Não presumir que herdar paginação torna todos os contratos igualmente estritos. IDs, versões, bytes e datas precisam de serialização pública própria.

### Shell e build

`vue_shell.py` procura `.vite/manifest.json` em `backend/static/app/`, lê a entrada `index.html`, coleta CSS dela e dos imports e gera URLs por `backend_vue.static`. O template é `backend/app/shell.html`, fornecido com prefixo para não colidir com o legado.

Manifest ausente, inválido ou sem as chaves esperadas resulta em 503 com a mensagem da feature. O token só é obtido depois de localizar o build. O shell válido retorna `Cache-Control: private, no-store`; não cachear HTML que contém token de sessão. O manifesto existir não garante que todos os assets estejam presentes: publicar o build inteiro e conferir no ambiente autorizado.

## 7. Cliente Vue e verificação

`requestJson` usa sessão no mesmo domínio, CSRF, validação do tipo de resposta e `ApiError`. O padrão de timeout é dez segundos; upload de Demandas usa 60 e `requestPdf`, 30. Em `FormData`, não definir `Content-Type`: o navegador fornece o boundary.

Usar TanStack Query para dados remotos; a chave inclui página/filtros que mudam o resultado. Após escrita confirmada, atualizar as consultas. Desabilitar repetição automática de gravações e preservar dados quando o resultado for incerto. `validationMessages` associa 422 aos campos conhecidos.

`requestJson<T>` fornece tipagem TypeScript, não validação runtime do formato completo da resposta. O cliente verifica tipo de conteúdo, redirecionamento e status; o contrato continua precisando corresponder ao schema do backend. Redirecionamento para login vira 401 no cliente; rede/timeout vira `ApiError` de status 0. Erros 5xx são apresentados de forma genérica, preservando `detail` quando recebido.

O timeout usa AbortController no navegador. Cancelar a espera não garante cancelar processamento ou commit no servidor. Da mesma forma, resposta 2xx com conteúdo inesperado pode esconder uma escrita concluída: não reenviar automaticamente. Demandas dispõe de chave de envio; Eventos/presença têm estratégias próprias descritas nos guias.

### Paginação e cache na interface

`usePagination(12)` mantém página a partir de um e fornece `resetPage()`. `paginationQuery` serializa os dois campos; `ListPagination` converte o índice zero do controle Volt para o índice um da API e só aparece quando há mais de uma página. Ao excluir o último item ou mudar filtros, a feature corrige a página conforme o total.

Uma composição mínima de leitura, baseada em Eventos, é:

```ts
const { page, perPage, resetPage } = usePagination()
const { data, isPending, isError, error, refetch } = useQuery({
  queryKey: ['events', 'list', page, filters],
  queryFn: () => eventsApi.list(page.value, perPage, filters.value),
  retry: false,
})
```

É um recorte: imports, definição de `filters` e apresentação estão em [EventsPage.vue](../../frontend/src/features/events/pages/EventsPage.vue). O uso de atualização periódica e de foco depende da feature. Não copiar polling de presença para toda listagem, nem permitir que uma atualização substitua o formulário aberto.

Depois de uma escrita confirmada, invalidar as chaves afetadas ou atualizar o detalhe com o retorno do servidor. Tratar falha de renovação como falha de leitura, sem transformar sucesso de gravação em convite a cadastrar novamente. `RequestState` apresenta estados; não escolhe filtros, permissões nem estratégia de cache.

## 8. Onde alterar e como revisar

| Mudança | Arquivos a conferir |
|---|---|
| Nova ação ou regra por registro | Mapa do módulo, rota/Service, SQL do escopo e capacidades de saída. |
| Novo campo | Schema, Service, SQL, migration revisada quando necessária, tipos/clientes/formulário e documento da feature. |
| Nova entrada Vue | Router, shell Flask, registro de blueprints e navegação. |
| Mudança HTTP/CSRF | Plataforma, erros globais, shell, cliente e ambos os módulos consumidores. |
| Novo adaptador | Contrato e configuração, composição quando necessária, fluxo de falhas e operações que o recebem. |
| Componente comum | Consumidores de Eventos e Demandas e [padrão visual](../docs/padrao-visual.md). |

Conferir também quem usa as mesmas tabelas e arquivos, inclusive jobs legados. Não executar o portal para validar um exemplo. Scripts SQL, build, integrações e testes dependem de autorização específica conforme AGENTS.md.

Na revisão estática, conferir guardas, mapa de ações, argumentos do Service, parâmetros SQL, transação e contrato TypeScript. Em ambiente autorizado, verificar acesso negado, CSRF, validação, limites, conflitos, rollback e integração. **O sistema não foi executado; a validação foi somente estática.**

Os exemplos são recortes dos módulos existentes ou do padrão indicado, não arquivos completos para substituir as implementações. A antiga base continha um módulo de Equipamentos ilustrativo; ele não foi registrado como uma feature real e não deve aparecer no manual como entrega pronta.
