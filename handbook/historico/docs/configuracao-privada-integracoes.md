> **Registro histórico.** Pode conter decisões, caminhos e comandos superados. Consulte o [manual atual](../../README.md); este arquivo não define o padrão vigente.

# Configuração privada das integrações — entrega S1b

Data: **14/10/2026**. Base da alteração: `21c4c81`, após a entrega S1 de TD/sessão.

## 1. Resultado e limites

O responsável autorizou preparar um `.env` privado com as credenciais existentes e fazer a aplicação carregá-lo. Os valores atuais foram preservados por transformação textual, sem executar/importar Python, iniciar o sistema ou testar sua validade. O arquivo privado foi criado somente nesta cópia de trabalho, com 19 variáveis; ele não integra o commit nem é enviado por Git.

O `.env.example` contém somente os nomes e valores vazios. Credenciais de TD/sessão, FTM, Plex, Plex de teste, Trace QR, MES, LDAP, Microsoft, SAP e Oracle foram retiradas dos arquivos Python identificados pelo inventário. O banco TD, contas, permissões, opções das conexões e fluxos de integração continuam sendo os atuais.

**Organização dos arquivos privados e do modelo:** o grupo A contém TD, sessão e o par LDAP, compartilhados pelas duas arquiteturas. O grupo B contém as demais integrações implementadas no legado. LDAP fornece identidade no legado e nome/setor nas presenças pelo cliente moderno; Microsoft participa dos erros globais e ainda pode afetar o Vue indiretamente. O grupo C identifica Plex de teste sem consumidor ativo encontrado e Oracle de horas produtivas desativadas. Os grupos são comentários: não ativam, desativam nem criam conexões.

Essa entrega não faz rotação/revogação, não limpa histórico/clones/cópias, não altera backups históricos e não certifica ausência de outros segredos. Os mesmos valores nas versões antigas continuam expostos. Os demais achados de segurança, efeitos de imports, threads, inicialização e autorização permanecem fora do escopo.

## 2. Como a leitura funciona

`backend/platform/environment.py` continua sendo um leitor compartilhado pela ponte legada e pelo backend moderno. Importar somente esse módulo não lê o arquivo nem inicia threads/conexões. A primeira chamada a `required_env()` carrega a configuração, que permanece durante a vida do processo:

1. Se `DJ_ENV_FILE` estiver definido no ambiente do processo, usar esse arquivo; o caminho deve ser absoluto e o arquivo deve existir. Essa variável é um seletor de arquivo, não uma credencial.
2. Caso contrário, procurar somente `.env` na raiz do projeto, calculada pela localização do módulo. Não pesquisar diretórios superiores nem depender de `os.getcwd()`.
3. Se o `.env` padrão não existir, usar apenas o ambiente do processo. Não importar `python-dotenv` nesse caso. Um `DJ_ENV_FILE` explicitamente configurado, mas inválido, gera erro.
4. Havendo arquivo, usar `python-dotenv==1.2.4`, com `override=False`, `interpolate=False` e `encoding="utf-8-sig"`. As variáveis já presentes no Windows têm prioridade, inclusive quando vazias; senhas com `${...}` não são expandidas por esse leitor. As opções são do [contrato de python-dotenv](https://bbc2.github.io/python-dotenv/reference/).
5. Exigir valor não vazio para cada configuração solicitada. O erro informa apenas seu nome; nenhum valor é impresso. Os caracteres originais são preservados. Alterações no arquivo exigem reiniciar o consumidor em janela autorizada.

Um arquivo inacessível, de tipo incorreto ou com codificação inválida interrompe a leitura. Erros de formato podem ser sinalizados pelo parser e resultar em variáveis ausentes. Não há senha ou chave literal de reserva.

### Atenção ao Flask CLI

Com `python-dotenv` instalado, o Flask CLI pode carregar `.env` antes de importar a aplicação, usando sua própria política de busca/interpolação. Para usar este leitor de maneira consistente, configurar **`FLASK_SKIP_DOTENV=1` no ambiente do processo antes de iniciar o Flask CLI**, inclusive no IIS que utiliza `-m flask run`. Colocar essa opção dentro do próprio `.env` não garante impedir o carregamento antecipado. Essa orientação vem da [documentação do Flask CLI](https://flask.palletsprojects.com/en/stable/cli/#disable-dotenv).

O fluxo habitual local via `main.py` e os serviços também alcançam o leitor por suas configurações legadas. Isso descreve os caminhos do código, não autoriza executar o projeto pelo agente.

O `web.config` versionado recebeu somente a opção pública `FLASK_SKIP_DOTENV=1`. Na publicação manual, aplicar essa entrada à configuração efetiva do servidor, preservando os outros valores; não substituir indiscriminadamente o arquivo do IIS.

## 3. Nomes e consumidores

| Configuração | Variáveis | Onde os valores são utilizados |
| --- | --- | --- |
| TD e sessão | `DJ_TD_ODBC_CONNECTION_STRING`, `DJ_SESSION_SECRET_KEY` | `backend/config.py`, `app/utils/constants.py` e `app/config.py`; sessão Flask e conexões modernas/legadas. |
| Outros bancos | `DJ_FTM_ODBC_CONNECTION_STRING`, `DJ_PLEX_ODBC_CONNECTION_STRING`, `DJ_PLEX_TEST_ODBC_CONNECTION_STRING`, `DJ_TRACE_QR_ODBC_CONNECTION_STRING` | Constantes `CNNX_FTM`, `CNNX_PLEX`, `CNNX_PLEX_TEST` e `CNNX_TRACE_QR`, mantendo seus consumidores. |
| MES | `DJ_MES_USER`, `DJ_MES_PASSWORD` | Constantes `MES_MAIN_USER`/`MES_MAIN_PASSWORD`; integração de alteração de paradas. |
| LDAP | `DJ_LDAP_USER`, `DJ_LDAP_PASSWORD` | Login, criação de usuários externos, H24 e função temporária desativada no legado; consulta moderna de nome/setor em presenças. Os clientes continuam independentes e reutilizam somente o par privado. |
| Microsoft | `DJ_MICROSOFT_TENANT_ID`, `DJ_MICROSOFT_CLIENT_ID`, `DJ_MICROSOFT_CLIENT_SECRET`, `DJ_MICROSOFT_USERNAME`, `DJ_MICROSOFT_PASSWORD` | Gerenciador de tokens já utilizado por Teams e usuários. |
| SAP | `DJ_SAP_USER`, `DJ_SAP_PASSWORD` | Conexão dos relatórios de manutenção. |
| Oracle | `DJ_ORACLE_USER`, `DJ_ORACLE_PASSWORD` | Função de horas produtivas, cujo blueprint continua desativado e sem novo registro. |

As constantes legadas continuam sendo resolvidas durante seu import. Por isso todos os consumidores delas precisam dos cinco destinos de banco e do par MES, mesmo que uma rotina use somente parte desses valores. O gerenciador Microsoft também mantém sua inicialização existente; consumidores de Teams precisam das cinco variáveis Microsoft. LDAP, SAP e Oracle legados mantêm seus pontos de utilização. A configuração LDAP moderna é lida por `BackendConfig.from_env()` sem abrir conexão; a consulta ocorre somente durante o preenchimento de uma presença incompleta. Opções de host/base/porta/SSL e timeouts modernos estão no `.env.example` e no handbook; não alteram a configuração dos clientes antigos.

Os quatro serviços S30, M5, H24 e Auto usam constantes/acessos legados e Teams. Todos precisam da configuração correspondente de bancos/MES/Microsoft; H24 também utiliza LDAP. A chave de sessão é necessária ao portal e aos consumidores que importam `app/config.py`. O arquivo completo preparado facilita o provisionamento nesta fase, sem alterar os contratos antigos. Privilégios distintos por processo permanecem uma melhoria futura.

## 4. Uso no computador da empresa

1. Atualizar o conjunto de código/documentação desta entrega.
2. Transferir privadamente o `.env` preparado nesta cópia de trabalho para a raiz do projeto local, junto de `main.py`. **Um pull não traz esse arquivo.** Não substituir um `.env` local já existente sem conferir seus valores privadamente. O `.env.example` está vazio e não substitui o arquivo preenchido.
3. Disponibilizar `python-dotenv==1.2.4` na `.venv` utilizada. A dependência foi declarada em `requirements.txt`, preservando UTF-16 e as demais versões; nada foi instalado pelo agente. A versão utilizada está no [registro do pacote](https://pypi.org/project/python-dotenv/1.2.4/).
4. Conferir se variáveis Windows antigas precisam permanecer: elas têm prioridade sobre o arquivo. Não imprimir os valores como diagnóstico.
5. Usar o processo de verificação do responsável somente com autorização de ambiente/comando/escopo. Não é necessário novo build Vue para esta mudança; o build existente continua necessário para a interface.

O arquivo privado foi criado com permissões `0600` nesta cópia Linux. Ao transferir para Windows, aplicar ACL restrita ao responsável/processo; a permissão Unix não configura a ACL de destino. Não enviar o arquivo por chat, pasta pública ou junto do pacote comum de publicação.

## 5. Servidor e serviços Windows

Escolher uma das fontes, preservando os valores atuais:

- Variáveis do ambiente dos processos, sem arquivo `.env` no site; ou
- arquivo privado **fora de `I:\IIS\Digital_Jost` e de qualquer diretório público**, acessível somente às identidades necessárias. Definir `DJ_ENV_FILE` com seu caminho absoluto no ambiente do IIS e de cada serviço consumidor.

`DJ_ENV_FILE` deve ser definido externamente, antes da inicialização; colocá-lo dentro de `.env` não seleciona outro arquivo. No IIS/Flask CLI, definir também `FLASK_SKIP_DOTENV=1` conforme a seção 2. Não gravar segredos no `web.config` versionado ou no frontend. A forma efetiva de cadastro, identidades e eventual compartilhamento de pool ainda exige conferência com o responsável/TI.

Preparar a fonte, ACLs, dependência quando houver arquivo e recepção pelo processo antes da troca do código. Os dois arquivos de comandos offline usados pelo projeto passam a incluir `python-dotenv==1.2.4`: [download no PC](baixar-dependencias-eventos-pc.txt) e [instalação offline no servidor](instalar-dependencias-eventos-servidor.txt). São instruções para o procedimento autorizado; nenhum deles foi executado. Eles não substituem a preparação das `.venv` dos serviços, se forem distintas da do site.

### Arquivos Python que precisam acompanhar a publicação

- `backend/platform/environment.py`;
- `app/utils/constants.py`;
- `app/utils/azure_utils.py`;
- `app/utils/security_utils.py`;
- `app/routes/auth_routes.py`;
- `app/routes/reports/maintenance.py`;
- `app/services/jobs/mon_mon_h_24_userCheck.py`;
- `app/routes/jdt/temp.py` e `app/routes/reports/productiveHours.py`, sem ativar seus blueprints.

Manter o pacote moderno, `app/config.py` e demais arquivos compatíveis da S1. Incluir também `requirements.txt` e a preparação da dependência; copiar esse arquivo não instala pacotes. Se os serviços utilizarem cópias separadas do projeto, atualizar o conjunto e fornecer o pacote `backend/` nelas. O `.env` privado não acompanha o Git nem o pacote público.

No `web.config` efetivo, incluir dentro de `<httpPlatform><environmentVariables>` somente este controle público, sem credenciais:

```xml
<environmentVariable name="FLASK_SKIP_DOTENV" value="1" />
```

## 6. Risco, retorno e verificação pendente

Os riscos operacionais são falta de variável, pacote ausente quando houver arquivo, caminho/ACL inadequados, precedência de valores Windows e configuração diferente por consumidor. Eles podem impedir o início do portal/serviço ou falhar somente ao usar LDAP/SAP/Oracle. A mudança não troca banco, conta ou senha, mas precisa de confirmação em cada ambiente autorizado.

Guardar privadamente o pacote anterior compatível. Caso seja necessário retornar, restaurar os nove arquivos Python acima como conjunto e manter a configuração válida; o leitor anterior não lê arquivos, portanto um retorno a S1 exige suas variáveis no ambiente. O código anterior das outras integrações pode reintroduzir segredos literais; não distribuir nem versionar o pacote de retorno. Não remover o `.env` ou outros arquivos operacionais por iniciativa do agente.

Conferir portal, sessão, Eventos, uma tela legada, login/usuários, manutenção e quatro serviços em janela autorizada. Validação de escrita ou notificações exige escopo específico. Não ativar horas produtivas ou módulo temporário para testar credenciais. Não retirar configurações da produção para simular falhas.

## 7. Validação estática realizada

Inspeção de imports e diff, busca dos consumidores e dos nomes de credenciais, comparação textual dos quatro pares LDAP, dos nomes do arquivo privado/modelo e da inclusão única da dependência em UTF-16; conferência de prioridade, caminhos, ausência de interpolação e erros sem valores; `git diff --check`. O `.env` permaneceu ignorado e não foi adicionado ao índice. Não foram criados testes dinâmicos.

**O sistema não foi executado; a validação foi somente estática.** O carregamento efetivo pela biblioteca, as credenciais, o IIS, as ACLs e os serviços não foram testados. Não houve instalação, conexão, alteração de dados, envio de mensagens, publicação, rotação ou revogação.

## 8. Arquivos versionados desta entrega

O arquivo privado `.env` não está nesta lista nem no commit.

| Grupo | Arquivos |
| --- | --- |
| Leitor e consumidores | `backend/platform/environment.py`, `app/utils/constants.py`, `app/utils/azure_utils.py`, `app/utils/security_utils.py`, `app/routes/auth_routes.py`, `app/routes/jdt/temp.py`, `app/routes/reports/maintenance.py`, `app/routes/reports/productiveHours.py`, `app/services/jobs/mon_mon_h_24_userCheck.py`. |
| Configuração pública/dependências | `.env.example`, `requirements.txt`, `web.config`. |
| Documentação | `README.md`, `docs/configuracao-privada-integracoes.md`, `docs/configuracao-externa-td-sessao.md`, `docs/plano-separacao-backend-legado.md`, `docs/ambientes-desenvolvimento-servidor.md`, `docs/revisao-seguranca-modernizacao.md`, `docs/baixar-dependencias-eventos-pc.txt`, `docs/instalar-dependencias-eventos-servidor.txt`. |

## 9. Revisão posterior: comentários e comparação com o Git

Revisão solicitada após `c21e21d`, sem execução do sistema. Foram reorganizados somente os comentários/grupos de `.env` e `.env.example`; as 19 linhas de configuração do arquivo privado foram preservadas, incluindo seus escapes. O arquivo preenchido continua fora do Git.

### Evidências verificadas como texto

- Os **19 valores** do arquivo privado, considerando aspas/escapes do formato, coincidem com os valores originais. TD e sessão foram comparados com `4c7befd`; as demais categorias, com `21c4c81`. Nenhum valor foi exibido ou testado em serviço externo.
- Os **oito consumidores Python** alterados na S1b coincidem integralmente com `21c4c81` quando se desconsideram apenas o import do leitor e as substituições dos literais por `required_env(...)`. Não houve mudança adicional em consultas, condições, chamadas, transações ou restante desses arquivos.
- `main.py`, bootstrap, plataforma de banco, módulos de Eventos, `db_utils.py` e os quatro schedulers não mudaram entre `21c4c81` e `c21e21d`. Os contratos de composição de TD/sessão foram revisados separadamente entre `4c7befd` e `c21e21d`.
- `requirements.txt`, em UTF-16, preserva exatamente os bytes anteriores ao acréscimo da linha de `python-dotenv==1.2.4`. Os comandos offline usam a mesma versão.
- O modelo tem 19 nomes e nenhum valor; a ordem dos nomes coincide com o arquivo privado. Este permanece ignorado/não rastreado, com permissões `0600` nesta cópia Linux.
- A gramática de aspas simples/escapes foi conferida no [parser da versão 1.2.4](https://github.com/theskumar/python-dotenv/blob/v1.2.4/src/dotenv/parser.py); a prioridade e os argumentos usados pelo leitor, no [código da biblioteca](https://github.com/theskumar/python-dotenv/blob/v1.2.4/src/dotenv/main.py). Foram lidos como texto, não executados.

**Resultado:** não foram encontradas diferenças indevidas nos valores nem nos consumidores examinados. A comparação estática não comprova conexão, autenticação ou execução correta no PC/IIS/serviços. Não foi necessária correção no código Python nesta revisão.

### O papel de `environment.py`

Esse arquivo é o leitor de configuração compartilhado. Ele fornece valores para as configurações do legado e do backend moderno; não abre uma conexão de banco nem escolhe uma funcionalidade para ativar. Cada engine e integração continua sendo criado pelo seu código responsável.

`load_environment()` prepara a fonte uma vez por processo: arquivo absoluto indicado por `DJ_ENV_FILE`, ou `.env` da raiz, ou somente ambiente quando não há arquivo padrão. Isso permite usar o arquivo no PC e manter uma configuração privada fora do site no servidor. A raiz é calculada pelo módulo para que o diretório de trabalho de um serviço não selecione o arquivo errado.

`override=False` preserva valores fornecidos pelo Windows/IIS; `interpolate=False` protege senhas contendo expressões como `${...}`; `utf-8-sig` aceita o arquivo UTF-8 com ou sem BOM. `required_env()` exige a configuração solicitada e informa apenas seu nome se estiver ausente/vazia. Reiniciar o processo é necessário para trocar configurações já carregadas.

`FLASK_SKIP_DOTENV=1` controla a leitura antecipada feita pelo Flask CLI. Ele **não desliga o nosso leitor** nem qualquer feature. A biblioteca possui outro controle, `PYTHON_DOTENV_DISABLED`: quando definido como verdadeiro no ambiente, `load_dotenv()` não carrega arquivos; nesse caso os valores necessários devem estar no ambiente ou o responsável deve ajustar esse controle. O estado efetivo desses controles no servidor não foi inspecionado.

### Condições para a confirmação funcional

Antes da publicação, conferir arquivo/variáveis efetivos de cada processo, dependência na `.venv` quando houver arquivo, caminhos e ACLs, `FLASK_SKIP_DOTENV` para o CLI e prioridade das variáveis Windows. Os cinco destinos de banco e MES continuam obrigatórios ao importar as constantes legadas; Microsoft é exigido pelo gerenciador de tokens atual. Não excluir grupos B/C em bloco por uma tela nova usar apenas TD: Plex de teste ainda é resolvido no import, enquanto Oracle só é exigido pela função do módulo desativado quando utilizada.

**O sistema não foi executado; a validação foi somente estática.** Não foram verificadas credenciais, instalações ou respostas reais. A confirmação funcional continua condicionada ao ambiente e escopo autorizados.
