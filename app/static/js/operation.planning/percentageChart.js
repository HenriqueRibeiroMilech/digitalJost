function showPlannedGoal(totals) {
    const button = document.getElementById('stopped3');
    button.style.display = 'flex';
    if (!Number.isFinite(totals.goal)) {
        button.innerText = 'Sem base para a meta';
        button.style.backgroundColor = 'gray';
        button.title = 'Tempo planejado indisponível, inconsistente ou meta não cadastrada.';
        return;
    }
    const balance = totals.goal - totals.planned_sum;
    button.innerText = `${Math.trunc(balance)} minutos`;
    button.style.backgroundColor = balance < 0 ? '#A52A2A' : 'green';
    button.title = 'Saldo da meta considerando somente paradas dentro do tempo planejado.';
}

function createPercentage(data, title, elementId, areaId) {

    const goals = received_data.goal.find(data => data.presentationMotive == motiveId && data.presentationArea == areaId)
    const goal = goals?.goal ?? null;
    const values = data.map(item => Number.isFinite(item.Percentage) ? item.Percentage : null);
    const missingWeeks = data.length
        ? data.filter(item => !Number.isFinite(item.Percentage)).map(item => item.Label)
        : ['período consultado'];
    const maxYValue = Math.max(1, Number(goal) || 0, ...values.filter(value => value !== null));

    var trace0 = {
        x: ["meta"],
        y: [goal],
        name: 'Paradas em (%)',
        type: 'bar',
        marker: {
            color: 'blue',
            line: {
                color: 'black',
                width: 2
            }
        },
        text: [goal === null ? 'Sem meta' : `${goal}%`],
        textfont: {
            size: 12,
            family: 'Arial Black, sans-serif',
            weight: 'bold'
        },
        textposition: 'inside'

    };

    var trace1 = {
        x: data.map(item => item.Label),
        y: values.map(value => value === null ? null : Number(value.toFixed(2))),
        name: 'Paradas em (%)',
        type: 'bar',
        marker: {
            color: values.map(value => goal !== null && value < goal ? 'green' : '#A52A2A'),
            line: {
                color: 'black',
                width: 2
            }
        },
        text: values.map(value => value === null ? '' : `${value.toFixed(2)}%`),
        textfont: {
            size: 12,
            family: 'Arial Black, sans-serif',
            weight: 'bold'
        },
        textposition: 'inside'

    };

    var layout = {
        title: title,
        barmode: 'group',
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        showlegend: false,
        yaxis: {
            range: [0, maxYValue * 1.2],
        },
        annotations: missingWeeks.length ? [{
            text: `Sem base planejada: ${missingWeeks.join(', ')}`,
            xref: 'paper', yref: 'paper', x: 0.5, y: -0.22,
            showarrow: false
        }] : [],
        margin: {l: 40, r: 20, t:60, b: missingWeeks.length ? 70 : 30}
    };

    Plotly.newPlot(elementId, [trace0, trace1], layout, { displayModeBar: false });
}
