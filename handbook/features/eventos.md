# Eventos e listas de presença

**Estado:** implementado no código moderno, em `/app/eventos`; funcionamento, schema aplicado e publicação no ambiente real precisam de confirmação autorizada. Revisão estática em **20/10/2026**, confrontando backend, Vue, scripts SQL e os antigos guias de [campos](../historico/handbook/eventos.md) e [presença](../historico/handbook/listas-de-presenca.md). Este arquivo reúne cadastro de eventos, tipos, presença e PDF.

O módulo não utiliza o gerenciador antigo de demandas. Reutiliza sessão/perfis, CSRF, engine TD e shell da [base compartilhada](base-compartilhada.md). A consulta de funcionários é independente do cliente de login legado e não autentica o convidado.

## 1. Uso e campos

A página permite pesquisar eventos por título, combinar status, cadastrar, abrir detalhes, editar e excluir. Começa com futuros (`upcoming`) e em andamento (`ongoing`); os estados vêm do horário do TD. Encerrados usam `completed`, e registros antigos sem período aparecem como `unscheduled`. Busca é literal, filtros atuam no servidor e a lista usa 12 cards por página.

| Campo | Regra de cadastro e edição |
|---|---|
| `name` | Obrigatório, de 3 a 120 caracteres. |
| `description` | Obrigatório, de 1 a 2.000 caracteres. |
| `event_type_id` | Inteiro positivo de tipo cadastrado. |
| `instructor` | Opcional, até 200 caracteres. |
| `syllabus` | Opcional, até 4.000 caracteres, preservando quebras de linha. |
| `starts_at`, `ends_at` | Horários locais ISO 8601 sem fuso; fim posterior ao início e precisão de até milissegundos. |

Espaços externos são retirados; opcionais em branco viram NULL. PUT substitui o formulário completo, inclusive limpando opcionais omitidos. Registros antigos com campos nulos continuam consultáveis; editar exige preencher período e tipo. Autoria é definida pelo servidor.

O Select de tipos permite pesquisar, cadastrar pelo **+** e excluir pela lixeira ou por Alt+Delete no controle. Criar um tipo o seleciona sem salvar o evento; cancelar o evento não desfaz esse cadastro. Nomes iguais reutilizam o tipo conforme a collation definida no SQL. Tipos em uso não podem ser removidos: HTTP 409; ausentes retornam 404.

### Status, filtros e datas

| Status | Regra calculada pelo backend | Apresentação |
|---|---|---|
| `unscheduled` | Início ou fim nulo. | Sem período, tom neutro. |
| `completed` | Fim menor ou igual ao horário atual do TD. | Concluído, tom neutro. |
| `ongoing` | Início atingido e fim ainda não atingido. | Em andamento, verde. |
| `upcoming` | Início ainda não atingido. | Futuro, azul. |

O Service obtém `SYSDATETIME()` e usa a mesma referência no cálculo da consulta. O Vue apresenta o resultado; não decide status por seu próprio relógio. Períodos são locais e não recebem conversão com `toISOString()`. Datas de autoria criadas por defaults SQL usam UTC; não confundir com o período do evento.

A pesquisa de título espera 300 ms sem digitação ou é aplicada imediatamente com Enter. Status podem ser combinados; desmarcar todos faz o cliente enviar os quatro estados. O parâmetro `status` vazio não é válido na API. Busca escapa `%`, `_`, `[` e `~`, mantendo a entrada literal. Ordenação: ID decrescente. Busca/estado/contagem/paginação são de servidor; trocar filtros volta à primeira página.

A listagem consulta a cada 60 segundos com a aba ativa e pausa com o diálogo aberto. O detalhe também atualiza a cada 60 segundos, mas pausa durante edição, exclusão e presença. Não substituir o formulário por um refetch. Criação/exclusão volta à primeira página; edição preserva filtros e pode retirar o card dos resultados se o período mudar de estado.

### Cadastro e edição

Exemplo sintético do corpo JSON de POST/PUT; o ID de tipo deve existir no ambiente autorizado:

```json
{
  "name": "Treinamento de exemplo",
  "description": "Descrição do encontro.",
  "event_type_id": 1,
  "instructor": null,
  "syllabus": "Primeiro tópico\nSegundo tópico",
  "starts_at": "2026-11-10T08:00:00.000",
  "ends_at": "2026-11-10T10:00:00.000"
}
```

Schemas rejeitam campos extras e coerções de tipos de escrita. ID de tipo é inteiro positivo até o limite de INT do SQL Server. `instructor` e `syllabus` podem ser omitidos ou nulos; PUT não é edição parcial. O nome de tipo tem de 1 a 80 caracteres após trim.

Criação/edição exige a ação, valida fim posterior ao início e mantém o tipo existente com HOLDLOCK durante a transação. A exclusão de tipo usa XLOCK/HOLDLOCK e verifica uso antes de remover; cadastrar nome usa UPDLOCK/HOLDLOCK e a chave única. A collation `Latin1_General_100_CI_AS` determina igualdade de nomes. Não remover essas proteções por tratar tipos como cadastro simples.

O formulário mantém dados em falha e associa 422 aos campos. Cadastro de tipo é uma operação própria; sua conclusão pode persistir mesmo que o formulário de evento seja cancelado. Uma resposta incerta exige conferir os tipos/eventos antes de repetir: a criação de evento não tem `submission_key`.

## 2. Presença e identificação

Dentro do evento, **Listas de presença** permite criar, renomear, excluir listas e remover participantes. Nome da lista: 1 a 120 caracteres após trim. A coleção usa seis itens por página; participantes, 25. Excluir uma lista remove suas presenças; excluir o evento também remove suas listas, pelas cascatas previstas no schema.

O leitor usa a sessão autenticada do responsável, com a mesma autorização e CSRF; não é uma página pública. O crachá deve ter exatamente 12 dígitos ASCII, preservados na API e no banco. A tabela e o PDF mostram Empresa, Matrícula, Nome e Setor; a matrícula visível contém os oito dígitos finais, com zeros.

O registro consulta o LDAP em toda tentativa, inclusive repetida. A identificação aceita somente uma pessoa compatível com a matrícula; não há exigência de um prefixo fixo de empresa. Na mesma lista, repetição pelos oito dígitos finais não cria outra linha e pode completar dados faltantes sem sobrescrever os preenchidos. Outra lista pode receber a mesma pessoa.

| Resultado da identificação | Resposta e efeito |
|---|---|
| Pessoa única, dados completos ou parciais | Sucesso com `item`, `created` e `lookup_status` (`complete`/`partial`). |
| Ausente, ambígua, consulta truncada ou código não identificável | 422, sem gravar nessa tentativa. |
| Diretório indisponível, bind ou timeout | 503, sem gravar nessa tentativa. |
| Crachá ou campo inválido | 422 com os detalhes dos campos; JSON malformado pode retornar 400. |

O Service valida o vínculo antes do LDAP, libera a conexão SQL durante a consulta externa e revalida a lista com trava antes de gravar. A conexão LDAP é encerrada ao final. As mesmas travas coordenam registro, renomeação e exclusão; preservá-las em futuras alterações.

O PDF contém o evento e a lista completa, independentemente da página aberta. É gerado em memória após liberar conexão/travas, com logo, quatro colunas e páginas A4. Não consulta LDAP nem cria arquivo operacional.

### Leitor: sequência e recuperação

1. Abrir o evento, entrar em Listas de presença, abrir uma lista e escolher **Iniciar preenchimento por leitor**. A captura ocupa a janela e usa um leitor que funciona como teclado.
2. Cada alteração no campo reinicia uma espera de **300 ms** (`readingDelay`). Enter não antecipa nem reinicia essa espera. Enter vazio/tardio é ignorado.
3. Após estabilizar, exigir exatamente 12 dígitos ASCII. Código curto, longo, com espaços ou outros caracteres é descartado e não chama a API; o backend aplica a mesma exigência.
4. Durante a API, bloquear nova leitura e fechamento; descartar fragmentos recebidos nesse intervalo. Não há fila nem reenvio automático.
5. Mostrar confirmação somente após resposta bem-sucedida. Verde identifica criação completa ou presença já existente; azul informa presença salva com dados opcionais ausentes. Voltar à instrução após 3,5 segundos ou na próxima leitura.
6. Restaurar foco após a tentativa e quando a janela volta a ter foco. Ao sair do campo, cancelar partes/temporizador da leitura. **Encerrar leitura** pode cancelar a estabilização, mas aguarda uma escrita pendente.

Falhas 400/401/403/404 bloqueiam a captura e pedem intervenção do responsável. Identificação rejeitada ou diretório indisponível informa que aquela tentativa não foi gravada. Rede/timeout genérico deixa resultado incerto; uma nova aproximação manual confere a presença pela regra de repetição. Não afirmar que um timeout desfez o commit.

Durante captura, gestão da lista ou geração do PDF, o diálogo do evento bloqueia fechamento/troca de aba/ações incompatíveis. Renomear lista e excluir participante/lista usam confirmação própria; exclusões avisam o alcance e priorizam Cancelar no foco inicial.

### Identificação LDAP

`EmployeeDirectory.find_by_badge` extrai os oito dígitos finais apenas para identificar a matrícula. No filtro de busca, remove zeros iniciais, mantendo `0` se todos forem zero, e escapa caracteres do filtro. Faz bind NTLM em conexão própria, somente leitura, sem referrals, limitada a dois resultados e ao timeout configurado.

São solicitados `description`, `displayName`, `department` e `physicalDeliveryOfficeName`. O segundo campo de `description`, separado por `;`, contém a matrícula; sem separador, o atributo inteiro é avaliado. São aceitos um a oito dígitos ASCII, completados com zeros até oito e comparados por igualdade. Uma substring em outro campo, sinal ou número maior não identifica a pessoa.

| Dado salvo | Atributo |
|---|---|
| Nome | `displayName` |
| Setor | `department` |
| Empresa | `physicalDeliveryOfficeName` |

Dados opcionais vazios, inválidos ou acima de 200 unidades UTF-16 ficam nulos. Zero correspondências válidas gera `not_found`; mais de uma ou resultado truncado gera `ambiguous`. Falha de bind/rede/timeout ou configuração ausente gera `unavailable`. Não escolher o primeiro candidato nem cadastrar uma presença sem correspondência única.

Não existe whitelist de prefixos de empresa. O código original de 12 dígitos fica salvo; a busca por oito dígitos pode retornar uma presença com outro prefixo, que é preservada. Campos preenchidos não são atualizados automaticamente com mudanças do diretório; somente ausências podem ser completadas. `lookup_status` final considera os campos persistidos após essa composição.

A verificação cadastral não comprova quem apresentou fisicamente o crachá. O código não exige que a captura ocorra apenas durante o período do evento. Não documentar essas restrições como implementadas.

### Consulta, atualização e PDF

As listas são exibidas por ID decrescente, seis por página; participantes, também do mais recente ao mais antigo, 25 por página. Confirmação de presença atualiza a primeira página/cache e totais sem refazer a escrita. Sem captura/gestão/exportação, a tabela consulta a cada cinco segundos com a aba ativa. Retornar da captura ou fechar uma ação invalida as consultas para conciliar outra sessão ou resposta incerta.

Remover o último participante de uma página pode recuar a página. Excluir lista retorna à coleção e retira o detalhe do cache; fechar restaura foco para o controle de origem ou um destino válido. Falha de atualização não desfaz uma alteração já confirmada.

O PDF inclui nome/tipo/instrutor/período/descrição/conteúdo programático, total e todos os participantes. Tem logo em cada página, cabeçalho da tabela repetido e emissão pelo horário TD; campos ausentes mostram “Não informado”. Não exibe IDs de evento/lista no conteúdo, e gera documento vazio com total zero quando necessário.

O Service trava evento e lista enquanto captura os dados; renderiza depois de liberar SQL. Textos são escapados antes de entrar no markup do ReportLab. Retorna attachment `lista-presenca-evento-<id>-lista-<id>.pdf`, MIME PDF, `Cache-Control: private, no-store`, `Pragma: no-cache` e `nosniff`. O cliente aguarda 30 segundos, exige conteúdo PDF em sucesso e não baixa HTML/JSON como documento. Falta de biblioteca/logo tratada pelo Service gera 503.

## 3. API e autorização

Base `/api/v1/events`. Todas as entradas exigem sessão e GENERAL. O mapa de ações fica em `routes.py`; capacidades da interface não substituem autorização. As escritas exigem `X-CSRF-Token`.

Todas as ações atuais são mapeadas para GENERAL, inclusive editar/excluir. Não há filtro por autor ou participante para listar/gerenciar eventos. A segurança por vínculo exige que a lista pertença ao evento e a presença à lista; não equivale à restrição por solicitante de Demandas.

| Método e caminho relativo | Resultado e ação |
|---|---|
| GET `""` | Lista paginada; `page`, `per_page`, `search`, `status` separados por vírgula; `events.read`. |
| POST `""` | Evento criado, 201; `events.create`. |
| GET / PUT / DELETE `/<event_id>` | Detalhe / edição completa / `{id}` excluído; `events.read/update/delete`. |
| GET `/types` | `{items, can_create, can_delete}`; consulta direta ao Repository, `events.read`. |
| POST `/types` | Cadastro/reutilização, 200; `events.types.create`. |
| DELETE `/types/<event_type_id>` | Exclusão; `events.types.delete`. |
| GET / POST `/<event_id>/attendance-lists` | Listar / criar lista (201); `events.attendance.read/create`. |
| GET / PUT / DELETE `/<event_id>/attendance-lists/<list_id>` | Detalhar / renomear / excluir; `events.attendance.read/update/delete`. |
| GET / POST `/<event_id>/attendance-lists/<list_id>/entries` | Listar / registrar crachá; `events.attendance.read/register`. |
| DELETE `/<event_id>/attendance-lists/<list_id>/entries/<entry_id>` | Remover presença; `events.attendance.delete_entry`. |
| GET `/<event_id>/attendance-lists/<list_id>/pdf` | Download privado; `events.attendance.export`. |

Nos caminhos acima, os IDs são inteiros nos decorators Flask. Lista/evento incompatíveis ou participante ausente retornam 404. PDF e downloads devem conservar os cabeçalhos privados e a validação de tipo de conteúdo do cliente.

GET na base recebe `page` ≥ 1, `per_page` de 1 a 100 (padrão 12), `search` até 120 caracteres e `status` com valores separados por vírgula. A API remove status repetidos e rejeita desconhecidos. GET de listas/participantes usa `PaginationQuery`; seis e 25 são escolhas da interface, não novos limites do backend.

| Contrato de saída | Campos principais |
|---|---|
| `EventOut` | ID, nome, descrição, tipo ID/nome, instrutor, conteúdo, início/fim e status. |
| `EventList`, `EventDetail` | Ambos incluem `capabilities` com `can_create`, `can_update` e `can_delete`; lista acrescenta paginação. |
| `AttendanceListOut` | ID, evento, nome e total; detalhe inclui capacidades da presença. |
| `AttendanceEntries` | Paginação, capacidades e registros com ID, código completo, nome, setor e empresa. |
| `AttendanceRegistered` | `item`, `created` e `lookup_status`; POST retorna 200 inclusive quando criou. |
| Exclusões | `{id}`; não retornam 204 no contrato atual. |

Schema inválido retorna 422; período/tipo inválido também usa `detail.json`. LDAP usa `detail.lookup_status`, em vez de erro de campo. Recurso ausente gera 404, tipo em uso 409, PDF/diretório indisponíveis 503. Demais erros comuns seguem [Base compartilhada](base-compartilhada.md).

## 4. Código e dados

| Local | Responsabilidade |
|---|---|
| [Módulo backend](../../backend/modules/events/) | `routes.py`, `schemas.py`, Services funcionais e SQL parametrizado no Repository. |
| [Feature Vue](../../frontend/src/features/events/) | Página, filtros, formulários, tipos, listas, leitor e clientes da API. |
| [Diretório](../../backend/integrations/employee_directory.py) | Consulta LDAP somente leitura, configuração separada do login antigo. |
| [PDF](../../backend/modules/events/attendance_pdf.py) | Renderização em memória; depende de ReportLab e do logo em `assets/`. |

Tabelas: `DJ_EVENTS`, `DJ_EVENT_TYPES`, `DJ_EVENT_ATTENDANCE_LISTS` e `DJ_EVENT_ATTENDANCE_ENTRIES`. Types usa chave única; presença tem vínculos/FKs e proteção por lista/matrícula. O período, o tipo e o uso de um tipo são validados nas transações correspondentes. A edição do evento não possui o mesmo controle `row_version` de Demandas; não presumir essa proteção.

| Tabela | Integridade prevista nos scripts |
|---|---|
| `DJ_EVENTS` | IDENTITY, autoria/data, campos públicos; período totalmente nulo ou fim posterior ao início; FK opcional de tipo para antigos. |
| `DJ_EVENT_TYPES` | IDENTITY, nome único não vazio, autoria/data. Não possui exclusão em cascata dos eventos. |
| `DJ_EVENT_ATTENDANCE_LISTS` | FK de evento com cascade, índice por evento/ID, autoria/data. Nome não possui unicidade por evento no script. |
| `DJ_EVENT_ATTENDANCE_ENTRIES` | FK de lista com cascade, código ASCII de 12 posições, campos opcionais e autoria/data; UNIQUE por lista/código completo. |

A repetição pelos oito dígitos finais é serializada pela trava da lista no fluxo da aplicação. A constraint SQL existente é por **código completo**, não por oito dígitos. Escritores externos podem violar a regra lógica; linhas históricas duplicadas não são fundidas ou excluídas automaticamente. Conferir esse ponto antes de criar importação ou novo escritor.

No código pesquisado de `app/services`, não foram encontradas referências às tabelas modernas de Eventos. O módulo não introduz e-mails, mensagens ou schedulers. Isso não elimina os ciclos/logs globais do portal. Eventos tem autoria/data de criação, mas não histórico próprio de edições/exclusões.

## 5. Schema, publicação e retorno

Os [scripts versionados](../../database/migrations/) são propostas para revisão e aplicação explícita; esta documentação não comprova que foram aplicados. Em uma instalação nova, conferir a sequência necessária:

1. `20261007_create_dj_events.sql` e `20261015_add_dj_events_schedule.sql`.
2. `20261015_create_dj_event_attendance.sql` e `20261016_add_dj_event_attendance_company_shift.sql`.
3. `20261016_drop_dj_event_attendance_shift.sql`, que remove turno, e `20261016_add_dj_event_types_and_details.sql` para tipos/opcionais.

Em ambiente existente com turno, publicar a API/build sem referências a `shift` antes de uma remoção de coluna autorizada. Depois dela, código antigo que usa turno fica incompatível. Não reaplicar scripts indiscriminadamente nem remover tabelas como retorno automático.

O script de tipos/detalhes depende do período e deve preceder a API que consulta esses campos. Não usar ordem alfabética como substituto das dependências indicadas no SQL. Registros antigos não recebem período/tipo fictícios; são preservados nulos até edição válida. A remoção de turno elimina valores e exige avaliação própria de backup/retorno.

Publicar backend, build compatível, logo e dependências conforme [Servidor e publicação](../docs/servidor-e-publicacao.md). O LDAP moderno depende de credenciais/configuração válidas; ausência pode permitir inicializar o recurso, mas impede confirmar presenças. SQL, diretório e leitor físico não foram verificados nesta revisão.

## 6. Conferência e evolução

No ambiente autorizado, conferir campos/limites e registros antigos; filtros/status/paginação; permissões e CSRF; tipo duplicado ou em uso; crachá inválido, repetido e ambíguo; LDAP indisponível; exclusão concorrente de lista; vínculo evento/lista/participante; cascatas em dados aprovados; PDF vazio/com muitas páginas; teclado, foco e resposta incerta sem repetição automática.

| Cenário | O que conferir |
|---|---|
| Período e status | Limites exatos de início/fim, fuso rejeitado, filtros, relógio TD e registro antigo sem período. |
| Tipos concorrentes | Nomes equivalentes reutilizados; exclusão disputada com novo vínculo sem perder integridade. |
| Presença repetida | Mesma matrícula com prefixos diferentes não aumenta total via fluxo normal; só completa ausências. |
| LDAP | Matrícula com zeros, ocorrência em campo errado, parcial, duas pessoas, truncamento, bind/timeout. |
| Concorrência | Registro contra exclusão de lista/evento e PDF contra escritas, sem órfãos ou confirmação indevida. |
| Interface | Enter tardio, perda de foco, leitura longa, partes durante envio e fechamento durante estabilização/API. |
| PDF | Lista vazia, várias páginas, textos longos, caracteres de markup, logo e MIME/cabeçalhos privados. |

Ao mudar um campo, revisar schemas, Services, Repository, tipos TypeScript, formulário/detalhe/PDF e SQL correspondente. Ao mudar captura, revisar também LDAP, mensagens, cache e atalhos. Uma mudança geral de grade/diálogo vai para o [padrão visual](../docs/padrao-visual.md), sem copiar regras de presença para componentes comuns.

Não há nova autenticação, notificações ou jobs específicos neste módulo. Mudanças futuras devem atualizar este documento e preservar a [base compartilhada](base-compartilhada.md). **O sistema não foi executado; a validação foi somente estática.**
