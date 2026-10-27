# Proposta de arquitetura próxima ao curso de Flask

**Situação: direção implementada no código de Eventos e Solicitações de Demandas; validação funcional e publicação pendentes.** Este documento registra a aproximação aos conhecimentos das [anotações do curso](../../curso_notion/), buscando menos arquivos obrigatórios, menos código repetitivo e operações fáceis de acompanhar.

O escopo é a arquitetura nova em `backend/`, no estado após o revert do painel moderno de gestão de Demandas. A [arquitetura vigente](arquitetura-modernizada.md) e a [base compartilhada](../features/base-compartilhada.md) descrevem a implementação, e o [AGENTS.md](../../AGENTS.md) continua definindo as regras operacionais. A migração de código não comprova funcionamento no ambiente nem autoriza executar o sistema.

## 1. Decisão principal

**Manter a organização por feature, adotar SQLAlchemy ORM como padrão e concentrar a sequência das operações nas rotas, sem Service ou Repository obrigatórios.**

Uma rota pode receber os dados, conferir permissões, aplicar regras, consultar ou alterar entidades, controlar a transação e preparar a resposta. Ter regra de negócio, autorização por registro ou mais de uma gravação não obriga, por si só, a criar outro arquivo.

Funções auxiliares entram quando dão nome a uma etapa, evitam repetição ou tornam a operação mais fácil de compreender. Começam próximas das rotas que as utilizam. A extração para um arquivo próprio depende de uma responsabilidade clara, volume ou reutilização real.

O objetivo é facilitar o desenvolvimento para quem mantém o JOST. Uma chamada direta e algumas linhas repetidas podem ser mais compreensíveis que um helper genérico com várias opções.

### O que muda em relação ao padrão atual

| Aspecto | Direção proposta |
|---|---|
| Estrutura mínima | `__init__.py`, `routes.py`, `schemas.py` e `models.py`, quando houver persistência ORM. |
| Caminho mais comum | Rota → ORM → resposta. |
| Regras da operação | Podem ficar na rota ou em funções auxiliares locais. |
| Service | Deixa de ser camada exigida; uma função de operação pode ser extraída quando ajudar. |
| Repository | Deixa de ser passagem obrigatória; consultas comuns ficam próximas das operações. |
| Acesso ao banco | ORM como primeira opção, com expressões SQLAlchemy para filtros, joins e operações específicas. |
| Infraestrutura | Banco, segurança, erros e contratos comuns reutilizados em todas as features. |
| Dependências | Aproveitar SQLAlchemy, APIFlask e Pydantic já presentes no projeto. |

## 2. Relação com o curso

| Conhecimento do curso | Aplicação no backend novo |
|---|---|
| Application Factory | A aplicação continua montando e registrando seus recursos explicitamente. |
| Blueprints | Cada feature disponibiliza seus blueprints para registro. |
| Funções de rota | São a entrada principal para entender o fluxo de cada operação. |
| Modelos Pydantic | Permanecem em `schemas.py`, com campos, tipos e validações. |
| Consulta e gravação na rota | São feitas por uma sessão ORM com ciclo e transação definidos. |
| Decorators | Reduzem repetição de validação e autorização, mantendo a ação visível. |

No curso, `db.products.find()` é uma chamada à interface do MongoDB. No JOST, SQLAlchemy ORM permite trabalhar com classes e atributos Python sobre o SQL Server. Essa é uma ferramenta adicional ao conhecimento do curso, sem necessidade de trocar o banco.

Os dois tipos de modelo continuam distintos: **Pydantic define os dados aceitos e devolvidos pela API; ORM representa tabelas e relacionamentos**. Entrada, persistência e resposta podem compartilhar conceitos, mas seus campos e permissões de alteração nem sempre coincidem.

## 3. Organização por feature

```text
backend/
├── bootstrap.py          # prepara recursos e registra o backend na aplicação
├── config.py             # configuração do backend
├── platform/             # banco, HTTP, CSRF, identidade e recursos comuns
├── compatibility/        # ponte com a sessão e as permissões existentes
├── integrations/         # adaptadores externos, como LDAP
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

Essa árvore representa a organização implementada. Em Demandas, a área e as permissões ficam nas rotas, os limites de anexos ficam em `storage.py` e os erros usam o `ApiProblem` compartilhado, sem precisar de `domain.py`. Features sem persistência não precisam de `models.py`. Arquivos de PDF, armazenamento ou integração existem porque cumprem responsabilidades específicas.

`services.py` e `repository.py` não fazem parte da estrutura mínima. Os quatro arquivos desses nomes em Eventos e Demandas foram retirados após transferir as operações para rotas/auxiliares ORM e conferir referências. Em futuras migrações, retirar um arquivo somente depois de transferir todas as responsabilidades.

| Arquivo básico | Responsabilidade |
|---|---|
| `__init__.py` | Disponibilizar os blueprints, sem executar configuração ou acessar recursos externos. |
| `routes.py` | Definir endpoints, mostrar a sequência das operações e suas funções auxiliares. |
| `schemas.py` | Declarar campos, tipos, normalizações e contratos públicos com Pydantic. |
| `models.py` | Mapear tabelas e relacionamentos com ORM, sem commits ou integrações externas. |

Preservar os nomes atuais de módulos, URLs, tabelas e blueprints. A convivência com o legado e os contratos do frontend permanece; esta proposta não inclui reestruturar `app/` ou o Vue.

## 4. Como escrever as rotas

A sequência deve permitir acompanhar a operação de cima para baixo:

```text
Autenticação e proteção HTTP
  → validação da entrada e autorização da ação
  → sessão e transação apropriadas
  → autorização por registro e regras da operação
  → consulta ou alteração ORM
  → preparação dos dados públicos
  → confirmação da transação
  → resposta HTTP
```

Leituras não precisam de commit. Integrações e arquivos podem exigir etapas fora da transação; a sequência de cada operação deve preservar esse comportamento.

### Exemplo de leitura

Este é um recorte da listagem de tipos de Eventos. Os imports, o modelo `EventType` e a configuração de `permissions` e `require_action` estão nos arquivos reais. `action_access`, `ApiProblem` e `get_td_session_factory` foram implementados na plataforma compartilhada.

```python
@events_bp.get("/types")
@require_action("events.read")
@events_bp.output(EventTypes)
def list_event_types():
    sessions = get_td_session_factory()
    with sessions() as session:
        query = select(EventType.id, EventType.name).order_by(
            EventType.name,
            EventType.id,
        )
        items = [dict(row) for row in session.execute(query).mappings()]

    actor = identity.current_actor()
    return {
        "items": items,
        "can_create": permissions.can(actor, "events.types.create"),
        "can_delete": permissions.can(actor, "events.types.delete"),
    }
```

O blueprint continua protegido por `configure_api`. O decorator de ação complementa essa proteção. O resultado mantém os campos, a ordem e as capacidades atuais, sem devolver colunas internas ou depender de carregamentos depois do fechamento da sessão.

### Escritas e funções auxiliares

Na criação de um evento, validar período, conferir o tipo e preencher autoria pode ficar na própria rota. Preservar as proteções de concorrência da consulta do tipo e preparar a resposta antes de fechar a sessão.

Nas operações maiores, usar funções com nomes concretos para as etapas que mereçam separação. Cada função recebe os dados e a sessão necessários, sem abrir outra transação nem fazer commit independente. Se uma função for extraída para reutilização fora do HTTP, passar também identidade e dependências explicitamente.

Evitar helpers que recebam o nome da feature, da operação e vários sinalizadores para decidir o que executar. Não é necessário construir um framework de CRUD ou uma classe base de Service.

## 5. Reduzir repetição com a base existente

A infraestrutura deve retirar trabalho repetitivo das features sem esconder suas regras.

| Recurso compartilhado | Contrato proposto |
|---|---|
| Permissão por ação | Um decorator pequeno, como `require_action("events.create")`, usa o mapa de ações e a identidade atuais. Regras por registro continuam na operação. |
| Sessões ORM | Uma factory de sessões por aplicação, ligada ao engine moderno; cada operação cria e fecha sua sessão. |
| Erros esperados | Tratamento comum de mensagem, status e detalhes de campo, preservando `{message, detail}`. Erros específicos continuam explícitos onde necessário. |
| Paginação | Uma função recebe sessão, consulta já filtrada e parâmetros validados; calcula total e página sem criar engine ou confirmar transação. |
| Respostas | Schemas Pydantic selecionam os campos públicos; conversão de atributos e composição de dados são preparadas antes de fechar a sessão. |
| Validação reutilizada | Reaproveitar definições comuns de criação/edição, como já ocorre em Demandas. Regras entre campos podem ficar no schema quando pertencem ao contrato. |

Implementar esses recursos apenas quando a repetição concreta do piloto justificar. A função de paginação precisa manter a contagem correta em consultas com joins; não prometer que uma implementação simples atende qualquer consulta.

### Bibliotecas escolhidas

- **SQLAlchemy ORM:** primeira opção para persistência no backend novo, aproveitando o engine compartilhado atual.
- **APIFlask e Pydantic:** manter `input`, `output`, validação e contratos existentes. Evitar reescrever parsing, serialização e documentação manualmente.
- **Flask-SQLAlchemy:** já atende o legado e oferece conveniências de integração e paginação. Seu uso no moderno exigiria uma decisão própria sobre recursos e sessões; não é requisito para esta proposta.
- **SQLModel e geradores de CRUD:** não acrescentar nesta etapa. Primeiro avaliar o ganho com as bibliotecas presentes.

A proposta não inclui instalação ou atualização de dependências. Novas abstrações precisam demonstrar redução de esforço frente à base existente.

## 6. ORM, sessões e transações

### Mapeamento das tabelas

Usar uma base declarativa comum, separada dos metadados do `db.Model` legado, e modelos por feature. Essa base fornece somente o mapeamento comum, sem operações de CRUD ou métodos `save()` que confirmem alterações.

Declarar explicitamente tabela, schema, chave, tipos, nulabilidade, defaults e campos gerados pelo banco. Preservar collation, relacionamentos e comportamento de exclusão. Os scripts versionados orientam a revisão; a estrutura aplicada precisa ser confirmada em ambiente autorizado.

Mapear as tabelas necessárias a cada operação, sem `create_all()`, `drop_all()` ou descoberta do banco por reflexão automática. A leitura de `JDT_USER_DETAILS` no moderno não deve importar o modelo legado como atalho nem passar a alterar esse cadastro.

A factory legada ainda chama `db.create_all()`. Separar os novos mapeamentos evita ampliar seu alcance, mas não elimina os efeitos existentes da inicialização.

### Um dono para a transação

- Reutilizar o engine e o pool modernos; criar uma factory de sessões por aplicação, não um engine por feature ou requisição.
- Para leitura, abrir e fechar uma sessão curta. Para escrita, a factory pode oferecer `with sessions.begin() as session:`, que confirma no sucesso e desfaz alterações SQL em falha.
- A rota ou a função que coordena a operação é dona da transação. Todas as gravações relacionadas, inclusive histórico, utilizam a mesma sessão.
- Funções auxiliares recebem a sessão; não fazem commits próprios. Sessões não são globais nem compartilhadas entre requisições ou threads.
- Usar `flush()` quando for necessário obter IDs ou tornar alterações pendentes visíveis à próxima etapa. `flush()` não confirma a transação.
- Montar o resultado público enquanto a sessão está aberta e retornar sucesso somente depois da confirmação bem-sucedida.

Durante a migração, SQL explícito pode ser executado pela própria sessão com parâmetros. Quando ele depender de alterações ORM pendentes, fazer `flush()` antes. Não misturar `db.session` legado, outra conexão e a sessão moderna para operações que precisam confirmar juntas.

Defaults, horários locais dos eventos, horário de referência do banco, datas UTC de auditoria e `row_version` precisam manter suas semânticas atuais. Evitar substituir essas diferenças por uma normalização genérica de datas.

### ORM como padrão, sem promessa de conversão mecânica

Filtros, joins, contagens, cálculos de status e atualizações condicionais podem ser expressos com SQLAlchemy. Travas do SQL Server exigem configuração explícita de hints ou uma estratégia equivalente demonstrada. Uma busca seguida de `add()` ou `commit()` não substitui as garantias atuais automaticamente.

SQL textual permanece uma opção excepcional quando facilitar uma operação específica. Seu uso não exige um Repository: uma consulta curta pode ficar próxima da operação; uma consulta extensa ou reutilizada pode justificar uma função ou arquivo próprio. Valores continuam parametrizados.

Evitar consultas por item em laços, carregamentos automáticos inesperados e serialização de relacionamentos depois do fechamento da sessão. Menos linhas Python não garante menos consultas ou melhor desempenho.

## 7. Aplicação às funcionalidades atuais

A revisão estática encontrou dois módulos registrados, com 17 operações de API em Eventos e seis em Solicitações de Demandas. As tabelas próprias descritas nos scripts são sete; Demandas também lê o cadastro compartilhado de usuários. Esses números delimitam o backend atual, não certificam o banco publicado.

| Operação | Destino proposto | Comportamento a preservar |
|---|---|---|
| Listar tipos, contribuintes e presenças | ORM diretamente nas rotas. | Filtros, campos públicos, permissões, ordem e paginação. |
| Listar e consultar eventos | ORM na rota, com função auxiliar para consulta/status quando útil. | Horário de referência do TD, pesquisa literal, status calculado e capacidades. |
| Criar e editar eventos | Regras e gravação na rota. | Período válido, tipo existente, autoria, transação e proteção do vínculo. |
| Criar e excluir tipos | ORM e regras na rota ou em função local. | Reutilização do mesmo nome, unicidade, travas e impedimento de excluir tipo em uso. |
| Gerenciar listas e presenças | ORM com verificações explícitas de vínculo. | Evento/lista corretos, concorrência e exclusões em cascata existentes. |
| Registrar presença | Rota coordena etapas e chama LDAP e funções auxiliares necessárias. | Consulta externa sem conexão SQL retida, nova verificação sob trava e prevenção de duplicidade. |
| Criar demanda | Rota coordena sessão, armazenamento e funções auxiliares. | Visibilidade, chave de envio, identificação do conteúdo, anexos, histórico e compensação de arquivos. |
| Editar demanda | ORM e validações na rota ou em função local. | Solicitante, área, estado, classificação, versão enviada pelo cliente e histórico na mesma transação. |
| Exportar PDF e baixar anexos | ORM obtém dados; apresentação e armazenamento continuam específicos. | Consistência da exportação, autorização por registro, caminho privado e cabeçalhos de resposta. |

### Presença

Primeiro conferir o vínculo da lista e liberar a conexão. Consultar LDAP. Depois abrir a transação, verificar novamente a lista sob trava e cadastrar ou complementar a presença. A identificação considera os últimos oito dígitos da matrícula e preserva os estados de identificação consumidos pela interface.

O ORM substitui a persistência; não substitui o adaptador LDAP. O código dessa sequência pode ficar na rota com funções auxiliares, sem obrigação de manter `services.py`.

### Demandas e anexos

Preservar a identificação do conteúdo enviado, a chave de envio e a distinção entre uma repetição válida e uma chave reaproveitada com conteúdo diferente. Demanda, metadados de anexos e histórico confirmam na mesma transação SQL.

Arquivos não fazem parte do rollback SQL. Manter a compensação restrita aos arquivos novos nas falhas previstas e a preservação em falha de commit com resultado incerto. Não substituir o tratamento atual por exclusão automática de arquivos em qualquer exceção.

### Edição e exclusão

O versionamento ORM não dispensa conferir a versão enviada pelo formulário. Preservar também os filtros de usuário, área, estado e classificação. Configurar exclusões de acordo com as FKs existentes, sem introduzir cascatas adicionais por conveniência.

Essas operações exigem atenção pela quantidade de responsabilidades, mas não tornam uma camada de Service obrigatória. Se a extração facilitar a leitura, ela deve separar uma operação concreta, sem apenas renomear os arquivos atuais ou acrescentar chamadas de repasse.

## 8. Segurança, contratos e inicialização

Continuam obrigatórios autenticação e sessão atuais, CSRF, permissão por ação e registro, autoria definida pelo backend, seleção de campos públicos, limites de upload e proteção de caminhos.

Preservar URLs, métodos HTTP, códigos de resposta, formato `{message, detail}`, capacidades, filtros, paginação e formatos de datas e versões usados pelo frontend. O decorator de ação proposto complementa a proteção do blueprint; ele não substitui regras de visibilidade ou edição do registro.

O bootstrap prepara engine, factory de sessões e adaptadores compartilhados e registra blueprints explicitamente. A aplicação Flask existente continua hospedando o backend novo. Tornar esse percurso mais claro é útil, mas mover a factory ou reorganizar o legado não é pré-requisito para a mudança.

Criar sessões e modelos não deve introduzir consultas, criação de tabelas, threads ou acesso a integrações durante imports. Os efeitos conhecidos do legado continuam sujeitos às restrições do AGENTS.md.

## 9. Roteiro adotado e futuras migrações

1. **Alinhar as referências de arquitetura.** Os trechos afetados do AGENTS.md, da arquitetura oficial e da base compartilhada acompanham o padrão ORM nas rotas, sem Service/Repository obrigatórios.
2. **Preparar a base ORM.** Definir base declarativa e factory de sessões sobre o engine moderno, com ciclo e transações explícitos e sem DDL automático.
3. **Converter uma leitura de Eventos.** Começar pela listagem de tipos, preservando endpoint, ordenação, campos e capacidades.
4. **Converter uma escrita completa de Eventos.** Incluir validação, autoria, vínculo, transação, resposta e erros. Regras curtas permanecem na rota.
5. **Centralizar repetição observada.** Introduzir apenas os helpers de permissão, erros, paginação e serialização que reduzirem o trabalho real do piloto.
6. **Migrar as demais operações de Eventos e depois Demandas.** Preservar as etapas de concorrência, arquivos e integrações. Retirar Services e Repositories conforme suas responsabilidades forem incorporadas e suas referências deixarem de existir.
7. **Comparar e consolidar.** Avaliar facilidade de leitura, quantidade de arquivos e código repetido; ampliar o padrão conforme o ganho demonstrado.

O primeiro piloto deve atravessar a operação inteira, da entrada HTTP à resposta. Uma conversão que só troca a sintaxe da consulta não demonstra o resultado da arquitetura proposta.

## 10. Critérios de aceitação e limites

- O responsável consegue localizar a rota, entender o fluxo e alterar campos ou consultas sem percorrer várias camadas de repasse.
- A feature começa com os arquivos necessários; novos arquivos têm responsabilidade concreta.
- Resultados, ordenação, permissões, conflitos e contratos correspondem à implementação anterior.
- Sessões fecham corretamente, gravações relacionadas compartilham a transação e sucesso só é retornado após sua confirmação.
- Concorrência, idempotência, histórico, arquivos e integrações mantêm as garantias existentes.
- Não há DDL automático, alteração do cadastro compartilhado ou novos efeitos de import.
- A contagem de consultas e os carregamentos são adequados ao endpoint.

Mapeamentos ORM acrescentam definições. A expectativa é reduzir arquivos obrigatórios, SQL repetitivo e esforço para desenvolver; a redução total de linhas precisa ser medida por comparação das versões. Retirar arquivos transferindo todo o conteúdo sem melhorar a leitura não cumpre o objetivo.

O agente trabalha somente com as validações estáticas permitidas: diff, referências, comparação de contratos e inspeção textual. A confirmação funcional exige autorização explícita com comando, ambiente e escopo, incluindo schema aplicado, consultas geradas, rollback, concorrência e efeitos de triggers quando existirem.

Cada entrega precisa preservar uma forma de retorno da versão sem apagar dados. Não executar duas gravações para comparar implementações, nem alterar o banco para experimentar o mapeamento.

## Referências

- [Arquitetura vigente](arquitetura-modernizada.md), [base compartilhada](../features/base-compartilhada.md) e [anotações do curso](../../curso_notion/).
- [Rotas](../../backend/modules/events/routes.py), [modelos](../../backend/modules/events/models.py) e [schemas de Eventos](../../backend/modules/events/schemas.py).
- [Rotas](../../backend/modules/demands/routes.py), [modelos](../../backend/modules/demands/models.py) e [armazenamento de Demandas](../../backend/modules/demands/storage.py).
- [Banco compartilhado](../../backend/platform/database.py), [segurança HTTP](../../backend/platform/http.py) e [bootstrap atual](../../backend/bootstrap.py).
- [Sessões SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html), [particularidades do SQL Server](https://docs.sqlalchemy.org/en/20/dialects/mssql.html) e [APIFlask com Pydantic](https://apiflask.com/usage/).

Os mapeamentos consideram os metadados de banco fornecidos pelo responsável: tipos, defaults, chaves, índices, constraints e ausência de triggers nas oito tabelas. Isso não substitui validar consultas geradas, concorrência, rollback e integrações no ambiente autorizado. **O sistema não foi executado; a validação foi somente estática.**
