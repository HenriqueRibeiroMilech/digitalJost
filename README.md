# Digital JOST

Portal interno para demandas, operações industriais, laboratório, desvios, monitoramento, relatórios e usuários. A modernização acontece gradualmente, preservando os fluxos antigos.

## Comece pelo manual

A documentação oficial está em **[handbook/README.md](handbook/README.md)**.

- [Arquitetura e modernização](handbook/docs/arquitetura-modernizada.md): organização, responsabilidades e critérios para novas funcionalidades.
- [Ambiente, servidor e publicação](handbook/docs/servidor-e-publicacao.md): preparação do computador, configuração privada, build, IIS e serviços Windows.
- [Publicação no Azure DevOps](handbook/docs/publicacao-azure.md): envio da versão de código ao repositório Azure.
- [Padrão visual](handbook/docs/padrao-visual.md): componentes, layout e interação das telas modernas.

Regras operacionais para agentes ficam em [AGENTS.md](AGENTS.md). Planos, análises e tutoriais anteriores foram preservados no [histórico](handbook/historico/README.md).

## Mapa do repositório

| Local | Responsabilidade |
|---|---|
| `main.py`, `app/config.py` | Entrada, factory, extensões, sessão e ciclo global da aplicação. |
| `app/` | Backend Flask/Jinja legado, integrações, arquivos e schedulers. |
| `backend/` | Inicialização e configuração na raiz, funcionalidades em `modules/`, recursos comuns em `shared/` e entrega do Vue em `web/`. |
| `frontend/` | Código Vue/TypeScript, navegação e componentes. |
| `backend/web/static/app/` | Build Vue gerado; ignorado pelo Git, precisa acompanhar a publicação quando necessário. |
| `database/` | Scripts SQL sujeitos a revisão e aplicação explícita. |
| `handbook/docs/` | Guias gerais oficiais. |
| `handbook/features/` | Documentação atual de funcionalidades e recursos compartilhados. |
| `handbook/historico/` | Registros anteriores, identificados como históricos. |

## Como as partes convivem

Há uma aplicação Flask no Windows/IIS: `main.py` registra o legado, e a factory chama o bootstrap moderno. A sessão e os perfis antigos são reutilizados por uma ponte; o backend moderno ainda não é independente de `app/`.

Módulos modernos compartilham um engine/pool do TD por instância da aplicação. O legado mantém acessos próprios, inclusive a outras fontes; conexões diferentes não formam uma transação conjunta.

O frontend gera os assets em `backend/web/static/app/`. Fazer pull não gera build nem instala dependências. Seguir o guia de servidor para preparar e publicar uma versão compatível, preservando configuração privada e dados operacionais.

A inicialização ainda contém efeitos do legado. Não iniciar, importar, testar ou conectar o sistema por iniciativa do agente; autorizações precisam indicar comando, ambiente e escopo conforme AGENTS.md.
