> **Registro histórico.** Pode conter decisões, caminhos e comandos superados. Consulte o [manual atual](../../README.md); este arquivo não define o padrão vigente.

# Publicação no servidor — de c3838b0 para 6eeffa8

Preparado em **14/10/2026**, por comparação textual entre `c3838b077a51329f5ed52e899fa46aca3ffb5127` e `6eeffa8`.

Este é o roteiro consolidado para a publicação manual. Substitui as listas parciais das entregas anteriores para esse intervalo. A versão realmente instalada no servidor ainda precisa ser confirmada: se houve publicação parcial ou customização, comparar privadamente antes de copiar. Não pressupor que a data de um documento identifica o código em produção.

O alvo de código é `6eeffa8`; o commit deste guia altera somente documentação e comandos em arquivos de texto. Na preparação, `origin/main` já apontava para `6eeffa8`. Este roteiro não comprova publicação nem funcionamento no servidor.

## 1. Resultado esperado e condições

- Mesmo site e processo Flask, com páginas antigas e Vue convivendo.
- Backend moderno em `backend/`, usando um engine/pool geral do TD; nenhum banco ou segredo por feature.
- Build Vue em `backend/static/app/`, servido em `/static/app/`.
- Credenciais atuais em fonte privada; não houve troca de senhas ou chave de sessão.
- Eventos, OEE/sinais e alteração de paradas recebem todas as mudanças do intervalo.

Ambiente informado anteriormente: site e Application Pool `Digital Jost`, diretório `I:\IIS\Digital_Jost`, Python da `.venv` do site, **CPython 3.13.2 para Windows 64 bits** e servidor sem internet. Confirmar esses dados antes de usar os caminhos/comandos. A exclusividade do pool e a configuração dos serviços não foram verificadas pelo agente.

Antes da manutenção, identificar as contas que executam IIS/Python e os serviços S30, M5, H24 e Auto, seus diretórios de código e suas `.venv`. Não cadastrar a configuração somente no usuário que acessa o servidor pelo PAM.

## 2. Arquivos a publicar

A lista em texto está em [arquivos-publicacao-modernizacao.txt](arquivos-publicacao-modernizacao.txt). Não é um script automático; o build e a configuração privada exigem tratamento separado.

### Adicionar o backend moderno inteiro

Copiar `backend/` para `I:\IIS\Digital_Jost\backend\`, incluindo bootstrap, configuração, `compatibility/`, `platform/`, `modules/` e `templates/`. São **19 arquivos Python e um template** na lista. Incluir o build da seção 3. Não copiar caches Python, configuração privada, logs ou outros arquivos locais junto com essa pasta.

Se já existir um `backend/` de publicação parcial, comparar se contém alguma customização. Após guardar a versão anterior privadamente e confirmar que só contém recursos da aplicação, substituir pelo conjunto compatível preparado. Não misturar arquivos Python de entregas diferentes.

### Substituir 13 arquivos do legado, individualmente

Todos os caminhos abaixo são relativos à raiz do site:

| Arquivo | Alteração no intervalo |
|---|---|
| `app/config.py` | Composição do backend moderno; leitura externa da chave de sessão |
| `app/errors.py` | Respostas JSON para a API moderna; HTML legado preservado |
| `app/routes/auth_routes.py` | Leitura externa do par LDAP |
| `app/routes/jdt/temp.py` | Leitura externa do LDAP; módulo continua desativado |
| `app/routes/reports/maintenance.py` | Leitura externa do par SAP |
| `app/routes/reports/oee.py` | Correção das consultas de sinais sem roteiro/detalhes |
| `app/routes/reports/productiveHours.py` | Leitura externa do par Oracle; módulo continua desativado |
| `app/routes/request/workcentersLogChange.py` | Correções da alteração de paradas |
| `app/services/jobs/mon_mon_h_24_userCheck.py` | Leitura externa do LDAP no job H24 |
| `app/templates/reports.oee/oee_signal.html` | Frontend compatível com a consulta de sinais |
| `app/utils/azure_utils.py` | Leitura externa das cinco configurações Microsoft |
| `app/utils/constants.py` | Leitura externa das conexões de bancos e do par MES |
| `app/utils/security_utils.py` | Leitura externa do LDAP usado no cadastro de usuários |

Conferir diferenças locais do servidor antes de substituir, especialmente em `app/config.py` e `app/utils/constants.py`: caminhos, modo de ambiente, pools e integrações existentes. O código atual registra `ENV = 'prod'`; preservar a configuração efetiva de produção. Os valores privados provisionados precisam corresponder aos valores efetivos do servidor, não apenas aos do PC. Não copiar essas diferenças para documentação ou chat quando contiverem segredos.

Copiar também `requirements.txt` como registro de versões. **Não executar instalação de todas as dependências apenas porque esse arquivo mudou.** Neste intervalo, a única dependência Python acrescentada foi `python-dotenv==1.2.4`; a seção 4 prepara a instalação incremental.

`main.py`, `app/utils/db_utils.py`, modelos de usuário, scripts dos schedulers e migrations não mudaram nesse intervalo. Manter seus arquivos ativos existentes; não recriar a tabela `dbo.DJ_EVENTS`, informada como já existente.

## 3. Preparação do build no PC

1. Atualizar o fonte até `6eeffa8` ou a versão que contém esse código e este roteiro.
2. Usar o Node compatível com o `frontend/package.json` (`^22.18.0` ou `>=24.12.0`). O Node/npm são necessários no PC de build; o servidor utiliza os arquivos compilados.
3. No CMD do PC, entrar em `frontend/`. Se as dependências ainda não estiverem preparadas, usar `npm ci`; não transferir `node_modules` para o servidor.
4. Executar no procedimento autorizado:

```cmd
npm run build:local
```

5. Se o comando falhar, interromper a preparação e tratar a falha antes da publicação. Não usar um build antigo para completar um pacote novo.
6. Conferir pelo Explorador que `backend/static/app/.vite/manifest.json` existe e que os arquivos referenciados no manifest acompanham o build. Copiar a pasta inteira, incluindo `.vite`, `assets` e outros recursos eventualmente gerados.
7. Conferir no localhost o build servido pelo Flask, depois guardar uma cópia desse mesmo conjunto para publicação. `npm run dev` com mock não valida a API real; o adaptador de mock não atua no build de produção.

`backend/static/app/` é ignorado pelo Git: pull/checkout não produz esses arquivos. O destino antigo `app/static/app/` não é usado pelo shell moderno. Não executar build no servidor nem iniciar um processo Node nele.

## 4. Dependência sem internet

APIFlask, Pydantic, Flask e Werkzeug já estavam declarados em `c3838b0`; a instalação anterior foi relatada no servidor. Confirmar que estão na `.venv` efetivamente usada pelo IIS. Não pressupor que o conteúdo de `requirements.txt` comprova instalação.

### Download no PC com internet

Na raiz do projeto, em CMD, usar [baixar-dependencias-modernizacao-pc.txt](baixar-dependencias-modernizacao-pc.txt):

```cmd
".venv\Scripts\python.exe" -m pip --disable-pip-version-check download --dest "pacotes-modernizacao" --only-binary=:all: --no-deps --platform win_amd64 --python-version 3.13 --implementation cp --abi cp313 "python-dotenv==1.2.4"
```

O comando não instala pacotes no PC; baixa o wheel solicitado. Conferir o término bem-sucedido e a presença de `python_dotenv-1.2.4-py3-none-any.whl`, disponibilizado na [página oficial da versão](https://pypi.org/project/python-dotenv/1.2.4/). Transferir a pasta inteira, sem acrescentar `.env`, logs ou outros arquivos privados. Usar uma pasta desta entrega, separada de pacotes antigos. O alvo Windows/CPython corresponde ao servidor registrado; se mudou, ajustar o alvo antes de prosseguir. Referência: [download e seleção do alvo no pip](https://pip.pypa.io/en/stable/cli/pip_download/).

### Instalação no servidor

Copiar a pasta para `I:\IIS\Digital_Jost\pacotes-modernizacao` e usar [instalar-dependencias-modernizacao-servidor.txt](instalar-dependencias-modernizacao-servidor.txt), durante a manutenção:

```cmd
"I:\IIS\Digital_Jost\.venv\Scripts\python.exe" -m pip --disable-pip-version-check install --no-index --find-links "I:\IIS\Digital_Jost\pacotes-modernizacao" --only-binary=:all: --no-deps "python-dotenv==1.2.4"
```

Não exige ativar a `.venv` e pode ser executado de qualquer diretório do CMD. `--no-index` evita consulta a índices; `--find-links` indica a pasta local. Não há `--upgrade`, reinstalação forçada ou instalação do requirements completo. `--no-deps` restringe esta operação ao pacote solicitado, que não exige outra dependência de runtime. Referência: [instalação local/offline no pip](https://pip.pypa.io/en/stable/cli/pip_install/).

O arquivo contém também conferências de metadados, para execução pelo responsável:

```cmd
"I:\IIS\Digital_Jost\.venv\Scripts\python.exe" -m pip --disable-pip-version-check show python-dotenv APIFlask pydantic Flask Werkzeug
"I:\IIS\Digital_Jost\.venv\Scripts\python.exe" -m pip --disable-pip-version-check check
```

Essas conferências não iniciam nem importam o projeto. Confirmar `python-dotenv 1.2.4`, os demais pacotes e ausência de incompatibilidades antes de iniciar o site. Um problema de dependência anterior deve ser entendido antes de atualizar pacotes em bloco.

Se APIFlask/Pydantic estiverem ausentes, o procedimento incremental não basta. Usar o conjunto anterior de [download de Eventos](baixar-dependencias-eventos-pc.txt) e [instalação de Eventos](instalar-dependencias-eventos-servidor.txt), que inclui Flask/Werkzeug nas versões registradas e python-dotenv. Conferir as versões atuais antes de usar essa alternativa; ela não prepara uma `.venv` nova com todas as integrações do portal.

Repetir o provisionamento nas `.venv` distintas dos serviços consumidores. Não copiar a `.venv` do PC por cima da do servidor. Nenhum desses comandos foi executado pelo agente.

## 5. Configuração privada e IIS

Recomendação para este roteiro: arquivo privado fora de qualquer webroot, selecionado por `DJ_ENV_FILE`. Exemplo de localização a criar no servidor:

```text
I:\DigitalJostConfig\digitaljost.env
```

Esse caminho é um exemplo, não um diretório já verificado. Pode ser outro caminho absoluto aprovado. Preparar o arquivo por transferência privada, preservando os valores efetivos atuais do servidor, inclusive a chave de sessão. Não copiar literalmente aspas/prefixos de literais Python antigos; usar o formato `.env` já preparado e conferido.

O modelo [.env.example](../../../.env.example) contém **19 nomes sem valores**. A relação e os consumidores estão no [guia de configuração privada](configuracao-privada-integracoes.md#3-nomes-e-consumidores). Manter o conjunto completo nesta fase. Plex de teste continua exigido ao importar as constantes, embora não haja tela ativa identificada; Oracle continua em módulo desativado.

Pelo Explorador/Propriedades/Segurança, conferir as permissões da pasta e do arquivo: acesso somente ao responsável e às contas efetivamente necessárias para IIS/Python e serviços. Não pressupor que a conta do Application Pool é a identidade padrão; confirmar no servidor. Transferência de permissões Unix do PC não configura ACL no Windows.

No `web.config` **efetivo do servidor**, editar somente o necessário, preservando handlers, autenticação Windows, `forwardWindowsAuthToken`, caminhos, logs, limites, `FLASK_APP` e demais opções. Dentro de `<httpPlatform><environmentVariables>`, incluir ou ajustar, sem duplicar entradas:

```xml
<environmentVariable name="DJ_ENV_FILE" value="I:\DigitalJostConfig\digitaljost.env" />
<environmentVariable name="FLASK_SKIP_DOTENV" value="1" />
```

Usar em `DJ_ENV_FILE` o caminho realmente escolhido. O `web.config` versionado já possui `FLASK_SKIP_DOTENV`, mas não define um caminho privado de servidor. Não copiar o arquivo inteiro cegamente. Não inserir senhas nele. O seletor público é passado ao processo pelo [HttpPlatformHandler](https://learn.microsoft.com/en-us/iis/extensions/httpplatformhandler/httpplatformhandler-configuration-reference); o controle evita a leitura antecipada pelo [Flask CLI](https://flask.palletsprojects.com/en/stable/cli/#disable-dotenv).

Cuidados que afetam o início:

- Definir `DJ_ENV_FILE` antes de iniciar o processo; colocá-lo dentro do próprio `.env` não seleciona outro arquivo.
- Variáveis já existentes no ambiente do processo têm prioridade sobre o arquivo, inclusive quando vazias. Conferir privadamente sem listar valores em terminal, screenshots ou logs.
- `FLASK_SKIP_DOTENV=1` não desliga nosso leitor; deve estar no ambiente antes do Flask CLI iniciar.
- Se `PYTHON_DOTENV_DISABLED` estiver definido como verdadeiro, a biblioteca pode ignorar o arquivo; conferir esse controle.
- Não há variável `EVENTS_ENABLED` necessária nem nova configuração obrigatória de pool. Não trocar a chave de sessão nesta entrega.

Também é possível fornecer todas as credenciais por ambiente dos processos, sem arquivo; nesse caso não definir `DJ_ENV_FILE` para um caminho inexistente. Este roteiro usa arquivo externo para facilitar a manutenção, sem mudar os destinos ou privilégios das integrações.

## 6. Pastas que podem ser trocadas e áreas a preservar

| Caminho | Orientação |
|---|---|
| `backend/` | Adicionar/substituir como conjunto completo, após comparar eventual versão parcial e guardar retorno; incluir build |
| `backend/static/app/` | Substituir pelo build inteiro da mesma versão, com manifest e assets; não misturar builds |
| `frontend/` | Fonte opcional no servidor; se mantido, atualizar o fonte compatível, preservando arquivos locais e sem transferir `node_modules`/credenciais; runtime depende do build |
| `app/` | Atualizar somente os 13 arquivos listados; não trocar a pasta inteira |
| `app/static/` | Preservar; contém recursos legados e dados operacionais |
| `app/static/uploads/` | Preservar integralmente; nenhum arquivo de usuário entra nesta entrega |
| `app/templates/` | Substituir somente `reports.oee/oee_signal.html`; manter os demais templates ativos |
| `app/services/` | Substituir somente o job H24 listado, observando as cópias usadas pelos serviços |
| `.venv/`, logs e configuração efetiva | Preservar; a instalação incremental e a edição do IIS seguem as etapas próprias |

Não colocar backups, `.env` preenchido, histórico de logs, arquivos operacionais ou pacotes de retorno em diretórios públicos. A transferência comum de código/build/wheels fica separada da configuração privada. Não levar a pasta `.git` ou caches de desenvolvimento para o site.

## 7. Caminhos antigos de Eventos

Os seguintes arquivos foram movidos/retirados do código ativo nesse intervalo:

```text
app/modules/__init__.py
app/modules/events/__init__.py
app/modules/events/routes.py
app/modules/events/schemas.py
app/modules/events/services.py
app/modules/events/repository.py
app/templates/app/shell.html
```

O build antigo `app/static/app/` também deixou de ser o destino do shell moderno. Ele não integra a comparação Git porque é ignorado.

Para reduzir risco, a limpeza desses caminhos não é condição da primeira publicação. Guardar os antigos no pacote privado de retorno e, após validar o novo pacote, conferir que nenhuma customização/job do servidor ainda os referencia antes de arquivá-los fora do webroot. Não excluir `app/modules/`, `app/templates/app/` ou `app/static/` inteiros apenas pelos nomes; podem conter outros arquivos locais. Não usar comandos destrutivos ou limpeza recursiva de dados operacionais.

## 8. Ordem da manutenção no servidor

1. **Preparar no PC:** fonte compatível, novo build aprovado no localhost, wheels e inventário. Separar a configuração privada; não iniciar a manutenção enquanto o pacote estiver incompleto.
2. **Confirmar o servidor:** caminhos/.venv/versão, site/pool, contas e serviços consumidores. Conferir customizações contra a base antes de substituir. Se a versão instalada não for conhecida, resolver essa comparação primeiro.
3. **Abrir a janela:** parar o site e os serviços que compartilham os arquivos alterados. Confirmar encerramento dos processos afetados; parar o site não deve ser presumido como encerramento automático de todo Python/job. Se precisar parar/reiniciar o pool, confirmar exclusividade ou coordenar com TI as outras aplicações. Não usar reinício global de IIS como rotina.
4. **Guardar retorno consistente:** copiar os arquivos que serão substituídos, o build antigo completo, `web.config` efetivo e registrar privadamente a configuração dos serviços. Guardar fora do webroot, com proteção equivalente à das credenciais: código antigo pode conter senhas. Preservar dados e uploads; não alterar banco para preparar retorno.
5. **Provisionar:** preparar arquivo privado, ACLs, seletores/controles do IIS e configuração de ambiente de cada serviço. Conferir a prioridade de variáveis já existentes.
6. **Instalar offline:** usar a `.venv` do site e, quando diferentes, as dos serviços. Conferir metadados/dependências. Se faltar wheel ou houver conflito, interromper a troca e resolver antes de iniciar a nova versão.
7. **Copiar como conjunto:** backend completo com build; 13 arquivos legados; registro de dependências. Aplicar a edição localizada do `web.config` sem sobrescrever customizações. Conferir arquivos/manifest antes de iniciar.
8. **Iniciar o portal:** pelo procedimento do IIS; não abrir `main.py` por fora do IIS para validar autenticação de produção. Confirmar que o processo recebeu a configuração nova e fazer as conferências da seção 10.
9. **Retomar os serviços:** somente após preparar suas cópias e configuração, em janela combinada. Observar o ciclo normal; não executar jobs manualmente apenas para diagnosticar credenciais.
10. **Encerrar:** registrar versão, build, resultados por tela e consumidor, horário e eventual retorno. Arquivar caminhos antigos somente após a conferência específica da seção 7.

A inicialização ainda possui `db.create_all()`, imports com threads/acesso externo e auditoria legada. Este roteiro não transforma iniciar o portal em uma operação sem efeitos; a manutenção e as verificações pertencem ao responsável no ambiente e escopo autorizados.

## 9. Serviços Windows

S30, M5, H24 e Auto continuam usando acessos legados. A troca de `constants.py`, `azure_utils.py` e `security_utils.py` pode afetá-los mesmo quando somente o job H24 mudou diretamente.

Para cada serviço, conferir e registrar privadamente:

| Item | Conferência |
|---|---|
| Código usado | Mesma raiz do site ou cópia separada; incluir `backend/` e consumidores compatíveis em cada cópia |
| Python | `.venv` real do serviço; preparar python-dotenv se houver arquivo privado |
| Identidade | Conta efetiva e permissão de leitura no arquivo privado |
| Ambiente | `DJ_ENV_FILE` absoluto no mecanismo aprovado que inicia o serviço, ou todas as variáveis necessárias |
| Inicialização | Processo novo recebendo configuração após a manutenção; não confiar em variáveis apenas do usuário interativo |
| Operação | Serviço retomado e ciclo normal acompanhado, sem disparo manual de jobs ou envio de mensagens de teste |

O `web.config` fornece ambiente para o processo do site; não configura serviços independentes. O método específico de cadastro de ambiente dos serviços deve ser confirmado com TI/responsável, conforme seu launcher. Não foram criados comandos de registro/reinstalação de serviços, porque os nomes instalados, launchers e contas não foram informados. H24 também exige LDAP; todos dependem das configurações de bancos/MES/Microsoft conforme seus imports. Não ativar módulos temporário/horas produtivas.

## 10. Conferências pela web

Usar o domínio efetivo do site e perfis autorizados. Primeiro consultar; operações de gravação devem usar um caso real/aprovado, pois o banco continua corporativo. Mesmo consultas podem produzir auditoria ou notificações em caso de falha.

| Tela/caso | Ação e evidência |
|---|---|
| `/` e navegação legada | Página inicial, menus e uma funcionalidade habitual carregam |
| `/app/eventos` | Listagem conclui; F5 e nova aba carregam JS/CSS; nenhum 404 de asset ou 503 de manifest |
| `/cadastros/metas` | Lista carrega usando TD legado; não salvar para apenas conferir leitura |
| `/cadastros/fatores` | Lista carrega usando Plex SQL |
| `/monitoramento/hardware` | Centros carregam com consulta ao FTM |
| `/rastreabilidade/qr/cadastro/1` | Receitas carregam via Trace QR; exige permissão específica |
| `/manutencao/controle/consulta` | Centros SAP carregam e consulta de nota existente responde |
| `/usuarios/alertas` | Consulta Graph do usuário e opções carregam; não enviar mensagem/salvar para esse teste |
| `/oee/sinal` | Pesquisar período curto com centro Plex e centro FTM, conferindo resposta e os casos corrigidos quando houver exemplos aprovados |
| Sessão e permissões | Identidade Windows correta, nova requisição mantém sessão; acesso negado é tratado como permissão, não diagnóstico automático de banco |
| API moderna | Em escopo autorizado, conferir 401/403, 400 de CSRF, 422 de campos e 404/405 JSON; não retirar variáveis de produção para provocar falhas |
| Cadastro de Eventos | Somente caso aprovado: gravação 201, feedback, lista atualizada e persistência após F5; registrar o dado criado |

Uma listagem vazia com resposta válida é diferente de falha de conexão. Uma tela montada sem consulta concluída não comprova a integração. Para requisições do browser, conferir status e resultado na aba Rede do navegador, sem compartilhar headers/tokens/payloads privados.

LDAP não é comprovado pelo login de um usuário já cadastrado: o fluxo pode não consultar o diretório. Configuração/aprovação de usuários pode acionar LDAP e alterar cadastros. MES é chamado na aprovação final de alteração de parada Plex; **abrir pendências não testa MES**, e aprovar altera dados reais. Esses casos exigem escopo próprio; não aprovar uma solicitação apenas para testar conexão. Carregar `/usuarios/alertas` comprova o caminho de consulta Graph, não todas as permissões de envio Teams.

Plex de teste não tem consumidor ativo identificado além da constante; Oracle está em módulo desativado. Não há tela ativa a incluir nesta conferência apenas para testar essas contas.

## 11. Falhas e retorno

| Sintoma | Conferir primeiro |
|---|---|
| Site não inicia / variável ausente | Nome informado, arquivo selecionado, ACL da conta efetiva, ambiente recebido pelo processo e variáveis Windows vazias |
| Erro ao importar dotenv | Instalação na `.venv` realmente usada pelo consumidor |
| Eventos retorna 503 | Build no novo destino e `.vite/manifest.json` completo |
| Asset retorna 404 | Arquivo do manifest ausente, build incompleto ou versões misturadas |
| POST de Eventos retorna 400 CSRF | Atualizar a página/sessão e conferir o token/meta/header; não desativar proteção |
| Resposta 403 | Perfil exigido e identidade efetiva; não concluir que a conexão falhou |
| Microsoft/SAP/LDAP falha | Categoria e disponibilidade da configuração; resposta do serviço, conta/permissões/rede precisam de diagnóstico próprio |
| Portal funciona, serviço falha | Cópia de código, `.venv`, conta, ACL e ambiente específicos do serviço |

Ler logs somente no ambiente privado e autorizado. O legado pode registrar strings de conexão, payloads e outros dados; não colar traceback completo no chat. Para pedir ajuda, informar tela, status e mensagem já sanitizada, sem valores de configuração, tokens ou dados pessoais.

Se o novo pacote não puder ser estabilizado na janela:

1. Parar os consumidores afetados pelo procedimento combinado.
2. Restaurar os 13 arquivos legados, `requirements.txt` e `web.config` efetivo anteriores, juntamente com os recursos de Eventos e o build no destino usado pela versão anterior. Se a versão anterior já tinha backend moderno, restaurar também seu `backend/` completo.
3. Restaurar a configuração/launcher dos serviços que foi alterada, conforme o registro privado. Não mudar a chave de sessão ou remover configuração privada por tentativa.
4. Iniciar a versão anterior e conferir portal/serviços. Não restaurar apenas `app/config.py` nem misturar seu bootstrap com o backend novo.

Para retorno à base `c3838b0`, recuperar os antigos `app/modules/` e `app/templates/app/shell.html` e o build antigo de `app/static/app/`, pois essa versão usa aqueles caminhos. O arquivo privado pode permanecer fora do webroot; o código anterior possui sua configuração antiga. Se essa versão exigia `EVENTS_ENABLED`, restaurar a configuração efetiva registrada no backup, em vez de aplicar as regras novas ao código antigo. Não retirar python-dotenv por iniciativa própria: manter `FLASK_SKIP_DOTENV=1` impede a leitura antecipada pelo CLI também durante o retorno, se compatível com a configuração registrada.

O retorno do código não desfaz cadastros, aprovações, mensagens ou operações já realizadas por usuários/jobs. Não executar SQL para tentar desfazer dados. Qualquer reversão de dados exige análise e autorização próprias. Backups antigos podem reintroduzir segredos literais; manter acesso restrito.

## 12. Validação e limites

Foram conferidos como texto o intervalo Git, os 20 arquivos do pacote backend, os 13 arquivos legados, referências aos caminhos novos, scripts npm, incremento de dependências, leitor privado e configuração do IIS. Comandos offline e opções foram revisados com documentação primária; `git diff --check` e inspeção do patch são as validações locais.

Não foram executados comandos Python, pip, npm, testes ou builds. Não houve acesso ao servidor, instalação, conexão, publicação, edição de configuração do servidor, mudança de dados ou notificações. O estado real de versão, identidades/ACLs, ambiente e serviços do servidor permanece dependente de confirmação pelo responsável.

**O sistema não foi executado; a validação foi somente estática.**
