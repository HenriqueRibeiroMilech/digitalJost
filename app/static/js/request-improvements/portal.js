(function () {
    'use strict';

    const config = window.requestImprovementsConfig || {};
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
        tabs: Array.from(document.querySelectorAll('.ri-tab')),
        newView: document.getElementById('ri-new-view'),
        requestsView: document.getElementById('ri-requests-view'),
        summary: document.getElementById('ri-summary'),
        grid: document.getElementById('ri-request-grid'),
        search: document.getElementById('ri-search'),
        typeFilter: document.getElementById('ri-filter-type'),
        statusFilter: document.getElementById('ri-filter-status'),
        clearFilters: document.getElementById('ri-clear-filters'),
        form: document.getElementById('ri-request-form'),
        demandType: document.getElementById('ri-demand-type'),
        objectiveLabel: document.getElementById('ri-objective-label'),
        objective: document.getElementById('ri-objective'),
        structuredFields: document.getElementById('ri-structured-fields'),
        fileInput: document.getElementById('ri-documents-input'),
        filePickerLabel: document.getElementById('ri-file-picker-label'),
        fileList: document.getElementById('ri-file-list'),
        submit: document.getElementById('ri-submit'),
        toast: document.getElementById('ri-toast')
    };

    function escapeHtml(value) {
        return String(value === null || value === undefined ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function normalizeText(value) {
        return String(value === null || value === undefined ? '' : value)
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase();
    }

    function requestType(requestItem) {
        const type = String(requestItem.demandType || 'melhoria').toLowerCase();
        return typeLabels[type] ? type : 'melhoria';
    }

    function requestStatus(requestItem) {
        const status = String(requestItem.status === null || requestItem.status === undefined ? 0 : requestItem.status);
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

        const summaryItems = [
            [requests.length, 'Total'],
            [countStatus(0), 'Em análise'],
            [countStatus(1) + countStatus(4), 'Em andamento'],
            [countStatus(2), 'Concluídas']
        ];

        elements.summary.innerHTML = summaryItems.map(function (item) {
            return '<div class="ri-summary__item">' +
                '<strong>' + item[0] + '</strong>' +
                '<span>' + item[1] + '</span>' +
            '</div>';
        }).join('');
    }

    function fillFilters() {
        Object.entries(typeLabels).forEach(function (entry) {
            const option = document.createElement('option');
            option.value = entry[0];
            option.textContent = entry[1];
            elements.typeFilter.appendChild(option);
        });

        Object.entries(statusLabels).forEach(function (entry) {
            const option = document.createElement('option');
            option.value = entry[0];
            option.textContent = entry[1];
            elements.statusFilter.appendChild(option);
        });
    }

    function detailValue(requestItem) {
        const status = requestStatus(requestItem);

        if (status === '2' && requestItem.finalDate) {
            return ['Concluída em', requestItem.finalDate];
        }

        if (status === '3') {
            return ['Resultado', 'Solicitação recusada'];
        }

        return ['Prazo', requestItem.deliveryDate || 'Não definido'];
    }

    function cardClass(status) {
        if (status === '3') {
            return ' ri-request-card--denied';
        }

        if (status === '2') {
            return ' ri-request-card--complete';
        }

        return '';
    }

    function urgencyClass(urgency) {
        return normalizeText(urgency) === 'alta' ? ' ri-badge--urgency-high' : '';
    }

    function typeClass(type) {
        return ' ri-badge--type-' + type;
    }

    function requestCard(requestItem) {
        const type = requestType(requestItem);
        const status = requestStatus(requestItem);
        const urgency = requestItem.urgency || 'Não informada';
        const secondaryDetail = detailValue(requestItem);

        return '<article class="ri-request-card' + cardClass(status) + '" tabindex="0" role="button" aria-label="Visualizar ' +
            escapeHtml(requestItem.title || 'solicitação') + '" data-request-id="' + escapeHtml(requestItem.requestId) + '">' +
                '<div class="ri-request-card__badges">' +
                    '<span class="ri-badge' + typeClass(type) + '">' + escapeHtml(typeLabels[type]) + '</span>' +
                    '<span class="ri-badge ri-badge--status-' + status + '">' + escapeHtml(statusLabels[status]) + '</span>' +
                    '<span class="ri-badge' + urgencyClass(urgency) + '">' + escapeHtml(urgency) + '</span>' +
                '</div>' +
                '<h3>' + escapeHtml(requestItem.title || 'Demanda sem título') + '</h3>' +
                '<p class="ri-request-card__description">' + escapeHtml(requestItem.info || 'Sem descrição informada.') + '</p>' +
                '<div class="ri-request-card__details">' +
                    '<div><span>Solicitada em</span><strong>' + escapeHtml(requestItem.requestDate || 'Não informado') + '</strong></div>' +
                    '<div><span>' + escapeHtml(secondaryDetail[0]) + '</span><strong>' + escapeHtml(secondaryDetail[1]) + '</strong></div>' +
                '</div>' +
                '<div class="ri-request-card__footer">' +
                    '<span>Solicitação #' + escapeHtml(requestItem.requestId) + '</span>' +
                    '<button class="ri-button ri-button--card" type="button">Ver detalhes</button>' +
                '</div>' +
            '</article>';
    }

    function filteredRequests() {
        const search = normalizeText(elements.search.value);
        const type = elements.typeFilter.value;
        const status = elements.statusFilter.value;

        return requests.filter(function (requestItem) {
            const searchableText = normalizeText((requestItem.title || '') + ' ' + (requestItem.info || ''));
            const matchesSearch = !search || searchableText.includes(search);
            const matchesType = !type || requestType(requestItem) === type;
            const matchesStatus = !status || requestStatus(requestItem) === status;

            return matchesSearch && matchesType && matchesStatus;
        });
    }

    function renderRequests() {
        const filtered = filteredRequests();

        if (!filtered.length) {
            const hasFilters = Boolean(elements.search.value || elements.typeFilter.value || elements.statusFilter.value);
            elements.grid.innerHTML = '<div class="ri-empty">' +
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
        const selectedFiles = Array.from(elements.fileInput.files || []);
        elements.fileList.innerHTML = '';
        elements.filePickerLabel.textContent = selectedFiles.length
            ? 'Alterar documentos selecionados'
            : 'Selecionar documentos *';

        selectedFiles.forEach(function (file) {
            const item = document.createElement('li');
            item.textContent = file.name;
            elements.fileList.appendChild(item);
        });
    }

    function showToast(message) {
        elements.toast.textContent = message;
        elements.toast.classList.add('is-visible');

        window.setTimeout(function () {
            elements.toast.classList.remove('is-visible');
        }, 4500);
    }

    elements.tabs.forEach(function (tab) {
        tab.addEventListener('click', function () {
            setTab(tab.dataset.tab, true);
        });
    });

    [elements.search, elements.typeFilter, elements.statusFilter].forEach(function (filter) {
        filter.addEventListener('input', renderRequests);
        filter.addEventListener('change', renderRequests);
    });

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

    elements.form.addEventListener('reset', function () {
        window.setTimeout(function () {
            updateDemandFields();
            updateFileList();
        }, 0);
    });

    elements.form.addEventListener('submit', function () {
        elements.submit.disabled = true;
        elements.submit.textContent = 'Enviando...';
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
