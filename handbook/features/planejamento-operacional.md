# Planejamento operacional: disponibilidade e manutenção

**Escopo:** regras de disponibilidade do Operation Meeting em `/op/plano/area/` e do relatório `/manutencao/disponibilidade`. São funcionalidades legadas integradas a fontes corporativas; este documento não descreve todo o planejamento operacional. Código e documentação foram comparados estaticamente, sem consulta ao banco.

Revisão em **20/10/2026**, confrontando utilitários, handlers GET/POST, JavaScript/templates e o [registro histórico da disponibilidade](../historico/docs/operation-planning-availability.md). Planos de ação, metas, histórico de responsáveis e anexos do planejamento têm operações próprias fora deste recorte; não foram declarados migrados para Vue/backend moderno.

### Entradas e operações

| URL/método | Uso neste recorte |
|---|---|
| GET `/op/plano` | Página inicial legada. |
| GET `/op/plano/area/<areaId>` | Renderiza slides da categoria; Material (2) redireciona para Movimentação (1). |
| POST da área com `type=graph&year=<ano>&week=<semana>` | Dados dos gráficos de quatro semanas ISO e conjuntos auxiliares. |
| POST `/op/plano/area/3?type=maintenance&year=<ano>&week=<semana>` | Disponibilidade mensal de manutenção. `diagnostic=1` inclui diagnóstico de linhas sem cálculo. |
| GET `/manutencao/disponibilidade` | Formulário do relatório, catálogo de motivos e centros. |
| POST do relatório com `type=dash` | Consulta JSON com os filtros do corpo. |
| POST do relatório com `type=excel` | Gera planilha em memória usando os filtros enviados. |

No handler da área, o ramo diferente de `graph` atende o mensal; no relatório, o ramo diferente de `dash` atende exportação. Os seletores acima são os usados pelo frontend, não uma API REST moderna com schemas Pydantic. As rotas exigem sessão e GENERAL no `before_request`; não usam os guardas/CSRF do módulo moderno. Não inferir uma autorização de edição ou uma revisão completa de segurança a partir dessas leituras.

`areaId` identifica a categoria do slide: 0 Mão de Obra, 1 Movimentação, 2 Material, 3 Manutenção, 4 Método (Qualidade) e 5 Método (Processos). É diferente da área fabril do centro, como Montagem/Usinagem. Ano/semana são validados como semana ISO; IDs de slide arbitrários não possuem o mesmo contrato de validação dos módulos modernos.

## 1. Fontes e critérios

| Fonte | Uso |
|---|---|
| `TD_OEE_CalcularDisponibilidadePorCentro` | Minutos planejados e produzidos por centro; sua coluna de disponibilidade geral não é o indicador de manutenção. |
| `TD_OEE_ObterParadas` | Paradas e revisões de categoria aprovadas. |
| `Mach_2_Current_Status` | Complemento de `PlannedProductionTime` por ID, planejamento sem turno do P04 e base dos agrupamentos do relatório. |

Entram nos percentuais e no saldo somente paradas com `PlannedProductionTime = 1`. Rankings e totais históricos podem incluir outras paradas, inclusive FTM; não combinar esse total com um denominador TD como se fossem a mesma base. Não há fallback para a disponibilidade Plex antiga quando falta histórico TD.

### Cadeia dos dados

```text
Filtros/semana → rotas legadas
    → planning_availability / maintenance_availability
        ├── catálogo getPlex: nomes, códigos, áreas e motivos
        ├── procedure TD: minutos planejados/produzidos
        └── getStopsData / procedure de paradas + revisões aprovadas
              → conferir IDs planejados em Mach_2_Current_Status
    → classificar e recortar → consolidar → JSON/tela ou Excel
```

Os utilitários acessam essas fontes pelo mecanismo legado `engine_run_query`, inclusive engine denominada `plex` para objetos qualificados em `JOST_INTEGRATION_PRD`. O nome “fonte TD” do indicador não significa que ele usa o engine moderno de `backend/platform/database.py`. Cadastro/classificação também depende do cache Plex, mesmo sem usar sua disponibilidade antiga.

`get_planned_availability` parte dos centros das áreas Montagem, Usinagem, Soldagem e Pré-Fabricação, aplica filtros e cruza pelos códigos normalizados. Centro com mais de um nome/área no catálogo gera erro; não escolher arbitrariamente um vínculo. Valores negativos/não finitos da base são tratados como ausência.

`get_planning_stops` usa `getStopsData(use_current_status=True, include_all_statuses=True, ...)`. As paradas TD planejadas são identificadas por ID, `PlannedProductionTime = 1`, `CanRunProduction = 0` e sobreposição com a janela. Linhas históricas FTM não passam a ser planejadas por terem o mesmo motivo.

### Classificação das paradas

`classify_planning_stops` normaliza Manutenção Parada/Produtiva para Manutenção e aplica o mapa de códigos `_STOP_AREAS` para Método (Qualidade/Processos). Quando falta código, tenta inferi-lo pelo catálogo somente se descrição/grupo identificarem um código único; não escolher uma opção ambígua.

O fluxo compartilhado preserva revisões aprovadas de categoria/motivo; em [business.py](../../app/utils/business.py), há consultas a `JDT_REQUEST_STOPCHANGES` e `JDT_REQUEST_STOPCHANGES_PLEX`. Alterações nesse domínio podem mudar os indicadores sem mudar a fonte de minutos. Conferir leitores e escritores dessas revisões em uma tarefa que altere suas regras.

## 2. Fórmulas e ausência de base

- Impacto da categoria: `100 × minutos planejados parados na categoria / minutos planejados`.
- Disponibilidade de manutenção: `1 − minutos planejados parados por manutenção / minutos planejados`.
- Saldo da meta: `minutos planejados × meta percentual / 100 − minutos planejados parados na categoria`.
- Geral mensal: soma dos minutos planejados menos manutenção, dividida pela soma dos minutos planejados. Não é média simples dos percentuais dos centros.

| Planejado | Manutenção no planejado | Exibição |
|---:|---:|---|
| 600 | 0 | 100% |
| 600 | 150 | 75% |
| 600 | 600 | 0%, permanece visível |
| 0 ou sem histórico | 0 | Sem base; oculto na tabela mensal |
| 600 | 700 | Sem base por inconsistência; não limitar artificialmente a 0% |

Produção zero, sozinha, não significa disponibilidade de manutenção zero. Centros sem base continuam no JSON/diagnóstico; inconsistências com base positiva permanecem visíveis como “Sem base”. Cadastros sem associação válida de área exigem conferência, sem inventar vínculos.

### Unidades e indicadores relacionados

| Campo/indicador | Unidade/semântica |
|---|---|
| `PlannedMinutes`, `RunMinutes` | Minutos planejados/produzidos retornados pela fonte e recortados na janela. |
| `Log_Minutes_Sum` | Minutos da parada/categoria no contexto da agregação. |
| `Planned_Log_Minutes` | Parcela planejada utilizada no gráfico semanal. |
| `Log_Minutes_Percentage` / `Percentage` | Percentual de impacto, já na escala de 0 a 100. |
| `CALC` / `overall` mensal | Fração de disponibilidade; 0,75 corresponde a 75%. |
| `TotalAvail`, `TotalRun` | Horas mantidas no JSON por compatibilidade; o Excel converte para minutos. |
| MTTR | Minutos de manutenção planejada / número de ocorrências, com base válida. |
| MTBF | (Minutos planejados − manutenção planejada) / número de ocorrências, com base válida. |

MTBF usa tempo planejado menos manutenção, não `RunMinutes` diretamente. Sem ocorrências, MTBF/MTTR permanecem sem valor. Não converter `null` para zero nem multiplicar por 100 um campo já percentual.

No semanal, inconsistência de paradas planejadas sem base ou acima da base invalida o percentual do grupo/semana; não somar categorias sobre um denominador incoerente. No mensal, o geral ponderado fica indefinido quando há parada sem base válida. Ausência de histórico é serializada como `null`, não NaN/Infinity.

`Availability_Status` distingue Calculado, Sem tempo planejado, Sem histórico na fonte TD e Paradas excedem o tempo planejado. A tolerância numérica é apenas para ponto flutuante, não para absorver diferenças operacionais relevantes. A interface deve manter 0% válido e apresentar “Sem base” quando o cálculo for indefinido.

## 3. Períodos e exceção do P04

Janelas são `[início, fim)`, com fim exclusivo. Gráficos cobrem quatro semanas ISO, de segunda a segunda. O mensal começa no primeiro dia do mês da segunda-feira selecionada e termina no fim da semana, limitado ao fim do mês. Períodos em andamento param no momento da consulta.

As fontes usam turnos 1, 2 e 3; a disponibilidade também aceita os aliases Primeiro, Segundo e Terceiro. A exceção do P04 inclui status planejados com turno original NULL, vazio ou só espaços. Outros turnos desconhecidos, `No Shift` e `Extra` não entram por essa regra.

O complemento do P04 é obtido sem persistir dados ou alterar procedures, sem duplicar turnos conhecidos. Nas paradas, candidatos “A confirmar” ainda são filtrados pelo ID e pelo turno original. A regra vale para os gráficos e para o mensal. No relatório com seleção parcial de turnos, a exceção sem turno só entra quando os três turnos estão selecionados.

As chamadas de disponibilidade usam os aliases `Primeiro,Turno 1,Segundo,Turno 2,Terceiro,Turno 3`; a seleção de turno do relatório é 1/2/3. Não ampliar a exceção do P04 para outros centros ou distribuir minutos sem turno entre os conhecidos sem nova regra de negócio.

O SQL captura o resultado da procedure em variável de tabela e soma o complemento do P04 na mesma chamada. Esse uso de variável/CTE não altera schema persistente. Para os gráficos, cada parada é dividida nos limites semanais antes de somar minutos, inclusive quando começou antes da semana ou cruza ano ISO.

Exemplo de referência: semana 37/2026 cobre 07/09 00:00 até 14/09 00:00 exclusivo; seu acumulado mensal começa em 01/09. Semana ISO usa seu próprio ano: não montar a chave com o ano civil de um dia sem conferir a semana correspondente.

## 4. Relatório de manutenção

`preload=5&year=2026&week=39` seleciona o acumulado mensal da semana: de 01/09/2026 00:00 até 28/09/2026 00:00 exclusivo. A tela pode mostrar o último minuto inclusivo; o backend acrescenta um minuto para consultar a janela exclusiva.

Filtros de centros, áreas e turnos afetam planejado e paradas. Todos os motivos incluem a manutenção classificada pela regra compartilhada, inclusive sem código identificável; uma seleção parcial usa somente os códigos escolhidos após as revisões.

Dia, Semana ISO, Mês e Ano recortam os status por período. Uma parada atravessando meia-noite não fica toda no primeiro dia. A base agrupada vem de uma consulta parametrizada, sem executar uma procedure por dia. Livre e resumo geral usam a fonte TD compartilhada.

A contagem por agrupador considera sobreposição: o mesmo status contínuo pode aparecer em vários dias, mas conta uma vez no resumo da janela. Somar contagens diárias não equivale ao total geral; minutos são recortados. MTBF/MTTR sem ocorrências ficam sem valor.

A exportação usa os filtros da última consulta bem-sucedida, inclui a situação da base e deixa indicadores indefinidos em branco. Centros/períodos sem planejamento e sem paradas planejadas ficam ocultos; 0% válido permanece.

### Corpo da consulta/exportação

| Campo | Valores e validação observada |
|---|---|
| `start_date`, `end_date` | Data/hora local ISO, sem fuso, precisão de minutos. O fim selecionado é inclusivo; a consulta acrescenta um minuto e limita ao agora. |
| `time_group` | `0` Dia, `1` Semana ISO, `2` Mês, `3` Ano, `5` Livre; outros valores são rejeitados. |
| `shift` | Lista não vazia com 1/2/3, como texto ou inteiro; combinações são normalizadas. |
| `w_group` | Lista das quatro áreas aceitas. |
| `w_name_plex` | Chaves de centros resolvidas pelo catálogo Plex. |
| `w_name_mic` | Compatibilidade de filtros antigos; só aceita códigos que existam no catálogo atual. |
| `m_event` | Lista de códigos de motivos; seleção parcial filtra as paradas já revisadas/classificadas. |

Filtros em lista rejeitam objetos, booleanos e estruturas inválidas. Erros de validação tratados pelo caso de uso retornam 400 com `{error: mensagem}`. Esse formato legado difere de `{message, detail}` das APIs modernas. Não importar o cliente moderno sem adaptar o contrato.

As escolhas de centros/áreas delimitam o universo; lista vazia não deve ser presumida como “todos” por um novo consumidor. Quando todos os motivos estão selecionados, a consulta inclui toda manutenção classificada, até sem código identificável; a seleção parcial considera somente os códigos pedidos. O código trata lista de motivos vazia como ausência de filtro de código, ponto que um consumidor deve considerar explicitamente.

### Resultado e exportação

O JSON retorna `workcenters`, `overall` e `period` com início/fim exclusivo efetivos. `workcenters` inclui agrupador, centro/área, minutos, contagem, indicadores e situação da base; `overall` resume a janela inteira. Um centro/período com parada positiva, mas sem base, permanece como inconsistência visível.

Dia/semana/mês/ano usam uma consulta parametrizada com `OPENJSON` para obter a base de todos os períodos, sem uma procedure por dia. Status/paradas são recortados pela sobreposição; contagens diárias podem repetir o mesmo status, mas seus minutos não devem ser duplicados. O resumo geral não é obtido somando contagens sobrepostas de agrupadores.

O Excel é gerado com openpyxl em memória, com abas **Workcenters** e **Resumo Geral**, colunas de minutos, contagens, MTBF/MTTR, disponibilidade e situação. O servidor fornece `relatorio_kpi.xlsx`; o frontend sugere `manutenção.xlsx` ao baixar. Indicadores indefinidos ficam vazios. O gráfico/tabela usa frações convertidas em percentual para exibição.

O template guarda `lastSuccessfulFilters` após consulta válida e os utiliza no download; falha de consulta limpa esse estado para não exportar outro filtro por engano. A exportação faz uma **nova consulta** com esses filtros, não usa um snapshot persistido da resposta anterior: status aberto e revisões podem produzir diferença temporal.

## 5. Onde alterar

| Código | Responsabilidade |
|---|---|
| [planning_availability.py](../../app/utils/planning_availability.py) | Fontes, períodos, classificação, exceção do P04 e consolidações. |
| [maintenance_availability.py](../../app/utils/maintenance_availability.py) | Caso de uso e agrupamentos do relatório. |
| [Rotas de planejamento](../../app/routes/operation/planning.py) | Composição das telas e dos dados do Operation Meeting. |
| [Rotas de manutenção](../../app/routes/reports/maintenance.py) | Consulta e exportação do relatório. |
| [JavaScript do planejamento](../../app/static/js/operation.planning/) | Gráficos, categorias, percentuais, tabela mensal e navegação dos slides. |
| [Template de manutenção](../../app/templates/reports.maintenance/maintenance_availability.html) | Filtros e apresentação do relatório. |

O filtro de metas, permissões de edição e demais operações das rotas têm regras próprias; não inferir autorização de gravação a partir deste indicador de leitura. Ao alterar qualquer uma delas, rastrear todos os métodos, tabelas e jobs correspondentes.

### Responsabilidade por alteração

- Fonte/planejamento/turnos: `get_planned_availability`, `get_planning_stops` e `business.py`; conferir procedure/IDs e o recorte em ambas as telas.
- Fórmula/base válida: `summarize_weekly_availability`, `summarize_monthly_availability` e geral do relatório; conferir unidades e null em gráficos/tabelas/Excel.
- Período/preload: `get_planning_month_range`, handler GET de manutenção e interpretação do último minuto no POST.
- Agrupamento: `_periods`/`_grouped_base` e recorte das paradas no relatório; não usar somente a data inicial da ocorrência.
- Interface OP: `getData.js`, `getDataMaintenance.js`, `chart0.js`, `chartMotive*.js`, `percentageChart.js` e `slidesController.js`.
- Interface do relatório: template Jinja com JavaScript inline; possui filtros, cache da consulta, gráficos e download. Não movê-lo para static sem adaptar os valores Jinja.

No OP, falha de nova consulta mensal limpa o indicador anterior e mostra indisponibilidade. Não apresentar percentual antigo como se fosse resultado do novo filtro. No relatório, conferir o estado de falha/últimos filtros e o botão de exportação.

## 6. Publicação e conferência

Seguir [Servidor e publicação](../docs/servidor-e-publicacao.md). Estas regras não pedem recriação de procedures, mudanças em cadastro ou dependências. A conta da aplicação precisa das permissões corporativas de leitura/execução necessárias; qualquer concessão é uma ação específica do responsável.

No ambiente autorizado, comparar centro/período/turnos iguais entre fontes, JSON e tela; conferir quatro semanas ISO e mês cruzando ano; status aberto ou anterior à janela; P04 sem turno sem duplicidade; turno parcial excluindo a exceção; centro sem base oculto e 0% válido visível; revisões de motivos, geral ponderado, agrupamentos e exportação.

### Comparação dirigida

1. Confirmar EXECUTE nas duas procedures, SELECT em `Mach_2_Current_Status` e leitura dos cadastros/revisões necessários. Não aplicar um SQL de recriação de procedure como requisito presumido.
2. Fixar centro, período, turnos e motivos iguais. Comparar `PlannedMinutes` com o tempo planejado da procedure e, no P04, acrescentar apenas seu complemento sem turno.
3. Comparar IDs/minutos de paradas planejadas e sua categoria revisada, não o total bruto histórico nem a coluna geral `Disponibilidade`.
4. Conferir os exemplos 100%/75%/0%/Sem base, inclusive inconsistência com base positiva e centro sem planejamento oculto.
5. Conferir P04 misturando turnos conhecidos/sem turno, outro centro sem turno, `No Shift`/`Extra` e seleção parcial de turnos.
6. Conferir status iniciado antes da janela, aberto, cruzando dia/mês/ano e ano ISO; comparar soma de minutos sem somar contagens sobrepostas como total geral.
7. Conferir seleção parcial de motivo revisado, agrupadores, geral ponderado, null no JSON e células vazias no Excel.
8. Repetir a conferência de leitura após publicar scripts/template e atualizar cache do navegador, sem disparar gravações do planejamento ou jobs.

O período mensal de exemplo, com semana 39/2026, termina em 28/09 00:00 exclusivo e aparece no formulário como 27/09 23:59. Essa equivalência precisa permanecer ao comparar OP e relatório. Dados reais, permissões, desempenho e resultados das procedures não foram observados nesta revisão.

Comparar minutos e classificação, não soma de contagens diárias nem disponibilidade geral da procedure. Conferir falhas de consulta e atualização do JavaScript publicado. **O sistema não foi executado; a validação foi somente estática.**
