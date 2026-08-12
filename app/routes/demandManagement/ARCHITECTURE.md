# Arquitetura do Gerenciador de Demandas

O módulo é separado do legado, mas continua compatível com o monólito Flask.

```text
routes.py       HTTP, autenticação, CSRF e respostas JSON
composition.py  criação das dependências concretas
services.py     casos de uso e limites de transação
repository.py   SQL parametrizado e acesso a dados
validation.py   validações sem dependência de Flask
integration.py  sincronização vinda de /solicitar/manage
constants.py    áreas, opções e campos permitidos
```

## Regras de dependência

- A rota não contém SQL.
- O repositório não conhece Flask nem decide respostas HTTP.
- O serviço controla transações e valida responsáveis da área.
- O adaptador legado recebe uma conexão já aberta, para participar da mesma transação da aprovação.
- Dados originais não são copiados: `sourceRequestId` relaciona o registro operacional a `JDT_REQUEST_IMPROVEMENTS_SMALL`.
- O `schema.sql` lê o tipo e a collation reais de `JDT_USER_DETAILS.id` para criar as FKs de usuário sem depender do tamanho declarado no modelo ORM.

Para adicionar outra área no futuro, inclua sua configuração em `constants.py`, valide os campos necessários no banco e reutilize as mesmas rotas com `?area=Nome da Área`.
