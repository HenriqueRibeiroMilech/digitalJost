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
    } else {
        title.innerHTML = `Visualizar Desvios`;
        desc.innerHTML = 'Clique para visualizar os documentos de Desvio de Processo';
    }
}

function returnSt() {
    title = document.querySelector('#display_title');
    desc = document.querySelector('#display_desc');

    title.innerHTML = 'Selecione';
    desc.innerHTML = 'uma opção para continuar...';
}