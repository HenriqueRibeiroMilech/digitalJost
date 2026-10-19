# Manual do Digital JOST

Esta pasta reúne a documentação oficial do projeto. O nome `handbook` significa manual: um lugar para consultar como o sistema é organizado e como deve evoluir.

| Documento | Conteúdo |
|---|---|
| [Arquitetura modernizada](arquitetura-modernizada.md) | Objetivos, implementação atual, criação de features, reutilização e evolução planejada. |
| [Padrão visual](padrao-visual.md) | Identidade, largura das telas, grade de quatro cards no desktop e componentes compartilhados da modernização. |
| [Campos e tipos de Eventos](eventos.md) | Cadastro de tipos pelo Select, instrutor/conteúdo opcionais, contratos e publicação. |
| [Listas de presença](listas-de-presenca.md) | Listas de um evento, leitura de crachá, contratos, publicação e conferência em ambiente autorizado. |
| [Solicitações de demandas](solicitacoes-demandas.md) | Nova solicitação e Minhas solicitações, tabelas novas, anexos privados e convivência com o gerenciador antigo. |
| [Servidor e publicação](servidor-e-publicacao.md) | IIS, serviços Windows, dependências offline, publicação no servidor e retorno à versão anterior. |
| [Publicação no Azure](publicacao-azure.md) | Passo a passo para gerar o ZIP filtrado, substituir o código preservando .git e publicar a versão oficial no Azure. |

Preparação do computador, configuração privada e build estão no [README principal](../README.md). Os procedimentos completos de servidor e de publicação ficam nos guias acima.

Os documentos devem distinguir o que está implementado do que é proposta, acompanhar as mudanças relevantes do código e explicar as decisões em linguagem simples.
