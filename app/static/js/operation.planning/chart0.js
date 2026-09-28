function chart0() {

    ['stopped1', 'stopped2', 'stopped3'].forEach((item) => {
        document.getElementById(item).onclick = function() {
            openStops(4);
        };
    });

    document.getElementById('stopped1').innerText = `${parseInt(received_data.totals.sum)} minutos parados`
    document.getElementById('stopped1').style.display = 'flex'
    document.getElementById('stopped2').innerText = `${received_data.totals.count} paradas`
    document.getElementById('stopped2').style.display = 'flex'
    document.getElementById('stopped3').style.display = 'none'
    document.getElementById('areaName').innerHTML = areaName


    const chartsContainer = document.getElementById('charts-container1');
    chartsContainer.innerHTML = '';

    for (const [area, areaData] of Object.entries(received_data.general)) {

        const weeks = ['meta', ...new Set(areaData.map(d => d.WEEK))];
        const traces = [];

        const metaValues = {};
        received_data.goal.filter(data => data.presentationArea == area).forEach(item => {
            const chave = item.presentationMotiveName;
            const valor = item.goal;
            metaValues[chave] = valor;
        });

        const quantitiesByMS = {};

        areaData.forEach(entry => {
            entry.Log_Minutes_Percentage = Number.isFinite(entry.Log_Minutes_Percentage)
                ? Number(entry.Log_Minutes_Percentage.toFixed(2)) : null;
        });
        
        areaData.forEach(entry => {
            if (!quantitiesByMS[entry.WEEK]) {
                quantitiesByMS[entry.WEEK] = {};
            }
            quantitiesByMS[entry.WEEK][entry.MS] = entry.Log_Minutes_Percentage;
            
        });

        quantitiesByMS['meta'] = {};
        received_data.goal.filter(data => data.presentationArea == area).forEach(item => {
            const chave = item.presentationMotiveName;
            const valor = item.goal;
            quantitiesByMS['meta'][chave] = valor;
        });


        const msColoridos = current_area;
        const missingWeeks = new Set(areaData.filter(
            entry => entry.Log_Minutes_Percentage === null
        ).map(entry => entry.WEEK));
        if (!areaData.length) missingWeeks.add('período consultado');

        weeks.sort((a, b) => (a === 'meta' ? -1 : a - b)).forEach(week => {
            let totalHeight = 0;
            if (week !== 'meta') {
                if (missingWeeks.has(week)) return;
                for (const [ms, meta] of Object.entries(metaValues)) {
                    const quantity = quantitiesByMS[week] ? (quantitiesByMS[week][ms] || 0) : 0;

                    const isMsColorido = msColoridos.includes(ms);

                    const quantityTrace = {
                        x: [week],
                        y: [quantity],
                        name: `${ms}`,
                        type: 'bar',
                        marker: { 
                            color: isMsColorido ? (quantity >= meta ? '#A52A2A' : 'green') : 'gray',
                            line: {
                                color: 'black',
                                width: 2
                            }
                        },
                        text: isMsColorido ? [`${quantity}%`] : [``],
                        hovertemplate: `<b>Area:</b> ${ms}<br><b>Real:</b> ${quantity}%<extra></extra>`,
                        textfont: {
                            size: 12,
                            family: 'Arial Black, sans-serif',
                            weight: 'bold'
                        },
                        textposition: 'inside',
                        base: totalHeight
                    };
                    traces.push(quantityTrace);
                    totalHeight += quantity;
                }
            }

            if (week === 'meta') {
                totalHeight = 0;
                for (const [ms, meta] of Object.entries(metaValues)) {

                    const isMsColorido = msColoridos.includes(ms);

                    const metaTrace = {
                        x: [week],
                        y: [meta],
                        name: `${ms}`,
                        type: 'bar',
                        marker: { 
                            color: isMsColorido ? 'blue' : 'gray',
                            line: {
                                color: 'black',
                                width: 2
                            }
                        },
                        textfont: {
                            size: 12,
                            family: 'Arial Black, sans-serif',
                            weight: 'bold'
                        },
                        text: isMsColorido ? [`${meta}%`] : [``],
                        hovertemplate: `<b>Area:</b> ${ms}<br><b>Meta:</b> ${meta}%<extra></extra>`,
                        textposition: 'inside',
                        base: totalHeight
                    };
                    traces.push(metaTrace);
                    totalHeight += meta;
                }
            }
        });

        const totalPerWeek = weeks.map(week => {
            if (missingWeeks.has(week)) return {week, total: null};
            const total = Object.values(quantitiesByMS[week] || {}).reduce((acc, curr) => acc + (Number(curr) || 0), 0).toFixed(2);
            return { week, total };
        });

        const scatterTrace = {
            x: totalPerWeek.map(w => w.week),
            y: totalPerWeek.map(w => w.total),
            mode: 'lines+markers+text',
            name: 'Total',
            marker: { 
                color: 'black', 
                size: 10 
            },
            line: { 
                color: 'black', 
                width: 2 
            },
            text: totalPerWeek.map(w => w.total === null ? '' : `${w.total}%`),
            textposition: 'top center',
            textfont: {
                size: 12,
                family: 'Arial Black, sans-serif',
                weight: 'bold'
            }
        };
        traces.push(scatterTrace);
        const maxTotal = Math.max(1, ...totalPerWeek.filter(
            item => item.total !== null
        ).map(item => Number(item.total)));

        const layout = {
            title: `${areasNames[area]}`,
            barmode: 'stack',
            showlegend: false,
            annotations: missingWeeks.size ? [{
                text: `Sem base planejada: ${[...missingWeeks].join(', ')}`,
                xref: 'paper', yref: 'paper', x: 0.5, y: -0.22,
                showarrow: false
            }] : [],
            margin: {l: 30, r: 20, t:60, b: missingWeeks.size ? 70 : 30},
            yaxis: {
                range: [0, Math.max(45, maxTotal * 1.2)]
            }                
        };
        
        const chartDiv = document.createElement('div');
        chartDiv.classList.add('chart');
        chartsContainer.appendChild(chartDiv);

        Plotly.newPlot(chartDiv, traces, layout, { displayModeBar: false });
    }
}
