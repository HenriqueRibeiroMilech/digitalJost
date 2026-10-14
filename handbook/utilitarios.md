# Utilitários do Digital JOST

## Publicar versões oficiais no Azure DevOps

O GitHub continua recebendo os commits do cotidiano. A cada nova versão oficial, escolha um commit do GitHub, exporte seus arquivos com os filtros abaixo e prepare a atualização no clone separado do Azure.

Este procedimento cobre a primeira publicação e as próximas: gerar o ZIP, conferir os arquivos, preservar o legado, substituir o código no clone Azure, fazer commit, enviar a branch e concluir o pull request na branch principal.

Os comandos de exportação não enviam nada. O envio ocorre somente no passo 10, e a versão oficial entra na branch principal no passo 11. Não execute o Digital JOST, testes, builds, scripts ou integrações durante este procedimento.

### Caminhos no computador

| Uso | Caminho |
|---|---|
| Pasta de códigos | C:\Users\00063689\dev\codes\td |
| Clone do GitHub | C:\Users\00063689\dev\codes\td\digitalJost |
| Clone do Azure | C:\Users\00063689\dev\codes\td\digitalJostAzure |
| ZIPs e pastas extraídas | C:\Users\00063689\dev\codes\td\exportacoes |

Execute os comandos deste guia no PowerShell do computador que contém essas pastas. Os caminhos são locais desse computador; ajuste-os se preparar a publicação em outro ambiente. Execute cada etapa na ordem e pare se algum comando falhar.

Se estiver no CMD, execute primeiro:

~~~cmd
powershell -NoProfile
~~~

O prompt deve começar com PS. Variáveis como $shaOrigem, New-Item e Write-Host pertencem ao PowerShell e não funcionam diretamente no CMD. Mantenha a mesma janela do PowerShell durante as etapas para preservar as variáveis.

### Preparação da primeira publicação

No portal Azure DevOps, abra o projeto e o repositório existente em **Repos**. Confirme que ele usa Git, que você tem permissão para contribuir e qual é a branch principal. Os exemplos usam main; se o Azure usa master ou outro nome, informe esse nome em $branchAzure no passo 5, sem renomear a branch.

Confirme com a equipe se existem pipelines ou integrações que rodam ao receber branches, PRs ou alterações na main. Antes de qualquer envio, essas automações precisam estar tratadas para que o processo de versionamento não execute nem implante o sistema.

O clone digitalJostAzure deve apontar para o repositório Azure existente, e o clone digitalJost deve continuar apontando para o GitHub. Confira a origem no cliente Git ou na configuração local, sem compartilhar URLs com credenciais ou tokens.

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
| Arquivos .env e variantes, inclusive .env.example, em qualquer pasta, incluindo frontend/ | Excluídos |
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

Se você já gerou e conferiu o ZIP dessa versão, não precisa gerá-lo novamente: continue no passo 5. Anote o hash completo que aparece no nome do ZIP.

### 5. Preparar o clone Azure

Entre na pasta do Azure:

~~~powershell
cd "C:\Users\00063689\dev\codes\td\digitalJostAzure"

git branch --show-current
git remote
git status --short
~~~

Confirme que origin existe e corresponde ao Azure. O status deve estar vazio antes de preparar a branch. Se houver alterações anteriores, pare; não descarte nem misture esse trabalho.

Antes de comandos Git mutáveis, inspecione .git/hooks e qualquer core.hooksPath como texto, ignorando arquivos .sample. Se algum hook puder executar o projeto ou acessar serviços externos, solicite orientação antes de prosseguir. Não desative hooks permanentemente.

Informe a branch principal real do Azure e atualize-a. Execute uma linha por vez e não avance se houver erro:

~~~powershell
$branchAzure = "main"
git switch $branchAzure
git pull --ff-only origin $branchAzure
~~~

Se o pull falhar, divergir ou exigir resolução de conflitos, pare. Não use rebase, reset ou force push para contornar o erro.

#### Preservar o legado, somente na primeira publicação

Antes de substituir os arquivos, no portal Azure DevOps:

1. Abra **Repos → Branches**.
2. Localize a branch principal atual, a mesma informada em $branchAzure.
3. No menu da branch, escolha **New branch / Nova branch**.
4. Crie legacy/pre-atualizacao usando a branch principal como origem.
5. Confirme que a nova branch mostra o código antigo.

Se essa branch já foi criada e conferida, não a recrie. Deixe-a sem novas alterações: ela é a referência do estado anterior à primeira atualização. Tudo permanece no mesmo repositório Azure.

#### Criar a branch desta publicação

O valor $shaOrigem deve ser o hash do commit que gerou o ZIP. Se abriu outra janela do PowerShell, informe o hash completo do nome do ZIP antes de continuar:

~~~powershell
$shaOrigem = "COLE_AQUI_O_HASH_COMPLETO_DO_ZIP"
~~~

Não execute essa atribuição com o texto de exemplo. Se manteve a janela do passo 2, a variável já contém o hash correto.

Confira o valor e crie a branch:

~~~powershell
Write-Host "Origem GitHub: $shaOrigem"
$branchPublicacao = "publicacao/github-$($shaOrigem.Substring(0, 12))"

git switch -c $branchPublicacao
~~~

Se a branch já existir, pare para conferir a publicação anterior ou em andamento. Não sobrescreva nem exclua branches para repetir a operação.

### 6. Exibir a pasta .git oculta e retirar o código antigo

Esta substituição é feita somente no clone local Azure, nunca na pasta do GitHub ou no servidor de produção:

~~~text
C:\Users\00063689\dev\codes\td\digitalJostAzure
~~~

Abra essa pasta no Explorador de Arquivos e habilite a visualização de itens ocultos:

- **Windows 11:** **Exibir → Mostrar → Itens ocultos**.
- **Windows 10:** aba **Exibir → Itens ocultos**.

A pasta .git deve aparecer. Ela contém o histórico local, as branches e a configuração do remoto. **Nunca exclua nem substitua .git.**

Confirme que digitalJostAzure é um clone exclusivo para publicação de código. Se encontrar arquivos privados de ambiente, uploads, logs, dados operacionais ou configurações exclusivas do Azure, preserve-os e faça uma revisão específica antes da substituição. Não use uma exclusão geral nesses casos.

Para um clone que contém apenas o código versionado e .git:

1. Confira o caminho na barra de endereço do Explorador.
2. Use **Ctrl+A** para selecionar os itens.
3. Segure **Ctrl** e clique na pasta **.git** para retirá-la da seleção.
4. Confira visualmente que **.git não está selecionada**.
5. Pressione **Delete**, sem usar Shift+Delete, para retirar o código antigo.
6. Confirme que .git continua dentro de digitalJostAzure.

A exclusão dos arquivos de código na pasta de trabalho não apaga os commits antigos. Eles continuam no histórico, e a referência legacy/pre-atualizacao permanece no Azure.

Se não conseguir identificar .git ou tiver dúvidas sobre os itens selecionados, pare antes de excluir.

### 7. Copiar o conteúdo extraído do ZIP

Abra a pasta nova em que extraiu o ZIP no passo 4. Entre no nível que contém main.py, app/, backend/ e frontend/.

Selecione o conteúdo dessa pasta, incluindo os .gitignore, copie e cole diretamente em digitalJostAzure. Não copie a pasta externa de extração como uma subpasta do repositório.

A estrutura esperada é:

~~~text
digitalJostAzure/
├── .git/                 ← preservada do clone Azure
├── .gitignore            ← copiada do ZIP
├── app/
├── backend/
├── frontend/
├── main.py
├── requirements.txt
├── web.config
└── ...
~~~

A pasta extraída do ZIP não deve conter .git. Se houver pedido para substituir essa pasta ao copiar, pare e confira a origem da cópia.

Confira que docs/, handbook/, database/, AGENTS.md e arquivos .env não foram copiados. Arquivos antigos que estavam somente no Azure e foram retirados aparecerão como exclusões no Git.

### 8. Revisar e adicionar os arquivos ao commit

No PowerShell, ainda dentro de digitalJostAzure:

~~~powershell
git branch --show-current
git status --short
git diff --stat
git diff --check
git diff
~~~

Confirme que a branch atual é a publicação criada no passo 5. É esperado que a primeira atualização mostre muitos arquivos modificados, removidos e adicionados.

No status, D indica arquivo removido, M indica modificado e ?? indica arquivo novo ainda não adicionado. O diff comum não mostra o conteúdo dos arquivos novos: abra esses arquivos como texto ou confira-os no controle de versão do editor.

Revise também os caminhos excluídos que já existiam no Azure. Não copie nem adicione segredos ou dados operacionais para completar a publicação.

Depois da revisão, adicione cada arquivo aprovado individualmente. Exemplos:

~~~powershell
git add -- "main.py"
git add -- ".gitignore"
git add -- "frontend/package.json"
~~~

Use os caminhos reais listados pelo status, incluindo arquivos de código removidos: git add com o caminho antigo registra a exclusão. Repita para todos os arquivos aprovados. Não use git add ., git add -A ou git commit -a.

Se usar o controle de versão do VS Code, adicione os arquivos revisados individualmente pelo botão **+** de cada arquivo. Não abra o sistema nem execute tarefas, testes ou builds do editor.

Confira exatamente o conteúdo preparado:

~~~powershell
git diff --cached --stat
git diff --cached --check
git diff --cached
git status --short
~~~

Os arquivos aprovados precisam estar preparados para commit; os demais não devem entrar. Pare se o diff contiver algo inesperado. Arquivos excluídos da nova versão continuam disponíveis nos commits antigos do Azure.

### 9. Criar o commit local da publicação

Confirme que $shaOrigem ainda corresponde ao hash do ZIP. A partir de digitalJostAzure:

~~~powershell
git commit -m "Atualiza Digital JOST para a versao oficial" -m "Origem GitHub: $shaOrigem"
~~~

Depois:

~~~powershell
git status --short
git log -1 --format="%h %s%n%b"
~~~

Confira o hash de origem na mensagem e que não restaram alterações aprovadas fora do commit. Se o Git informar que não há alterações para commit, não crie um commit vazio: confira se a versão filtrada já estava publicada.

### 10. Enviar a branch para o Azure

Somente depois da revisão, com autorização para enviar ao Azure e com as automações tratadas:

~~~powershell
git push -u origin $branchPublicacao
~~~

O envio ocorre a partir de digitalJostAzure, cujo origin aponta para o Azure. Não execute esse push na pasta digitalJost do GitHub.

Esse comando publica a branch de atualização; a main ainda não recebe o código novo. Se o push for rejeitado por permissão, política ou divergência, pare e confira a causa com a equipe. Não use --force nem --force-with-lease.

### 11. Concluir o pull request e oficializar a versão

No portal Azure DevOps:

1. Abra **Repos → Pull requests → New pull request**.
2. Em origem, selecione a branch publicacao/github-... enviada no passo 10.
3. Em destino, selecione a branch principal informada em $branchAzure.
4. Informe um título que descreva a versão e inclua o hash completo do GitHub na descrição.
5. Confira a lista de arquivos, inclusive as exclusões, e crie o PR.
6. Aguarde a revisão e os requisitos da equipe; confirme novamente que nenhuma automação executará o sistema sem autorização.
7. Conclua o PR com **Complete / Concluir** quando estiver aprovado.

O pull request é a proposta de incorporar a publicação à branch principal. Depois de concluído, abra **Repos → Files**, selecione a main ou a branch principal real e confira o código atualizado e a ausência dos caminhos excluídos.

Na primeira publicação, confira também que legacy/pre-atualizacao continua apontando para o código antigo. O histórico anterior da branch principal permanece preservado.

Se surgirem conflitos, pare para revisão. Não substitua o histórico nem resolva conflitos automaticamente.

### 12. Atualizar o clone Azure após a conclusão

Com o PR concluído e a árvore local limpa, execute uma linha por vez:

~~~powershell
cd "C:\Users\00063689\dev\codes\td\digitalJostAzure"

git status --short
git switch $branchAzure
git pull --ff-only origin $branchAzure
git status --short
~~~

Pare antes do switch se o primeiro status listar alterações. Ao terminar, o clone Azure fica na branch principal atualizada, pronto para a próxima publicação.

### Frequência e divisão dos históricos

Repita os passos 1 a 12 a cada nova versão oficial para o Azure. A criação da referência legacy/pre-atualizacao é feita apenas na primeira publicação. Os caminhos e filtros podem ser reutilizados; o hash, o nome do ZIP e a branch de publicação mudam com o commit escolhido.

O GitHub mantém os commits do cotidiano. O Azure registra as publicações oficiais sobre seu próprio histórico, com o hash do GitHub na mensagem de cada publicação. Não envie a branch original do GitHub ao Azure para tentar aplicar esses filtros.

Se houver correção diretamente no Azure, incorpore-a também ao GitHub antes de exportar outra versão, para não perdê-la na próxima substituição completa.

Os builds excluídos precisam de um processo de implantação autorizado separado. O ZIP de código não representa, por si só, uma instalação pronta para o servidor.

Este guia fica no GitHub: a própria pasta handbook/ está excluída da exportação para o Azure.

### Referências

- [Git archive: exportação de arquivos de um commit](https://git-scm.com/docs/git-archive).
- [Gitignore: arquivos já rastreados não são excluídos](https://git-scm.com/docs/gitignore).
- [Git: seleção e exclusão de caminhos](https://git-scm.com/docs/gitglossary#Documentation/gitglossary.txt-pathspec).
- [Git add: preparar arquivos para commit](https://git-scm.com/docs/git-add).
- [Git push: enviar commits e branches](https://git-scm.com/docs/git-push).
- [Azure DevOps: criar pull requests](https://learn.microsoft.com/en-us/azure/devops/repos/git/pull-requests?view=azure-devops).
- [Azure DevOps: permissões de branches](https://learn.microsoft.com/en-us/azure/devops/repos/git/branch-permissions?view=azure-devops).
- [Microsoft: itens ocultos no Explorador de Arquivos](https://support.microsoft.com/pt-br/windows/experience/fileexplorer/file-explorer-in-windows).
