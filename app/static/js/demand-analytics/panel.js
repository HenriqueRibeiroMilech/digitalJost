(function () {
    'use strict';

    const config = window.demandAnalyticsConfig || {};
    const elements = {
        dashboard: document.getElementById('da-dashboard'),
        loading: document.getElementById('da-loading'),
        error: document.getElementById('da-error'),
        content: document.getElementById('da-content'),
        summary: document.getElementById('da-summary')
    };
    let loading = false;
    let loaded = false;
    let plotlyLoading = null;

    if (!elements.dashboard) return;

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function chartEmpty(elementId, message) {
        const element = document.getElementById(elementId);
        if (window.Plotly) window.Plotly.purge(element);
        element.innerHTML = `<div class="da-chart-empty">${escapeHtml(message)}</div>`;
    }

    function plot(elementId, traces, layout) {
        if (!window.Plotly) {
            chartEmpty(elementId, 'Não foi possível carregar o gráfico.');
            return;
        }
        window.Plotly.react(elementId, traces, Object.assign({
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Montserrat, sans-serif', color: '#17202a', size: 11 },
            margin: { l: 45, r: 20, t: 20, b: 50 },
            showlegend: true
        }, layout || {}), {
            displayModeBar: false,
            responsive: true
        });
    }

    function loadPlotly() {
        if (window.Plotly) return Promise.resolve();
        if (plotlyLoading) return plotlyLoading;
        plotlyLoading = new Promise(function (resolve, reject) {
            const script = document.createElement('script');
            script.src = config.plotlyUrl;
            script.async = true;
            script.onload = resolve;
            script.onerror = function () {
                reject(new Error('Não foi possível carregar a biblioteca dos gráficos.'));
            };
            document.head.appendChild(script);
        });
        return plotlyLoading;
    }

    function hasValues(items) {
        return items.some(function (item) { return Number(item.value) > 0; });
    }

    function renderSummary(summary) {
        const items = [
            [summary.total, 'Solicitações'],
            [summary.pending, 'Em análise'],
            [summary.active, 'Ativas'],
            [summary.completed, 'Concluídas']
        ];
        elements.summary.innerHTML = items.map(function (item) {
            return `<article class="da-summary__item"><strong>${escapeHtml(item[0])}</strong><span>${escapeHtml(item[1])}</span></article>`;
        }).join('');
    }

    function renderStatusChart(items) {
        if (!hasValues(items)) {
            chartEmpty('da-status-chart', 'Ainda não existem solicitações nesta área.');
            return;
        }
        plot('da-status-chart', [{
            type: 'pie',
            labels: items.map(function (item) { return item.label; }),
            values: items.map(function (item) { return item.value; }),
            hole: .58,
            textinfo: 'label+value',
            hovertemplate: '%{label}: %{value}<extra></extra>',
            marker: {
                colors: ['#5f6b78', '#8a96a3', '#163a8a', '#ef7b04', '#18794e', '#b42318', '#7b2cbf']
            }
        }], {
            margin: { l: 10, r: 10, t: 20, b: 25 },
            legend: { orientation: 'h', x: 0, y: -0.05 }
        });
    }

    function renderTypeChart(items) {
        if (!hasValues(items)) {
            chartEmpty('da-type-chart', 'Ainda não existem tipos para comparar.');
            return;
        }
        plot('da-type-chart', [{
            type: 'bar',
            x: items.map(function (item) { return item.label; }),
            y: items.map(function (item) { return item.value; }),
            text: items.map(function (item) { return item.value; }),
            textposition: 'auto',
            marker: { color: ['#163a8a', '#ef7b04', '#b42318'] },
            hovertemplate: '%{x}: %{y}<extra></extra>'
        }], {
            showlegend: false,
            yaxis: {
                rangemode: 'tozero',
                showgrid: false,
                zeroline: false,
                showticklabels: false
            }
        });
    }

    function renderMonthlyChart(items) {
        const hasMonthlyValues = items.some(function (item) {
            return item.requested || item.completed;
        });
        if (!hasMonthlyValues) {
            chartEmpty('da-monthly-chart', 'Nenhuma movimentação registrada nos últimos 12 meses.');
            return;
        }
        const labels = items.map(function (item) { return item.label; });
        plot('da-monthly-chart', [
            {
                type: 'bar',
                name: 'Solicitadas',
                x: labels,
                y: items.map(function (item) { return item.requested; }),
                marker: { color: '#163a8a' },
                hovertemplate: '%{x}: %{y} solicitadas<extra></extra>'
            },
            {
                type: 'bar',
                name: 'Concluídas',
                x: labels,
                y: items.map(function (item) { return item.completed; }),
                marker: { color: '#18794e' },
                hovertemplate: '%{x}: %{y} concluídas<extra></extra>'
            }
        ], {
            barmode: 'group',
            legend: { orientation: 'h', x: 0, y: 1.12 },
            yaxis: { title: 'Demandas', rangemode: 'tozero', dtick: 1 }
        });
    }

    function renderResponsibleChart(items) {
        if (!hasValues(items)) {
            chartEmpty('da-responsible-chart', 'Ainda não existem demandas ativas atribuídas.');
            return;
        }
        plot('da-responsible-chart', [{
            type: 'bar',
            orientation: 'h',
            x: items.map(function (item) { return item.value; }),
            y: items.map(function (item) { return item.label; }),
            text: items.map(function (item) { return item.value; }),
            textposition: 'auto',
            marker: { color: '#163a8a' },
            hovertemplate: '%{y}: %{x} demandas ativas<extra></extra>'
        }], {
            showlegend: false,
            margin: { l: 150, r: 20, t: 20, b: 35 },
            xaxis: {
                rangemode: 'tozero',
                showgrid: false,
                zeroline: false,
                showticklabels: false
            },
            yaxis: { autorange: 'reversed', automargin: true }
        });
    }

    function render(payload) {
        renderSummary(payload.summary || {});
        renderStatusChart(payload.status || []);
        renderTypeChart(payload.types || []);
        renderMonthlyChart(payload.monthly || []);
        renderResponsibleChart(payload.responsibles || []);
    }

    async function load() {
        if (loading || loaded) return;
        loading = true;
        elements.loading.hidden = false;
        elements.error.hidden = true;
        try {
            const url = new URL(config.apiUrl, window.location.origin);
            url.searchParams.set('area', config.area);
            const results = await Promise.all([
                fetch(url.pathname + url.search, {
                    credentials: 'same-origin',
                    headers: { Accept: 'application/json' }
                }),
                loadPlotly()
            ]);
            const response = results[0];
            if (response.redirected && new URL(response.url).pathname.includes('/login')) {
                window.location.assign(response.url);
                return;
            }
            const payload = await response.json().catch(function () { return {}; });
            if (!response.ok) {
                throw new Error(payload.error || 'Não foi possível carregar os indicadores da área.');
            }
            render(payload);
            elements.content.hidden = false;
            loaded = true;
        } catch (error) {
            elements.error.textContent = error.message;
            elements.error.hidden = false;
        } finally {
            elements.loading.hidden = true;
            loading = false;
        }
    }

    document.addEventListener('demand-analytics:show', load);
    window.demandAnalyticsPanel = { show: load };
}());
