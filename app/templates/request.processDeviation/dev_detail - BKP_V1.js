closeAttachments()

function init() {
  var myTable = document.createElement("table"),
      row = myTable.insertRow(), cell;
  var ct = 'None'
  var perrow = 1;

  var tableData = {{table | tojson}};
  tableData.forEach((entry, k) => {
    entry.forEach((info, i) => {
      if (k > 0) {

        if (i != 1 && i != 8 && i != 9) {
          cell = row.insertCell();
          cell.innerHTML = info;
        }

        if (i == 2) {
          cell.style.width = '20vw'
        }

        if (i == 0) {
          cell.style.width = "12vw"
          cell.style.textDecoration = "underline";
          cell.onclick = function () { // caso o usuario clique, ele é redirecionado para a pagina de edicao da demanda
            var url = '/desvios/detalhes/fisico?id=' + info
            window.open(url, '_blank');
          };
          // ⬇️ BOTÃO DE REVISÃO (HTML real)
          cell.innerHTML = `<button type="button" style="min-width: 9vw" class="table_btn" name="col_` + i + `"><b>Revisão ` + entry[1] + `</b></button>`;

          // ⬇️ BOTÃO ANEXOS (HTML real)
          cell = row.insertCell();
          cell.innerHTML = `<button type="button" style="min-width: 7vw" class="table_btn" onclick="openAttachments('` + entry[0] + `','` + entry[9] + `')" name="col_` + i + `">Anexos</button>`;

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
            cell.innerHTML = 'Aprovado';
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
            cell.innerHTML = 'Vencido';
          }

          // ===== COLUNA AÇÕES =====
          cell = row.insertCell();

          if ('{{resp}}' == '1') {

            cell.innerHTML = '';

            // ✅ FINALIZADO => Sem ação disponível na coluna AÇÕES
            if (entry[7] == 4) {
              const semAcao = document.createElement("button");
              semAcao.type = "button";
              semAcao.style.minWidth = "7vw";
              semAcao.className = "table_btn";
              semAcao.disabled = true;
              semAcao.innerText = "Sem ação disponivel";
              cell.appendChild(semAcao);
              return;
            }

            if (entry[7] == 0) {
              cell.style.textDecoration = "underline";
              cell.onclick = function () {
                var id = entry[0];
                var url = '/desvios/detalhes?cancelar=' + id
                window.location = url
              };

              // ⬇️ BOTÃO CANCELAR (HTML real)
              const cancelar = document.createElement("button");
              cancelar.type = "button";
              cancelar.style.minWidth = "7vw";
              cancelar.className = "table_btn";
              cancelar.name = "col_" + i;
              cancelar.innerText = "Cancelar";
              cell.appendChild(cancelar);

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

              // Admin: FINALIZAR (mantido)
              if ("{{admin}}" == '1') {
                cell.style.textDecoration = "underline";
                var id = entry[0];

                var finalizarButton = document.createElement("button");
                finalizarButton.type = "button";
                finalizarButton.style.minWidth = "7vw";
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

            } else if (tableData.length == 2 && ((entry[7] == 2 && '{{min_status}}' != '0') || '{{admin}}' == '1' || '{{resp}}' == '1')) {
              cell.style.textDecoration = "underline";
              cell.onclick = function () {
                var id = entry[0];
                var url = '/desvios/gerar?editar=' + id
                window.location = url
              };

              // ⬇️ BOTÃO EDITAR (HTML real)
              const editar = document.createElement("button");
              editar.type = "button";
              editar.style.minWidth = "7vw";
              editar.className = "table_btn";
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

  // ====== Bind do botão EXCLUIR no topo (somente admin) ======
  const topDeleteBtn = document.getElementById('add_btn');
  if (topDeleteBtn) {
    const devId = topDeleteBtn.getAttribute('data-devid') || '';
    const baseId = devId.split('-').slice(0,2).join('-'); // AAAA-NNNN
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

  // Cabeçalho
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
  // Linhas de anexos
  if (str.length !== 0) {
    for (let k = 0; k < str.length; k++) {
      cell = row.insertCell();
      cell.innerHTML = str[k];

      cell = row.insertCell();
      let imageType = str[k].split('.')[str[k].split('.').length - 1].toUpperCase();

      // ⬇️ BOTÃO DOWNLOAD (HTML real)
      cell.innerHTML =
        `<button class="table_btn" onclick="window.location='/desvios/detalhes/anexo/download?anexo=` + str[k] + `&id=` + id + `'"
                style="padding:15px;width:inherit;background-color:#228C22">
            <i class="fa fa-download"></i> DOWNLOAD <b>` + imageType + `</b>
         </button>`;

      if ('{{resp}}' == '1') {
        cell = row.insertCell();
        cell.style.width = "5vw";
        cell.style.maxWidth = "5vw";

        // ⬇️ BOTÃO REMOVER (HTML real)
        cell.innerHTML =
          `<button class="remove" onclick="window.location='/desvios/detalhes?anexo=` + str[k] + `&id=` + id + `'"">&times;</button>`;
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
  if (!hasAttachmentsFor(finalizeId)) {
    if (window.Swal) {
      Swal.fire({
        icon: 'warning',
        title: 'Sem anexos',
        text: 'É necessário anexar pelo menos 1 arquivo para finalizar o desvio.',
        confirmButtonText: 'OK'
      });
    } else {
      alert('Não há arquivo anexado.\nÉ necessário anexar pelo menos 1 arquivo para finalizar o desvio.');
    }
    return;
  }
  if (typeof doPostFinalize === 'function') {
    doPostFinalize(finalizeId);
  }
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