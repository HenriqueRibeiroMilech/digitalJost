# Servidor e publicação

Preparação local, configuração privada e build: [README](../README.md). Os caminhos abaixo descrevem o ambiente informado; confirme-os antes de instalar ou publicar.

## Ambiente

O portal roda em Windows/IIS, em `I:\IIS\Digital_Jost`, sem internet no servidor.

| Processo | Python |
|---|---|
| Site | `I:\IIS\Digital_Jost\.venv\Scripts\python.exe`. |
| H24 (`RunH24Scheduler`, Local System) | Host `C:\python13\pythonservice.exe`; pacotes instalados com `C:\python13\python.exe`. |
| Outros serviços | Confira o executável e a conta de cada um. |

O IIS usa `httpPlatformHandler`, `arguments="-m flask run --port %HTTP_PLATFORM_PORT%"` e `forwardWindowsAuthToken="true"`. Dentro de `<httpPlatform>`:

```xml
<environmentVariables>
    <environmentVariable name="FLASK_SKIP_DOTENV" value="1" />
    <environmentVariable name="FLASK_APP" value="I:\IIS\Digital_Jost\main.py" />
</environmentVariables>
```

Sem `DJ_ENV_FILE`, o leitor procura `.env` na raiz. Para outro arquivo, defina o seletor com caminho absoluto antes de iniciar. `FLASK_SKIP_DOTENV=1` evita a leitura automática do Flask CLI e mantém o leitor do projeto.

As variáveis de `web.config` valem apenas para o site. Serviços precisam de configuração própria ou acesso ao `.env` padrão. A conta de cada processo precisa conseguir ler o arquivo privado.

| Serviço | Rotina |
|---|---|
| `RunS30Scheduler` | Monitoramento a cada 30 segundos. |
| `RunM5Scheduler` | Alertas e ponto a cada 5 minutos. |
| `RunH24Scheduler` | Rotinas às 06:00; parte somente de segunda a sexta. |
| `RunAutoScheduler` | Agendamentos a cada minuto. |

Reiniciar o site não reinicia os serviços. Eles podem alterar os mesmos dados das telas.

## Dependências sem internet

Use **CMD**. Os exemplos são para CPython 3.13 / Windows 64 bits; ajuste se o processo de destino for diferente.

### python-dotenv

No computador com internet, na raiz do projeto:

```bat
".venv\Scripts\python.exe" -m pip --disable-pip-version-check download --dest "pacotes-modernizacao" --only-binary=:all: --no-deps --platform win_amd64 --python-version 3.13 --implementation cp --abi cp313 "python-dotenv==1.2.4"
```

Copie `pacotes-modernizacao` para a raiz do projeto no servidor. Durante a manutenção autorizada, instale no Python do site:

```bat
"I:\IIS\Digital_Jost\.venv\Scripts\python.exe" -m pip --disable-pip-version-check install --no-index --find-links "I:\IIS\Digital_Jost\pacotes-modernizacao" --only-binary=:all: --no-deps "python-dotenv==1.2.4"
```

Para o H24, instale também no Python base, se necessário. Confirme o interpretador antes de repetir para outros serviços:

```bat
"C:\python13\python.exe" -m pip --disable-pip-version-check install --no-index --find-links "I:\IIS\Digital_Jost\pacotes-modernizacao" --only-binary=:all: --no-deps "python-dotenv==1.2.4"
```

### Outros pacotes

1. Valide e registre a versão em `requirements.txt`.
2. No computador com internet, substitua `NOME_PACOTE==VERSAO` e baixe o pacote com suas dependências:

```bat
".venv\Scripts\python.exe" -m pip download --dest "pacotes-nova-dependencia" --only-binary=:all: --platform win_amd64 --python-version 3.13 --implementation cp --abi cp313 --constraint requirements.txt "NOME_PACOTE==VERSAO"
```

3. Resolva conflitos ou falta de wheel antes da publicação e valide o conjunto fora de produção.
4. Copie a pasta inteira e instale no Python do processo afetado; abaixo, o do site:

```bat
"I:\IIS\Digital_Jost\.venv\Scripts\python.exe" -m pip install --no-index --find-links "I:\IIS\Digital_Jost\pacotes-nova-dependencia" --only-binary=:all: --constraint "I:\IIS\Digital_Jost\requirements.txt" "NOME_PACOTE==VERSAO"
```

`--no-index` usa apenas os arquivos locais de `--find-links`. `--no-deps` foi usado somente para `python-dotenv`, que não exige dependências adicionais nessa leitura. Outros pacotes precisam das dependências transitivas.

## Publicar no servidor

1. Registre o commit em produção e compare com `git diff --name-status COMMIT_EM_PRODUCAO HEAD`, substituindo o marcador.
2. Prepare código, build Vue completo e pacotes offline da mesma versão.
3. Guarde backup privado do código substituído, build, configuração e `web.config`, fora de pastas publicadas.
4. Na janela de manutenção, pare o site e os serviços afetados por código, configuração ou bibliotecas compartilhadas.
5. Instale somente as dependências necessárias no Python de cada processo. Preserve a `.venv` existente.
6. Copie a entrega conforme a tabela e confira caminhos, arquivo privado e permissões.
7. Inicie o site; confira uma tela antiga e Eventos, F5, assets, sessão, perfis e consultas. Gravações somente com dados autorizados.
8. Inicie os serviços afetados um por vez; confira `Running` e acompanhe logs e ciclos naturais, sem executar jobs manualmente. Registre o resultado.

| Local | O que copiar |
|---|---|
| `backend/` | Código da versão e build inteiro em `static/app/`, incluindo `.vite/manifest.json`. Confira arquivos removidos. |
| `app/` | Somente arquivos do diff; preserve uploads, logs e dados operacionais. |
| Raiz e `web.config` | Arquivos alterados; preserve as particularidades do servidor ao ajustar o XML. |
| Configuração privada | Valores atuais, enviados por canal separado e seguro. |

O servidor não precisa de Node, `node_modules` ou Vite em execução. Não copie a `.venv` do computador nem reinstale todo o inventário para adicionar um pacote. Remova sobras dos caminhos antigos somente após conferir referências e funcionamento.

**Para voltar:** pare os processos afetados, restaure código, build, configuração e `web.config` compatíveis e inicie novamente. Isso não desfaz gravações no banco; não restaure dados ou remova bibliotecas compartilhadas sem avaliar o impacto.
