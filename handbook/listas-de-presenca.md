# Listas de presença de Eventos

## Uso e comportamento implementado

Em `/app/eventos`, abra um evento e selecione **Listas de presença**. Crie uma lista pelo nome e abra-a para ver Matrícula, Nome e Setor. Um evento pode ter várias listas, e uma pessoa pode participar de listas diferentes. A listagem de listas usa seis itens por página; participantes usam 25, com os mais recentes primeiro.

**Iniciar preenchimento por leitor** abre uma tela que ocupa a janela para os convidados. Ela usa a sessão autenticada do responsável pelo evento; não é uma página pública nem uma nova forma de login. A tela informa “Encoste o crachá até receber a aprovação” e mantém um campo de texto preparado para o leitor que funciona como teclado e encerra a leitura com Enter.

Uma leitura é aceita somente quando contém exatamente **12 dígitos de 0 a 9**. A matrícula é texto em todas as camadas para preservar zeros à esquerda. Não são retirados prefixos, espaços ou caracteres extras, nem truncadas leituras longas. Uma leitura incompleta, longa ou com outros caracteres mostra “Tente novamente”, limpa o campo e não envia uma gravação à API. O backend repete a validação, inclusive para requisições feitas fora da interface.

Uma leitura válida mostra “Confirmando presença…” enquanto aguarda a API. **“Presença confirmada!” só aparece após a transação ser confirmada pelo servidor.** A tela informa que o crachá pode ser retirado e retorna à instrução em 3,5 segundos ou ao iniciar a próxima leitura. Leituras durante um envio pendente são descartadas; o campo permanece somente leitura até o envio terminar.

A matrícula é única dentro de uma lista. Uma repetição retorna “Sua presença já está registrada” sem criar outra linha. Isso permite também conferir uma leitura quando uma falha de comunicação deixa o resultado incerto. Não há reenvio automático de escritas. Em falha de conexão, a tela pede uma nova aproximação; em falha de segurança da sessão, sessão expirada, acesso negado ou lista ausente, bloqueia novas leituras e orienta chamar o responsável.

Nome e setor ficam nulos e aparecem como “Não informado”. Não há consulta a API de funcionários ou outra integração nesta etapa. O formato do crachá é validado, mas a existência/identidade da pessoa ainda não é verificada.

O foco volta ao campo após cada leitura e quando a janela recupera o foco. Se o usuário mover o foco, uma ação permite ativar o campo novamente; partes de uma leitura são apagadas ao sair do campo. Durante a captura, a navegação do evento fica bloqueada. **Encerrar leitura** restaura a lista e o foco no botão de iniciar, ficando indisponível durante uma gravação.

Presenças confirmadas atualizam o cache da primeira página. A tabela consulta novamente ao sair da captura e, enquanto aberta sem captura e com a aba do navegador ativa, a cada cinco segundos. O total das listas é atualizado ao retornar à coleção. Falha nessa atualização não refaz uma presença já salva.

## API e responsabilidades

Base: `/api/v1/events/<event_id>/attendance-lists`.

| Método e caminho | Entrada e retorno |
|---|---|
| GET na base | `page` e `per_page`; itens `{id, event_id, name, total}`, paginação e capacidades. |
| POST na base | `{name}`, texto de 1 a 120 caracteres após trim; retorna a lista criada com total zero e HTTP 201. |
| GET `/<list_id>` | Lista, total e capacidades da sessão. |
| GET `/<list_id>/entries` | `page` e `per_page`; itens `{id, registration, name, department}`, paginação e capacidades. |
| POST `/<list_id>/entries` | `{registration}` como string; HTTP 200 com `{item, created}` tanto na criação quanto na repetição. |

Paginação usa o contrato compartilhado: página mínima 1 e de 1 a 100 itens por página. JSON inválido retorna 422. Evento ausente na coleção ou lista ausente/no evento errado retorna 404. A listagem de registros é sempre restrita à lista cujo vínculo foi verificado pelo serviço.

Todas as rotas usam a guarda de identidade, o perfil GENERAL e o CSRF compartilhados. Serviços exigem `events.attendance.read`, `events.attendance.create` ou `events.attendance.register`, mapeados explicitamente em `backend/bootstrap.py`. Capacidades `can_create` e `can_register` orientam a interface; não substituem a autorização do backend.

O serviço delimita transações na engine TD. A criação de lista mantém o evento existente com HOLDLOCK durante a escrita. O registro trava a lista com UPDLOCK/HOLDLOCK, verifica a matrícula e grava apenas se ela ainda não existir. A constraint UNIQUE é uma defesa adicional contra duplicidade. Consultas e escritas usam parâmetros SQL; não há jobs, uploads, e-mails ou chamadas corporativas novas.

## Banco e publicação

O arquivo [20261015_create_dj_event_attendance.sql](../database/migrations/20261015_create_dj_event_attendance.sql) é uma **proposta para revisão e aplicação pelo responsável pelo banco**, em ambiente e janela autorizados. O agente não o executou, e a aplicação não o executa automaticamente.

Ele requer `dbo.DJ_EVENTS` e cria:

- `dbo.DJ_EVENT_ATTENDANCE_LISTS`: vínculo com evento, nome, autor e data UTC de criação.
- `dbo.DJ_EVENT_ATTENDANCE_ENTRIES`: vínculo com lista, matrícula, nome e setor anuláveis, autor e data UTC de criação.
- FKs, índices para listagem, UNIQUE por lista/matrícula e CHECK para os 12 dígitos.

As FKs têm exclusão em cascata: excluir um evento também exclui suas listas e presenças. A confirmação na interface avisa esse efeito. Não há edição/exclusão individual de listas ou participantes nesta etapa.

Depois da revisão e aplicação do SQL, publique backend e build compatíveis juntos, conforme [Servidor e publicação](servidor-e-publicacao.md). Os componentes Volt necessários já estão no repositório; não há dependência nova. Em retorno de código, as tabelas podem ser mantidas sem remoção de dados. A exclusão de evento pelo código anterior também seguirá as novas cascatas do banco, caso sejam mantidas.

## Conferência em ambiente autorizado

A entrega recebeu somente análise estática. Build, migração, navegador, leitor físico e concorrência no SQL Server precisam de validação pelo responsável, conforme `AGENTS.md`:

1. Criar duas listas no mesmo evento e outra em evento diferente; conferir isolamento e paginação.
2. Ler 12 dígitos com Enter, inclusive com zero inicial; conferir uma linha persistida e os dois campos opcionais vazios.
3. Ler menos/mais de 12 caracteres e valores com letras ou espaços; conferir “Tente novamente” sem nova presença e a validação 422 da API.
4. Repetir a matrícula na mesma lista, inclusive simultaneamente em duas sessões autorizadas; conferir uma linha e a resposta de presença existente. A mesma matrícula em outra lista deve ser aceita.
5. Conferir foco inicial, leituras consecutivas, perda/retorno de foco e bloqueio durante gravação.
6. Conferir falha de conexão, resultado incerto, nova leitura idempotente, sessão expirada e lista/evento ausente. Nenhuma falha deve mostrar confirmação falsa.
7. Conferir acesso sem permissão, CSRF ausente e lista informada com evento errado; não devem permitir ler ou registrar os dados.
8. Em dados de conferência autorizados, verificar o aviso e a cascata ao excluir um evento. O agente não cria nem remove dados para essa validação.
