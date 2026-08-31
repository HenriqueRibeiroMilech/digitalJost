document.querySelector("#op_img_input_1").oninput = function() {
    if (this.files.length > 0) {
        document.querySelector("#op_input_label_1").textContent = "Alterar Imagens Selecionadas...";
        document.querySelector("#lista_label_1").style.display = "block";
        document.querySelector("#lista_1").style.display = "block";
    } else {
        document.querySelector("#op_input_label_1").textContent = "Adicione as Imagens 'NOK'...";
        document.querySelector("#lista_label_1").style.display = "none";
        document.querySelector("#lista_1").style.display = "none";
    };

    var input = document.getElementById('op_img_input_1');
    var output = document.getElementById('lista_1');
    var children = "";

    for (var i = 0; i < document.getElementById("op_img_input_1").files.length; ++i) {
        children += '<li>' + input.files.item(i).name + '</li>';
    }
    output.innerHTML = '<ul>'+children+'</ul>';
};

document.querySelector("#op_img_input_2").oninput = function() {
    if (this.files.length > 0) {
        document.querySelector("#op_input_label_2").textContent = "Alterar Imagens Selecionadas...";
        document.querySelector("#lista_label_2").style.display = "block";
        document.querySelector("#lista_2").style.display = "block";
    } else {
        document.querySelector("#op_input_label_2").textContent = "Adicione as Imagens 'OK'...";
        document.querySelector("#lista_label_2").style.display = "none";
        document.querySelector("#lista_2").style.display = "none";
    };

    var input = document.getElementById('op_img_input_2');
    var output = document.getElementById('lista_2');
    var children = "";

    for (var i = 0; i < document.getElementById("op_img_input_2").files.length; ++i) {
        children += '<li>' + input.files.item(i).name + '</li>';
    }

    output.innerHTML = '<ul>'+children+'</ul>';
};

function validateForm() {
    var empty = 0
    for (let i = 0; i < document.forms["op_qual_post"].length; i++)  {
        var x = document.forms["op_qual_post"][i].value;
        if (x == "") {
            alert('Você precisa preencher todos os campos do formulário para adicionar uma entrada!')
            return false;
        }
    }
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
            document.getElementById('produto').innerHTML = `<input class="input_qual" oninput="searchProduct(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" value="Aguardando seleção..." autocomplete="off" name="id_mater">`


        } else {
            document.getElementById('produto').innerHTML =
                `<input class="input_qual" oninput="searchProduct(this.name)" required onkeyup="this.value=this.value.replace(/'/g, '')" placeholder="Selecione uma opção..." autocomplete="off" list="id_mater" name="id_mater">
                <datalist id="id_mater">
                    <option value="" selected>Selecione uma opção...</option>
                </datalist>`

            for (let i = 0; i < JSON.parse(xhr.responseText).length; i++) {
                document.getElementById('id_mater').innerHTML += `<option id="`+ JSON.parse(xhr.responseText)[i] + `" value="`+ JSON.parse(xhr.responseText)[i] + `">`+ JSON.parse(xhr.responseText)[i] + `</option>`
            }

        }
    };

    xhr.send()
}

function searchProduct(name) {

    var produto = document.getElementsByName(name)[0]

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

document.addEventListener("DOMContentLoaded", function () {
    const unidadeSelect = document.getElementById("unidade");
    const localEspecificoInput = document.getElementById("op_local_info");
    const centroTrabalhoInput = document.getElementById("centro_trabalho");
    const centroTrabalhoDatalist = document.getElementById("ct");

    // Guarda a lista original carregada pelo backend.
    // Essa será a lista utilizada para Caxias do Sul.
    const centrosCaxias = Array.from(
        centroTrabalhoDatalist.querySelectorAll("option")
    )
        .map(function (option) {
            return option.value;
        })
        .filter(function (value) {
            return value !== "";
        });

    // Lista fixa de Centros de Trabalho de Campinas.
    const centrosCampinas = [
        "M101-Montagem Articulação De Onibus",
        "M102-Montagem Trava De Quinta Roda",
        "S101-Solda Robotizada Articulação De Onibus"
    ];

    function atualizarCentrosTrabalho() {
        const unidadeSelecionada = unidadeSelect.value;

        // Limpa o valor anteriormente selecionado.
        centroTrabalhoInput.value = "";

        // Limpa todas as opções atuais do datalist.
        centroTrabalhoDatalist.innerHTML = "";

        let centrosSelecionados;

        if (unidadeSelecionada === "1") {
            centrosSelecionados = centrosCampinas;
            localEspecificoInput.removeAttribute("list");
            localEspecificoInput.placeholder = "Digite aqui...";
        } else {
            centrosSelecionados = centrosCaxias;
            localEspecificoInput.setAttribute("list", "ct");
            localEspecificoInput.placeholder = "Selecione ou digite aqui...";
        }

        centrosSelecionados.forEach(function (centro) {
            const option = document.createElement("option");
            option.value = centro;
            centroTrabalhoDatalist.appendChild(option);
        });
    }

    unidadeSelect.addEventListener("change", atualizarCentrosTrabalho);

    // Monta a lista correta assim que a página carregar.
    atualizarCentrosTrabalho();
});

// V1
