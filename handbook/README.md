# Manual do Digital JOST

Este é o índice da documentação oficial. Os guias descrevem o código atual e distinguem comportamento implementado, propostas e condições dependentes do ambiente; publicação e funcionamento em produção não são presumidos.

Os oito guias foram aprofundados em **20/10/2026**, comparando código e versões históricas. Incluem fluxos, contratos, responsabilidades, configuração, integridade, tratamento de falhas e verificações pendentes. A completude documental não substitui validar o comportamento no ambiente autorizado.

## Guias gerais — docs/

| Documento | Quando consultar |
|---|---|
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

- Atualizar o documento do assunto quando mudar seu comportamento. Não criar um arquivo por tarefa, correção ou commit.
- Arquitetura contém padrões gerais; features contêm regras, API, arquivos, dados e verificações específicas.
- Manter textos objetivos e links para a fonte de verdade; evitar copiar listas extensas de código ou repetir procedimentos.
- Ao revisar, rastrear o fluxo no código e confrontar o histórico para recuperar decisões relevantes. Se houver divergência, descrever o estado implementado e identificar a proposta superada, sem tratá-la como entrega.
- Detalhar contratos, permissões, transações, dados, integrações, falhas e publicação quando fizerem parte do assunto. Não reduzir informação necessária apenas para atingir um limite de linhas.
- Identificar propostas como planejadas. Um script SQL versionado não comprova execução, e um recurso implementado não comprova publicação.
- Criar documento novo somente para um assunto distinto que precise ser mantido; acrescentá-lo a este índice.
- Ao mover arquivos, corrigir referências internas, README principal e AGENTS.md.

O [histórico](historico/README.md) preserva estudos, planos e versões anteriores dos documentos. Ele não define a arquitetura vigente nem autoriza executar comandos antigos. O [README principal](../README.md) apresenta o projeto; [AGENTS.md](../AGENTS.md) continua definindo as restrições operacionais.

Esta reorganização alterou somente documentação. **O sistema não foi executado; a validação foi somente estática.**
