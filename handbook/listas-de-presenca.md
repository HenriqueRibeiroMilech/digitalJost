# Listas de presença de Eventos

## Uso e comportamento implementado

Em `/app/eventos`, abra um evento e selecione **Listas de presença**. Crie uma lista pelo nome e abra-a para ver Matrícula, Nome e Setor. Um evento pode ter várias listas, e uma pessoa pode participar de listas diferentes. A listagem de listas usa seis itens por página; participantes usam 25, com os mais recentes primeiro.

**Iniciar preenchimento por leitor** abre uma tela que ocupa a janela para os convidados. Ela usa a sessão autenticada do responsável pelo evento; não é uma página pública nem uma nova forma de login. A tela informa “Encoste o crachá até receber a aprovação” e mantém um campo de texto preparado para o leitor que funciona como teclado, com ou sem Enter ao final.

Ao receber caracteres, a tela mostra “Confirmando presença…” e espera **2 segundos sem alteração no campo** antes de validar e enviar. Cada alteração reinicia a espera, permitindo conferir o código completo em vez de gravar assim que chegar ao 12º dígito. O Enter é aceito sem antecipar nem reiniciar a contagem; quando o leitor não o envia, a confirmação automática usa a mesma espera. Enter com campo vazio, inclusive tardio ou repetido após uma leitura, é ignorado e preserva o resultado exibido.

Uma leitura é aceita somente quando contém exatamente **12 dígitos de 0 a 9**. A matrícula é texto em todas as camadas para preservar zeros à esquerda. Não são retirados prefixos, espaços ou caracteres extras, nem truncadas leituras longas. Uma leitura incompleta, longa ou com outros caracteres mostra “Tente novamente”, limpa o campo e não envia uma gravação à API. O backend repete a validação, inclusive para requisições feitas fora da interface.

Após estabilizar, uma leitura válida continua mostrando “Confirmando presença…” enquanto aguarda a API. **“Presença confirmada!” só aparece após a transação ser confirmada pelo servidor.** A tela informa que o crachá pode ser retirado e retorna à instrução em 3,5 segundos ou ao iniciar a próxima leitura. O campo aceita correções durante a espera de estabilização e fica somente leitura durante a gravação na API; leituras nesse envio pendente são descartadas.

A matrícula é única dentro de uma lista. Uma repetição não cria outra linha e, quando nome e setor estão completos, retorna “Sua presença já está registrada”. Se faltarem dados, pode completá-los ou apresentar o aviso de identificação incompleta. Isso permite também conferir uma leitura quando uma falha de comunicação deixa o resultado incerto. Não há reenvio automático de escritas. Em falha de conexão, a tela pede uma nova aproximação; em falha de segurança da sessão, sessão expirada, acesso negado ou lista ausente, bloqueia novas leituras e orienta chamar o responsável.

Nome e setor são preenchidos automaticamente por uma consulta LDAP na arquitetura nova. Para crachás com prefixo `2300`, o cliente usa os oito dígitos finais na busca, preservando os 12 dígitos na presença. Solicita `description`, `displayName` e `department`; busca candidatos que contenham a matrícula e exige uma correspondência exata no **segundo campo** de `description`, separado por ponto e vírgula, conforme o login legado. Espaços ao redor do campo são ignorados, e campos posteriores são permitidos. Quando não há separador, aceita o atributo contendo somente a matrícula completa de oito dígitos. Uma ocorrência em outro campo ou dentro de um número maior não identifica o funcionário. O campo nome vem de `displayName` e setor vem de `department`. Valores ausentes, vazios, inválidos ou maiores que os 200 caracteres UTF-16 suportados pelas colunas ficam nulos e aparecem como “Não informado”.

A exigência anterior de matrícula no fim de `description`, tanto no filtro LDAP quanto na validação local, podia descartar registros compatíveis com o parser do login legado quando havia outros campos após a matrícula. A busca atual permite esses campos e valida os candidatos antes de selecionar: zero correspondências exatas gera `not_found`, duas gera `ambiguous`, e resultado truncado continua gerando `ambiguous` mesmo quando um dos candidatos aparenta conferir. A correção permanece no cliente moderno, sem alterar rotas ou utilitários do legado.

Se o diretório estiver indisponível, não houver correspondência única ou o prefixo não for suportado, **a presença é salva mesmo assim**, com aviso de identificação incompleta na tela. O formato válido não é tratado como prova de identidade; a consulta é complementar e não autentica o convidado. O sucesso completo continua verde; identificação incompleta usa mensagem informativa azul, deixando claro que a presença foi salva. Uma nova leitura de presença incompleta tenta preencher somente os campos que faltam, sem duplicar a matrícula. Presenças já completas dispensam nova consulta. Não há atualização em lote dos registros antigos.

O foco volta ao campo após cada leitura e quando a janela recupera o foco. Se o usuário mover o foco, uma ação permite ativar o campo novamente; partes de uma leitura e sua espera de estabilização são canceladas ao sair do campo. Durante a captura, a navegação do evento fica bloqueada. **Encerrar leitura** cancela uma leitura ainda em estabilização, restaura a lista e o foco no botão de iniciar, ficando indisponível durante uma gravação na API. Os temporizadores são removidos ao desmontar a tela.

Presenças confirmadas atualizam o cache da primeira página. A tabela consulta novamente ao sair da captura e, enquanto aberta sem captura e com a aba do navegador ativa, a cada cinco segundos. O total das listas é atualizado ao retornar à coleção. Falha nessa atualização não refaz uma presença já salva.

## API e responsabilidades

Base: `/api/v1/events/<event_id>/attendance-lists`.

| Método e caminho | Entrada e retorno |
|---|---|
| GET na base | `page` e `per_page`; itens `{id, event_id, name, total}`, paginação e capacidades. |
| POST na base | `{name}`, texto de 1 a 120 caracteres após trim; retorna a lista criada com total zero e HTTP 201. |
| GET `/<list_id>` | Lista, total e capacidades da sessão. |
| GET `/<list_id>/entries` | `page` e `per_page`; itens `{id, registration, name, department}`, paginação e capacidades. |
| POST `/<list_id>/entries` | `{registration}` como string; HTTP 200 com `{item, created, lookup_status}` tanto na criação quanto na repetição. Nome e setor vêm exclusivamente do backend. |

`lookup_status` é `complete` quando o registro retornado possui nome e setor; `partial` quando algum dado está ausente; `not_found` para matrícula não localizada; `unavailable` para falha de configuração/consulta; `ambiguous` para múltiplos resultados ou resultado truncado; `unsupported_badge` para um prefixo diferente de `2300`. Esse status é retornado pela operação, sem nova coluna no banco.

Paginação usa o contrato compartilhado: página mínima 1 e de 1 a 100 itens por página. JSON inválido retorna 422. Evento ausente na coleção ou lista ausente/no evento errado retorna 404. A listagem de registros é sempre restrita à lista cujo vínculo foi verificado pelo serviço.

Todas as rotas usam a guarda de identidade, o perfil GENERAL e o CSRF compartilhados. Serviços exigem `events.attendance.read`, `events.attendance.create` ou `events.attendance.register`, mapeados explicitamente em `backend/bootstrap.py`. Capacidades `can_create` e `can_register` orientam a interface; não substituem a autorização do backend.

O serviço delimita transações na engine TD. A criação de lista mantém o evento existente com HOLDLOCK durante a escrita. O registro verifica permissão e vínculo antes do LDAP, encerra a leitura SQL e faz a consulta externa sem reter conexão/trava SQL. Em seguida, revalida a lista, trava-a com UPDLOCK/HOLDLOCK e insere ou completa campos nulos/vazios. A constraint UNIQUE é uma defesa adicional contra duplicidade. Consultas e escritas usam parâmetros SQL. Não há novos jobs, uploads, e-mails ou notificações.

O cliente em `backend/integrations/employee_directory.py` tem configuração própria e conexão por consulta, usando NTLM, modo somente leitura, sem seguir referrals e com filtro escapado, no máximo dois resultados e limites de tempo. Não busca schema nem dados no startup; encerra a conexão em `finally` e não devolve detalhes LDAP/credenciais ao navegador. A configuração vem de `backend/config.py` e dos valores privados `DJ_LDAP_USER`/`DJ_LDAP_PASSWORD`, sem importar utilitários ou rotas do legado. Os padrões de host/base são os mesmos do cliente antigo; opções e SSL estão em [Arquitetura modernizada](arquitetura-modernizada.md). A dependência `ldap3==2.9.1` já consta no projeto. Veja também as referências oficiais de [conexão](https://ldap3.readthedocs.io/en/latest/connection.html) e [busca](https://ldap3.readthedocs.io/en/latest/searches.html).

## Banco e publicação

O arquivo [20261015_create_dj_event_attendance.sql](../database/migrations/20261015_create_dj_event_attendance.sql) é uma **proposta para revisão e aplicação pelo responsável pelo banco**, em ambiente e janela autorizados. O agente não o executou, e a aplicação não o executa automaticamente.

Ele requer `dbo.DJ_EVENTS` e cria:

- `dbo.DJ_EVENT_ATTENDANCE_LISTS`: vínculo com evento, nome, autor e data UTC de criação.
- `dbo.DJ_EVENT_ATTENDANCE_ENTRIES`: vínculo com lista, matrícula, nome e setor anuláveis, autor e data UTC de criação.
- FKs, índices para listagem, UNIQUE por lista/matrícula e CHECK para os 12 dígitos.

As FKs têm exclusão em cascata: excluir um evento também exclui suas listas e presenças. A confirmação na interface avisa esse efeito. Não há edição/exclusão individual de listas ou participantes nesta etapa.

Depois da revisão e aplicação do SQL, publique backend e build compatíveis juntos, conforme [Servidor e publicação](servidor-e-publicacao.md). Os componentes Volt necessários já estão no repositório; não há dependência nova. Em retorno de código, as tabelas podem ser mantidas sem remoção de dados. A exclusão de evento pelo código anterior também seguirá as novas cascatas do banco, caso sejam mantidas.

A integração LDAP usa as colunas `name` e `department` já existentes: não requer outra migration. Confira o par privado LDAP e a conectividade no ambiente autorizado, e publique a API/build compatíveis com `lookup_status`. O cliente HTTP possui timeout de dez segundos; ampliar os tempos LDAP exige considerar também a espera do banco e esse limite total. A consulta foi implementada por leitura estática e não foi executada pelo agente.

## Diagnóstico isolado da consulta por matrícula

O módulo `backend.integrations.diagnose_employee_directory` permite ao responsável testar a consulta no computador Windows com acesso à rede corporativa, usando a `.venv` já existente. Na raiz do repositório, ao lado de `main.py`, execute no PowerShell:

```powershell
.\.venv\Scripts\python.exe -B -m backend.integrations.diagnose_employee_directory
```

Informe o crachá completo de 12 dígitos com prefixo `2300` quando solicitado. A entrada fica oculta, preserva zeros e não entra no histórico do comando. Se o leitor não enviar Enter, pressione Enter manualmente. Não há leitura contínua nem registro de presença.

**Escopo:** uma execução, uma matrícula, uma conexão LDAP com no máximo um bind e duas buscas somente leitura. A primeira usa o filtro atual, que contém a matrícula; a segunda reproduz o filtro legado, que termina com a matrícula. Cada busca retorna no máximo dois candidatos e usa os tempos limite configurados. Ambas usam o parser atual para informar a correspondência exata. O diagnóstico não chama a rota antiga de login, não inicializa Flask, não importa `app`/`main`/`bootstrap`, não abre banco e não grava arquivos. A opção `-B` impede a geração de bytecode pelo Python. Não executa o fluxo HTTP ou de gravação da presença.

Quando as duas buscas terminarem com código zero e nenhum candidato, compare também com o filtro usado pelo login do portal:

```powershell
.\.venv\Scripts\python.exe -B -m backend.integrations.diagnose_employee_directory --by-login
```

Esse modo pede o crachá e o **login Windows da mesma pessoa**, sem domínio nem sufixo de e-mail. Os dois valores ficam ocultos. Acrescenta uma terceira busca exata por `mailNickname`, mantendo uma única conexão/bind, modo somente leitura e limite de dois candidatos por busca. Não cria usuário, não faz login no portal e não grava presença. O login informado não é incluído no relatório.

Se `por_login` retornar um candidato, os indicadores comparam o `description` dessa pessoa com o crachá informado. Por exemplo, `igual_sem_zeros_iniciais: true` com `igual_matricula: false` indica diferença de preenchimento com zeros, mas não autoriza alterar a regra da aplicação sem conferir a identidade. `resultado_pela_regra_atual` continua avaliando a correspondência com o crachá, mesmo na consulta por login; não indica se o login foi encontrado. Se as três buscas retornarem zero, é preciso conferir login, cadastro, base de busca e visibilidade de leitura com o responsável pelo diretório. Bind bem-sucedido, sozinho, não prova acesso de leitura a todos os usuários/atributos.

A configuração é a mesma do cliente moderno: ambiente do processo tem prioridade sobre `.env` ou `DJ_ENV_FILE`. O comando importa somente a configuração e o cliente independente, além das bibliotecas já existentes; não instala dependências. Se o portal estiver no IIS com ambiente ou conta diferentes, um resultado positivo no terminal não prova que o processo do IIS recebeu a mesma configuração.

O relatório JSON não inclui crachá, matrícula, nomes, setores, conteúdo de `description`, DN, host, usuário, senha ou mensagens brutas do LDAP. Mostra somente etapa, código numérico LDAP, duração, contagem, tamanhos e indicadores de correspondência/presença dos campos. Apenas os oito primeiros campos de `description` têm a estrutura detalhada. As comparações com crachá inteiro e sem zeros são **indicadores de diagnóstico**; não alteram as regras de identificação da aplicação.

| Resultado | Interpretação |
|---|---|
| Falha em `dependencias` ou `configuracao` | O teste ainda não consultou o LDAP. Conferir dependências/configuração no ambiente autorizado. |
| Falha em `conexao_e_bind` | A conexão/autenticação não terminou. Código 49 indica credenciais rejeitadas; exceções de socket podem indicar rede ou timeout. O tipo da exceção é mostrado sem mensagem privada. |
| `codigo_ldap: 0`, zero candidatos | O diretório não devolveu registros para aquele filtro/base/conta. Não é possível concluir apenas disso que a pessoa não existe. |
| Candidatos, mas `aceito_pelo_parser_atual: false` | A busca encontrou dados, mas o segundo campo de `description` (ou o atributo inteiro sem separador) não coincide com os oito dígitos finais. Os tamanhos e indicadores ajudam a identificar o formato sem expor valores. |
| `codigo_ldap: 4` | Resultado truncado; permanece `ambiguous`, sem selecionar uma pessoa. |
| `resultado_pela_regra_atual: complete` | A busca isolada encontrou uma correspondência única com nome e setor utilizáveis. Conferir diferenças de ambiente/publicação se a tela continuar sem nome. |
| `resultado_pela_regra_atual: partial` | Houve correspondência única, mas nome ou setor está ausente/inválido/acima do limite. |

O código de saída zero significa que todas as consultas do modo escolhido terminaram, mesmo que o resultado seja `not_found` ou `ambiguous`; 1 indica falha e 2 indica entrada inválida ou interrupção. Compartilhe somente o relatório sanitizado para análise.

O agente preparou este diagnóstico por análise estática e não o executou. Pelo [AGENTS.md](../AGENTS.md), a execução pelo agente exige autorização explícita com o comando acima, o ambiente e o escopo descrito; o pedido genérico para testar não autoriza conexão corporativa.

## Conferência em ambiente autorizado

A entrega recebeu somente análise estática. Build, migração, navegador, leitor físico e concorrência no SQL Server precisam de validação pelo responsável, conforme `AGENTS.md`:

1. Criar duas listas no mesmo evento e outra em evento diferente; conferir isolamento e paginação.
2. Ler 12 dígitos com e sem Enter, inclusive com zero inicial na matrícula de oito dígitos; conferir a espera de dois segundos desde a última alteração, uma linha persistida e nome/setor preenchidos quando houver correspondência única. Enters repetidos ou tardios não devem apagar o sucesso nem gerar outra tentativa vazia.
3. Ler menos/mais de 12 caracteres e valores com letras ou espaços; conferir “Tente novamente” sem nova presença e a validação 422 da API.
4. Repetir a matrícula na mesma lista, inclusive simultaneamente em duas sessões autorizadas; conferir uma linha e a resposta de presença existente. A mesma matrícula em outra lista deve ser aceita.
5. Conferir foco inicial, leituras consecutivas, perda/retorno de foco e bloqueio durante gravação. Alterar o código durante a espera deve reiniciar os dois segundos; acrescentar um 13º caractere deve invalidar a leitura completa. Perder foco, encerrar ou desmontar a tela durante a espera deve cancelá-la sem gravar depois.
6. Conferir falha de conexão, resultado incerto, nova leitura idempotente, sessão expirada e lista/evento ausente. Nenhuma falha deve mostrar confirmação falsa.
7. Conferir acesso sem permissão, CSRF ausente e lista informada com evento errado; não devem permitir ler ou registrar os dados.
8. Em dados de conferência autorizados, verificar o aviso e a cascata ao excluir um evento. O agente não cria nem remove dados para essa validação.
9. Conferir matrícula no segundo campo com conteúdo posterior e espaços ao redor; deve preencher nome/setor. Também conferir atributo contendo somente os oito dígitos. Matrícula em outro campo, como parte de um número maior, resultado múltiplo/truncado, ausência de nome/setor, valores longos e prefixo diferente de `2300` não devem associar dados de outra pessoa. Com resultado completo, um candidato válido e outro com matrícula diferente deve selecionar somente a correspondência exata; dois candidatos válidos ou resultado truncado devem gerar `ambiguous`.
10. Conferir LDAP indisponível, timeout e falha de bind; deve salvar presença incompleta, sem vazar detalhes internos. Repetir essa presença após a recuperação deve completar somente campos faltantes, sem nova linha. Presença completa não deve consultar o LDAP novamente.
11. Conferir que a conexão SQL é liberada antes da consulta externa, que a conexão LDAP é encerrada e que exclusão concorrente da lista durante o LDAP é revalidada antes de gravar. O login/sessão do convidado não deve ser alterado.
