# Requisitos da nova tela de gestão de demandas

## Objetivo

Reformular o painel de gestão de demandas na arquitetura moderna do Digital JOST, seguindo o padrão visual de `/app/eventos` e mantendo uma organização semelhante à do gerenciador atual.

O desenvolvimento será retomado com calma, a partir destes requisitos.

## Escopo dos dados

- Começar somente com os registros das tabelas novas.
- Manter o sistema antigo e suas tabelas separados durante a transição.
- Não incluir os registros antigos nesta primeira etapa.
- Atividades devem utilizar a mesma tabela principal e o mesmo sistema de gerenciamento dos demais tipos de demanda.
- Não incluir atividades recorrentes no novo gerenciador.

## Organização do painel

O painel terá duas abas principais:

1. **Demandas:** acompanhamento e gerenciamento do trabalho da equipe.
2. **Solicitações:** análise das solicitações abertas.

Não haverá aba de gráficos nesta etapa.

## Aba Solicitações

Exibir as solicitações abertas em cards, com as seguintes opções de análise:

### Aceitar

- Selecionar o responsável.
- Classificar a solicitação de demanda como **Melhoria** ou **Projeto**, por enquanto.
- Encaminhar a solicitação aceita para o gerenciamento de demandas.

### Recusar

- Exigir uma justificativa para a recusa.

### Solicitar mais informações ou reunião

- Disponibilizar a opção de pedir informações complementares.
- Disponibilizar a opção de solicitar que a pessoa marque uma reunião.
- Ter um campo para descrever quais informações são necessárias ou o que precisa ser alinhado na reunião.
- Enviar um e-mail ao solicitante com o pedido.
- Mostrar esse pedido também em **Minhas solicitações**, para que a pessoa consiga acompanhá-lo.

## Aba Demandas

Manter a separação das demandas por usuários/responsáveis, semelhante à existente no gerenciador atual.

### Nova demanda ou aviso

Substituir os cadastros separados de atividade e aviso por uma única ação: **Nova demanda ou aviso**.

A primeira informação solicitada será o tipo:

- Projeto.
- Melhoria.
- Erro.
- Atividade.
- Aviso.

Somente depois da escolha do tipo serão exibidos os campos correspondentes.

| Tipo | Formulário esperado |
|---|---|
| Projeto | Campos correspondentes à solicitação normal de demanda. |
| Melhoria | Campos correspondentes à solicitação normal de demanda. |
| Erro | Campos correspondentes ao relato de erro. |
| Atividade | Mesmos campos do cadastro atual de atividade, sem recorrência. |
| Aviso | Mesmos campos do cadastro atual de aviso. |

## Cards e detalhes das demandas

Os cards devem manter as informações que já apresentam hoje, mas sem campos de preenchimento ou edição na parte externa.

Toda alteração deve acontecer dentro do detalhe aberto a partir do card.

O detalhe terá três abas:

1. **Informações da demanda e gerenciamento:** dados da demanda, campos de gestão, anexos, botões e ações.
2. **Tarefas:** tarefas vinculadas à demanda.
3. **Histórico:** histórico da demanda.

### Demandas com início agendado

Quando uma demanda estiver agendada para iniciar, seu card deverá mostrar:

- A data de início agendada.
- O prazo da demanda.
- Uma tag com o texto **Demanda agendada**.

## Botões e ações de andamento

Separar as ações principais do fluxo das opções disponíveis em **Outras ações**.

| Situação | Ações principais | Outras ações |
|---|---|---|
| Demanda ainda não iniciada | Iniciar; cancelar. | Agendar início; solicitar mais informações. |
| Demanda iniciada | Concluir; cancelar. | Solicitar mais informações; iniciar validação; pausar; aguardando terceiros. |

Os novos estados e suas ações precisam ser considerados na reformulação dos status do gerenciador.

### Alteração de prazo

- Manter a alteração de prazo em uma ação própria, como acontece atualmente.
- Exigir uma justificativa para alterar o prazo.
- Não permitir alterar o prazo pelos botões de andamento nem pelas opções de **Outras ações**.

## Filtro de período de conclusão

Adicionar dois campos de data:

- **Data inicial.**
- **Data final**, preenchida inicialmente com a data de hoje.

O objetivo é mostrar as demandas ativas junto das demandas concluídas no período selecionado.

### Comportamento esperado

- Manter as demandas ativas no resultado, sem limitar sua data de abertura pelo período de conclusão.
- Acrescentar as demandas concluídas entre a data inicial e a data final, incluindo os dois dias.
- Usar a data de conclusão para selecionar as demandas concluídas.

**Exemplo:** ao selecionar o período do dia 17 ao dia 23, exibir as demandas ativas e as demandas concluídas entre os dias 17 e 23.

## Formulário de solicitação do usuário

Preservar a distinção entre o tipo de entrada escolhido pelo solicitante e a classificação feita pela gestão:

- Na solicitação do usuário, o seletor oferece somente **Solicitar demanda** e **Reportar erro**.
- A classificação em **Melhoria** ou **Projeto** acontece na gestão, ao aceitar a solicitação e definir o responsável.
- O cadastro interno **Nova demanda ou aviso** permite os cinco tipos listados neste documento.
