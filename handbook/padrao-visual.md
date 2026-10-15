# Padrão visual da modernização

Esta é a base visual implementada no shell Vue e em Eventos. Ela orienta as próximas telas, incluindo a futura modernização do Gerenciador de Demandas. O gerenciador antigo ainda não foi alterado.

## Identidade e estrutura

O azul JOST identifica a navegação e as ações principais. O laranja aparece como detalhe da marca no cabeçalho. O conteúdo usa fundo claro, superfícies brancas, bordas suaves e sombras discretas. Cores, fonte, raio dos cards e sombras ficam em `frontend/src/shared/styles/tokens.css`; evite repetir valores específicos em cada feature.

O `AppShell` mantém cabeçalho e conteúdo alinhados pelo mesmo `.dj-container`, com largura máxima de 110 rem (1.760 px na referência de 16 px/rem). As margens internas variam de 16 a 40 px conforme a janela. Isso aproveita a largura de notebooks e monitores e mantém um limite de leitura em telas muito grandes. Não adicione outro container de 1.200 px dentro das páginas de listagem.

Cada página começa com `PageHeader`: identificação curta e opcional da área em `eyebrow`, título principal, descrição e ações. Use o botão Volt para a ação principal. A listagem pode apresentar seu título e o total retornado pela API antes da grade; não crie indicadores sem uma fonte real.

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
| Informações do domínio | Slot padrão, com os campos necessários para reconhecer o registro. |
| Ação | Rótulo obrigatório em `actionLabel`, evento `open` e, quando necessário, `actionId` para restaurar o foco. `opensDialog` informa que a ação abre um diálogo. |

O card inteiro é acionável por um botão nativo, incluindo Enter e Espaço. O rótulo acessível contém a ação e o título completo. Essa variante possui uma única ação; não coloque links, botões ou campos nos slots cobertos pelo botão. Se uma tela precisar de ações independentes, componha uma variante apropriada antes de adicionar controles que não poderão ser acionados.

O título reserva duas linhas e o resumo mantém uma altura mínima uniforme. A ação fica no rodapé. O foco usa um contorno visível, e a elevação por movimento respeita `prefers-reduced-motion`. Para superfícies apenas informativas, o `Card` Volt continua disponível.

Em Eventos, `EventCard` continua responsável por selecionar os campos, formatar o período, apresentar dia/mês, o identificador e emitir a abertura do evento. `RecordCard` não consulta a API, não conhece permissões e não calcula status ou regras de negócio.

## Estados e componentes existentes

Use `RequestState` para carregamento, falha e vazio. O estado vazio usa a mesma superfície e pode receber `emptyIcon`; a mensagem deve explicar o que aparecerá naquela tela. Skeletons ficam dentro de `CardGrid`. Mensagens, botões, campos, tags, paginação e diálogos continuam usando Volt e os componentes compartilhados existentes.

As cores de foco se adaptam ao fundo: azul nas superfícies claras e branco no cabeçalho escuro. Textos longos precisam quebrar dentro dos cards; informações truncadas no resumo devem permanecer acessíveis ao abrir o registro.

## Como replicar

1. Use o `AppShell` existente e componha o cabeçalho com `PageHeader`.
2. Coloque os cards e os skeletons em `CardGrid`.
3. Crie um componente pequeno na feature que forneça os dados ao `RecordCard`, como faz `EventCard`.
4. Preserve autorizações no backend e o tratamento de carregamento, falha, vazio e foco na interface.
5. Ajuste tokens e componentes comuns quando a decisão visual for compartilhada; mantenha estilos e regras específicos próximos da feature.

Esta entrega foi conferida somente por análise estática. Build, aparência no navegador, interação por teclado e adaptação em diferentes larguras precisam ser confirmados em ambiente autorizado, conforme `AGENTS.md`.
