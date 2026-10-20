> **Registro histórico.** Pode conter decisões, caminhos e comandos superados. Consulte o [manual atual](../../README.md); este arquivo não define o padrão vigente.

# Disponibilidade no Operation Meeting

## Fontes e regra

As telas `/op/plano/area/` usam `TD_OEE_CalcularDisponibilidadePorCentro`
somente para obter minutos planejados e produzidos por centro. A coluna
`Disponibilidade` retornada pela procedure não é usada no indicador de manutenção.

As paradas vêm da `TD_OEE_ObterParadas`, incluindo revisões aprovadas. Como essa
procedure não retorna o indicador de planejamento, o backend consulta
`Mach_2_Current_Status.PlannedProductionTime` pelo mesmo ID do status. Somente
paradas com esse indicador igual a 1 entram nos percentuais e no saldo da meta.
Nenhuma procedure é criada ou alterada pelo código desta mudança.

- Impacto da categoria: `100 × minutos planejados parados na categoria / minutos planejados`.
- Disponibilidade mensal de manutenção: `1 − minutos planejados parados por manutenção / minutos planejados`.
- Saldo da meta: `minutos planejados × meta percentual / 100 − minutos planejados parados na categoria`.
- Geral mensal: soma dos minutos planejados menos manutenção, dividida pela soma dos minutos planejados; não é média simples dos centros.

Os rankings e os botões de total de paradas continuam contabilizando as paradas
totais, inclusive o histórico FTM. O percentual e a tabela mensal não combinam
essas paradas históricas com um denominador TD: dependem do histórico disponível
na fonte Mach2. Sem base positiva, os percentuais exibem “Sem base”, não 0% ou
100%. Na tabela mensal, centros sem tempo planejado positivo ficam ocultos;
continuam no JSON e no diagnóstico. Disponibilidade válida de 0% continua visível.

As janelas são `[início, fim)`, com fim exclusivo. Os gráficos cobrem quatro
semanas ISO, de segunda-feira a segunda-feira. A tabela mensal cobre do início
do mês da segunda-feira selecionada até o fim da semana, limitado ao fim desse
mês. Ambos param no momento da consulta quando o período ainda está em andamento.
As duas fontes usam os turnos 1, 2 e 3; a chamada da procedure de disponibilidade
aceita também seus aliases `Primeiro`, `Segundo` e `Terceiro`.

Exceção restrita ao P04: status com `CurrentShift` vazio, somente espaços ou
`NULL` entram quando `PlannedProductionTime = 1`. A consulta de disponibilidade
captura o resultado da procedure em uma variável de tabela local e complementa
os minutos desses status na mesma chamada ao banco, sem alterar a procedure ou
persistir dados. Não há duplicidade com os turnos 1, 2 e 3. Para as paradas,
o backend solicita também candidatos “A confirmar”, mas mantém somente os IDs
planejados do P04 cujo turno original é realmente vazio ou `NULL`. Outros turnos
desconhecidos, `No Shift` e `Extra` não passam a ser aceitos por essa exceção.
O mesmo critério vale para os gráficos semanais e a disponibilidade mensal,
mantendo as revisões de categoria aprovadas e sem inventar um turno.

## Conferência manual em ambiente autorizado

Não executar o projeto, consultar bancos ou alterar objetos por iniciativa do
agente. A comparação abaixo deve ser feita pelo responsável no ambiente autorizado.

1. Conferir que a conta da aplicação tem EXECUTE nas duas procedures e SELECT
   em `Mach_2_Current_Status`. Não aplicar o script SQL da procedure de paradas
   apenas para instalar esta alteração.
2. No mesmo período, centro e turnos, comparar `PlannedMinutes` do JSON com
   `Disponibilidade_Tempo_Planejado` retornado pela procedure TD.
   Para o P04, somar também os minutos planejados sem turno, recortados na mesma
   janela; não comparar somente com a procedure filtrada por turnos 1, 2 e 3.
3. Comparar as paradas da categoria dentro do período planejado, considerando
   as revisões aprovadas. O total bruto do histórico pode ser maior, por incluir
   paradas fora do planejamento. Não usar `Disponibilidade_Tempo_Parado` geral
   como se fosse apenas manutenção.
4. Conferir as quatro semanas dos gráficos, Movimentação e Material, as demais
   áreas e a tabela mensal. Recarregar os arquivos JavaScript após a implantação.
5. Conferir semana que cruza mês/ano, status iniciado antes da janela e status
   aberto. Para semana 37 de 2026, o período semanal é de 07/09 00:00 até
   14/09 00:00; o mensal até essa semana é de 01/09 00:00 até 14/09 00:00.

Exemplos sintéticos esperados (minutos):

| Planejado | Manutenção no planejado | Disponibilidade de manutenção |
|---:|---:|---:|
| 600 | 0 | 100% |
| 600 | 150 | 75% |
| 600 | 600 | 0% |
| 0 | 0 | Sem base; oculto na tabela |
| Sem histórico | 0 | Sem base; oculto na tabela |
| 600 | 700 | Sem base: inconsistência, sem limitar artificialmente a 0% |

Produção zero, sozinha, não determina disponibilidade de manutenção zero.
Centro sem tempo planejado permanece no diagnóstico, mas fica oculto na tabela.
Inconsistências em centros com base positiva continuam visíveis como “Sem base”.
Centros sem associação válida às quatro áreas no cadastro Plex precisam de
conferência do cadastro; esta
mudança não inventa associações nem altera o cadastro.

Conferir também em ambiente autorizado:

- P04 com turno vazio ou `NULL` e planejamento positivo aparece com a base
  recuperada; sua disponibilidade usa somente a categoria de manutenção, não a
  disponibilidade geral retornada pela procedure.
- P04 com registros em turno conhecido e sem turno soma os dois conjuntos uma
  única vez. Status sem turno que não são planejados continuam fora da exceção.
- E01, E03, L03, L05, M09, R01 e S18 ficam ocultos enquanto não tiverem base
  positiva; se houver base válida em outro período, reaparecem automaticamente.
- C04 com disponibilidade de manutenção de 0% permanece visível.

## Arquivos desta alteração

Backend:

- `app/routes/operation/planning.py`
- `app/utils/business.py`
- `app/utils/planning_availability.py` (novo)

Frontend, todos em `app/static/js/operation.planning/`:

- `chart0.js`
- `chartMotive0.js`
- `chartMotive1.js`
- `chartMotive3.js`
- `chartMotive5.js`
- `getData.js`
- `getDataMaintenance.js`
- `percentageChart.js`
- `slidesController.js`

Documentação: `docs/operation-planning-availability.md` (novo).
Não há alteração em templates, dependências, procedures ou cadastro.

## Relatório detalhado de manutenção

`/manutencao/disponibilidade` passa a compartilhar as fontes, a classificação
das paradas e a fórmula de manutenção do Operation Meeting. O relatório deixa
de consultar a procedure Plex antiga, `OEEQWorkCellDetail` e `CONFIG_TABLET` para
esse indicador. Não há fallback para a base antiga quando falta histórico TD.

O link com `preload=5&year=2026&week=39` seleciona o acumulado mensal usado pela
tabela do OP Meeting: de 01/09/2026 00:00 até 28/09/2026 00:00, exclusivo.
O campo final da tela mostra 27/09/2026 23:59: o último minuto selecionado é
inclusivo e o backend acrescenta um minuto para consultar a janela exclusiva.
Períodos em andamento continuam limitados ao momento da consulta.

Os filtros de centros, áreas e turnos valem tanto para os minutos planejados
quanto para as paradas. A exceção de planejamento sem turno do P04 só entra
quando os três turnos estão selecionados; não é atribuída a um turno específico.
Todos os motivos selecionados incluem a manutenção classificada pela mesma
regra do OP Meeting, inclusive motivos sem código identificável. Uma seleção
parcial de motivos considera somente seus códigos após as revisões aprovadas.

Os agrupadores Dia, Semana ISO, Mês e Ano recortam os status em cada período;
uma parada que cruza a meia-noite não fica inteira no dia em que começou.
O denominador agrupado é obtido em uma única consulta parametrizada à mesma
`Mach_2_Current_Status`, com os mesmos indicadores e filtros da fonte TD,
sem executar uma procedure para cada dia. Os dias incluem o ano no rótulo.
O agrupador Livre e o resumo geral usam a procedure TD compartilhada.

A quantidade de paradas por agrupador conta os status que sobrepõem aquele
período. Um status contínuo pode aparecer em vários dias; o resumo geral conta
esse status apenas uma vez na janela completa. Por isso, somar as quantidades
diárias não equivale necessariamente à quantidade geral. Os tempos são
recortados, não duplicados. MTBF e MTTR sem ocorrências ficam sem valor.

Centros/períodos sem planejamento e sem paradas planejadas ficam ocultos.
Disponibilidade válida de 0% permanece visível. Inconsistências com paradas
planejadas e base ausente ou insuficiente aparecem como “Sem base”, sem
inventar 100%. A exportação usa os filtros da última consulta bem-sucedida,
inclui a situação da base e deixa indicadores indefinidos em branco.

### Conferência após implantação

Somente o responsável, no ambiente autorizado:

1. Abrir o link acima e comparar com a disponibilidade mensal do OP Meeting
   na semana 39, com os quatro grupos, todos os centros, motivos e turnos e o
   agrupador Livre. Conferir o período, cada centro e o geral ponderado.
2. Conferir C04 com 0%, P04 com a base sem turno recuperada e os centros sem
   planejamento ocultos. Selecionar apenas um turno e conferir que a exceção
   sem turno do P04 fica fora, tanto do denominador quanto das paradas.
3. Comparar os agrupadores, uma semana que cruza ano, uma parada que cruza
   dia/mês e um status aberto. Conferir soma dos minutos, não soma das
   quantidades de ocorrências por dia.
4. Conferir filtros parciais de motivos, centros e áreas, consulta sem
   resultados, tratamento de falha e nova pesquisa. Conferir também o Excel,
   inclusive campos sem valor e a coluna de situação da base.

Arquivos desta integração do relatório detalhado:

- `app/utils/maintenance_availability.py` (novo serviço do relatório).
- `app/utils/planning_availability.py` (regras e período compartilhados).
- `app/routes/operation/planning.py` (usa a classificação e o período compartilhados).
- `app/routes/reports/maintenance.py` (consulta e exportação do relatório).
- `app/templates/reports.maintenance/maintenance_availability.html` (filtros e exibição).
- `docs/operation-planning-availability.md` (esta documentação).

Nenhuma procedure, dependência ou objeto persistente do banco foi alterado.
