var df = {{df}}
var imagens = df['images'][0]

var condicao = "{{admin}}";

function deletar(arq) {
    document.getElementById("lab_form").action = "/demandas/detalhes/apoio?area={{area}}&projeto={{projeto}}&arq=" + arq
    document.getElementById("lab_form").submit()

}

function fillTable() { // funcao para preencher as tabelas de documentos

    document.getElementById("titulo").innerHTML += df['title'][0]
    document.getElementById("responsavel").innerHTML += df['userName'][0]
    document.getElementById("area").innerHTML += '{{area}}'
    document.getElementById("prazo").innerHTML += df['finalDate'][0]
    document.getElementById("status").innerHTML += df['status'][0]
    document.getElementById("descricao").innerHTML += df['description'][0]

    var myTable = document.createElement("table"),
    row = myTable.insertRow(), cell;
    // cria a table

    cell = row.insertCell();

    cell.innerHTML = 'ARQUIVOS'
    cell.style.width = '65vw';
    cell.style.overflow = 'hidden';
    cell.style.textOverflow = 'ellipsis';

    cell = row.insertCell();

    cell.innerHTML = '';
    cell.style.width = '20vw';
    cell.style.overflow = 'hidden';
    cell.style.textOverflow = 'ellipsis';

    if (condicao == "1") {
        cell = row.insertCell();
        cell.style.width = "5vw";
        cell.style.maxWidth = "5vw";
    }

    row.style.fontWeight = 'bold';
    row.style.background = '#163A8A';
    row.style.color = 'white';

    row = myTable.insertRow();
    // TODOS OS ITENS ACIMA SÃO RESPONSAVEIS PELA CRIACAO DO CABEÇALHO DA TABLE

    if (imagens.length !== 0) {  // condicao se existir algum desenho
        for (let k = 0; k < imagens.length; k++) { // percorre as linhas dos desenhos
            for (let i = 0; i < 2; i++) {

                cell = row.insertCell(); // adciona uma cell

                if (i == 0) {  // condicao se for a primeira coluna
                    cell.innerHTML = imagens[k];  // adiciona as informacoes na celula
                } else {
                    cell.innerHTML = `<button class="table_btn" onclick="window.location='/demandas//detalhes/apoio/download?area={{area}}&projeto={{projeto}}&arq=`+ imagens[k]+ `'" style="padding:15px;width:inherit;background-color:#228C22"><i class="fa fa-download"></i> DOWNLOAD <b>` + imagens[k].split('.')[1].toUpperCase() + `</b></button>`
                    // botao de download

                    if (condicao == "1") { // condicao se o usuario tiver administrador, ele poderá deletar o desenho
                        cell = row.insertCell();
                        cell.style.width = "5vw";
                        cell.style.maxWidth = "5vw";
                        cell.innerHTML = `<button class="remove" onclick="deletar('`+ imagens[k]+ `')">&times;</button>`;
                    }
                }
            }

            row = myTable.insertRow(); // insere uma linha
        }
    }

    document.getElementById("lab-container").innerHTML = '';
    myTable.lang = "pt-BR";
    myTable.id = "paradas_table";
    document.getElementById("lab-container").appendChild(myTable);
    // adiciona a table na pagina

    var inputs = document.querySelectorAll(".img_input");  // seleciona todos os elementos de inputs de imagem

    inputs.forEach(function(item) {  // percorre todos os elementos inputs
        item.addEventListener('input', function (e) { // cria uma funcao para cada evento de input que ocorrer
            if (item.files.length > 0) {  // condicao se tiver mais de um arquivo inputado
                document.querySelector("#placehold").textContent = "Alterar arquivos selecionados...";
                document.querySelector("#label").style.display = "block";
                document.querySelector("#lista").style.display = "block";
            } else {
                document.querySelector("#placehold").textContent = "Adicione documentos...";
                document.querySelector("#label_").style.display = "none";
                document.querySelector("#lista").style.display = "none";
            };
            console.log("teste")
            // adiciona uma lista na tela com os arquivos selecionados
            var input = document.querySelector('#input')
            var output = document.querySelector("#lista")
            var children = "";

            for (var i = 0; i < item.files.length; ++i) {
                children += '<li>' + input.files.item(i).name + '</li>';
            }

            output.innerHTML = '<ul>'+children+'</ul>';
        });

    });

    if (condicao == "0") { // condicao se o usuario não tiver permissao de aministrador
       document.getElementById("admin").style.display = 'none'
    }
}

fillTable();