function loadPage() { // funcao que carrega a pagina
    // ATENÇÃO: TODAS FUNCOES QUE TIVER UMA PROMISE (CASO DO .THEN) DEVE, SER ASSINCRONAS
    document.getElementById("main_sidebar").style.width = "0px"; // deixa a MAIN_SIDEBAR com tamanho 0
}

var myTable = document.createElement("table"),
row = myTable.insertRow(), cell;
myTable.id = "table_admim"
myTable.style.padding = "0"
var filter_form = document.getElementById("table_form")
var perrow = 1;
{{table | tojson}}.forEach((entry, k) => { // criacao e estilização da table

    entry.forEach((info, i) => { // percorre todos os dados
        // I = COLUNA --- K = LINHA

        if (i == 0 || i == 1 || i == 2 || i == 3 || i == 4 || i == 5) { // i != 7 NAO FUNCIONA

           var color =  "#163A8A"
           cell = row.insertCell(); // insere uma nova linha na tabela
           cell.style.cursor = "default";

           if (k > 0 && i == 3) { // condicao para todas as colunas 0 depois da primeira linha
              if (info == "None") {
                cell.innerHTML = "Não Aplicavel" + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;
              } else {
                cell.innerHTML = info + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;
              }

              cell.style.width = "12vw";
              cell.style.maxWidth = "12vw";

           } else if (k > 0 && i == 0) { // condicao para todas as colunas 3 depois da primeira linha
            cell.style.width = "16vw";
            cell.style.maxWidth = "16vw";
            cell.style.textDecoration = "underline";
            cell.style.cursor = "pointer";
            cell.onclick = function () { // caso o usuario clique, ele é redirecionado para a pagina de edicao da demanda
                var id = entry[i + 6];
                var url = '/demandas/detalhes?area=' + {{area | tojson}} + '&projeto=' + id;
                filter_form.action = url;
                filter_form.submit();
            };

            cell.innerHTML = `<input disabled type="hidden" style="width:12vw;max-width:14vw;color:` + color + `" class="table_input" name="col_` + i + `"/>` + info + `</input>`;


           } else if (k > 0 && i == 1) { // condicao para todas as colunas 6 depois da primeira linha

                cell.innerHTML = `<textarea onlyRead onclick='this.style.height = "";this.style.height = this.scrollHeight + "px"' style=";width:19vw;max-width:19vw;color:` + color + `" class="table_input" name="col_` + i + `"/>` + info + `</textarea>`;
                cell.style.width = "26vw";
                cell.style.maxWidth = "26vw";


           } else if (k > 0 && i == 2) { // condicao para todas as colunas 1 depois da primeira linha
                cell.style.width = "14vw";
                cell.style.maxWidth = "14vw";

                if (info != "None" && info != "") { // condicao se o texto tiver um link
                    teste = {{table | tojson}}[k][i + 5]
                    console.log(teste)
                    if (teste != "None") {
                        cell.style.cursor = "pointer";
                        cell.innerHTML = info.link(teste) + `<input id="entrada" type="hidden" name="col_` + i + `" value="` + info + `"/>`;
                    } else {
                        cell.innerHTML = info + `<input id="entrada" type="hidden" name="col_` + i + `" value="` + info + `"/>`;
                    }

                } else {
                    cell.innerHTML = "Não informado" + `<input id="entrada" type="hidden" name="col_` + i + `" value="` + info + `"/>`;
                }

           } else if (k > 0 && i == 5) {
                cell.innerHTML = info + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;
                cell.style.width = "12vw";
                cell.style.maxWidth = "12vw";

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
           } else if (k > 0 && i == 4) {
                cell.innerHTML = info + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;
                cell.style.width = "14vw";
                cell.style.maxWidth = "14vw";

           } else { // todas as colunas e linhas que não possuem uma conficao MUITO especifica
              cell.innerHTML = info + `<input type="hidden" name="col_` + i + `" value="` + info + `"/>`;

              if (i == 4) {
                cell.style.width = "14.4vw";
                cell.style.maxWidth = "14.4vw";
                cell.title = "Responsável/criador da demanda"

              } else if (i == 2) {
                cell.style.width = "14.6vw";
                cell.style.maxWidth = "14.6vw";
                cell.title = "Origem da demanda"

              } else if (i == 3) {
                cell.style.width = "12.3vw";
                cell.style.maxWidth = "12.3vw";
                cell.title = "Tipo de processo"

              } else if (i == 0) {
                cell.style.width = "16.5vw";
                cell.style.maxWidth = "16.5vw";
                cell.title = "Tipo de projeto + número do projeto"

              } else if (i == 1) {
                cell.style.width = "26.7vw";
                cell.style.maxWidth = "26.7vw";
                cell.textContent = 'DESCRIÇÃO DA DEMANDA';

              } else if (i == 5) {
                cell.style.width = "12vw";
                cell.style.maxWidth = "12vw";
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
