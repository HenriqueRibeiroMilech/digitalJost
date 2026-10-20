> **Registro histórico.** Pode conter decisões, caminhos e comandos superados. Consulte o [manual atual](../../README.md); este arquivo não define o padrão vigente.

# Revisão de segurança e melhorias para a modernização

Data: **13/10/2026**. Código analisado: commit `49ad011`, posterior à entrega 3b, com o backend moderno em `backend/` e o Vue em `frontend/`.

**Atualização posterior — entrega S1:** a leitura externa de TD e sessão foi implementada após esta revisão, conforme o [guia de configuração externa](configuracao-externa-td-sessao.md) e a seção 14 do plano. Os valores literais dessas duas categorias foram retirados do código atual; os demais achados e as referências abaixo registram o estado analisado na revisão. Por decisão do responsável, as credenciais atuais serão mantidas no ambiente, sem rotação nesta etapa. Provisionamento/publicação/verificação funcional e tratamento da exposição anterior permanecem pendentes.

**Atualização S1b — 14/10/2026:** o [carregamento de configuração privada e as outras integrações](configuracao-privada-integracoes.md) foram preparados, preservando os valores por decisão do responsável. Os valores identificados de FTM/Plex/Trace QR, MES, LDAP, Microsoft, SAP e Oracle saíram dos arquivos Python correspondentes; o `.env` privado criado nesta cópia de trabalho permanece fora do Git e o modelo não contém valores. Backups/histórico, rotação e demais achados continuam pendentes. Não houve teste de validade ou execução.

## 1. Escopo e limites

Esta revisão é estática: leitura de código, buscas e conferência de referências. Foram considerados a factory, os registros de `main.py`, autenticação, permissões, configurações e integrações, o backend de Eventos, exemplos de operações legadas de leitura/escrita/download, templates e o cliente Vue. Os achados abaixo têm exemplos rastreados; não representam uma auditoria exaustiva de cada handler, job ou integração.

Não houve execução, imports, consultas, requests à aplicação ou serviços corporativos, instalação, build, teste de credenciais, alterações de banco ou acesso ao servidor/PC da empresa. Foram consultadas referências públicas de documentação primária. Logs e uploads não foram abertos: a verificação desses diretórios limitou-se à quantidade de caminhos rastreados pelo Git. Valores de senhas, tokens, contas e strings de conexão foram omitidos durante a inspeção e não são reproduzidos aqui.

**Fato observado** significa uma característica verificável no código. O alcance em produção depende de IIS, rede, ACLs, contas, permissões e configurações efetivas que não foram inspecionadas. Nenhum achado comprova que houve exploração ou comprometimento.

As prioridades são qualitativas, sem pontuação CVSS: **P0** exige tratamento coordenado imediato de exposição; **P1** deve preceder a ampliação dos fluxos afetados; **P2** deve entrar nas próximas entregas de endurecimento. Todas as correções abaixo estão **propostas**, não implementadas nesta revisão.

## 2. Conclusão principal

Há segredos definidos diretamente em arquivos versionados e problemas de autorização, montagem de SQL, interpretação de dados como código e manipulação de arquivos no legado. A separação física entre `app/` e `backend/` melhora a organização, mas não isola a segurança: os dois continuam na mesma aplicação, com sessão e origem web compartilhadas. O engine moderno recebe a configuração de destino que vem do legado.

Uma falha em uma tela antiga pode atingir os dados e a sessão usados pela tela nova. Por isso, a base moderna deve ter contratos seguros próprios, acompanhados de correções focadas nas pontes e nos fluxos antigos de maior risco. O banco corporativo aprovado pode permanecer nesta fase; retirar segredos do código e restringir os acessos não exige trocar seu destino.

## 3. Inventário de segredos no código

Os arquivos abaixo são versionados. Foram observadas definições literais ou credenciais literais fornecidas a clientes de integração; sua validade, privilégios e eventual reutilização não foram verificados.

| Categoria | Evidência e consumidores conhecidos |
| --- | --- |
| SQL Server: TD, FTM, Plex, Plex de teste e Trace QR | `app/utils/constants.py:24`, `:32`, `:40`, `:48`, `:56`, com campos de usuário e senha nas conexões. Consumidos pela factory, `app/utils/db_utils.py`, rotas e jobs. |
| Conta da integração MES | `app/utils/constants.py:20`; utilizada por `app/routes/request/workcentersLogChange.py:1282`. |
| Chave de assinatura da sessão Flask | `app/config.py:51`. Afeta a sessão compartilhada pelo legado e pelo moderno. |
| Segredo de aplicação e credencial de usuário Microsoft | `app/utils/azure_utils.py:34` e `:36`. Consumidos pelo gerenciador de tokens e pelos utilitários de Teams/usuários. |
| Credencial de consulta LDAP | `app/routes/auth_routes.py:35`, `app/utils/security_utils.py:65` e `app/services/jobs/mon_mon_h_24_userCheck.py:19`. A rotação precisa considerar login, criação de usuários externos e serviço H24. |
| Credencial SAP/SOAP | `app/routes/reports/maintenance.py:41`, `:42`, passada a `HTTPBasicAuth`. |
| Credenciais em código desativado | Exemplos em `app/routes/jdt/temp.py:27` e `app/routes/reports/productiveHours.py:239`. Não foram tratadas como endpoints ativos; continuar no repositório ainda exige verificar se os segredos estão válidos. |

**P0 — causa e impacto:** distribuir o código também distribui material de autenticação. A chave de sessão exposta compromete a confiança na assinatura dos cookies, conforme o papel de [SECRET_KEY no Flask](https://flask.palletsprojects.com/en/stable/config/#SECRET_KEY); credenciais de integração podem permitir acessos fora do portal, conforme seus privilégios. Acesso restrito ao repositório reduz a audiência, mas não substitui gestão de segredos.

**Melhoria:** coordenar com TI/DBA os consumidores, a troca e a revogação dos segredos potencialmente expostos; provisionar a fonte externa antes de publicar o código que passa a exigi-la. Excluir o valor da versão atual não apaga versões anteriores. O tratamento de histórico/cópias e qualquer reescrita de Git precisam de escopo próprio; esta revisão não autoriza essas ações. A orientação de rotação e revogação segue a [OWASP sobre gestão de segredos](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html#27-secret-lifecycle).

A permanência em clones, cópias e histórico também precisa ser tratada pelos responsáveis, conforme as [orientações do GitHub para dados sensíveis](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository). Nenhuma remoção ou reescrita foi realizada aqui.

## 4. Achados nos fluxos ativos

### A01 — identidade fixa quando falta o token Windows — P1

**Evidência:** `app/routes/auth_routes.py:19` lê o token do IIS; `:26` escolhe uma identidade fixa quando o cabeçalho está ausente; o fluxo chega a `login_user(user)` em `:172`. A obtenção da identidade Windows em `:22` a `:25` também não está protegida por `finally` para garantir a reversão em uma exceção.

**Impacto:** uma execução fora da fronteira esperada pode autenticar como outra identidade. A exposição real da porta Python e o tratamento do cabeçalho pelo IIS não foram verificados; não se afirma que qualquer cliente externo consiga apresentar um token válido.

**Melhoria:** falhar sem identidade corporativa válida no ambiente operacional; restringir acesso direto ao processo Python e confiar no token somente pela fronteira controlada do IIS. Reverter impersonação e fechar o handle em `finally`. Um ambiente de teste deve fornecer identidade de teste explicitamente, com acesso isolado; não reutilizar o fallback fixo como validação de autorização.

### A02 — flags textuais usadas como booleanos — P1

**Evidência:** `app/models/user.py:29` e `:30` definem `admin` e `active` como strings. O cadastro em `app/routes/auth_routes.py:142` usa `admin='0'`. `app/routes/jdt/library.py:134` autoriza a gestão com `if current_user.admin`; outros exemplos estão em `app/routes/request/improvements.py:807` e `app/routes/request/processDeviation.py:2130`. O login usa `if not user.active` em `app/routes/auth_routes.py:168`.

**Impacto:** a string não vazia `"0"` é verdadeira em Python. Nessas expressões, ela pode satisfazer o teste de administrador ou deixar de bloquear um usuário inativo. Os valores atuais dos registros não foram consultados. O efeito depende da rota e das demais verificações; não se atribui o problema a todos os módulos.

**Melhoria:** normalizar flags na fronteira de identidade, com valores explicitamente aceitos e negação para estados desconhecidos. Corrigir os usos ativos por fluxos pequenos, sem depender apenas de um novo adaptador. `app/routes/jdt/userManager.py:27` já tem uma conversão explícita de administração, útil como referência; sua política combina flag e role e deve ser alinhada antes de reutilização. Manter autorização por ação e registro no servidor, conforme a [OWASP sobre autorização](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html).

### A03 — entrada do navegador interpolada em SQL — P1

**Evidência rastreada:** `POST /biblioteca/criar` passa pelo `before_request` em `app/routes/jdt/library.py:51`, lê JSON em `:83`, inclui seus campos `title` e `description` diretamente no SQL em `:84` a `:90` e executa `text(query)` sem parâmetros em `:92`. Outros exemplos usam `request.args['id']` nas consultas em `:174`, `:180` e `:211`.

**Impacto:** a entrada pode mudar o significado da consulta, com alcance limitado pelos privilégios da conta SQL. Estar autenticado não torna esses campos confiáveis; envolver uma string já interpolada com `text()` não a parametriza. Não foram enviados payloads ou executadas consultas.

**Melhoria:** manter o texto SQL fixo e fornecer valores por parâmetros; usar listas explícitas para identificadores/ordenação que não podem ser vinculados como valores. Migrar uma operação completa por entrega, incluindo leitores, escritores e transações. A base de Eventos já utiliza esse padrão. Referência: [prevenção de SQL injection da OWASP](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html#defense-option-1-prepared-statements-with-parameterized-queries).

### A04 — `eval` aplicado a dados persistidos — P1

**Evidência:** `app/routes/jdt/library.py:186` e `:225` interpretam listas de permissões do banco; `app/routes/operation/planning.py:784`, `:787`, `:950`, `:951` interpretam campos de consultas; `app/routes/request/improvements.py:393` interpreta `current_user.role`; há usos também em Comunicação. São módulos registrados em `main.py`, além de ocorrências em backups que não foram contadas como rotas ativas.

**Impacto:** dados adulterados podem passar a ser código executado no processo Python. A revisão não comprovou um caminho direto de uma request até cada `eval`; parte das entradas vem do banco, cuja integridade também pode ser afetada por outros escritores.

**Melhoria:** padronizar JSON e validar tipo, tamanho e conteúdo das estruturas. Formatos antigos podem exigir um parser limitado durante a transição, com validação e inventário dos escritores; não converter todos os dados por iniciativa do agente. O uso de `json.loads` e o fallback limitado de `_parse_role` em `app/routes/jdt/userManager.py:32` demonstram uma direção mais segura que `eval`, sem dispensar validação do resultado.

### A05 — proteção CSRF irregular — P1

**Evidência:** Eventos valida o token nas escritas em `backend/modules/events/routes.py:47`. Gerenciador de Demandas e Solicitações têm verificações próprias. Já o `before_request` de Biblioteca em `app/routes/jdt/library.py:51` e suas escritas examinadas não verificam CSRF; não foi encontrado um middleware global de CSRF na factory. O fluxo de Melhorias em `app/routes/request/improvements.py:366` é POST e também seleciona operações por query args em `:377` e `:400`; parâmetros na URL não significam que a operação seja GET.

**Impacto:** a autenticação compartilhada pode acompanhar uma request induzida por outra página. O sucesso de um ataque depende do formato aceito, método, cookies e controles efetivos de origem. Não se conclui que todas as rotas antigas estejam desprotegidas, nem que exigir JSON sozinho resolva o problema.

**Melhoria:** criar um mecanismo comum de CSRF no backend e aplicá-lo aos métodos que alteram estado, preservando o contrato vigente de Eventos durante a transição. Ao revisar um domínio, conferir todos os métodos e operações por `type`/`cmd`/query args; eventuais escritas em GET exigem adaptar também seus clientes. Introduzir proteção no legado por módulo para evitar interromper todos os clientes de uma vez. `SameSite` é uma defesa adicional, conforme a [OWASP sobre CSRF](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).

### A06 — nomes/caminhos e autorização de anexos — P1

**Evidência:** `app/routes/jdt/library.py:242` e `:278` salvam arquivos usando `file.filename` em caminhos montados por strings. `GET /biblioteca/conhecimentos/download`, em `:288`, utiliza `request.args['arq']` no caminho em `:290` e envia o arquivo em `:292`; o handler não repete a verificação de permissão do conhecimento usada em `:225`. Na montagem de ZIP de rastreabilidade, `app/routes/factoryRegister/assembly.py:517` a `:535` utiliza nomes do banco em `os.path.join`, sem uma conferência visível de permanência no diretório permitido.

**Impacto:** há risco de atravessamento de diretórios e leitura de anexos fora do escopo autorizado, conforme os nomes aceitos e a conta Windows. Não houve abertura de arquivos nem tentativa de exploração. Não se atribui o mesmo problema aos trechos que já usam `secure_filename` em Desvios ou às rotas com validações próprias.

**Melhoria:** localizar anexos por identificador, conferir permissão sobre o registro, gerar o nome físico no servidor e verificar o caminho canonicalizado dentro de uma raiz permitida. Aplicar limites por operação e tipos permitidos, além do limite global de 200 MiB observado na factory. Para novos módulos, guardar anexos fora de `backend/static/` e do webroot; arquivos estáticos modernos devem conter apenas recursos públicos do frontend. Referência: [uploads seguros da OWASP](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).

### A07 — uploads sob a pasta estática e dados rastreados — P1

**Evidência:** `app/config.py:82` e `:84` mantêm uploads dentro de `app/static/`, servido pela aplicação. A rota estática não executa a autorização do blueprint da funcionalidade. Na cópia inspecionada, o Git rastreia **11 caminhos em `app/static/uploads/`** e **596 caminhos de logs**, considerando `logs`, `log` e arquivos `*.log`.

**Impacto:** arquivos potencialmente confidenciais podem ser distribuídos pelo repositório, pelos pacotes ou por acesso estático sem autorização por registro. Seu conteúdo não foi inspecionado; acesso efetivo via rede depende do IIS. Estar no `.gitignore` não retira um arquivo já rastreado ou seus snapshots anteriores.

**Melhoria:** definir armazenamento operacional fora da área pública, rotas de download autorizadas e política de retenção/ACL/backup. Preparar separadamente o tratamento dos arquivos rastreados e do histórico; não excluir, mover ou abrir dados operacionais nesta revisão. Uma cópia antiga de segurança deve ficar em armazenamento protegido, sem ser servida pelo site.

### A08 — dados do banco inseridos em HTML/JavaScript — P1

**Evidência rastreada:** a Biblioteca recebe título/descrição no cadastro e os devolve na gestão em `app/routes/jdt/library.py:127` a `:129`. `app/templates/jdt.library/library_manage.html:219` insere os dados com `|safe`; em `:293` a `:295`, `item.title` e `item.description` entram em uma string atribuída a `innerHTML`. O mesmo padrão aparece no filtro em `:348` a `:350`.

**Impacto:** conteúdo de usuários pode ser interpretado como HTML ou romper o contexto do script, afetando a sessão e requests da vítima. O caminho inseguro foi observado; não foi executado um payload nem determinado todo o alcance de cada campo.

**Melhoria:** passar dados estruturados com `tojson`, montar elementos usando conteúdo textual e evitar HTML bruto para campos de cadastro. Em Vue, manter interpolações escapadas e restringir `v-html` a conteúdo sanitizado quando houver necessidade real de HTML. Os cards de Eventos exibem nome/descrição por interpolação normal. Referência: [prevenção de XSS no DOM da OWASP](https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html#rule-6---populate-the-dom-using-safe-javascript-functions-or-properties).

### A09 — validação de certificados desativada — P1

**Evidência:** `app/utils/data_utils.py:65`, `app/utils/teams_utils.py:199`, `:203` e `app/routes/jdt/userManager.py:820`, `:867` usam `verify=False`. As conexões SQL de `app/utils/constants.py` usam `TrustServerCertificate=yes`. Os clientes LDAP examinados usam `use_ssl=False`.

**Impacto:** os primeiros casos desativam validação HTTPS, segundo o [contrato de verificação do Requests](https://requests.readthedocs.io/en/latest/user/advanced/#ssl-cert-verification); a opção SQL dispensa validação do certificado quando utilizada, conforme a [configuração do driver ODBC Microsoft](https://learn.microsoft.com/en-us/sql/connect/odbc/using-azure-active-directory?view=sql-server-ver17#new-andor-modified-dsn-and-connection-string-keywords). A criptografia efetiva das conexões SQL, LDAP signing/sealing e a configuração de certificados corporativos não foram verificadas. `use_ssl=False` não demonstra, sozinho, transmissão da senha LDAP em texto puro.

**Melhoria:** provisionar a cadeia de confiança corporativa e habilitar validação de certificados por integração, com plano de compatibilidade. Conferir os endpoints SOAP efetivos e os requisitos LDAP com TI. Não substituir todas as opções simultaneamente, porque a disponibilidade depende dessa preparação no servidor e nos serviços Windows.

### A10 — payload completo na auditoria e detalhes de erro — P1

**Evidência:** `app/config.py:148` e `:156` a `:164` coletam query args, JSON/form e os enviam à auditoria. `app/utils/security_utils.py:15` e `:16` serializam o conteúdo sem filtragem visível. O handler em `app/errors.py:29` e `:30` encaminha URL, traceback e identidade a Teams. Há retorno de `str(e)` ao navegador em `app/routes/factoryRegister/assembly.py:483`.

**Impacto:** novos campos sensíveis podem entrar automaticamente em registros, mensagens e erros. Não foram abertos logs nem confirmados valores sensíveis já gravados. Auditoria parametrizada protege a consulta de gravação, mas não protege a confidencialidade do conteúdo registrado.

**Melhoria:** registrar por lista explícita de campos e aplicar mascaramento central antes de qualquer destino. Separar trilha de negócio de diagnóstico técnico, usar identificador de correlação e mensagens externas genéricas. Preservar a rastreabilidade necessária com acesso e retenção controlados. Nunca registrar corpo completo por padrão, cookies, cabeçalhos de autenticação, tokens, senhas ou URL de engine/conexão. `hide_parameters=True` no engine moderno ajuda com parâmetros SQL, mas não corrige os outros destinos de logs nem garante ocultação de uma URI.

### A11 — destino de redirecionamento do login sem validação — P2

**Evidência:** `app/routes/auth_routes.py:174` a `:178` copia o parâmetro `next` para `redirect` sem conferência de origem/esquema.

**Impacto:** permite encaminhar o usuário para um destino controlado por outra parte após o login, conforme o formato aceito pelo cliente.

**Melhoria:** aceitar somente caminhos/destinos internos autorizados e usar a home como padrão seguro. Revisar junto dos links, redirects e da ponte de identidade, preservando os destinos internos atualmente utilizados.

### A12 — sessão e cabeçalhos sem endurecimento explícito — P2

**Evidência:** não foram encontradas definições explícitas de `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`, `TRUSTED_HOSTS` ou cabeçalhos CSP/HSTS/nosniff nos arquivos de configuração examinados. A chave de sessão é literal. A configuração efetiva do IIS e os cabeçalhos das respostas não foram consultados; não se afirma ausência desses controles na publicação.

**Melhoria:** documentar e conferir cookies `Secure`, `HttpOnly` e `SameSite`, domínio/path, expiração e descarte de sessão ao alterar identidade. Configurar confiança no proxy e hosts aprovados a partir da hospedagem real. Planejar CSP inicialmente em modo de relatório e limites de framing compatíveis com os iframes e scripts inline do legado; HSTS depende de HTTPS corretamente estabelecido. Referência: [segurança de cookies e cabeçalhos no Flask](https://flask.palletsprojects.com/en/stable/web-security/).

### A13 — integrações e DDL no ciclo de inicialização — P2

**Evidência:** `app/config.py:216` chama `db.create_all()` na factory. `app/utils/azure_utils.py:85` instancia um objeto que inicia thread em `:48`; `app/utils/dynamic_constants.py:48` também inicia thread. Esses módulos chegam à aplicação por imports de rotas/utilitários ativos, como Usuários e Teams.

**Impacto:** iniciar ou importar a aplicação pode acessar recursos corporativos, mesmo quando o objetivo é validar outra parte. A conta operacional pode precisar de privilégios além dos casos de uso; seus grants não foram verificados. Jobs e processos continuam na mesma fronteira operacional do legado.

**Melhoria:** separar gestão de schema da inicialização HTTP e explicitar o ciclo de vida das integrações, em entregas próprias. Mapear rotas, serviços Windows e escritores relacionados antes de reduzir privilégios. O backend moderno já evita criar engines no import e dispõe de pool limitado; a factory compartilhada continua carregando os efeitos antigos.

## 5. Controles existentes que devem ser preservados

- Eventos usa SQL parametrizado, transação explícita nas escritas, identificação do autor pelo usuário da sessão e validação Pydantic de campos/tamanhos/paginação.
- API e shell de Eventos verificam sessão e permissão no backend; escritas exigem token aleatório e comparação com `hmac.compare_digest`.
- O cliente Vue usa requests de mesma origem e o cabeçalho CSRF; os cards de Eventos não renderizam nome/descrição como HTML bruto.
- O engine moderno limita conexões, usa `pool_pre_ping`, oculta parâmetros SQL e recebe dependências explicitamente. Seu URI fica fora do `repr` de `BackendConfig`.
- Gerenciador de Demandas/Solicitações já demonstra separação de HTTP, regras e repositório, CSRF próprio e downloads com verificações que podem servir de referência. Não se deve declarar esses módulos integralmente auditados a partir dessa amostra.

Os controles de Eventos não substituem correções da chave de sessão, do login, da auditoria global ou de uma tela legada que compartilha a mesma origem.

## 6. Configuração segura para as duas arquiteturas

### Fonte de segredos e convivência

1. Inventariar cada segredo por finalidade, proprietário, consumidores e processo Windows/IIS; registrar nomes e categorias, nunca valores neste repositório.
2. Escolher a fonte aprovada: cofre corporativo, quando disponível, ou configuração externa ao Git e ao webroot, com ACL restrita às identidades dos processos que realmente precisam dela. Variáveis de ambiente são uma forma de injeção, não um cofre por si só.
3. Preparar essa fonte no PC/servidor e nos serviços afetados antes de publicar a leitura obrigatória de configurações. Não mover segredos para um `web.config` versionado ou para outro arquivo Python.
4. Preservar temporariamente os nomes de configuração usados pelo legado, por um adaptador simples. Manter engines separados e o mesmo destino TD aprovado; novos módulos recebem o engine central, sem ler credenciais diretamente.
5. Exigir os valores na composição, sem fallback para senha/chave literal e sem produzir conexões, tokens ou threads durante imports da base nova.
6. Coordenar rotação/revogação e reinício dos consumidores com TI. Preparar retorno compatível com as credenciais válidas; nunca voltar a usar um segredo revogado. A troca da chave Flask deve prever encerramento das sessões; não manter uma chave exposta como fallback para preservar cookies antigos.

O backend pode receber depois uma conta SQL dedicada, com grants restritos às funcionalidades migradas, mantendo o mesmo banco. Essa é uma alteração de acesso a ser definida com DBA, não uma mudança automática nesta entrega. O portal HTTP e os jobs devem ter permissões compatíveis com responsabilidades distintas; não se presume que as contas atuais sejam administrativas.

### Fronteira com o frontend

O navegador deve receber apenas configurações públicas, contratos e dados autorizados. Credenciais SQL/LDAP/SAP, segredo Microsoft e chave Flask pertencem ao servidor. Nunca colocá-los em variáveis `VITE_*`: elas podem ser incorporadas ao código entregue ao navegador, conforme a [documentação de ambiente do Vite](https://vite.dev/guide/env-and-mode#env-variables).

O build gerado e seu manifesto são recursos públicos; anexos de usuários são dados operacionais. Separar suas pastas e permissões, mesmo que ambos sejam arquivos. A mudança do build para `backend/static/app/` não autoriza colocar documentos privados ali.

## 7. Sequência de melhorias recomendada

| Entrega proposta | Escopo pequeno | Evidência necessária para liberação |
| --- | --- | --- |
| S1 — configuração externa | Remover segredos literais por categoria, começando por sessão/TD, preservando os contratos legados e o destino corporativo. Planejar também LDAP, Microsoft, MES/SAP e serviços. | Configuração provisionada; todos os consumidores mapeados; diff sem valores; ausência de fallback literal. |
| S2 — rotação coordenada | Troca/revogação pelos responsáveis, com tratamento de sessões, serviços, cópias e histórico. | Confirmação dos proprietários e verificação em janela autorizada; agente não testa credenciais. |
| S3 — identidade e autorização | Normalizar flags, tratar ausência de token, validar destino do login e corrigir operações específicas de maior risco. A ponte moderna deve reutilizar apenas uma política definida. | Casos de usuário permitido/negado/inativo/desconhecido em ambiente autorizado; nenhum falso administrador pela string `"0"`. |
| S4 — SQL, interpretação e saída | Corrigir o fluxo de Biblioteca e depois outros exemplos ativos: parametrização, retirada de `eval`, serialização segura e renderização textual. | Cadeia HTTP → entrada → banco → interface conhecida; contratos/transações preservados e verificações autorizadas. |
| S5 — CSRF, anexos e logs | Extrair CSRF moderno, adaptar módulos legados por partes, proteger arquivos por registro e filtrar auditoria/erros. | Clientes compatíveis, rejeições conferidas, anexos privados fora de static e logs sem campos sensíveis. |
| S6 — hospedagem e inicialização | Certificados, cookies/headers, ACLs, privilégios, schema fora do startup e integrações com ciclo explícito. | Configuração efetiva aprovada com TI; verificações específicas no IIS/serviços sem regressão dos consumidores. |

São propostas independentes, não uma autorização para realizar todas juntas. A rotação exige coordenação e não deve ser adiada apenas porque o trabalho no código ainda está em planejamento. A implementação pode avançar por análise estática; liberação e verificações dinâmicas continuam exigindo ambiente e escopo autorizados. Correções pontuais de alto risco no legado podem preceder sua migração completa.

## 8. Verificações ainda necessárias

- Estado efetivo do IIS: autenticação Windows/anônimo, tratamento do token, acesso direto à porta Python, HTTPS, headers e locais acessíveis por static.
- Inventário/grants das contas SQL e das integrações, permissões Microsoft e ACLs das identidades do portal e dos quatro serviços Windows.
- Conteúdo/retenção dos logs, trilhas no banco, cópias, uploads e artefatos, somente por responsáveis autorizados; não foram inspecionados aqui.
- Mapeamento completo de handlers, ações por `type`/`cmd`, autorização por registro e jobs escritores antes da correção/migração de cada domínio. O H24 atualiza `JDT_USER_DETAILS` e deve acompanhar mudanças de identidade/configuração.
- Versões realmente instaladas no servidor e no PC comparadas com os manifests e avisos oficiais de segurança. Não foram executados scanners de dependências nem analisados todos os CVEs; esta revisão não certifica ausência de vulnerabilidades em pacotes.
- Evidências de testes positivos/negativos em ambiente autorizado, incluindo rollback e retorno de pacote, sem usar a identidade fixa de fallback para validar permissões.

**O sistema não foi executado; a validação foi somente estática.** Nenhum segredo foi alterado/revogado, nenhuma vulnerabilidade foi corrigida no código e nenhum arquivo operacional foi modificado por esta revisão.
