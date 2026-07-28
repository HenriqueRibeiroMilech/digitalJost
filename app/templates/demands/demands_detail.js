var myTable = document.createElement("table"),
row = myTable.insertRow(), cell;
myTable.id = "myTable"
myTable.style.padding = "0"
var filter_form = document.getElementById("filters")
var perrow = 1;
{{table | tojson}}.forEach((entry, k) => {

    entry.forEach((info, i) => {

        if (i != 9) {

            cell = row.insertCell()
            cell.style.cursor = "default";

            if (k > 0) {
                if (i == 0 || i == 6) {
                    cell.innerHTML = `<textarea readonly onclick='this.style.height = "";this.style.height = this.scrollHeight + "px"' style="width:10vw" class="table_input" name="col_` + i + `">` + info + `</textarea>`;
                    cell.style.width = "13vw";
                    cell.style.maxWidth = "13vw";

                } else if (i == 1) {
                    cell.innerHTML = info + `<input readonly type="hidden" style="width:7vw;" id="date_` + k + `_` + i + `" class="table_input" name="col_` + i + `" value="` + info + `"/>`;
                    cell.style.width = "10vw";
                    cell.style.maxWidth = "10vw";
                } else if (i == 2) {
                    cell.innerHTML = info + `<input readonly type="hidden" style="width:7vw;" id="date_` + k + `_` + i + `" class="table_input" name="col_` + i + `" value="` + info + `"/>`;
                    cell.style.width = "11vw";
                    cell.style.maxWidth = "11vw";
                } else if (i == 3) {
                    cell.innerHTML = `<input readonly type="date" style="width:8vw;" id="date_` + k + `_` + i + `" class="table_input" name="col_` + i + `" value="` + info + `"/>`;
                    cell.style.width = "8vw";
                    cell.style.maxWidth = "8vw";
                } else if (i == 5) {
                    cell.style.width = "8vw";
                    cell.style.maxWidth = "8vw";

                    if (info != '') {
                        cell.innerHTML = `<input readonly type="date" style="width:8vw;" id="date_` + k + `_` + i + `" class="table_input" name="col_` + i + `" value="` + info + `"/>`;
                    } else {
                        cell.innerHTML = 'Não informado';
                    }

                } else if (i == 4) {
                    cell.innerHTML = `<input readonly type="date" style="width:8vw;" id="date_` + k + `_` + i + `" class="table_input" name="col_` + i + `" value="` + info + `"/>`;
                    cell.style.width = "8vw";
                    cell.style.maxWidth = "8vw";
                    if (entry[i + 5] != "None") {
                        cell.innerHTML = `<input readonly type="date" style="width:8vw;font-weight:bold" id="date_` + k + `_` + i + `" class="table_input" name="col_` + i + `" value="` + info + `"/>`;
                        var lista = entry[i + 5].split(",").join('\n')
                        cell.title = "Este prazo não é o original,\nveja os prazos anteriores:\n\n" + lista
                    }


                } else if (i == 7) {
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
                    }

                    cell = row.insertCell();
                    cell.style.width = "7vw";
                    cell.style.maxWidth = "7vw";

                    if("True" == '{{admin}}') {
                        cell.innerHTML = `<button type='button' class="edit_btn" onclick="window.location='/demandas/tarefa/gerenciar?area={{area}}&projeto={{idproj}}&id=` + entry[i + 1] + `'">EDITAR</button>`;
                    }
                }
            } else {
                cell.innerHTML = info;
                if (i == 0) {
                    cell.style.width = "14vw";
                    cell.style.maxWidth = "14vw";
                } else if (i == 1) {
                    cell.style.width = "12.3vw";
                    cell.style.maxWidth = "12.3vw";
                } else if (i == 2) {
                    cell.style.width = "11vw";
                    cell.style.maxWidth = "11vw";
                } else if (i == 3) {
                    cell.innerHTML = info + `<a onclick="filtrar(this)" class='triangulo'> &#9650;</a>`;
                    cell.style.width = "9vw";
                    cell.style.maxWidth = "9vw";
                } else if (i == 4) {
                    cell.innerHTML = info + `<a onclick="filtrar(this)" class='triangulo'> &#9650;</a>`;
                    cell.style.width = "9vw";
                    cell.style.maxWidth = "9vw";
                } else if (i == 5) {
                    cell.style.width = "9.7vw";
                    cell.style.maxWidth = "9.7vw";
                } else if (i == 6) {
                    cell.style.width = "13vw";
                    cell.style.maxWidth = "13vw";
                } else if (i == 7) {
                    cell.style.width = "13.3vw";
                    cell.style.maxWidth = "13.3w";

                    cell = row.insertCell();
                    cell.style.width = "7vw";
                    cell.style.maxWidth = "7vw";
                }
            }

            if (i == 8) {
                cell.innerHTML = info + `<input type="hidden" name="col_` + i + `" onclick='' value="` + info + `"/>`;
                cell.classList.add('apagar')
            }
        }

    });
    var next = k + 1;
    if (next%perrow==0) { row = myTable.insertRow(); }
});

if ("False" == "{{admin}}") {

    var campos_input = document.querySelectorAll('input');
    campos_input.forEach(input => {
        input.setAttribute('readonly', 'true');
    });

    var campos_text = document.querySelectorAll('textarea');
    campos_text.forEach(textarea => {
        textarea.setAttribute('readonly', 'true');
    });
    document.getElementById("table-container2").style.transform="translate(0, 0)";
} else {
    botoes = document.querySelector('p.select_desc#desc_add');
    botoes.innerHTML += `
            <button class="add_btn" style="margin-top:1vh" onclick="window.location='/demandas/tarefa/criar?area={{area}}&projeto={{idproj}}'">Adicionar nova Tarefa</button>`


    botoes = document.getElementById('div-direita');
    botoes.innerHTML += `
            <button class="add_btn" style="float:right;" onclick="deletar()">Deletar Demanda</button>
            <br><button class="add_btn" type='button' style="float:right;margin-top:1vh" onclick="concluir()" id='botao_status'>Concluir Demanda</button>
            <br><button class="add_btn" style='float:right;margin-top:1vh' onclick="window.location='/demandas/gerenciar?area={{area}}&projeto={{idproj}}'">Gerenciar Propriedades</button>

            <div style='display:none'> <form action="/demandas/detalhes?area={{area}}&projeto={{idproj}}&conc=1" id='form_status' method="post"> <button id='final'type='submit'></button></form>`
    if ('{{status}}' == 'Concluído') {
        document.getElementById('botao_status').textContent = 'Retomar Demanda'
        document.getElementById('form_status').action = '/demandas/detalhes?area={{area}}&projeto={{idproj}}&conc=2'
    }
    document.getElementById("table-container2").style.transform="translate(0, -20%)";
}

if (window.history.replaceState) {
    window.history.replaceState({}, document.title, window.location.href);
}

document.getElementById("table-container2").innerHTML = '';
document.getElementById("table-container2").appendChild(myTable);

function initialStatus() {
    document.getElementById("main_sidebar").style.width = "0px";
    document.getElementById("app_sidebar").style.width = "0px";
    document.getElementById("dem_sidebar").style.width = "0px";
    document.getElementById("sol_sidebar").style.width = "0px";
    document.getElementById("op_sidebar").style.width = "0px";

    document.getElementById("prod").style.fontWeight = "bold";
    if ('{{grades}}' == '5') {
        document.getElementById("prod").style.backgroundColor = "rgba(226, 131, 129, 0.3)";
        document.getElementById("prod").style.color = "#900D09"
        document.getElementById("prod").innerHTML += 'Impacto Alto'
    } else if ('{{grades}}' == '3') {
        document.getElementById("prod").style.backgroundColor = "rgba(246, 230, 178, 0.3)";
        document.getElementById("prod").style.color = "#CA9B00"
        document.getElementById("prod").innerHTML += 'Impacto Médio'
    } else if ('{{grades}}' == '1') {
        document.getElementById("prod").style.backgroundColor = "rgba(166, 209, 166, 0.3)";
        document.getElementById("prod").style.color = "#228C22"
        document.getElementById("prod").innerHTML += 'Impacto Baixo'
    } else if ('{{grades}}' == 'Não Aplicavel') {
        document.getElementById("prod").innerHTML += 'Não Aplicavel'

    } else {
        document.getElementById("prod").innerHTML = 'Inicio da Demanda: {{grades}}'
    }
}

function downloadFile() {
   window.location = "/demandas/detalhes/download?area=" + {{area | tojson}} + "&projeto=" + {{idproj | tojson}};
}

function deletar() { // funcao para remover uma demanda
    var test = confirm('Toda as informações da demanda serão deletadas');
    if (test) { // caso o usuario confirme, será chamado a API para fazer o trabalho de deletar toda a demanda
        var http = new XMLHttpRequest();
        http.open("POST", "/demandas/detalhes?area=" + {{area | tojson}} + "&index=" + 0 + "&projeto=" + {{idproj | tojson}} + "&remove=1"  , false);
        http.setRequestHeader("Content-type","application/x-www-form-urlencoded");
        http.send()
        window.location='/demandas?area={{area}}';
    }
}

var direcao = true;
var botao_prazo = true;
var botao_data = true;

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

function concluir() {

    var test = confirm('Você tem certeza que deseja concluir a demanda?\nOBS: esta ação é reversivel');
    if (test) { // caso o usuario confirme, será chamado a API para fazer o trabalho de deletar toda a demanda
        document.getElementById("final").click();
    }
}

function submitFilters() {
    var filters = document.getElementById("filters")
    var url = '/demandas?area=' + {{area | tojson}}
    filters.action = url
    filters.submit()
}
