removeNav()
var last_changed = 0

function lastChange(index) {
    last_changed = index
}


var form = document.querySelector("#table_form")
form.addEventListener('change', function() {
    var http = new XMLHttpRequest();
    http.open("POST", "/demandas/entrada?index=" + last_changed + "&area={{area}}", true);
    http.setRequestHeader("Content-type","application/x-www-form-urlencoded");
    var data = new FormData(form);
    var params = new URLSearchParams(data).toString();
    http.send(params);
});

var myTable = document.createElement("table"),
row = myTable.insertRow(), cell;
myTable.id = "myTable"
myTable.style.padding = "0"
var perrow = 1;
{{table | tojson}}.forEach((entry, k) => {

    entry.forEach((info, i) => {

        if (i != 3) {
            var color =  "#163A8A"
            cell = row.insertCell();
            cell.id = "col_" + i + "row_" + k

            if (i == 0) {
                cell.style.width = "41vw";
                cell.style.maxWidth = "41vw";
                cell.innerHTML += info;
            } else if (i == 1) {
                cell.style.width = "20vw";
                cell.style.maxWidth = "20vw";
                cell.innerHTML += info;
            } else {
                 if (k > 0) {
                    cell.style.width = "30vw";
                    cell.style.maxWidth = "30vw";
                    cell.innerHTML += info;

                    cell = row.insertCell();
                    cell.style.width = "5vw";
                    cell.style.maxWidth = "5vw";
                    cell.innerHTML = `<button class="remove" type='button' onclick="remove(` + k + `,` + entry[3] + `)">&times;</button>`;
                } else {
                    cell.style.width = "30vw";
                    cell.style.maxWidth = "30vw";
                    cell.innerHTML += info;

                    cell = row.insertCell();
                    cell.style.width = "5vw";
                    cell.style.maxWidth = "5vw";

                }
            }
        }
    });
    var next = k + 1;
    if (next%perrow==0) { row = myTable.insertRow(); }

});

document.getElementById("table-container").innerHTML = '';
document.getElementById("table-container").appendChild(myTable);

function myFunction() {
  var input, filter, table, tr, td, i, txtValue, display;
  display = []
  table = document.getElementById("myTable");
  tr = table.getElementsByTagName("tr");
  filters = [[0, 'entrada']]
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

function addLine() {

    var table = document.getElementById("myTable");
    var row = table.insertRow(-1);

    var today = new Date().toLocaleDateString();

    var cell0 = row.insertCell(0);
    var cell1 = row.insertCell(1);
    var cell2 = row.insertCell(2);
    var cell3 = row.insertCell(3);

    cell0.innerHTML = `<textarea oninput="lastChange('` + (table.rows.length - 1) + `')" placeholder="Nome da entrada..." onclick='this.style.height = "";this.style.height = this.scrollHeight + "px"' style="width:40vw;max-width:40vw;color:#163A8A" class="table_input" name="col_0" onkeyup="this.value=this.value.replace(/'/g, '')"></textarea>`;
    cell0.style.width = "40vw";
    cell0.style.maxWidth = "40vw";
    cell0.id = "col_0row_" + table.index;

    cell1.style.width = "20vw";
    cell1.style.maxWidth = "20vw";
    cell1.innerHTML = '<select style="margin-top: 3vw" class="filter" name="col_1"><option>Sim</option><option>Não</option></select>';
    cell1.id = "col_1row_" + table.index;

    cell2.style.width = "30vw";
    cell2.style.maxWidth = "30vw";
    cell2.innerHTML = today + `<input type="hidden" name="col_2" value="` + today + `"/>`;
    cell2.id = "col_1row_" + table.index;

    cell3.innerHTML = `<button class="remove" onclick="remove(` + (table.rows.length - 1) + `)">&times;</button>`;
    cell3.style.width = "5vw";
    cell3.style.maxWidth = "5vw";

    table.scrollBy({
        top: (table.tBodies[0].offsetHeight),
        behavior: 'smooth'
    });
}

function remove(index, id) {

   var table = document.getElementById('myTable');
   var test = confirm('Toda a linha será deletada');
   if (test) {
        table.deleteRow(index)

        var http = new XMLHttpRequest();
        http.open("POST", "/demandas/entrada/update?id=" + id + "&area={{area}}", true);
        http.setRequestHeader("Content-type","application/x-www-form-urlencoded");

        form = document.querySelector("#table_form")
        var data = new FormData(form);
        var params = new URLSearchParams(data).toString();
        http.send(params);
   } else if (!test) {
        table.innerHTML = table.innerHTML
   }

   return false
}