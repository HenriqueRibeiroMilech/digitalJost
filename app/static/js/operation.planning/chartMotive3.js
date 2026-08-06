function chart1() {

    ['stopped1', 'stopped2', 'stopped3'].forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(0);
        };
    });

    loadActionPlan(0);

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals0.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals0.count} paradas`

    document.getElementById('stopped3').style.display = 'flex'
    document.getElementById('stopped3').innerText = `${parseInt(received_data.area.totals0.goal - received_data.area.totals0.sum)} minutos`
    
    if (parseFloat(received_data.area.totals0.goal - received_data.area.totals0.sum) < 0) {
        document.getElementById('stopped3').style.backgroundColor = '#A52A2A'
    } else {
        document.getElementById('stopped3').style.backgroundColor = 'green'
    }

    createBarChart(received_data.area.barchart1, 'Top 5 Centros de Trabalho Parados', 'chart1');
    createBarChart(received_data.area.barchart2, 'Top 5 Paradas por Motivo', 'chart2');
    createPercentage(received_data.area.barchart3, 'Impacto de Paradas na Disponibilidade', 'chart3', 0);
    
}

function chart2() {

    ['stopped1', 'stopped2', 'stopped3'].forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(1);
        };
    });

    loadActionPlan(1);

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals1.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals1.count} paradas`
    document.getElementById('stopped3').innerText = `${parseInt(received_data.area.totals1.goal - received_data.area.totals1.sum)} minutos`

    if (parseFloat(received_data.area.totals1.goal - received_data.area.totals1.sum) < 0) {
        document.getElementById('stopped3').style.backgroundColor = '#A52A2A'
    } else {
        document.getElementById('stopped3').style.backgroundColor = 'green'
    }

    createBarChart(received_data.area.barchart4, 'Top 5 Centros de Trabalho Parados', 'chart4');
    createBarChart(received_data.area.barchart5, 'Top 5 Paradas por Motivo', 'chart5');
    createPercentage(received_data.area.barchart6, 'Impacto de Paradas na Disponibilidade', 'chart6', 1);
    
}

function chart3() {

    ['stopped1', 'stopped2', 'stopped3'].forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(2);
        };
    });

    loadActionPlan(2);

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals2.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals2.count} paradas`
    document.getElementById('stopped3').innerText = `${parseInt(received_data.area.totals2.goal - received_data.area.totals2.sum)} minutos`

    if (parseFloat(received_data.area.totals2.goal - received_data.area.totals2.sum) < 0) {
        document.getElementById('stopped3').style.backgroundColor = '#A52A2A'
    } else {
        document.getElementById('stopped3').style.backgroundColor = 'green'
    }

    createBarChart(received_data.area.barchart7, 'Top 5 Centros de Trabalho Parados', 'chart7');
    createBarChart(received_data.area.barchart8, 'Top 5 Paradas por Motivo', 'chart8');
    createPercentage(received_data.area.barchart9, 'Impacto de Paradas na Disponibilidade', 'chart9', 2);
    
}

function chart4() {

    ['stopped1', 'stopped2', 'stopped3'].forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(3);
        };
    });

    loadActionPlan(3);

    document.getElementById('stopped1').style.display = 'flex'
    document.getElementById('stopped2').style.display = 'flex'
    document.getElementById('stopped3').style.display = 'flex'
    document.getElementById('maintenance').style.display = 'none'



    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals3.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals3.count} paradas`
    document.getElementById('stopped3').innerText = `${parseInt(received_data.area.totals3.goal - received_data.area.totals3.sum)} minutos`

    if (parseFloat(received_data.area.totals3.goal - received_data.area.totals3.sum) < 0) {
        document.getElementById('stopped3').style.backgroundColor = '#A52A2A'
    } else {
        document.getElementById('stopped3').style.backgroundColor = 'green'
    }

    createBarChart(received_data.area.barchart10, 'Top 5 Centros de Trabalho Parados', 'chart10');
    createBarChart(received_data.area.barchart11, 'Top 5 Paradas por Motivo', 'chart11');
    createPercentage(received_data.area.barchart12, 'Impacto de Paradas na Disponibilidade', 'chart12', 3);
    
}

function chart5() {

    document.getElementById('stopped1').style.display = 'none'
    document.getElementById('stopped2').style.display = 'none'
    document.getElementById('stopped3').style.display = 'none'
    document.getElementById('maintenance').style.display = 'flex'


    function populateTable() {

        received_data.availability.forEach(info => {

            // Determina a qual div o dado pertence 
            const targetDivId = `infoTableBody${Object.entries(areasNames).find(([key, value]) => value == info.Workcenter_Group)?.[0]}`; 
            const targetDiv = document.getElementById(targetDivId);

            if (targetDiv) {
                // Cria um novo elemento para exibir os dados
                const row = document.createElement('tr'); 
        
                // Nome do Workcenter
                let cell = document.createElement('td');
                cell.textContent = info.Workcenter_Name;
                row.appendChild(cell);
        
                // Cálculo formatado
                cell = document.createElement('td');
                cell.textContent = `${(info.CALC * 100.0).toFixed(2)}%`;
                cell.style.fontWeight = 'bold';

                if ((info.CALC * 100.0).toFixed(2) >= 98) {
                    cell.style.backgroundColor = '#00B050'
                } else if ((info.CALC * 100.0).toFixed(2) >= 97) {
                    cell.style.backgroundColor = '#FFC000'
                } else {
                    cell.style.backgroundColor = '#FF5050'
                }

                row.appendChild(cell);
        
                // Adiciona na div correspondente
                targetDiv.appendChild(row);
            }
        });

    }

    if (received_data.availability) {
        document.getElementById('infoTableBody0').innerHTML = ''
        document.getElementById('infoTableBody1').innerHTML = ''
        document.getElementById('infoTableBody2').innerHTML = ''
        document.getElementById('infoTableBody3').innerHTML = ''
        populateTable()
    
        const edit = new Intl.DateTimeFormat('pt-BR', { month: 'long' });
        let monthName = edit.format(new Date(2022, received_data.month - 1, 1));
        monthName = monthName.charAt(0).toUpperCase() + monthName.slice(1);
    
        document.getElementById('monthToShow').innerHTML = monthName
        document.getElementById('overall').innerHTML = `${(received_data.overall * 100).toFixed(2)}%`
    }

}

function chart6() {

    document.getElementById('maintenance').style.display = 'none'


    loadActionPlan(4);
}