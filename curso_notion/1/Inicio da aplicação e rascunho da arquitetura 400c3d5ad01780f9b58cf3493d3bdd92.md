# Inicio da aplicação e rascunho da arquitetura

## 🎯 Objetivo

Criar a estrutura inicial de uma API utilizando **Flask**, organizando os arquivos e separando suas responsabilidades.

Nesta etapa, vamos aprender a:

- Configurar o ambiente de desenvolvimento.
- Inicializar uma aplicação Flask.
- Organizar a estrutura de pastas e arquivos.
- Utilizar os padrões **Application Factory** e **Blueprints**.
- Criar rotas e retornar respostas em JSON.
- Executar e testar a API localmente.

---

## 1. Preparando o ambiente de desenvolvimento

### 1.1. Criando o ambiente virtual

O ambiente virtual, também conhecido como `venv`, serve para **isolar as bibliotecas utilizadas pelo projeto** das demais instaladas no computador.

No terminal, dentro da pasta do projeto, execute:

```
python -m venv venv
```

Após a criação, precisamos ativá-lo. No Windows PowerShell:

```
.\venv\Scripts\Activate.ps1
```

Quando ativado, geralmente aparece `(venv)` no início do terminal.

Ou, após criar um arquivo Python, podemos selecionar a `.venv` no VS Code para ativá-la automaticamente no terminal, conforme as imagens: 

![image.png](Inicio%20da%20aplica%C3%A7%C3%A3o%20e%20rascunho%20da%20arquitetura/image.png)

![image.png](Inicio%20da%20aplica%C3%A7%C3%A3o%20e%20rascunho%20da%20arquitetura/image%201.png)

### 1.2. Instalando o Flask

Com o ambiente virtual ativo:

```
python -m pip install Flask
```

O `pip` é o gerenciador de pacotes do Python. Esse comando instala o Flask e suas dependências no ambiente virtual.

**Importante:** a pasta `venv/` normalmente não deve ser enviada ao GitHub, pois cada desenvolvedor pode criar seu próprio ambiente.

---

## 2. Estrutura e arquitetura do projeto

Antes de desenvolver as funcionalidades, precisamos organizar a aplicação para facilitar sua manutenção e crescimento.

### 📁 Estrutura inicial

```
flask_alura/
│
├── app/
│   ├── __init__.py
│   │
│   └── routes/
│       └── main.py
│
└── run.py
```

**Responsabilidade de cada arquivo:**

| Arquivo / Pasta | Responsabilidade |
| --- | --- |
| `app/` | Contém o código principal da aplicação. |
| `__init__.py` | Cria e configura a aplicação Flask. |
| `routes/` | Agrupa os arquivos responsáveis pelas rotas. |
| `main.py` | Define as rotas iniciais da API. |
| `run.py` | Inicializa o servidor de desenvolvimento. |

📸 **Print:** estrutura de pastas do projeto no VS Code.

![image.png](Inicio%20da%20aplica%C3%A7%C3%A3o%20e%20rascunho%20da%20arquitetura/image%202.png)

### 🏗️ Padrões utilizados

Nesta arquitetura, utilizamos dois conceitos importantes:

**Application Factory:** é um padrão em que uma função cria e configura a aplicação. No nosso projeto, essa função se chama `create_app()`.

**Blueprints:** permitem organizar as rotas em grupos, separando funcionalidades sem precisar concentrar tudo em um único arquivo.

Com essa organização, conseguimos manter o código separado, facilitar testes e adicionar novos módulos futuramente.

---

## 3. Criando a aplicação Flask

Para entender a base da aplicação, podemos começar com uma versão simples, utilizando apenas um arquivo:

```
from flask import Flask

app = Flask(__name__)

@app.route('/')
def main():
    return 'Olá, mundo!'

app.run(debug=True)
```

**O que acontece nesse código?**

1. `from flask import Flask`: importa a classe utilizada para criar a aplicação.
2. `app = Flask(__name__)`: cria uma instância do Flask.
3. `@app.route('/')`: associa a URL `/` à função logo abaixo.
4. `def main()`: define a função executada ao acessar essa rota.
5. `return 'Olá, mundo!'`: devolve a resposta ao cliente.
6. `app.run(debug=True)`: inicia o servidor de desenvolvimento com o modo debug ativado.

O `__name__` é uma variável especial do Python que identifica o módulo atual. O Flask utiliza essa informação como referência para localizar recursos da aplicação.

Agora vamos organizar essa aplicação em arquivos separados.

---

## 4. Application Factory — `app/__init__.py`

A Application Factory é o padrão utilizado para centralizar a **criação e configuração da aplicação**.

Em vez de criar a aplicação diretamente em `run.py`, criamos uma função chamada `create_app()`.

### Código do projeto

```
from flask import Flask
from .routes.main import main_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(main_bp)
    return app
```

📸 **Print:** arquivo `app/__init__.py`.

![image.png](Inicio%20da%20aplica%C3%A7%C3%A3o%20e%20rascunho%20da%20arquitetura/image%203.png)

### Entendendo cada parte

**`from flask import Flask`**

Importa a classe principal do Flask, utilizada para criar nossa aplicação.

**`from .routes.main import main_bp`**

Importa o Blueprint `main_bp`, definido no arquivo `app/routes/main.py`.

O ponto antes de `routes` indica uma importação relativa ao pacote atual, que é `app`.

**`def create_app():`**

Define a função responsável por criar a aplicação. É ela que implementa o padrão Application Factory.

**`app = Flask(__name__)`**

Cria a instância da aplicação Flask.

**`app.register_blueprint(main_bp)`**

Registra o Blueprint na aplicação, permitindo que o Flask reconheça as rotas definidas nele.

**`return app`**

Retorna a instância do Flask já configurada.

### 💡 Por que utilizar uma factory?

A principal vantagem é separar a criação da aplicação da execução do servidor.

Isso permite que, futuramente, a função `create_app()` também seja responsável por configurar extensões, banco de dados, autenticação e outras funcionalidades.

Além disso, facilita a criação de instâncias independentes para testes.

---

## 5. Blueprints e rotas — `app/routes/main.py`

Uma **rota** é a combinação de um caminho de URL e um método HTTP que direciona uma requisição para determinada função.

Já um **Blueprint** é um recurso do Flask utilizado para agrupar e organizar essas rotas.

Por exemplo, futuramente poderíamos ter Blueprints separados para produtos, usuários e autenticação.

📸 **Print:** arquivo `app/routes/main.py`.

![image.png](Inicio%20da%20aplica%C3%A7%C3%A3o%20e%20rascunho%20da%20arquitetura/image%204.png)

### 5.1. Criando o Blueprint

No arquivo `app/routes/main.py`:

```
from flask import Blueprint, jsonify

main_bp = Blueprint('main_bp', __name__)
```

**Explicação:**

- `Blueprint`: classe do Flask utilizada para agrupar rotas.
- `jsonify`: função utilizada para criar respostas HTTP em formato JSON.
- `'main_bp'`: nome que identifica o Blueprint dentro do Flask.
- `__name__`: informa o módulo ao qual o Blueprint pertence.

**Importante:** criar o Blueprint não significa executá-lo separadamente. Ele precisa ser registrado na aplicação com `app.register_blueprint()`.

### 5.2. Criando a rota inicial

```
@main_bp.route('/')
def index():
    return jsonify({"message": "Rota inical do app"})
```

**Como funciona?**

O `@main_bp.route('/')` é um *decorator*, recurso do Python que, nesse caso, informa ao Flask que a função `index()` será responsável pelas requisições à rota `/`.

A função `index()` retorna um dicionário convertido em uma resposta JSON através do `jsonify()`.

**Resultado:**

```
{
  "message": "Rota inical do app"
}
```

O Flask também configura o tipo da resposta como `application/json`.

### 5.3. Criando a rota de produtos

```
@main_bp.route('/products')
def get_products():
    return jsonify({
        "message": "Rota de listagem de produtos"
    })
```

Essa rota é executada quando o cliente acessa:

`GET http://127.0.0.1:5000/products`

Observe que não definimos o método HTTP explicitamente.

Isso acontece porque **o Flask utiliza GET por padrão** quando não especificamos `methods`.

Por enquanto, a rota retorna apenas uma mensagem. Nas próximas etapas, poderá retornar uma lista real de produtos.

### 5.4. Criando a rota de login

```
@main_bp.route('/login', methods=['POST'])
def login():
    return jsonify({
        "message": "Rota de listagem de produtos"
    })
```

Diferentemente das rotas anteriores, aqui utilizamos:

`methods=['POST']`

Isso indica que a função aceita requisições HTTP do tipo POST.

**Diferença principal:**

- **GET:** utilizado normalmente para consultar informações.
- **POST:** utilizado normalmente para enviar dados ao servidor, como informações de login ou criação de registros.

Ao tentar acessar `/login` diretamente pela barra de endereços do navegador, o Flask retorna o erro **405 — Method Not Allowed**, porque o navegador faz uma requisição GET, enquanto a rota aceita POST.

> Neste momento, a rota de login ainda não realiza autenticação. Ela apenas simula um endpoint POST, e sua mensagem de retorno ainda é provisória.
> 

---

## 6. Executando a aplicação — `run.py`

O arquivo `run.py` é o ponto de entrada utilizado para iniciar a aplicação durante o desenvolvimento.

### Código do projeto

```
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
```

📸 **Print:** arquivo `run.py`.

![image.png](Inicio%20da%20aplica%C3%A7%C3%A3o%20e%20rascunho%20da%20arquitetura/image%205.png)

### Entendendo cada linha

**`from app import create_app`**

Importa a função responsável por criar a aplicação, definida em `app/__init__.py`.

**`app = create_app()`**

Executa a factory e recebe a instância do Flask configurada com os Blueprints.

**`if __name__ == '__main__':`**

Verifica se o arquivo está sendo executado diretamente.

Assim, o servidor de desenvolvimento só será iniciado por esse bloco quando executarmos `run.py` como programa principal.

**`app.run(debug=True)`**

Inicia o servidor de desenvolvimento do Flask.

O parâmetro `debug=True` habilita recursos úteis, como a recarga automática após alterações no código e informações detalhadas de erros.

**Atenção:** o modo debug deve ser utilizado somente em desenvolvimento, nunca em produção.

### Iniciando o servidor

No terminal, execute:

```
python run.py
```

Por padrão, a aplicação estará disponível em:

`http://127.0.0.1:5000`

O endereço `127.0.0.1` representa o próprio computador (*localhost*), e `5000` é a porta padrão utilizada pelo Flask durante o desenvolvimento.

---

## 7. Como a arquitetura funciona na prática?

Agora que entendemos cada arquivo, podemos visualizar como eles trabalham juntos.

### Inicialização da aplicação

```
python run.py
      |
      v
    run.py
      |
      | Chama create_app()
      v
app/__init__.py
      |
      | Cria o Flask
      | Registra main_bp
      v
app/routes/main.py
      |
      | Disponibiliza as rotas
      v
Aplicação pronta para receber requisições
```

### Fluxo de uma requisição

Imagine que um cliente faça:

`GET /products`

```
Cliente / Navegador
         |
         | GET /products
         v
    Aplicação Flask
         |
         | Localiza a rota registrada
         v
     main_bp
         |
         | Executa get_products()
         v
      jsonify()
         |
         | Resposta HTTP + JSON
         v
       Cliente
```

**Em resumo:** o `run.py` inicia o servidor, o `create_app()` monta a aplicação, o Blueprint organiza as rotas, e a função associada à rota gera a resposta.

Esse é o fluxo básico que utilizaremos durante o desenvolvimento da API.

---

## 8. Testando as rotas

Com o servidor em execução, podemos testar os endpoints.

| Método | Endpoint | Resultado esperado |
| --- | --- | --- |
| GET | `/` | Retorna a mensagem inicial em JSON. |
| GET | `/products` | Retorna a mensagem de listagem de produtos. |
| POST | `/login` | Retorna a mensagem provisória do login. |
| GET | `/login` | Retorna erro HTTP 405. |

Para testar as rotas GET, basta abrir o navegador.

Já para testar o POST, podemos utilizar ferramentas como Postman, Insomnia ou o próprio terminal.

No Windows PowerShell, por exemplo:

```
curl.exe -X POST http://127.0.0.1:5000/login
```

Esse comando envia uma requisição POST para o endpoint `/login`.

**Lembrete:** uma API não precisa de páginas HTML para funcionar. Ela pode disponibilizar endpoints que retornam dados para outros sistemas, aplicações web ou aplicativos móveis.

---

## 9. Resumo rápido para consulta

| Conceito | Para que serve |
| --- | --- |
| `Flask` | Classe utilizada para criar a aplicação. |
| `__name__` | Identifica o módulo Python atual. |
| `create_app()` | Cria e configura a aplicação Flask. |
| `Blueprint` | Agrupa rotas por funcionalidade. |
| `@route()` | Associa um endpoint a uma função. |
| `register_blueprint()` | Registra as rotas de um Blueprint na aplicação. |
| `jsonify()` | Cria uma resposta HTTP em JSON. |
| `methods=['POST']` | Restringe a rota ao método POST. |
| `app.run()` | Inicia o servidor de desenvolvimento. |
| `debug=True` | Ativa recursos de depuração durante o desenvolvimento. |

### Comandos essenciais

**Criar ambiente virtual:**

```
python -m venv venv
```

**Ativar no PowerShell:**

```
.\venv\Scripts\Activate.ps1
```

**Instalar Flask:**

```
python -m pip install Flask
```

**Executar aplicação:**

```
python run.py
```