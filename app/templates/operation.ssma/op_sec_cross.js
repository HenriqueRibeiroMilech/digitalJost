var state = 'Geral'
// JS
function createCross() {
    var cross = document.getElementById('cross')
    cross.innerHTML = `<div id="seg_cross">
        <div class="seg_cross_section" id="seg_cross_1"></div>
        <div class="seg_cross_section" id="seg_cross_2"></div>
        <div class="seg_cross_section" id="seg_cross_3"></div>
    </div>`

    var actual_month = meses.indexOf(atual.innerHTML.split(' ')[0]) + 1;
    var actual_year = atual.innerHTML.split(' ')[1];
    var max_days = new Date(actual_year, actual_month, 0).getDate();

    var days = 1
    for (let i = 0; i < 3; i++) {
        var container = document.getElementById('seg_cross_' + (i + 1))
        if (i == 0 || i == 2 ) {
            for (let k = 0; k < 6; k++) {
                if (days <= max_days) {
                    container.innerHTML += `<div class="seg_cross_day" id="seg_day_${days}">
                        <span class="seg_day">${days}</span>
                        <div class="cross_square_container">
                            <div class="cross_square cross_square_0" id="cross_square_0_${days}"></div>
                            <div class="cross_square cross_square_1" id="cross_square_1_${days}"></div>
                            <div class="cross_square cross_square_2" id="cross_square_2_${days}"></div>
                            <div class="cross_square cross_square_3" id="cross_square_3_${days}"></div>
                            <div class="cross_square cross_square_4" id="cross_square_4_${days}"></div>
                            <div class="cross_square cross_square_5" id="cross_square_5_${days}"></div>
                        </div>
                    </div>`
                } else if (days > max_days && days < 32) {
                    container.innerHTML += `<div class="seg_cross_day" id="seg_day_${days}">
                        <span class="seg_day"><br></span>
                    </div>`
                } else {
                    if (days == 32) {
                        container.innerHTML += `<div id="back" class="seg_cross_day" onclick="changeMonth(-1)">
                            <i class='fas fa-angle-double-left'></i>
                        </div>`
                    } else if (days == 33) {
                        container.innerHTML += `<div id="next" class="seg_cross_day" onclick="changeMonth(1)">
                            <i class='fas fa-angle-double-right'></i>
                        </div>`
                    }
                }
                days += 1;
            }
        } else {
            for (let k = 0; k < 21; k++) {
                days += 1
            }
        }
    }

    days = 7
    for (let i = 0; i < 3; i++) {
        var container = document.getElementById('seg_cross_' + (i + 1))
        if (i == 1) {
            for (let k = 0; k < 21; k++) {
                container.innerHTML += `<div class="seg_cross_day" id="seg_day_${days}">
                    <span class="seg_day">${days}</span>
                    <div class="cross_square_container">
                        <div class="cross_square cross_square_0" id="cross_square_0_${days}"></div>
                        <div class="cross_square cross_square_1" id="cross_square_1_${days}"></div>
                        <div class="cross_square cross_square_2" id="cross_square_2_${days}"></div>
                        <div class="cross_square cross_square_3" id="cross_square_3_${days}"></div>
                        <div class="cross_square cross_square_4" id="cross_square_4_${days}"></div>
                        <div class="cross_square cross_square_5" id="cross_square_5_${days}"></div>
                    </div>
                </div>`
                days += 1
            }
        }
    }
}

function changeLoc(loc) {
    window.location = loc;
}

function changeState(loc) {
    state = loc
    createCross();
    paintCross();
}

var meses = ['JANEIRO','FEVEREIRO','MARÇO','ABRIL','MAIO','JUNHO','JULHO','AGOSTO','SETEMBRO','OUTUBRO','NOVEMBRO','DEZEMBRO']
var year = new Date().getFullYear();
var atual = document.getElementById("month");
atual.innerHTML = meses[{{month | tojson}} - 1] + ' ' + year ;

function changeMonth(val) {
    var atual = document.getElementById("month");
    var index = meses.indexOf(atual.innerHTML.split(' ')[0]) + val;
    if (index > 11) {
        index = 0;
        year += 1;
    } else if (index < 0) {
        index = 11;
        year -= 1;
    }
    atual.innerHTML = meses[index] + ' ' + year ;
    createCross();
    paintCross();
}

function paintCross() {

    if (state == 'Geral') {
        condition = ''
    } else {
        condition = '&state=' + state
    }

    var atual = document.getElementById("month");
    var xhr = new XMLHttpRequest();
    var index = meses.indexOf(atual.innerHTML.split(' ')[0]) + 1
    xhr.open("POST", "/op/ssma?month=" + index + "&year=" + atual.innerHTML.split(' ')[1] + condition);
    xhr.setRequestHeader("Content-type","application/json");

    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            var data = JSON.parse(xhr.responseText);
            var new_data = []
            data.forEach(elm => new_data.push(elm));

            document.querySelectorAll('.cross_square').forEach(elm => {
                elm.style.display = 'none';
            });

            var days = [];

            for (let i = 0; i < new_data.length; i++) {

                var acidente_com_count = 0;
                var acidente_sem_count = 0;
                var inc_count = 0;
                var amb_count = 0;
                var ambiental_count = 0;

                for (let k = 0; k < new_data.length; k++) {

                    // 🔧 CORREÇÃO: só conta ACIDENTE COM AFASTAMENTO
                    if (new_data[k][1] === 'Acidente com Afastamento' &&
                        new_data[k][0] == new_data[i][0]) {
                        acidente_com_count += 1;

                    } else if (new_data[k][1] == 'Acidente sem Afastamento' &&
                               new_data[k][0] == new_data[i][0]) {
                        acidente_sem_count += 1;

                    } else if (new_data[k][1] == 'Registro de Incidente' &&
                               new_data[k][0] == new_data[i][0]) {
                        inc_count += 1;

                    } else if (new_data[k][1] == 'Atendimento Ambulatorial' &&
                               new_data[k][0] == new_data[i][0]) {
                        amb_count += 1;

                    } else if (new_data[k][1] == 'Incidente Ambiental' &&
                               new_data[k][0] == new_data[i][0]) {
                        ambiental_count += 1;
                    }
                }

                // 🔧 CORREÇÃO: NÃO incluir "Acidente" genérico
                if (new_data[i][1] === 'Acidente com Afastamento') {
                    document.querySelector("#cross_square_0_" + new_data[i][0]).style.display = 'block';
                    document.querySelector("#cross_square_0_" + new_data[i][0]).innerHTML =
                        '<p>' + acidente_com_count + '</p>';

                } else if (new_data[i][1] == 'Acidente sem Afastamento') {
                    document.querySelector("#cross_square_1_" + new_data[i][0]).style.display = 'block';
                    document.querySelector("#cross_square_1_" + new_data[i][0]).innerHTML =
                        '<p>' + acidente_sem_count + '</p>';

                } else if (new_data[i][1] == 'Atendimento Ambulatorial') {
                    document.querySelector("#cross_square_2_" + new_data[i][0]).style.display = 'block';
                    document.querySelector("#cross_square_2_" + new_data[i][0]).innerHTML =
                        '<p>' + amb_count + '</p>';

                } else if (new_data[i][1] == 'Registro de Incidente') {
                    document.querySelector("#cross_square_3_" + new_data[i][0]).style.display = 'block';
                    document.querySelector("#cross_square_3_" + new_data[i][0]).innerHTML =
                        '<p>' + inc_count + '</p>';

                } else if (new_data[i][1] == 'Em Análise') {
                    document.querySelector("#cross_square_4_" + new_data[i][0]).style.display = 'block';

                } else if (new_data[i][1] == 'Incidente Ambiental') {
                    document.querySelector("#cross_square_5_" + new_data[i][0]).style.display = 'block';
                    document.querySelector("#cross_square_5_" + new_data[i][0]).innerHTML =
                        '<p>' + ambiental_count + '</p>';
                }

                var minhaDiv = document.getElementById("seg_day_" + new_data[i][0]);
                minhaDiv.onclick = function() {
                    view(new_data[i][0])
                };

                if (!days.includes(new_data[i][0])) {
                    days.push(new_data[i][0]);
                }
            }

            const date = new Date()
            var month = date.getMonth();
            var year = date.getFullYear();
            var greater = false;
            var today = date.getDate();

            var actual_month = meses.indexOf(atual.innerHTML.split(' ')[0]) + 1;
            var actual_year = atual.innerHTML.split(' ')[1];
            var max_days = new Date(actual_year, actual_month, 0).getDate();

            if (year > atual.innerHTML.split(' ')[1] ||
                (month > (index - 1) && year == atual.innerHTML.split(' ')[1])) {
                today = max_days;
            }

            if (atual.innerHTML.split(' ')[1] > year ||
               (atual.innerHTML.split(' ')[1] == year && (index - 1) > month)) {
                greater = true;
            }

            for (let i = 1; i <= 31; i++) {
                document.querySelector('#seg_day_' + i).style.background =
                    "rgba(205,205,205,0.4)";
            }

            for (let i = 1; i <= max_days; i++) {
                if (i <= today && !greater) {
                    if (!days.includes(i)) {
                        document.querySelector('#seg_day_' + i).style.background = "#06ad53";
                    } else {
                        document.querySelector('#seg_day_' + i).style.background =
                            "rgba(205,205,205,0.4)";
                    }
                } else {
                    document.querySelector('#seg_day_' + i).style.background =
                        "rgba(205,205,205,0.4)";
                }
            }
        }
    }

    xhr.send()
}

function view(day) {

    if (state == 'Geral') {
        condition = ''
    } else {
        condition = '&state=' + state
    }

    var atual = document.getElementById("month");
    var month = meses.indexOf(atual.innerHTML.split(' ')[0]) + 1
    var year = atual.innerHTML.split(' ')[1]
    window.location =
      "/op/ssma/view?day=" + day + "&month=" + month + "&year=" + year + condition;
}

createCross();
paintCross();
removeNav();