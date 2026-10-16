# Campos e tipos de Eventos

Em `/app/eventos`, **Novo evento** e **Editar** usam o mesmo formulário. Os detalhes apresentam o tipo, o instrutor e o conteúdo programático, além da descrição e do período. Campos antigos sem esses dados aparecem como “Não informado”. As listas de presença continuam descritas no [guia próprio](listas-de-presenca.md).

## Campos

| Campo | Obrigatoriedade e limite |
|---|---|
| Título (`name`) | Obrigatório; de 3 a 120 caracteres. |
| Tipo de evento (`event_type_id`) | Obrigatório ao cadastrar/editar; ID inteiro positivo de uma opção cadastrada. |
| Instrutor (`instructor`) | Opcional; texto de até 200 caracteres. |
| Descrição (`description`) | Obrigatória; de 1 a 2.000 caracteres. |
| Conteúdo programático (`syllabus`) | Opcional; texto com múltiplas linhas, até 4.000 caracteres. |
| Início e fim (`starts_at`, `ends_at`) | Obrigatórios; horários locais sem fuso, com fim posterior ao início. |

Espaços externos são retirados. Instrutor/conteúdo em branco são armazenados como NULL; ambos também aceitam null ou ausência no JSON. O PUT substitui os dados do evento, inclusive limpando opcionais omitidos. Eventos antigos continuam consultáveis com tipo e opcionais nulos, sem preenchimento automático; na edição, é necessário escolher um tipo.

## Cadastro das opções

O Select Volt permite pesquisar entre os tipos existentes. O botão **+**, ao lado, abre um cadastro no próprio formulário, sem apagar os demais valores. O nome do tipo aceita de 1 a 80 caracteres após trim. **Salvar tipo** ou Enter nesse campo grava a opção e a seleciona; não salva o evento. **Cancelar tipo** fecha apenas esse cadastro e devolve o foco ao botão +. Enquanto o cadastro do tipo está aberto, o envio do evento fica desabilitado.

Tipos são compartilhados entre eventos e permanecem cadastrados mesmo se o responsável cancelar o evento. O catálogo começa vazio; nenhuma opção de negócio é inventada pela migration. Nomes iguais, desconsiderando maiúsculas/minúsculas e mantendo distinção de acentos, reutilizam a opção existente. Não há edição/exclusão de tipos nesta entrega. A FK não permite remover um tipo ainda usado por eventos.

Consulta e gravação têm tratamento de falha, sem repetição automática das escritas. Durante a gravação de um tipo, os controles e o fechamento do evento ficam bloqueados. Falhas preservam os campos para correção ou nova tentativa manual. O cache de tipos recebe a opção retornada pelo backend.

## API e arquitetura

Base: `/api/v1/events`. As rotas mantêm identidade, GENERAL e CSRF compartilhados. Serviços autorizam ações e controlam transações; o repositório usa SQL parametrizado e não conhece Flask. Não há imports ou chamadas às integrações do legado, jobs ou notificações novos.

| Operação | Contrato |
|---|---|
| GET `/types` | HTTP 200 com `{items: [{id, name}], can_create}`; exige `events.read`. |
| POST `/types` | `{name}`; HTTP 200 com `{id, name}`, tanto na criação quanto ao reutilizar nome existente. Exige `events.types.create`, mapeada para GENERAL no bootstrap. |
| POST na base e PUT `/<id>` | Mantêm o contrato anterior e passam a exigir `event_type_id`; aceitam `instructor` e `syllabus` opcionais. |
| GET na base e GET `/<id>`, retorno de POST/PUT | Acrescentam `event_type_id`, `event_type_name`, `instructor` e `syllabus`, anuláveis para registros antigos. |

O serviço verifica a existência do tipo na mesma transação da escrita do evento; IDs inexistentes retornam 422 no campo `event_type_id`. A FK também protege esse vínculo. O cadastro de tipo usa UPDLOCK/HOLDLOCK e uma chave única por nome para serializar pedidos concorrentes iguais. Reutilizar um tipo não altera seu nome nem sua autoria. Todas as escritas retornam após o commit.

`EventForm` compõe Select, InputText, Textarea, Message e botões Volt já instalados. `EventDialog` mantém o bloqueio durante as gravações e exibe os novos dados. Nenhum arquivo de `src/volt/` foi alterado. O Select associa nome, obrigatoriedade e erro ao controle de foco por seus atributos e Pass Through; referência: [implementação oficial do Select 4.5.5](https://github.com/primefaces/primevue/blob/4.5.5/packages/primevue/src/select/Select.vue).

## Banco e publicação

O SQL proposto está em [20261016_add_dj_event_types_and_details.sql](../database/migrations/20261016_add_dj_event_types_and_details.sql). **Não foi executado e não é aplicado pela aplicação.** Requer `DJ_EVENTS` já criada com a migration de período e deve ser revisado/aplicado pelo responsável no TD antes da API/build compatíveis.

O script cria `dbo.DJ_EVENT_TYPES` com nome único, autor e data UTC de cadastro. Adiciona `event_type_id INT NULL`, `instructor NVARCHAR(200) NULL` e `syllabus NVARCHAR(4000) NULL` a `dbo.DJ_EVENTS`, mais a FK para o catálogo. Não modifica valores de eventos ou presenças existentes.

Publique backend e build juntos conforme [Servidor e publicação](servidor-e-publicacao.md). O frontend anterior não envia o tipo exigido pela nova API. Não há dependências novas. Em retorno de código, as colunas e o catálogo podem ser mantidos; o código anterior não os utiliza. Não remova o catálogo ou as colunas como parte de um retorno automático.

## Conferência em ambiente autorizado

A entrega teve somente validação estática. O responsável deve conferir, em dados e ambiente autorizados:

1. Revisar/aplicar a migration e gerar o build. Confirmar que registros antigos continuam abrindo sem tipo, instrutor ou conteúdo, e que editar exige escolher um tipo.
2. Criar uma opção pelo + em cadastro e edição; confirmar seleção imediata, preservação dos demais campos e persistência em outro evento. Enter no nome do tipo deve salvar só o tipo. Cancelar o painel deve manter os dados do evento.
3. Salvar e editar eventos com e sem instrutor/conteúdo. Limpar os opcionais e conferir NULL; verificar os novos campos nos detalhes, inclusive quebra de linhas e textos longos.
4. Conferir nomes vazios, espaços, limites, tipo ausente/nulo/inexistente e campos JSON extras. Conferir falta de sessão, permissão e CSRF; as escritas devem ser rejeitadas.
5. Cadastrar simultaneamente o mesmo tipo, inclusive variando maiúsculas e espaços externos; deve existir uma opção só, sem alterar autoria/nome anterior. Nomes com acentos distintos seguem a collation CI_AS declarada no script.
6. Conferir falhas de consulta e gravação: manter os dados, permitir tentativa manual e não repetir escrita automaticamente. Confirmar bloqueio de fechar/Escape/novos envios durante gravações, foco, navegação por teclado e adaptação em telas pequenas.
7. Conferir filtros de status, busca por título e listas de presença após a publicação. Nenhuma regra desses fluxos foi alterada por esta entrega.
