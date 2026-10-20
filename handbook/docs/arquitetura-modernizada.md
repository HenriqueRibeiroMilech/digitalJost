# Arquitetura e modernização

Referência oficial da organização atual do Digital JOST, revisada em **20/10/2026** por comparação textual entre código, contratos e documentos anteriores. Explica como desenvolver e migrar funcionalidades. Exemplos completos da infraestrutura ficam em [Base compartilhada](../features/base-compartilhada.md).

**Limite da revisão:** implementação no repositório, schema aplicado e versão publicada são estados diferentes. Este guia confirma a organização observada no código; não certifica o ambiente corporativo ou a ausência de defeitos.

## 1. Como o sistema se organiza

O Digital JOST é um monólito Flask/APIFlask no Windows/IIS. O legado Jinja e as APIs modernas pertencem à mesma aplicação e compartilham a identidade e a sessão existentes.

```text
Navegador → IIS / autenticação Windows → main.py → app/config.py
    ├── app/                  rotas, páginas, integrações e jobs legados
    └── backend/              APIs modernas e shell que carrega o Vue
          ├── modules/        funcionalidades
          ├── platform/       banco, HTTP, identidade, CSRF, paginação e shell
          ├── compatibility/  ponte com a identidade do legado
          └── integrations/   adaptadores modernos, como o diretório de funcionários

frontend/src/ → build → backend/static/app/ → /static/app/
```

`main.py` registra os blueprints antigos. A factory chama `backend/bootstrap.py`, que inicializa recursos e usa `backend/modules/__init__.py` para registrar explicitamente os módulos modernos. Não há descoberta automática de funcionalidades.

### Inicialização e entradas

1. `main.py` importa `create_app` e os blueprints legados. Imports antigos podem produzir efeitos antes de receber qualquer requisição.
2. `app/config.py` cria `APIFlask(json_errors=False)`, configura Flask-SQLAlchemy, Mail, Login e Principal e registra os ciclos globais e erros. A aplicação continua sendo a mesma para HTML e API.
3. A factory ainda chama `db.create_all()` e depois `init_backend(app, config=BackendConfig.from_env())`.
4. O bootstrap inicializa o engine moderno do TD, compõe diretório LDAP e armazenamento de anexos, registra os recursos do shell e os módulos.
5. Ao retornar da factory, `main.py` registra os blueprints antigos restantes. Desativação de registro não significa necessariamente ausência de import.

| Entrada atual | Responsabilidade |
|---|---|
| `/` e URLs antigas | Páginas Flask/Jinja e operações já existentes. |
| `/app/` | Redirecionamento autorizado para Eventos. |
| `/app/eventos` | Entrada Flask do Vue de Eventos. |
| `/app/demandas/solicitacoes` | Entrada Flask das solicitações modernas. |
| `/api/v1/events`, `/api/v1/demands` | Contratos JSON e operações dos módulos. |
| `/static/app/` | Assets públicos compilados, servidos pelo blueprint `backend_vue`. |

Vue Router usa a base `/app/`, mas não configura sozinho uma rota no servidor. Sua página de URL desconhecida cobre navegação já carregada; não existe um catch-all Flask genérico para todas as URLs Vue. Cada entrada direta precisa ser registrada e autorizada.

## 2. Estrutura de uma funcionalidade

```text
backend/modules/<feature>/
├── __init__.py       # exporta os blueprints
├── routes.py         # HTTP, schemas, autorização e dependências
├── schemas.py        # contratos Pydantic de entrada e saída
├── repository.py     # SQL parametrizado; recebe uma conexão
├── services.py       # funções de caso de uso, quando necessárias
└── domain.py         # definições e erros, quando necessários

frontend/src/features/<feature>/
├── pages/
├── components/
├── api.ts
└── types.ts
```

Criar somente os arquivos que tenham responsabilidade real. `models.py`, armazenamento, políticas e integrações específicas entram quando necessários. Não criar classes base de CRUD, arquivos vazios ou uma segunda implementação de infraestrutura.

| Arquivo/camada | Deve fazer | Deve evitar |
|---|---|---|
| `routes.py` | Adaptar HTTP, aplicar schemas/guardas, compor dependências, traduzir erros e devolver resposta. | SQL, lógica extensa ou decidir privilégios a partir do navegador. |
| `schemas.py` | Definir campos, tipos, limites, normalizações e modelos públicos. | Acessar banco ou integrar sistemas para validar um campo. |
| `services.py` | Exigir ação, conferir regras/vínculos, coordenar transação e efeitos do caso de uso. | Ler sessão/request ou criar engine/cliente global. |
| `repository.py` | Executar SQL parametrizado usando a conexão recebida e retornar dados. | Flask, commits próprios, selecionar usuário ou criar transação independente. |
| `domain.py` | Regras puras, opções, constantes e erros que justifiquem agrupamento. | Virar requisito para um módulo pequeno. |
| Adaptador local | Encapsular armazenamento ou integração com contrato explícito. | Expor credenciais, caminho privado ou cliente externo na API. |
| Página Vue | Coordenar navegação, consultas, mutações e feedback. | Ser a única barreira de autorização ou recalcular a verdade persistida. |
| Componente Vue | Apresentar/interagir com uma parte da feature; receber dados e emitir ações. | Buscar dados de vários domínios sem responsabilidade definida. |

O Repository pode usar funções comuns e SQL textual. Não há obrigação de converter tabelas corporativas em models ORM. Classes de schema, configuração, resultado e adaptadores continuam adequadas; a simplificação removeu a obrigação de objetos de Service, não o uso de classes em Python.

## 3. Qual caminho usar

| Operação | Caminho e responsabilidade |
|---|---|
| Consulta simples | Rota → Repository; a rota exige a ação e compõe a resposta. |
| Gravação simples | Rota com transação → Repository; autorização, schemas e CSRF permanecem obrigatórios. |
| Caso de uso | Rota → Service funcional → Repository/integração; o Service coordena regras e transações. |

Uma gravação só pode dispensar Service se não coordenar várias gravações, arquivos ou integrações; não decidir transições ou regras além da validação declarativa dos campos e da permissão da ação; não exigir autorização por registro, idempotência ou concorrência especial; e não precisar ser reutilizada por outra entrada. A sequência deve continuar clara na rota. Se algum critério falhar, usar Service. GET também pode precisar de Service.

Rotas não contêm SQL. Repositórios não conhecem Flask, não decidem o usuário autenticado e não executam commits próprios. Services recebem identidade e dependências explicitamente, sem acessar `request`, `current_user` ou `current_app`. Schemas delimitam os contratos; não substituem regras dependentes do banco ou autorização.

### Exemplos que orientam a decisão

- **Tipos de Eventos e contribuintes elegíveis:** consultas diretas nas rotas, com autorização e conexão comuns. Não se criou Service que apenas repassaria a chamada.
- **Listar Eventos:** continua em Service porque combina o horário de referência do TD, filtros/status e capacidades. Ser GET não obriga a simplificar para uma única consulta.
- **Criar ou editar evento:** Service confere período e tipo antes de gravar, na transação apropriada.
- **Registrar presença:** exige vínculo, LDAP fora da conexão SQL e nova validação sob trava. É um caso de uso mesmo com um cadastro pequeno.
- **Consultar uma demanda ou baixar anexo:** leitura com escopo por registro e, no download, proteção do caminho. Permanece em Service.
- **Cadastro hipotético sem essas regras:** pode ir diretamente ao Repository, desde que a rota autorize, valide e delimite a transação. Não há uma gravação atual desses módulos que precise ser movida para a rota para cumprir o padrão.

A quantidade de arquivos e o número de linhas não são critérios isolados. Extrair uma função quando der nome a uma responsabilidade real; compartilhar código quando existir um contrato comum compreensível. Manter uma pequena diferença entre módulos costuma ser mais claro que configurar um CRUD universal.

## 4. Recursos compartilhados e consistência

O bootstrap cria um engine/pool moderno do TD por instância da aplicação. Todos os módulos modernos o reutilizam; cada operação abre e encerra sua conexão. O legado mantém mecanismos próprios para TD e outras fontes. Conexões diferentes não formam uma transação única.

Nas rotas, `get_td_engine()` recupera o recurso já inicializado. `_service_deps()` pode reunir dependências repetidas dentro do próprio módulo; o usuário e os adaptadores especiais permanecem visíveis nas chamadas. Não registrar objetos de Service por feature nem guardar dados de uma requisição globalmente.

Os casos de uso abrem a transação com `engine.begin()`; nas gravações simples, a rota faz isso. Todas as alterações atômicas usam a mesma conexão. Preservar travas, versões de edição, histórico e idempotência existentes. Commit SQL não torna arquivos, e-mails ou LDAP atômicos; essas operações exigem tratamento próprio de falhas.

### Ciclo das dependências

| Recurso | Vida e acesso |
|---|---|
| Engine TD | Um por instância da aplicação em `backend_td_engine`; conexão emprestada a cada operação. |
| `RolePermissions` | Composto na rota com a ponte de identidade e o mapa de ações local. |
| `EmployeeDirectory` | Adaptador por aplicação; abre/encerra LDAP somente na consulta de presença. |
| `DemandAttachmentStorage` | Adaptador por aplicação; compõe o caminho sem criar diretório no startup. |
| Estado do formulário/cache Vue | Da interface; não representa confirmação de commit nem fonte de autorização. |

O pool moderno tem, por padrão, cinco conexões, sem overflow, espera de 30 segundos e reciclagem de 1.800 segundos; utiliza pre-ping e oculta parâmetros nos erros SQLAlchemy. Mais processos significam mais pools. Não descartar o engine no teardown da requisição. Alterar esses limites exige analisar o consumo total, inclusive os pools legados.

Uma consulta e sua contagem podem observar alterações entre comandos; usar a mesma conexão não promete snapshot para toda leitura. Quando o domínio exige consistência especial, ela precisa ser projetada: PDF e escritas de presença usam travas; Demandas usa trava e versão na edição. Não generalizar essas garantias para todas as operações.

## 5. Segurança e convivência

- A ponte de identidade reutiliza Flask-Login e os perfis antigos. `configure_api` aplica autenticação, perfil geral e CSRF; a ação e o acesso ao registro continuam explícitos no backend.
- `RolePermissions` consulta a sessão corrente. Passar outro `Actor` não consulta as permissões daquele identificador; jobs exigem política apropriada ao contexto.
- O frontend recebe apenas contratos públicos. Botões e capacidades não autorizam operações. Arquivos privados exigem autorização e contenção do caminho.
- Configuração privada vem do ambiente/arquivo separado, nunca do Vue ou de valores copiados para os módulos.
- O legado ainda possui efeitos na inicialização, incluindo `db.create_all()` e imports com threads/acesso externo. A base moderna não torna a aplicação inteira isolada.

Riscos conhecidos do legado — autenticação de fallback, flags textuais, SQL interpolado, `eval`, CSRF irregular, arquivos, logs e segredos históricos — não foram resolvidos apenas pela separação de pastas. O [levantamento anterior](../historico/docs/revisao-seguranca-modernizacao.md) preserva evidências e prioridades; sua situação efetiva deve ser conferida antes de uma correção específica.

### Fronteiras que precisam permanecer explícitas

**Identidade e autorização.** Windows/IIS e o login antigo estabelecem a sessão; Flask-Principal resolve os perfis a partir do cadastro compartilhado. Não criar outro login para o Vue. Os módulos atuais mapeiam suas ações para GENERAL, mas as regras por registro são diferentes: Eventos verifica vínculos de recursos; Demandas restringe também por participantes e área. Não existe regra geral de que apenas o autor possa editar todo registro moderno.

**Contratos e erros.** A API usa Pydantic e `{message, detail}`. O prefixo `/api/v1` tem uma ponte nos erros globais para evitar HTML em 404/405/500. `json_errors=False` preserva os fluxos antigos fora desse prefixo. Capacidade retornada ao Vue controla apresentação; o backend autoriza novamente cada operação.

**Auditoria.** O ciclo global de acesso continua ligado ao legado. Demandas possui histórico transacional de criação/edição; Eventos armazena autoria/data de criação, sem histórico equivalente de todas as alterações. Não chamar isso de uma auditoria de negócio completa para qualquer módulo.

**Configuração.** `environment.py` é compartilhado com os consumidores antigos; ler configuração não conecta o banco por si só. A inicialização completa continua alcançando constantes, threads e integrações antigas. Não basta apontar um Service para uma dependência falsa para garantir isolamento de toda a aplicação.

**Arquivos e frontend.** Assets Vue são públicos; anexos de Demandas são privados. Variáveis de build e JavaScript entregue ao navegador não armazenam segredos. Manter texto como texto, escapar markup nos exports e revalidar IDs/vínculos no backend.

## 6. Como evoluir

1. Delimitar a funcionalidade: URLs, métodos, contratos, ações, registros, tabelas, arquivos, integrações e jobs.
2. Escolher o caminho de cada operação e reutilizar a [base compartilhada](../features/base-compartilhada.md).
3. Manter regras e consultas junto do módulo, com frontend na feature correspondente.
4. Registrar blueprints e navegação explicitamente; uma rota Vue também precisa de entrada Flask para acesso direto e F5.
5. Conferir referências, contratos e diff. Verificação funcional e publicação exigem ambiente e escopo autorizados.
6. Na migração, considerar leitores e escritores antigos, retorno de versão e compatibilidade de dados. Não mover o legado inteiro por estética.

Atualmente [Eventos](../features/eventos.md) e [Solicitações de Demandas](../features/demandas.md) usam essa estrutura. Não há migração automática das solicitações antigas nem um gerenciador moderno completo.

### Migrar uma parte legada

Rastrear menu/URL, todos os métodos e seletores de operação, template, JavaScript incluído ou estático, payload, tabelas, arquivos e jobs. Ler apenas o GET da página deixa de fora grande parte das regras antigas. Confirmar quais registros e contratos terão de conviver durante a entrega.

Uma migração deve definir: quem continua escrevendo nos mesmos dados; como impedir execução duplicada; quais permissões e efeitos preservar; qual código e build precisam ser publicados juntos; e como retornar sem apagar dados. Não renomear rotas/tabelas ou remover o leitor antigo só porque existe uma página nova.

Se a alteração permanecer em Flask/Jinja, seguir o padrão legado de [AGENTS.md](../../AGENTS.md): rotas/Services/Repository junto da feature, HTML estrutural em templates, CSS e JavaScript em static. JavaScript já incluído por Jinja pode depender de variáveis do template; mover exige adaptar esses valores, não apenas trocar de pasta.

Concluir a migração só depois de conferir consumidores antigos, jobs e dados, obter validação no ambiente autorizado e atualizar navegação/manual. Uma tela visualmente moderna não comprova a retirada do fluxo antigo.

### Próximas melhorias, ainda pendentes

| Frente | Situação e limite |
|---|---|
| Validar reutilização | A segunda feature já existe: Demandas. Evoluir a base a partir das repetições reais dessas duas implementações. |
| Testes isolados | Services aceitam dependências explícitas, mas ainda é necessário preparar entradas sem imports/startup corporativo. Não executar a aplicação para descobrir testes. |
| Inicialização | Separar gradualmente DDL, threads e integrações do carregamento; exige escopo próprio. |
| Permissões fora do HTTP | Projetar política para jobs/outros atores; `RolePermissions` atual depende da sessão. |
| Operação e segurança | Evoluir diagnóstico sem segredos, identificação da versão publicada, publicação offline e correções por domínio. |
| Automação | Avaliar geração de tipos/modelo de feature quando o custo de repetição justificar manter uma ferramenta. Não é requisito atual. |

Separar totalmente o backend de `app/`, migrar o gerenciador completo ou trocar a hospedagem não foi realizado pela simplificação.

## 7. Onde consultar e atualizar

| Assunto | Referência |
|---|---|
| Recursos comuns, contratos HTTP e exemplos | [Base compartilhada](../features/base-compartilhada.md) |
| Componentes e comportamento visual | [Padrão visual](padrao-visual.md) |
| Ambiente, configuração, build e IIS | [Servidor e publicação](servidor-e-publicacao.md) |
| Envio de versões ao repositório Azure | [Publicação no Azure DevOps](publicacao-azure.md) |

Atualizar este arquivo quando mudar uma regra geral. Campos, endpoints e detalhes de uma funcionalidade ficam no documento dela. Planos e estudos anteriores estão no [histórico](../historico/README.md), sem substituir esta referência.

Fontes principais: [entrada](../../main.py), [bootstrap](../../backend/bootstrap.py), [registro dos módulos](../../backend/modules/__init__.py) e [roteador Vue](../../frontend/src/router/index.ts). As restrições de execução permanecem em [AGENTS.md](../../AGENTS.md).

Foram confrontados também a [arquitetura anterior](../historico/handbook/arquitetura-modernizada.md), o [plano de separação](../historico/docs/plano-separacao-backend-legado.md) e o [plano de simplificação](../historico/docs/plano-simplificacao-arquitetura.md). Instruções antigas sobre `app/modules`, `EVENTS_ENABLED`, Services registrados no bootstrap e engine recebido de `db.engine` não descrevem o estado atual.

**O sistema não foi executado; a validação foi somente estática.**
