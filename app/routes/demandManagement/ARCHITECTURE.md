# Arquitetura do Gerenciador de Demandas

O módulo é separado do legado, mas continua compatível com o monólito Flask.

```text
routes.py                HTTP, autenticação, CSRF, respostas JSON e montagem do serviço
services.py              casos de uso e limites de transação
repository.py            SQL parametrizado e acesso a dados
domain.py                regras, opções, validações e erros da feature
integration.py           sincronização e notificações dos fluxos de aprovação
schema.sql               criação manual das tabelas do gerenciador
```

## Regras de dependência

- A rota não contém SQL.
- A rota é o ponto de composição das dependências concretas da feature.
- O repositório não conhece Flask nem decide respostas HTTP.
- O serviço controla transações e valida responsáveis da área.
- O domínio reúne regras e validações sem dependência de Flask ou banco.
- As integrações externas da feature ficam juntas em um único adaptador.
- O adaptador legado recebe uma conexão já aberta, para participar da mesma transação da aprovação.
- Dados originais não são copiados: `sourceRequestId` relaciona o registro operacional a `JDT_REQUEST_IMPROVEMENTS_SMALL`.
- Solicitações em análise e recusadas são lidas diretamente da tabela original; a aba não cria uma cópia desses registros.
- A aprovação e a criação idempotente do card acontecem na mesma transação.
- O `schema.sql` lê o tipo e a collation reais de `JDT_USER_DETAILS.id` para criar as FKs de usuário sem depender do tamanho declarado no modelo ORM.

Para adicionar outra área no futuro, inclua sua configuração em `domain.py`, valide os campos necessários no banco e reutilize as mesmas rotas com `?area=Nome da Área`.
