# Estruturando requisitos de um projeto de software

## 🎯 Objetivo

Criar a estrutura funcional de uma API utilizando **Flask e Pydantic**, transformando os requisitos do sistema em rotas, modelos de dados e funcionalidades que recebem e validam informações.

Nesta etapa, vamos aprender a:

- Mapear os requisitos funcionais e transformá-los em rotas Flask.
- Utilizar métodos HTTP (GET, POST, PUT e DELETE) e parâmetros dinâmicos.
- Organizar e modelar os dados da aplicação utilizando Pydantic.
- Definir campos obrigatórios, opcionais e seus respectivos tipos.
- Integrar os modelos Pydantic às rotas Flask para validar requisições.
- Tratar exceções e retornar respostas com códigos de status HTTP.
- Implementar e testar um endpoint de login com autenticação simulada.

---

## 1. Mapeando os requisitos e gerando as rotas Flask

O objetivo é transformar os **requisitos funcionais (RF)** do sistema em rotas Flask, criando um planejamento diretamente no código antes de implementar as funcionalidades.

Um **requisito funcional** descreve uma ação que o sistema deve permitir realizar. Por exemplo:

- O usuário deve conseguir realizar login.
- O sistema deve permitir listar e cadastrar produtos.
- O sistema deve permitir atualizar e excluir produtos.

Cada funcionalidade pode ser representada por uma ou mais **rotas (endpoints)**, que definem como o cliente poderá interagir com a API.

### 1.1. Mapeando os requisitos

No arquivo `app/routes/main.py`, utilizamos comentários `# RF:` para descrever cada funcionalidade que será desenvolvida.

A partir desses requisitos, definimos os caminhos e métodos HTTP correspondentes.

#### Mapeamento das rotas

| Método | Rota | Funcionalidade |
| --- | --- | --- |
| POST | `/login` | Autenticar usuário e obter token |
| GET | `/products` | Listar todos os produtos |
| POST | `/products` | Criar um produto |
| GET | `/product/<int:product_id>` | Consultar um produto pelo ID |
| PUT | `/product/<int:product_id>` | Atualizar um produto |
| DELETE | `/product/<int:product_id>` | Excluir um produto |
| POST | `/sales/upload` | Importar arquivo de vendas |

Além dessas rotas, mantemos `GET /` como endpoint inicial da aplicação.

**Entendendo os métodos HTTP:**

- **GET:** consulta informações.
- **POST:** envia dados, geralmente para criar recursos ou executar operações.
- **PUT:** atualiza ou substitui um recurso existente.
- **DELETE:** remove um recurso.

> 💡 Uma mesma URL pode ter funcionalidades diferentes dependendo do método HTTP utilizado. Por exemplo, `GET /products` consulta produtos, enquanto `POST /products` cria um novo produto.
> 

### 1.2. Criando as rotas no Flask

As rotas continuam sendo definidas no Blueprint `main_bp`, utilizando o decorator `@main_bp.route()`.

#### Exemplo 1 — Listagem e criação de produtos

```
# RF: O sistema deve permitir a listagem de todos os produtos.
@main_bp.route('/products', methods=['GET'])
def get_products():
    return jsonify({"message": "Rota de listagem de produtos"})

# RF: O sistema deve permitir a criação de um novo produto.
@main_bp.route('/products', methods=['POST'])
def create_product():
    return jsonify({"message": "Rota de criação de produtos"})
```

**Como funciona?**

- `@main_bp.route('/products')`: define o endereço da rota.
- `methods=['GET']`: especifica quais métodos HTTP são aceitos.
- `def get_products()`: função executada quando a requisição corresponde à rota e ao método.
- `jsonify()`: gera uma resposta HTTP em formato JSON.

Observe que ambas utilizam `/products`, mas executam funções diferentes devido ao método HTTP.

#### Exemplo 2 — Rotas com parâmetros dinâmicos

Para consultar um produto específico, precisamos receber seu identificador pela URL.

```
# RF: O sistema deve permitir a visualização de um unico produto existente.
@main_bp.route('/product/<int:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    return jsonify({
        "message": f"Rota de visualização detalhada do produto {product_id}"
    })
```

**Entendendo as novidades:**

**`<int:product_id>`**

É um parâmetro dinâmico da rota:

- `int`: determina que o valor deve ser um número inteiro.
- `product_id`: nome do parâmetro que será passado para a função.

**`def get_product_by_id(product_id)`**

Recebe o ID capturado diretamente da URL.

**`f"...{product_id}"`**

É uma *f-string* do Python, utilizada para inserir o valor de uma variável dentro de um texto.

**Exemplo prático:**

Requisição:

```
GET /product/10
```

Resposta:

```
{
  "message": "Rota de visualização detalhada do produto 10"
}
```

O Flask captura automaticamente o valor `10` e o envia como argumento para `get_product_by_id()`.

Esse mesmo padrão é utilizado nas rotas de atualização (`PUT`) e exclusão (`DELETE`), que também precisam identificar qual produto será manipulado.

### 1.3. Implementando os demais endpoints

Seguindo o mesmo padrão, criamos as rotas de login, atualização, exclusão e importação de vendas.

Por exemplo, a rota de login:

```
# RF: O sistema deve permitir que um usuário se autentique para obter um token.
@main_bp.route('/login', methods=['POST'])
def login():
    return jsonify({"message": "Realizar o login"})
```

Nesse caso, o método `POST` foi escolhido porque o cliente futuramente enviará suas credenciais para autenticação.

O mesmo princípio se aplica ao upload de vendas, que utiliza `POST /sales/upload` para futuramente receber um arquivo.

**Importante:** nesta etapa, estamos apenas **mapeando as funcionalidades**, não implementando suas regras de negócio. As funções ainda retornam mensagens de exemplo, sem consultar bancos de dados, autenticar usuários ou manipular arquivos.

📸 **Print:** arquivo `app/routes/main.py` .

![image.png](Estruturando%20requisitos%20de%20um%20projeto%20de%20software/image.png)

### 1.4. Executando e testando as rotas

Para iniciar a aplicação:

```
python run.py
```

O servidor de desenvolvimento ficará disponível em:

`http://127.0.0.1:5000`

Podemos testar diretamente pelo navegador as rotas GET, como:

```
http://127.0.0.1:5000/products
http://127.0.0.1:5000/product/10
```

Para testar métodos como POST, PUT e DELETE, podemos utilizar ferramentas como **Postman** ou Insomnia.

Caso tentemos acessar `/login` pela barra de endereços do navegador, receberemos o erro **405 — Method Not Allowed**, pois o navegador utiliza GET e essa rota aceita POST.

### ✅ Resumo

Nesta etapa, transformamos os requisitos funcionais em endpoints Flask, definindo seus caminhos, métodos HTTP e funções responsáveis.

**Principais conceitos aprendidos:**

- **RF:** descreve o que o sistema deve fazer.
- **Endpoint:** ponto de acesso a uma funcionalidade da API.
- **Métodos HTTP:** determinam o tipo de operação realizada.
- **Parâmetros dinâmicos:** permitem receber informações diretamente da URL.
- **`jsonify()`:** permite retornar respostas em JSON.

Com isso, temos um **rascunho funcional da API**, que já define como cada operação será acessada, mesmo antes de implementar as funcionalidades reais.

---

## 2. Modelando os dados com Pydantic

O objetivo é definir a estrutura dos dados que nossa API irá receber e manipular, utilizando o **Pydantic** para validar automaticamente os tipos e campos obrigatórios.

Na etapa anterior, mapeamos **o que o sistema faz** através das rotas. Agora, vamos definir **quais dados essas funcionalidades utilizam**.

### 2.1. O que é Pydantic?

O **Pydantic** é uma biblioteca Python que permite criar modelos de dados utilizando classes e tipagem (*type hints*).

Esses modelos funcionam como um **contrato de dados**, definindo quais informações são esperadas, quais são obrigatórias e seus respectivos tipos.

Por exemplo, um produto pode precisar de nome, preço e quantidade em estoque. O Pydantic verifica essas informações quando criamos uma instância do modelo.

**Principais vantagens:**

- Validação automática de campos e tipos.
- Identificação de dados ausentes ou inválidos.
- Conversão de alguns valores para os tipos esperados.
- Organização e padronização dos objetos da aplicação.

#### Instalando o Pydantic

Com o ambiente virtual ativo, execute:

```
pip install pydantic
```

### 2.2. Atualizando a arquitetura do projeto

Para separar a definição dos dados das rotas, criamos uma pasta chamada `models/` dentro de `app/`.

#### 📁 Estrutura atualizada

```
flask_alura/
│
├── app/
│   ├── __init__.py
│   │
│   ├── models/           # Modelos de dados
│   │   ├── products.py   # Modelo Product
│   │   ├── sale.py       # Modelo Sale
│   │   └── user.py       # Modelo Login
│   │
│   └── routes/
│       └── main.py       # Rotas da API
│
└── run.py
```

| Arquivo | Responsabilidade |
| --- | --- |
| `models/products.py` | Define os dados de um produto. |
| `models/user.py` | Define os dados necessários para o login. |
| `models/sale.py` | Define os dados de uma venda. |
| `routes/main.py` | Continua responsável pelos endpoints da API. |

Dessa forma, as **rotas** definem como acessar uma funcionalidade, enquanto os **models** definem a estrutura dos dados utilizados por ela.

📸 **Print:** estrutura de pastas do projeto no VS Code.

![image.png](Estruturando%20requisitos%20de%20um%20projeto%20de%20software/image%201.png)

### 2.3. Criando o modelo de produtos

No arquivo `app/models/products.py`:

```
from pydantic import BaseModel
from typing import Optional

class Product(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    stock: int
```

#### Entendendo o código

**`from pydantic import BaseModel`**

Importa a classe principal do Pydantic. Ao herdar de `BaseModel`, nossa classe passa a ter recursos de validação e conversão de dados.

**`class Product(BaseModel):`**

Cria um modelo chamado `Product`, que representa a estrutura esperada de um produto.

**Tipos dos atributos:**

| Campo | Tipo | Obrigatório? |
| --- | --- | --- |
| `name` | `str` | Sim |
| `price` | `float` | Sim |
| `description` | `Optional[str]` | Não |
| `stock` | `int` | Sim |

#### O que significa `Optional[str] = None`?

```
description: Optional[str] = None
```

- `Optional[str]`: permite que o valor seja uma string ou `None`.
- `= None`: define um valor padrão, permitindo omitir o campo ao criar o objeto.

Assim, podemos criar um produto sem descrição, mas não sem nome, preço ou estoque.

**Importante:** no Pydantic, um campo se torna opcional para preenchimento quando possui um valor padrão. Apenas utilizar `Optional[str]`, sem `= None`, não o torna automaticamente dispensável.

📸 **Print:** arquivo `app/models/products.py`.

![image.png](Estruturando%20requisitos%20de%20um%20projeto%20de%20software/image%202.png)

### 2.4. Criando o modelo de login

No arquivo `app/models/user.py`:

```
from pydantic import BaseModel

class LoginPayload(BaseModel):
    username: str
    password: str
```

Esse modelo define os dados necessários para uma tentativa de autenticação.

- `username`: identificação do usuário.
- `password`: senha informada pelo usuário.

Ambos são obrigatórios e esperam valores do tipo `str`.

**Por que criar um modelo específico para login?**

Porque os dados necessários para realizar login não são necessariamente os mesmos utilizados para representar um usuário completo.

Futuramente, poderemos criar outro modelo para armazenar informações do usuário, como nome, e-mail e permissões.

> O modelo `LoginPayload` apenas define e valida a estrutura dos dados. A verificação da senha e a autenticação serão implementadas separadamente.
> 

📸 **Print:** arquivo `app/models/user.py`.

![image.png](Estruturando%20requisitos%20de%20um%20projeto%20de%20software/image%203.png)

### 2.5. Criando o modelo de vendas

No arquivo `app/models/sale.py`:

```
from pydantic import BaseModel
from datetime import date

class Sale(BaseModel):
    sale_date: date
    product_id: str
    quantity: int
    total_value: float
```

Aqui utilizamos os tipos comuns do Python e também o tipo `date`, importado do módulo `datetime`.

| Campo | Tipo | Finalidade |
| --- | --- | --- |
| `sale_date` | `date` | Data da venda |
| `product_id` | `str` | Identificador do produto |
| `quantity` | `int` | Quantidade vendida |
| `total_value` | `float` | Valor total da venda |

**Exemplo de um objeto de venda:**

```
{
  "sale_date": "2026-10-21",
  "product_id": "P001",
  "quantity": 2,
  "total_value": 199.90
}
```

O Pydantic consegue interpretar uma data no formato `AAAA-MM-DD` e convertê-la para um objeto `date` do Python.

📸 **Print:** arquivo `app/models/sale.py`.

![image.png](Estruturando%20requisitos%20de%20um%20projeto%20de%20software/image%204.png)

### 2.6. Como os modelos se relacionam com as rotas?

Agora temos duas partes importantes da nossa API:

- **Routes:** definem quais operações podem ser executadas.
- **Models:** definem quais dados são esperados nessas operações.

O fluxo que construiremos será semelhante a:

```
Cliente envia JSON
        |
        v
  Rota Flask
        |
        v
 Modelo Pydantic
        |
        | Valida os dados
        v
 Lógica da aplicação
        |
        v
 Resposta HTTP
```

**Atenção:** no Flask, o Pydantic não valida automaticamente todas as requisições. Precisamos integrar os modelos às rotas para que os dados recebidos sejam efetivamente validados.

Essa integração será realizada nas próximas etapas do projeto.

### ✅ Resumo

Nesta etapa, criamos os primeiros **modelos de dados** da aplicação utilizando Pydantic, separando sua definição das rotas Flask.

| Conceito | Para que serve |
| --- | --- |
| `BaseModel` | Classe base que fornece os recursos de validação. |
| `str`, `int`, `float` | Definem os tipos esperados dos campos. |
| `Optional` | Permite que um campo aceite `None`. |
| `= None` | Define `None` como valor padrão. |
| `date` | Representa uma data sem horário. |
| `ValidationError` | Erro gerado quando os dados não passam na validação. |
| `model_dump()` | Converte um modelo Pydantic em dicionário. |

**O que aprendemos:** enquanto as rotas representam as ações da nossa API, os modelos representam a estrutura dos dados que essas ações utilizarão.

Com isso, temos os requisitos funcionais e os requisitos de dados definidos, preparando a aplicação para implementar suas funcionalidades reais.

---

## 3. Realizando o login na prática

O objetivo  é integrar uma **rota Flask** com um **modelo Pydantic**, permitindo receber, validar e processar dados enviados pelo cliente.

Nesta etapa, implementaremos um login simulado, utilizando credenciais fixas para entender o fluxo completo de uma requisição HTTP.

### 3.1. Integrando Flask e Pydantic

Até agora, criamos as rotas e os modelos separadamente. Vamos conectá-los para que os dados recebidos pela API sejam validados antes de serem utilizados.

No arquivo `app/models/user.py`, temos o modelo:

```
from pydantic import BaseModel

class LoginPayload(BaseModel):
    username: str
    password: str
```

Ele define que uma requisição de login deve conter os campos `username` e `password`, ambos do tipo `str`.

Agora, no arquivo `app/routes/main.py`, adicionamos as importações:

```
from flask import Blueprint, jsonify, request
from app.models.user import LoginPayload
from pydantic import ValidationError
```

**Entendendo as importações:**

- `request`: permite acessar os dados enviados pelo cliente na requisição HTTP.
- `LoginPayload`: modelo Pydantic responsável por validar os dados do login.
- `ValidationError`: exceção gerada quando os dados não atendem às regras do modelo.

### 3.2. Recebendo e validando os dados

Na rota `/login`, utilizamos `request.get_json()` para capturar o corpo JSON enviado pelo cliente.

```
raw_data = request.get_json()
user_data = LoginPayload(**raw_data)
```

**Como funciona?**

**`request.get_json()`**

Lê o corpo da requisição e converte o JSON recebido em um objeto Python, normalmente um dicionário.

Exemplo de JSON enviado:

```
{
  "username": "admin",
  "password": "123"
}
```

**`LoginPayload(**raw_data)`**

Cria uma instância do modelo Pydantic e valida os campos recebidos.

O operador `**` desempacota as chaves do dicionário em argumentos nomeados.

É equivalente a escrever:

```
user_data = LoginPayload(
    username="admin",
    password="123"
)
```

Se algum campo obrigatório estiver ausente ou tiver um valor inválido, o Pydantic gera um `ValidationError`.

Após a validação, podemos acessar os dados diretamente:

```
user_data.username
user_data.password
```

### 3.3. Tratando erros com try e except

Para impedir que erros não tratados interrompam o processamento da requisição, utilizamos `try` e `except`.

```
try:
    raw_data = request.get_json()
    user_data = LoginPayload(**raw_data)

except ValidationError as e:
    return jsonify({"error": e.errors()}), 400

except Exception as e:
    return jsonify({
        "error": "Erro durante a requisição do dado"
    }), 500
```

#### Entendendo cada parte

- **`try`:** executa o código que pode gerar uma exceção.
- **`except ValidationError as e`:** captura erros de validação gerados pelo Pydantic.
- **`e.errors()`:** retorna detalhes dos problemas encontrados nos campos.
- **`except Exception as e`:** captura outras exceções que não foram tratadas anteriormente.

Também utilizamos códigos de status HTTP para informar o resultado da operação.

| Status | Significado |
| --- | --- |
| `200 OK` | Requisição processada com sucesso. |
| `400 Bad Request` | Dados da requisição inválidos. |
| `500 Internal Server Error` | Erro interno durante o processamento. |

**Exemplo:**

```
return jsonify({"error": e.errors()}), 400
```

O `jsonify()` cria a resposta JSON, enquanto o `400`, colocado após a vírgula, define o status HTTP retornado pelo Flask.

> 💡 No código atual, uma requisição com JSON malformado ou sem o tipo de conteúdo esperado pode acabar recebendo status 500, devido ao tratamento genérico. Posteriormente, podemos melhorar esse comportamento para retornar erros 400 ou 415 conforme o caso.
> 

### 3.4. Simulando a autenticação

Com os dados validados, podemos verificar se as credenciais correspondem às esperadas.

```
if user_data.username == 'admin' and user_data.password == '123':
    return jsonify({"message": "Login bem-sucedido!"})
else:
    return jsonify({"message": "Credenciais invalidas!"})
```

**Como funciona?**

- `user_data.username`: acessa o nome de usuário validado.
- `user_data.password`: acessa a senha validada.
- `and`: exige que as duas condições sejam verdadeiras.
- `if / else`: determina qual resposta será enviada.

Se o usuário informar `admin` e a senha `123`, receberá a mensagem de sucesso. Qualquer outra combinação retornará credenciais inválidas.

**Importante:** essa autenticação é apenas uma simulação. Em uma aplicação real, as senhas devem ser verificadas de forma segura, normalmente utilizando hashes, e não comparadas com valores fixos no código.

### 3.5. Código completo do endpoint

O resultado no arquivo `app/routes/main.py`:

```
# RF: O sistema deve permitir que um usuário se autentique para obter um token.
@main_bp.route('/login', methods=['POST'])
def login():
    try:
        raw_data = request.get_json()
        user_data = LoginPayload(**raw_data)

    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    except Exception as e:
        return jsonify({
            "error": "Erro durante a requisição do dado"
        }), 500

    if user_data.username == 'admin' and user_data.password == '123':
        return jsonify({"message": "Login bem-sucedido!"})
    else:
        return jsonify({"message": "Credenciais invalidas!"})
```

📸 **Print:** função `login()`.

![image.png](Estruturando%20requisitos%20de%20um%20projeto%20de%20software/image%205.png)

Observe que separamos o endpoint em três responsabilidades:

1. **Receber:** capturar os dados da requisição.
2. **Validar:** verificar se os dados atendem ao modelo Pydantic.
3. **Processar:** verificar as credenciais e retornar uma resposta.

### 3.6. Testando o endpoint

Inicie o servidor:

```
python run.py
```

Como a rota utiliza o método POST, podemos realizar os testes utilizando Postman, Insomnia ou outra ferramenta de requisições HTTP.

<escape>**Endpoint:** `POST http://127.0.0.1:5000/login`</escape>

#### Teste 1 — Credenciais corretas

**Body (JSON):**

```
{
  "username": "admin",
  "password": "123"
}
```

**Resposta:**

```
{
  "message": "Login bem-sucedido!"
}
```

Status HTTP: `200 OK`.

#### Teste 2 — Credenciais incorretas

**Body (JSON):**

```
{
  "username": "admin",
  "password": "456"
}
```

**Resposta:**

```
{
  "message": "Credenciais invalidas!"
}
```

No código atual, essa resposta também utiliza HTTP 200 por padrão. Em uma autenticação real, o mais adequado seria retornar **401 Unauthorized**, indicando credenciais inválidas.

#### Teste 3 — Dados incompletos

**Body (JSON):**

```
{
  "username": "admin"
}
```

Como o campo `password` é obrigatório, o Pydantic gera um `ValidationError` e o endpoint retorna status `400 Bad Request`, acompanhado dos detalhes do erro.

### 3.7. Entendendo o fluxo completo

Agora podemos visualizar como o Flask e o Pydantic trabalham juntos:

```
Cliente envia POST /login
           |
           v
     Rota Flask
           |
           v
   request.get_json()
           |
           v
  LoginPayload (Pydantic)
           |
           v
     Dados válidos?
       /       \
     Não       Sim
      |         |
      v         v
   Erro 400  Verifica credenciais
                |
                v
           Retorna JSON
```

O Flask recebe a requisição, enquanto o Pydantic verifica se os dados possuem a estrutura esperada.

Após essa validação, nossa lógica pode utilizar os dados com maior segurança quanto aos tipos e campos obrigatórios.

### ✅ Resumo

Neste tópico, construímos nosso primeiro endpoint que recebe e valida dados utilizando Flask e Pydantic.

| Conceito | Para que serve |
| --- | --- |
| `request` | Permite acessar informações da requisição HTTP. |
| `get_json()` | Lê e interpreta o JSON enviado pelo cliente. |
| `**raw_data` | Desempacota um dicionário em argumentos nomeados. |
| `LoginPayload()` | Cria e valida os dados do login. |
| `ValidationError` | Identifica erros de validação do Pydantic. |
| `try / except` | Permite capturar e tratar exceções. |
| `jsonify(), status` | Retorna JSON acompanhado de um código HTTP. |

**O que aprendemos:** unimos os requisitos funcionais (rotas) aos requisitos de dados (modelos Pydantic), criando uma funcionalidade que recebe informações, valida seus campos e retorna respostas apropriadas.