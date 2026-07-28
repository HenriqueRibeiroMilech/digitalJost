removeNav();
window.onload = setTimeout(loadPage, 50);

var dia = new Date().toLocaleDateString();
var data = {{data}}
var pessoas = {{people}};

function loadPage() { // funcao que carrega a pagina
    painted = 0;

    document.querySelector("#desv_sidenav").style.width = "22vw";
    document.querySelector("#desv_sidenav").style.minWidth = "calc(15vh + 5vw)";

    setTimeout(() => {
        document.querySelector("#desv_form_container").style.width = "60vw";
        document.querySelector("#desv_form_container").style.minWidth = "calc(35vh + 15vw)";
    }, 350);

    var sidenav = document.getElementById("desv_sidenav");
    var form_container = document.getElementById("desv_form_container");

    sidenav.innerHTML = `
        <div class="side_wrapper">
            <div style="height:50vh">
                <p class="topics_title"><i class='fas fa-list'></i> Gerenciar Tarefa</p>
                <p class="paint" style="color: rgba(239,123,4,1)"><i class='far fa-circle'></i> Data</p>
                <p class="paint" id="paint_responsavel"><i class='far fa-circle'></i> Responsável</p>
                <p class="paint" id="paint_prazo"><i class='far fa-circle'></i> Prazo</p>
                <p class="paint" id="paint_conclusao"><i class='far fa-circle'></i> Data de Conclusão</p>
                <p class="paint" id="paint_tarefa"><i class='far fa-circle'></i> Tarefa</p>
                <p class="paint" id="paint_observacoes"><i class='far fa-circle'></i> Observações</p>
            </div>
            <form method='post' action="/demandas/tarefa/criar?area={{area}}&projeto={{projeto}}&tarefa={{tarefa}}&delete=1">
                <div id="div-link" style='margin-top:32vh;display: flex; justify-content: center; align-items: center;'>
                    <button class="desv_submit" type="submit">Excluir Tarefa</button>
                </div>
            </form>
        </div>`

    form_container.innerHTML = `
        <div class="form_wrapper1">
            <form id="desv_form" method="post" action="/demandas/tarefa/criar?area={{area}}&projeto={{projeto}}&tarefa={{tarefa}}">
                <div style="width: 40%; height: 30vh; float:left">

                    <span class="desv_label">Data</span>
                    <input disabled id="data" name="data" type="text">

                    <span class="desv_label">Nome do Responsável</span>
                    <input required oninput="paint(this.name)" type="text" id="responsavel" name='responsavel' list="opcoes" placeholder="Digite aqui..." value="` + data[0]['RESPONSÁVEL'] + `">
                    <datalist id="opcoes"></datalist><br>

                    <span class="desv_label" style="display:inline-block">Responsável externo?</span>
                    <input class="checar" type="checkbox" name="externo" id="externo" value="ok"><br>
                </div>

                <div style="width: 50%; height: 30.5vh; float:right">
                    <span class="desv_label">Prazo</span>
                    <input oninput="paint(this.name)" required type="date" id="prazo" value="` + data[0]['PRAZO'] + `" name="prazo"/>

                    <span class="desv_label">Data de Conclusão</span>
                    <input oninput="paint(this.name)" type="date" id="conclusao" name="conclusao"/>
                </div>

                <div style="clear: both;height: 51.5vh;">
                    <span class="desv_label">Tarefa</span>
                    <textarea oninput="paint(this.name)" placeholder="Digite aqui..." required onkeyup="this.value=this.value.replace(/'/g, '')" id="tarefa" name="tarefa" autocomplete="off" style="resize: none;"></textarea>

                    <span class="desv_label">Observações</span>
                    <textarea oninput="paint(this.name)" placeholder="Digite aqui..." onkeyup="this.value=this.value.replace(/'/g, '')" id="observacoes" name="observacoes" autocomplete="off" style="resize: none;"></textarea>
                </div>

                <div id="div-link">
                    <button class="desv_submit" type="button" onclick="verificar()" style='margin-top:1vh'>Atualizar</button>
                    <button style='display:none' id='enviar' type="submit"></button>
                </div>
            </form>
        </div>`

    document.getElementById('data').value = dia;
    document.getElementById("tarefa").value = data[0]['TAREFA']

    paint('responsavel')
    paint('prazo')
    paint('tarefa')

    if (data[0]['CONCLUSAO']) {
        document.getElementById("conclusao").value = data[0]['CONCLUSAO']
        paint('conclusao')
    }
    if (data[0]['OBSERVACOES']) {
        document.getElementById("observacoes").value = data[0]['OBSERVACOES']
        paint('observacoes')
    }

    var datalist = document.getElementById("opcoes");

    for (var i = 0; i < pessoas.length; i++) {
        var opcao = document.createElement("option");
        opcao.value = pessoas[i]['NOME'];
        datalist.appendChild(opcao);
    }

    var input = document.getElementById("responsavel");
    input.setAttribute("list", "opcoes");
}


function paint(name) {
    var paint = document.getElementById('paint_' + name);
    var input = document.getElementsByName(name)[0];

    if (input.value == '' || input.value == 'undefined') {
        paint.style.color = "rgba(205,205,205,0.45)";
    } else {
        paint.style.color = "rgba(239,123,4,1)";
    }
}

function verificar() {
    var check = document.getElementById("externo");
    if (check.checked == false) {
        var texto = document.getElementById("responsavel");
        for (var i = 0; i < pessoas.length; i++) {
            if (texto.value == pessoas[i]['NOME']) {
                document.getElementById("enviar").click();
                return
            }
        }
        alert("Caso o responsavel nâo seja externo, você deve escrever o nome como na lista que aparece ao lado")
    } else {
        document.getElementById("enviar").click();
    }
}