# Frontend do Digital JOST

O frontend moderno usa Vue, TypeScript, Vue Router, Vue Query e controles Volt sobre PrimeVue/Tailwind. As funcionalidades ficam organizadas por feature, com componentes visuais compartilhados para manter o mesmo padrão entre telas.

Este arquivo é o mapa para localizar e desenvolver o código. As convenções de aparência e interação ficam no [padrão visual](../handbook/docs/padrao-visual.md); preparação do ambiente, build e publicação ficam no [guia de servidor](../handbook/docs/servidor-e-publicacao.md). As regras de execução de [AGENTS.md](../AGENTS.md) continuam obrigatórias.

## 1. Onde fica cada coisa

```text
src/
├── main.ts                   # instala plugins e importa os estilos globais
├── App.vue                   # liga o shell às páginas do Router
├── app/
│   ├── layouts/AppShell.vue  # cabeçalho, navegação e área comum
│   └── pages/                # páginas gerais, como a de endereço inexistente
├── router/index.ts           # endereços e páginas Vue
├── assets/main.css           # entrada dos estilos
├── volt/                     # controles básicos locais sobre PrimeVue
├── shared/
│   ├── api/                  # cliente HTTP, paginação e erros de validação
│   ├── components/           # composições visuais do Digital JOST
│   ├── composables/          # comportamento reutilizado, como usePagination
│   └── styles/               # tokens visuais e regras comuns de layout
└── features/
    ├── events/
    └── demands/
```

Dentro de uma feature, o padrão atual é:

```text
features/<feature>/
├── pages/             # coordenação da tela, consultas, filtros e diálogos
├── components/        # cards, formulários e detalhes próprios da feature
├── api.ts             # chamadas HTTP da funcionalidade
├── types.ts           # contratos TypeScript de entrada e saída
└── arquivos locais    # formatação de datas/status e outros auxiliares necessários
```

Os auxiliares são criados conforme o uso. Eventos possui `dates.ts`, `statuses.ts` e `attendanceApi.ts`; Demandas usa `presentation.ts`. Não é preciso criar todos esses arquivos para uma nova tela. Um composable local só faz sentido quando organizar ou reutilizar um comportamento concreto.

## 2. Volt, componentes compartilhados e componentes da feature

| Local | Responsabilidade | Exemplos |
|---|---|---|
| `volt/` | Controles básicos e sua apresentação local. | `Button`, `InputText`, `Select`, `DatePicker`, `Dialog`. |
| `shared/components/` | Composições comuns das telas do portal. | `RecordCard`, `PageHeader`, `AppDialog`, `FormField`. |
| `features/.../components/` | Dados, campos e comportamento de uma funcionalidade. | `EventCard`, `RequestCard`, `EventForm`. |

Os arquivos Volt são wrappers locais de controles PrimeVue com classes Tailwind. O comportamento do controle vem do PrimeVue; a apresentação local pode ser mantida no projeto. A configuração em `main.ts` usa PrimeVue em modo `unstyled`.

Nas features, use os controles de `@/volt/`. Quando houver uma composição compartilhada apropriada, use-a: por exemplo, `AppDialog` combina o Dialog com as convenções de título, largura, busy e foco do portal. A tabela de presença usa `Column` de `primevue/column`, uma peça estrutural da tabela, junto do DataTable Volt.

Não é necessário criar outro wrapper apenas para renomear um controle. Alterações em `volt/` ou `shared/` devem considerar todos os consumidores. Estilos específicos de um domínio permanecem na feature.

## 3. Os cards das próximas funcionalidades

```text
volt/Card
  → shared/RecordCard
    → EventCard, RequestCard e futuros cards de domínio
```

[RecordCard.vue](src/shared/components/RecordCard.vue) centraliza superfície, título, resumo, ação, foco e interação. O card da feature fornece os dados e as informações específicas por props e slots. Ele não precisa repetir bordas, sombras e toda a estrutura HTML do card.

| Necessidade | Recurso existente |
|---|---|
| Cabeçalho da página | `PageHeader` com título, descrição e slot de ações. |
| Cabeçalho dos resultados | `ListHeader` com título, total do servidor e orientação opcional. |
| Superfície dos filtros | Classe compartilhada `dj-filter-panel` no formulário da feature. |
| Grade responsiva de registros | `CardGrid`. |
| Card com uma ação principal | `RecordCard`, normalmente dentro de um card da feature. |
| Carregamento de uma grade | `CardGridSkeleton`, com `count` e `compact`. |
| Carregando, vazio e falha | `RequestState`, com mensagens do domínio. |
| Paginação | `usePagination`, `ListPagination` e o total retornado pela API. |
| Campo com rótulo e erro | `FormField` com o controle Volt apropriado. |
| Diálogo | `AppDialog` com conteúdo e ações da feature. |

As variações atuais do card são densidade padrão ou `compact`, e tons `brand`, `success`, `neutral` ou `warning`. `EventCard` usa a densidade padrão; `RequestCard` usa a compacta. O significado de cada status e seu texto pertencem à feature.

As medidas de densidade ficam em `shared/styles/layout.css` e são consumidas por `RecordCard` e `CardGridSkeleton`. Um marcador próprio usa `--dj-card-marker-size` para acompanhar essa densidade. Não repetir padding e tamanhos do card em cada feature; manter `compact` igual no card e no skeleton correspondente.

O `RecordCard` possui um botão que cobre sua superfície. Seus slots devem conter informações; links, botões e campos independentes precisam de uma composição apropriada para múltiplas ações. IDs de título e ação devem ser únicos.

O `CardGridSkeleton` é decorativo. Use-o no slot `loading` de `RequestState`, que fornece o anúncio acessível. `count` define apenas quantos placeholders são desenhados; não muda a paginação da API. Eventos preserva oito placeholders; Demandas, doze compactos.

## 4. Referência para montar uma listagem

Leia [EventsPage.vue](src/features/events/pages/EventsPage.vue) para ver a composição completa: cabeçalho, filtros, consulta, estados, cards, paginação e coordenação do diálogo. Veja [RequestsPage.vue](src/features/demands/pages/RequestsPage.vue) para as particularidades de abas e seleção pela URL. Aproveite a estrutura comum e mantenha os fluxos específicos da nova feature.

A composição visual segue esta sequência:

```text
AppShell
  → página da feature
    → PageHeader
    → filtros e feedback quando necessários
    → ListHeader com total do servidor, quando disponível
    → RequestState
      → carregando: CardGridSkeleton
      → resultado: CardGrid + card da feature
      → vazio ou falha: mensagens do domínio
    → ListPagination
    → diálogo da feature composto com AppDialog, quando necessário
```

As consultas ficam na feature usando Vue Query e as funções de `api.ts`. Cards e componentes visuais compartilhados recebem dados e emitem eventos, sem buscar registros por conta própria. Os componentes de detalhe podem coordenar sua própria consulta, como acontece nos fluxos atuais.

As chaves de consulta distinguem feature, operação, filtros e página. Após uma gravação, atualize ou invalide as consultas relacionadas. Não copie as chaves de Eventos para outra funcionalidade nem repita escritas automaticamente quando a resposta for incerta.

## 5. Onde alterar cada coisa

| Quero alterar… | Arquivo ou pasta |
|---|---|
| Menu e cabeçalho geral | `src/app/layouts/AppShell.vue`. |
| Endereço de uma página | `src/router/index.ts` e a rota Flask de shell correspondente. |
| Conteúdo e comportamento da tela | `src/features/<feature>/pages/`. |
| Card, formulário ou detalhe do domínio | `src/features/<feature>/components/`. |
| URL, payload ou chamada da API | `api.ts` e `types.ts` da feature; conferir os schemas do backend. |
| Cores, fonte, raio e sombras comuns | `src/shared/styles/tokens.css`. |
| Grade e regras gerais de layout | `src/shared/styles/layout.css`. |
| Título e contagem da listagem | `ListHeader.vue`; a feature fornece o total e decide quando exibi-lo. |
| Estrutura dos cards de várias features | `RecordCard.vue` e seu carregamento em `CardGridSkeleton.vue`. |
| Controle básico usado em várias telas | Wrapper correspondente em `src/volt/`. |

Uma alteração compartilhada deve ser conferida em Eventos e Demandas. Uma diferença pontual pode ficar no componente da feature; uma variação repetida deve ganhar um contrato simples no componente comum. Evite acumular props para casos hipotéticos.

## 6. Passos para criar ou ampliar uma tela

1. Confira o contrato da API, os perfis e o que cada usuário pode ver ou alterar.
2. Localize a feature ou crie sua pasta quando for uma funcionalidade nova.
3. Defina os tipos e as chamadas em `types.ts` e `api.ts`, reutilizando [requestJson/requestPdf](src/shared/api/client.ts). O cliente comum trata sessão, CSRF e falhas; uploads usam FormData.
4. Monte a página com os componentes da seção 3 e controles Volt. Use os tokens existentes e as variações documentadas no padrão visual.
5. Mantenha consultas, estado e regras de apresentação perto da feature. Extraia somente quando existir responsabilidade ou reutilização clara.
6. Se for uma nova página, registre a rota Vue e a entrada Flask `/app/...`; acrescente o menu quando necessário. O Router usa base `/app/`, portanto a rota Vue `/eventos` corresponde à entrada Flask `/app/eventos`.
7. Preserve carregamento, vazio, falha, validação por campo, bloqueio durante envio e retorno de foco. Permissões visuais ajudam a interface; a autorização continua no backend.
8. Revise o diff, os consumidores e a correspondência com a API. Build, testes e navegador dependem de autorização explícita conforme AGENTS.md. Publicação segue o guia de servidor; fazer pull não gera assets.

## 7. Ao pedir uma tela para a IA

Use este roteiro, preenchendo o comportamento e os dados da feature:

> Leia `frontend/README.md` e `handbook/docs/padrao-visual.md`. Implemente a tela na feature correspondente, usando Eventos como referência de composição. Reutilize os controles Volt, os tokens e os componentes compartilhados. Em listagens com uma ação por card, use `CardGrid` e um card da feature composto com `RecordCard`; no carregamento, use `CardGridSkeleton` dentro de `RequestState`. Inclua os estados e a paginação necessários. Preserve contratos da API, acessibilidade, busy e foco. Extraia componentes quando houver responsabilidade clara ou reutilização real.

Informe também quais ações a tela oferece, quais campos exibe e quais regras mudam por estado ou permissão. A IA deve seguir o padrão existente e apresentar uma variação explícita quando o comportamento exigir outra composição.
