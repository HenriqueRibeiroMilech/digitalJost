# Padrão visual

Base oficial das telas Vue modernas. O legado Jinja mantém seus estilos até uma migração explícita. Os valores abaixo refletem os arquivos versionados; acessibilidade e responsividade precisam de conferência no navegador autorizado.

Revisão em **20/10/2026**, comparando tokens/layout, componentes compartilhados e consumidores de Eventos e Demandas com o [guia anterior](../historico/handbook/padrao-visual.md). Este arquivo concentra convenções comuns; interação de leitor, campos e regras de cada domínio ficam nos documentos de features.

## Como os estilos chegam à tela

`frontend/src/main.ts` instala PrimeVue em modo `unstyled`, o roteador e Vue Query, importa PrimeIcons e `assets/main.css`. Esse CSS importa Tailwind, `tailwindcss-primeui`, tokens e layout compartilhados. Os wrappers em `src/volt/` compõem os controles PrimeVue com classes e Pass Through.

`App.vue` envolve o RouterView em [AppShell](../../frontend/src/app/layouts/AppShell.vue). O shell possui o cabeçalho da marca, navegação e conteúdo principal, alinhados pelo mesmo `.dj-container`. Não carregar outro CSS completo do legado dentro do shell para reproduzir sua aparência.

## 1. Identidade e estrutura da página

| Elemento | Convenção atual |
|---|---|
| Tipografia | Montserrat, com fallbacks Segoe UI e sans-serif. |
| Cor principal | Azul JOST para navegação e ações principais. |
| Destaque | Laranja para detalhes e ações específicas, como o PDF de presença. |
| Superfícies | Fundo claro, cards brancos, bordas suaves e sombras discretas. |
| Conteúdo | `.dj-container`, largura máxima de 110 rem; margens adaptáveis. |
| Cabeçalho | `PageHeader` em painel com gradientes suaves, título, descrição, ícone opcional e ações; `eyebrow` somente quando necessário. |

Usar os tokens de [tokens.css](../../frontend/src/shared/styles/tokens.css) e as regras de [layout.css](../../frontend/src/shared/styles/layout.css). Não repetir cores e medidas da marca em cada feature nem criar um container menor dentro da listagem sem uma necessidade de leitura específica.

### Tokens e medidas de referência

| Token | Valor atual | Papel |
|---|---|---|
| `--color-dj-brand` | `#163a8a` | Marca e ações principais. |
| `--color-dj-header` | `#102656` | Cabeçalho escuro. |
| `--color-dj-accent` | `#ef7b04` | Detalhe da identidade. |
| `--color-dj-accent-action` | `#ff8a00` | Ação de destaque, hoje PDF. |
| `--color-dj-canvas` / `surface` | `#f5f7fb` / `#ffffff` | Fundo da página e superfícies. |
| `--color-dj-ink` / `muted` | `#182337` / `#526078` | Texto principal e secundário. |
| `--color-dj-border` | `#dfe6ef` | Bordas. |
| `--color-dj-success` / `danger` | `#087f5b` / `#b42318` | Feedback semântico. |
| `--radius-dj-card` | `1.25rem` | Cards e diálogos comuns. |
| `--container-dj-page` | `110rem` | Largura máxima do conteúdo. |

Com 16 px/rem, o container chega a 1.760 px; o padding horizontal usa `clamp(1rem, 2.5vw, 2.5rem)`, de 16 a 40 px. Breakpoints em rem acompanham a configuração de fonte; os valores em pixels são referências, não travas absolutas.

Montserrat é a primeira fonte declarada. A regra CSS não garante sua instalação/carregamento; na indisponibilidade entram Segoe UI e sans-serif. Não presumir uma entrega de fonte local apenas pelo nome no token. O tema atual é claro; classes dark dos wrappers não comprovam um modo escuro completo do produto.

### Cabeçalho e página

`PageHeader` recebe `id` e `title` obrigatórios, além de `description`, `eyebrow` e `icon` opcionais; o slot `actions` contém controles reais. O ícone é decorativo e usa uma classe PrimeIcons. O ID nomeia o título principal e pode ser usado em `aria-labelledby` da seção. Eventos usa calendário; Demandas usa lâmpada e identifica Transformação Digital no eyebrow. O painel combina azul e laranja suaves sobre a superfície clara, usando os tokens compartilhados. Ações podem quebrar linha em telas pequenas, sem provocar rolagem horizontal da página inteira.

O título usa 24 px em telas pequenas e 30 px a partir de 640 px, com a referência de 16 px/rem. O ícone acompanha essa proporção, com 40/48 px. Descrição e título ficam alinhados; o painel usa padding de 16/24 px para manter a listagem próxima do cabeçalho.

### Filtros e cabeçalho dos resultados

Aplicar `dj-filter-panel` ao formulário de filtros para compartilhar superfície, borda, raio, sombra e padding de 16/20 px. Labels, controles, disposição dos campos e eventos continuam na feature. Em espaços menores, empilhar campos antes de comprimir busca, seletor e ações em uma linha. Eventos continua aplicando busca com espera; Demandas continua aplicando por envio do formulário.

[ListHeader](../../frontend/src/shared/components/ListHeader.vue) centraliza título, etiqueta de contagem e orientação da listagem. Recebe `id` e `title` obrigatórios, `total`, `totalLabel` (padrão “Total de registros”) e `description` opcionais. O total zero é exibido; `undefined` omite a etiqueta. A feature passa a contagem filtrada da API e a omite durante carregamento inicial ou falha. O componente não calcula totais nem consulta endpoints.

```vue
<ListHeader id="events-results-title" title="Eventos encontrados"
  :total="!loading && !isError ? data?.total : undefined" total-label="Total de eventos"
  description="Selecione um evento para ver os detalhes." />
```

## 2. Listagens e cards

`CardGrid` é usado tanto nos registros quanto nos skeletons. Com a referência de 16 px/rem:

| Janela | Colunas |
|---|---:|
| Menor que 640 px | 1 |
| A partir de 640 px | 2 |
| A partir de 960 px | 3 |
| A partir de 1.200 px | 4 |

O espaçamento é de 20 px e o limite permanece em quatro colunas. Eventos e Minhas solicitações usam 12 itens por página; outras coleções podem escolher um tamanho apropriado.

`RecordCard` concentra a superfície e a interação. A feature fornece título, descrição, identificação visual, informações de domínio e ação; o componente não busca dados nem decide permissões.

- Usar IDs únicos em `titleId` e, quando necessário, `actionId`; informar `actionLabel` e `opensDialog`.
- Título e resumo têm até duas linhas visuais; o conteúdo completo continua disponível nos detalhes.
- Tons `brand`, `success` e `neutral` acompanham um significado definido pela feature, com texto e ícone além da cor.
- A superfície recebe um gradiente suave no tom do card; título e indicador da ação ganham destaque tanto no hover quanto no foco de teclado. A identificação e o status podem quebrar linha para acomodar cards estreitos.
- A variante `compact` reduz espaços e alturas mínimas. Demandas a utiliza; Eventos mantém a densidade padrão.
- O card possui um botão que cobre sua superfície. Não inserir links, botões ou campos nos slots sob essa ação.
- Hover controla elevação e sombra; foco de teclado usa contorno. Restaurar o foco não deve deixar o card elevado.

### Contrato do RecordCard

| Entrada/slot | Uso |
|---|---|
| `title`, `titleId` | Conteúdo e ID único do título. |
| `description` | Resumo opcional, com quebras de linha e duas linhas visuais. |
| `icon` ou `marker` | Ícone padrão ou identificação do domínio. |
| `badge` | Etiqueta/status com significado em texto. |
| `tone` | `brand`, `success` ou `neutral`; padrão `brand`. |
| `compact` | Padrão false; altera densidade, não grade/paginação. |
| Slot padrão | Informações curtas para reconhecer o registro. |
| `actionLabel`, `actionId`, `opensDialog` | Nome da ação, destino para restaurar foco e indicação de diálogo. |
| Evento `open` | Solicita ao consumidor abrir o registro. Não executa consulta. |

Na densidade padrão, há padding de 20 px, título/resumo com alturas mínimas e maior espaço no rodapé. A compacta usa padding de 16 px e dispensa essas alturas mínimas, mantendo duas linhas visuais. Não truncar o conteúdo persistido para caber no card.

`RecordCard` e `CardGridSkeleton` compartilham as medidas de densidade de `.dj-record-card` e `.dj-record-card-compact` em `layout.css`: padding, espaçamento, marcador, altura de linha e indicador da ação. A altura mínima de título/resumo também é definida pela densidade e acompanha duas linhas na padrão; a compacta dispensa essa reserva. A prop `compact` seleciona esse conjunto nos dois componentes. Marcadores da feature usam `--dj-card-marker-size` (48 px na padrão e 32 px na compacta); ajustes comuns ficam na base, sem sobrescrever a estrutura em cada tela. Em Demandas, tipo e urgência ficam na mesma faixa quando há espaço, com a data abaixo, sem um painel interno que aumente a altura do card.

O botão nativo cobre a superfície e fornece Enter/Espaço, nome acessível com ação+título e foco. O rodapé visual fica oculto de leitores de tela para evitar repetição. Para múltiplas ações independentes, criar uma composição apropriada; colocar controles embaixo desse botão os torna inacessíveis à interação pretendida.

Exemplo de composição, seguindo `RequestCard` (recorte de template):

```vue
<RecordCard :title-id="'request-title-' + request.id" :title="request.title"
  :description="request.description" :action-id="'request-open-' + request.id"
  action-label="Ver solicitação" opens-dialog compact @open="$emit('open')">
  <template #badge><Tag :value="statusLabel(request.status)" /></template>
  <p class="text-sm text-dj-muted">{{ request.urgency }}</p>
</RecordCard>
```

Imports, props e formatações ficam na feature; não copiar esse recorte como arquivo completo. `EventCard` fornece data/período, com marcador em formato de calendário, e tom do status. `RequestCard` fornece número/tipo, urgência/data e vínculo de contribuinte. Em Demandas, status ativos usam azul, concluído usa verde e pausado/cancelado/recusado usam neutro, sempre com rótulo e ícone. Urgência alta recebe destaque de perigo acompanhado do texto. Ambos usam a mesma grade, sem obrigar os mesmos campos ou densidade.

### Carregamento compartilhado dos cards

[CardGridSkeleton](../../frontend/src/shared/components/CardGridSkeleton.vue) compõe a mesma grade com placeholders Volt. Recebe `count` (padrão 12) e `compact` (padrão false). Os placeholders acompanham os marcadores e blocos de informação dos cards: Eventos usa oito na densidade padrão; Demandas usa doze compactos. Essa quantidade é visual e não altera o número de itens por página da API.

Usar no slot `loading` de `RequestState`, que anuncia o carregamento. A grade de placeholders fica oculta de leitores de tela. No exemplo, RequestState, CardGrid e CardGridSkeleton vêm de `shared/components/`; EventCard vem da feature e as variáveis/eventos pertencem à página:

```vue
<RequestState :loading="loading" :failed="isError" :error="listError"
  :empty="data?.items.length === 0" loading-label="Carregando eventos…"
  empty-title="Nenhum evento encontrado" @retry="refetch()">
  <template #loading><CardGridSkeleton :count="8" /></template>
  <CardGrid>
    <EventCard v-for="event in data?.items ?? []" :key="event.id"
      :event="event" @open="openEvent" />
  </CardGrid>
</RequestState>
```

Para outra feature, usar seu card e suas mensagens. A densidade do skeleton acompanha a dos registros. Uma alteração comum no carregamento deve ser feita nesse componente e conferida nos dois consumidores.

## 3. Formulários e diálogos

Compor controles Volt/PrimeVue com `FormField`, associando rótulo, controle e erro por ID. Identificar campos opcionais, apresentar mensagens próximas dos campos e preservar o que foi digitado em falhas.

`AppDialog` compõe o Dialog Volt: `size="standard"` é o padrão de 64 rem; `size="small"` usa 32 rem para confirmações e operações curtas. Ambos são limitados à janela, com rolagem interna, título acessível e tons `brand`, `success`, `neutral` e `danger`. O cabeçalho usa ícone de 36 px, título de 16 px e padding vertical de 12 px; conteúdo tem 16 px na vertical e 16/20 px nas laterais, conforme a janela. Rodapé segue o mesmo espaçamento lateral e 12 px na vertical. Essas medidas ficam na base compartilhada e valem para Demandas, Solicitações, Eventos e seus diálogos auxiliares. A máscara não fecha por clique externo. `busy` bloqueia fechamento e Escape; a feature também bloqueia envios e ações incompatíveis.

Detalhes usam `dj-detail-title` para o título do registro, `dj-detail-grid` para metadados e `dj-detail-section` para conteúdo e divisões. A grade distribui de uma a quatro colunas na largura padrão, preservando a quebra de nomes, datas e textos longos; não repetir um card completo para cada atributo. Seções usam divisores e espaçamento de 16 px. Rótulos de `FormField` dentro de `AppDialog` usam 13 px e distância de 6 px até o controle; `dj-form-section` mantém fieldsets com padding de 16 px no modal. A altura inicial menor de um textarea não reduz seu limite de conteúdo nem deve impedir rolagem/redimensionamento.

Abas de detalhe usam os controles Volt `Tabs`, `TabList`, `Tab`, `TabPanels` e `TabPanel`, com `dj-dialog-tabs` no Tabs e `pt:root:class="dj-tab-panels"` no TabPanels. O estilo comum reduz o espaçamento das abas e elimina padding lateral duplicado. Preservar rascunhos ao alternar painéis e bloquear mudanças incompatíveis enquanto há escrita ou alterações pendentes. Demandas separa Informações, Execução, Tarefas e Histórico; Eventos usa Informações e Listas de presença.

Usar `closed`, emitido após a transição, para restaurar o foco. Em exclusões, explicar o alcance da operação, priorizar Cancelar no foco inicial e retornar ao controle de origem ou a um destino válido se o registro tiver sido removido.

Cadastro e edição devem agrupar campos relacionados e manter botões com verbos claros. Regras, requisições, confirmação de sucesso e atualização de cache permanecem na feature.

### Campos acessíveis

`FormField` recebe `id`, `label` e `error`; o slot fornece `controlProps` com ID, `invalid`, `aria-invalid` e associação ao erro. Em InputText/Textarea, aplicar essas propriedades ao controle. O Select pode exigir `input-id` e Pass Through para associar a descrição ao elemento que recebe foco; copiar o uso verificado nos formulários atuais.

```vue
<FormField id="event-name" v-slot="{ controlProps }" label="Nome do evento"
  :error="fieldErrors.name">
  <InputText v-bind="controlProps" v-model="name" required :maxlength="120" />
</FormField>
```

Contadores e `maxlength` ajudam na entrada; o servidor continua validando campos, escopo e regras. Em falha 422, associar mensagens por campo conhecido, preservar o formulário e focar o primeiro controle inválido. Erros gerais aparecem em Message sem traceback/SQL. Informar formatos, limites de anexos e opcionais perto da decisão correspondente.

### Diálogo e foco

| Propriedade/evento | Comportamento comum |
|---|---|
| `id`, `title`, `subtitle`, `icon` | Identificação e cabeçalho; ícone padrão de calendário, substituível. |
| `visible`, `update:visible` | Estado controlado pelo chamador. |
| `tone` | Marca, sucesso, neutro ou perigo; não concede autorização. |
| `busy` | Impede fechar pelo controle/Escape e ignora mudança de visibilidade. |
| `descriptionId` | Associa uma instrução já existente no conteúdo. |
| `initialFocusId` | Foca o controle depois da transição de abertura. |
| `closed` | Emitido após ocultar, para o consumidor restaurar foco. |
| Slots padrão/`footer` | Conteúdo e ações específicos da feature. |

AppDialog limita altura à janela, mantém conteúdo rolável e cabeçalho/rodapé separados. O foco inicial configurado é aplicado após a transição, porque o Dialog Volt também define foco nessa fase. Em confirmação destrutiva, usar tom danger e Cancelar como foco inicial; em renomeação, o campo do nome.

`busy` não desabilita sozinho cada botão/rota da página nem decide quando há operação pendente. A feature precisa bloquear envio duplicado, controles e navegação incompatíveis e repassar o estado dos filhos. Restaurar foco para elemento ainda existente; se foi excluído/filtrado, escolher título, criação ou outro controle válido.

O leitor de presença é uma exceção consciente: usa Dialog Volt maximizado, sem fechamento por Escape/máscara e com encerramento explícito. Não transformar AppDialog em tela cheia para todos os usos por causa dessa necessidade local.

## 4. Estados e feedback

- `RequestState`: carregando, vazio, falha e tentativa manual; adaptar os textos ao domínio.
- `CardGridSkeleton`: placeholders de cards nas densidades padrão e compacta, dentro do estado de carregamento.
- `ListPagination`: navegação a partir de dados retornados pela API, sem filtrar apenas a página visível.
- `validationMessages`: associação de erros 422 aos campos conhecidos.
- Durante envio: impedir duplicidade e fechamento que descarte o formulário.
- Após sucesso: atualizar a consulta correspondente; falha ao renovar a lista não desfaz uma gravação concluída.
- Em resposta incerta: orientar conferência antes de repetir. Não repetir escritas automaticamente.
- Status precisa de rótulo compreensível; SQL, traceback e detalhes de infraestrutura não aparecem ao usuário.

`RequestState` prioriza carregamento, depois falha, depois vazio; nos demais casos apresenta o slot. Carregamento tem anúncio acessível e skeletons ocultos de leitores de tela. Para 401/403/404, orienta voltar ao portal; outras falhas oferecem tentativa manual. A feature escolhe textos e passa o erro real para identificar o status.

`ListPagination` aparece apenas com `total > perPage`; o controle usa índice zero internamente e a API começa em um. Exibir a contagem filtrada do servidor, sem inventar total por multiplicação do tamanho da página. Skeletons devem acompanhar a densidade/layout usados pelos resultados.

### Convenções de ações e dados

- Ação principal: Button Volt com verbo/objeto. Cancelar, voltar e ações secundárias usam a composição apropriada, geralmente SecondaryButton.
- Exclusão: confirmação de alcance, tom danger e classe compartilhada `dj-danger-action` quando aplicável. Não usar o mesmo destaque visual de uma ação neutra.
- Ícone sem texto: nome acessível específico, título útil e alvo de interação suficiente. Gestão de presença usa 40 px; não reduzir a lixeira a um ícone pequeno sem área clicável.
- Informações completas: detalhes preservam quebras de linha e textos longos; campos ausentes usam mensagem adequada, como “Não informado”.
- Tabelas: manter colunas legíveis e rolagem local quando necessária. A de presença usa DataTable Volt e Column de `primevue/column`, com dados paginados no servidor.
- Cor: acompanhar status por texto e/ou ícone. Azul, verde e cinza não devem ser a única informação transmitida. O destaque laranja atual não substitui conferência de contraste.

O foco global usa contorno de 2 px e offset de 3 px; no cabeçalho escuro a cor é branca. O tema reduz duração de animação/transição com `prefers-reduced-motion`; `RecordCard` também limita movimento ao contexto permitido. Essa existência no CSS não equivale a certificação de acessibilidade.

## 5. Aplicação e manutenção

Reutilizar [componentes compartilhados](../../frontend/src/shared/components/) e os wrappers locais de [Volt](../../frontend/src/volt/). Alterações nos wrappers afetam vários consumidores e exigem escopo próprio; uma necessidade específica começa na feature.

Na revisão visual, conferir teclado, nomes acessíveis dos botões com ícone, foco de abertura/retorno, campos inválidos, textos longos, telas pequenas, rolagem de tabelas e preferência por movimento reduzido. Captura de crachá e PDF têm cuidados próprios em [Eventos](../features/eventos.md).

Mudanças em cores, medidas ou componentes comuns atualizam este guia. Regras visuais específicas ficam em [Eventos](../features/eventos.md), [Demandas](../features/demandas.md) ou no documento da feature correspondente. A base de chamadas HTTP está em [Base compartilhada](../features/base-compartilhada.md).

### Roteiro para uma nova tela

1. Registrar a página no shell/Router e definir título, descrição e ação principal com PageHeader.
2. Compor filtros com controles Volt e rótulos em `dj-filter-panel`; aplicar no servidor e voltar à página inicial quando necessário. Usar ListHeader para o título e a contagem dos resultados.
3. Usar RequestState e, em listagem de cards, CardGridSkeleton no carregamento e CardGrid nos registros, mantendo a mesma densidade.
4. Criar o card pequeno da feature como consumidor de RecordCard; manter regras/formatos de domínio locais.
5. Usar AppDialog quando apropriado, decidir foco inicial/retorno e repassar busy dos fluxos filhos.
6. Tratar validação, resultado incerto, conteúdo longo e erro de renovação separado da escrita.
7. Conferir consumidores antes de alterar tokens/wrappers comuns; revisar aparência e teclado em ambiente autorizado.

### Referência de composição e variações

O [mapa do frontend](../../frontend/README.md) explica onde implementar cada parte. [EventsPage.vue](../../frontend/src/features/events/pages/EventsPage.vue) é a referência atual de listagem: PageHeader, filtros, RequestState, grade de cards, paginação e diálogo. Para a relação entre abas, URL e detalhes, consultar RequestsPage.vue. Reutilizar as composições e manter consultas, permissões, mensagens e regras específicas na feature.

| Necessidade | Variação adotada |
|---|---|
| Card com uma ação principal | RecordCard com densidade padrão ou compacta; o conteúdo vem da feature. |
| Cor do card | Tons brand, success ou neutral conforme significado do domínio, acompanhados de texto. |
| Ação principal | Button Volt com verbo claro; controles secundários usam SecondaryButton quando apropriado. |
| Confirmação destrutiva | AppDialog com tom danger, Cancelar no foco inicial e indicação do alcance da exclusão. |
| Formulário em diálogo | AppDialog com conteúdo/FormField e estado busy coordenados pela feature. |
| Mais de uma ação independente no card | Composição própria que mantenha controles acessíveis, sem colocá-los sob o botão de superfície do RecordCard. |

Uma nova variação precisa responder a uma necessidade concreta e manter um contrato simples. Não criar um componente para cada combinação de cor e espaçamento nem repetir overrides extensos por tela. Se a estrutura comum precisar mudar, alterar o componente responsável e conferir seus consumidores.

### Desenvolvimento com IA

Antes de gerar uma tela, fornecer comportamento, contrato da API, campos e ações, além deste guia e da referência de composição. A IA deve partir dos controles de `volt/` e dos componentes de `shared/`, usando os tokens de marca. O pedido pode usar o roteiro de [frontend/README.md](../../frontend/README.md#7-ao-pedir-uma-tela-para-a-ia).

Na revisão, conferir se a feature reaproveitou o componente apropriado, se o card contém apenas os dados específicos, se carregamento/erro/vazio foram cobertos e se alterações comuns foram feitas no lugar responsável. Estados de envio, foco, responsividade e permissões fazem parte da implementação. Não acrescentar dependências ou abstrações sem uma necessidade demonstrada.

Na revisão estática, comparar props/slots/IDs, condições de busy, labels e classes entre consumidores. No navegador autorizado, conferir larguras próximas dos breakpoints, zoom, teclado completo, abertura/retorno de foco, leitores de tela, contraste e redução de movimento. Não afirmar conformidade apenas pela presença de ARIA.

**O sistema não foi executado; a validação foi somente estática.** Não houve build, inspeção em navegador ou medição de contraste nesta revisão.
