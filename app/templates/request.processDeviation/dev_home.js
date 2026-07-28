removeNav();
window.onload = setTimeout(animate, 100);

function animate() {

    document.querySelector("#boa_pratica").style.bottom = "55%";
    document.querySelector("#boa_pratica").style.opacity = "1";

    document.querySelector("#title").style.opacity = "1";
    document.querySelector("#title").style.marginTop = "17.5vh";

    document.querySelector("#title_desc").style.opacity = "1";
    document.querySelector("#title_desc").style.marginTop = "17.5vh";

    document.querySelector("#data").style.opacity = "1";
    document.querySelector("#data").style.marginTop = "35vh";


}

function changeData(id) {
    title = document.querySelector('#display_title');
    desc = document.querySelector('#display_desc');

    if (id == 'criar') {
        title.innerHTML = `Novo Documento`;
        desc.innerHTML = 'Clique para acessar o formulário de preenchimento de um novo Desvio de Processo. Lembre-se, o documento tem de passar por um processo avaliativo antes de ser aprovado e oficializado!';
    } else if (id == 'view') {
        title.innerHTML = `Minhas aprovações`;
        desc.innerHTML = 'Clique para acessar a pagina, onde é possivel verificar o status de aprovação e realizar a aprovação de um desvio pela sua área';
    } else if (id == 'cad') {
        title.innerHTML = `Aprovadores de Desvio`;
        desc.innerHTML = 'Clique para acessar a pagina de visualização e gerenciamento dos aprovadores de desvio, onde é possivel cadastrar, editar e excluir aprovadores';
    } else if (id == 'hist') {
        title.innerHTML = `Visualizar Desvios`;
        desc.innerHTML = 'Clique para visualizar os documentos de Desvio de Processo';
    } else {
        title.innerHTML = `Minhas Ações`;
        desc.innerHTML = 'Clique para acessar a pagina de visualização e gerenciamento das suas ações de desvio';
    }
}

function returnSt() {
    title = document.querySelector('#display_title');
    desc = document.querySelector('#display_desc');

    title.innerHTML = 'Selecione';
    desc.innerHTML = 'uma opção para continuar...';
}

/* =====================================================
   ALTERAR POP - ADMIN
   - Abre modal para upload do novo POP.
   - Envia PDF para /desvios/pop/alterar.
   - Backend substitui o PDF e reseta os aceites.
   ===================================================== */

function openPopConfigModal() {
    var modal = document.getElementById('pop_config_modal');

    if (!modal) return;

    modal.style.display = 'flex';

    var msg = document.getElementById('pop_config_message');
    if (msg) {
        msg.style.display = 'none';
        msg.innerText = '';
    }

    var input = document.getElementById('pop_pdf_input');
    if (input) {
        input.value = '';
    }
}

function closePopConfigModal() {
    var modal = document.getElementById('pop_config_modal');

    if (!modal) return;

    modal.style.display = 'none';
}

document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('pop_config_form');

    if (!form) return;

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        var input = document.getElementById('pop_pdf_input');
        var btn = document.getElementById('pop_config_submit');
        var msg = document.getElementById('pop_config_message');

        if (!input || !input.files || input.files.length === 0) {
            alert('Selecione um arquivo PDF.');
            return;
        }

        var file = input.files[0];
        var fileName = String(file.name || '').toLowerCase();

        if (!fileName.endsWith('.pdf')) {
            alert('Arquivo inválido. Envie apenas PDF.');
            input.value = '';
            return;
        }

        if (!confirm('Deseja realmente alterar o POP? Todos os usuários precisarão aceitar novamente.')) {
            return;
        }

        var formData = new FormData();
        formData.append('pop_pdf', file);

        if (btn) {
            btn.disabled = true;
            btn.innerText = 'Atualizando...';
        }

        if (msg) {
            msg.style.display = 'block';
            msg.style.color = '#163A8A';
            msg.innerText = 'Enviando novo POP...';
        }

        fetch('/desvios/pop/alterar', {
            method: 'POST',
            body: formData
        })
        .then(function (r) {
            return r.json().then(function (j) {
                return { ok: r.ok, j: j };
            });
        })
        .then(function (res) {
            if (!res.ok) {
                throw new Error(res.j && res.j.message ? res.j.message : 'Erro ao atualizar POP.');
            }

            if (msg) {
                msg.style.color = '#228c22';
                msg.innerText = res.j.message || 'POP atualizado com sucesso.';
            }

            alert(res.j.message || 'POP atualizado com sucesso.');

            closePopConfigModal();
        })
        .catch(function (err) {
            if (msg) {
                msg.style.color = '#d33';
                msg.innerText = err.message || 'Erro inesperado.';
            }

            alert(err.message || 'Erro inesperado.');
        })
        .finally(function () {
            if (btn) {
                btn.disabled = false;
                btn.innerText = 'Atualizar POP e resetar aceites';
            }
        });
    });
});