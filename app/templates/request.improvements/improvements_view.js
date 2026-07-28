function init() {
    var myTable = document.createElement("table"),
    row = myTable.insertRow(), cell;
    var df = JSON.parse({{df | tojson}})

    for (let i = 0; i < Object.keys(df).length - 1; i++) {
        cell = row.insertCell();
        cell.innerHTML = Object.keys(df)[i]
        cell.style.width = "20vw";
        if (i == 1) {
           cell.style.width = "35vw";
        }
    }

    row.style.fontWeight = 'bold';
    row.style.background = '#163A8A';
    row.style.color = 'white';

    row = myTable.insertRow();

    for (let k = 0; k < Object.keys(df[Object.keys(df)[0]]).length; k++) {
        for (let i = 0; i < Object.keys(df).length - 1; i++) {
            cell = row.insertCell();
            cell.innerHTML = df[Object.keys(df)[i]][k];
            if (i == 0) {
               cell.style.fontWeight = "bold";
               cell.style.fontStyle = "italic";
            }

            if ('{{requestType}}' == 'melhorias') {
                if (df[Object.keys(df)[i]][k] == '0') {
                    cell.innerHTML = 'Em avaliação';
                    cell.style.background = 'rgb(228, 202, 0)';
                    cell.style.color = 'black';
                } else if (df[Object.keys(df)[i]][k] == '1') {
                    cell.innerHTML = 'Em andamento';
                    cell.style.background = 'rgb(88,132,228)';
                    cell.style.color = 'white';
                } else if (df[Object.keys(df)[i]][k] == '2') {
                    cell.innerHTML = 'Concluída';
                    cell.style.background = '#228C22';
                } else if (df[Object.keys(df)[i]][k] == '3') {
                    cell.innerHTML = 'Recusada';
                    cell.style.background = 'rgb(198, 15, 15)';
                } else if (df[Object.keys(df)[i]][k] == '4') {
                    cell.innerHTML = 'Pausada';
                    cell.style.background = 'rgb(228, 202, 0)';
                    cell.style.color = 'black';
                }
            } else {
                if (df[Object.keys(df)[i]][k] == '0') {
                    cell.innerHTML = 'Aguardando aprovação do coordenador';
                    cell.style.background = 'rgb(228, 202, 0)';
                    cell.style.color = 'black';
                } else if (df[Object.keys(df)[i]][k] == '1') {
                    cell.innerHTML = 'Aguardando aprovação da área';
                    cell.style.background = 'rgb(88,132,228)';
                    cell.style.color = 'white';
                } else if (df[Object.keys(df)[i]][k] == '2') {
                    cell.innerHTML = 'Aprovada';
                    cell.style.background = '#228C22';
                } else if (df[Object.keys(df)[i]][k] == '3') {
                    cell.innerHTML = 'Recusada pelo coordenador';
                    cell.style.background = 'rgb(198, 15, 15)';
                } else if (df[Object.keys(df)[i]][k] == '4') {
                    cell.innerHTML = 'Recusada pela área';
                    cell.style.background = 'rgb(198, 15, 15)';
                }
            }

            if (i == 3) {
                cell.innerHTML += `<br><br><button onclick="acessDetail(` + df['requestId'][k] + `)" style="width:9vw;background:#ef7b04;height:calc(2vh + 3vw);" class="table_btn">Visualizar solicitação</button><br>`

            }
            cell.style.width = "20vw";
        }
        row = myTable.insertRow();
    }

    document.getElementById("table-container").innerHTML = '';
    myTable.lang = "pt-BR";
    myTable.id = "paradas_table";
    document.getElementById("table-container").appendChild(myTable);
}

init();

function acessDetail(id) {
    window.location = "/solicitar/detail?area={{area}}&tipo={{requestType}}&id=" + id
}