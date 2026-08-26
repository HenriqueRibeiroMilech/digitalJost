(function () {
    'use strict';

    const config = window.demandManagementConfig;
    const state = {
        demands: [],
        responsibles: [],
        options: { status: [], difficulty: [], type: [] },
        detail: null,
        requests: [],
        requestDetail: null,
        view: config.initialView === 'requests' ? 'requests' : 'demands',
        collapsedOwners: new Set(),
        updateQueues: new Map(),
        deadlineChanges: new Map(),
        filtersInitialized: false,
        statusAction: null
    };

    const elements = {
        board: document.getElementById('dm-board'),
        demandsView: document.getElementById('dm-demands-view'),
        requestsView: document.getElementById('dm-requests-view'),
        tabs: Array.from(document.querySelectorAll('[data-view]')),
        subtitle: document.getElementById('dm-subtitle'),
        loading: document.getElementById('dm-loading'),
        summary: document.getElementById('dm-summary'),
        search: document.getElementById('dm-search'),
        responsible: document.getElementById('dm-filter-responsible'),
        type: document.getElementById('dm-filter-type'),
        status: document.getElementById('dm-filter-status'),
        difficulty: document.getElementById('dm-filter-difficulty'),
        clearFilters: document.getElementById('dm-clear-filters'),
        createDemand: document.getElementById('dm-create-demand'),
        requestList: document.getElementById('dm-request-list'),
        requestLoading: document.getElementById('dm-request-loading'),
        requestSearch: document.getElementById('dm-request-search'),
        requestType: document.getElementById('dm-request-type'),
        requestStatus: document.getElementById('dm-request-status'),
        requestUrgency: document.getElementById('dm-request-urgency'),
        clearRequestFilters: document.getElementById('dm-clear-request-filters'),
        pendingCount: document.getElementById('dm-pending-count'),
        modal: document.getElementById('dm-modal'),
        modalContent: document.getElementById('dm-modal-content'),
        toast: document.getElementById('dm-toast')
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
        return normalize(value).replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    }

    function valueOrEmpty(value) {
        return value == null ? '' : value;
    }

    function display(value, fallback) {
        return value == null || value === '' ? (fallback || 'Não informado') : value;
    }

    function formatDate(value, withTime) {
        if (!value) return 'Não informado';
        const raw = String(value);
        const parts = raw.substring(0, 10).split('-');
        if (parts.length !== 3) return raw;
        const date = `${parts[2]}/${parts[1]}/${parts[0]}`;
        return withTime && raw.length >= 16 ? `${date} ${raw.substring(11, 16)}` : date;
    }

    function typeLabel(type) {
        return {
            atividade: 'Atividade',
            melhoria: 'Melhoria',
            projeto: 'Projeto',
            erro: 'Erro'
        }[type] || display(type);
    }

    function typeBadgeClass(type) {
        return `dm-badge--type dm-badge--type-${slug(type)}`;
    }

    function requestStatusLabel(status) {
        return Number(status) === 3 ? 'Recusada' : 'Em análise';
    }

    const statusActions = {
        'A Fazer': [
            { action: 'start', label: 'Iniciar' },
            { action: 'cancel', label: 'Cancelar' }
        ],
        'Em Andamento': [
            { action: 'pause', label: 'Pausar' },
            { action: 'complete', label: 'Concluir' },
            { action: 'cancel', label: 'Cancelar' }
        ],
        'Pausado': [
            { action: 'resume', label: 'Despausar' },
            { action: 'cancel', label: 'Cancelar' }
        ],
        'Concluído': [
            { action: 'reopen', label: 'Retomar' }
        ],
        'Cancelado': []
    };

    function requestAttachmentUrl(requestId, attachmentIndex) {
        const url = new URL(
            `${config.apiRoot}/requests/${requestId}/attachments/${attachmentIndex}`,
            window.location.origin
        );
        url.searchParams.set('area', config.area);
        return url.toString();
    }

    function renderAttachments(requestId, attachments) {
        if (!attachments || !attachments.length) {
            return '<p class="dm-source-empty">Nenhum documento anexado.</p>';
        }
        return `
            <ul class="dm-attachment-list">
                ${attachments.map(function (attachment) {
                    const url = requestAttachmentUrl(requestId, attachment.index);
                    return `
                        <li>
                            <a href="${escapeHtml(url)}">
                                <span>${escapeHtml(attachment.name)}</span>
                                <strong>Baixar</strong>
                            </a>
                        </li>`;
                }).join('')}
            </ul>`;
    }

    function renderRequestPauses(pauses) {
        if (!pauses || !pauses.length) return '';
        return `
            <div class="dm-source-section">
                <h4>Histórico de pausas</h4>
                <ul class="dm-pause-list">
                    ${pauses.map(function (pause) {
                        return `
                            <li>
                                <strong>${escapeHtml(formatDate(pause.initDate, true))}</strong>
                                até ${escapeHtml(formatDate(pause.finalDate || pause.expectDate, Boolean(pause.finalDate)))}
                                <span>${escapeHtml(display(pause.reason, 'Sem justificativa informada'))}</span>
                            </li>`;
                    }).join('')}
                </ul>
            </div>`;
    }

    function daysUntilDeadline(demand) {
        if (!demand.deadline || ['Concluído', 'Cancelado'].includes(demand.status)) return null;
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const deadline = new Date(`${demand.deadline.substring(0, 10)}T00:00:00`);
        if (Number.isNaN(deadline.getTime())) return null;
        return Math.round((deadline.getTime() - today.getTime()) / 86400000);
    }

    function isLate(demand) {
        const days = daysUntilDeadline(demand);
        return days !== null && days < 0;
    }

    function deadlineBadge(demand) {
        const days = daysUntilDeadline(demand);
        if (days === null || days < 0 || days > 3) return '';
        const label = days === 0
            ? 'Vence hoje'
            : `Vence em ${days} dia${days === 1 ? '' : 's'}`;
        return `<span class="dm-badge dm-badge--deadline">${label}</span>`;
    }

    function optionList(items, selected, emptyLabel) {
        const empty = emptyLabel == null ? '' : `<option value="">${escapeHtml(emptyLabel)}</option>`;
        return empty + items.map(function (item) {
            const value = typeof item === 'object' ? item.id : item;
            const label = typeof item === 'object' ? item.name : item;
            const isSelected = String(valueOrEmpty(selected)) === String(value) ? ' selected' : '';
            return `<option value="${escapeHtml(value)}"${isSelected}>${escapeHtml(label)}</option>`;
        }).join('');
    }

    async function api(path, options) {
        const url = new URL(path, window.location.origin);
        url.searchParams.set('area', config.area);
        const settings = Object.assign({ method: 'GET', headers: {} }, options || {});
        settings.headers.Accept = 'application/json';
        if (settings.body) {
            settings.headers['Content-Type'] = 'application/json';
        }
        if (settings.method !== 'GET') {
            settings.headers['X-CSRF-Token'] = config.csrfToken;
        }

        const response = await fetch(url.pathname + url.search, settings);
        let data = {};
        try {
            data = await response.json();
        } catch (error) {
            data = {};
        }
        if (!response.ok) {
            const apiError = new Error(data.error || data.description || 'Não foi possível concluir a operação.');
            apiError.status = response.status;
            throw apiError;
        }
        return data;
    }

    function toast(message, isError) {
        elements.toast.textContent = message;
        elements.toast.classList.toggle('is-error', Boolean(isError));
        elements.toast.classList.add('is-visible');
        window.clearTimeout(toast.timeout);
        toast.timeout = window.setTimeout(function () {
            elements.toast.classList.remove('is-visible');
        }, 3200);
    }

    async function loadBoard(showLoading) {
        if (showLoading !== false) {
            elements.loading.style.display = 'flex';
            elements.board.innerHTML = '';
        }
        try {
            const data = await api(config.apiRoot);
            state.demands = data.demands || [];
            state.responsibles = data.responsibles || [];
            state.options = data.options || state.options;
            configureFilters();
            renderAll();
            elements.createDemand.disabled = false;
        } catch (error) {
            elements.board.innerHTML = `<div class="dm-empty">${escapeHtml(error.message)}</div>`;
        } finally {
            elements.loading.style.display = 'none';
        }
    }

    async function loadRequests(showLoading) {
        if (showLoading !== false) {
            elements.requestLoading.style.display = 'flex';
            elements.requestList.innerHTML = '';
        }
        try {
            const data = await api(`${config.apiRoot}/requests`);
            state.requests = data.requests || [];
            configureRequestFilters();
            renderRequests();
            renderNavigation();
        } catch (error) {
            elements.requestList.innerHTML = `<div class="dm-empty">${escapeHtml(error.message)}</div>`;
        } finally {
            elements.requestLoading.style.display = 'none';
        }
    }

    function configureRequestFilters() {
        const selected = elements.requestType.value;
        const types = Array.from(new Set(state.requests.map(function (item) {
            return item.demandType;
        }))).filter(Boolean);
        elements.requestType.innerHTML = '<option value="">Todos</option>' + types.map(function (type) {
            return `<option value="${escapeHtml(type)}">${escapeHtml(typeLabel(type))}</option>`;
        }).join('');
        elements.requestType.value = selected;
    }

    function renderNavigation() {
        const requestsSelected = state.view === 'requests';
        elements.demandsView.hidden = requestsSelected;
        elements.requestsView.hidden = !requestsSelected;
        elements.tabs.forEach(function (tab) {
            const selected = tab.dataset.view === state.view;
            tab.classList.toggle('is-active', selected);
            tab.setAttribute('aria-current', selected ? 'page' : 'false');
        });
        elements.pendingCount.textContent = state.requests.filter(function (item) {
            return Number(item.status) === 0;
        }).length;
        elements.subtitle.textContent = requestsSelected
            ? 'Solicitações aguardando análise e histórico de recusas.'
            : 'Demandas aprovadas e atividades internas da Transformação Digital.';
        renderSummary();
    }

    function changeView(view) {
        if (!['demands', 'requests'].includes(view)) return;
        state.view = view;
        const url = new URL(window.location.href);
        url.searchParams.set('view', view);
        window.history.replaceState({}, '', url.pathname + url.search);
        renderNavigation();
    }

    function configureFilters() {
        const selectedResponsible = elements.responsible.value;
        const selectedType = elements.type.value;
        const selectedStatus = state.filtersInitialized ? elements.status.value : '__active__';
        const selectedDifficulty = elements.difficulty.value;

        elements.responsible.innerHTML = '<option value="">Todos</option>' +
            optionList(state.responsibles, selectedResponsible) +
            '<option value="__unassigned__">Histórico de antigos colaboradores</option>';
        elements.type.innerHTML = '<option value="">Todos</option>' +
            Array.from(new Set(state.demands.map(function (item) { return item.demandType; })))
                .filter(Boolean)
                .map(function (item) {
                    return `<option value="${escapeHtml(item)}">${escapeHtml(typeLabel(item))}</option>`;
                }).join('');
        elements.status.innerHTML = '<option value="">Todos</option>' + 
            '<option value="__active__">Ativas</option>' +
            optionList(state.options.status || [], selectedStatus) +
            '<option value="__late__">Atrasadas</option>';
        elements.difficulty.innerHTML = '<option value="">Todas</option>' + optionList(state.options.difficulty || [], selectedDifficulty);

        elements.responsible.value = selectedResponsible;
        elements.type.value = selectedType;
        elements.status.value = selectedStatus;
        elements.difficulty.value = selectedDifficulty;
        state.filtersInitialized = true;
    }

    function filteredDemands() {
        const search = normalize(elements.search.value);
        return state.demands.filter(function (demand) {
            const responsibleFilter = elements.responsible.value;
            const statusFilter = elements.status.value;
            const matchesResponsible = !responsibleFilter ||
                (responsibleFilter === '__unassigned__' ? !demand.responsibleId : demand.responsibleId === responsibleFilter);
            let matchesStatus = !statusFilter;
            if (statusFilter === '__active__') {
                matchesStatus = ['A Fazer', 'Em Andamento', 'Pausado'].includes(demand.status);
            } else if (statusFilter === '__late__') {
                matchesStatus = isLate(demand);
            } else if (statusFilter) {
                matchesStatus = demand.status === statusFilter;
            }
            return matchesResponsible &&
                (!elements.type.value || demand.demandType === elements.type.value) &&
                matchesStatus &&
                (!elements.difficulty.value || demand.difficulty === elements.difficulty.value) &&
                (!search || normalize(demand.title).includes(search));
        });
    }

    function renderSummary() {
        if (state.view === 'requests') {
            const pending = state.requests.filter(function (item) {
                return Number(item.status) === 0;
            }).length;
            const declined = state.requests.filter(function (item) {
                return Number(item.status) === 3;
            }).length;
            const highPriority = state.requests.filter(function (item) {
                return Number(item.status) === 0 && item.urgency === 'Alta';
            }).length;
            elements.summary.innerHTML = [
                [pending, 'Em análise'],
            ].map(function (item) {
                return `<div class="dm-summary__item"><strong>${item[0]}</strong><span>${item[1]}</span></div>`;
            }).join('');
            return;
        }
        const active = state.demands.filter(function (item) {
            return !['Concluído', 'Cancelado'].includes(item.status);
        }).length;
        const late = state.demands.filter(isLate).length;
        const completed = state.demands.filter(function (item) { return item.status === 'Concluído'; }).length;
        elements.summary.innerHTML = [
            [state.demands.length, 'Total'],
            [completed, 'Concluídas'],
            [active, 'Ativas'],
            [late, 'Atrasadas']
        ].map(function (item) {
            return `<div class="dm-summary__item"><strong>${item[0]}</strong><span>${item[1]}</span></div>`;
        }).join('');
    }

    function renderAll() {
        renderSummary();
        renderBoard();
    }

    function renderBoard() {
        const demands = filteredDemands();
        if (!demands.length) {
            elements.board.innerHTML = '<div class="dm-empty"><strong>Nenhuma demanda encontrada.</strong><br>Ajuste os filtros ou aguarde uma nova aprovação.</div>';
            return;
        }

        const groups = new Map();
        demands.forEach(function (demand) {
            const key = demand.responsibleId || '__unassigned__';
            if (!groups.has(key)) {
                groups.set(key, {
                    key: key,
                    name: demand.responsibleName || 'Histórico de antigos colaboradores',
                    demands: []
                });
            }
            groups.get(key).demands.push(demand);
        });

        elements.board.innerHTML = Array.from(groups.values()).map(renderOwner).join('');
    }

    function filteredRequests() {
        const search = normalize(elements.requestSearch.value);
        return state.requests.filter(function (item) {
            return (!search || normalize(item.title).includes(search)) &&
                (!elements.requestType.value || item.demandType === elements.requestType.value) &&
                (!elements.requestStatus.value || String(item.status) === elements.requestStatus.value) &&
                (!elements.requestUrgency.value || item.urgency === elements.requestUrgency.value);
        });
    }

    function renderRequests() {
        const requests = filteredRequests();
        if (!requests.length) {
            elements.requestList.innerHTML = '<div class="dm-empty"><strong>Nenhuma solicitação encontrada.</strong><br>Altere os filtros para consultar outro grupo.</div>';
            return;
        }
        elements.requestList.innerHTML = requests.map(renderRequestCard).join('');
    }

    function renderRequestCard(item) {
        const status = requestStatusLabel(item.status);
        const refused = Number(item.status) === 3;
        return `
            <article class="dm-review-card${refused ? ' dm-review-card--declined' : ''}" data-request-id="${item.requestId}" tabindex="0" role="button" aria-label="Abrir análise de ${escapeHtml(item.title)}">
                <div class="dm-badges">
                    <span class="dm-badge ${typeBadgeClass(item.demandType)}">${escapeHtml(typeLabel(item.demandType))}</span>
                    <span class="dm-badge dm-badge--review-${refused ? 'declined' : 'pending'}">${escapeHtml(status)}</span>
                    <span class="dm-badge dm-badge--urgency-${slug(item.urgency)}">Urgência ${escapeHtml(display(item.urgency))}</span>
                </div>
                <h2 class="dm-card__title">${escapeHtml(item.title)}</h2>
                <div class="dm-card__requester">Solicitante: <strong>${escapeHtml(item.requesterName)}</strong> · #${item.requestId}</div>
                <p class="dm-card__description">${escapeHtml(item.initialDescription)}</p>
                <div class="dm-review-card__footer">
                    <span>Solicitada em ${escapeHtml(formatDate(item.requestDate, true))}</span>
                    <button class="dm-button" type="button" data-review-request="${item.requestId}">${refused ? 'Ver detalhes' : 'Analisar demanda'}</button>
                </div>
            </article>`;
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

    function field(label, fieldName, value, type, options) {
        const safeValue = escapeHtml(valueOrEmpty(value));
        const fieldClass = `dm-field--${slug(fieldName)}`;
        let control;
        if (type === 'select') {
            control = `<select class="dm-input" data-field="${fieldName}">${optionList(options, value, 'Não informado')}</select>`;
        } else if (type === 'textarea') {
            control = `<textarea class="dm-textarea" data-field="${fieldName}" placeholder="Adicione uma observação">${safeValue}</textarea>`;
        } else {
            const step = type === 'number' ? ' step="1" min="0"' : '';
            control = `<input class="dm-input" data-field="${fieldName}" type="${type}"${step} value="${safeValue}">`;
        }
        return `<label class="dm-field ${fieldClass}${type === 'textarea' ? ' dm-field--wide' : ''}"><span>${label}</span>${control}</label>`;
    }

    function readonlyField(label, fieldName, value, type) {
        return `
            <label class="dm-field dm-field--${slug(fieldName)}">
                <span>${label}</span>
                <input class="dm-input" type="${type}" value="${escapeHtml(valueOrEmpty(value))}" readonly aria-readonly="true" title="Definida automaticamente ao iniciar a demanda">
            </label>`;
    }

    function renderDeadlineChangeForm(demand) {
        const change = state.deadlineChanges.get(demand.managementId);
        if (!change) return '';
        return `
            <form class="dm-status-form dm-deadline-form" data-deadline-change-form="${demand.managementId}">
                <div class="dm-status-form__heading">
                    <strong>Alterar prazo</strong>
                    <span>Informe a justificativa que será enviada ao solicitante.</span>
                </div>
                <label class="dm-field">
                    <span>Novo prazo de entrega</span>
                    <input class="dm-input" type="date" value="${escapeHtml(change.value || '')}" readonly aria-readonly="true">
                </label>
                <label class="dm-field dm-field--wide">
                    <span>Justificativa</span>
                    <textarea class="dm-textarea" name="reason" maxlength="4000" required placeholder="Descreva o motivo da alteração do prazo"></textarea>
                </label>
                <div class="dm-status-form__actions">
                    <button class="dm-button dm-button--quiet" type="button" data-cancel-deadline-change="${demand.managementId}">Cancelar</button>
                    <button class="dm-button" type="submit">Confirmar alteração</button>
                </div>
            </form>`;
    }

    function renderStatusActions(demand) {
        const actions = statusActions[demand.status] || [];
        if (!actions.length) {
            return '<p class="dm-status-actions__empty">Esta demanda está encerrada.</p>';
        }
        return `
            <div class="dm-status-actions">
                ${actions.map(function (item) {
                    return `<button class="dm-button dm-status-action dm-status-action--${item.action}" type="button" data-status-action="${item.action}">${item.label}</button>`;
                }).join('')}
            </div>`;
    }

    function renderStatusActionForm(demand) {
        const action = state.statusAction;
        if (!action) return '';

        const content = {
            start: ['Iniciar demanda', 'Defina o prazo que será informado ao solicitante.'],
            pause: ['Pausar demanda', 'Explique a interrupção e informe a previsão de retorno.'],
            resume: ['Despausar demanda', 'A demanda será retomada mantendo o prazo atual.'],
            complete: ['Concluir demanda', 'Confirme que o desenvolvimento foi finalizado.'],
            cancel: ['Cancelar demanda', 'Informe ao solicitante por que a demanda será cancelada.'],
            reopen: ['Retomar demanda', 'Defina o novo prazo e justifique a alteração.']
        }[action];
        if (!content) return '';

        const asksDeadline = ['start', 'reopen'].includes(action);
        const asksReason = ['pause', 'cancel', 'reopen'].includes(action);
        const submitLabel = {
            start: 'Confirmar início',
            pause: 'Confirmar pausa',
            resume: 'Confirmar retomada',
            complete: 'Confirmar conclusão',
            cancel: 'Confirmar cancelamento',
            reopen: 'Confirmar retomada'
        }[action];

        return `
            <form class="dm-status-form" id="dm-status-transition" data-action="${action}">
                <div class="dm-status-form__heading">
                    <strong>${content[0]}</strong>
                    <span>${content[1]}</span>
                </div>
                ${asksDeadline ? `
                    <label class="dm-field">
                        <span>Prazo de entrega</span>
                        <input class="dm-input" name="deadline" type="date" value="${escapeHtml(demand.deadline ? demand.deadline.substring(0, 10) : '')}" required>
                    </label>` : ''}
                ${asksReason ? `
                    <label class="dm-field dm-field--wide">
                        <span>Justificativa</span>
                        <textarea class="dm-textarea" name="reason" maxlength="4000" required placeholder="Descreva o motivo desta alteração"></textarea>
                    </label>` : ''}
                ${action === 'pause' ? `
                    <label class="dm-field">
                        <span>Previsão de retorno</span>
                        <input class="dm-input" name="expectedReturn" type="date" required>
                    </label>` : ''}
                <div class="dm-status-form__actions">
                    <button class="dm-button dm-button--quiet" type="button" data-cancel-status-action>Voltar</button>
                    <button class="dm-button dm-status-action dm-status-action--${action}" type="submit">${submitLabel}</button>
                </div>
            </form>`;
    }

    function renderCard(demand) {
        const late = isLate(demand);
        const statusClass = `dm-card--status-${slug(demand.status)}`;
        const taskProgress = `${demand.completedTasks || 0}/${demand.totalTasks || 0}`;
        const badges = [
            `<span class="dm-badge ${typeBadgeClass(demand.demandType)}">${escapeHtml(typeLabel(demand.demandType))}</span>`,
            `<span class="dm-badge dm-badge--status-${slug(demand.status)}">${escapeHtml(demand.status)}</span>`,
            demand.difficulty ? `<span class="dm-badge dm-badge--difficulty-${slug(demand.difficulty)}">${escapeHtml(demand.difficulty)}</span>` : '',
            deadlineBadge(demand),
            late ? '<span class="dm-badge dm-badge--late">Atrasada</span>' : ''
        ].join('');

        return `
            <article class="dm-card ${statusClass}${late ? ' dm-card--late' : ''}" data-management-id="${demand.managementId}" tabindex="0" role="button" aria-label="Abrir detalhes de ${escapeHtml(demand.title)}">
                <div class="dm-card__top">
                    <div class="dm-card__identity">
                        <div class="dm-badges">${badges}</div>
                        <h2 class="dm-card__title">${escapeHtml(demand.title)}</h2>
                        <div class="dm-card__requester">${demand.isDirectDemand
                            ? `Criada por: <strong>${escapeHtml(demand.createdByName || demand.requesterName)}</strong>`
                            : `Solicitante: <strong>${escapeHtml(demand.requesterName)}</strong> · #${demand.sourceRequestId}`}</div>
                        <p class="dm-card__description">${escapeHtml(demand.initialDescription)}</p>
                    </div>
                    <div class="dm-card__progress" title="Progresso das tarefas">
                        <strong>${taskProgress}</strong><span>tarefas</span>
                    </div>
                </div>
                <div class="dm-card__fields">
                    ${field('Prazo', 'deadline', demand.deadline && demand.deadline.substring(0, 10), 'date')}
                    ${readonlyField('Data de início', 'startDate', demand.startDate && demand.startDate.substring(0, 10), 'date')}
                    ${renderDeadlineChangeForm(demand)}
                    ${field('Tempo estimado (h)', 'estimatedHours', demand.estimatedHours, 'number')}
                    ${field('Tempo realizado (h)', 'completedHours', demand.completedHours, 'number')}
                    ${field('Tempo diário (h)', 'dailyHours', demand.dailyHours, 'number')}
                    ${field('Observações', 'observations', demand.observations, 'textarea')}
                </div>
            </article>`;
    }

    function updateDemand(managementId, fieldName, value, input, options) {
        const settings = options || {};
        input.disabled = true;
        const previous = state.updateQueues.get(managementId) || Promise.resolve();
        const operation = previous.catch(function () {}).then(async function () {
            const demand = state.demands.find(function (item) { return item.managementId === managementId; });
            if (!demand) return;
            const payload = {
                field: fieldName,
                value: value,
                rowVersion: demand.rowVersion
            };
            if (settings.reason) payload.reason = settings.reason;
            const updated = await api(`${config.apiRoot}/${managementId}`, {
                method: 'PATCH',
                body: JSON.stringify(payload)
            });
            replaceDemand(updated);
            if (fieldName === 'deadline') {
                state.deadlineChanges.delete(managementId);
            }
            if (state.detail && state.detail.managementId === managementId) {
                state.detail = updated;
                renderModal(updated);
            }
            renderAll();
            toast('Alteração salva.');
        });

        state.updateQueues.set(managementId, operation);
        operation.catch(async function (error) {
            toast(error.message, true);
            if (error.status === 409) await loadBoard(false);
        }).finally(function () {
            input.disabled = false;
            if (state.updateQueues.get(managementId) === operation) {
                state.updateQueues.delete(managementId);
            }
        });
        return operation;
    }

    function changeDemandField(managementId, input) {
        const fieldName = input.dataset.field;
        const value = input.value || null;
        if (fieldName !== 'deadline') {
            updateDemand(managementId, fieldName, value, input);
            return;
        }

        const demand = state.demands.find(function (item) {
            return item.managementId === managementId;
        });
        if (!demand) return;
        const previousValue = demand.deadline ? demand.deadline.substring(0, 10) : '';
        if (previousValue === (value || '')) return;
        state.deadlineChanges.set(managementId, { value: value });
        renderAll();
        if (state.detail && state.detail.managementId === managementId) {
            renderModal(state.detail);
        }
    }

    function cancelDeadlineChange(managementId) {
        state.deadlineChanges.delete(managementId);
        renderAll();
        if (state.detail && state.detail.managementId === managementId) {
            renderModal(state.detail);
        }
    }

    function submitDeadlineChange(form) {
        const managementId = Number(form.dataset.deadlineChangeForm);
        const change = state.deadlineChanges.get(managementId);
        if (!change) return;
        updateDemand(managementId, 'deadline', change.value, form.elements.reason, {
            reason: form.elements.reason.value.trim()
        });
    }

    function replaceDemand(updated) {
        const index = state.demands.findIndex(function (item) {
            return item.managementId === updated.managementId;
        });
        if (index >= 0) state.demands[index] = updated;
    }

    async function openModal(managementId) {
        state.statusAction = null;
        elements.modal.classList.add('is-open');
        elements.modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('dm-modal-open');
        elements.modalContent.innerHTML = '<div class="dm-feedback"><span class="dm-spinner"></span>Carregando detalhes...</div>';
        try {
            state.detail = await api(`${config.apiRoot}/${managementId}`);
            renderModal(state.detail);
        } catch (error) {
            elements.modalContent.innerHTML = `<div class="dm-empty">${escapeHtml(error.message)}</div>`;
        }
    }

    async function openRequestModal(requestId) {
        elements.modal.classList.add('is-open');
        elements.modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('dm-modal-open');
        elements.modalContent.innerHTML = '<div class="dm-feedback"><span class="dm-spinner"></span>Carregando solicitação...</div>';
        try {
            state.requestDetail = await api(`${config.apiRoot}/requests/${requestId}`);
            renderRequestModal(state.requestDetail);
        } catch (error) {
            elements.modalContent.innerHTML = `<div class="dm-empty">${escapeHtml(error.message)}</div>`;
        }
    }

    function openCreateDemandModal() {
        state.detail = null;
        state.requestDetail = null;
        state.statusAction = null;
        elements.modal.classList.add('is-open');
        elements.modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('dm-modal-open');
        renderCreateDemandModal();
    }

    function renderCreateDemandModal() {
        const difficulties = state.options.difficulty || [];
        elements.modalContent.innerHTML = `
            <header class="dm-modal__header">
                <div class="dm-badges">
                    <span class="dm-badge dm-badge--type dm-badge--type-atividade">Nova atividade pessoal</span>
                </div>
                <h2 id="dm-modal-title">Criar atividade</h2>
                <p class="dm-modal__meta">Ela será atribuída automaticamente a ${escapeHtml(config.currentUserName)}.</p>
            </header>

            <form class="dm-create-form" id="dm-create-demand-form">
                <section class="dm-panel">
                    <h3>Dados principais</h3>
                    <div class="dm-create-grid">
                        <label class="dm-field dm-create-grid__title">
                            <span>Título</span>
                            <input class="dm-input" name="title" type="text" required maxlength="250" placeholder="Ex.: Atualizar indicador semanal">
                        </label>
                        <label class="dm-field dm-create-grid__description">
                            <span>Descrição da atividade</span>
                            <textarea class="dm-textarea" name="initialDescription" required maxlength="4000" placeholder="Descreva o que precisa ser feito"></textarea>
                        </label>
                    </div>
                </section>

                <section class="dm-panel">
                    <h3>Planejamento inicial</h3>
                    <div class="dm-form-grid dm-create-planning-grid">
                        ${createSelectField('Dificuldade', 'difficulty', difficulties, '', 'Não informada')}
                        ${createInputField('Prazo', 'deadline', 'date')}
                        ${createInputField('Tempo total estimado (h)', 'estimatedHours', 'number')}
                        ${createInputField('Tempo diário (h)', 'dailyHours', 'number')}
                        ${createInputField('Tempo realizado (h)', 'completedHours', 'number')}
                        <label class="dm-field dm-field--wide">
                            <span>Observações</span>
                            <textarea class="dm-textarea" name="observations" maxlength="4000" placeholder="Informações adicionais"></textarea>
                        </label>
                    </div>
                </section>

                <div class="dm-modal__footer">
                    <button class="dm-button dm-button--quiet" type="button" data-close-modal>Cancelar</button>
                    <button class="dm-button" type="submit">Criar atividade</button>
                </div>
            </form>`;
    }

    function createSelectField(label, name, options, selected, emptyLabel) {
        return `
            <label class="dm-field dm-field--${slug(name)}">
                <span>${escapeHtml(label)}</span>
                <select class="dm-input" name="${name}">${optionList(options, selected, emptyLabel)}</select>
            </label>`;
    }

    function createInputField(label, name, type) {
        const numberOptions = type === 'number' ? ' min="0" max="99999.99" step="0.25"' : '';
        return `
            <label class="dm-field dm-field--${slug(name)}">
                <span>${escapeHtml(label)}</span>
                <input class="dm-input" name="${name}" type="${type}"${numberOptions}>
            </label>`;
    }

    function personalDemandPayload(form) {
        function value(name) {
            return form.elements[name].value || null;
        }
        return {
            demandType: 'atividade',
            title: value('title'),
            initialDescription: value('initialDescription'),
            difficulty: value('difficulty'),
            deadline: value('deadline'),
            estimatedHours: value('estimatedHours'),
            dailyHours: value('dailyHours'),
            completedHours: value('completedHours'),
            observations: value('observations')
        };
    }

    async function createPersonalDemand(form) {
        const button = form.querySelector('button[type="submit"]');
        button.disabled = true;
        try {
            const created = await api(config.apiRoot, {
                method: 'POST',
                body: JSON.stringify(personalDemandPayload(form))
            });
            state.demands.push(created);
            if (created.responsibleId && !state.responsibles.some(function (item) {
                return String(item.id) === String(created.responsibleId);
            })) {
                state.responsibles.push({
                    id: created.responsibleId,
                    name: created.responsibleName
                });
                state.responsibles.sort(function (left, right) {
                    return left.name.localeCompare(right.name, 'pt-BR');
                });
            }
            configureFilters();
            state.detail = created;
            renderAll();
            renderModal(state.detail);
            toast('Demanda criada e atribuída a você.');
        } catch (error) {
            toast(error.message, true);
            button.disabled = false;
        }
    }

    function closeModal() {
        elements.modal.classList.remove('is-open');
        elements.modal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('dm-modal-open');
        state.detail = null;
        state.requestDetail = null;
        state.statusAction = null;
    }

    function readonlyItem(label, value, wide) {
        return `<div class="dm-readonly${wide ? ' dm-readonly--wide' : ''}"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(display(value))}</dd></div>`;
    }

    function directDemandField(label, fieldName, value, type, wide) {
        let control;
        if (type === 'textarea') {
            control = `<textarea class="dm-textarea" data-field="${fieldName}" maxlength="4000">${escapeHtml(valueOrEmpty(value))}</textarea>`;
        } else {
            control = `<input class="dm-input" data-field="${fieldName}" type="text" maxlength="250" value="${escapeHtml(valueOrEmpty(value))}">`;
        }
        return `<label class="dm-field${wide ? ' dm-field--wide' : ''}"><span>${escapeHtml(label)}</span>${control}</label>`;
    }

    function renderDirectDemandPanel(demand) {
        const structured = ['projeto', 'melhoria'].includes(demand.demandType);
        if (!demand.createdByCurrentUser) {
            return `
                <section class="dm-panel">
                    <h3>Dados da demanda interna</h3>
                    <dl class="dm-readonly-grid">
                        ${readonlyItem('Título', demand.title, true)}
                        ${readonlyItem('Descrição', demand.initialDescription, true)}
                        ${structured ? readonlyItem('Premissas', demand.assumptions, true) : ''}
                        ${structured ? readonlyItem('Problemas atuais', demand.actualProblems, true) : ''}
                        ${structured ? readonlyItem('Ganhos esperados', demand.benefits, true) : ''}
                        ${readonlyItem('Tipo', typeLabel(demand.demandType))}
                        ${readonlyItem('Criada por', demand.createdByName)}
                        ${readonlyItem('Criada em', formatDate(demand.createdAt, true))}
                    </dl>
                </section>`;
        }

        return `
            <section class="dm-panel">
                <h3>Dados da atividade interna</h3>
                <p class="dm-personal-note">Esta atividade pode ser editada.</p>
                <div class="dm-direct-grid">
                    ${directDemandField('Título', 'title', demand.title, 'text', true)}
                    ${directDemandField(
                        demand.demandType === 'erro' ? 'Descrição completa do erro' : 'Descrição inicial / objetivo',
                        'initialDescription', demand.initialDescription, 'textarea', true
                    )}
                    ${structured ? directDemandField('Premissas', 'assumptions', demand.assumptions, 'textarea', true) : ''}
                    ${structured ? directDemandField('Problemas atuais', 'actualProblems', demand.actualProblems, 'textarea', true) : ''}
                    ${structured ? directDemandField('Ganhos esperados', 'benefits', demand.benefits, 'textarea', true) : ''}
                </div>
            </section>`;
    }

    function renderOriginalRequestPanel(demand) {
        return `
            <section class="dm-panel">
                <h3>Solicitação original · somente leitura</h3>
                <dl class="dm-readonly-grid">
                    ${readonlyItem('Título', demand.title, true)}
                    ${readonlyItem('Descrição inicial / objetivo', demand.initialDescription, true)}
                    ${demand.demandType !== 'erro' ? readonlyItem('Premissas', demand.assumptions, true) : ''}
                    ${demand.demandType !== 'erro' ? readonlyItem('Problemas atuais', demand.actualProblems, true) : ''}
                    ${demand.demandType !== 'erro' ? readonlyItem('Ganhos esperados', demand.benefits, true) : ''}
                    ${readonlyItem('Solicitante', demand.requesterName)}
                    ${readonlyItem('ID da solicitação', `#${demand.sourceRequestId}`)}
                    ${readonlyItem('Tipo', typeLabel(demand.demandType))}
                    ${readonlyItem('Urgência', demand.urgency)}
                    ${readonlyItem('Data da solicitação', formatDate(demand.requestDate, true))}
                    ${readonlyItem('Início original', formatDate(demand.requestStartDate, false))}
                    ${readonlyItem('Prazo original', formatDate(demand.requestDeadline, false))}
                    ${readonlyItem('Conclusão original', formatDate(demand.requestFinalDate, true))}
                    ${readonlyItem('Reprogramações', String(demand.requestReprograms || 0))}
                </dl>
                <div class="dm-source-section">
                    <h4>Documentos anexados</h4>
                    ${renderAttachments(demand.sourceRequestId, demand.attachments)}
                </div>
                ${renderRequestPauses(demand.requestPauses)}
            </section>`;
    }

    function renderModal(demand) {
        elements.modalContent.innerHTML = `
            <header class="dm-modal__header">
                <div class="dm-badges">
                    <span class="dm-badge ${typeBadgeClass(demand.demandType)}">${escapeHtml(typeLabel(demand.demandType))}</span>
                    <span class="dm-badge dm-badge--status-${slug(demand.status)}">${escapeHtml(demand.status)}</span>
                    ${demand.difficulty ? `<span class="dm-badge dm-badge--difficulty-${slug(demand.difficulty)}">${escapeHtml(demand.difficulty)}</span>` : ''}
                    ${isLate(demand) ? '<span class="dm-badge dm-badge--late">Atrasada</span>' : ''}
                </div>
                <h2 id="dm-modal-title">${escapeHtml(demand.title)}</h2>
            </header>

            <div class="dm-modal__columns">
                <section class="dm-panel">
                    <h3>Gerenciamento</h3>
                    <div class="dm-form-grid">
                        ${field('Responsável', 'responsibleId', demand.responsibleId, 'select', state.responsibles)}
                        ${field('Dificuldade', 'difficulty', demand.difficulty, 'select', state.options.difficulty || [])}
                        ${field('Prazo', 'deadline', demand.deadline && demand.deadline.substring(0, 10), 'date')}
                        ${readonlyField('Data de início', 'startDate', demand.startDate && demand.startDate.substring(0, 10), 'date')}
                        ${renderDeadlineChangeForm(demand)}
                        ${field('Tempo total estimado (h)', 'estimatedHours', demand.estimatedHours, 'number')}
                        ${field('Tempo diário (h)', 'dailyHours', demand.dailyHours, 'number')}
                        ${field('Tempo total realizado (h)', 'completedHours', demand.completedHours, 'number')}
                        ${field('Observações', 'observations', demand.observations, 'textarea')}
                    </div>
                    ${renderStatusActions(demand)}
                    ${renderStatusActionForm(demand)}
                </section>

                ${demand.isDirectDemand ? renderDirectDemandPanel(demand) : renderOriginalRequestPanel(demand)}
            </div>

            <section class="dm-panel dm-tasks">
                <h3>Tarefas · ${demand.completedTasks || 0}/${demand.totalTasks || 0} concluídas</h3>
                <div class="dm-task-warning" data-task-warning role="status" aria-live="polite" hidden>
                    <span class="dm-task-warning__dot" aria-hidden="true"></span>
                    <strong>Alterações pendentes</strong>
                    <span data-task-warning-text>Uma tarefa foi modificada e ainda não foi salva.</span>
                </div>
                <div class="dm-task-list">${renderTasks(demand.tasks || [])}</div>
                ${renderNewTaskForm()}
            </section>`;
    }

    function renderRequestModal(item) {
        const refused = Number(item.status) === 3;
        elements.modalContent.innerHTML = `
            <header class="dm-modal__header">
                <div class="dm-badges">
                    <span class="dm-badge ${typeBadgeClass(item.demandType)}">${escapeHtml(typeLabel(item.demandType))}</span>
                    <span class="dm-badge dm-badge--review-${refused ? 'declined' : 'pending'}">${escapeHtml(requestStatusLabel(item.status))}</span>
                    <span class="dm-badge dm-badge--urgency-${slug(item.urgency)}">Urgência ${escapeHtml(display(item.urgency))}</span>
                </div>
                <h2 id="dm-modal-title">${escapeHtml(item.title)}</h2>
                <p class="dm-modal__meta">Solicitação #${item.requestId} · ${escapeHtml(item.requesterName)} · ${escapeHtml(formatDate(item.requestDate, true))}</p>
            </header>

            <div class="dm-modal__columns dm-review-modal__columns">
                <section class="dm-panel">
                    <h3>Dados da solicitação</h3>
                    <dl class="dm-readonly-grid">
                        ${readonlyItem('Título', item.title, true)}
                        ${readonlyItem('Descrição inicial / objetivo', item.initialDescription, true)}
                        ${item.demandType !== 'erro' ? readonlyItem('Premissas', item.assumptions, true) : ''}
                        ${item.demandType !== 'erro' ? readonlyItem('Problemas atuais', item.actualProblems, true) : ''}
                        ${item.demandType !== 'erro' ? readonlyItem('Ganhos esperados', item.benefits, true) : ''}
                        ${readonlyItem('Solicitante', item.requesterName)}
                        ${readonlyItem('Tipo', typeLabel(item.demandType))}
                        ${readonlyItem('Urgência', item.urgency)}
                        ${readonlyItem('Data da solicitação', formatDate(item.requestDate, true))}
                        ${refused ? readonlyItem('Responsável pela análise', item.responsibleName) : ''}
                        ${refused ? readonlyItem('Data da recusa', formatDate(item.finalDate, true)) : ''}
                        ${refused ? readonlyItem('Motivo da recusa', item.deniedText, true) : ''}
                    </dl>
                    <div class="dm-source-section">
                        <h4>Documentos anexados</h4>
                        ${renderAttachments(item.requestId, item.attachments)}
                    </div>
                </section>

                ${refused ? renderDeclinedRequestPanel() : renderReviewDecisionPanel()}
            </div>`;
    }

    function renderDeclinedRequestPanel() {
        return `
            <aside class="dm-panel dm-review-decision">
                <h3>Análise finalizada</h3>
                <p>Esta solicitação foi recusada e permanece disponível apenas para consulta.</p>
            </aside>`;
    }

    function renderReviewDecisionPanel() {
        return `
            <aside class="dm-panel dm-review-decision">
                <h3>Analisar demanda</h3>
                <form id="dm-approve-request" class="dm-decision-form">
                    <p>Ao aprovar, o card será criado como A Fazer para o responsável selecionado. O prazo será definido quando o desenvolvimento for iniciado.</p>
                    <label class="dm-field">
                        <span>Responsável pela demanda</span>
                        <select class="dm-input" name="responsibleId" required>${optionList(state.responsibles, '', 'Selecione um responsável')}</select>
                    </label>
                    <button class="dm-button" type="submit">Aprovar demanda</button>
                </form>
                <div class="dm-decision-divider"><span>ou</span></div>
                <form id="dm-decline-request" class="dm-decision-form">
                    <label class="dm-field">
                        <span>Motivo da recusa</span>
                        <textarea class="dm-textarea" name="reason" required maxlength="4000" placeholder="Explique ao solicitante por que a demanda não será aprovada"></textarea>
                    </label>
                    <button class="dm-button dm-button--danger" type="submit">Recusar demanda</button>
                </form>
            </aside>`;
    }

    async function decideRequest(form, action) {
        if (!state.requestDetail) return;
        const button = form.querySelector('button[type="submit"]');
        const payload = action === 'approve'
            ? { responsibleId: form.elements.responsibleId.value }
            : { reason: form.elements.reason.value };
        button.disabled = true;
        try {
            await api(`${config.apiRoot}/requests/${state.requestDetail.requestId}/${action}`, {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            closeModal();
            await Promise.all([loadBoard(false), loadRequests(false)]);
            toast(action === 'approve'
                ? 'Demanda aprovada como A Fazer e atribuída ao responsável.'
                : 'Solicitação recusada.');
        } catch (error) {
            toast(error.message, true);
            button.disabled = false;
        }
    }

    async function transitionStatus(form) {
        if (!state.detail) return;
        const button = form.querySelector('button[type="submit"]');
        const action = form.dataset.action;
        const payload = {
            action: action,
            rowVersion: state.detail.rowVersion
        };
        if (form.elements.deadline) payload.deadline = form.elements.deadline.value;
        if (form.elements.reason) payload.reason = form.elements.reason.value;
        if (form.elements.expectedReturn) {
            payload.expectedReturn = form.elements.expectedReturn.value;
        }

        button.disabled = true;
        try {
            const detail = await api(`${config.apiRoot}/${state.detail.managementId}/status`, {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            state.statusAction = null;
            applyDetail(detail);
            toast('Status da demanda atualizado.');
        } catch (error) {
            toast(error.message, true);
            button.disabled = false;
            if (error.status === 409) await loadBoard(false);
        }
    }

    function renderTasks(tasks) {
        if (!tasks.length) return '<div class="dm-empty">Nenhuma tarefa cadastrada.</div>';
        return tasks.map(function (task) {
            const completed = Boolean(task.completedAt);
            const taskLate = !completed && task.deadline && new Date(`${task.deadline.substring(0, 10)}T00:00:00`) < new Date(new Date().setHours(0, 0, 0, 0));
            const taskStatus = completed ? 'Concluída' : (taskLate ? 'Atrasada' : 'Em andamento');
            return `
                <div class="dm-task${completed ? ' dm-task--completed' : ''}" data-task-id="${task.taskId}" data-row-version="${escapeHtml(task.rowVersion)}">
                    <input class="dm-task__check" name="completed" type="checkbox" ${completed ? 'checked' : ''} title="Marcar como concluída">
                    <label class="dm-field dm-task__description"><span>Tarefa · ${taskStatus}</span><textarea class="dm-textarea" name="description">${escapeHtml(task.description)}</textarea></label>
                    <label class="dm-field dm-task__responsible"><span>Responsável</span><select class="dm-input" name="responsibleId">${optionList(state.responsibles, task.responsibleId, 'Não informado')}</select></label>
                    <label class="dm-field dm-task__deadline"><span>Prazo</span><input class="dm-input" name="deadline" type="date" value="${escapeHtml(task.deadline ? task.deadline.substring(0, 10) : '')}"></label>
                    <label class="dm-field dm-task__observations"><span>Observações</span><textarea class="dm-textarea" name="observations">${escapeHtml(valueOrEmpty(task.observations))}</textarea></label>
                    <div class="dm-task__actions">
                        <span class="dm-task__pending" data-task-pending hidden>Não salvo</span>
                        <button class="dm-button" type="button" data-save-task>Salvar</button>
                        <button class="dm-button dm-button--danger" type="button" data-delete-task>Excluir</button>
                    </div>
                </div>`;
        }).join('');
    }

    function renderNewTaskForm() {
        return `
            <form class="dm-task-form" id="dm-new-task">
                <label class="dm-field dm-task-form__description"><span>Nova tarefa</span><input class="dm-input" name="description" type="text" required maxlength="1000" placeholder="Descreva uma entrega objetiva"></label>
                <label class="dm-field dm-task-form__responsible"><span>Responsável</span><select class="dm-input" name="responsibleId">${optionList(state.responsibles, '', 'Não informado')}</select></label>
                <label class="dm-field dm-task-form__deadline"><span>Prazo</span><input class="dm-input" name="deadline" type="date"></label>
                <button class="dm-button" type="submit">Adicionar tarefa</button>
            </form>`;
    }

    function taskPayload(container) {
        const observationsInput = container.querySelector('[name="observations"]');
        return {
            description: container.querySelector('[name="description"]').value,
            responsibleId: container.querySelector('[name="responsibleId"]').value || null,
            deadline: container.querySelector('[name="deadline"]').value || null,
            observations: observationsInput ? observationsInput.value || null : null,
            completed: Boolean(container.querySelector('[name="completed"]') && container.querySelector('[name="completed"]').checked)
        };
    }

    async function createTask(form) {
        const button = form.querySelector('button[type="submit"]');
        button.disabled = true;
        try {
            const detail = await api(`${config.apiRoot}/${state.detail.managementId}/tasks`, {
                method: 'POST',
                body: JSON.stringify(taskPayload(form))
            });
            applyDetail(detail);
            toast('Tarefa adicionada.');
        } catch (error) {
            toast(error.message, true);
        } finally {
            button.disabled = false;
        }
    }

    function comparableTaskPayload(task) {
        return {
            description: String(valueOrEmpty(task.description)),
            responsibleId: String(valueOrEmpty(task.responsibleId)),
            deadline: task.deadline ? String(task.deadline).substring(0, 10) : '',
            observations: String(valueOrEmpty(task.observations)),
            completed: Boolean(task.completed !== undefined ? task.completed : task.completedAt)
        };
    }

    function taskHasChanges(row) {
        if (!state.detail) return false;
        const taskId = Number(row.dataset.taskId);
        const original = (state.detail.tasks || []).find(function (task) {
            return Number(task.taskId) === taskId;
        });
        if (!original) return false;

        const current = comparableTaskPayload(taskPayload(row));
        const saved = comparableTaskPayload(original);
        return Object.keys(current).some(function (fieldName) {
            return current[fieldName] !== saved[fieldName];
        });
    }

    function updateTaskWarning() {
        const warning = elements.modalContent.querySelector('[data-task-warning]');
        if (!warning) return;
        const dirtyCount = elements.modalContent.querySelectorAll('.dm-task--dirty').length;
        warning.hidden = dirtyCount === 0;
        const message = warning.querySelector('[data-task-warning-text]');
        if (message) {
            message.textContent = dirtyCount === 1
                ? 'Uma tarefa foi modificada e ainda não foi salva.'
                : `${dirtyCount} tarefas foram modificadas e ainda não foram salvas.`;
        }
    }

    function markTaskChanges(row) {
        const changed = taskHasChanges(row);
        const pending = row.querySelector('[data-task-pending]');
        row.classList.toggle('dm-task--dirty', changed);
        if (pending) pending.hidden = !changed;
        updateTaskWarning();
    }

    async function saveTask(row) {
        const taskId = Number(row.dataset.taskId);
        const button = row.querySelector('[data-save-task]');
        button.disabled = true;
        try {
            const payload = taskPayload(row);
            payload.rowVersion = row.dataset.rowVersion;
            const detail = await api(`${config.apiRoot}/${state.detail.managementId}/tasks/${taskId}`, {
                method: 'PATCH',
                body: JSON.stringify(payload)
            });
            applyDetail(detail);
            toast('Tarefa salva.');
        } catch (error) {
            toast(error.message, true);
        } finally {
            button.disabled = false;
        }
    }

    async function deleteTask(row) {
        if (!window.confirm('Excluir esta tarefa?')) return;
        try {
            const detail = await api(`${config.apiRoot}/${state.detail.managementId}/tasks/${row.dataset.taskId}`, {
                method: 'DELETE',
                body: JSON.stringify({ rowVersion: row.dataset.rowVersion })
            });
            applyDetail(detail);
            toast('Tarefa excluída.');
        } catch (error) {
            toast(error.message, true);
        }
    }

    function applyDetail(detail) {
        state.detail = detail;
        replaceDemand(detail);
        renderAll();
        renderModal(detail);
    }

    elements.board.addEventListener('click', function (event) {
        const cancelDeadline = event.target.closest('[data-cancel-deadline-change]');
        if (cancelDeadline) {
            cancelDeadlineChange(Number(cancelDeadline.dataset.cancelDeadlineChange));
            return;
        }
        const toggle = event.target.closest('[data-owner-toggle]');
        if (toggle) {
            const key = toggle.dataset.ownerToggle;
            state.collapsedOwners.has(key) ? state.collapsedOwners.delete(key) : state.collapsedOwners.add(key);
            renderBoard();
            return;
        }
        if (event.target.closest('input, select, textarea, button, a')) return;
        const card = event.target.closest('[data-management-id]');
        if (card) openModal(Number(card.dataset.managementId));
    });

    elements.board.addEventListener('keydown', function (event) {
        if (event.key !== 'Enter' || event.target.closest('input, select, textarea, button, a')) return;
        const card = event.target.closest('[data-management-id]');
        if (card) openModal(Number(card.dataset.managementId));
    });

    elements.requestList.addEventListener('click', function (event) {
        const target = event.target.closest('[data-review-request], [data-request-id]');
        if (target) openRequestModal(Number(target.dataset.reviewRequest || target.dataset.requestId));
    });

    elements.requestList.addEventListener('keydown', function (event) {
        if (event.key !== 'Enter') return;
        const card = event.target.closest('[data-request-id]');
        if (card) openRequestModal(Number(card.dataset.requestId));
    });

    elements.board.addEventListener('change', function (event) {
        const input = event.target.closest('[data-field]');
        if (!input) return;
        const card = input.closest('[data-management-id]');
        changeDemandField(Number(card.dataset.managementId), input);
    });

    elements.board.addEventListener('submit', function (event) {
        const form = event.target.closest('[data-deadline-change-form]');
        if (!form) return;
        event.preventDefault();
        submitDeadlineChange(form);
    });

    elements.modal.addEventListener('click', function (event) {
        if (event.target.closest('[data-close-modal]')) {
            closeModal();
            return;
        }
        const cancelDeadline = event.target.closest('[data-cancel-deadline-change]');
        if (cancelDeadline) {
            cancelDeadlineChange(Number(cancelDeadline.dataset.cancelDeadlineChange));
            return;
        }
        const statusButton = event.target.closest('[data-status-action]');
        if (statusButton && state.detail) {
            state.statusAction = statusButton.dataset.statusAction;
            renderModal(state.detail);
            return;
        }
        if (event.target.closest('[data-cancel-status-action]') && state.detail) {
            state.statusAction = null;
            renderModal(state.detail);
            return;
        }
        const saveButton = event.target.closest('[data-save-task]');
        if (saveButton) saveTask(saveButton.closest('[data-task-id]'));
        const deleteButton = event.target.closest('[data-delete-task]');
        if (deleteButton) deleteTask(deleteButton.closest('[data-task-id]'));
    });

    elements.modal.addEventListener('change', function (event) {
        const taskRow = event.target.closest('[data-task-id]');
        if (taskRow) {
            markTaskChanges(taskRow);
            return;
        }
        const input = event.target.closest('[data-field]');
        if (!input || !state.detail) return;
        changeDemandField(state.detail.managementId, input);
    });

    elements.modal.addEventListener('input', function (event) {
        const taskRow = event.target.closest('[data-task-id]');
        if (taskRow) markTaskChanges(taskRow);
    });

    elements.modal.addEventListener('submit', function (event) {
        if (event.target.matches('[data-deadline-change-form]')) {
            event.preventDefault();
            submitDeadlineChange(event.target);
        } else if (event.target.id === 'dm-create-demand-form') {
            event.preventDefault();
            createPersonalDemand(event.target);
        } else if (event.target.id === 'dm-new-task') {
            event.preventDefault();
            createTask(event.target);
        } else if (event.target.id === 'dm-approve-request') {
            event.preventDefault();
            decideRequest(event.target, 'approve');
        } else if (event.target.id === 'dm-decline-request') {
            event.preventDefault();
            decideRequest(event.target, 'decline');
        } else if (event.target.id === 'dm-status-transition') {
            event.preventDefault();
            transitionStatus(event.target);
        }
    });

    [elements.responsible, elements.type, elements.status, elements.difficulty].forEach(function (filter) {
        filter.addEventListener('change', renderBoard);
    });
    elements.search.addEventListener('input', renderBoard);
    elements.clearFilters.addEventListener('click', function () {
        elements.search.value = '';
        elements.responsible.value = '';
        elements.type.value = '';
        elements.status.value = '';
        elements.difficulty.value = '';
        renderBoard();
    });
    elements.createDemand.addEventListener('click', openCreateDemandModal);

    [elements.requestType, elements.requestStatus, elements.requestUrgency].forEach(function (filter) {
        filter.addEventListener('change', renderRequests);
    });
    elements.requestSearch.addEventListener('input', renderRequests);
    elements.clearRequestFilters.addEventListener('click', function () {
        elements.requestSearch.value = '';
        elements.requestType.value = '';
        elements.requestStatus.value = '0';
        elements.requestUrgency.value = '';
        renderRequests();
    });
    elements.tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            changeView(tab.dataset.view);
        });
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && elements.modal.classList.contains('is-open')) closeModal();
    });

    renderNavigation();
    Promise.all([loadBoard(), loadRequests()]);
}());
