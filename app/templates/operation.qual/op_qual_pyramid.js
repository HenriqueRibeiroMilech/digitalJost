var meses = ['JANEIRO', 'FEVEREIRO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO']
var year = new Date().getFullYear();
var state = 'Geral'
var last_month;

function createPyramid() {
    var line_max = 1;
    var current_line = 0;
    var pyramid = document.getElementById('pyramid');
    for (let i = 0; i < 31; i++) {
        pyramid.innerHTML += `<div onclick="view(this.id)" id="day_` + (i + 1) + `" class="day">
        <div id="day_` + (i + 1) + `_` + (0) + `" class="small_day"></div>
        <div id="day_` + (i + 1) + `_` + (1) + `" class="small_day"></div>
        <div id="day_` + (i + 1) + `_` + (2) + `" class="small_day"></div>
        <div id="day_` + (i + 1) + `_` + (3) + `" class="small_day"></div>
        <div id="day_` + (i + 1) + `_` + (4) + `" class="small_day"></div>
        <div id="day_` + (i + 1) + `_` + 'num' + `" class="num_day">` + (i + 1) + `</div>
        </div>`;
        current_line += 1;
        if (current_line == line_max) {
            pyramid.innerHTML += '<br>'
            if (line_max < 5) {
                line_max += 1;
            } else if (line_max == 5) {
                pyramid.innerHTML += `<button onclick="changeMonth(-1)" class="change"><i class='fas fa-angle-left'></i></button><p id="month" class="month">`+ meses[{{month | tojson}} - 1] + ` ` + year +`</p><button class="change" onclick="changeMonth(1)"><i class='fas fa-angle-right'></i></button><br>`
                line_max += 2;
            } else {
                line_max += 2;
            }
            current_line = 0;
        }
    }
    changeMonth(0);
}

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
    paintPyramid((index + 1))
}

function paintPyramid(month) {
    last_month = month

    const date = new Date();
    let to_day = date.getDate();
    let to_month = date.getMonth() + 1;
    let to_year = date.getFullYear();

    var atual = document.getElementById("month");
   
    if (state == 'Geral') {
        condition = ''
    } else {
        condition = '&unit=' + state
    }

   var xhr = new XMLHttpRequest();
   xhr.open("POST", "/op/qualidade?month=" + month + "&year=" + atual.innerHTML.split(' ')[1] + condition);
   xhr.setRequestHeader("Content-type","application/json");
   
   xhr.onreadystatechange = function () {
       if (xhr.readyState === 4 && xhr.status === 200) {
           var data = JSON.parse(xhr.responseText)

            document.querySelectorAll('.day').forEach((elm, i) => {
                if (to_day >= parseInt(elm.id.split('_')[1]) && to_month == month) {
                    elm.style.backgroundColor = "rgba(28,124,84,1)";

                } else if (to_month > month) {
                    elm.style.backgroundColor = "rgba(28,124,84,1)"

                } else {
                    elm.style.backgroundColor = "rgba(205,205,205,0.22)";
                }
            });

            document.querySelectorAll('.small_day').forEach((elm, i) => {
                elm.style.background = "none";
                elm.innerHTML = "";
            });

            var count_f = 1
            var count_i = 1
            var count_cn = 1
            var count_cf = 1

            var last_day = 0
            data.forEach((elm, i) => {

                var day = document.getElementById('day_' + elm[0]);

                day.style.color = 'white';
                day.style.backgroundColor = 'rgba(55,55,55,0.3)';


                if (last_day != elm[0]) {
                    count_f = 1
                    count_i = 1
                    count_cn = 1
                    count_cf = 1
                }

                last_day = elm[0];

                if (elm[1] == 'Fornecedor') {
                    var small = document.getElementById(day.id + '_0');
                    small.style.background = "#3944BC";
                    if (small.innerHTML != '') {
                        small.innerHTML = '<p>' + (count_f + 1) + '</p>'
                        count_f += 1
                    } else {
                        small.innerHTML = '<p>' + 1 + '</p>';
                    }

                } else if (elm[1] == 'Interno') {
                    var small = document.getElementById(day.id + '_1');
                    small.style.marginLeft = "calc(calc(calc(3.5vh + 3.5vw) / 2) * -1.01)"
                    small.style.background = "#E1AD01";
                    if (small.innerHTML != '') {
                        small.innerHTML = '<p>' + (count_i + 1) + '</p>'
                        count_i += 1
                    } else {
                        small.innerHTML = '<p>' + 1 + '</p>';
                    }

                } else if (elm[1] == 'Cliente (Formal)') {
                    var small = document.getElementById(day.id + '_2');
                    small.style.marginTop = "calc(calc(3.5vh + 3.5vw) / 1.99)"
                    small.style.background = "red";
                    if (small.innerHTML != '') {
                        small.innerHTML = '<p style="padding-top: 20px">' + (count_cf + 1) + '</p>'
                        count_cf += 1
                    } else {
                        small.innerHTML = '<p style="padding-top: 20px">' + 1 + '</p>';
                    }
                } else if (elm[1] == 'Cliente (Não Formal)') {
                    var small = document.getElementById(day.id + '_3');
                    small.style.marginLeft = "calc(calc(calc(3.5vh + 3.5vw) / 2) * -1.01)"
                    small.style.marginTop = "calc(calc(3.5vh + 3.5vw) / 1.99)"
                    small.style.background = "#3E3D53";
                    if (small.innerHTML != '') {
                        small.innerHTML = '<p style="padding-top: 20px">' + (count_cn + 1) + '</p>'
                        count_cn += 1
                    } else {
                        small.innerHTML = '<p style="padding-top: 20px">' + 1 + '</p>';
                    }
                } else if (elm[1] == 'Cliente (Logística)') {
                    var small = document.getElementById(day.id + '_4');
                    small.style.marginLeft = "calc(((3.5vh + 3.5vw) / 2 - (1.75vh + 1.75vw) / 2)  * -1.01)"
                    small.style.marginTop = "calc((3.5vh + 3.5vw) / 2 - (1.75vh + 1.75vw) / 2)"
                    small.style.background = "#a626a6";
                    if (small.innerHTML != '') {
                        small.innerHTML = '<p>' + (count_cn + 1) + '</p>'
                        count_cn += 1
                    } else {
                        small.innerHTML = '<p>' + 1 + '</p>';
                    }
                }
            });
        }
    }

   xhr.send()
}

function view(day) {
    var parent = document.getElementById(day);
    var count = 0;
    for (let i = 0; i < parent.children.length; i++ ) {
        if (!['none', ''].includes(parent.children[i].style.background)) {
            count += 1
        }
    }

    if (count != 0) {

        if (state == 'Geral') {
            condition = ''
        } else {
            condition = '&unit=' + state
        }


        var day = day.split('_')[1]
        var atual = document.getElementById("month");
        var month = meses.indexOf(atual.innerHTML.split(' ')[0]) + 1;
        var date = day + '/' + month + '/' + year
        window.location = '/op/qualidade/view?day=' + date + condition;
    }
}

function changeState(loc) {
    state = loc
    paintPyramid(last_month)
}

removeNav();
createPyramid();


