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
na fonte Mach2. Sem base positiva, exibem “Sem base”, não 0% ou 100%.

As janelas são `[início, fim)`, com fim exclusivo. Os gráficos cobrem quatro
semanas ISO, de segunda-feira a segunda-feira. A tabela mensal cobre do início
do mês da segunda-feira selecionada até o fim da semana, limitado ao fim desse
mês. Ambos param no momento da consulta quando o período ainda está em andamento.
As duas fontes usam os turnos 1, 2 e 3; a chamada da procedure de disponibilidade
aceita também seus aliases `Primeiro`, `Segundo` e `Terceiro`.

## Conferência manual em ambiente autorizado

Não executar o projeto, consultar bancos ou alterar objetos por iniciativa do
agente. A comparação abaixo deve ser feita pelo responsável no ambiente autorizado.

1. Conferir que a conta da aplicação tem EXECUTE nas duas procedures e SELECT
   em `Mach_2_Current_Status`. Não aplicar o script SQL da procedure de paradas
   apenas para instalar esta alteração.
2. No mesmo período, centro e turnos, comparar `PlannedMinutes` do JSON com
   `Disponibilidade_Tempo_Planejado` retornado pela procedure TD.
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
| 0 | 0 | Sem base |
| Sem histórico | 0 | Sem base |
| 600 | 700 | Sem base: inconsistência, sem limitar artificialmente a 0% |

Produção zero, sozinha, não determina disponibilidade de manutenção zero.
Centro sem tempo planejado permanece na tabela. Centros sem associação válida
às quatro áreas no cadastro Plex precisam de conferência do cadastro; esta
mudança não inventa associações nem altera o cadastro.

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
