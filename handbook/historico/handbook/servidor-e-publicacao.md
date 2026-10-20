> **Registro histórico.** Pode conter decisões, caminhos e comandos superados. Consulte o [manual atual](../../README.md); este arquivo não define o padrão vigente.

# Servidor e publicação

Este guia reúne o funcionamento do IIS e dos serviços Windows, a instalação de dependências sem internet e o processo de publicação e retorno à versão anterior.

Os caminhos descrevem o ambiente informado pelo responsável; confirme-os antes de uma nova instalação. Preparação do computador, configuração privada e build Vue estão no [README principal](../../../README.md).

## 1. Como o servidor funciona hoje

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

Se usar o arquivo padrão `I:\IIS\Digital_Jost\.env`, não é necessário `DJ_ENV_FILE`. Para arquivo externo, acrescente uma variável `DJ_ENV_FILE` com o caminho absoluto real, sem credenciais no XML.

`FLASK_SKIP_DOTENV=1` evita que o Flask CLI carregue arquivos por conta própria antes do leitor do projeto; ele **não desativa** o leitor comum. Defina-o antes de iniciar o processo.

### Serviços Windows separados do site

| Nome no Windows | Rotina |
|---|---|
| `RunS30Scheduler` | Monitoramento a cada 30 segundos. |
| `RunM5Scheduler` | Alertas e ponto a cada 5 minutos. |
| `RunH24Scheduler` | Rotinas diárias às 06:00; parte dos jobs apenas de segunda a sexta. |
| `RunAutoScheduler` | Agendamentos de laboratório e demandas a cada minuto. |

Os serviços leem `app/services/` e podem alterar os mesmos dados das telas. Reiniciar o site não reinicia esses serviços. A conta do serviço precisa conseguir ler o arquivo privado; as variáveis do `web.config` não são herdadas por ele.

## 2. Instalar dependências no servidor sem internet

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

Para Services, quando necessário, a instalação é separada:

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

## 3. Passo a passo para publicar mudanças

1. **Identifique a versão em produção.** Registre o commit e compare no computador de desenvolvimento com `git diff --name-status COMMIT_EM_PRODUCAO HEAD`, substituindo o marcador. Revise adições, alterações e exclusões; não copie arquivos por memória.
2. **Prepare a entrega.** Gere o Vue quando necessário, reúna os arquivos alterados e prepare os pacotes offline. Frontend e API devem ser da mesma versão.
3. **Prepare o retorno.** Guarde cópia privada dos arquivos substituídos, build inteiro, `web.config` efetivo e configuração anterior. Mantenha backups com segredos fora de pastas publicadas e registre os caminhos/Pythons dos serviços.
4. **Abra uma janela de manutenção.** Pare o site e os serviços afetados antes de substituir código compartilhado ou bibliotecas. Configuração e constantes comuns podem afetar todos os schedulers. Confirme a parada e evite cópia com processos usando arquivos antigos.
5. **Instale as dependências necessárias** no Python correto de cada processo, pelo procedimento offline. Não substitua `.venv` nem reinstale todo o inventário de produção para adicionar um pacote.
6. **Copie o código e o build**, conforme a tabela abaixo. Ajuste somente os campos necessários do `web.config` existente e confira a configuração privada, o seletor e as permissões das contas.
7. **Inicie e confira o site.** Acesse uma tela antiga e Eventos, faça F5, confira assets, sessão, permissões e consultas. Gravações somente com dados autorizados. Consulte os logs se houver erro.
8. **Inicie os serviços afetados, um por vez.** Confira `Running` em `Services` e acompanhe logs/ciclos naturais; não execute jobs manualmente apenas para testar. Registre a versão publicada e o resultado.

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
