removeNav();
window.onload = setTimeout(loadPage, 50);

var painted = 1;

function loadPage() { // funcao que carrega a pagina
    painted = 0;

    var today = new Date().toISOString().split('T')[0];

    document.querySelector("#desv_sidenav").style.width = "22vw";
    document.querySelector("#desv_sidenav").style.minWidth = "calc(15vh + 5vw)";

    setTimeout(() => {
        document.querySelector("#desv_form_container").style.width = "65vw";
        document.querySelector("#desv_form_container").style.minWidth = "calc(35vh + 15vw)";
    }, 350);

    var sidenav = document.getElementById("desv_sidenav");
    var form_container = document.getElementById("desv_form_container");


    if ("{{area}}" == "Engenharia de Processo") {
        sidenav.innerHTML = `
            <div class="side_wrapper">
                <p class="topics_title"><i class='fas fa-list'></i> Adicionar Nova Demanda</p>
                <p class="paint" id="paint_projeto"><i class='far fa-circle'></i> Nome do Projeto</p>
                <p class="paint" style="color: rgba(239,123,4,1)"><i class='far fa-circle'></i> Responsável</p>
                <p class="paint" style="color: rgba(239,123,4,1)"><i class='far fa-circle'></i> Área Geral</p>
                <p class="paint" id="paint_prazo"><i class='far fa-circle'></i> Prazo da Demanda</p>
                <p class="paint" id="paint_entrada"><i class='far fa-circle'></i> Tipo de Entrada</p>
                <p class="paint" id="paint_url_entrada"><i class='far fa-circle'></i> LINK de Entrada</p>
                <p class="paint" id="paint_descricao"><i class='far fa-circle'></i> Descrição</p>
                <p class="paint" id="paint_processo"><i class='far fa-circle'></i> Processos</p>
                <p class="paint" id="paint_familia"><i class='far fa-circle'></i> Familias de Produtos</p>
                <p class="paint" style="color: rgba(239,123,4,1)" ><i class='far fa-circle'></i> Demanda Estratégica</p>
                <p class="paint" style="color: rgba(239,123,4,1)" ><i class='far fa-circle'></i> Está no POA</p>
                <p class="paint" id="paint_qualidade"><i class='far fa-circle'></i> Melhoria em Qualidade</p>
                <p class="paint" id="paint_seguranca"><i class='far fa-circle'></i> Saúde e Segurança</p>
                <p class="paint" id="paint_produtividade"><i class='far fa-circle'></i> Aumento em Produtividade</p>
                <p class="paint" id="paint_inovacao"><i class='far fa-circle'></i> Inovação</p>
                <p class="paint" id="paint_normas"><i class='far fa-circle'></i> Atendimento a Normas</p>
            </div>`

        form_container.innerHTML = `
            <div class="form_wrapper1">
                <form id="desv_form" method="post" action="/demandas/criar?area={{area}}&att=0">
                    <div style="width: 40%; height: 35vh; float:left">

                        <span class="desv_label">Nome do Projeto</span>
                        <input oninput="paint(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" id="projeto" name="projeto" placeholder="Digite aqui..." autocomplete="off" type="text">

                        <span class="desv_label">Área Geral</span>
                        <input oninput="paint(this.name)" disabled id="area_grande" name="area_grande" value="{{area}}" autocomplete="off" type="text">

                        <span class="desv_label">Tipo de Entrada</span>
                        <select oninput="paint(this.name)" required name="entrada" id="entrada"></select>
                    </div>

                    <div style="width: 50%; height: 35.5vh; float:right">
                        <span class="desv_label">Responsável</span>
                        <input oninput="paint(this.name)" required readOnly id="responsavel" name="responsavel" type="text" value="{{user}}">

                        <span class="desv_label">Prazo da Demanda</span>
                        <input oninput="paint(this.name)" required id="prazo" name="prazo" value="" autocomplete="off" type="date" min="` + today + `">

                        <span class="desv_label">LINK da Entrada</span>
                        <input oninput="paint(this.name)" onkeyup="this.value=this.value.replace(/'/g, '')" id="url_entrada" name="url_entrada" placeholder="Digite aqui..." autocomplete="off" type="text">

                    </div>
                    <div style="clear: both">
                        <span class="desv_label">Descrição</span>
                        <textarea oninput="paint(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" id="descricao" name="descricao" autocomplete="off" style="resize: none;"></textarea>
                    </div>

                    <div style="margin-bottom: 1vw" id="div_processo">
                        <span id="span_processo" class="desv_label1">Processo Geral</span> <input class="botoes" oninput="this.value=''" required id="processo" name="processo"><br>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Montagem">Montagem</button>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Pré Fabricação">Pré Fabricação</button>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Solda">Solda</button>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Usinagem">Usinagem</button>
                    </div>
                    <div style="margin-bottom: 1vw" id="div_familia">
                        <span id="span_familia" class="desv_label1">Familias de Produtos</span> <input class="botoes" required oninput="this.value=''" id="familia" name="familia"><br>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title="Quinta Roda">QR</button>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title="Quinta Roda + Mesa">QR + MESA</button>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title='Articulação de ônibus'>AO</button><br>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title='Suspensor Pneumático 3° Eixo'>SP 3° EIXO</button>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title='Suspensor Pneumático Semi Reboque'>SP SR</button>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title='Engate Esférico'>EE</button><br>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title='Pino Rei'>PR</button>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title='Aparelho de Levantamento'>AL</button>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title='Semi-Varão'>VT</button><br>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title='Engate Automático'>EA</button>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title='Porta Estepe'>PE</button>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="x" title='Engate de Contêiner'>EC</button>
                    </div>
                    <div id="div_prior">
                        <div style="width: 40%; height: 40vh; float:left">
                            <span class="desv_label" style="display:inline-block">Demanda Estratégica</span>
                            <input class="checar" type="checkbox" name="estrategico" id="estrategico" value="ok"><br>

                            <span class="desv_label1">Melhoria em Qualidade</span>
                            <input class="botoes" required oninput="this.value=''" id="qualidade"><br>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="1" name="qualidade">1</button>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="3" name="qualidade">3</button>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="5" name="qualidade">5</button><br>

                            <span class="desv_label1" style='margin-top:1vh'>Aumento em Produtividade</span>
                            <input class="botoes" required oninput="this.value=''" id="produtividade"><br>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="1" name="produtividade">1</button>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="3" name="produtividade">3</button>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="5" name="produtividade">5</button><br>

                            <span class="desv_label1" style='margin-top:1vh'>Atendimento a Normas</span>
                            <input class="botoes" required oninput="this.value=''" id="normas"><br>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="1" name="normas">1</button>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="3" name="normas">3</button>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="5" name="normas">5</button><br>
                        </div>
                        <div style="width: 50%; height: 40.5vh; float:right">
                            <span class="desv_label" style="display:inline-block">Está no POA</span>
                            <input class="checar" type="checkbox" name="poa" id="poa" value="ok"><br>

                            <span class="desv_label1">Saúde e Segurança</span>
                            <input class="botoes" required oninput="this.value=''" id="seguranca"><br>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="1" name="seguranca">1</button>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="3" name="seguranca">3</button>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="5" name="seguranca">5</button><br>

                            <span class="desv_label1" style='margin-top:1vh'>Inovação</span>
                            <input class="botoes" required oninput="this.value=''" id="inovacao"><br>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="1" name="inovacao">1</button>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="3" name="inovacao">3</button>
                            <button type='button' class="nivel_btn" onclick="rank(this)" value="5" name="inovacao">5</button>

                        </div>
                    </div>
                    <div id="div-link">
                        <input class="desv_submit" id="finalizar" value="Finalizar" type="button" onclick="criar()">
                        <button type="submit" style="display:none" id="validar"></button>
                    </div>
                </form>
            </div>`

    } else if ("{{area}}" == "SSMA") {

        sidenav.innerHTML = `
            <div class="side_wrapper">
                <p class="topics_title"><i class='fas fa-list'></i> Adicionar Nova Demanda</p>
                <p class="paint" id="paint_projeto"><i class='far fa-circle'></i> Nome do Projeto</p>
                <p class="paint" style="color: rgba(239,123,4,1)"><i class='far fa-circle'></i> Responsável</p>
                <p class="paint" style="color: rgba(239,123,4,1)"><i class='far fa-circle'></i> Área Geral</p>
                <p class="paint" id="paint_prazo"><i class='far fa-circle'></i> Prazo da Demanda</p>
                <p class="paint" id="paint_entrada"><i class='far fa-circle'></i> Tipo de Entrada</p>
                <p class="paint" id="paint_url_entrada"><i class='far fa-circle'></i> LINK de Entrada</p>
                <p class="paint" id="paint_descricao"><i class='far fa-circle'></i> Descrição</p>
                <p class="paint" id="paint_processo"><i class='far fa-circle'></i> Processo</p>
                <p class="paint" style="color: rgba(239,123,4,1)" ><i class='far fa-circle'></i> Demanda Estratégica</p>
                <p class="paint" style="color: rgba(239,123,4,1)" ><i class='far fa-circle'></i> Está no POA</p>
                <p class="paint" style="color: rgba(239,123,4,1)" ><i class='far fa-circle'></i> Atendimento a Legislação</p>
                <p class="paint" id="paint_risco"><i class='far fa-circle'></i> Potencial de Risco</p>
                <p class="paint" id="paint_familia"><i class='far fa-circle'></i> Área</p>

            </div>`

        form_container.innerHTML = `
            <div class="form_wrapper1">
                <form id="desv_form" method="post" action="/demandas/criar?area={{area}}&att=0">
                    <div style="width: 40%; height: 35vh; float:left">

                        <span class="desv_label">Nome do Projeto</span>
                        <input oninput="paint(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" id="projeto" name="projeto" placeholder="Digite aqui..." autocomplete="off" type="text">

                        <span class="desv_label">Área Geral</span>
                        <input oninput="paint(this.name)" disabled id="area_grande" name="area_grande" value="{{area}}" autocomplete="off" type="text">

                        <span class="desv_label">Tipo de Entrada</span>
                        <select oninput="paint(this.name)" required name="entrada" id="entrada"></select>
                    </div>

                    <div style="width: 50%; height: 35.5vh; float:right">
                        <span class="desv_label">Responsável</span>
                        <input oninput="paint(this.name)" required readOnly id="responsavel" name="responsavel" type="text" value="{{user}}">

                        <span class="desv_label">Prazo da Demanda</span>
                        <input oninput="paint(this.name)" required id="prazo" name="prazo" value="" autocomplete="off" type="date" min="` + today + `">

                        <span class="desv_label">LINK da Entrada</span>
                        <input oninput="paint(this.name)" onkeyup="this.value=this.value.replace(/'/g, '')" id="url_entrada" name="url_entrada" placeholder="Digite aqui..." autocomplete="off" type="text">

                    </div>
                    <div style="clear: both">
                        <span class="desv_label">Descrição</span>
                        <textarea oninput="paint(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" id="descricao" name="descricao" autocomplete="off" style="resize: none;"></textarea>
                    </div>

                    <div style="margin-bottom: 1vw" id="div_processo">
                        <span id="span_processo" class="desv_label1">Processo Geral</span> <input class="botoes" oninput="this.value=''" required id="processo" name="processo"><br>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="JOST Campinas">JOST Campinas</button>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Administrativo">Administrativo</button>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Almoxarifado">Almoxarifado</button><br>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Doca de Entrada">Doca de Entrada</button>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Doca de saída">Doca de saída</button>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Expedição">Expedição</button><br>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Logística">Logística</button>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Montagem">Montagem</button>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Mov. Interna">Mov. Interna</button><br>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Pré fabricação">Pré fabricação</button>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Solda">Solda</button>
                        <button type='button' class="info_btn" onclick="rank(this)" name="processo" value="Usinagem">Usinagem</button>
                    </div>

                    <div style="margin-bottom: 1vw" id="div_prior">
                        <span class="desv_label" style="display:inline-block">Demanda Estratégica</span>
                        <input class="checar" type="checkbox" name="estrategico" id="estrategico" value="ok"><br>

                        <span class="desv_label" style="display:inline-block">Está no POA</span>
                        <input class="checar" type="checkbox" name="poa" id="poa" value="ok"><br>

                        <span class="desv_label" style="display:inline-block">Atendimento a Legislação</span>
                        <input class="checar" type="checkbox" name="legislacao" id="legislacao" value="ok"><br>

                        <span class="desv_label1">Potencial de Risco</span>
                        <input class="botoes" required oninput="this.value=''" id="risco"><br>
                        <button type='button' class="info_btn" onclick="rank(this)" value="1" name="risco">1</button>
                        <button type='button' class="info_btn" onclick="rank(this)" value="3" name="risco">3</button>
                        <button type='button' class="info_btn" onclick="rank(this)" value="5" name="risco">5</button><br>

                    </div>
                    <div style="margin-bottom: 1vw" id="div_familia">
                        <span id="span_familia" class="desv_label1">Área</span> <input class="botoes" required oninput="this.value=''" id="familia" name="familia"><br>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="" name="familia" title="Saúde">Saúde</button>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="" name="familia" title="Segurança">Segurança</button>
                        <button type='button' class="info_btn" onclick="clicar(this)" value="" name="familia" title="Meio Ambiente">Meio Ambiente</button><br>
                    </div>

                    <div id="div-link">
                        <input class="desv_submit" id="finalizar" value="Finalizar" type="button" onclick="criar()">
                        <button type="submit" style="display:none" id="validar"></button>
                    </div>
                </form>
            </div>`

    } else if ("{{area}}" == "Engenharia de Dev. de Fornecedores") {

        sidenav.innerHTML = `
            <div class="side_wrapper">
                <p class="topics_title"><i class='fas fa-list'></i> Adicionar Nova Demanda</p>
                <p class="paint" id="paint_projeto"><i class='far fa-circle'></i> Nome do Projeto</p>
                <p class="paint" style="color: rgba(239,123,4,1)"><i class='far fa-circle'></i> Responsável</p>
                <p class="paint" style="color: rgba(239,123,4,1)"><i class='far fa-circle'></i> Área Geral</p>
                <p class="paint" id="paint_prazo"><i class='far fa-circle'></i> Prazo da Demanda</p>
                <p class="paint" id="paint_entrada"><i class='far fa-circle'></i> Tipo de Entrada</p>
                <p class="paint" id="paint_url_entrada"><i class='far fa-circle'></i> LINK de Entrada</p>
                <p class="paint" id="paint_descricao"><i class='far fa-circle'></i> Descrição</p>
                <p class="paint" id="paint_fornecedorTexto"><i class='far fa-circle'></i> Fornecedor</p>
                <p class="paint" id="paint_inicio"><i class='far fa-circle'></i> Data de Inicio</p>
            </div>`

        form_container.innerHTML = `
            <div class="form_wrapper1">
                <form id="desv_form" method="post" action="/demandas/criar?area={{area}}&att=0">
                    <div style="width: 40%; float:left">

                        <span class="desv_label">Nome do Projeto</span>
                        <input oninput="paint(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" id="projeto" name="projeto" placeholder="Digite aqui..." autocomplete="off" type="text">

                        <span class="desv_label">Área Geral</span>
                        <input oninput="paint(this.name)" disabled id="area_grande" name="area_grande" value="{{area}}" autocomplete="off" type="text">

                        <span class="desv_label">Tipo de Entrada</span>
                        <select oninput="paint(this.name)" required name="entrada" id="entrada"></select>

                        <span class="desv_label">Fornecedor</span>
                        <input oninput="paint(this.name)" onkeyup="this.value=this.value.replace(/'/g, '')" id="fornecedorTexto" name="fornecedorTexto" placeholder="Digite aqui..." autocomplete="off" type="text">

                    </div>

                    <div style="width: 50%; float:right">
                        <span class="desv_label">Responsável</span>
                        <input oninput="paint(this.name)" required readOnly id="responsavel" name="responsavel" type="text" value="{{user}}">

                        <span class="desv_label">Prazo da Demanda</span>
                        <input oninput="paint(this.name)" required id="prazo" name="prazo" value="" autocomplete="off" type="date" min="` + today + `">

                        <span class="desv_label">LINK da Entrada</span>
                        <input oninput="paint(this.name)" onkeyup="this.value=this.value.replace(/'/g, '')" id="url_entrada" name="url_entrada" placeholder="Digite aqui..." autocomplete="off" type="text">

                        <span class="desv_label">Data de Inicio</span>
                        <input oninput="paint(this.name)" required id="inicio" name="inicio" value="" autocomplete="off" type="date">
                    </div>

                    <div style="clear: both">
                        <span class="desv_label">Descrição</span>
                        <textarea oninput="paint(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" id="descricao" name="descricao" autocomplete="off" style="resize: none;"></textarea>
                    </div>


                    <div id="div-link">
                        <input class="desv_submit" id="finalizar" value="Finalizar" type="submit">
                    </div>
                </form>
            </div>`

    } else {

        sidenav.innerHTML = `
            <div class="side_wrapper">
                <p class="topics_title"><i class='fas fa-list'></i> Adicionar Nova Demanda</p>
                <p class="paint" id="paint_projeto"><i class='far fa-circle'></i> Nome do Projeto</p>
                <p class="paint" style="color: rgba(239,123,4,1)"><i class='far fa-circle'></i> Responsável</p>
                <p class="paint" style="color: rgba(239,123,4,1)"><i class='far fa-circle'></i> Área Geral</p>
                <p class="paint" id="paint_prazo"><i class='far fa-circle'></i> Prazo da Demanda</p>
                <p class="paint" id="paint_entrada"><i class='far fa-circle'></i> Tipo de Entrada</p>
                <p class="paint" id="paint_url_entrada"><i class='far fa-circle'></i> LINK de Entrada</p>
                <p class="paint" id="paint_descricao"><i class='far fa-circle'></i> Descrição</p>
            </div>`

        form_container.innerHTML = `
            <div class="form_wrapper1">
                <form id="desv_form" method="post" action="/demandas/criar?area={{area}}&att=0">
                    <div style="width: 40%; height: 35vh; float:left">

                        <span class="desv_label">Nome do Projeto</span>
                        <input oninput="paint(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" id="projeto" name="projeto" placeholder="Digite aqui..." autocomplete="off" type="text">

                        <span class="desv_label">Área Geral</span>
                        <input oninput="paint(this.name)" disabled id="area_grande" name="area_grande" value="{{area}}" autocomplete="off" type="text">

                        <span class="desv_label">Tipo de Entrada</span>
                        <select oninput="paint(this.name)" required name="entrada" id="entrada"></select>
                    </div>

                    <div style="width: 50%; height: 35.5vh; float:right">
                        <span class="desv_label">Responsável</span>
                        <input oninput="paint(this.name)" required readOnly id="responsavel" name="responsavel" type="text" value="{{user}}">

                        <span class="desv_label">Prazo da Demanda</span>
                        <input oninput="paint(this.name)" required id="prazo" name="prazo" value="" autocomplete="off" type="date" min="` + today + `">

                        <span class="desv_label">LINK da Entrada</span>
                        <input oninput="paint(this.name)" onkeyup="this.value=this.value.replace(/'/g, '')" id="url_entrada" name="url_entrada" placeholder="Digite aqui..." autocomplete="off" type="text">

                    </div>
                    <div style="clear: both">
                        <span class="desv_label">Descrição</span>
                        <textarea oninput="paint(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" id="descricao" name="descricao" autocomplete="off" style="resize: none;"></textarea>
                    </div>
                    <div id="div-link">
                        <input class="desv_submit" id="finalizar" value="Finalizar" type="submit">
                    </div>
                </form>
            </div>`
    }

    var entrada = document.getElementById("entrada"); // pega o select com id ENTRADA, para personalizar

    entradasLista = {{entries}}

    for (i in entradasLista) { // para cada entrada, é criada uma opcao no select
        var option = document.createElement("option");
        option.value = entradasLista[i][0];
        text = document.createTextNode(entradasLista[i][1]);
        option.appendChild(text);
        entrada.appendChild(option);
    }

    entrada.innerHTML += '<option disabled value="">Selecionar Entrada</option>'; // cria uma opcao default no select

    var finalizar = document.getElementById('finalizar');
}


function paint(name) {
    var paint = document.getElementById('paint_' + name);
    var input = document.getElementById(name);
    if (input.value == '' || input.value == 'undefined') {
        paint.style.color = "rgba(205,205,205,0.45)";
        painted -= 1;
    } else {
        paint.style.color = "rgba(239,123,4,1)";
        painted += 1;
    }
}

var acum = 0;

function clicar(botao) {

    var tipo = botao.parentNode.querySelector('span').id;

    if (botao.value == "x") {
        botao.classList.add('info_click');
        botao.value = botao.innerText;
        acum += 1;
    } else {
        botao.classList.remove('info_click');
        botao.classList.add('info_btn');
        botao.value = "x";
        acum -= 1;
    }

    if (tipo === "span_familia" && acum > 0) {
        document.getElementById("familia").value = ' '
        paint("familia");
    } else if (tipo == "span_familia") {
        document.getElementById("familia").value = ''
        paint("familia");
    }
    console.log(botao.value)
}

function rank(botao) {
    var botoes = document.getElementsByName(botao.name)

    botoes.forEach((elemento) => {
        elemento.classList.remove('info_click');
        document.getElementById(elemento.name).value = ""
    });

    botao.classList.add('info_click');
    document.getElementById(botao.name).value = " "
    paint(botao.name)
}

function criar() {

    var lista_processos = [];
    var lista_familia = [];
    var lista_prior = [];

    var div = document.getElementById("div_processo");
    var botoes = div.querySelectorAll('button');
    for (let i = 0; i < botoes.length; i++) {
        if (botoes[i].classList.contains("info_click")) {
            lista_processos.push(botoes[i].value);
        }
    }

    div = document.getElementById("div_familia");
    botoes = div.querySelectorAll('button');
    for (let i = 0; i < botoes.length; i++) {
        lista_familia.push(botoes[i].value);
    }

    div = document.getElementById("div_prior");
    botoes = div.querySelectorAll('button');
    for (let i = 0; i < botoes.length; i++) {
        if (botoes[i].classList.contains("info_click")) {
            lista_prior.push(botoes[i].value);
        }
    }

    if (lista_processos != [] && lista_familia != [] && (lista_prior.length == 5 || lista_prior.length == 1)) {

        var form_container = document.getElementById("desv_form");
        var enviar_processo = document.createElement('input')

        enviar_processo.value = lista_processos
        enviar_processo.id = 'enviar_processo'
        enviar_processo.name = 'enviar_processo'
        enviar_processo.style = 'display:none'

        var enviar_familia = document.createElement('input')
        enviar_familia.value = lista_familia
        enviar_familia.id = 'enviar_familia'
        enviar_familia.name = 'enviar_familia'
        enviar_familia.style = 'display:none'

        var enviar_prior = document.createElement('input')
        enviar_prior.value = lista_prior
        enviar_prior.id = 'enviar_prior'
        enviar_prior.name = 'enviar_prior'
        enviar_prior.style = 'display:none'

        form_container.appendChild(enviar_processo)
        form_container.appendChild(enviar_familia)
        form_container.appendChild(enviar_prior)
        document.getElementById('validar').click()

    } else {
        document.getElementById('validar').click()
    }

}
