removeNav();
var selected = 'realtime';
var area = 'gen'
var realtime = false;
var oper_data = '';
var curr_oper = 0;

var freezeClic = true;

selectType('realtime');
selectArea('gen');


document.addEventListener("click", e => {
    if (freezeClic) {
        e.stopPropagation();
        e.preventDefault();
    }
}, true);

function selectType(id) {
    var btn = document.getElementById(id);
    selected = btn.id;
    if (btn.className == "chp_btn") {
        btn.className = "chp_selected";
        var btn_names = ["realtime", "periodic"];
        for (let i = 0; i < btn_names.length; i++) {
            if (id != btn_names[i]) {
                document.getElementById(btn_names[i]).className = "chp_btn";
            }
        }
    }

    if (selected == 'realtime' && !realtime) {
        document.getElementById('chp_desc_wrapper').innerHTML = `<p class="chp_desc">...</p>`
        setTimeout(update, 0100);
        interval_id =  setInterval(update, 10000);
        realtime = true;
        document.getElementById('opers').style.display = "inline-block";
    } else if (selected != 'realtime' && realtime) {
        clearInterval(interval_id);
        document.getElementById('chp_desc_wrapper').innerHTML = `<input type="date" id="init" class="chp_date" value="` + {{today | tojson}} + `">
                                                                 <input type="date" id="end" class="chp_date" value="` + {{today | tojson}} + `">
                                                                 <button onclick="filterPeriod()" class="chp_search"><i class="fa fa-search"></i></button>`

        document.getElementById('opers').style.display = "none";
        filterPeriod();
        realtime = false;
    }

    selectArea(area);
}
function selectArea(id) {
    var btn = document.getElementById(id);
    area = id;
    if (btn.className == "dash_btn_b") {
        btn.className = "dash_btn_b_sel";
        var btn_names = ["emp", "oper", "gen"];
        for (let i = 0; i < btn_names.length; i++) {
            if (id != btn_names[i]) {
                document.getElementById(btn_names[i]).className = "dash_btn_b";
            }
        }
    }

    var content = document.getElementById('chp_main_wrapper');
    if (id == 'gen') {
        content.removeAttribute('style');
        document.getElementById('proxs').style.opacity = "0";
        document.getElementById('proxs').style.display = "none";
        document.getElementById('last').style.opacity = "0";
        document.getElementById('last').style.display = "none";
        content.innerHTML = `<div class="chp_box_wrapper">
                                <div class="chp_small_box"><p class="chp_ct_txt">OEE</p><p id="oee" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                                <div class="chp_small_box"><p class="chp_ct_txt">PERFORMANCE</p><p id="perf" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                                <div class="chp_small_box"><p class="chp_ct_txt">DISPONIBILIDADE</p><p id="disp" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                              </div>
                              <div class="chp_box_wrapper">
                                <div class="chp_small_box"><p class="chp_ct_txt">PRODUZINDO - T1</p><p id="ht_1" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                                <div class="chp_small_box"><p class="chp_ct_txt">PARADO - T1</p><p id="hp_1" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                                <div class="chp_small_box"><p class="chp_ct_txt">DISPONÍVEL - T1</p><p id="hd_1" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                              </div>
                              <div class="chp_box_wrapper">
                                <div class="chp_small_box"><p class="chp_ct_txt">PRODUZINDO - T2</p><p id="ht_2" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                                <div class="chp_small_box"><p class="chp_ct_txt">PARADO - T2</p><p id="hp_2" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                                <div class="chp_small_box"><p class="chp_ct_txt">DISPONÍVEL - T2</p><p id="hd_2" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                              </div>
                              <div class="chp_box_wrapper">
                                <div class="chp_small_box"><p class="chp_ct_txt">PRODUZINDO - T3</p><p id="ht_3" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                                <div class="chp_small_box"><p class="chp_ct_txt">PARADO - T3</p><p id="hp_3" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                                <div class="chp_small_box"><p class="chp_ct_txt">DISPONÍVEL - T3</p><p id="hd_3" class="chp_ct_num"></p><div class="sml_loader"></div></div>
                              </div>`
    } else if (id == 'oper') {
        content.innerHTML = '<div class="loader"></div>';
    } else if (id == 'emp') {
        content.innerHTML = '<div class="loader"></div>';
    }

    freezeClic = true;
    if (selected == 'periodic') {
        filterPeriod();
    } else {
        update();
    }
}

function filterPeriod() {
    var xhr = new XMLHttpRequest();
    var init = document.getElementById('init').value;
    var end = document.getElementById('end').value;
    var type = document.querySelector(".chp_selected").id;
    var dash = document.querySelector(".dash_btn_b_sel").id;
    var content = document.getElementById('chp_main_wrapper');

    if (dash == 'oper' || dash == 'emp') {
        content.innerHTML = '<div class="loader"></div>';
    }
    xhr.open('POST', '/dashboards/chp/ct')
    xhr.setRequestHeader("Content-type","application/json");
    xhr.onreadystatechange = function () {
        document.querySelectorAll(".sml_loader").forEach((elm, i) => {
            elm.style.display = "block";
        });
        if (xhr.readyState == 4) {
            document.querySelectorAll(".sml_loader").forEach((elm, i) => {
                elm.style.display = "none";
            });

            if (dash == 'gen') {
                genData(xhr.responseText);
                freezeClic = false;
            } else if (dash == 'oper') {
                oper_data = JSON.parse(JSON.parse(xhr.responseText)[1]);
                operData(Object.keys(oper_data['NOME']).length);
                document.getElementById('proxs').style.display = "inline-block";
                document.getElementById('proxs').style.opacity = "1";
                document.getElementById('last').style.display = "inline-block";
                document.getElementById('last').style.opacity = "1";
                freezeClic = false;
            } else if (dash == 'emp') {
                var emp_data = JSON.parse(JSON.parse(xhr.responseText)[1])
                empData(emp_data)
                document.getElementById('proxs').style.display = "none";
                document.getElementById('proxs').style.opacity = "0";
                document.getElementById('last').style.display = "none";
                document.getElementById('last').style.opacity = "0";
                freezeClic = false;
            }
        }
    }
    var ct = document.getElementById('ct').innerHTML;
    xhr.send(JSON.stringify([ct, type, dash, init, end]));
}

function update() {
    var xhr = new XMLHttpRequest();
    var type = document.querySelector(".chp_selected").id;
    var dash = document.querySelector(".dash_btn_b_sel").id;
    xhr.open('POST', '/dashboards/chp/ct')
    xhr.setRequestHeader("Content-type","application/json");
    xhr.onreadystatechange = function () {
        document.querySelectorAll(".sml_loader").forEach((elm, i) => {
            elm.style.display = "block";
        });
        if (xhr.readyState == 4) {
            var status_data = JSON.parse(JSON.parse(xhr.responseText)[0])
            var status = status_data["Status"][0]
            var numreal = status_data['NUMREAL'][0]
            var numplan = status_data['NUMPLAN'][0]
            var time = status_data["Tempo"][0]
            if (status == 'Parada') {
                desc = JSON.parse(JSON.parse(xhr.responseText)[0])["Descricao"][0]
                document.getElementById('chp_desc_wrapper').innerHTML = `<p class="chp_desc" id="stop"><i class="fa fa-circle"></i> ` + desc + ` - ` + time + `</p>`
            } else {
                document.getElementById('chp_desc_wrapper').innerHTML = `<p class="chp_desc" id="prod"><i class="fa fa-circle"></i> ` + status + ` - ` + time + `</p>`
            }
            document.getElementById('opers').innerHTML = numreal + ' DE ' + numplan + ' OPERADORES';
            if (dash == 'gen') {
                document.querySelectorAll(".sml_loader").forEach((elm, i) => {
                    elm.style.display = "none";
                });
                document.getElementById('opers').style.display = "inline-block";
                genData(xhr.responseText);
                freezeClic = false;
            } else if (dash == 'oper') {
                document.getElementById('opers').style.display = "inline-block";
                oper_data = JSON.parse(JSON.parse(xhr.responseText)[1]);
                operData(numreal);
                document.getElementById('proxs').style.display = "inline-block";
                document.getElementById('proxs').style.opacity = "1";
                document.getElementById('last').style.display = "inline-block";
                document.getElementById('last').style.opacity = "1";
                freezeClic = false;
            } else if (dash == 'emp') {
                var emp_data = JSON.parse(JSON.parse(xhr.responseText)[1])
                empData(emp_data)
                document.getElementById('opers').style.display = "none";
                document.getElementById('proxs').style.display = "none";
                document.getElementById('proxs').style.opacity = "0";
                document.getElementById('last').style.display = "none";
                document.getElementById('last').style.opacity = "0";
                freezeClic = false;
            }
        }
    }
    var ct = document.getElementById('ct').innerHTML;
    xhr.send(JSON.stringify([ct, type, dash]));
}

function genData(response) {
    var stop_data = JSON.parse(JSON.parse(response)[2])
    var prod_data = JSON.parse(JSON.parse(response)[1])

    var oee = prod_data['OEE'][0].toFixed(2);
    var perf = prod_data['PERFORMANCE'][0].toFixed(2);
    var disp = prod_data['DISPONIBILIDADE'][0].toFixed(2);

    if (oee > prod_data['META_OEE'][0]) {
        document.getElementById('oee').style.color = "#228C22";
    } else if (oee < prod_data['META_OEE'][0] - 15) {
        document.getElementById('oee').style.color = "#990000";
    } else {
        document.getElementById('oee').style.color = "rgb(241,202,5)";
    }

    if (perf > 95) {
        document.getElementById('perf').style.color = "#228C22";
    } else if (perf < 80) {
        document.getElementById('perf').style.color = "#990000";
    } else {
        document.getElementById('perf').style.color =  "rgb(241,202,5)";
    }

    document.getElementById('oee').innerHTML = oee + '%';
    document.getElementById('perf').innerHTML = perf + '%';
    document.getElementById('disp').innerHTML = disp + '%';

    if (disp > prod_data['META_OEE'][0]) {
        document.getElementById('disp').style.color = "#228C22";
    } else if (disp < prod_data['META_OEE'][0] - 15) {
        document.getElementById('disp').style.color = "#990000";
    } else {
        document.getElementById('disp').style.color = "rgb(241,202,5)";
    }

    for (let i = 0; i < 3; i++) {
        document.getElementById('ht_' + (i + 1)).innerHTML = 0 + 'H';
        document.getElementById('hp_' + (i + 1)).innerHTML = 0 + 'H';
        document.getElementById('hd_' + (i + 1)).innerHTML = 0 + 'H';
    }

    for (let i = 0; i < Object.keys(stop_data['TURNO']).length; i++) {
        document.getElementById('ht_' + stop_data['TURNO'][i]).innerHTML = stop_data['H_PROD'][i] + 'H';
        document.getElementById('hp_' + stop_data['TURNO'][i]).innerHTML = stop_data['H_PARADO'][i] + 'H';
        document.getElementById('hd_' + stop_data['TURNO'][i]).innerHTML = stop_data['H_DISP'][i] + 'H';
    }
}

function operData(num_opers) {
    if (curr_oper > Object.keys(oper_data['NOME']).length) {
        curr_oper = 0;
    }

    var content = document.getElementById('chp_main_wrapper');

    if (Object.keys(oper_data['NOME']).length < 1) {
        content.innerHTML = '<p class="chp_warning">NENHUM OPERADOR COM LOGIN EFETUADO</p>';
    } else {
        content.innerHTML = `<div class="chp_card">
                                <div class="chp_oper_wrap">
                                    <p class="chp_oper_icon"><i class="fa fa-user"></i> OPERADOR ` + (curr_oper + 1) + ` DE ` + num_opers + `</p>
                                    <p class="chp_oper"><b>NOME: </b>` + oper_data['NOME'][curr_oper].toUpperCase() + `</p>
                                    <p class="chp_oper"><b>MATRÍCULA: </b>` + oper_data['MATRICULA'][curr_oper].toUpperCase() + `</p>
                                    <p class="chp_oper"><b>TURNO: </b>` + oper_data['TURNO'][curr_oper] + `</p>
                                    <p class="chp_oper"><b>CT DE ORIGEM: </b>` + oper_data['CT_ORIGEM'][curr_oper].toUpperCase() + `</p><br>
                                    <p class="chp_oper_half"><b>TEMPO NO CT: </b><br><span class="time">` + oper_data['HORAS'][curr_oper] + `H</span></p>
                                    <p class="chp_oper_half"><b>TEMPO PONTO: </b><br><span class="time">` + oper_data['PONTO'][curr_oper] + `H</span></p>
                                </div>
                                <div class="chp_oper_wrap">
                                    <p class="chp_oper_icon"><i class="fa fa-hourglass-start"></i> APROVEITAMENTO</p>
                                    <p class="chp_oper_half"><b>PERCENTUAL: </b><br><span class="time">` + oper_data['PCT'][curr_oper] + `%</p>
                                    <p class="chp_oper_half"><b>FORA DO CT: </b><br><span class="time">` + (oper_data['PONTO'][curr_oper] - oper_data['HORAS'][curr_oper]).toFixed(2) + `H</span></p><br><br>
                                    <p class="chp_oper_half"><b>PRODUZINDO: </b><br><span class="time">` + oper_data['H_PROD'][curr_oper] + `H</span></p>
                                    <p class="chp_oper_half"><b>LINHA PARADA: </b><br><span class="time">` + oper_data['H_PARADO'][curr_oper] + `H</span></p>
                                </div>
                             </div>`
    }
}

function chooseNext(val) {
    curr_oper += val;
    if (curr_oper >= Object.keys(oper_data['NOME']).length) {
        curr_oper = 0;
    } else if (curr_oper < 0) {
        curr_oper = Object.keys(oper_data['NOME']).length - 1;
    }
    operData(Object.keys(oper_data['NOME']).length);
}

function empData(emp_df) {
    var content = document.getElementById('chp_main_wrapper');

    var table = document.createElement("table"),
    row = table.insertRow(), cell;

    cols = ['NOME', 'MATRICULA', 'TURNO', 'CT_ORIGEM', 'H_TRABALHADAS', 'H_PONTO']

    for (let i = 0; i < cols.length; i++) {
        cell = row.insertCell()
        cell.innerHTML = cols[i]
        cell.style.width = "15vw"
    }

    row = table.insertRow()

    for (let k = 0; k < Object.keys(emp_df['CT_ORIGEM']).length; k++) {
        for (let i = 0; i < cols.length; i++) {
            cell = row.insertCell()
            cell.innerHTML = emp_df[cols[i]][k]
            cell.style.width = "15vw"
        }
        row = table.insertRow()
    }

    content.innerHTML = ''
    table.id = "emp_tbl"
    content.appendChild(table)
    content.style.overflowY = 'scroll'
    content.style.marginTop = '5vh'
    content.style.height = '68vh'
}