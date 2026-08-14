# AGENTS.md — instruções para trabalhar no Digital JOST

Este arquivo aplica-se a todo o repositório.

## Regra principal: não executar o sistema

**É proibido executar, inicializar ou importar o Digital JOST neste ambiente, salvo autorização explícita posterior do responsável pelo sistema.**

Não faça nenhuma destas ações por iniciativa própria:

- executar `python main.py`, `flask run` ou qualquer servidor;
- importar `main`, `app.config`, módulos de rota, utilities ou jobs com Python;
- instalar, atualizar ou remover dependências;
- executar testes, builds, linters que importem o projeto ou ferramentas de descoberta automática;
- executar `teste_h24.py`;
- executar qualquer arquivo de `scripts/`;
- executar `app/services/run_*_scheduler.py`;
- executar funções de `app/services/jobs/`;
- iniciar serviços Windows;
- abrir conexão com banco, LDAP, SMTP, SAP, Oracle, Plex, Microsoft Graph ou outro recurso corporativo;
- disparar requests HTTP para endpoints internos/externos do projeto;
- executar migrations, `db.create_all()`, DDL ou consultas SQL;
- enviar e-mails, mensagens Teams ou notificações;
- mover, excluir, gerar ou alterar uploads/dados operacionais;
- abrir a aplicação em navegador para teste local.

### Por que essa regra existe

- `create_app()` executa `db.create_all()`;
- `dynamic_constants.py` inicia thread e pode consultar Plex durante o import;
- `azure_utils.py` inicia thread e pode solicitar token durante o import;
- configurações versionadas apontam para infraestrutura corporativa;
- scripts e jobs alteram bancos, arquivos e notificações;
- fora do IIS, o login possui identidade fixa de fallback;
- alguns módulos realizam trabalho no import ou na inicialização.

Não presuma que um import Python, teste ou comando de diagnóstico seja inofensivo.

## Forma autorizada de investigação

Use somente análise estática, salvo instrução explícita em contrário:

- listar e ler arquivos;
- pesquisar texto com `rg`/`rg --files`;
- usar comandos Git somente de leitura, como `git status`, `git diff` e `git log`;
- analisar decorators, imports, SQL e templates como texto;
- comparar referências de rota/template por processamento textual que não importe o projeto;
- editar documentação ou código solicitado usando `apply_patch`;
- validar sintaxe e consistência por leitura/regex quando a validação normal importaria o sistema.

PowerShell e utilitários externos podem ser usados apenas para tratar arquivos como texto. Não invoque interpretadores do projeto para carregar módulos.

## Contexto obrigatório

Antes de uma mudança relevante:

1. leia este arquivo;
2. consulte [GUIA_TECNICO_DIGITAL_JOST.md](GUIA_TECNICO_DIGITAL_JOST.md);
3. use `main.py` como fonte de verdade para módulos ativos;
4. leia a seção do guia correspondente ao domínio;
5. rastreie a cadeia completa de frontend a dados.

O guia técnico contém arquitetura, 179 paths ativos, templates, JavaScript, tabelas, integrações, schedulers, módulos desativados e riscos conhecidos.

## Resumo arquitetural para agentes

- Monólito Flask/Jinja hospedado em Windows/IIS.
- `main.py` cria o app e registra blueprints.
- `app/config.py` configura Flask, SQLAlchemy, Flask-Login, Flask-Principal e Flask-Mail.
- `app/routes/` contém backend por domínio.
- `app/templates/` contém HTML Jinja, JavaScript incluído e e-mails.
- Parte do JavaScript está inline; parte está em `.js` dentro de `templates`.
- `app/static/js/operation.planning/` contém scripts compartilhados do planejamento.
- `app/static/uploads/` contém dados operacionais de usuários.
- `app/services/` contém serviços Windows e jobs independentes da aplicação web.
- O modelo ORM explícito é `User`; a maior parte dos dados usa SQL textual e pandas.
- Engines: `jdt`, `ftm`, `plex` e `trace_qr`.
- Integrações adicionais: LDAP, SMTP, SAP SOAP, Oracle, Graph/Teams, Power BI e sistemas FTWeb/SSRS.

## Fluxo de análise de uma funcionalidade

Sempre rastreie:

```text
link/URL
  → blueprint registrado
  → before_request e decorators de permissão
  → handler por método HTTP
  → template/JSON/arquivo retornado
  → JavaScript, formulário ou fetch
  → query args e payload
  → tabelas lidas e gravadas
  → uploads/exports
  → e-mails e integrações
  → jobs que alteram os mesmos dados
```

Não analise apenas a função GET: várias regras ficam em POST/PATCH/PUT/DELETE ou são selecionadas por parâmetros como `type`, `cmd`, `area` e `id`.

## Fonte de verdade e arquivos legados

- Um módulo só deve ser considerado ativo quando seu blueprint estiver registrado em `main.py` ou `create_app()`.
- `computers`, `temp`, `productiveHours` e `setup` estão desativados no snapshot documentado.
- Arquivos com `Copy`, `BKP`, datas, `versaoFim` ou `NOT_ACTIVATED` são históricos, salvo prova explícita em contrário.
- Não edite um backup esperando alterar o comportamento ativo.
- Não remova arquivos legados sem pedido explícito e análise de referências.

## Segurança e dados sensíveis

O repositório contém segredos em texto puro. Ao trabalhar nele:

- nunca reproduza credenciais, tokens, chaves, strings de conexão ou senhas em respostas;
- nunca copie segredos para README, guia, comentários, issues ou commits;
- descreva achados usando localização e categoria, não o valor;
- não teste credenciais;
- não acesse serviços usando essas credenciais;
- evite exibir linhas contendo segredos na saída de ferramentas;
- trate logs, payloads e uploads como potencialmente confidenciais.

Se a tarefa for corrigir segredos, a remoção do código não substitui rotação/revogação e tratamento do histórico Git.

## Cuidados com banco e SQL

- Há SQL interpolado por f-string e entrada de request em vários módulos.
- Prefira parâmetros nomeados/posicionais em qualquer código novo.
- Não altere schema, tabelas, views, procedures ou dados sem autorização específica.
- Não presuma que `jdt` seja a única fonte: uma tela pode cruzar FTM, Plex e bancos qualificados.
- Procure jobs que escrevem na mesma tabela antes de propor mudança.
- Considere transações e commits explícitos; os padrões variam entre SQLAlchemy e pyodbc.
- `db.create_all()` na inicialização é um risco conhecido; não o acione.

## Cuidados com arquivos

- Uploads sob `app/static/uploads/` são dados operacionais, não fixtures.
- Não apague, mova, renomeie ou abra arquivos de usuário sem pedido explícito.
- Antes de alterar download/upload, valide path traversal, canonicalização, autorização e `secure_filename`.
- Há usos inconsistentes de `os.getcwd()`, `APP_PATH` e caminhos absolutos.
- Scripts em `scripts/` podem mover arquivos reais e são proibidos por padrão.
- Não use comandos destrutivos para “limpar” logs, uploads ou backups.

## Autenticação e autorização

- Autenticação principal: token Windows do IIS e consulta LDAP.
- Sessão: Flask-Login.
- Roles: JSON textual em `JDT_USER_DETAILS.role` convertido em Flask-Principal.
- Quase todo blueprint possui `before_request` com autenticação e `GENERAL`.
- Há permissões específicas como `LABORATORY`, `DEVIATION`, `QUALITY`, `SSMA` e `SYSADMIN`.
- Não confie apenas no que a interface esconde; valide autorização no backend.
- `current_user.admin` é armazenado como string e seu uso como booleano é um risco conhecido.
- O fallback de login fora do IIS é um risco conhecido; não dependa dele para testes.

## Frontend

- Preserve includes Jinja de arquivos `.js` em `app/templates`.
- Não mova esses scripts para `static` sem adaptar variáveis Jinja.
- Verifique JavaScript inline, includes e scripts compartilhados.
- Muitas telas usam o mesmo path para GET e POST.
- Não suponha semântica REST convencional; POST também pode consultar/exportar.
- Ao mudar uma URL, pesquise formulários, `fetch`, `XMLHttpRequest`, redirects e menu.
- Ao mudar um template, pesquise `render_template`, `{% include %}` e e-mails relacionados.

## Schedulers

Existem quatro serviços separados:

- S30: consolidação de monitoramento a cada 30 segundos;
- M5: alertas Teams e relógio-ponto a cada 5 minutos;
- H24: rotinas diárias de usuários, demandas, paradas, laboratório e desvios;
- Auto: agendamentos de equipamentos do laboratório a cada minuto.

Mudanças em status, prazos, usuários, equipamentos ou alertas devem considerar tanto as rotas quanto esses jobs.

## Edição do repositório

- Preserve mudanças existentes do usuário.
- Antes de editar, verifique `git status --short`.
- Faça mudanças pequenas e localizadas.
- Use `apply_patch` para editar arquivos.
- Não faça refatoração ampla sem solicitação.
- Não altere nomes de rotas, templates, tabelas ou pastas por estética.
- Não faça commit, push, branch, PR ou stage sem pedido explícito.
- Não altere `.gitignore` para esconder um problema sem entender arquivos já rastreados.
- Se arquitetura, rota, tabela, integração ou scheduler mudar, atualize `GUIA_TECNICO_DIGITAL_JOST.md` e, quando apropriado, `README.md`.

## Validação permitida por padrão

Como a aplicação não pode ser executada, valide proporcionalmente por meios estáticos:

- `git diff --check` para arquivos já rastreados;
- inspeção do diff;
- busca de referências com `rg`;
- comparação textual de rotas e templates;
- conferência de imports sem carregá-los;
- conferência de delimitadores, indentação e blocos por leitura;
- validação de Markdown como texto.

Não execute compilação Python (`py_compile`, `compileall`) sem autorização, pois a política deste projeto é não acionar ferramentas Python sobre o código neste ambiente.

## Achados conhecidos que não devem ser esquecidos

- segredos versionados;
- `db.create_all()` durante criação do app;
- threads iniciadas em import;
- SQL interpolado;
- ausência aparente de CSRF;
- paths dinâmicos de arquivo;
- `os.abort(403)` em rastreabilidade;
- uso de string como booleano em `current_user.admin`;
- template `jdt.permission/permission_pending.html` ausente;
- template `planning_area2.html` ausente;
- dashboard de alteração de paradas bloqueado por retorno antecipado;
- alertas sistêmicos via Teams aparentemente sem envio efetivo;
- falta de testes isolados;
- backups e grande volume de logs rastreados.

Não corrija esses itens automaticamente quando a tarefa não pedir implementação. Em tarefas de diagnóstico, documente causa, impacto e arquivos envolvidos.

## Comunicação com o responsável

- Informe explicitamente que o sistema não foi executado.
- Diferencie fato observado no código de inferência dependente do ambiente.
- Quando não houver validação dinâmica autorizada, diga isso claramente.
- Aponte os arquivos exatos envolvidos.
- Não exponha segredos em explicações.
- Se a única forma de prosseguir exigir execução, acesso externo ou ação destrutiva, pare e solicite autorização.

