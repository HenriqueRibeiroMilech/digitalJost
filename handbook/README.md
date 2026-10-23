# Manual do Digital JOST

Este é o índice da documentação oficial. Os guias descrevem o código atual e distinguem comportamento implementado, propostas e condições dependentes do ambiente; publicação e funcionamento em produção não são presumidos.

Os oito guias foram aprofundados em **20/10/2026**, comparando código e versões históricas. Incluem fluxos, contratos, responsabilidades, configuração, integridade, tratamento de falhas e verificações pendentes. A completude documental não substitui validar o comportamento no ambiente autorizado.

## Guias gerais — docs/

| Documento | Quando consultar |
|---|---|
| [Colinha do projeto](docs/colinha-do-projeto.md) | Entender o projeto com explicações simples, localizar pastas e arquivos e preparar uma apresentação. |
| [Arquitetura e modernização](docs/arquitetura-modernizada.md) | Entender a organização, escolher camadas e criar ou migrar uma feature. |
| [Ambiente, servidor e publicação](docs/servidor-e-publicacao.md) | Preparar computador/configuração/build, atualizar IIS e serviços ou retornar uma versão. |
| [Publicação no Azure DevOps](docs/publicacao-azure.md) | Exportar e enviar uma versão aprovada ao repositório Azure; não implanta o sistema. |
| [Padrão visual](docs/padrao-visual.md) | Reutilizar layout, cards, campos, diálogos e estados acessíveis. |

## Funcionalidades — features/

| Documento | Escopo |
|---|---|
| [Eventos](features/eventos.md) | Cadastro, tipos, listas de presença, identificação LDAP e PDF. |
| [Demandas](features/demandas.md) | Solicitações modernas, edição, anexos, histórico e limites do gerenciador ainda planejado. |
| [Base compartilhada](features/base-compartilhada.md) | Identidade, permissões, CSRF, banco, contratos, dependências e criação de módulos. |
| [Planejamento operacional](features/planejamento-operacional.md) | Disponibilidade e manutenção no Operation Meeting e no relatório detalhado. |

## Como manter o manual

As regras de inclusão e manutenção estão em [Guias gerais e manutenção da documentação](docs/README.md), junto do índice de `docs/`.

Atualizar somente quando uma mudança relevante ou uma informação incorreta afetar a utilidade do documento. Refatorações internas e ajustes pequenos não exigem atualizar o manual se suas orientações continuarem corretas. Preferir o arquivo do assunto; não criar um documento por tarefa, correção ou commit.

O [histórico](historico/README.md) preserva estudos, planos e versões anteriores dos documentos. Ele não define a arquitetura vigente nem autoriza executar comandos antigos. O [README principal](../README.md) apresenta o projeto; [AGENTS.md](../AGENTS.md) continua definindo as restrições operacionais.

Esta reorganização alterou somente documentação. **O sistema não foi executado; a validação foi somente estática.**
