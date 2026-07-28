removeNav();
window.onload = setTimeout(loadPage, 50);
var acum = 0;

var painted = 0;
var acao = true;

function end_dsv(valor) {
    data = new Date(valor);
    if (data > data_fim.valueAsDate) {
        data_fim.value = '';
    }

    data.setDate(data.getDate() + 45);
    data_fim.max = data.toISOString().split('T')[0];

    data2 = new Date(valor);
    data2.setDate(data2.getDate() + 1);
    data_fim.min = data2.toISOString().split('T')[0];
}

var mails = {{mails}}
var resp_emails = []

function loadPage() {

    // Crie um objeto Date representando a data atualvar

    dataAtual = new Date();
    end_dsv(dataAtual.toISOString().split('T')[0]);
    data_inicio.min = dataAtual.toISOString().split('T')[0];

    document.querySelector("#desv_sidenav").style.width = "22vw";
    document.querySelector("#desv_sidenav").style.minWidth = "calc(15vh + 5vw)";

    setTimeout(() => {
        document.querySelector("#desv_form_container").style.width = "60vw";
        document.querySelector("#desv_form_container").style.minWidth = "calc(35vh + 15vw)";
    }, 350);

    var sidenav = document.getElementById("desv_sidenav");
    var form_container = document.getElementById("desv_form_container");

    setTimeout(() => {
        document.querySelector("#desv_tags").style.width = "20vw";
    }, 850);

    try {
        var teste = {{df}}

        document.getElementById('equipe_input').value = teste['sectorId'][0]
        paint('equipe')

        document.getElementById('unidade').value = teste['unit'][0]
        paint('unidade')

        document.getElementById('desc').value = teste['prodDescription'][0]
        paint('desc')

        document.getElementById('dr_input').value = teste['documents'][0]
        paint('doc')

        document.getElementById('ras_input').value = teste['traceability'][0]
        paint('rast')

        document.getElementById('mc_input').innerHTML = teste['motive'][0]
        paint('motivo')

        document.getElementById('risco_input').innerHTML = teste['riskAnalisys'][0]
        paint('riscos')

        document.getElementById('risco_input').innerHTML = teste['riskAnalisys'][0]
        paint('riscos')

        document.getElementById('especial1').value = (teste['special1'][0] === 'True') ? 1 : 0
        paint('especial1')
        
        document.getElementById('especial2').value = (teste['special2'][0] === 'True') ? 1 : 0
        paint('especial2')

        document.getElementById('procedimentos_input').innerHTML = teste['procedures'][0]
        paint('proced')

        JSON.parse(teste['workCenter'][0]).forEach(function(elemento) {
            document.getElementById('ct').value = elemento
            addInfo('ct')
        });

        JSON.parse(teste['prodCode'][0]).forEach(function(elemento) {
            document.getElementById('produto').value = elemento
            addInfo('produto')
        });

        JSON.parse(teste['families'][0]).forEach(function(elemento) {
            document.getElementById('familia').value = elemento
            addInfo('familia')
        });

        JSON.parse(teste['workInstruction'][0]).forEach(function(elemento) {
            document.getElementById('instrucao').value = elemento
            addInfo('instrucao')
        });

        JSON.parse(teste['workInstruction'][0]).forEach(function(elemento) {
            document.getElementById('instrucao').value = elemento
            addInfo('instrucao')
        });

        df_plan = {{df_plan}}

        let lines_lenght = Object.keys(df_plan["deviationId"]).length;

        for (let i = 0; i < lines_lenght; i++) {
            addAcao();
            document.getElementById('acao_' + acum).value = df_plan['text'][i]
            document.getElementById('resp_' + acum).value = df_plan['userId'][i]
            document.getElementById('prazo_' + acum).value = df_plan['deadline'][i]
        }

    } catch (error) {
    
    }


}

function paint(name) {
    var paint = document.getElementById('paint_' + name);
    var input = document.getElementsByName(name)[0];

    if (input.value == '' || input.value == 'undefined') {
        if (paint.style.color != "rgba(205, 205, 205, 0.45)") {
            paint.style.color = "rgba(205, 205, 205, 0.45)";
            painted -= 1;
        }
    } else {
        if (paint.style.color != "rgb(239, 123, 4)") {
            paint.style.color = "rgb(239, 123, 4)";
            painted += 1;
        }

    }

}


function addAcao() {

    acum++

    if (acao) {
        acao = false
        document.getElementById('ver_acao').value = 1
        paint('ver_acao')
    }

    var novaDiv = document.createElement('div');

    novaDiv.innerHTML += `
        <span class="desv_label">Ação ` + acum + `</span>
        <textarea id="acao_` + acum + `" name="acao_` + acum + `" required onkeyup="this.value=this.value.replace(/'/g, '')" autocomplete="off"></textarea><br>
        <span class="desv_label" style="display:inline-block;width:20vw;">Email responsável ` + acum + `</span>
        <span class="desv_label" style="display:inline-block;width:20vw;margin-left:3vh">Prazo ` + acum + `</span>
        <br>
        <input list="options_mails" required value="" onkeyup="this.value=this.value.replace(/'/g, '')" id="resp_` + acum + `" name="resp_` + acum + `" autocomplete="off" placeholder="Digite aqui..." type="text" style="width:20vw;">
        <input required value="" id="prazo_` + acum + `" name="prazo_` + acum + `" autocomplete="off" type="date" style="margin-left:3vh;width:20vw;"><br>
        <button style="display: inline-block;" class="desv_submit" type="button" onclick="removeAcao(` + acum + `)">Remover Ação</button>`

    novaDiv.id = 'acao_div_' + acum
    document.getElementById('acao_div').appendChild(novaDiv)
    resp_emails.push('resp_' + acum)
}

function removeAcao(str) {
    
    var divExcluir = document.getElementById('acao_div_' + str)
    document.getElementById('acao_div').removeChild(divExcluir)

    resp_emails = resp_emails.filter(function(item) {
        return item !== 'resp_' + str;
    });

    if (document.getElementById('acao_div').innerHTML == '') {
        acao = true
        document.getElementById('ver_acao').value = ''
        paint('ver_acao')
    }
}


var infos = {'ct_info': [],
             'produto_info': [],
             'familia_info': [],
             'instrucao_info': []}

function addInfo(str) {
    var info = document.getElementById(str).value;
    var info_values = document.getElementById(str + '_info');

    if (info == 'Todos') {
        infos[str + '_info'] = []; // Reinicializa a lista quando 'Todos' é selecionado
        info_values.innerHTML = '<span class="desv_label" style="color:black">Todos</span>';
        infos[str + '_info'].push(info);
    } else if (!info_values.innerHTML.includes(">" + info + "<") && info != '') {
        if (info_values.innerHTML.includes('Todos')) {
            infos[str + '_info'] = []; // Reinicializa a lista se 'Todos' estava presente
            info_values.innerHTML = createInfoRow(info, str + '_info');
        } else {
            info_values.innerHTML += createInfoRow(info, str + '_info');
        }
        infos[str + '_info'].push(info); // Adiciona a informação à lista correspondente
    }

    if (infos[str + '_info'].length === 1) {
        paint(str)
    }

    document.getElementById(str + "_send").value = JSON.stringify(infos[str + '_info']);
}

function createInfoRow(info, col) {
    return '<div class="info-row">' +
               '<span class="desv_label" style="color:black">' + info + '</span>' +
               '<button name="' + col + '" onclick="removeInfoRow(this)">Remover</button>' +
           '</div>'
}

function removeInfoRow(button) {
    var infoRow = button.parentNode; // Obtém o elemento pai (div.info-row)
    var infoLabel = infoRow.querySelector('.desv_label').innerText; // Obtém o texto do span
    var str = button.name

    // Remove o elemento da lista
    infos[str] = infos[str].filter(item => item !== infoLabel);

    // Remove a linha da interface
    infoRow.remove();

    if (infos[str].length === 0) {
        document.getElementById(str.slice(0, str.indexOf('_'))).value = ''
        paint(str.slice(0, str.indexOf('_')))
    }
}

function enviar() {

    for (var key in infos) {
        if (infos.hasOwnProperty(key) && infos[key].length === 0) {
            alert('Não esqueça de clicar em "Adicionar" ao preencher os campos de (Centro de Trabalho, Código do Produto, Familia do Produto, Instrução de Trabalho)')
            return
        }
    }

    motiveFiles = document.getElementById('input_imagens');
    proceduresFiles = document.getElementById('input_imagens1');

    if (painted < 18) {
        alert('Preencha todos os campos corretamente!')
        return
    } else if (painted == 18 && motiveFiles.files.length != 0 && proceduresFiles.files.length != 0) {
        alert('Preencha todos os campos corretamente!')
        return
    } else if (painted < 20 && (motiveFiles.files.length != 0 || proceduresFiles.files.length != 0)) {
        alert('Preencha todos os campos corretamente!')
        return
    }

    for (var i = 0; i < resp_emails.length; i++) {
        var email = resp_emails[i];
        if (!mails.includes(document.getElementById(email).value)) {
            alert('Email preenchido no plano de ação não foi encontrado na base de dados!')
            return
        }
    } 

    document.getElementById('sendForm').disabled = true
    document.getElementById('desv_form').submit()
    
}

if (window.history.replaceState) {
    window.history.replaceState({}, document.title, window.location.href);
}