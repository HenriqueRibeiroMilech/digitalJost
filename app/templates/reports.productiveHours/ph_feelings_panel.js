function filterPeriod() {
    var xhr = new XMLHttpRequest();
    var init = document.getElementById('init').value;
    var end = document.getElementById('end').value;
    document.getElementById('1').innerHTML = '<div class="loader"></div>';
    document.getElementById('2').innerHTML = '<div class="loader"></div>';
    xhr.open('POST', '/dashboards/chp/rh')
    xhr.setRequestHeader("Content-type","application/json");
    xhr.onreadystatechange = function () {
        var resp = xhr.responseText
        var data = JSON.parse(resp)[0];
        var chart = JSON.parse(data);

        chart['layout']['font']['size'] = (window.innerHeight * 0.03) + (window.innerWidth * 0.0027);
        chart['layout']['title']['font']['size'] = (window.innerHeight * 0.028) + (window.innerWidth * 0.0025);
        chart['layout']['legend']['font']['size'] = (window.innerHeight * 0.023) + (window.innerWidth * 0.0022);
        chart['layout']['xaxis']['tickfont']['size'] = (window.innerHeight * 0.023) + (window.innerWidth * 0.0025);

        document.getElementById('1').innerHTML = '';
        Plotly.newPlot('1', chart['data'], chart['layout'], chart['config']);

        var info = JSON.parse(resp)[1];
        var flt = info['faltas']
        var rat = info['ratio']

        document.getElementById('2').innerHTML = '';
        document.getElementById('2').innerHTML += `<div class="pseudo_wrap"><p class="leg_ttl">Índice de Absenteísmo</p>
                                                   <p class="leg_ind">` + rat + `%</p>
                                                   <p class="leg_bot">Qtd. de Faltas: <b>` + flt + `</b></p></div>`

        freezeClic = false;
    }

    xhr.send(JSON.stringify([init, end]))
}

filterPeriod();