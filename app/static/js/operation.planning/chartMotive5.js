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
    showPlannedGoal(received_data.area.totals0);

    createBarChart(received_data.area.barchart1, 'Top 5 Paradas de Processo', 'chart1');
    createBarChart(received_data.area.barchart2, 'Top 5 Paradas por Motivo', 'chart2');
    createPercentage(received_data.area.barchart3, 'Impacto de Paradas na Disponibilidade', 'chart3', 0);
    
}

function chart2() {

    ['stopped1', 'stopped2', 'stopped3'].forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(1);
        };
    });

    loadActionPlan(-1);

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals1.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals1.count} paradas`
    showPlannedGoal(received_data.area.totals1);

    createBarChart(received_data.extra0, 'Meta x Média - Minutos de Troca de Insumo', 'chart4');

}

function chart3() {

    ['stopped1', 'stopped2', 'stopped3'].forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(1);
        };
    });

    loadActionPlan(1);

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals1.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals1.count} paradas`
    showPlannedGoal(received_data.area.totals1);

    createBarChart(received_data.area.barchart4, 'Top 5 Paradas de Processo', 'chart5');
    createBarChart(received_data.area.barchart5, 'Top 5 Paradas por Motivo', 'chart6');
    createPercentage(received_data.area.barchart6, 'Impacto de Paradas na Disponibilidade', 'chart7', 1);
    
}

function chart4() {

    ['stopped1', 'stopped2', 'stopped3'].forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(2);
        };
    });

    loadActionPlan(-2);

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals2.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals2.count} paradas`
    showPlannedGoal(received_data.area.totals2);

    createBarChart(received_data.extra1, 'Meta x Média - Minutos de Setup', 'chart8');

}

function chart5() {

    ['stopped1', 'stopped2', 'stopped3'].forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(2);
        };
    });

    loadActionPlan(2);

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals2.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals2.count} paradas`
    showPlannedGoal(received_data.area.totals2);

    createBarChart(received_data.area.barchart7, 'Top 5 Paradas de Processo', 'chart9');
    createBarChart(received_data.area.barchart8, 'Top 5 Paradas por Motivo', 'chart10');
    createPercentage(received_data.area.barchart9, 'Impacto de Paradas na Disponibilidade', 'chart11', 2);
    
}

function chart6() {

    ['stopped1', 'stopped2', 'stopped3'].forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(3);
        };
    });

    loadActionPlan(-3);

    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals3.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals3.count} paradas`
    showPlannedGoal(received_data.area.totals3);

    createBarChart(received_data.extra2, 'Meta x Média - Minutos de Setup', 'chart12');

}

function chart7() {

    ['stopped1', 'stopped2', 'stopped3'].forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(3);
        };
    });

    loadActionPlan(3);

    document.getElementById('stopped1').style.display = 'flex'
    document.getElementById('stopped2').style.display = 'flex'
    document.getElementById('stopped3').style.display = 'flex'


    document.getElementById('stopped1').innerText = `${parseInt(received_data.area.totals3.sum)} minutos parados`
    document.getElementById('stopped2').innerText = `${received_data.area.totals3.count} paradas`
    showPlannedGoal(received_data.area.totals3);

    createBarChart(received_data.area.barchart10, 'Top 5 Paradas de Processo', 'chart13');
    createBarChart(received_data.area.barchart11, 'Top 5 Paradas por Motivo', 'chart14');
    createPercentage(received_data.area.barchart12, 'Impacto de Paradas na Disponibilidade', 'chart15', 3);
    

}

function chart8() {

    document.getElementById('stopped1').style.display = 'none'
    document.getElementById('stopped2').style.display = 'none'
    document.getElementById('stopped3').style.display = 'none'

    loadActionPlan(4);
}
