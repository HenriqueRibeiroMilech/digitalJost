removeNav();

function update() {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/demandas/dashboards/dash_callback?area=" + {{area | tojson}}, true);
    xhr.setRequestHeader("Content-type","application/json");
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            if (first) {
                var checkList = document.getElementById('list2');

                checkList.getElementsByClassName('anchor')[0].onclick = function(evt) {
                  if (checkList.classList.contains('visible'))
                    checkList.classList.remove('visible');
                  else
                    checkList.classList.add('visible');
                    filho = checkList.getElementsByTagName("ul")[0];

                    div_filtros.forEach(div => {
                        if (div.id == "list3") {
                            div.style.marginTop = filho.offsetHeight + "px"
                        }
                    });
                }

                lista = document.querySelectorAll('#lista li');
                lista2 = document.querySelectorAll('#lista2 li');
                lista3 = document.querySelectorAll('#lista3 li');
                first = false
            }

            var ov_chart = JSON.parse(JSON.parse(xhr.responseText)[0]);
            ov_chart['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
            ov_chart['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);

            var os_chart = JSON.parse(JSON.parse(xhr.responseText)[1]);
            os_chart['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
            os_chart['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);

            var op_chart = JSON.parse(JSON.parse(xhr.responseText)[2]);
            op_chart['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
            op_chart['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);
            op_chart['layout']['xaxis']['tickfont']['size'] = (window.innerHeight * 0.013) + (window.innerWidth * 0.0015);
            op_chart['layout']['xaxis']['tickangle'] = 90;

            var ox_chart = JSON.parse(JSON.parse(xhr.responseText)[3]);
            ox_chart['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
            ox_chart['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);
            ox_chart['layout']['xaxis']['tickfont']['size'] = (window.innerHeight * 0.013) + (window.innerWidth * 0.0015);
            ox_chart['layout']['xaxis']['tickangle'] = 90;

            var teste_graph = JSON.parse(JSON.parse(xhr.responseText)[4]);
            teste_graph['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
            teste_graph['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);

            var tarefa_status = JSON.parse(JSON.parse(xhr.responseText)[5]);
            tarefa_status['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
            tarefa_status['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);

            var tarefa_processos_status = JSON.parse(JSON.parse(xhr.responseText)[6]);
            tarefa_processos_status['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
            tarefa_processos_status['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);

            var tarefa_pessoas = JSON.parse(JSON.parse(xhr.responseText)[7]);
            tarefa_pessoas['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
            tarefa_pessoas['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);
            tarefa_pessoas['layout']['xaxis']['tickfont']['size'] = (window.innerHeight * 0.013) + (window.innerWidth * 0.0015);
            tarefa_pessoas['layout']['xaxis']['tickangle'] = 90;

            window.addEventListener('resize', function () {
               ov_chart['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
               ov_chart['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);
               Plotly.newPlot('overview', ov_chart['data'], ov_chart['layout'], ov_chart['config']);

               os_chart['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
               os_chart['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);
               Plotly.newPlot('os_process', os_chart['data'], os_chart['layout'], os_chart['config']);

               op_chart['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
               op_chart['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);
               op_chart['layout']['xaxis']['tickfont']['size'] = (window.innerHeight * 0.013) + (window.innerWidth * 0.0015);
               op_chart['layout']['xaxis']['tickangle'] = 90;
               Plotly.newPlot('person_bars', op_chart['data'], op_chart['layout'], op_chart['config']);

               ox_chart['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
               ox_chart['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);
               ox_chart['layout']['xaxis']['tickfont']['size'] = (window.innerHeight * 0.013) + (window.innerWidth * 0.0015);
               ox_chart['layout']['xaxis']['tickangle'] = 90;
               Plotly.newPlot('os_teste', ox_chart['data'], ox_chart['layout'], ox_chart['config']);

               teste_graph['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
               teste_graph['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);
               Plotly.newPlot('teste_graph', teste_graph['data'], teste_graph['layout'], teste_graph['config']);

               tarefa_status['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
               tarefa_status['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);
               Plotly.newPlot('tarefa_status', tarefa_status['data'], tarefa_status['layout'], tarefa_status['config']);

               tarefa_processos_status['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
               tarefa_processos_status['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);
               Plotly.newPlot('tarefa_processos_status', tarefa_processos_status['data'], tarefa_processos_status['layout'], tarefa_processos_status['config']);

               tarefa_pessoas['layout']['font']['size'] = (window.innerHeight * 0.017) + (window.innerWidth * 0.004);
               tarefa_pessoas['layout']['title']['font']['size'] = (window.innerHeight * 0.019) + (window.innerWidth * 0.006);
               tarefa_pessoas['layout']['xaxis']['tickfont']['size'] = (window.innerHeight * 0.013) + (window.innerWidth * 0.0015);
               tarefa_pessoas['layout']['xaxis']['tickangle'] = 90;
               Plotly.newPlot('tarefa_pessoas', op_chart['data'], op_chart['layout'], op_chart['config']);
            });

            document.getElementById("overview").innerHTML = '';
            document.getElementById("os_process").innerHTML = '';
            document.getElementById("person_bars").innerHTML = '';
            document.getElementById("os_teste").innerHTML = '';
            document.getElementById("teste_graph").innerHTML = '';
            document.getElementById("tarefa_status").innerHTML = '';
            document.getElementById("tarefa_processos_status").innerHTML = '';
            document.getElementById("tarefa_pessoas").innerHTML = '';

            Plotly.newPlot('overview', ov_chart['data'], ov_chart['layout'], ov_chart['config'])
            Plotly.newPlot('os_process', os_chart['data'], os_chart['layout'], os_chart['config']);
            Plotly.newPlot('person_bars', op_chart['data'], op_chart['layout'], op_chart['config'])

            if (ox_chart['data'][0]['x'].length > 0) {
                Plotly.newPlot('os_teste', ox_chart['data'], ox_chart['layout'], ox_chart['config']);
            } else {
                document.getElementById('os_teste').style.display = 'none'
            }
            
            Plotly.newPlot('tarefa_status', tarefa_status['data'], tarefa_status['layout'], tarefa_status['config']);
            Plotly.newPlot('tarefa_processos_status', tarefa_processos_status['data'], tarefa_processos_status['layout'], tarefa_processos_status['config']);
            Plotly.newPlot('tarefa_pessoas', tarefa_pessoas['data'], tarefa_pessoas['layout'], tarefa_pessoas['config']);

            var myPlot = document.getElementById('teste_graph')
            Plotly.newPlot('teste_graph', teste_graph['data'], teste_graph['layout'], teste_graph['config']);
            dragLayer = document.getElementsByClassName('nsewdrag')[0]

            myPlot.on('plotly_click', function(data){
                var point = data.points[0];
                var url = point.customdata;
                window.open(url);
            });
        }
    }

    var gdd_area = "";
    var line = {"andamento" : [andamento.value], "atrasado" : [atrasado.value], "concluido" : [concluido.value], "responsavel" : [],
     "area" : [gdd_area], "processo" : [], "familia": []}

    if (!first) {
        lista.forEach(li => {
            var input = li.querySelector('input');
            if (input.value != "") {
                line['responsavel'].push(input.value)
            }
        });

        lista2.forEach(li => {
            var inputs = li.querySelector('input');
            if (inputs.value != "") {
                line['processo'].push(inputs.value)
            }
        });

        lista3.forEach(li => {
            var inputs = li.querySelector('input');
            if (inputs.value != "") {
                line['familia'].push(inputs.id)
            }
        });
    }

    xhr.send([JSON.stringify(line)]);
}

var andamento = document.getElementById("andamento");
var atrasado = document.getElementById("atrasado");
var concluido = document.getElementById("concluido");
var formulario = document.getElementById("filters");
var div_filtros = formulario.querySelectorAll("div");
var lista = document.querySelectorAll('#lista li');
var lista2 = document.querySelectorAll('#lista2 li');
var first = true;

update();

config_filtro3();
config_filtro4();

function config_filtro3() {
    var checkList = document.getElementById('list3');

    checkList.getElementsByClassName('anchor')[0].onclick = function(evt) {
      if (checkList.classList.contains('visible'))
        checkList.classList.remove('visible');
      else
        checkList.classList.add('visible');
        filho = checkList.getElementsByTagName("ul")[0];

        div_filtros.forEach(div => {
            if (div.id == "list4") {
                div.style.marginTop = filho.offsetHeight + "px"
            }
        });
    }
}

function config_filtro4() {
    var checkList = document.getElementById('list4');

    checkList.getElementsByClassName('anchor')[0].onclick = function(evt) {
      if (checkList.classList.contains('visible'))
        checkList.classList.remove('visible');
      else
        checkList.classList.add('visible');
        filho = checkList.getElementsByTagName("ul")[0];

        div_filtros.forEach(div => {
            if (div.id.split("list")[1] > checkList.id.split("list")[1]) {
                div.style.marginTop = filho.offsetHeight + "px"
            }
        });
    }
}

function myFunction() { // funcão para filtrar todas as demandas

    lista.forEach(li => {
        var input = li.querySelector('input');
        if (input.checked == true) {

            input.value = input.name;
        } else {
            input.value = "";
        }
    });

    lista2.forEach(li => {
        var inputs = li.querySelector('input');
        if (inputs.checked == true) {

            inputs.value = inputs.name;
        } else {
            inputs.value = "";
        }
    });

    lista3.forEach(li => {
        var inputs = li.querySelector('input');
        if (inputs.checked == true) {
            inputs.value = "";
        } else {
            inputs.value = inputs.name;
        }
    });

    update();
}

function valor_botao(botao) {
    var igual = ""
    if (botao.id == "atrasado") {
        igual = "Atrasado"
    } else if (botao.id == "concluido") {
        igual = "Concluído"
    } else {
        igual = "Em Andamento"
    }

    if (botao.value == igual) {
        botao.value = "NULO"
        botao.style.backgroundColor = '#163A8A';
    } else {
        botao.value = igual
        botao.style.backgroundColor = '#EF7B04';
    }
    update();
}

var condicao = true

function selecionar(li) {
    var lista_especifica = li.parentNode
    lista_especifica = lista_especifica.querySelectorAll('li');
    var check = li.children[0]
    lista_especifica.forEach(pequeno => {
        var input = pequeno.querySelector('input');
        if (condicao != true) {
            input.checked = true;
        } else {
            input.checked = false;
        }
    });
    if (condicao) {
        condicao = false;
    } else {
        condicao = true;
    }
    check.checked = true
    myFunction();
}