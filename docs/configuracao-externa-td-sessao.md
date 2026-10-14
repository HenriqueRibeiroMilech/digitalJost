# Configuração externa do TD e da sessão

Data: **13/10/2026**. Entrega S1 limitada ao banco TD e à chave da sessão Flask.

**Evolução posterior — S1b, 14/10/2026:** este documento registra a primeira entrega, commit `21c4c81`. O código atual também carrega arquivo privado e externaliza as outras integrações identificadas. Para preparação, pacote e retorno da versão atual, usar o [guia de configuração privada das integrações](configuracao-privada-integracoes.md). O pacote de quatro arquivos e a ausência de leitura de `.env` descritos originalmente abaixo não são o procedimento atual.

## 1. Decisão e estado da entrega

Por decisão do responsável, **as credenciais atuais serão mantidas nesta etapa**. O código passa a recebê-las do ambiente dos processos, sem valores literais para TD ou sessão e sem fallback para os valores anteriores. O destino continua sendo o mesmo banco corporativo aprovado.

A implementação está preparada no repositório e foi revisada somente como texto. As variáveis não foram cadastradas no PC/servidor; não houve publicação, execução, conexão, troca de senha, revogação ou alteração de schema/dados.

Retirar os valores do código atual não elimina sua presença nas versões anteriores, clones e cópias. A exposição anterior permanece enquanto os mesmos valores forem válidos. Outros bancos e integrações do inventário da revisão de segurança também permanecem pendentes; esta entrega não os modifica.

## 2. Como as arquiteturas recebem a configuração

```text
Ambiente do processo no PC ou no servidor
    ├── DJ_TD_ODBC_CONNECTION_STRING
    │       ├── app/utils/constants.py → CNNX_JDT
    │       │       → conexões legadas, rotas e jobs
    │       └── backend/config.py → BackendConfig.from_env()
    │               → engine/pool geral do backend moderno
    │                   → Eventos e próximas funcionalidades
    └── DJ_SESSION_SECRET_KEY
            → app/config.py → sessão Flask compartilhada
```

Cada arquitetura mantém sua configuração e seus mecanismos de conexão. O backend moderno deixa de receber `app.config["SQLALCHEMY_DATABASE_URI"]`; sua configuração lê o TD diretamente do ambiente. Os nomes, consumidores, pools e transações existentes do legado são preservados. O pool moderno continua sendo único por instância da aplicação e compartilhado pelos módulos.

O leitor pequeno em `backend/platform/environment.py` é usado também como ponte pelo legado. Ele apenas lê uma variável quando chamado: importar esse módulo não lê segredos, cria conexão, inicia thread nem carrega Flask ou módulos de `app/`. Exige um valor não vazio, preserva os caracteres originais e informa somente o nome da variável quando ela está ausente ou contém apenas espaços.

`app/utils/constants.py` continua resolvendo `CNNX_JDT` durante seu import, para preservar o contrato legado. Portanto, a variável do TD deve existir **antes de iniciar qualquer consumidor dessas constantes**, inclusive processos que importem o módulo apenas para outras configurações. Isso não remove os demais efeitos de import/inicialização já conhecidos no sistema.

## 3. Variáveis obrigatórias

| Nome | Valor a cadastrar privadamente | Consumidores |
| --- | --- | --- |
| `DJ_TD_ODBC_CONNECTION_STRING` | O valor completo da conexão ODBC anteriormente definido em `CNNX_JDT`, preservando driver, servidor, banco, usuário, senha e demais opções. | Portal legado, backend moderno, serviços e scripts que importam as constantes direta ou indiretamente. |
| `DJ_SESSION_SECRET_KEY` | O valor efetivo da `SECRET_KEY` atual, preservado exatamente. | Aplicação Flask; também qualquer processo que importe `app/config.py`. |

Cadastrar o **valor efetivo**, sem os delimitadores, prefixos de literal Python ou concatenações do arquivo antigo. Não alterar parâmetros de conexão, codificar a conexão manualmente como URL nem gerar uma nova chave nesta entrega. As configurações de cada arquitetura fazem a construção/formatação que já utilizavam.

Usar a mesma chave mantém a assinatura das sessões; as outras regras de validade das sessões continuam aplicáveis. Uma chave diferente exigirá novo login. Usar as mesmas credenciais do TD mantém o acesso conforme os privilégios existentes; esses privilégios não foram verificados.

As opções `BACKEND_TD_POOL_SIZE`, `BACKEND_TD_MAX_OVERFLOW`, `BACKEND_TD_POOL_TIMEOUT` e `BACKEND_TD_POOL_RECYCLE` permanecem opcionais, com os padrões da entrega 2. Não são necessárias novas variáveis por funcionalidade.

O [.env.example](../.env.example) contém somente os nomes, com valores vazios. **Na primeira S1, a aplicação não implementava carregamento de `.env`. A S1b adiciona essa leitura**, conforme o guia atual indicado acima. O `.gitignore` ignora `.env` e `.env.*`, exceto esse modelo. Essa proteção não retira arquivos já rastreados nem protege um arquivo de configuração contra acesso pelo servidor web.

## 4. Preparação no computador de desenvolvimento

1. Antes de atualizar o código utilizado para execução, obter privadamente os dois valores da configuração anterior ou da fonte aprovada pela empresa. Não enviá-los em chat, documentação, screenshots, arquivos de transferência pública ou comandos registrados no histórico.
2. Cadastrar as duas variáveis no ambiente do usuário Windows que abre o VS Code. A interface de Variáveis de Ambiente do Windows permite cadastrar nome e valor sem gravá-los no código. Caso a empresa use outro mecanismo de injeção, ele deve fornecer essas mesmas variáveis ao processo Python.
3. Fechar e reabrir o VS Code e os terminais utilizados, para que os novos processos recebam o ambiente atualizado. Não listar ou imprimir os valores como diagnóstico.
4. Atualizar todos os arquivos desta entrega juntos. Não é necessária instalação de dependências nem novo build Vue para esta alteração Python.
5. A verificação funcional depende de ambiente, comando e escopo explicitamente autorizados. O banco corporativo continua sendo utilizado e a inicialização existente pode produzir efeitos externos; o cadastro das variáveis não autoriza execução pelo agente.

## 5. Preparação no IIS e nos serviços Windows

O servidor utiliza IIS/httpPlatformHandler e quatro serviços Windows. Seu mecanismo efetivo de provisionamento de ambiente não foi inspecionado. Uma variável cadastrada apenas no usuário que acessa o servidor não garante que IIS e serviços a recebam.

Antes da publicação, o responsável/TI deve:

1. Identificar as identidades e os processos que iniciam o portal e os serviços S30, M5, H24 e Auto. Incluir scripts manuais que utilizem as constantes.
2. Disponibilizar `DJ_TD_ODBC_CONNECTION_STRING` para todos esses consumidores. Disponibilizar `DJ_SESSION_SECRET_KEY` para o portal e qualquer consumidor de `app/config.py`. Os quatro serviços importam direta ou indiretamente constantes/acessos legados; todos precisam do TD.
3. Usar o mecanismo aprovado de configuração do ambiente, com acesso restrito às identidades necessárias. Variáveis de ambiente são uma forma de fornecer segredos aos processos, não um cofre criptografado. Não cadastrar valores reais no `web.config` versionado, no frontend, em variáveis `VITE_*` ou em arquivos sob a pasta publicada do site.
4. Confirmar como os processos passam a receber o ambiente novo. Reiniciar apenas os processos necessários em janela autorizada; pode ser necessário atuar no processo hospedeiro, além de parar/iniciar o site. Não presumir que um recycle do pool resolve todos os casos.

Não foram preparados comandos de alteração de IIS ou serviços porque suas identidades, compartilhamento do pool e forma de inicialização não foram confirmados. O cadastro e os reinícios são ações do responsável no ambiente autorizado, não executadas nesta entrega.

## 6. Pacote e ordem de publicação

Publicar juntos:

- `backend/platform/environment.py`;
- `backend/config.py`;
- `app/utils/constants.py`;
- `app/config.py`.

Os demais arquivos do backend e o build Vue completo já existentes devem continuar no pacote. Esta alteração não exige modificar `main.py`, rotas, tabela de Eventos, dependências, configuração do pool ou recursos do frontend.

Ordem para o responsável:

1. Guardar privadamente um pacote anterior para retorno, sem colocá-lo em pastas públicas ou no Git. Ele pode conter credenciais e precisa da mesma proteção da configuração externa.
2. Provisionar as variáveis com os valores atuais e preparar a recepção pelos processos antes da troca dos arquivos.
3. Publicar o conjunto acima na janela autorizada, incluindo o pacote `backend/` também onde os serviços utilizam uma cópia separada do projeto.
4. Iniciar/reiniciar os consumidores conforme o procedimento autorizado e verificar portal, sessão, uma tela legada, listagem de Eventos e operação dos quatro serviços. Verificações de escrita exigem escopo próprio e atingem o TD real.
5. Confirmar também os caminhos de erro por configuração ausente em ambiente isolado e autorizado. Não retirar variáveis da produção apenas para testar.

O erro por variável ausente ou vazia contém somente seu nome. Uma configuração preenchida, mas inválida, pode causar os erros de conexão já tratados pelo legado; esta entrega não revisa globalmente seus logs/tracebacks. Não compartilhar saídas que contenham segredos.

## 7. Riscos e retorno

O principal risco operacional é um consumidor não receber uma variável obrigatória. O portal pode não iniciar e um serviço pode parar ao importar as constantes. Outro risco é cadastrar um valor diferente, com alterações em opções ODBC ou caracteres da chave. Por isso o provisionamento precede a publicação, e cada consumidor precisa de confirmação em ambiente autorizado.

Em caso de falha, primeiro conferir privadamente o nome, valor e disponibilização da variável ao processo afetado. Se houver necessidade de retornar o código, restaurar **os quatro arquivos como conjunto compatível** do pacote anterior e reiniciar apenas os consumidores afetados na janela autorizada. Não restaurar só `app/config.py`, pois a assinatura de `BackendConfig.from_env()` também mudou. Não remover o pacote `backend/` nem outros arquivos modernos necessários à versão de retorno.

O pacote anterior pode reintroduzir valores no código; esse retorno é temporário e mantém a exposição já existente. Não registrar nem distribuir tais valores durante a operação. Rotação/revogação e limpeza de histórico permanecem fora desta entrega, conforme a decisão atual do responsável.

## 8. Validação realizada

Conferência textual do leitor, da configuração de ambas as arquiteturas, da assinatura de `from_env`, dos consumidores de `CNNX_JDT` e dos serviços; inspeção do diff, dos valores removidos de forma mascarada e das adições sem segredos; `git diff --check`. Não há fallback literal, novas consultas, migrations, testes, imports, instalações ou build nesta entrega.

**O sistema não foi executado; a validação foi somente estática.** O cadastro das variáveis, a recepção pelo IIS/serviços e o funcionamento dependem de confirmação em ambiente autorizado.
