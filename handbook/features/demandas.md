# Demandas

**Estado atual:** a arquitetura moderna entrega **Nova solicitação** e **Minhas solicitações**, em `/app/demandas/solicitacoes`, e **Gestão de demandas**, em `/app/demandas/gerenciador`, somente para Transformação Digital (`area_id = 1`). O painel trabalha apenas com registros das tabelas novas; o gerenciador antigo continua separado. Código implementado não comprova schema aplicado ou publicação no servidor.

Revisão em **23/10/2026**, por análise estática de rotas, contratos, serviços, SQL, armazenamento, Vue e job automático. Os antigos documentos de [solicitações](../historico/handbook/solicitacoes-demandas.md) e [proposta do gerenciador](../historico/handbook/proposta-gerenciador-demandas.md) são históricos. O escopo deste arquivo é o módulo moderno; os fluxos antigos são citados para explicar a convivência.

## 1. Escopo e uso

O usuário escolhe **Solicitar demanda** (`demanda`) ou **Reportar erro** (`erro`), preenche o formulário e anexa evidências. A criação começa em `em_analise`, com `classification` nula; solicitante, área e status são definidos pelo backend.

Minhas solicitações mostra registros em que o usuário é solicitante ou contribuinte. Busca literal por título ou número, com ou sem `#`, filtro de tipo, contagem e paginação acontecem no servidor. A página usa 12 cards compactos; detalhes incluem conteúdo, anexos, histórico e capacidade de edição. O formulário de demanda mostra uma imagem ilustrativa de fluxo; o relato de erro usa a área de evidências sem essa imagem.

Solicitações modernas aparecem na aba Solicitações do painel novo. Não há importação, sincronização ou migração automática de tabelas legadas. O link de solicitações anteriores mantém o acesso ao fluxo antigo. Demandas internas só entram em Minhas solicitações quando houver pedido de informações, respeitando o vínculo de solicitante/contribuinte.

### Navegação e estados da página

- Sem seletor, a página abre Nova solicitação. `?tab=minhas` abre a listagem; `?request=<id>` também seleciona Minhas solicitações e tenta abrir o detalhe autorizado.
- `area`, quando fornecida, deve ser exatamente `Transformação Digital`; outra área recebe 400. O backend usa `AREA_ID = 1`, sem confiar em um ID de área recebido no payload.
- A navegação moderna tem Eventos, Solicitações, Gestão de demandas e retorno ao portal. O link **Consultar solicitações anteriores** aponta para `/demandas/solicitacoes?area=Transformação%20Digital&tab=minhas` no legado. A gestão exige também o perfil da área ou administração no backend.
- O formulário permanece montado ao trocar Nova/Minhas, preservando o rascunho na mesma página. Recarregar ou sair não persiste rascunho, arquivos ou chave de envio.
- Durante gravação, a página bloqueia troca de seção/rota interna; o diálogo bloqueia fechamento enquanto salva. Isso não impede fechamento do navegador nem prova cancelamento no servidor.

Após criação confirmada, a interface limpa o formulário, gera nova chave, atualiza cache/listagem, limpa filtros e mostra Minhas solicitações com mensagem de sucesso. Falha de listagem posterior não autoriza repetir a criação.

## 2. Campos e limites

| Campo | Contrato |
|---|---|
| `entry_kind` | `demanda` ou `erro`. |
| `title` | Obrigatório, até 250 unidades UTF-16. |
| `description` | Obrigatório, até 4.000 unidades UTF-16. |
| `urgency` | `Alta`, `Média` ou `Baixa`. |
| `contributor_id` | Opcional; outra pessoa ativa, não genérica e com nome/e-mail corporativo. |
| `assumptions`, `current_problems`, `expected_benefits` | Obrigatórios para demanda, até 4.000 unidades UTF-16 cada; normalizados para NULL em erro. |
| `submission_key` | UUID textual obrigatório na criação; identifica o envio. |
| `row_version` | Versão hexadecimal obrigatória na edição. |
| Documentos | De 1 a 10 arquivos; até 10 MiB por arquivo e 40 MiB no total, com conteúdo. |

Campos extras e caracteres inválidos são rejeitados; espaços externos são retirados. Os limites de texto consideram a representação do SQL Server. Não aceitar responsável, classificação ou status arbitrários do navegador.

Extensões: Word, Excel, PowerPoint, TXT, PDF e imagens PNG/JPG/JPEG/GIF/BMP/WebP previstas em `domain.py`. O limite HTTP é 45 MiB, incluindo multipart; IIS/proxy também precisam comportar o envio. Upload aguarda até 60 segundos; outras chamadas usam o cliente comum.

### Normalização e exemplo de entrada

Textos seguem o tamanho em unidades UTF-16, coerente com NVARCHAR; caracteres fora do plano básico podem consumir duas unidades. IDs de pessoas são texto, até 128 posições, preservando identificadores alfanuméricos e zeros. As datas de criação/atualização são gravadas em UTC por `SYSUTCDATETIME()`; `presentation.ts` as interpreta como UTC quando o retorno não informa fuso e as exibe localmente.

O JSON abaixo é apenas o conteúdo sintético do campo multipart `payload`, sem arquivos nem dados de usuário:

```json
{
  "entry_kind": "demanda",
  "title": "Automatizar uma conferência",
  "description": "Reduzir a digitação repetida no processo.",
  "urgency": "Média",
  "contributor_id": null,
  "assumptions": "O arquivo de origem seguirá o formato combinado.",
  "current_problems": "A conferência depende de cópia manual.",
  "expected_benefits": "Reduzir retrabalho e tempo de conferência.",
  "submission_key": "00000000-0000-4000-8000-000000000001"
}
```

Na edição, enviar JSON diretamente, substituir `submission_key` por `row_version` obtida no detalhe e incluir todos os campos editáveis. `row_version` tem 16 caracteres hexadecimais, representando os oito bytes do SQL Server; não é data nem contador calculado pelo cliente. A chave de criação deve ser UUID textual no formato minúsculo aceito pelo schema.

Para erro, `assumptions`, `current_problems` e `expected_benefits` são normalizados para NULL; o backend não persiste conteúdo desses campos como parte do relato. A validação de tipo/tamanho ainda pode rejeitar valores inválidos enviados. Trocar uma demanda existente para erro limpa esses campos na linha principal e registra a alteração no histórico.

## 3. Autorização, edição e repetição

Todas as rotas exigem sessão e GENERAL. As ações `demands.read/create/update` ficam em `domain.py`; o backend restringe registros à área e ao vínculo de solicitante/contribuinte. Recurso inacessível retorna 404. Escritas exigem o CSRF compartilhado.

Somente o solicitante edita a solicitação, enquanto o registro está em análise e sem classificação. O contribuinte consulta e baixa anexos. A edição revalida vínculo, estado e classificação sob trava e compara `row_version`; conflito retorna 409. Histórico e alteração usam a mesma transação. O PUT preserva anexos. A gestão permite inclusão e remoção lógica de anexos; o solicitante pode anexar documentos ao responder a um pedido de informações.

Na criação, `submission_key` e fingerprint do conteúdo/arquivos permitem reconhecer repetições: mesma chave/conteúdo devolve o registro; conteúdo diferente retorna 409. A verificação é serializada e depende da restrição única no banco. O browser conserva o mesmo envio após falha, sem repetição automática. Depois de abandonar ou recarregar o formulário, conferir a lista antes de iniciar outro cadastro: a chave não é persistida no navegador.

Uma falha na renovação da lista não desfaz a gravação. Resultado incerto exige conferência ou repetição do mesmo envio, sem alterar chave/dados inadvertidamente.

### Matriz de acesso atual

| Pessoa/contexto | Listar/detalhar/baixar | Editar |
|---|---|---|
| Solicitante, área atendida e GENERAL | Sim. | Se `em_analise`, classificação NULL, ação e versão válidas. |
| Contribuinte, área atendida e GENERAL | Sim. | Não; tentativa de edição retorna 404. |
| Outro usuário com GENERAL | Não vê o registro; detalhe/anexo retorna 404. | Não. |
| Sem sessão / sem GENERAL | 401 / 403 na API. | Negado antes da operação. |

As três ações da API de solicitações são mapeadas para GENERAL, mas esse perfil sozinho não concede acesso a todas as solicitações. A condição SQL inclui área e `(requester_id = actor_id OR contributor_id = actor_id)`. Não existe exceção administrativa nessa API pessoal; a API de gestão tem autorização própria por área. Alterar o contribuinte pode retirar o acesso da pessoa anterior; o serviço revalida a elegibilidade da pessoa selecionada ao salvar.

A lista de contribuintes consulta `JDT_USER_DETAILS`: `active = 1`, `generic = 0`, ID diferente do solicitante, nome não nulo e e-mail corporativo não vazio. Não cria usuários, envia convites ou consulta LDAP. A mesma condição é aplicada na gravação; não confiar apenas nas opções do Select. Se o colaborador antigo deixar de ser elegível, a interface ainda pode mostrá-lo como atual, mas o backend exige uma escolha válida ou sua remoção.

### Fluxo de criação e idempotência

```text
Guarda HTTP e limite → multipart → RequestCreate → ação demands.create
    → preparar/validar conteúdo dos arquivos
    → fingerprint → transação TD → buscar envio sob trava
        ├── existente e igual: devolver o detalhe existente
        ├── existente e diferente: conflito 409
        └── novo: validar contribuinte → inserir solicitação
                 → salvar arquivos → inserir metadados/histórico → obter detalhe
    → commit → resposta 201
```

O fingerprint SHA-256 usa os dados normalizados e, para cada arquivo, nome saneado e digest, preservando a ordem da lista. Mesma chave com arquivos reordenados, renomeados ou dados diferentes pode ser conflito; a recuperação deve repetir o mesmo envio. O bloqueio `UPDLOCK, HOLDLOCK` e a chave única serializam tentativas concorrentes da mesma área/solicitante/chave.

Todos os arquivos são novamente preparados antes de conferir a chave. Se o envio já existe e coincide, não há nova gravação de arquivos/histórico; a resposta de criação ainda é 201 no contrato atual. A deduplicação não procura títulos parecidos nem pedidos equivalentes com outra chave.

O frontend mantém chave e conteúdo após falha de envio. Em rede/timeout, 5xx ou sucesso HTTP com conteúdo inesperado, bloqueia alteração/limpeza do formulário e oferece **Conferir minhas solicitações** ou **Confirmar envio novamente**. Não faz retry automático. Um erro definitivo de validação permite corrigir campos. Após recarregar, a chave anterior se perde: conferir a listagem antes de iniciar outra solicitação.

### Fluxo de edição e histórico

O Service abre transação, lê a solicitação visível com UPDLOCK/HOLDLOCK, exige vínculo de solicitante e confere status/classificação. O UPDATE repete essas condições e compara a versão recebida. Se nenhuma linha for atualizada, retorna 409 para reabrir os dados; não sobrescreve deliberadamente outra edição.

Os campos são comparados com a linha atual. Se houver mudanças, grava evento `updated` com valores anteriores/posteriores em JSON na mesma transação. Na criação, grava `created`. Um PUT sem mudança de conteúdo pode atualizar data/ROWVERSION sem gerar evento de mudança. O campo `history` expõe evento, autor, data e `changes`; o detalhe mostra justificativas, respostas e alterações anteriores/posteriores. Ações de gestão também geram histórico.

A capacidade `can_update` orienta o botão, mas é recalculada e não substitui as condições na escrita. Não há inclusão, troca ou exclusão de anexos pelo PUT.

## 4. API

Base `/api/v1/demands`; IDs são inteiros nas rotas Flask. `area`, quando informado, deve ser a área atendida.

| Método e caminho relativo | Entrada e retorno |
|---|---|
| GET `""` | `page`, `per_page`, `search`, `entry_kind`; lista paginada e capacidade de criar. |
| GET `/contributors` | IDs/nomes elegíveis; consulta direta ao Repository, exige `demands.create`. |
| POST `""` | Multipart com somente `payload` (JSON de `RequestCreate`) e `files`; detalhe, HTTP 201 após commit. |
| GET `/<demand_id>` | Detalhe, anexos, histórico, versão e `can_update`. |
| PUT `/<demand_id>` | JSON completo de `RequestUpdate`; detalhe após commit. |
| GET `/<demand_id>/attachments/<attachment_id>` | Download autorizado, privado, sem cache e com `nosniff`. |
| POST `/<demand_id>/information-reply` | Multipart `payload` com `row_version`, `information_id` e `reply`; arquivos opcionais. Somente o solicitante responde ao pedido aberto. |

Erros seguem `{message, detail}`: campos inválidos 422, conflito 409, tamanho HTTP 413 e armazenamento indisponível 503. A área e o limite de request são conferidos antes do parsing do formulário.

### Detalhes do contrato

GET da base usa `page` inicial 1, `per_page` padrão 12 e máximo 100, `search` até 250 caracteres e `entry_kind` igual a `todos`, `demanda` ou `erro`. A busca escapa curingas e compara também ID textual, retirando `#` inicial; ordenação por ID decrescente. O total corresponde ao mesmo escopo de visibilidade e filtro, não a todas as demandas.

O POST aceita somente a chave de formulário `payload` e a chave de arquivos `files`, que pode ter vários itens. Mimetype/formato multipart incorreto gera 400. Não definir `Content-Type` manualmente no cliente: FormData fornece o boundary. A API valida `payload` com `RequestCreate.model_validate_json` e adapta as mensagens para `detail.json`.

| Resposta | Conteúdo público |
|---|---|
| Lista | ID, entrada, título, descrição, urgência, status, data, nome do solicitante e relação (`requester`/`contributor`), paginação e capacidade de criar. |
| Detalhe | Campos da lista, contribuinte, contexto, atualização, versão, `can_update`, anexos, histórico, `information_requests` e `can_reply`. |
| Anexo no detalhe | Somente ID, nome e tamanho; sem caminho/chave privada ou digest. |
| Histórico no detalhe | ID, tipo do evento, nome do autor, data e mudanças em JSON. |
| Contribuintes | `{items: [{id, name}]}`, sem e-mail/cadastro completo. |

O módulo aplica `Cache-Control: private, no-store` a suas respostas. Downloads são links autenticados para a rota de anexo; o servidor responde como `application/octet-stream`, attachment, sem resposta condicional e com `X-Content-Type-Options: nosniff`. Não servir o armazenamento por uma URL estática.

### Painel de gestão

O painel tem abas **Demandas** e **Solicitações**, sem gráficos. Cards agrupados por responsável são de consulta; gerenciamento, anexos, tarefas e histórico ficam no diálogo, em três abas. A aba Solicitações mostra entradas ainda sem responsável, em análise ou aguardando informações.

Na análise, aceitar exige responsável elegível e classificação **Melhoria** ou **Projeto**; um relato de erro mantém **Erro**. Recusar exige justificativa. Pedir informações permite escolher complemento ou agendamento de reunião e exige uma descrição. O solicitante recebe e-mail e responde em Minhas solicitações, com anexos opcionais; a resposta restaura o estado anterior e notifica quem pediu. Aceitar, recusar ou cancelar encerra um pedido de informações ainda aberto.

**Nova demanda ou aviso** pede primeiro Projeto, Melhoria, Erro, Atividade ou Aviso. Os quatro primeiros usam a mesma `DJ_DEMANDS`: origem `interna`, responsável obrigatório e status `a_fazer`. Projeto/melhoria exigem os campos de contexto e evidências; erro exige descrição/evidências; atividade admite anexos opcionais e os campos de tempo/dificuldade/observações. Não há recorrência moderna. Avisos têm título, descrição, início/fim locais opcionais e finalização automática após o fim; ficam em tabela própria.

| Estado | Ações de andamento |
|---|---|
| A fazer | Iniciar, cancelar; outras ações: agendar início, cancelar agendamento existente, solicitar informações/reunião. |
| Em andamento | Concluir, cancelar; outras ações: solicitar informações/reunião, iniciar validação, pausar, aguardar terceiros. |
| Em validação | Concluir, retomar execução, cancelar e solicitar informações. |
| Pausado / aguardando terceiros | Retomar, cancelar e solicitar informações. |
| Aguardando informações | Resposta pelo solicitante; cancelamento pelo responsável. |
| Concluído / cancelado / recusado | Consulta, sem edição operacional. |

Cancelamento, pausa e espera por terceiros exigem justificativa; pausa também exige previsão de retorno. O prazo inicial pode ser definido ao iniciar/agendar; demandas diferentes de atividade precisam dele. Alterar prazo já existente usa exclusivamente a ação própria com justificativa. O editor de gerenciamento e as demais ações não aceitam campo de prazo. Agendamento exige início futuro e prazo compatível; o card exibe início agendado, prazo e tag **Demanda agendada**.

O filtro começa com fim igual à data de hoje do SQL Server e início vazio, exibindo ativas. Informar o início acrescenta as concluídas entre as duas datas, inclusive, por `completed_on`; a criação das demandas ativas não é limitada pelo período. Responsável, tipo, dificuldade, status e busca continuam aplicados ao conjunto. Selecionar explicitamente um status restringe esse resultado.

Todas as rotas `/api/v1/demand-management` exigem sessão, GENERAL e perfil Transformação Digital ou administração normalizada. A consulta abrange a área; alterações operacionais exigem responsável atual ou administrador, estado compatível e versão. A análise de solicitações é permitida aos gestores da área. As ações são mapeadas em `MANAGEMENT_ROLES`. Avisos são editáveis/finalizáveis pelo autor ou administrador. Tarefas também verificam a versão da demanda; atualizações de tarefa verificam sua própria versão.

| Método/caminho relativo | Finalidade |
|---|---|
| GET `/options`, GET `""`, GET `/requests`, GET `/<id>` | Opções, painel filtrado, fila de análise e detalhe. |
| POST `""` | Criar demanda interna com multipart e chave de envio. |
| POST `/<id>/review` | Aceitar, recusar ou pedir complemento/reunião. |
| PUT `/<id>`, POST `/<id>/actions`, PATCH `/<id>/deadline` | Gerenciamento, transição e prazo com justificativa. |
| POST `/<id>/tasks`, PUT/DELETE `/<id>/tasks/<task_id>` | Criar, atualizar ou remover tarefa. |
| POST `/<id>/attachments`, GET/DELETE `/<id>/attachments/<attachment_id>` | Adicionar, baixar ou remover logicamente anexo. |
| POST `/notices`, PUT/DELETE `/notices/<notice_id>` | Criar, editar ou finalizar aviso. |

Demandas internas e avisos usam chave/fingerprint para repetição segura da criação. O envio de e-mail é enfileirado junto da mudança e ocorre após commit. Falha de transporte não desfaz a gravação; a API retorna aviso de e-mail pendente. O Auto tenta novamente após cinco minutos, até cinco tentativas. Se houver interrupção com estado `sending`, o resultado é incerto: exige conciliação manual, sem reenvio automático que possa duplicar e-mail. O destinatário é consultado no cadastro compartilhado; responsável/contribuinte ativos podem receber cópia.

`/app/demandas/gerenciador?view=requests` abre a análise; `?demand=<id>` abre o detalhe autorizado a partir de uma notificação de resposta. A solicitação enviada ao usuário mantém o link de Minhas solicitações.

## 5. Arquivos, transações e dados

Anexos ficam em `<instance_path>/modern_demand_attachments/`, fora dos assets públicos. O nome de download é saneado; o armazenamento usa chave aleatória, sem incorporar nome ou caminho enviado. O download autoriza a demanda, confere o vínculo do anexo e valida chave, contenção de caminho e ausência de link simbólico no arquivo.

Arquivos são preparados antes da transação SQL. Falhas cobertas pela compensação removem somente arquivos novos da operação. Falha durante commit preserva os arquivos, pois o resultado pode ser incerto; conciliação exige uma ação específica, sem limpeza automática. SQL e filesystem não formam uma transação única.

### Proteções e limites do armazenamento

`prepare()` lê até 10 MiB + 1 por arquivo, rejeita vazio/excesso, soma o total e calcula SHA-256. O nome passa por `secure_filename`; a base do nome é limitada a 180 caracteres e a extensão é normalizada. Extensões exatas: `doc`, `docx`, `xls`, `xlsx`, `ppt`, `pptx`, `txt`, `pdf`, `png`, `jpg`, `jpeg`, `gif`, `bmp`, `webp`.

Os bytes preparados ficam em memória antes da transação. `save()` cria o diretório sob demanda e escreve com abertura exclusiva (`xb`), usando UUID hexadecimal de 32 caracteres. `resolve()` aceita apenas esse formato, rejeita symlink no arquivo e exige contenção na pasta base resolvida. ACLs e proteção da própria pasta continuam sendo requisitos do ambiente.

Esses controles não são antivírus nem validação de assinatura/MIME do conteúdo. SHA-256 identifica conteúdo para integridade/fingerprint; não certifica que um documento é seguro. A aplicação não implementa quarentena ou preview dos anexos. Uma evolução nessa área exige análise própria.

Se `save()` falhar com erro de filesystem, tenta remover apenas os arquivos novos daquela execução. Se falhar a inserção de metadados/histórico ou a montagem do detalhe depois de salvar, o Service solicita essa compensação e relança para rollback SQL. A remoção é uma tentativa e pode falhar; não há promessa de ausência de órfãos. Falha ao sair da transação, inclusive durante commit, preserva arquivos para conciliação por resultado incerto.

| Fonte | Responsabilidade |
|---|---|
| `DJ_DEMANDS` | Solicitação, participantes, estado, datas, ROWVERSION, chave e fingerprint do envio. |
| `DJ_DEMAND_ATTACHMENTS` | Metadados, tamanho, SHA-256 e chave privada dos arquivos. |
| `DJ_DEMAND_HISTORY` | Criação e edição; autor, data e mudanças em JSON. |
| `DJ_DEMAND_TASKS` | Tarefas vinculadas à demanda, versão e conclusão. |
| `DJ_DEMAND_INFORMATION_REQUESTS` | Perguntas/reuniões, estado anterior e respostas; somente um pedido aberto por demanda. |
| `DJ_DEMAND_NOTICES` | Avisos independentes com período e finalização. |
| `DJ_DEMAND_NOTIFICATIONS` | Fila persistente de e-mail por evento do histórico. |
| `JDT_USER_DETAILS` | Consulta compartilhada de nomes e colaboradores; não substitui as tabelas modernas. |

O [script de criação](../../database/migrations/20261019_create_dj_demands.sql) prevê IDENTITY, índices, FKs dos anexos/histórico e unicidade de `(area_id, requester_id, submission_key)`. É sujeito a revisão/aplicação explícita; esta documentação não comprova sua execução. A API depende desses objetos e não aplica o script automaticamente.

A migration inclui checks de área positiva, participantes, entrada/classificação, texto obrigatório, urgência e detalhes de demanda. Anexos/histórico possuem FK para a solicitação **sem cascade de exclusão**. IDs de usuário são referências lógicas ao cadastro compartilhado: nenhuma FK foi presumida sem confirmar tipo/chave reais. Não substituir IDENTITY por `MAX(id) + 1`.

A coluna `classification` recebe `melhoria`, `projeto` ou `atividade` para entrada demanda; erro mantém classificação NULL. O [script de gestão](../../database/migrations/20261023_add_dj_demand_management.sql), aplicado depois do script inicial, acrescenta as colunas operacionais e tabelas auxiliares. Ele adapta o check de contexto para atividade, mantém as solicitações já cadastradas e não copia nem altera tabelas JDT. Não é um script de reaplicação idempotente. A máquina de estados é validada no serviço, com travas, versão e histórico.

Criação/atualização/início/conclusão/histórico usam UTC; `completed_on`, prazos, início agendado e previsões usam datas do calendário local do SQL Server. Períodos de avisos usam horário local sem fuso. Remoção de anexo preenche `deleted_at`, sem apagar o arquivo físico; até 30 anexos ativos por demanda, mantendo o limite de dez por envio.

## 6. Onde alterar e publicar

- [Backend](../../backend/modules/demands/): rotas/schemas, Services funcionais, Repository, definições de domínio e `storage.py`.
- [Frontend](../../frontend/src/features/demands/): página, formulário, detalhe, cards, tipos e cliente HTTP.
- [Bootstrap](../../backend/bootstrap.py): inicializa o adaptador de armazenamento; rotas fornecem engine, identidade, permissões e demais dependências aos serviços funcionais.
- [Auto moderno](../../app/services/jobs/mon_mon_auto_modernDemands.py): job explícito a cada minuto no Auto, separado do job legado; inicia agendamentos vencidos em `a_fazer` e processa a fila de e-mails. Antes da migration, retorna sem trabalho se a tabela da fila não existir.

Seguir [Servidor e publicação](../docs/servidor-e-publicacao.md), com backend/build compatíveis, schema revisado, limites de upload, ACLs e backup de tabelas **e** arquivos. Retorno de código não remove solicitações ou documentos nem os torna visíveis ao legado.

| Mudança desejada | Onde começar e o que acompanhar |
|---|---|
| Campo ou regra de cadastro | `schemas.py`, Services, Repository, migration quando necessária, tipos e `RequestForm.vue`/`RequestDetail.vue`. |
| Visibilidade/edição | `_VISIBLE` no Repository, Services, ações/capacidades e consultas de anexo; não alterar só o card. |
| Arquivo/limites | `domain.py`, `storage.py`, request/IIS, formulário e contrato de download; preservar compensação. |
| Rascunho/envio incerto | `RequestForm.vue`, `RequestsPage.vue`, `api.ts` e o contrato de idempotência no Service. |
| Apresentação | `RequestCard.vue`, `presentation.ts` e componentes comuns; datas UTC diferem do período local de Eventos. |

Publicação: revisar/aplicar o script inicial, se ainda ausente, e depois o script de gestão **antes de publicar este backend**, pois também as consultas de Minhas solicitações passam a depender das novas colunas/tabelas. Conferir armazenamento/limites; publicar backend e build compatíveis e atualizar/reiniciar o Auto em janela autorizada para os agendamentos e retentativas. Validar acessos de solicitante/contribuinte/gestor e convivência com o legado. O build também depende da imagem pública `app/static/images/FLUXO.PNG` usada no formulário; ela não é um anexo de usuário.

## 7. Limites e verificações pendentes

Não estão incluídos gráficos, recorrências modernas ou migração dos registros antigos. A decisão atual é começar somente com dados das tabelas novas. A [proposta anterior](../historico/handbook/proposta-gerenciador-demandas.md) preserva ideias históricas; não substitui os contratos atuais nem comprova schema aplicado.

### O que permanece da proposta e o que mudou

| Assunto | Situação correta para próximas entregas |
|---|---|
| Armazenamento | A decisão posterior escolheu tabelas `DJ_*` novas. A antiga ideia de unificar tudo em `JDT_REQUEST_IMPROVEMENTS_SMALL` foi superada. |
| Entrada/classificação | Solicitante escolhe demanda ou erro; gestão classifica demanda como melhoria/projeto. O cadastro interno também admite atividade. |
| Atividades e execução | Mesma tabela de demandas, gerenciamento, tarefas, anexos e histórico; avisos mantêm tabela própria. |
| Recorrências | Ausentes no moderno; nenhuma automação recorrente antiga foi desligada. Agendamento inicia uma demanda já existente. |
| Migração | Não realizada. Exige levantamento do schema real, mapeamento de IDs/participantes/status, anexos, histórico e plano de conciliação/retorno. |
| Indicadores/notificações | Sem gráficos; e-mail implementado com fila pós-commit, consulta e resposta em Minhas solicitações. |

Os fluxos antigos em [demandRequests](../../app/routes/demandRequests/), [demandManagement](../../app/routes/demandManagement/) e o [job automático legado](../../app/services/jobs/mon_mon_auto_demandManagement.py) continuam ligados às tabelas legadas. Somente o novo job moderno usa `DJ_DEMAND*`; o registro dele no Auto preserva os jobs anteriores.

### Cenários essenciais para validação autorizada

| Grupo | Casos e resultado a conferir |
|---|---|
| Campos | Demanda/erro, normalização, UTF-16, opcionais, contribuinte inativo/igual ao solicitante, campos extras. |
| Acesso | Solicitante, contribuinte e terceiro; outra área; anexo de outra demanda; sessão/CSRF. |
| Criação repetida | Mesmo envio simultâneo, mesmo envio após timeout, chave reutilizada com dados/ordem de arquivos alterados. |
| Edição | Versão antiga, registro já analisado/classificado, contribuinte tentando editar, mudança para erro e histórico. |
| Arquivos | Zero/11 arquivos, vazio, limites exatos, nome/caminho malicioso, extensão rejeitada e arquivo privado ausente. |
| Falhas | Erro ao salvar arquivo, inserir metadados, montar resposta e confirmar transação; conferir SQL e arquivos juntos. |
| Interface | Rascunho entre seções, envio incerto bloqueado, foco, URL do detalhe, volta da página e sucesso com falha de renovação. |
| Gestão | Aceitar melhoria/projeto/erro, recusar com motivo, responsáveis/perfil/admin, versão antiga, tarefas e alterações somente dentro do detalhe. |
| Informação | Pergunta/reunião, e-mail, resposta apenas pelo solicitante, arquivos opcionais, retorno ao estado anterior e concorrência com aceite/cancelamento. |
| Datas e prazo | Ativas antigas mais conclusões inclusivas no período; ação própria exige motivo; início agendado/card/job sem recorrência. |
| Avisos/e-mail | Período, finalização, repetição de cadastro, falha após commit, cinco tentativas e resultado incerto em `sending`. |

Nenhum desses cenários foi executado nesta revisão documental. Não existe evidência aqui de ACL efetiva, aplicação do SQL, ausência de órfãos ou operação correta sob concorrência real.

Em ambiente autorizado, conferir criação de demanda/erro, limites, contribuinte, área e vínculo por usuário, CSRF, edição negada, concorrência, repetição após timeout, armazenamento/commit, download/path traversal, anexos e histórico, teclado/foco e convivência com o legado. **O sistema não foi executado; a validação foi somente estática.**
