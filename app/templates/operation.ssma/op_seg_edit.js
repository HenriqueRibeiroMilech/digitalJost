// op_seg_edit.js

var data = JSON.parse({{data | tojson}});

// ✅ children estava como array no seu arquivo, mas é usado como string.
// Isso evita bugs na montagem/remoção da lista de arquivos.
var children = "";
var dell = [];

function fillForm() {

    // ====== COORDENADORES ======
    coord = {{coord}};
    for (dados in coord) {
        var coordSelect = document.getElementById('coord');
        if (coordSelect) {
            coordSelect.innerHTML += '<option value="' + coord[dados][1] + '" name="' + coord[dados][0] + '">' + coord[dados][0] + '</option>';
        }
    }

    // ====== CHECKS (event/class) ======
    for (let i = 0; i < document.querySelectorAll('.seg_check').length; i++) {
        if (i < 6) {
            let ev = [];
            try { ev = JSON.parse(data['event'][0]); } catch (e) { ev = []; }

            for (let k = 0; k < Object.keys(ev).length; k++) {
                if (ev[k] == document.querySelector('#check_' + i).innerHTML) {
                    document.querySelector('#check_' + i).click();
                }
            }
        } else {
            let cl = [];
            try { cl = JSON.parse(data['class'][0]); } catch (e) { cl = []; }

            for (let k = 0; k < Object.keys(cl).length; k++) {
                if (cl[k] == document.querySelector('#check_' + i).innerHTML) {
                    document.querySelector('#check_' + i).click();
                }
            }
        }
    }

    // ====== PREENCHER CAMPOS ======
    // ✅ Proteção: se você removeu a "Seção" do HTML, não tenta acessar.
    // ✅ Proteção: só tenta preencher se existir elemento com aquele id.
    for (let i = 0; i < Object.keys(data).length; i++) {
        const key = Object.keys(data)[i];

        if (i > 2 && !['images', 'openDate', 'ramalContact'].includes(key)) {

            // ✅ Se "section" vem do backend mas você removeu do HTML, ignore
            if (key === 'section') continue;

            // Caso especial antigo (não necessário se você removeu o campo),
            // mas se existir no HTML ainda assim não quebra.
            if (key === 'section') {
                const secByName = document.getElementsByName('seção')[0];
                if (secByName) secByName.value = data['section'][0];
                continue;
            }

            const el = document.getElementById(key);
            if (el) {
                el.value = data[key][0];
            }
        }
    }

    // ====== SETAR SELECTS (com proteção) ======
    if (document.getElementById('coord')) document.getElementById('coord').value = data['coord'] ? data['coord'][0] : '';
    if (document.getElementById('manager')) document.getElementById('manager').value = data['manager'] ? data['manager'][0] : '';
    if (document.getElementById('unit')) document.getElementById('unit').value = data['unit'] ? data['unit'][0] : '';
    if (document.getElementById('userContact')) document.getElementById('userContact').value = data['userContact'] ? data['userContact'][0] : '';
    if (document.getElementById('involved')) document.getElementById('involved').value = data['involved'] ? data['involved'][0] : '';

    // ====== LISTA DE IMAGENS SALVAS ======
    if (data['images'] && data['images'][0]) {
        let imgs = [];
        try { imgs = JSON.parse(data['images'][0]); } catch (e) { imgs = []; }

        if (imgs && imgs.length > 0) {
            var output = document.getElementById("seg_filename");
            if (output) {
                children = "";
                for (var i = 0; i < imgs.length; ++i) {
                    children += '<li><a tabindex="0" onclick="remove(this.parentNode)" class="delete_lista"> x </a>&nbsp;&nbsp;<a style="display: inline">' + imgs[i] + '</a></li>';
                }
                output.innerHTML = '<ul>' + children + '</ul>';
            }
        }
    }
}

// ====== LISTA DE ARQUIVOS NOVOS ======
document.querySelector("#fotos").oninput = function () {

    var input = document.getElementById('fotos');
    var output = document.getElementById('seg_filename');

    if (!input || !output) return;

    if (this.files.length > 0) {
        for (var i = 0; i < input.files.length; ++i) {
            children += '<li style="margin-top:17px"><a style="display: inline; padding-left:27px"></a>' + input.files[i].name + '</a></li>';
        }
    }

    output.innerHTML = '<ul id="lista_mae_1">' + children + '</ul>';
};

removeNav();

function changeLoc(loc) {
    window.location = loc;
}

function select(id) {
    var event = document.getElementById(id);
    if (!event) return;

    if (event.style.background == "rgba(205, 205, 205, 0.2)" || event.style.background == "") {
        event.style.background = "rgba(239, 123, 4, 0.9)";
    } else {
        event.style.background = "";
    }
}

function submitData() {
    var dataSend = { 'evento': [], 'classificação': [], 'imagens': [], 'deletar': [] };

    // ====== CHECKS ======
    var checks = document.querySelectorAll('.seg_check');
    checks.forEach((elm) => {
        if (elm.style.background == 'rgba(239, 123, 4, 0.9)') {
            if (elm.id.split('_')[1] < 6) dataSend['evento'].push(elm.innerHTML);
            else dataSend['classificação'].push(elm.innerHTML);
        }
    });

    // ====== INPUTS ======
    var names = document.querySelectorAll('.seg_input');
    names.forEach((name) => {
        dataSend[name.name] = name.value;
    });

    // ====== TEXTAREAS ======
    var texts = document.querySelectorAll('.seg_textarea');
    texts.forEach((text) => {
        dataSend[text.name] = text.value;
    });

    // ====== IMAGENS NOVAS ======
    var inputFotos = document.getElementById('fotos');
    if (inputFotos) {
        for (var i = 0; i < inputFotos.files.length; ++i) {
            dataSend['imagens'].push(inputFotos.files[i].name);
        }
    }

    // ====== IMAGENS PARA DELETAR ======
    for (var i = 0; i < dell.length; ++i) {
        dataSend['deletar'].push(dell[i]);
    }

    var keys = Object.keys(dataSend);

    // ====== VALIDAÇÃO VISUAL (com proteção) ======
    for (let i = 0; i < keys.length; i++) {
        if (['evento', 'classificação', 'imagens', 'deletar'].includes(keys[i])) continue;

        var field = document.getElementsByName(keys[i])[0];

        // ✅ Se o campo não existe na tela (ex.: você removeu "seção"), ignora
        if (!field) continue;

        if (dataSend[keys[i]] == '') {
            if (field.tagName != 'TEXTAREA') field.style.borderBottom = "solid 0.3vh red";
            else field.style.border = "solid 0.3vh red";
        } else {
            if (field.tagName != 'TEXTAREA') field.style.borderBottom = "solid 0.3vh rgba(239,123,4,1)";
            else field.style.border = "solid 0.3vh rgba(239,123,4,1)";
        }
    }

    // ====== VALIDAÇÃO FINAL (com proteção) ======
    var ok = true;
    for (let i = 0; i < keys.length; i++) {
        if (['evento', 'classificação', 'imagens', 'deletar'].includes(keys[i])) continue;

        var field = document.getElementsByName(keys[i])[0];

        // ✅ Se o campo não existe na tela, ignora
        if (!field) continue;

        if (dataSend[keys[i]] == '') {
            alert('Preencha todos os campos corretamente!');
            field.scrollIntoView({ behavior: "smooth", block: "center" });
            ok = false;
            break;
        }
    }

    if (ok) {
        var photos = document.getElementById("fotos") ? document.getElementById("fotos").files : [];
        var formData = new FormData();

        for (let i = 0; i < photos.length; i++) {
            formData.append("fotos", photos[i]);
        }

        formData.append("data", JSON.stringify(dataSend));

        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/op/ssma/edit?id=" + {{id | tojson}}, false);

        xhr.onreadystatechange = function () {
            window.location = "/op/ssma";
        };

        xhr.send(formData);
    }
}

function remove(li) {
    if (!li) return;

    // ✅ Proteção: evita erro se a estrutura do <li> mudar
    if (li.children && li.children.length > 1) {
        dell.push(li.children[1].textContent);
    } else {
        // fallback: tenta capturar texto do li
        dell.push(li.textContent.replace('x', '').trim());
    }

    // ✅ Proteção: remove do HTML local (string) sem depender 100% do formato
    try {
        children = children.replace("<li>" + li.innerHTML + "</li>", "");
    } catch (e) {}

    var UL = li.closest('ul');
    if (UL) UL.removeChild(li);
}
``