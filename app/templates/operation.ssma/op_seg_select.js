function changeLoc(loc) {
    window.location = loc;
}

function insertTable() {
    var headers = ['ID', 'Setor', 'Local', 'Data', 'Tipo', 'Unidade']
    var df = JSON.parse({{df | tojson}})
    var myTable = document.createElement("table"),
    row = myTable.insertRow(), cell;

    for (let k = 0; k < Object.keys(df['id']).length + 1; k++) {
        var index = 0
        for (let i = 0; i < Object.keys(df).length; i++) {
            cell = row.insertCell();
            var val = df[Object.keys(df)[i]][k - 1]
            cell.style.maxWidth = "9.5vw";
            cell.style.width = "9.5vw";   
            if (k == 0) {
                cell.innerHTML = headers[index];
                index += 1
            } else {
                if (Object.keys(df)[i] == 'date') {
                    cell.innerHTML = val.split(' ')[0].split('-')[2] + '/' + val.split(' ')[0].split('-')[1] + '/' + val.split(' ')[0].split('-')[0] + ' ' + val.split(' ')[1];
                } else if (Object.keys(df)[i] == 'id') {
                    cell.innerHTML = `<button class="seg_edit" onclick="view('` + val + `')">` +  val + `</button>`;
                    cell.style.maxWidth = "5vw";
                    var id = val;
                } else if (Object.keys(df)[i] == 'UNIDADE') {
                    cell.innerHTML = val;
                    cell.style.maxWidth = "6vw";
                    cell.style.width = "6vw";   
                } else {
                    cell.innerHTML = val;
                }

            }

        }

        cell = row.insertCell();
        if (k > 0) {
            cell.innerHTML = `<button class="seg_remove" onclick="del('` + id + `')">Remover</button>`;
        } else {
            cell.innerHTML = '';
        }
        cell.style.maxWidth = "8vw";
        cell.style.width = "8vw";
        row = myTable.insertRow();
    }

    myTable.id = 'seg_table';
    document.getElementById('qtd').innerHTML += (myTable.getElementsByTagName('tr').length - 2) + " Ocorrências"
    document.getElementById('seg_form').appendChild(myTable);
}

function view(id) {
    window.location = "/op/ssma/edit?id=" + id;
}

function del(id) {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/op/ssma/remove?id=" + id);

    xhr.onreadystatechange = function () {
        window.location = "/op/ssma/edit_select"
    }

    xhr.send();
}

insertTable();
removeNav();

var dia = new Date();
document.getElementById("filtro_data2").value = dia.toISOString().slice(0, 10);

function myFunction() {

    var input, filter, table, tr, td, i, txtValue, display;
    display = []
    table = document.getElementById("seg_table");
    tr = table.getElementsByTagName("tr");
    filters = [[1, 'setor'], [2, 'local'], [3, 'filtro_data', 'filtro_data2'], [4, 'coord'], [5, 'state']]
    for (i = 0; i < tr.length; i++) {
        var line = []
        filters.forEach((item, l) => {
            var id, index
            id = item[1]
            index = item[0]

            input = document.getElementById(id);
            filter = input.value.toUpperCase();
            if (i < tr.length && filter != '') {
                td = tr[i].getElementsByTagName("td")[index];
                if (td) {
                    txtValue = td.textContent || td.innerText;
                    if (index == 3) {
                        filtro3 = true
                    } else {
                        filter = input.value.toUpperCase();
                        filtro3 = false
                    }
                    if (txtValue.toUpperCase().indexOf(filter) > -1 || filtro3) {
                        if (filtro3) {
                            filtro1 = new Date(document.getElementById(item[1]).value)
                            filtro2 = new Date(document.getElementById(item[2]).value)
                            lista = txtValue.split(' ')[0].split('/')
                            filtro = new Date(lista[1] + '-' + lista[0] + '-' + lista[2])

                            if (filtro >= filtro1 && filtro <= filtro2) {
                                line.push("yes");
                            } else {
                                line.push("none");
                            }

                        } else {
                            line.push("yes");
                        }

                    } else {
                        line.push("none");
                    }
                }
            } else if (i < tr.length && filter == '') {
                line.push("no_filter");
            }
        });
        display.push(line)
    }

    var ocorr = table.getElementsByTagName('tr').length - 2
    for (k = 1; k < tr.length - 1; k++) {
        if (display[k].includes("none")) {
            tr[k].style.display = "none";
            ocorr -= 1
        } else {
            tr[k].style.display = "";
        }
    }

    document.getElementById('qtd').innerHTML = ocorr + " Ocorrências"

}