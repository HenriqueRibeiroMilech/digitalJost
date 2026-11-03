document.title = "Informativo da Qualidade - " + {{day | tojson}}
function init() {
    var data = {{file | tojson}}
    for (let i = 0; i < data.length; i++) {
        var entry = data[i];
        var id_color = entry['Local da Ocorrencia'][0].toLowerCase();
        if (entry['Local da Ocorrencia'][0].toLowerCase() == 'cliente (não formal)') {
            var id_color = 'clientenf';
        } else if (entry['Local da Ocorrencia'][0].toLowerCase() == 'cliente (formal)') {
            var id_color = 'clientef';
        } else if (entry['Local da Ocorrencia'][0].toLowerCase() == 'cliente (logística)') {
            var id_color = 'clienteLG';
        }

        document.getElementById('op_qual_body').innerHTML += `
            <div class="qual_event">
                <div class="qual_view_event" id="` + id_color + `">
                    <div class="qual_view_info_wrap">
                        <div class="qual_view_problem">
                            <p class="qual_view_title" id="` + id_color + `">Informativo da Qualidade {{day}} || Nº ` + entry['ID'] + `</p>
                            <p class="qual_view_p"><b>Problema: </b>` + entry['Problema'] + `</p>
                            <p class="qual_view_p"><b>Código Prod: </b>` + entry['prodCode'] + `</p>
                            <button class="qual_view_print" onclick="printer()">Formato de Impressão</button>
                            {% if can_edit %}<button class="qual_view_print" onclick="editar(` + entry['ID'] + `)">Editar</button>{% endif %}
                        </div>

                        <div class="qual_view_other_info">
                            <p class="qual_view_title" id="` + id_color + `">Dados da Ocorrência</p>
                            <p class="qual_view_hp"><b>Reincidente: </b>` + entry['Reincidente'] + `</p>
                            <p class="qual_view_p"><b>Local da Ocorrência: </b>` + entry['Local da Ocorrencia'][1] + `</p>
                            <p class="qual_view_hp"><b>Família: </b>` + entry['Familia do Produto'] + `</p>
                            <p class="qual_view_hp"><b>Turno de Trabalho: </b>` + entry['Turno'] + `</p>
                        </div>

                        <div class="qual_view_contention">
                            <p class="qual_view_title" id="` + id_color + `">Contenção</p>
                            <p class="qual_view_p"><b>O que: </b>` + entry['Contencao']['O que'] + `</p>
                            <p class="qual_view_p"><b>Quem: </b>` + entry['Contencao']['Quem'] + `</p>
                            <p class="qual_view_p"><b>Como: </b>` + entry['Contencao']['Como'] + `</p>
                        </div>
                    </div>

                    <div class="qual_view_img_section"></div>
                </div>
            </div>`
        var acum = 100 / (entry['Imagens NOK'].length + entry['Imagens OK'].length)

        for (let k = 0; k < entry['Imagens NOK'].length; k++) {
            var src = (entry['URLs Imagens NOK'] || [])[k] || '/static/uploads/operation/img_nok/' + entry['ID'] + '/' + encodeURIComponent(entry['Imagens NOK'][k])
            document.querySelectorAll('.qual_view_img_section')[i].innerHTML += `
                <div class="qual_img_wrap" style="background:rgb(182,21,21);max-width:` + acum + `vw;max-height:` + 50 + `vh;">NOK  <img class="qual_view_img" style="max-width:` + (acum - 5) + `vw;max-height:` + 45 + `vh;" src="` + src + `"/></div>`
        }

        for (let k = 0; k < entry['Imagens OK'].length; k++) {
            var src = (entry['URLs Imagens OK'] || [])[k] || '/static/uploads/operation/img_ok/' + entry['ID'] + '/' + encodeURIComponent(entry['Imagens OK'][k])
            document.querySelectorAll('.qual_view_img_section')[i].innerHTML += `
                <div class="qual_img_wrap" style="background:#228C22;max-width:` + acum + `vw;max-height:` + 50 + `vh;">OK <img class="qual_view_img" style="max-width:` + (acum - 5) + `vw;max-height:` + 45 + `vh;" src="` + src + `"/></div>`
        }
    }
}

removeNav();
init();

function printer () {
    window.open({{ print_url | tojson }})
}

function changeLoc(acao) {
    var str = {{day | tojson}}
    var dia = new Date(str.split('/').reverse().join('/'))

    if (acao == "voltar") {
        if (dia.getDay() - 1 === 0) {
            dia.setDate(dia.getDate() - 2);
        } else {
            dia.setDate(dia.getDate() - 1);
        }
        var enviar = dia.toLocaleDateString()
        window.location = '/op/qualidade/view?day=' + enviar
    } else if (acao == "prox") {
        if (dia.getDay() === 6) {
            dia.setDate(dia.getDate() + 2);
        } else {
            dia.setDate(dia.getDate() + 1);
        }
        var enviar = dia.toLocaleDateString()
        window.location = '/op/qualidade/view?day=' + enviar
    } else {
        window.print();
    }
}

function editar(id) {
   var url = 'edit?entryID=' + id + '&command=edit';
   window.location = url;
};

function scrollToNextOrPreviousDivMae(event) {

    const divMaes = document.querySelectorAll('.qual_event');
    let currentDivMae;
    let targetDivMae;

    // Encontra a div-mae atual que está visível na tela
    for (let i = 0; i < divMaes.length; i++) {
        const rect = divMaes[i].getBoundingClientRect();
        if (rect.top <= window.innerHeight / 2 && rect.bottom >= window.innerHeight / 2) {
            currentDivMae = divMaes[i];
            break;
        }
    }

    // Encontra a próxima ou a div-mae anterior
    if (event.deltaY > 0) {
        targetDivMae = currentDivMae.nextElementSibling;
    } else {
        targetDivMae = currentDivMae.previousElementSibling;
    }

    // Faz o scroll para a próxima ou anterior div-mae e posiciona no meio
    if (targetDivMae) {
        const targetMiddlePosition = targetDivMae.offsetTop + targetDivMae.offsetHeight / 2 - window.innerHeight / 2;

        isScrolling = true;

        window.scrollTo({
            top: targetMiddlePosition,
            behavior: 'smooth'
        });
    }
}

document.addEventListener('wheel', scrollToNextOrPreviousDivMae);
