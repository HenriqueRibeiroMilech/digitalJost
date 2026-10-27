# Guias gerais e manutenção da documentação

Esta pasta contém as referências gerais do Digital JOST. O [índice do manual](../README.md) reúne também os documentos de funcionalidades. Este README define onde documentar e quando uma atualização é necessária; as restrições operacionais continuam em [AGENTS.md](../../AGENTS.md).

## Índice dos guias

| Documento | Conteúdo |
|---|---|
| [Colinha do projeto](colinha-do-projeto.md) | Introdução simples à arquitetura, pastas, arquivos e fluxos, com roteiro de apresentação. |
| [Arquitetura e modernização](arquitetura-modernizada.md) | Organização do sistema, responsabilidades, escolha das camadas e migração do legado. |
| [Proposta de aproximação ao curso de Flask](proposta-arquitetura-proxima-ao-curso.md) | Backend por feature, ORM nas rotas e quatro arquivos básicos, sem Service ou Repository obrigatórios; implementação pendente. |
| [Ambiente, servidor e publicação](servidor-e-publicacao.md) | Preparação, configuração privada, dependências, build, IIS, serviços Windows e retorno de versão. |
| [Publicação no Azure DevOps](publicacao-azure.md) | Exportação filtrada e envio de uma versão de código ao repositório Azure. |
| [Padrão visual](padrao-visual.md) | Identidade, layout, componentes, formulários, diálogos, estados e acessibilidade. |

## Onde incluir cada assunto

| Local | Quando usar |
|---|---|
| `handbook/docs/` | Padrões e procedimentos gerais, aplicáveis a várias funcionalidades ou à operação do sistema. |
| `handbook/features/` | Comportamento, regras, contratos, dados, integrações e manutenção de uma funcionalidade ou recurso comum, como a base compartilhada. |
| `handbook/historico/` | Material retirado da referência atual que ainda precisa ser preservado, como propostas superadas e estudos anteriores. |
| `handbook/README.md` | Índice geral e apresentação do manual. |
| `README.md` da raiz | Apresentação do projeto e acesso ao manual, sem reproduzir os guias. |
| `AGENTS.md` | Regras operacionais dos agentes; não substituí-las por instruções em um guia. |

Por exemplo: uma regra de anexos de Demandas pertence a [Demandas](../features/demandas.md); uma mudança geral no tratamento HTTP pertence à [base compartilhada](../features/base-compartilhada.md); uma decisão sobre camadas pertence à arquitetura. Usar links quando o assunto atravessar documentos, evitando copiar a mesma explicação em vários lugares.

## Quando atualizar

**Atualizar somente quando uma mudança relevante ou uma informação incorreta tornar a documentação inadequada para desenvolver, usar, manter ou publicar o sistema. Não atualizar por rotina a cada tarefa ou commit.**

| Situação | Orientação |
|---|---|
| Mudança importante de comportamento ou regra de negócio | Atualizar o documento da funcionalidade afetada. |
| Alteração de contrato público, permissão, transação, concorrência, dados ou integração | Atualizar as seções necessárias para explicar o novo funcionamento e seus cuidados. |
| Mudança de arquitetura, configuração, publicação ou padrão visual comum | Atualizar o guia correspondente e os documentos específicos somente se também ficarem incorretos. |
| Funcionalidade nova ou retirada | Documentar o escopo duradouro e ajustar os índices afetados. |
| Informação incorreta ou link quebrado | Corrigir o trecho ou a referência, mesmo sem mudança de código. |
| Refatoração interna que preserva contratos, comportamento e orientação do manual | Não atualizar, salvo se invalidar um caminho, exemplo ou explicação existente. |
| Ajuste pequeno de texto, ícone, espaçamento ou implementação | Não atualizar se não mudar uma convenção ou informação relevante já documentada. |
| Trabalho sem impacto no conteúdo atual | Manter os documentos como estão. |

Pergunta de decisão: **quem seguir o documento depois da mudança receberá uma orientação incorreta ou ficará sem uma informação importante?** Se não, normalmente não há atualização a fazer.

Não acrescentar uma data de revisão, resumo da tarefa ou lista de arquivos alterados apenas para registrar atividade. O histórico de commits cumpre esse papel. Corrigir um bug para voltar ao comportamento já descrito também não exige alterar o manual, a menos que existam novos cuidados ou limitações a registrar.

## Quando criar um documento

Primeiro procurar um documento do assunto e complementar a seção correspondente. Criar outro arquivo somente para um assunto distinto, com escopo próprio e informação que precise continuar sendo consultada e mantida.

Não criar um arquivo por correção, conversa, commit ou etapa de implementação. Também não dividir uma funcionalidade em vários documentos pequenos quando um guia com seções claras for suficiente. Por exemplo, cadastro, tipos, presença e PDF continuam reunidos em [Eventos](../features/eventos.md).

Usar nome descritivo, em minúsculas e com hífens, sem datas ou números de versão para o guia vigente. Um documento novo em `docs/` entra no índice desta pasta e no índice geral; um documento de feature entra no índice geral. Ajustar índices apenas quando sua navegação ou descrição mudar.

O histórico não precisa receber uma cópia a cada edição: o Git já preserva versões. Arquivar material quando ele deixar de ser referência atual e ainda tiver valor, identificando sua situação e apontando para o guia vigente.

## Como revisar uma atualização necessária

1. Conferir o código ativo e os contratos relacionados. Consultar o histórico para recuperar decisões, sem tratar instruções antigas como estado atual.
2. Identificar a mudança relevante e editar apenas as seções afetadas. Preservar explicações corretas; evitar reescrever ou reorganizar todo o documento sem necessidade.
3. Explicar o funcionamento e, quando aplicável, permissões, dados, falhas, publicação e compatibilidade. Usar exemplos curtos e links para o código, sem transformar o guia em cópia da implementação.
4. Distinguir o que está implementado, o que é proposta e o que depende de confirmação no ambiente. Não apresentar um script SQL como aplicado ou código versionado como publicado sem evidência.
5. Conferir links e referências quando houver inclusão, remoção ou mudança de caminho. Atualizar índices, README ou AGENTS.md somente se suas orientações também forem afetadas.
6. Revisar Markdown e diff. Não incluir credenciais, dados pessoais, payloads reais, logs ou arquivos operacionais. Seguir as limitações de execução de AGENTS.md.

O objetivo é manter uma referência confiável e suficiente para o trabalho, sem multiplicar arquivos nem gerar alterações documentais sem motivo.
