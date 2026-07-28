
var requestData = {{df}}
var requestType = '{{requestType}}'

fillData()

function fillData() { // funcao que preenche os dados da SSL

    document.getElementById('id_detail').innerHTML += 'DADOS DO PROJETO Nº ' + requestData['requestId'][0]

    document.getElementById('requester').value += requestData['requesterName'][0]
    document.getElementById('area').value += '{{area}}'
    document.getElementById('openDate').value += requestData['openDate'][0]
    document.getElementById('title').value += requestData['title'][0]
    document.getElementById('objective').innerHTML += requestData['objective'][0]
    document.getElementById('info').innerHTML += requestData['info'][0]
    document.getElementById('actualProblems').innerHTML += requestData['actualProblems'][0]
    document.getElementById('benefits').innerHTML += requestData['benefits'][0]
    document.getElementById('budget').value += requestData['budget'][0]
    document.getElementById('clientExpectDate').value += requestData['clientExpectDate'][0]

    if (requestData['status'][0] == 0) {
        document.getElementById('status').value = 'AGUARDANDO APROVAÇÃO DO GESTOR'
    } else if (requestData['status'][0] == 1) {
        document.getElementById('status').value = 'AGUARDANDO APROVAÇÃO DA ÁREA REQUISITADA'
    } else if (requestData['status'][0] == 2) {
        document.getElementById('status').value = 'APROVADO'
    } else if (requestData['status'][0] == 3) {
        document.getElementById('status').value = 'RECUSADO PELO GESTOR APROVADOR'
    } else if (requestData['status'][0] == 4) {
        document.getElementById('status').value = 'RECUSADO PELA ÁREA REQUISITADA'
    }

    document.getElementById('bossName').value += requestData['bossName'][0]

    if (requestData['status'][0] == 2) {
        document.getElementById('admin').innerHTML =
            '<p class="edit_label">Responsável área: </p>' +
            '<input class="edit_filter" style="width:50vw" readonly type="text" id="finalDate" value="'+ requestData['approverAreaName'][0] + '"><br>' +
            '<p class="edit_label">Data de aprovação: </p>' +
            '<input class="edit_filter" style="width:50vw" readonly type="text" id="finalDate" value="'+ requestData['finalDate'][0] + '"><br>'
    } else if (requestData['status'][0] == 3 || requestData['status'][0] == 4) {
            document.getElementById('admin').innerHTML =
                    '<p class="edit_label">Data de recusa: </p>' +
                    '<input class="edit_filter" style="width:50vw" readonly type="text" id="finalDate" value="'+ requestData['finalDate'][0] + '"><br>'
    }

    if ('{{admin}}' == 'True') {

        document.getElementById('admin').innerHTML = `<p class="lab_subt">TROCA DE STATUS</p>`

        if (requestData['status'][0] == 0) {
            document.getElementById('admin').innerHTML += `
                <button style="margin-left: calc(0.7vh + 0.8vw);width:20vw;background:#ef7b04;height:calc(2vh + 4vw);" class="table_btn" onclick="changeStatus(this.innerHTML, '`+ requestData['requestId'][0] +`')">Aprovar solicitação</button>
                <button style="width:20vw;background:rgb(181,12,12);height:calc(2vh + 4vw);" class="table_btn" onclick="changeStatus(this.innerHTML, '`+ requestData['requestId'][0] +`')">Recusar solicitação</button><br><br>`

        } else if (requestData['status'][0] == 1) {
            document.getElementById('admin').innerHTML += `
                <button style="margin-left: calc(0.7vh + 0.8vw);width:20vw;background:#ef7b04;height:calc(2vh + 4vw);" class="table_btn" onclick="changeStatus(this.innerHTML, '`+ requestData['requestId'][0] +`')">Aprovar desenvolvimento</button>
                <button style="width:20vw;background:rgb(181,12,12);height:calc(2vh + 4vw);" class="table_btn" onclick="changeStatus(this.innerHTML, '`+ requestData['requestId'][0] +`')">Recusar desenvolvimento</button><br><br>`
        }
    }
}

function changeStatus(info, id) {
    if (info == 'Aprovar solicitação') {
        window.location = '/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=approveBoss&id=' + id;
    } else if (info == 'Recusar solicitação') {
        window.location = '/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=deniedBoss&id=' + id;
    } else if (info == 'Aprovar desenvolvimento') {
        window.location = '/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=approveArea&id=' + id;
    } else if (info == 'Recusar desenvolvimento') {
        window.location = '/solicitar/manage/def?area={{area}}&tipo={{requestType}}&cmd=deniedArea&id=' + id;
    }
}

var intervalFunc;

function changeHeight(text1, text2) {
    intervalFunc = setInterval(function() {
        document.getElementById(text2).style.height = document.getElementById(text1).offsetHeight + 'px';
    }, 10);
}

function stopChangeHeight() {
    clearInterval(intervalFunc);
}