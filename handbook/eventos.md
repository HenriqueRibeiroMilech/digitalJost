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

Tipos são compartilhados entre eventos e permanecem cadastrados mesmo se o responsável cancelar o evento. O catálogo começa vazio; nenhuma opção de negócio é inventada pela migration. Nomes iguais, desconsiderando maiúsculas/minúsculas e mantendo distinção de acentos, reutilizam a opção existente. A edição de nomes de tipos não faz parte deste fluxo.

Cada opção no Select apresenta uma lixeira quando a sessão tem `can_delete`. Acioná-la abre a confirmação **Excluir tipo de evento**, sem selecionar essa opção ou apagar os outros campos do formulário. Por teclado, selecione um tipo e use **Alt+Delete**; o atalho e sua instrução são associados ao controle de foco. Cancelar preserva a seleção. Confirmar remove a opção do catálogo compartilhado e, se ela estava selecionada no formulário, limpa somente o campo de tipo para permitir outra escolha. A exclusão não é desfeita ao cancelar o evento.

Um tipo vinculado a qualquer evento, inclusive concluído, não pode ser excluído: a API retorna 409 com a orientação de alterar esses eventos primeiro. O vínculo e os dados dos eventos são preservados. Tipo ausente/já removido retorna 404. Não há exclusão em cascata ou substituição automática de tipo.

Consulta e gravação têm tratamento de falha, sem repetição automática das escritas. Durante a gravação de um tipo ou enquanto a confirmação de exclusão está aberta, os controles e o fechamento do evento ficam bloqueados. O diálogo de exclusão recebe foco inicial em Cancelar e bloqueia fechamento, Escape e novo envio durante o DELETE. Falhas mantêm o diálogo aberto com mensagem. Ao fechá-lo, o foco retorna ao Select e as opções são consultadas novamente, inclusive após cancelamento/resposta incerta. O cache recebe as criações/exclusões confirmadas; se uma consulta atualizada indicar que o tipo selecionado deixou de existir, a seleção é limpa sem alterar outros campos.

## API e arquitetura

Base: `/api/v1/events`. As rotas mantêm identidade, GENERAL e CSRF compartilhados. Serviços autorizam ações e controlam transações; o repositório usa SQL parametrizado e não conhece Flask. Não há imports ou chamadas às integrações do legado, jobs ou notificações novos.

| Operação | Contrato |
|---|---|
| GET `/types` | HTTP 200 com `{items: [{id, name}], can_create, can_delete}`; exige `events.read`. |
| POST `/types` | `{name}`; HTTP 200 com `{id, name}`, tanto na criação quanto ao reutilizar nome existente. Exige `events.types.create`, mapeada para GENERAL em `backend/modules/events/routes.py`. |
| DELETE `/types/<id>` | HTTP 200 com `{id}` após o commit; exige `events.types.delete`, mapeada para GENERAL. 404 se ausente e 409 se usado por algum evento. |
| POST na base e PUT `/<id>` | Mantêm o contrato anterior e passam a exigir `event_type_id`; aceitam `instructor` e `syllabus` opcionais. |
| GET na base e GET `/<id>`, retorno de POST/PUT | Acrescentam `event_type_id`, `event_type_name`, `instructor` e `syllabus`, anuláveis para registros antigos. |

O serviço verifica a existência do tipo na mesma transação da escrita do evento; IDs inexistentes retornam 422 no campo `event_type_id`. A FK também protege esse vínculo. O cadastro de tipo usa UPDLOCK/HOLDLOCK e uma chave única por nome para serializar pedidos concorrentes iguais. Reutilizar um tipo não altera seu nome nem sua autoria. Todas as escritas retornam após o commit.

O serviço autoriza a exclusão antes de abrir a transação, obtém XLOCK/HOLDLOCK no tipo, verifica referências em `DJ_EVENTS` e só então remove por ID. A trava serializa a exclusão com as validações HOLDLOCK usadas na criação/edição de eventos; a FK existente também protege o vínculo. O repositório concentra o SQL parametrizado; rotas traduzem os erros para HTTP. A operação não consulta LDAP e não altera schema, eventos ou presenças.

`EventForm` compõe Select, InputText, Textarea, Message e botões Volt já instalados. O slot `option` apresenta o nome e a lixeira; a ação interrompe mousedown/click para preservar a seleção, e o Select é remontado com o mesmo v-model para encerrar o overlay antes da confirmação. `EventTypeDeleteDialog` compõe AppDialog/Volt e emite o resultado após a transição de fechamento. `EventDialog` mantém o bloqueio durante o gerenciamento e exibe os dados. Nenhum arquivo de `src/volt/` foi alterado. O Select associa nome, obrigatoriedade, erro e instrução de teclado ao controle de foco por seus atributos e Pass Through; referência: [implementação oficial do Select 4.5.5](https://github.com/primefaces/primevue/blob/4.5.5/packages/primevue/src/select/Select.vue).

## Banco e publicação

O SQL proposto está em [20261016_add_dj_event_types_and_details.sql](../database/migrations/20261016_add_dj_event_types_and_details.sql). **Não foi executado e não é aplicado pela aplicação.** Requer `DJ_EVENTS` já criada com a migration de período e deve ser revisado/aplicado pelo responsável no TD antes da API/build compatíveis.

O script cria `dbo.DJ_EVENT_TYPES` com nome único, autor e data UTC de cadastro. Adiciona `event_type_id INT NULL`, `instructor NVARCHAR(200) NULL` e `syllabus NVARCHAR(4000) NULL` a `dbo.DJ_EVENTS`, mais a FK para o catálogo. Não modifica valores de eventos ou presenças existentes.

Publique backend e build juntos conforme [Servidor e publicação](servidor-e-publicacao.md). O frontend anterior não envia o tipo exigido pela nova API. Não há dependências novas. Em retorno de código, as colunas e o catálogo podem ser mantidos; o código anterior não os utiliza. Não remova o catálogo ou as colunas como parte de um retorno automático.

A exclusão de tipos usa as tabelas/FK existentes e não requer nova migration ou dependência. Publique a API com DELETE/capacidade `can_delete` e o build compatível juntos.

## Conferência em ambiente autorizado

A entrega teve somente validação estática. O responsável deve conferir, em dados e ambiente autorizados:

1. Revisar/aplicar a migration e gerar o build. Confirmar que registros antigos continuam abrindo sem tipo, instrutor ou conteúdo, e que editar exige escolher um tipo.
2. Criar uma opção pelo + em cadastro e edição; confirmar seleção imediata, preservação dos demais campos e persistência em outro evento. Enter no nome do tipo deve salvar só o tipo. Cancelar o painel deve manter os dados do evento.
3. Salvar e editar eventos com e sem instrutor/conteúdo. Limpar os opcionais e conferir NULL; verificar os novos campos nos detalhes, inclusive quebra de linhas e textos longos.
4. Conferir nomes vazios, espaços, limites, tipo ausente/nulo/inexistente e campos JSON extras. Conferir falta de sessão, permissão e CSRF; as escritas devem ser rejeitadas.
5. Cadastrar simultaneamente o mesmo tipo, inclusive variando maiúsculas e espaços externos; deve existir uma opção só, sem alterar autoria/nome anterior. Nomes com acentos distintos seguem a collation CI_AS declarada no script.
6. Conferir falhas de consulta e gravação: manter os dados, permitir tentativa manual e não repetir escrita automaticamente. Confirmar bloqueio de fechar/Escape/novos envios durante gravações, foco, navegação por teclado e adaptação em telas pequenas.
7. Conferir filtros de status, busca por título e listas de presença após a publicação. Nenhuma regra desses fluxos foi alterada por esta entrega.
8. Acionar a lixeira de uma opção não selecionada com mouse/toque e cancelar: a seleção e os demais campos devem permanecer iguais. Excluir um tipo sem uso deve retirá-lo do catálogo; se estava selecionado no formulário, deve limpar somente esse campo. Conferir pesquisa, última opção removida e tentativa de enviar o evento sem tipo após a exclusão.
9. Conferir teclado (incluindo Alt+Delete somente no combobox), nomes acessíveis, foco inicial em Cancelar e retorno ao Select. Enter/Espaço na ação não devem selecionar a opção nem enviar o formulário de evento. Durante o DELETE, fechar/Escape/novos envios devem ficar bloqueados.
10. Tentar excluir tipo usado por evento futuro, em andamento ou concluído: deve retornar 409 e preservar ambos os registros. Conferir 404 para tipo já excluído, falta de sessão/permissão/CSRF e falhas de rede, sem repetição automática da escrita.
11. Conferir criação/edição de evento concorrente com exclusão do mesmo tipo e atualização de opções em outra sessão. A FK deve ser preservada: a operação que encontrar referência válida impede exclusão, ou o evento é rejeitado por tipo ausente. Confirmar os dados persistidos antes de repetir uma operação cuja resposta foi incerta.
