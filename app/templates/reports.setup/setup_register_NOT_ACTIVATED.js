var df = JSON.parse({{df | tojson}})

init();
removeNav();

function init() {
    var myTable = document.createElement("table"),
    row = myTable.insertRow(), cell;

    for (let i = 0; i < Object.keys(df).length; i++) {
        cell = row.insertCell();
        cell.innerHTML = Object.keys(df)[i].split('_').join(' ');
        if (i != 7) {
            cell.style.maxWidth = "13vw";
        } else {
            cell.style.minWidth = "35vw";
        }
    }

    cell = row.insertCell();
    cell.innerHTML = " ";
    cell.style.width = "12vw";

    row.style.fontWeight = 'bold';
    row.style.background = '#163A8A';
    row.style.color = 'white';

    row = myTable.insertRow();

    for (let k = 0; k < Object.keys(df[Object.keys(df)[0]]).length; k++) {
        for (let i = 0; i < Object.keys(df).length; i++) {
            cell = row.insertCell();


            if (i == 0) {
                cell.style.width = "20vw";
            } else if (i == 1) {
                cell.style.width = "20vw";
            } else if (i == 2 || i == 3 || i == 4) {
                cell.style.width = "10vw";
            }

            if (i == 1) {
                cell.innerHTML = `<input onchange="submitData('` + Object.keys(df)[i] + `', '` + (k + 1) + `', this.value)" type="text" class="std_tbl_input" value="` + df[Object.keys(df)[i]][k] + `"/>`
            } else if (i == 4) {
                cell.innerHTML = `<input onchange="submitData('` + Object.keys(df)[i] + `', '` + (k + 1) + `', this.value)" type="number" class="std_tbl_input" value="` + df[Object.keys(df)[i]][k] + `"/>`
            } else {
                cell.innerHTML = `<input readonly type="text" class="std_tbl_input" value="` + df[Object.keys(df)[i]][k] + `"/>`
            }
        }

        cell = row.insertCell();
        cell.innerHTML = `<btn class="std_remove_btn" onclick="removeData('` + (k + 1) + `')">Excluir</btn>`;
        cell.style.width = "5vw";

        row = myTable.insertRow();
    }

    document.getElementById("table-container").innerHTML = '';
    myTable.lang = "pt-BR";
    myTable.className = "std_table";
    myTable.id = "cadastros_table"
    document.getElementById("table-container").appendChild(myTable);
}

function submitData(col, row, info) {
    var table = document.getElementById("cadastros_table");
    var code = table.rows[row].cells[0].querySelector('input').value;
    var workcenter = table.rows[row].cells[3].querySelector('input').value;
    var http = new XMLHttpRequest();

    http.open("POST", "/cadastros/parametros_setup?cmd=edit", false);
    http.setRequestHeader("Content-type","application/json");
    http.onreadystatechange = function () {
        df = JSON.parse(http.responseText);
        filter(code);
        init();
    }
    http.send(JSON.stringify([code, workcenter, info, col]));
}

function removeData(row) {
    var test = confirm('Toda a linha será deletada');
    var table = document.getElementById("cadastros_table");
    var code = table.rows[row].cells[0].querySelector('input').value;
    var workcenter = table.rows[row].cells[3].querySelector('input').value;

    if (test) {
        var http = new XMLHttpRequest();
        http.open("POST", "/cadastros/parametros_setup?cmd=delete", false);
        http.setRequestHeader("Content-type","application/json");
        http.onreadystatechange = function () {
            table.deleteRow(row);
            df = JSON.parse(http.responseText);
            init();
        }
        http.send(JSON.stringify([code, workcenter]));

    } else if (!test) {
        //pass;
    }

    return false
}

function addData() {
    document.querySelector('.cad_container').style.display = "block";
    document.querySelector('.cad_container').style.opacity = "1";
    document.querySelector('.blur_mask').style.filter = "blur(10px)";
    document.querySelector('#myVideo').style.filter = "blur(10px)";
}

function closeData() {
    document.querySelector('.blur_mask').style.filter = "";
    document.querySelector('#myVideo').style.filter = "";
    document.querySelector('.cad_container').style.opacity = "0";
    document.querySelector('.cad_container').style.display = "none";
}

function toNormal() {
    var area = document.getElementById("setup_area").value;
    var ct = document.getElementById("setup_ct").value;
    var material = document.getElementById("setup_material").value;
    var tools = document.getElementsByName("setup_tools")[0].value;
    var setup_time = document.getElementsByName("time")[0].value;
    var inputs = [material, tools, area, ct, setup_time]

    if (inputs.includes('') || inputs.includes('none')) {
        alert('Preencha os dados corretamente!');
    } else {
        var http = new XMLHttpRequest();
        http.open("POST", "/cadastros/parametros_setup?cmd=insert&data=" + inputs, false);
        http.setRequestHeader("Content-type","application/x-www-form-urlencoded");
        http.onreadystatechange = function () {
            df = JSON.parse(http.responseText);
            init();
        }
        http.send();

        closeData();

        area.value = ""
        ct.value = ""
        material.value = ""
        tools.value = ""
        setup_time.value = ""
    }
}

function filter(info) {
    var input, filter, table, tr, td, i, txtValue, display;    display = []
    table = document.getElementById("cadastros_table");
    tr = table.getElementsByTagName("tr");
    filters = [[0]]
    for (i = 0; i < tr.length; i++) {
        var line = []
        filters.forEach((item, l) => {
            var id, index
            index = item[0];
            filter = info.toUpperCase();
            if (i > 0 && filter != '') {
                td = tr[i].getElementsByTagName("td")[index];
                if (td) {
                    txtValue = td.innerHTML.split('value="')[1].split('"')[0];
                    if (txtValue.toUpperCase().indexOf(filter) > -1) {
                        line.push("yes");
                    } else {
                        line.push("none");
                    }
                }
            } else if (i > 0 && filter == '') {
                line.push("no_filter");
            }
        });
        display.push(line);
    }

    for (k = 1; k < tr.length - 1; k++) {
        if (k > 0) {
            if (display[k].includes("none")) {
                tr[k].style.display = "";
            } else {
                tr[k].scrollIntoView({
                    behavior: 'smooth',
                    block: 'center',
                    inline: 'center'
                });
            }
        }
    }
}

function filter_dynamic() {
  var input, filter, table, tr, td, i, txtValue, display;
  display = []
  table = document.getElementById("cadastros_table");
  tr = table.getElementsByTagName("tr");
  filters = [[0, 'mat_filter']]
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
               txtValue = td.innerHTML.split('value="')[1].split('"')[0];
               if (txtValue.toUpperCase().indexOf(filter) > -1) {
                  line.push("yes");
               } else {
                  line.push("none");
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

function filterByArea(strValue) {
    var http = new XMLHttpRequest();
    http.open("POST", "/cadastros/parametros_setup?searchByArea=" + strValue, false);
    http.setRequestHeader("Content-type","application/json");
    http.onreadystatechange = function () {
        if (http.readyState === 4 && http.status === 200) {
            document.getElementById('setup_ct').innerHTML = '<option value="" disabled selected>Centro de Trabalho</option>';
            document.getElementById('setup_material').innerHTML = '<option value="" disabled selected>Material</option>';

            ct = JSON.parse(http.responseText)[0];
            ct.forEach(function(valor) {
                document.getElementById('setup_ct').innerHTML += '<option value="' + valor + '">' + valor + '</option>';
            });

            material = JSON.parse(http.responseText)[1];
            material.forEach(function(valor) {
                document.getElementById('setup_material').innerHTML += '<option value="' + valor + '">' + valor + '</option>';
            });
        }
    }

    http.send();
}

function filterByCt(strValue) {
    var http = new XMLHttpRequest();
    http.open("POST", "/cadastros/parametros_setup?searchByCt=" + strValue, false);
    http.setRequestHeader("Content-type","application/json");
    http.onreadystatechange = function () {
        if (http.readyState === 4 && http.status === 200) {
            document.getElementById('setup_material').innerHTML = '<option value="" disabled selected>Material</option>';

            material = JSON.parse(http.responseText);
            material.forEach(function(valor) {
                document.getElementById('setup_material').innerHTML += '<option value="' + valor + '">' + valor + '</option>';
            });
        }
    }

    http.send();
}