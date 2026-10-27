# Base compartilhada da arquitetura moderna

Referência prática dos recursos que Eventos, Demandas e próximas funcionalidades reutilizam. As regras de organização ficam em [Arquitetura](../docs/arquitetura-modernizada.md); comportamento de negócio pertence à feature.

## 1. Recursos existentes

| Necessidade | Fonte e uso |
|---|---|
| Identidade atual | [compatibility/identity.py](../../backend/compatibility/identity.py): sessão autenticada e `current_actor()`. |
| Permissões por ação | [platform/identity.py](../../backend/platform/identity.py): `RolePermissions`; mapa junto da feature, ação desconhecida negada. |
| Segurança HTTP e erros | [http.py](../../backend/platform/http.py): `configure_api`, `action_access`, `page_access`, `ApiProblem` e `api_error`. |
| CSRF | [csrf.py](../../backend/platform/csrf.py): token comum e validação das escritas. |
| Banco TD e modelos | [database.py](../../backend/platform/database.py): `Base`, engine e factory de sessões por aplicação; acesso por `get_td_session_factory()`. |
| Consultas comuns | `paginate(session, statement, query)` e `literal_contains(value)` no mesmo módulo de banco. |
| Contratos paginados | [schemas.py](../../backend/platform/schemas.py): `PaginationQuery` e `PaginatedResponse`. |
| Shell Vue | [vue_shell.py](../../backend/platform/vue_shell.py): manifest, assets, título e token após autorizar a página. |
| Cliente e apresentação | [shared](../../frontend/src/shared/): HTTP, paginação, validação, componentes e estilos. |

O bootstrap compõe os recursos com ciclo de vida da aplicação. As chaves atuais são `backend_td_engine`, `backend_td_sessions`, `backend_employee_directory` e `demands_attachment_storage`. Uma integração nova pode precisar de composição explícita, sem recriar banco/login por módulo.

`Actor` é um contrato mínimo, imutável, contendo `id`; não carrega perfis, área ou e-mail. A ponte obtém o ID de Flask-Login e consulta os perfis via Flask-Principal. `RolePermissions.can(actor, action)` nega ações fora do mapa; a implementação atual consulta a sessão e não utiliza o ID para resolver outro usuário. A política por registro pertence ao caso de uso/SQL, não ao helper de dependências.

Os construtores de `EmployeeDirectory` e `DemandAttachmentStorage` guardam configuração/caminho. O primeiro abre LDAP apenas em `find_by_badge`; o segundo cria a pasta apenas ao salvar arquivos. Isso não elimina os efeitos dos imports e da factory legados que hospedam esses recursos.

## 2. Criar uma funcionalidade

1. Definir URL, métodos, entradas/saídas, ação, escopo dos registros e fontes; considerar integrações, anexos e jobs.
2. Criar `backend/modules/<feature>/` com `__init__.py`, `routes.py`, `schemas.py` e `models.py` quando houver persistência ORM. Extrair auxiliares conforme a responsabilidade, sem camadas obrigatórias.
3. Aplicar `configure_api` no blueprint de API e `page_access` na página; definir mapa de ações, decorator de ação e schemas públicos.
4. Exportar os blueprints em `__init__.py` e registrá-los em `backend/modules/__init__.py`. Não copiar o bootstrap ou criar engine por request.
5. Criar `frontend/src/features/<feature>/` com API, tipos, página e componentes locais. Registrar Vue Router e a rota Flask para entrada direta/F5.
6. Usar o cliente comum, estados de consulta, validação e componentes do [padrão visual](../docs/padrao-visual.md).
7. Revisar referências, contratos e diff; preparar verificações e publicação conforme [Servidor](../docs/servidor-e-publicacao.md).

Uma feature simples pode ter quatro arquivos Python; uma feature sem persistência não precisa de modelo ORM. Não criar tabela, camada, classe ou componente para preencher uma estrutura.

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

## 3. Permissões e erros nas rotas

Cada módulo mantém seu mapa de ações e uma política sem estado de requisição. O decorator obtém o usuário a cada chamada:

```python
permissions = RolePermissions(identity.can_access, ACTION_ROLES)
require_action = action_access(identity=identity, permissions=permissions)
```

Usar `@require_action("events.create")`, por exemplo, além de `configure_api`. A ação fica visível na rota; vínculos, área e estado do registro continuam sendo verificados na operação. O mapa não armazena usuários nem resultados de permissão. `RolePermissions` consulta a sessão corrente; jobs precisam de política apropriada.

`ApiProblem(status, message=None, detail=None)` representa uma falha esperada e é traduzido por `configure_api` para `{message, detail}`. O argumento `detail` é nomeado. Demandas usa esse contrato diretamente nas rotas e no armazenamento. A plataforma também traduz `ValidationError` explícito do multipart, sem expor a entrada ou detalhes internos.

## 4. Modelos e consultas ORM

Modelos herdam de `Base`, com metadados separados do `db.Model` legado. Mapear tabelas existentes com tipos, tamanhos, nulabilidade, defaults e FKs reais. Não chamar `create_all()` nem refletir o banco. A projeção `SharedUser` de Demandas é somente de leitura e não importa o modelo legado.

Exemplo de consulta, extraído da listagem de tipos; a resposta completa também inclui capacidades:

```python
@events_bp.get("/types")
@require_action("events.read")
@events_bp.output(EventTypes)
def list_event_types():
    sessions = get_td_session_factory()
    with sessions() as session:
        items = session.execute(
            select(EventType.id, EventType.name).order_by(EventType.name, EventType.id),
        )
        result = {"items": [dict(row) for row in items.mappings()]}
    actor = identity.current_actor()
    return {
        **result,
        "can_create": permissions.can(actor, "events.types.create"),
        "can_delete": permissions.can(actor, "events.types.delete"),
    }
```

Os imports e a configuração do blueprint estão nas [rotas de Eventos](../../backend/modules/events/routes.py). A consulta projeta campos públicos e os materializa antes de fechar a sessão. Modelos Pydantic continuam delimitando o contrato; `model_validate(objeto, from_attributes=True)` é usado quando convém obter os campos públicos de uma entidade carregada.

`paginate(session, statement, query)` recebe uma projeção já filtrada/ordenada, conta sua subconsulta sem ordenação e retorna `items`, `total`, `page` e `per_page`. Capacidades são acrescentadas pela feature. `literal_contains(value)` escapa `~`, `%`, `_` e `[`; usar o padrão com `.like(..., escape="~")` para pesquisa literal no SQL Server.

## 5. Escritas, integrações e transações

A mesma factory oferece `with sessions.begin() as session:`. A rota aplica as regras e prepara o resultado antes de sair; o retorno de sucesso acontece depois do commit. Auxiliares recebem a mesma sessão e não confirmam gravações próprias. `session.flush()` envia alterações e obtém IDs/defaults, sem confirmar a transação.

Criar tipo de evento continua verificando o nome com `UPDLOCK, HOLDLOCK` e reutilizando a opção existente. Excluir tipo usa `XLOCK, HOLDLOCK` e confere vínculos. As rotas usam `.with_hint(..., "mssql")` para manter as travas específicas. Um `add()` isolado não substitui essas regras.

Eventos usa funções locais para projeções, vínculos e período. Demandas mantém auxiliares para visibilidade, detalhe e elegibilidade de contribuintes. A presença consulta LDAP fora da sessão SQL e revalida a lista sob trava. PDF é renderizado em memória depois de liberar conexão e travas. Ver [Eventos](../../backend/modules/events/routes.py) e [Demandas](../../backend/modules/demands/routes.py).

Filesystem e integrações não entram no rollback SQL. Demandas compensa arquivos novos nas falhas previstas durante a gravação dos metadados/histórico e preparação do detalhe; falha no commit preserva arquivos para conciliação. Manter essa distinção ao alterar a operação.

### Garantias e limites

- Exceção dentro de `sessions.begin()` provoca rollback SQL; confirmar o contexto antes de devolver sucesso.
- Uma sessão de leitura não deve esconder gravações sem commit.
- Sessões/conexões diferentes não pertencem à mesma transação. Não misturar o `db.session` legado com a sessão moderna.
- SQL excepcional, se necessário, usa parâmetros e a própria sessão. Fazer `flush()` se ele depender de alterações ORM pendentes.
- Preservar constraints, hints, autoria, área, estado e versão recebida do cliente; uma validação prévia sozinha pode ficar desatualizada.
- Auditoria de acesso global e histórico de negócio são responsabilidades distintas. Histórico usa a mesma transação da alteração.

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
| Nova ação ou regra por registro | Mapa do módulo, decorator, rota/auxiliar, filtros ORM e capacidades de saída. |
| Novo campo | Schema, modelo, rota/auxiliar, migration revisada quando necessária, tipos/clientes/formulário e documento da feature. |
| Nova entrada Vue | Router, shell Flask, registro de blueprints e navegação. |
| Mudança HTTP/CSRF | Plataforma, erros globais, shell, cliente e ambos os módulos consumidores. |
| Novo adaptador | Contrato e configuração, composição quando necessária, fluxo de falhas e operações que o recebem. |
| Componente comum | Consumidores de Eventos e Demandas e [padrão visual](../docs/padrao-visual.md). |

Conferir também quem usa as mesmas tabelas e arquivos, inclusive jobs legados. Não executar o portal para validar um exemplo. Scripts SQL, build, integrações e testes dependem de autorização específica conforme AGENTS.md.

Na revisão estática, conferir guardas, mapa de ações, modelos, filtros e hints ORM, parâmetros, sessão/transação e contrato TypeScript. Em ambiente autorizado, verificar acesso negado, CSRF, validação, limites, conflitos, rollback e integração. **O sistema não foi executado; a validação foi somente estática.**

Os exemplos são recortes dos módulos existentes ou do padrão indicado, não arquivos completos para substituir as implementações. A antiga base continha um módulo de Equipamentos ilustrativo; ele não foi registrado como uma feature real e não deve aparecer no manual como entrega pronta.
