> **Registro histórico.** Pode conter decisões, caminhos e comandos superados. Consulte o [manual atual](../../README.md); este arquivo não define o padrão vigente.

**Eu recomendo adotar a simplificação, com alguns limites claros.** Ela pode facilitar bastante seu trabalho sem comprometer a arquitetura. O principal ganho seria tornar explícito o caminho de cada operação e reduzir a montagem de objetos de Service.

Depois de examinar o código, minha avaliação é: **a estrutura geral é adequada; parte da configuração pode ser simplificada, mas boa parte da complexidade dentro das funcionalidades corresponde a regras reais.**

Há um detalhe relevante: sua proposta já está, em grande parte, prevista na [arquitetura documentada](arquitetura-modernizacao.md). O documento admite funções simples e consultas triviais sem Service. Já o [guia da base compartilhada](base-compartilhada-novas-features.md) orienta a composição de objetos de Service no bootstrap. Essa diferença entre o princípio e o exemplo prático aumenta a dificuldade de aprendizado.

1. **A arquitetura atual está excessivamente complexa?**

   Não considero excessivo separar rotas, contratos, regras e SQL para o Digital JOST. O sistema tem autorização, integrações corporativas, arquivos, concorrência e convivência com código antigo; essas responsabilidades justificam a separação.

   O que pode estar excessivamente trabalhoso para você é o **procedimento necessário para acrescentar uma operação**: criar ou localizar a classe, entender suas dependências, montá-la no bootstrap, registrá-la em `app.extensions` e recuperá-la pela rota.

   Também não encontrei uma arquitetura carregada de interfaces, classes abstratas ou frameworks de injeção. Portanto, a simplificação seria localizada. Converter classes em funções não eliminará a maior parte das regras nem produzirá uma grande redução de linhas.

2. **Qual complexidade é necessária e qual pode ser simplificada?**

   | Manter | Simplificar |
   |---|---|
   | Autenticação, CSRF e tratamento HTTP compartilhados | Registro de um objeto de Service para cada funcionalidade |
   | Schemas explícitos de entrada e saída | Classes que apenas agrupam funções e guardam dependências |
   | SQL parametrizado nos repositórios | Obrigação de atravessar Service em consultas triviais |
   | Transações e controles de concorrência | Mapas de ações das funcionalidades dentro do bootstrap |
   | Autorização por registro e proteção dos anexos | Documentação que apresenta exemplos antigos como referência inicial |
   | Separação entre moderno e legado | Arquivos adicionais criados apenas para completar uma estrutura |

   A pasta `platform/` atual é relativamente pequena e tem responsabilidades identificáveis. Eu a preservaria, evitando transformá-la em um lugar para regras específicas dos módulos.

3. **Trocar classes de Service por funções é uma boa decisão?**

   Sim, para `EventsService` e `DemandsService`.

   As duas classes guardam dependências no construtor e executam operações usando essas dependências. Não identifiquei estado de negócio que precise sobreviver entre chamadas. Os métodos podem virar funções como:

   ```python
   def create_event(data, actor, *, engine, permissions):
       ...

   def register_attendance(
       event_id, list_id, data, actor, *, engine, permissions, employee_directory
   ):
       ...

   def create_request(data, files, actor, *, engine, permissions, storage):
       ...
   ```

   Isso torna visível que apenas o registro de presença precisa do diretório e apenas certas operações de Demandas precisam do armazenamento.

   O cuidado é preservar a passagem explícita dessas dependências. Se as funções começarem a buscar `request`, `current_user`, engines e configurações globais internamente, a troca apenas esconderá a complexidade e dificultará verificações isoladas no futuro.

   Também não recomendo eliminar classes por regra. `EmployeeDirectory` guarda configuração de integração e `DemandAttachmentStorage` guarda sua raiz de armazenamento. Essas classes continuam sendo compreensíveis e úteis. Os modelos Pydantic também permanecem classes.

4. **Podemos reduzir o bootstrap?**

   Sim. O [bootstrap atual](../../../backend/bootstrap.py) conhece as classes dos Services, suas dependências e os mapas de ações de Eventos e Demandas.

   Eu deixaria nele:

   - Inicialização única do engine moderno.
   - Composição explícita dos adaptadores necessários, como diretório e armazenamento.
   - Inicialização do shell Vue.
   - Registro explícito dos módulos.

   Retiraria a criação e o registro de `EventsService` e `DemandsService`. Os mapas de ações ficariam junto da funcionalidade, inicialmente em `services.py` ou no `domain.py` já existente.

   Não é necessário eliminar toda referência a funcionalidades no bootstrap. Algumas linhas explícitas de composição são fáceis de acompanhar. Não introduziria descoberta automática, um contêiner de dependências ou um objeto genérico que carregue todos os recursos da aplicação.

5. **Rotas podem consultar diretamente o Repository?**

   Sim, quando a operação for realmente simples: autorização por ação, parâmetros validados, consulta e composição curta da resposta.

   Um exemplo concreto é `GET /api/v1/events/types`.

   A decisão não deve depender apenas de ser GET. O download de um anexo de Demandas e a exportação de presença em PDF são leituras, mas coordenam verificações e recursos suficientes para justificar Service.

   No padrão recomendado, consultas com autorização por registro continuam passando por uma função de Service. Isso mantém um lugar evidente para conferir o acesso e evita que a regra se espalhe pelas rotas.

6. **Essa arquitetura pode crescer em um sistema corporativo?**

   Sim. Funções podem coordenar operações tão complexas quanto métodos de classes. A capacidade de crescimento depende principalmente de responsabilidades claras, controle de transações, contratos e regras localizadas.

   O limite surgiria se `services.py` se tornasse um arquivo difícil de navegar. Nesse momento, seria possível separar operações por assunto dentro do próprio módulo. Não é necessário preparar essa subdivisão agora.

   Também preservaria a responsabilidade de cada módulo sobre seus dados. Uma funcionalidade não deveria começar a alterar diretamente tabelas de outra apenas porque ambas usam o mesmo engine.

7. **Existe uma alternativa ainda mais simples?**

   Existe uma alternativa com menos arquivos: concentrar consultas e operações na rota. Eu não a adotaria como padrão para este projeto, porque ela tende a misturar HTTP, autorização, transações e regras — justamente o problema que a modernização procura reduzir.

   Para seu objetivo, considero suficiente:

   **Rotas + schemas + repository; funções de Service quando houver escrita, regra, integração ou autorização por registro.**

   Não acrescentaria agora classes base de CRUD, interfaces para cada repositório, novos frameworks ou um gerador de funcionalidades. Um exemplo pequeno, atual e explicado seria mais útil para seu aprendizado.

8. **Como ficariam Eventos e Demandas?**

   Eu faria a seguinte distribuição:

   | Módulo e operação | Recomendação |
   |---|---|
   | Eventos: listar tipos | Rota → Repository |
   | Eventos: listar e detalhar eventos | Manter funções de Service inicialmente; hoje coordenam horário do TD, capacidades e resultado |
   | Eventos: criar, editar e excluir eventos e tipos | Service |
   | Eventos: consultar listas e participantes | Manter Service para as verificações de existência e vínculo entre recursos |
   | Eventos: registrar presença | Service |
   | Eventos: exportar PDF | Service |
   | Demandas: listar colaboradores elegíveis | Pode ser Rota → Repository, preservando a ação `demands.create` |
   | Demandas: listar e detalhar solicitações | Service, preservando a visibilidade por usuário |
   | Demandas: criar e editar | Service |
   | Demandas: baixar anexos | Service |

   Em Eventos, a listagem e o detalhe de eventos também poderiam ser levados às rotas. Eu não começaria por eles: há pouco benefício imediato em redistribuir essa composição enquanto se muda o formato dos Services.

   Em Demandas, a restrição por solicitante ou colaborador já aparece no [Repository](../../../backend/modules/demands/repository.py). Essa filtragem deve permanecer no SQL, com a identidade fornecida pelo servidor, mesmo mantendo uma função de Service por cima.

9. **Qual arquitetura eu recomendo para você?**

   **O monólito modular atual, com Services funcionais, dependências explícitas e complexidade progressiva.**

   A mudança deve reduzir as decisões necessárias para começar uma funcionalidade. Você precisa conseguir responder: “onde entra a requisição?”, “onde está a regra?” e “onde está o SQL?”. Não precisa aprender a montar um objeto de Service antes de implementar sua primeira operação.

Eu organizaria os módulos assim, preservando as pastas existentes:

```text
app/                              # legado, mantido durante a transição

backend/
├── bootstrap.py                  # inicialização e composição explícitas
├── config.py
├── compatibility/
│   └── identity.py               # ponte com a identidade do legado
├── platform/
│   ├── database.py               # engine compartilhado e acesso HTTP a ele
│   ├── identity.py               # Actor e mecanismo de permissões
│   ├── http.py                   # guardas e respostas de erro
│   ├── csrf.py
│   ├── schemas.py                # contratos comuns de paginação
│   ├── environment.py
│   └── vue_shell.py
├── integrations/
│   └── employee_directory.py
└── modules/
    ├── __init__.py               # registro explícito dos blueprints
    ├── events/
    │   ├── __init__.py
    │   ├── routes.py
    │   ├── schemas.py
    │   ├── services.py           # funções de casos de uso
    │   ├── repository.py
    │   ├── attendance_pdf.py     # responsabilidade real já existente
    │   └── assets/
    └── demands/
        ├── __init__.py
        ├── routes.py
        ├── schemas.py
        ├── services.py           # funções de casos de uso
        ├── repository.py
        ├── domain.py            # limites e erros já existentes
        └── storage.py           # anexos privados

frontend/
└── src/
    ├── features/
    │   ├── events/
    │   └── demands/
    └── shared/
```

Para uma nova funcionalidade, os arquivos teriam estas responsabilidades:

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Exportar os blueprints; sem inicializações externas no import |
| `routes.py` | HTTP, validação, autorização de entrada, dependências e resposta |
| `schemas.py` | Campos, tipos, limites e contratos públicos |
| `repository.py` | SQL parametrizado e mapeamento dos resultados; recebe conexão |
| `services.py`, quando necessário | Regras, autorização do caso de uso, transações e coordenação |
| Arquivos adicionais | Somente responsabilidades reais, como armazenamento ou PDF |

Schemas não são uma etapa linear entre rota e Service: eles descrevem e validam a entrada e a saída da API.

Os dois caminhos seriam:

```text
Consulta simples
HTTP → autenticação/permissão → schema de entrada, se houver
     → rota abre conexão → repository
     → schema de saída → resposta

Operação com gravação
HTTP → autenticação/permissão/CSRF → schema de entrada
     → rota fornece dependências e identidade
     → service autoriza e aplica regras
     → transação → repository usando a mesma conexão
     → commit → schema de saída → resposta
```

O Repository não abre outra transação nem executa commit por conta própria. Uma consulta que precise de consistência especial também pode usar uma transação no Service, como já acontece na exportação de presença.

Os exemplos abaixo são **propostas ilustrativas baseadas nas funções atuais**, sem implementação no repositório.

Para obter o engine na camada HTTP, bastaria um acesso pequeno em `platform/database.py`:

```python
def get_td_engine():
    from flask import current_app

    return current_app.extensions["backend_td_engine"]
```

Somente as rotas usariam esse acesso. Services e repositórios continuariam recebendo suas dependências por argumentos.

Para a consulta de tipos de Eventos, a rota poderia ficar assim:

```python
# routes.py
# ACTION_ROLES representa o mapa completo transferido do bootstrap.
from backend.platform.database import get_td_engine
from backend.platform.identity import RolePermissions
from . import repository, services


def _permissions():
    return RolePermissions(identity.can_access, services.ACTION_ROLES)


@events_bp.get("/types")
@events_bp.output(EventTypes)
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

O `configure_api` existente permaneceria configurado no blueprint. A função do Repository já existe e não precisaria mudar.

Para criar um evento, a função de Service manteria as verificações do [método atual](../../../backend/modules/events/services.py):

```python
# services.py
def create_event(data, actor, *, engine, permissions):
    permissions.require(actor, "events.create")

    if data.ends_at <= data.starts_at:
        raise InvalidEventScheduleError()

    with engine.begin() as connection:
        if not repository.event_type_exists(connection, data.event_type_id):
            raise InvalidEventTypeError()

        event = repository.create_event(
            connection,
            name=data.name,
            description=data.description,
            event_type_id=data.event_type_id,
            instructor=data.instructor or None,
            syllabus=data.syllabus or None,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            created_by=str(actor.id),
            now=repository.current_time(connection),
        )

    return event
```

A rota continuaria curta:

```python
@events_bp.post("")
@events_bp.input(EventCreate)
@events_bp.output(EventOut, status_code=201)
def create_event(json_data):
    return services.create_event(
        json_data,
        identity.current_actor(),
        engine=get_td_engine(),
        permissions=_permissions(),
    )
```

Nesse exemplo, desaparecem o construtor, os atributos `self` e o registro de `EventsService`. Permanecem o contrato, a autorização, a validação do horário, a existência do tipo, a autoria e a transação.

Em Demandas, a edição exige preservar mais comportamento. A conversão do [método atual](../../../backend/modules/demands/services.py) poderia seguir este formato:

```python
def update_request(demand_id, data, actor, *, engine, permissions):
    permissions.require(actor, "demands.update")
    actor_id = str(actor.id)

    with engine.begin() as connection:
        current = repository.get_request(
            connection, demand_id, AREA_ID, actor_id, lock=True,
        )
        if current is None or current["relationship"] != "requester":
            raise DemandNotFoundError()

        if current["status"] != "em_analise" or current["classification"] is not None:
            raise DemandConflictError(
                "Esta solicitação já foi analisada e não pode mais ser editada."
            )

        _validate_contributor(connection, data.contributor_id, actor_id)

        changes = {
            field: {"before": current[field], "after": value}
            for field, value in data.model_dump(exclude={"row_version"}).items()
            if current[field] != value
        }

        updated = repository.update_request(
            connection, demand_id, AREA_ID, actor_id, data,
        )
        if updated is None:
            raise DemandConflictError(
                "A solicitação mudou. Reabra os detalhes antes de salvar novamente."
            )

        if changes:
            repository.add_history(
                connection, demand_id, actor_id, "updated", changes,
            )

        result = _detail(
            connection, demand_id, actor, permissions=permissions,
        )

    return result
```

Aqui, `_validate_contributor` e `_detail` seriam os auxiliares atuais convertidos em funções. `_detail` manteria as capacidades, a conversão de `row_version`, os anexos e o histórico.

**Essa função continuará relativamente extensa porque a operação tem regras reais.** Remover essas verificações para deixá-la curta seria uma perda funcional.

Para adaptar os módulos, eu faria uma entrega focada nesta sequência:

1. Converter os métodos dos dois Services em funções, preservando primeiro a distribuição atual das operações.
2. Passar engine, permissões, diretório e armazenamento somente às funções que precisam deles.
3. Atualizar as rotas e retirar os registros dos objetos de Service do bootstrap.
4. Transferir os mapas de ações para os módulos, preservando exatamente os acessos atuais.
5. Levar apenas as consultas claramente triviais às rotas.
6. Atualizar os três documentos e os exemplos de aprendizado para refletirem o código atual.

Não seria necessário trocar SQLAlchemy por ORM, criar `models.py`, alterar tabelas ou modificar os contratos do Vue por causa dessa reorganização.

Alguns cuidados específicos precisam orientar a mudança:

- **Presença:** preservar a verificação antes do LDAP, liberar a conexão durante a consulta externa e revalidar a lista com trava antes de gravar. Essa sequência existe no [Service de Eventos](../../../backend/modules/events/services.py).
- **PDF:** preservar a leitura consistente e gerar o documento depois de liberar conexão e travas.
- **Criação de Demandas:** manter `submission_key`, fingerprint, controle de repetição, histórico e compensação dos arquivos. Banco e filesystem continuam sem uma transação única; a política atual para falha de commit precisa ser preservada.
- **Edição de Demandas:** manter solicitante, estado, classificação, trava e `row_version`, inclusive as condições repetidas no SQL de atualização.
- **Downloads:** manter autorização da demanda antes de resolver o anexo e validar o caminho privado.
- **Contratos:** conservar URLs, métodos, status HTTP, campos, capacidades e detalhes de erro utilizados pelo frontend.

Há ainda duas limitações atuais que a simplificação não resolve automaticamente.

A primeira é que [`RolePermissions`](../../../backend/platform/identity.py) consulta permissões da sessão corrente pelo callback; o argumento `actor` não faz uma consulta às permissões daquele identificador. Passar um `Actor` diferente não torna essa política apropriada para jobs. A possibilidade futura de reutilização fora do HTTP depende de uma política compatível com esse contexto.

A segunda é que os requisitos desejados não equivalem a garantias já implementadas em todos os módulos. Demandas tem histórico de alterações e controle de versão na edição; não identifiquei proteção equivalente na edição de Eventos. A refatoração deve preservar o comportamento existente, enquanto eventuais melhorias ficam em tarefas próprias.

Na busca textual realizada, as tabelas modernas `DJ_DEMANDS` e relacionadas aparecem no módulo moderno; os jobs de demandas examinados trabalham com tabelas legadas `JDT_*`. Isso ajuda a delimitar a mudança, mas não comprova ausência de triggers, procedures ou consumidores externos.

O benefício esperado é **menos configuração por funcionalidade e um caminho mais fácil de compreender**, mantendo as regras nos lugares atuais. O principal risco é, durante a conversão, perder verificações, mudar limites de transação ou esconder dependências em acessos globais. Não há uma redução de código quantificada nem garantia de desempenho decorrente da troca de classes por funções.

Não alterei arquivos, não fiz pull ou commit e não executei migrations ou operações no banco. **O sistema não foi executado; a validação foi somente estática.** A equivalência funcional em IIS, LDAP, SQL Server, anexos e requisições concorrentes precisaria de verificação posterior em ambiente e escopo autorizados.
