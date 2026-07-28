document.querySelector("#fotos").oninput = function() {
    if (this.files.length > 0) {
        document.querySelector("#fotos_label").textContent = "Alterar Imagens Selecionadas...";
        document.querySelector("#seg_lista").style.display = "block";
        document.querySelector("#seg_filename").style.display = "block";
    } else {
        document.querySelector("#fotos_label").textContent = "Adicione as Imagens...";
        document.querySelector("#seg_lista").style.display = "none";
        document.querySelector("#seg_filename").style.display = "none";
    };

    var input = document.querySelector("#fotos");
    var output = document.getElementById('seg_filename');
    var children = "";

    for (var i = 0; i < document.getElementById('fotos').files.length; ++i) {
        children += '<li>' + input.files[i].name + '</li>';
    }

    output.innerHTML = '<ul>'+children+'</ul>';
};

removeNav();

coord = {{coord}}
for (dados in coord) {
    document.getElementById('coordenador').innerHTML += '<option value=' + coord[dados][1] + '>' + coord[dados][0] + '</option>'
}

function changeLoc(loc) {
    window.location = loc;
}

function select(id) {
    var event = document.getElementById(id);

    if (event.style.background == "rgba(205, 205, 205, 0.2)" || event.style.background == "") {
        event.style.background = "rgba(239, 123, 4, 0.9)";
    } else {
        event.style.background = "";
    }
}


function submitData() {
   var data = {'evento': [], 'classificação': [], 'imagens': []}
   var checks = document.querySelectorAll('.seg_check');
   checks.forEach((elm, i) => {
       if (elm.style.background == 'rgba(239, 123, 4, 0.9)') {
           if (elm.id.split('_')[1] < 6) {
               data['evento'].push(elm.innerHTML);
           } else {
               data['classificação'].push(elm.innerHTML);
           }
       }
   });

   var names = document.querySelectorAll('.seg_input');
   names.forEach((name,i) => {
       data[name.name] = name.value;
   });

   var texts = document.querySelectorAll('.seg_textarea');
   texts.forEach((text, i) => {
       data[text.name] = text.value;
   });

   var input = document.getElementById('fotos')
   for (var i = 0; i < input.files.length; ++i) {
       data['imagens'].push(input.files[i].name);
   }

   var keys = Object.keys(data);
   for (let i = 0; i < keys.length; i++) {
       var input = document.getElementsByName(keys[i])[0];
       if (data[keys[i]] == '' && !['evento', 'classificação', 'imagens'].includes(keys[i])) {
           if (input.tagName != 'TEXTAREA') {
               input.style.borderBottom = "solid 0.3vh red";
           } else {
               input.style.border = "solid 0.3vh red";
           }

       } else if (data[keys[i]] != '' && !['evento', 'classificação', 'imagens'].includes(keys[i])) {
           if (input.tagName != 'TEXTAREA') {
               input.style.borderBottom = "solid 0.3vh rgba(239,123,4,1)";
           } else {
               input.style.border = "solid 0.3vh rgba(239,123,4,1)";
           }
       }
   }


   for (let i = 0; i < keys.length; i++) {
       if (data[keys[i]] == '' && !['evento', 'classificação', 'imagens'].includes(keys[i])) {
           alert('Preencha todos os campos corretamente!');
           var input = document.getElementsByName(keys[i])[0];
           input.scrollIntoView({behavior: "smooth", block: "center"});
           var ok = false;
           break;
       } else {
           var ok = true;
       }
   }

   if (ok) {
       var photos = document.getElementById("fotos").files;
       var formData = new FormData();

       for (let i = 0; i < photos.length; i++) {
           formData.append("fotos", photos[i]);
       }

       formData.append("data", JSON.stringify(data));

       var xhr = new XMLHttpRequest();
       xhr.open("POST", "/op/ssma/add", false);

       xhr.onreadystatechange = function () {
          window.location = "/op/ssma"
       }
       xhr.send(formData)
   }
}