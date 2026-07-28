document.querySelector("#op_img_input_1").oninput = function() {  // funcao para caso exista algum input

    var input = document.getElementById('op_img_input_1');  // cria a variavel para acessar o campo input
    var output = document.getElementById('lista_1');  // cria a variavel para acessar a div da lista de arquivos
    children[0] = imagens1  // redefini o valor de todas <li>

    if (this.files.length > 0) { // condicao se tiver mais de um arquivo inputado
        document.querySelector("#lista_label_1").style.display = "block";
        document.querySelector("#lista_1").style.display = "block";

        for (var i = 0; i < document.getElementById("op_img_input_1").files.length; ++i) {  // percorre os arquivos que foram inputados
            children[0] += '<li style="margin-top:17px"><a style="display: inline; padding-left:27px"></a>' + input.files[i].name + '</a></li>';
            // adiciona o arquivo inputado na lista
        }
    }

    output.innerHTML = '<ul id="lista_mae_1">' +children[0]+'</ul>'; // atualiza na tela, a lista dos arquivos
};

document.querySelector("#op_img_input_2").oninput = function() {  // funcao para caso exista algum input

    var input = document.getElementById('op_img_input_2');  // cria a variavel para acessar o campo input
    var output = document.getElementById('lista_2');  // cria a variavel para acessar a div da lista de arquivos
    children[1] = imagens2  // redefini o valor de todas <li>

    if (this.files.length > 0) { // condicao se tiver mais de um arquivo inputado
        document.querySelector("#lista_label_2").style.display = "block";
        document.querySelector("#lista_2").style.display = "block";

        for (var i = 0; i < document.getElementById("op_img_input_2").files.length; ++i) {  // percorre os arquivos que foram inputados
            children[1] += '<li style="margin-top:17px"><a style="display: inline; padding-left:27px"></a>' + input.files[i].name + '</a></li>';
            // adiciona o arquivo inputado na lista
        }

    }

    output.innerHTML = '<ul id="lista_mae_2">' +children[1]+'</ul>'; // atualiza na tela, a lista dos arquivos
};

var data = [{{photos_nok | tojson}}, {{photos_ok | tojson}}];  // armazena a lista de arquivos que já estão salvos
var children = ["", ""];

for (let k = 0; k < 2; k++) {  // repetição para criar as listas iniciais de arquivos já salvos na tela
    if (data[k].length > 0) {  // condicao se já tiver algum arquivo salvo
        document.querySelector("#lista_label_" + (k + 1)).style.display = "block";
        document.querySelector("#lista_" + (k + 1)).style.display = "block";

        var output = document.getElementById("lista_" + (k + 1));  // cria a variavel para acessar a div da lista de arquivos
        data1 = data[k]
        for (var i = 0; i < data1.length; ++i) {  // percorre os arquivos salvos
            children[k] += '<li><a tabindex="0" onclick="remove(this.parentNode)" class="delete_lista"> x </a>&nbsp;&nbsp;<a style="display: inline">' + data1[i] + '</a></li>';
            // adiciona o arquivo inputado na lista
        }

        output.innerHTML = '<ul id="lista_mae_'+ (k + 1) + '">' +children[k]+'</ul>'; // atualiza na tela, a lista dos arquivos

    }

}

var imagens1 = children[0]
var imagens2 = children[1]
var dell1 = []
var dell2 = []

var registerData = {{values}}

fillData()

function fillData() {
    document.getElementById('unidade').value = registerData['unit'][0]
    document.getElementById('op_local_ocorr').value = registerData['type'][0]
    document.getElementById('op_local_info').value = registerData['typeDesc'][0]
    document.getElementById('center').value = registerData['workCenter'][0]
    filter('ct')
    document.getElementById('id_mater').value = registerData['prodCode'][0]
    searchProduct('id_mater')
    document.getElementById('op_familia').value = registerData['prodFamily'][0]
    document.getElementById('op_problema').value = registerData['description'][0]

    if (registerData['repeat'][0] == '1') {
        document.getElementById('op_reincidente').checked = true;
    }
    document.getElementById('op_cont_1').value = registerData['text1'][0]
    document.getElementById('op_cont_2').value = registerData['text2'][0]
    document.getElementById('op_cont_3').value = registerData['text3'][0]
    document.getElementById('op_date').value = registerData['openDate'][0]

    if (registerData['shift'][0].includes('NA')) {
        document.getElementById('NA').checked = true;
    } else {
        if (registerData['shift'][0].includes('1')) {
            document.getElementById('turno1').checked = true;
        }
        if (registerData['shift'][0].includes('2')) {
            document.getElementById('turno2').checked = true;
        }
        if (registerData['shift'][0].includes('3')) {
            document.getElementById('turno3').checked = true;
        }
    }

}

function remove(li) {  // funcao para que arquivos sejam deletados
    var div = li.closest('div');  // acessa a div da lista de arquivos

    if (div.id == "lista_1") {  // condicao se for a lista_1

        dell1.push(li.children[1].textContent);
        document.getElementById('deletar1').value = dell1.join("__,")  // adiciona as imagens a serem deletadas na variavel que será enviada para a API
        imagens1 = imagens1.replace("<li>" + li.innerHTML + "</li>", "")  // tira a linha da imagem da lista da variavel imagens1

    } else {

        dell2.push(li.children[1].textContent);
        document.getElementById('deletar2').value = dell2.join("__,")  // adiciona as imagens a serem deletadas na variavel que será enviada para a API
        imagens2 = imagens1.replace("<li>" + li.innerHTML + "</li>", "")  // tira a linha da imagem da lista da variavel imagens2
    }

    var UL = li.closest('ul');  // acessa a <ul> da lista de arquivos
    UL.removeChild(li);  // remove totalmente a <li> da tela

}

function filter(name) {

    var ct = document.getElementsByName(name)[0]

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/op/qualidade/add?searchCt=" + ct.value , false);
    xhr.setRequestHeader("Content-type","application/json");

    xhr.onreadystatechange = function () {

        if (JSON.parse(xhr.responseText)[0] == '' || typeof(JSON.parse(xhr.responseText)[0]) === 'undefined') {

            document.getElementById('familia').innerHTML = "Aguardando seleção..."
            document.getElementById('desc').innerHTML = "Aguardando seleção..."
            document.getElementById('produto').innerHTML = `<input class="input_qual" oninput="searchProduct(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" value="Aguardando seleção..."  id="id_mater" autocomplete="off" name="id_mater">`


        } else {
            document.getElementById('produto').innerHTML =
                `<input class="input_qual" oninput="searchProduct(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" placeholder="Selecione uma opção..." autocomplete="off" list="id_list" id="id_mater" name="id_mater">
                <datalist id="id_list">
                    <option value="" selected>Selecione uma opção...</option>
                </datalist>`

            for (let i = 0; i < JSON.parse(xhr.responseText).length; i++) {
                document.getElementById('id_list').innerHTML += `<option id="`+ JSON.parse(xhr.responseText)[i] + `" value="`+ JSON.parse(xhr.responseText)[i] + `">`+ JSON.parse(xhr.responseText)[i] + `</option>`
            }

        }
    };

    xhr.send()
}

function searchProduct(id) {

    var produto = document.getElementById(id)
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/op/qualidade/add?searchProd=" + produto.value , false);
    xhr.setRequestHeader("Content-type","application/json");

    xhr.onreadystatechange = function () {
        if (JSON.parse(xhr.responseText)[0] == '' || typeof(JSON.parse(xhr.responseText)[0]) === 'undefined') {
            document.getElementById('desc').innerHTML = "Aguardando seleção..."
        } else {
            document.getElementById('desc').innerHTML = JSON.parse(xhr.responseText)[0]
        }
    };

    xhr.send()
}