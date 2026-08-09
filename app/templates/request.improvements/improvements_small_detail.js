
var requestData = {{df}}
var imagesData = requestData['images'][0].split('||')
var requestPauseData = {{dfPause}}
var requestType = '{{requestType}}'

fillData()

function fillData() { // funcao que preenche os dados da SSL

    document.getElementById('id_detail').innerHTML += 'DADOS DA DEMANDA Nº ' + requestData['requestId'][0]

    document.getElementById('requester').value += requestData['requesterName'][0]
    document.getElementById('area').value += '{{area}}'
    document.getElementById('openDate').value += requestData['openDate'][0]
    document.getElementById('title').value += requestData['title'][0]
    document.getElementById('demandType').value = getDemandTypeLabel(requestData['demandType'][0])
    document.getElementById('urgency').value += requestData['urgency'][0]
    document.getElementById('info').value = requestData['info'][0]

    if (requestData['demandType'][0] == 'erro') {
        document.getElementById('infoLabel').textContent = 'Descrição completa do problema: '
        document.querySelectorAll('.structured-demand-field').forEach(function(field) {
            field.style.display = 'none'
        })
    } else {
        document.getElementById('assumptions').value = requestData['assumptions'][0] || 'Não informado no registro original'
        document.getElementById('actualProblems').value = requestData['actualProblems'][0] || 'Não informado no registro original'
        document.getElementById('benefits').value = requestData['benefits'][0] || 'Não informado no registro original'
    }

    fillImageTable()

    if (requestData['status'][0] == 0) {
        document.getElementById('status').value = 'EM ANÁLISE'
    } else if (requestData['status'][0] == 1) {
        document.getElementById('status').value = 'EM ANDAMENTO'
    } else if (requestData['status'][0] == 2) {
        document.getElementById('status').value = 'CONCLUÍDA'
    } else if (requestData['status'][0] == 3) {
        document.getElementById('status').value = 'RECUSADA'
    } else if (requestData['status'][0] == 4) {
        document.getElementById('status').value = 'PAUSADA'
    }

    if (requestData['respName'][0] === null) {
        document.getElementById('respName').value += 'indefinido'
    } else {
        document.getElementById('respName').value += requestData['respName'][0]
    }

    if (requestData['startDate'][0] === null) {
        document.getElementById('startDate').value += 'Não Iniciado'
    } else {
        document.getElementById('startDate').value += requestData['startDate'][0]
    }

    if (requestData['deliveryDate'][0] === null) {
        document.getElementById('deliveryDate').value += 'indefinido'
    } else {
        document.getElementById('deliveryDate').value += requestData['deliveryDate'][0]
    }

    if (requestData['reprogs'][0] == '0') {
        document.getElementById('reprogs').value += 'O prazo de conclusão não foi alterado'
    } else {
        document.getElementById('reprogs').value += 'O prazo de conclusão foi alterado ' + requestData['reprogs'][0] + ' vezes'
    }

    if (requestData['deniedText'][0] !== null) {
        document.getElementById('extra').innerHTML +=
                    '<p class="edit_label">Justificativa: </p>' +
                    '<input class="edit_filter" style="width:50vw" readonly type="text" id="deniedText" value="'+ requestData['deniedText'][0] + '"><br>' +
                    '<p class="edit_label">Data da recusa: </p>' +
                    '<input class="edit_filter" style="width:50vw" readonly type="text" id="finalDate" value="'+ requestData['finalDate'][0] + '"><br>'

        document.getElementById('deadline').style.display = 'none';
    } else {
        fillPauseTable()
    }

    if ('{{admin}}' == 'True') {

        document.getElementById('admin').innerHTML = `<p class="lab_subt">TROCA DE STATUS</p>`

        if (requestData['status'][0] == 0) {
            document.getElementById('admin').innerHTML += `
                <button style="margin-left: calc(0.7vh + 0.8vw);width:20vw;background:#ef7b04;height:calc(2vh + 4vw);" class="table_btn" onclick="changeStatus(this.innerHTML, '`+ requestData['requestId'][0] +`')">Iniciar</button>
                <button style="width:20vw;background:rgb(181,12,12);height:calc(2vh + 4vw);" class="table_btn" onclick="changeStatus(this.innerHTML, '`+ requestData['requestId'][0] +`')">Recusar</button><br><br>`

        } else if (requestData['status'][0] == 1) {
            document.getElementById('admin').innerHTML += `
                <button style="margin-left: calc(0.7vh + 0.8vw);width:20vw;background:#ef7b04;height:calc(2vh + 4vw);" class="table_btn" onclick="changeStatus(this.innerHTML, '`+ requestData['requestId'][0] +`')">Pausar</button>
                <button style="width:20vw;background:#163A8A;height:calc(2vh + 4vw);" class="table_btn" onclick="changeStatus(this.innerHTML, '`+ requestData['requestId'][0] +`')">Reprogramar</button>
                <button style="width:20vw;background:#228c22;height:calc(2vh + 4vw);" class="table_btn" onclick="changeStatus(this.innerHTML, '`+ requestData['requestId'][0] +`')">Concluir</button><br><br>`

        } else if (requestData['status'][0] == 2) {
            document.getElementById('admin').innerHTML = ''
            document.getElementById('extra').innerHTML +=
                    '<p class="edit_label">Data de conclusão: </p>' +
                    '<input class="edit_filter" style="width:50vw" readonly type="text" id="finalDate" value="'+ requestData['finalDate'][0] + '"><br>'


        } else if (requestData['status'][0] == 3) {
            document.getElementById('admin').innerHTML = ''

        } else if (requestData['status'][0] == 4) {
            document.getElementById('admin').innerHTML += `
                <button style="margin-left: calc(0.7vh + 0.8vw);width:20vw;background:#163A8A;height:calc(2vh + 4vw);" class="table_btn" onclick="changeStatus(this.innerHTML, '`+ requestData['requestId'][0] +`')">Retomar</button><br><br>`

        }

    }
}

function fillImageTable() { // funcao para preencher as tabelas de documentos
    var myTable = document.createElement("table"),
    row = myTable.insertRow(), cell;
    // cria a table

    cell = row.insertCell();

    cell.innerHTML = 'NOME DOS ARQUIVOS'
    cell.style.width = '65vw';
    cell.style.overflow = 'hidden';
    cell.style.textOverflow = 'ellipsis';

    cell = row.insertCell();

    cell.innerHTML = '';
    cell.style.width = '19vw';
    cell.style.overflow = 'hidden';
    cell.style.textOverflow = 'ellipsis';

    row.style.fontWeight = 'bold';
    row.style.background = '#163A8A';
    row.style.color = 'white';

    row = myTable.insertRow();
    // TODOS OS ITENS ACIMA SÃO RESPONSAVEIS PELA CRIACAO DO CABEÇALHO DA TABLE

    if (imagesData.length !== 0) {  // condicao se existir algum desenho
        for (let k = 0; k < imagesData.length - 1; k++) { // percorre as linhas dos desenhos

            cell = row.insertCell(); // adciona uma cell
            cell.innerHTML = imagesData[k].split('.')[0].toUpperCase();  // adiciona as informacoes na celula

            cell = row.insertCell(); // adciona uma cell
            cell.innerHTML = `<button class="table_btn" onclick="downloadData('` +  imagesData[k] + `','` + requestData['requestId'][0] + `')" style="padding:15px;width:inherit;background-color:#228C22"><i class="fa fa-download"></i> DOWNLOAD <b>` + imagesData[k].split('.')[imagesData[k].split('.').length -1].toUpperCase() + `</b></button>`

            row = myTable.insertRow(); // insere uma linha
        }
    }

    document.getElementById("lab-container").innerHTML = '';
    myTable.lang = "pt-BR";
    myTable.id = "paradas_table";
    document.getElementById("lab-container").appendChild(myTable);
    // adiciona a table na pagina

}

function fillPauseTable() { // funcao para preencher as tabelas de documentos
    var myTable = document.createElement("table"),
    row = myTable.insertRow(), cell;
    // cria a table

    row.style.fontWeight = 'bold';
    row.style.background = '#163A8A';
    row.style.color = 'white';

    // TODOS OS ITENS ACIMA SÃO RESPONSAVEIS PELA CRIACAO DO CABEÇALHO DA TABLE
    if (requestPauseData.length == 1) {
        cell = row.insertCell();
        cell.innerHTML = requestPauseData[0][0]
        cell.style.width = '91.5vw';
        cell.style.overflow = 'hidden';
        cell.style.textOverflow = 'ellipsis';
    } else {
        for (let k = 0; k < requestPauseData.length; k++) { // percorre as linhas dos desenhos

            for (let i = 0; i < requestPauseData[k].length; i++) { // percorre as linhas dos desenhos
                cell = row.insertCell();
                cell.innerHTML = requestPauseData[k][i]

                if (k == 0) {
                    cell.style.width = '20vw';
                    cell.style.overflow = 'hidden';
                    cell.style.textOverflow = 'ellipsis';

                }

                if (i == 2 && requestPauseData[k][i].length < 6) {
                    cell.innerHTML = 'Continua em pausa'
                }

                if (i == 3) {
                    cell.style.width = '31.5vw';
                }


            }
            row = myTable.insertRow(); // insere uma linha
        }
    }

    document.getElementById("lab-container2").innerHTML = '';
    myTable.lang = "pt-BR";
    myTable.id = "paradas_table";
    document.getElementById("lab-container2").appendChild(myTable);
    // adiciona a table na pagina

}


function downloadData(img, id) {
    window.location = "/solicitar/detail/download/image?id=" + id + '&arq=' + img

}

function changeStatus(info, id) {
    if (info == 'Iniciar') {
        window.location = '/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=start&id=' + id;
    } else if (info == 'Recusar') {
        window.location = '/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=decline&id=' + id;
    } else if (info == 'Pausar') {
        window.location = '/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=pause&id=' + id;
    } else if (info == 'Retomar') {
        window.location = '/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=unpause&id=' + id;
    } else if (info == 'Reprogramar') {
        window.location = '/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=reprogram&id=' + id;
    } else if (info == 'Concluir') {
        window.location = '/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=finish&id=' + id;
    }
}

function getDemandTypeLabel(demandType) {
    if (demandType == 'projeto') {
        return 'Projeto'
    } else if (demandType == 'erro') {
        return 'Erro/Defeito em aplicação'
    }

    return 'Melhoria'
}
