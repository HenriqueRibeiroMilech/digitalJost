function createBarChart(data, title, elementId) {

    const maxYValue = Math.max(...data.map(item => Math.max(item.Log_Minutes_Sum, item.Log_Minutes_Count)));
    const hover1 = title.includes('meta') ? 'Meta' : 'Quantidade de Paradas'
    const hover2 = title.includes('meta') ? 'Média de Paradas' : 'Minutos Parados'
    var trace1 = {
        x: data.map(item => item.Label),
        y: data.map(item => item.Log_Minutes_Count.toFixed(0)),
        type: 'bar',
        marker: {
            color: 'blue'
        },
        text: data.map(item => item.Log_Minutes_Count.toFixed(0)),
        textfont: {
                        size: 12,
                        family: 'Arial Black, sans-serif',
                        weight: 'bold',
                        color: 'black'
                    },
        textposition: 'outside',
        hovertemplate: `<b>%{x}</b><br>Valor: %{y}<br><b>${hover1}</b><extra></extra>`

    };

    var trace2 = {
        x: data.map(item => item.Label),
        y: data.map(item => item.Log_Minutes_Sum.toFixed(0)),
        type: 'bar',
        marker: {
            color: 'orange'
        },
        text: data.map(item => item.Log_Minutes_Sum.toFixed(0)),
        textfont: {
                        size: 12,
                        family: 'Arial Black, sans-serif',
                        weight: 'bold',
                        color: 'black'
                    },
        textposition: 'outside',
        hovertemplate: `<b>%{x}</b><br>Valor: %{y}<br><b>${hover2}</b><extra></extra>`
    };

    var layout = {
        title: title,
        barmode: 'group',
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        xaxis: {
            tickangle: -45,
            automargin: true
        },
        yaxis: {
            range: [0, maxYValue * 1.2], // Definir a escala Y com 20% a mais que o valor máximo
        },
        showlegend: false,
        margin: {l: 40, r: 20, t:60, b: 30}
    };

    Plotly.newPlot(elementId, [trace1, trace2], layout, { displayModeBar: false });
}
