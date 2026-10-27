# Implemente a logica de negocios e a persistencia de dados

## 🎯 Objetivo

---

## 1. Buscando dados reais no MongoDB

O objetivo deste tópico é conectar a aplicação Flask ao **MongoDB**, permitindo que nossas rotas de consulta retornem produtos armazenados em um banco de dados real.

Até agora, nossas rotas retornavam mensagens fixas. Vamos substituir essas simulações por consultas ao banco, começando pela listagem de todos os produtos e pela busca de um produto específico.

### 1.1. Conhecendo o MongoDB

O **MongoDB** é um banco de dados NoSQL orientado a documentos. Diferentemente de bancos relacionais, que organizam os dados em tabelas e linhas, o MongoDB utiliza **coleções e documentos**.

Os documentos possuem uma estrutura semelhante ao JSON e são armazenados internamente no formato BSON (*Binary JSON*).

| Banco relacional | MongoDB |
| --- | --- |
| Banco de dados | Banco de dados |
| Tabela | Collection (coleção) |
| Linha ou registro | Document (documento) |
| Coluna | Campo |
| Chave primária | Campo `_id` |

A principal vantagem dessa abordagem é a flexibilidade para trabalhar com documentos, embora a escolha entre SQL e NoSQL dependa dos requisitos da aplicação.

### 1.2. Instalando e configurando o MongoDB

Para executar o banco localmente, utilizaremos duas ferramentas:

- **MongoDB Community Server:** servidor responsável por armazenar e disponibilizar os dados.
- **MongoDB Compass:** interface gráfica para visualizar bancos, coleções e documentos.

Downloads oficiais:

- [MongoDB Community Server](https://www.mongodb.com/try/download/community)
- [MongoDB Compass](https://www.mongodb.com/try/download/compass)

No Windows, podemos instalar o Community Server pelo instalador `.msi`, selecionando a instalação completa. Também podemos instalar o Compass durante esse processo.

Após a instalação, abrimos o Compass e criamos uma conexão local. O endereço padrão do MongoDB é:

```
mongodb://localhost:27017
```

**Entendendo o endereço:**

- `mongodb://`: protocolo utilizado na conexão.
- `localhost`: indica que o banco está executando no próprio computador.
- `27017`: porta padrão do MongoDB.

Se o servidor exigir autenticação, também será necessário informar as credenciais de acesso.

#### Criando nosso primeiro banco e coleção

No Compass, criamos um banco para armazenar os produtos da aplicação.

Para acompanhar o código utilizado no repositório, usaremos:

- **Database:** `meu_banco`
- **Collection:** `products`

Dentro da coleção, podemos utilizar a opção **Insert Document** para cadastrar um produto de exemplo:

```
{
  "name": "Placa de Vídeo RTX 9090",
  "price": 15999.90,
  "description": "Placa de vídeo para jogos",
  "stock": 50
}
```

O MongoDB também cria automaticamente um identificador `_id` para o documento, caso não seja informado.

> 💡 Os nomes do banco e da coleção precisam corresponder à configuração da aplicação. No código desta etapa, utilizamos o banco `meu_banco` e a coleção `products`.
> 

### 1.3. Atualizando a arquitetura do projeto

Para conectar nossa aplicação ao banco de dados, adicionamos dois arquivos à raiz do projeto: `.env` e `config.py`.

#### 📁 Estrutura atualizada

```
flask_alura/
│
├── app/
│   ├── __init__.py       # Factory e conexão MongoDB
│   │
│   ├── models/
│   │   ├── products.py
│   │   ├── sale.py
│   │   └── user.py
│   │
│   └── routes/
│       └── main.py       # Rotas que consultam o banco
│
├── .env                  # Variáveis de ambiente
├── config.py             # Configurações da aplicação
└── run.py                # Inicialização do servidor
```

**Responsabilidade dos arquivos envolvidos:**

| Arquivo | Responsabilidade |
| --- | --- |
| `.env` | Armazena configurações locais, incluindo a URI de conexão. |
| `config.py` | Carrega as variáveis de ambiente e centraliza configurações. |
| `app/__init__.py` | Inicializa o Flask e prepara o acesso ao MongoDB. |
| `app/routes/main.py` | Executa as consultas e retorna os resultados pela API. |

A pasta `models/` permanece com os modelos Pydantic criados anteriormente.

**Importante:** o `.env` deve existir localmente, mas não deve ser versionado quando contém informações sensíveis. No repositório dessa aula ele foi incluído por engano, e precisa ser retirado do controle de versão.

📸 **Print:** estrutura de pastas  no VS Code.

![image.png](Implemente%20a%20logica%20de%20negocios%20e%20a%20persistencia%20d/image.png)

### 1.4. Configurando as variáveis de ambiente

Para evitar espalhar configurações de conexão pelo código, utilizaremos um arquivo `.env`.

Primeiro, instalamos as bibliotecas necessárias:

```
pip install pymongo python-dotenv
```

**Para que serve cada uma?**

- `pymongo`: driver que permite ao Python acessar e manipular dados no MongoDB.
- `python-dotenv`: permite carregar variáveis de ambiente de um arquivo `.env`.

#### Arquivo `.env`

Neste arquivo, configuramos a variável `MONGO_URI`, que representa o endereço de conexão com o banco.

Exemplo local sem autenticação:

```
MONGO_URI=mongodb://localhost:27017/meu_banco
```

Se o servidor exigir usuário e senha, a URI também poderá conter as credenciais e o banco utilizado para autenticação:

```
MONGO_URI=mongodb://USUARIO:SENHA@localhost:27017/meu_banco?authSource=admin
```

Nesse segundo exemplo:

- `USUARIO:SENHA`: credenciais de acesso.
- `meu_banco`: banco que a aplicação utilizará.
- `authSource=admin`: indica o banco onde as credenciais serão verificadas.

Os valores `USUARIO` e `SENHA` são apenas exemplos e devem ser substituídos localmente.

#### Arquivo `config.py`

Agora, na raiz do projeto, criamos:

```
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv('MONGO_URI')
```

**Entendendo o código:**

**`import os`**

Importa um módulo nativo do Python que permite, entre outras funcionalidades, acessar variáveis de ambiente.

**`from dotenv import load_dotenv`**

Importa a função responsável por carregar as configurações armazenadas no `.env`.

**`load_dotenv()`**

Carrega as variáveis do arquivo `.env` para que possam ser acessadas durante a execução.

**`os.getenv('MONGO_URI')`**

Busca o valor da variável `MONGO_URI`.

**`class Config`**

Centraliza as configurações utilizadas pela aplicação. O Flask poderá carregar seus atributos de configuração através da Application Factory.

📸 **Print:** arquivo `config.py` e  `.env`.

![image.png](Implemente%20a%20logica%20de%20negocios%20e%20a%20persistencia%20d/image%201.png)

![image.png](Implemente%20a%20logica%20de%20negocios%20e%20a%20persistencia%20d/image%202.png)

### 1.5. Conectando o MongoDB à Application Factory

Agora precisamos utilizar essas configurações para preparar o acesso ao banco de dados.

No arquivo `app/__init__.py`, adicionamos o PyMongo à nossa factory.

#### Código do projeto

```
from flask import Flask
from pymongo import MongoClient

db = None

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    global db

    try:
        client = MongoClient(app.config['MONGO_URI'])
        db = client.get_default_database()
    except Exception as e:
        print(f'Erro ao realizar a conexao com o banco de dados: {e}')

    from .routes.main import main_bp
    app.register_blueprint(main_bp)

    return app
```

#### Entendendo cada parte

**`from pymongo import MongoClient`**

Importa a classe utilizada para criar um cliente de acesso ao MongoDB.

**`db = None`**

Declara uma variável no nível do módulo. Inicialmente ela não possui uma referência de banco.

**`app.config.from_object('config.Config')`**

Carrega para o Flask as configurações definidas na classe `Config`, incluindo `MONGO_URI`.

**`global db`**

Permite que a função `create_app()` altere a variável `db` definida fora dela, em vez de criar uma nova variável local.

**`MongoClient(app.config['MONGO_URI'])`**

Cria o cliente MongoDB utilizando o endereço configurado.

**`client.get_default_database()`**

Seleciona o banco de dados informado na URI e atribui sua referência à variável `db`.

**`try / except`**

Captura possíveis exceções durante essa configuração e exibe uma mensagem de erro no terminal.

> 💡 Criar um `MongoClient` não garante, por si só, que o servidor está acessível. A conexão pode ser estabelecida posteriormente, quando uma operação for executada.
> 

#### Por que a importação do Blueprint mudou de lugar?

Observe que agora importamos `main_bp` **dentro de `create_app()`**, após preparar a variável `db`:

```
from .routes.main import main_bp
app.register_blueprint(main_bp)
```

Isso acontece porque `main.py` também importa `db` do pacote `app`.

Se os módulos tentarem importar informações um do outro antes de terminarem sua inicialização, podemos encontrar problemas de **importação circular**.

Ao adiar a importação do Blueprint, garantimos que a variável `db` já foi definida antes da importação das rotas.

📸 **Print:** arquivo `app/__init__.py`.

![image.png](Implemente%20a%20logica%20de%20negocios%20e%20a%20persistencia%20d/image%203.png)

### 1.6. Buscando todos os produtos

Com o banco configurado, vamos modificar o endpoint `GET /products` para buscar documentos reais.

No arquivo `app/routes/main.py`, importamos:

```
from app import db
from bson import ObjectId
```

O `db` representa a referência ao banco configurada na factory, enquanto `ObjectId` será utilizado para trabalhar com os identificadores do MongoDB.

#### Código da rota

```
@main_bp.route('/products', methods=['GET'])
def get_products():
    products_cursor = db.products.find({})
    products_list = []

    for products in products_cursor:
        products['_id'] = str(products['_id'])
        products_list.append(products)

    return jsonify(products_list)
```

#### Entendendo o código

**`db.products.find({})`**

Executa uma consulta na coleção `products`.

- `db`: banco de dados selecionado.
- `.products`: coleção que queremos consultar.
- `.find({})`: busca todos os documentos, pois o filtro está vazio.

**`products_cursor`**

Armazena um *cursor*, objeto que permite percorrer os resultados retornados pela consulta.

**`products_list = []`**

Cria uma lista vazia que armazenará os documentos encontrados.

**`for products in products_cursor`**

Percorre os documentos retornados pelo MongoDB.

**`products['_id'] = str(products['_id'])`**

Converte o identificador `_id` do documento em uma string.

Isso é necessário porque o identificador padrão do MongoDB utiliza o tipo `ObjectId`, que não pode ser convertido diretamente pelo `jsonify()` padrão do Flask.

**`products_list.append(products)`**

Adiciona o documento à lista que será retornada.

**`return jsonify(products_list)`**

Devolve todos os produtos encontrados em formato JSON.

> Agora, o conteúdo retornado depende dos documentos existentes no MongoDB, e não de mensagens fixas definidas no código.
> 

📸 **Print:** função `get_products()`.

![image.png](Implemente%20a%20logica%20de%20negocios%20e%20a%20persistencia%20d/image%204.png)

### 1.7. Buscando um produto pelo ID

Além de consultar todos os produtos, precisamos buscar um documento específico.

Para isso, utilizaremos o identificador `_id` gerado pelo MongoDB.

#### Alterando o tipo do parâmetro

Anteriormente, nossa rota recebia um número inteiro:

```
@main_bp.route('/product/<int:product_id>', methods=['GET'])
```

Agora, alteramos para:

```
@main_bp.route('/product/<string:product_id>', methods=['GET'])
```

**Por quê?**

O `ObjectId` padrão do MongoDB é representado por uma sequência hexadecimal de 24 caracteres, contendo números e letras.

Portanto, o identificador precisa ser recebido inicialmente como texto.

#### Código da rota

```
@main_bp.route('/product/<string:product_id>', methods=['GET'])
def get_product_by_id(product_id):
    try:
        oid = ObjectId(product_id)
    except Exception as e:
        return jsonify({
            "error": f"Erro ao transformar o {product_id} em ObjectId: {e}"
        })

    product = db.products.find_one({'_id': oid})

    if product:
        product['_id'] = str(product['_id'])
        return jsonify(product)
    else:
        return jsonify({
            "error": f"Produto com o id: {product_id} - Não encontrado"
        })
```

#### Entendendo cada parte

**`ObjectId(product_id)`**

Converte o identificador recebido na URL para o tipo `ObjectId`, utilizado no campo `_id` dos documentos.

**`try / except`**

Permite tratar erros caso o identificador não esteja em um formato válido.

**`db.products.find_one({'_id': oid})`**

Consulta a coleção `products` e procura um único documento cujo campo `_id` corresponda ao identificador informado.

Diferentemente do `find()`, o `find_one()` retorna um documento ou `None`, caso nenhum seja encontrado.

**`if product:`**

Verifica se algum documento foi encontrado.

Se existir, convertemos seu `_id` para string e retornamos o documento em JSON.

Caso contrário, retornamos uma mensagem informando que o produto não foi encontrado.

#### Diferença entre `find()` e `find_one()`

| Método | Resultado |
| --- | --- |
| `find({})` | Retorna um cursor para percorrer os documentos encontrados. |
| `find_one({'_id': oid})` | Retorna um único documento ou `None`. |

📸 **Print:** função `get_product_by_id()` .

![image.png](Implemente%20a%20logica%20de%20negocios%20e%20a%20persistencia%20d/image%205.png)

### 1.8. Executando e testando a aplicação

Com o MongoDB em execução e a configuração pronta, iniciamos o Flask:

```
python run.py
```

Utilizando o Postman ou Insomnia, podemos testar as duas rotas:

| Método | Endpoint | Resultado |
| --- | --- | --- |
| GET | `/products` | Lista os produtos do banco. |
| GET | `/product/<product_id>` | Busca o produto pelo ID. |

#### Teste 1 — Listar produtos

```
GET http://127.0.0.1:5000/products
```

A API deverá retornar uma lista JSON contendo os documentos encontrados.

#### Teste 2 — Buscar um produto específico

Copie o `_id` do produto no MongoDB Compass e utilize na URL:

```
http://127.0.0.1:5000/product/SEU_ID
```

A API deverá retornar apenas o produto correspondente.

### 1.9. Entendendo o fluxo completo

Agora nossa aplicação possui um caminho para buscar dados persistidos no MongoDB:

```
Cliente / Postman
        |
        | GET /products
        v
   Rota Flask
        |
        | Acessa db
        v
     PyMongo
        |
        | db.products.find({})
        v
     MongoDB
        |
        | Documentos encontrados
        v
 Conversão de ObjectId
        |
        v
     jsonify()
        |
        v
  Resposta HTTP
```

O Flask recebe a requisição, o PyMongo realiza a consulta e os documentos encontrados são preparados para uma resposta JSON.

O banco de dados permanece independente do servidor Flask. Dessa forma, os registros armazenados continuam disponíveis mesmo após reiniciarmos a aplicação.

### ✅ Resumo

Nesta etapa, conectamos nossa API Flask ao MongoDB e implementamos as primeiras consultas que retornam informações reais.

| Conceito | Para que serve |
| --- | --- |
| MongoDB | Banco NoSQL orientado a documentos. |
| MongoDB Compass | Interface gráfica para gerenciar bancos e coleções. |
| PyMongo | Driver utilizado para acessar o MongoDB pelo Python. |
| `.env` | Armazena configurações e variáveis de ambiente. |
| `load_dotenv()` | Carrega as variáveis do arquivo `.env`. |
| `os.getenv()` | Recupera valores de variáveis de ambiente. |
| `MongoClient` | Cria o cliente de acesso ao MongoDB. |
| `get_default_database()` | Seleciona o banco indicado na URI. |
| `find({})` | Consulta todos os documentos de uma coleção. |
| `find_one()` | Busca um único documento. |
| `ObjectId` | Tipo utilizado nos identificadores padrão do MongoDB. |
| `str()` | Converte o identificador para texto antes de retornar JSON. |

**O que aprendemos:** conectamos a arquitetura Flask a um banco de dados real, utilizando variáveis de ambiente para configurar a conexão e o PyMongo para consultar documentos.

Agora, os endpoints `GET /products` e `GET /product/<product_id>` deixam de retornar respostas simuladas e passam a consultar dados armazenados no MongoDB.

Nos próximos tópicos, poderemos integrar os modelos Pydantic e implementar operações de criação, atualização e exclusão de registros.

---

## 2. Utilizando os models nos dados reais do MongoDB

O objetivo é integrar os **modelos Pydantic** às consultas do MongoDB, garantindo que os documentos retornados pela API sejam validados, padronizados e convertidos corretamente para JSON.

Na etapa anterior, buscamos os produtos diretamente no banco de dados. Agora, utilizaremos nossos modelos para tratar essas informações antes de enviá-las ao cliente.

### 2.1. Adaptando o modelo Product para o MongoDB

Até agora, nosso modelo `Product` definia apenas os dados básicos dos produtos: nome, preço, descrição e estoque.

Entretanto, os documentos armazenados no MongoDB também possuem um identificador `_id`, que normalmente utiliza o tipo `ObjectId`.

Precisamos adaptar o modelo para reconhecer esse campo.

No arquivo `app/models/products.py`, adicionamos as seguintes importações:

```
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from bson import ObjectId
```

**Novos recursos utilizados:**

- `Field`: permite configurar propriedades de um campo, como aliases e valores padrão.
- `ConfigDict`: permite definir configurações internas do modelo Pydantic.
- `ObjectId`: representa o tipo utilizado nos identificadores padrão do MongoDB.

#### Atualizando a classe Product

```
class Product(BaseModel):
    id: Optional[ObjectId] = Field(None, alias='_id')
    name: str
    price: float
    description: Optional[str] = None
    stock: int

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
```

#### Entendendo as novidades

**`id: Optional[ObjectId] = Field(None, alias='_id')`**

Define o identificador do produto e permite associá-lo ao campo `_id` utilizado pelo MongoDB.

- `id`: nome do atributo dentro do modelo Python.
- `Optional[ObjectId]`: permite receber um `ObjectId` ou `None`.
- `Field(None, ...)`: define `None` como valor padrão.
- `alias='_id'`: associa o atributo `id` ao campo `_id` do documento.

Assim, conseguimos trabalhar com `id` dentro da aplicação e com `_id` na estrutura do banco.

**`model_config = ConfigDict(...)`**

Define configurações específicas para o funcionamento do Pydantic.

| Configuração | Finalidade |
| --- | --- |
| `populate_by_name=True` | Permite preencher o modelo tanto pelo nome `id` quanto pelo alias `_id`. |
| `arbitrary_types_allowed=True` | Permite utilizar tipos externos aos tipos nativos do Python, como `ObjectId`. |

> 💡 Permitir o uso de `ObjectId` não significa convertê-lo automaticamente em JSON. Para isso, ainda precisamos preparar sua serialização.
> 

📸 **Print:** classe `Product`.

![image.png](Implemente%20a%20logica%20de%20negocios%20e%20a%20persistencia%20d/image%206.png)

### 2.2. Criando o modelo ProductDBModel

Para trabalhar com os produtos recuperados do MongoDB, criamos uma nova classe chamada `ProductDBModel`.

Ela herda da classe `Product`, reutilizando todos os seus campos e validações.

```
class ProductDBModel(Product):
```

Agora, precisamos adaptar a forma como seus dados são convertidos para um dicionário Python.

#### Sobrescrevendo o método model_dump()

O Pydantic disponibiliza o método `model_dump()`, utilizado para converter uma instância do modelo em um dicionário.

Como o `ObjectId` não é serializado diretamente pelo `jsonify()` padrão do Flask, vamos sobrescrever esse método para converter o identificador em string.

No nosso código, a classe ficou assim:

```
class ProductDBModel(Product):
    def model_dump(
        self, *, mode='python', include=None,
        exclude=None, context=None, by_alias=None,
        exclude_unset=False, exclude_defaults=False,
        exclude_none=False, round_trip=False
    ):
        data = super().model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip
        )

        if self.id:
            data["_id"] = str(data["_id"])

        return data
```

#### Entendendo o código

**`class ProductDBModel(Product)`**

Cria uma classe que herda de `Product`, reutilizando seus atributos e configurações.

**`def model_dump(...)`**

Sobrescreve o método original do Pydantic para personalizar o dicionário retornado.

Os parâmetros permitem controlar quais campos serão incluídos e como os dados serão exportados.

**`super().model_dump(...)`**

Chama o método original da classe herdada e armazena o dicionário resultante em `data`.

**`if self.id:`**

Verifica se o produto possui um identificador.

**`data["_id"] = str(data["_id"])`**

Converte o `ObjectId` em string, permitindo que o identificador seja incluído na resposta JSON.

**`return data`**

Retorna o dicionário com os dados preparados.

> **Importante:** essa implementação foi construída para ser utilizada com `by_alias=True`, como veremos nas rotas. Sem esse parâmetro, o dicionário poderá conter `id` em vez de `_id`, causando um erro ao acessar `data["_id"]`.
> 

📸 **Print:** classe `ProductDBModel`.

![image.png](Implemente%20a%20logica%20de%20negocios%20e%20a%20persistencia%20d/image%207.png)

### 2.3. Utilizando os models na listagem de produtos

Com os modelos preparados, vamos atualizar o endpoint `GET /products` para validar e transformar cada documento retornado pelo banco.

No arquivo `app/routes/main.py`, importamos:

```
from app.models.products import *
```

O `*` importa os nomes públicos do módulo, incluindo `Product` e `ProductDBModel`. Em projetos maiores, geralmente é preferível importar explicitamente as classes utilizadas.

#### Código atualizado

```
@main_bp.route('/products', methods=['GET'])
def get_products():
    products_cursor = db.products.find({})

    products_list = [
        ProductDBModel(**product).model_dump(
            by_alias=True,
            exclude_none=True
        )
        for product in products_cursor
    ]

    return jsonify(products_list)
```

#### Entendendo o código

**`db.products.find({})`**

Continua realizando a consulta de todos os produtos armazenados no MongoDB.

**`ProductDBModel(**product)`**

Cria uma instância do modelo para cada documento retornado.

O operador `**` desempacota o documento em argumentos nomeados, permitindo que o Pydantic valide os campos recebidos.

**`.model_dump(by_alias=True, exclude_none=True)`**

Transforma o modelo validado em um dicionário Python.

Os parâmetros utilizados são:

- `by_alias=True`: utiliza os aliases definidos no modelo, como `_id`.
- `exclude_none=True`: remove do resultado os campos cujo valor seja `None`.

**`for product in products_cursor`**

Percorre todos os documentos encontrados pelo MongoDB.

**`products_list = [...]`**

Utiliza uma *list comprehension*, recurso do Python que permite construir uma lista de forma compacta.

#### 💡 Entendendo a list comprehension

A expressão:

```
products_list = [
    ProductDBModel(**product).model_dump(
        by_alias=True,
        exclude_none=True
    )
    for product in products_cursor
]
```

É equivalente, na sua lógica principal, a escrever:

```python
products_list = []

for product in products_cursor:
    product_model = ProductDBModel(**product)

    product_data = product_model.model_dump(
        by_alias=True,
        exclude_none=True
    )

    products_list.append(product_data)
```

As duas formas percorrem os documentos, validam cada produto e adicionam o resultado à lista.

A primeira é mais compacta, enquanto a segunda pode ser mais fácil de compreender inicialmente.

📸 **Print:** função `get_products()`.

![image.png](Implemente%20a%20logica%20de%20negocios%20e%20a%20persistencia%20d/image%208.png)

### 2.4. Adaptando a busca por um único produto

Também precisamos atualizar o endpoint `GET /product/<product_id>` para utilizar o novo modelo.

A consulta com `find_one()` permanece igual. A mudança acontece no tratamento do documento encontrado.

#### Código atualizado

```
product = db.products.find_one({'_id': oid})

if product:
    product_model = ProductDBModel(**product).model_dump(
        by_alias=True,
        exclude_none=True
    )
    return jsonify(product_model)
else:
    return jsonify({
        "error": f"Produto com o id: {product_id} - Não encontrado"
    })
```

**Como funciona?**

- `find_one({'_id': oid})`: procura o produto pelo identificador.
- `ProductDBModel(**product)`: cria o modelo e valida os dados encontrados.
- `model_dump(...)`: converte o modelo em um dicionário, utilizando os aliases e removendo valores `None`.
- `jsonify(product_model)`: retorna o produto em formato JSON.

**Diferença entre as duas rotas:**

| Endpoint | Processamento |
| --- | --- |
| `GET /products` | Percorre vários documentos e cria uma lista de modelos. |
| `GET /product/<product_id>` | Valida e converte apenas o documento encontrado. |

Com isso, ambas as rotas seguem o mesmo padrão de tratamento dos dados.

📸 **Print:** função `get_product_by_id()`.

![image.png](Implemente%20a%20logica%20de%20negocios%20e%20a%20persistencia%20d/image%209.png)

### 2.5. Testando as consultas

Para verificar o funcionamento, iniciamos nossa aplicação:

```
python run.py
```

No Postman ou Insomnia, podemos executar as duas consultas.

#### Teste 1 — Listagem de produtos

```
GET http://127.0.0.1:5000/products
```

**Exemplo de resposta:**

```
[
  {
    "_id": "507f1f77bcf86cd799439011",
    "name": "Placa de Vídeo RTX 9090",
    "price": 15999.9,
    "stock": 50
  }
]
```

Nesse exemplo, o campo `description` não aparece porque seu valor seria `None` e utilizamos `exclude_none=True`.

#### Teste 2 — Busca por um produto

```
GET http://127.0.0.1:5000/product/507f1f77bcf86cd799439011
```

**Exemplo de resposta:**

```
{
  "_id": "507f1f77bcf86cd799439011",
  "name": "Placa de Vídeo RTX 9090",
  "price": 15999.9,
  "stock": 50
}
```

O identificador utilizado é apenas ilustrativo. Para testar, precisamos informar o `_id` de um documento realmente existente no MongoDB.

### 2.6. Entendendo o fluxo completo

Agora, além de consultar o banco, nossa aplicação também valida e transforma os documentos antes de retorná-los.

```
Cliente / Postman
        |
        | GET /products
        v
     Rota Flask
        |
        v
    MongoDB / PyMongo
        |
        | Retorna os documentos
        v
    ProductDBModel
        |
        | Valida os campos
        v
     model_dump()
        |
        | Aplica aliases
        | Converte ObjectId
        | Remove valores None
        v
       jsonify()
        |
        v
   Resposta HTTP
```

Essa separação facilita a manutenção e evita repetir manualmente a conversão do identificador em cada endpoint.

**Observação:** os modelos validam os tipos declarados, mas não garantem que todas as informações armazenadas no banco estejam corretas. Caso algum documento não atenda às regras do Pydantic, ocorrerá um erro de validação que ainda precisará ser tratado adequadamente nas rotas.

### ✅ Resumo

Nesta etapa, integramos os modelos Pydantic às consultas do MongoDB, padronizando os dados retornados pela API.

| Conceito | Para que serve |
| --- | --- |
| `Field()` | Configura propriedades e aliases dos campos. |
| `alias='_id'` | Associa o atributo `id` ao identificador do MongoDB. |
| `ConfigDict` | Define configurações internas do Pydantic. |
| `populate_by_name=True` | Permite preencher campos pelo nome ou alias. |
| `arbitrary_types_allowed=True` | Permite utilizar tipos externos, como `ObjectId`. |
| `ProductDBModel` | Modelo utilizado para validar e preparar os produtos lidos do banco. |
| `super()` | Permite chamar métodos da classe herdada. |
| `model_dump()` | Converte o modelo em um dicionário Python. |
| `by_alias=True` | Utiliza os aliases definidos nos campos. |
| `exclude_none=True` | Remove campos com valor `None` do resultado. |
| *List comprehension* | Permite construir listas de maneira compacta. |

**O que aprendemos:** agora nossas consultas não retornam diretamente os documentos do MongoDB. Antes de responder ao cliente, utilizamos o Pydantic para validar a estrutura, aplicar os aliases e preparar os dados para serialização em JSON.

Com isso, os endpoints de listagem e busca individual compartilham o mesmo padrão de tratamento dos produtos, preparando a aplicação para implementar as próximas operações de manipulação de dados.

---

## 3. Autenticação real com JWT

## 🎯 Objetivo

Implementar a **autenticação baseada em JWT (JSON Web Token)** na API Flask, permitindo gerar tokens de acesso, validar sua autenticidade e proteger endpoints contra requisições não autorizadas.

Nesta etapa, vamos transformar nosso login simulado em um endpoint que gera tokens e utilizá-los para controlar o acesso à criação de produtos no MongoDB.

## 3.1. O que é JWT?

O **JWT (JSON Web Token)** é um padrão utilizado para transmitir informações entre sistemas através de um token compacto e assinado digitalmente.

Em uma API, ele pode ser utilizado para autenticação: após validar as credenciais, o servidor gera um token que o cliente deverá enviar nas próximas requisições a endpoints protegidos.

Um JWT normalmente possui três partes:

```
HEADER.PAYLOAD.SIGNATURE
```

| Parte | Responsabilidade |
| --- | --- |
| Header | Informa o tipo do token e o algoritmo utilizado. |
| Payload | Contém informações (*claims*), como identificação do usuário e expiração. |
| Signature | Permite verificar se o token foi alterado e se foi assinado com a chave esperada. |

**Como funciona na prática?**

1. O cliente envia usuário e senha para `/login`.
2. O servidor verifica as credenciais e gera um JWT.
3. O cliente armazena temporariamente o token.
4. Ao acessar uma rota protegida, envia o JWT no cabeçalho `Authorization`.
5. O servidor valida o token antes de executar a funcionalidade.

> 💡 O conteúdo de um JWT assinado não é criptografado. Por isso, não devemos colocar senhas ou informações sensíveis no seu payload.
> 

---

## 3.2. Atualizando a arquitetura do projeto

Para centralizar a verificação dos tokens e reutilizá-la em diferentes endpoints, criamos o arquivo `decorators.py`.

### 📁 Estrutura atualizada

```
flask_alura/
│
├── app/
│   ├── __init__.py
│   ├── decorators.py       # Validação de tokens JWT
│   │
│   ├── models/
│   │   ├── products.py
│   │   ├── sale.py
│   │   └── user.py
│   │
│   └── routes/
│       └── main.py         # Login e rotas protegidas
│
├── .env                    # Configurações e chaves
├── config.py               # Configurações Flask
└── run.py
```

**Responsabilidade dos arquivos envolvidos:**

| Arquivo | Responsabilidade |
| --- | --- |
| `app/decorators.py` | Verifica se o token JWT é válido antes de executar uma rota. |
| `app/routes/main.py` | Gera o token no login e protege o cadastro de produtos. |
| `config.py` | Carrega a chave utilizada para assinar e validar os tokens. |
| `.env` | Armazena a chave secreta e as configurações do banco. |

📸 **Print:** estrutura atualizada do projeto no VS Code.

---

## 3.3. Configurando a autenticação

Para gerar e validar os JWTs, utilizaremos a biblioteca **PyJWT**.

Com o ambiente virtual ativo, podemos instalá-la:

```
pip install PyJWT
```

A biblioteca é importada no Python utilizando:

```
import jwt
```

### Configurando a chave secreta

Precisamos de uma chave utilizada tanto para assinar quanto para verificar a assinatura dos tokens.

No arquivo `.env`, adicionamos a variável:

```
SECRET_KEY=SUBSTITUA_POR_UMA_CHAVE_FORTE_E_ALEATORIA
```

Em seguida, no arquivo `config.py`, adicionamos a configuração:

```
class Config:
    MONGO_URI = os.getenv('MONGO_URI')
    SECRET_KEY = os.getenv('SECRET_KEY')
```

**Como funciona?**

- `SECRET_KEY`: chave utilizada para assinar e verificar o JWT.
- `os.getenv('SECRET_KEY')`: recupera a variável de ambiente.
- `app.config.from_object('config.Config')`: carrega essa configuração na aplicação Flask, conforme implementamos anteriormente.

**Importante:** a chave deve ser forte, aleatória, mantida em segredo e diferente para cada ambiente. O arquivo `.env` não deve ser enviado ao GitHub.

---

## 3.4. Gerando o JWT no endpoint de login

Agora vamos modificar a rota de login para que, após verificar as credenciais, ela gere um token de acesso.

No arquivo `app/routes/main.py`, adicionamos:

```
from flask import current_app
from datetime import datetime, timedelta, timezone
import jwt
```

**Novos recursos utilizados:**

- `current_app`: permite acessar as configurações da aplicação Flask durante uma requisição.
- `datetime`: trabalha com datas e horários.
- `timedelta`: permite calcular um intervalo de tempo.
- `timezone`: permite utilizar o horário UTC.
- `jwt`: biblioteca responsável pela criação e validação dos tokens.

### Código da autenticação

Após validar os dados recebidos pelo modelo `LoginPayload`, utilizamos:

```
if user_data.username == 'admin' and user_data.password == '123':
    token = jwt.encode(
        {
            "user_id": user_data.username,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        },
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )

    return jsonify({'access_token': token}), 200

return jsonify({"error": "Credenciais inválidas"}), 401
```

### Entendendo o código

**`jwt.encode(...)`**

Cria um JWT assinado a partir de um conjunto de informações.

**`"user_id": user_data.username`**

Adiciona ao payload a identificação do usuário autenticado.

**`"exp": datetime.now(timezone.utc) + timedelta(minutes=30)`**

Define o momento em que o token expirará.

- `datetime.now(timezone.utc)`: obtém a data e o horário atual em UTC.
- `timedelta(minutes=30)`: adiciona 30 minutos ao horário atual.
- `exp`: claim padrão utilizado para indicar a expiração do token.

**`current_app.config['SECRET_KEY']`**

Recupera a chave secreta configurada na aplicação.

**`algorithm='HS256'`**

Define o algoritmo utilizado para assinar o JWT. O HS256 utiliza uma chave secreta compartilhada.

**`return jsonify({'access_token': token}), 200`**

Retorna o token gerado em uma resposta JSON com status HTTP `200 OK`.

Caso as credenciais estejam incorretas, o endpoint retorna `401 Unauthorized`.

> Nesta implementação, a validação das credenciais ainda é fixa (`admin` e `123`). A novidade é que, após essa verificação, geramos um JWT real e assinado, com tempo de expiração.
> 

📸 **Print:** função `login()` atualizada, mostrando a geração do JWT.

---

## 3.5. Criando o decorator de autenticação

Para proteger nossas rotas, utilizaremos um **decorator**, recurso do Python que permite adicionar comportamentos a uma função sem modificar diretamente sua implementação.

Criamos o arquivo `app/decorators.py` e definimos uma função chamada `token_required`.

### Código do projeto

```
from functools import wraps
from flask import request, jsonify, current_app
import jwt

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):

        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'message': 'Token Malformado'}), 401

        if not token:
            return jsonify({'error': 'Token não encontrado'}), 401

        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token Expirado'}), 401

        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token Inválido'}), 401

        return f(data, *args, **kwargs)

    return decorated
```

### Entendendo cada parte

**`def token_required(f):`**

Define um decorator que recebe a função que queremos proteger.

**`@wraps(f)`**

Preserva informações da função original, como seu nome e metadados, importantes também para o registro correto dos endpoints no Flask.

**`request.headers['Authorization']`**

Acessa o cabeçalho HTTP onde o cliente enviará o token.

O formato convencional é:

```
Authorization: Bearer SEU_TOKEN_JWT
```

**`auth_header.split(' ')[1]`**

Divide o conteúdo do cabeçalho pelo espaço e captura a segunda parte, correspondente ao token.

No código atual, esse trecho extrai o token, mas ainda não verifica explicitamente se o prefixo é `Bearer`.

**`jwt.decode(...)`**

Verifica a assinatura do token utilizando a chave secreta configurada e valida informações como sua expiração.

O parâmetro `algorithms=['HS256']` restringe a verificação ao algoritmo esperado.

### Tratando os erros de autenticação

O decorator diferencia alguns problemas:

| Situação | Retorno |
| --- | --- |
| Token não informado | `401` — Token não encontrado |
| Cabeçalho malformado | `401` — Token Malformado |
| Token expirado | `401` — Token Expirado |
| Token inválido | `401` — Token Inválido |
| Token válido | A requisição continua para a função protegida |

**`return f(data, *args, **kwargs)`**

Quando o token é válido, executa a função original e repassa o payload decodificado como primeiro argumento.

Assim, a rota protegida pode acessar as informações contidas no JWT.

📸 **Print:** arquivo `app/decorators.py`, destacando a extração e validação do token.

---

## 3.6. Protegendo a criação de produtos

Com o decorator implementado, podemos utilizá-lo para proteger o endpoint `POST /products`.

Dessa forma, somente requisições com um JWT válido poderão executar a função de cadastro.

No arquivo `app/routes/main.py`, importamos:

```
from app.decorators import token_required
```

### Código atualizado da rota

```
@main_bp.route('/products', methods=['POST'])
@token_required
def create_product(token):
    try:
        product = Product(**request.get_json())
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    result = db.products.insert_one(product.model_dump())

    return jsonify({
        "message": "Produto criado com sucesso",
        "id": str(result.inserted_id)
    }), 201
```

### Entendendo o código

**`@token_required`**

Aplica o decorator à função, exigindo a validação do JWT antes de executar o cadastro.

**Ordem dos decorators**

Observe que `@token_required` aparece abaixo de `@main_bp.route(...)`.

```
@main_bp.route('/products', methods=['POST'])
@token_required
def create_product(token):
```

Os decorators são aplicados de baixo para cima. Portanto, `token_required` protege a função antes de o Flask registrar a rota.

Essa ordem é importante: na implementação inicial da aula, ela precisou ser corrigida.

**`def create_product(token):`**

Recebe o payload decodificado do JWT, enviado pelo decorator após a validação.

Nesse momento, o argumento `token` contém os dados do token, como `user_id` e `exp`, não a string JWT original.

**`Product(**request.get_json())`**

Recebe os dados enviados no corpo da requisição e cria uma instância do modelo Pydantic, validando os campos do produto.

**`db.products.insert_one(product.model_dump())`**

Converte o modelo validado em um dicionário e insere o documento na coleção `products` do MongoDB.

**`result.inserted_id`**

Recupera o identificador gerado pelo MongoDB para o documento inserido.

**`return jsonify(...), 201`**

Retorna uma resposta confirmando o cadastro com status `201 Created`, utilizado quando um recurso é criado com sucesso.

> 💡 No código atual, `model_dump()` utiliza os nomes dos atributos Python e inclui campos com valor `None`. Para um documento mais limpo e alinhado aos aliases do MongoDB, posteriormente podemos utilizar `model_dump(by_alias=True, exclude_none=True)`. Essa versão chegou a aparecer durante os ajustes, mas não permaneceu no último commit da aula.
> 

📸 **Print:** rota `create_product()` com o decorator e a inserção no MongoDB.

---

## 3.7. Testando a autenticação e o cadastro

Agora podemos testar o fluxo completo utilizando Postman ou Insomnia.

Inicie a aplicação:

```
python run.py
```

### Teste 1 — Realizando login

**Endpoint:**

```
POST http://127.0.0.1:5000/login
```

**Body (JSON):**

```
{
  "username": "admin",
  "password": "123"
}
```

**Resposta esperada:**

```
{
  "access_token": "SEU_JWT_GERADO"
}
```

Status HTTP: `200 OK`.

O valor retornado em `access_token` será um JWT assinado e com prazo de expiração.

📸 **Print:** resposta do login no Postman, mostrando o token gerado.

### Teste 2 — Criando um produto com JWT

**Endpoint:**

```
POST http://127.0.0.1:5000/products
```

No Postman, na aba **Authorization**, podemos selecionar `Bearer Token` e informar o token obtido no login.

Também podemos configurar manualmente o cabeçalho:

```
Authorization: Bearer SEU_JWT_GERADO
```

No corpo da requisição, enviamos os dados do produto:

```
{
  "name": "Teclado Mecânico",
  "price": 299.90,
  "description": "Teclado para jogos",
  "stock": 15
}
```

**Resposta esperada:**

```
{
  "message": "Produto criado com sucesso",
  "id": "ID_GERADO_PELO_MONGODB"
}
```

Status HTTP: `201 Created`.

O MongoDB deverá armazenar o novo produto na coleção `products`.

### Teste 3 — Criando produto sem token

Se tentarmos acessar `POST /products` sem o cabeçalho `Authorization`, o decorator impedirá a execução da função.

**Resposta:**

```
{
  "error": "Token não encontrado"
}
```

Status HTTP: `401 Unauthorized`.

Também podemos testar um token inválido ou expirado para verificar os demais tratamentos implementados.

📸 **Print:** tentativa de cadastro sem token e cadastro realizado com sucesso.

---

## 3.8. Entendendo o fluxo completo

Agora temos um fluxo que combina autenticação JWT, validação Pydantic e persistência no MongoDB.

```
Cliente / Postman
       |
       | POST /login
       v
   LoginPayload
       |
       | Valida os campos
       v
 Verifica credenciais
       |
       v
   jwt.encode()
       |
       | Gera token assinado
       v
 Cliente recebe JWT
       |
       | POST /products
       | Authorization: Bearer JWT
       v
  @token_required
       |
       | jwt.decode()
       | Verifica assinatura e expiração
       v
    Token válido?
       /       \
     Não       Sim
      |         |
      v         v
   Erro 401  create_product()
                |
                v
          Product (Pydantic)
                |
                | Valida os dados
                v
         MongoDB insert_one()
                |
                v
           Resposta 201
```

O decorator centraliza a verificação dos tokens, permitindo que essa mesma lógica seja reutilizada futuramente em outros endpoints protegidos.

---

### ✅ Resumo

Nesta etapa, implementamos a geração e validação de JWTs e utilizamos essa autenticação para proteger o cadastro de produtos no MongoDB.

| Conceito | Para que serve |
| --- | --- |
| JWT | Token assinado utilizado para transmitir informações verificáveis. |
| PyJWT | Biblioteca Python para gerar e validar JWTs. |
| `SECRET_KEY` | Chave utilizada para assinar e validar o token HS256. |
| `jwt.encode()` | Gera um token assinado. |
| `jwt.decode()` | Valida e decodifica o token. |
| `exp` | Define o momento de expiração. |
| `current_app` | Permite acessar as configurações da aplicação Flask. |
| `@wraps(f)` | Preserva metadados da função decorada. |
| `@token_required` | Restringe o acesso a endpoints protegidos. |
| `Authorization` | Cabeçalho utilizado para enviar o JWT. |
| `insert_one()` | Insere um documento no MongoDB. |
| `inserted_id` | Retorna o ID do documento criado. |

**O que aprendemos:** implementamos um mecanismo de autenticação baseado em JWT, permitindo gerar tokens com expiração, verificar sua validade e proteger operações da API.

Além disso, o endpoint `POST /products` passou a cadastrar documentos reais no MongoDB, utilizando Pydantic para validar os dados recebidos.

A autenticação ainda utiliza credenciais fixas, mas a estrutura de geração e verificação dos tokens já está preparada para evoluir para usuários reais e regras de autorização mais completas.

---

## 4. Modificando o estado dos Produtos

## 🎯 Objetivo

Completar as operações de **CRUD (Create, Read, Update e Delete)** da nossa API Flask, implementando a atualização e exclusão de produtos armazenados no MongoDB.

Nesta etapa, vamos utilizar um modelo Pydantic para validar atualizações parciais e proteger as operações de modificação através da autenticação JWT.

## 4.1. Entendendo o CRUD

O CRUD representa as quatro operações básicas utilizadas para manipular registros em um sistema.

| Operação | Método HTTP | Funcionalidade |
| --- | --- | --- |
| Create | POST | Criar um produto |
| Read | GET | Consultar produtos |
| Update | PUT | Atualizar um produto |
| Delete | DELETE | Excluir um produto |

Nas etapas anteriores, implementamos a leitura e criação de produtos. Agora, vamos completar o ciclo utilizando os métodos `PUT` e `DELETE`.

---

## 4.2. Criando o modelo UpdateProduct

Nosso modelo `Product` exige determinados campos obrigatórios, como nome, preço e estoque.

Entretanto, durante uma atualização, podemos precisar modificar apenas uma dessas informações, sem enviar todos os dados novamente.

Para isso, vamos criar um modelo específico chamado `UpdateProduct`.

No arquivo `app/models/products.py`, adicionamos:

```
class UpdateProduct(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    stock: Optional[int] = None
```

### Entendendo o código

**`class UpdateProduct(BaseModel)`**

Cria um novo modelo Pydantic destinado à validação dos dados recebidos durante uma atualização.

**`Optional[...] = None`**

Permite que todos os campos sejam omitidos da requisição.

Dessa forma, não precisamos informar novamente todos os atributos do produto para modificar apenas um deles.

**Por que o ID não está presente?**

Porque o identificador é recebido diretamente pela URL e utilizado para localizar o documento no MongoDB. Ele não faz parte dos campos que desejamos atualizar.

### Diferença entre os modelos

| Product | UpdateProduct |
| --- | --- |
| Utilizado na criação | Utilizado na atualização |
| Possui campos obrigatórios | Todos os campos podem ser omitidos |
| Define a estrutura completa | Permite enviar apenas os campos desejados |
| Pode receber um identificador | Não inclui o identificador |

📸 **Print:** modelo `UpdateProduct` adicionado ao arquivo `app/models/products.py`.

---

## 4.3. Implementando a atualização de produtos

Vamos modificar a função `update_product()` no arquivo `app/routes/main.py`.

O endpoint receberá o identificador pela URL e os campos que desejamos alterar pelo corpo JSON da requisição.

### Código atualizado

```
@main_bp.route('/product/<string:product_id>', methods=['PUT'])
@token_required
def update_product(token, product_id):
    try:
        oid = ObjectId(product_id)
        update_data = UpdateProduct(**request.get_json())

        update_result = db.products.update_one(
            {"_id": oid},
            {"$set": update_data.model_dump(exclude_unset=True)}
        )

        if update_result.matched_count == 0:
            return jsonify({"error": "Produto não encontrado"}), 404

        updated_product = db.products.find_one({"_id": oid})

        return jsonify(
            ProductDBModel(**updated_product).model_dump(
                by_alias=True,
                exclude_none=True
            )
        )

    except ValidationError as e:
        return jsonify({"error": e.errors()})
```

### Entendendo cada parte

**`@main_bp.route('/product/<string:product_id>', methods=['PUT'])`**

Define uma rota que recebe o identificador do produto como texto e aceita requisições HTTP do tipo `PUT`.

O ID é recebido como `string` porque os identificadores padrão do MongoDB utilizam o tipo `ObjectId`.

**`@token_required`**

Exige um JWT válido antes de permitir a atualização.

**`def update_product(token, product_id)`**

Recebe os dados decodificados do JWT através do decorator e o identificador do produto informado na URL.

**`oid = ObjectId(product_id)`**

Converte o identificador recebido em texto para o tipo utilizado pelo MongoDB.

**`update_data = UpdateProduct(**request.get_json())`**

Captura o JSON enviado pelo cliente e utiliza o Pydantic para validar os dados da atualização.

---

## 4.4. Atualizando o documento no MongoDB

A operação responsável por modificar os dados é:

```
update_result = db.products.update_one(
    {"_id": oid},
    {"$set": update_data.model_dump(exclude_unset=True)}
)
```

### Entendendo o código

**`db.products.update_one()`**

Método do PyMongo que atualiza um único documento correspondente ao filtro informado.

Ele recebe dois argumentos principais:

1. **Filtro:** identifica qual documento queremos atualizar.
2. **Operação:** determina quais alterações serão realizadas.

**`{"_id": oid}`**

Procura o produto cujo identificador corresponde ao valor recebido.

**`$set`**

Operador do MongoDB utilizado para definir ou alterar valores de campos, preservando os demais campos do documento.

**`update_data.model_dump(exclude_unset=True)`**

Converte o modelo Pydantic em um dicionário, incluindo somente os campos informados explicitamente na criação do modelo.

### 💡 Por que utilizar exclude_unset=True?

Imagine que o produto possui os seguintes dados:

```
{
  "name": "Notebook Gamer",
  "price": 5000,
  "description": "Notebook para jogos",
  "stock": 10
}
```

Queremos alterar apenas o preço, então enviamos:

```
{
  "price": 4500
}
```

Com `exclude_unset=True`, o Pydantic gera:

```
{"price": 4500.0}
```

O MongoDB atualizará somente o preço, preservando as demais informações do produto.

**Importante:** `exclude_unset=True` remove os campos não enviados, mas mantém um campo explicitamente enviado como `null` (`None` no Python). Isso pode afetar a validação dos dados caso um campo obrigatório do produto seja alterado para `null`.

> Embora a rota utilize o método PUT, a implementação permite atualizações parciais, um comportamento frequentemente associado ao método PATCH em APIs REST.
> 

---

## 4.5. Verificando o resultado da atualização

Após executar o `update_one()`, precisamos verificar se o produto realmente existe.

```
if update_result.matched_count == 0:
    return jsonify({"error": "Produto não encontrado"}), 404
```

**`matched_count`**

Informa quantos documentos corresponderam ao filtro da atualização.

- `0`: nenhum produto foi encontrado.
- `1`: o produto foi encontrado, mesmo que os novos valores sejam iguais aos atuais.

Se nenhum documento corresponder ao identificador, retornamos `404 Not Found`.

### Retornando o produto atualizado

Quando o produto existe, buscamos novamente seus dados:

```
updated_product = db.products.find_one({"_id": oid})

return jsonify(
    ProductDBModel(**updated_product).model_dump(
        by_alias=True,
        exclude_none=True
    )
)
```

**Como funciona?**

- `find_one()`: consulta o documento após a atualização.
- `ProductDBModel(**updated_product)`: valida o produto recuperado.
- `model_dump()`: converte o modelo em um dicionário.
- `by_alias=True`: utiliza `_id` no lugar de `id`.
- `exclude_none=True`: remove campos com valor `None`.
- `jsonify()`: retorna o produto atualizado em JSON.

Assim, o cliente recebe os dados completos do produto após a modificação.

📸 **Print:** função `update_product()` e resultado da atualização no Postman.

---

## 4.6. Implementando a exclusão de produtos

Agora vamos implementar a operação responsável por excluir um documento do MongoDB.

No arquivo `app/routes/main.py`, atualizamos a função `delete_product()`.

### Código atualizado

```
@main_bp.route('/product/<string:product_id>', methods=['DELETE'])
@token_required
def delete_product(token, product_id):
    try:
        oid = ObjectId(product_id)

        delete_product = db.products.delete_one({"_id": oid})

        if delete_product.deleted_count == 0:
            return jsonify({"error": "Produto não foi encontrado"}), 404

        return "", 204

    except Exception:
        return jsonify({"error": "id do produto inválido"}), 400
```

### Entendendo o código

**`methods=['DELETE']`**

Define que o endpoint aceita requisições HTTP do tipo DELETE, utilizado para excluir recursos.

**`@token_required`**

Protege a operação de exclusão, exigindo um JWT válido.

**`ObjectId(product_id)`**

Converte o identificador recebido pela URL para o tipo esperado pelo MongoDB.

**`db.products.delete_one({"_id": oid})`**

Exclui um único documento cujo `_id` corresponde ao identificador informado.

### Verificando a exclusão

```
if delete_product.deleted_count == 0:
    return jsonify({"error": "Produto não foi encontrado"}), 404
```

**`deleted_count`**

Informa quantos documentos foram realmente excluídos.

- `0`: nenhum documento foi excluído.
- `1`: o documento foi excluído com sucesso.

Quando a exclusão ocorre, retornamos:

```
return "", 204
```

O status **204 No Content** indica que a operação foi realizada com sucesso, mas não existe conteúdo para retornar no corpo da resposta.

### Tratamento de erros

```
except Exception:
    return jsonify({"error": "id do produto inválido"}), 400
```

O `except` captura possíveis exceções e retorna status `400 Bad Request`.

**Observação:** como estamos utilizando `Exception`, qualquer erro ocorrido nesse bloco será tratado como ID inválido, inclusive problemas de conexão ou operação no banco. Futuramente, podemos tornar esse tratamento mais específico.

📸 **Print:** função `delete_product()` no VS Code.

---

## 4.7. Testando as operações

Com a aplicação e o MongoDB em execução, podemos testar os novos endpoints utilizando Postman ou Insomnia.

Primeiro, iniciamos o servidor:

```
python run.py
```

Como as duas rotas estão protegidas, precisamos realizar login e obter um JWT válido.

Depois, configuramos a autenticação como **Bearer Token**, informando o token gerado.

### Teste 1 — Atualizando um produto

**Endpoint:**

```
PUT http://127.0.0.1:5000/product/SEU_ID
```

**Body (JSON):**

```
{
  "name": "Notebook Gamer X16"
}
```

Como utilizamos o modelo `UpdateProduct`, podemos enviar apenas o campo que desejamos alterar.

**Resultado esperado:**

A API retorna o documento atualizado em JSON, com o novo nome e os demais campos preservados.

Status HTTP: `200 OK`.

📸 **Print:** atualização no Postman e confirmação da alteração no MongoDB Compass.

### Teste 2 — Excluindo um produto

**Endpoint:**

```
DELETE http://127.0.0.1:5000/product/SEU_ID
```

Não precisamos enviar um corpo JSON, pois o identificador do produto já está presente na URL.

**Resultado esperado:**

Status HTTP: `204 No Content`, sem corpo de resposta.

Após a exclusão, podemos consultar o MongoDB Compass para confirmar que o documento não existe mais.

📸 **Print:** requisição DELETE no Postman e resultado no MongoDB Compass.

### Teste 3 — Produto inexistente

Caso informemos um identificador com formato válido, mas que não corresponda a nenhum documento, as duas operações retornam `404 Not Found`.

**Observações sobre o código atual:**

- Na atualização, erros de validação do Pydantic retornam uma resposta sem status explícito, ou seja, HTTP 200 por padrão. O ideal seria utilizar 400.
- Um `ObjectId` inválido na atualização não é capturado pelo `except ValidationError` e pode resultar em erro 500.
- A exclusão utiliza um tratamento genérico de exceções, que poderá ser refinado posteriormente.

---

## 4.8. Completando o fluxo CRUD

Com a implementação das novas rotas, nossa API passa a oferecer as quatro operações básicas de gerenciamento de produtos.

| Método | Endpoint | Operação | JWT |
| --- | --- | --- | --- |
| POST | `/products` | Criar produto | Sim |
| GET | `/products` | Listar produtos | Não |
| GET | `/product/<product_id>` | Consultar produto | Não |
| PUT | `/product/<product_id>` | Atualizar produto | Sim |
| DELETE | `/product/<product_id>` | Excluir produto | Sim |

### Fluxo de atualização

```
Cliente envia PUT /product/ID
            |
            v
     @token_required
            |
            | Valida JWT
            v
      UpdateProduct
            |
            | Valida os campos
            v
     MongoDB update_one()
            |
            | Atualiza com $set
            v
      MongoDB find_one()
            |
            | Busca o resultado
            v
      ProductDBModel
            |
            v
      Resposta JSON
```

Para a exclusão, o fluxo é semelhante, mas utiliza `delete_one()` e retorna HTTP 204 quando a operação é concluída com sucesso.

---

### ✅ Resumo

Nesta etapa, completamos o CRUD de produtos, permitindo atualizar e excluir documentos armazenados no MongoDB.

| Conceito | Para que serve |
| --- | --- |
| `UpdateProduct` | Modelo Pydantic para alterações parciais. |
| `Optional[...] = None` | Permite omitir campos durante a atualização. |
| `update_one()` | Atualiza um único documento no MongoDB. |
| `$set` | Altera os campos indicados sem substituir todo o documento. |
| `exclude_unset=True` | Remove da saída os campos não informados. |
| `matched_count` | Informa quantos documentos corresponderam ao filtro. |
| `delete_one()` | Exclui um único documento do MongoDB. |
| `deleted_count` | Informa quantos documentos foram excluídos. |
| `404 Not Found` | Indica que o recurso não foi encontrado. |
| `204 No Content` | Indica sucesso sem corpo de resposta. |
| `@token_required` | Exige autenticação JWT antes de modificar os dados. |

**O que aprendemos:** nossa API agora permite criar, consultar, atualizar e excluir produtos reais no MongoDB.

As operações de criação, atualização e exclusão exigem autenticação JWT, enquanto as consultas continuam públicas.

Com isso, concluímos o ciclo de gerenciamento de produtos e preparamos a aplicação para implementar outras funcionalidades, como o processamento de arquivos de vendas.

---

## 5. Processando upload do CSV de Vendas

## 🎯 Objetivo

Implementar uma funcionalidade de **importação de vendas através de arquivos CSV**, utilizando Flask para receber o arquivo, Pydantic para validar os registros e MongoDB para armazenar as informações.

Nesta etapa, vamos aprender a processar arquivos enviados por requisições HTTP, validar os dados linha por linha, tratar erros e realizar inserções em lote no banco de dados.

## 5.1. Entendendo o processamento de arquivos CSV

O **CSV (Comma-Separated Values)** é um formato de arquivo utilizado para representar dados tabulares, normalmente separados por vírgulas.

É muito utilizado na exportação e importação de informações entre sistemas, planilhas e bancos de dados.

**Exemplo de arquivo `vendas.csv`:**

```
sale_date,product_id,quantity,total_value
2026-10-20,P001,2,199.90
2026-10-21,P002,1,89.50
2026-10-22,P003,3,450.00
```

Nesse exemplo:

- A primeira linha contém os nomes das colunas.
- Cada linha seguinte representa uma venda.
- Os nomes das colunas correspondem aos atributos definidos no nosso modelo `Sale`.

Nosso objetivo é receber esse arquivo através da API, transformar suas linhas em objetos Python, validar os dados e armazená-los na coleção `sales` do MongoDB.

### Fluxo da importação

```
Cliente envia arquivo CSV
           |
           v
      Rota Flask
           |
           v
    Leitura do arquivo
           |
           v
      csv.DictReader
           |
           v
    Validação Pydantic
           |
           v
   MongoDB insert_many()
           |
           v
      Resposta JSON
```

## 5.2. Preparando o endpoint de upload

Vamos implementar a funcionalidade na rota que criamos anteriormente:

```
POST /sales/upload
```

No arquivo `app/routes/main.py`, adicionamos algumas importações:

```
import csv
import os
import io
from app.models.sale import Sale
```

**Entendendo as importações:**

- `csv`: biblioteca padrão do Python para leitura e escrita de arquivos CSV.
- `os`: biblioteca para interagir com recursos do sistema operacional. Foi importada nesta etapa, mas não é utilizada diretamente na função de upload.
- `io`: permite trabalhar com arquivos e fluxos de dados em memória.
- `Sale`: modelo Pydantic responsável por validar as informações de cada venda.

### Protegendo a rota com JWT

Assim como nas operações de criação, atualização e exclusão de produtos, o upload será protegido por autenticação.

```
@main_bp.route('/sales/upload', methods=['POST'])
@token_required
def upload_sales(token):
```

**Como funciona?**

- `methods=['POST']`: permite enviar dados para o servidor.
- `@token_required`: exige um JWT válido antes de executar a função.
- `token`: recebe os dados decodificados do JWT, repassados pelo decorator.

Dessa forma, apenas requisições autenticadas poderão executar a importação.

---

## 5.3. Recebendo e verificando o arquivo

Antes de processar o CSV, precisamos verificar se o cliente realmente enviou um arquivo.

### Verificando a presença do arquivo

```
if 'file' not in request.files:
    return jsonify({
        "error": "Nenhum arquivo foi enviado"
    }), 400
```

**`request.files`**

É uma estrutura disponibilizada pelo Flask que permite acessar arquivos enviados em uma requisição HTTP, normalmente utilizando `multipart/form-data`.

**`'file' not in request.files`**

Verifica se existe um arquivo associado à chave `file`.

Caso não exista, retornamos HTTP `400 Bad Request`.

### Verificando se um arquivo foi selecionado

```
file = request.files['file']

if file.filename == '':
    return jsonify({
        "error": "Nenhum arquivo selecionado"
    }), 400
```

Aqui, recuperamos o arquivo enviado e verificamos se seu nome está vazio.

Isso diferencia duas situações: uma requisição sem o campo `file` e outra que possui o campo, mas não informa um arquivo selecionado.

### Verificando a extensão

```
if file and file.filename.endswith('.csv'):
```

O método `endswith('.csv')` verifica se o nome do arquivo termina com a extensão `.csv`.

Essa é uma verificação inicial, mas não garante que o conteúdo realmente esteja no formato CSV.

> 💡 No código atual, não existe um retorno específico para arquivos com outra extensão. Esse tratamento poderá ser melhorado posteriormente.
> 

---

## 5.4. Lendo e interpretando o conteúdo CSV

Depois de verificar o arquivo, precisamos interpretar seu conteúdo para que o Python consiga trabalhar com os registros.

### Lendo o arquivo em memória

```
csv_stream = io.StringIO(
    file.stream.read().decode('UTF-8'),
    newline=None
)
```

### Entendendo o código

**`file.stream.read()`**

Lê o conteúdo do arquivo enviado pela requisição, retornando seus dados em bytes.

**`.decode('UTF-8')`**

Converte os bytes para texto utilizando a codificação UTF-8.

**`io.StringIO(...)`**

Cria um objeto semelhante a um arquivo de texto, mas armazenado em memória.

Dessa forma, conseguimos utilizar ferramentas que esperam receber um arquivo de texto sem precisar salvar o CSV no disco.

**`newline=None`**

Permite o tratamento universal das quebras de linha presentes no texto.

### Transformando linhas em dicionários

Agora utilizamos:

```
csv_reader = csv.DictReader(csv_stream)
```

O `DictReader` utiliza a primeira linha do CSV como cabeçalho e transforma as demais linhas em dicionários Python.

Por exemplo, esta linha:

```
2026-10-21,P002,1,89.50
```

Será interpretada inicialmente como:

```
{
    "sale_date": "2026-10-21",
    "product_id": "P002",
    "quantity": "1",
    "total_value": "89.50"
}
```

Observe que os valores são recebidos inicialmente como strings.

Posteriormente, o Pydantic será responsável por converter e validar essas informações conforme os tipos declarados no modelo.

📸 **Print:** implementação da leitura do arquivo utilizando `StringIO` e `DictReader`.

---

## 5.5. Validando as vendas com Pydantic

Para garantir que os registros tenham uma estrutura válida, utilizaremos o modelo `Sale`, criado anteriormente.

No arquivo `app/models/sale.py`, temos:

```
from pydantic import BaseModel, ConfigDict
from datetime import date

class Sale(BaseModel):
    sale_date: date
    product_id: str
    quantity: int
    total_value: float

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
```

### Entendendo os campos

| Campo | Tipo | Finalidade |
| --- | --- | --- |
| `sale_date` | `date` | Data em que a venda ocorreu. |
| `product_id` | `str` | Identificador do produto vendido. |
| `quantity` | `int` | Quantidade vendida. |
| `total_value` | `float` | Valor total da venda. |

O Pydantic valida os campos e realiza conversões quando os valores recebidos são compatíveis com os tipos esperados.

Por exemplo, ele pode converter:

- `"2026-10-21"` em um objeto `date`.
- `"2"` em um número inteiro.
- `"199.90"` em um número decimal.

### Configurações do modelo

**`populate_by_name=True`**

Permite preencher os campos utilizando seus nomes. Neste modelo, não definimos aliases, então essa configuração não altera significativamente o comportamento atual.

**`arbitrary_types_allowed=True`**

Permite utilizar tipos arbitrários em modelos Pydantic. Também foi mantida conforme a aula, embora os tipos utilizados em `Sale` não dependam dessa configuração.

---

## 5.6. Processando e validando cada linha

Para armazenar os registros válidos e identificar possíveis problemas, criamos duas listas auxiliares:

```
sales_to_insert = []
errors = []
```

**`sales_to_insert`**

Armazena os documentos que passaram pela validação e serão enviados ao MongoDB.

**`errors`**

Armazena mensagens sobre problemas encontrados durante o processamento.

### Percorrendo os registros

```
for row_num, row in enumerate(csv_reader, 1):
    try:
        sale_data = Sale(**row)
        sales_to_insert.append(sale_data.model_dump())

    except ValidationError as e:
        errors.append(
            f"Linha {row_num}: Dados inválidos - {e.errors()}"
        )

    except Exception as e:
        errors.append(
            f"Linha {row_num}: Erro inesperado ao processar a linha - {str(e)}"
        )
```

### Entendendo cada parte

**`enumerate(csv_reader, 1)`**

Percorre os registros do CSV e atribui um número a cada linha processada, começando em `1`.

Como o cabeçalho já foi consumido pelo `DictReader`, o primeiro registro recebe o número 1, embora esteja na segunda linha física do arquivo.

**`Sale(**row)`**

Cria uma instância do modelo Pydantic a partir do dicionário correspondente à linha atual.

O operador `**` desempacota os campos do dicionário em argumentos nomeados.

**`sale_data.model_dump()`**

Converte o modelo validado em um dicionário Python.

**`sales_to_insert.append(...)`**

Adiciona os dados preparados à lista de documentos que serão inseridos.

### Tratando erros de cada registro

**`except ValidationError as e`**

Captura problemas de validação do Pydantic, como campos ausentes ou valores incompatíveis.

**`except Exception as e`**

Captura outros erros inesperados que possam ocorrer no processamento da linha.

Em vez de interromper toda a importação quando encontra um registro inválido, a função registra o erro e continua para o próximo.

Isso permite aproveitar os registros válidos mesmo quando o arquivo contém algumas informações incorretas.

📸 **Print:** estrutura do `for`, validação pelo modelo `Sale` e tratamento de exceções.

---

## 5.7. Inserindo as vendas no MongoDB

Após percorrer o CSV, teremos uma lista contendo os registros que passaram pela validação.

Agora, precisamos inseri-los no banco de dados.

### Inserção em lote

```
if sales_to_insert:
    try:
        db.sales.insert_many(sales_to_insert)

    except Exception as e:
        return jsonify({
            "error": f"Erro ao inserir dados no banco: {str(e)}"
        }), 500
```

### Entendendo o código

**`if sales_to_insert:`**

Verifica se existem registros válidos para inserir.

Como uma lista vazia é avaliada como falsa pelo Python, a operação somente será executada quando houver documentos preparados.

**`db.sales`**

Acessa a coleção `sales` no MongoDB.

**`insert_many(sales_to_insert)`**

Insere vários documentos em uma única operação de inserção em lote.

Isso evita executar uma chamada individual ao banco para cada venda.

**`except Exception as e`**

Captura problemas durante a operação de inserção e retorna HTTP `500 Internal Server Error`.

### Por que a indentação é importante?

No primeiro commit da aula, a operação `insert_many()` ficou dentro do `for`.

No segundo commit, ela foi movida para fora do laço, corrigindo o fluxo de processamento.

**A sequência correta é:**

1. Percorrer todas as linhas do CSV.
2. Validar os registros e acumular os documentos.
3. Registrar os erros encontrados.
4. Inserir o lote após finalizar a leitura.
5. Retornar o resultado da importação.

> **Atenção ao tipo de data:** no código atual, `Sale.model_dump()` mantém `sale_date` como um objeto `datetime.date`. O PyMongo não consegue armazenar diretamente esse tipo. Portanto, antes da inserção, será necessário converter a data para um tipo compatível com BSON, como `datetime.datetime`, ou optar conscientemente por armazená-la como string ISO.
> 

Para exemplificar uma alternativa que mantém a data como texto, podemos substituir, em uma melhoria futura:

```
sales_to_insert.append(sale_data.model_dump())
```

por:

```
sales_to_insert.append(sale_data.model_dump(mode='json'))
```

Isso gera tipos compatíveis com JSON, incluindo a data como texto no formato `AAAA-MM-DD`.

Essa mudança **não faz parte dos commits desta aula**. O código original foi mantido acima para acompanhar o repositório.

---

## 5.8. Retornando o resultado do upload

Após a tentativa de inserção, nossa API retorna uma resposta JSON com o resultado do processamento:

```
return jsonify({
    "message": "Upload processado com sucesso.",
    "vendas_importadas": len(sales_to_insert),
    "erros_encontrados": errors
}), 200
```

**Entendendo os campos:**

- `message`: informa que a rotina de processamento foi concluída.
- `vendas_importadas`: quantidade de registros que passaram pela validação e foram preparados para inserção.
- `erros_encontrados`: lista contendo os problemas identificados em cada registro.

### Exemplo de resposta

```
{
  "message": "Upload processado com sucesso.",
  "vendas_importadas": 3,
  "erros_encontrados": []
}
```

Esse é um exemplo do formato de resposta esperado após uma inserção bem-sucedida e com o tratamento de data resolvido.

**Importante:** o retorno HTTP 200 também pode ocorrer quando nenhuma linha é válida, pois o código retorna a lista de erros mesmo sem inserir documentos. Além disso, `len(sales_to_insert)` representa a quantidade preparada para inserção, não uma confirmação individual de cada documento persistido.

---

## 5.9. Código completo do endpoint

Após os ajustes do segundo commit, a função `upload_sales()` ficou organizada da seguinte forma:

```
@main_bp.route('/sales/upload', methods=['POST'])
@token_required
def upload_sales(token):
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo foi enviado"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400

    if file and file.filename.endswith('.csv'):
        csv_stream = io.StringIO(
            file.stream.read().decode('UTF-8'),
            newline=None
        )

        csv_reader = csv.DictReader(csv_stream)

        sales_to_insert = []
        errors = []

        for row_num, row in enumerate(csv_reader, 1):
            try:
                sale_data = Sale(**row)
                sales_to_insert.append(sale_data.model_dump())

            except ValidationError as e:
                errors.append(
                    f"Linha {row_num}: Dados inválidos - {e.errors()}"
                )

            except Exception as e:
                errors.append(
                    f"Linha {row_num}: Erro inesperado ao processar a linha - {str(e)}"
                )

        if sales_to_insert:
            try:
                db.sales.insert_many(sales_to_insert)

            except Exception as e:
                return jsonify({
                    "error": f"Erro ao inserir dados no banco: {str(e)}"
                }), 500

        return jsonify({
            "message": "Upload processado com sucesso.",
            "vendas_importadas": len(sales_to_insert),
            "erros_encontrados": errors
        }), 200
```

Nessa implementação, o processamento está concentrado dentro da verificação de extensão `.csv`, conforme o código final do repositório.

📸 **Print:** função `upload_sales()` completa no VS Code.

---

## 5.10. Testando o upload no Postman

Para testar a funcionalidade, iniciamos o servidor Flask:

```
python run.py
```

Como a rota exige autenticação JWT, precisamos obter um token válido através do endpoint `/login`.

### Configurando a requisição

**Endpoint:**

```
POST http://127.0.0.1:5000/sales/upload
```

**Authorization:** selecionar `Bearer Token` e informar o JWT gerado no login.

**Body:** selecionar `form-data`.

No formulário, configuramos:

| Key | Tipo | Value |
| --- | --- | --- |
| `file` | File | Selecionar `vendas.csv` |

O Postman enviará o arquivo utilizando o formato `multipart/form-data`.

Não devemos utilizar `raw JSON` para esse upload, pois a rota espera um arquivo através de `request.files`.

### Testando diferentes situações

| Situação | Resultado |
| --- | --- |
| Arquivo não enviado | HTTP 400 — Nenhum arquivo foi enviado |
| Arquivo não selecionado | HTTP 400 — Nenhum arquivo selecionado |
| Token ausente ou inválido | HTTP 401 |
| Linha com dados inválidos | Erro registrado na lista `erros_encontrados` |
| Arquivo processado sem falha de inserção | HTTP 200 com resumo do processamento |

Na transcrição da aula, o teste terminou com 12 vendas importadas. Para reproduzir esse resultado com o código do repositório, precisamos também resolver a serialização do campo `sale_date` mencionada anteriormente.

Após uma importação bem-sucedida, podemos acessar o MongoDB Compass e verificar os registros na coleção `sales`.

📸 **Print:** configuração de upload no Postman, resposta da API e documentos na coleção `sales` do MongoDB.

---

## 5.11. Entendendo o fluxo completo

A implementação reúne conceitos que estudamos ao longo do curso:

```
Cliente / Postman
        |
        | POST /sales/upload
        | Bearer Token + arquivo CSV
        v
    @token_required
        |
        | Valida o JWT
        v
    request.files
        |
        | Recebe o arquivo
        v
    io.StringIO
        |
        | Interpreta o texto
        v
    csv.DictReader
        |
        | Converte linhas em dicionários
        v
     Modelo Sale
        |
        | Valida cada registro
        v
  sales_to_insert / errors
        |
        | Acumula resultados
        v
  MongoDB insert_many()
        |
        | Insere os documentos válidos
        v
      jsonify()
        |
        v
     Resposta HTTP
```

Esse é um exemplo de processamento de dados provenientes de fontes externas, com autenticação, validação e persistência em banco de dados.

---

### ✅ Resumo

Nesta etapa, implementamos uma rotina de upload e processamento de vendas utilizando arquivos CSV.

| Conceito | Para que serve |
| --- | --- |
| `request.files` | Acessa arquivos enviados em requisições HTTP. |
| `file.filename` | Obtém o nome do arquivo enviado. |
| `endswith('.csv')` | Verifica a extensão do arquivo. |
| `file.stream.read()` | Lê o conteúdo do arquivo em bytes. |
| `decode('UTF-8')` | Converte bytes para texto. |
| `io.StringIO()` | Permite tratar texto como um arquivo em memória. |
| `csv.DictReader()` | Transforma linhas CSV em dicionários. |
| `enumerate()` | Percorre registros com numeração. |
| `Sale(**row)` | Valida os campos de uma venda utilizando Pydantic. |
| `model_dump()` | Converte o modelo em dicionário Python. |
| `ValidationError` | Identifica erros de validação. |
| `insert_many()` | Insere vários documentos no MongoDB em lote. |
| `len()` | Obtém a quantidade de elementos de uma lista. |
| `@token_required` | Protege o upload exigindo autenticação JWT. |

**O que aprendemos:** nossa API passou a possuir um endpoint capaz de receber arquivos CSV, transformar seu conteúdo em registros estruturados, validar cada venda individualmente e preparar os dados para inserção em lote no MongoDB.

Essa funcionalidade demonstra um fluxo comum em sistemas reais: receber informações externas, validar os dados, registrar erros e persistir os registros processados.

Para concluir a implementação com segurança, ainda precisamos ajustar a serialização da data e melhorar algumas validações do arquivo recebido.