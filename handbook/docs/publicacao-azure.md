# Publicar versões no Azure DevOps

Procedimento manual para levar uma versão aprovada do GitHub ao repositório Azure DevOps, preservando o histórico próprio do Azure. Não implanta nem executa o Digital JOST; a implantação está em [Servidor e publicação](servidor-e-publicacao.md).

Os comandos abaixo são para o responsável em ambiente autorizado. Não concedem autorização de push, exclusão, instalação ou execução a um agente; para agentes valem as restrições de [AGENTS.md](../../AGENTS.md).

Revisão em **20/10/2026**, comparando o [procedimento anterior](../historico/handbook/publicacao-azure.md), a organização atual do repositório e o [`.gitignore`](../../.gitignore). O roteiro usa Git e manipulação manual de arquivos, sem conexão com banco, build ou inicialização do portal. Não foi executado nesta revisão.

### O que este fluxo preserva

| Elemento | Comportamento |
|---|---|
| Histórico GitHub | Permanece no clone de origem; não entra no ZIP. |
| Histórico Azure | Permanece no `.git` do clone de destino; recebe um commit com o novo conteúdo. |
| Código | Uma fotografia filtrada de um commit aprovado da origem. |
| Documentação e migrations | Excluídas pelo filtro deste procedimento; devem continuar disponíveis na origem e nas entregas que precisem delas. |
| Build e dependências | Não são instalados/gerados por esse fluxo. |
| Configuração privada e dados | Não pertencem ao pacote de código; nunca substituir por uma cópia de desenvolvimento. |

Não é merge dos históricos nem garantia de igualdade byte a byte entre repositórios: existem exclusões deliberadas. O hash do commit Azure será próprio. Enviar fonte ao Azure não comprova implantação no IIS nem execução de pipelines; automações configuradas fora do repositório precisam ser conhecidas pelo responsável antes do push.

## 1. Preparar os caminhos e a versão

Usar PowerShell, mantendo a mesma janela. Estes caminhos são exemplos sem identificação pessoal; substituir pelos diretórios reais:

```powershell
$origem = 'C:\dev\digitalJost'
$destinoAzure = 'C:\dev\digitalJostAzure'
$exportacoes = 'C:\dev\exportacoes'
Set-Location $origem
git branch --show-current
git status --short
git log -1 --oneline
```

Confirmar `main`, árvore limpa e commit aprovado já disponível no GitHub. O clone Azure deve ser outra pasta, exclusiva para esse fluxo. Revisar hooks ativos antes de comandos mutáveis; não alterar hooks/configuração por iniciativa própria. Parar se houver erro ou conteúdo inesperado.

### Condições antes de começar

- Git e PowerShell disponíveis no computador do responsável, com acesso autorizado aos dois repositórios.
- Origem, destino e exportações em diretórios distintos; o clone Azure e a extração não podem ficar dentro da árvore de origem nem do site IIS.
- Clone Azure já existente e identificado como destino correto. Se faltar, obtê-lo pelo procedimento da equipe com autenticação aprovada; não copiar `.git` do GitHub para fabricar um clone Azure.
- Nenhuma mudança pendente em qualquer clone; se houver, interromper para definir seu tratamento sem stash/descarte automático.
- Identificação da versão desejada e confirmação do responsável de que ela está disponível na origem remota. `git log -1` sozinho não comprova envio ao GitHub.
- Hooks ativos conferidos como texto, sem executar scripts de inicialização/teste/publicação como efeito inesperado do Git.

Use a mesma janela PowerShell para manter as variáveis. CMD interpreta esses blocos de outra forma; se necessário, abrir PowerShell primeiro. Os caminhos são exemplos, não diretórios pessoais a reproduzir literalmente.

## 2. Gerar o ZIP filtrado

O ZIP leva somente arquivos rastreados do commit escolhido. `.git` e arquivos não versionados não entram; os filtros também retiram dados e recursos rastreados que não pertencem ao pacote:

```powershell
$sha = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel identificar o commit.' }
$sha = $sha.Trim()
New-Item -ItemType Directory -Path $exportacoes -Force | Out-Null
$zip = Join-Path $exportacoes "digitalJost-$sha.zip"
if (Test-Path $zip) { throw 'Ja existe um ZIP para este commit. Confira-o antes de continuar.' }
$excluir = @(
    ':(top,exclude)handbook'
    ':(top,exclude)docs'
    ':(top,exclude)database'
    ':(top,glob,icase,exclude)**/AGENTS.md'
    ':(top,glob,exclude)**/.env*'
    ':(top,exclude)app/static/uploads'
    ':(top,glob,exclude)**/log/**'
    ':(top,glob,exclude)**/logs/**'
    ':(top,glob,exclude)**/*.log'
    ':(top,glob,exclude)**/.venv/**'
    ':(top,glob,exclude)**/venv/**'
    ':(top,glob,exclude)**/node_modules/**'
    ':(top,glob,exclude)**/__pycache__/**'
    ':(top,glob,exclude)**/*.pyc'
    ':(top,glob,exclude)**/*.pyo'
    ':(top,glob,exclude)**/.vscode/**'
    ':(top,glob,exclude)**/.idea/**'
    ':(top,exclude).github'
    ':(top,exclude).agents'
    ':(top,exclude).codex'
    ':(top,glob,exclude)**/.pytest_cache/**'
    ':(top,glob,exclude)**/.mypy_cache/**'
    ':(top,glob,exclude)**/.ruff_cache/**'
    ':(top,glob,exclude)**/.coverage*'
    ':(top,glob,exclude)**/coverage/**'
    ':(top,glob,exclude)**/htmlcov/**'
    ':(top,exclude)frontend/dist'
    ':(top,exclude)backend/web/static/app'
    ':(top,exclude)backend/static/app'
    ':(top,exclude)app/static/app'
)
git archive --format=zip "--output=$zip" $sha -- . @excluir
if ($LASTEXITCODE -ne 0) { throw 'Exportacao falhou. Nao utilizar o ZIP desta tentativa.' }
Write-Host "Origem: $sha"
Write-Host "Pacote: $zip"
```

O filtro `docs` atende também versões anteriores à reorganização do manual. O `.gitignore` permanece no pacote, mas não filtra arquivos já rastreados; revisar segredos eventualmente embutidos antes de publicar. `.env*` exclui também modelos e variantes do frontend. Código-fonte Vue continua incluído; build e configuração privada são provisionados separadamente.

### Como interpretar a exportação

O `$sha` fixa HEAD no início do bloco. Mudanças locais e arquivos não rastreados não entram; por isso uma árvore limpa e um commit aprovado são pré-requisitos. O ZIP nasce diretamente na pasta de exportações e não inclui `.git`, remotos, credenciais de autenticação do Git ou o histórico da origem por esse mecanismo.

O filtro exclui também `database/`, inclusive scripts SQL necessários a uma publicação de feature. Não concluir que o banco deixou de precisar deles: o responsável obtém os scripts aprovados separadamente e aplica somente com autorização específica. O README da origem pode conter links para o handbook excluído; a referência completa continua sendo o manual do repositório de origem.

Exclusões por nome não detectam segredos embutidos em código nem todos os arquivos operacionais possíveis. Revisar o inventário exportado, inclusive arquivos antigos já rastreados. Não acrescentar ao ZIP um `.env` preenchido, uploads ou logs só porque o destino tem internet restrita.

Se existir um ZIP do mesmo SHA, não sobrescrever sem conferir sua procedência/filtros. Para uma exportação corrigida, escolher outro nome e registrar o motivo. Se `git archive` falhar, não usar nem distribuir o arquivo parcial; nenhum sucesso é presumido só pela existência do ZIP.

## 3. Extrair e conferir

No Explorador, usar **Extrair Tudo** para uma pasta nova. Conferir a raiz do projeto, `main.py`, `app/`, `backend/`, `frontend/`, manifests e arquivos ocultos como `.gitignore`. Não deve existir `.git` no conteúdo extraído nem uploads, configuração privada, caches ou os builds excluídos acima. Não usar um ZIP de exportação que terminou com erro.

Não copiar a pasta externa de extração para dentro do projeto. O resultado esperado no destino é `main.py`, `app/`, `backend/` e `frontend/` diretamente na raiz, ao lado do `.git` preservado. Conferir também os arquivos de dependências (`requirements.txt`, `package.json` e lockfile quando pertencentes ao commit), que são descrições de dependências, não instalações.

## 4. Atualizar o clone Azure

```powershell
Set-Location $destinoAzure
git branch --show-current
git status --short
```

Confirmar `main`, árvore limpa e remoto correspondente ao Azure, sem expor URLs com credenciais. Somente então:

```powershell
git pull --ff-only origin main
```

Se exigir merge, divergir, falhar ou houver mudanças anteriores, parar antes de substituir arquivos. Não resolver com force push ou descarte automático.

O pull atualiza o histórico Azure, não mistura commits do GitHub. Se ele falhar por rede/autenticação/política, corrigir o acesso pelo procedimento aprovado antes de continuar. Não imprimir URL/token para compartilhar o erro. Se outra pessoa publicar enquanto a atualização é preparada, o push final pode ser rejeitado; não forçar para sobrescrevê-la.

## 5. Substituir o conteúdo e enviar

Mostrar itens ocultos no Explorador. No clone **exclusivo de código do Azure**, preservar `.git` integralmente e substituir o restante pelo conteúdo extraído, incluindo `.gitignore`. Remover código antigo que não pertence mais ao pacote exige conferir cada exclusão. Se houver `.env`, uploads, logs, dados ou configuração exclusiva no clone, preservar esses itens e resolver o escopo antes de qualquer exclusão geral. Não fazer essa substituição no GitHub ou no servidor IIS.

### Conferência no Explorador

No Windows 11, usar **Exibir → Mostrar → Itens ocultos**; no Windows 10, a opção correspondente na aba Exibir. Conferir a pasta de destino pela barra de endereço, não apenas pelo nome da janela.

Em um clone exclusivo de código, retirar somente arquivos/pastas de código aprovados para substituição e copiar o conteúdo extraído. Preservar `.git` em qualquer hipótese e preservar itens privados/operacionais que eventualmente estejam ali. Arquivo antigo removido do projeto precisa aparecer como exclusão no diff; apenas sobrepor arquivos não remove código abandonado.

Uma exclusão ampla só pode ser decidida pelo responsável após conferir o conteúdo real. Este guia não fornece comando recursivo de limpeza e não autoriza apagar dados para tornar o clone igual ao ZIP. Não alterar branches históricas para acomodar a publicação atual.

Na raiz Azure, revisar o resultado:

```powershell
git status --short
git diff --check
git diff
```

Preparar somente os caminhos revisados, incluindo os arquivos removidos, com `git add -- CAMINHO_1 CAMINHO_2` — substituir os marcadores pela lista real. Depois:

```powershell
git diff --cached --check
git diff --cached
git commit -m "DESCRICAO DA VERSAO"
git push origin main
```

O push é a etapa explícita do responsável nesse procedimento, não uma autorização geral a agentes. Se não houver mudanças, não criar commit vazio. Se o push for rejeitado, parar e verificar a causa; se a política do Azure exigir revisão por PR, seguir o fluxo da equipe, sem contorná-lo.

### Revisão antes de confirmar o commit

`git diff` não mostra o conteúdo de arquivos novos ainda não preparados. Conferir esses arquivos como texto e, depois de adicioná-los individualmente, revisar `git diff --cached` completo. O mesmo vale para novos arquivos indevidos vindos da extração.

1. Conferir que a branch e o diretório continuam corretos.
2. Comparar a relação de arquivos com o escopo aprovado, incluindo exclusões/renomeações.
3. Verificar ausência de configuração preenchida, credenciais embutidas, dados pessoais, uploads, logs e artefatos excluídos.
4. Adicionar caminhos específicos; não usar `git add .`, `-A` ou commit com `-a` como atalho.
5. Executar a conferência de whitespace e ler o patch preparado. Validação de diff não substitui teste de funcionamento.
6. Usar mensagem que identifique a entrega; registrar também o SHA de origem para permitir rastreio posterior.
7. Confirmar o commit/push somente segundo a autorização e política do destino. Nenhum comando de force push faz parte do procedimento.

Se o conteúdo preparado estiver errado, corrigir a seleção/arquivos antes do commit, preservando alterações de terceiros. Não iniciar o portal ou migrations para concluir a revisão de publicação de código.

## 6. Confirmar e registrar

No Azure DevOps, abrir **Repos → Files**, selecionar `main` e conferir o commit e os arquivos. Registrar o SHA de origem do GitHub e o commit de destino do Azure; eles não precisam ter o mesmo hash. Preservar branches históricas já existentes.

O ZIP e o push não comprovam funcionamento da aplicação. Publicar build, configuração privada ou código no IIS exige o procedimento de servidor e as verificações da funcionalidade afetada. Esta revisão do manual não executou nenhuma dessas etapas.

| Registro da entrega | Informação a guardar |
|---|---|
| Origem | SHA GitHub aprovado e referência da entrega. |
| Exportação | Nome do ZIP e filtro utilizado, incluindo eventuais mudanças no filtro. |
| Destino | Repositório/branch Azure identificados sem credenciais e SHA do commit recebido. |
| Revisão | Arquivos adicionados/removidos, diferença esperada por filtros e resultado da conferência. |
| Implantação | Separada deste envio; registrar versão/build/IIS quando de fato publicados. |

Se for preciso retornar uma versão, escolher um estado aprovado e preparar outra atualização revisada pelo fluxo da equipe, preservando os históricos. Não apagar `.git`, recriar o repositório, reescrever commits publicados ou executar rollback de dados como parte de uma correção do ZIP.

**O sistema não foi executado; a validação foi somente estática.** Não foram gerados ZIPs, alterados clones Azure, feitos commits ou enviados pushes nesta revisão.
