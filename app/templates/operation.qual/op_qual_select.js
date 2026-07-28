var myTable = document.createElement("table"),
row = myTable.insertRow(), cell;

var perrow = 1;
{{entries | tojson}}.forEach((entry, i) => {

    entry.forEach((info, i) => {
       if (info == "Editar") {
           let btn = document.createElement("button");
           btn.innerHTML = info;
           btn.style.backgroundColor = "#F4BC1C";
           btn.style.color = "white";
           btn.style.border = "0";
           btn.style.outline = "0";
           btn.onclick = function () {
               var url = 'edit?entryID=' + entry[5] + '&command=edit';
               window.location = url;
           };
           cell = row.insertCell();
           cell.appendChild(btn);
           cell.style.minWidth = "7vw";

       } else if (info == "Remover") {
           let btn = document.createElement("button");
           btn.innerHTML = info;
           btn.style.backgroundColor = "#DE0A26";
           btn.style.color = "white";
           btn.style.border = "0";
           btn.style.outline = "0";
           btn.onclick = function () {
               if (confirm('A entrada será deletada.')) {
                   var url = 'edit?entryID=' + entry[5] + '&command=remove';
                   window.location = url;
               }
           };
           cell = row.insertCell();
           cell.appendChild(btn);
           cell.style.minWidth = "9vw";

       } else if (info == entry[6]) {
            cell = row.insertCell();
            if (info == 'True') {
                cell.innerHTML = 'Campinas';
            } else {
                cell.innerHTML = 'Caxias do Sul';
            }
            cell.style.minWidth = "9vw";
           
       } else if (entry[5] != info) {
           cell = row.insertCell();
           cell.innerHTML = info;
           cell.style.minWidth = "9vw";
       }
        
    });

    var next = i + 1;
    if (next%perrow==0) { row = myTable.insertRow(); }

});

document.getElementById("entries_table").innerHTML = '';
myTable.id = 'qual_table';
myTable.style.maxWidth = "90vw;"
document.getElementById("entries_table").appendChild(myTable);

const hist_slider = document.querySelector('#hist_filters');
let hist_mouseDown = false;
let hist_startX, hist_scrollLeft;

let hist_startDragging = function (e) {
  hist_mouseDown = true;
  hist_startX = e.pageX - hist_slider.offsetLeft;
  hist_scrollLeft = hist_slider.scrollLeft;
  hist_slider.style.cursor = "grab"
};
let hist_stopDragging = function (event) {
  hist_mouseDown = false;
};

hist_slider.addEventListener('mousemove', (e) => {
  e.preventDefault();
  if(!hist_mouseDown) { return; }
  const hist_x = e.pageX - hist_slider.offsetLeft;
  const hist_scroll = hist_x - hist_startX;
  hist_slider.scrollLeft = hist_scrollLeft - hist_scroll;
});

hist_slider.addEventListener('mousedown', hist_startDragging, false);
hist_slider.addEventListener('mouseup', hist_stopDragging, false);
hist_slider.addEventListener('mouseleave', hist_stopDragging, false);

function myFunction() {
  var input, filter, table, tr, td, i, txtValue, display;
  display = []
  table = document.getElementById("qual_table");
  tr = table.getElementsByTagName("tr");
  filters = [[3, 'date'], [0, 'qual_sel'], [5, 'unit']]
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
                  filter = filter.split('-')[2] + '/' + filter.split('-')[1] + '/' + filter.split('-')[0];
               } else {
                  filter = input.value.toUpperCase();
               }

               if (txtValue.toUpperCase().indexOf(filter) > -1) {
                  line.push("yes");
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

  for (k = 0; k < tr.length - 1; k++) {
     if (display[k].includes("none")) {
         tr[k].style.display = "none";
     } else {
         tr[k].style.display = "";
     }
  }
}
