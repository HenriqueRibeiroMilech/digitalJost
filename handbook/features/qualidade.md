# Controle de Qualidade e Informativo QSB

O controle legado Flask/Jinja em `/op/qualidade/tabela` reúne cadastro horizontal, consulta e edição de ocorrências. O registro é a fonte dos dados apresentados no informativo; não há integração nova com Excel. A tela é adicional: os formulários anteriores continuam disponíveis.

A consulta inicial traz somente os últimos 15 dias corridos, incluindo hoje e os 14 dias anteriores, pela data de abertura (`openDate`) e pelo calendário do servidor. O período é aplicado na consulta SQL, antes de renderizar os registros e suas imagens, mantendo o maior ID primeiro. Não há paginação; todos os registros do intervalo escolhido são retornados.

Para consultar o histórico, alterar `De` e `Até` e clicar em `Buscar período` (ou pressionar Enter nesses campos). A busca atualiza apenas os registros, preservando o preenchimento do cadastro. Um limite de data vazio deixa aquele lado do intervalo aberto; ambos vazios permitem consultar todo o histórico explicitamente. `Limpar filtros` restaura o período padrão da abertura da página e a ordenação por ID. Pesquisa, unidade e publicação filtram os registros do período já carregado. Uma falha de consulta preserva os resultados anteriores; a interface indica quando o novo período ainda não foi aplicado.

## Registro e publicação

Cada ocorrência tem unidade, local da ocorrência, local específico, detalhamento opcional, centro de trabalho, produto, família, problema, reincidência, contenção, imagens, data e turnos. A descrição do produto é consultada no FTM; não é um novo campo persistido.

Os quatro dados de parada são horário, motivo, **tempo total de todas as paradas em minutos** e quantidade. Tempo é decimal positivo com até duas casas; quantidade é inteira positiva. Os motivos são lidos do catálogo `JDT_OPE_QUAL_STOP_REASONS`; `Problema de Qualidade`, apresentado no PDF, é a opção inicial.

O botão `+` de Motivo da parada, no cadastro e na edição, abre o mesmo modal de cadastro rápido do Local Específico. Após salvar, a opção fica disponível nos dois formulários e é selecionada naquele que abriu o modal. O nome aceita até 150 caracteres, normaliza espaços e rejeita vazio e duplicidade, inclusive diferenças de maiúsculas/minúsculas. O backend valida o motivo contra o catálogo ao salvar a ocorrência, preservando um motivo anterior fora da lista quando mantido sem alteração.

As duas referências a local do PDF são mapeadas para local da ocorrência e local específico, já existentes. O detalhamento adicional é opcional e não duplica esses valores.

`Publicar na pirâmide = Não` mantém a ocorrência no controle, mas a exclui da pirâmide e das páginas diárias de visualização/impressão. `Sim` a inclui nesses fluxos. Registros anteriores sem metadados continuam publicados. Horário, motivo, tempo, quantidade e detalhamento aparecem automaticamente no informativo e na impressão quando informados.

Os novos dados de parada são obrigatórios no novo cadastro. Um registro sem nenhum desses dados pode continuar sem eles ao ser corrigido; preencher qualquer um exige os quatro. Isso preserva informações desconhecidas de registros antigos ou provenientes dos formulários anteriores. As telas anteriores não passam a exigir os campos novos.

## Modal, autorização e contratos

Visualizar abre apenas a ocorrência escolhida, com imagens e as últimas 30 entradas do histórico. Editar abre os mesmos campos no próprio modal; cancelar preserva o registro salvo. Excluir exige confirmação e faz exclusão lógica. Registros excluídos saem das listagens, pirâmide, visualização, impressão e exportação anterior.

A autenticação e a permissão `GENERAL` continuam no `before_request` legado. Página, detalhes e operações da nova tela exigem `QUALITY`, que já permite gerenciar os informativos. Imagens de ocorrências publicadas também podem ser lidas por `GENERAL`, como no informativo diário; imagens não publicadas exigem `QUALITY`. As capacidades de editar/excluir retornadas pela API seguem `QUALITY`; não foram criados perfis novos. A criação de locais mantém a autorização específica já existente. A criação de motivos reutiliza exatamente `_can_manage_qsb_locations()`, também conferida no backend; a permissão geral de editar ocorrências não concede esse cadastro automaticamente.

| Endpoint | Contrato |
|---|---|
| `GET /op/qualidade/tabela` | HTML da tela adicional |
| `GET /op/qualidade/tabela/registros` | Consulta por `date_from`/`date_until` ISO; retorna `entries` e os limites aplicados; sem parâmetros usa os últimos 15 dias |
| `POST /op/qualidade/tabela/registros` | Cadastro multipart com `submission_key`; retorna registro e ID |
| `GET /op/qualidade/tabela/registros/<id>` | Um registro, revisão, permissões, imagens e histórico |
| `PATCH /op/qualidade/tabela/registros/<id>` | Edição multipart com `revision` e remoções explícitas de imagens |
| `DELETE /op/qualidade/tabela/registros/<id>` | JSON com `revision`; sucesso 204 |
| `GET /op/qualidade/tabela/registros/<id>/imagens/<categoria>/<nome>` | Imagem vinculada a registro ativo, com autorização |
| `GET /op/qualidade/tabela/produtos` | Consulta parametrizada ao FTM, por produto ou centro |
| `POST /op/qualidade/tabela/locais` | Cadastro de local com a autorização específica existente |
| `POST /op/qualidade/tabela/motivos-parada` | JSON com `name`, CSRF e mesma autorização de locais; retorna `reason` e status 201 |

Operações de escrita da nova tela exigem CSRF da sessão no header `X-CSRF-Token`. O token fica fora dos payloads de formulário capturados pelo log global legado. Campos obrigatórios, unidade/local/centro, opções Sim/Não, motivos, números, data e turnos são validados no backend. Não aplicável é exclusivo dos turnos numéricos. Um local ou centro desativado pode ser mantido em registro existente, sem permitir seu uso arbitrário em novos registros.

Os endpoints antigos permanecem por compatibilidade, inclusive a remoção legada via GET. A nova interface não usa esse GET nem as consultas antigas de produtos. Esta alteração não ativa CSRF global nem moderniza todas as validações e uploads dos formulários anteriores.

## Persistência, histórico e concorrência

`quality.py` mantém HTTP, autorização e composição. O pacote `app/routes/operation/quality_control/` concentra validações (`domain.py`), SQL parametrizado (`repository.py`) e coordenação/transações/anexos (`services.py`). Não há descoberta automática ou inicialização de serviço no bootstrap.

`JDT_OPE_QUAL` mantém suas 16 colunas. `JDT_OPE_QUAL_CONTROL` complementa cada ID com dados de parada, publicação, autoria, atualização, chave de envio e exclusão. A relação usa representação textual do ID e é lógica, sem presumir uma FK/tipo existente. `JDT_OPE_QUAL_HISTORY` registra ação, ator, data UTC e snapshots anteriores/posteriores. Não existe histórico retroativo inventado.

`JDT_OPE_QUAL_STOP_REASONS` guarda nome único, autor do cadastro e data UTC. O cadastro usa transação e chave primária sem distinção de maiúsculas/minúsculas para impedir duplicidades concorrentes; a violação de unicidade retorna 409. O motivo continua salvo como texto na ocorrência, preservando seu conteúdo histórico. Não há exclusão ou renomeação de opções nesta tela.

Criação, edição e exclusão da tela nova usam uma transação por operação. A revisão é um hash dos dados atuais e da atualização dos metadados; edições e exclusões com revisão desatualizada retornam 409. Leituras de escrita travam a ocorrência com `UPDLOCK, HOLDLOCK`. A chave de envio evita duplicar um cadastro reenviado pelo mesmo usuário, conferindo também os dados e hashes dos arquivos.

A alocação anual do ID mantém o formato legado e usa um application lock transacional no SQL Server. Cadastro antigo e novo compartilham esse lock. Escritas dos formulários anteriores também registram histórico na mesma transação, preservam os metadados novos e não editam registros excluídos. Não passam a exigir o token de revisão da tela nova.

As imagens novas usam a raiz `current_app.root_path/static/uploads/operation`, nomes únicos normalizados e limites de 10 MB por arquivo, 20 arquivos e 40 MB por envio. Há conferência de assinatura de PNG/JPEG/GIF/WEBP/BMP, canonicalização e vínculo ao registro antes do download. O envio HTTP admite até 42 MB incluindo o envelope multipart.

Imagens removidas do registro e arquivos de ocorrências excluídas são preservados para rastreabilidade; nenhuma limpeza automática foi adicionada. Se a operação falhar antes de tentar confirmar a transação, só arquivos criados naquela tentativa são candidatos à remoção. Em falha de confirmação do commit, os arquivos são retidos, pois o banco pode ter confirmado a gravação; o reenvio com a mesma chave permite recuperar o resultado sem duplicar. Arquivos legados são procurados na pasta por ocorrência e, como compatibilidade, na pasta antiga da categoria. A entrega estática anterior dos uploads não foi removida.

## Publicação e verificação autorizada

O script [20261028_create_qsb_control.sql](../../database/migrations/20261028_create_qsb_control.sql) é uma proposta para revisão e aplicação manual no banco `jdt`. **Não foi aplicado pelo agente nem é executado pela aplicação.**

O catálogo exige também [20261030_create_qsb_stop_reasons.sql](../../database/migrations/20261030_create_qsb_stop_reasons.sql), após o script do controle e antes da publicação do código de cadastro de motivos. Ele cria a tabela e a opção inicial, sem alterar as ocorrências. Revisar e aplicar em janela autorizada; a conta da aplicação precisa de leitura e inserção no catálogo. A aplicação não executa esse script automaticamente.

Antes de publicar o código correspondente, o responsável deve revisar o script, conferir no ambiente a chave/unicidade e os tipos/tamanhos reais das 16 colunas de `JDT_OPE_QUAL`, inclusive a capacidade das listas de imagens, e aplicar as tabelas complementares em janela autorizada. O código usa essas tabelas também nas consultas legadas; a publicação precisa ser coordenada. A conta da aplicação precisa poder obter `sp_getapplock` e ler/gravar as tabelas envolvidas. Não há alteração automática de schema, reflexão nem chamada a `create_all` nesta feature.

Depois da aplicação autorizada, a verificação funcional deve cobrir cadastro com múltiplas paradas, publicação Sim/Não, modal com/sem imagens, edição preservando/removendo anexos, conflito entre duas edições, reenvio de cadastro sem duplicação, exclusão lógica, permissões/CSRF e os formulários anteriores. Conferir também os filtros por período, unidade e publicação e os novos dados na visualização e impressão.

Na consulta por período, conferir os dois dias de limite, a ausência inicial de registros anteriores aos 15 dias, a busca histórica e com limites vazios, intervalo invertido/inválido e retorno do período padrão em `Limpar filtros`. Confirmar que buscar não apaga o cadastro em preenchimento e que uma resposta atrasada não desfaz um cadastro/edição/exclusão recém-confirmado. Ocorrências salvas fora do período permanecem gravadas, com aviso na tela para ajustar a consulta. Medir o carregamento no ambiente autorizado; não houve medição dinâmica pelo agente.

Para os motivos, conferir o `+` com usuário autorizado e sua ausência com usuário fora da autorização de locais; a tentativa direta deste último deve retornar 403. Cadastrar a partir da primeira linha e da edição, salvar uma ocorrência com o motivo novo e recarregar a tela para confirmar a persistência. Verificar vazio, limite de tamanho, duplicidade com variações de caixa/espaços e CSRF inválido. Confirmar que o cadastro rápido de Local Específico mantém seu comportamento.

O sistema não foi executado; a validação foi somente estática. Não há afirmação de implantação ou de aprovação funcional em produção.
