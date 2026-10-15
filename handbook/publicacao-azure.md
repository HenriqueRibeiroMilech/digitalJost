# Publicar versões no Azure DevOps

Gere o ZIP, atualize o clone Azure e envie o commit. Este fluxo publica código no repositório; não atualiza o servidor.

| Uso | Caminho |
|---|---|
| GitHub | C:\Users\00063689\dev\codes\td\digitalJost |
| Azure | C:\Users\00063689\dev\codes\td\digitalJostAzure |
| ZIPs | C:\Users\00063689\dev\codes\td\exportacoes |

Use a mesma janela do **PowerShell**. Se estiver no CMD:

~~~cmd
powershell -NoProfile
~~~

Siga a ordem e pare se houver erro.

## 1. Gerar o ZIP

~~~powershell
cd "C:\Users\00063689\dev\codes\td\digitalJost"
git branch --show-current
git status --short
~~~

Confirme a branch `main`, o status limpo e o commit já enviado ao GitHub. Copie o bloco inteiro:

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

O ZIP contém o commit escolhido, sem `.git` ou histórico. Se já existir, confira-o; para refazer com outros filtros, use outro nome.

## 2. Conferir o ZIP

No Explorador, use **Extrair Tudo** para uma pasta nova.

Confira código, `.gitignore`, README e `handbook/`. O filtro exclui `docs/`, `database/`, `AGENTS.md`, `.env*`, uploads, logs, dependências instaladas, caches e builds.

A exclusão de `.env*` também vale para o frontend; `frontend/src/` continua incluído.

O `.gitignore` não retira arquivos já rastreados do ZIP. Revise possíveis segredos no código antes de publicar.

## 3. Atualizar o clone Azure

~~~powershell
cd "C:\Users\00063689\dev\codes\td\digitalJostAzure"
git branch --show-current
git status --short
~~~

Prossiga somente na `main`, com status limpo:

~~~powershell
git pull --ff-only origin main
~~~

Se o pull falhar, pare.

## 4. Substituir o código

No Explorador, abra **digitalJostAzure** e habilite a exibição de itens ocultos.

**Preserve `.git`. Faça a substituição somente no clone Azure, fora da pasta GitHub e do servidor.**

Se houver `.env`, uploads, logs, outros dados operacionais ou configuração exclusiva nesse clone, preserve-os e revise antes de excluir arquivos.

Em um clone exclusivo de código:

1. Selecione os itens com **Ctrl+A**.
2. Segure **Ctrl** e clique em **.git** para removê-la da seleção.
3. Confira a seleção e use **Delete**, sem Shift+Delete.
4. Copie o conteúdo extraído, incluindo `.gitignore` e `handbook/`, para o clone.
5. Confira `main.py`, `app/`, `backend/` e `frontend/` na raiz, ao lado da `.git` preservada.

Copie o conteúdo do ZIP, sem a pasta externa de extração e sem outra `.git`. A substituição deve registrar também os arquivos removidos da versão.

## 5. Enviar ao Azure

Na raiz do clone Azure:

~~~powershell
cd "C:\Users\00063689\dev\codes\td\digitalJostAzure"
git branch --show-current
git status --short
git diff --check
~~~

Confira a `main` e as mudanças, incluindo adições e exclusões. Somente neste fluxo manual no seu PC, prepare os arquivos:

~~~powershell
git add .
git diff --cached --check
git diff --cached
~~~

Revise o conteúdo preparado, incluindo arquivos novos:

~~~powershell
git commit -m "NOME DO COMMIT"
git push origin main
~~~

Sem mudanças, a versão filtrada pode já estar publicada. Se o push for rejeitado, pare e confira; não use force push. Se houver exigência de PR, siga a revisão da equipe.

## 6. Confirmar

No Azure DevOps, abra **Repos → Files**, selecione `main` e confira o commit e os arquivos. Preserve o estado da branch `legacy/pre-atualizacao`.

Repita para cada versão. Traga correções feitas no Azure de volta ao GitHub antes da próxima exportação.

Para instalar a versão no servidor, siga o [guia de servidor e publicação](servidor-e-publicacao.md).
