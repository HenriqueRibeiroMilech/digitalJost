# Base fictícia — OEE e paradas do piloto Digital JOST

Versão da base simulada: 1. Data de preparação: 04/11/2026.

Todos os valores, equipamentos e registros deste documento são fictícios, criados manualmente para testar um agente. Não representam a produção da Randon ou da JOST e não foram extraídos de sistemas corporativos.

## Cobertura dos dados

- Uma máquina fictícia: **SIM-01**.
- Uma linha fictícia: **Linha Simulada A**.
- Dois recortes: **primeiro turno de 02/11/2026** e **primeiro turno de 03/11/2026**.
- Não há registros de outros dias, turnos, equipamentos, operadores ou ordens.
- Os registros não são dados em tempo real nem histórico completo da fábrica.
- Ausência de um recorte significa informação indisponível, e não valor zero.

## Definições usadas somente neste exemplo

OEE = disponibilidade × performance × qualidade, usando os fatores como frações.

Disponibilidade = minutos em operação / minutos planejados para produção.

Os minutos parados são a diferença entre tempo planejado e tempo em operação. Neste conjunto simulado, todas as paradas listadas ficam dentro da janela planejada, não se sobrepõem e reduzem a disponibilidade.

Performance e qualidade já são fornecidas como fatores calculados para o piloto. Não há contagens de peças ou tempos de ciclo para recalculá-las. Essas definições não estabelecem as regras reais do Digital JOST.

## Registro R01 — SIM-01, primeiro turno, 02/11/2026

- Linha: Linha Simulada A.
- Tempo planejado para produção: **480 minutos**.
- Tempo em operação: **360 minutos**.
- Tempo parado: **120 minutos**.
- Disponibilidade calculada: **75,00%**.
- Performance informada: **80,00%**.
- Qualidade informada: **95,00%**.
- OEE calculado: **57,00%**.
- Memória do cálculo: 0,75 × 0,80 × 0,95 = 0,57.

Categorias de parada e seus totais no recorte:

| Categoria registrada | Minutos |
| --- | ---: |
| Falha de equipamento | 60 |
| Setup | 40 |
| Falta de material | 20 |
| Total | 120 |

## Registro R02 — SIM-01, primeiro turno, 03/11/2026

- Linha: Linha Simulada A.
- Tempo planejado para produção: **480 minutos**.
- Tempo em operação: **408 minutos**.
- Tempo parado: **72 minutos**.
- Disponibilidade calculada: **85,00%**.
- Performance informada: **90,00%**.
- Qualidade informada: **100,00%**.
- OEE calculado: **76,50%**.
- Memória do cálculo: 0,85 × 0,90 × 1,00 = 0,765.

Categorias de parada e seus totais no recorte:

| Categoria registrada | Minutos |
| --- | ---: |
| Falha de equipamento | 30 |
| Setup | 24 |
| Falta de material | 18 |
| Total | 72 |

## Comparativo calculado entre R01 e R02

Recorte da comparação: mesma máquina SIM-01 e mesmo primeiro turno, de 02 para 03/11/2026.

| Indicador | 02/11/2026 | 03/11/2026 | Diferença |
| --- | ---: | ---: | --- |
| OEE | 57,00% | 76,50% | Aumento de 19,50 pontos percentuais |
| Disponibilidade | 75,00% | 85,00% | Aumento de 10,00 pontos percentuais |
| Performance | 80,00% | 90,00% | Aumento de 10,00 pontos percentuais |
| Qualidade | 95,00% | 100,00% | Aumento de 5,00 pontos percentuais |
| Tempo parado | 120 min | 72 min | Redução de 48 min, equivalente a 40,00% |

A redução relativa do tempo parado é (120 − 72) / 120 = 40,00%. A diferença de OEE é 76,50 − 57,00 = 19,50 pontos percentuais; esse número não é uma variação relativa de 19,50%.

## Totais de paradas nos dois recortes

| Categoria registrada | Soma dos minutos |
| --- | ---: |
| Falha de equipamento | 90 |
| Setup | 64 |
| Falta de material | 38 |
| Total | 192 |

Falha de equipamento é a categoria com maior soma de minutos nos dois recortes disponíveis. Essa categoria não descreve uma causa raiz técnica.

## Informações que não estão disponíveis

Não há diagnóstico de causa raiz, histórico de manutenção, intervenções realizadas, custos, metas, peças produzidas, refugos em unidades ou dados de outros recortes. Não é possível afirmar que uma intervenção de manutenção causou a melhora do OEE.

Não foi calculado OEE consolidado para os dois recortes. Não usar a média simples dos percentuais de OEE como se fosse um indicador consolidado oficial.

Este arquivo contém somente dados de referência para consulta. Não representa uma conexão ao Digital JOST nem permite alterações de dados operacionais.
