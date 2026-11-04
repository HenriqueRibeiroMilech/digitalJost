# Passo a passo — Copilot Studio conectado ao banco

Objetivo: consultar OEE atual e paradas reais pelo painel de teste. Sem incorporar o chat ao Digital JOST nesta etapa. Os nomes dos menus podem variar entre versões.

## 1. Tenha estes acessos

Você já consegue criar agentes. Para conectar ao banco, precisa também de:

- Nome do servidor/instância e do banco, fornecidos pela TI.
- Conexão com permissão somente de leitura nos dados autorizados.
- Gateway corporativo compartilhado, caso o SQL Server esteja na rede interna.
- Conector SQL Server Premium e fluxos liberados no ambiente.

Se faltar gateway ou conexão, peça à TI: **“Preciso de uma conexão SQL Server de leitura e acesso ao gateway corporativo no ambiente do Copilot Studio para consultar OEE e paradas.”** Não coloque credenciais no chat.

## 2. Abra o agente

1. Acesse [Copilot Studio](https://copilotstudio.microsoft.com/).
2. Selecione o ambiente da empresa liberado para o piloto.
3. Clique em **Agentes → Criar agente**.
4. Nome: **Digital JOST — OEE e paradas**.
5. Idioma: **Português (Brasil)**.
6. Finalize a criação.

## 3. Crie a ferramenta de OEE

1. Abra **Ferramentas / Tools → Adicionar ferramenta / Add tool**.
2. Em criar nova, escolha **Fluxo de agente / Agent flow**.
3. Nomeie o fluxo **consultar_oee_atual**.
4. Mantenha o gatilho **Quando um agente chama o fluxo** e a ação **Responder ao agente**.
5. Entre eles, clique em **+ → Adicionar ação**.
6. Pesquise **SQL Server** e escolha **Obter linhas (V2) / Get rows (V2)**.
7. Selecione a conexão autorizada. Se precisar criá-la, preencha servidor, banco, autenticação e gateway com as informações da TI.
8. Renomeie a ação para **Consultar_OEE**, para usar as expressões abaixo.

## 4. Configure a consulta

O monitoramento do projeto usa `TEMP_WORKCENTER_STATUS`; confirme com o DBA o catálogo, schema e acesso a esse objeto ou à projeção autorizada equivalente.

Preencha a ação:

| Campo | Valor |
| --- | --- |
| Servidor | Servidor autorizado |
| Banco | Banco confirmado pela TI |
| Tabela | `TEMP_WORKCENTER_STATUS` ou projeção autorizada equivalente |
| Filter Query | `Workcenter_Code eq '<CENTRO>'` |
| Top Count | `2` |
| Select Query | `Workcenter_Code,Performance,Availability,Quality,Log_Date` |

Substitua `<CENTRO>` por um código real autorizado. Neste primeiro teste, deixe-o fixo no fluxo; não use texto livre da pergunta para montar o filtro.

## 5. Trate o retorno e calcule o OEE

1. Depois de **Consultar_OEE**, adicione **Controle → Condição**.
2. No primeiro campo da condição, abra **Expressão** e cole:

```text
length(body('Consultar_OEE')?['value'])
```

3. Configure **é igual a → 1**.
4. No ramo **Não**, adicione **Responder ao agente**, com duas saídas de texto: `resultado` com **Erro: a consulta não retornou exatamente um registro para o centro configurado**, e `consultado_em_utc` com a expressão `utcNow()`.
5. No ramo **Sim**, adicione **Operações de dados → Compor / Compose** e renomeie para **Registro**.
6. No campo de entrada de **Registro**, use a expressão:

```text
first(body('Consultar_OEE')?['value'])
```

7. Ainda no ramo **Sim**, adicione outro **Compor**, nome **OEE**, com:

```text
div(mul(mul(float(outputs('Registro')?['Performance']), float(outputs('Registro')?['Availability'])), float(outputs('Registro')?['Quality'])), 10000.0)
```

Essa é a fórmula encontrada no monitoramento: os três fatores estão em percentual. Se um fator vier ausente ou inválido, investigue o retorno; não substitua por zero.

8. Mova a ação original **Responder ao agente** para o final do ramo **Sim**. Adicione as saídas:

| Nome | Tipo | Valor pela aba Expressão |
| --- | --- | --- |
| `resultado` | Texto | `string(setProperty(outputs('Registro'), 'OEE', outputs('OEE')))` |
| `consultado_em_utc` | Texto | `utcNow()` |

Use os mesmos nomes e tipos de saída nos dois ramos. No sucesso, `resultado` contém o registro em JSON, incluindo o OEE calculado.

9. Nas configurações de **Responder ao agente**, deixe **Resposta assíncrona** desativada.
10. Salve/publique o fluxo e adicione-o às ferramentas do agente. Publicar o fluxo é diferente de publicar o agente em um canal. Se o plano bloquear essa operação, a TI precisa liberar o recurso.

O fluxo deve ficar assim:

```text
Quando um agente chama o fluxo
  → Consultar_OEE
  → Condição: retornou exatamente uma linha?
      Sim → Registro → OEE → Responder com dados
      Não → Responder com erro
```

## 6. Configure o agente

Na ferramenta **consultar_oee_atual**, use a descrição:

```text
Consulta o OEE atual e seus fatores para o centro configurado no piloto.
Use para perguntas sobre o estado atual. Não fornece OEE histórico.
```

Em **Visão geral → Instruções**, cole:

```text
Responda em português.
Para OEE atual, sempre chame consultar_oee_atual.
Informe o centro retornado, OEE, disponibilidade, performance e qualidade.
Use os valores retornados; não recalcule os indicadores.
Informe o instante da consulta. Log_Date é referência do evento da fonte,
não garantia de atualização de todos os indicadores.
Não invente dados. Se a ferramenta falhar, informe o erro.
Explique que a ferramenta de OEE atual não oferece histórico por período.
Não execute alterações e não solicite credenciais no chat.
```

Se anexou a base fictícia anteriormente, remova-a das fontes desse agente. Desative pesquisa web para estas consultas.

## 7. Faça a primeira pergunta

1. Abra **Testar seu agente / Test your agent**.
2. Inicie uma nova conversa.
3. Pergunte: **“Consulte o OEE atual do centro configurado no piloto.”**
4. Confira no painel de atividade se **consultar_oee_atual** executou.
5. Compare os fatores e o OEE com o monitoramento do mesmo centro, em um instante próximo.

Se respondeu sem executar a ferramenta, o teste não passou. Se ela executou com erro, abra a execução do fluxo e confira a ação que falhou.

## 8. Adicione paradas

1. Confirme com o DBA a existência, versão e permissão de execução somente de leitura de **TD_OEE_ObterParadas**. O script do repositório não confirma a implantação.
2. Crie outro fluxo, nome **consultar_paradas_td**, pelo mesmo caminho da etapa 3.
3. No gatilho, adicione duas entradas de texto: **inicio** e **fim**.
4. Adicione a ação **SQL Server → Executar procedimento armazenado (V2) / Execute stored procedure (V2)**, com servidor, banco e procedure fixos.
5. Renomeie a ação para **Consultar_Paradas**.
6. Mapeie os parâmetros:

| Parâmetro SQL | Valor |
| --- | --- |
| `data_inicio` | Entrada `inicio` |
| `data_fim` | Entrada `fim` |
| `workcenter_list` | Código real autorizado, fixo no fluxo |
| `shift_list` | `Turno 1`, fixo para a primeira consulta |

7. Antes da ação SQL, valide as datas e limite a janela inicial a um dia, com início menor que fim. Combine com o DBA a interpretação do horário local; não acrescente `Z` a horários locais sem conversão.
8. Em **Responder ao agente**, crie a saída de texto **resultado** com a expressão:

```text
string(body('Consultar_Paradas'))
```

9. Salve/publique o fluxo e adicione-o ao agente.
10. Na descrição da ferramenta, informe: **Consulta paradas TD de um centro fixo e do Turno 1. Requer início e fim explícitos; use para listar as paradas desse recorte.**
11. Acrescente às instruções do agente:

```text
Para listar paradas TD, use consultar_paradas_td.
Peça início e fim se faltarem. Informe o centro e o turno fixos do piloto.
Apresente motivo, início, fim e minutos retornados. Não invente valores.
Não apresente essa consulta como relatório consolidado de todo o histórico.
```

12. Teste: **“Liste as paradas TD do centro configurado, no Turno 1, de [data e hora inicial] até [data e hora final].”** Preencha um intervalo real autorizado, de até um dia.

Essa procedure retorna o recorte TD. O relatório completo aplica tratamentos adicionais no backend, inclusive revisões e histórico. Para coincidir com ele, precisaremos incorporar esses tratamentos. Rankings e totais devem ser calculados no fluxo/SQL sobre o conjunto completo; esta primeira ferramenta apenas lista os registros retornados.

## 9. Se travar

| Problema | Ação |
| --- | --- |
| SQL Server bloqueado/Premium | Solicitar liberação de conector e capacidade à TI. |
| Gateway não aparece | Solicitar compartilhamento/configuração do gateway corporativo. |
| Tabela/procedure não aparece | Confirmar catálogo, schema, implantação e permissões com o DBA. |
| Consulta retorna zero ou várias linhas de OEE | Conferir o centro e o objeto; não escolher uma linha arbitrária. |
| OEE falha em `float` | Conferir valores ausentes e tipos dos fatores na saída SQL. |
| Fluxo não aparece como ferramenta | Conferir ambiente, publicação do fluxo e licença. |
| Erro em consulta SQL livre via gateway | Usar as ações deste guia; `Execute a SQL query (V2)` não suporta SQL Server local via gateway. |

Use inicialmente só sua conta e o escopo de leitura aprovado. Uma conexão do autor não herda as permissões individuais do Digital JOST.

## Referências

- [Criar fluxo como ferramenta — Microsoft](https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-flow-create).
- [Conector SQL Server e limitações — Microsoft](https://learn.microsoft.com/en-us/connectors/sql/).

Arquivo simplificado, sem commit. Nenhuma conexão ou ferramenta foi criada pelo assistente; os passos ainda precisam ser executados no ambiente autorizado.

O sistema não foi executado; a validação foi somente estática.
