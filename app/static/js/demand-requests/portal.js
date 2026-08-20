(function () {
    'use strict';

    const config = window.demandRequestsConfig || {};
    const requests = Array.isArray(config.requests) ? config.requests : [];

    const typeLabels = {
        melhoria: 'Melhoria',
        projeto: 'Projeto',
        erro: 'Erro/Defeito'
    };

    const statusLabels = {
        0: 'Em análise',
        1: 'Em andamento',
        2: 'Concluída',
        3: 'Recusada',
        4: 'Pausada'
    };

    const elements = {
        tabs: Array.from(document.querySelectorAll('.dr-tab')),
        newView: document.getElementById('dr-new-view'),
        requestsView: document.getElementById('dr-requests-view'),
        summary: document.getElementById('dr-summary'),
        grid: document.getElementById('dr-request-grid'),
        search: document.getElementById('dr-search'),
        typeFilter: document.getElementById('dr-filter-type'),
        statusFilter: document.getElementById('dr-filter-status'),
        clearFilters: document.getElementById('dr-clear-filters'),
        form: document.getElementById('dr-request-form'),
        formFeedback: document.getElementById('dr-form-feedback'),
        demandType: document.getElementById('dr-demand-type'),
        objectiveLabel: document.getElementById('dr-objective-label'),
        objective: document.getElementById('dr-objective'),
        structuredFields: document.getElementById('dr-structured-fields'),
        fileInput: document.getElementById('dr-documents-input'),
        filePickerLabel: document.getElementById('dr-file-picker-label'),
        fileList: document.getElementById('dr-file-list'),
        submit: document.getElementById('dr-submit'),
        toast: document.getElementById('dr-toast')
    };

    function valueOrEmpty(value) {
        return value === null || value === undefined ? '' : value;
    }

    function escapeHtml(value) {
        return String(valueOrEmpty(value))
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function normalizeText(value) {
        return String(valueOrEmpty(value))
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase();
    }

    function formatDate(value, includeTime) {
        if (!value) {
            return 'Não informado';
        }

        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return String(value);
        }

        const options = includeTime
            ? { dateStyle: 'short', timeStyle: 'short' }
            : { dateStyle: 'short' };
        return new Intl.DateTimeFormat('pt-BR', options).format(date);
    }

    function requestType(requestItem) {
        const type = String(requestItem.demandType || 'melhoria').toLowerCase();
        return typeLabels[type] ? type : 'melhoria';
    }

    function requestStatus(requestItem) {
        const rawStatus = requestItem.status === null || requestItem.status === undefined
            ? 0
            : requestItem.status;
        const status = String(rawStatus);
        return statusLabels[status] ? status : '0';
    }

    function setTab(tabName, updateAddress) {
        const activeTab = tabName === 'minhas' ? 'minhas' : 'nova';

        elements.tabs.forEach(function (tab) {
            const isActive = tab.dataset.tab === activeTab;
            tab.classList.toggle('is-active', isActive);
            tab.setAttribute('aria-selected', String(isActive));
        });

        elements.newView.hidden = activeTab !== 'nova';
        elements.requestsView.hidden = activeTab !== 'minhas';

        if (updateAddress && window.history && window.history.replaceState) {
            const url = new URL(window.location.href);
            url.searchParams.delete('sent');

            if (activeTab === 'minhas') {
                url.searchParams.set('tab', 'minhas');
            } else {
                url.searchParams.delete('tab');
            }

            window.history.replaceState({}, '', url);
        }
    }

    function renderSummary() {
        const countStatus = function (status) {
            return requests.filter(function (requestItem) {
                return requestStatus(requestItem) === String(status);
            }).length;
        };

        const items = [
            [requests.length, 'Total'],
            [countStatus(0), 'Em análise'],
            [countStatus(1) + countStatus(4), 'Em andamento'],
            [countStatus(2), 'Concluídas']
        ];

        elements.summary.innerHTML = items.map(function (item) {
            return '<div class="dr-summary__item">' +
                '<strong>' + item[0] + '</strong>' +
                '<span>' + item[1] + '</span>' +
            '</div>';
        }).join('');
    }

    function fillFilters() {
        Object.keys(typeLabels).forEach(function (type) {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = typeLabels[type];
            elements.typeFilter.appendChild(option);
        });

        Object.keys(statusLabels).forEach(function (status) {
            const option = document.createElement('option');
            option.value = status;
            option.textContent = statusLabels[status];
            elements.statusFilter.appendChild(option);
        });
    }

    function secondaryDetail(requestItem) {
        const status = requestStatus(requestItem);

        if (status === '2') {
            return ['Concluída em', formatDate(requestItem.finalDate, true)];
        }

        if (status === '3') {
            return ['Resultado', 'Solicitação recusada'];
        }

        return ['Prazo', formatDate(requestItem.deadline, false)];
    }

    function cardClass(status) {
        if (status === '3') {
            return ' dr-request-card--denied';
        }
        if (status === '2') {
            return ' dr-request-card--complete';
        }
        return '';
    }

    function urgencyClass(urgency) {
        return normalizeText(urgency) === 'alta' ? ' dr-badge--urgency-high' : '';
    }

    function requestCard(requestItem) {
        const type = requestType(requestItem);
        const status = requestStatus(requestItem);
        const urgency = requestItem.urgency || 'Não informada';
        const detail = secondaryDetail(requestItem);

        return '<article class="dr-request-card' + cardClass(status) + '" tabindex="0" role="button" aria-label="Visualizar ' +
            escapeHtml(requestItem.title || 'solicitação') + '" data-request-id="' + escapeHtml(requestItem.requestId) + '">' +
                '<div class="dr-request-card__badges">' +
                    '<span class="dr-badge dr-badge--type-' + type + '">' + escapeHtml(typeLabels[type]) + '</span>' +
                    '<span class="dr-badge dr-badge--status-' + status + '">' + escapeHtml(statusLabels[status]) + '</span>' +
                    '<span class="dr-badge' + urgencyClass(urgency) + '">' + escapeHtml(urgency) + '</span>' +
                '</div>' +
                '<h3>' + escapeHtml(requestItem.title || 'Demanda sem título') + '</h3>' +
                '<p class="dr-request-card__description">' + escapeHtml(requestItem.initialDescription || 'Sem descrição informada.') + '</p>' +
                '<div class="dr-request-card__details">' +
                    '<div><span>Solicitada em</span><strong>' + escapeHtml(formatDate(requestItem.requestDate, true)) + '</strong></div>' +
                    '<div><span>' + escapeHtml(detail[0]) + '</span><strong>' + escapeHtml(detail[1]) + '</strong></div>' +
                '</div>' +
                '<div class="dr-request-card__footer">' +
                    '<span>Solicitação #' + escapeHtml(requestItem.requestId) + '</span>' +
                    '<button class="dr-button dr-button--card" type="button">Ver detalhes</button>' +
                '</div>' +
            '</article>';
    }

    function filteredRequests() {
        const search = normalizeText(elements.search.value);
        const type = elements.typeFilter.value;
        const status = elements.statusFilter.value;

        return requests.filter(function (requestItem) {
            const text = normalizeText(
                (requestItem.title || '') + ' ' + (requestItem.initialDescription || '')
            );
            return (!search || text.includes(search)) &&
                (!type || requestType(requestItem) === type) &&
                (!status || requestStatus(requestItem) === status);
        });
    }

    function renderRequests() {
        const filtered = filteredRequests();

        if (!filtered.length) {
            const hasFilters = Boolean(
                elements.search.value || elements.typeFilter.value || elements.statusFilter.value
            );
            elements.grid.innerHTML = '<div class="dr-empty">' +
                '<strong>' + (hasFilters ? 'Nenhuma solicitação encontrada' : 'Você ainda não fez nenhuma solicitação') + '</strong>' +
                '<span>' + (hasFilters ? 'Altere os filtros para tentar novamente.' : 'Use a primeira aba para enviar uma nova demanda.') + '</span>' +
            '</div>';
            return;
        }

        elements.grid.innerHTML = filtered.map(requestCard).join('');
    }

    function openRequestDetail(requestId) {
        const url = new URL(config.detailUrl, window.location.origin);
        url.searchParams.set('area', config.area);
        url.searchParams.set('tipo', 'melhorias');
        url.searchParams.set('id', requestId);
        window.location.assign(url.toString());
    }

    function updateDemandFields() {
        const isError = elements.demandType.value === 'erro';
        const structuredInputs = elements.structuredFields.querySelectorAll('textarea');

        elements.structuredFields.hidden = isError;
        elements.objectiveLabel.textContent = isError
            ? 'Descrição completa do problema *'
            : 'Objetivo da demanda *';
        elements.objective.placeholder = isError
            ? 'Descreva detalhadamente o erro ou defeito encontrado'
            : 'Explique de forma clara o objetivo da demanda';

        structuredInputs.forEach(function (input) {
            input.required = !isError;
        });
    }

    function updateFileList() {
        const files = Array.from(elements.fileInput.files || []);
        elements.fileList.innerHTML = '';
        elements.filePickerLabel.textContent = files.length
            ? 'Alterar documentos selecionados'
            : 'Selecionar documentos *';

        files.forEach(function (file) {
            const item = document.createElement('li');
            item.textContent = file.name;
            elements.fileList.appendChild(item);
        });
    }

    function setFormError(message) {
        elements.formFeedback.textContent = message || '';
        elements.formFeedback.hidden = !message;
    }

    function setSubmitting(isSubmitting) {
        elements.submit.disabled = isSubmitting;
        elements.submit.textContent = isSubmitting ? 'Enviando...' : 'Solicitar demanda';
    }

    function showToast(message) {
        elements.toast.textContent = message;
        elements.toast.classList.add('is-visible');
        window.setTimeout(function () {
            elements.toast.classList.remove('is-visible');
        }, 4500);
    }

    async function submitRequest(event) {
        event.preventDefault();
        setFormError('');
        setSubmitting(true);
        let errorMessage = 'Não foi possível enviar a solicitação. Tente novamente.';

        try {
            const response = await fetch(elements.form.action, {
                method: 'POST',
                body: new FormData(elements.form),
                credentials: 'same-origin'
            });

            if (response.redirected && new URL(response.url).pathname.includes('/login')) {
                window.location.assign(response.url);
                return;
            }

            if (!response.ok) {
                errorMessage = response.status === 400
                    ? 'Revise os campos obrigatórios e tente novamente.'
                    : 'Não foi possível enviar a solicitação. Tente novamente.';
                throw new Error('request_failed');
            }

            const destination = new URL(config.portalUrl, window.location.origin);
            destination.searchParams.set('tab', 'minhas');
            destination.searchParams.set('sent', '1');
            window.location.assign(destination.toString());
        } catch (error) {
            setFormError(errorMessage);
            setSubmitting(false);
        }
    }

    elements.tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            setTab(tab.dataset.tab, true);
        });
    });

    elements.search.addEventListener('input', renderRequests);
    elements.typeFilter.addEventListener('change', renderRequests);
    elements.statusFilter.addEventListener('change', renderRequests);

    elements.clearFilters.addEventListener('click', function () {
        elements.search.value = '';
        elements.typeFilter.value = '';
        elements.statusFilter.value = '';
        renderRequests();
    });

    elements.grid.addEventListener('click', function (event) {
        const card = event.target.closest('[data-request-id]');
        if (card) {
            openRequestDetail(card.dataset.requestId);
        }
    });

    elements.grid.addEventListener('keydown', function (event) {
        const card = event.target.closest('[data-request-id]');
        if (card && (event.key === 'Enter' || event.key === ' ')) {
            event.preventDefault();
            openRequestDetail(card.dataset.requestId);
        }
    });

    elements.demandType.addEventListener('change', updateDemandFields);
    elements.fileInput.addEventListener('change', updateFileList);
    elements.form.addEventListener('submit', submitRequest);
    elements.form.addEventListener('reset', function () {
        window.setTimeout(function () {
            setFormError('');
            updateDemandFields();
            updateFileList();
        }, 0);
    });

    fillFilters();
    renderSummary();
    renderRequests();
    updateDemandFields();
    updateFileList();
    setTab(config.initialTab, false);

    if (config.requestSent) {
        showToast('Solicitação enviada com sucesso.');
        if (window.history && window.history.replaceState) {
            const url = new URL(window.location.href);
            url.searchParams.delete('sent');
            window.history.replaceState({}, '', url);
        }
    }
}());
