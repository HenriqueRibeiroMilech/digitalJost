# Publicar versões no Azure DevOps

Para publicar uma versão oficial no Azure, gere um ZIP filtrado, substitua o código no clone Azure e faça commit e push.

| Uso | Caminho |
|---|---|
| GitHub | C:\Users\00063689\dev\codes\td\digitalJost |
| Azure | C:\Users\00063689\dev\codes\td\digitalJostAzure |
| ZIPs | C:\Users\00063689\dev\codes\td\exportacoes |

Use **PowerShell** e mantenha a mesma janela durante o procedimento. Se estiver no CMD, entre no PowerShell primeiro:

~~~cmd
powershell -NoProfile
~~~

Execute os comandos na ordem e pare se houver erro.

## 1. Gerar o ZIP na pasta do GitHub

~~~powershell
cd "C:\Users\00063689\dev\codes\td\digitalJost"
git branch --show-current
git status --short
~~~

Confirme que está na main, sem alterações pendentes, e que o último commit é a versão escolhida e já foi enviado ao GitHub. Depois, copie o bloco inteiro:

~~~powershell
$shaOrigem = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) {
    throw "Nao foi possivel identificar o commit. Confira a pasta atual."
}
$shaOrigem = $shaOrigem.Trim()

$pastaExportacao = "C:\Users\00063689\dev\codes\td\exportacoes"
New-Item -ItemType Directory -Path $pastaExportacao -Force | Out-Null
$arquivoZip = Join-Path $pastaExportacao "digitalJost-$shaOrigem.zip"

if (Test-Path $arquivoZip) {
    throw "Ja existe um ZIP para este commit em: $arquivoZip"
}

$exclusoesAzure = @(
    ":(top,exclude)docs"
    ":(top,exclude)handbook"
    ":(top,exclude)database"
    ":(top,glob,icase,exclude)**/AGENTS.md"
    ":(top,glob,exclude)**/.env*"
    ":(top,exclude)app/static/uploads"
    ":(top,glob,exclude)**/log/**"
    ":(top,glob,exclude)**/logs/**"
    ":(top,glob,exclude)**/*.log"
    ":(top,glob,exclude)**/.venv/**"
    ":(top,glob,exclude)**/venv/**"
    ":(top,glob,exclude)**/node_modules/**"
    ":(top,glob,exclude)**/__pycache__/**"
    ":(top,glob,exclude)**/*.pyc"
    ":(top,glob,exclude)**/*.pyo"
    ":(top,glob,exclude)**/.vscode/**"
    ":(top,glob,exclude)**/.idea/**"
    ":(top,exclude).github"
    ":(top,exclude).agents"
    ":(top,exclude).codex"
    ":(top,glob,exclude)**/.pytest_cache/**"
    ":(top,glob,exclude)**/.mypy_cache/**"
    ":(top,glob,exclude)**/.ruff_cache/**"
    ":(top,glob,exclude)**/.coverage*"
    ":(top,glob,exclude)**/coverage/**"
    ":(top,glob,exclude)**/htmlcov/**"
    ":(top,exclude)frontend/dist"
    ":(top,exclude)backend/static/app"
    ":(top,exclude)app/static/app"
)

git archive --format=zip "--output=$arquivoZip" $shaOrigem -- . @exclusoesAzure
if ($LASTEXITCODE -ne 0) {
    throw "A exportacao falhou. Nao utilize o ZIP desta tentativa."
}

Write-Host "Commit de origem: $shaOrigem"
Write-Host "ZIP criado em: $arquivoZip"
~~~

O ZIP contém os arquivos do commit selecionado, sem a pasta .git nem o histórico do GitHub. Se ele já existir para esse commit, confira o arquivo existente; para mudar os filtros e refazer a exportação, escolha outro nome de ZIP.

## 2. Extrair e conferir o ZIP

Abra a pasta exportacoes no Explorador, localize o ZIP e use **Extrair Tudo** para uma pasta nova.

Confira se o código e os .gitignore estão presentes. Ficam fora docs/, handbook/, database/, AGENTS.md, arquivos .env e variantes, uploads, logs, dependências instaladas, caches e os builds listados no bloco.

O filtro de .env vale também para frontend/.env.local e outras variantes dentro do frontend. O código de frontend/src/ continua incluído.

O .gitignore é mantido, mas não exclui do ZIP arquivos já rastreados: os filtros acima fazem essa seleção. Revise também possíveis segredos embutidos no código antes de publicar.

## 3. Atualizar o clone Azure antes de substituir os arquivos

~~~powershell
cd "C:\Users\00063689\dev\codes\td\digitalJostAzure"
git branch --show-current
git status --short
~~~

Confirme que está na main e que o status está vazio. Se estiver em outra branch ou houver alterações anteriores, pare para conferir.

Somente com essas condições atendidas:

~~~powershell
git pull --ff-only origin main
~~~

Se o pull falhar, não continue com a substituição.

## 4. Substituir o código, preservando .git

No Explorador, abra **digitalJostAzure** e mostre os itens ocultos:

- **Windows 11:** **Exibir → Mostrar → Itens ocultos**.
- **Windows 10:** aba **Exibir → Itens ocultos**.

**A pasta .git deve permanecer intacta. Não faça esta substituição na pasta do GitHub ou no servidor de produção.**

Se esse clone contiver .env, uploads, logs, dados operacionais ou configurações exclusivas do Azure, preserve-os e revise o caso antes de fazer uma exclusão geral.

Para um clone exclusivo de código:

1. Use **Ctrl+A** para selecionar os itens.
2. Segure **Ctrl** e clique em **.git** para retirá-la da seleção.
3. Confira que .git não está selecionada e pressione **Delete**, sem Shift+Delete.
4. Copie o conteúdo da pasta extraída do ZIP para digitalJostAzure, incluindo os .gitignore.
5. Confira que main.py, app/, backend/ e frontend/ estão diretamente na raiz, ao lado da .git preservada.

Copie o conteúdo extraído, não a pasta externa de extração. A origem não deve conter .git. A retirada do código antigo registra exclusões no próximo commit e preserva o histórico anterior.

## 5. Conferir e enviar ao Azure

Na raiz de digitalJostAzure:

~~~powershell
cd "C:\Users\00063689\dev\codes\td\digitalJostAzure"
git branch --show-current
git status --short
git diff --check
~~~

Confirme que a branch é main e que só aparecem as alterações desejadas. Arquivos antigos removidos e arquivos novos são esperados. Para este fluxo manual no seu PC, prepare as alterações:

~~~powershell
git add .
git diff --cached --check
git diff --cached
~~~

Confira o conteúdo preparado, inclusive os arquivos novos. 

~~~powershell
git commit -m "NOME DO COMMIT"
git push origin main
~~~

O git add . registra arquivos novos, modificados e removidos dentro dessa pasta.

Se não houver alterações, a versão filtrada pode já estar publicada. Se o push for rejeitado, pare e confira a causa; não use force push. Se o Azure exigir PR, use uma branch de publicação e siga o fluxo de revisão da equipe.

## 6. Confirmar a publicação

No Azure DevOps, abra **Repos → Files**, selecione main e confira o código atualizado e o commit recém-enviado. A branch legacy/pre-atualizacao deve continuar mostrando o estado legado.

Repita os passos 1 a 6 a cada nova versão oficial. Correções feitas diretamente no Azure precisam voltar também ao GitHub antes da próxima exportação.

Este processo não implanta nem executa o sistema. Builds e configuração privada do servidor são tratados separadamente.
