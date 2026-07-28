maxDate()
removeNav()
createTable({{data}})

function maxDate() {
    var hoje = new Date();
    var ano = hoje.getFullYear();
    var mes = (hoje.getMonth() + 1).toString().padStart(2, '0'); // Adiciona um zero à esquerda, se necessário
    var dia = hoje.getDate().toString().padStart(2, '0'); // Adiciona um zero à esquerda, se necessário

    var dataFormatada = ano + '-' + mes + '-' + dia;

    document.getElementById('start').max = dataFormatada;
    document.getElementById('final').max = dataFormatada;
}

function createTable(data) {
    var myTable = document.createElement("table"),
    row = myTable.insertRow(), cell;
    var table = data;
    var perrow = 1;

    if (table.length > 1) {
        document.getElementById("setup_tbl").style.display = 'inline-block';
        table.forEach((entry, k) => {
            entry.forEach((info, i) => {
                cell = row.insertCell();
                cell.innerHTML = '<a>' + info + '</a>';
                if (i == 0) {
                    if ({{meta_min}} > entry[2]) {
                        colors = '#61D16A'; // Substitua 'cor-desejada' pela cor que você deseja usar
                    } else {
                        colors = '#E5332E'; // Substitua 'cor-desejada' pela cor que você deseja usar
                    }
                }
                cell.style.width = "15vw";
                cell.style.maxWidth = "15vw";
                cell.style.cursor= "default";
                if (k > 0) {

                    if (i == 0 || i == 1) {
                        var dateInfo = info;
                        var newDate = dateInfo.substring(0, 16).replace(" ", "T");
                        cell.innerHTML = '<input style="width:13vw" type="datetime-local" readonly class="dash_filter" value="' + newDate + '">'
                    }

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

function redefine() {

    var xhr = new XMLHttpRequest();
    // Configura a requisição
    xhr.open('POST', '/dashboards/setup/material?att=1', true);
    xhr.setRequestHeader("Content-type","application/json");

    // Define a função a ser chamada quando a requisição for concluída com sucesso
    xhr.onload = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            data = JSON.parse(xhr.responseText);

            document.getElementById('data0').innerHTML = 'UM SETUP PADRÃ0 DURA ' + data[1][0] + ' MIN'
            document.getElementById('data1').innerHTML = data[1][1] + ' PARADAS DE SETUP REALIZADAS'
            document.getElementById('data2').innerHTML = data[1][2] + ' MINUTOS DE SETUP REALIZADOS'
            document.getElementById('data4').innerHTML = data[1][3]

            createTable(data[0])
        }
    };

    xhr.send(JSON.stringify(["{{ct}}", document.querySelector('#start').value, document.querySelector('#final').value, '{{material}}']));

}
