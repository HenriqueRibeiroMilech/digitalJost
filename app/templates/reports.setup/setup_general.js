closeBoxData()
redefine()
limitDate()

function limitDate() {
    var hoje = new Date();
    var ano = hoje.getFullYear();
    var mes = (hoje.getMonth() + 1).toString().padStart(2, '0'); // Adiciona um zero à esquerda, se necessário
    var dia = hoje.getDate().toString().padStart(2, '0'); // Adiciona um zero à esquerda, se necessário

    var dataFormatada = ano + '-' + mes + '-' + dia;

    document.getElementById('start').max = dataFormatada;
    document.getElementById('final').max = dataFormatada;
}

function closeBoxData() {  // funcao para fechar a tela de definição de prazo
    var overlay = document.querySelector('#normal');
    overlay.style.opacity = "0";
    overlay.style.display = "none";
    document.querySelector(".blur_wrap").style.filter = "none";
    document.querySelector(".blur_wrap").style.pointerEvents = "auto";

}

function openBoxData(key) {  // funcao para fechar a tela de definição de prazo
    var overlay = document.querySelector('#normal')
    overlay.style.display = "block";
    overlay.style.opacity = "1";
    document.querySelector(".blur_wrap").style.filter = "blur(8px)";
    document.querySelector(".blur_wrap").style.pointerEvents = "none";

    var xhr = new XMLHttpRequest();
    // Configura a requisição
    xhr.open('POST', '/dashboards/setup/geral?prod=1', true);
    xhr.setRequestHeader("Content-type","application/json");

    // Define a função a ser chamada quando a requisição for concluída com sucesso
    xhr.onload = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            var myTable = document.createElement("table"),
            row = myTable.insertRow(), cell;
            var table = JSON.parse(xhr.responseText);

            var perrow = 1;

            if (table.length > 1) {
                document.getElementById("setup_tbl").style.display = 'inline-block';
                table.forEach((entry, k) => {
                    entry.forEach((info, i) => {
                        cell = row.insertCell();
                        cell.innerHTML = '<a>' + info + '</a>';
                        if (i == 0) {
                            if (entry[i + 1] > entry[i + 3]) {
                                colors = '#61D16A'; // Substitua 'cor-desejada' pela cor que você deseja usar
                            } else {
                                colors = '#E5332E'; // Substitua 'cor-desejada' pela cor que você deseja usar
                            }

                            cell.style.width = "12vw";
                            cell.style.maxWidth = "12vw";
                            cell.style.cursor = 'pointer';
                            if (k > 0) {

                                cell.onclick = function () { // caso o usuario clique, ele é redirecionado para a pagina de edicao da demanda

                                    id = entry[0]

                                    document.getElementById('material').value = id;
                                    document.getElementById('ct').value = key;

                                    document.getElementById('dash_period').submit();

                                };
                            }


                        } else {
                            cell.style.cursor = 'default';
                            cell.style.width = "7vw";
                            cell.style.maxWidth = "7vw";
                        }
                        if (k != 0) {
                            cell.style.backgroundColor = colors
                            cell.style.fontWeight = 'bold'
                            cell.style.color = 'black'
                        }

                    });
                    var next = k + 1;
                    if (next%perrow==0) { row = myTable.insertRow(); }

                });
            }

            document.getElementById("setup_tbl").innerHTML = '';
            myTable.id = "setup_dsp_tbl"
            document.getElementById("setup_tbl").appendChild(myTable);
        }
    };

    xhr.send(JSON.stringify(["%%", document.querySelector('#start').value, document.querySelector('#final').value, key]));
    document.getElementById('WORK_TITLE').innerHTML = key;
}

function changeBorder(clickedButton) {
    if (activeButton) {
    // Restaura a borda do botão anterior
        activeButton.classList.remove('active');

        if (activeButton == clickedButton) {
            var squareContainer = document.getElementById('squareContainer');
            squareContainer.innerHTML = ""
            activeButton = null
            return
        }
    }

    // Define o botão clicado como ativo
    clickedButton.classList.add('active');
    activeButton = clickedButton;

    filterData(clickedButton.value)
}

function filterData(str) {
    var squareContainer = document.getElementById('squareContainer');
    var xhr = new XMLHttpRequest();

    // Configura a requisição
    xhr.open('POST', '/dashboards/setup/geral?ct=1', true);
    xhr.setRequestHeader("Content-type","application/json");

    // Define a função a ser chamada quando a requisição for concluída com sucesso
    xhr.onload = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            squareContainer.innerHTML = ""
            // Converte a resposta JSON
            var data = JSON.parse(xhr.responseText);

            // Adiciona as caixas com base nos dados da resposta
            for (var key in data) {
                if (data.hasOwnProperty(key)) {
                    var box = document.createElement('div');
                    box.className = 'box5';

                    // Define a cor de fundo com base no valor
                    if (data[key] === 0) {
                        box.classList.add('box-green');
                    } else {
                        box.classList.add('box-red');
                    }
                    box.textContent = key

                    // Usando uma função auxiliar para criar um closure
                    function createClickHandler(text) {
                        return function() {
                            openBoxData(text);
                        };
                    }

                    // Atribui a função de clique
                    box.onclick = createClickHandler(key);

                    squareContainer.appendChild(box);
                }
            }
        }
    };

    xhr.send(JSON.stringify([str, document.querySelector('#start').value, document.querySelector('#final').value]));
}

var activeButton = null;
function redefine() {

    var squareContainer = document.getElementById('squareContainer');
    squareContainer.innerHTML = ""
    if (activeButton) {
    // Restaura a borda do botão anterior
        activeButton.classList.remove('active');
        activeButton = null
    }

    var buttonContainer = document.getElementById('principal');
    var buttons = buttonContainer.querySelectorAll('.box4');
    var acum = 0

    var xhr = new XMLHttpRequest();
    // Configura a requisição
    xhr.open('POST', '/dashboards/setup/geral', true);
    xhr.setRequestHeader("Content-type","application/json");

    // Define a função a ser chamada quando a requisição for concluída com sucesso
    xhr.onload = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {

            console.log(xhr.responseText)
            var data = JSON.parse(xhr.responseText);

            var buttonContainer = document.getElementById('principal');
            var buttons = buttonContainer.querySelectorAll('.box4');
            var acum = 0

            filterText(data[1])

            buttons.forEach(button => {

                button.classList.remove('box-green')
                button.classList.remove('box-red')

                if (data[0][acum] == 0) {
                    button.classList.add('box-green');
                } else if (data[0][acum] == 1) {
                    button.classList.add('box-red');
                } else {
                    button.classList.add('box-grey');
                }
                acum++
            });
        }
    };

    xhr.send(JSON.stringify(["%%", document.querySelector('#start').value, document.querySelector('#final').value]));
}

function filterText(data) {
    document.getElementById('data1').innerHTML = data[0] + ' PARADAS DE SETUP REALIZADAS'
    document.getElementById('data2').innerHTML = data[1] + ' MINUTOS DE SETUP REALIZADOS'
    document.getElementById('data4').innerHTML = data[2]
}
