function createPercentage(data, title, elementId, areaId) {

    const goals = received_data.goal.find(data => data.presentationMotive == motiveId && data.presentationArea == areaId)
    const maxYValue = Math.max(...data.map(item => item.Percentage));

    var trace0 = {
        x: ["meta"],
        y: [goals.goal],
        name: 'Paradas em (%)',
        type: 'bar',
        marker: {
            color: 'blue',
            line: {
                color: 'black',
                width: 2
            }
        },
        text: [`${goals.goal}%`],
        textfont: {
            size: 12,
            family: 'Arial Black, sans-serif',
            weight: 'bold'
        },
        textposition: 'inside'

    };

    var trace1 = {
        x: data.map(item => item.Label),
        y: data.map(item => item.Percentage.toFixed(2)),
        name: 'Paradas em (%)',
        type: 'bar',
        marker: {
            color: data.map(item => item.Percentage < goals.goal ? 'green' : '#A52A2A'), // Verde se menor que goal.value
            line: {
                color: 'black',
                width: 2
            }
        },
        text: data.map(item => `${item.Percentage.toFixed(2)}%`),
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
        margin: {l: 40, r: 20, t:60, b: 30}
    };

    Plotly.newPlot(elementId, [trace0, trace1], layout, { displayModeBar: false });
}
