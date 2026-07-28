removeNav();

function update() {
    var xhr = new XMLHttpRequest()
    xhr.open('POST', '/dashboards/chp/ct_callback')
    xhr.setRequestHeader("Content-type","application/json");
    xhr.onreadystatechange = function () {

        if (xhr.readyState === 4 && xhr.status === 200) {
            var info = JSON.parse(xhr.responseText)[0];
            document.getElementById('aus').innerHTML = '<b>' + info['AUSENTES'] + '</b> OPERADORES';
            document.getElementById('ct').innerHTML = '<b>' + info['NO CT DE ORIGEM'] + '</b> OPERADORES';
            document.getElementById('emps').innerHTML = '<b>' + info['EM EMPRÉSTIMO'] + '</b> OPERADORES';
            document.getElementById('nalloc').innerHTML = '<b>' + info['NÃO ALOCADOS'] + '</b> OPERADORES';

            var data = JSON.parse(xhr.responseText)[1];
            var chart = JSON.parse(data);
            document.getElementById('general').innerHTML = '';
            Plotly.newPlot('general', chart['data'], chart['layout'], chart['config']);
        }
    }
    xhr.send(JSON.stringify(["geral"]))
}

setInterval(update, 5000);