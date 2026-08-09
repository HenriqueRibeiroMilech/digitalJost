var requestType = '{{requestType}}'
var df = JSON.parse({{df | tojson}})
let df_filtered = JSON.parse({{df | tojson}})

configTopNav()
initTable()

function configTopNav() {

    var count = {{counts}}

    if (requestType == 'melhorias') {
        document.getElementById('filters').innerHTML += `
            <p class="sol_status_desc" style="margin-left: calc(1.3vh + 2vw);"><button class="head_btn" onclick="filterData(0)">Em análise:</button> ` + count[0] + `</p>
            <p class="sol_status_desc"><button class="head_btn" onclick="filterData(1)">Em andamento:</button> ` + count[1] + `</p>
            <p class="sol_status_desc"><button class="head_btn" onclick="filterData(2)">Concluídas:</button> ` + count[2] + `</p>
            <p class="sol_status_desc"><button class="head_btn" onclick="filterData(3)">Recusadas:</button> ` + count[3] + `</p>
            <p class="sol_status_desc"><button class="head_btn" onclick="filterData(4)">Pausadas:</button> ` + count[4] + `</p>
            <p class="sol_status_desc"><button class="head_btn" onclick="filterData(5)">Total:</button> ` + count[5] + `</p>`

    } else {
        document.getElementById('filters').innerHTML += `
            <p class="sol_status_desc" style="margin-left: calc(1.3vh + 2vw);"><button class="head_btn" onclick="filterData(0)">Espera Coord:</button> ` + count[0] + `</p>
            <p class="sol_status_desc"><button class="head_btn" onclick="filterData(1)">Espera Área:</button> ` + count[1] + `</p>
            <p class="sol_status_desc"><button class="head_btn" onclick="filterData(2)">Aprovados:</button> ` + count[2] + `</p>
            <p class="sol_status_desc"><button class="head_btn" onclick="filterData(3)">Negados Coord:</button> ` + count[3] + `</p>
            <p class="sol_status_desc"><button class="head_btn" onclick="filterData(4)">Negados Área:</button> ` + count[4] + `</p>
            <p class="sol_status_desc"><button class="head_btn" onclick="filterData(5)">Total:</button> ` + count[5] + `</p>`
    }
}

function initTable() {
    var myTable = document.createElement("table"),
    row = myTable.insertRow(), cell;

    for (let i = 0; i < Object.keys(df).length - 1; i++) {
        cell = row.insertCell();
        cell.innerHTML = Object.keys(df)[i].split('_').join(' ');
        cell.style.width = "14vw";
    }

    row.style.fontWeight = 'bold';
    row.style.background = '#163A8A';
    row.style.color = 'white';

    if (requestType == 'melhorias') {
        myTable = configTableSmall(myTable)
    } else {
        myTable = configTableBig(myTable)
    }

    document.getElementById("table-container3").innerHTML = '';
    myTable.lang = "pt-BR";
    myTable.id = "paradas_table";
    document.getElementById("table-container3").appendChild(myTable);

}

function configTableSmall(table) {
    row = table.insertRow();

    for (let k = 0; k < Object.keys(df_filtered[Object.keys(df_filtered)[0]]).length; k++) {
        for (let i = 0; i < Object.keys(df_filtered).length - 1; i++) {
            cell = row.insertCell();
            cell.innerHTML = df_filtered[Object.keys(df_filtered)[i]][k];

            cell.style.maxWidth = "10vw";

            if (i == 0) {
                cell.style.fontWeight = "bold";
                cell.style.fontStyle = "italic";
                cell.style.maxWidth = "14vw"

            } else if (i == 1) {
                cell.style.maxWidth = "15vw";

            } else if (i == 2) {
                cell.innerHTML = `<textarea readOnly onclick='this.style.height = "";this.style.height = this.scrollHeight + "px"' style=";width:22vw;max-width:22vw" class="table_input"/>` + df_filtered[Object.keys(df_filtered)[i]][k] + `</textarea>`;
                cell.style.minWidth = "24vw";
                cell.style.maxWidth = "24vw";

            } else if (i == 3) {
                if (df_filtered[Object.keys(df_filtered)[i]][k] == 'Média') {
                    cell.innerHTML = 'Média';
                    cell.style.color = 'rgb(228, 202, 0)';
                    cell.style.fontWeight = 'bold';
                } else if (df_filtered[Object.keys(df_filtered)[i]][k] == 'Baixa') {
                    cell.innerHTML = 'Baixa';
                    cell.style.color = 'rgb(88,132,228)'
                    cell.style.fontWeight = 'bold';
                } else if (df_filtered[Object.keys(df_filtered)[i]][k] == 'Nula') {
                    cell.innerHTML = 'Nula';
                    cell.style.color = '#228C22';
                    cell.style.fontWeight = 'bold';
                } else if (df_filtered[Object.keys(df_filtered)[i]][k] == 'Alta') {
                    cell.innerHTML = df_filtered[Object.keys(df_filtered)[i]][k];
                    cell.style.color = 'rgb(198, 15, 15)';
                    cell.style.fontWeight = 'bold';
                }
                cell.style.minWidth = "8vw";
                cell.style.maxWidth = "8vw";

            } else if (i == 4) {
                if (df_filtered[Object.keys(df_filtered)[i]][k] == 'None') {
                    cell.innerHTML = 'Indefinido';
                }

            } else if (i == 6) {
                if ( df_filtered[Object.keys(df_filtered)[i]][k] == '0') {
                    cell.innerHTML = `<p style="color:rgb(228,202,0);width:9vw;text-align:center"><b><i>Em análise</i></b></p>`

                } else if (df_filtered[Object.keys(df_filtered)[i]][k] == '1') {
                    cell.innerHTML = `<p style="color:rgb(88,132,228);width:9vw;text-align:center"><b><i>Em andamento</i></b></p>`

                } else if (df_filtered[Object.keys(df_filtered)[i]][k] == '2') {
                    cell.innerHTML = `<p style="color:#228C22;width:9vw;text-align:center"><b><i>Concluído</i></b></p>`

                } else if (df_filtered[Object.keys(df_filtered)[i]][k] == '3') {
                    cell.innerHTML = `<p style="color:rgb(198, 15, 15);width:9vw;text-align:center"><b><i>Recusado</i></b></p>`

                } else if (df_filtered[Object.keys(df_filtered)[i]][k] == '4') {
                    cell.innerHTML = `<p style="color:#EF7B04;width:9vw;text-align:center"><b><i>Pausado</i></b></p>`
                }

                cell.innerHTML += `<button onclick="acessDetail('`+ df_filtered['idSolicitacao'][k] +`')" style="width:9vw;background:#ef7b04;height:calc(2vh + 3vw);" class="table_btn">Analisar demanda</button><br><br>`
                cell.style.minWidth = "11vw";
                cell.style.maxWidth = "11vw";
            }

        }
        row = table.insertRow();
    }

    return table
}

function configTableBig(table) {
    row = table.insertRow();

    for (let k = 0; k < Object.keys(df_filtered[Object.keys(df_filtered)[0]]).length; k++) {
        for (let i = 0; i < Object.keys(df_filtered).length - 1; i++) {
            cell = row.insertCell();
            cell.innerHTML = df_filtered[Object.keys(df_filtered)[i]][k];

            if (i == 0) {
                cell.style.fontWeight = "bold";
                cell.style.fontStyle = "italic";
                cell.style.maxWidth = "14vw"

            } else if (i == 1 || i == 2 || i == 3) {
                cell.innerHTML = `<textarea readOnly onclick='this.style.height = "";this.style.height = this.scrollHeight + "px"' style=";width:18vw;max-width:18vw" class="table_input"/>` + df_filtered[Object.keys(df_filtered)[i]][k] + `</textarea>`;
                cell.style.minWidth = "20vw";
                cell.style.maxWidth = "20vw";

            } else if (i == 5) {
                if (df_filtered[Object.keys(df_filtered)[i]][k] == '0') {
                    cell.innerHTML = `<p style="color:rgb(228,202,0);width:9vw;text-align:center"><b><i>Espera Coord</i></b></p>`

                } else if (df_filtered[Object.keys(df_filtered)[i]][k] == '1') {
                    cell.innerHTML = `<p style="color:rgb(88,132,228);width:9vw;text-align:center"><b><i>Espera Área</i></b></p>`

                } else if (df_filtered[Object.keys(df_filtered)[i]][k] == '2') {
                    cell.innerHTML = `<p style="color:#228C22;width:9vw;text-align:center"><b><i>Aprovado</i></b></p>`

                } else if (df_filtered[Object.keys(df_filtered)[i]][k] == '3') {
                    cell.innerHTML = `<p style="color:rgb(198, 15, 15);width:9vw;text-align:center"><b><i>Negado Coord</i></b></p>`

                } else if (df_filtered[Object.keys(df_filtered)[i]][k] == '4') {
                    cell.innerHTML = `<p style="color:#EF7B04;width:9vw;text-align:center"><b><i>Negado Área</i></b></p>`
                }

                cell.innerHTML += `<button onclick="acessDetail('`+ df_filtered['idSolicitacao'][k] +`')" style="width:9vw;background:#ef7b04;height:calc(2vh + 3vw);" class="table_btn">Analisar projeto</button><br><br>`
                cell.style.minWidth = "11vw";
                cell.style.maxWidth = "11vw";
            }

        }
        row = table.insertRow();
    }

    return table
}


function filterData(status) {
    status = status.toString();
    // Filtra os dados conforme o status selecionado
    let filtered = {};
    let statusKey = 'STATUS';

    // Obtém o tamanho do array de status corretamente
    let statusLength = Array.isArray(df[statusKey]) ? df[statusKey].length : Object.keys(df[statusKey]).length;
    
    // Cria arrays filtrados para cada coluna
    Object.keys(df).forEach(key => {
        filtered[key] = [];
    });

    for (let i = 0; i < statusLength; i++) {

        if (status == '5' || df[statusKey][i] == status) {
            console.log(df[statusKey][i])
            Object.keys(df).forEach(key => {
                filtered[key].push(df[key][i]);
            });
        }
    }

    df_filtered = filtered;

    initTable();
}

function acessDetail(id) {
    window.location = "/solicitar/detail?area={{area}}&tipo={{requestType}}&id=" + id
}
