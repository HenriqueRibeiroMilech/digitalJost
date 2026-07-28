removeNav();
window.onload = setTimeout(loadPage, 50);
var acum = 0;
var painted = 0;
var acao = true;

/* === ADICIONADO: upload de evidências agora é opcional === */
var imagens_ok = false;

var ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png'];
var ALLOWED_IMAGE_MIME_TYPES = ['image/jpeg', 'image/png'];

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

/* =====================================================
   ADIÇÃO SEGURA:
   - evidências não são obrigatórias;
   - se anexar, aceita somente JPG, JPEG e PNG.
   ===================================================== */

function getFileExtension(fileName) {
 try {
  var parts = String(fileName || '').split('.');
  if (parts.length <= 1) return '';
  return parts[parts.length - 1].toLowerCase();
 } catch (e) {
  return '';
 }
}

function isAllowedImageFile(file) {
 if (!file) return true;

 var ext = getFileExtension(file.name);
 var mime = String(file.type || '').toLowerCase();

 return ALLOWED_IMAGE_EXTENSIONS.includes(ext) &&
        (mime === '' || ALLOWED_IMAGE_MIME_TYPES.includes(mime));
}

function validarImagemInput(input, showAlert) {
 if (!input) return true;

 var files = input.files || [];

 for (var i = 0; i < files.length; i++) {
  if (!isAllowedImageFile(files[i])) {
   if (showAlert) {
    alert(
     'Arquivo inválido: ' + files[i].name +
     '\n\nEnvie apenas imagens JPG, JPEG ou PNG nos campos de evidência.'
    );
   }

   input.value = '';
   return false;
  }
 }

 return true;
}

function validarTodasImagens() {
 var motiveFiles = document.getElementById('input_imagens');
 var proceduresFiles = document.getElementById('input_imagens1');

 if (!validarImagemInput(motiveFiles, true)) return false;
 if (!validarImagemInput(proceduresFiles, true)) return false;

 return true;
}

/* =====================================================
   PRÉ-VISUALIZAÇÃO DAS IMAGENS
   - Não altera backend.
   - Apenas mostra na tela as imagens selecionadas.
   - Mantém validação atual JPG/JPEG/PNG.
   ===================================================== */

function limparPreviewImagens(containerId) {
 var container = document.getElementById(containerId);

 if (!container) return;

 container.innerHTML = '';
}

function criarCardPreviewImagem(file) {
 var wrapper = document.createElement('div');

 wrapper.style.width = '120px';
 wrapper.style.border = '1px solid #d9d9d9';
 wrapper.style.borderRadius = '8px';
 wrapper.style.padding = '6px';
 wrapper.style.background = 'white';
 wrapper.style.boxShadow = '0 2px 6px rgba(0,0,0,.12)';
 wrapper.style.display = 'flex';
 wrapper.style.flexDirection = 'column';
 wrapper.style.alignItems = 'center';
 wrapper.style.justifyContent = 'center';

 var img = document.createElement('img');

 img.style.width = '110px';
 img.style.height = '90px';
 img.style.objectFit = 'cover';
 img.style.borderRadius = '6px';
 img.style.marginBottom = '6px';

 var fileName = document.createElement('div');

 fileName.style.width = '110px';
 fileName.style.fontSize = '11px';
 fileName.style.color = '#333';
 fileName.style.textAlign = 'center';
 fileName.style.wordBreak = 'break-word';
 fileName.innerText = file.name;

 wrapper.appendChild(img);
 wrapper.appendChild(fileName);

 var reader = new FileReader();

 reader.onload = function(e) {
  img.src = e.target.result;
 };

 reader.readAsDataURL(file);

 return wrapper;
}

function previewImagensSelecionadas(inputId, containerId) {
 var input = document.getElementById(inputId);
 var container = document.getElementById(containerId);

 if (!input || !container) return;

 limparPreviewImagens(containerId);

 var files = input.files || [];

 if (files.length === 0) {
  return;
 }

 for (var i = 0; i < files.length; i++) {
  if (!isAllowedImageFile(files[i])) {
   continue;
  }

  container.appendChild(criarCardPreviewImagem(files[i]));
 }
}

function aplicarPreviewImagens() {
 var inputMotivo = document.getElementById('input_imagens');
 var inputProced = document.getElementById('input_imagens1');

 if (inputMotivo) {
  inputMotivo.addEventListener('change', function() {
   previewImagensSelecionadas('input_imagens', 'preview_imagens1');
  });
 }

 if (inputProced) {
  inputProced.addEventListener('change', function() {
   previewImagensSelecionadas('input_imagens1', 'preview_imagens2');
  });
 }
}

/* === ADICIONADO: apenas detecta se há algum anexo, sem obrigar === */
function validarImagens() {
 var motiveFiles = document.getElementById('input_imagens');
 var proceduresFiles = document.getElementById('input_imagens1');

 validarImagemInput(motiveFiles, true);
 validarImagemInput(proceduresFiles, true);

 imagens_ok =
  (motiveFiles && motiveFiles.files.length > 0) ||
  (proceduresFiles && proceduresFiles.files.length > 0);
}

function aplicarRegrasUploadOpcional() {
 try {
  var form = document.getElementById('desv_form');
  if (form) {
   form.setAttribute('enctype', 'multipart/form-data');
  }

  // Documentos relacionados passa a ser opcional
  var docInput = document.getElementById('dr_input') || document.querySelector('[name="doc"]');
  if (docInput) {
   docInput.removeAttribute('required');
  }

  // Evidências motivo
  var inputMotivo = document.getElementById('input_imagens');
  if (inputMotivo) {
   inputMotivo.removeAttribute('required');
   inputMotivo.setAttribute('accept', '.jpg,.jpeg,.png,image/jpeg,image/png');
   inputMotivo.addEventListener('change', validarImagens);
  }

  // Evidências procedimentos
  var inputProced = document.getElementById('input_imagens1');
  if (inputProced) {
   inputProced.removeAttribute('required');
   inputProced.setAttribute('accept', '.jpg,.jpeg,.png,image/jpeg,image/png');
   inputProced.addEventListener('change', validarImagens);
  }

  // Texto visual dos labels
  var labelMotivo = document.getElementById('placehold_3');
  if (labelMotivo) {
   labelMotivo.innerHTML = 'Evidências motivo de concessão (apenas JPG, JPEG ou PNG)';
  }

  var labelProced = document.getElementById('placehold_2');
  if (labelProced) {
   labelProced.innerHTML = 'Evidências procedimentos a serem seguidos (penas JPG, JPEG ou PNG)';
  }

 } catch (e) {}
}

/* =====================================================
   ADIÇÃO SEGURA:
   valida os campos obrigatórios reais sem depender do count painted.
   Assim documentos/imagens podem ser opcionais sem liberar envio incompleto.
   ===================================================== */
function validarCamposObrigatoriosPrincipais() {
 var requiredIds = [
  'equipe_input',
  'unidade',
  'desc',
  'data_inicio',
  'data_fim',
  'ras_input',
  'mc_input',
  'risco_input',
  'especial1',
  'especial2',
  'ssma',
  'procedimentos_input'
 ];

 for (var i = 0; i < requiredIds.length; i++) {
  var el = document.getElementById(requiredIds[i]);

  if (!el || String(el.value || '').trim() === '') {
   alert('Preencha todos os campos obrigatórios corretamente!');
   if (el) el.focus();
   return false;
  }
 }

 // Campos de lista que precisam clicar em Adicionar
 for (var key in infos) {
  if (infos.hasOwnProperty(key) && infos[key].length === 0) {
   alert('Não esqueça de clicar em "Adicionar" ao preencher os campos de (Centro de Trabalho, Código do Produto, Familia do Produto, Instrução de Trabalho)');
   return false;
  }
 }

 // Plano de ação obrigatório
 if (document.getElementById('ver_acao').value === '' || document.getElementById('acao_div').innerHTML === '') {
  alert('Adicione pelo menos uma ação no plano de ação.');
  return false;
 }

 // Valida ações criadas dinamicamente
 var actionItems = document.querySelectorAll('#acao_div textarea[id^="acao_"], #acao_div input[id^="resp_"], #acao_div input[id^="prazo_"]');

 for (var j = 0; j < actionItems.length; j++) {
  if (String(actionItems[j].value || '').trim() === '') {
   alert('Preencha todos os campos do plano de ação.');
   actionItems[j].focus();
   return false;
  }
 }

 return true;
}

function loadPage() {

 aplicarRegrasUploadOpcional();
 aplicarPreviewImagens();

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

  df_plan = {{df_plan}}
  let lines_lenght = Object.keys(df_plan["deviationId"]).length;
  for (let i = 0; i < lines_lenght; i++) {
   addAcao();
   document.getElementById('acao_' + acum).value = df_plan['text'][i]
   document.getElementById('resp_' + acum).value = df_plan['userId'][i]
   document.getElementById('prazo_' + acum).value = df_plan['deadline'][i]
  }
 } catch (error) {}
}

function paint(name) {
 var paint = document.getElementById('paint_' + name);
 var input = document.getElementsByName(name)[0];

 if (!paint || !input) return;

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
 <span class="desv_label">Ação ${acum}</span>
 <textarea id="acao_${acum}" name="acao_${acum}" required autocomplete="off"></textarea><br>
 <span class="desv_label" style="display:inline-block;width:20vw;">Email responsável ${acum}</span>
 <span class="desv_label" style="display:inline-block;width:20vw;margin-left:3vh">Prazo ${acum}</span><br>
 <input list="options_mails" required id="resp_${acum}" name="resp_${acum}" style="width:20vw;">
 <input required type="date" id="prazo_${acum}" name="prazo_${acum}" style="margin-left:3vh;width:20vw;"><br>
 <button type="button" onclick="removeAcao(${acum})">Remover Ação</button>`
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

var infos = {
 'ct_info': [],
 'produto_info': [],
 'familia_info': [],
 'instrucao_info': []
}

function addInfo(str) {
 var info = document.getElementById(str).value;
 var info_values = document.getElementById(str + '_info');

 if (info == 'Todos') {
  infos[str + '_info'] = [];
  info_values.innerHTML = '<span class="desv_label" style="color:black">Todos</span>';
  infos[str + '_info'].push(info);
 } else if (!info_values.innerHTML.includes(">" + info + "<") && info != '') {
  if (info_values.innerHTML.includes('Todos')) {
   infos[str + '_info'] = [];
   info_values.innerHTML = createInfoRow(info, str + '_info');
  } else {
   info_values.innerHTML += createInfoRow(info, str + '_info');
  }
  infos[str + '_info'].push(info);
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
 var infoRow = button.parentNode;
 var infoLabel = infoRow.querySelector('.desv_label').innerText;
 var str = button.name

 infos[str] = infos[str].filter(item => item !== infoLabel);
 infoRow.remove();

 if (infos[str].length === 0) {
  document.getElementById(str.slice(0, str.indexOf('_'))).value = ''
  paint(str.slice(0, str.indexOf('_')))
 }
}

function enviar() {

 if (!validarCamposObrigatoriosPrincipais()) {
  return
 }

 if (!validarTodasImagens()) {
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