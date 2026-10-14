# Digital JOST

Portal interno da JOST para demandas, operações industriais, laboratório, desvios, monitoramento, relatórios e gestão de usuários. O sistema funciona em Windows/IIS e está sendo modernizado aos poucos, mantendo as telas antigas em operação.

Este README reúne os procedimentos essenciais sem depender de outros documentos de projeto. Os caminhos do servidor descrevem o ambiente informado pelo responsável; confirme-os antes de uma nova instalação.

> **Execução controlada:** os comandos abaixo são instruções para o responsável, em ambiente e janela autorizados. Eles não autorizam agentes a executá-los. A inicialização pode acessar recursos corporativos, iniciar threads e chamar `db.create_all()`. Localhost também pode atingir produção. Para agentes, continuam valendo as regras de análise estática de `AGENTS.md`.

## 1. Como as duas arquiteturas convivem

```text
Navegador → IIS / autenticação Windows → aplicação Flask
                                         ├─ app/: páginas Jinja e rotas antigas
                                         └─ backend/: APIs e página base do Vue
                                                           ↑
                                              build gerado por frontend/
```

| Parte | Responsabilidade atual |
|---|---|
| `main.py` e `app/config.py` | Criam a aplicação, registram módulos e mantêm extensões, sessão e ciclo global. |
| `app/` | Arquitetura antiga: rotas, templates, usuários, permissões, integrações, arquivos e schedulers. Continua necessária. |
| `backend/` | Arquitetura nova: módulos Python, configuração própria, acesso geral ao TD, infraestrutura HTTP e shell Vue. |
| `frontend/` | Código Vue/TypeScript, navegação e componentes. Seu build é publicado dentro de `backend/`. |

**Banco:** as duas arquiteturas acessam o mesmo banco TD. Cada uma mantém seus mecanismos de conexão; a nova tem uma engine e um pool compartilhados por todos os seus módulos, por instância da aplicação. Pool é um conjunto de conexões reutilizáveis. Não existe um banco ou uma conexão exclusiva de Eventos. Transações antigas e novas continuam independentes.

**Identidade:** a nova arquitetura reaproveita o login, a sessão e os perfis antigos por uma ponte em `backend/compatibility/`. Ela ainda não é uma aplicação independente de `app/`.

**Primeira feature:** Eventos usa `/app/eventos`, API `/api/v1/events` e assets `/static/app/`. É uma feature normal, sem `EVENTS_ENABLED`. Já há base compartilhada para identidade/permissões, CSRF e erros JSON, componentes Vue, paginação e mensagens de validação. Essa proteção moderna não corrige automaticamente as rotas antigas.

## 2. Onde encontrar cada coisa

```text
Digital_Jost/                       ← raiz: pasta que contém main.py
├── main.py                         # Entrada da aplicação e blueprints antigos
├── web.config                      # Hospedagem no IIS
├── requirements.txt                # Versões das dependências Python
├── .env.example                    # Modelo sem credenciais
├── .env                            # Arquivo privado opcional; nunca versionar
├── app/
│   ├── config.py                    # Factory, extensões e sessão compartilhada
│   ├── routes/                     # Backend antigo por domínio
│   ├── templates/                  # Jinja, includes JavaScript e e-mails
│   ├── static/                     # CSS/JS/imagens e uploads operacionais
│   ├── services/                   # Serviços Windows e jobs
│   └── utils/                      # Banco, segurança e integrações antigas
├── backend/
│   ├── bootstrap.py                # Composição da arquitetura nova
│   ├── config.py                   # Configuração do TD e do pool moderno
│   ├── compatibility/              # Ponte com identidade antiga
│   ├── platform/                   # Banco, ambiente, HTTP, CSRF e shell Vue
│   ├── modules/events/             # Rotas, schemas, serviços e repositório
│   ├── templates/app/shell.html    # Página que carrega o Vue
│   └── static/app/                 # Build gerado; não acompanha o Git
└── frontend/
    ├── package.json / package-lock.json
    └── src/                        # Features Vue e recursos compartilhados
```

`main.py` é a referência dos blueprints antigos registrados; `backend/modules/__init__.py`, dos novos. Computadores, temporário, horas produtivas e setup estão sem registro ativo no estado atual. Arquivos `Copy`, `BKP` e similares podem ser históricos.

## 3. Dependências e preparação do computador

| Requisito | Uso |
|---|---|
| Windows e Python 3.13 de 64 bits | Referência do servidor; há dependências específicas de Windows. |
| Driver ODBC compatível com as conexões configuradas | Acesso ao SQL Server; instalar `pyodbc` não instala o driver do Windows. |
| Acesso corporativo e permissões | TD, FTM, Plex, Trace QR, LDAP e demais integrações necessárias. |
| Node `^22.18.0` ou `>=24.12.0`, com npm | Instalação e build do Vue no computador de desenvolvimento. |
| IIS, autenticação Windows e `httpPlatformHandler` | Hospedagem atual e validação da identidade real. |

O Python usa Flask/APIFlask, SQLAlchemy, pyodbc, pandas, Flask-Login/Principal/Mail, APScheduler e pywin32, além de clientes LDAP, Microsoft Graph, SAP SOAP e Oracle. O frontend usa Vue 3, TypeScript, Vite, Vue Router, Tailwind, PrimeVue/Volt e TanStack Query.

As versões estão em `requirements.txt` e nos manifests de `frontend/`. O arquivo Python está em UTF-16; preserve sua codificação ao editá-lo. Ele é um inventário de versões e a instalação completa em ambiente vazio ainda precisa ser validada; não force versões incompatíveis para concluir uma instalação.

Em um **ambiente novo e autorizado**, abra o **Command Prompt (CMD)** na raiz do projeto:

```bat
py -3.13 -m venv .venv
".venv\Scripts\python.exe" -m pip install -r requirements.txt
```

Esses comandos não são o procedimento de atualização de um servidor já funcionando. Usar o caminho completo do Python evita instalar pacotes no interpretador errado. O isolamento da `.venv` é descrito na [documentação do Python](https://docs.python.org/3.13/library/venv.html).

## 4. Configuração privada: vale para as duas arquiteturas

O leitor comum está em `backend/platform/environment.py`. Ele atende o backend novo e os pontos adaptados do antigo, inclusive serviços Windows.

1. Copie `.env.example` para um arquivo privado e preencha os valores existentes pelo canal seguro da empresa. Não publique credenciais no modelo.
2. Sem `DJ_ENV_FILE`, o leitor procura **`.env` na raiz, ao lado de `main.py`**. Confirme que o Windows não salvou `.env.txt`.
3. Para outro nome/local, defina `DJ_ENV_FILE` no ambiente do processo, com o caminho absoluto. O seletor precisa existir antes da inicialização.
4. Variáveis já existentes no ambiente do Windows têm prioridade sobre o arquivo, inclusive valores vazios. O arquivo é lido uma vez; alterações exigem reiniciar o processo afetado.

| Grupo | Variáveis e finalidade |
|---|---|
| Compartilhado | `DJ_TD_ODBC_CONNECTION_STRING`: conexão geral do TD; `DJ_SESSION_SECRET_KEY`: assinatura da sessão Flask. |
| Bancos antigos | `DJ_FTM_ODBC_CONNECTION_STRING`, `DJ_PLEX_ODBC_CONNECTION_STRING`, `DJ_TRACE_QR_ODBC_CONNECTION_STRING`. |
| MES e LDAP | Pares `DJ_MES_USER`/`DJ_MES_PASSWORD` e `DJ_LDAP_USER`/`DJ_LDAP_PASSWORD`. |
| Microsoft/Teams | `DJ_MICROSOFT_TENANT_ID`, `DJ_MICROSOFT_CLIENT_ID`, `DJ_MICROSOFT_CLIENT_SECRET`, `DJ_MICROSOFT_USERNAME`, `DJ_MICROSOFT_PASSWORD`. |
| SAP | `DJ_SAP_USER` e `DJ_SAP_PASSWORD`. |
| Legado sem uso ativo confirmado | `DJ_PLEX_TEST_ODBC_CONNECTION_STRING` ainda é exigida no import das constantes. `DJ_ORACLE_USER`/`DJ_ORACLE_PASSWORD` são referenciadas em horas produtivas, atualmente desativado. |

Várias constantes e integrações antigas são carregadas já na inicialização. Por isso, preencher somente TD e sessão não basta para subir o portal inteiro. Preserve a chave de sessão atual para evitar invalidar as sessões existentes.

O arquivo usa UTF-8, não interpola `${...}` e depende de **`python-dotenv==1.2.4` no Python de cada processo que o lê**. Não coloque credenciais Python em variáveis `VITE_*`: elas podem entrar no JavaScript enviado ao navegador.

No servidor, a recomendação é guardar o arquivo **fora de qualquer pasta publicada pelo IIS**, com leitura apenas para as contas necessárias. O `.env` na raiz é suportado e foi usado na recuperação do H24, mas exige verificar a proteção contra download e permanece uma pendência de hospedagem. Mover o arquivo exige configurar o seletor também nos serviços; `web.config` só configura o site.

## 5. Frontend e teste em localhost

No computador autorizado, a partir da raiz, instale pelo lockfile e gere o build:

```bat
cd frontend
npm ci
npm run build:local
cd ..
```

O comando verifica os tipos e gera **`backend/static/app/`**, incluindo **`.vite/manifest.json`**. O backend encontra o build nesse local automaticamente. Publique a pasta inteira, com manifest e assets da mesma compilação. Ela é ignorada pelo Git: um pull não produz esses arquivos. O comportamento de instalação pelo lockfile está na [documentação do npm](https://docs.npmjs.com/cli/v11/commands/npm-ci/).

Para conferir o fluxo completo em localhost, prepare um IIS local com autenticação Windows, os caminhos locais do Python/`main.py` e o ambiente privado, seguindo a estrutura da seção seguinte. Use dados e acessos autorizados para esse ambiente. **Ainda não há isolamento automático dos bancos corporativos nem um procedimento de testes sem efeitos externos.** Executar `main.py` fora do IIS usa fallback de identidade e não comprova login ou permissões reais.

`npm run dev` serve para desenvolvimento da interface. Quando `VITE_EVENTS_MOCK=true` no modo de desenvolvimento, Eventos usa dados simulados; isso não valida banco nem integrações. O build integrado ao Flask usa a API real.

Após a preparação autorizada, confira pela web: uma tela antiga, `/app/eventos`, atualização da página com F5, paginação e perfis de acesso. Cadastros e testes de integrações precisam de registros de teste aprovados, pois podem gravar dados ou enviar notificações.

## 6. Como o servidor funciona hoje

O ambiente informado usa **Windows/IIS**, projeto em **`I:\IIS\Digital_Jost`** e servidor sem acesso à internet. O `httpPlatformHandler` inicia o Python do site e encaminha as requisições e o token Windows para o Flask.

| Processo | Python/configuração |
|---|---|
| Site Digital JOST | `I:\IIS\Digital_Jost\.venv\Scripts\python.exe`, definido em `web.config`. |
| H24, serviço `RunH24Scheduler` | Host confirmado: `C:\python13\pythonservice.exe`, conta Local System. Instalações de pacotes usam `C:\python13\python.exe`. |
| Demais schedulers | Confira o executável e a conta de cada serviço; não presuma que usam a `.venv` do site. |

O `web.config` atual utiliza `arguments="-m flask run --port %HTTP_PLATFORM_PORT%"` e `forwardWindowsAuthToken="true"`. Preserve as configurações reais de autenticação e hospedagem ao publicar.

Dentro de `<httpPlatform>`, a configuração básica do ambiente é:

```xml
<environmentVariables>
    <environmentVariable name="FLASK_SKIP_DOTENV" value="1" />
    <environmentVariable name="FLASK_APP" value="I:\IIS\Digital_Jost\main.py" />
</environmentVariables>
```

Se usar o arquivo padrão `I:\IIS\Digital_Jost\.env`, não é necessário `DJ_ENV_FILE`. Para arquivo externo, acrescente uma variável `DJ_ENV_FILE` com o caminho absoluto real, sem credenciais no XML. Um seletor antigo ainda apontando para `digitaljost.env` prevalece sobre o nome `.env` e precisa ser corrigido.

`FLASK_SKIP_DOTENV=1` evita que o Flask CLI carregue arquivos por conta própria antes do leitor do projeto; ele **não desativa** o leitor comum. Defina-o antes de iniciar o processo. Veja a [documentação do Flask CLI](https://flask.palletsprojects.com/en/stable/cli/#disable-dotenv).

### Serviços Windows separados do site

| Nome no Windows | Rotina |
|---|---|
| `RunS30Scheduler` | Monitoramento a cada 30 segundos. |
| `RunM5Scheduler` | Alertas e ponto a cada 5 minutos. |
| `RunH24Scheduler` | Rotinas diárias às 06:00; parte dos jobs apenas de segunda a sexta. |
| `RunAutoScheduler` | Agendamentos de laboratório e demandas a cada minuto. |

Os serviços leem `app/services/` e podem alterar os mesmos dados das telas. Reiniciar o site não reinicia esses serviços. A conta do serviço precisa conseguir ler o arquivo privado; as variáveis do `web.config` não são herdadas por ele.

**Incidente já observado:** o H24 encontrou o `.env`, mas não iniciou porque `python-dotenv` estava disponível somente na `.venv` do site. A instalação offline no Python base `C:\python13\python.exe` resolveu o erro segundo a confirmação do responsável. Para outros serviços, confirme o interpretador antes de repetir a instalação.

## 7. Instalar dependências no servidor sem internet

Prepare os pacotes em um computador com internet e copie a pasta para o servidor. Os exemplos são para **CPython 3.13 / Windows 64 bits**; ajuste os parâmetros se o processo de destino for diferente.

### Pacote usado pela configuração privada

No computador, na raiz do projeto:

```bat
".venv\Scripts\python.exe" -m pip --disable-pip-version-check download --dest "pacotes-modernizacao" --only-binary=:all: --no-deps --platform win_amd64 --python-version 3.13 --implementation cp --abi cp313 "python-dotenv==1.2.4"
```

Copie a pasta completa para `I:\IIS\Digital_Jost\pacotes-modernizacao`. No CMD do servidor, durante a manutenção autorizada, instale no Python do **site**:

```bat
"I:\IIS\Digital_Jost\.venv\Scripts\python.exe" -m pip --disable-pip-version-check install --no-index --find-links "I:\IIS\Digital_Jost\pacotes-modernizacao" --only-binary=:all: --no-deps "python-dotenv==1.2.4"
```

Para o **H24**, quando necessário, a instalação é separada:

```bat
"C:\python13\python.exe" -m pip --disable-pip-version-check install --no-index --find-links "I:\IIS\Digital_Jost\pacotes-modernizacao" --only-binary=:all: --no-deps "python-dotenv==1.2.4"
```

### Uma dependência nova no futuro

1. Escolha e valide a versão no ambiente autorizado e registre-a em `requirements.txt`.
2. No computador com internet, use o download abaixo. Substitua `NOME_PACOTE==VERSAO`; baixe também as dependências transitivas, portanto **não use `--no-deps` nesse caso**.

```bat
".venv\Scripts\python.exe" -m pip download --dest "pacotes-nova-dependencia" --only-binary=:all: --platform win_amd64 --python-version 3.13 --implementation cp --abi cp313 --constraint requirements.txt "NOME_PACOTE==VERSAO"
```

3. Revise as versões coletadas e valide o conjunto fora de produção. Se houver conflito com o inventário ou faltar wheel compatível, resolva antes da publicação; não force atualização geral no servidor.
4. Copie a pasta inteira e instale somente o pacote solicitado no interpretador do processo afetado:

```bat
"I:\IIS\Digital_Jost\.venv\Scripts\python.exe" -m pip install --no-index --find-links "I:\IIS\Digital_Jost\pacotes-nova-dependencia" --only-binary=:all: --constraint "I:\IIS\Digital_Jost\requirements.txt" "NOME_PACOTE==VERSAO"
```

`--no-index` impede consulta ao índice online; `--find-links` aponta para os arquivos locais. `--no-deps` foi usado acima apenas para o pacote conhecido `python-dotenv`, que não precisa de dependências adicionais para essa leitura. Não o copie indiscriminadamente para outros pacotes. Referências: [pip download](https://pip.pypa.io/en/stable/cli/pip_download/) e [pip install](https://pip.pypa.io/en/stable/cli/pip_install/).

## 8. Passo a passo para publicar mudanças

1. **Identifique a versão em produção.** Registre o commit e compare no computador de desenvolvimento com `git diff --name-status COMMIT_EM_PRODUCAO HEAD`, substituindo o marcador. Revise adições, alterações e exclusões; não copie arquivos por memória.
2. **Prepare a entrega.** Gere o Vue quando necessário, reúna os arquivos alterados e prepare os pacotes offline. Frontend e API devem ser da mesma versão.
3. **Prepare o retorno.** Guarde cópia privada dos arquivos substituídos, build inteiro, `web.config` efetivo e configuração anterior. Mantenha backups com segredos fora de pastas publicadas e registre os caminhos/Pythons dos serviços.
4. **Abra uma janela de manutenção.** Pare o site e os serviços afetados antes de substituir código compartilhado ou bibliotecas. Configuração e constantes comuns podem afetar todos os schedulers. Confirme a parada e evite cópia com processos usando arquivos antigos.
5. **Instale as dependências necessárias** no Python correto de cada processo, pelo procedimento offline. Não substitua `.venv` nem reinstale todo o inventário de produção para adicionar um pacote.
6. **Copie o código e o build**, conforme a tabela abaixo. Ajuste somente os campos necessários do `web.config` existente e confira a configuração privada, o seletor e as permissões das contas.
7. **Inicie e confira o site.** Acesse uma tela antiga e Eventos, faça F5, confira assets, sessão, permissões e consultas. Gravações somente com dados autorizados. Consulte os logs se houver erro.
8. **Inicie os serviços afetados, um por vez.** Confira `Running` em `Services` e acompanhe logs/ciclos naturais; não execute jobs manualmente apenas para testar. O H24 não executa todas as rotinas ao iniciar. Registre a versão publicada e o resultado.

| Arquivo/pasta | Como publicar |
|---|---|
| `backend/` | Pode ser atualizado como conjunto de código da mesma versão; publique também o build completo em `backend/static/app/`. Confira arquivos removidos para não deixar módulos antigos misturados. |
| `app/` | Copie somente os arquivos identificados no diff. Preserve uploads, logs e arquivos operacionais; não troque a pasta inteira. |
| `main.py`, `requirements.txt` e demais arquivos da raiz | Atualize quando constarem na entrega; o manifest Python não instala pacotes sozinho. |
| `web.config` | Preserve as particularidades do servidor; adapte os campos necessários. |
| Configuração privada | Transfira por canal separado e seguro, preservando os valores atuais. Não inclua no pacote comum. |
| `frontend/` | Fonte usada no computador para gerar o build; o servidor não precisa de Node, `node_modules` ou Vite em execução. |

Não sobrescreva `.venv`, `app/static/uploads/`, logs ou recursos operacionais. Não copie a `.venv` do computador. Pastas antigas como `app/modules/events/` e `app/static/app/` não são os destinos atuais; confira referências e validação antes de arquivar ou remover sobras, sem limpar outras áreas de `app/`.

**Se precisar voltar:** pare os processos afetados, restaure o conjunto compatível de código, manifest/assets, configuração e `web.config`, e inicie novamente. Voltar arquivos não desfaz gravações no banco. Não desinstale bibliotecas compartilhadas nem restaure dados sem avaliar os demais processos.

## 9. Onde procurar erros

| Sintoma | Primeira conferência |
|---|---|
| Site não inicia após publicar | Caminho do Python e de `FLASK_APP`, seletor `DJ_ENV_FILE`, acesso ao arquivo e log configurado em `stdoutLogFile`. |
| Variável `DJ_*` ausente | Arquivo realmente lido por esse processo, nome `.env`, variável preenchida e ambiente do Windows prevalecendo. Não conclua que a senha está errada. |
| Pedido para instalar `python-dotenv` | Pacote ausente no Python desse processo; instalação na `.venv` não atende automaticamente ao serviço. |
| Serviço retorna erro específico 1 | `Event Viewer` → `Windows Logs` → `Application`; procure o traceback de `Python Service`. Confira também `System` para o Service Control Manager. |
| Vue indisponível, página vazia ou assets 404 | Build inteiro em `backend/static/app/`, com `.vite/manifest.json` e arquivos da mesma compilação. |
| API retorna 401, 403 ou erro de token | 401 indica sessão ausente; 403, perfil sem acesso; CSRF inválido retorna 400. Confira a causa sem remover a proteção. |

Os logs dos schedulers ficam em `app/services/logs/`, mas falhas de importação podem ocorrer antes de o logger iniciar. Não compartilhe logs completos sem retirar segredos e dados pessoais.

## 10. Manutenção e segurança

Para evoluir a parte moderna, use `backend/modules/` e as bases existentes de `backend/platform/` e `frontend/src/shared/`. Mantenha HTTP, regras e SQL separados. Registre o módulo e a rota Vue; novas URLs precisam também da rota Flask que entrega o shell para acesso direto/F5. Para corrigir uma tela antiga, confirme seus imports, templates, JavaScript, permissões, tabelas e jobs antes de alterar.

A externalização das credenciais reduz a exposição no código ativo, mas **não elimina segredos de histórico, cópias e backups nem substitui rotação**. As credenciais foram mantidas por decisão operacional. Permanecem pendências no legado, como SQL interpolado, proteção CSRF desigual, caminhos dinâmicos de arquivos, fallback de identidade e efeitos externos na inicialização. Migrar uma tela exige revisar esses pontos; apenas mudar sua pasta não os resolve.

Este README foi revisado por leitura de código e configuração. Instalação completa, acesso corporativo, autenticação, publicação e execução dos jobs precisam de validação pelo responsável em ambiente autorizado.
