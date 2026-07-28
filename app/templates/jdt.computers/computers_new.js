function createInputs() {
    var inputs = document.querySelectorAll(".img_input");
    inputs.forEach(function(item) {
        var id = item.id.split('_')[1];
        item.addEventListener('input', function (e) {
            if (item.files.length > 0) {
                document.querySelector("#placehold_" + id).textContent = "Alterar arquivos selecionados...";
                document.querySelector("#label_" + id).style.display = "block";
                document.querySelector("#lista_" + id).style.display = "block";
            } else {
                document.querySelector("#placehold_" + id).textContent = "Adicione documentos...";
                document.querySelector("#label_" + id).style.display = "none";
                document.querySelector("#lista_" + id).style.display = "none";
            };

            var input = document.querySelector('#input_' + id)
            var output = document.querySelector("#lista_" + id)
            var children = "";

            for (var i = 0; i < item.files.length; ++i) {
                children += '<li>' + input.files.item(i).name + '</li>';
            }

            output.innerHTML = '<ul>'+children+'</ul>';
        });
    });
}

createInputs();
