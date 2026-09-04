(function () {
    'use strict';

    const config = window.demandRequestsConfig || {};
    const requests = Array.isArray(config.requests) ? config.requests : [];
    const selectedFiles = [];
    const maxFiles = 10;

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
        4: 'Pausada',
        5: 'Aprovada',
        6: 'Cancelada'
    };

    const elements = {
        tabs: Array.from(document.querySelectorAll('.dr-tab')),
        newView: document.getElementById('dr-new-view'),
        requestsView: document.getElementById('dr-requests-view'),
        analyticsView: document.getElementById('dr-analytics-view'),
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
        modal: document.getElementById('dr-modal'),
        modalContent: document.getElementById('dr-modal-content'),
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

    function apiUrl(path) {
        const url = new URL(config.apiRoot + (path || ''), window.location.origin);
        url.searchParams.set('area', config.area);
        return url;
    }

    function setRequestInAddress(requestId) {
        if (!window.history || !window.history.replaceState) {
            return;
        }
        const url = new URL(window.location.href);
        if (requestId) {
            url.searchParams.set('tab', 'minhas');
            url.searchParams.set('request', requestId);
        } else {
            url.searchParams.delete('request');
        }
        window.history.replaceState({}, '', url);
    }

    function setTab(tabName, updateAddress) {
        const activeTab = ['minhas', 'graficos'].includes(tabName)
            ? tabName
            : 'nova';

        elements.tabs.forEach(function (tab) {
            const isActive = tab.dataset.tab === activeTab;
            tab.classList.toggle('is-active', isActive);
            tab.setAttribute('aria-selected', String(isActive));
        });

        elements.newView.hidden = activeTab !== 'nova';
        elements.requestsView.hidden = activeTab !== 'minhas';
        elements.analyticsView.hidden = activeTab !== 'graficos';
        elements.summary.hidden = activeTab === 'graficos';

        if (activeTab === 'graficos') {
            document.dispatchEvent(new CustomEvent('demand-analytics:show'));
        }

        if (updateAddress && window.history && window.history.replaceState) {
            const url = new URL(window.location.href);
            url.searchParams.delete('sent');

            if (activeTab !== 'nova') {
                url.searchParams.set('tab', activeTab);
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
            [countStatus(1) + countStatus(4) + countStatus(5), 'Ativas'],
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

        if (status === '5') {
            return ['Situação', 'Aguardando definição do prazo'];
        }

        if (status === '4') {
            return ['Situação', 'Desenvolvimento pausado'];
        }

        if (status === '6') {
            return ['Resultado', 'Demanda cancelada'];
        }

        return ['Prazo', formatDate(requestItem.deadline, false)];
    }

    function cardClass(status) {
        return ' dr-request-card--status-' + status;
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

    function readonlyItem(label, value, fullWidth) {
        return '<div class="' + (fullWidth ? 'dr-readonly--full' : '') + '">' +
            '<dt>' + escapeHtml(label) + '</dt>' +
            '<dd>' + escapeHtml(value || 'Não informado') + '</dd>' +
        '</div>';
    }

    function renderAttachments(item) {
        if (!item.attachments || !item.attachments.length) {
            return '<p class="dr-modal__meta">Nenhum documento anexado.</p>';
        }
        return '<ul class="dr-attachment-list">' + item.attachments.map(function (attachment) {
            const url = apiUrl('/' + item.requestId + '/attachments/' + attachment.index);
            return '<li><a href="' + escapeHtml(url.toString()) + '">' +
                '<span>' + escapeHtml(attachment.name) + '</span><span>Baixar &darr;</span>' +
            '</a></li>';
        }).join('') + '</ul>';
    }

    function renderPauses(item) {
        if (!item.pauses || !item.pauses.length) {
            return '<p class="dr-modal__meta">A demanda não sofreu pausas.</p>';
        }
        return '<ul class="dr-pause-list">' + item.pauses.map(function (pause) {
            return '<li><strong>' + escapeHtml(formatDate(pause.initDate, true)) + '</strong>' +
                ' até ' + escapeHtml(formatDate(
                    pause.finalDate || pause.expectDate,
                    Boolean(pause.finalDate)
                )) +
                '<br>' + escapeHtml(pause.reason || 'Sem justificativa informada.') + '</li>';
        }).join('') + '</ul>';
    }

    function renderRequestDetail(item) {
        const type = requestType(item);
        const status = requestStatus(item);
        const structured = type !== 'erro';

        elements.modalContent.innerHTML =
            '<header class="dr-modal__header">' +
                '<div class="dr-request-card__badges">' +
                    '<span class="dr-badge dr-badge--type-' + type + '">' + escapeHtml(typeLabels[type]) + '</span>' +
                    '<span class="dr-badge dr-badge--status-' + status + '">' + escapeHtml(statusLabels[status]) + '</span>' +
                    '<span class="dr-badge' + urgencyClass(item.urgency) + '">' + escapeHtml(item.urgency || 'Não informada') + '</span>' +
                '</div>' +
                '<h2 id="dr-modal-title">' + escapeHtml(item.title) + '</h2>' +
                '<p class="dr-modal__meta">Solicitação #' + escapeHtml(item.requestId) +
                    ' · ' + escapeHtml(item.requesterName) +
                    ' · ' + escapeHtml(formatDate(item.requestDate, true)) + '</p>' +
            '</header>' +
            '<div class="dr-modal__grid">' +
                '<section class="dr-detail-panel">' +
                    '<h3>Dados da solicitação</h3>' +
                    '<dl class="dr-readonly-grid">' +
                        readonlyItem('Título', item.title, true) +
                        readonlyItem('Descrição inicial / objetivo', item.initialDescription, true) +
                        (structured ? readonlyItem('Premissas', item.assumptions, true) : '') +
                        (structured ? readonlyItem('Problemas atuais', item.actualProblems, true) : '') +
                        (structured ? readonlyItem('Ganhos esperados', item.benefits, true) : '') +
                        readonlyItem('Tipo', typeLabels[type]) +
                        readonlyItem('Urgência', item.urgency) +
                    '</dl>' +
                '</section>' +
                '<section class="dr-detail-panel">' +
                    '<h3>Andamento</h3>' +
                    '<dl class="dr-readonly-grid">' +
                        readonlyItem('Status', statusLabels[status]) +
                        readonlyItem('Responsável', item.responsibleName) +
                        readonlyItem('Data de início', formatDate(item.startDate, false)) +
                        readonlyItem('Prazo', formatDate(item.deadline, false)) +
                        readonlyItem('Data de encerramento', formatDate(item.finalDate, true)) +
                        readonlyItem('Reprogramações', String(item.reprogs || 0)) +
                        (status === '3' ? readonlyItem('Motivo da recusa', item.deniedText, true) : '') +
                        (status === '6' ? readonlyItem('Motivo do cancelamento', item.deniedText, true) : '') +
                    '</dl>' +
                '</section>' +
                '<section class="dr-detail-panel dr-detail-panel--full">' +
                    '<h3>Documentos</h3>' + renderAttachments(item) +
                '</section>' +
                '<section class="dr-detail-panel dr-detail-panel--full">' +
                    '<h3>Histórico de pausas</h3>' + renderPauses(item) +
                '</section>' +
            '</div>';
    }

    function closeModal(updateAddress) {
        elements.modal.classList.remove('is-open');
        elements.modal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('dr-modal-open');
        if (updateAddress !== false) {
            setRequestInAddress(null);
        }
    }

    async function openRequestDetail(requestId, updateAddress) {
        elements.modal.classList.add('is-open');
        elements.modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('dr-modal-open');
        elements.modalContent.innerHTML = '<div class="dr-modal-loading">Carregando solicitação...</div>';
        if (updateAddress !== false) {
            setRequestInAddress(requestId);
        }

        try {
            const response = await fetch(apiUrl('/' + requestId), {
                credentials: 'same-origin'
            });
            const payload = await response.json().catch(function () { return {}; });
            if (!response.ok) {
                throw new Error(payload.error || 'Não foi possível carregar a solicitação.');
            }
            renderRequestDetail(payload);
        } catch (error) {
            elements.modalContent.innerHTML = '<div class="dr-modal-loading">' +
                escapeHtml(error.message || 'Não foi possível carregar a solicitação.') +
            '</div>';
        }
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
        elements.fileList.innerHTML = '';
        elements.filePickerLabel.textContent = selectedFiles.length
            ? 'Adicionar mais documentos'
            : 'Selecionar documentos *';

        selectedFiles.forEach(function (file, index) {
            const item = document.createElement('li');
            const name = document.createElement('span');
            const remove = document.createElement('button');
            name.textContent = file.name;
            remove.type = 'button';
            remove.className = 'dr-file-list__remove';
            remove.dataset.fileIndex = String(index);
            remove.textContent = 'Remover';
            remove.setAttribute('aria-label', 'Remover ' + file.name);
            item.appendChild(name);
            item.appendChild(remove);
            elements.fileList.appendChild(item);
        });
    }

    function addSelectedFiles() {
        const newFiles = Array.from(elements.fileInput.files || []);
        elements.fileInput.value = '';
        if (!newFiles.length) return;
        const uniqueFiles = newFiles.filter(function (file, index) {
            const alreadySelected = selectedFiles.some(function (selected) {
                return selected.name === file.name
                    && selected.size === file.size
                    && selected.lastModified === file.lastModified;
            });
            const repeatedInSelection = newFiles.slice(0, index).some(function (selected) {
                return selected.name === file.name
                    && selected.size === file.size
                    && selected.lastModified === file.lastModified;
            });
            return !alreadySelected && !repeatedInSelection;
        });
        if (selectedFiles.length + uniqueFiles.length > maxFiles) {
            setFormError('Envie no máximo ' + maxFiles + ' documentos por solicitação.');
            return;
        }

        uniqueFiles.forEach(function (file) {
            selectedFiles.push(file);
        });
        setFormError('');
        updateFileList();
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
        if (!selectedFiles.length) {
            setFormError('Adicione pelo menos um documento à solicitação.');
            return;
        }
        setSubmitting(true);
        let errorMessage = 'Não foi possível enviar a solicitação. Tente novamente.';

        try {
            const formData = new FormData(elements.form);
            formData.delete('docs');
            selectedFiles.forEach(function (file) {
                formData.append('docs', file, file.name);
            });
            const response = await fetch(elements.form.action, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
                headers: {
                    'X-CSRF-Token': config.csrfToken
                }
            });

            if (response.redirected && new URL(response.url).pathname.includes('/login')) {
                window.location.assign(response.url);
                return;
            }

            const payload = await response.json().catch(function () { return {}; });
            if (!response.ok) {
                errorMessage = payload.error || (
                    response.status === 400
                        ? 'Revise os campos obrigatórios e tente novamente.'
                        : 'Não foi possível enviar a solicitação. Tente novamente.'
                );
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

    document.querySelectorAll('[data-close-modal]').forEach(function (control) {
        control.addEventListener('click', function () {
            closeModal(true);
        });
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && elements.modal.classList.contains('is-open')) {
            closeModal(true);
        }
    });

    elements.demandType.addEventListener('change', updateDemandFields);
    elements.fileInput.addEventListener('change', addSelectedFiles);
    elements.fileList.addEventListener('click', function (event) {
        const remove = event.target.closest('[data-file-index]');
        if (!remove) return;
        selectedFiles.splice(Number(remove.dataset.fileIndex), 1);
        setFormError('');
        updateFileList();
    });
    elements.form.addEventListener('submit', submitRequest);
    elements.form.addEventListener('reset', function () {
        window.setTimeout(function () {
            selectedFiles.splice(0, selectedFiles.length);
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

    if (config.initialRequestId) {
        setTab('minhas', false);
        openRequestDetail(config.initialRequestId, false);
    }
}());

// V2