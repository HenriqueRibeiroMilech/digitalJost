const stopsButton = ['stopped1', 'stopped2', 'stopped3']

function chart1() {

    stopsButton.forEach((item) => {
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
    
    document.getElementById('areaName').innerHTML = 'Movimentação'
}

function chart2() {

    stopsButton.forEach((item) => {
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

    stopsButton.forEach((item) => {
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

    motiveId = 1

    stopsButton.forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(3);
        };
    });

    loadActionPlan(3);


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
    
    document.getElementById('areaName').innerHTML = 'Movimentação'
}

function chart5() {
    
    motiveId = 2

    stopsButton.forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(0);
        };
    });

    loadActionPlan(0);

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals4.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals4.count} paradas`
    document.getElementById('stopped3').innerText = `${parseInt(received_data.area.totals4.goal - received_data.area.totals4.sum)} minutos`

    if (parseFloat(received_data.area.totals4.goal - received_data.area.totals4.sum) < 0) {
        document.getElementById('stopped3').style.backgroundColor = '#A52A2A'
    } else {
        document.getElementById('stopped3').style.backgroundColor = 'green'
    }

    createBarChart(received_data.area.barchart13, 'Top 5 Centros de Trabalho Parados', 'chart13');
    createBarChart(received_data.area.barchart14, 'Top 5 Paradas por Motivo', 'chart14');
    createPercentage(received_data.area.barchart15, 'Impacto de Paradas na Disponibilidade', 'chart15', 0);
    
    document.getElementById('areaName').innerHTML = 'Material'
}

function chart6() {

    stopsButton.forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(1);
        };
    });

    loadActionPlan(1);

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals5.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals5.count} paradas`
    document.getElementById('stopped3').innerText = `${parseInt(received_data.area.totals5.goal - received_data.area.totals5.sum)} minutos`

    if (parseFloat(received_data.area.totals5.goal - received_data.area.totals5.sum) < 0) {
        document.getElementById('stopped3').style.backgroundColor = '#A52A2A'
    } else {
        document.getElementById('stopped3').style.backgroundColor = 'green'
    }

    createBarChart(received_data.area.barchart16, 'Top 5 Centros de Trabalho Parados', 'chart16');
    createBarChart(received_data.area.barchart17, 'Top 5 Paradas por Motivo', 'chart17');
    createPercentage(received_data.area.barchart18, 'Impacto de Paradas na Disponibilidade', 'chart18', 1);
    
}

function chart7() {

    stopsButton.forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(2);
        };
    });

    loadActionPlan(2);

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals6.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals6.count} paradas`
    document.getElementById('stopped3').innerText = `${parseInt(received_data.area.totals6.goal - received_data.area.totals6.sum)} minutos`

    if (parseFloat(received_data.area.totals6.goal - received_data.area.totals6.sum) < 0) {
        document.getElementById('stopped3').style.backgroundColor = '#A52A2A'
    } else {
        document.getElementById('stopped3').style.backgroundColor = 'green'
    }

    createBarChart(received_data.area.barchart19, 'Top 5 Centros de Trabalho Parados', 'chart19');
    createBarChart(received_data.area.barchart20, 'Top 5 Paradas por Motivo', 'chart20');
    createPercentage(received_data.area.barchart21, 'Impacto de Paradas na Disponibilidade', 'chart21', 2);
    
}

function chart8() {

    stopsButton.forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(3);
        };
    });

    loadActionPlan(3);

    document.getElementById('stopped1').style.display = 'flex'
    document.getElementById('stopped2').style.display = 'flex'
    document.getElementById('stopped3').style.display = 'flex'

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals7.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals7.count} paradas`
    document.getElementById('stopped3').innerText = `${parseInt(received_data.area.totals7.goal - received_data.area.totals7.sum)} minutos`

    if (parseFloat(received_data.area.totals7.goal - received_data.area.totals7.sum) < 0) {
        document.getElementById('stopped3').style.backgroundColor = '#A52A2A'
    } else {
        document.getElementById('stopped3').style.backgroundColor = 'green'
    }

    createBarChart(received_data.area.barchart22, 'Top 5 Centros de Trabalho Parados', 'chart22');
    createBarChart(received_data.area.barchart23, 'Top 5 Paradas por Motivo', 'chart23');
    createPercentage(received_data.area.barchart24, 'Impacto de Paradas na Disponibilidade', 'chart24', 3);
    
    document.getElementById('areaName').innerHTML = 'Material'
}

function chart9() {

    document.getElementById('stopped1').style.display = 'none'
    document.getElementById('stopped2').style.display = 'none'
    document.getElementById('stopped3').style.display = 'none'

    document.getElementById('areaName').innerHTML = 'Movimentação e Material'

    loadActionPlan(4);
}