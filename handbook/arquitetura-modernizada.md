# Arquitetura modernizada

## Objetivo

Facilitar novas entregas e migrar o legado aos poucos, mantendo o portal funcionando. Cada feature cuida de suas regras e reaproveita a infraestrutura comum.

## Estado atual

```text
IIS → Flask (app/config.py)
        ├─ app/: páginas, usuários, integrações e jobs antigos
        └─ backend/: shell Vue → API → serviço → repositório → TD

frontend/ → build → backend/static/app/
```

Existe uma aplicação Flask. A parte nova ainda depende do login, sessão, perfis e ciclo global de `app/`. `backend/compatibility/` concentra a ponte de identidade com o legado.

Eventos é o primeiro módulo: listagem e cadastro em `/app/eventos`, API `/api/v1/events` e tabela `dbo.DJ_EVENTS`. Usa a API real em desenvolvimento e produção.

O backend novo tem uma engine e um pool geral do TD por instância da aplicação. As conexões são reutilizadas pelos módulos; o legado mantém seus acessos separados. Transações entre essas conexões não são unificadas. A configuração fica em `backend/config.py` e usa `DJ_TD_ODBC_CONNECTION_STRING`.

A factory ainda chama `db.create_all()`, e imports antigos podem iniciar threads e acessar serviços. O ambiente ainda não garante testes isolados.

## Onde colocar o código

| Arquivo/local | Responsabilidade |
|---|---|
| `backend/modules/<feature>/routes.py` | Receber HTTP, aplicar acesso e chamar o serviço. |
| `schemas.py` | Definir e validar entradas e respostas. |
| `services.py` | Regras, permissões por ação e transações. |
| `repository.py` | SQL parametrizado; recebe a conexão e não depende de Flask. |
| `__init__.py` | Exportar os blueprints do módulo. |
| `frontend/src/features/<feature>/pages/` | Montar a tela e coordenar os dados. |
| `components/`, `api.ts` e `types.ts` | Componentes locais, chamadas HTTP e tipos da feature. |

Crie arquivos adicionais, como `domain.py` ou `integration.py`, somente quando houver uma responsabilidade real para separar.

## O que reutilizar

| Base | Recursos existentes |
|---|---|
| `backend/platform/` | Banco TD, ambiente, identidade, autorização HTTP, CSRF, erros JSON, paginação e shell Vue. |
| `frontend/src/shared/` | `requestJson`, `ApiError`, `validationMessages`, `usePagination`, `ListPagination`, `PageHeader`, `FormField` e `RequestState`. |
| `frontend/src/app/layouts/AppShell.vue` | Layout comum das páginas Vue. |
| `frontend/src/volt/` e `shared/styles/tokens.css` | Controles e estilos visuais. |

Use o que já existe. Mantenha regras e componentes específicos dentro da feature. Extraia uma parte comum quando usos reais mostrarem que isso facilita a manutenção. Evite abstrações que precisem de muitas exceções.

Exemplo: `FormField` é comum; `EventForm` pertence a Eventos. Serviços novos recebem a engine geral pela composição, sem criar outro pool para o mesmo TD.

## Criar uma feature

1. **Defina a entrega:** ações, permissões, dados, tabelas, integrações e jobs afetados. Comece por um fluxo pequeno.
2. **Defina os contratos:** página em `/app/<pagina>`, API em `/api/v1/<recurso>` e schemas de entrada e saída.
3. **Implemente regras e SQL:** serviço exige a permissão; repositório usa parâmetros. Agrupe gravações atômicas na mesma conexão, com `engine.begin()`. E-mails e chamadas externas exigem tratamento próprio de falha.
4. **Componha o backend:** em `backend/bootstrap.py`, crie o serviço com engine e permissões e registre-o em `app.extensions`. Use `configure_api`, `get_service`, `page_access` e `render_vue_shell`. Registre os blueprints em `backend/modules/__init__.py`.
5. **Monte a interface:** use `requestJson`, TanStack Query para dados remotos e os componentes comuns. Trate carregamento, vazio, erros, validação, foco e envio duplicado.
6. **Adicione a navegação:** registre a rota Vue em `frontend/src/router/index.ts` e a rota Flask que entrega o shell no caminho completo. Isso permite acesso direto e F5. Menus não são gerados automaticamente.
7. **Confira o fluxo:** acesso, consultas, gravações, falhas e perfis sem permissão. Agentes validam estaticamente; execução, testes e builds exigem autorização explícita de comando, ambiente e escopo, conforme `AGENTS.md`.
8. **Publique e documente:** gere o build quando autorizado e siga o [guia do servidor](servidor-e-publicacao.md). Atualize este guia somente se a descrição arquitetural precisar mudar.

Regras comuns:

- `Actor` identifica o usuário; `RolePermissions` consulta os perfis da sessão corrente. Eventos mapeia leitura e criação para `GENERAL`; escolha as permissões de cada nova feature.
- Capacidades enviadas à interface orientam botões. O backend continua autorizando cada ação e define o autor pela sessão.
- Reutilize `PaginationQuery` e `PaginatedResponse`: entrada com `page` e `per_page`; saída com `items`, `page`, `per_page`, `total` e `capabilities`. A página começa em 1, com 12 itens por padrão e `per_page` limitado a 100. Contagem e itens aplicam os mesmos filtros e acessos.
- Mantenha tipos TypeScript e schemas Python compatíveis; a sincronização é manual. Inclua página/filtros na chave da consulta e atualize a lista após gravar. Não repita automaticamente uma gravação de resultado incerto.

## Migrar o legado durante uma mudança

Ao mexer em uma conexão, integração, rotina ou regra antiga, prefira migrar a parte relacionada quando houver benefício, escopo controlado e risco baixo ou moderado.

Por exemplo: ao alterar o acesso ao Jost Integration, avalie levar a configuração e o acesso à camada moderna adequada ao destino. Preserve uma ponte para telas ou jobs antigos que ainda precisem dele. Isso não exige trocar banco, tabelas ou credenciais, nem usar a engine TD para outro destino.

Antes de migrar, identifique consumidores, permissões, gravações e impacto na publicação. Preserve URLs e comportamentos necessários, defina uma forma de retorno e evite rotinas duplicadas. Retire o código antigo somente após conferir referências e consumidores.

**Para IA, a migração precisa estar no pedido ou já autorizada.** Se ampliar o escopo, apresente benefício e impactos e obtenha autorização. Se houver impacto alto, dependências desconhecidas ou falta de condições para validar, conclua a tarefa no legado e registre a migração na lista futura, com o motivo do adiamento.

## Próximos passos

Propostas, em ordem sugerida; ainda não representam funcionalidades entregues:

| Prioridade | Proposta e objetivo |
|---|---|
| 1 | Criar uma segunda feature para avaliar a reutilização da base atual. |
| 2 | Preparar configuração de desenvolvimento e testes isolados de recursos corporativos. |
| 3 | Retirar efeitos externos de imports e planejar alterações de schema fora da inicialização. |
| 4 | Evoluir permissões por ação/registro e reduzir a dependência da identidade antiga. |
| 5 | Padronizar logs sem segredos e tornar publicação offline e retorno mais previsíveis. |
| 6 | Migrar conexões, integrações e rotinas relacionadas às partes alteradas, com escopo autorizado. |
| 7 | Revisar SQL, arquivos, CSRF e autorização a cada migração. Tratar rotação de segredos, histórico e backups. |
| 8 | Avaliar geração de tipos, modelo de feature e catálogo de navegação quando a repetição justificar. |

A independência completa do legado pode vir depois; não é requisito para a próxima feature.

## Manter este guia atualizado

- Atualize somente as seções afetadas por mudanças de arquitetura, dependências, contratos comuns ou processo de desenvolvimento.
- Correções locais que não alterem essa descrição dispensam atualização. Preserve o que continua válido.
- Acrescente novas propostas à lista acima, com objetivo e escopo; complemente itens existentes para evitar duplicação.
- Ao entregar uma proposta, atualize o estado atual e retire da lista futura apenas o que foi concluído.

Detalhes de cada alteração ficam no Git. Configuração local fica no [README](../README.md); operação, no [guia do servidor](servidor-e-publicacao.md).
