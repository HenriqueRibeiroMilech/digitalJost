(function () {
    'use strict';

    const config = window.demandTrackingConfig;
    const state = {
        demands: [],
        responsibles: [],
        options: { status: [], difficulty: [], type: [] },
        collapsedOwners: new Set()
    };
    const elements = {
        summary: document.getElementById('dt-summary'),
        search: document.getElementById('dt-search'),
        responsible: document.getElementById('dt-filter-responsible'),
        type: document.getElementById('dt-filter-type'),
        status: document.getElementById('dt-filter-status'),
        difficulty: document.getElementById('dt-filter-difficulty'),
        urgency: document.getElementById('dt-filter-urgency'),
        clearFilters: document.getElementById('dt-clear-filters'),
        periodStart: document.getElementById('dt-period-start'),
        periodEnd: document.getElementById('dt-period-end'),
        loading: document.getElementById('dt-loading'),
        board: document.getElementById('dt-board'),
        modal: document.getElementById('dt-modal'),
        modalContent: document.getElementById('dt-modal-content')
    };

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function normalize(value) {
        return String(value || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase();
    }

    function slug(value) {
        return normalize(value)
            .replace(/[^a-z0-9]+/g, '-')
            .replace(/^-|-$/g, '');
    }

    function display(value, fallback) {
        return value == null || value === ''
            ? (fallback || 'Não informado')
            : value;
    }

    function formatDate(value, withTime) {
        if (!value) return 'Não informado';
        const raw = String(value);
        const parts = raw.substring(0, 10).split('-');
        if (parts.length !== 3) return raw;
        const date = `${parts[2]}/${parts[1]}/${parts[0]}`;
        return withTime && raw.length >= 16
            ? `${date} ${raw.substring(11, 16)}`
            : date;
    }

    function formatNumber(value, decimals) {
        if (value == null || value === '') return 'Não informado';
        const number = Number(value);
        if (!Number.isFinite(number)) return display(value);
        return number.toLocaleString('pt-BR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: decimals == null ? 2 : decimals
        });
    }

    function typeLabel(type) {
        return {
            melhoria: 'Melhoria',
            projeto: 'Projeto',
            erro: 'Erro'
        }[type] || display(type);
    }

    function parseDate(value) {
        if (!value) return null;
        const date = new Date(`${String(value).substring(0, 10)}T00:00:00`);
        return Number.isNaN(date.getTime()) ? null : date;
    }

    function isLate(demand) {
        if (!demand.deadline || ['Concluído', 'Cancelado'].includes(demand.status)) {
            return false;
        }
        const deadline = parseDate(demand.deadline);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return Boolean(deadline && deadline < today);
    }

    function apiUrl(path) {
        const url = new URL(`${config.apiRoot}${path || ''}`, window.location.origin);
        url.searchParams.set('area', config.area);
        return url.toString();
    }

    async function api(path) {
        const response = await fetch(apiUrl(path), {
            headers: { Accept: 'application/json' }
        });
        let payload = {};
        try {
            payload = await response.json();
        } catch (error) {
            payload = {};
        }
        if (!response.ok) {
            throw new Error(payload.error || 'Não foi possível carregar o acompanhamento.');
        }
        return payload;
    }

    function optionList(items, selected) {
        return items.map(function (item) {
            const value = typeof item === 'object' ? item.id : item;
            const label = typeof item === 'object' ? item.name : item;
            return `<option value="${escapeHtml(value)}"${String(value) === String(selected) ? ' selected' : ''}>${escapeHtml(label)}</option>`;
        }).join('');
    }

    function initializePeriod() {
        const end = new Date();
        const start = new Date(end.getFullYear(), end.getMonth() - 11, 1);
        elements.periodStart.value = localIsoDate(start);
        elements.periodEnd.value = localIsoDate(end);
    }

    function localIsoDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function configureFilters() {
        elements.responsible.innerHTML = '<option value="">Todos</option>' +
            optionList(state.responsibles, '');
        elements.type.innerHTML = '<option value="">Todos</option>' +
            (state.options.type || []).map(function (type) {
                return `<option value="${escapeHtml(type)}">${escapeHtml(typeLabel(type))}</option>`;
            }).join('');
        elements.status.innerHTML = '<option value="">Todos</option>' +
            '<option value="__active__" selected>Ativas</option>' +
            optionList(state.options.status || [], '__active__') +
            '<option value="__late__">Atrasadas</option>';
        elements.difficulty.innerHTML = '<option value="">Todas</option>' +
            optionList(state.options.difficulty || [], '');
        elements.urgency.innerHTML = '<option value="">Todas</option>' +
            optionList(['Alta', 'Média', 'Baixa'], '');
    }

    function baseFilteredDemands() {
        const search = normalize(elements.search.value);
        return state.demands.filter(function (demand) {
            return (!search || normalize(demand.title).includes(search)) &&
                (!elements.responsible.value || String(demand.responsibleId || '') === elements.responsible.value) &&
                (!elements.type.value || demand.demandType === elements.type.value) &&
                (!elements.difficulty.value || demand.difficulty === elements.difficulty.value) &&
                (!elements.urgency.value || demand.urgency === elements.urgency.value);
        });
    }

    function boardDemands() {
        const status = elements.status.value;
        return baseFilteredDemands().filter(function (demand) {
            if (!status) return true;
            if (status === '__active__') {
                return ['A Fazer', 'Em Andamento', 'Pausado'].includes(demand.status);
            }
            if (status === '__late__') return isLate(demand);
            return demand.status === status;
        });
    }

    function completedInPeriod(demands) {
        const start = parseDate(elements.periodStart.value);
        const end = parseDate(elements.periodEnd.value);
        if (!start || !end || start > end) return [];
        end.setHours(23, 59, 59, 999);
        return demands.filter(function (demand) {
            if (demand.status !== 'Concluído') return false;
            const completed = parseDate(demand.requestFinalDate);
            return completed && completed >= start && completed <= end;
        });
    }

    function isCompletedOnTime(demand) {
        const completed = parseDate(demand.requestFinalDate);
        const deadline = parseDate(demand.deadline);
        return Boolean(completed && deadline && completed <= deadline);
    }

    function businessDaysBetween(startValue, endValue) {
        const start = parseDate(startValue);
        const end = parseDate(endValue);
        if (!start || !end || start > end) return null;
        let total = 0;
        const cursor = new Date(start);
        while (cursor < end) {
            const day = cursor.getDay();
            if (day !== 0 && day !== 6) total += 1;
            cursor.setDate(cursor.getDate() + 1);
        }
        return total;
    }

    function renderSummary() {
        const demands = baseFilteredDemands();
        const active = demands.filter(function (item) {
            return ['A Fazer', 'Em Andamento', 'Pausado'].includes(item.status);
        });
        const completed = completedInPeriod(demands);
        const withDeadline = completed.filter(function (item) { return item.deadline; });
        const onTime = withDeadline.filter(isCompletedOnTime).length;
        const durations = completed.map(function (item) {
            return businessDaysBetween(item.requestDate, item.requestFinalDate);
        }).filter(function (value) { return value != null; });
        const average = durations.length
            ? durations.reduce(function (sum, value) { return sum + value; }, 0) / durations.length
            : null;
        const items = [
            [active.length, 'Ativas'],
            [active.filter(function (item) { return item.status === 'Em Andamento'; }).length, 'Em andamento'],
            [active.filter(isLate).length, 'Atrasadas'],
            [completed.length, 'Concluídas no período'],
            [withDeadline.length ? `${Math.round(onTime / withDeadline.length * 100)}%` : '—', 'No prazo'],
            [average == null ? '—' : formatNumber(average, 1), 'Dias úteis médios']
        ];
        elements.summary.innerHTML = items.map(function (item) {
            return `<div class="dm-summary__item"><strong>${escapeHtml(item[0])}</strong><span>${escapeHtml(item[1])}</span></div>`;
        }).join('');
    }

    function renderBoard() {
        const demands = boardDemands();
        if (!demands.length) {
            elements.board.innerHTML = '<div class="dm-empty"><strong>Nenhuma demanda encontrada.</strong><br>Ajuste os filtros para consultar outro grupo.</div>';
            return;
        }
        const groups = new Map();
        demands.forEach(function (demand) {
            const key = demand.responsibleId || '__unassigned__';
            if (!groups.has(key)) {
                groups.set(key, {
                    key: key,
                    name: demand.responsibleName || 'Sem responsável ativo',
                    demands: []
                });
            }
            groups.get(key).demands.push(demand);
        });
        elements.board.innerHTML = Array.from(groups.values()).map(renderOwner).join('');
    }

    function renderOwner(group) {
        const collapsed = state.collapsedOwners.has(group.key);
        const active = group.demands.filter(function (item) {
            return !['Concluído', 'Cancelado'].includes(item.status);
        }).length;
        return `
            <section class="dm-owner${collapsed ? ' dm-owner--collapsed' : ''}" data-owner-section="${escapeHtml(group.key)}">
                <button class="dm-owner__header" type="button" data-owner-toggle="${escapeHtml(group.key)}" aria-expanded="${!collapsed}">
                    <span class="dm-owner__chevron" aria-hidden="true">▼</span>
                    <span class="dm-owner__name">${escapeHtml(group.name)}</span>
                    <span class="dm-owner__capacity">${group.demands.length} demanda(s) · ${active} ativa(s)</span>
                </button>
                <div class="dm-owner__cards">${group.demands.map(renderCard).join('')}</div>
            </section>`;
    }

    function readonlyCard(label, value, modifier) {
        return `<div class="dt-readonly-card${modifier ? ` dt-readonly-card--${modifier}` : ''}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(display(value))}</strong></div>`;
    }

    function renderCard(demand) {
        const late = isLate(demand);
        const tasks = `${demand.completedTasks || 0}/${demand.totalTasks || 0}`;
        return `
            <article class="dm-card dm-card--status-${slug(demand.status)}${late ? ' dm-card--late' : ''}" data-management-id="${demand.managementId}" tabindex="0" role="button" aria-label="Abrir detalhes de ${escapeHtml(demand.title)}">
                <div class="dm-card__top">
                    <div class="dm-card__identity">
                        <div class="dm-badges">
                            <span class="dm-badge dm-badge--type dm-badge--type-${slug(demand.demandType)}">${escapeHtml(typeLabel(demand.demandType))}</span>
                            <span class="dm-badge dm-badge--status-${slug(demand.status)}">${escapeHtml(demand.status)}</span>
                            ${demand.urgency ? `<span class="dm-badge dm-badge--urgency-${slug(demand.urgency)}">Urgência ${escapeHtml(demand.urgency)}</span>` : ''}
                            ${demand.difficulty ? `<span class="dm-badge dm-badge--difficulty-${slug(demand.difficulty)}">${escapeHtml(demand.difficulty)}</span>` : ''}
                            ${late ? '<span class="dm-badge dm-badge--late">Atrasada</span>' : ''}
                        </div>
                        <h2 class="dm-card__title">${escapeHtml(demand.title)}</h2>
                        <div class="dm-card__requester">${demand.sourceRequestId
                            ? `Solicitante: <strong>${escapeHtml(display(demand.requesterName))}</strong> · #${escapeHtml(demand.sourceRequestId)}`
                            : `Criada por: <strong>${escapeHtml(display(demand.createdByName || demand.requesterName))}</strong>`}</div>
                        <p class="dm-card__description">${escapeHtml(display(demand.initialDescription))}</p>
                    </div>
                    <div class="dt-card__progress" title="Progresso das tarefas"><strong>${tasks}</strong><span>tarefas</span></div>
                </div>
                <div class="dm-card__fields">
                    ${readonlyCard('Prazo', formatDate(demand.deadline, false), 'half')}
                    ${readonlyCard('Data de início', formatDate(demand.startDate, false), 'half')}
                    ${readonlyCard('Tempo estimado (h)', formatNumber(demand.estimatedHours))}
                    ${readonlyCard('Tempo realizado (h)', formatNumber(demand.completedHours))}
                    ${readonlyCard('Tempo diário (h)', formatNumber(demand.dailyHours))}
                    ${readonlyCard('Observações', display(demand.observations), 'wide')}
                </div>
            </article>`;
    }

    function chartEmpty(elementId, message) {
        const element = document.getElementById(elementId);
        if (window.Plotly) window.Plotly.purge(element);
        element.innerHTML = `<div class="dt-chart-empty">${escapeHtml(message)}</div>`;
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
            margin: { l: 45, r: 20, t: 15, b: 45 },
            showlegend: true
        }, layout || {}), {
            displayModeBar: false,
            responsive: true
        });
    }

    function renderStatusChart(demands) {
        const statuses = state.options.status || [];
        const values = statuses.map(function (status) {
            return demands.filter(function (item) { return item.status === status; }).length;
        });
        if (!values.some(Boolean)) {
            chartEmpty('dt-status-chart', 'Nenhuma demanda para os filtros selecionados.');
            return;
        }
        plot('dt-status-chart', [{
            type: 'pie',
            labels: statuses,
            values: values,
            hole: .58,
            textinfo: 'label+value',
            hovertemplate: '%{label}: %{value}<extra></extra>',
            marker: { colors: ['#8a96a3', '#163a8a', '#ffa300', '#18794e', '#b42318'] }
        }], {
            margin: { l: 15, r: 15, t: 10, b: 10 },
            legend: { orientation: 'h', x: 0, y: -0.08 }
        });
    }

    function renderResponsibleChart(demands) {
        const active = demands.filter(function (item) {
            return ['A Fazer', 'Em Andamento', 'Pausado'].includes(item.status);
        });
        const totals = new Map();
        active.forEach(function (item) {
            const name = item.responsibleName || 'Sem responsável ativo';
            totals.set(name, (totals.get(name) || 0) + 1);
        });
        const rows = Array.from(totals.entries()).sort(function (left, right) {
            return left[1] - right[1];
        });
        if (!rows.length) {
            chartEmpty('dt-responsible-chart', 'Nenhuma demanda ativa para os filtros selecionados.');
            return;
        }
        plot('dt-responsible-chart', [{
            type: 'bar',
            orientation: 'h',
            x: rows.map(function (item) { return item[1]; }),
            y: rows.map(function (item) { return item[0]; }),
            text: rows.map(function (item) { return item[1]; }),
            textposition: 'auto',
            marker: { color: '#163a8a' },
            hovertemplate: '%{y}: %{x}<extra></extra>'
        }], {
            showlegend: false,
            margin: { l: 125, r: 20, t: 15, b: 35 },
            xaxis: { title: 'Demandas ativas', rangemode: 'tozero', dtick: 1 }
        });
    }

    function monthRows() {
        const start = parseDate(elements.periodStart.value);
        const end = parseDate(elements.periodEnd.value);
        if (!start || !end || start > end) return [];
        const rows = [];
        const cursor = new Date(start.getFullYear(), start.getMonth(), 1);
        const limit = new Date(end.getFullYear(), end.getMonth(), 1);
        while (cursor <= limit && rows.length < 120) {
            rows.push({
                key: `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}`,
                label: cursor.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' }),
                onTime: 0,
                late: 0,
                noDeadline: 0
            });
            cursor.setMonth(cursor.getMonth() + 1);
        }
        return rows;
    }

    function renderDeliveryChart(demands) {
        const rows = monthRows();
        if (!rows.length) {
            chartEmpty('dt-delivery-chart', 'Informe um período válido.');
            return;
        }
        const byMonth = new Map(rows.map(function (row) { return [row.key, row]; }));
        completedInPeriod(demands).forEach(function (demand) {
            const completed = parseDate(demand.requestFinalDate);
            if (!completed) return;
            const key = `${completed.getFullYear()}-${String(completed.getMonth() + 1).padStart(2, '0')}`;
            const row = byMonth.get(key);
            if (!row) return;
            if (!demand.deadline) row.noDeadline += 1;
            else if (isCompletedOnTime(demand)) row.onTime += 1;
            else row.late += 1;
        });
        plot('dt-delivery-chart', [
            {
                type: 'bar', name: 'No prazo',
                x: rows.map(function (row) { return row.label; }),
                y: rows.map(function (row) { return row.onTime; }),
                marker: { color: '#18794e' },
                hovertemplate: '%{x}: %{y} no prazo<extra></extra>'
            },
            {
                type: 'bar', name: 'Com atraso',
                x: rows.map(function (row) { return row.label; }),
                y: rows.map(function (row) { return row.late; }),
                marker: { color: '#b42318' },
                hovertemplate: '%{x}: %{y} com atraso<extra></extra>'
            },
            {
                type: 'bar', name: 'Sem prazo registrado',
                x: rows.map(function (row) { return row.label; }),
                y: rows.map(function (row) { return row.noDeadline; }),
                marker: { color: '#8a96a3' },
                hovertemplate: '%{x}: %{y} sem prazo<extra></extra>'
            }
        ], {
            barmode: 'stack',
            legend: { orientation: 'h', x: 0, y: 1.15 },
            yaxis: { title: 'Demandas concluídas', rangemode: 'tozero', dtick: 1 }
        });
    }

    function renderDurationChart(demands) {
        const urgencies = ['Alta', 'Média', 'Baixa'];
        const completed = completedInPeriod(demands);
        let durationCount = 0;
        const values = urgencies.map(function (urgency) {
            const durations = completed.filter(function (item) {
                return item.urgency === urgency;
            }).map(function (item) {
                return businessDaysBetween(item.requestDate, item.requestFinalDate);
            }).filter(function (value) { return value != null; });
            durationCount += durations.length;
            if (!durations.length) return 0;
            return durations.reduce(function (sum, value) { return sum + value; }, 0) / durations.length;
        });
        if (!durationCount) {
            chartEmpty('dt-duration-chart', 'Nenhuma conclusão com duração calculável no período.');
            return;
        }
        plot('dt-duration-chart', [{
            type: 'bar',
            x: urgencies,
            y: values,
            text: values.map(function (value) { return value ? formatNumber(value, 1) : '—'; }),
            textposition: 'auto',
            marker: { color: ['#b42318', '#d48a00', '#18794e'] },
            hovertemplate: '%{x}: %{y:.1f} dias úteis<extra></extra>'
        }], {
            showlegend: false,
            yaxis: { title: 'Dias úteis', rangemode: 'tozero' }
        });
    }

    function renderAnalytics() {
        const demands = baseFilteredDemands();
        renderSummary();
        renderStatusChart(demands);
        renderResponsibleChart(demands);
        renderDeliveryChart(demands);
        renderDurationChart(demands);
    }

    function readonlyItem(label, value, wide) {
        return `<div class="dm-readonly${wide ? ' dm-readonly--wide' : ''}"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(display(value))}</dd></div>`;
    }

    function requestAttachmentUrl(demand, attachment) {
        return apiUrl(`/${demand.managementId}/request-attachments/${attachment.index}`);
    }

    function internalAttachmentUrl(demand, attachment) {
        return apiUrl(`/${demand.managementId}/attachments/${attachment.id}`);
    }

    function renderAttachmentList(demand, attachments, internal) {
        if (!attachments || !attachments.length) {
            return '<p class="dm-source-empty">Nenhum arquivo anexado.</p>';
        }
        return `
            <ul class="dm-attachment-list">
                ${attachments.map(function (attachment) {
                    const url = internal
                        ? internalAttachmentUrl(demand, attachment)
                        : requestAttachmentUrl(demand, attachment);
                    return `<li><a href="${escapeHtml(url)}"><span>${escapeHtml(attachment.name)}</span><strong>Baixar</strong></a></li>`;
                }).join('')}
            </ul>`;
    }

    function renderTasks(tasks) {
        if (!tasks || !tasks.length) {
            return '<div class="dm-empty">Nenhuma tarefa cadastrada.</div>';
        }
        return `<div class="dt-task-list">${tasks.map(function (task) {
            const completed = Boolean(task.completedAt);
            const taskDeadline = parseDate(task.deadline);
            const today = parseDate(localIsoDate(new Date()));
            const late = Boolean(!completed && taskDeadline && today && taskDeadline < today);
            const status = completed ? 'Concluída' : (late ? 'Atrasada' : 'Em andamento');
            return `
                <article class="dt-task${completed ? ' dt-task--completed' : ''}">
                    <div class="dt-task__heading"><strong>${escapeHtml(task.description)}</strong><span>${escapeHtml(status)}</span></div>
                    <div class="dt-task__meta">
                        <span>Responsável: <strong>${escapeHtml(display(task.responsibleName))}</strong></span>
                        <span>Prazo: <strong>${escapeHtml(formatDate(task.deadline, false))}</strong></span>
                        ${completed ? `<span>Concluída em: <strong>${escapeHtml(formatDate(task.completedAt, true))}</strong></span>` : ''}
                    </div>
                    ${task.observations ? `<p class="dt-task__observations">${escapeHtml(task.observations)}</p>` : ''}
                </article>`;
        }).join('')}</div>`;
    }

    function renderHistory(history) {
        const labels = {
            status_start: 'Demanda iniciada',
            status_pause: 'Demanda pausada',
            status_resume: 'Demanda despausada',
            status_complete: 'Demanda concluída',
            status_cancel: 'Demanda cancelada',
            status_reopen: 'Demanda retomada',
            deadline_changed: 'Prazo alterado'
        };
        if (!history || !history.length) {
            return '<p class="dm-history__empty">Nenhum evento foi registrado neste histórico.</p>';
        }
        return `<ol class="dm-history__list">${history.map(function (item) {
            const statusChanged = item.previousStatus && item.newStatus && item.previousStatus !== item.newStatus;
            const deadlineChanged = item.previousDeadline !== item.newDeadline && (item.previousDeadline || item.newDeadline);
            return `
                <li class="dm-history__item">
                    <div class="dm-history__heading"><strong>${escapeHtml(labels[item.eventType] || 'Atualização da demanda')}</strong><time>${escapeHtml(formatDate(item.createdAt, true))}</time></div>
                    <p class="dm-history__actor">Por ${escapeHtml(display(item.actorName, 'Usuário não identificado'))}</p>
                    ${statusChanged ? `<p>Status: <strong>${escapeHtml(item.previousStatus)}</strong> → <strong>${escapeHtml(item.newStatus)}</strong></p>` : ''}
                    ${deadlineChanged ? `<p>Prazo: <strong>${escapeHtml(formatDate(item.previousDeadline, false))}</strong> → <strong>${escapeHtml(formatDate(item.newDeadline, false))}</strong></p>` : ''}
                    ${item.expectedReturn ? `<p>Previsão de retorno: <strong>${escapeHtml(formatDate(item.expectedReturn, false))}</strong></p>` : ''}
                    ${item.reason ? `<div class="dm-history__reason"><span>Justificativa</span><p>${escapeHtml(item.reason)}</p></div>` : ''}
                </li>`;
        }).join('')}</ol>`;
    }

    function renderModal(demand) {
        elements.modalContent.innerHTML = `
            <header class="dm-modal__header">
                <div class="dm-badges">
                    <span class="dm-badge dm-badge--type dm-badge--type-${slug(demand.demandType)}">${escapeHtml(typeLabel(demand.demandType))}</span>
                    <span class="dm-badge dm-badge--status-${slug(demand.status)}">${escapeHtml(demand.status)}</span>
                    ${demand.urgency ? `<span class="dm-badge dm-badge--urgency-${slug(demand.urgency)}">Urgência ${escapeHtml(demand.urgency)}</span>` : ''}
                    ${demand.difficulty ? `<span class="dm-badge dm-badge--difficulty-${slug(demand.difficulty)}">${escapeHtml(demand.difficulty)}</span>` : ''}
                    ${isLate(demand) ? '<span class="dm-badge dm-badge--late">Atrasada</span>' : ''}
                </div>
                <h2 id="dt-modal-title">${escapeHtml(demand.title)}</h2>
                <p class="dm-modal__meta">Visualização completa · somente leitura</p>
            </header>
            <div class="dm-modal__columns">
                <section class="dm-panel">
                    <h3>Gerenciamento</h3>
                    <dl class="dm-readonly-grid">
                        ${readonlyItem('Responsável', demand.responsibleName)}
                        ${readonlyItem('Status', demand.status)}
                        ${readonlyItem('Dificuldade', demand.difficulty)}
                        ${readonlyItem('Data de início', formatDate(demand.startDate, false))}
                        ${readonlyItem('Prazo', formatDate(demand.deadline, false))}
                        ${readonlyItem('Início agendado', formatDate(demand.scheduledStartAt, false))}
                        ${readonlyItem('Tempo total estimado (h)', formatNumber(demand.estimatedHours))}
                        ${readonlyItem('Tempo diário (h)', formatNumber(demand.dailyHours))}
                        ${readonlyItem('Tempo total realizado (h)', formatNumber(demand.completedHours))}
                        ${readonlyItem('Observações', demand.observations, true)}
                    </dl>
                </section>
                <section class="dm-panel">
                    <h3>${demand.sourceRequestId ? 'Solicitação original' : 'Dados da demanda'}</h3>
                    <dl class="dm-readonly-grid">
                        ${readonlyItem('Título', demand.title, true)}
                        ${readonlyItem(demand.demandType === 'erro' ? 'Descrição completa do erro' : 'Descrição inicial / objetivo', demand.initialDescription, true)}
                        ${demand.demandType !== 'erro' ? readonlyItem('Premissas', demand.assumptions, true) : ''}
                        ${demand.demandType !== 'erro' ? readonlyItem('Problemas atuais', demand.actualProblems, true) : ''}
                        ${demand.demandType !== 'erro' ? readonlyItem('Ganhos esperados', demand.benefits, true) : ''}
                        ${readonlyItem(demand.sourceRequestId ? 'Solicitante' : 'Criada por', demand.requesterName)}
                        ${demand.sourceRequestId ? readonlyItem('ID da solicitação', `#${demand.sourceRequestId}`) : ''}
                        ${readonlyItem('Tipo', typeLabel(demand.demandType))}
                        ${readonlyItem('Urgência', demand.urgency)}
                        ${readonlyItem('Data da solicitação', formatDate(demand.requestDate, true))}
                        ${readonlyItem('Início original', formatDate(demand.requestStartDate, false))}
                        ${readonlyItem('Prazo original', formatDate(demand.requestDeadline, false))}
                        ${readonlyItem('Conclusão', formatDate(demand.requestFinalDate, true))}
                        ${readonlyItem('Reprogramações', String(demand.requestReprograms || 0))}
                    </dl>
                    ${demand.sourceRequestId ? `<div class="dm-source-section">
                        <h4>Documentos da solicitação</h4>
                        ${renderAttachmentList(demand, demand.attachments, false)}
                    </div>` : ''}
                </section>
            </div>
            <section class="dm-panel dm-internal-attachments">
                <h3>Anexos internos</h3>
                ${renderAttachmentList(demand, demand.internalAttachments, true)}
            </section>
            <section class="dm-panel dm-tasks">
                <h3>Tarefas · ${demand.completedTasks || 0}/${demand.totalTasks || 0} concluídas</h3>
                ${renderTasks(demand.tasks)}
            </section>
            <section class="dm-panel dm-history">
                <h3>Histórico da demanda</h3>
                ${renderHistory(demand.history)}
            </section>`;
    }

    async function openModal(managementId) {
        elements.modal.classList.add('is-open');
        elements.modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('dm-modal-open');
        elements.modalContent.innerHTML = '<div class="dm-feedback"><span class="dm-spinner"></span>Carregando detalhes...</div>';
        try {
            renderModal(await api(`/${managementId}`));
        } catch (error) {
            elements.modalContent.innerHTML = `<div class="dm-empty">${escapeHtml(error.message)}</div>`;
        }
    }

    function closeModal() {
        elements.modal.classList.remove('is-open');
        elements.modal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('dm-modal-open');
    }

    function renderAll() {
        renderBoard();
        renderAnalytics();
    }

    async function load() {
        try {
            const payload = await api('');
            state.demands = (payload.demands || []).filter(function (demand) {
                return ['melhoria', 'projeto', 'erro'].includes(demand.demandType);
            });
            state.responsibles = payload.responsibles || [];
            state.options = payload.options || state.options;
            configureFilters();
            renderAll();
        } catch (error) {
            elements.board.innerHTML = `<div class="dm-empty">${escapeHtml(error.message)}</div>`;
        } finally {
            elements.loading.style.display = 'none';
        }
    }

    [elements.responsible, elements.type, elements.status, elements.difficulty, elements.urgency].forEach(function (element) {
        element.addEventListener('change', renderAll);
    });
    elements.search.addEventListener('input', renderAll);
    elements.periodStart.addEventListener('change', renderAnalytics);
    elements.periodEnd.addEventListener('change', renderAnalytics);
    elements.clearFilters.addEventListener('click', function () {
        elements.search.value = '';
        elements.responsible.value = '';
        elements.type.value = '';
        elements.status.value = '__active__';
        elements.difficulty.value = '';
        elements.urgency.value = '';
        renderAll();
    });
    elements.board.addEventListener('click', function (event) {
        const ownerToggle = event.target.closest('[data-owner-toggle]');
        if (ownerToggle) {
            const key = ownerToggle.dataset.ownerToggle;
            if (state.collapsedOwners.has(key)) state.collapsedOwners.delete(key);
            else state.collapsedOwners.add(key);
            renderBoard();
            return;
        }
        const card = event.target.closest('[data-management-id]');
        if (card) openModal(card.dataset.managementId);
    });
    elements.board.addEventListener('keydown', function (event) {
        if (!['Enter', ' '].includes(event.key)) return;
        const card = event.target.closest('[data-management-id]');
        if (!card) return;
        event.preventDefault();
        openModal(card.dataset.managementId);
    });
    elements.modal.addEventListener('click', function (event) {
        if (event.target.closest('[data-close-tracking-modal]')) closeModal();
    });
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && elements.modal.classList.contains('is-open')) {
            closeModal();
        }
    });

    initializePeriod();
    load();
}());
