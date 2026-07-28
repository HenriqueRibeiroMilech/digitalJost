var dados = {{table | tojson}}

if (window.history.replaceState) {
    window.history.replaceState({}, document.title, window.location.href);
}

function config() {

    var myTable = document.createElement("table"),
    row = myTable.insertRow(), cell;
    myTable.id = "myTable"
    myTable.style.padding = "0"
    var filter_form = document.getElementById("filters")
    var perrow = 1;
    dados.forEach((entry, k) => { // criacao e estilização da table

        entry.forEach((info, i) => { // percorre todos os dados
            // I = COLUNA --- K = LINHA
            if (entry[4] != 'nan') {
                if (i == 0 || i == 1 || i == 2) { // i != 7 NAO FUNCIONA

                    var color =  "#163A8A"
                    cell = row.insertCell(); // insere uma nova linha na tabela
                    cell.style.cursor = "default";

                    if (k > 0 && i == 0) { // condicao para todas as colunas 3 depois da primeira linha
                        cell.style.width = "15vw";
                        cell.style.maxWidth = "15vw";
                        cell.style.textDecoration = "underline";
                        cell.style.cursor = "pointer";
                        cell.onclick = function () { // caso o usuario clique, ele é redirecionado para a pagina de edicao da demanda
                            var id = entry[i + 3];
                            var url = '/demandas/detalhes?area=' + {{area | tojson}} + '&projeto=' + id;
                            filter_form.action = url;
                            filter_form.submit();
                        };

                        cell.innerHTML = `<input disabled type="hidden" style="width:12vw;max-width:12vw;color:` + color + `" class="table_input" name="col_` + i + `"/>` + info + `</input>`;
                   } else if (k > 0 && i == 1) {

                        cell.innerHTML = `<textarea onlyRead onclick='this.style.height = "";this.style.height = this.scrollHeight + "px"' style=";width:17vw;max-width:17vw;color:` + color + `" class="table_input" name="col_` + i + `"/>` + info + `</textarea>`;
                        cell.style.width = "20vw";
                        cell.style.maxWidth = "20vw";

                   } else if (k > 0 && i == 2) {
                        cell.innerHTML = info + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;
                        cell.style.width = "10vw";
                        cell.style.maxWidth = "10vw";

                         if (info == 'Atrasado') {
                            cell.style.backgroundColor = "#E28381";
                            cell.style.color = "#900D09"
                            cell.style.fontWeight = "bold";

                         } else if (info == 'Em Andamento') {
                            cell.style.backgroundColor = "#F6E6B2";
                            cell.style.color = "#CA9B00"
                            cell.style.fontWeight = "bold";

                         } else if (info.includes('Concluído')) {
                            cell.style.backgroundColor = "#a6d1a6";
                            cell.style.color = "#228C22";
                            cell.style.fontWeight = "bold";

                         } else if (info.includes('Sem')) {
                            cell.style.backgroundColor = "#163A8A";
                            cell.style.color = "white";
                            cell.style.fontWeight = "bold";
                         }
                   } else { // todas as colunas e linhas que não possuem uma conficao MUITO especifica
                      cell.innerHTML = info + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;

                      if (i == 0) {
                        cell.style.width = "16vw";
                        cell.style.maxWidth = "16vw";
                        cell.title = "Tipo de projeto + número do projeto"

                      } else if (i == 1) {
                        cell.style.width = "21vw";
                        cell.style.maxWidth = "21vw";

                      } else if (i == 2) {
                        cell.style.width = "10.5vw";
                        cell.style.maxWidth = "10.5vw";
                      }
                   }

                   cell.id = "col_" + i + "row_" + k // PASSA UM ID PARA TODAS AS CELL

                }
            }
        });
        var next = k + 1;
        if (next%perrow==0) { row = myTable.insertRow(); }

    });

    document.getElementById("table-container3").appendChild(myTable);
    document.getElementById("main_sidebar").style.width = "0px";

    var datalist = document.getElementById("opcoes");

    for (var i = 0; i < dados.length; i++) {
        var opcao = document.createElement("option");
        opcao.value = dados[i][0];
        datalist.appendChild(opcao);
    }

    var input = document.getElementById("titulo");
    input.setAttribute("list", "opcoes");
}

function projeto() {
    valor = document.getElementById("titulo").value

    for (var i = 0; i < dados.length; i++) {
        if (valor == dados[i][0]) {
            proj = dados[i][3]
        }
    }
    return proj
}

function buscar() {

    proj = projeto()

    document.getElementById("info_titulo").innerHTML = ''
    document.getElementById("info_resp").innerHTML = ''
    document.getElementById("info_entrada").innerHTML = ''
    document.getElementById("info_processo").innerHTML = ''
    document.getElementById("info_prazo").value = ''
    document.getElementById("info_status").innerHTML = ''
    document.getElementById("info_desc").innerHTML = ''

    document.getElementById('campo_status').classList.remove('andamento')
    document.getElementById('campo_status').classList.remove('atrasado')

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/demandas/admin?area=" + {{area | tojson}} + "&proj=" + proj, true);
    xhr.setRequestHeader("Content-type","application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {

            lista = JSON.parse(xhr.response)

            document.getElementById("info_titulo").innerHTML += lista[0]
            document.getElementById("info_resp").innerHTML += lista[1]
            document.getElementById("info_entrada").innerHTML += lista[2]
            document.getElementById("info_processo").innerHTML += lista[3]
            document.getElementById("info_prazo").value = lista[4]
            document.getElementById("info_status").innerHTML += lista[5]
            document.getElementById("info_desc").innerHTML += lista[6]

            if (lista[5] == "Em Andamento") {
                document.getElementById('campo_status').classList.add('andamento')
            } else if (lista[5] == "Atrasado") {
                document.getElementById('campo_status').classList.add('atrasado')
            }

        }
    }
    xhr.send();
}

function alterar() {

    if (document.getElementById("info_titulo").innerText != '' && document.getElementById("info_titulo").innerText != 'Procure uma demanda valida') {

        proj = projeto()
        window.location = "/demandas/admin?area=" + {{area | tojson}} + "&proj=" + proj + "&alt=" + document.getElementById("admin").value;
    } else {
        alert('Pesquise por uma demanda para alterar uma prioridade')
    }

}

function apresentacao() {
    window.location = "/demandas/admin/apresentacao?area=" + {{area | tojson}};
}