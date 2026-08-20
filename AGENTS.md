# AGENTS.md — regras do Digital JOST

Este arquivo se aplica a todo o repositório. Ele é o contexto operacional principal para qualquer agente que trabalhe no Digital JOST.

## 1. Regra absoluta: não executar o sistema

**Não execute, inicialize, importe ou teste dinamicamente o Digital JOST.** Uma autorização genérica para “implementar”, “corrigir” ou “testar” não suspende esta regra. A exceção exige autorização explícita do responsável, informando exatamente o comando, o ambiente e o escopo permitido.

É proibido, por iniciativa própria:

- executar `python`, `py`, `flask`, `pytest`, `pip`, `uv`, `poetry`, `tox`, `nox` ou outro interpretador/runner sobre o projeto;
- executar `main.py`, `teste_h24.py`, arquivos de `scripts/`, schedulers ou jobs;
- importar módulos Python do projeto, inclusive para introspecção, descoberta de testes ou validação;
- instalar, atualizar ou remover dependências;
- iniciar servidor, serviço Windows, container, navegador ou processo em segundo plano;
- abrir conexões ou executar consultas em SQL Server, Oracle, LDAP, SMTP, SAP, Plex, Graph/Teams ou qualquer serviço corporativo;
- fazer requests para endpoints da aplicação ou integrações internas/externas;
- executar migrations, DDL, `db.create_all()` ou alterar dados;
- enviar e-mails, mensagens, alertas ou notificações;
- abrir, mover, excluir ou modificar uploads e dados operacionais.

Motivos conhecidos:

- `create_app()` chama `db.create_all()`;
- `app/utils/dynamic_constants.py` inicia thread e pode consultar o Plex durante o import;
- `app/utils/azure_utils.py` inicia thread e pode solicitar token durante o import;
- configurações versionadas apontam para recursos corporativos;
- scripts, jobs e schedulers alteram bancos, arquivos e notificações;
- fora do IIS, a autenticação possui uma identidade fixa de fallback.

Nunca presuma que um import, teste, build ou comando de diagnóstico seja inofensivo.

## 2. O que é permitido

Trabalhe somente por análise estática:

- listar e ler arquivos como texto;
- pesquisar com `rg` e `rg --files`;
- usar Git de forma controlada conforme o fluxo da seção 4;
- analisar imports, decorators, SQL, HTML, Jinja, CSS e JavaScript como texto;
- editar arquivos solicitados com mudanças pequenas e localizadas;
- validar por diff, busca de referências e inspeção textual.

PowerShell e utilitários externos só podem tratar arquivos como texto. Não use o interpretador do projeto para validar sintaxe ou carregar módulos.

## 3. Contexto mínimo do projeto

- Monólito Flask/Jinja hospedado em Windows/IIS.
- `main.py` é a fonte de verdade para blueprints ativos.
- `app/config.py` cria o Flask e configura SQLAlchemy, login, permissões, e-mail e ciclo global.
- `app/routes/` contém o backend por domínio.
- `app/templates/` contém páginas Jinja, JavaScript incluído e templates de e-mail.
- Parte do JavaScript está inline ou em `.js` dentro de `templates`; esses arquivos podem depender de variáveis Jinja.
- `app/static/js/operation.planning/` e `app/static/js/demand-management/` contêm scripts compartilhados.
- `app/static/uploads/` contém dados operacionais, não fixtures.
- `app/services/` contém quatro schedulers Windows e seus jobs.
- A maior parte do acesso a dados usa SQL textual, pandas, SQLAlchemy ou pyodbc.
- Engines principais: `jdt`, `ftm`, `plex` e `trace_qr`.
- Integrações: IIS/Windows Auth, LDAP, SMTP, SAP SOAP, Oracle, Microsoft Graph/Teams, Power BI, FTWeb e SSRS.
- `computers`, `temp`, `productiveHours` e `setup` estão desativados no estado atual; confirme sempre em `main.py`.
- Arquivos com `Copy`, `BKP`, datas, `versaoFim` ou `NOT_ACTIVATED` são históricos até prova em contrário.

## 4. Fluxo remoto de Git

Este fluxo vale quando o responsável envia pelo Codex Remote um pedido que inclui **implementar ou alterar código**. Perguntas, diagnósticos e revisões somente de leitura não autorizam `pull`, edição ou commit.

O responsável autorizou commits locais diretamente na `main` para esse fluxo. Isso não autoriza `push` automático.

### 4.1 Antes de editar

1. Execute `git status --short`.
2. Se houver qualquer mudança local anterior, pare e informe os arquivos encontrados. Não faça `stash`, descarte, commit ou mistura automática.
3. Antes de qualquer comando Git mutável, confira como texto se há hooks ativos em `.git/hooks` ou `core.hooksPath`. Ignore arquivos `.sample`. Se um hook puder executar o projeto ou acessar recursos externos, pare.
4. Confirme com `git branch --show-current` que a branch é `main`. Se não for, pare; não troque de branch sozinho.
5. Confirme com `git remote` que o remoto `origin` existe. Não imprima URLs que possam conter credenciais ou tokens.
6. Execute somente `git pull --ff-only origin main`. Acesso de rede continua sujeito às permissões do ambiente.
7. Se o pull falhar, exigir merge, divergir ou apresentar conflito, pare e informe. Não use rebase, merge ou resolução automática por iniciativa própria. Quando a divergência envolver somente commits locais ainda não publicados, o responsável pode autorizar explicitamente o rebase na tarefa atual. Antes de executá-lo, confirme que a árvore está limpa, apresente os commits divergentes e verifique se os arquivos alterados se sobrepõem. Se o rebase apresentar conflito, pare e informe; não resolva o conflito sem uma nova autorização explícita.
8. Leia este arquivo, `README.md`, `main.py` e os arquivos diretamente ligados à funcionalidade.

Não solicite nem habilite Full Access ou acesso amplo à rede. Uma elevação de rede, quando necessária, deve ficar limitada ao comando Git exato desta seção ou a um push explicitamente autorizado.

### 4.2 Durante a implementação

- Preserve mudanças e comportamento fora do pedido.
- Faça alterações pequenas e focadas; não aproveite a tarefa para refatorar outras áreas.
- Não renomeie rotas, templates, tabelas, pastas ou arquivos por estética.
- Não edite cópias ou backups esperando alterar o código ativo.
- Não remova código legado sem pedido explícito e busca prévia de referências.
- Nunca inclua credenciais, tokens, strings de conexão, dados pessoais, logs ou uploads no commit.

### 4.3 Antes do commit

1. Revise `git status --short` e o diff completo.
2. Confirme que somente arquivos da tarefa foram alterados.
3. Execute apenas as validações estáticas permitidas na seção 8.
4. Verifique se nenhum segredo ou dado operacional entrou no diff, sem imprimir valores sensíveis.
5. Consulte `git log -15 --pretty=format:"%s"` e siga o padrão recente do mesmo módulo. Não invente ou incremente versão sem base clara no histórico ou no pedido.
6. Adicione arquivos individualmente; nunca use `git add .`, `git add -A` ou `git commit -a`.
7. Faça um único commit focado na `main`, salvo se o responsável pedir outra divisão.

### 4.4 Depois do commit

- Informe hash, mensagem e arquivos incluídos.
- Declare que o sistema não foi executado e que a validação foi somente estática.
- **Não faça `git push` sem uma instrução explícita do responsável naquela tarefa.**
- Quando o push for autorizado, use apenas o push normal da `main`; nunca use `--force` ou `--force-with-lease`.
- Não crie branch, tag, PR, release ou novo commit sem solicitação.

## 5. Como analisar uma funcionalidade

Rastreie a cadeia completa:

```text
URL, menu ou botão
  → blueprint registrado em main.py/create_app()
  → before_request e decorators de permissão
  → handlers de todos os métodos HTTP
  → template, JSON, arquivo ou redirect retornado
  → JavaScript inline, include, formulário, fetch ou XMLHttpRequest
  → query args e payload
  → tabelas lidas e gravadas
  → uploads, downloads e exports
  → e-mails e integrações externas
  → jobs que alteram os mesmos dados
```

Não analise apenas GET. O projeto concentra regras em POST, PATCH, PUT e DELETE e frequentemente seleciona operações por `type`, `cmd`, `area` ou `id`.

## 6. Regras por área

### Arquitetura de novas features Flask

Para features novas, prefira uma organização autocontida por domínio, seguindo o padrão adotado no Gerenciador de Demandas:

```text
app/
├── routes/<feature>/
│   ├── __init__.py          # exporta o blueprint
│   ├── routes.py            # HTTP, autorização, CSRF e composição
│   ├── services.py          # casos de uso, regras e transações
│   ├── repository.py        # SQL parametrizado e acesso a dados
│   ├── domain.py            # opções, validações e erros da feature (opcional)
│   └── integration.py       # e-mail e sistemas externos (opcional)
├── templates/<feature>/
│   └── pagina.html          # estrutura HTML e valores fornecidos pelo Jinja
└── static/
    ├── CSS/<feature>.css    # aparência e responsividade
    └── js/<feature>/
        └── pagina.js        # estado da tela, eventos, renderização e chamadas à API
```

No backend, `routes.py` deve traduzir requisições e respostas sem conter SQL ou regras extensas; `services.py` coordena os casos de uso e os limites das transações; e `repository.py` concentra as consultas ao banco sem conhecer Flask. Use `domain.py` e `integration.py` somente quando essas responsabilidades realmente existirem. Não crie arquivos vazios ou camadas artificiais: uma feature pequena pode começar apenas com `__init__.py`, `routes.py`, `services.py` e `repository.py`.

No frontend, mantenha o HTML estrutural no template Jinja, o CSS em `app/static/CSS/` e o JavaScript em `app/static/js/`. Essa separação é o padrão correto do Flask: templates são renderizados no servidor, enquanto CSS e JavaScript são arquivos estáticos servidos diretamente. Use o mesmo nome ou prefixo da feature nessas pastas para que os arquivos continuem fáceis de localizar como uma unidade.

O template pode expor para o JavaScript apenas uma configuração pequena gerada pelo Jinja, como URLs produzidas por `url_for`, área atual e token CSRF. A lógica de interação, estado, eventos, `fetch` e atualização da interface deve permanecer no arquivo `.js`; estilos e regras responsivas ficam no `.css`. Prefira classes CSS com prefixo da feature para evitar conflito com telas legadas. Regras de autorização e de negócio continuam obrigatoriamente no backend, mesmo quando a interface também faz validações.

Arquivos JavaScript já existentes dentro de `templates` podem depender diretamente de variáveis Jinja e não devem ser movidos por estética. Para features novas, prefira JavaScript em `static` e passe os poucos valores dinâmicos necessários por um objeto de configuração no HTML, como feito no Gerenciador de Demandas.

### Segurança e dados sensíveis

- Nunca reproduza valores de credenciais, tokens, chaves, senhas ou strings de conexão.
- Descreva segredos apenas por arquivo e categoria.
- Não teste credenciais nem copie segredos para documentação, mensagens ou commits.
- Trate logs, payloads e uploads como dados potencialmente confidenciais.
- Remover um segredo do código não substitui rotação/revogação e tratamento do histórico Git.

### Banco e SQL

- Não altere schema, views, procedures ou dados sem autorização específica.
- Use parâmetros em SQL novo; não interpole entrada de request em f-strings.
- Não presuma que `jdt` é a única fonte: telas podem cruzar FTM, Plex, Trace QR e bancos qualificados.
- Procure jobs que escrevem nas mesmas tabelas.
- Preserve transações e commits explícitos de cada tecnologia.

### Autenticação e autorização

- Autenticação principal: token Windows do IIS e LDAP; sessão via Flask-Login.
- Roles vêm do JSON textual de `JDT_USER_DETAILS.role` e Flask-Principal.
- Verifique autorização no backend, não apenas elementos escondidos na interface.
- `current_user.admin` é armazenado como string; não o trate implicitamente como booleano.
- Não use o fallback de login fora do IIS para testes.

### Frontend

- Preserve `.js` incluídos por Jinja em `app/templates`; movê-los para `static` exige adaptar variáveis Jinja.
- Pesquise JavaScript inline, `{% include %}`, formulários, `fetch`, `XMLHttpRequest`, redirects e links de menu.
- Ao alterar um template, pesquise todos os `render_template` e includes correspondentes.
- Não presuma uma API REST convencional: POST também pode consultar ou exportar.

### Arquivos

- Não abra nem modifique arquivos de usuário em `app/static/uploads/`.
- Em código de upload/download, valide autorização, canonicalização, path traversal e `secure_filename`.
- Considere caminhos absolutos e usos inconsistentes de `os.getcwd()` e `APP_PATH`.
- Não use comandos destrutivos para limpar logs, backups ou uploads.

### Schedulers

- S30 consolida monitoramento a cada 30 segundos.
- M5 processa alertas e relógio-ponto a cada 5 minutos.
- H24 executa rotinas diárias de usuários, demandas, paradas, laboratório e desvios.
- Auto processa agenda de equipamentos do laboratório a cada minuto.
- Mudanças em status, prazos, usuários, equipamentos ou alertas devem considerar rotas e jobs.

## 7. Riscos conhecidos

Não corrija estes itens automaticamente fora do escopo da tarefa:

- segredos versionados;
- `db.create_all()` durante a criação do app;
- threads e acesso externo iniciados em imports;
- SQL interpolado e uso de `eval`;
- ausência aparente de CSRF;
- paths dinâmicos de arquivo e caminhos absolutos;
- fallback de autenticação fora do IIS;
- string usada como booleano em `current_user.admin`;
- templates referenciados, mas ausentes;
- módulos e dashboards bloqueados/desativados;
- falta de testes isolados;
- backups, logs e dados operacionais rastreados.

Em diagnóstico, informe causa, impacto, evidência e arquivos envolvidos. Diferencie fato observado de inferência dependente do ambiente.

## 8. Validação permitida

Use somente:

- `git diff --check`;
- `git diff`, `git status` e inspeção do patch;
- `rg` para referências de rotas, templates, imports, tabelas e nomes alterados;
- comparação textual de frontend e backend;
- conferência manual de delimitadores, indentação e blocos;
- validação de Markdown como texto.

Não execute compilação Python (`py_compile`, `compileall`), testes, linters, formatadores, builds ou ferramentas de descoberta automática sem autorização explícita.

## 9. Comunicação final

Ao concluir uma tarefa:

- resuma o que mudou e os arquivos principais;
- informe o commit quando o fluxo remoto tiver autorizado sua criação;
- declare explicitamente: **“O sistema não foi executado; a validação foi somente estática.”**;
- informe limitações que só poderiam ser verificadas em ambiente autorizado;
- nunca exponha segredos;
- se a única forma de continuar exigir execução, acesso externo, conflito Git ou ação destrutiva, pare e peça orientação.
