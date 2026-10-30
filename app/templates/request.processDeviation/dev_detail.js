closeAttachments()

var actionsSummary = {{ actions_summary | default({
  'total': 0,
  'done': 0,
  'pending': 0,
  'percent': 100,
  'canFinalize': true,
  'statusText': 'Sem ações cadastradas'
}) | tojson }};

var actionsPendingText = "{{ actions_pending_text | default('0 ações pendentes') }}";
var mails = {{ mails | default([]) | tojson }};


// ===== ADIÇÃO: DATA FIM RENOVADA =====
function formatRenewedFinalDate(tableData, k, info) {
  try {
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
// BOTÃO NOVA AÇÃO
// =====================================================
function appendNewActionButton(cell, deviationId, devStatus) {
  try {
    if (!cell) return;

    var canCreateAction = (
      ('{{ admin }}' == '1' || '{{ owner }}' == '1') &&
      devStatus != 3 &&
      devStatus != 4
    );

    if (!canCreateAction) return;

    cell.appendChild(document.createElement("br"));

    var novaAcaoButton = document.createElement("button");

    novaAcaoButton.type = "button";
    novaAcaoButton.style.minWidth = "7vw";
    novaAcaoButton.style.marginTop = "4px";
    novaAcaoButton.style.background = "rgb(45, 90, 187)";
    novaAcaoButton.className = "table_btn";
    novaAcaoButton.name = "nova_acao";
    novaAcaoButton.innerText = "Nova ação";

    novaAcaoButton.onclick = function (e) {
      e.stopPropagation();
      openNewActionModal(deviationId);
    };

    cell.appendChild(novaAcaoButton);

  } catch (e) {}
}


function init() {
  var myTable = document.createElement("table"),
      row = myTable.insertRow(), cell;
  var ct = 'None'
  var perrow = 1;

  var tableData = {{table | tojson}};
  //console.log(tableData);
  //console.log("ANEXO =", tableData[1][9]);
  //console.log(JSON.stringify(tableData[1][9]));
  tableData.forEach((entry, k) => {
    entry.forEach((info, i) => {
      if (k > 0) {

        if (i != 1 && i != 8 && i != 9) {
          cell = row.insertCell();

          // ===== ADIÇÃO: DATA FIM RENOVADA =====
          if (i == 6) {
            cell.innerHTML = formatRenewedFinalDate(tableData, k, info);
          } else {
            cell.innerHTML = info;
          }
        }

        if (i == 2) {
          cell.style.width = '20vw'
        }

        if (i == 0) {
          cell.style.width = "12vw"
          cell.style.textDecoration = "underline";
          cell.onclick = function () {
            var url = '/desvios/detalhes/fisico?id=' + info
            window.open(url, '_blank');
          };

          cell.innerHTML = `<button type="button" style="min-width: 9vw" class="table_btn" name="col_` + i + `"><b>Revisão ` + entry[1] + `</b></button>`;
          
          //Codigo antigo
          // cell = row.insertCell();
          //cell.innerHTML = `<button type="button" style="min-width: 7vw" class="table_btn" onclick="openAttachments('` + entry[0] + `','` + entry[9] + `')" name="col_` + i + `">Anexos</button>`;
          //I NEW CODE
          cell = row.insertCell();

          let anexosBtn = document.createElement("button");

          anexosBtn.type = "button";
          anexosBtn.style.minWidth = "7vw";
          anexosBtn.className = "table_btn";
          anexosBtn.name = "col_" + i;
          anexosBtn.innerText = "Anexos";

          anexosBtn.onclick = function () {
              openAttachments(entry[0], entry[9]);
          };

          cell.appendChild(anexosBtn);
          //F NEW CODE

        } else if (i == 7) {
          if (info == 0) {
            cell.style.backgroundColor = "yellow";
            cell.style.color = "black";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Aguardando Aprovação';
          } else if (info == 1) {
            cell.style.backgroundColor = "#228c22";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Em andamento';
          } else if (info == 2) {
            cell.style.backgroundColor = "red";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Recusado';
          } else if (info == 3) {
            cell.style.backgroundColor = "gray";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Cancelado';
          } else if (info == 4) {
            cell.style.backgroundColor = "gray";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Finalizado';
          } else if (info == 5) {
            cell.style.backgroundColor = "#228c22";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Em andamento';
          } else if (info == 6) {
            cell.style.backgroundColor = "red";
            cell.style.color = "white";
            cell.style.border = "0";
            cell.style.outline = "0";
            cell.innerHTML = 'Atrasado';
          }

          // ===== COLUNA AÇÕES =====
          cell = row.insertCell();

          if ('{{resp}}' == '1') {

            cell.innerHTML = '';

            if (entry[7] == 4) {
              const semAcao = document.createElement("button");
              semAcao.type = "button";
              semAcao.style.minWidth = "7vw";
              semAcao.className = "table_btn";
              semAcao.disabled = true;
              semAcao.innerText = "Sem ação disponivel";
              cell.appendChild(semAcao);

              appendNewActionButton(cell, entry[0], entry[7]);
              return;
            }

            if (entry[7] == 0) {
              cell.style.textDecoration = "underline";
              cell.onclick = function () {
                var id = entry[0];
                var url = '/desvios/detalhes?cancelar=' + id
                window.location = url
              };

              const cancelar = document.createElement("button");
              cancelar.type = "button";
              cancelar.style.minWidth = "7vw";
              cancelar.className = "table_btn";
              cancelar.name = "col_" + i;
              cancelar.innerText = "Cancelar";
              cell.appendChild(cancelar);

              if ('{{admin}}' == '1') {
                const editarAdmAguardando = document.createElement("button");
                editarAdmAguardando.type = "button";
                editarAdmAguardando.style.minWidth = "7vw";
                editarAdmAguardando.style.textDecoration = "none";
                editarAdmAguardando.style.marginTop = "4px";
                editarAdmAguardando.className = "table_btn";
                editarAdmAguardando.name = "col_" + i;
                editarAdmAguardando.innerText = "Editar";

                editarAdmAguardando.onclick = function (e) {
                  e.stopPropagation();
                  var id = entry[0];
                  var url = '/desvios/gerar?editar=' + id;
                  window.location = url;
                };

                cell.appendChild(editarAdmAguardando);
              }

            } else if (entry[7] == 5 || entry[7] == 6) {

              var count = 0;

              if ('{{resp}}' == '1' && entry[8] < 5) {
                const hasPendingApproval = tableData.some(otherEntry =>
                  otherEntry[7] == 0
                );

                if (!hasPendingApproval) {
                  cell.style.textDecoration = "underline";
                  const id = entry[0];
                  const renovarButton = document.createElement("button");
                  renovarButton.type = "button";
                  renovarButton.style.minWidth = "7vw";
                  renovarButton.className = "table_btn";
                  renovarButton.name = "col_" + i;
                  renovarButton.innerText = "Renovar";
                  renovarButton.onclick = function () {
                    var url = '/desvios/renovar?id=' + id.slice(0, -2);
                    window.location = url;
                  };
                  cell.appendChild(renovarButton);
                }

                count = 1
              }

              if ("{{admin}}" == '1') {
                cell.style.textDecoration = "underline";
                var id = entry[0];

                var actionStatusLabel = document.createElement("div");
                actionStatusLabel.style.fontSize = "12px";
                actionStatusLabel.style.fontWeight = "600";
                actionStatusLabel.style.marginBottom = "6px";
                actionStatusLabel.style.textDecoration = "none";
                actionStatusLabel.style.lineHeight = "14px";
                actionStatusLabel.innerText = actionsPendingText;

                if (actionsSummary.pending > 0) {
                  actionStatusLabel.style.color = "#b36b00";
                } else {
                  actionStatusLabel.style.color = "#228c22";
                }

                var finalizarButton = document.createElement("button");
                finalizarButton.type = "button"; 
                finalizarButton.style.minWidth = "7vw";
                finalizarButton.style.marginTop = "4px";
                finalizarButton.style.background = "rgb(45, 90, 187)";
                finalizarButton.className = "table_btn";
                finalizarButton.name = "col_" + i;
                finalizarButton.innerText = "Finalizar";

                function postFinalize(did) {
                  var http = new XMLHttpRequest();
                  http.open("POST", "/desvios/detalhes?finalizar=" + did, false);
                  http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
                  http.onreadystatechange = function () {
                    if (http.readyState == 4) {
                      if (http.responseText == 'ACCESS DENIED') {
                        window.location = '/denied';
                      } else if (http.responseText == 'ACTIONS_PENDING') {
                        if (window.Swal) {
                          Swal.fire({
                            icon: 'warning',
                            title: 'Ações pendentes',
                            text: actionsSummary.statusText || 'Existem ações pendentes. Finalize todas as ações antes de finalizar o desvio.',
                            confirmButtonText: 'OK'
                          });
                        } else {
                          alert(actionsSummary.statusText || 'Existem ações pendentes. Finalize todas as ações antes de finalizar o desvio.');
                        }
                      } else {
                        location.reload();
                      }
                    }
                  };
                  http.send();
                }

                finalizarButton.onclick = function () {
                  tryFinalize(id, postFinalize);
                };
                cell.appendChild(finalizarButton);

                const editarAdmAndamento = document.createElement("button");
                editarAdmAndamento.type = "button";
                editarAdmAndamento.style.minWidth = "7vw";
                editarAdmAndamento.style.textDecoration = "none";
                editarAdmAndamento.style.marginTop = "4px";
                editarAdmAndamento.className = "table_btn";
                editarAdmAndamento.name = "col_" + i;
                editarAdmAndamento.innerText = "Editar";

                editarAdmAndamento.onclick = function () {
                  var url = '/desvios/gerar?editar=' + id;
                  window.location = url;
                };

                cell.appendChild(editarAdmAndamento);

                count = 1
              }

              if (count == 0) {
                const semAcao = document.createElement("button");
                semAcao.type = "button";
                semAcao.style.minWidth = "7vw";
                semAcao.className = "table_btn";
                semAcao.disabled = true;
                semAcao.innerText = "Sem ação disponivel";
                cell.appendChild(semAcao);
              }

            } else if (
              (entry[7] == 2 && '{{owner}}' == '1') ||
              ('{{admin}}' == '1' && entry[7] != 3 && entry[7] != 4)
            ) {

              cell.style.textDecoration = "underline";
              cell.onclick = function () {
                var id = entry[0];
                var url = '/desvios/gerar?editar=' + id
                window.location = url
              };

              const editar = document.createElement("button");
              editar.type = "button";
              editar.style.minWidth = "7vw";
              editar.className = "table_btn";
              editar.style.marginTop = "4px";
              editar.name = "col_" + i;
              editar.innerText = "Editar";
              cell.appendChild(editar);

            } else {
              const semAcao = document.createElement("button");
              semAcao.type = "button";
              semAcao.style.minWidth = "7vw";
              semAcao.className = "table_btn";
              semAcao.disabled = true;
              semAcao.innerText = "Sem ação disponivel";
              cell.appendChild(semAcao);
            }

            appendNewActionButton(cell, entry[0], entry[7]);
          }

        }

      } else {
        // Cabeçalho
        if (i != 1 && i != 8 && i != 9) {
          cell = row.insertCell();
          cell.innerHTML = info;
        }
        if (i == 0) {
          cell = row.insertCell();
          cell.innerHTML = 'ANEXOS';
        } else if (i == 7) {
          if ('{{admin}}' == '1') {
            cell.innerHTML = info;
            cell = row.insertCell();
            cell.innerHTML = 'AÇÕES'
          }
        }
      }

    });

    if (k == 0) {
      row.style.fontWeight = 'bold';
      row.style.background = '#163A8A';
      row.style.color = 'white';
    }

    var next = k + 1;
    if (next%perrow==0) {
      row = myTable.insertRow();
    }

  });

  myTable.lang = "pt-BR"
  myTable.id = "paradas_table"
  document.getElementById("table-container").appendChild(myTable);

  const topDeleteBtn = document.getElementById('add_btn');
  if (topDeleteBtn) {
    const devId = topDeleteBtn.getAttribute('data-devid') || '';
    const baseId = devId.split('-').slice(0,2).join('-');
    topDeleteBtn.addEventListener('click', function () {
      confirmAndDeleteDeviation(baseId);
    });
  }
}
init();

function myFunction() {
  var input, filter, table, tr, td, i, txtValue, display;
  display = []
  table = document.getElementById("paradas_table");
  tr = table.getElementsByTagName("tr");
  filters = [[0, 'solicitante'], [1, 'equipe'], [2, 'ct'], [3, 'familia'], [4, 'data'], [5, 'n_desvio'], [8, 'status']]
  for (i = 0; i < tr.length; i++) {
    var line = []
    filters.forEach((item, l) => {
      var id, index
      id = item[1]
      index = item[0]

      input = document.getElementById(id);
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
    display.push(line)
  }

  for (k = 1; k < tr.length - 1; k++) {
    if (k > 0) {
      if (display[k].includes("none")) {
        tr[k].style.display = "none";
      } else {
        tr[k].style.display = "";
      }
    }
  }
}

function openAttachments(id, str) {
  document.getElementById('lab_form').action = ("/desvios/detalhes?anexo=" + id)
  str = str.split('\n\n').slice(0, -1)

  document.querySelector(".blur_wrap").style.pointerEvents = "none";
  var overlay = document.querySelector('#box');
  overlay.style.display = "block";
  overlay.style.opacity = "1";

  var myTable = document.createElement("table"),
      row = myTable.insertRow(), cell;

  cell = row.insertCell();
  cell.innerHTML = 'ANEXOS'
  cell.style.width = '85vw';
  cell.style.overflow = 'hidden';
  cell.style.textOverflow = 'ellipsis';

  if (str.length !== 0) {
    cell.style.width = '65vw';
    cell = row.insertCell();
    cell.innerHTML = '';
    cell.style.width = '20vw';
    cell.style.overflow = 'hidden';
    cell.style.textOverflow = 'ellipsis';

    if ('{{resp}}' == '1') {
      cell = row.insertCell();
      cell.style.width = "5vw";
      cell.style.maxWidth = "5vw";
      document.getElementById('lab_form').style.display = 'block'
    }
  } else {
    if ('{{resp}}' == '1') {
      document.getElementById('lab_form').style.display = 'block'
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
        `<button class="table_btn" onclick="window.location='/desvios/detalhes/anexo/download?anexo=` + str[k] + `&id=` + id + `'"
                style="padding:15px;width:inherit;background-color:#228C22">
            <i class="fa fa-download"></i> DOWNLOAD <b>` + imageType + `</b>
         </button>`;

      if ('{{resp}}' == '1') {
        cell = row.insertCell();
        cell.style.width = "5vw";
        cell.style.maxWidth = "5vw";

        cell.innerHTML =
          `<button class="remove" onclick="window.location='/desvios/detalhes?anexo=` + str[k] + `&id=` + id + `'">&times;</button>`;
      }
      row = myTable.insertRow();
    }
  } else {
    cell = row.insertCell();
    cell.style.width = '85vw'
    cell.innerHTML = 'SEM ANEXOS ENVIADOS'
  }

  document.getElementById("lab-container").innerHTML = '';
  myTable.lang = "pt-BR";
  myTable.id = "paradas_table";
  document.getElementById("lab-container").appendChild(myTable);
}

function closeAttachments() {
  var overlay = document.querySelector('#box');
  overlay.style.opacity = "0";
  overlay.style.display = "none";
  document.querySelector(".blur_wrap").style.pointerEvents = "auto";
}

/* ===================== Validação de anexos no Finalizar (SweetAlert2) ===================== */

function hasAttachmentsFor(did) {
  try {
    if (!window.__dsvTableData && Array.isArray({{table | tojson}})) {
      window.__dsvTableData = {{table | tojson}};
    }
    var tdata = window.__dsvTableData || [];
    var row = tdata.find && tdata.find(e => e && e[0] === did);
    if (!row) return false;
    var att = (row[9] || '').trim();
    if (!att) return false;
    var list = att.split('\n\n').filter(x => x && x.trim() !== '');
    return list.length > 0;
   } catch (e) {
    return false;
  }
}

function tryFinalize(finalizeId, doPostFinalize) {
  if ('{{ admin }}' != '1' && !actionsSummary.canFinalize) {
    if (window.Swal) {
      Swal.fire({
        icon: 'warning',
        title: 'Ações pendentes',
        text: actionsSummary.statusText || 'Existem ações pendentes. Finalize todas as ações antes de finalizar o desvio.',
        confirmButtonText: 'OK'
      });
    } else {
      alert(actionsSummary.statusText || 'Existem ações pendentes. Finalize todas as ações antes de finalizar o desvio.');
    }
    return;
  }

  if (typeof doPostFinalize === 'function') {
    doPostFinalize(finalizeId);
  }
}



/* ===================== NOVA AÇÃO EM REVISÃO ===================== */
function ensureNewActionMailDatalist() {
  try {
    var listId = 'options_mails_new_action';

    if (document.getElementById(listId)) return listId;

    var datalist = document.createElement('datalist');
    datalist.id = listId;

    (mails || []).forEach(function (mail) {
      var opt = document.createElement('option');
      opt.value = mail;
      datalist.appendChild(opt);
    });

    document.body.appendChild(datalist);

    return listId;

  } catch (e) {
    return '';
  }
}

function openNewActionModal(deviationId) {
  var mailsOptions = '';

  for (var i = 0; i < mails.length; i++) {
    mailsOptions += '<option value="' + mails[i] + '"></option>';
  }

  if (window.Swal) {
    Swal.fire({
      title: 'Nova ação',
      html:
        '<textarea id="newActionText" class="swal2-textarea" placeholder="Descrição da ação"></textarea>' +
        '<input list="options_mails" id="newActionUser" class="swal2-input" placeholder="E-mail do responsável">' +
        '<datalist id="options_mails">' + mailsOptions + '</datalist>' +
        '<input id="newActionDeadline" class="swal2-input" type="date">',
      showCancelButton: true,
      confirmButtonText: 'Adicionar',
      cancelButtonText: 'Cancelar',
      focusConfirm: false,
      preConfirm: () => {
        const text = document.getElementById('newActionText').value;
        const userId = document.getElementById('newActionUser').value;
        const deadline = document.getElementById('newActionDeadline').value;

        if (!text || !userId || !deadline) {
          Swal.showValidationMessage('Preencha descrição, responsável e prazo.');
          return false;
        }

        if (!mails.includes(userId)) {
          Swal.showValidationMessage('Email preenchido no plano de ação não foi encontrado na base de dados!');
          return false;
        }

        return { text, userId, deadline };
      }
    }).then((res) => {
      if (res.isConfirmed) {
        doPostNewAction(deviationId, res.value);
      }
    });

  } else {
    const text = prompt('Descrição da ação:');
    if (!text) return;

    const userId = prompt('E-mail do responsável:');
    if (!userId) return;

    const deadline = prompt('Prazo da ação no formato YYYY-MM-DD:');
    if (!deadline) return;

    doPostNewAction(deviationId, { text, userId, deadline });
  }
}

function doPostNewAction(deviationId, payload) {
  fetch('/desvios/detalhes?nova_acao=' + deviationId, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
  .then(r => r.json().then(j => ({ ok: r.ok, j })))
  .then(({ ok, j }) => {
    if (!ok) {
      throw new Error(j?.message || 'Erro ao adicionar ação.');
    }

    if (window.Swal) {
      Swal.fire({
        icon: 'success',
        title: 'Ação adicionada',
        text: j.message || 'Nova ação adicionada com sucesso.'
      }).then(() => {
        window.location.reload();
      });
    } else {
      alert(j.message || 'Nova ação adicionada com sucesso.');
      window.location.reload();
    }
  })
  .catch(err => {
    if (window.Swal) {
      Swal.fire({
        icon: 'error',
        title: 'Falha ao adicionar ação',
        text: err.message || 'Erro inesperado.'
      });
    } else {
      alert(err.message || 'Erro inesperado.');
    }
  });
}


/* ===================== EXCLUIR DESVIO — ADMIN (topo) ===================== */

function confirmAndDeleteDeviation(baseId) {
  if (window.Swal) {
    Swal.fire({
      icon: 'warning',
      title: 'Excluir desvio?',
      html: `Esta ação removerá <b>todas as revisões</b> do desvio <code>${baseId}</code>, incluindo anexos. Não será possível desfazer.`,
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonText: 'Cancelar',
      confirmButtonText: 'Excluir'
    }).then((res) => {
      if (res.isConfirmed) {
        doDeleteDeviation(baseId);
      }
    });
  } else {
    if (confirm(`Excluir TODAS as revisões do desvio ${baseId}?`)) {
      doDeleteDeviation(baseId);
    }
  }
}

function doDeleteDeviation(baseId) {
  fetch('/desvios/excluir', {
    method: 'POST',
    headers: { 'Content-Type':'application/json' },
    body: JSON.stringify({ id: baseId })
  })
  .then(r => r.json().then(j => ({ ok: r.ok, j })))
  .then(({ ok, j }) => {
    if (!ok) throw new Error(j?.message || 'Erro ao excluir');

    if (window.Swal) {
      Swal.fire({ icon:'success', title:'Excluído', text:j.message || 'Desvio excluído.' })
        .then(()=> window.location = '/desvios/consultar');
    } else {
      alert(j.message || 'Desvio excluído.');
      window.location = '/desvios/consultar';
    }
  })
  .catch(err => {
    if (window.Swal) {
      Swal.fire({ icon:'error', title:'Falha ao excluir', text: err.message || 'Erro inesperado.' });
    } else {
      alert(err.message || 'Erro inesperado.');
    }
  });
}
