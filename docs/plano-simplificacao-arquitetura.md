# Plano de simplificação da arquitetura do Digital JOST

**Situação:** simplificação aplicada ao código e à documentação; validação somente estática. Verificação funcional e publicação permanecem pendentes.

Este documento reúne a direção discutida para facilitar a criação de funcionalidades no backend moderno. O objetivo é reduzir configuração, navegação entre arquivos e decisões repetitivas, preservando contratos, regras de negócio e segurança.

Este documento começou como plano e agora também registra sua implementação. Services, rotas, composição e orientações foram adaptados sem alterar banco, contratos ou frontend. Execução, instalação, build, publicação e acesso corporativo continuam sujeitos às regras de [AGENTS.md](../AGENTS.md).

## 1. Resultado esperado

Uma funcionalidade simples deve permitir ao desenvolvedor acompanhar claramente:

```text
Requisição → validação e autorização → consulta ou gravação → resposta
```

Uma funcionalidade com regras deve acrescentar um ponto explícito de coordenação:

```text
Requisição → validação e autorização → Service funcional → Repository → resposta
```

O sucesso será medido pela facilidade de criar, explicar e alterar uma funcionalidade pequena. Reduzir linhas ou arquivos é um meio, não uma garantia de simplicidade.

## 2. Tecnologias e organização preservadas

- Monólito modular organizado por funcionalidades.
- `app/` como código legado durante a transição.
- `backend/` como backend moderno Flask/APIFlask, com Pydantic.
- SQLAlchemy e SQL Server, preservando o SQL parametrizado existente.
- `frontend/` com Vue 3 e os recursos compartilhados já adotados.
- Infraestrutura compartilhada para identidade, permissões, CSRF, erros, banco, paginação e shell Vue.
- Modernização gradual, sem reorganização ampla do legado.

Não faz parte desta mudança trocar tecnologias, introduzir ORM nos módulos atuais, criar um framework de CRUD, implantar descoberta automática de módulos ou adicionar um contêiner de injeção de dependências.

## 3. Mudanças adotadas

| Estado anterior | Direção aplicada |
|---|---|
| `EventsService` e `DemandsService` agrupam operações e guardam dependências | Converter seus métodos em funções de caso de uso |
| O bootstrap compõe e registra um objeto de Service por módulo | Retirar esses registros e manter a inicialização dos recursos necessários |
| Mapas de ações de Eventos e Demandas ficam no bootstrap | Aproximar os mapas da funcionalidade responsável |
| Todas as rotas desses módulos chamam os objetos de Service | Permitir acesso direto ao Repository em operações que atendam aos critérios deste plano |
| O documento arquitetural exige Service em toda mutação | Passar a admitir gravações simples nas rotas, com limites explícitos |
| Os exemplos principais envolvem módulos que já cresceram | Documentar um exemplo mínimo completo, atual e fácil de acompanhar |
| Guias apresentam estágios diferentes da modernização | Alinhar as orientações à arquitetura efetivamente adotada |

A conversão de classes em funções não implica remover regras, verificações, auxiliares ou exceções de domínio. Também não significa que todas as classes devam desaparecer.

## 4. Como escolher o caminho de uma operação

### 4.1. Consulta simples: Rota → Repository

Pode dispensar Service quando a rota apenas aplica a permissão da ação, recebe parâmetros validados, consulta dados e compõe uma resposta curta.

Não deve envolver autorização por registro, integração externa, leitura com coordenação especial de concorrência ou montagem de um caso de uso com várias regras.

Exemplo atual: listagem de tipos de Eventos.

### 4.2. Gravação simples: Rota com transação → Repository

Pode dispensar Service somente quando todas estas condições forem atendidas:

1. Não coordena várias gravações que precisam confirmar juntas.
2. Não envolve anexos, LDAP, e-mail, notificações ou outra integração.
3. Não decide transições de estado ou outras regras de negócio além da validação declarativa dos campos e da permissão da ação.
4. Não exige autorização específica sobre o registro, como vínculo de solicitante, responsável ou aprovador.
5. Não exige coordenação especial de concorrência, idempotência ou sequência de travas.
6. Não precisa compartilhar sua operação com jobs, páginas antigas ou outras entradas.
7. A sequência de autorização, transação, chamada ao Repository e resposta permanece evidente na rota.

Um cadastro independente com campos validados e um INSERT é um candidato, desde que seu comportamento real satisfaça esses critérios. Um único INSERT não basta para classificar uma operação como simples: pode haver regras, efeitos indiretos ou dependências a considerar.

Neste caminho, a rota controla a transação com o engine compartilhado. O Repository continua recebendo a conexão e executando SQL parametrizado, sem commit próprio. Metadados como autoria são definidos pelo servidor.

Não classificar uma operação pelo número de linhas ou apenas pelo verbo HTTP. Se algum critério não for atendido, usar Service funcional.

### 4.3. Caso de uso: Rota → Service funcional → Repository

Usar Service quando houver regras de negócio, autorização por registro, múltiplas gravações coordenadas, histórico transacional, anexos, integrações, concorrência especial, idempotência ou necessidade de reutilização fora da rota.

GET também pode precisar de Service. Download privado, exportação consistente e consultas com escopo por usuário são exemplos relevantes.

Se uma operação simples crescer, extrair seu caso de uso para Service preservando o contrato da API. Não manter duas implementações da mesma regra.

## 5. Estrutura dos módulos

```text
backend/
├── bootstrap.py
├── config.py
├── compatibility/
│   └── identity.py
├── platform/
│   ├── database.py
│   ├── identity.py
│   ├── http.py
│   ├── csrf.py
│   ├── schemas.py
│   ├── environment.py
│   └── vue_shell.py
├── integrations/
│   └── employee_directory.py
└── modules/
    ├── __init__.py
    └── minha_feature/
        ├── __init__.py
        ├── routes.py
        ├── schemas.py
        ├── repository.py
        └── services.py          # somente quando necessário
```

Esta árvore mostra as responsabilidades relevantes; não determina a criação de arquivos vazios. `domain.py`, `models.py`, `storage.py`, políticas e integrações específicas entram quando houver uma responsabilidade concreta.

Os arquivos adicionais atuais de Eventos e Demandas, como `attendance_pdf.py`, seus assets, `domain.py` e `storage.py`, permanecem necessários.

| Arquivo | Responsabilidade e limites |
|---|---|
| `__init__.py` do módulo | Exportar blueprints; não iniciar conexões, threads ou operações externas durante import |
| `routes.py` | HTTP, schemas, autorização de entrada, obtenção das dependências e resposta; pode controlar a transação de uma gravação simples |
| `schemas.py` | Contratos de entrada e saída, tipos, campos permitidos, limites e validações declarativas; sem consultas ao banco |
| `repository.py` | SQL parametrizado e mapeamento dos resultados; recebe conexão; não conhece Flask nem controla commits |
| `services.py` | Funções que coordenam regras, autorização do caso de uso, transações e integrações; sem dependência direta do contexto HTTP |
| `domain.py`, quando existir | Estados, limites, erros e regras próprias da funcionalidade |
| `storage.py` ou integração específica | Detalhes de arquivos ou acesso externo, separados das decisões do caso de uso |

Schemas não constituem uma camada linear de execução entre rota e Service. Eles definem e validam os contratos nas fronteiras apropriadas.

## 6. Services funcionais e dependências

Os métodos dos dois Services foram convertidos em funções com nomes específicos da operação. Cada função recebe somente as dependências que utiliza, por argumentos nomeados.

Assinaturas usadas pelas funções atuais:

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

As rotas obtêm o usuário autenticado e os recursos compostos pela aplicação. O Service recebe esses valores explicitamente; o Repository recebe a conexão que participa da operação.

Não buscar `request`, `current_user`, `current_app` ou engines globais dentro dos Services e repositórios. O acesso ao contexto Flask deve ficar na entrada HTTP e na infraestrutura destinada a atendê-la.

Manter classes que representam contratos ou adaptadores úteis, como modelos Pydantic, `Actor`, `RolePermissions`, `EmployeeDirectory` e `DemandAttachmentStorage`. Não convertê-las apenas para uniformizar a sintaxe.

Ao extrair auxiliares, preservar a sequência principal do caso de uso legível. Não dividir uma operação em muitas funções que apenas repassam argumentos.

## 7. Bootstrap, permissões e registro

O bootstrap continuará inicializando uma única vez o engine moderno, os adaptadores necessários, o shell Vue e o registro dos módulos. Não criará mais instâncias de `EventsService` e `DemandsService`.

O engine e os adaptadores com ciclo de vida da aplicação podem continuar em `app.extensions`. A simplificação retira o registro de objetos de Service; não elimina o mecanismo de extensões do Flask.

O acesso ao engine pela camada HTTP terá uma função pequena em `backend/platform/database.py`, aproveitando a chave `backend_td_engine` já existente. Essa função apenas recuperará o recurso inicializado; não criará engine, pool ou conexão global por módulo ou requisição.

Os mapas de ações ficarão no próprio módulo: em `routes.py` nos módulos mínimos ou em `domain.py` quando esse arquivo já existir e concentrar suas definições. Sua composição com `RolePermissions` deve ser curta e explícita, sem duplicar o mapa por endpoint. Preservar ações desconhecidas como negadas e todos os mapeamentos atuais.

Não armazenar usuário ou autorização específica de uma requisição em um objeto global compartilhado.

O registro dos blueprints continuará explícito em `backend/modules/__init__.py`, incluindo as entradas de API e shell necessárias. Uma funcionalidade comum não precisará de um novo registro de Service no bootstrap. Uma integração nova pode exigir composição explícita adicional; não prometer ausência total de configuração para todos os módulos.

## 8. Segurança e transações

Reutilizar os mecanismos existentes em vez de criar uma segunda infraestrutura:

- `configure_api` para autenticação, permissão geral, CSRF e erros modernos.
- `page_access` para as páginas Flask que entregam o shell.
- `RolePermissions` para ações, com autorização por registro nas operações que a exigirem.
- Schemas de entrada e saída, com os campos públicos definidos explicitamente.
- Engine moderno compartilhado, SQL parametrizado e limites de consulta.
- Cliente HTTP e componentes comuns do Vue conforme a necessidade da página.

A permissão geral do blueprint não substitui a autorização de cada ação. Capacidades exibidas ao frontend não substituem a autorização no backend.

Nas gravações simples, a rota abre a transação. Nos casos de uso, o Service abre a transação. Todas as gravações que precisam confirmar juntas usam a mesma conexão. Repositórios não abrem transações independentes nem fazem commits ocultos.

Preservar rollback, condições de atualização, travas e tratamento de conflitos. Não transformar uma leitura seguida de escrita em uma sequência vulnerável à concorrência ao redistribuir funções.

Uma falha na resposta depois do commit não desfaz uma gravação. Preservar o tratamento de resultado incerto e impedir repetições automáticas indevidas no frontend.

Transações SQL não tornam atômicos filesystem e serviços externos. A refatoração manterá as estratégias de compensação e recuperação existentes.

`RolePermissions` atualmente consulta a sessão corrente por callback; receber um `Actor` não significa consultar as permissões daquele identificador. O uso futuro por jobs exige uma política adequada ao contexto, sem simular uma sessão HTTP.

## 9. Adaptação de Eventos

| Operação | Destino aplicado |
|---|---|
| Listar tipos | Rota → Repository |
| Listar e detalhar eventos | Manter funções de Service nesta adaptação |
| Criar, atualizar e excluir eventos | Service funcional |
| Criar e excluir tipos | Service funcional, preservando concorrência e verificação de uso |
| Consultar listas de presença e participantes | Service funcional, preservando a verificação dos vínculos |
| Criar, renomear e excluir listas; excluir participantes | Service funcional |
| Registrar presença | Service funcional com diretório explícito |
| Exportar PDF | Service funcional com renderização separada |

Não deslocar todas as consultas para as rotas para demonstrar o caminho simples. Listagem e detalhe de eventos já coordenam horário do TD, resposta e capacidades; sua conversão em funções basta nesta etapa.

Preservar especialmente:

- Validação de início e fim, tipo existente e autoria definida pelo servidor.
- Horário do TD e semântica atual das datas e dos status.
- Filtros, ordenação, paginação, limites e retorno das capacidades.
- Verificações de vínculo entre evento, lista e participante.
- Travas e tratamento de exclusão de tipos em uso.
- Verificação da lista antes de consultar o LDAP, sem manter conexão ou trava SQL durante a consulta externa.
- Revalidação com trava depois do LDAP e tratamento de leituras repetidas.
- Leitura consistente dos dados do PDF e renderização depois de liberar a conexão.
- Contratos de erro, respostas de criação e proteção da exportação.

Esta mudança não introduz automaticamente auditoria detalhada ou controle de versão na edição de Eventos. Melhorias funcionais ou de segurança adicionais serão tratadas em escopo próprio.

## 10. Adaptação de Demandas

| Operação | Destino aplicado |
|---|---|
| Listar colaboradores elegíveis | Rota → Repository, exigindo `demands.create` |
| Listar solicitações | Service funcional com escopo do usuário |
| Detalhar solicitação | Service funcional com capacidades, anexos e histórico |
| Criar solicitação | Service funcional com armazenamento explícito |
| Editar solicitação | Service funcional com autorização, concorrência e histórico |
| Baixar anexo | Service funcional com autorização e resolução do arquivo |

Preservar especialmente:

- Área atendida e visibilidade somente para solicitante ou colaborador, inclusive os filtros no SQL.
- Validação do colaborador elegível e regras de edição pelo solicitante.
- Estado `em_analise`, classificação e `row_version` na atualização.
- Histórico na mesma transação das alterações correspondentes.
- `submission_key`, fingerprint e reconhecimento de repetição de um envio.
- Contrato multipart, campos, tipos e limites de anexos e requisição.
- Nomes seguros, chaves de armazenamento e acesso privado aos documentos.
- Compensação restrita aos arquivos novos da operação e política atual diante de falha no commit.
- Autorização da solicitação antes de buscar e resolver o anexo.
- Retorno de `row_version`, capacidades, histórico e anexos no formato atual.

A criação continuará mostrando sua sequência principal: autorizar, preparar arquivos, reconhecer repetição, validar colaborador, gravar solicitação, salvar anexos e registrar histórico, respeitando as ramificações e os limites de transação atuais.

Não migrar dados, anexos ou fluxos legados como parte desta reorganização. A busca textual anterior identificou os jobs examinados usando tabelas legadas `JDT_*`; isso não comprova ausência de consumidores externos, triggers ou procedures sobre as tabelas modernas.

## 11. Contratos e frontend

A adaptação deve preservar URLs, métodos HTTP, nomes de blueprints e endpoints, payloads, códigos de resposta, paginação, capacidades e detalhes de erros consumidos pelo Vue.

Também deve preservar sessão, cabeçalho `X-CSRF-Token`, emissão do token pelo shell e compatibilidade de sessão já existente. Não alterar mapeamentos de acesso como parte da simplificação.

Não há mudança funcional planejada no Vue para acompanhar a conversão dos Services. O registro de novas páginas no Vue Router e das entradas Flask para acesso direto e F5 continua necessário.

## 12. Experiência de criação de uma funcionalidade

O roteiro mínimo será:

1. Definir contrato, tabela existente, ação permitida e escopo dos registros.
2. Classificar cada operação pelos critérios da seção 4.
3. Criar `__init__.py`, `routes.py`, `schemas.py` e `repository.py` quando necessários.
4. Acrescentar `services.py` apenas para os casos de uso que o exigirem.
5. Aplicar as proteções compartilhadas e registrar os blueprints em um único ponto.
6. Quando houver tela, criar a feature Vue, reutilizar o cliente HTTP e registrar a navegação e a entrada Flask.
7. Conferir contratos, referências, regras e diff por análise estática.

O exemplo didático completo de consulta e cadastro simples está na seção 7 da [base compartilhada](base-compartilhada-novas-features.md). Ele documenta os quatro arquivos mínimos, segurança, transação e registro do módulo; não foi criado como módulo ativo.

Um exemplo de equipamentos pode ser apresentado como código documentado. Não criar tabela, módulo ativo ou funcionalidade artificial em produção apenas para demonstrar a arquitetura. Se o exemplo exigir persistência nova, sua implementação e seu schema terão escopo próprio.

Não exigir configuração de autenticação, CSRF, pool ou objeto de Service para cada nova funcionalidade comum. As permissões específicas e os contratos continuam sendo responsabilidade explícita do módulo.

## 13. Etapas da adaptação

### Etapa 1 — regras e guias alinhados

Foram atualizados de forma localizada:

- [AGENTS.md](../AGENTS.md), para reconhecer a arquitetura moderna em `backend/`, o frontend Vue e a exceção de transação na rota para gravações simples.
- [Arquitetura e modernização](arquitetura-modernizacao.md), principalmente responsabilidades e critérios de complexidade progressiva.
- [Plano de separação do legado](plano-separacao-backend-legado.md), para atualizar a orientação de composição sem apagar o histórico das entregas.
- [Base compartilhada](base-compartilhada-novas-features.md), para oferecer o roteiro mínimo e exemplos atuais.

As orientações anteriores atribuíam transações aos Services e exigiam Service em toda mutação. AGENTS.md e o documento arquitetural agora admitem a exceção para gravações simples pelos critérios da seção 4. Não foi deslocada nenhuma gravação complexa de Eventos ou Demandas para as rotas.

A proibição de executar o sistema e as demais restrições operacionais foram preservadas. As duas análises anteriores são registros da discussão; este documento consolida a direção adotada e o resultado da adaptação.

### Etapa 2 — composição simplificada e Services convertidos

`get_td_engine()` recupera o engine já inicializado. Os mapas de ações ficam em `events/routes.py` e `demands/domain.py`; as rotas compõem `RolePermissions` por chamada. Os métodos foram convertidos em funções e os registros `events_service` e `demands_service`, junto do acesso `get_service`, foram retirados após atualizar seus consumidores.

Engine, adaptadores e registro explícito dos módulos foram mantidos. O diretório permanece em `app.extensions["backend_employee_directory"]`, e o armazenamento em `app.extensions["demands_attachment_storage"]`; somente as rotas que os utilizam os fornecem aos Services. Não foram acrescentadas inicializações externas no import.

### Etapa 3 — consultas escolhidas adaptadas

As listagens de tipos de Eventos e de colaboradores de Demandas passaram às rotas, preservando permissões, schemas e respostas. As demais operações permanecem em Services funcionais.

A permissão para gravações simples foi documentada e demonstrada no exemplo mínimo; não foi usada para reclassificar operações complexas já existentes.

### Etapa 4 — referência de desenvolvimento documentada

A base compartilhada mostra consulta, cadastro simples, schemas, SQL parametrizado, registro e critérios para extrair Service, utilizando os recursos finais. A tabela e o módulo do exemplo são fictícios e não foram criados ou registrados.

### Etapa 5 — revisão estática e verificação funcional pendente

A adaptação foi revisada estaticamente; a seção 14 registra os cenários funcionais pendentes. Qualquer execução ou publicação depende do comando, ambiente e escopo explicitamente autorizados pelo responsável. O registro da seção 17 do plano de separação lista os arquivos do backend que devem acompanhar a publicação e o retorno.

As etapas organizam o trabalho e não determinam quantidade de commits. Seguir o fluxo Git vigente; não criar branches, PRs, commits adicionais ou fazer push por iniciativa própria.

## 14. Verificação e critérios de aceite

### Conferência estática

- Somente arquivos necessários à adaptação foram alterados.
- Não há referências restantes aos registros de Service retirados.
- Engine e adaptadores mantêm inicialização explícita e não são recriados por request.
- Cada operação conserva autorização, contrato e limite de transação identificáveis.
- Repositórios continuam sem Flask, commits próprios ou SQL com entrada interpolada.
- As consultas diretas preservam a ação correta e os schemas existentes.
- As regras especiais das seções 9 e 10 permanecem rastreáveis.
- Documentos e exemplos apresentam o mesmo padrão.
- Diff e referências foram inspecionados; `git diff --check` foi conferido.
- Não há segredos ou dados operacionais incluídos.

### Verificações funcionais posteriores, em ambiente autorizado

Conferir sessão, acesso permitido e negado, CSRF, validação e contratos de erro; filtros e paginação; gravação e rollback; edição concorrente e repetição de envio em Demandas; acesso e limites de anexos; registro de presença com LDAP e exclusão concorrente de lista; exportação de PDF; navegação, F5 e compatibilidade com o legado.

Esses cenários não autorizam criar dados, consultar serviços ou executar ferramentas. O ambiente, os dados e os comandos precisam estar no escopo autorizado. A revisão estática não comprova equivalência funcional.

## 15. Fora do escopo desta simplificação

- Mudanças de schema, migrations, procedures, triggers ou dados.
- Movimentação de uploads ou anexos existentes.
- Alteração de regras, permissões, estados ou contratos de API por conveniência.
- Novas funcionalidades de Eventos ou Demandas.
- Correções amplas de segurança do legado, tratadas em tarefas próprias.
- Mudança de hospedagem, autenticação ou infraestrutura corporativa.
- Instalação, execução, testes dinâmicos, builds e publicação sem autorização específica.

O ganho esperado é reduzir o esforço de começar uma feature e tornar o caminho de cada operação mais compreensível. Não há promessa de redução percentual de código ou melhoria de desempenho. As regras reais dos módulos continuarão existindo.

## 16. Referências e situação desta entrega

- [Primeira avaliação](avaliacao-simplificacao-arquitetura.md).
- [Segunda avaliação, focada na facilidade de desenvolvimento](segunda-avaliacao-simplificacao-arquitetura.md).
- [Composição atual do backend](../backend/bootstrap.py).
- [Eventos](../backend/modules/events/services.py) e [Demandas](../backend/modules/demands/services.py).

Nesta entrega foram adaptados os dois módulos modernos, a composição e os guias. Os repositórios, schemas, frontend, banco e arquivos operacionais foram preservados. Não foram executados imports, testes, builds, consultas, migrations, integrações ou publicação. A equivalência funcional depende das verificações autorizadas da seção 14.

**O sistema não foi executado; a validação foi somente estática.**
