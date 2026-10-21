> **Registro histórico.** Pode conter decisões, caminhos e comandos superados. Consulte o [manual atual](../../README.md); este arquivo não define o padrão vigente.

# Solicitações de demandas na arquitetura moderna

## Escopo desta entrega

A página `/app/demandas/solicitacoes` oferece **Nova solicitação** e **Minhas solicitações**, no padrão visual de Eventos. O menu do shell moderno permite alternar entre Eventos e Solicitações. A área atendida nesta etapa é Transformação Digital; a página aceita `?area=Transforma%C3%A7%C3%A3o%20Digital` e rejeita outras áreas.

As opções de entrada são **Solicitar demanda** (`demanda`) e **Reportar erro** (`erro`). O solicitante não escolhe Melhoria, Projeto ou Atividade. A classificação fica nula para ser definida no futuro gerenciador. Toda criação começa como `em_analise`.

O gerenciador e o portal antigos continuam funcionando com suas tabelas e URLs. Solicitações modernas não aparecem no gerenciador antigo. A nova tela inclui um link para consultar solicitações anteriores; ela não importa nem mistura os registros antigos. Não há gráficos, aprovação, atribuição, notificações, recorrências ou jobs novos nesta entrega.

## Campos e regras

| Campo | Regra |
|---|---|
| Tipo de entrada | `demanda` ou `erro`, obrigatório. |
| Título | Obrigatório, até 250 unidades UTF-16. |
| Objetivo/descrição do erro | Obrigatório, até 4.000 unidades UTF-16. |
| Urgência | Alta, Média ou Baixa. |
| Contribuinte | Opcional, outra pessoa ativa e não genérica com e-mail corporativo. |
| Premissas, problemas atuais e ganhos esperados | Obrigatórios para demanda, até 4.000 unidades UTF-16 por campo; omitidos e gravados como NULL para erro. |
| Documentos/evidências | Entre 1 e 10 arquivos, com conteúdo, até 10 MiB por arquivo e 40 MiB no total. |

Solicitante e área vêm do contexto autorizado do backend. A API rejeita campos de responsável, classificação ou status enviados pelo cliente. Os nomes e e-mails dos exemplos operacionais fornecidos na conversa não foram usados em código, documentação ou dados de exemplo.

São aceitos Word, Excel, PowerPoint, TXT, PDF e imagens PNG/JPG/JPEG/GIF/BMP/WebP. O limite HTTP do módulo é 45 MiB, incluindo multipart; os limites de cada arquivo e do total são conferidos novamente no backend. IIS e proxy também precisam permitir esse tamanho para que o limite da aplicação possa ser utilizado.

O cliente aguarda até 60 segundos no upload. As demais chamadas JSON mantêm o padrão compartilhado de dez segundos; o comportamento de Eventos permanece com seus limites anteriores.

No cadastro de demanda, o exemplo de fluxo aparece como imagem ao lado dos documentos, em duas colunas de mesma largura em telas grandes. Em telas menores, fica abaixo dos anexos. A imagem mantém sua proporção e pode ser aberta em tamanho original ao clicar. No relato de erro, a seção de evidências ocupa a largura disponível, sem o exemplo de fluxo.

Minhas solicitações inclui registros em que a pessoa é solicitante ou contribuinte. A busca por título é literal; também aceita o número, com ou sem `#`. Filtro de tipo, contagem e paginação são aplicados no servidor. A página usa 12 cards por página e apresenta os estados de carregamento, vazio e falha.

Os cards usam a variante compacta do `RecordCard`, com número e tipo no cabeçalho, status ao lado, título/resumo de até duas linhas e urgência/data agrupadas. A identificação de contribuinte ocupa uma linha, com o nome completo também disponível nos detalhes. A largura, as colunas e a paginação permanecem iguais. Os skeletons acompanham a apresentação compacta; os cards de Eventos mantêm o padrão anterior.

O solicitante pode editar os dados enquanto o registro está em análise e sem classificação. O contribuinte pode consultar e baixar anexos, sem editar. A edição mantém os documentos existentes; substituição ou gestão de anexos após envio não faz parte desta etapa.

## Banco novo

O SQL está em [20261019_create_dj_demands.sql](../../../database/migrations/20261019_create_dj_demands.sql). É uma proposta para revisão e aplicação manual no TD; não foi executado e não é chamado pela aplicação.

| Tabela | Responsabilidade |
|---|---|
| `dbo.DJ_DEMANDS` | Cadastro principal, entrada, classificação futura, status, conteúdo, participantes, datas, versão e identificação do envio. |
| `dbo.DJ_DEMAND_ATTACHMENTS` | Metadados, tamanho, SHA-256 e chave privada de armazenamento, vinculados à demanda por FK. |
| `dbo.DJ_DEMAND_HISTORY` | Eventos de criação e edição, autor, data e mudanças em JSON, vinculados à demanda por FK. |

O cadastro usa IDENTITY, sem `MAX(id) + 1`. Há índices para solicitante e contribuinte, proteção de concorrência por ROWVERSION e unicidade de `(area_id, requester_id, submission_key)`.

A criação grava apenas `entry_kind`, deixando `classification` NULL. A restrição permite que o futuro gerenciador classifique demandas como `melhoria`, `projeto` ou `atividade`; relatos de erro continuam identificados pela entrada `erro`. Ainda não há operação de classificação. Novos status e campos de execução serão definidos com o gerenciador, sem assumir o fluxo completo proposto anteriormente.

IDs de usuários são texto para preservar zeros e identificadores alfanuméricos. Nesta etapa são referências lógicas ao cadastro compartilhado `JDT_USER_DETAILS`, consultado somente para nomes e contribuintes. A definição completa da chave/tipo desse cadastro não foi fornecida; não foi criada uma FK por suposição.

A migration não altera, exclui ou importa tabelas `JDT_*`. As amostras recebidas não definem tipos, tamanhos, constraints, índices ou todos os vínculos do legado. O script de migração dos registros antigos permanece para uma etapa específica, após esse levantamento e definição dos mapeamentos.

## API e isolamento

Base: `/api/v1/demands`. Todas as rotas usam a sessão atual e GENERAL; os serviços também verificam a ação. GET de detalhe e anexo exige vínculo como solicitante ou contribuinte na área atendida. Recursos sem esse vínculo retornam 404. Escritas usam o CSRF compartilhado, sem outro login ou consulta LDAP.

| Operação | Contrato |
|---|---|
| GET na base | `page`, `per_page`, `search` e `entry_kind` (`todos`, `demanda`, `erro`); retorna itens, total e capacidade de criar. |
| GET `/contributors` | Pessoas elegíveis, somente ID e nome. |
| POST na base | Multipart: `payload` contém JSON de `RequestCreate`; `files` contém os arquivos. Retorna os detalhes com HTTP 201 após commit. |
| GET `/<id>` | Conteúdo, documentos, histórico, versão e capacidade de editar. |
| PUT `/<id>` | JSON de `RequestUpdate`, com todos os campos editáveis e `row_version`; retorna os detalhes após commit. |
| GET `/<id>/attachments/<attachment_id>` | Download autorizado como attachment, sem cache e com `nosniff`. |

`RequestCreate` acrescenta `submission_key` (UUID textual) aos campos de cadastro. O browser mantém a chave e os arquivos ao falhar o envio. Uma repetição com a mesma chave e conteúdo retorna o mesmo registro; a mesma chave com conteúdo diferente retorna 409. A verificação é serializada na transação e protegida pela chave única, incluindo pedidos concorrentes.

Uma resposta incerta de criação mantém o formulário bloqueado para alteração e oferece conferir Minhas solicitações ou repetir o mesmo envio. Não há repetição automática de escritas. Depois de recarregar/abandonar a página, conferir a listagem antes de iniciar outro cadastro; a chave do formulário não é persistida no navegador.

A edição exige a versão recebida nos detalhes e revalida solicitante, status e classificação na transação. Alterações concorrentes retornam 409. O histórico registra os campos alterados com valores anterior e posterior. Mudanças de tipo para erro limpam os campos específicos de demanda, mantendo-os recuperáveis no histórico da edição.

## Arquivos e transações

Os anexos novos usam `<instance_path>/modern_demand_attachments/`, fora da pasta pública. O cadastro mantém nome saneado para download, mas armazena cada arquivo por uma chave aleatória; nomes enviados não compõem caminhos. Downloads verificam vínculo, relação anexo/demanda, formato da chave e contenção do caminho, rejeitando links simbólicos no arquivo.

O serviço valida os arquivos antes de abrir a transação SQL. Em erro anterior ao commit, remove somente arquivos novos da operação corrente. Se houver falha durante o commit, preserva os arquivos, pois o resultado da gravação pode ser incerto. Conciliação de eventuais arquivos sem referência deve ser uma ação específica, autorizada e sem limpeza automática.

O diretório não é criado no import nem no startup. A identidade do processo IIS precisa ter leitura/escrita nesse armazenamento privado. Backups devem incluir tabelas e arquivos. Nenhum upload antigo foi aberto ou modificado durante esta implementação.

## Publicação e retorno

1. O responsável revisa e aplica a migration no banco TD autorizado.
2. Confere permissões do armazenamento privado e limites de upload do IIS/proxy.
3. Em ambiente autorizado, gera e publica backend e build compatíveis, conforme [Servidor e publicação](servidor-e-publicacao.md).
4. Acessa `/app/demandas/solicitacoes`; os links antigos do portal e o gerenciador antigo permanecem nas URLs atuais.

A aplicação não cria as tabelas no startup. Publicar o código sem aplicar a migration permite manter o legado, mas a API moderna depende das novas tabelas para funcionar. A versão moderna não envia e-mails nem mensagens.

O retorno de código pode manter as tabelas e arquivos novos, preservando o que já foi cadastrado. O legado não passa a consultar esses registros automaticamente. Uma mudança de endereço principal ou migração de dados deve ser planejada separadamente, sem excluir as tabelas desta entrega como retorno automático.

## Validação pendente em ambiente autorizado

Conferir criação de demanda/erro, campos obrigatórios, limites de texto e arquivo, contribuinte, paginação e busca; acesso por outro usuário/área, sessão e CSRF; download, path traversal e vínculo do anexo; edição por solicitante e tentativa por contribuinte; concorrência e repetição após timeout; falhas de armazenamento/commit; foco, teclado, telas pequenas e preservação do formulário ao trocar de seção. Conferir também Eventos e o fluxo antigo após a publicação conjunta.

**O sistema não foi executado; a validação foi somente estática.** Não foram executados build, testes, imports do projeto, consultas ao banco, migration, downloads ou uploads operacionais.
