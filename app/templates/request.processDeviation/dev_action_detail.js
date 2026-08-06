/*
  "A persistência é o caminho do êxito."
  — Charles Chaplin

  Detalhe da ação:
  A ação usa a mesma roupa bonita do detalhe do desvio.
  Mesma tabela, mesmo popup de anexos, mesmo estilo.
*/


// =====================================================
// HISTÓRICO DE PRAZO:
// Datas antigas da ação enviadas pelo backend.
// Serão exibidas riscadas/apagadas acima da data atual.
// =====================================================
var actionDeadlineHistory = {{ deadlineHistory | default('') | tojson }};


// =====================================================
// ADIÇÃO: DATA FIM RENOVADA DA AÇÃO
// =====================================================
function formatRenewedActionFinalDate(tableData, k, info) {
  try {
    var historyRaw = String(actionDeadlineHistory || '').trim();

    if (historyRaw) {
      var historyDates = historyRaw
        .split('\n\n')
        .map(function (x) { return x.trim(); })
        .filter(Boolean);

      if (historyDates.length > 0) {
        var html = `
          <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:16px;text-align:center;">
        `;

        historyDates.forEach(function (oldDate) {
          html += `
            <div style="font-size:11px;opacity:.55;text-decoration:line-through;margin-bottom:2px;">` + oldDate + `</div>
          `;
        });

        html += `
            <div style="font-size:14px;font-weight:600;">` + info + `</div>
          </div>
        `;

        return html;
      }
    }

    if (k < tableData.length - 1) {
      var oldFinalDate = tableData[k + 1][6];

      if (oldFinalDate && oldFinalDate != info) {
        return `
          <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:16px;text-align:center;">
            <div style="font-size:11px;opacity:.55;text-decoration:line-through;margin-bottom:2px;">` + oldFinalDate + `</div>
            <div style="font-size:14px;font-weight:600;">` + info + `</div>
          </div>
        `;
      }
    }

    return info;
  } catch (e) {
    return info;
  }
}


// =====================================================
// INICIALIZAÇÃO DA TABELA
// =====================================================
function init() {
  closeAttachments();

  var myTable = document.createElement("table"),
      row = myTable.insertRow(),
      cell;

  var perrow = 1;
  var tableData = {{ table | tojson }};

  tableData.forEach((entry, k) => {
    entry.forEach((info, i) => {

      // =====================================================
      // LINHAS DE DADOS
      // =====================================================
      if (k > 0) {

        if (i != 1 && i != 8 && i != 9) {
          cell = row.insertCell();

          // =====================================================
          // ADIÇÃO: DATA FIM RENOVADA DA AÇÃO
          // =====================================================
          if (i == 6) {
            cell.innerHTML = formatRenewedActionFinalDate(tableData, k, info);
          } else {
            cell.innerHTML = info;
          }
        }

        if (i == 2) {
          cell.style.width = '20vw';
        }

        // =====================================================
        // COLUNA DETALHES DA AÇÃO
        // =====================================================
        if (i == 0) {
          cell.style.width = "12vw";
          cell.style.textDecoration = "underline";

          cell.onclick = function () {
            var url = '/desvios/detalhes?id={{ deviationBase }}';
            window.open(url, '_blank');
          };

          cell.innerHTML =
            `<button type="button"
                     style="min-width: 9vw"
                     class="table_btn"
                     name="col_${i}">
                <b>Ação {{ actionNumber }}</b>
             </button>`;

          // =====================================================
          // COLUNA ANEXOS
          // =====================================================
          cell = row.insertCell();

          var anexosButton = document.createElement("button");

          anexosButton.type = "button";
          anexosButton.style.minWidth = "7vw";
          anexosButton.className = "table_btn";
          anexosButton.name = "col_" + i;
          anexosButton.innerText = "Anexos";

          anexosButton.onclick = function (e) {
            e.stopPropagation();

            openAttachments(
              '{{ deviationId }}',
              entry[9] || ''
            );
          };

          cell.appendChild(anexosButton);
        }

        // =====================================================
        // COLUNA STATUS
        // =====================================================
        else if (i == 7) {

          if (info == 0) {
            cell.style.backgroundColor = "yellow";
            cell.style.color = "black";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Ação pendente';

          } else if (info == 1) {
            cell.style.backgroundColor = "#228c22";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Concluído';

          } else if (info == 2) {
            cell.style.backgroundColor = "gray";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Cancelado';

          } else if (info == 3) {
            cell.style.backgroundColor = "gray";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Finalizado';

          } else if (info == 4) {
            cell.style.backgroundColor = "red";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Recusado';

          } else if (info == 5) {
            cell.style.backgroundColor = "red";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Atrasado';

          } else {
            cell.style.backgroundColor = "gray";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Indefinido';
          }

          // =====================================================
          // COLUNA AÇÕES
          // =====================================================
          cell = row.insertCell();
          cell.innerHTML = '';

          var canExecuteAction = (
            '{{ resp }}' == '1'
            || '{{ admin }}' == '1'
          );

          var canEditDeadline = (
            '{{ can_edit_deadline }}' == '1'
          );

          var actionHasAttachments = hasAttachmentsFor();
          var hasAvailableAction = false;

          // =====================================================
          // AÇÃO PENDENTE
          //
          // Responsável ou administrador pode finalizar.
          // O backend continuará exigindo pelo menos um anexo.
          // =====================================================
          if (entry[7] == 0 && canExecuteAction) {
            var finalizarButton = document.createElement("button");

            finalizarButton.type = "button";
            finalizarButton.style.minWidth = "7vw";
            finalizarButton.style.background = "rgb(45, 90, 187)";
            finalizarButton.className = "table_btn";
            finalizarButton.name = "col_" + i;
            finalizarButton.innerText = "Finalizar";

            finalizarButton.onclick = function () {
              tryFinalizeAction('{{ actionId }}');
            };

            cell.appendChild(finalizarButton);
            hasAvailableAction = true;
          }

          // =====================================================
          // AÇÃO ATRASADA COM ANEXO
          //
          // O botão Validar aparece somente se:
          // - for responsável ou administrador;
          // - existir pelo menos um arquivo anexado.
          // =====================================================
          if (
            entry[7] == 5
            && canExecuteAction
            && actionHasAttachments
          ) {
            var validarButton = document.createElement("button");

            validarButton.type = "button";
            validarButton.style.minWidth = "7vw";
            validarButton.style.background = "rgb(45, 90, 187)";
            validarButton.className = "table_btn";
            validarButton.name = "col_" + i;
            validarButton.innerText = "Validar";

            validarButton.onclick = function () {
              tryValidateDelayedAction('{{ actionId }}');
            };

            cell.appendChild(validarButton);
            hasAvailableAction = true;
          }

          // =====================================================
          // ALTERAR PRAZO
          //
          // Administrador ou criador pode alterar o prazo.
          // Pode ser ação pendente ou atrasada.
          // =====================================================
          if (
            canEditDeadline
            && (entry[7] == 0 || entry[7] == 5)
          ) {
            if (hasAvailableAction) {
              cell.appendChild(document.createElement("br"));
              cell.appendChild(document.createElement("br"));
            }

            var alterarPrazoButton = document.createElement("button");

            alterarPrazoButton.type = "button";
            alterarPrazoButton.style.minWidth = "7vw";
            alterarPrazoButton.style.transition =
              "background-color 0.1s ease, transform 0.1s ease, box-shadow 0.1s ease";
            alterarPrazoButton.style.background = "rgb(45, 90, 187)";
            alterarPrazoButton.className = "table_btn";
            alterarPrazoButton.name = "col_" + i;
            alterarPrazoButton.innerText = "Prazo";

            var prazoHoverTimer = null;

            alterarPrazoButton.onmouseenter = function () {
              prazoHoverTimer = setTimeout(function () {
                alterarPrazoButton.style.backgroundColor = "#EF7B04";
                alterarPrazoButton.style.boxShadow =
                  "0 4px 10px rgba(0,0,0,.18)";
              }, 180);
            };

            alterarPrazoButton.onmouseleave = function () {
              clearTimeout(prazoHoverTimer);
              alterarPrazoButton.style.backgroundColor =
                "rgb(45, 90, 187)";
              alterarPrazoButton.style.boxShadow = "";
            };

            alterarPrazoButton.onclick = function () {
              tryChangeActionDeadline(
                '{{ actionId }}',
                entry[6]
              );
            };

            cell.appendChild(alterarPrazoButton);
            hasAvailableAction = true;
          }

          // =====================================================
          // NENHUMA AÇÃO DISPONÍVEL
          //
          // Se estiver atrasada e sem anexo, orienta o responsável
          // a anexar um documento para liberar o botão Validar.
          // =====================================================
          if (!hasAvailableAction) {
            var semAcao = document.createElement("button");

            semAcao.type = "button";
            semAcao.style.minWidth = "7vw";
            semAcao.className = "table_btn";
            semAcao.disabled = true;

            if (
              entry[7] == 5
              && canExecuteAction
              && !actionHasAttachments
            ) {
              semAcao.innerText = "Anexe para validar";
            } else {
              semAcao.innerText = "Sem ação disponível";
            }

            cell.appendChild(semAcao);
          }
        }
      }

      // =====================================================
      // CABEÇALHO
      // =====================================================
      else {

        if (i != 1 && i != 8 && i != 9) {
          cell = row.insertCell();

          if (i == 0) {
            cell.innerHTML = 'DETALHES<br>AÇÃO';

          } else if (i == 2) {
            cell.innerHTML = 'AÇÃO';
          
          } else if (i == 6) {
            cell.innerHTML = 'PRAZO';

          } else {
            cell.innerHTML = info;
          }
        }

        if (i == 0) {
          cell = row.insertCell();
          cell.innerHTML = 'ANEXOS';
        }

        else if (i == 7) {
          cell.innerHTML = info;

          cell = row.insertCell();
          cell.innerHTML = 'AÇÕES';
        }
      }

    });

    if (k == 0) {
      row.style.fontWeight = 'bold';
      row.style.background = '#163A8A';
      row.style.color = 'white';
    }

    var next = k + 1;

    if (next % perrow == 0) {
      row = myTable.insertRow();
    }
  });

  myTable.lang = "pt-BR";
  myTable.id = "paradas_table";

  var container = document.getElementById("table-container");

  if (container) {
    container.innerHTML = '';
    container.appendChild(myTable);
  }
}


// =====================================================
// FILTRO
// =====================================================
function myFunction() {
  var input, filter, table, tr, td, i, txtValue, display;

  display = [];

  table = document.getElementById("paradas_table");

  if (!table) return;

  tr = table.getElementsByTagName("tr");

  filters = [
    [0, 'solicitante'],
    [1, 'equipe'],
    [2, 'ct'],
    [3, 'familia'],
    [4, 'data'],
    [5, 'n_desvio'],
    [8, 'status']
  ];

  for (i = 0; i < tr.length; i++) {
    var line = [];

    filters.forEach((item) => {
      var id = item[1];
      var index = item[0];

      input = document.getElementById(id);

      if (!input) {
        line.push("no_filter");
        return;
      }

      filter = input.value.toUpperCase();

      if (i > 0 && filter != '') {
        td = tr[i].getElementsByTagName("td")[index];

        if (td) {
          txtValue = td.textContent || td.innerText;

          if (txtValue.toUpperCase().indexOf(filter) > -1) {
            line.push("yes");

          } else {
            if (td.childElementCount > 0) {
              if (td.firstElementChild.value == filter) {
                line.push("yes");
              } else {
                line.push("none");
              }

            } else {
              line.push("none");
            }
          }
        }

      } else if (i > 0 && filter == '') {
        line.push("no_filter");
      }
    });

    display.push(line);
  }

  for (k = 1; k < tr.length - 1; k++) {
    if (display[k].includes("none")) {
      tr[k].style.display = "none";
    } else {
      tr[k].style.display = "";
    }
  }
}


// =====================================================
// ANEXOS
// =====================================================
function openAttachments(id, str) {
  var form = document.getElementById('lab_form');

  if (form) {
    form.action = "/desvios/acoes/{{ actionId }}";
  }

  str = (str || '').split('\n\n').filter(x => x && x.trim() !== '');

  var blur = document.querySelector(".blur_wrap");

  if (blur) {
    blur.style.pointerEvents = "none";
  }

  var overlay = document.querySelector('#box');

  if (overlay) {
    overlay.style.display = "block";
    overlay.style.opacity = "1";
  }

  var myTable = document.createElement("table"),
      row = myTable.insertRow(),
      cell;

  cell = row.insertCell();
  cell.innerHTML = 'ANEXOS';
  cell.style.width = '85vw';
  cell.style.overflow = 'hidden';
  cell.style.textOverflow = 'ellipsis';

  var labForm = document.getElementById('lab_form');

  if (str.length !== 0) {
    cell.style.width = '65vw';

    cell = row.insertCell();
    cell.innerHTML = '';
    cell.style.width = '20vw';
    cell.style.overflow = 'hidden';
    cell.style.textOverflow = 'ellipsis';

    if ('{{ resp }}' == '1' || '{{ admin }}' == '1') {
      cell = row.insertCell();
      cell.style.width = "5vw";
      cell.style.maxWidth = "5vw";

      if (labForm) {
        labForm.style.display = 'block';
      }
    }

  } else {
    if ('{{ resp }}' == '1' || '{{ admin }}' == '1') {
      if (labForm) {
        labForm.style.display = 'block';
      }
    }
  }

  row.style.fontWeight = 'bold';
  row.style.background = '#163A8A';
  row.style.color = 'white';

  row = myTable.insertRow();

  if (str.length !== 0) {
    for (let k = 0; k < str.length; k++) {
      cell = row.insertCell();
      cell.innerHTML = str[k];

      cell = row.insertCell();

      let imageType = str[k].split('.')[str[k].split('.').length - 1].toUpperCase();

      cell.innerHTML =
        `<button class="table_btn"
                 onclick="window.location='/desvios/acoes/anexo/download?anexo=${encodeURIComponent(str[k])}&action_id={{ actionId }}'"
                 style="padding:15px;width:inherit;background-color:#228C22">
            <i class="fa fa-download"></i> DOWNLOAD <b>${imageType}</b>
         </button>`;


      if ('{{ resp }}' == '1' || '{{ admin }}' == '1') {
        cell = row.insertCell();
        cell.style.width = "5vw";
        cell.style.maxWidth = "5vw";


        cell.innerHTML =
          `<button class="remove"
                   onclick="window.location='/desvios/acoes/{{ actionId }}?anexo=${encodeURIComponent(str[k])}'">
             &times;
           </button>`;

      }

      row = myTable.insertRow();
    }

  } else {
    cell = row.insertCell();
    cell.style.width = '85vw';
    cell.innerHTML = 'SEM ANEXOS ENVIADOS';
  }

  var labContainer = document.getElementById("lab-container");

  if (labContainer) {
    labContainer.innerHTML = '';
    myTable.lang = "pt-BR";
    myTable.id = "paradas_table";
    labContainer.appendChild(myTable);
  }
}


// =====================================================
// FECHAR POPUP DE ANEXOS
// =====================================================
function closeAttachments() {
  var overlay = document.querySelector('#box');

  if (overlay) {
    overlay.style.opacity = "0";
    overlay.style.display = "none";
  }

  var blur = document.querySelector(".blur_wrap");

  if (blur) {
    blur.style.pointerEvents = "auto";
  }
}


// =====================================================
// LISTA DE ARQUIVOS SELECIONADOS
// =====================================================
function bindAttachmentInput() {
  var input = document.getElementById('input_1');

  if (!input) return;

  input.addEventListener('change', function () {
    const list = document.getElementById('lista_1');

    if (!list) return;

    list.innerHTML = '';

    Array.from(this.files || []).forEach(file => {
      const item = document.createElement('div');
      item.textContent = file.name;
      list.appendChild(item);
    });
  });
}


// =====================================================
// VALIDAÇÃO DE ANEXOS PARA FINALIZAR
// =====================================================
function hasAttachmentsFor() {
  try {
    if (!window.__actionTableData && Array.isArray({{ table | tojson }})) {
      window.__actionTableData = {{ table | tojson }};
    }

    var tdata = window.__actionTableData || [];

    if (!tdata || tdata.length < 2) return false;

    var row = tdata[1];

    if (!row) return false;

    var att = (row[9] || '').trim();

    if (!att) return false;

    var list = att.split('\n\n').filter(x => x && x.trim() !== '');

    return list.length > 0;

  } catch (e) {
    return false;
  }
}


// =====================================================
// FORMATAR DATA PARA INPUT DATE
// =====================================================
function convertActionDateToInput(value) {
  try {
    if (!value) return '';

    var parts = String(value).split('/');

    if (parts.length == 3) {
      return parts[2] + '-' + parts[1] + '-' + parts[0];
    }

    return String(value).slice(0, 10);
  } catch (e) {
    return '';
  }
}


// =====================================================
// TENTAR ALTERAR PRAZO DA AÇÃO
// =====================================================
function tryChangeActionDeadline(actionId, currentDeadline) {
  var currentValue = convertActionDateToInput(currentDeadline);

  if (window.Swal) {
    Swal.fire({
      icon: 'question',
      title: 'Alterar prazo da ação',
      text: 'Informe a nova data da ação.',
      input: 'date',
      inputValue: currentValue,
      showCancelButton: true,
      confirmButtonText: 'Alterar prazo',
      cancelButtonText: 'Cancelar',
      inputValidator: (value) => {
        if (!value) {
          return 'Informe uma data válida.';
        }
      }
    }).then((res) => {
      if (res.isConfirmed) {
        doPostChangeActionDeadline(actionId, res.value);
      }
    });

  } else {
    var novaData = prompt('Informe a nova data da ação no formato YYYY-MM-DD:', currentValue);

    if (novaData) {
      doPostChangeActionDeadline(actionId, novaData);
    }
  }
}


// =====================================================
// POST ALTERAR PRAZO DA AÇÃO
// =====================================================
function doPostChangeActionDeadline(actionId, deadline) {
  fetch('/desvios/acoes/' + actionId, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      cmd: 'alterar_prazo',
      deadline: deadline
    })
  })
  .then(r => r.json().then(j => ({ ok: r.ok, j })))
  .then(({ ok, j }) => {
    if (!ok) {
      throw new Error(j?.message || 'Erro ao alterar prazo.');
    }

    if (window.Swal) {
      Swal.fire({
        icon: 'success',
        title: 'Prazo alterado',
        text: j.message || 'Prazo da ação alterado com sucesso.'
      }).then(() => {
        window.location = '/desvios/acoes/' + actionId;
      });

    } else {
      alert(j.message || 'Prazo da ação alterado com sucesso.');
      window.location = '/desvios/acoes/' + actionId;
    }
  })
  .catch(err => {
    if (window.Swal) {
      Swal.fire({
        icon: 'error',
        title: 'Falha ao alterar prazo',
        text: err.message || 'Erro inesperado.'
      });

    } else {
      alert(err.message || 'Erro inesperado.');
    }
  });
}


// =====================================================
// TENTAR FINALIZAR AÇÃO
// =====================================================
function tryFinalizeAction(actionId) {
  if (!hasAttachmentsFor()) {
    if (window.Swal) {
      Swal.fire({
        icon: 'warning',
        title: 'Sem anexos',
        text: 'É necessário anexar pelo menos 1 arquivo para finalizar a ação.',
        confirmButtonText: 'OK'
      });

    } else {
      alert('Não há arquivo anexado.\nÉ necessário anexar pelo menos 1 arquivo para finalizar a ação.');
    }

    return;
  }

  if (window.Swal) {
    Swal.fire({
      icon: 'question',
      title: 'Finalizar ação?',
      text: 'Deseja finalizar esta ação?',
      showCancelButton: true,
      confirmButtonText: 'Finalizar',
      cancelButtonText: 'Cancelar'
    }).then((res) => {
      if (res.isConfirmed) {
        doPostFinalizeAction(actionId);
      }
    });

  } else {
    if (confirm('Deseja finalizar esta ação?')) {
      doPostFinalizeAction(actionId);
    }
  }
}

// =====================================================
// VALIDAR AÇÃO ATRASADA
//
// Reutiliza a mesma finalização do backend.
// O backend confirma a existência do anexo e altera
// o status da ação de 5 para 1.
// =====================================================
function tryValidateDelayedAction(actionId) {
  if (!hasAttachmentsFor()) {
    if (window.Swal) {
      Swal.fire({
        icon: 'warning',
        title: 'Sem anexos',
        text: 'É necessário anexar pelo menos 1 arquivo antes de validar a ação.',
        confirmButtonText: 'OK'
      });
    } else {
      alert(
        'É necessário anexar pelo menos 1 arquivo antes de validar a ação.'
      );
    }

    return;
  }

  if (window.Swal) {
    Swal.fire({
      icon: 'question',
      title: 'Validar ação atrasada?',
      text: 'Deseja validar e concluir esta ação?',
      showCancelButton: true,
      confirmButtonText: 'Validar',
      cancelButtonText: 'Cancelar'
    }).then(function (res) {
      if (res.isConfirmed) {
        doPostFinalizeAction(actionId);
      }
    });
  } else {
    if (confirm('Deseja validar e concluir esta ação?')) {
      doPostFinalizeAction(actionId);
    }
  }
}

// =====================================================
// POST FINALIZAR AÇÃO
// =====================================================
function doPostFinalizeAction(actionId) {
  fetch('/desvios/acoes/' + actionId, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      cmd: 'finalizar'
    })
  })
  .then(r => r.json().then(j => ({ ok: r.ok, j })))
  .then(({ ok, j }) => {
    if (!ok) {
      throw new Error(j?.message || 'Erro ao finalizar');
    }

    if (window.Swal) {
      Swal.fire({
        icon: 'success',
        title: 'Ação finalizada',
        text: j.message || 'Ação finalizada com sucesso.'
      }).then(() => {
        window.location = '/desvios/acoes';
      });

    } else {
      alert(j.message || 'Ação finalizada com sucesso.');
      window.location = '/desvios/acoes';
    }
  })
  .catch(err => {
    if (window.Swal) {
      Swal.fire({
        icon: 'error',
        title: 'Falha ao finalizar',
        text: err.message || 'Erro inesperado.'
      });

    } else {
      alert(err.message || 'Erro inesperado.');
    }
  });
}


// =====================================================
// START DA PÁGINA
// =====================================================
document.addEventListener('DOMContentLoaded', function () {
  closeAttachments();
  bindAttachmentInput();
  init();
});

// V1