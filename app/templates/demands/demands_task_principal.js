function postFilters(proj) {
    var url = 'detalhes?area=' + {{area | tojson}} + '&projeto=' + proj;
    filter_form.action = url;
    filter_form.submit();
}

function loadPage() { // funcao que carrega a pagina
    // ATENÇÃO: TODAS FUNCOES QUE TIVER UMA PROMISE (CASO DO .THEN) DEVE, SER ASSINCRONAS
    document.getElementById("main_sidebar").style.width = "0px"; // deixa a MAIN_SIDEBAR com tamanho 0

    myFunction(); // chama a funcao dos filtros
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
                if (info != "None" && info != "") { // condicao se o texto tiver um link
                cell.innerHTML = `<input readonly type="date" style="width:8vw" id="date_` + k + `_` + i + `" class="table_input" name="col_` + i + `" value="` + info + `"/>`;
                } else {
                    cell.innerHTML = "Não Informado" + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;
                }

                cell.style.width = "10vw";
                cell.style.maxWidth = "10vw";

            } else if (k > 0 && i == 0) { // condicao para todas as colunas 3 depois da primeira linha
                cell.style.width = "14vw";
                cell.style.maxWidth = "14vw";
                cell.style.textDecoration = "underline";
                cell.style.cursor = "pointer";
                cell.onclick = function () { // caso o usuario clique, ele é redirecionado para a pagina de edicao da demanda
                    var id = entry[i + 7];
                    var url = 'detalhes?area=' + {{area | tojson}} + '&projeto=' + id;
                    filter_form.action = url;
                    filter_form.submit();
                };

                cell.innerHTML = `<input disabled type="hidden" style="width:12vw;max-width:12vw;color:` + color + `" class="table_input" name="col_` + i + `"/>` + info + `</input>`;

           } else if (k > 0 && i == 5) { // condicao para todas as colunas 6 depois da primeira linha

                cell.innerHTML = `<textarea disabled onclick='this.style.height = "";this.style.height = this.scrollHeight + "px"' style=";width:13vw;max-width:13vw;color:` + color + `" class="table_input" name="col_` + i + `"/>` + info + `</textarea>`;
                cell.style.width = "17vw";
                cell.style.maxWidth = "17vw";

           } else if (k > 0 && i == 3) { // condicao para todas as colunas 1 depois da primeira linha
                cell.style.width = "12vw";
                cell.style.maxWidth = "12vw";
                cell.innerHTML = `<input readonly type="date" style="width:8vw" id="date_` + k + `_` + i + `" class="table_input" name="col_` + i + `" value="` + info + `"/>`;

                if (entry[i + 5] != "None") {
                        cell.innerHTML = `<input readonly type="date" style="width:8vw;font-weight:bold" id="date_` + k + `_` + i + `" class="table_input" name="col_` + i + `" value="` + info + `"/>`;
                        var lista = entry[i + 5].split(",").join('\n')
                        cell.title = "Este prazo não é o original,\nveja os prazos anteriores:\n\n" + lista
                }

           } else if (k > 0 && i == 1) {
                cell.innerHTML = `<textarea disabled onclick='this.style.height = "";this.style.height = this.scrollHeight + "px"' style=";width:13vw;max-width:13vw;color:` + color + `" class="table_input" name="col_` + i + `"/>` + info + `</textarea>`;
                cell.style.width = "17vw";
                cell.style.maxWidth = "17vw";

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

           } else { // todas as colunas e linhas que não possuem uma conficao MUITO especifica
              cell.innerHTML = info + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;

              if (i == 2) {
                cell.style.width = "12.5vw";
                cell.style.maxWidth = "12.5vw";

              } else if (i == 3) {
                cell.style.width = "11vw";
                cell.style.maxWidth = "11vw";
                cell.innerHTML = info + `<a onclick="filtrar(this)" class='triangulo'> &#9650;</a>`;

              } else if (i == 4) {
                cell.style.width = "13.5vw";
                cell.style.maxWidth = "13.5vw";
                cell.innerHTML = info + `<a onclick="filtrar(this)" class='triangulo'> &#9650;</a>`;

              } else if (i == 1) {
                cell.style.width = "17.65vw";
                cell.style.maxWidth = "17.65vw";

              } else if (i == 0) {
                cell.style.width = "14.55vw";
                cell.style.maxWidth = "14.55vw";

              } else if (i == 5) {
                cell.style.width = "16.3vw";
                cell.style.maxWidth = "16.3vw";

              } else if (i == 6) {
                cell.style.width = "10vw";
                cell.style.maxWidth = "10vw";
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

function myFunction() { // funcão para filtrar todas as demandas

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
    filters = [[0, 'titulo'], [1, 'tarefa'], [2, 'responsavel'], [6, 'andamento', 'atrasado', 'concluido']] // declara os filtros
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

var direcao = true;
var botao_prazo = true;
var botao_data = true;

var datalist = document.getElementById("opcoes");

var pessoas = {{resp}};
for (var i = 0; i < pessoas.length; i++) {
    var opcao = document.createElement("option");
    opcao.value = pessoas[i];
    datalist.appendChild(opcao);
}

function filtrar(elemento){

    var td = elemento.closest('td'); // Encontrar o elemento <td> pai do link
    var tr = td.parentNode; // Encontrar o elemento <tr> pai da célula
    var index = Array.from(tr.cells).indexOf(td);

    var table, rows, condicao, i, x, y, verifica;
    table = document.getElementById("myTable");
    condicao = true;

    if (elemento.innerHTML == " ▲") {
        elemento.innerHTML = " ▼";
        direcao = true;
    } else {
        elemento.innerHTML = " ▲";
        direcao = false;
    }

    while (condicao) {
        condicao = false;
        rows = table.rows;
        for (i = 1; i < (rows.length - 1); i++) {
            verifica = false;
            var cellX = rows[i].getElementsByTagName("TD")[index];
            var cellY = rows[i + 1].getElementsByTagName("TD")[index];
            if (cellX && cellY) {
                x = cellX.children[0].value;
                y = cellY.children[0].value;
                if (direcao) {
                    if (Date.parse(x) > Date.parse(y)) {
                        verifica = true;
                        break;
                    }
                } else {
                    if (Date.parse(x) < Date.parse(y)) {
                        verifica = true;
                        break;
                    }
                }
            }
        }
        if (verifica) {
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            condicao = true;
        }
    }
}
