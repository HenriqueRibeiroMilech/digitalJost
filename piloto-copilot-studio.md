# Piloto com dados reais no Copilot Studio

Roteiro atualizado em 04/11/2026. Você já consegue acessar o Copilot Studio e criar agentes. O objetivo agora é consultar o banco corporativo pelo chat de teste do Studio. A versão futura usará Microsoft Foundry; a interface dentro do Digital JOST ficará para depois.

Este roteiro substitui a proposta inicial com arquivos fictícios. O arquivo de dados fictícios foi preservado, mas não será fonte deste piloto.

## 1. Arquitetura do piloto

Para começar pelo banco, a proposta é usar ferramentas de consulta com filtros e cálculos definidos:

```text
Você pergunta no painel do Copilot Studio
                  ↓
Agente escolhe a ferramenta e seus parâmetros
                  ↓
Fluxo valida filtros e chama o conector SQL Server
                  ↓
Gateway corporativo, se o banco estiver na rede interna
                  ↓
Objetos SQL autorizados para consulta
                  ↓
Resultado estruturado → agente explica a resposta
```

O agente não recebe usuário/senha do banco nem produz SQL livre para executar. Ele chama operações como `consultar_oee_atual` e `consultar_paradas`.

O conector SQL Server é Premium e tem suporte a gateway. Para SQL Server local, **Execute a SQL query (V2) não é suportado via gateway**. O caminho deste guia usa **Get rows (V2)** para uma leitura delimitada e **Execute stored procedure (V2)** para uma operação aprovada. [Conector SQL Server — Microsoft](https://learn.microsoft.com/en-us/connectors/sql/).

Uma alternativa com mais reaproveitamento no Foundry é disponibilizar essas operações em uma API interna. Nesse caso, o fluxo chama a API por um conector personalizado, e a API consulta o banco. Essa API ainda precisa ser implementada e receber autenticação própria; as rotas de tela existentes não devem ser presumidas como prontas para isso. [Conectores personalizados — Microsoft](https://learn.microsoft.com/connectors/custom-connectors).

## 2. O que falta confirmar com a TI

Antes de criar a conexão, solicite estes dados e liberações no canal corporativo:

| Item | O que confirmar |
| --- | --- |
| Ambiente | Qual ambiente do Copilot Studio será usado no piloto. |
| Capacidade | Uso de ferramentas SQL e fluxos permitido e coberto pelo plano/capacidade. |
| Banco | Servidor, instância e catálogo corretos para cada consulta, sem usar nomes de engines Python como endereços. |
| Rede | Se o SQL está na rede interna e qual gateway corporativo compartilhado deve ser usado. |
| Identidade | Autenticação SQL ou Windows compatível com a conexão e definida pela TI. |
| Permissões | Leitura apenas nos objetos e centros aprovados; execução apenas das procedures revisadas como somente leitura. |
| Participantes | Inicialmente, um operador do piloto com escopo de dados definido. |
| Dados enviados | Autorização para os resultados operacionais necessários serem processados pelo Copilot Studio. |

Texto para a TI:

> Já tenho acesso para criar agentes no Copilot Studio. Gostaria de realizar um piloto conectado aos dados reais de OEE e paradas do Digital JOST, usando somente o painel de teste, sem incorporar o chat ao portal. Solicito orientação sobre o gateway corporativo, a conexão SQL Server autorizada, o ambiente/capacidade para ferramentas e fluxos, e uma identidade com acesso de leitura restrito aos objetos e centros aprovados. Também precisamos confirmar o processamento desses dados no Copilot Studio e a referência oficial para validar os indicadores. A interface definitiva será no Microsoft Foundry; pretendemos reaproveitar as operações de consulta.

Não copie credenciais das configurações versionadas do Digital JOST. Insira credenciais somente na conexão gerenciada aprovada, nunca nas instruções ou na conversa do agente.

## 3. Fontes encontradas no projeto

O mapeamento abaixo foi feito como texto; não confirma os objetos efetivamente implantados ou as permissões do banco.

| Consulta | Evidência no código | Limite a preservar |
| --- | --- | --- |
| OEE exibido no monitoramento | `app/routes/jdt/monitoring.py`, em `monitoring_oee_post`, lê `TEMP_WORKCENTER_STATUS`. | É o estado disponibilizado pelo monitoramento; não é uma série de OEE histórico por período arbitrário. |
| Fórmula do OEE no monitoramento | `Performance * Availability * Quality / 10000`. | Os três fatores estão em escala percentual nessa consulta. |
| Paradas TD | `database/procedures/TD_OEE_ObterParadas.sql` e chamada em `app/utils/business.py`. | É necessário confirmar a versão implantada e o tratamento adicional do backend. |
| Paradas do relatório | `app/routes/reports/oee.py` usa `get_stops_with_plex_history`. | Combina fontes e aplica regras além da procedure isolada. |

O backend trata revisões aprovadas, nomes, categorias e histórico. Por isso, **consultar somente a procedure não comprova equivalência com o relatório completo**. Para essa equivalência, a operação deve reproduzir esses tratamentos ou reutilizá-los por uma API.

O primeiro marco é consultar o OEE atual de um centro aprovado. O segundo é consultar paradas reais com escopo TD explícito. O piloto só deve ser chamado equivalente aos relatórios depois da comparação e das adaptações necessárias.

## 4. Criar a conexão SQL Server

Passos para o responsável executar no ambiente corporativo liberado:

1. Abra [Copilot Studio](https://copilotstudio.microsoft.com/) e selecione o ambiente indicado pela TI.
2. Crie ou abra o agente **Digital JOST — Dados operacionais**.
3. Vá a **Ferramentas / Tools → Adicionar ferramenta / Add tool** e procure o conector **SQL Server**. Os menus podem variar conforme a experiência disponível.
4. Escolha uma conexão corporativa compartilhada autorizada, ou a opção para criar uma conexão.
5. Para SQL local, selecione o gateway indicado pela TI. Se ele não aparecer, confirme seu compartilhamento e as políticas do ambiente com a TI.
6. Informe servidor, catálogo e autenticação conforme os dados liberados. Esses valores ficam na conexão, não são entradas do agente.
7. Use apenas a operação de leitura aprovada. Não adicione operações de inclusão, atualização ou exclusão.

Se o conector estiver bloqueado, ou não houver gateway disponível, a integração ainda depende dessa configuração da TI. Conseguir criar o agente não confirma acesso ao banco.

Ao configurar a conexão de uma ferramenta, diferencie autenticação do usuário de autenticação do autor. Uma conexão do autor pode consultar com os privilégios dele, e não com os de quem pergunta. Não compartilhe esse acesso como se herdasse automaticamente as permissões do Digital JOST. [Autenticação de ferramentas — Microsoft](https://learn.microsoft.com/en-us/microsoft-copilot-studio/configure-enduser-authentication).

## 5. Montar a primeira ferramenta: OEE atual

A proposta abaixo usa um fluxo para validar e formatar a leitura. A TI pode preferir uma view ou procedure restrita que já devolva esse contrato; nesse caso, adapte somente a ação de consulta.

### 5.1 Criar o fluxo

1. No agente, abra **Tools → Add tool → Agent flow / Fluxo de agente**, em criar novo.
2. Use o nome **consultar_oee_atual**.
3. Confirme o gatilho **When an agent calls the flow / Quando um agente chama o fluxo** e a ação final **Respond to the agent / Responder ao agente**.
4. No primeiro teste, deixe o centro autorizado fixo no fluxo. Isso reduz ambiguidades enquanto verificamos a conexão. Só habilite entrada de centro depois de implementar a validação da lista permitida.
5. Entre o gatilho e a resposta, adicione **SQL Server → Get rows (V2) / Obter linhas (V2)**.

Fluxos desse tipo precisam de licença compatível, resposta síncrona e conclusão dentro do limite documentado de 100 segundos. Publicar o fluxo para torná-lo ferramenta é diferente de publicar o agente em um canal. [Criação de fluxo — Microsoft](https://learn.microsoft.com/en-us/microsoft-copilot-studio/advanced-flow-create).

### 5.2 Configurar a leitura

O DBA deve confirmar o objeto e os campos antes da execução. O objeto pode ser uma projeção restrita da fonte, caso a leitura direta não seja adequada.

| Campo da ação | Configuração proposta |
| --- | --- |
| Servidor e banco | Fixos, da conexão aprovada. |
| Tabela/view | Objeto autorizado baseado em `TEMP_WORKCENTER_STATUS`. |
| Filter Query | `Workcenter_Code eq '<CENTRO_AUTORIZADO>'`, substituindo o marcador pelo código aprovado. |
| Top Count | 2, para detectar se há mais de um registro quando esperamos apenas um. |
| Select Query, quando disponível | `Workcenter_Code,Performance,Availability,Quality,Log_Date`. |

Não use texto livre da pergunta para montar o filtro. Com um único centro, o valor é uma configuração fixa. Ao ampliar, o fluxo deve validar o código contra uma lista autorizada; filtros de interface ou instruções do agente não são uma barreira de acesso.

Depois da consulta, trate explicitamente:

- Nenhuma linha: devolver `sem_dados`, com o centro consultado.
- Mais de uma linha: devolver `resultado_ambiguo`; não escolher uma linha arbitrária.
- Uma linha com fator ausente/inválido: devolver `dados_incompletos`; não substituir por zero.
- Uma linha válida: devolver os fatores e calcular o OEE no fluxo ou na consulta aprovada.

No fluxo, use ações **Compor / Compose** para obter os três fatores numéricos e uma operação determinística equivalente a:

```text
OEE em percentual = Performance × Availability × Quality / 10000
```

Esse cálculo deve acontecer antes de responder ao modelo. Como conferência manual, fatores 80, 75 e 95 resultam em OEE 57; esses números são apenas exemplo de escala, não dados do banco.

### 5.3 Definir a resposta

Na ação **Respond to the agent**, devolva um campo de texto `resultado` contendo JSON estruturado por ações do fluxo. Use os valores dinâmicos, sem concatenar manualmente conteúdo não escapado.

Contrato proposto:

```text
status: ok | sem_dados | dados_incompletos | resultado_ambiguo | erro
centro: código validado
escopo: estado atual do monitoramento
performance_pct: número ou null
availability_pct: número ou null
quality_pct: número ou null
oee_pct: número ou null
data_evento_referencia: valor de Log_Date, se houver
consultado_em_utc: instante da consulta
fonte: identificação do objeto autorizado
```

`Log_Date` é tratado aqui como referência do evento da fonte, não como garantia de atualização de todos os fatores. O instante da consulta também não comprova que o dado de origem está atualizado.

Publique/salve o fluxo conforme a interface e adicione-o ao agente como ferramenta. Se essa operação estiver bloqueada pelo plano ou por política, solicite a liberação à TI; não presuma que uma avaliação permite todos os fluxos.

## 6. Adicionar a ferramenta de paradas

Faça essa etapa depois que a leitura de OEE estiver funcionando.

1. Peça ao DBA para confirmar a existência e a revisão somente de leitura de `TD_OEE_ObterParadas` no catálogo correto. O arquivo SQL do repositório é uma definição, não confirmação de implantação.
2. Crie um fluxo **consultar_paradas_td** com entradas de período e, posteriormente, centro/turno validados.
3. Valide início menor que fim, fuso/semântica das datas e limite de intervalo aprovado. Uma proposta inicial é um centro e até sete dias.
4. Use **SQL Server → Execute stored procedure (V2)**, com servidor, catálogo e nome da procedure fixos.
5. Mapeie os parâmetros conforme a tabela abaixo.
6. Trate o primeiro result set retornado e devolva resultados estruturados ao agente. Se a saída aparecer sem tipo, defina o schema no fluxo com base no contrato revisado; não use registros operacionais como exemplos em arquivos versionados.

| Parâmetro existente | Origem |
| --- | --- |
| `data_inicio` | Data/hora inicial validada. |
| `data_fim` | Data/hora final validada. |
| `workcenter_list` | Centro autorizado; nunca vazio para este piloto. |
| `shift_list` | `Turno 1`, `Turno 2`, `Turno 3` ou `Extra`, conforme recorte aprovado. |

O arquivo consultado retorna `id`, `workcenter`, `status`, `motivo`, `data_inicio`, `data_fim`, `turno` e `minutos_parados`. O código considera sobreposição com a janela e paradas abertas. O gateway retorna apenas o primeiro result set nessa operação. [Limitações de procedures no conector — Microsoft](https://learn.microsoft.com/en-us/connectors/sql/).

A procedure aceita filtros vazios como recorte amplo. O fluxo deve impedir isso; a identidade SQL deve ter restrição efetiva de acesso. Um limite de entrada no fluxo não substitui a permissão no banco.

Para ranking e comparação, faça a soma e o agrupamento no fluxo ou em uma operação SQL/API revisada. Devolva agregados completos e uma amostra limitada dos registros. Não envie milhares de linhas para o modelo somar e não calcule totais sobre uma lista truncada.

Informe no retorno: escopo TD, período, centro, turno, total, ranking por motivo, quantidade de registros, limite/truncamento, fonte e instante da consulta. Se houver truncamento antes da agregação, a resposta deve identificar resultado incompleto e não apresentar um ranking como completo.

Para reproduzir o relatório do Digital JOST, adapte essa ferramenta com os tratamentos de revisões aprovadas e histórico encontrados em `app/utils/business.py`. Até lá, seu nome e descrição devem deixar claro **paradas TD da procedure**, sem anunciar equivalência com o relatório consolidado.

## 7. Instruções do agente

Remova a base fictícia das fontes do agente, se tiver seguido o roteiro anterior. Em **Overview / Visão geral → Instructions / Instruções**, use:

```text
Você é o assistente de consulta operacional do Digital JOST no piloto
conectado a dados reais, executado pelo painel do Copilot Studio.
Responda em português do Brasil.

Para informar um indicador, chame a ferramenta correspondente. Nunca
complete números com conhecimento geral, arquivos fictícios ou estimativas.

consultar_oee_atual consulta o estado atual disponibilizado no monitoramento.
Não atende pedidos de OEE histórico por período. Informe essa limitação.

consultar_paradas_td consulta paradas TD no período e escopo informados.
Não apresente essa fonte como relatório consolidado de todo o histórico.

Solicite os filtros ausentes antes da consulta. Não invente códigos de
centro. Use somente centros e turnos aceitos pela ferramenta. Para datas
relativas como "ontem", peça a data absoluta se não houver uma referência
de data e fuso confiável fornecida pelo sistema.

Ao receber status diferente de ok, explique o problema. Falha de consulta,
falta de permissão ou dado ausente não significam zero.

Informe filtros, fonte e instante da consulta. Distinga estado atual,
referência do evento e atualização da fonte. Não chame o dado de tempo real
sem essa garantia explícita.

Use cálculos e agregações retornados pela ferramenta. Não calcule OEE
consolidado por média simples nem some listas truncadas. Expresse mudanças
de percentuais em pontos percentuais quando esse for o comparativo recebido.

Não afirme causa raiz sem evidência. Diferencie motivo registrado de hipótese.

Não execute alterações, não sugira SQL para execução automática e não peça
credenciais no chat. Explique que este piloto faz somente consultas.

Uma resposta no histórico não comprova uma nova consulta. Ao pedir dado
atualizado, chame novamente a ferramenta e informe a nova referência.
```

Desative pesquisa web para o piloto e confira no painel de atividade qual ferramenta foi chamada. Essas instruções orientam as respostas; a proteção dos dados depende das permissões efetivas e das validações das ferramentas.

## 8. Validar no painel de teste

Comece com filtros explícitos e compare com a referência oficial usando o mesmo recorte e instante tão próximo quanto possível. Estado atual pode mudar entre duas leituras.

| Teste | O que verificar |
| --- | --- |
| OEE atual do centro liberado | A ferramenta executou; fatores e fórmula coincidem com a fonte do monitoramento. |
| Pedir novamente o dado atualizado | Houve nova chamada; a resposta não apenas repetiu o histórico. |
| OEE de um mês passado | Explica que a ferramenta atual ainda não oferece histórico. |
| Paradas TD de um turno fechado | Período, centro e turno estão corretos; totais coincidem com a operação autorizada. |
| Ranking de motivos | Agregação feita antes da resposta e cobrindo o conjunto completo. |
| Centro fora do piloto | Bloqueio efetivo pela ferramenta/banco, não apenas recusa verbal do agente. |
| Período vazio ou invertido | Validação impede consulta ampla ou inválida. |
| Fonte indisponível | Explica o erro; não inventa número nem responde zero. |
| Alterar ou excluir dados | Nenhuma ferramenta de escrita disponível; identidade sem essas permissões. |
| Procedure versus relatório completo | Divergências de revisão/histórico são explicadas e resolvidas antes de afirmar equivalência. |

Registre em local corporativo aprovado o caso, filtros, fonte de referência, resultado esperado, resultado observado e desvio. Não versione logs ou dados de produção neste repositório.

Se houver mais participantes, valide a identidade e as permissões de cada um. O teste com sua conexão de autor não comprova autorização por usuário.

## 9. Migração para Foundry

A interface do chat e a configuração de ferramentas serão refeitas no Foundry. Não conte com uma migração automática do agente ou dos fluxos.

Para reduzir retrabalho:

1. Mantenha contratos estáveis para `consultar_oee_atual` e `consultar_paradas_td`.
2. Centralize cálculos e regras em operações SQL/API revisadas, fora das instruções do modelo.
3. Quando precisarmos dos tratamentos do backend, exponha uma API autenticada que coordene essas consultas sem executar o bootstrap legado em um serviço improvisado.
4. Reutilize os mesmos contratos e casos de validação nas ferramentas do Foundry.
5. Reavalie rede, identidade e permissões no novo ambiente. A configuração do gateway do Power Platform não é automaticamente reutilizada pelo Foundry.

A inclusão do chat no Digital JOST é uma etapa posterior; não é necessária para consultar dados reais pelo painel do Studio.

## 10. Situação desta preparação

Foi atualizado somente este roteiro. Nenhuma conexão, fluxo, agente ou objeto de banco foi criado pelo assistente. O nome do servidor, o gateway, as permissões e os objetos implantados ainda precisam ser confirmados com a TI.

Este arquivo descreve os passos para a execução no ambiente autorizado. Pelas regras de `AGENTS.md`, o assistente não pode iniciar/importar o Digital JOST, abrir conexão corporativa ou executar consultas por iniciativa própria; uma execução pelo assistente exige autorização explícita com comando, ambiente e escopo.

O sistema não foi executado; a validação foi somente estática.
