# Padrão visual da modernização

Esta é a base visual implementada no shell Vue e em Eventos. Ela orienta as próximas telas, incluindo a futura modernização do Gerenciador de Demandas. O gerenciador antigo ainda não foi alterado.

## Identidade e estrutura

O azul JOST identifica a navegação e as ações principais. O laranja aparece como detalhe da marca no cabeçalho e destaca o download de PDF nas listas de presença. O conteúdo usa fundo claro, superfícies brancas, bordas suaves e sombras discretas. Cores, fonte, raio dos cards e sombras ficam em `frontend/src/shared/styles/tokens.css`; evite repetir valores específicos em cada feature.

O `AppShell` mantém cabeçalho e conteúdo alinhados pelo mesmo `.dj-container`, com largura máxima de 110 rem (1.760 px na referência de 16 px/rem). As margens internas variam de 16 a 40 px conforme a janela. Isso aproveita a largura de notebooks e monitores e mantém um limite de leitura em telas muito grandes. Não adicione outro container de 1.200 px dentro das páginas de listagem.

Cada página começa com `PageHeader`: identificação curta e opcional da área em `eyebrow`, título principal, descrição e ações. Use o botão Volt para a ação principal. A listagem pode apresentar seu título e o total retornado pela API antes da grade; não crie indicadores sem uma fonte real.

Eventos usa somente o título **Eventos** e a descrição **Organize os eventos, acompanhe os períodos de realização e listas de presença.**, sem identificação de área acima do título.

## Grade de cards

Use `CardGrid` tanto para os registros quanto para o carregamento, evitando regras de colunas diferentes entre os dois estados. As medidas abaixo consideram a referência de 16 px/rem; os pontos de adaptação estão em rem para acompanhar as preferências de fonte.

| Largura da janela | Colunas |
|---|---|
| Abaixo de 640 px | 1 |
| A partir de 640 px | 2 |
| A partir de 960 px | 3 |
| A partir de 1.200 px | 4 |

O espaço entre cards é de 20 px. As colunas usam `minmax(0, 1fr)` para permitir a adaptação dos textos. O limite é de quatro colunas mesmo em monitores maiores. Eventos mantém os 12 registros por página, formando três linhas completas no desktop quando há dados suficientes.

## Card de registro

`frontend/src/shared/components/RecordCard.vue` compõe o `Card` Volt e concentra a superfície, o espaçamento, a tipografia, a área de informações, a ação e os estados de interação. Não é necessário copiar o HTML ou alterar o componente de `src/volt/` para criar outro card de domínio.

| Parte | Como fornecer |
|---|---|
| Título | `title` e `titleId`, com ID único na página. |
| Resumo | `description`, limitado visualmente a duas linhas. O texto completo deve continuar disponível nos detalhes. |
| Identificação visual | `icon` para um PrimeIcon ou slot `marker` para conteúdo específico, como a data do evento. |
| Identificador ou etiqueta | Slot `badge`, usando Tag Volt quando adequado. O texto precisa explicar o significado, sem depender somente da cor. |
| Cor de identificação | `tone`: `brand`, `success` ou `neutral`. Controla a faixa superior, o marcador, a ação e o destaque ao interagir. A feature escolhe o tom. |
| Informações do domínio | Slot padrão, com os campos necessários para reconhecer o registro. |
| Ação | Rótulo obrigatório em `actionLabel`, evento `open` e, quando necessário, `actionId` para restaurar o foco. `opensDialog` informa que a ação abre um diálogo. |

O card inteiro é acionável por um botão nativo, incluindo Enter e Espaço. O rótulo acessível contém a ação e o título completo. Essa variante possui uma única ação; não coloque links, botões ou campos nos slots cobertos pelo botão. Se uma tela precisar de ações independentes, componha uma variante apropriada antes de adicionar controles que não poderão ser acionados.

O título reserva duas linhas e o resumo mantém uma altura mínima uniforme. A ação fica no rodapé. Elevação, sombra e destaque da seta acompanham somente o hover; o foco de teclado usa o contorno `:focus-visible` do botão. Restaurar o foco ao fechar um modal não mantém o card elevado. A elevação por movimento respeita `prefers-reduced-motion`. Para superfícies apenas informativas, o `Card` Volt continua disponível.

Em Eventos, `EventCard` continua responsável por selecionar os campos, formatar o período, apresentar dia/mês e o rótulo de status e emitir a abertura do evento. `RecordCard` não consulta a API, não conhece permissões e não calcula status ou regras de negócio.

## Status e filtros de Eventos

O status vem da API e determina a identificação visual, sempre acompanhada de texto e ícone.

| Status | Identificação | Critério |
|---|---|---|
| Futuro (`upcoming`) | Azul | O início ainda não foi atingido. |
| Em andamento (`ongoing`) | Verde | Início atingido e fim ainda não atingido. |
| Concluído (`completed`) | Cinza | Fim atingido. |
| Sem período (`unscheduled`) | Neutra, com rótulo próprio | Registro antigo sem período completo. |

A faixa superior do card, o marcador da data e o rodapé acompanham o tom. `EventStatusBadge` usa Tag Volt e centraliza o rótulo e o ícone, tanto no card quanto nos detalhes e na confirmação de exclusão. Os modais identificam o evento pelo título. Cores adicionais de outros domínios precisam ter um significado definido pela própria feature.

`EventFilters` compõe InputText e MultiSelect Volt. A tela começa com Futuros e Em andamento selecionados. É possível combinar vários status, desmarcar todos para consultar todos ou usar “Restaurar padrão”. A pesquisa por título reage após uma pausa de 300 ms ou imediatamente ao pressionar Enter. Os filtros consultam a API; não se limitam aos 12 itens da página atual. O total exibido é o total filtrado.

As consultas de lista e detalhes atualizam o status a cada 60 segundos com a aba ativa, usando o relógio do TD. A lista pausa com o modal aberto, e os detalhes pausam na edição, na confirmação de exclusão e na aba de presença. A edição preserva os filtros da lista; ao alterar o período, um evento pode deixar de corresponder aos status selecionados. O estado vazio orienta a ajustar a busca ou incluir outros status.

## Modais

`AppDialog` compõe o Dialog Volt com cabeçalho, ícone, subtítulo, superfície arredondada e rodapé separado. Use um `id` único, `visible`, `title` e o evento `update:visible`; `closed` é emitido após a transição e permite que a página restaure o foco. O título recebe um ID explícito para nomear o diálogo de forma acessível. `descriptionId` pode associar uma instrução existente no conteúdo.

Os modais que usam `AppDialog` têm largura padrão de **64 rem (1.024 px na referência de 16 px/rem)** e máximo de `calc(100vw - 2rem)`, respeitando a janela e mantendo rolagem interna. Esse padrão atende cadastro, edição, detalhes e exclusão de Eventos e será reaproveitado pelas próximas features. `tone` aceita `brand`, `success`, `neutral` ou `danger`. O estado `busy` bloqueia o botão de fechar e a tecla Escape; a máscara não fecha o diálogo ao clicar fora. Regras, envio e tratamento das falhas continuam na feature.

Em Eventos, cadastro e edição agrupam identificação e período em fieldsets com legendas e rótulos. Detalhes destacam título, status, período e descrição, com editar e excluir no topo. A confirmação de exclusão apresenta o evento e o período, usa tom vermelho e mantém o foco inicial em Cancelar. A ação de confirmar só fica disponível com a permissão correspondente e sem gravação em andamento. Requisições de consulta em segundo plano não desmontam o conteúdo dos detalhes nem reiniciam o formulário.

O formulário também apresenta Tipo de evento com Select Volt pesquisável e botão + ao lado; o cadastro da opção abre no próprio formulário, preserva os demais campos e seleciona o tipo salvo. Instrutor aparece ao lado do tipo no desktop e Conteúdo programático usa Textarea com contador; ambos são identificados como opcionais. Os detalhes apresentam tipo/instrutor e uma seção própria para o conteúdo, preservando quebras de linha e mostrando “Não informado” quando ausente. Veja [Campos e tipos de Eventos](eventos.md).

Cada opção de tipo apresenta uma lixeira com nome acessível e título quando a sessão permite excluir. O clique na lixeira abre a confirmação sem selecionar o item; Alt+Delete no tipo selecionado oferece a mesma ação por teclado. `EventTypeDeleteDialog` usa AppDialog em tom vermelho, nome do tipo em destaque, foco inicial em Cancelar, aviso para tipos em uso e bloqueio durante o envio. Fechar devolve foco ao Select e preserva os outros campos do formulário.

Os detalhes de Eventos usam Tabs Volt para separar Informações e Listas de presença. Cada lista tem nome, total e uma ação explícita de abertura. Seus participantes aparecem no DataTable Volt, com paginação no servidor e quatro colunas de dados: Empresa, Matrícula, Nome e Setor. A matrícula mostra apenas os oito dígitos finais, preservando zeros e ocultando o prefixo da empresa na exibição. Os demais campos vazios aparecem como “Não informado”. Uma coluna Ações oferece Remover quando a sessão tem essa capacidade. As colunas vêm do `primevue/column`, pois recebem o estilo do DataTable Volt instalado.

Dentro da lista, Editar nome e Excluir lista usam somente os ícones de lápis e lixeira no cabeçalho, em um grupo separado das ações com texto. Esses botões e o de remover participante têm área de 40 px, título ao passar o mouse e nome acessível. `AttendanceActionDialog` compõe AppDialog, InputText, Message e botões Volt: edição usa o tom da marca e foco no nome; exclusões usam o tom vermelho e foco inicial em Cancelar. A confirmação da lista avisa que todas as presenças dela serão removidas; a de participante apresenta nome, matrícula de oito dígitos e empresa. Durante a escrita, não se pode fechar ou reenviar. O evento e a captura ficam bloqueados enquanto o diálogo está aberto. Após confirmar, totais e páginas são atualizados; excluir a lista retorna à coleção e remover a última linha pode recuar a página.

O cabeçalho da lista coloca as ações à direita do nome em telas grandes, ocupando o espaço antes reservado ao logo, e abaixo dele em telas menores. A página web da lista não exibe logo. Baixar PDF e Iniciar preenchimento por leitor usam Button Volt e ficam lado a lado no mesmo grupo: PDF em laranja vivo (`--color-dj-accent-action: #ff8a00`) com texto branco, pela classe compartilhada `dj-accent-action`, e captura em azul. O PDF mantém ícone, rótulo de progresso e mensagem de falha na própria lista. O documento A4 usa azul JOST no cabeçalho da tabela, linhas alternadas, nomes e dados do evento/lista antes dos participantes, logo no alto à direita e rodapé numerado, sem exibir IDs do evento/lista. A tabela repete seu cabeçalho nas continuações e mostra apenas os oito dígitos finais da matrícula.

`initialFocusId`, opcional no AppDialog, escolhe o controle que recebe foco após a transição de abertura via Pass Through, pois o próprio Dialog também define foco nessa etapa. O diálogo de gestão usa o campo do nome ou Cancelar; outros chamadores mantêm o comportamento padrão enquanto não informarem essa propriedade. Referências oficiais: [ciclo de abertura do Dialog](https://github.com/primefaces/primevue/blob/4.5.5/packages/primevue/src/dialog/Dialog.vue) e [atributos Pass Through](https://github.com/primefaces/primevue/blob/4.5.5/packages/core/src/basecomponent/BaseComponent.vue).

Empresa, nome e setor são preenchidos pelo backend quando a consulta ao diretório encontra uma única pessoa compatível. A confirmação completa pode mostrar o nome do participante. Quando a presença foi salva com dados opcionais incompletos, o leitor apresenta “Presença registrada” em azul com aviso de dados indisponíveis. Sem correspondência única ou com LDAP indisponível, informa que a tentativa não foi registrada e permite tentar novamente. A tabela mantém “Não informado” nos campos ausentes. Repetir uma leitura pode completar dados faltantes, mantendo a posição e o total do registro existente.

O preenchimento por leitor usa Dialog Volt ocupando a janela, com o evento e a lista no cabeçalho. A tela para convidados concentra instrução, campo e resultado: azul para aguardar/gravar, verde para confirmação ou presença existente e vermelho para tentar novamente/falha. Texto e ícone acompanham as cores. “Confirmando presença…” cobre o intervalo de estabilização configurado em `readingDelay` desde o último caractere e a consulta/gravação na API. O envio é automático mesmo sem Enter; Enter vazio ou tardio preserva o resultado. O campo recebe foco ao abrir e após cada leitura; há uma ação para reativá-lo quando perde foco. O sucesso retorna à instrução após 3,5 segundos ou ao começar outra leitura. A tela não exibe a tabela dos demais participantes.

Durante a captura, não se pode trocar de aba, editar/excluir ou fechar o evento; “Encerrar leitura” devolve o foco ao botão de iniciar. O encerramento fica bloqueado enquanto uma gravação está pendente. A exclusão do evento avisa que também remove suas listas e presenças.

## Estados e componentes existentes

Use `RequestState` para carregamento, falha e vazio. O estado vazio usa a mesma superfície e pode receber `emptyIcon`; a mensagem deve explicar o que aparecerá naquela tela. Skeletons ficam dentro de `CardGrid`. Mensagens, botões, campos, tags, paginação e diálogos continuam usando Volt e os componentes compartilhados existentes. Os tons e a classe `dj-danger-action` ficam nos estilos compartilhados; esta evolução não altera os arquivos dos componentes Volt instalados.

As cores de foco se adaptam ao fundo: azul nas superfícies claras e branco no cabeçalho escuro. Textos longos precisam quebrar dentro dos cards; informações truncadas no resumo devem permanecer acessíveis ao abrir o registro.

## Como replicar

1. Use o `AppShell` existente e componha o cabeçalho com `PageHeader`.
2. Coloque os cards e os skeletons em `CardGrid`.
3. Crie um componente pequeno na feature que forneça os dados ao `RecordCard`, como faz `EventCard`.
4. Preserve autorizações no backend e o tratamento de carregamento, falha, vazio e foco na interface.
5. Ajuste tokens e componentes comuns quando a decisão visual for compartilhada; mantenha estilos e regras específicos próximos da feature.
6. Componha os modais com `AppDialog` e mantenha a restauração de foco, a confirmação das exclusões e o bloqueio de ações duplicadas.

Esta entrega foi conferida somente por análise estática. Build, aparência no navegador, interação por teclado e adaptação em diferentes larguras precisam ser confirmados em ambiente autorizado, conforme `AGENTS.md`.
