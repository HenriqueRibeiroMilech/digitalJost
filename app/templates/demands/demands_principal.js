function postFilters(proj) {
    var url = 'edit?area=' + {{area | tojson}} + '&projeto=' + proj;
    filter_form.action = url;
    filter_form.submit();
}

function loadPage() { // funcao que carrega a pagina
    document.getElementById("main_sidebar").style.width = "0px"; // deixa a MAIN_SIDEBAR com tamanho 0
    filtroEntradas();

    myFunction(); // chama a funcao dos filtros
}

function filtroEntradas() {

    var entrada = document.getElementById("entrada"); // pega o select com id ENTRADA, para personalizar

    entradasLista = {{entries}}

    for (i in entradasLista) { // para cada entrada, é criada uma opcao no select
        var option = document.createElement("option"),
        text = document.createTextNode(entradasLista[i][0]);
        option.appendChild(text);
        entrada.appendChild(option);
    }

    entrada.innerHTML += '<option value="" selected>Filtrar por ENTRADA</option>'; // cria uma opcao default no select
}

var myTable = document.createElement("table"),
row = myTable.insertRow(), cell;
myTable.id = "myTable"
myTable.style.padding = "0"
var filter_form = document.getElementById("filters")
var perrow = 1;
{{table | tojson}}.forEach((entry, k) => { // criacao e estilização da table

    entry.forEach((info, i) => { // percorre todos os dados
        // I = COLUNA --- K = LINHA

        if (i == 0 || i == 1 || i == 2 || i == 3 || i == 4 || i == 5 || i == 6) { // i != 7 NAO FUNCIONA

           var color =  "#163A8A"
           cell = row.insertCell(); // insere uma nova linha na tabela
           cell.style.cursor = "default";

           if (k > 0 && i == 4) { // condicao para todas as colunas 0 depois da primeira linha
              if (info == "None") {
                cell.innerHTML = "Não Aplicavel" + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;
              } else {
                cell.innerHTML = info + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;
              }

              cell.style.width = "10vw";
              cell.style.maxWidth = "10vw";

           } else if (k > 0 && i == 1) { // condicao para todas as colunas 3 depois da primeira linha
            cell.style.width = "20vw";
            cell.style.maxWidth = "14vw";
            cell.style.textDecoration = "underline";
            cell.style.cursor = "pointer";
            cell.onclick = function () { // caso o usuario clique, ele é redirecionado para a pagina de edicao da demanda
                var id = entry[i + 6];
                var url = 'demandas/detalhes?area=' + {{area | tojson}} + '&projeto=' + id;
                window.location.href = url;
            };

            cell.innerHTML = `<input disabled type="hidden" style="width:12vw;max-width:12vw;color:` + color + `" class="table_input" name="col_` + i + `"/>` + info + `</input>`;


           } else if (k > 0 && i == 2) { // condicao para todas as colunas 6 depois da primeira linha

                cell.innerHTML = `<textarea readOnly onclick='this.style.height = "";this.style.height = this.scrollHeight + "px"' style=";width:19vw;max-width:19vw;color:` + color + `" class="table_input" name="col_` + i + `"/>` + info + `</textarea>`;
                cell.style.width = "24vw";
                cell.style.maxWidth = "24vw";


           } else if (k > 0 && i == 3) { // condicao para todas as colunas 1 depois da primeira linha
                cell.style.width = "12vw";
                cell.style.maxWidth = "12vw";

                if (info != "None" && info != "") { // condicao se o texto tiver um link
                    teste = {{table | tojson}}[k][i + 5]
                    if (teste != "None") {
                        cell.style.cursor = "pointer";
                        cell.innerHTML = info.link(teste) + `<input id="entrada" type="hidden" name="col_` + i + `" value="` + info + `"/>`;
                    } else {
                        cell.innerHTML = info + `<input id="entrada" type="hidden" name="col_` + i + `" value="` + info + `"/>`;
                    }

                } else {
                    cell.innerHTML = "Não informado" + `<input id="entrada" type="hidden" name="col_` + i + `" value="` + info + `"/>`;
                }

           } else if (k > 0 && i == 0) {
                cell.style.width = "10vw";
                cell.style.maxWidth = "10vw";
                cell.textContent = k + "°";
                cell.style.color = "#900D09";
                cell.style.fontWeight = "bold";


           } else if (k > 0 && i == 6) {
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
           } else if (k > 0 && i == 5) {
                cell.innerHTML = info + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;
                cell.style.width = "12vw";
                cell.style.maxWidth = "12vw";

           } else { // todas as colunas e linhas que não possuem uma conficao MUITO especifica
              cell.innerHTML = info + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;

              if (i == 5) {
                cell.style.width = "12.4vw";
                cell.style.maxWidth = "12.4vw";
                cell.title = "Responsável/criador da demanda"

              } else if (i == 3) {
                cell.style.width = "12.6vw";
                cell.style.maxWidth = "12.6vw";
                cell.title = "Origem da demanda"

              } else if (i == 4) {
                cell.style.width = "10.3vw";
                cell.style.maxWidth = "10.3vw";
                cell.title = "Tipo de processo"

              } else if (i == 0) {
                cell.style.width = "10.5vw";
                cell.style.maxWidth = "10.5vw";
                cell.title = "Criticidade em proporção ao prazo estipulado"
                cell.textContent = "PRIORIZAÇÃO"

              } else if (i == 1) {
                cell.style.width = "14.5vw";
                cell.style.maxWidth = "14.5vw";
                cell.title = "Tipo de projeto + número do projeto"

              } else if (i == 2) {
                cell.style.width = "24.7vw";
                cell.style.maxWidth = "24.7vw";
                cell.textContent = 'DESCRIÇÃO DA DEMANDA';

              } else if (i == 6) {
                cell.style.width = "10.5vw";
                cell.style.maxWidth = "10.5vw";
              }
           }

           cell.id = "col_" + i + "row_" + k // PASSA UM ID PARA TODAS AS CELL

        }
    });
    var next = k + 1;
    if (next%perrow==0) { row = myTable.insertRow(); }

});

document.getElementById("table-container").innerHTML = '';
document.getElementById("table-container").appendChild(myTable);

function filterItems(arr, query) {
    return arr.filter((el) => el.toLowerCase().includes(query.toLowerCase()));
}

function myFunction(elemento) { // funcão para filtrar todas as demandas

    var andamento = document.getElementById("andamento");
    andamento.value = "";
    var atrasado = document.getElementById("atrasado");
    atrasado.value = "";
    var concluido = document.getElementById("concluido");
    concluido.value = "";



    if (andamento.checked == true) {
        andamento.value = "Em Andamento";
    }
    if (atrasado.checked == true) {
        atrasado.value = "Atrasado";
    }
    if (concluido.checked == true) {
        concluido.value = "Concluído";
    }

    var input, filter, table, tr, td, i, txtValue, display; // declara as variaveis
    display = []
    table = document.getElementById("myTable");
    tr = table.getElementsByTagName("tr");
    filters = [[1, 'titulo'], [2, 'descricao'], [3, 'entrada'], [4, 'processo'], [5, 'leader'], [6, 'andamento', 'atrasado', 'concluido']] // declara os filtros
    for (i = 0; i < tr.length; i++) { // percore todas as TR
        var line = []
        filters.forEach((item, l) => {
            var id, index

            index = item[0];
            id = item[1];
            lista1= [];


            input = document.getElementById(id);
            filter = input.value.toUpperCase();

            if (i > 0 && (filter != '' || index == 6)) {
                td = tr[i].getElementsByTagName("td")[index];
                if (td) {
                    let txtValue = td.textContent;
                    if (txtValue.toUpperCase().indexOf(filter) > -1) {
                        line.push('yes');

                    } else {
                        line.push('none');
                    }

                    if (index == 6) {

                        id2 = item[2];
                        input2 = document.getElementById(id2);
                        filter2 = input2.value.toUpperCase();

                        id3 = item[3];
                        input3 = document.getElementById(id3);
                        filter3 = input3.value.toUpperCase();
                        filter4 = input3.value.toUpperCase();
                        filter5 = input3.value.toUpperCase();
                        if (filter3 == "CONCLUÍDO") {
                            filter3 = "Concluído - Antecipado";
                            filter4 = "Concluído - No Prazo";
                            filter5 = "Concluído - Com Atraso";
                        }


                        lista = [filter, filter2, filter3, filter4, filter5, "Sem Prazo Definido", "Sem Ações"];
                        lista1 = filterItems(lista, txtValue);
                        if (lista1.length > 0) {
                            line.pop();
                            line.push('yes');
                        } else {
                            line.pop();
                            line.push('none');
                        }

                    }
                }
            } else if (i > 0 && filter == '') {
                line.push("no_filter");
            }
        });
        display.push(line)
    }

    for (k = 1; k < tr.length - 1; k++) {
        if (k > 0) {
            if (display[k].includes("none")) {
                tr[k].style.display = "none";
            } else {
                tr[k].style.display = "";
            }
        }
    }

}

var checkList = document.getElementById('list1');
checkList.getElementsByClassName('anchor')[0].onclick = function(evt) {
  if (checkList.classList.contains('visible'))
    checkList.classList.remove('visible');
  else
    checkList.classList.add('visible');
}

if (window.history.replaceState) {
    window.history.replaceState({}, document.title, window.location.href);
}




