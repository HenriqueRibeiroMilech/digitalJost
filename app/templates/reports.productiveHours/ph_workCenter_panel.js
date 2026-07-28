function update() {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", '/dashboards/chp/select');

    xhr.onreadystatechange = function () {
        document.getElementById('data_ct').style.animationPlayState = "paused";
        var centros = JSON.parse(xhr.responseText)['data'];
        var myTable = document.createElement("table"),
        row = myTable.insertRow(), cell;

        var perrow = 1;
        centros.forEach((entry, k) => {
            entry.forEach((info, i) => {
                cell = row.insertCell();
                if (info != 'Produção' && k > 0 && i == 1) {
                    cell.style.backgroundColor = "#FF6700";
                }
                if ((info < 0 || info > 0) && i == 4) {
                    cell.style.backgroundColor = "#B30000";
                    cell.style.fontWeight = "bold";
                }
                cell.innerHTML = '<a>' + info + '</a><input type="hidden" name="col_' + i + '" value="' + info + '"/>';
                if (i == 0 || i == 1) {
                    if (i == 0 && k > 0) {
                        cell.innerHTML = `<button class="table_btn" onclick="window.location=('/dashboards/chp/ct?ct=` + info +  `')">` + info + `</button>`;
                    }
                    cell.style.width = "26vw";
                    cell.style.maxWidth = "26vw";
                } else {
                    cell.style.width = "13vw";
                    cell.style.maxWidth = "13vw";
                }
            });
            var next = k + 1;
            if (next%perrow==0) { row = myTable.insertRow(); }

        });

    document.getElementById("data_ct").innerHTML = '';
    myTable.id = "ct_status"
    document.getElementById("data_ct").appendChild(myTable);
    }

    xhr.send();
}

window.addEventListener('load', function () {
    update();
    var fetchInterval = 30000;
    setInterval(update, fetchInterval);
});