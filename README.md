# Digital JOST

Portal interno da JOST para operações industriais, solicitações, gestão, monitoramento e relatórios.

> **Atenção:** este repositório não deve ser executado localmente nem importado apenas para inspeção. A inicialização e alguns imports podem acessar bancos e serviços corporativos, criar threads e executar operações externas. Consulte [AGENTS.md](AGENTS.md) antes de trabalhar no código.

## Documentação principal

- [AGENTS.md](AGENTS.md) — regras obrigatórias de segurança, contexto arquitetural, roteiro de análise estática e fluxo remoto de Git.
- [Arquitetura e modernização](docs/arquitetura-modernizacao.md) — decisões, organização e roteiro de adoção progressiva.
- [Plano de separação do backend e legado](docs/plano-separacao-backend-legado.md) — etapas da transição para `backend/` e registro das entregas.
- [Guia da primeira feature: Eventos](docs/guia-primeira-feature-eventos.md) — tutorial de cards e cadastro de nome e descrição na arquitetura nova.

O próprio código é a fonte de verdade para detalhes funcionais. Comece por `main.py` e rastreie a rota, o template, o JavaScript, as tabelas e os jobs envolvidos.

## Visão geral

O Digital JOST é um monólito Flask hospedado em Windows/IIS. O backend renderiza páginas Jinja e as telas usam formulários, `fetch` e `XMLHttpRequest` para chamar as próprias rotas Flask.

```text
Navegador
  → IIS com autenticação Windows
  → Flask / Blueprints
  → Templates Jinja + JavaScript
  → SQL Server, Plex, FT Metrics, Trace QR e arquivos
  → LDAP, SMTP, SAP, Oracle e Microsoft Graph quando necessário
```

As telas Vue convivem com as páginas Jinja na mesma aplicação. Eventos fica em `/app/eventos`, com API em `/api/v1/events` e código Python em `backend/modules/events/`.

O carregamento do build Vue e a renderização da página base são compartilhados em `backend/platform/vue_shell.py`. Cada módulo mantém sua rota e suas verificações de acesso, fornecendo título, token CSRF e mensagem de indisponibilidade ao shell. O template fica em `backend/templates/app/shell.html`. O comando `npm run build:local`, executado em `frontend/`, gera o build em `backend/static/app/`, ignorado pelo Git e servido em `/static/app/`. Consulte o [registro da entrega 3b](docs/plano-separacao-backend-legado.md#12-registro-da-entrega-3b) para o pacote e o procedimento de retorno.

O backend moderno possui configuração e engine/pool próprios para o TD, compartilhados pelos seus módulos. A factory fornece o destino já configurado para o banco; os acessos do legado continuam nos mecanismos atuais. As opções do pool, seu ciclo de vida e o procedimento de retorno estão no [registro da entrega 2](docs/plano-separacao-backend-legado.md#10-registro-da-entrega-2).

## Principais funcionalidades

- Gestão de demandas, projetos e tarefas;
- solicitações de melhorias;
- desvios de processo e planos de ação;
- solicitações de serviço de laboratório;
- gestão e agendamento de equipamentos do laboratório;
- alteração de paradas industriais;
- indicadores de logística, produção, qualidade e SSMA;
- planejamento do Operation Meeting;
- monitoramento industrial, hardware e OEE;
- rastreabilidade QR e gestão de plaquetas;
- matriz de versatilidade;
- metas, fatores e auditorias 5S;
- biblioteca de conhecimentos;
- comunicação interna em TVs/cockpit;
- relatórios de manutenção e Power BI;
- gestão de usuários, áreas, perfis e alertas.

## Tecnologias

- Python;
- Flask, Flask-Login, Flask-Principal, Flask-Mail e Flask-SQLAlchemy;
- SQLAlchemy, pyodbc e pandas;
- Microsoft SQL Server;
- Oracle em um job de sincronização;
- Jinja2, HTML, CSS e JavaScript;
- Plotly para dashboards;
- LDAP/Active Directory;
- Microsoft Graph/Teams;
- SOAP/Zeep para SAP;
- APScheduler e serviços Windows;
- IIS `httpPlatformHandler`.

As versões completas estão fixadas em `requirements.txt`.

## Estrutura do projeto

```text
DigitalJost/
├── main.py                         # Criação do app e registro de blueprints
├── web.config                      # Configuração do IIS
├── requirements.txt                # Dependências Python
├── README.md                       # Introdução e onboarding
├── AGENTS.md                       # Regras para agentes e automações
├── app/
│   ├── config.py                   # Factory Flask e extensões
│   ├── errors.py                   # Handlers de erro
│   ├── models/                     # Modelo ORM de usuário
│   ├── routes/                     # Backend legado organizado por domínio
│   ├── templates/                  # Jinja, JavaScript incluído e e-mails
│   ├── static/                     # CSS, JS, imagens, vídeos e uploads
│   ├── services/                   # Schedulers e jobs
│   └── utils/                      # Banco, segurança, arquivos e integrações
├── backend/                        # Backend moderno, inicialmente com Eventos
│   ├── bootstrap.py                # Composição e registro do backend moderno
│   ├── config.py                   # Opções próprias do acesso geral ao TD
│   ├── platform/
│   │   ├── database.py             # Engine/pool compartilhado pelos módulos modernos
│   │   └── vue_shell.py            # Recursos, assets e renderização do shell Vue
│   ├── modules/                    # Registro explícito e módulos modernos
│   ├── templates/app/shell.html    # Página base do Vue
│   └── static/app/                 # Build Vue gerado e ignorado pelo Git
├── frontend/                       # Código-fonte da interface Vue
├── scripts/                        # Manutenções manuais potencialmente destrutivas
└── logs/                           # Logs históricos
```

## Pontos de entrada para leitura

Leia nesta ordem:

1. `AGENTS.md` — regras obrigatórias de segurança;
2. `main.py` — módulos registrados;
3. `app/config.py` — criação do Flask e ciclo global;
4. `app/templates/home.html` — menu e navegação;
5. `app/utils/permissions.py` — perfis;
6. rota, template e JavaScript do módulo que será alterado.

## Módulos ativos

O `main.py` é a fonte de verdade sobre os blueprints ativos.

| Domínio | Backend principal |
|---|---|
| Autenticação e home | `app/routes/auth_routes.py`, `main_default_routes.py` |
| Demandas | `app/routes/demands/default.py` |
| Rastreabilidade e cadastros | `app/routes/factoryRegister/` |
| Comunicação, biblioteca, monitoramento e usuários | `app/routes/jdt/` |
| Operation Meeting | `app/routes/operation/` |
| Manutenção, OEE e Power BI | `app/routes/reports/` |
| Melhorias, laboratório, desvios e paradas | `app/routes/request/` |

## Módulos presentes, mas desativados

Os seguintes módulos possuem código no repositório, porém não estão registrados atualmente:

- computadores;
- extras/temporário;
- horas produtivas;
- setup.

Também existem arquivos `Copy`, `BKP`, arquivos com datas e `versaoFim`. Não os trate como versão ativa sem confirmar o import em `main.py`.

## Execução local

**Não há procedimento de execução local autorizado neste repositório.**

Não execute:

- `python main.py`;
- `flask run`;
- `teste_h24.py`;
- arquivos em `scripts/`;
- arquivos `run_*_scheduler.py`;
- jobs em `app/services/jobs/`;
- imports Python para introspecção;
- testes, builds ou instalação de dependências sem autorização explícita.

Motivos:

- `create_app()` chama `db.create_all()`;
- módulos podem iniciar threads durante o import;
- configurações apontam para recursos corporativos;
- scripts e jobs podem alterar registros, mover arquivos ou enviar notificações;
- há identidade fixa de fallback fora do IIS.

Toda investigação inicial deve ser feita por leitura estática.

## Como rastrear uma tela

```text
URL no menu ou JavaScript
  → decorator @blueprint.route no arquivo Python
  → função GET/POST/PATCH/PUT/DELETE
  → render_template ou resposta JSON/arquivo
  → template em app/templates
  → JavaScript inline ou incluído
  → SQL, upload, e-mail ou integração externa
```

## Bancos e integrações

O utilitário `app/utils/db_utils.py` expõe quatro engines:

- `jdt` — dados principais do portal;
- `ftm` — eventos e informações industriais do FT Metrics/Mach2;
- `plex` — dados do Plex e linked server;
- `trace_qr` — rastreabilidade de montagem.

O sistema também se integra com Active Directory, SMTP, SAP SOAP, Oracle, Microsoft Graph/Teams, Power BI e sistemas legados via iframe.

## Serviços automáticos

Há quatro schedulers separados da aplicação web:

- a cada 30 segundos: consolidação do monitoramento;
- a cada 5 minutos: alertas de paradas e sincronização de ponto;
- diariamente: usuários, demandas, laboratório, desvios e alterações de parada;
- a cada minuto: agendamentos automáticos do laboratório, início agendado de demandas e geração de atividades recorrentes.

Eles são serviços Windows e modificam as mesmas fontes utilizadas pelas telas.

## Segurança

O repositório contém problemas conhecidos que devem ser tratados antes de qualquer abertura ou modernização:

- credenciais e segredos versionados;
- SQL montado por interpolação em diversos pontos;
- downloads e exclusões baseados em caminhos dinâmicos;
- ausência aparente de proteção CSRF;
- efeitos externos durante inicialização/importação;
- verificação TLS desabilitada em algumas integrações;
- logs e payloads potencialmente sensíveis;
- código legado, backups e logs rastreados no Git.

Não copie credenciais para documentação, tickets, commits ou mensagens. Consulte as regras e os riscos conhecidos em `AGENTS.md`.

## Regra de contribuição

Antes de modificar qualquer funcionalidade:

1. confirme qual arquivo está ativo;
2. leia permissões e todos os métodos da rota;
3. identifique tabelas, arquivos e integrações afetadas;
4. procure jobs que alteram os mesmos dados;
5. preserve mudanças existentes no worktree;
6. faça alterações pequenas e localizadas;
7. valide estaticamente enquanto não houver ambiente seguro autorizado;
8. atualize `README.md` ou `AGENTS.md` quando arquitetura, regras de segurança ou o fluxo de manutenção mudarem.
