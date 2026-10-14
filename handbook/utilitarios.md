# Utilitários do Digital JOST

## Publicar versões oficiais no Azure DevOps

O GitHub continua recebendo os commits do cotidiano. A cada nova versão oficial, escolha um commit do GitHub, exporte seus arquivos com os filtros abaixo e prepare a atualização no clone separado do Azure.

Este procedimento detalha a exportação do passo 5. Ele não executa o Digital JOST, não faz push e não altera o clone Azure.

### Caminhos no computador

| Uso | Caminho |
|---|---|
| Pasta de códigos | C:\Users\00063689\dev\codes\td |
| Clone do GitHub | C:\Users\00063689\dev\codes\td\digitalJost |
| Clone do Azure | C:\Users\00063689\dev\codes\td\digitalJostAzure |
| ZIPs e pastas extraídas | C:\Users\00063689\dev\codes\td\exportacoes |

Execute os comandos deste guia no PowerShell do computador que contém essas pastas. Os caminhos são locais desse computador; ajuste-os se preparar a publicação em outro ambiente.

### 1. Conferir o commit de origem

Na pasta do GitHub:

~~~powershell
cd "C:\Users\00063689\dev\codes\td\digitalJost"

git branch --show-current
git status --short
~~~

Confirme que a branch é main e que o status não lista arquivos alterados. Se houver mudanças locais, finalize o trabalho antes de continuar. Confira também que o último commit local é a versão escolhida e já foi enviado ao GitHub.

Antes de comandos Git mutáveis em outras etapas da publicação, inspecione os hooks como texto e siga o AGENTS.md da raiz. Não execute hooks que possam iniciar o projeto ou acessar recursos externos sem autorização específica.

### 2. Criar o ZIP filtrado

Copie o bloco inteiro abaixo para o PowerShell, ainda na raiz do clone GitHub:

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

O ZIP recebe o hash completo do commit no nome. Guarde o valor exibido como "Commit de origem": ele deverá constar na mensagem do commit de publicação no Azure.

Se já existir um ZIP para o mesmo commit, o bloco para antes de sobrescrevê-lo. Confira a exportação existente. Se mudar os filtros e precisar de outra exportação do mesmo commit, use outro nome de arquivo.

### 3. Entender o que entra na exportação

O Git exporta os arquivos do commit selecionado, sem incluir o histórico de commits ou a pasta .git. Alterações ainda não commitadas ficam fora.

Estar no .gitignore não garante uma exclusão: arquivos já rastreados podem continuar presentes no commit e no ZIP. Por isso, o bloco filtra explicitamente uploads, logs e os demais caminhos.

| Conteúdo | Tratamento |
|---|---|
| .gitignore da raiz e do frontend | Mantidos |
| app/, backend/ e fontes do frontend/ | Mantidos, exceto os caminhos filtrados |
| main.py, requirements.txt, package.json e package-lock.json | Mantidos quando presentes no commit |
| docs/, handbook/, database/ e AGENTS.md | Excluídos |
| .env e variantes, inclusive .env.example e arquivos do frontend | Excluídos |
| app/static/uploads/ | Excluído |
| Pastas log/ e logs/, inclusive scripts/logs/, e arquivos .log | Excluídos |
| Ambientes virtuais, node_modules e caches | Excluídos |
| Configurações de IDE, .github/, .agents/ e .codex/ | Excluídas |
| Builds do frontend e relatórios de cobertura listados no bloco | Excluídos |

Não exclua automaticamente todos os arquivos JSON, planilhas, imagens, vídeos ou nomes com Copy/BKP. Alguns podem ser recursos da aplicação. A retirada de arquivos históricos exige uma revisão de referências.

Os filtros por nome não detectam credenciais embutidas em arquivos de código ou configuração. Revise o conteúdo que será publicado sem reproduzir valores sensíveis.

### 4. Extrair e conferir o resultado

Abra no Explorador de Arquivos:

~~~text
C:\Users\00063689\dev\codes\td\exportacoes
~~~

Localize o ZIP recém-criado e use **Extrair Tudo**, escolhendo uma pasta nova dentro de exportacoes. Não extraia por cima de uma publicação anterior, pois arquivos ausentes no ZIP novo poderiam permanecer na pasta.

Confira:

- Os arquivos de código e os .gitignore estão presentes.
- docs/, handbook/, database/, AGENTS.md, arquivos .env, uploads e logs estão ausentes.
- A pasta .git está ausente.
- O hash anotado corresponde ao commit escolhido para a publicação.

Não execute o sistema, builds, testes, scripts ou integrações para validar essa exportação. Faça a revisão por comparação textual e inspeção de arquivos.

### 5. Seguir para a atualização no clone Azure

Depois da conferência, a exportação está pronta para ser usada em:

~~~text
C:\Users\00063689\dev\codes\td\digitalJostAzure
~~~

Na etapa seguinte, atualize a branch principal do clone Azure conforme o fluxo aprovado e prepare a publicação sobre o histórico existente. Na primeira atualização, preserve uma referência do estado legado em legacy/pre-atualizacao, no mesmo repositório.

Copiar os arquivos novos por cima não remove arquivos antigos. Confira explicitamente os arquivos de código obsoletos e os caminhos excluídos que já possam existir no Azure. Não remova nem modifique uploads ou dados operacionais. Preserve a pasta .git do clone Azure.

Registre o hash do GitHub no commit de publicação e envie somente a versão revisada, conforme a autorização e as regras da equipe. Não envie a branch original do GitHub ao Azure para tentar aplicar esses filtros: a exportação filtrada deve gerar um commit próprio no histórico Azure.

Os builds excluídos precisam de um processo de implantação autorizado separado. O ZIP de código não representa, por si só, uma instalação pronta para o servidor.

### Frequência

Repita a escolha do commit, a exportação e a revisão a cada nova versão oficial para o Azure. Os caminhos e filtros podem ser reutilizados; o hash e o nome do ZIP mudam com o commit escolhido.

Este guia fica no GitHub: a própria pasta handbook/ está excluída da exportação para o Azure.

### Referências

- [Git archive: exportação de arquivos de um commit](https://git-scm.com/docs/git-archive).
- [Gitignore: arquivos já rastreados não são excluídos](https://git-scm.com/docs/gitignore).
- [Git: seleção e exclusão de caminhos](https://git-scm.com/docs/gitglossary#Documentation/gitglossary.txt-pathspec).
