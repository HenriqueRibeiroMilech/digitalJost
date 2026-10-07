# Curso prático — Primeira feature moderna: Eventos

> Versão didática do `guia-primeira-feature-eventos.md`.
>
> **Objetivo deste material:** chegar ao mesmo resultado técnico e aos mesmos exemplos de código do guia original, mas entendendo como construir uma feature moderna do Digital JOST do início ao fim.
>
> Os blocos de implementação do guia original foram preservados. O que foi acrescentado são explicações, modelos mentais, perguntas de conferência e conexões entre as camadas.

## O que você deve saber ao terminar

Ao concluir Eventos, a meta não é apenas ter uma página funcionando. Você deve conseguir olhar para uma nova funcionalidade e responder sozinho:

1. Qual é o contrato da feature?
2. Quais dados entram e quais saem?
3. O que pertence ao Vue e o que pertence ao backend?
4. Quando criar um componente?
5. Quando uma regra pertence ao `service`?
6. Quando uma consulta pertence ao `repository`?
7. O que um `schema` valida?
8. Como a rota HTTP fica pequena?
9. Como o frontend troca um mock pela API sem reescrever os componentes?
10. Como sessão, permissão, CSRF e transação entram no fluxo?
11. Como a aplicação Vue convive com o Flask/Jinja e com o legado?
12. Como repetir o mesmo padrão na próxima feature sem copiar tudo cegamente?

Essa é a ideia central da arquitetura do Digital JOST: a **feature é a unidade principal de organização**. Em vez de espalhar uma funcionalidade entre pastas globais de controllers, models e views, colocamos as partes que mudam juntas perto umas das outras.

---

# Parte 0 — O mapa mental antes de programar

Antes de abrir o VS Code, guarde este fluxo:

```text
USUÁRIO
  ↓
EventsPage.vue
  ↓
EventForm.vue / EventCard.vue
  ↓
eventsApi
  ↓
requestJson
  ↓
HTTP /api/v1/events
  ↓
routes.py
  ↓
schemas.py valida os dados
  ↓
services.py executa o caso de uso
  ↓
repository.py acessa o banco
  ↓
SQL Server
```

Na volta, a resposta percorre o caminho contrário:

```text
SQL Server
  ↓
repository
  ↓
service
  ↓
route + schema de saída
  ↓
JSON
  ↓
eventsApi
  ↓
Vue Query
  ↓
EventsPage
  ↓
EventCard
```

Esse fluxo é mais importante que decorar qualquer biblioteca.

## A responsabilidade de cada camada em uma frase

| Parte | Pergunta que ela responde |
| --- | --- |
| `types.ts` | Qual é o formato dos dados no frontend? |
| `EventCard.vue` | Como um evento é exibido? |
| `EventForm.vue` | Como o usuário informa os dados de um evento? |
| `EventsPage.vue` | Como os componentes e os estados da tela trabalham juntos? |
| `api.ts` | De onde a feature obtém e envia dados? |
| `client.ts` | Como toda API moderna faz HTTP de forma consistente? |
| `schemas.py` | Quais dados HTTP são aceitos e devolvidos? |
| `routes.py` | Qual endpoint chama qual caso de uso? |
| `services.py` | Qual é a operação de negócio e sua transação? |
| `repository.py` | Como os dados são lidos ou gravados? |
| `platform/` | Quais mecanismos compartilhados sustentam as features? |

Uma boa regra para se orientar é:

```text
Vue não conhece SQL.
Repository não conhece Flask.
Service não conhece request.
Route não implementa regra de negócio.
Schema não decide permissão.
```

## O que é específico de Eventos e o que será reutilizado

**Específico de Eventos:**

- `EventCreate`, `EventOut`, `EventList`;
- regras de nome e descrição;
- SQL de `DJ_EVENTS`;
- `EventCard`;
- `EventForm`;
- `EventsPage`;
- permissão `events.read` / `events.create`.

**Reutilizável por outras features:**

- shell da aplicação;
- tokens visuais;
- componentes Volt;
- cliente HTTP;
- sessão;
- CSRF;
- mecanismo de permissões;
- composição da aplicação;
- padrão de erros;
- integração Vite/Flask/IIS.

Essa separação é o que faz a primeira feature valer como teste da arquitetura.

---

# Como estudar este curso

Em cada etapa faça três coisas:

1. **Entenda primeiro o papel da peça.**
2. **Escreva o código.**
3. **Explique com suas próprias palavras por que o arquivo existe.**

Se você só copiar e a feature funcionar, você terminou a implementação, mas não terminou o aprendizado.

Quando aparecer código de configuração, integração ou infraestrutura, entenda o suficiente para saber **por que ele é necessário e onde mexer depois**. Não é preciso memorizar detalhes que não pertencem à lógica cotidiana de uma feature.

---

# Primeira feature moderna: Eventos

**Data:** 5 de outubro de 2026

**Objetivo:** aprender a construir a primeira tela da arquitetura nova do Digital JOST.

**Ponto de partida:** preparação do frontend da antiga seção 17.4, parte 1, informada como concluída.

Vamos começar por uma entrega que você consegue acompanhar inteira: uma página de eventos, uma grade de cards e um modal para criar um evento com nome e descrição. Usaremos os componentes Volt para os controles, deixando no código da feature apenas a composição e o comportamento de Eventos. Ela será a entrada do futuro módulo de chamada. Quando a chamada for implementada, haverá um evento com identificador ao qual relacionar participantes e presenças.

Este guia é um roteiro de implementação, com exemplos para você escrever no projeto. Nesta tarefa foram alterados somente documentos. Nenhum exemplo foi executado. Os comandos de instalação, execução, build, teste, publicação ou alteração de banco continuam sujeitos às regras do [AGENTS.md](../AGENTS.md).

A [arquitetura principal](arquitetura-modernizacao.md) define o desenho. Aqui vamos percorrer esse desenho na ordem em que faz sentido aprender e construir.

## Como usar este guia

Leia uma etapa, escreva os arquivos indicados e confira a entrega esperada antes de seguir. Comece pela interface com dados fictícios. Depois prepare o ambiente isolado e implemente o cadastro real. Você pode estudar e escrever os arquivos como texto sem executar o Digital JOST.

| Etapa | Você vai aprender | Entrega |
| --- | --- | --- |
| [1](#1-primeiro-defina-o-que-a-tela-faz) | Delimitar uma feature | Escopo e contrato definidos. |
| [2](#2-aproveite-o-que-já-existe) | Organizar arquivos | Um lugar claro para cada responsabilidade. |
| [3](#3-comece-pelo-padrão-visual-do-digital-jost) | Definir o padrão visual | Tokens, shell, cards e formulário. |
| [4](#4-monte-a-primeira-versão-com-dados-fictícios) | Montar a tela Vue | Listagem e criação em memória. |
| [5](#5-prepare-o-ambiente-antes-do-cadastro-real) | Preparar o ambiente | Backend e banco isolados antes de executar. |
| [6](#6-construa-o-backend-de-dentro-para-fora) | Escrever schemas, SQL e serviço | Persistência com parâmetros e transação. |
| [7](#7-exponha-a-api-com-proteção-no-servidor) | Expor uma API protegida | GET, POST, sessão, permissões e CSRF. |
| [8](#8-troque-a-simulação-pela-api-real) | Consumir a API no Vue | HTTP e atualização da listagem. |
| [9](#9-prepare-assets-e-roteamento-para-o-iis) | Preparar a entrega | Assets e piloto no IIS. |
| [10](#10-confira-cada-camada) | Verificar a entrega | Casos e evidências por ambiente. |
| [11](#11-entenda-o-padrão-que-você-acabou-de-criar) | Reaproveitar o padrão | Próximas features e evolução para chamada. |


# Aula 1 — Comece pela feature, não pelo framework

Antes de pensar em Vue, Flask ou SQLAlchemy, transforme o pedido em comportamento observável.

Para Eventos, a história mínima é:

```text
abrir página
→ ver eventos
→ clicar em Novo evento
→ informar nome e descrição
→ salvar
→ ver o novo evento na listagem
```

Isso delimita o que realmente precisa existir.

## Por que fazemos isso antes do código?

Porque tecnologia não define requisito. Se você começa pelo banco ou pelo componente, é muito fácil inventar campos e funcionalidades “porque talvez sejam úteis”.

Aqui, por exemplo, chamada, presença, participantes, edição e exclusão **não existem ainda**. Portanto, não criamos botões, tabelas ou endpoints vazios para eles.

## Contrato é a fronteira da feature

Um contrato diz o que uma parte pode esperar da outra.

No frontend:

```ts
create({ name, description })
```

Na API:

```json
{
  "name": "...",
  "description": "..."
}
```

Na resposta:

```json
{
  "id": 1,
  "name": "...",
  "description": "..."
}
```

Perceba que `created_by` não vem do navegador. Isso é intencional: identidade confiável é responsabilidade do servidor.

### Exercício mental

Antes de continuar, tente responder sem olhar o código:

- O usuário pode escolher o `id`?
- O usuário pode mandar `created_by`?
- Onde fica a regra de 3 a 120 caracteres?
- O frontend pode esconder o botão e considerar isso uma permissão?

Se as respostas forem **não, não, frontend+backend, não**, o modelo está correto.


## 1. Primeiro, defina o que a tela faz

Imagine que o usuário abre **Eventos**, encontra os eventos já cadastrados e clica em **Novo evento**. Um modal abre sobre a página. Ele preenche os dois campos e salva. Depois da confirmação, o modal fecha e o novo evento aparece na listagem. Se o envio falhar, o modal permanece aberto com o texto digitado.

Nesta versão, os cards mostram nome e descrição como texto. Eles não precisam ser clicáveis: ainda não existe uma tela interna do evento. Não coloque botões de chamada, presença, edição ou exclusão que não tenham uma operação real por trás.

Adotaremos estas escolhas iniciais:

| Item | Escolha proposta |
| --- | --- |
| Nome técnico do módulo | `events`. |
| Título da página | Eventos. |
| URL da interface | `/app/eventos`. |
| URL da API | `/api/v1/events`. |
| Campos do formulário | Nome obrigatório; descrição obrigatória. |
| Nome | De 3 a 120 caracteres depois de remover espaços nas extremidades. |
| Descrição | De 1 a 2.000 caracteres depois da mesma normalização. |
| Nome repetido | Permitido nesta primeira versão. |
| Listagem | 12 cards por página; acesso a todos os eventos permitidos pela paginação. |
| Ordem | Identificador decrescente, exibindo os recém-criados primeiro. |
| Visibilidade inicial | Todos os eventos do módulo para quem possui `events.read`. |
| Criação | Somente para quem possui `events.create`. |

Os limites e a visibilidade são propostas deste guia, pois o pedido ainda não definiu esses detalhes. Confirme-os antes da implementação real. Se houver restrição por setor ou organizador, defina essa regra antes de abrir o cadastro: esconder cards no navegador não protege os registros.

Você só pede nome e descrição ao usuário. O sistema acrescenta identificador, autor e instante de criação, que são metadados técnicos. Não adicione campos de participantes ou datas do evento para tentar antecipar as próximas versões.

### Desenhe o contrato antes dos arquivos

Ao listar, a API deverá devolver:

```json
{
  "items": [
    {
      "id": 1,
      "name": "Encontro de integração",
      "description": "Apresentação das rotinas para a equipe."
    }
  ],
  "page": 1,
  "per_page": 12,
  "total": 1,
  "capabilities": {
    "can_create": true
  }
}
```

Ao criar, o navegador enviará somente:

```json
{
  "name": "Encontro de integração",
  "description": "Apresentação das rotinas para a equipe."
}
```

A resposta será `201` com `id`, `name` e `description`. O `can_create` da listagem orienta a interface e é calculado pelo servidor. O POST continua verificando a permissão independentemente do botão.

**Confira antes de seguir:** você consegue descrever o comportamento sem mencionar uma biblioteca? Se sim, o escopo está suficientemente claro para começar.


# Aula 2 — Leia a base antes de criar arquivos

Em um projeto real, desenvolver não começa com `npm install`.

Primeiro você descobre:

```text
o que já existe
→ o que já está configurado
→ o que falta
→ o que você realmente precisa alterar
```

No Digital JOST isso é especialmente importante porque estamos modernizando sem reescrever o sistema inteiro.

## Por que não recriar o frontend?

Porque a arquitetura é incremental. O Vue já foi preparado. Recriar `frontend/` seria:

- perder decisões já feitas;
- gerar diff desnecessário;
- aumentar risco;
- dificultar comparar o que realmente pertence a Eventos.

## Como pensar nos componentes Volt

Use duas camadas:

```text
Volt / PrimeVue
    ↓
componente genérico de interface
    ↓
EventCard / EventForm
    ↓
componente do domínio Eventos
```

`Card.vue` sabe ser um card.

`EventCard.vue` sabe mostrar **um evento**.

Não altere `Card.vue` para colocar regras específicas de evento. Essa é uma das ideias mais importantes para as próximas features.


## 2. Aproveite o que já existe

Na leitura estática deste repositório, encontrei:

- Vue, TypeScript, Vue Router, Tailwind e Vue Query declarados em `frontend/package.json`.
- PrimeVue configurado com `unstyled: true` e Vue Query registrado em `src/main.ts`.
- `src/volt/Button.vue` e `InputText.vue` já gerados.
- `src/App.vue` ainda com o conteúdo inicial “You did it!”.
- `src/router/index.ts` com a lista de rotas vazia.
- `src/assets/main.css` com os imports de Tailwind e `tailwindcss-primeui`.
- APIFlask, Pydantic e Pydantic Settings declarados em `requirements.txt`.
- A factory ainda cria uma instância de Flask e chama `db.create_all()`.

Essa leitura confirma arquivos e declarações, não confirma instalação ou funcionamento. Não recrie o projeto Vue nem reinstale tudo para continuar o tutorial.

Há um ajuste de dependência a planejar: a arquitetura exige `tailwindcss-primeui: "0.6.1"`, mas o manifesto examinado usa `"^0.6.1"`. O lockfile examinado já resolve `0.6.1`. Na etapa autorizada de dependências, fixe essa versão e atualize o lockfile de forma controlada; não edite o lockfile manualmente. Preserve `primevue: "4.5.5"` e `primeicons: "7.0.0"`.

### 2.1 Escolha os componentes e preserve a versão gratuita

Volt copia componentes para `src/volt/`. Eles envolvem os controles PrimeVue em modo unstyled e aplicam Tailwind. Você passa a compor esses controles em cada feature; não precisa recriar modal, paginação ou campo de descrição. Esse é o modelo de [propriedade do código do Volt](https://volt.primevue.org/overview/).

Para esta entrega, use:

| Componente | Papel em Eventos | Situação |
| --- | --- | --- |
| `Button` | Abrir cadastro, salvar, cancelar e tentar novamente. | Já existe; preservar. |
| `InputText` | Nome do evento. | Já existe; preservar. |
| `Card` | Estrutura visual de cada evento. | Adicionar. |
| `Textarea` | Descrição com várias linhas. | Adicionar. |
| `Dialog` | Modal de cadastro, máscara e gestão de foco. | Adicionar. |
| `Message` | Erros de validação, falhas e confirmação. | Adicionar. |
| `Skeleton` | Espaços visuais durante o carregamento. | Adicionar. |
| `Paginator` | Controles da listagem paginada. | Adicionar. |
| `SecondaryButton` | Controle auxiliar usado pelo `Dialog` consultado. | Adicionar se não vier junto; conferir os imports. |

**Conferência em 5 de outubro de 2026:** o pacote da tag `4.5.5` exporta todos os controles PrimeVue usados aqui. As APIs empregadas nos exemplos, incluindo `visible`, `modal`, `closable`, `closeOnEscape`, `after-hide`, `autoResize`, `invalid` e paginação por `first`/`rows`/`totalRecords`, foram conferidas estaticamente nessa versão. Consulte o [manifesto da versão 4.5.5](https://github.com/primefaces/primevue/blob/4.5.5/packages/primevue/package.json), o [Dialog nessa versão](https://github.com/primefaces/primevue/blob/4.5.5/packages/primevue/src/dialog/Dialog.vue), o [Textarea nessa versão](https://github.com/primefaces/primevue/blob/4.5.5/packages/primevue/src/textarea/Textarea.vue) e o [Paginator nessa versão](https://github.com/primefaces/primevue/blob/4.5.5/packages/primevue/src/paginator/Paginator.vue).

O PrimeVue **4.5.5 usa licença MIT**, permitindo uso comercial sem compra de licença ou chave de ativação, desde que sejam mantidos os avisos de copyright e licença exigidos. Ele tem uma licença de código aberto; “gratuito” não significa ausência de licença. A [licença da tag 4.5.5](https://github.com/primefaces/primevue/blob/4.5.5/LICENSE.md) é a referência para a versão adotada. O código Volt consultado pertence ao mesmo [repositório com licença MIT](https://github.com/primefaces/primevue/blob/master/LICENSE.md). PrimeIcons 7 também tem [licença MIT](https://github.com/primefaces/primeicons/blob/7.0.0/LICENSE), e o lockfile local registra MIT para `tailwindcss-primeui@0.6.1`.

Os exemplos não dependem de templates, blocos ou ferramentas comerciais. Preserve a combinação definida na arquitetura: PrimeVue `4.5.5`, PrimeIcons `7.0.0`, `tailwindcss-primeui` `0.6.1`, Tailwind 4 e Vue 3. Não acrescente um gerenciador de licença ou mude a versão principal para baixar esses componentes.

### 2.2 Como baixar os componentes que faltam

Na futura etapa autorizada de dependências, abra o terminal na raiz do projeto e entre em `frontend`. Estes são comandos para você usar nessa etapa; não foram executados nesta tarefa:

```powershell
Set-Location frontend
npx volt-vue@0.0.0-alpha.4 add Card
npx volt-vue@0.0.0-alpha.4 add Textarea
npx volt-vue@0.0.0-alpha.4 add Message
npx volt-vue@0.0.0-alpha.4 add Skeleton
npx volt-vue@0.0.0-alpha.4 add Paginator
npx volt-vue@0.0.0-alpha.4 add Dialog
```

A sintaxe `add NomeDoComponente` está nas páginas oficiais de [Card](https://volt.primevue.org/card/), [Textarea](https://volt.primevue.org/textarea/), [Message](https://volt.primevue.org/message/), [Skeleton](https://volt.primevue.org/skeleton/), [Paginator](https://volt.primevue.org/paginator/) e [Dialog](https://volt.primevue.org/dialog/). Aqui fixamos a versão da CLI prevista na arquitetura em vez de deixar `npx` escolher outra versão.

Após adicionar `Dialog`, leia seus imports. A implementação oficial consultada importa `./SecondaryButton.vue`. Se esse arquivo ainda não existir e a CLI não o tiver incluído, adicione-o também:

```powershell
npx volt-vue@0.0.0-alpha.4 add SecondaryButton
```

Não gere novamente `Button`, `InputText` ou `utils.ts` nem aceite sobrescrevê-los sem comparar o conteúdo. Dependências auxiliares só entram quando um import realmente exigir. Não é necessário instalar um pacote separado para cada controle: a base já é o PrimeVue e os arquivos Volt ficam no código do projeto.

**Fixar a CLI não fixa necessariamente a revisão dos arquivos que ela baixa.** A compatibilidade das APIs com PrimeVue 4.5.5 foi conferida; o resultado futuro de cada download ainda precisa ser lido antes de entrar no projeto. Depois de adicionar, confira como texto:

1. Os arquivos estão em `frontend/src/volt/`, com imports resolvidos e sem exigir PrimeVue 5.
2. `package.json` e `package-lock.json` preservam as versões aprovadas e não receberam dependências de licença comercial.
3. Os componentes continuam usando `unstyled`, Pass Through e o helper local `ptViewMerge`.
4. O botão de fechar do `Dialog` tem nome acessível. Se o arquivo Volt definir um slot `closebutton` com `SecondaryButton` sem label, acrescente `aria-label="Fechar cadastro"` nesse botão; a configuração de botão do PrimeVue pode ser substituída pelo slot.
5. A origem, a revisão de origem quando disponível e a licença dos arquivos copiados foram registradas, por exemplo em `frontend/src/volt/README.md`, preservando os avisos exigidos pela MIT.

Se o download produzir um wrapper que depende de API posterior, use uma revisão compatível do componente ou adapte o wrapper às APIs 4.5.5 verificadas. Não atualize a base para resolver isso automaticamente. Os downloads e a compatibilidade em execução não foram testados nesta tarefa.

Na raiz do repositório, esta comparação textual ajuda a revisar o resultado:

```powershell
git diff -- frontend/package.json frontend/package-lock.json frontend/src/volt
git status --short -- frontend
```

O diff não mostra o conteúdo de arquivos novos ainda não rastreados: abra também cada `.vue` adicionado como texto. A CLI entrega a base de apresentação; nós vamos escrever os tipos, os eventos emitidos e as chamadas à API nas pastas da feature.

### Crie a estrutura conforme for escrevendo

```text
app/
├── modules/
│   ├── __init__.py
│   └── events/
│       ├── __init__.py
│       ├── routes.py
│       ├── schemas.py
│       ├── services.py
│       └── repository.py
└── platform/
    ├── auth/                    # identidade resolvida no servidor
    ├── permissions/             # mecanismo usado pelo módulo
    ├── database/                # conexão configurada por ambiente
    └── errors/                  # erros da API

frontend/src/
├── App.vue                      # ponto de montagem
├── main.ts                      # bootstrap existente
├── router/index.ts              # mantenha o caminho atual nesta entrega
├── app/
│   ├── layouts/AppShell.vue
│   └── pages/NotFoundPage.vue
├── assets/main.css              # ponto de entrada CSS existente
├── shared/
│   ├── styles/tokens.css
│   └── api/client.ts
├── features/events/
│   ├── types.ts
│   ├── api.ts
│   ├── mock-api.ts
│   ├── components/EventCard.vue
│   ├── components/EventForm.vue
│   └── pages/EventsPage.vue
└── volt/                        # componentes existentes e os adicionados na etapa 2.2
```

A árvore é um destino de arquivos reais; não crie pastas vazias. O roteador fica no caminho atual para evitar uma movimentação sem necessidade. `AppShell` vai para `app/` porque define a estrutura global. `EventCard` fica em `features/events/` porque representa um evento.

No backend, `routes.py` fala HTTP, `schemas.py` define os dados, `services.py` coordena a operação e `repository.py` fala SQL. Vamos usar SQLAlchemy Core com SQL parametrizado neste exemplo, então não precisamos de `models.py`. Se você escolher ORM, faça essa escolha no repositório e acrescente o modelo, preservando o mesmo contrato público.

**Confira antes de seguir:** cada arquivo tem uma responsabilidade que você consegue explicar em uma frase. Não crie `domain.py`, `integrations.py` ou jobs enquanto a feature não precisar deles.


# Aula 3 — Tailwind e componentes sem transformar CSS em bagunça

Nesta etapa existem três conceitos diferentes:

```text
token visual
→ decisão de design reutilizável

classe Tailwind
→ forma de aplicar essa decisão

componente Vue
→ composição visual + comportamento
```

Exemplo:

```css
--color-dj-brand: #163a8a;
```

Esse token significa “azul principal do Digital JOST”.

Depois:

```html
<header class="bg-dj-brand">
```

O componente não precisa decorar `#163a8a`.

## Por que isso importa?

Imagine trocar o azul no futuro. Com token, a mudança acontece em um ponto. Sem token, você procura dezenas de hexadecimais espalhados.

## `AppShell` versus `EventsPage`

Pense assim:

```text
AppShell
└── estrutura comum da aplicação moderna
    └── RouterView
        └── EventsPage
```

O cabeçalho “Digital JOST” não pertence a Eventos. Por isso fica no shell.

Já o título “Eventos” pertence à feature. Por isso fica na página.

## `EventCard` é um ótimo exemplo de composição

O componente recebe:

```ts
{ event: EventItem }
```

e somente transforma esses dados em interface.

Ele não sabe:

- qual endpoint existe;
- qual banco existe;
- quem é o usuário;
- se o evento veio de mock ou SQL Server.

Quando um componente fica assim, ele é fácil de entender e testar.


## 3. Comece pelo padrão visual do Digital JOST

Vamos usar uma direção visual industrial e sóbria: cabeçalho azul, conteúdo sobre uma superfície clara, ações bem destacadas e pouco ruído. O CSS legado já usa azul `#163A8A`, laranja `#EF7B04` e a família Montserrat. Isso serve como referência da identidade existente, não como aprovação de um manual de marca.

O azul será a cor de ação principal. O laranja fica em pequenos destaques da identidade; não o use como fundo de todo botão com texto branco sem avaliar contraste. Para a primeira versão, concentre-se no tema claro.

| Elemento | Regra inicial |
| --- | --- |
| Conteúdo | Largura máxima de 1.200 px, centralizado. |
| Espaçamento | Escala de 4, 8, 12, 16, 24 e 32 px. |
| Cabeçalho | Identidade Digital JOST e retorno ao portal atual. |
| Título | 28–32 px, peso 600, um `h1` por página. |
| Texto | 14–16 px; cinza escuro; linhas confortáveis. |
| Cards | Fundo branco, borda discreta, raio de 12 px, sem sombra pesada. |
| Grade | Uma coluna no celular, duas no tablet, três em telas maiores. |
| Ação principal | “Novo evento”, ícone de adição e foco visível. |
| Formulário | Modal com título, labels visíveis e erro junto do campo. |
| Modal | Até 576 px de largura; cabe no celular; Cancelar e fechar por teclado. |
| Movimento | Transições curtas; respeitar redução de movimento. |

### 3.1 Escreva os tokens

Crie `frontend/src/shared/styles/tokens.css`. Um token é um nome para uma decisão visual: você escolhe a cor uma vez e usa esse nome em toda a interface.

```css
@theme {
  --font-sans: "Montserrat", "Segoe UI", sans-serif;
  --color-dj-brand: #163a8a;
  --color-dj-accent: #ef7b04;
  --color-dj-canvas: #f4f6fa;
  --color-dj-ink: #182337;
  --color-dj-muted: #526078;
  --color-dj-border: #d7dfea;
  --color-dj-danger: #b42318;

  --color-primary: #163a8a;
  --color-primary-emphasis: #123174;
  --color-primary-emphasis-alt: #0e285f;
  --color-primary-contrast: #ffffff;
  --color-primary-50: #eef3fc;
  --color-primary-100: #dce6f8;
  --color-primary-200: #b9cdee;
  --color-primary-300: #92aee2;
  --color-primary-400: #6688ca;
  --color-primary-500: #4166b2;
  --color-primary-600: #285099;
  --color-primary-700: #163a8a;
  --color-primary-800: #123174;
  --color-primary-900: #0e285f;
  --color-primary-950: #081937;

  --color-surface-0: #ffffff;
  --color-surface-50: #f8fafc;
  --color-surface-100: #f1f5f9;
  --color-surface-200: #e2e8f0;
  --color-surface-300: #cbd5e1;
  --color-surface-400: #94a3b8;
  --color-surface-500: #64748b;
  --color-surface-600: #475569;
  --color-surface-700: #334155;
  --color-surface-800: #1e293b;
  --color-surface-900: #0f172a;
  --color-surface-950: #020617;
}

body {
  margin: 0;
  background: var(--color-dj-canvas);
  color: var(--color-dj-ink);
  font-family: var(--font-sans);
}

:focus-visible {
  outline: 2px solid var(--color-dj-brand);
  outline-offset: 3px;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

Os nomes `primary` e `surface` também aparecem nos componentes Volt que você já gerou. Defini-los evita depender de um tema visual instalado separadamente. Mantenha esses tokens depois do import da integração PrimeUI.

No `src/assets/main.css`, preserve os imports e acrescente:

```css
@import "tailwindcss";
@import "tailwindcss-primeui";
@import "../shared/styles/tokens.css";
```

Agora classes como `bg-dj-canvas`, `text-dj-muted` e `border-dj-border` têm significado comum no projeto. A diretiva `@theme` é o mecanismo do Tailwind 4 para declarar valores que geram utilitários. [Referência oficial](https://tailwindcss.com/docs/theme).

Se Montserrat não estiver disponível no frontend novo, use o fallback enquanto prepara uma fonte local aprovada e um `@font-face`. Declarar a família não baixa a fonte. Não acrescente uma dependência de Google Fonts para resolver essa etapa.

### 3.2 Escreva o shell

Crie `frontend/src/app/layouts/AppShell.vue`:

```vue
<template>
  <div class="min-h-screen bg-dj-canvas">
    <header class="bg-dj-brand text-white">
      <div class="mx-auto flex max-w-[1200px] items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <span class="border-l-4 border-dj-accent pl-3 text-lg font-semibold">
          Digital JOST
        </span>
        <a href="/" class="rounded px-2 py-1 text-sm underline underline-offset-4">
          Voltar ao portal
        </a>
      </div>
    </header>
    <main class="mx-auto max-w-[1200px] px-4 py-8 sm:px-6">
      <slot />
    </main>
  </div>
</template>
```

O `slot` é o espaço em que entra a página. Na próxima feature, você reaproveita o mesmo cabeçalho e a mesma largura. Em produção, use a URL do portal resolvida pelo Flask se ele estiver hospedado sob um prefixo; `/` é a proposta para a hospedagem na raiz. O shell não deve receber identidade fictícia ou permissões fixas.

### 3.3 Defina os tipos e o card

Crie `frontend/src/features/events/types.ts`:

```ts
export interface EventItem {
  id: number
  name: string
  description: string
}

export interface EventCreate {
  name: string
  description: string
}

export interface EventList {
  items: EventItem[]
  page: number
  per_page: number
  total: number
  capabilities: { can_create: boolean }
}

export interface EventsApi {
  list(page: number, perPage: number): Promise<EventList>
  create(payload: EventCreate): Promise<EventItem>
}
```

Crie `frontend/src/features/events/components/EventCard.vue`:

```vue
<script setup lang="ts">
import Card from '@/volt/Card.vue'
import type { EventItem } from '../types'
defineProps<{ event: EventItem }>()
</script>

<template>
  <article :aria-labelledby="'event-title-' + event.id">
    <Card pt:root:class="h-full border border-dj-border shadow-none" pt:body:class="p-6">
      <template #title>
        <h2 :id="'event-title-' + event.id" class="break-words text-lg font-semibold text-dj-ink">
          {{ event.name }}
        </h2>
      </template>
      <template #content>
        <p class="whitespace-pre-wrap break-words text-sm leading-6 text-dj-muted">
          {{ event.description }}
        </p>
      </template>
    </Card>
  </article>
</template>
```

`EventCard` compõe o `Card` da biblioteca com os campos de um evento. Os slots `title` e `content` recebem o conteúdo; `pt:root:class` e `pt:body:class` ajustam partes internas pelo Pass Through, com a mesclagem do Volt, para retirar a sombra e aplicar nosso espaçamento. Isso evita duplicar a estrutura visual ou mudar o `Card.vue` compartilhado por uma necessidade específica. [Card](https://volt.primevue.org/card/) e [personalização do Volt](https://volt.primevue.org/overview/).

A interpolação do Vue mostra o conteúdo como texto. Não use `v-html` para a descrição. Neste início, mostre a descrição inteira; se a experiência pedir um resumo depois, defina uma ação real para ler o restante antes de cortar informação.

**Confira antes de seguir:** o card sabe exibir um evento, mas não sabe consultar uma API, salvar no banco ou verificar permissões. Essa separação é intencional.


# Aula 4 — Aprenda o frontend antes de misturar o banco

Esta é uma decisão pedagógica e arquitetural importante.

Vamos separar dois problemas:

```text
Problema A: a tela funciona?
Problema B: a integração real funciona?
```

Primeiro resolvemos A com mock.

Depois trocamos a fonte dos dados e resolvemos B.

Isso reduz muito a quantidade de coisas que você precisa depurar ao mesmo tempo.

## Os conceitos de Vue que aparecem aqui

### `ref`

Use quando temos um valor reativo simples:

```ts
const page = ref(1)
const showForm = ref(false)
```

Você altera no script com:

```ts
page.value = 2
```

No template, o Vue desempacota automaticamente.

### `reactive`

É útil para um objeto cujo conteúdo muda:

```ts
const fields = reactive({
  name: '',
  description: '',
})
```

### `props`

Dados que entram no componente:

```ts
defineProps<{ busy: boolean }>()
```

Mentalmente:

```text
pai → prop → filho
```

### `emit`

Evento que sai do componente:

```ts
emit('submit', payload)
```

Mentalmente:

```text
filho → evento → pai
```

Isso explica a relação:

```text
EventsPage
  ↓ props
EventForm
  ↑ submit/cancel
```

## Por que `EventForm` não chama a API?

Porque formulário e persistência são responsabilidades diferentes.

Se o formulário chamasse `fetch` diretamente:

- ficaria acoplado à API;
- seria mais difícil usar mock;
- a página perderia controle sobre modal e feedback;
- tratamento de sucesso/erro ficaria espalhado.

Por isso ele apenas diz:

> “os dados são estes; alguém acima decide o que fazer”.

## O papel do adaptador

`EventsApi` cria uma interface comum:

```ts
list(...)
create(...)
```

O restante da aplicação não precisa saber se a implementação é:

```text
mockEventsApi
ou
realEventsApi
```

Esse é um padrão extremamente útil.

A tela programa contra o **contrato**, não contra a implementação.

## Vue Query em uma frase

Vue Query gerencia **estado vindo do servidor**.

Aqui temos:

```text
useQuery    → leitura/listagem
useMutation → alteração/criação
```

Depois de criar:

```ts
invalidateQueries(...)
```

significa:

> “os dados de eventos podem ter ficado desatualizados; carregue novamente”.

Isso é diferente de guardar uma lista global manualmente e tentar sincronizá-la em toda tela.


## 4. Monte a primeira versão com dados fictícios

Vamos fazer a tela funcionar sem banco. Isso permite aprender componentes, estado e formulário sem misturar os problemas de integração.

### 4.1 Escreva o formulário

Crie `frontend/src/features/events/components/EventForm.vue`:

```vue
<script setup lang="ts">
import { reactive, ref } from 'vue'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Message from '@/volt/Message.vue'
import Textarea from '@/volt/Textarea.vue'
import type { EventCreate } from '../types'

const props = defineProps<{ busy: boolean; serverError: string }>()
const emit = defineEmits<{
  submit: [payload: EventCreate]
  cancel: []
}>()
const fields = reactive({ name: '', description: '' })
const errors = reactive({ name: '', description: '' })
const formElement = ref<HTMLFormElement | null>(null)

function submit() {
  if (props.busy) return
  const payload = {
    name: fields.name.trim(),
    description: fields.description.trim(),
  }
  errors.name = payload.name.length < 3 || payload.name.length > 120
    ? 'Informe um nome entre 3 e 120 caracteres.' : ''
  errors.description = payload.description.length < 1 || payload.description.length > 2000
    ? 'Informe uma descrição entre 1 e 2.000 caracteres.' : ''
  if (errors.name || errors.description) {
    const invalidId = errors.name ? 'event-name' : 'event-description'
    formElement.value?.querySelector<HTMLElement>('#' + invalidId)?.focus()
    return
  }
  emit('submit', payload)
}
</script>

<template>
  <form ref="formElement" novalidate :aria-busy="busy" @submit.prevent="submit">
    <p id="event-form-help" class="text-sm text-dj-muted">
      Comece pelo nome e pela descrição do evento.
    </p>

    <div class="mt-6">
      <label for="event-name" class="mb-2 block text-sm font-medium">Nome</label>
      <InputText id="event-name" v-model="fields.name" class="w-full"
        autofocus required :maxlength="120" :invalid="Boolean(errors.name)" :disabled="busy"
        :aria-invalid="Boolean(errors.name)"
        :aria-describedby="errors.name ? 'event-name-error' : undefined" />
      <Message v-if="errors.name" id="event-name-error" severity="error" variant="simple"
        size="small" class="mt-2">{{ errors.name }}</Message>
    </div>

    <div class="mt-4">
      <label for="event-description" class="mb-2 block text-sm font-medium">Descrição</label>
      <Textarea id="event-description" v-model="fields.description" :rows="4" auto-resize
        required :maxlength="2000" :invalid="Boolean(errors.description)" :disabled="busy"
        :aria-invalid="Boolean(errors.description)"
        :aria-describedby="errors.description ? 'event-description-error' : undefined"
        class="w-full" />
      <Message v-if="errors.description" id="event-description-error" severity="error"
        variant="simple" size="small" class="mt-2">{{ errors.description }}</Message>
    </div>

    <Message v-if="serverError" severity="error" class="mt-4">
      {{ serverError }}
    </Message>
    <div class="mt-6 flex flex-wrap gap-3">
      <Button type="submit" :label="busy ? 'Salvando…' : 'Criar evento'"
        :loading="busy" :disabled="busy" />
      <Button type="button" label="Cancelar" outlined :disabled="busy" @click="emit('cancel')" />
    </div>
  </form>
</template>
```

O formulário mantém os campos e os erros locais. Ao salvar, emite um objeto normalizado; quem decide como persistir é a página. Em falha do servidor, ele continua montado com o texto digitado. `Textarea` fornece o campo multilinha e `Message` padroniza os erros. O `autofocus` do nome indica ao `Dialog` o campo inicial. O título “Novo evento” será fornecido pelo modal, evitando repetir um cabeçalho dentro do formulário.

O `v-model` conecta campo e estado. O `@submit.prevent` intercepta o envio HTML para que a página cuide da operação. [Referência do Vue sobre formulários](https://vuejs.org/guide/essentials/forms.html). Os tipos de props e eventos são declarados no `script setup`. [Referência de TypeScript](https://vuejs.org/guide/typescript/composition-api.html).

### 4.2 Crie o adaptador simulado

Crie `frontend/src/features/events/mock-api.ts`:

```ts
import type { EventItem, EventsApi } from './types'

let nextId = 3
const events: EventItem[] = [
  { id: 2, name: 'Encontro de integração', description: 'Apresentação das rotinas da equipe.' },
  { id: 1, name: 'Oficina de melhoria', description: 'Discussão de oportunidades no processo.' },
]

export const mockEventsApi: EventsApi = {
  async list(page, perPage) {
    const start = (page - 1) * perPage
    return {
      items: events.slice(start, start + perPage).map(event => ({ ...event })),
      page,
      per_page: perPage,
      total: events.length,
      capabilities: { can_create: true },
    }
  },
  async create(payload) {
    const event = { id: nextId++, ...payload }
    events.unshift(event)
    return { ...event }
  },
}
```

Esse contador só existe na simulação. No banco real o identificador será gerado pelo SQL Server. A simulação perde os cadastros ao recarregar e não usa dados de funcionários.

### 4.3 Escolha o adaptador por configuração de desenvolvimento

Crie `frontend/src/features/events/api.ts` inicialmente assim:

```ts
import type { EventsApi } from './types'

async function adapter(): Promise<EventsApi> {
  if (import.meta.env.DEV && import.meta.env.VITE_EVENTS_MOCK === 'true') {
    return (await import('./mock-api')).mockEventsApi
  }
  throw new Error('O adaptador real de Eventos ainda precisa ser implementado.')
}

export const eventsApi: EventsApi = {
  async list(page, perPage) {
    return (await adapter()).list(page, perPage)
  },
  async create(payload) {
    return (await adapter()).create(payload)
  },
}
```

Na futura execução autorizada do frontend isolado, use `VITE_EVENTS_MOCK=true` no arquivo local de configuração de desenvolvimento. Variáveis com prefixo `VITE_` são públicas no navegador: nunca coloque credenciais nelas. A simulação depende de `DEV`, não de query string. A etapa 8 substituirá o erro pelo adaptador real.

### 4.4 Monte a página

Crie `frontend/src/features/events/pages/EventsPage.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import Button from '@/volt/Button.vue'
import Dialog from '@/volt/Dialog.vue'
import Message from '@/volt/Message.vue'
import Paginator from '@/volt/Paginator.vue'
import Skeleton from '@/volt/Skeleton.vue'
import EventCard from '../components/EventCard.vue'
import EventForm from '../components/EventForm.vue'
import { eventsApi } from '../api'
import type { EventCreate } from '../types'

const page = ref(1)
const perPage = 12
const showForm = ref(false)
const feedback = ref('')
const submitError = ref('')
const newEventAction = ref<HTMLElement | null>(null)
const queryClient = useQueryClient()
const { data, isPending: loading, isError, refetch } = useQuery({
  queryKey: ['events', page],
  queryFn: () => eventsApi.list(page.value, perPage),
  retry: false,
})
const { mutateAsync, isPending: saving } = useMutation({
  mutationFn: eventsApi.create,
  retry: false,
})

function openForm() {
  feedback.value = ''
  submitError.value = ''
  showForm.value = true
}

function updateDialogVisibility(visible: boolean) {
  if (saving.value) return
  showForm.value = visible
}

function closeForm() {
  updateDialogVisibility(false)
}

function restoreFocus() {
  newEventAction.value?.querySelector('button')?.focus()
}

function changePage(event: { page: number }) {
  // O Paginator começa em zero; a API começa em um.
  page.value = event.page + 1
}

async function createEvent(payload: EventCreate) {
  if (saving.value) return
  submitError.value = ''
  try {
    await mutateAsync(payload)
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : 'Não foi possível criar o evento.'
    return
  }
  // A gravação terminou. Uma falha posterior ao listar não transforma o POST em falha.
  feedback.value = 'Evento criado com sucesso.'
  page.value = 1
  showForm.value = false
  await queryClient.invalidateQueries({ queryKey: ['events'] })
}
</script>

<template>
  <section aria-labelledby="events-title">
    <div class="mb-8 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 id="events-title" class="text-3xl font-semibold">Eventos</h1>
        <p class="mt-2 text-dj-muted">Organize os eventos do Digital JOST.</p>
      </div>
      <div v-if="data?.capabilities.can_create" ref="newEventAction">
        <Button type="button" label="Novo evento" icon="pi pi-plus"
          :disabled="showForm" @click="openForm" />
      </div>
    </div>

    <Message v-if="feedback" severity="success" role="status" aria-live="polite" class="mb-6">
      {{ feedback }}
    </Message>

    <div v-if="loading" aria-busy="true">
      <p role="status" class="sr-only">Carregando eventos…</p>
      <div aria-hidden="true" class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        <div v-for="index in 6" :key="index" class="rounded-xl border border-dj-border bg-white p-6">
          <Skeleton width="70%" height="1.5rem" />
          <Skeleton width="100%" height="4.5rem" class="mt-4" />
        </div>
      </div>
    </div>
    <div v-else-if="isError">
      <Message severity="error" class="mb-4">Não foi possível carregar os eventos.</Message>
      <Button type="button" label="Tentar novamente" outlined @click="refetch()" />
    </div>
    <div v-else-if="data?.items.length === 0" class="rounded-xl border border-dj-border bg-white p-8">
      <h2 class="text-lg font-semibold">Nenhum evento cadastrado</h2>
      <p class="mt-2 text-dj-muted">Os eventos aparecerão aqui quando forem criados.</p>
    </div>
    <div v-else class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
      <EventCard v-for="event in data?.items ?? []" :key="event.id" :event="event" />
    </div>

    <nav v-if="!loading && !isError && data && data.total > perPage"
      aria-label="Páginas de eventos" class="mt-8">
      <Paginator :first="(page - 1) * perPage" :rows="perPage" :total-records="data.total"
        @page="changePage" />
    </nav>

    <Dialog :visible="showForm" header="Novo evento" modal :draggable="false"
      :closable="!saving" :close-on-escape="!saving" :dismissable-mask="false"
      :style="{ width: '36rem', maxWidth: 'calc(100vw - 2rem)' }"
      aria-describedby="event-form-help"
      @update:visible="updateDialogVisibility" @after-hide="restoreFocus">
      <EventForm v-if="showForm" :busy="saving" :server-error="submitError"
        @submit="createEvent" @cancel="closeForm" />
    </Dialog>
  </section>
</template>
```

Repare nos estados: a query cuida da listagem e a mutation cuida do cadastro. O POST tem retentativa automática desligada. Depois da criação, invalidamos o cache de eventos para buscar a lista atualizada. Essa abordagem corresponde ao modelo de mutations do [Vue Query](https://tanstack.com/query/v5/docs/framework/vue/guides/mutations). O `page` entra como ref na chave da query para que a troca de página provoque uma nova consulta. [Referência de reatividade](https://tanstack.com/query/v5/docs/framework/vue/reactivity).

O `Dialog` cuida da máscara, do foco dentro do modal e da semântica de diálogo. Nós controlamos quando ele abre e fecha. Cancelar, o botão de fechar e Escape ficam bloqueados durante a gravação; clicar na máscara não fecha o cadastro. Em erro, preservamos `showForm` e os campos. Em sucesso, fechamos, confirmamos na página e renovamos a listagem. Ao terminar a animação de fechamento, `after-hide` devolve o foco ao botão “Novo evento”. Ao cancelar e abrir novamente, o formulário começa vazio. [Dialog do Volt](https://volt.primevue.org/dialog/) e [implementação PrimeVue 4.5.5](https://github.com/primefaces/primevue/blob/4.5.5/packages/primevue/src/dialog/Dialog.vue).

`Skeleton` representa o carregamento e `Message` padroniza a comunicação. `Paginator` recebe o total do servidor; `first` é o índice do primeiro item, e o evento `page` usa páginas começando em zero. Convertemos esse índice para o contrato da API, que começa em um. Mantemos 12 itens por página, sem seletor de quantidade nesta versão. [Paginator do Volt](https://volt.primevue.org/paginator/).

Se o POST sofrer timeout, a gravação pode ter ocorrido. Na API real, mostre uma mensagem orientando conferir a listagem antes de tentar novamente. O botão desabilitado evita cliques repetidos na tela, mas não garante idempotência no servidor. Não prometa que retentar sempre é seguro.

### 4.5 Conecte o roteador e o App

No roteador existente, registre a página e o comportamento da raiz:

```ts
import { createRouter, createWebHistory } from 'vue-router'

export default createRouter({
  history: createWebHistory('/app/'),
  routes: [
    { path: '/', redirect: '/eventos' },
    {
      path: '/eventos',
      name: 'events',
      component: () => import('@/features/events/pages/EventsPage.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      component: () => import('@/app/pages/NotFoundPage.vue'),
    },
  ],
})
```

Crie `frontend/src/app/pages/NotFoundPage.vue`:

```vue
<template>
  <section>
    <h1 class="text-3xl font-semibold">Página não encontrada</h1>
    <RouterLink to="/eventos" class="mt-4 inline-block text-primary underline">
      Voltar para Eventos
    </RouterLink>
  </section>
</template>
```

Esse redirecionamento interno não troca a home Flask. Com a base `/app/`, a raiz do Vue é `/app/`, enquanto `/` continua sendo o portal atual. Para a futura execução do frontend simulado, ajuste também `base: '/app/'` no Vite atual, preservando plugins e alias. A etapa 9 explica como separar a base dos assets no build.

Substitua o conteúdo inicial de `frontend/src/App.vue` por:

```vue
<script setup lang="ts">
import AppShell from '@/app/layouts/AppShell.vue'
</script>

<template>
  <AppShell>
    <RouterView />
  </AppShell>
</template>
```

Não mantenha um teste esperando “You did it!” depois dessa mudança. Na futura etapa de testes autorizados, revise `src/__tests__/App.spec.ts` e prepare o roteador no teste ou verifique componentes isolados.

**Confira antes de seguir:** você tem uma feature completa no frontend, com um adaptador em memória. Na execução isolada autorizada, deve ser possível listar, abrir o formulário, cancelar, validar e criar um card. Isso ainda não é persistência.


# Aula 5 — O momento em que a brincadeira vira persistência

Até aqui, errar apaga apenas dados fictícios da memória.

A partir daqui:

```text
POST
→ service
→ transaction
→ INSERT
→ banco
```

Por isso o ambiente deixa de ser detalhe.

A arquitetura exige desenvolvimento e homologação isolados antes das gravações reais. O objetivo desta aula não é decorar toda infraestrutura; é entender uma regra:

> **nenhuma feature de escrita deve ser usada como experimento em produção.**

## O que você precisa reconhecer como desenvolvedor de feature

Você não precisa virar especialista em infraestrutura para implementar Eventos, mas precisa saber verificar:

- qual configuração está carregada;
- para qual banco a engine aponta;
- se jobs estão desligados;
- se imports disparam integrações;
- se `db.create_all()` ainda altera schema;
- se identidade de desenvolvimento é controlada.

Se qualquer uma dessas respostas estiver incerta, o backend pode ser escrito como código, mas não deve ser executado contra ambientes reais.


## 5. Prepare o ambiente antes do cadastro real

Agora muda a natureza da entrega: o próximo passo grava dados. Antes de executar o backend ou aplicar SQL, prepare desenvolvimento e homologação isolados conforme a seção 9 da arquitetura.

Não basta mudar a conexão de Eventos. A factory atual chama `db.create_all()`; imports transitivos podem iniciar threads e pedir tokens; autenticação, logs e jobs também podem acessar recursos reais. O isolamento precisa alcançar esse caminho inteiro.

Planeje uma configuração por ambiente que:

1. Exija uma conexão própria para o banco de desenvolvimento, sem fallback de produção.
2. Deixe jobs e notificações desligados ou simulados.
3. Não inicie threads nem faça chamadas externas durante imports.
4. Remova a criação de tabelas da inicialização normal.
5. Use identidade fictícia explícita no ambiente isolado, sem reaproveitar o fallback fixo do legado.
6. Inicialize conexões e serviços somente na composição configurada da aplicação.
7. Use diretórios próprios para quaisquer arquivos de desenvolvimento.

Isso pertence à preparação da plataforma, não ao componente Vue. Instalar APIFlask não remove esses efeitos.

Os comandos futuros de Python e pip usam a `.venv` e as dependências versionadas. Não instale Alembic por impulso: escolha a ferramenta aprovada para evolução do schema ou um fluxo de scripts SQL revisados com aplicação explícita. Não execute nada sobre o banco corporativo para acompanhar este tutorial.

**Confira antes de seguir:** a execução autorizada do ambiente isolado não deve alcançar produção nem integrações reais. Enquanto isso não estiver comprovado, continue apenas com arquivos e frontend simulado.


# Aula 6 — Backend: schema → repository → service

Agora começa o padrão que você mais vai repetir em features novas.

Use esta pergunta para cada arquivo:

```text
schema     = quais dados são válidos?
repository = como acesso os dados?
service    = qual operação estou executando?
route      = como HTTP entra nessa operação?
```

Nesta etapa fazemos primeiro os três primeiros. A rota entra depois.

## 6.0 Entenda a diferença entre schema, entidade e tabela

Eles podem parecer a mesma coisa, mas não são.

### Tabela

É como o dado existe no banco:

```text
id
name
description
created_by
created_at
```

### Schema de entrada

É o que o cliente tem permissão de enviar:

```text
name
description
```

### Schema de saída

É o que queremos expor:

```text
id
name
description
```

Esse desacoplamento é uma proteção importante.

O fato de uma coluna existir no banco **não significa** que deve aparecer na API.

## Pydantic: pense nele como porteiro do contrato

Quando você declara:

```python
name: str = Field(min_length=3, max_length=120)
```

você está dizendo que qualquer requisição válida precisa cumprir esse formato.

E:

```python
extra="forbid"
```

evita que o navegador invente campos extras.

Mas Pydantic não responde perguntas como:

> Esse usuário pode criar eventos?

Isso é regra de autorização, portanto fica fora do schema.

## Repository: limite da persistência

O repository deve aceitar dados prontos e falar com o banco.

Ele não deve descobrir usuário, request ou permissão.

Pense nele como uma função que poderia ser chamada de qualquer contexto:

```python
repository.create_event(
    connection,
    name="...",
    description="...",
    created_by="...",
)
```

## Por que parametrizar SQL?

Isto:

```python
VALUES (:name, :description, :created_by)
```

separa comando SQL dos valores.

Nunca monte entrada do usuário por concatenação ou f-string.

## Service: o caso de uso

O service coordena:

```text
autorizar
→ abrir transação
→ chamar repository
→ devolver resultado
```

É a camada que melhor responde:

> “o que significa criar um evento no sistema?”

Hoje é simples. Amanhã pode incluir:

```text
criar evento
→ registrar auditoria
→ definir organizador
→ criar configuração inicial
```

A rota pode continuar igual porque a evolução fica concentrada no caso de uso.

## Transação

```python
with self.engine.begin() as connection:
```

significa que as gravações dentro do bloco são tratadas como uma unidade.

Se uma exceção ocorrer, o esperado é rollback.

Essa decisão pertence ao service porque é o caso de uso que sabe **quais operações precisam acontecer juntas**.


## 6. Construa o backend de dentro para fora

Vamos escrever primeiro os dados e a persistência, depois a entrada HTTP. Assim você consegue entender o caso de uso sem depender da rota.

### 6.1 Escreva os schemas

Crie `app/modules/events/schemas.py`:

```python
from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        strict=True,
    )

    name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=1, max_length=2000)


class EventQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=12, ge=1, le=100)


class EventOut(BaseModel):
    id: int
    name: str
    description: str


class EventCapabilities(BaseModel):
    can_create: bool


class EventList(BaseModel):
    items: list[EventOut]
    page: int
    per_page: int
    total: int
    capabilities: EventCapabilities
```

`EventCreate` representa o que o cliente pode enviar. `EventOut` representa o que ele pode receber. Por isso autor, área, role e instante de criação não são campos de entrada. `extra="forbid"` rejeita tentativas de acrescentá-los.

A query não usa `strict=True`, pois parâmetros da URL chegam como texto e precisam ser convertidos para inteiro. Pydantic declara limites e normalização; a permissão de criar pertence ao caso de uso. [Referência de campos](https://docs.pydantic.dev/latest/concepts/fields/).

### 6.2 Planeje a tabela e sua evolução

Use o banco próprio da aplicação definido para o ambiente. O cadastro não precisa consultar Plex, SAP ou Jost Integration PRD. A preferência por procedures para consultas corporativas complexas não exige uma procedure para este cadastro simples.

Uma proposta de tabela é `dbo.DJ_EVENTS`. Antes de adotá-la, confirme como texto que não conflita com um objeto existente e valide o nome, schema e tipo do autor com o responsável pelo banco. O exemplo abaixo é um **desenho a versionar e revisar**, não um comando autorizado para executar:

```sql
CREATE TABLE dbo.DJ_EVENTS (
    id INT IDENTITY(1, 1) NOT NULL PRIMARY KEY,
    name NVARCHAR(120) NOT NULL,
    description NVARCHAR(2000) NOT NULL,
    created_by NVARCHAR(128) NOT NULL,
    created_at DATETIME2(3) NOT NULL DEFAULT SYSUTCDATETIME()
);
```

`NVARCHAR` guarda texto Unicode. A identidade gera o identificador; não use `MAX(id) + 1`. `created_at` usa UTC e `created_by` recebe a identidade resolvida no servidor. Confirme que o limite proposto para o autor atende ao identificador atual.

Esses metadados registram a origem da criação. Se a política exigir trilha de auditoria separada, acrescente-a na mesma transação mediante desenho aprovado. Não reutilize logs operacionais como tabela de auditoria.

Versione o script ou a migration no fluxo aprovado. O repositório já possui `database/migrations/` para SQL versionado; esse é um possível destino quando a escolha for scripts, sem inventar uma segunda ferramenta de migrations paralela.

Um retorno de publicação deve desligar o acesso e preservar os eventos criados. Não planeje `DROP TABLE` automático como rollback: a perda de registros não é um retorno seguro.

### 6.3 Escreva o repositório

Crie `app/modules/events/repository.py`:

```python
from sqlalchemy import text


def list_events(connection, *, page, per_page):
    total = connection.execute(
        text("SELECT COUNT(*) FROM dbo.DJ_EVENTS")
    ).scalar_one()
    rows = connection.execute(
        text("""
            SELECT id, name, description
            FROM dbo.DJ_EVENTS
            ORDER BY id DESC
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
        """),
        {"offset": (page - 1) * per_page, "limit": per_page},
    ).mappings().all()
    return [dict(row) for row in rows], total


def create_event(connection, *, name, description, created_by):
    row = connection.execute(
        text("""
            INSERT INTO dbo.DJ_EVENTS (name, description, created_by)
            OUTPUT inserted.id, inserted.name, inserted.description
            VALUES (:name, :description, :created_by)
        """),
        {
            "name": name,
            "description": description,
            "created_by": created_by,
        },
    ).mappings().one()
    return dict(row)
```

A conexão é um argumento. O repositório não escolhe o ambiente, não lê a sessão Flask e não faz commit. Os valores passam por parâmetros; nomes de tabela e colunas são fixos.

Esse exemplo pressupõe a tabela proposta sem triggers que afetem o uso de `OUTPUT`. Reveja o comando se o desenho aprovado incluir triggers. [Referência do SQL Server](https://learn.microsoft.com/en-us/sql/t-sql/queries/output-clause-transact-sql?view=sql-server-ver17). A contagem e a listagem são consultas separadas; cadastros concorrentes podem mudar o total entre elas. Para uma listagem simples isso pode ser aceitável; não altere o isolamento global do banco sem uma necessidade definida.

### 6.4 Escreva o serviço

Crie `app/modules/events/services.py`:

```python
from . import repository


class EventsService:
    def __init__(self, engine, permissions):
        self.engine = engine
        self.permissions = permissions

    def list(self, query, actor):
        self.permissions.require(actor, "events.read")
        with self.engine.connect() as connection:
            items, total = repository.list_events(
                connection,
                page=query.page,
                per_page=query.per_page,
            )
        return {
            "items": items,
            "page": query.page,
            "per_page": query.per_page,
            "total": total,
            "capabilities": {
                "can_create": self.permissions.can(actor, "events.create")
            },
        }

    def create(self, data, actor):
        self.permissions.require(actor, "events.create")
        with self.engine.begin() as connection:
            event = repository.create_event(
                connection,
                name=data.name,
                description=data.description,
                created_by=str(actor.id),
            )
        return event
```

O serviço recebe uma engine do ambiente e um mecanismo de permissões. `permissions.require` e `permissions.can` são contratos que você implementará na plataforma: o primeiro rejeita a operação proibida, o segundo devolve um booleano. `actor` é a identidade confiável do servidor e deve conter um identificador validado.

No `engine.begin()`, o bloco inteiro participa da transação: saída normal confirma; uma exceção provoca rollback. Se houver auditoria adicional, ela entra dentro desse bloco usando a mesma conexão. [Referência do SQLAlchemy 2 sobre transações](https://docs.sqlalchemy.org/en/20/core/connections.html#connect-and-begin-once-from-the-engine).

A engine deste cadastro é distinta da sessão ORM que eventualmente carregou a identidade. Isso precisa ser explícito. Não misture gravações em `db.session`, pyodbc e essa conexão esperando uma única transação.

**Confira antes de seguir:** nenhuma dessas funções depende de `request`, template ou usuário recebido pelo navegador. Um job futuro poderia chamar o mesmo serviço com uma identidade de sistema autorizada.


# Aula 7 — A rota deve ser a parte mais sem graça

Uma rota boa é pequena porque ela apenas conecta HTTP ao caso de uso.

Idealmente você consegue ler:

```python
@bp.post(...)
@bp.input(...)
@bp.output(...)
def create_event(json_data):
    return service.create(...)
```

e entender o endpoint inteiro.

Se aparecer SQL, `commit`, regra extensa ou manipulação de HTML dentro da rota, provavelmente responsabilidades começaram a se misturar.

## O que APIFlask acrescenta

O Flask continua sendo a base.

APIFlask ajuda a declarar:

```text
entrada
saída
status HTTP
OpenAPI
```

O schema Pydantic passa a servir também como contrato HTTP.

## Autenticação versus autorização

São perguntas diferentes:

```text
Autenticação:
"Quem é você?"

Autorização:
"Você pode fazer isto?"
```

`current_actor()` resolve a primeira.

`permissions.require(actor, "events.create")` resolve a segunda.

Um usuário autenticado não é automaticamente autorizado a criar.

## Por que o frontend não é segurança?

Isto:

```vue
v-if="can_create"
```

melhora a experiência.

Mas alguém ainda pode chamar o endpoint manualmente.

Portanto o POST verifica novamente no service/servidor.

## CSRF

Como a API usa a sessão do navegador, operações mutáveis precisam provar que a requisição veio de uma página legítima da sessão.

Fluxo simplificado:

```text
servidor gera token
→ shell coloca token em <meta>
→ client.ts envia X-CSRF-Token
→ servidor valida
→ só então executa POST
```

O token não identifica o usuário e não substitui permissão. É outra proteção, com outra responsabilidade.


## 7. Exponha a API com proteção no servidor

Agora vamos ligar HTTP ao serviço. Há dois trabalhos diferentes: preparar a plataforma e escrever as rotas de eventos.

### 7.1 Prepare os contratos da plataforma

Implemente primeiro os mecanismos abaixo, aproveitando a autenticação existente por um adaptador explícito. Eles **ainda não existem com esses nomes no estado examinado**; são pontos de integração deste guia, não imports prontos.

| Mecanismo | Comportamento exigido |
| --- | --- |
| `current_actor()` | Resolve a sessão autenticada no servidor; retorna identidade normalizada; sem sessão, erro JSON `401` na API. |
| `permissions.require(actor, action)` | Mapeia ações para roles existentes e produz erro de acesso negado quando necessário. |
| `permissions.can(actor, action)` | Usa o mesmo mapeamento e retorna booleano, sem modificar permissões. |
| `get_events_service()` | Obtém o serviço já composto para o ambiente; não cria engine global no import. |
| Verificação de CSRF | Rejeita POST sem token válido associado à sessão. |
| Verificação de disponibilidade | Protege shell e API quando `EVENTS_ENABLED` está desligado ou o usuário não pertence ao piloto. |

Não transforme `events.read` e `events.create` em roles de banco automaticamente. Elas são ações do módulo que você precisa mapear para o modelo de autorização atual. Não conceda criação a qualquer usuário só porque ele está autenticado. Normalize o indicador textual de administrador, como orienta o AGENTS.md.

Para CSRF, você pode adotar um mecanismo aprovado da plataforma ou adaptar o padrão já usado pelo Gerenciador de Demandas: token aleatório salvo na sessão, envio em `X-CSRF-Token` e comparação segura no servidor. Proteja todos os métodos mutáveis. O token não deve ir na URL.

O shell autenticado pode expor o token em uma tag `meta`, com escape pelo Jinja, e a API não recebe usuário ou permissões do navegador. Para `/api/`, sessão expirada devolve JSON `401`; não redireciona silenciosamente o fetch para HTML de login.

### 7.2 Integre APIFlask sem mudar o legado por acidente

Antes de registrar um `APIBlueprint`, prepare a factory como `APIFlask`. A documentação informa que blueprints Flask comuns podem ser registrados nessa aplicação, mas `APIBlueprint` não pode ser registrado em uma instância Flask comum. [Referência de migração](https://apiflask.com/migrations/flask/).

Faça essa integração em uma mudança pequena e revisada, depois do isolamento. Preserve os handlers HTML das páginas antigas e defina erros JSON para a API. Avalie `json_errors=False` na factory para manter a resposta legada, complementando o tratamento explícito dos erros de `/api/`. Isso exige mapear os handlers existentes, não apenas trocar o nome da classe.

Mantenha o ponto de entrada do IIS e os blueprints antigos em `main.py`. A factory passa a chamar um registro explícito dos módulos modernos depois de configurar extensões e dependências. Ela não cria tabelas.

### 7.3 Escreva as rotas

Em `app/modules/events/routes.py`, o formato será:

```python
from apiflask import APIBlueprint

from .schemas import EventCreate, EventList, EventOut, EventQuery

# Adicione aqui os imports reais dos mecanismos da etapa 7.1.
# current_actor e get_events_service precisam estar implementados.

events_bp = APIBlueprint(
    "events",
    __name__,
    url_prefix="/api/v1/events",
)


@events_bp.get("")
@events_bp.input(EventQuery, location="query")
@events_bp.output(EventList)
def list_events(query_data):
    return get_events_service().list(query_data, current_actor())


@events_bp.post("")
@events_bp.input(EventCreate)
@events_bp.output(EventOut, status_code=201)
def create_event(json_data):
    return get_events_service().create(json_data, current_actor())
```

Este trecho mostra as rotas; ele só fica completo com os imports, os mecanismos da plataforma e os guards de sessão, piloto e CSRF. Aplique esses guards antes de chamar os handlers. Não registre uma API aberta para experimentar a tela.

APIFlask 3 aceita modelos Pydantic como schemas de entrada e saída. O argumento JSON validado chega como `json_data` e a query como `query_data`. [Referência dessa integração](https://apiflask.com/schema/pydantic/).

Em `app/modules/events/__init__.py`, exporte o blueprint:

```python
from .routes import events_bp
```

Em `app/modules/__init__.py`, registre explicitamente os módulos:

```python
def register_modules(app):
    from .events import events_bp
    app.register_blueprint(events_bp)
```

A factory monta `EventsService` com a engine configurada e o mecanismo de permissões, guarda a instância em um ponto explícito de composição, como `app.extensions["events_service"]`, e chama `register_modules(app)`. `get_events_service()` lê essa dependência. Nenhum import deve abrir conexão, iniciar thread ou enviar mensagem.

### 7.4 Fixe o contrato de erros

Use JSON com `message` e `detail`, compatível com o tratamento de validação do APIFlask. Falhas inesperadas devolvem uma mensagem pública genérica, com identificador técnico quando adotado pela plataforma. Não devolva SQL, conexão, stack trace ou dados internos.

| Situação | Resposta esperada |
| --- | --- |
| Sessão ausente ou expirada | `401`. |
| Sem permissão para a ação | `403`. |
| CSRF ausente ou inválido | `400` com motivo de segurança, sem tentar novamente automaticamente. |
| Nome ou descrição inválidos | `422` com erros de campo. |
| JSON malformado | `400`. |
| Feature desligada ou fora do piloto | Resposta definida da plataforma, como `404`, no shell e na API. |
| Falha inesperada | `500` com mensagem genérica. |

Faça a validação de sessão/piloto antes de expor informações e normalize as exceções do mecanismo de permissões para o contrato JSON. Confirme que o esquema público é consistente no OpenAPI e no frontend.

**Confira antes de seguir:** GET e POST estão protegidos no servidor; conhecer a URL não permite contornar a interface. Ainda não publique no IIS nesta etapa.


# Aula 8 — A melhor prova de separação: trocar a fonte sem trocar a tela

Aqui você testa se a arquitetura do frontend ficou boa.

Antes:

```text
EventsPage → EventsApi → mock
```

Depois:

```text
EventsPage → EventsApi → HTTP → backend
```

`EventCard` continua igual.

`EventForm` continua igual.

Grande parte de `EventsPage` continua igual.

Esse é exatamente o benefício de programar contra um contrato.

## Por que `client.ts` é compartilhado?

Toda feature moderna provavelmente precisará repetir:

- `Accept: application/json`;
- `Content-Type`;
- cookies da sessão;
- CSRF;
- timeout;
- interpretação de erro;
- tratamento de sessão expirada.

Se cada feature implementar isso, bugs e diferenças aparecem rapidamente.

Então o compartilhamento aqui é justificado por uma necessidade real.

## `ApiError`

A ideia é transformar respostas HTTP em um erro que a UI consiga entender:

```ts
status
message
detail
```

A feature pode então decidir:

```text
401 → sessão expirou
403 → sem permissão
404 → feature indisponível
422 → corrigir campos
500 → falha do servidor
```

## Um detalhe importante sobre TypeScript

Quando escrevemos:

```ts
requestJson<EventList>(...)
```

o TypeScript acredita que a resposta tem esse formato.

Ele **não valida o JSON real** no navegador.

Por isso o guia alerta que a resposta real deve ser conferida ou validada por algum mecanismo apropriado.

TypeScript protege seu código em desenvolvimento; não transforma automaticamente dados externos em dados confiáveis.


## 8. Troque a simulação pela API real

Quando o backend estiver pronto no ambiente isolado, você trocará a origem dos dados. O card e o formulário não precisam saber que essa troca aconteceu.

### 8.1 Escreva o cliente HTTP compartilhado

Crie `frontend/src/shared/api/client.ts`:

```ts
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail: unknown = {},
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function requestJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase()
  const writing = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.body) headers.set('Content-Type', 'application/json')
  if (writing) {
    const token = document.querySelector<HTMLMetaElement>('meta[name="csrf-token"]')?.content
    if (!token) throw new ApiError('Atualize a página para renovar a segurança da sessão.', 400)
    headers.set('X-CSRF-Token', token)
  }

  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 10000)
  let response: Response
  let body: unknown
  try {
    response = await fetch(path, {
      ...options,
      headers,
      credentials: 'same-origin',
      signal: controller.signal,
    })
    if (response.redirected) {
      throw new ApiError('A sessão precisa ser renovada. Acesse novamente o portal.', 401)
    }
    const contentType = response.headers.get('content-type') ?? ''
    if (!contentType.includes('application/json')) {
      throw new ApiError(
        writing ? 'Resposta inesperada. Confira a listagem antes de tentar cadastrar novamente.'
          : 'O servidor devolveu uma resposta inesperada.',
        response.status,
      )
    }
    body = await response.json()
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError(
      writing ? 'Não foi possível confirmar o cadastro. Confira a listagem antes de tentar novamente.'
        : 'Não foi possível carregar os dados. Verifique a conexão.',
      0,
    )
  } finally {
    window.clearTimeout(timeout)
  }

  if (!response.ok) {
    const value = typeof body === 'object' && body !== null
      ? body as { message?: unknown; detail?: unknown } : {}
    const message = response.status === 401 ? 'Sua sessão expirou. Acesse novamente o portal.'
      : response.status === 403 ? 'Você não tem permissão para esta operação.'
      : response.status >= 500 ? 'Não foi possível concluir a operação.'
      : typeof value.message === 'string' ? value.message : 'Revise os dados enviados.'
    throw new ApiError(message, response.status, value.detail)
  }
  return body as T
}
```

O cliente concentra credenciais de sessão, CSRF, timeout, JSON e erros. Não registra payloads nem tokens. Dez segundos é um limite inicial a ajustar conforme o ambiente, não uma medição do servidor.

O tipo genérico `T` ajuda o TypeScript, mas não valida JSON em runtime. No adaptador da feature, confira campos essenciais ou adote a validação de respostas aprovada pela plataforma. Por exemplo, uma lista precisa ter `items` como array, eventos com ID inteiro e textos, números válidos de paginação e `can_create` booleano. Uma resposta incompatível deve produzir erro de contrato, não uma tela aparentemente vazia.

Como esse cliente atende a toda API moderna, sua responsabilidade compartilhada já é clara. Se crescer, extraia a definição de `ApiError` para `shared/api/errors.ts`; não crie esse arquivo apenas para repassar uma classe que ainda cabe aqui.

### 8.2 Complete o adaptador real de eventos

Em `features/events/api.ts`, acrescente os imports e o objeto:

```ts
import { requestJson } from '@/shared/api/client'
import type { EventItem, EventList } from './types'

const realEventsApi: EventsApi = {
  list(page, perPage) {
    const query = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
    })
    return requestJson<EventList>('/api/v1/events?' + query.toString())
  },
  create(payload) {
    return requestJson<EventItem>('/api/v1/events', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}
```

Mantenha o import de `EventsApi` e os métodos exportados da etapa 4.3. Na função `adapter()`, substitua somente o `throw` final por `return realEventsApi`. A condição de mock continua limitada a desenvolvimento.

Os endpoints acima pressupõem o sistema na raiz do domínio. Se o IIS usa um prefixo, gere a base da API no shell com `url_for` e forneça-a como configuração pequena e confiável. Não espalhe o nome do servidor corporativo em arquivos Vue.

### 8.3 Exponha o CSRF no shell

No template Jinja de entrada do Vue, use o token gerado na sessão pelo mecanismo da plataforma:

```html
<meta name="csrf-token" content="{{ csrf_token }}">
```

O template precisa receber esse valor do servidor, com autoescape ativo. Não copie um token fixo para o frontend. A tela simulada não usa HTTP nem precisa de CSRF.

No desenvolvimento integrado autorizado, o shell e o fetch precisam compartilhar o contexto de sessão. Uma proxy apenas para `/api/` não cria por conta própria uma sessão autenticada nem preenche essa tag meta. Escolha explicitamente entre servir o shell pelo Flask com assets do Vite ou criar um bootstrap de desenvolvimento exclusivo do ambiente isolado. Não crie um atalho de login acessível em produção.

### 8.4 Trate os estados de integração na página

No `useQuery`, capture também `error: listError`. A partir de `ApiError.status`, apresente mensagem de sessão expirada para `401`, acesso negado para `403` e indisponibilidade para `404`. Ofereça retorno ao portal para renovar sessão e não uma sequência de tentativas automáticas.

No erro de criação, preserve o formulário. Para `422`, leia `detail.json` e passe as mensagens de `name` e `description` ao componente, exibindo-as junto dos respectivos campos. O formato efetivo desse detalhe deve ser confirmado com a versão integrada do APIFlask; não tente interpretar HTML como erro de campo.

Na primeira implementação, o exemplo da etapa 4 já mostra a mensagem pública no formulário. Antes de concluir a API real, acrescente essa diferenciação por status e o mapeamento de erros de campo. Assim o usuário sabe se precisa corrigir o texto, renovar a sessão ou aguardar o serviço.

**Confira antes de seguir:** trocar o adaptador não muda o contrato nem os componentes. Um evento real criado aparece depois da renovação da lista e continua existindo ao recarregar.


# Aula 9 — Vue Router, Vite, Flask e IIS têm responsabilidades diferentes

Esta parte costuma confundir porque existem vários “caminhos”.

Guarde três coisas:

```text
/app/eventos
= URL que o usuário navega

/app/
= base do Vue Router

/static/app/
= caminho dos arquivos compilados de produção
```

## Vue Router

Decide qual componente renderizar para uma URL da SPA.

## Vite

No desenvolvimento, serve e transforma módulos.

No build, gera JavaScript/CSS compilados com nomes que podem conter hash.

## Flask

Entrega o shell HTML, sessão, CSRF e endpoints da API.

## IIS

É parte da hospedagem e precisa encaminhar as URLs sem quebrar legado, assets ou API.

## Por que usar manifest?

O build pode gerar algo como:

```text
index-B7d91abc.js
```

Esse nome muda.

O template Flask não deve adivinhar o hash.

Ele lê o manifesto do Vite e descobre o arquivo atual.

## O shell não é a aplicação inteira

`shell.html` é basicamente:

```text
HTML mínimo
+ meta CSRF
+ links dos assets
+ <div id="app">
```

Depois o Vue monta dentro dessa `div`.

Os eventos em si chegam pela API, não são renderizados pelo Jinja.


## 9. Prepare assets e roteamento para o IIS

Até aqui, você aprendeu a feature. Agora precisa entregá-la sem capturar URLs do legado.

### Separe a base da navegação da base dos arquivos

A navegação será `/app/eventos`. Os arquivos de produção serão `/static/app/`. São caminhos diferentes.

No roteador, mantenha `createWebHistory('/app/')`, definido na etapa 4.5 para a hospedagem proposta na raiz. Se houver diretório virtual no IIS, configure o prefixo aprovado nos dois lados. A base do Vue Router controla navegação; a base do Vite controla imports e URLs de assets. [Referência de history mode](https://router.vuejs.org/guide/essentials/history-mode.html).

No `vite.config.ts`, preserve plugins e alias atuais. Para distinguir desenvolvimento e build, a configuração pode receber `command`:

```ts
export default defineConfig(({ command }) => ({
  // Preserve aqui os plugins e o alias já existentes.
  base: command === 'serve' ? '/app/' : '/static/app/',
  build: {
    manifest: true,
  },
}))
```

Esse é um trecho de configuração para **mesclar** com o arquivo atual, não para apagar seus plugins. O pacote compilado em `frontend/dist/` contém assets e, na configuração proposta, `.vite/manifest.json`. O processo de publicação autorizado copia o conjunto inteiro para o destino aprovado, preservando os caminhos relativos.

O Flask lê o manifesto publicado e resolve a entrada `src/main.ts`, seus estilos e imports. Ele monta tags de script e link com URLs do próprio sistema. Não fixe no template o nome de um arquivo com hash, pois ele muda a cada build. [Referência de integração do Vite](https://vite.dev/guide/backend-integration).

Crie `app/templates/app/shell.html` como entrada HTML do Vue. O formato mínimo é:

```html
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token }}">
    <title>Eventos | Digital JOST</title>
    {% for stylesheet in stylesheets %}
      <link rel="stylesheet" href="{{ stylesheet }}">
    {% endfor %}
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="{{ entry_script }}"></script>
  </body>
</html>
```

`stylesheets` e `entry_script` são URLs produzidas no servidor a partir do manifesto publicado, inclusive o CSS das dependências da entrada. `csrf_token` vem da sessão. O handler Flask de `/app/eventos` autoriza e renderiza esse template; ele não consulta a tabela de eventos para montar HTML. A listagem chega pela API. Defina esse handler na composição da entrada moderna, fora do prefixo `/api/v1/events`.

Use uma lista de rotas Vue reconhecidas no servidor para entregar o shell. Como a primeira feature é Eventos, essa lista começa por `/app/` e `/app/eventos`, ambas protegidas. A raiz pode redirecionar para a página de eventos. Não registre um catch-all global sobre o portal para entregar esse template.

O shell de `/app/eventos` deve:

1. Conferir sessão, configuração e grupo piloto.
2. Gerar a configuração pequena de URLs e CSRF.
3. Entregar o HTML com assets do manifesto.
4. Preservar as páginas antigas.

Permita recarregar `/app/eventos` diretamente. O fallback só deve atender rotas da SPA conhecidas; `/api/`, arquivo estático ausente e URL antiga não podem devolver silenciosamente o HTML de Eventos. Uma rota desconhecida de `/app/` deve ter comportamento de 404 definido e página de não encontrada.

Assets com hash podem ter cache longo. O shell autenticado com token de sessão não deve ser compartilhado entre usuários; defina cache privado ou `no-store` conforme a plataforma. O manifesto e o HTML não recebem o mesmo cache longo dos assets.

O Vite só é um servidor durante desenvolvimento autorizado. Em produção, entregue arquivos compilados pelo Flask/IIS; não deixe Node executando no servidor.

### Publique como piloto

Use uma configuração como `EVENTS_ENABLED`, desligada por padrão, e permissões resolvidas no backend. O grupo piloto deve valer para shell e API. Ocultar o link do menu sozinho não protege a feature.

Antes de publicar, documente o pacote, o schema compatível, a janela, o responsável e a volta à versão anterior. Desligar a feature preserva os registros. A home atual e o destino após login continuam oficiais.


# Aula 10 — “Funcionou na minha tela” não valida a arquitetura

Teste cada responsabilidade no lugar em que ela pode falhar.

Exemplos:

```text
maxlength no input
≠
validação do backend

botão escondido
≠
autorização

POST retornou 201
≠
listagem atualizou

build gerou arquivos
≠
IIS entrega rota direta corretamente
```

A tabela de verificação abaixo existe justamente para separar essas evidências.

Durante seu aprendizado, tente sempre registrar:

```text
o que eu alterei?
onde validei?
qual comportamento provei?
```

Isso ajuda muito em sistemas corporativos, onde desenvolvimento local, homologação e IIS podem se comportar de maneiras diferentes.


## 10. Confira cada camada

Nesta tarefa, a conferência é somente estática. Na implementação futura, execução, testes, consultas, migrations, build e publicação precisam da autorização específica exigida pelo repositório.

| Camada | O que conferir | Evidência esperada |
| --- | --- | --- |
| Texto e diff | Arquivos, contratos, parâmetros, imports, referências e ausência de segredos. | Diff revisado e `git diff --check` sem erros. |
| Frontend simulado | Layout, modal, teclado, formulário, erro, vazio e paginação. | Verificação autorizada com dados fictícios. |
| Backend isolado | Schemas, sessão, permissões, CSRF e transação. | Testes autorizados sem produção. |
| Homologação | Persistência, Unicode, publicação, sessão e falhas. | Casos documentados em ambiente próprio. |
| IIS | Windows Auth, assets, cache, URLs diretas, piloto e legado. | Validação controlada do pacote publicado. |

Na verificação funcional autorizada, passe por estas situações:

- Lista vazia mostra a orientação; o usuário autorizado pode criar.
- Nome com espaços nas extremidades é normalizado; só espaços é rejeitado.
- Nome abaixo de 3 ou acima de 120 caracteres é rejeitado.
- Descrição vazia ou acima de 2.000 caracteres é rejeitada.
- Acentos e quebras de linha persistem; texto parecido com HTML aparece como texto.
- Campo extra como `created_by` ou `admin` é rejeitado.
- Sem sessão: `401` JSON na API; sem permissão: `403`.
- Sem CSRF válido: POST rejeitado e nenhum registro inserido.
- Se uma etapa da transação falhar, não fica um cadastro parcial.
- Em erro de envio, o formulário conserva o texto.
- “Novo evento” abre o modal com foco no nome; Tab permanece no diálogo.
- Cancelar, fechar e Escape encerram o modal e devolvem o foco à ação de abertura.
- Durante o envio, campos e botões ficam desabilitados; Escape e fechar não interrompem o cadastro.
- A confirmação aparece depois do POST; o modal fecha e um novo cadastro abre com campos vazios.
- Em timeout do POST, a interface orienta conferir a lista antes de repetir.
- A listagem percorre todas as páginas com limite e ordem estável.
- Cadastro confirmado permanece após recarregar a página.
- Falha ao renovar a lista depois de um POST confirmado não oferece cadastrar de novo como se o POST tivesse falhado.
- Em celular, os campos e botões cabem; tabulação e foco têm ordem clara.
- O shell com CSRF não é servido do cache de outro usuário.
- Desligar a configuração bloqueia a API e o shell sem excluir eventos.
- Home, login e páginas antigas continuam funcionando.

Não execute comandos do `package.json` por hábito: os scripts de lint atuais incluem correção automática. Escolha os comandos exatos e o ambiente antes da etapa autorizada de validação.


# Aula 11 — Agora transforme Eventos em um molde mental, não em um template cego

A feature terminou quando você consegue recriar o raciocínio.

Para uma próxima feature, não comece copiando a pasta `events`.

Comece perguntando:

```text
qual é o comportamento?
qual é o contrato?
é leitura ou escrita?
quais permissões?
quais dados?
qual persistência?
quais estados de UI?
```

Só depois você escolhe quais arquivos realmente são necessários.

## Checklist para decidir a estrutura de uma feature nova

### É apenas uma leitura simples?

Talvez baste:

```text
route
→ schema
→ repository/query
→ response
```

### Existe criação, alteração ou exclusão?

Use:

```text
route
→ schema
→ service
→ repository
```

### Existe entidade ORM própria?

Aí pode surgir:

```text
models.py
```

### Existem regras de estado complexas?

Talvez faça sentido:

```text
domain.py
```

### Existe integração específica?

Talvez:

```text
integrations.py
```

Não crie esses arquivos antecipadamente.

Isso é “complexidade progressiva”: a estrutura cresce quando a responsabilidade realmente aparece.

## O padrão final que você precisa memorizar

Não memorize os nomes exatos dos arquivos. Memorize o raciocínio:

```text
1. definir comportamento
2. definir contrato
3. construir UI independente
4. simular dependência externa
5. preparar ambiente seguro
6. validar entrada
7. encapsular persistência
8. coordenar caso de uso
9. expor HTTP
10. trocar mock pela integração
11. validar cada camada
12. extrair compartilhamento somente quando fizer sentido
```

Se você souber repetir isso, a primeira feature cumpriu o objetivo pedagógico.


## 11. Entenda o padrão que você acabou de criar

O fluxo completo fica assim:

```text
EventsPage → Dialog contém EventForm, que emite nome e descrição
           → eventsApi → cliente HTTP com sessão e CSRF
           → rota valida EventCreate
           → serviço autoriza e abre transação
           → repositório faz INSERT parametrizado
           → banco gera ID e metadados
           → resposta 201
           → página confirma e renova a listagem
```

Para criar outra feature, você reaproveita shell, tokens, componentes Volt, cliente HTTP e mecanismos da plataforma. `Card` continua genérico; `EventCard` compõe esse controle com nome e descrição. `Dialog` fornece o modal; `EventForm` define os campos e validações da feature. O que muda são contrato, regra, consultas e componentes do domínio. Não transforme os cards de Eventos em um card universal com dezenas de opções antes de outra tela precisar disso.

Quando chegar a chamada, comece por definir as regras: quem participa, quem registra presença, quem pode corrigir um registro e como relacionar tudo ao evento. Essas decisões determinarão novas tabelas e casos de uso. O `id` do evento já fornece o vínculo; não é necessário criar estruturas vazias agora.

### Uma ordem prática para o seu próximo trabalho

Confira a base e adicione os componentes da etapa 2.2 quando houver autorização para essa instalação. Comece o código pelos tokens e pelo shell. Depois escreva os tipos e o card. Em seguida, conecte página, modal, formulário e adaptador em memória. Só depois avance para o ambiente isolado, os schemas, o repositório, o serviço e as rotas protegidas. Troque o adaptador quando os contratos estiverem alinhados e prepare o piloto por último.

Ao final de cada etapa, registre o que foi escrito e em qual camada foi realmente verificado. “Existe no código” e “foi validado no IIS” são evidências diferentes.

**Limite deste guia:** os exemplos foram conferidos como texto e precisam de adaptação aos mecanismos reais de identidade, permissões, configuração e implantação. O sistema não foi executado; a validação foi somente estática.


---

# Checklist final de aprendizado

Antes de considerar o curso concluído, tente explicar sem consultar o documento:

- [ ] Por que `EventForm` emite `submit` em vez de chamar a API?
- [ ] Por que `EventCard` não conhece Vue Query?
- [ ] Qual diferença entre `ref` e `reactive` neste exemplo?
- [ ] Por que `EventsApi` permite trocar mock por API real?
- [ ] Para que serve `useQuery`?
- [ ] Para que serve `useMutation`?
- [ ] Por que invalidamos a query depois de criar?
- [ ] Por que frontend e backend validam nome e descrição?
- [ ] O que `extra="forbid"` protege?
- [ ] Por que `created_by` não vem do navegador?
- [ ] Por que o repository recebe a conexão?
- [ ] Por que o repository não faz commit?
- [ ] Por que a transação fica no service?
- [ ] Qual diferença entre autenticação e autorização?
- [ ] Por que esconder botão não é segurança?
- [ ] Para que serve CSRF neste fluxo?
- [ ] O que uma `APIBlueprint` acrescenta ao Flask?
- [ ] Por que `requestJson` é compartilhado?
- [ ] Por que TypeScript não valida automaticamente o JSON real?
- [ ] Qual diferença entre `/app/` e `/static/app/`?
- [ ] Por que o Flask lê o manifesto do Vite?
- [ ] Por que Node/Vite não precisa ficar rodando em produção?
- [ ] Como você começaria uma segunda feature?

Se você consegue responder a maior parte disso com suas próprias palavras, você já não está apenas reproduzindo Eventos: está começando a entender o padrão de desenvolvimento da arquitetura nova.

# Resumo de bolso

```text
FRONTEND
types → components → page → api adapter → shared HTTP client

BACKEND
route → schema → service → repository → database

SEGURANÇA
server identity + permission + CSRF + controlled environment

ENTREGA
Vue Router + Vite build + Flask shell + IIS

REGRA DE OURO
A feature contém suas políticas.
A plataforma fornece mecanismos compartilhados.
```
