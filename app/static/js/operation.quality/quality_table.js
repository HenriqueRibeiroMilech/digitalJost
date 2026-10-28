(function () {
    'use strict';
    const root = document.getElementById('qsb-control');
    const createForm = document.getElementById('qsb-table-form');
    const editForm = document.getElementById('qsb-edit-form');
    const csrf = root.dataset.csrfToken;
    const grid = document.getElementById('qsb-table-scroll');
    const table = grid.querySelector('table');
    const body = document.getElementById('qsb-table-entries');
    const topScroll = document.getElementById('qsb-top-scroll');
    const columns = Array.from(table.querySelectorAll('[data-column]'), function (cell) {
        return { key: cell.dataset.column, label: cell.dataset.label, group: cell.dataset.group };
    });
    const sections = Array.from(table.querySelectorAll('[data-qsb-section]'));
    const sectionButtons = Array.from(root.querySelectorAll('[data-qsb-go]'));
    const campinasCenters = Array.from(document.getElementById('qsb-campinas-centers').options, function (item) { return item.value; });
    const descriptions = new Map();
    const records = new Map();
    const dialog = document.getElementById('qsb-record-dialog');
    const content = document.getElementById('qsb-record-content');
    const recordError = document.getElementById('qsb-record-error');
    const loading = document.getElementById('qsb-record-loading');
    const viewActions = document.getElementById('qsb-view-actions');
    const editActions = document.getElementById('qsb-edit-actions');
    const deleteConfirm = document.getElementById('qsb-delete-confirm');
    const editButton = document.getElementById('qsb-edit-record');
    const deleteButton = document.getElementById('qsb-delete-record');
    let activeRecord = null;
    let detailSequence = 0;
    let editing = false;
    let recordBusy = false;
    let skipTopScroll = false;
    let skipGridScroll = false;

    function node(tag, className, value) {
        const element = document.createElement(tag);
        if (className) { element.className = className; }
        if (value !== undefined && value !== null) { element.textContent = String(value); }
        return element;
    }
    function showMessage(element, message) { element.textContent = message; element.hidden = !message; }
    function announce(message) { showMessage(document.getElementById('qsb-page-status'), message); }
    function normalize(value) { return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').toLocaleLowerCase('pt-BR'); }
    function recordUrl(id) { return root.dataset.apiRoot + '/' + encodeURIComponent(id); }
    function newSubmissionKey() {
        if (crypto.randomUUID) { return crypto.randomUUID(); }
        const bytes = new Uint8Array(16); crypto.getRandomValues(bytes);
        bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
        const hex = Array.from(bytes, function (value) { return value.toString(16).padStart(2, '0'); }).join('');
        return hex.slice(0, 8) + '-' + hex.slice(8, 12) + '-' + hex.slice(12, 16) + '-' + hex.slice(16, 20) + '-' + hex.slice(20);
    }
    function setRecordBusy(value) {
        recordBusy = value; dialog.setAttribute('aria-busy', String(value));
        dialog.querySelectorAll('[data-close-record], #qsb-cancel-edit, #qsb-cancel-delete, #qsb-edit-record, #qsb-delete-record').forEach(function (button) { button.disabled = value; });
    }
    async function requestJSON(url, options) {
        const settings = options || {};
        settings.headers = Object.assign({ Accept: 'application/json' }, settings.headers || {});
        let response;
        try { response = await fetch(url, settings); }
        catch (error) { throw new Error('Não foi possível confirmar a resposta do sistema. Os dados foram preservados; confira o registro antes de reenviar.'); }
        if (response.redirected) { throw new Error('Sua sessão expirou. Atualize a página para entrar novamente.'); }
        if (response.status === 204) { return null; }
        let data;
        try { data = await response.json(); }
        catch (error) {
            if (response.ok) { throw new Error('Resposta inesperada do sistema. Atualize a página para conferir o registro.'); }
            data = {};
        }
        if (!response.ok) {
            const error = new Error(data.error || (response.status === 403 ? 'Você não tem permissão para esta ação.' : 'Não foi possível concluir a operação.'));
            error.field = data.field;
            error.status = response.status;
            throw error;
        }
        return data;
    }
    async function lookup(key, value) {
        const url = new URL(root.dataset.lookupUrl, window.location.origin);
        url.searchParams.set(key, value);
        return requestJSON(url);
    }
    function fillOptions(list, values) {
        list.replaceChildren();
        values.forEach(function (value) { const option = node('option'); option.value = value; list.appendChild(option); });
    }
    function displayValue(key, value) {
        if (key === 'unit') { return Number(value) === 1 ? 'Campinas' : 'Caxias do Sul'; }
        if (key === 'repeat') { return value === true || value === 1 || value === '1' ? 'Sim' : 'Não'; }
        if (key === 'publish_qsb') { return value === true || value === 1 || value === '1' ? 'Na pirâmide' : 'Só no controle'; }
        if (value === null || value === undefined || value === '') { return 'Não informado'; }
        if (key === 'openDate') { return String(value).slice(0, 10).split('-').reverse().join('/'); }
        if (key === 'stop_time') { return String(value).slice(0, 5); }
        if (key === 'stop_minutes') { return Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 2 }); }
        if (key === 'shift') { return String(value).split(',').map(function (shift) { return shift === 'NA' ? 'Não aplicável' : 'Turno ' + shift; }).join(', '); }
        if (key === 'deleted_at') { return value ? 'Excluída' : 'Ativa'; }
        return String(value);
    }
    function photoLink(photo, category) {
        const link = node('a');
        link.href = photo.url;
        link.target = '_blank';
        link.rel = 'noopener';
        link.title = photo.label;
        const image = node('img');
        image.src = photo.url;
        image.alt = 'Imagem ' + category.toUpperCase() + ': ' + photo.label;
        image.loading = 'lazy';
        link.append(image, node('span', '', photo.label));
        return link;
    }
    document.addEventListener('error', function (event) {
        if (event.target instanceof HTMLImageElement && event.target.closest('.qsb-saved-photos, .qsb-record-gallery, .qsb-file-previews, .qsb-existing-images')) {
            event.target.hidden = true;
        }
    }, true);

    function scrollToField(element, smooth) {
        const pinnedWidth = table.querySelector('.qsb-pinned').getBoundingClientRect().width;
        const left = element.getBoundingClientRect().left - grid.getBoundingClientRect().left + grid.scrollLeft - pinnedWidth;
        const animate = smooth && !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        grid.scrollTo({ left: Math.max(0, left), behavior: animate ? 'smooth' : 'auto' });
    }
    function updateCurrentSection() {
        const pinnedWidth = table.querySelector('.qsb-pinned').getBoundingClientRect().width;
        let current = sections[0].dataset.qsbSection;
        sections.forEach(function (section) {
            if (section.getBoundingClientRect().left - grid.getBoundingClientRect().left <= pinnedWidth + 20) { current = section.dataset.qsbSection; }
        });
        if (grid.scrollLeft >= grid.scrollWidth - grid.clientWidth - 2) { current = sections[sections.length - 1].dataset.qsbSection; }
        sectionButtons.forEach(function (button) {
            if (button.dataset.qsbGo === current) { button.setAttribute('aria-current', 'true'); }
            else { button.removeAttribute('aria-current'); }
        });
    }
    sectionButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            scrollToField(sections.find(function (section) { return section.dataset.qsbSection === button.dataset.qsbGo; }), true);
            grid.scrollTop = 0;
        });
    });
    topScroll.addEventListener('scroll', function () {
        if (skipTopScroll) { skipTopScroll = false; return; }
        if (Math.abs(grid.scrollLeft - topScroll.scrollLeft) > 1) { skipGridScroll = true; grid.scrollLeft = topScroll.scrollLeft; }
    }, { passive: true });
    grid.addEventListener('scroll', function () {
        if (skipGridScroll) { skipGridScroll = false; }
        else if (Math.abs(topScroll.scrollLeft - grid.scrollLeft) > 1) { skipTopScroll = true; topScroll.scrollLeft = grid.scrollLeft; }
        updateCurrentSection();
    }, { passive: true });
    function resizeScroll() {
        document.getElementById('qsb-top-scroll-width').style.width = (grid.scrollWidth + topScroll.clientWidth - grid.clientWidth) + 'px';
        updateCurrentSection();
    }
    new ResizeObserver(resizeScroll).observe(grid);
    resizeScroll();

    function bindForm(form, isCreate) {
        const unit = form.querySelector('[data-unit]');
        const select = form.querySelector('[data-location-select]');
        const freeLocation = form.querySelector('[data-location-free]');
        const workcenter = form.querySelector('[data-workcenter]');
        const centerOptions = form.querySelector('[data-workcenters]');
        const caxiasCenters = Array.from(centerOptions.options, function (item) { return item.value; });
        const product = form.querySelector('[data-product]');
        const productOptions = form.querySelector('[data-products]');
        const description = form.querySelector('[data-product-description]');
        const formError = form.querySelector('[data-form-error]');
        const stopFields = Array.from(form.querySelectorAll('[data-stop-field]'));
        const shifts = ['turno1', 'turno2', 'turno3', 'NA'].map(function (name) { return form.elements.namedItem(name); });
        const buttons = Array.from(document.querySelectorAll('[form="' + form.id + '"][data-qsb-submit]')).concat(Array.from(form.querySelectorAll('[data-qsb-submit]')));
        const labels = buttons.map(function (button) { return button.textContent.trim(); });
        const previews = { nok: [], ok: [] };
        let legacy = false;
        let initializing = false;
        let pending = false;
        let disabledStates = [];
        let centerTimer;
        let productTimer;
        let centerVersion = 0;
        let productVersion = 0;
        let invalidPending = false;
        let initialValues = '';

        function captureValues() {
            return JSON.stringify(Array.from(new FormData(form).entries(), function (entry) {
                return [entry[0], entry[1] instanceof File ? entry[1].name + ':' + entry[1].size : entry[1]];
            }));
        }
        function setUnit(location) {
            const caxias = unit.value === '0';
            select.disabled = !caxias;
            select.hidden = !caxias;
            freeLocation.disabled = caxias;
            freeLocation.hidden = caxias;
            const add = form.querySelector('[data-create-location]');
            if (add) { add.hidden = !caxias; }
            if (location !== undefined) {
                if (caxias && location && !Array.from(select.options).some(function (option) { return option.value === location; })) {
                    const option = node('option', '', location); option.value = location; option.dataset.legacy = 'true'; select.appendChild(option);
                }
                select.value = caxias ? location : '';
                freeLocation.value = caxias ? '' : location;
            }
            fillOptions(centerOptions, caxias ? caxiasCenters : campinasCenters);
            const label = form.querySelector('label[for="' + select.id + '"], label[for="' + freeLocation.id + '"]');
            if (label) { label.htmlFor = caxias ? select.id : freeLocation.id; }
        }
        function updateValidity() {
            const hasStop = stopFields.some(function (field) { return field.value.trim() !== ''; });
            stopFields.forEach(function (field) { field.required = !legacy || hasStop; });
            shifts[0].setCustomValidity(shifts.some(function (shift) { return shift.checked; }) ? '' : 'Selecione um turno ou Não aplicável.');
            if (isCreate) {
                const required = Array.from(form.querySelectorAll('[required]')).filter(function (field) { return !field.disabled; });
                const total = required.length + 1;
                const complete = required.filter(function (field) { return field.validity.valid; }).length + (shifts[0].validity.valid ? 1 : 0);
                const progress = document.getElementById('qsb-form-progress');
                progress.max = total; progress.value = complete;
                document.getElementById('qsb-form-progress-text').textContent = complete + ' de ' + total + ' obrigatórios preenchidos';
            }
        }
        function showError(error) {
            showMessage(formError, error.message || 'Não foi possível salvar. Os dados foram preservados.');
            if (error.field) {
                const fields = Array.from(form.elements).filter(function (field) { return field.name === error.field && !field.disabled; });
                if (fields.length) { revealInvalid(fields[0]); }
            }
        }
        function revealInvalid(field) {
            field.classList.add('qsb-field-invalid');
            if (isCreate) { grid.scrollTop = 0; scrollToField(field.closest('td'), false); }
            else { field.closest('.qsb-modal-field').scrollIntoView({ block: 'nearest' }); }
            field.focus({ preventScroll: true });
        }
        function resetProduct() {
            clearTimeout(productTimer); productVersion += 1;
            product.value = ''; productOptions.replaceChildren(); description.textContent = 'Aguardando código do produto.';
        }
        async function productDescription() {
            const version = ++productVersion;
            const code = product.value.trim();
            description.textContent = code ? 'Consultando descrição...' : 'Aguardando código do produto.';
            if (!code) { return; }
            try {
                if (!descriptions.has(code)) { const values = await lookup('searchProd', code); descriptions.set(code, values[0] || 'Descrição não encontrada.'); }
                if (version === productVersion) { description.textContent = descriptions.get(code); }
            } catch (error) {
                if (version === productVersion) { description.textContent = 'Descrição indisponível. Confira o código informado.'; }
            }
        }
        unit.addEventListener('change', function () {
            clearTimeout(centerTimer); centerVersion += 1; workcenter.value = '';
            setUnit(''); resetProduct(); updateValidity();
        });
        workcenter.addEventListener('input', function () {
            clearTimeout(centerTimer); const version = ++centerVersion; resetProduct(); updateValidity();
            if (!workcenter.value.trim()) { return; }
            centerTimer = setTimeout(async function () {
                try { const values = await lookup('searchCt', workcenter.value); if (version === centerVersion) { fillOptions(productOptions, values); } }
                catch (error) { if (version === centerVersion) { description.textContent = 'Sugestões indisponíveis. Informe o código do produto.'; } }
            }, 300);
        });
        product.addEventListener('input', function () { clearTimeout(productTimer); productVersion += 1; productTimer = setTimeout(productDescription, 300); });
        shifts.forEach(function (shift) {
            shift.addEventListener('change', function () {
                if (shift.checked) {
                    if (shift.name === 'NA') { shifts.slice(0, 3).forEach(function (other) { other.checked = false; }); }
                    else { shifts[3].checked = false; }
                }
                updateValidity();
            });
        });
        function renderFiles(category) {
            const input = form.querySelector('[data-files="' + category + '"]');
            const list = form.querySelector('[data-file-previews="' + category + '"]');
            previews[category].forEach(function (url) { URL.revokeObjectURL(url); }); previews[category] = []; list.replaceChildren();
            Array.from(input.files).forEach(function (file) {
                const item = node('li');
                if (file.type.startsWith('image/')) {
                    const image = node('img'); const url = URL.createObjectURL(file);
                    previews[category].push(url); image.src = url; image.alt = 'Prévia de ' + file.name; item.appendChild(image);
                }
                const name = node('span', '', file.name); name.title = file.name; item.appendChild(name); list.appendChild(item);
            });
            form.querySelector('[data-file-count="' + category + '"]').textContent = input.files.length ? input.files.length + ' imagem(ns) selecionada(s).' : 'Nenhuma imagem selecionada.';
        }
        function validateFiles() {
            const inputs = Array.from(form.querySelectorAll('[data-files]'));
            const files = inputs.flatMap(function (input) { input.setCustomValidity(''); return Array.from(input.files); });
            let message = '';
            if (files.some(function (file) { return file.size === 0 || file.size > 10 * 1024 * 1024; })) { message = 'Cada imagem deve ter conteúdo e no máximo 10 MB.'; }
            else if (files.length > 20 || files.reduce(function (total, file) { return total + file.size; }, 0) > 40 * 1024 * 1024) { message = 'Envie até 20 imagens, somando no máximo 40 MB.'; }
            if (message) { inputs.find(function (input) { return input.files.length; }).setCustomValidity(message); }
        }
        ['nok', 'ok'].forEach(function (category) {
            form.querySelector('[data-files="' + category + '"]').addEventListener('change', function () { renderFiles(category); validateFiles(); });
        });
        form.addEventListener('input', function (event) {
            if (event.target.validity && event.target.validity.valid) { event.target.classList.remove('qsb-field-invalid'); }
            updateValidity();
        });
        form.addEventListener('change', updateValidity);
        form.addEventListener('invalid', function (event) {
            event.target.classList.add('qsb-field-invalid');
            if (invalidPending) { return; }
            invalidPending = true;
            const label = event.target.getAttribute('aria-label') || 'Turnos da ocorrência';
            showMessage(formError, event.target.validationMessage || 'Preencha: ' + label + '.');
            revealInvalid(event.target);
            setTimeout(function () { invalidPending = false; }, 0);
        }, true);
        function resetState() {
            clearTimeout(centerTimer); centerVersion += 1;
            form.querySelectorAll('option[data-legacy]').forEach(function (option) { option.remove(); });
            setUnit(''); resetProduct(); legacy = false;
            ['nok', 'ok'].forEach(function (category) {
                renderFiles(category); form.querySelector('[data-existing-images="' + category + '"]').replaceChildren();
            });
            form.querySelectorAll('.qsb-field-invalid').forEach(function (field) { field.classList.remove('qsb-field-invalid'); });
            showMessage(formError, ''); validateFiles(); updateValidity();
            if (isCreate) {
                form.elements.namedItem('submission_key').value = newSubmissionKey();
                grid.scrollTo({ left: 0, top: 0 });
            }
            initialValues = captureValues();
        }
        form.addEventListener('reset', function () { if (!initializing) { setTimeout(resetState, 0); } });
        function setBusy(value) {
            if (value && !pending) {
                disabledStates = Array.from(form.elements, function (field) { return [field, field.disabled]; });
                disabledStates.forEach(function (item) { item[0].disabled = true; });
            } else if (!value && pending) { disabledStates.forEach(function (item) { item[0].disabled = item[1]; }); }
            pending = value;
            buttons.forEach(function (button, index) { button.disabled = value; button.textContent = value ? 'Salvando...' : labels[index]; });
            document.querySelectorAll('[form="' + form.id + '"][type="reset"]').forEach(function (button) { button.disabled = value; });
        }
        function load(entry) {
            initializing = true; form.reset(); initializing = false; resetState();
            legacy = entry.is_legacy;
            const mapping = {
                unidade: entry.unit, op_local_ocorr: entry.type, ct: entry.workCenter,
                id_mater: entry.prodCode, op_familia: entry.prodFamily, op_problema: entry.description,
                op_reincidente: entry.repeat ? '1' : '0', op_cont_1: entry.text1,
                op_cont_2: entry.text2, op_cont_3: entry.text3, op_date: entry.openDate,
                stop_time: entry.stop_time, stop_reason: entry.stop_reason,
                stop_minutes: entry.stop_minutes, stop_count: entry.stop_count,
                location_detail: entry.location_detail, publish_qsb: entry.publish_qsb ? '1' : '0',
                revision: entry.revision,
            };
            Object.entries(mapping).forEach(function (item) {
                const field = form.elements.namedItem(item[0]);
                if (field instanceof HTMLSelectElement && item[1] && !Array.from(field.options).some(function (option) { return option.value === String(item[1]); })) {
                    const option = node('option', '', item[1]); option.value = item[1]; option.dataset.legacy = 'true'; field.appendChild(option);
                }
                if (field) { field.value = item[1] === null || item[1] === undefined ? '' : item[1]; }
            });
            setUnit(entry.typeDesc);
            shifts.forEach(function (shift) { shift.checked = entry.shift.split(',').includes(shift.value); });
            ['nok', 'ok'].forEach(function (category) {
                const holder = form.querySelector('[data-existing-images="' + category + '"]');
                entry['images_' + category].forEach(function (photo) {
                    const row = node('div', 'qsb-existing-image'); row.appendChild(photoLink(photo, category));
                    const label = node('label'); const remove = node('input'); remove.type = 'checkbox'; remove.name = 'remove_' + category; remove.value = photo.name;
                    label.append(remove, node('span', '', 'Remover do registro')); row.appendChild(label); holder.appendChild(row);
                });
            });
            document.getElementById('qsb-edit-legacy').hidden = !legacy;
            updateValidity(); productDescription(); initialValues = captureValues();
        }
        form.addEventListener('submit', function (event) {
            event.preventDefault(); if (pending) { return; }
            updateValidity(); validateFiles();
            if (!form.reportValidity()) { return; }
            saveForm(form, controller, isCreate);
        });
        setUnit(select.value || freeLocation.value); updateValidity(); initialValues = captureValues();
        const controller = {
            form: form, load: load, setBusy: setBusy, showError: showError,
            dirty: function () { return captureValues() !== initialValues; },
            addLocation: function (location, selected) {
                if (!Array.from(select.options).some(function (option) { return option.value === location; })) {
                    const option = node('option', '', location); option.value = location; select.appendChild(option);
                    Array.from(select.options).slice(1).sort(function (a, b) { return a.value.localeCompare(b.value, 'pt-BR'); }).forEach(function (option) { select.appendChild(option); });
                }
                if (selected) { select.value = location; updateValidity(); }
            },
            refresh: function () { setUnit(unit.value === '0' ? select.value : freeLocation.value); ['nok', 'ok'].forEach(renderFiles); updateValidity(); },
            release: function () { clearTimeout(centerTimer); clearTimeout(productTimer); centerVersion += 1; productVersion += 1; Object.values(previews).flat().forEach(function (url) { URL.revokeObjectURL(url); }); previews.nok = []; previews.ok = []; },
        };
        return controller;
    }

    const createController = bindForm(createForm, true);
    const editController = bindForm(editForm, false);
    const filterFrom = document.getElementById('qsb-filter-from');
    const filterUntil = document.getElementById('qsb-filter-until');
    const filterUnit = document.getElementById('qsb-filter-unit');
    const filterPublish = document.getElementById('qsb-filter-publish');
    const filterSearch = document.getElementById('qsb-filter-search');
    body.querySelectorAll('[data-entry-id]').forEach(function (row) { records.set(row.dataset.entryId, { row: row, text: normalize(row.textContent) }); });
    function filterRows() {
        const search = normalize(filterSearch.value.trim());
        let count = 0; let minutes = 0; let stops = 0;
        records.forEach(function (item) {
            const row = item.row;
            row.hidden = Boolean(
                (filterFrom.value && row.dataset.date < filterFrom.value) ||
                (filterUntil.value && row.dataset.date > filterUntil.value) ||
                (filterUnit.value && row.dataset.unit !== filterUnit.value) ||
                (filterPublish.value && row.dataset.publish !== filterPublish.value) ||
                (search && !item.text.includes(search))
            );
            if (!row.hidden) { count += 1; minutes += Number(row.dataset.minutes || 0); stops += Number(row.dataset.count || 0); }
        });
        document.getElementById('qsb-table-empty').hidden = count !== 0;
        document.getElementById('qsb-table-count').textContent = count + ' de ' + records.size + ' ocorrência(s)';
        document.getElementById('qsb-filter-totals').textContent = 'Tempo informado: ' + minutes.toLocaleString('pt-BR', { maximumFractionDigits: 2 }) + ' min · Paradas informadas: ' + stops.toLocaleString('pt-BR');
    }
    const filters = [filterFrom, filterUntil, filterUnit, filterPublish, filterSearch];
    filters.forEach(function (filter) { filter.addEventListener('input', filterRows); });
    document.getElementById('qsb-clear-filters').addEventListener('click', function () { filters.forEach(function (filter) { filter.value = ''; }); filterRows(); });
    filterRows();

    function renderRow(entry) {
        const row = node('tr'); row.dataset.entryId = entry.id; row.dataset.date = entry.date_iso;
        row.dataset.unit = entry.unit; row.dataset.publish = entry.publish_qsb ? '1' : '0';
        row.dataset.minutes = entry.stop_minutes === null ? '' : entry.stop_minutes;
        row.dataset.count = entry.stop_count === null ? '' : entry.stop_count;
        const pinned = node('th', 'qsb-pinned'); pinned.scope = 'row'; pinned.appendChild(node('span', 'qsb-record-id', '#' + entry.id));
        const view = node('button', 'qsb-button qsb-button-secondary qsb-edit-link', 'Visualizar'); view.type = 'button'; view.dataset.viewRecord = entry.id; pinned.appendChild(view);
        if (entry.permissions.edit) { const edit = node('button', 'qsb-description-button qsb-row-edit', 'Editar'); edit.type = 'button'; edit.dataset.editRecord = entry.id; pinned.appendChild(edit); }
        row.appendChild(pinned);
        columns.forEach(function (column) {
            const cell = node('td');
            if (column.key === 'imgNOK' || column.key === 'imgOK') {
                const category = column.key === 'imgNOK' ? 'nok' : 'ok'; const list = node('ul', 'qsb-saved-photos');
                entry['images_' + category].forEach(function (photo) { const item = node('li'); item.appendChild(photoLink(photo, category)); list.appendChild(item); });
                if (!list.children.length) { list.appendChild(node('li', 'qsb-muted', 'Sem imagens')); }
                cell.appendChild(list);
            } else if (column.key === 'product_description') {
                cell.appendChild(node('span', 'qsb-description-value'));
                const button = node('button', 'qsb-description-button', 'Consultar descrição'); button.type = 'button'; button.dataset.productCode = entry.prodCode; cell.appendChild(button);
            } else if (column.key === 'repeat' || column.key === 'publish_qsb') {
                cell.appendChild(node('span', 'qsb-badge ' + (entry[column.key] ? 'qsb-badge-new' : 'qsb-badge-neutral'), displayValue(column.key, entry[column.key])));
            } else { cell.appendChild(node('div', 'qsb-cell-text', displayValue(column.key, entry[column.key]))); }
            row.appendChild(cell);
        });
        const previous = records.get(entry.id);
        if (previous) { previous.row.replaceWith(row); }
        else { body.insertBefore(row, body.querySelector('.qsb-history-divider').nextSibling); }
        records.set(entry.id, { row: row, text: normalize(row.textContent) }); filterRows(); resizeScroll();
    }
    function renderDetail(entry) {
        content.replaceChildren();
        const published = node('span', 'qsb-badge ' + (entry.publish_qsb ? 'qsb-badge-new' : 'qsb-badge-neutral'), displayValue('publish_qsb', entry.publish_qsb)); content.appendChild(published);
        sections.forEach(function (heading) {
            const group = heading.dataset.qsbSection;
            const section = node('section', 'qsb-record-section'); section.appendChild(node('h3', '', heading.textContent));
            if (group === 'images') {
                ['nok', 'ok'].forEach(function (category) {
                    section.appendChild(node('h4', '', 'Imagens ' + category.toUpperCase()));
                    const gallery = node('div', 'qsb-record-gallery');
                    entry['images_' + category].forEach(function (photo) { gallery.appendChild(photoLink(photo, category)); });
                    if (!gallery.children.length) { gallery.appendChild(node('span', 'qsb-muted', 'Sem imagens')); }
                    section.appendChild(gallery);
                });
            } else {
                const list = node('dl', 'qsb-record-values');
                columns.filter(function (column) { return column.group === group; }).forEach(function (column) {
                    const item = node('div'); item.appendChild(node('dt', '', column.label));
                    const value = node('dd');
                    if (column.key === 'product_description') {
                        value.appendChild(node('span', 'qsb-description-value'));
                        const button = node('button', 'qsb-description-button', 'Consultar descrição'); button.type = 'button'; button.dataset.productCode = entry.prodCode; value.appendChild(button);
                    } else { value.textContent = displayValue(column.key, entry[column.key]); }
                    item.appendChild(value); list.appendChild(item);
                });
                section.appendChild(list);
                if (group === 'stop' && entry.is_legacy) { section.appendChild(node('p', 'qsb-legacy-note', 'Dados de parada não informados no registro antigo.')); }
            }
            content.appendChild(section);
        });
        const historySection = node('section', 'qsb-record-section'); historySection.appendChild(node('h3', '', 'Histórico de alterações'));
        const events = node('ol', 'qsb-record-history');
        (entry.history || []).forEach(function (event) {
            const item = node('li'); const details = node('details');
            const action = { create: 'Cadastro', update: 'Alteração', delete: 'Exclusão' }[event.action] || event.action;
            details.appendChild(node('summary', '', action + ' · Usuário ' + event.actor_id + ' · ' + new Date(event.occurred_at).toLocaleString('pt-BR')));
            const changes = node('ul');
            event.changes.forEach(function (change) {
                const column = columns.find(function (field) { return field.key === change.field; });
                const label = column ? column.label : change.field;
                changes.appendChild(node('li', '', label + ': ' + displayValue(change.field, change.before) + ' → ' + displayValue(change.field, change.after)));
            });
            details.appendChild(changes); item.appendChild(details); events.appendChild(item);
        });
        if (entry.historyUnavailable) { historySection.appendChild(node('p', 'qsb-muted', 'Histórico indisponível no momento. Reabra o registro para consultar.')); }
        else if (!events.children.length) { historySection.appendChild(node('p', 'qsb-muted', 'Nenhuma alteração registrada.')); }
        else { historySection.appendChild(events); }
        content.appendChild(historySection);
        document.getElementById('qsb-record-title').textContent = 'Ocorrência #' + entry.id;
        loading.hidden = true; content.hidden = false; editForm.hidden = true; editActions.hidden = true;
        deleteConfirm.hidden = true; viewActions.hidden = false; editing = false;
        editButton.hidden = !entry.permissions.edit; deleteButton.hidden = !entry.permissions.delete;
    }
    async function openRecord(id, startEditing) {
        const sequence = ++detailSequence; activeRecord = null; editing = false;
        content.hidden = true; editForm.hidden = true; editActions.hidden = true; viewActions.hidden = true; deleteConfirm.hidden = true;
        loading.hidden = false; showMessage(recordError, ''); document.getElementById('qsb-record-title').textContent = 'Ocorrência #' + id;
        if (!dialog.open) { dialog.showModal(); }
        try {
            const entry = await requestJSON(recordUrl(id));
            if (sequence !== detailSequence || !dialog.open) { return; }
            activeRecord = entry; renderDetail(entry);
            if (startEditing && entry.permissions.edit) { beginEdit(); }
        } catch (error) {
            if (sequence === detailSequence && dialog.open) { loading.hidden = true; showMessage(recordError, error.message); }
        }
    }
    function beginEdit() {
        if (!activeRecord || !activeRecord.permissions.edit || recordBusy) { return; }
        editController.load(activeRecord); editing = true; content.hidden = true; editForm.hidden = false;
        viewActions.hidden = true; editActions.hidden = false; deleteConfirm.hidden = true; showMessage(recordError, '');
        editForm.querySelector('[data-unit]').focus({ preventScroll: true }); editForm.scrollIntoView({ block: 'start' });
    }
    function closeRecord() {
        if (recordBusy) { return; }
        if (editing && editController.dirty() && !window.confirm('Descartar as alterações que ainda não foram salvas?')) { return; }
        dialog.close();
    }
    dialog.addEventListener('cancel', function (event) { event.preventDefault(); closeRecord(); });
    dialog.addEventListener('close', function () {
        detailSequence += 1; editController.release();
        const row = activeRecord && records.get(activeRecord.id);
        if (row) { row.row.querySelector('[data-view-record]').focus({ preventScroll: true }); }
    });
    dialog.querySelectorAll('[data-close-record]').forEach(function (button) { button.addEventListener('click', closeRecord); });
    editButton.addEventListener('click', beginEdit);
    document.getElementById('qsb-cancel-edit').addEventListener('click', function () {
        if (recordBusy) { return; }
        if (editController.dirty() && !window.confirm('Descartar as alterações que ainda não foram salvas?')) { return; }
        editController.release(); renderDetail(activeRecord); editButton.focus();
    });
    async function saveForm(form, controller, isCreate) {
        if (!isCreate && (!activeRecord || recordBusy)) { return; }
        const data = new FormData(form);
        controller.setBusy(true); if (!isCreate) { setRecordBusy(true); }
        try {
            const entry = await requestJSON(isCreate ? root.dataset.apiRoot : recordUrl(activeRecord.id), {
                method: isCreate ? 'POST' : 'PATCH', headers: { 'X-CSRF-Token': csrf }, body: data,
            });
            renderRow(entry);
            if (isCreate) { form.reset(); announce('Ocorrência #' + entry.id + ' cadastrada. A primeira linha está pronta para um novo registro.'); }
            else {
                activeRecord = entry;
                try { activeRecord = await requestJSON(recordUrl(entry.id)); } catch (error) { activeRecord.historyUnavailable = true; }
                renderRow(activeRecord); renderDetail(activeRecord);
                const success = node('p', 'qsb-modal-success', 'Alterações salvas.'); success.setAttribute('role', 'status'); content.prepend(success);
                announce('Ocorrência #' + entry.id + ' atualizada.');
            }
        } catch (error) { controller.showError(error); }
        finally { controller.setBusy(false); if (!isCreate) { setRecordBusy(false); } }
    }
    deleteButton.addEventListener('click', function () {
        if (!activeRecord || !activeRecord.permissions.delete || recordBusy) { return; }
        deleteConfirm.hidden = false; viewActions.hidden = true;
        document.getElementById('qsb-cancel-delete').focus(); deleteConfirm.scrollIntoView({ block: 'nearest' });
    });
    document.getElementById('qsb-cancel-delete').addEventListener('click', function () { if (!recordBusy) { deleteConfirm.hidden = true; viewActions.hidden = false; deleteButton.focus(); } });
    document.getElementById('qsb-confirm-delete').addEventListener('click', async function () {
        if (!activeRecord || recordBusy || !activeRecord.permissions.delete) { return; }
        setRecordBusy(true); const button = this; button.disabled = true; showMessage(recordError, '');
        try {
            await requestJSON(recordUrl(activeRecord.id), { method: 'DELETE', headers: { 'X-CSRF-Token': csrf, 'Content-Type': 'application/json' }, body: JSON.stringify({ revision: activeRecord.revision }) });
            const item = records.get(activeRecord.id); if (item) { item.row.remove(); records.delete(activeRecord.id); }
            announce('Ocorrência #' + activeRecord.id + ' excluída do controle e da pirâmide.'); filterRows(); dialog.close();
            createForm.querySelector('[data-unit]').focus({ preventScroll: true });
        } catch (error) { showMessage(recordError, error.message); }
        finally { setRecordBusy(false); button.disabled = false; }
    });
    document.addEventListener('click', async function (event) {
        const view = event.target.closest('[data-view-record], [data-edit-record]');
        if (view) { openRecord(view.dataset.viewRecord || view.dataset.editRecord, Boolean(view.dataset.editRecord)); return; }
        const button = event.target.closest('[data-product-code]');
        if (!button || button.disabled) { return; }
        const code = button.dataset.productCode; const output = button.parentElement.querySelector('.qsb-description-value'); button.disabled = true; button.textContent = 'Consultando...';
        try {
            if (!descriptions.has(code)) { const values = await lookup('searchProd', code); descriptions.set(code, values[0] || 'Descrição não encontrada.'); }
            output.textContent = descriptions.get(code); button.hidden = true;
        } catch (error) { output.textContent = 'Consulta indisponível. '; button.textContent = 'Tentar novamente'; }
        finally {
            button.disabled = false;
            const row = button.closest('[data-entry-id]');
            const item = row && records.get(row.dataset.entryId);
            if (item && item.row === row) { item.text = normalize(row.textContent); filterRows(); }
        }
    });

    const locationDialog = document.getElementById('qsb-location-dialog');
    if (locationDialog) {
        const locationForm = document.getElementById('qsb-location-form');
        let locationController = null; let locationBusy = false;
        document.addEventListener('click', function (event) {
            const button = event.target.closest('[data-create-location]');
            if (!button) { return; }
            locationController = button.closest('form') === createForm ? createController : editController;
            locationForm.reset(); showMessage(document.getElementById('qsb-location-error'), ''); locationDialog.showModal(); document.getElementById('qsb-location-name').focus();
        });
        document.getElementById('qsb-close-location').addEventListener('click', function () { if (!locationBusy) { locationDialog.close(); } });
        locationDialog.addEventListener('cancel', function (event) { if (locationBusy) { event.preventDefault(); } });
        locationForm.addEventListener('submit', async function (event) {
            event.preventDefault(); if (locationBusy) { return; }
            locationBusy = true; const button = locationForm.querySelector('[type="submit"]'); button.disabled = true;
            try {
                const data = await requestJSON(root.dataset.locationUrl, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf }, body: JSON.stringify({ name: locationForm.elements.namedItem('name').value }) });
                [createController, editController].forEach(function (controller) { controller.addLocation(data.location, controller === locationController); });
                locationDialog.close();
            } catch (error) { showMessage(document.getElementById('qsb-location-error'), error.message); }
            finally { locationBusy = false; button.disabled = false; }
        });
    }
    window.addEventListener('pagehide', function (event) { if (!event.persisted) { createController.release(); editController.release(); } });
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) { createController.setBusy(false); editController.setBusy(false); setRecordBusy(false); }
        createController.refresh(); filterRows(); resizeScroll();
    });
}());
