# Digital JOST

Portal interno da JOST para demandas, operações industriais, laboratório, desvios, monitoramento, relatórios e gestão de usuários. O sistema funciona em Windows/IIS e está sendo modernizado aos poucos, mantendo as telas antigas em operação.

Este README reúne os procedimentos essenciais. Os caminhos do servidor descrevem o ambiente informado pelo responsável; confirme-os antes de uma nova instalação.

A documentação oficial fica em [handbook/](handbook/README.md). Comece pelo [guia de arquitetura modernizada](handbook/docs/arquitetura-modernizada.md) para entender a base atual e criar novas features. Os detalhes de instalação e publicação ficam no [guia de servidor](handbook/docs/servidor-e-publicacao.md).

Regras operacionais para agentes ficam em [AGENTS.md](AGENTS.md). Os comandos deste README são procedimentos para o responsável em ambiente autorizado; não autorizam um agente a executar o sistema.

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
| `backend/` | Arquitetura nova: inicialização e configuração na raiz, funcionalidades em `modules/`, recursos comuns em `shared/` e shell/build Vue em `web/`. |
| `frontend/` | Código Vue/TypeScript, navegação e componentes. Seu build é publicado dentro de `backend/web/static/app/`. |

**Banco:** as duas arquiteturas acessam o mesmo banco TD. Cada uma mantém seus mecanismos de conexão; a nova tem uma engine, um pool e uma factory de sessões ORM compartilhados por todos os seus módulos, por instância da aplicação. Pool é um conjunto de conexões reutilizáveis. Não existe um banco ou uma conexão exclusiva de Eventos. Transações antigas e novas continuam independentes. O legado também acessa outras fontes, como FTM, Plex e Trace QR.

**Identidade:** a nova arquitetura reaproveita o login, a sessão e os perfis antigos por uma ponte em `backend/shared/identity.py`. Ela ainda não é uma aplicação independente de `app/`.

**Funcionalidades modernas:** incluem Eventos, Solicitações e Gerenciador de Demandas. O gerenciador moderno está restrito à Transformação Digital e continua separado do gerenciador antigo; não há sincronização automática entre os registros antigos e modernos.

## 2. Onde encontrar cada coisa

```text
Digital_Jost/                       ← raiz: pasta que contém main.py
├── main.py                         # Entrada da aplicação e blueprints antigos
├── web.config                      # Hospedagem no IIS
├── requirements.txt                # Versões das dependências Python
├── .env.example                    # Modelo sem credenciais
├── .env                            # Arquivo privado opcional; nunca versionar
├── app/
│   ├── config.py                   # Factory, extensões e sessão compartilhada
│   ├── routes/                     # Backend antigo por domínio
│   ├── templates/                  # Jinja, includes JavaScript e e-mails
│   ├── static/                     # CSS/JS/imagens e uploads operacionais
│   ├── services/                   # Serviços Windows e jobs
│   └── utils/                      # Banco, segurança e integrações antigas
├── backend/
│   ├── __init__.py                 # Composição da arquitetura nova
│   ├── config.py                   # Configuração do TD, pool e diretório LDAP
│   ├── shared/                     # Banco, ambiente, HTTP/CSRF, identidade e shell
│   ├── modules/
│   │   ├── events/                 # Eventos, presença e PDF
│   │   └── demands/                # Solicitações, gestão, tarefas e anexos
│   └── web/
│       ├── templates/app/shell.html # Página que carrega o Vue
│       └── static/app/             # Build gerado; não acompanha o Git
├── database/
│   └── migrations/                 # Scripts SQL; aplicação exige autorização
├── handbook/                       # Documentação oficial e histórico
└── frontend/
    ├── package.json / package-lock.json
    └── src/                        # Features Vue e recursos compartilhados
```

`main.py` é a referência dos blueprints antigos registrados; `backend/modules/__init__.py`, dos novos. A factory em `app/config.py` chama a inicialização moderna em `backend/__init__.py`.

Os módulos modernos usam `routes.py`, `schemas.py` e `models.py`, com arquivos adicionais quando houver responsabilidade específica. Consultas, regras e operações ORM podem ficar nas rotas; Service e Repository não são camadas obrigatórias no backend moderno. Os modelos usam uma base própria, sem criação automática de tabelas.

Computadores, temporário, horas produtivas e setup estão sem registro ativo no estado atual. Arquivos `Copy`, `BKP` e similares podem ser históricos.

## 3. Dependências e preparação do computador

| Requisito | Uso |
|---|---|
| Windows e Python 3.13 de 64 bits | Referência do servidor; há dependências específicas de Windows. |
| Driver ODBC compatível com as conexões configuradas | Acesso ao SQL Server; instalar `pyodbc` não instala o driver do Windows. |
| Acesso corporativo e permissões | TD, FTM, Plex, Trace QR, LDAP e demais integrações necessárias. |
| Node `^22.18.0` ou `>=24.12.0`, com npm | Instalação e build do Vue no computador de desenvolvimento. |
| IIS, autenticação Windows e httpPlatformHandler | Hospedagem atual e validação da identidade real. |

O Python usa Flask/APIFlask, Pydantic, SQLAlchemy, pyodbc, pandas, Flask-Login/Principal/Mail, APScheduler e pywin32, além de clientes LDAP, Microsoft Graph, SAP SOAP e Oracle. Eventos também usa ReportLab e Pillow para PDF. O frontend usa Vue 3, TypeScript, Vite, Vue Router, Tailwind, PrimeVue/Volt e TanStack Query.

As versões estão em `requirements.txt` e nos manifests de `frontend/`. O arquivo Python está em UTF-16; preserve sua codificação ao editá-lo. Ele é um inventário de versões e a instalação completa em ambiente vazio ainda precisa ser validada; não force versões incompatíveis para concluir uma instalação.

Em um ambiente novo e autorizado, abra o Command Prompt (CMD) na raiz do projeto:

```bat
py -3.13 -m venv .venv
".venv\Scripts\python.exe" -m pip install -r requirements.txt
```

Esses comandos não são o procedimento de atualização de um servidor já funcionando. Usar o caminho completo do Python evita instalar pacotes no interpretador errado.

## 4. Configuração privada: vale para as duas arquiteturas

O leitor comum está em `backend/shared/environment.py`. Ele atende o backend novo e os pontos adaptados do antigo, inclusive serviços Windows.

1. Copie `.env.example` para um arquivo privado e preencha os valores existentes pelo canal seguro da empresa. Não publique credenciais no modelo.
2. Sem `DJ_ENV_FILE`, o leitor procura `.env` na raiz, ao lado de `main.py`.
3. Para outro nome/local, defina `DJ_ENV_FILE` no ambiente do processo, com o caminho absoluto. O seletor precisa existir antes da inicialização.
4. Variáveis já existentes no ambiente do Windows têm prioridade sobre o arquivo, inclusive valores vazios. O arquivo é lido uma vez por processo; alterações exigem reiniciar o processo afetado.

| Grupo | Variáveis e finalidade |
|---|---|
| Compartilhado | `DJ_TD_ODBC_CONNECTION_STRING`: conexão geral do TD; `DJ_SESSION_SECRET_KEY`: assinatura da sessão Flask. |
| Bancos antigos | `DJ_FTM_ODBC_CONNECTION_STRING`, `DJ_PLEX_ODBC_CONNECTION_STRING`, `DJ_TRACE_QR_ODBC_CONNECTION_STRING`. |
| MES e LDAP | Pares `DJ_MES_USER`/`DJ_MES_PASSWORD` e `DJ_LDAP_USER`/`DJ_LDAP_PASSWORD`. |
| Microsoft/Teams | `DJ_MICROSOFT_TENANT_ID`, `DJ_MICROSOFT_CLIENT_ID`, `DJ_MICROSOFT_CLIENT_SECRET`, `DJ_MICROSOFT_USERNAME`, `DJ_MICROSOFT_PASSWORD`. |
| SAP | `DJ_SAP_USER` e `DJ_SAP_PASSWORD`. |
| Legado sem uso ativo confirmado | `DJ_PLEX_TEST_ODBC_CONNECTION_STRING` ainda é exigida no import das constantes. `DJ_ORACLE_USER`/`DJ_ORACLE_PASSWORD` são referenciadas em horas produtivas, atualmente desativado. |
| Pool moderno | `BACKEND_TD_POOL_SIZE`, `BACKEND_TD_MAX_OVERFLOW`, `BACKEND_TD_POOL_TIMEOUT` e `BACKEND_TD_POOL_RECYCLE`; possuem padrões em `backend/config.py`. |
| LDAP moderno | Reutiliza usuário/senha privados; host, base de busca, porta, SSL e timeouts podem ser configurados pelas opções `DJ_LDAP_*` descritas no guia de servidor. |
| Agendamento moderno | `DJ_DEMAND_WORK_AUTOSTART_ENABLED`: desativado por padrão; habilita o início agendado de demandas modernas no `RunAutoScheduler`, após preparação do banco e autorização. |

Várias constantes e integrações antigas são carregadas já na inicialização. Por isso, preencher somente TD e sessão não basta para subir o portal inteiro. Preserve a chave de sessão atual para evitar invalidar as sessões existentes.

## 5. Frontend e teste em localhost

No computador autorizado, a partir da raiz, instale pelo lockfile e gere o build:

```bat
cd frontend
npm ci
npm run build:local
cd ..
```

O comando verifica os tipos e gera `backend/web/static/app/`, incluindo `.vite/manifest.json`. O backend encontra o build nesse local automaticamente. Publique a pasta inteira, com manifest e assets da mesma compilação. Ela é ignorada pelo Git: um pull não produz esses arquivos.

A URL pública dos assets continua `/static/app/`, apesar da mudança da pasta física para `backend/web/static/app/`.

Para conferir o fluxo completo em localhost, prepare um IIS local com autenticação Windows, os caminhos locais do Python/`main.py` e o ambiente privado, seguindo a estrutura da seção seguinte. Use dados e acessos autorizados para esse ambiente. Ainda não há isolamento automático dos bancos corporativos nem um procedimento de testes sem efeitos externos. Executar `main.py` fora do IIS usa fallback de identidade e não comprova login ou permissões reais.

`npm run dev` serve para desenvolvimento da interface, mas não reproduz sozinho a sessão Windows/Flask. O frontend atual faz chamadas à API real; não há uso de `VITE_EVENTS_MOCK` no código atual.

Após a preparação autorizada, confira pela web: uma tela antiga, `/app/eventos`, `/app/demandas/solicitacoes` e, com o perfil correspondente, `/app/demandas/gerenciador`. Confira atualização da página com F5, paginação e perfis de acesso. Cadastros e testes de integrações precisam de registros de teste aprovados, pois podem gravar dados ou enviar notificações.

## 6. Como o servidor funciona hoje

O ambiente informado usa Windows/IIS, projeto em `I:\IIS\Digital_Jost` e servidor sem acesso à internet. O httpPlatformHandler inicia o Python do site e encaminha as requisições e o token Windows para o Flask.

| Processo | Python/configuração |
|---|---|
| Site Digital JOST | `I:\IIS\Digital_Jost\.venv\Scripts\python.exe`, definido em `web.config`. |
| H24, serviço `RunH24Scheduler` | Host informado: `C:\python13\pythonservice.exe`, conta Local System. Instalações de pacotes usam `C:\python13\python.exe`. Confirme esses dados antes da manutenção. |
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

`FLASK_SKIP_DOTENV=1` evita que o Flask CLI carregue arquivos por conta própria antes do leitor do projeto; ele não desativa o leitor comum. Defina-o antes de iniciar o processo.

**Serviços Windows separados do site**

| Nome no Windows | Rotina |
|---|---|
| `RunS30Scheduler` | Monitoramento a cada 30 segundos. |
| `RunM5Scheduler` | Alertas e ponto a cada 5 minutos. |
| `RunH24Scheduler` | Rotinas diárias às 06:00; parte dos jobs apenas de segunda a sexta. |
| `RunAutoScheduler` | Agendamentos de laboratório e demandas a cada minuto, incluindo início agendado de demandas modernas quando habilitado. |

Os serviços leem `app/services/` e podem alterar os mesmos dados das telas. Reiniciar o site não reinicia esses serviços. A conta do serviço precisa conseguir ler o arquivo privado; as variáveis do `web.config` não são herdadas por ele.

O início agendado moderno usa um pool TD próprio do processo `RunAutoScheduler`. Sua ativação exige a migration correspondente de Demandas e a configuração `DJ_DEMAND_WORK_AUTOSTART_ENABLED`. Consulte o [guia de servidor](handbook/docs/servidor-e-publicacao.md) antes de habilitar.

**Anexos modernos**

Os anexos de Demandas ficam em `<instance_path>/modern_demand_attachments/`, fora das pastas públicas. Confirme o caminho efetivo no servidor e as permissões de leitura/escrita da conta do site.

Preserve essa pasta nas publicações e faça backup coordenado dos arquivos e dos metadados no banco. Ela não deve ser publicada como conteúdo estático. Confira também os limites de upload do IIS/proxy: Demandas limita cada requisição a 45 MiB.

## 7. Instalar dependências no servidor sem internet

Prepare os pacotes em um computador com internet e copie a pasta para o servidor. Os exemplos são para CPython 3.13 / Windows 64 bits; ajuste os parâmetros se o processo de destino for diferente.

**Pacote usado pela configuração privada**

No computador, na raiz do projeto:

```bat
".venv\Scripts\python.exe" -m pip --disable-pip-version-check download --dest "pacotes-modernizacao" --only-binary=:all: --no-deps --platform win_amd64 --python-version 3.13 --implementation cp --abi cp313 "python-dotenv==1.2.4"
```

Copie a pasta completa para `I:\IIS\Digital_Jost\pacotes-modernizacao`. No CMD do servidor, durante a manutenção autorizada, instale no Python do site:

```bat
"I:\IIS\Digital_Jost\.venv\Scripts\python.exe" -m pip --disable-pip-version-check install --no-index --find-links "I:\IIS\Digital_Jost\pacotes-modernizacao" --only-binary=:all: --no-deps "python-dotenv==1.2.4"
```

Para serviços Windows, quando necessário, a instalação é separada:

```bat
"C:\python13\python.exe" -m pip --disable-pip-version-check install --no-index --find-links "I:\IIS\Digital_Jost\pacotes-modernizacao" --only-binary=:all: --no-deps "python-dotenv==1.2.4"
```

Esse exemplo instala somente `python-dotenv`. Ele não representa o conjunto completo de dependências das funcionalidades modernas atuais; confira `requirements.txt` e os pacotes já instalados no processo afetado.

**Uma dependência nova no futuro**

1. Escolha e valide a versão no ambiente autorizado e registre-a em `requirements.txt`.
2. No computador com internet, use o download abaixo. Substitua `NOME_PACOTE==VERSAO`; baixe também as dependências transitivas, portanto não use `--no-deps` nesse caso.

```bat
".venv\Scripts\python.exe" -m pip download --dest "pacotes-nova-dependencia" --only-binary=:all: --platform win_amd64 --python-version 3.13 --implementation cp --abi cp313 --constraint requirements.txt "NOME_PACOTE==VERSAO"
```

3. Revise as versões coletadas e valide o conjunto fora de produção. Se houver conflito com o inventário ou faltar wheel compatível, resolva antes da publicação; não force atualização geral no servidor.
4. Copie a pasta inteira e instale somente o pacote solicitado no interpretador do processo afetado:

```bat
"I:\IIS\Digital_Jost\.venv\Scripts\python.exe" -m pip install --no-index --find-links "I:\IIS\Digital_Jost\pacotes-nova-dependencia" --only-binary=:all: --constraint "I:\IIS\Digital_Jost\requirements.txt" "NOME_PACOTE==VERSAO"
```

`--no-index` impede consulta ao índice online; `--find-links` aponta para os arquivos locais. `--no-deps` foi usado acima apenas para o pacote conhecido `python-dotenv`, que não precisa de dependências adicionais para essa leitura. Não o copie indiscriminadamente para outros pacotes.

## 8. Passo a passo para publicar mudanças

1. **Identifique a versão em produção.** Registre o commit e compare no computador de desenvolvimento com `git diff --name-status COMMIT_EM_PRODUCAO HEAD`, substituindo o marcador. Revise adições, alterações e exclusões; não copie arquivos por memória.
2. **Prepare a entrega.** Gere o Vue quando necessário, reúna os arquivos alterados e prepare os pacotes offline. Frontend e API devem ser da mesma versão. Se houver alteração de banco, identifique os scripts necessários; sua aplicação exige revisão e autorização específicas.
3. **Prepare o retorno.** Guarde cópia privada dos arquivos substituídos, build inteiro, `web.config` efetivo e configuração anterior. Mantenha backups com segredos fora de pastas publicadas e registre os caminhos/Pythons dos serviços. Inclua os anexos privados e seus metadados no planejamento de backup.
4. **Abra uma janela de manutenção.** Pare o site e os serviços afetados antes de substituir código compartilhado ou bibliotecas. Configuração e constantes comuns podem afetar todos os schedulers. Confirme a parada e evite cópia com processos usando arquivos antigos.
5. **Instale as dependências necessárias** no Python correto de cada processo, pelo procedimento offline. Não substitua `.venv` nem reinstale todo o inventário de produção para adicionar um pacote.
6. **Copie o código e o build**, conforme a tabela abaixo. Ajuste somente os campos necessários do `web.config` existente e confira a configuração privada, o seletor e as permissões das contas.
7. **Inicie e confira o site.** Acesse uma tela antiga e as telas modernas afetadas, faça F5, confira assets, sessão, permissões e consultas. Gravações somente com dados autorizados. Consulte os logs se houver erro.
8. **Inicie os serviços afetados, um por vez.** Confira Running em Services e acompanhe logs/ciclos naturais; não execute jobs manualmente apenas para testar. Registre a versão publicada e o resultado.

| Arquivo/pasta | Como publicar |
|---|---|
| `backend/` | Pode ser atualizado como conjunto de código da mesma versão; publique também o build completo em `backend/web/static/app/`. Confira arquivos removidos para não deixar módulos antigos misturados. |
| `app/` | Copie somente os arquivos identificados no diff. Preserve uploads, logs e arquivos operacionais; não troque a pasta inteira. |
| `main.py`, `requirements.txt` e demais arquivos da raiz | Atualize quando constarem na entrega; o manifest Python não instala pacotes sozinho. |
| `database/migrations/` | Scripts sujeitos a revisão e aplicação explícita no ambiente autorizado. Copiar o arquivo não aplica a mudança ao banco. |
| `web.config` | Preserve as particularidades do servidor; adapte os campos necessários. |
| Configuração privada | Transfira por canal separado e seguro, preservando os valores atuais. Não inclua no pacote comum. |
| Anexos privados de Demandas | Preserve o armazenamento efetivo em `<instance_path>/modern_demand_attachments/`; não substitua por uma pasta do computador nem publique como conteúdo estático. |
| `frontend/` | Fonte usada no computador para gerar o build; o servidor não precisa de Node, `node_modules` ou Vite em execução. |

Não sobrescreva `.venv`, `app/static/uploads/`, anexos privados, logs ou recursos operacionais. Não copie a `.venv` do computador.

Pastas antigas como `app/modules/events/`, `app/static/app/` e `backend/static/app/` não são os destinos atuais. O build fica em `backend/web/static/app/`; confira referências e validação antes de arquivar ou remover sobras, sem limpar outras áreas de `app/`.

Se precisar voltar: pare os processos afetados, restaure o conjunto compatível de código, manifest/assets, configuração e `web.config`, e inicie novamente. Voltar arquivos não desfaz gravações no banco, anexos ou alterações de schema. Não desinstale bibliotecas compartilhadas nem restaure dados sem avaliar os demais processos.