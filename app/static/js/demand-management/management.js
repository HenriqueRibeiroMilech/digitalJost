(function () {
    'use strict';

    const config = window.demandManagementConfig;
    const state = {
        demands: [],
        responsibles: [],
        options: { status: [], difficulty: [] },
        detail: null,
        collapsedOwners: new Set(),
        updateQueues: new Map(),
        filtersInitialized: false
    };

    const elements = {
        board: document.getElementById('dm-board'),
        loading: document.getElementById('dm-loading'),
        summary: document.getElementById('dm-summary'),
        search: document.getElementById('dm-search'),
        responsible: document.getElementById('dm-filter-responsible'),
        type: document.getElementById('dm-filter-type'),
        status: document.getElementById('dm-filter-status'),
        difficulty: document.getElementById('dm-filter-difficulty'),
        clearFilters: document.getElementById('dm-clear-filters'),
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
            melhoria: 'Melhoria',
            projeto: 'Projeto',
            erro: 'Erro'
        }[type] || display(type);
    }

    function isLate(demand) {
        if (!demand.deadline || ['Concluído', 'Cancelado'].includes(demand.status)) return false;
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return new Date(`${demand.deadline.substring(0, 10)}T00:00:00`) < today;
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
        } catch (error) {
            elements.board.innerHTML = `<div class="dm-empty">${escapeHtml(error.message)}</div>`;
        } finally {
            elements.loading.style.display = 'none';
        }
    }

    function configureFilters() {
        const selectedResponsible = elements.responsible.value;
        const selectedType = elements.type.value;
        const selectedStatus = state.filtersInitialized ? elements.status.value : 'Em Andamento';
        const selectedDifficulty = elements.difficulty.value;

        elements.responsible.innerHTML = '<option value="">Todos</option><option value="__unassigned__">Sem responsável</option>' +
            optionList(state.responsibles, selectedResponsible);
        elements.type.innerHTML = '<option value="">Todos</option>' +
            Array.from(new Set(state.demands.map(function (item) { return item.demandType; })))
                .filter(Boolean)
                .map(function (item) {
                    return `<option value="${escapeHtml(item)}">${escapeHtml(typeLabel(item))}</option>`;
                }).join('');
        elements.status.innerHTML = '<option value="">Todos</option>' + optionList(state.options.status || [], selectedStatus);
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
            const matchesResponsible = !responsibleFilter ||
                (responsibleFilter === '__unassigned__' ? !demand.responsibleId : demand.responsibleId === responsibleFilter);
            return matchesResponsible &&
                (!elements.type.value || demand.demandType === elements.type.value) &&
                (!elements.status.value || demand.status === elements.status.value) &&
                (!elements.difficulty.value || demand.difficulty === elements.difficulty.value) &&
                (!search || normalize(demand.title).includes(search));
        });
    }

    function renderSummary() {
        const active = state.demands.filter(function (item) {
            return !['Concluído', 'Cancelado'].includes(item.status);
        }).length;
        const late = state.demands.filter(isLate).length;
        const completed = state.demands.filter(function (item) { return item.status === 'Concluído'; }).length;
        elements.summary.innerHTML = [
            [state.demands.length, 'Total'],
            [active, 'Ativas'],
            [late, 'Atrasadas'],
            [completed, 'Concluídas']
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
                    name: demand.responsibleName || 'Sem responsável',
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

    function field(label, fieldName, value, type, options) {
        const safeValue = escapeHtml(valueOrEmpty(value));
        const fieldClass = `dm-field--${slug(fieldName)}`;
        let control;
        if (type === 'select') {
            control = `<select class="dm-input" data-field="${fieldName}">${optionList(options, value, 'Não informado')}</select>`;
        } else if (type === 'textarea') {
            control = `<textarea class="dm-textarea" data-field="${fieldName}" placeholder="Adicione uma observação">${safeValue}</textarea>`;
        } else {
            const step = type === 'number' ? ' step="0.25" min="0"' : '';
            control = `<input class="dm-input" data-field="${fieldName}" type="${type}"${step} value="${safeValue}">`;
        }
        return `<label class="dm-field ${fieldClass}${type === 'textarea' ? ' dm-field--wide' : ''}"><span>${label}</span>${control}</label>`;
    }

    function renderCard(demand) {
        const late = isLate(demand);
        const taskProgress = `${demand.completedTasks || 0}/${demand.totalTasks || 0}`;
        const badges = [
            `<span class="dm-badge dm-badge--type">${escapeHtml(typeLabel(demand.demandType))}</span>`,
            `<span class="dm-badge dm-badge--status-${slug(demand.status)}">${escapeHtml(demand.status)}</span>`,
            demand.difficulty ? `<span class="dm-badge dm-badge--difficulty-${slug(demand.difficulty)}">${escapeHtml(demand.difficulty)}</span>` : '',
            late ? '<span class="dm-badge dm-badge--late">Atrasada</span>' : ''
        ].join('');

        return `
            <article class="dm-card${late ? ' dm-card--late' : ''}" data-management-id="${demand.managementId}" tabindex="0" role="button" aria-label="Abrir detalhes de ${escapeHtml(demand.title)}">
                <div class="dm-card__top">
                    <div class="dm-card__identity">
                        <div class="dm-badges">${badges}</div>
                        <h2 class="dm-card__title">${escapeHtml(demand.title)}</h2>
                        <div class="dm-card__requester">Solicitante: <strong>${escapeHtml(demand.requesterName)}</strong> · #${demand.sourceRequestId}</div>
                        <p class="dm-card__description">${escapeHtml(demand.initialDescription)}</p>
                    </div>
                    <div class="dm-card__progress" title="Progresso das tarefas">
                        <strong>${taskProgress}</strong><span>tarefas</span>
                    </div>
                </div>
                <div class="dm-card__fields">
                    ${field('Status', 'status', demand.status, 'select', state.options.status || [])}
                    ${field('Prazo', 'deadline', demand.deadline && demand.deadline.substring(0, 10), 'date')}
                    ${field('Data de início', 'startDate', demand.startDate && demand.startDate.substring(0, 10), 'date')}
                    ${field('Tempo estimado (h)', 'estimatedHours', demand.estimatedHours, 'number')}
                    ${field('Tempo diário (h)', 'dailyHours', demand.dailyHours, 'number')}
                    ${field('Tempo realizado (h)', 'completedHours', demand.completedHours, 'number')}
                    ${field('Observações', 'observations', demand.observations, 'textarea')}
                </div>
            </article>`;
    }

    function updateDemand(managementId, fieldName, value, input) {
        input.disabled = true;
        const previous = state.updateQueues.get(managementId) || Promise.resolve();
        const operation = previous.catch(function () {}).then(async function () {
            const demand = state.demands.find(function (item) { return item.managementId === managementId; });
            if (!demand) return;
            const updated = await api(`${config.apiRoot}/${managementId}`, {
                method: 'PATCH',
                body: JSON.stringify({ field: fieldName, value: value, rowVersion: demand.rowVersion })
            });
            replaceDemand(updated);
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

    function replaceDemand(updated) {
        const index = state.demands.findIndex(function (item) {
            return item.managementId === updated.managementId;
        });
        if (index >= 0) state.demands[index] = updated;
    }

    async function openModal(managementId) {
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

    function closeModal() {
        elements.modal.classList.remove('is-open');
        elements.modal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('dm-modal-open');
        state.detail = null;
    }

    function readonlyItem(label, value, wide) {
        return `<div class="dm-readonly${wide ? ' dm-readonly--wide' : ''}"><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(display(value))}</dd></div>`;
    }

    function renderModal(demand) {
        const originalUrl = `/solicitar/detail?area=${encodeURIComponent(config.area)}&tipo=melhorias&id=${demand.sourceRequestId}`;
        elements.modalContent.innerHTML = `
            <header class="dm-modal__header">
                <div class="dm-badges">
                    <span class="dm-badge dm-badge--type">${escapeHtml(typeLabel(demand.demandType))}</span>
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
                        ${field('Status', 'status', demand.status, 'select', state.options.status || [])}
                        ${field('Responsável', 'responsibleId', demand.responsibleId, 'select', state.responsibles)}
                        ${field('Dificuldade', 'difficulty', demand.difficulty, 'select', state.options.difficulty || [])}
                        ${field('Prazo', 'deadline', demand.deadline && demand.deadline.substring(0, 10), 'date')}
                        ${field('Data de início', 'startDate', demand.startDate && demand.startDate.substring(0, 10), 'date')}
                        ${field('Tempo total estimado (h)', 'estimatedHours', demand.estimatedHours, 'number')}
                        ${field('Tempo diário (h)', 'dailyHours', demand.dailyHours, 'number')}
                        ${field('Tempo total realizado (h)', 'completedHours', demand.completedHours, 'number')}
                        ${field('Observações', 'observations', demand.observations, 'textarea')}
                    </div>
                    <p class="dm-source-note">Os campos são salvos ao sair do controle. Alterar o responsável move o card para a seção da pessoa sem recarregar a página.</p>
                </section>

                <section class="dm-panel">
                    <h3>Solicitação original · somente leitura</h3>
                    <dl class="dm-readonly-grid">
                        ${readonlyItem('ID da solicitação', `#${demand.sourceRequestId}`)}
                        ${readonlyItem('Tipo', typeLabel(demand.demandType))}
                        ${readonlyItem('Solicitante', demand.requesterName)}
                        ${readonlyItem('Urgência', demand.urgency)}
                        ${readonlyItem('Data da solicitação', formatDate(demand.requestDate, true))}
                        ${readonlyItem('Reprogramações', demand.requestReprograms || 0)}
                        ${readonlyItem('Título', demand.title, true)}
                        ${readonlyItem('Descrição inicial / objetivo', demand.initialDescription, true)}
                        ${demand.demandType !== 'erro' ? readonlyItem('Premissas', demand.assumptions, true) : ''}
                        ${demand.demandType !== 'erro' ? readonlyItem('Problemas atuais', demand.actualProblems, true) : ''}
                        ${demand.demandType !== 'erro' ? readonlyItem('Ganhos esperados', demand.benefits, true) : ''}
                        ${readonlyItem('Início no fluxo original', formatDate(demand.requestStartDate))}
                        ${readonlyItem('Prazo no fluxo original', formatDate(demand.requestDeadline))}
                        ${readonlyItem('Conclusão no fluxo original', formatDate(demand.requestFinalDate))}
                        ${readonlyItem('Possui anexos', demand.hasAttachments ? 'Sim — consulte a solicitação original' : 'Não')}
                    </dl>
                    <a class="dm-button" href="${originalUrl}" target="_blank" rel="noopener">Abrir solicitação original</a>
                </section>
            </div>

            <section class="dm-panel dm-tasks">
                <h3>Tarefas · ${demand.completedTasks || 0}/${demand.totalTasks || 0} concluídas</h3>
                <div class="dm-task-list">${renderTasks(demand.tasks || [])}</div>
                ${renderNewTaskForm()}
            </section>`;
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
                        <button class="dm-button" type="button" data-save-task>Salvar</button>
                        <button class="dm-button dm-button--danger" type="button" data-delete-task>Excluir</button>
                    </div>
                </div>`;
        }).join('');
    }

    function renderNewTaskForm() {
        return `
            <form class="dm-task-form" id="dm-new-task">
                <label class="dm-field dm-task-form__description"><span>Nova tarefa</span><textarea class="dm-textarea" name="description" required placeholder="Descreva uma entrega objetiva"></textarea></label>
                <label class="dm-field dm-task-form__responsible"><span>Responsável</span><select class="dm-input" name="responsibleId">${optionList(state.responsibles, '', 'Não informado')}</select></label>
                <label class="dm-field dm-task-form__deadline"><span>Prazo</span><input class="dm-input" name="deadline" type="date"></label>
                <label class="dm-field dm-task-form__observations"><span>Observações</span><textarea class="dm-textarea" name="observations"></textarea></label>
                <button class="dm-button" type="submit">Adicionar tarefa</button>
            </form>`;
    }

    function taskPayload(container) {
        return {
            description: container.querySelector('[name="description"]').value,
            responsibleId: container.querySelector('[name="responsibleId"]').value || null,
            deadline: container.querySelector('[name="deadline"]').value || null,
            observations: container.querySelector('[name="observations"]').value || null,
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

    elements.board.addEventListener('change', function (event) {
        const input = event.target.closest('[data-field]');
        if (!input) return;
        const card = input.closest('[data-management-id]');
        updateDemand(Number(card.dataset.managementId), input.dataset.field, input.value || null, input);
    });

    elements.modal.addEventListener('click', function (event) {
        if (event.target.closest('[data-close-modal]')) {
            closeModal();
            return;
        }
        const saveButton = event.target.closest('[data-save-task]');
        if (saveButton) saveTask(saveButton.closest('[data-task-id]'));
        const deleteButton = event.target.closest('[data-delete-task]');
        if (deleteButton) deleteTask(deleteButton.closest('[data-task-id]'));
    });

    elements.modal.addEventListener('change', function (event) {
        const input = event.target.closest('[data-field]');
        if (!input || !state.detail) return;
        updateDemand(state.detail.managementId, input.dataset.field, input.value || null, input);
    });

    elements.modal.addEventListener('submit', function (event) {
        if (event.target.id !== 'dm-new-task') return;
        event.preventDefault();
        createTask(event.target);
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

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && elements.modal.classList.contains('is-open')) closeModal();
    });

    loadBoard();
}());
