# Retirada do linked server Plex no Digital JOST

## Objetivo e situação atual

Este documento organiza o trabalho necessário para retirar o `PLEX_DSN_JOST`. O inventário descreve o levantamento inicial; a implementação posterior dos catálogos e da retirada do S30 está nas seções 7.5 e 7.6. A criação/importação dos motivos e a publicação ainda precisam ser feitas pelo responsável, conforme a seção 15. Nenhuma execução de banco ou sistema foi realizada pelo agente.

**A primeira entrega implementada retira a consolidação S30 e o consumo de `TEMP_WORKCENTER_STATUS`: as telas e o M5 consultam as fontes locais diretamente.** Centros vêm de `DJ_WORKCENTERS`; motivos ativos vêm de `DJ_WORKCENTER_EVENTS`, importados manualmente por CSV. Isso não encerra a migração: `getPlex()`, produção, relatórios e alteração de paradas ainda possuem acessos próprios.

O levantamento inicial encontrou **19 referências diretas ao linked server em 7 arquivos Python**: 13 ocorrências de `OPENQUERY` e 6 de `EXEC ... AT`, estas últimas envolvendo quatro procedimentos distintos. Os dois `OPENQUERY` do S30 foram retirados nesta implementação. O levantamento exclui cópias e backups do escopo ativo. Há também um script SQL de diagnóstico que utiliza o linked server.

O registro de falha apresentado mostra uma exceção de acesso à memória no módulo `ivoa27`, durante uma consulta ao Plex. Ele identifica um componente envolvido na falha, mas não demonstra, sozinho, que o peso da consulta foi sua causa. A substituição proposta também busca diminuir consultas remotas repetidas e a dependência do provedor dentro do SQL Server.

Os caminhos citados neste documento são relativos à raiz do repositório. Código versionado e agendamentos encontrados não comprovam a versão publicada, os serviços ativos nem a configuração efetiva de produção.

## 1. Ordem de trabalho: urgência e facilidade

As dificuldades abaixo são relativas. Não são estimativas de prazo e pressupõem acesso aos contratos de dados e uma fonte substituta aprovada.

| Ordem | Frente | Urgência | Dificuldade | Por que fazer nessa posição |
|---|---|---|---|---|
| 1A | Catálogos locais de centros e motivos | Muito alta, como pré-requisito | Baixa a média no código; depende da obtenção dos dados | São dados compartilhados, com interface existente em `getPlex()`. Destravam o S30 e várias telas. |
| 1B | S30 e `TEMP_WORKCENTER_STATUS` | Muito alta | Média | O job está agendado a cada 30 segundos e contém a consulta identificada no dump. Podemos preservar a tabela e seus consumidores. |
| 2 | Taxas padrão e equipe por peça/centro | Alta | Média | A mesma informação é consultada por monitoramento, sinal e produção. Uma sincronização compartilhada atende vários pontos. |
| 3 | Disponibilidade e indicadores de produção | Alta | Alta | Há cálculos locais parecidos, mas precisam ser comparados aos contratos dos procedimentos Plex. |
| 4 | Histórico detalhado de paradas | Alta; iniciar o levantamento desde o começo | Alta | Precisamos preservar períodos anteriores à cobertura TD, turnos, duração e identificação original das paradas. |
| 5 | Solicitação e aprovação de alteração de paradas | Alta pelo impacto operacional | Alta | A escrita já usa HTTP, mas a leitura e validação da parada original ainda usam o linked server. Exige preservar aprovações e consistência entre sistemas. |
| 6 | Desativação final no servidor | Somente após concluir as dependências | Depende do inventário do DBA | Outros sistemas, objetos SQL e processos de alimentação podem depender do mesmo linked server. |

As frentes 3, 4 e 5 precisam de descoberta técnica desde o início, mesmo que sejam implantadas depois. A ordem não significa esperar terminar o S30 para pedir os contratos ao Plex.

**O caminho mais fácil para começar:** manter o formato de retorno de `getPlex()` e o formato de `TEMP_WORKCENTER_STATUS`, mudando a origem dos dados. **O mais difícil:** substituir as regras dos procedimentos remotos e garantir continuidade do histórico e das aprovações.

## 2. Como a conexão funciona

Hoje há duas etapas distintas:

```text
Digital JOST / schedulers
  → SQLAlchemy + pyodbc
  → SQL Server
  → OPENQUERY ou EXEC ... AT PLEX_DSN_JOST
  → MSDASQL / driver ODBC do Plex
  → Plex
```

`CNNX_PLEX`, em `app/utils/constants.py`, configura uma conexão ao SQL Server. A engine compartilhada é preparada em `app/utils/db_utils.py`; o S30 também prepara sua própria engine. O nome `plex` no código não significa necessariamente conexão direta ao serviço Plex.

**Retirar o linked server não exige retirar o SQL Server nem todas as chamadas a `get_engine('plex')`.** As consultas às tabelas de integração locais podem continuar, desde que o DBA confirme a natureza desses objetos e a independência de sua alimentação. Trocar somente `CNNX_PLEX` não resolve: existem chamadas ao linked server executadas também pelo engine `jdt`.

## 3. Inventário dos acessos diretos

| Arquivo e ponto de referência | Referências | Função atual | Mudança necessária |
|---|---:|---|---|
| `app/utils/dynamic_constants.py`, linhas 61 e 89 | 2 | Carrega centros de trabalho e eventos/motivos no `PlexDataManager`. | Alimentar o cache a partir de uma fonte sem linked server, preservando colunas, tipos, filtros e tratamento de falhas. |
| `app/services/jobs/mon_mon_s_30_monitoringOverall.py`, linha 83 | 2 | Combina paradas locais com centros e motivos Plex; grava `TEMP_WORKCENTER_STATUS`. | Substituir os dois `OPENQUERY` por catálogos locais. Preservar a consolidação com FTM e a transação de publicação. |
| `app/routes/jdt/monitoring.py`, linhas 408, 562 e 668 | 3 | Quadro Hora e Tela de OEE: tempo padrão, equipe e classificação de motivos. | Consultar relações locais de peça/centro/operação e motivos. Preservar cálculos e filtros próprios de cada tela. |
| `app/routes/reports/oee.py`, linha 48 | 1 | Relatório de sinal e Excel: obtém tempo padrão por peça e centro. | Substituir a origem de `Ideal_Rate` e seus relacionamentos, mantendo o cálculo de tempo padrão e o formato do relatório. |
| `app/routes/operation/production.py`, linhas 331, 393, 397, 401, 605, 627 e 652 | 7 | Produção mensal, indicadores e Excel: taxas, cadastros e procedimentos remotos. | Substituir as três consultas `OPENQUERY` e as quatro chamadas `EXEC ... AT` por fontes locais ou APIs equivalentes. |
| `app/utils/business.py`, linhas 607 e 618 | 2 | `getStopsData()` obtém histórico de paradas por procedimento remoto em dois caminhos de execução. | Preservar o contrato da função e trocar o acesso remoto por histórico local completo ou API equivalente. |
| `app/routes/request/workcentersLogChange.py`, linhas 368 e 581 | 2 | Busca a parada original por `Log_Key` para solicitação e aprovação. | Criar consulta equivalente sem linked server e manter as verificações de identidade, período, motivo e concorrência. |

O arquivo `database/diagnostico_aprovacao_paradas_3350_3352_3359.sql` também contém uma consulta ao linked server. Ele é um diagnóstico, não um job identificado como automático. Sua orientação precisará ser revista quando a fonte for retirada, para não induzir seu uso futuro.

Não foram encontradas referências diretas ao nome do linked server no backend moderno consultado. Isso não prova independência da aplicação inteira: a inicialização e recursos compartilhados ainda convivem com o legado.

## 4. Telas, jobs e efeitos indiretos

### 4.1 Consumidores de `TEMP_WORKCENTER_STATUS`

A rotina S30 preenchia a tabela com dados Plex e FTM. Os cinco consumidores abaixo foram migrados para `backend/modules/monitoring/current_status.py`; a tabela física foi preservada, mas deixou de ser lida e preenchida pelo código ativo identificado.

| Consumidor | Local | Efeito de uma consolidação desatualizada |
|---|---|---|
| Alerta de Paradas — `/monitoramento/paradas` | `app/routes/jdt/monitoring.py`, `monitoring_stop_post()` | Exibição de paradas e responsáveis pode ficar desatualizada. |
| Painel Geral — `/monitoramento/geral` | Mesmo arquivo, `monitoring_overall_post()` | O componente de situação/parada deixa de acompanhar a fonte. A tela também consulta outros dados. |
| Quadro Hora — `/monitoramento/quadro` | Mesmo arquivo, `monitoring_frame_post()` | Parte do status exibido depende da tabela. |
| Tela de OEE — `/monitoramento/oee` | Mesmo arquivo, `monitoring_oee_post()` | Parte do status exibido depende da tabela. |
| Notificações de paradas no Teams — M5 | `app/services/jobs/mon_mon_m_5_monitoringAlerts.py` | Notificações podem se basear em dados antigos. Agendamento encontrado: cinco minutos. |

O serviço `RunS30Scheduler`, em `app/services/run_s_30_scheduler.py`, não agenda mais a consolidação. Um processo antigo já iniciado precisa ser parado no servidor: publicar arquivos não altera o código em memória. O M5 mantém seu agendamento próprio em `app/services/run_m_5_scheduler.py`.

### 4.2 Consumidores dos catálogos de `getPlex()`

O cache oferece `getPlex('workcenters')` e `getPlex('events')`. Seu intervalo atual de atualização é de quatro horas por processo, com uma primeira tentativa ao iniciar o gerenciador. Há também tentativa de carregar um catálogo ainda não inicializado durante seu acesso.

| Área | Arquivos principais | Dependência |
|---|---|---|
| Monitoramento Industrial | `app/routes/jdt/monitoring.py` | Seleção de centros e cadastro de hardware. |
| Produção e relatórios de OEE | `app/routes/operation/production.py`, `app/routes/reports/oee.py` | Filtros, nomes dos centros e descrições dos motivos. |
| Planejamento operacional | `app/routes/operation/planning.py`, `app/utils/planning_availability.py` | Metas, planos, histórico, classificações e disponibilidade. |
| Disponibilidade da manutenção | `app/routes/reports/maintenance.py`, `app/utils/maintenance_availability.py` | Centros e classificação dos motivos de manutenção. |
| Qualidade/QSB | `app/routes/operation/quality.py` | Cadastro de centros utilizado pelos fluxos da área. |
| SSMA | `app/routes/operation/security.py` | Centros e áreas em formulários. |
| Cadastros gerais | `app/routes/factoryRegister/default.py` | Metas, fatores, 5S e exports correspondentes. |
| Matriz | `app/routes/factoryRegister/matrix.py` | Cadastro de centros e painel. |
| Configuração de alertas | `app/routes/jdt/userManager.py` | Centros e motivos disponíveis para configuração. |
| Alteração de paradas | `app/routes/request/workcentersLogChange.py` | Busca, descrição, classificação, seleção de motivos e validação das aprovações. |

Preservar a interface de `getPlex()` reduz o número de mudanças nos consumidores. Isso não substitui a revisão dos acessos diretos listados na seção 3.

## 5. Soluções possíveis

| Solução | Facilidade e reaproveitamento | Limitações | Indicação |
|---|---|---|---|
| APIs/Data Sources HTTPS alimentando tabelas locais | Boa para cadastros e dados reutilizados; mantém consultas SQL locais e consumidores atuais. O projeto já possui uma chamada HTTP ao Plex. | Precisamos confirmar endpoints, acesso, filtros, paginação, limites e política de atualização. Armazenamento novo exige desenho e autorização de banco. | Direção preferida para catálogos, taxas e histórico compartilhado. |
| API HTTPS sob demanda no backend | Próxima do padrão já utilizado para atualizar uma parada. Pode atender busca pontual por identificador. | Vincula a operação ao tempo e à disponibilidade da API. Fazer uma chamada por linha ou por card pode criar outra fonte de sobrecarga. | Boa candidata para validação pontual de uma parada antes da aprovação. |
| Reaproveitar tabelas e cálculos TD existentes | Há código pronto para `Mach_2_Current_Status`, paradas e disponibilidade. Pode reduzir a necessidade de buscar histórico recente no Plex. | Cobertura histórica, centros, turnos, motivos e equivalência dos indicadores precisam ser conferidos. O produtor desses dados também precisa ser independente do linked server. | Reaproveitar onde houver equivalência comprovada. |
| Extrator ODBC em processo separado alimentando SQL local | Pode aproveitar as consultas atuais se APIs equivalentes não estiverem disponíveis. | Retira o acesso nativo do processo SQL Server, mas mantém a dependência do driver em outro processo. Exige operação, recuperação e monitoramento próprios. | Alternativa transitória a avaliar com TI/Plex, caso HTTPS não cubra o necessário. |

Uma API que apenas execute, por trás, as mesmas consultas no `PLEX_DSN_JOST` mantém a dependência. O mesmo vale para criar uma view local que continue usando esse linked server.

Arquitetura proposta para as leituras recorrentes:

```text
Plex — API/Data Source aprovada
  → sincronização centralizada, fora das requisições das telas
  → catálogos, relações e histórico locais
  → SQL local dos jobs e relatórios
  → telas, Excel e alertas existentes
```

A documentação oficial apresenta integração Plex por REST/JSON. Isso comprova a existência da opção de integração, não a disponibilidade dos dados específicos no ambiente da empresa. A cobertura deverá ser confirmada com o responsável pelo Plex.

Referências: [Plex Connect](https://plex.rockwellautomation.com/en-us/company/newsroom/plex-systems-launches-plex-connect-integrating-manufacturing-cloud.html) e [portal oficial de desenvolvedores](https://developers.plex.com/).

## 6. O que já existe e podemos reaproveitar

| Recurso existente | Onde | Como ajuda | O que ainda falta |
|---|---|---|---|
| Interface única para centros e motivos | `app/utils/dynamic_constants.py`, `getPlex()` | Permite trocar a origem preservando os consumidores. | Nova fonte, catálogo persistente quando necessário e tratamento de desatualização. |
| Consolidação transacional do S30 | `app/services/jobs/mon_mon_s_30_monitoringOverall.py` | A gravação em `TEMP_WORKCENTER_STATUS` já está concentrada. | Trocar os joins remotos e preservar o conjunto de colunas e regras. |
| Consulta TD de paradas | `app/utils/business.py`, `_get_current_status_stops()`; `database/procedures/TD_OEE_ObterParadas.sql` | Já existe um caminho de leitura de `Mach_2_Current_Status` e um contrato de retorno. | Confirmar implantação da procedure, cobertura dos dados e correspondência com o histórico Plex. |
| Combinação de histórico antigo e recente | `app/utils/business.py`, `get_stops_with_plex_history()` | Já identifica a fronteira de cobertura TD por centro. | O histórico anterior à fronteira ainda depende do procedimento Plex; precisa de fonte substituta. |
| Disponibilidade e paradas do planejamento | `app/utils/planning_availability.py` | Já consulta `Mach_2_Current_Status` e chama `TD_OEE_CalcularDisponibilidadePorCentro`. | Conferir a definição e implantação da procedure e comparar regras aos indicadores de produção. |
| Agrupamento local para manutenção | `app/utils/maintenance_availability.py` | Já calcula tempos por período e centro usando status locais. | Validar unidades, turnos, cobertura e compatibilidade com os relatórios a migrar. |
| Atualização de parada por HTTP | `app/routes/request/workcentersLogChange.py`, chamada ao Data Source `12272` | Demonstra uma integração Plex sem `EXEC ... AT` para a escrita. | Confirmar APIs equivalentes de leitura e endurecer o contrato HTTP necessário à nova integração. |
| Helper HTTP existente | `app/utils/data_utils.py`, `POST_WITH_AUTH()` | Há uma referência de formato de chamada e resposta. | O helper atual não define timeout explícito, usa `verify=False` e retorna JSON diretamente; não deve ser tratado como cliente completo para sincronização. |

Reaproveitar significa manter contratos e regras úteis, não copiar automaticamente todo o comportamento técnico existente. Um cliente destinado à nova sincronização precisa de timeout, validação TLS, tratamento de status HTTP, erros e paginação conforme o serviço utilizado.

## 7. Primeira entrega: catálogos e `TEMP_WORKCENTER_STATUS`

### 7.1 Dados mínimos necessários

| Conjunto | Colunas observadas | Cuidados |
|---|---|---|
| Centros | `Workcenter_Key`, `Workcenter_Code`, `Name`, `Workcenter_Group`, `Active` | Preservar chaves, tipos e registros necessários ao histórico. Não substituir a chave Plex por um novo identificador sem mapear os consumidores. |
| Motivos/eventos | `Workcenter_Event_Key`, `Description`, `Workcenter_Event_Group`, `Active`, `Code` | Preservar a chave do evento. Há tratamento de códigos duplicados; `Code` não pode ser presumido único. |

O catálogo de centros utiliza `dbo.DJ_WORKCENTERS`, no banco `TRANSFORMACAODIGITAL_JOST`; os motivos atuais utilizam `dbo.DJ_WORKCENTER_EVENTS`. A carga CSV dos motivos não contém a chave Plex do evento e atende somente a classificação atual por descrição/código, sem substituir os contratos históricos que dependem daquela chave.

### 7.2 Proposta inicial, substituída pela leitura direta da seção 7.6

1. Obter uma fonte aprovada para os dois catálogos, com carga inicial completa e regra para atualizações e inativações.
2. Disponibilizar os catálogos localmente e manter uma versão válida publicada de forma consistente.
3. Adaptar o `PlexDataManager` para a nova fonte, mantendo `getPlex()` e os contratos esperados pelos consumidores. A frequência de sincronização deve ser definida separadamente da atualização das paradas.
4. Alterar o S30 para combinar `[JOST_INTEGRATION_PRD].[dbo].[Mach_2_Current_Status]`, indicada como fonte correta pelo responsável, com os catálogos locais. Usar `WcStatus`, `WcReason`, `StatusBegin` e `StatusEnd` conforme o contrato acordado; preservar a consulta FTM, a união das fontes e a classificação de `Responsible`.
5. Preservar `TEMP_WORKCENTER_STATUS`, suas colunas e os valores iniciais utilizados pela consolidação. As telas e o M5 continuam consumindo a mesma tabela.
6. Manter a publicação transacional: uma falha na obtenção ou transformação dos dados não deve publicar uma consolidação parcial ou apagar a última versão válida.
7. Registrar sucesso, duração, quantidade de registros e idade dos dados, sem credenciais ou conteúdo operacional desnecessário. Definir como os consumidores tratarão dados vencidos, sobretudo alertas.

### 7.3 Um cuidado que afeta a facilidade da mudança

**O catálogo usado pelo S30 não é exatamente a mesma projeção entregue hoje por `getPlex()`.** O cache exclui uma lista de centros e remove eventos de código vazio. A consulta S30 aplica seus próprios filtros e lê o catálogo de eventos sem esse mesmo filtro de código.

Por isso, substituir os `OPENQUERY` do S30 diretamente por `getPlex()` pode alterar o resultado. O caminho proposto é manter uma fonte local completa, com projeções e filtros específicos para cada consumidor. Esse detalhe deve entrar na comparação de resultados da primeira entrega.

### 7.4 O que esta entrega resolve e o que permanece

Ela retira a consolidação recorrente e sua dependência do linked server. As consultas próprias de produção, relatórios, taxas/histórico do Quadro Hora e Tela de OEE, `getPlex()` e validação de alterações ainda precisam ser migradas.

O estado atual passa a vir de `Mach_2_Current_Status`, com seleção do registro aberto mais recente antes do filtro de duração das paradas. Isso evita selecionar uma parada antiga quando o centro já está produzindo. Revisão de cobertura, plano e índices é uma atividade separada com o DBA, em ambiente autorizado.

Critérios para considerar a primeira entrega pronta, a verificar futuramente em ambiente autorizado:

- O S30 deixa de executar consultas e os novos consumidores usam os catálogos locais.
- O conjunto de centros, motivos, responsáveis e durações corresponde ao comportamento acordado, incluindo registros sem correspondência.
- Painel Geral, Alerta de Paradas, Quadro Hora, Tela de OEE e M5 continuam recebendo o contrato esperado.
- Falha de importação/sincronização preserva o catálogo anterior; falha de leitura de status retorna indisponibilidade, sem apresentar ausência de dados como ausência de paradas.
- A alimentação das tabelas locais utilizadas foi confirmada como independente do linked server.

### 7.5 Etapa preparada: cadastro moderno e job semanal legado

Esta etapa preparou o armazenamento e a sincronização dos centros. A migração posterior das telas e do M5 está na seção 7.6; `getPlex()` permanece no legado.

| Parte | Implementação preparada |
|---|---|
| Estrutura SQL | `database/migrations/20261106_create_dj_workcenters.sql`, para revisão/aplicação manual no banco solicitado. Não há `create_all()` ou DDL automático. |
| Modelo ORM | `backend/modules/workcenters/models.py`, sobre a `Base` moderna. |
| Leitura Plex | `backend/modules/workcenters/integration.py`: POST HTTPS em `/api/datasources/790/execute`, com `inputs.Active=1`, autenticação MES, certificado validado e timeout. |
| Publicação local | `backend/modules/workcenters/synchronization.py`: uma transação ORM no TD, preservando a última carga válida em caso de erro. |
| Agendamento | Adaptador `app/services/jobs/mon_h_24_workcentersSync.py`, registrado no H24 existente para segunda-feira às 06:10 no fuso do serviço. |
| Ativação | `DJ_WORKCENTERS_SYNC_ENABLED=false` por padrão. Reutiliza `DJ_TD_ODBC_CONNECTION_STRING`, `DJ_MES_USER` e `DJ_MES_PASSWORD` do ambiente privado do serviço; a permissão para o 790 ainda precisa ser validada. |

Campos locais: `id` (identidade local), `plex_workcenter_key` (vínculo interno com Plex), `workcenter_code`, `name`, `workcenter_group`, `created_at` e `last_synced_at`. Os horários são UTC. A chave Plex não ganha uma exibição nova; sua preservação interna facilita consumidores que ainda dependem dela. A sincronização identifica os registros por essa chave, permitindo atualizar código, nome e grupo sem recriar o registro local.

A tabela contém somente os centros ativos retornados pela fonte, incluindo os sem grupo, com exclusão explícita de `LABORAT`, `AUT_01`, `Mach2_Backup`, `Mach2_Backup2` e `SUBCON`. A comparação dos códigos ignora maiúsculas e minúsculas; os DOJO e os demais centros permanecem elegíveis. Essas exclusões são aplicadas na sincronização local depois de validar a resposta completa da API. A próxima carga válida também remove da tabela os registros excluídos que já haviam sido importados, na mesma transação das demais atualizações. Uma carga completa remove os que deixaram de retornar; essa tabela é um catálogo atual, não um histórico. Outros filtros de grupo e exclusões específicas serão responsabilidade dos consumidores. Respostas vazias, duplicadas, inválidas, com limite excedido ou com 1.000 linhas são rejeitadas antes de abrir a transação de escrita; um catálogo vazio após as exclusões também é rejeitado. O payload não é salvo nem registrado em log.

O contrato informado para o Data Source **790 — Workcenters_Get** cobre código, nome, grupo e chave. O **11942 — Workcenter_Events_Get_All** informa somente descrição e chave do evento: não comprova cobertura de `Code`, `Workcenter_Event_Group`, atividade ou regras de responsáveis. Esses dados ainda devem ser mapeados antes de substituir integralmente o catálogo de motivos e os alertas. A tabela local de status pode fornecer a situação e o motivo atuais, mas isso não comprova equivalência com todos os usos do catálogo Plex.

Próximos passos operacionais: revisar/aplicar a migration no ambiente autorizado; validar conta/unidade, resposta real do 790 e primeira carga; habilitar o job no H24; então migrar o S30 e os consumidores. Não há primeira carga automática ao importar ou iniciar o serviço: o próximo horário semanal é a primeira execução após habilitar. Um disparo antecipado depende de execução especificamente autorizada.

O parser espera o contrato de Data Source `tables[0].columns/rows` e `rowLimitExceeded=false`, com linhas posicionais e colunas identificadas por nome; não aceita o `Data.Rows` da tela do navegador. Esse formato precisa de confirmação no teste autorizado. Como referência pública do protocolo, o [exemplo de integração Plex UX da Workday](https://doc.workday.com/adaptive-planning/en-us/workday-adaptive-planning-documentation/integration/managing-data-integration/design-integrations/custom-cloud-data-source-ccds-/ccds-examples/reference--ccds-script-example-plex-ux.html) mostra POST com `inputs`, autenticação Basic, linhas posicionais em `tables[0].rows` e sinalização de limite. Isso não valida o contrato efetivo da conta de produção.

### 7.6 Leitura direta do estado atual e motivos por CSV

As quatro rotas POST de monitoramento e os alertas M5 utilizam a mesma leitura direta. O S30 não agenda mais consultas, e sua antiga entrada foi mantida apenas como operação sem efeito. A atualização automática dos motivos por API fica para uma etapa futura; o cadastro local é carregado pelo CSV original do Plex, somente com `Active=true`.

A leitura em `backend/modules/monitoring/current_status.py` recebe sessões TD e engines Mach2/FTM. Consulta os registros abertos de `Mach_2_Current_Status`, seleciona o mais recente por centro com desempate por ID e combina código, nome e grupo de `DJ_WORKCENTERS`. Os motivos vêm de `DJ_WORKCENTER_EVENTS`. A duração usa o início original e não reinicia após 24 horas. O modo de paradas aplica `CanRunProduction=0` e duração maior que 30 segundos ao Mach2; o estado atual também representa produção. A leitura FTM mantém os filtros anteriores, com precedência Mach2 quando ambos retornam o mesmo centro, inclusive quando o Mach2 indica produção. Há cache de cinco segundos por processo, preenchido sob demanda, sem tarefa periódica, linked server, escrita de status ou thread iniciada no import.

O retorno mantém os campos usados pelas telas, as metas de `PLEX_REGISTER_GOAL` e os indicadores que o S30 preenchia com zero. `Event_Code` é explícito e `Responsible` conserva as exceções anteriores. Falha de fonte, catálogo vazio e motivo ambíguo provocam erro; as rotas retornam 503, sem usar uma cópia vencida. Motivo ausente ou sem código continua visível com a classificação disponível, mas não gera alerta M5 por código; o job registra somente a contagem desses casos. A procedure `TD_OEE_ObterParadas` e os cálculos por período permanecem inalterados.

O importador `backend/modules/workcenters/import_events_csv.py` valida as quatro colunas originais e publica o conjunto ativo em uma transação. Identifica motivos pela descrição: códigos repetidos são permitidos, assim como código vazio. Uma nova importação atualiza os ativos e remove do catálogo os ausentes/inativos; erro reverte a carga. Não há agendamento ou consulta ao Plex nessa importação.

Contratos fornecidos pelo responsável durante a descoberta:

| Data Source | Evidência | Conclusão para os alertas |
|---|---|---|
| 11942 — `Workcenter_Events_Get_All` | Retorna `Description` e `Workcenter_Event_Key`. | Não fornece `Code`. |
| 11390 — `Workcenter_Events_By_Status_Get` | Retorna `Description`, `Equipment_Required`, `PLC_Event_Key` e `Workcenter_Event_Key`. | Não fornece `Code`; `PLC_Event_Key` não foi comprovado como equivalente. |
| 11343 — `Workcenter_Status_Workcenter_Events_Get` | Recebe `Workcenter_Key`; retorna propriedades de status, `Workcenter_Status_Key` e `Events` inteiro entre 25 campos. | Não fornece o código de cada motivo. |

O CSV fornecido cobre `Description`, `Code`, `Workcenter Event Group` e `Active`, resolvendo a carga inicial. As APIs acima não foram escolhidas como substitutas do CSV porque não comprovam o código usado pelos alertas.

Para ativar, seguir a seção 15 e conferir regras, cobertura e desempenho em ambiente autorizado, inclusive centros produzindo, paradas maiores que 24 horas, FTM e falha de fonte. Avaliar índices e concorrência, principalmente a seleção FTM dos últimos 30 dias. Não remover fisicamente `TEMP_WORKCENTER_STATUS` sem conferir consumidores externos. Esta implementação não foi executada ou publicada pelo agente.

## 8. Segunda entrega: taxas padrão e equipe

As consultas atuais usam os relacionamentos entre `Part_v_Part`, `Part_v_Approved_Workcenter`, `Part_v_Workcenter` e, em alguns casos, `Part_v_Part_Operation`.

Precisamos de uma fonte que represente corretamente peça, revisão, centro, operação, situação ativa e os campos `Ideal_Rate`, `Target_Rate` e `Crew_Size`. Não basta manter uma taxa por peça: a relação com centro e operação influencia o resultado.

Essa frente é relativamente favorável porque a informação se repete em três arquivos: `monitoring.py`, `reports/oee.py` e `operation/production.py`. Uma fonte local compartilhada reduz duplicação de chamadas remotas.

As consultas atuais não usam filtros idênticos. Algumas exigem revisão `SAP` e operação ativa; outras utilizam outra combinação. Há também diferenças entre `Ideal_Rate`, `Target_Rate` e a conversão `60 / Ideal_Rate`. A migração deve preservar unidades, agregações, tratamento de zero, ausências e os filtros de cada uso. Qualquer unificação de regra precisa de decisão de negócio própria.

Também é necessário decidir se os relatórios históricos devem usar a taxa vigente no momento da produção ou a taxa atual, pois guardar apenas o cadastro mais recente não garante equivalência histórica.

## 9. Frentes mais difíceis: procedimentos e histórico

### 9.1 Procedimentos remotos a substituir

| Nome chamado pelo código | Uso observado | O que precisamos obter |
|---|---|---|
| `sproc329396_18311230_1268435` | Histórico detalhado de paradas em `getStopsData()`. | Entradas, saída completa, chaves originais, turnos, recortes de período e regras das categorias. |
| `sproc329396_18311230_1264675` | Disponibilidade e tempos dos indicadores de produção e consolidado mensal. | Regras de tempo planejado/produzindo, unidades, filtros e agrupamentos por período, centro e turno. |
| `sproc329396_18311230_1245610` | Conjunto de paradas usado nos indicadores de produção. | Contrato completo e regra de cálculo/classificação efetivamente executada. |
| `sproc329396_18311230_1245623` | Conjunto auxiliar de paradas dos indicadores. | Contrato e diferenças em relação ao conjunto anterior. |

Os papéis acima derivam dos chamadores e nomes das variáveis; as definições dos procedimentos não foram obtidas. Não presumir equivalência com uma API nem efeitos somente de leitura sem conferir os contratos. Os números dos nomes também não podem ser convertidos automaticamente em IDs de Data Sources.

Há duas alternativas: obter chamadas HTTPS equivalentes ou reproduzir os resultados com dados locais e regras conhecidas. A segunda pode aproveitar planejamento/manutenção, mas exige comparação de resultados por centro, turno, período e categoria. A existência de cálculos parecidos não demonstra equivalência.

### 9.2 Cobertura histórica

O caminho TD usa `Mach_2_Current_Status`. O helper `get_stops_with_plex_history()` ainda busca no Plex a parte anterior ao início dessa cobertura por centro. Existe também uma ressalva específica para S18 no código.

Precisamos mapear o início da cobertura, centros ausentes, lacunas, correções posteriores e retenção desejada. Depois, escolher uma fonte para o passado: carga histórica autorizada, API sob demanda ou réplica já existente e comprovadamente completa.

Não podemos apontar tudo para `Mach_2_Current_Status` e presumir que o passado esteja atendido. A migração também precisa evitar sobreposição e dupla contagem entre FTM, histórico Plex e TD.

Os tratamentos existentes incluem chaves de evento, códigos duplicados, normalização de grupos, eventos sem turno, sobreposição de alterações aprovadas e ajustes de horário. `getStopsData()` possui um ajuste de uma hora na consulta remota e no resultado. A interpretação correta de datas e fusos deve ser confirmada antes de substituir a fonte.

## 10. Alteração e aprovação de paradas

O fluxo atual tem quatro partes relevantes:

1. Localiza a parada e usa os catálogos de centros e motivos.
2. Confere o registro original em `Part_v_Workcenter_Log` pelo linked server, incluindo `Log_Key`, `Log_Date`, `Log_Hours` e centro.
3. Quando aprovada, envia a alteração ao Plex pelo Data Source HTTP `12272`.
4. Atualiza os registros locais correspondentes, quando encontrados, e o histórico da solicitação, além das notificações do fluxo.

**A escrita HTTP é o principal exemplo já existente para essa frente.** O trabalho de substituição concentra-se na busca e conferência do original e nos catálogos, sem perder as regras da aprovação.

Precisamos de consulta por `Log_Key` que forneça os mesmos identificadores e período. Para uma decisão de aprovação, deve ser definida a validade aceitável do dado: uma réplica antiga pode servir a um relatório, mas pode não ser suficiente para validar uma alteração concorrente.

Devem ser preservados autorização por ação e registro, duas aprovações quando aplicáveis, chaves reais dos motivos, detecção de correspondência ambígua, rollback e auditoria. Como uma chamada HTTP e uma transação SQL não formam uma única transação atômica, a implementação precisa definir repetição segura, tratamento de resultado desconhecido e recuperação quando apenas uma parte for concluída. Não reenviar gravações automaticamente sem essa regra.

## 11. O que pedir à TI, ao DBA e ao responsável pelo Plex

| Informação ou decisão | Responsável principal sugerido | Destrava |
|---|---|---|
| Fonte aprovada de centros e motivos, com chaves, campos, ativos e inativos | Responsável Plex / integrações | Catálogos e primeira entrega S30. |
| Fonte de peças, operações, taxas e equipe | Responsável Plex / negócio | Monitoramento, sinal e parte da produção. |
| Contratos dos quatro procedimentos remotos e possíveis equivalentes HTTP | Responsável Plex / fornecedor | Histórico, disponibilidade e indicadores. |
| Consulta autorizada de parada por `Log_Key` | Responsável Plex / integrações | Solicitação e aprovação de alterações. |
| Autenticação, escopo da empresa/unidade, permissões e limites de API | TI / responsável Plex | Todas as integrações novas. Valores de credenciais devem permanecer em configuração privada. |
| Volume, paginação, filtros incrementais e tratamento de alterações retroativas | Integrações / DBA | Dimensionamento e sincronização confiável. |
| Cobertura e produtores de `Mach_2_Current_Status`, `Mach_2_Status_Reason_Time`, `Mach_2_OEE_v2` e `Mach_2_OEE_Cavity_Info` | DBA / responsável pela integração atual | Reaproveitamento das bases locais. |
| Definições e implantação das procedures TD utilizadas | DBA | Comparação de disponibilidade e paradas locais. |
| Idade máxima dos dados e comportamento de telas/alertas quando a fonte falha | Operação / responsáveis pelas funcionalidades | Frequência e política de contingência. |
| Armazenamento de catálogos, histórico, índices e retenção | DBA / desenvolvimento | Persistência e desempenho locais. Nenhuma alteração de schema está autorizada por este documento. |
| Inventário externo de dependências do linked server | DBA / TI | Desativação segura da instância. |

O inventário externo deve incluir views, procedures, functions, synonyms, SQL dinâmico, jobs SQL Agent, processos ETL, integrações que alimentam as tabelas locais e consumidores como relatórios, Power BI e SSRS. Eles não podem ser descartados apenas pela busca neste repositório.

## 12. Sequência de implantação e critérios de conclusão

### Etapa A — preparar as fontes

Confirmar contratos e cobertura; definir frequência, retenção e tratamento de falhas. Projetar a persistência necessária e obter autorização específica para banco, execução e ambiente. A sincronização precisa ser centralizada para não multiplicar chamadas por processo IIS, navegador ou scheduler.

### Etapa B — entregar catálogos e S30

Criar/importar o catálogo de motivos e publicar os consumidores diretos conforme a seção 15. O código retira os dois `OPENQUERY` do S30 e dispensa a tabela intermediária. Verificar resultados e desempenho; os consumidores de `getPlex()` continuam em uma etapa posterior.

### Etapa C — migrar monitoramento, sinal e taxas da produção

Substituir as consultas de taxas, equipe e motivos por dados locais. Conferir as telas, chamadas POST e exports, que podem executar consultas independentemente da exibição inicial.

### Etapa D — migrar histórico, procedimentos e aprovações

Substituir as seis chamadas `EXEC ... AT` e as consultas de validação por `Log_Key`. Reconciliar histórico, turnos, duração, categorias, indicadores e alterações aprovadas. Manter as notificações e a consistência entre sistemas.

### Etapa E — encerrar a dependência

Somente após validar em ambiente autorizado:

- Não há chamadas ao linked server no código ativo nem dependência indireta nas fontes locais utilizadas.
- Telas, jobs e exports possuem resultados aceitos pelos responsáveis, incluindo casos sem dados e falha de integração.
- Os sete arquivos foram revisados e o script de diagnóstico foi tratado conforme seu uso.
- O inventário do DBA não aponta consumidores restantes na instância.
- A versão nova está publicada, os serviços estão usando essa versão e o plano de retorno está definido. Restaurar uma versão que ainda dependa do linked server pode exigir sua disponibilidade; esse ponto deve ser resolvido antes da retirada.
- A desativação do linked server foi autorizada e coordenada com o DBA. Remover o DSN ou desinstalar o driver é uma decisão adicional, condicionada à confirmação de que nenhum outro consumidor precisa deles.

Comparações em produção devem ter escopo aprovado: repetir deliberadamente uma consulta associada ao incidente pode reproduzir a falha. Este documento não autoriza executar o sistema, consultas, capturas ou testes. A validação funcional e de desempenho permanece pendente.

## 13. Referências principais e limites do levantamento

| Referência | Finalidade |
|---|---|
| `main.py` | Registro dos blueprints legados envolvidos. |
| `app/utils/db_utils.py` | Engines SQL e funções compartilhadas de consulta. |
| `app/utils/dynamic_constants.py` | Catálogos e interface `getPlex()`. |
| `app/services/jobs/mon_mon_s_30_monitoringOverall.py` | Entrada antiga preservada sem consultas ou escrita. |
| `app/services/run_s_30_scheduler.py` | Serviço preservado sem jobs; desativar após a publicação dos consumidores. |
| `app/services/jobs/mon_mon_m_5_monitoringAlerts.py` | Consumo das paradas para notificações. |
| `app/routes/jdt/monitoring.py` | Telas e consultas do monitoramento. |
| `app/routes/reports/oee.py` | Relatórios de paradas, sinal e Excel. |
| `app/routes/operation/production.py` | Produção mensal, indicadores e Excel. |
| `app/utils/business.py` | Paradas TD, histórico Plex e sobreposição de revisões aprovadas. |
| `app/utils/planning_availability.py` | Disponibilidade e paradas usadas pelo planejamento. |
| `app/utils/maintenance_availability.py` | Cálculos locais por período e centro. |
| `app/routes/request/workcentersLogChange.py` | Solicitação, validação, aprovação e chamada HTTP de atualização. |
| `app/utils/data_utils.py` | Helper HTTP existente. |
| `database/procedures/TD_OEE_ObterParadas.sql` | Definição versionada de uma alternativa local para paradas. |
| `handbook/features/planejamento-operacional.md` | Contexto documentado dos cálculos de planejamento e manutenção. |
| `AGENTS.md` | Restrições operacionais para qualquer implementação futura. |

Não foram acessados SQL Server, Plex, IIS ou serviços corporativos. Não foram obtidos planos de execução, métricas de volume, contratos privados de APIs ou definições completas dos procedimentos remotos. As classificações de facilidade e as alternativas de arquitetura são propostas; os usos descritos são observações estáticas do código consultado.

## 14. Disparo manual único da sincronização de centros

Conforme o [guia do servidor](handbook/docs/servidor-e-publicacao.md#1-ambientes-e-processos), o ambiente informado do H24 usa `C:\python13\pythonservice.exe`, com `C:\python13\python.exe` para chamadas pelo terminal. A pasta informada do projeto é `I:\IIS\Digital_Jost`; a `.venv` do site é um ambiente separado. Esses caminhos foram conferidos na documentação, sem acesso ao servidor.

Após aplicar a tabela e publicar o código, executar no **PowerShell do servidor**, com a mesma configuração privada do H24 e `DJ_WORKCENTERS_SYNC_ENABLED=true`:

```powershell
Set-Location "I:\IIS\Digital_Jost"
& "C:\python13\python.exe" -c "import logging; from app.services.jobs.mon_h_24_workcentersSync import default; logging.basicConfig(level=logging.INFO); default(logging.getLogger('workcenters-manual'))"
```

Se o H24 usa `DJ_ENV_FILE`, disponibilizar o mesmo seletor de arquivo privado nesse PowerShell antes da chamada. Alterar `.env.example` não habilita o job. O comando executa somente a sincronização uma vez: consulta o Plex de produção e publica o catálogo em `dbo.DJ_WORKCENTERS`, sem iniciar o agendador completo. A mensagem de sucesso informa a quantidade de centros e a duração. Se a opção estiver desabilitada, o job retorna sem executar a carga ou emitir essa mensagem.

Para o agendamento semanal reconhecer o código e a configuração novos, reiniciar o H24 em momento autorizado; o reinício não dispara uma carga imediata. O comando acima foi apenas documentado, não executado pelo agente.

**O sistema não foi executado; a validação foi somente estática.**

## 15. Criar/importar os motivos e desativar o S30

Procedimento para o responsável no servidor; comandos apenas documentados.

1. No SSMS, selecionar `TRANSFORMACAODIGITAL_JOST` e executar [20261106_create_dj_workcenter_events.sql](database/migrations/20261106_create_dj_workcenter_events.sql). O script cria somente `dbo.DJ_WORKCENTER_EVENTS`, sem carregar dados. `DJ_WORKCENTERS` também precisa estar criada e carregada.
2. Disponibilizar o módulo importador e o CSV original na pasta do projeto. No PowerShell, com a configuração TD privada correta (`DJ_ENV_FILE`, quando utilizado), executar:

```powershell
Set-Location "I:\IIS\Digital_Jost"
& "C:\python13\python.exe" -m backend.modules.workcenters.import_events_csv --file ".\Workcenter Event (Setup Table)-2026-11-06T164128.csv" --apply
```

O comando valida o arquivo e importa somente os ativos. Sem `--apply`, apenas confere o CSV, sem conexão ao banco. O arquivo fornecido contém 45 motivos ativos. Não inicia Flask, scheduler ou notificações, não acessa o Plex e não cria tabelas. Reutiliza a configuração TD moderna. Código repetido ou vazio não é erro; descrições ativas duplicadas são rejeitadas. Para futuras atualizações manuais, repetir com um novo CSV completo; a tabela passa a representar somente o conjunto ativo dessa exportação.

3. Publicar juntos `backend/modules/workcenters/`, `backend/modules/monitoring/`, `app/routes/jdt/monitoring.py`, `app/services/jobs/mon_mon_m_5_monitoringAlerts.py`, `app/services/jobs/mon_mon_s_30_monitoringOverall.py` e `app/services/run_s_30_scheduler.py`, tanto na cópia do IIS quanto na dos serviços que a utilizam. A carga dos dois catálogos deve preceder a ativação dos novos consumidores. O M5 precisa da configuração TD moderna e de acesso às fontes SQL nativas Mach2/FTM, além das integrações que já utilizava.
4. Reciclar o site e reiniciar o M5 na janela autorizada. Conferir as quatro telas e os alertas, incluindo os casos descritos na seção 7.6. Com os novos consumidores ativos, parar e desabilitar `RunS30Scheduler` no gerenciador de serviços do Windows. Um S30 antigo em memória continua executando o código anterior até ser parado; reiniciar apenas o IIS não o interrompe.

Não excluir a tabela intermediária nesta publicação. Outras consultas de taxas, histórico e `getPlex()` ainda usam o linked server: desativar o serviço S30 não autoriza retirar `PLEX_DSN_JOST`. Para retornar à versão antiga dos consumidores, reativar também o S30 correspondente, pois essa versão depende da consolidação.

**O sistema não foi executado; a validação foi somente estática.** A aplicação do SQL, a importação e a verificação funcional/de desempenho ficam para o ambiente autorizado.
