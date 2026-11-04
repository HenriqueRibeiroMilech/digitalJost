# Diagnóstico e correção do desvio 2026-0081

## Evidência informada pelo responsável

Na rota `/desvios/detalhes?id=2026-0081`, os resultados fornecidos mostram:

| Revisão | Status geral | Aprovações setoriais |
|---|---|---|
| 00 | Finalizado (`4`) | 11 de 11 aprovadas |
| 01 | Atrasado (`6`) | 11 de 11 aprovadas |
| 02 | Recusado (`2`) | 11 de 11 aprovadas |

Todos os registros setoriais informados estão sem justificativa de recusa. Os status da view `JDT_VIEW_REQUEST_DEV_DETAILS` coincidem com os da tabela `JDT_REQUEST_DEV`.

Esses resultados confirmam a inconsistência entre o status geral da revisão 02 e suas aprovações. O agente não executou consultas nem acessou logs ou serviços corporativos.

## Causa identificada no código

O fluxo em [processDeviation.py](../app/routes/request/processDeviation.py) mantinha a nova revisão aguardando (`0`) quando a anterior ainda estava ativa (`5` ou `6`), mesmo após todas as aprovações.

O job [mon_fri_h_24_processDeviationCheck.py](../app/services/jobs/mon_fri_h_24_processDeviationCheck.py) recusava registros em status `0` após 48 horas úteis desde a abertura, sem conferir as aprovações. Isso permitia recusar uma revisão que apenas aguardava liberação, preservando todos os setores aprovados.

O comportamento é compatível com os resultados fornecidos. Para confirmar o evento histórico, ainda é necessário localizar no log H24:

```text
Desvio 2026-0081-2 recusado automaticamente após 48h úteis.
```

O cálculo existente conta as horas de segunda a sexta, inclusive fora do expediente, e não considera feriados. Essa regra de prazo foi preservada.

## Correção preparada

- A aprovação exige ao menos um registro setorial e todos eles em status `1`; `MIN(status) = 1` foi substituído, pois também aceitava uma mistura de aprovados e recusados.
- Quando uma revisão recusada é totalmente aprovada pelo fluxo de aprovação, ela retorna para espera (`0`). A função comum de liberação decide se pode entrar em andamento (`5`). As datas permanecem preservadas durante a espera.
- Aprovação, abertura dos detalhes e finalização da revisão ativa usam a mesma regra de liberação: não pode existir outra revisão da mesma base em status `5` ou `6`.
- A liberação revalida as aprovações e a ausência de outra revisão ativa no próprio `UPDATE`, e só informa sucesso quando uma linha foi alterada.
- O job seleciona para recusa somente registros com algum setor não aprovado. O `UPDATE` também confere essa condição para proteger contra uma seleção desatualizada. Registros sem setores não são recusados automaticamente por essa regra.
- A tela de detalhes mostra “Aprovado; aguardando liberação” para revisões em status `0` com todos os setores aprovados, por revisão.
- Registros antigos já recusados não são recuperados automaticamente ao abrir a tela.

As alterações estão preparadas no código local. Sua publicação e seu funcionamento no ambiente não foram verificados.

## Recuperação pontual da revisão 02

O arquivo [recuperar_desvio_2026_0081.sql](../database/recuperar_desvio_2026_0081.sql) está preparado para revisão e aplicação manual no SQL Server correspondente à conexão `jdt`. Não foi executado pelo agente.

Com `@Aplicar = 0`, o script apenas apresenta os status e as contagens atuais. Um responsável autorizado pode mudar para `1` após publicar a correção da aplicação e do job H24 e conferir o diagnóstico.

A gravação exige três revisões na base, a revisão 01 ainda ativa (`5`/`6`), a revisão 02 recusada (`2`) e exatamente 11 registros setoriais aprovados, todos sem justificativa de recusa. O script usa transação e travas de atualização; se o estado tiver mudado, interrompe e desfaz a operação. Não deve ser aplicado dentro de outra transação.

O único ajuste é `2026-0081-2: status 2 → 0`, preservando aprovações e datas. A revisão 01 continua atrasada. Após sua finalização pelo fluxo normal, a revisão 02 poderá ser liberada pela aplicação. O script não envia notificações nem chama endpoints.

## Conferência estática e validação pendente

O patch deve manter os seguintes comportamentos, cuja execução depende de ambiente autorizado:

| Cenário | Resultado esperado |
|---|---|
| Todos aprovados e outra revisão ativa | Espera em `0`, sem recusa por prazo |
| Todos aprovados e nenhuma revisão ativa | Liberação para `5` |
| Setores com status `1` e `2` | Sem liberação |
| Setor pendente ou nulo após 48 horas úteis | Recusa por prazo conforme a regra do job |
| Nenhum registro setorial | Sem liberação nem recusa automática por essa regra |
| Seleção do job seguida da aprovação do último setor | O `UPDATE` deve preservar a revisão totalmente aprovada |
| Revisão recusada que recebe a última aprovação | Retorno para espera ou liberação, conforme outra revisão ativa |
| Finalização da revisão ativa com próxima já aprovada | Liberação da próxima revisão em espera |
| Registro cancelado ou finalizado | Não recuperado pelo novo fluxo de liberação |

Foram usados somente revisão textual, busca de referências e inspeção de diff. Permanecem pendentes a validação funcional, os cenários concorrentes e a recuperação no banco em ambiente autorizado.

**O sistema não foi executado; a validação foi somente estática.**
