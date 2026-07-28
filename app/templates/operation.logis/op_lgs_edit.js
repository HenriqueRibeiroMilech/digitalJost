var data_to_update;
function changeLoc(loc) {
    window.location = loc;
}

function showInfo() {
    document.querySelector(".blur_wrap").style.filter = "blur(6px)";
    document.querySelector(".blur_wrap").style.pointerEvents = "none";
    var overlay = document.querySelector(".op_lgs_overlay");
    overlay.style.display = "block";
    overlay.style.opacity = "1";
}

function closeInfo() {
    var overlay = document.querySelector(".op_lgs_overlay");
    overlay.style.opacity = "0";
    overlay.style.display = "none";
    document.querySelector(".blur_wrap").style.filter = "none";
    document.querySelector(".blur_wrap").style.pointerEvents = "auto";
}

const classes = ["lgs_good", "lgs_mid", "lgs_bad"];

var areas = ['Entregas', 'Matéria Prima', 'Manufaturados'];
var info = 'Entregas';
var filter = document.getElementById('date').value

function changeInfo(text) {
    var next = areas.indexOf(text) + 1;
    if (next > 2) {
        next = 0;
    }
    var btn = document.getElementById('area');
    btn.innerHTML = areas[next];
    var filter = document.getElementById('date').value;

    checked = false;
    createTable(areas[next], filter);
}

function changeDate(date) {
    var btn = document.getElementById('area')
    createTable(btn.innerHTML, date);
    checked = false;
    create_new = false;
}

function changeBtnVal(col, id) {
    var input = document.getElementById("aux_" + col + "_" + id);
    var val = input.value;
    var new_val = parseInt(val) + 1;
    if (new_val > 2) {
        new_val = 0;
    }
    input.value = new_val;
    var btn = document.getElementById("btn_" + col + "_" + id);
    btn.className = classes[new_val];
    postChanges(id);
}

function checkEmpty(data, date) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/op/logistica/check", true);
    xhr.setRequestHeader("Content-type","application/json");

    xhr.onreadystatechange = function () {
        if (xhr.readyState == 4) {
            create_new = true;
            checked = true;
            var btn = document.getElementById('area');
            copyTable(btn.innerHTML, xhr.responseText);
        }
    }

    var params = JSON.stringify([data, date]);
    xhr.send(params);
}

function createTable(data, date) {
    var xhr = new XMLHttpRequest();

    xhr.open("POST", "/op/logistica/edit?copy=false", true);
    xhr.setRequestHeader("Content-type","application/json");

    xhr.onreadystatechange = function () {
        if (xhr.readyState == 4) {
            var test_df = JSON.parse(xhr.responseText);
            genElement(test_df);
            var btn = document.getElementById('area')
            if (Object.keys(test_df[Object.keys(test_df)[0]]).length == 0 && !checked) {
                document.getElementById('confirmData').style.display = 'table'
                data_to_update = date
            }


        }
    }

    var params = JSON.stringify([data, date]);
    xhr.send(params);
}



function updateData(action) {

    var btn = document.getElementById('area')

    if (action == 1) {
        var d = new Date(data_to_update)
        official = new Date(d.setDate(d.getDate() - 1));
        checkEmpty(btn.innerHTML, official)
    }

    var inputs = document.querySelectorAll('textarea');
    inputs.forEach(function(item) {
        item.style.height = item.scrollHeight + 1 + 'px';
    });

    document.getElementById('confirmData').style.display = 'none'

}

function copyTable(data, date) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/op/logistica/edit?copy=true", true);
    xhr.setRequestHeader("Content-type","application/json");

    xhr.onreadystatechange = function () {
        if (xhr.readyState == 4) {
            iter_df = JSON.parse(xhr.responseText);
            genElement(iter_df);
            var df_len = Object.keys(iter_df[Object.keys(iter_df)[0]]).length;

            for (let i = 0; i < df_len; i++) {
                setTimeout(function() {
                    postChanges(i);
                }, 200 * i);
            }

            var inputs = document.querySelectorAll('textarea');
            inputs.forEach(function(item) {
                item.style.height = item.scrollHeight + 1 + 'px';
            });

            setTimeout(function() {
                create_new = false;
            }, 202 * df_len);
        }
    }

    var params = JSON.stringify([data, date]);
    xhr.send(params);
}

function genElement(df) {
    var myTable = document.createElement("table"),
    row = myTable.insertRow(), cell;
    var btn = document.getElementById('area');

    for (let i = 0; i < Object.keys(df).length - 1; i++) {
        cell = row.insertCell();
        if (i < Object.keys(df).length - 2) {
            cell.innerHTML = Object.keys(df)[i].split('_').join(' ');
            if (Object.keys(df)[i].split('_').join(' ') == 'Quantity') {
                cell.innerHTML = 'QTD';
            }
            if ((i == 0 || i == 4 || i == 2) && btn.innerHTML == 'Entregas') {
                cell.style.maxWidth = "5vw";
            } else {
                cell.style.maxWidth = "12vw";
            }
        } else {
            cell.innerHTML = '';
            cell.style.maxWidth = "5vw";
        }
    }

    row = myTable.insertRow();

    for (let k = 0; k < Object.keys(df['Date']).length; k++) {
        for (let i = 0; i < Object.keys(df).length - 1; i++) {
            cell = row.insertCell();
            cell.style.whiteSpace = 'pre-wrap';
            cell.style.maxWidth = "none";
            cell.style.height = 'auto';

            if (i < Object.keys(df).length - 2) {
                if ((i == 0 || i == 4) && btn.innerHTML == 'Entregas') {
                    cell.innerHTML = `<input type="hidden" id="aux_` + i + `_` + k + `" name="col_` + i + `_` + k + `" value="` + df[Object.keys(df)[i]][k] + `"/>
                                      <button id="btn_` + i + `_` + k + `" type="button" onclick="changeBtnVal('` + i + `','` + k + `')" class="`+ classes[df[Object.keys(df)[i]][k]] + `"/></button>`
                    cell.style.maxWidth = "5vw";
                } else if (i == 4 && btn.innerHTML == 'Manufaturados') {
                    cell.innerHTML = `<input type="hidden" name="col_` + i + `_` + k + `" value="JOST"/>JOST`
                    cell.style.maxWidth = "4vw";
                    cell.style.color = "rgb(255,255,195)";
                } else if ((i == 8 && btn.innerHTML == 'Entregas') || (i == 7 && btn.innerHTML != 'Entregas')) {
                    cell.innerHTML = `<button class="op_lgs_table_btn" type="button">&times</button>`
                    cell.style.maxWidth = "5vw";
                } else if ((i == 2 && btn.innerHTML == 'Entregas')) {
                    cell.innerHTML = `<input onchange="postChanges(` + k + `)" name="col_` + i + `_` + k + `" type="number" min="0" placeholder="Digite aqui..." id="col_` + i + `" value="` + df[Object.keys(df)[i]][k] + `" class="op_lgs_text" style="width:4vw;"/>`
                    cell.style.maxWidth = "4vw";
                } else {
                    cell.innerHTML = `<textarea style="white-space: pre-wrap; height: auto; overflow: hidden;" onchange="postChanges(` + k + `)" name="col_` + i + `_` + k + `" oninput="this.style.height='auto';this.style.height=this.scrollHeight+'px'; this.value=this.value.replace(/'/g, '')" placeholder="Digite aqui..." id="col_` + i + `_` + k + `" class="op_lgs_text">` + df[Object.keys(df)[i]][k] + `</textarea>`;
                    setTimeout(function() {
                        var textarea = document.getElementById("col_" + i + "_" + k);
                        if (textarea) {
                            textarea.style.height = 'auto';
                            textarea.style.height = textarea.scrollHeight + 'px';
                        }
                    }, 0);
                    cell.style.maxWidth = "12vw";
                    cell.style.height = 'auto';
                }
            } else {
                cell.innerHTML = `<input type="hidden" id="line_id_` + k + `" name="line_id_` + k + `" value="` + df["Id"][k] + `"/><button value="` + df["Id"][k] + `" id="del_` + k + `" class="op_lgs_table_btn" onclick="deleteLine(this.parentNode.parentNode, this.value)" type="button">&times</button>`
                cell.style.maxWidth = "5vw";
            }
        }
        row = myTable.insertRow();
    }

    document.getElementById("op_lgs_tbl").innerHTML = '';
    myTable.className = "std_table";
    myTable.id = "lgs_table";
    document.getElementById("op_lgs_tbl").appendChild(myTable);
}

function addLine() {
    var table = document.getElementById("lgs_table");
    var row = table.insertRow(-1);
    var len = table.rows.length - 3;
    var btn = document.getElementById('area');

    for (let i = 0; i < table.rows[0].cells.length; i++) {
        cell = row.insertCell(i);
        cell.style.color = "rgb(255,255,195)";
        if ((i == 0 || i == 4) && btn.innerHTML == 'Entregas') {
            cell.innerHTML = `<input type="hidden" id="aux_` + i + `_` + len + `" name="col_` + i + `_` + len + `" value="0"/>
                              <button id="btn_` + i + `_` + len + `" type="button" onclick="changeBtnVal('` + i + `','` + len + `')" class="`+ classes[0] + `"/></button>`
            cell.style.maxWidth = "5vw";
        } else if (i == 4 && btn.innerHTML == 'Manufaturados') {
            cell.innerHTML = `<input type="hidden" name="col_` + i + `_` + len + `" value="JOST"/>JOST`
            cell.style.color = "rgb(255,255,195)";
        } else if ((i == 8 && btn.innerHTML == 'Entregas') || (i == 7 && btn.innerHTML != 'Entregas')) {
            cell.innerHTML = `<input type="hidden" id="line_id_` + len + `" name="line_id_` + len + `" value="new" /><button class="op_lgs_table_btn" value="new" id="del_` + len + `" onclick="deleteLine(this.parentNode.parentNode, this.value)" type="button">&times</button>`
            cell.style.maxWidth = "5vw";
        } else if ((i == 2 && btn.innerHTML == 'Entregas')) {
            cell.innerHTML = `<input onchange="postChanges(` + len + `)" name="col_` + i + `_` + len + `" type="number" min="0" placeholder="Digite aqui..." id="col_` + i + `" value="0" class="op_lgs_text" style="width:4vw;"/>`
            cell.style.maxWidth = "4vw";
        } else {
            cell.innerHTML = `<textarea onchange="postChanges(` + len + `)" name="col_` + i + `_` + len + `" onclick="this.style.height = '';this.style.height = this.scrollHeight + 'px';" onkeyup="this.style.height = '';this.style.height = this.scrollHeight + 'px'; this.value=this.value.replace(/'/g, '')" placeholder="Digite aqui..." id="col_` + i + `" class="op_lgs_text"></textarea>`
            cell.style.maxWidth = "12vw";
        }
    }

    postChanges(len);

    row.scrollIntoView({
        block: 'end',
        behavior: 'smooth'
    });
}

function postChanges(index) {
    var filter = document.getElementById('date').value;
    var btn = document.getElementById('area').innerHTML;

    var line = document.getElementById('line_id_' + index);
    var del = document.getElementById('del_' + index);

    var form = document.getElementById('lgs_form');
    var form_data = new FormData(form);
    form_data.append('area', btn);
    form_data.append('date', filter);
    form_data.append('index', index);
    form_data.append('copy', create_new);
    var form_param = new URLSearchParams(form_data).toString();

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/op/logistica/update", true);
    xhr.setRequestHeader("Content-type","application/x-www-form-urlencoded");

    xhr.onreadystatechange = function () {
       if (line.value == 'new' || line.value == '') {
          line.value = xhr.responseText;
          del.value = xhr.responseText;
       }

       if (xhr.readyState == 4) {
          info = false;
       }
    }

    var params = form_param;
    xhr.send(params);
}

function deleteLine(row, line_id) {
    var table = document.getElementById("lgs_table");
    var btn = document.getElementById("area").innerHTML
    if (confirm('Toda a linha será deletada')) {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/op/logistica/delete", true);
        xhr.setRequestHeader("Content-type","application/json");
        var params = JSON.stringify([btn, line_id]);
        xhr.send(params);
        table.deleteRow(row.rowIndex);
    }
}

function filterTbl(index, value) {
    var table, tr, td, i, txtValue, display;
    display = []
    table = document.getElementById("lgs_table");
    tr = table.getElementsByTagName("tr");

    if (index == 0) {
        var good = document.getElementById("f1");
        var mid = document.getElementById("f2");
        var bad = document.getElementById("f3");

        var n1 = document.getElementById("p1");
        var n2 = document.getElementById("p2");
        var n3 = document.getElementById("p3");
    } else {
        var good = document.getElementById("p1");
        var mid = document.getElementById("p2");
        var bad = document.getElementById("p3");

        var n1 = document.getElementById("f1");
        var n2 = document.getElementById("f2");
        var n3 = document.getElementById("f3");
    }

    var filters = [good, mid, bad];
    var not_selected = [n1, n2, n3];

    for (i = 0; i < filters.length; i++) {
        if (i != value) {
            filters[i].className = "op_lgs_unselect";
        } else {
            filters[i].className = "op_" + classes[value];
        }
        not_selected[i].className = "op_" + classes[i];
    }

    for (i = 0; i < tr.length; i++) {
        var line = []
        if (i < tr.length) {
            td = tr[i].getElementsByTagName("td")[index];
            if (td) {
                txtValue = td.innerHTML;
                if (i > 0) {
                    txtValue = txtValue.split('class="')[1].split('"')[0];
                        filter = value;
                    if (txtValue == classes[value]) {
                        line.push("yes");
                    } else {
                        line.push("none");
                    }
                } else {
                    line.push("yes");
                }

            }
        } else if (i < tr.length && filter == '') {
            line.push("no_filter");
        }
        display.push(line)
    }

    for (k = 0; k < tr.length - 1; k++) {
        if (display[k].includes("none")) {
            tr[k].style.display = "none";
        } else {
            tr[k].style.display = "";
        }
    }
}

var create_new = false;
var checked = false;
var iter_df = {};

createTable(info, filter);
removeNav();

