# Histórico da documentação

Esta pasta preserva o material anterior à consolidação do manual. Textos e comandos podem refletir decisões superadas, nomes antigos, propostas ainda não implementadas ou um ambiente informado em outra data. Para trabalhar no sistema, começar pelo [manual atual](../README.md) e seguir [AGENTS.md](../../AGENTS.md).

As subpastas `docs/` e `handbook/` registram de onde vieram os arquivos. Não são dois novos manuais: a referência vigente está em `handbook/docs/` e `handbook/features/`. Links de arquivos foram ajustados para os locais preservados; o conteúdo técnico antigo não foi atualizado para simular uma nova implementação.

## Planos e arquitetura anteriores — docs/

| Registro | Conteúdo preservado |
|---|---|
| [Arquitetura inicial](docs/arquitetura-modernizacao.md) | Proposta ampla e roteiro dos primeiros pilotos. |
| [Separação do legado](docs/plano-separacao-backend-legado.md) | Etapas, decisões e registros das entregas da infraestrutura moderna. |
| [Plano de simplificação](docs/plano-simplificacao-arquitetura.md) | Critérios e registro da conversão para Services funcionais. |
| [Primeira avaliação](docs/avaliacao-simplificacao-arquitetura.md) | Discussão inicial sobre camadas e dependências. |
| [Segunda avaliação](docs/segunda-avaliacao-simplificacao-arquitetura.md) | Discussão sobre gravações simples e facilidade de desenvolvimento. |
| [Base compartilhada anterior](docs/base-compartilhada-novas-features.md) | Guia anterior, incluindo exemplo documental de equipamentos. |
| [Curso de Eventos](docs/curso-pratico-primeira-feature-eventos.md) | Material didático da primeira versão; exemplos não representam integralmente o código atual. |
| [Guia inicial de Eventos](docs/guia-primeira-feature-eventos.md) | Roteiro do piloto e preparação da primeira feature. |

## Ambiente, segurança e entregas — docs/

| Registro | Conteúdo preservado |
|---|---|
| [TD e sessão](docs/configuracao-externa-td-sessao.md) | Extração da configuração privada do banco e da sessão. |
| [Integrações privadas](docs/configuracao-privada-integracoes.md) | Configuração das integrações e revisões da entrega. |
| [Publicação da modernização](docs/publicacao-modernizacao-servidor.md) | Pacote e ordem de implantação de uma sequência específica de commits. |
| [Ambiente informado](docs/ambientes-desenvolvimento-servidor.md) | Registro de computador, IIS e serviços informado à época. |
| [Revisão de segurança](docs/revisao-seguranca-modernizacao.md) | Evidências e prioridades; arquivar o registro não significa resolver seus achados. |
| [Disponibilidade operacional](docs/operation-planning-availability.md) | Histórico da integração de fontes e do relatório de manutenção. |

Listas de arquivos e comandos auxiliares daquela fase também foram preservadas: [arquivos da publicação](docs/arquivos-publicacao-modernizacao.txt), [download de Eventos](docs/baixar-dependencias-eventos-pc.txt), [instalação de Eventos](docs/instalar-dependencias-eventos-servidor.txt), [download da modernização](docs/baixar-dependencias-modernizacao-pc.txt) e [instalação da modernização](docs/instalar-dependencias-modernizacao-servidor.txt). Não são roteiros universais de uma nova entrega.

## Versões anteriores do manual — handbook/

| Registro | Referência atual ou situação |
|---|---|
| [Arquitetura](handbook/arquitetura-modernizada.md) | Consolidada no guia geral atual. |
| [Publicação Azure](handbook/publicacao-azure.md) | Procedimento revisado no guia geral, com caminhos de exemplo sem identificação pessoal. |
| [Servidor](handbook/servidor-e-publicacao.md) | Consolidado com preparação, configuração e build no guia atual. |
| [Padrão visual](handbook/padrao-visual.md) | Reescrito com os componentes e convenções atuais. |
| [Eventos](handbook/eventos.md) e [presença](handbook/listas-de-presenca.md) | Reunidos em um documento de Eventos. |
| [Solicitações](handbook/solicitacoes-demandas.md) | Consolidadas no documento atual de Demandas. |
| [Proposta do gerenciador](handbook/proposta-gerenciador-demandas.md) | Ideias e decisões ainda pendentes; não é um gerenciador completo já implementado. |

Nenhum script, migration, comando de publicação ou teste foi executado ao organizar estes registros. Caminhos pessoais de usuário Windows foram substituídos por marcadores; segredos nunca devem ser acrescentados ao histórico.
