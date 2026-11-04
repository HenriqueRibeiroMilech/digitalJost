# Ambiente, servidor e publicação

Guia oficial de preparação, configuração e implantação no Windows/IIS. Os comandos são procedimentos para o responsável em ambiente autorizado; não autorizam um agente a executar o sistema. Não houve instalação, build, conexão ou publicação nesta revisão documental.

Revisado em **20/10/2026** contra configuração versionada e registros históricos de [ambiente](../historico/docs/ambientes-desenvolvimento-servidor.md), [configuração privada](../historico/docs/configuracao-privada-integracoes.md) e [publicação anterior](../historico/docs/publicacao-modernizacao-servidor.md). Os caminhos informados e o Python instalado precisam ser confirmados antes de uma entrega; relato de instalação antiga não comprova a versão atual do servidor.

## 1. Ambientes e processos

Referência informada: Python 3.13 de 64 bits, Windows/IIS com `httpPlatformHandler`, projeto em `I:\IIS\Digital_Jost` e servidor sem internet. Confirme o ambiente real antes da manutenção. O banco corporativo usado localmente não é um ambiente isolado.

| Processo | Interpretador e cuidado |
|---|---|
| Site | `.venv\Scripts\python.exe` do projeto, conforme `web.config`. |
| H24 (`RunH24Scheduler`) | Ambiente informado usa `C:\python13\pythonservice.exe`; instalações correspondentes usam `C:\python13\python.exe`. |
| S30, M5 e Auto | Conferir executável e conta de cada serviço; não presumir a `.venv` do site. |

S30 acompanha monitoramento; M5 processa alertas/ponto; H24 executa rotinas diárias; Auto atende agendamentos de laboratório e demandas. São processos separados: reiniciar o site não reinicia os serviços. A conta de cada processo precisa acessar sua configuração e seus arquivos autorizados.

| Serviço | Arquivo ativo | Ciclo de referência |
|---|---|---|
| `RunS30Scheduler` | [run_s_30_scheduler.py](../../app/services/run_s_30_scheduler.py) | Monitoramento a cada 30 segundos. |
| `RunM5Scheduler` | [run_m_5_scheduler.py](../../app/services/run_m_5_scheduler.py) | Alertas/ponto a cada cinco minutos. |
| `RunH24Scheduler` | [run_h_24_scheduler.py](../../app/services/run_h_24_scheduler.py) | Jobs diários de vários domínios. |
| `RunAutoScheduler` | [run_auto_scheduler.py](../../app/services/run_auto_scheduler.py) | Agendamentos de laboratório e demandas. |

Não utilizar arquivos BKP como referência ativa. Se um serviço usa outra cópia do projeto, o pacote compartilhado `backend/` e a configuração precisam existir nela também. Identificar executável, conta, diretório de trabalho e versão de código de cada processo; não instalar uma dependência na `.venv` do site presumindo corrigir o H24.

O relato histórico indicava Python 3.13.2/Windows 64 bits e origem de uma `.venv` com caminho antigo diferente do site. Confirmar o interpretador efetivo, sem mover ambiente virtual ou corrigir caminhos por suposição. A factory ainda usa `os.getcwd()` em caminhos legados; diretório de trabalho importa.

## 2. Preparação do computador

Em ambiente novo e autorizado, na raiz do projeto, usando CMD:

```bat
py -3.13 -m venv .venv
".venv\Scripts\python.exe" -m pip install -r requirements.txt
```

`requirements.txt` está em UTF-16; preserve a codificação. É o inventário versionado de dependências, não uma comprovação de instalação compatível em ambiente vazio. Não force versões ou instale no Python global para contornar conflitos. `pyodbc` não instala o driver ODBC do Windows.

O frontend exige o Node descrito em [package.json](../../frontend/package.json), atualmente `^22.18.0` ou `>=24.12.0`. No computador autorizado:

```bat
cd frontend
npm ci
npm run build:local
cd ..
```

O build verifica tipos e gera `backend/web/static/app/`, com `.vite/manifest.json` e assets. Publicar a pasta inteira, sempre da mesma compilação; ela é ignorada pelo Git e não surge com um pull. Produção não precisa de Node, Vite ou `node_modules` em execução.

### Dependências e pré-requisitos

| Componente | Referência versionada | Cuidado |
|---|---|---|
| APIFlask / Pydantic | `3.1.2` / `2.13.5` | Contratos modernos, necessários ao carregar a aplicação atual. |
| Flask / Werkzeug | `3.1.1` / `3.1.3` | Compartilhados com o legado; não atualizar isoladamente como efeito da publicação. |
| SQLAlchemy / pyodbc | `2.0.41` / `5.2.0` | Também exigem driver ODBC e destino autorizado no Windows. |
| python-dotenv | `1.2.4` | Necessário para ler arquivo privado; ambiente sem arquivo não o importa pelo leitor. |
| LDAP | `ldap3==2.9.1` | Consulta moderna tem conta/opções próprias, reutilizando valores privados. |
| PDF | `reportlab==5.0.1` e Pillow conforme requirements | Publicar também o logo do módulo de Eventos. |
| Serviços Windows | `pywin32` e demais pacotes do processo | Preservar o ambiente efetivo de cada serviço. |

Essas são versões declaradas em `requirements.txt`, não resultado de instalação nesta revisão. Ler o conjunto completo para uma preparação inicial; uma atualização incremental deve identificar quais pacotes realmente faltam. Bibliotecas do ambiente, drivers e requisitos externos não são automaticamente entregues pelo Git.

`npm ci` usa `package-lock.json`; publicar alterações de dependências com seu lockfile. `build:local` executa `vue-tsc --build` e Vite. Não confundir com `dev`/`preview`, que iniciam processos e não fazem parte da hospedagem IIS atual. Não foi identificada configuração de proxy de API no `vite.config.ts`; abrir Vite sozinho não reproduz a sessão Windows/Flask do portal.

O build usa base `/static/app/` e entrada de manifest `index.html`. As pastas anteriores `backend/static/app/` e `app/static/app/` não são o destino atual. Incluir `.vite`, JavaScript, CSS e todos os assets referenciados, mesmo que a interface pareça carregar parcialmente com uma cópia incompleta.

Na reorganização para `backend/web/`, publicar o build completo em `backend/web/static/app/` junto da versão correspondente do backend. O Flask usa esse caminho físico e preserva a URL `/static/app/`; não procura o manifest no destino anterior. O template acompanha o código em `backend/web/templates/app/shell.html`. O `web.config` versionado encaminha as requisições ao Flask, sem um mapeamento físico específico para esses assets; conferir eventuais configurações externas do IIS antes de publicar. A reorganização do código não gera nem transfere os assets automaticamente.

## 3. Configuração privada

Usar [`.env.example`](../../.env.example) como lista de nomes, sem copiar valores para o manual. Credenciais e chaves são transferidas por canal privado.

| Grupo | Configuração necessária |
|---|---|
| TD e sessão | `DJ_TD_ODBC_CONNECTION_STRING` e `DJ_SESSION_SECRET_KEY`; preservar a chave de sessão em publicações comuns. |
| Bancos legados | Configurações FTM, Plex, Trace QR e demais destinos ainda consumidos no import. |
| Integrações | Pares e opções de MES, LDAP, Microsoft e SAP conforme os consumidores; Oracle permanece ligado ao módulo desativado correspondente. |
| LDAP moderno | `DJ_LDAP_USER`/`DJ_LDAP_PASSWORD`; host, base, porta, SSL e timeouts são opções de `backend/config.py`. |

O leitor [environment.py](../../backend/shared/environment.py) procura `.env` na raiz ou usa o caminho absoluto de `DJ_ENV_FILE`. O ambiente do processo tem prioridade, inclusive valores vazios; não há interpolação de credenciais. O carregamento ocorre uma vez por processo: mudanças exigem reinício do processo afetado.

Quando `DJ_ENV_FILE` é definido, ausência do arquivo, caminho inválido ou falta de acesso causam falha. O leitor usa `python-dotenv` para arquivo privado. Vários consumidores antigos carregam configuração durante imports: preencher só TD e sessão pode não bastar para iniciar o portal.

### Variáveis e consumidores

| Categoria | Nomes | Consumidores principais |
|---|---|---|
| Compartilhado | `DJ_TD_ODBC_CONNECTION_STRING`, `DJ_SESSION_SECRET_KEY` | Backend TD, constantes/factory legadas e sessão do portal. |
| Bancos legados | `DJ_FTM_ODBC_CONNECTION_STRING`, `DJ_PLEX_ODBC_CONNECTION_STRING`, `DJ_PLEX_TEST_ODBC_CONNECTION_STRING`, `DJ_TRACE_QR_ODBC_CONNECTION_STRING` | Constantes e acessos antigos. Plex de teste ainda é resolvido no import, sem consumidor ativo confirmado. |
| MES | `DJ_MES_USER`, `DJ_MES_PASSWORD` | Integração antiga de alteração de paradas e constantes. |
| LDAP | `DJ_LDAP_USER`, `DJ_LDAP_PASSWORD` | Login/usuários/H24 antigos e consulta moderna de presença, em clientes separados. |
| Microsoft | `DJ_MICROSOFT_TENANT_ID`, `DJ_MICROSOFT_CLIENT_ID`, `DJ_MICROSOFT_CLIENT_SECRET`, `DJ_MICROSOFT_USERNAME`, `DJ_MICROSOFT_PASSWORD` | Tokens/Teams/rotinas antigas; a infraestrutura global pode alcançar esses módulos. |
| SAP | `DJ_SAP_USER`, `DJ_SAP_PASSWORD` | Relatórios legados de manutenção. |
| Oracle | `DJ_ORACLE_USER`, `DJ_ORACLE_PASSWORD` | Função de horas produtivas, cujo blueprint segue desativado. Não ativar para conferir configuração. |

Grupos/comentários no modelo organizam nomes; não ativam integrações. As constantes antigas resolvem os cinco destinos de banco e MES durante import; retirar uma variável porque a tela moderna usa só TD pode impedir a aplicação inteira ou um serviço de carregar. A chave de sessão é exigida pelo portal e por consumidores da factory.

### Escolha e prioridade da fonte

1. `DJ_ENV_FILE` precisa ser fornecido externamente antes do carregamento. Colocá-lo dentro de `.env` não seleciona outro arquivo.
2. Quando definido, deve ser caminho absoluto não vazio, existente e regular. Sem ele, o leitor calcula a raiz pelo próprio módulo e procura somente `.env` ali.
3. Ausência do arquivo padrão permite ambiente puro. Um seletor explícito inválido é erro, mesmo que outras variáveis estejam preenchidas.
4. Havendo arquivo, o leitor usa `override=False`, `interpolate=False`, UTF-8 com ou sem BOM. Aspas/escapes pertencem ao formato do arquivo; não montar strings de conexão por concatenação no manual.
5. `required_env` rejeita variável ausente ou somente espaços sem retirar caracteres do valor válido. A mensagem informa o nome, nunca o conteúdo.
6. Uma variável já presente no processo, inclusive vazia, prevalece sobre o arquivo. Mudança de arquivo ou ambiente exige reiniciar cada consumidor afetado.

Não imprimir todo o ambiente para diagnóstico. No Windows, fornecer o arquivo fora da pasta publicada, com ACLs restritas às identidades necessárias. No computador, um `.env` privado pode ficar na raiz, ignorado pelo Git; um pull não o traz. O `.env.example` vazio é somente modelo.

### Opções modernas de pool e LDAP

| Opção | Padrão / validação |
|---|---|
| `BACKEND_TD_POOL_SIZE` | 5, inteiro ≥ 1. |
| `BACKEND_TD_MAX_OVERFLOW` | 0, inteiro ≥ 0. |
| `BACKEND_TD_POOL_TIMEOUT` | 30 segundos, inteiro ≥ 1. |
| `BACKEND_TD_POOL_RECYCLE` | 1.800 segundos, inteiro ≥ 1. |
| `DJ_LDAP_HOST`, `DJ_LDAP_SEARCH_BASE` | Defaults corporativos em `backend/config.py`; substituir somente quando necessário. |
| `DJ_LDAP_USE_SSL` | false; aceita true/false/1/0. Com SSL, o cliente exige certificado válido. |
| `DJ_LDAP_PORT` | 389 sem SSL, 636 com SSL; de 1 a 65.535. |
| `DJ_LDAP_CONNECT_TIMEOUT`, `DJ_LDAP_RECEIVE_TIMEOUT` | Dois segundos cada; inteiros positivos. |
| `DJ_DEMAND_WORK_AUTOSTART_ENABLED` | false; aceita true/false/1/0. Habilita o início agendado moderno no processo `RunAutoScheduler`, após aplicar a migration específica de Demandas. |

Pool é por instância/processo, separado do legado. Essas opções não alteram automaticamente os pools antigos. Se faltar usuário ou senha LDAP, o adaptador moderno fica sem configuração e presenças retornam indisponibilidade; não presumir que isso permite iniciar todo o legado ou registrar presença sem identificação.

O início automático moderno usa a configuração TD do ambiente do `RunAutoScheduler`, com pool próprio de uma conexão, criado no primeiro ciclo habilitado. Não inicializa Flask ou chama `create_app()`. Aplicar a migration de [evolução do trabalho](../../database/migrations/20261101_expand_demand_work.sql), publicar backend/build compatíveis e configurar a opção no ambiente privado do serviço antes da ativação autorizada. O ciclo verifica até 100 demandas por minuto; detalhes e condições ficam em [Demandas](../features/demandas.md).

O histórico também registra `PYTHON_DOTENV_DISABLED`, controle da biblioteca que pode impedir leitura por `load_dotenv`; ele não é um seletor implementado pela aplicação. Se existir no ambiente, conferir seu efeito na versão instalada em verificação autorizada. Não confundi-lo com `FLASK_SKIP_DOTENV`.

## 4. IIS, sessão e arquivos

Preservar autenticação Windows e encaminhamento do token no `web.config` efetivo. O ambiente informado utiliza `-m flask run --port %HTTP_PLATFORM_PORT%` no `httpPlatformHandler`; não substituir a hospedagem como efeito de uma publicação comum.

```xml
<environmentVariables>
    <environmentVariable name="FLASK_SKIP_DOTENV" value="1" />
    <environmentVariable name="FLASK_APP" value="I:\IIS\Digital_Jost\main.py" />
</environmentVariables>
```

`FLASK_SKIP_DOTENV=1` evita o carregamento antecipado pelo Flask CLI; o leitor do projeto continua ativo. Para arquivo externo, fornecer `DJ_ENV_FILE` absoluto. Variáveis do `web.config` não são herdadas automaticamente pelos serviços Windows; provisionar cada processo e suas ACLs separadamente.

Conferir limites de request do IIS/proxy para anexos: Demandas permite até 45 MiB por requisição no backend. O armazenamento privado usa `<instance_path>/modern_demand_attachments/`; a conta do site precisa de leitura/escrita. Preservar uploads legados, logs e dados operacionais.

### O que conferir no web.config efetivo

O [arquivo versionado](../../web.config) aponta o processo para a `.venv` do site, encaminha token Windows e define limite IIS de 209.715.200 bytes (200 MiB). A factory também declara limite global de 200 MiB; Demandas reduz a requisição para 45 MiB, além de validar 10 MiB por arquivo e 40 MiB de conteúdo. O menor limite entre proxy/IIS/aplicação prevalece; não aumentar tudo sem uma necessidade específica.

O `FLASK_SKIP_DOTENV` deve existir **antes** de o Flask CLI carregar a aplicação; colocá-lo somente dentro do arquivo privado pode ser tarde. O trecho XML acima pertence a `<httpPlatform>` e não substitui a configuração inteira. Preservar autenticação/token, handlers, conta, ACLs e particularidades do site.

A sessão atual usa a chave privada e prazo configurado de 60 minutos. Trocar a chave pode invalidar sessões; não fazê-lo como efeito colateral de publicação. O token CSRF moderno está nessa sessão e é entregue pelo shell. Fora do IIS existe fallback de identidade no legado; não usar localhost como comprovação de autenticação de produção.

O caminho `instance_path` deve ser confirmado no ambiente efetivo. Anexos modernos não ficam em `app/static/uploads` nem em `backend/web/static/app`. Fazer backup coordenado do SQL/metadados e dos arquivos privados. Não publicar o diretório como conteúdo estático ou copiar dados reais para o pacote de código.

## 5. Dependências offline

Baixar wheels no computador com internet para o Python/Windows do destino. Exemplo genérico, substituindo `NOME_PACOTE==VERSAO` pela versão revisada:

```bat
".venv\Scripts\python.exe" -m pip download --dest "pacotes" --only-binary=:all: --platform win_amd64 --python-version 3.13 --implementation cp --abi cp313 --constraint requirements.txt "NOME_PACOTE==VERSAO"
```

Incluir dependências transitivas, revisar o conjunto e validar fora de produção. Copiar a pasta completa; no interpretador do processo de destino:

```bat
"I:\IIS\Digital_Jost\.venv\Scripts\python.exe" -m pip install --no-index --find-links "I:\IIS\Digital_Jost\pacotes" --only-binary=:all: --constraint "I:\IIS\Digital_Jost\requirements.txt" "NOME_PACOTE==VERSAO"
```

Usar o Python correto de cada serviço quando afetado. Não copiar a `.venv` do computador, reinstalar todo o ambiente para acrescentar um pacote ou omitir dependências sem justificativa. `--no-index` impede uso do índice online; um pacote sem wheel compatível exige solução antes da manutenção.

### Preparação e conferência do pacote

Confirmar versão/arquitetura do destino e dependências transitivas antes de baixar. Criar pasta de pacotes específica da entrega; não misturar wheels antigos sem revisão. Os marcadores `NOME_PACOTE==VERSAO` nos exemplos precisam ser substituídos: não são comandos prontos para qualquer atualização.

O uso de `--constraint requirements.txt` restringe versões declaradas, mas não instala todo o arquivo. Uma preparação inicial e uma atualização incremental são procedimentos diferentes. Não usar `--no-deps` como regra geral: os comandos históricos que o utilizaram eram específicos de uma entrega de python-dotenv.

Para Eventos/PDF, incluir ReportLab e suas dependências revisadas e o arquivo `backend/modules/events/assets/jost_logo.jpg`. Uma biblioteca instalada somente no PC não acompanha o build Vue. Transferir dependências por canal aprovado; configuração privada permanece separada.

Conferências de instalação, mesmo de metadados, devem ser realizadas pelo responsável no ambiente autorizado. Não importar `main.py` para descobrir se um pacote está disponível: a importação carrega o portal e seus efeitos.

## 6. Publicar uma versão

1. Registrar a versão em produção e comparar com a versão aprovada: `git diff --name-status COMMIT_EM_PRODUCAO COMMIT_APROVADO`. Substituir os marcadores; considerar arquivos novos, alterados e removidos.
2. Preparar código, build quando necessário, pacotes offline e alterações privadas separadas. Scripts SQL exigem revisão e autorização próprias; não são executados por esta documentação.
3. Guardar retorno compatível: código, manifest/assets, configuração e `web.config` efetivo. Backups com segredos ficam fora de pastas públicas; anexos novos precisam de backup junto dos metadados.
4. Na janela autorizada, parar o site e os serviços afetados antes de substituir código compartilhado ou dependências. Confirmar a parada.
5. Instalar somente o necessário no Python correto e copiar o conjunto de arquivos aprovado. `backend/` deve permanecer coerente; em `app/`, atualizar somente os arquivos da entrega, preservando dados.
6. Preservar particularidades do `web.config`, caminhos, ACLs e configuração privada. Atualizar `requirements.txt` não instala pacotes sozinho.
7. Iniciar o site e conferir sessão, F5, assets, erros e fluxos afetados. Gravações usam somente dados autorizados. Iniciar serviços afetados um por vez e observar ciclos/logs, sem disparar jobs manualmente por conveniência.
8. Registrar versão, resultado e pendências. Consultar [Eventos](../features/eventos.md), [Demandas](../features/demandas.md) e [Planejamento](../features/planejamento-operacional.md) para cuidados específicos.

Nunca trocar integralmente `app/`, `.venv`, uploads ou logs por uma cópia do computador. Verificar remoções de código sem limpar arquivos operacionais. A aplicação ainda carrega o legado com efeitos na inicialização; um início aparentemente simples pode acessar recursos corporativos.

### Matriz mínima do pacote

| Tipo de mudança | Itens que precisam ser coordenados |
|---|---|
| Campo/contrato moderno | Módulo backend, tipos/cliente/tela Vue, build completo e schema autorizado quando necessário. |
| Plataforma/shell | Bootstrap, plataforma, consumidores, template moderno e assets compatíveis. |
| Configuração externa | Leitor e consumidores, dependência quando houver arquivo, fonte privada e ambiente de IIS/serviços. |
| Eventos/presença/PDF | Scripts de schema conforme estado real, módulo, cliente LDAP, logo, dependências e build. |
| Solicitações modernas | Migration revisada, módulo, build, armazenamento privado e limites/ACLs/backup. |
| Disponibilidade legada | Utilitários, rotas, template/scripts da entrega e permissões de leitura/EXECUTE; sem recriar procedures por rotina. |

Listas antigas de 13 arquivos ou hashes fixos representam um intervalo anterior, não o pacote universal de hoje. Gerar a relação a partir dos commits reais de origem/destino e preservar customizações do servidor. Para arquivos gerados e privados, a relação exige conferência separada do Git.

## 7. Retornar e verificar

Se for necessário retornar, parar os processos afetados, restaurar o conjunto compatível de código/build/configuração e iniciar novamente conforme a janela aprovada. Retorno de arquivos não desfaz gravações, anexos ou alterações de schema; não remover tabelas ou desinstalar bibliotecas compartilhadas automaticamente.

Antes de considerar a entrega validada, conferir sessão e permissões, CSRF, contratos, consultas, gravação/rollback, anexos, integrações, concorrência e fluxos antigos relacionados. As verificações variam por feature e dependem do ambiente real. [Publicar no Azure DevOps](publicacao-azure.md) é outro procedimento: enviar código ao repositório não implanta o IIS.

### Diagnóstico por sintoma

| Sintoma | Conferência dirigida, sem expor dados privados |
|---|---|
| Portal/serviço não inicia | Variável obrigatória, fonte escolhida, ACL, dependência, Python efetivo e caminho de trabalho. |
| Shell retorna 503 | Build no destino atual, `.vite/manifest.json`, entrada `index.html` e acesso de leitura. |
| HTML abre sem tela/estilo | Assets da mesma compilação, URLs `/static/app/`, cópia completa e cache do navegador. |
| API devolve HTML/redirecionamento | Sessão, IIS/proxy, código compatível e ponte de erros; o cliente moderno rejeita esse conteúdo. |
| Presença retorna 503 | Configuração LDAP/alcance permitido; para PDF, biblioteca/logo. São falhas diferentes. |
| Envio não chega à API/413 | Limites IIS/proxy/backend e tamanho multipart; não reenviar antes de conferir eventual resultado incerto. |
| Download falha | Vínculo/área, metadados, arquivo privado, chave e ACL; não tornar a pasta pública para contornar. |
| Site funciona, job falha | Ambiente/conta/Python/cópia do serviço e recepção das variáveis fora do web.config. |

Logs e payloads podem conter informações confidenciais. Conferir apenas o necessário, em ambiente autorizado; não anexar arquivos inteiros ao manual ou ao commit. Não retirar configuração da produção para simular falha.

### Registro de uma publicação

Guardar SHA do código, identificação do build/pacotes, estado de migrations revisadas/aplicadas pelo responsável, processos afetados, verificações autorizadas e resultado/retorno. Falha de resposta ou retorno de código não desfaz dados gravados. Retorno após remover coluna de turno, por exemplo, exige código compatível com o schema remanescente.

Não foram confirmados nesta revisão a versão efetivamente publicada, instalações, conectividade, ACLs, schema, comportamento de IIS ou ciclos dos serviços. **O sistema não foi executado; a validação foi somente estática.**
