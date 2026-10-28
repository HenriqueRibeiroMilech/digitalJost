(function () {
    'use strict';

    const form = document.getElementById('qsb-table-form');
    const unit = document.getElementById('unidade');
    const workcenter = document.getElementById('qsb-workcenter');
    const workcenters = document.getElementById('qsb-workcenters');
    const product = document.getElementById('qsb-product');
    const products = document.getElementById('qsb-products');
    const description = document.getElementById('qsb-product-description');
    const submitButtons = Array.from(document.querySelectorAll('[data-qsb-submit]'));
    const submitLabels = submitButtons.map(function (button) { return button.textContent.trim(); });
    const errorMessage = document.getElementById('qsb-form-error');
    const grid = document.getElementById('qsb-table-scroll');
    const table = grid.querySelector('table');
    const topScroll = document.getElementById('qsb-top-scroll');
    const sectionButtons = Array.from(document.querySelectorAll('[data-qsb-go]'));
    const sections = Array.from(table.querySelectorAll('[data-qsb-section]'));
    const caxiasCenters = Array.from(workcenters.options, function (option) { return option.value; });
    const campinasCenters = [
        'M101-Montagem Articulação De Onibus',
        'M102-Montagem Trava De Quinta Roda',
        'S101-Solda Robotizada Articulação De Onibus'
    ];
    const previewUrls = { nok: [], ok: [] };
    const descriptions = new Map();
    let centerTimer;
    let productTimer;
    let centerVersion = 0;
    let productVersion = 0;
    let submitting = false;
    let validationPending = false;
    let skipTopScroll = false;
    let skipGridScroll = false;

    removeNav();

    function fillOptions(list, values) {
        list.replaceChildren();
        values.forEach(function (value) {
            const option = document.createElement('option');
            option.value = String(value);
            list.appendChild(option);
        });
    }

    async function lookup(key, value) {
        const url = new URL(form.dataset.lookupUrl, window.location.origin);
        url.searchParams.set(key, String(value).replace(/'/g, ''));
        const response = await fetch(url, { method: 'POST' });
        if (!response.ok || response.redirected) { throw new Error('Consulta indisponível.'); }
        return response.json();
    }

    function updateProgress() {
        const fields = Array.from(form.querySelectorAll('[required]')).filter(function (field) { return !field.disabled; });
        const complete = fields.filter(function (field) { return field.validity.valid; }).length;
        const progress = document.getElementById('qsb-form-progress');
        progress.max = fields.length;
        progress.value = complete;
        document.getElementById('qsb-form-progress-text').textContent = complete + ' de ' + fields.length + ' obrigatórios preenchidos';
        if (complete === fields.length) { errorMessage.hidden = true; }
    }

    form.addEventListener('input', function (event) {
        if (event.target.validity && event.target.validity.valid) { event.target.classList.remove('qsb-field-invalid'); }
        updateProgress();
    });
    form.addEventListener('change', function () { setTimeout(updateProgress, 0); });
    document.addEventListener('DOMContentLoaded', updateProgress);
    new MutationObserver(updateProgress).observe(document.getElementById('op_local_info_select'), { childList: true });

    function resetProduct() {
        clearTimeout(productTimer);
        productVersion += 1;
        product.value = '';
        products.replaceChildren();
        description.textContent = 'Aguardando código do produto.';
    }

    function setWorkcenters() {
        fillOptions(workcenters, unit.value === '1' ? campinasCenters : caxiasCenters);
    }
    unit.addEventListener('change', function () {
        clearTimeout(centerTimer);
        centerVersion += 1;
        workcenter.value = '';
        setWorkcenters();
        resetProduct();
    });
    setWorkcenters();

    workcenter.addEventListener('input', function () {
        workcenter.value = workcenter.value.replace(/'/g, '');
        clearTimeout(centerTimer);
        const version = ++centerVersion;
        resetProduct();
        updateProgress();
        if (!workcenter.value.trim()) { return; }
        centerTimer = setTimeout(async function () {
            try {
                const values = await lookup('searchCt', workcenter.value);
                if (version === centerVersion) { fillOptions(products, values); }
            } catch (error) {
                if (version === centerVersion) { description.textContent = 'Sugestões indisponíveis. Informe o código do produto.'; }
            }
        }, 300);
    });

    product.addEventListener('input', function () {
        product.value = product.value.replace(/'/g, '');
        clearTimeout(productTimer);
        const version = ++productVersion;
        description.textContent = 'Aguardando código do produto.';
        if (!product.value.trim()) { return; }
        description.textContent = 'Consultando descrição...';
        productTimer = setTimeout(async function () {
            try {
                const values = await lookup('searchProd', product.value);
                if (version !== productVersion) { return; }
                description.textContent = values[0] || 'Descrição não encontrada para este código.';
            } catch (error) {
                if (version === productVersion) { description.textContent = 'Não foi possível consultar a descrição. Confira o código informado.'; }
            }
        }, 300);
    });

    function renderFiles(category) {
        const input = document.getElementById('qsb-files-' + category);
        const list = document.getElementById('qsb-files-' + category + '-list');
        previewUrls[category].forEach(function (url) { URL.revokeObjectURL(url); });
        previewUrls[category] = [];
        list.replaceChildren();
        Array.from(input.files).forEach(function (file) {
            const item = document.createElement('li');
            if (file.type.startsWith('image/')) {
                const preview = document.createElement('img');
                const url = URL.createObjectURL(file);
                previewUrls[category].push(url);
                preview.src = url;
                preview.alt = 'Prévia de ' + file.name;
                item.appendChild(preview);
            }
            const name = document.createElement('span');
            name.textContent = file.name;
            name.title = file.name;
            item.appendChild(name);
            list.appendChild(item);
        });
        document.getElementById('qsb-files-' + category + '-count').textContent = input.files.length
            ? input.files.length + ' imagem(ns) selecionada(s).'
            : 'Nenhuma imagem selecionada.';
    }
    ['nok', 'ok'].forEach(function (category) {
        document.getElementById('qsb-files-' + category).addEventListener('change', function () { renderFiles(category); });
    });
    window.addEventListener('pagehide', function (event) {
        if (!event.persisted) {
            Object.values(previewUrls).flat().forEach(function (url) { URL.revokeObjectURL(url); });
        }
    });
    document.querySelectorAll('.qsb-saved-photos img').forEach(function (image) {
        function recoverImage() {
            if (image.dataset.legacySrc) {
                const legacyUrl = image.dataset.legacySrc;
                delete image.dataset.legacySrc;
                image.closest('a').href = legacyUrl;
                image.src = legacyUrl;
            } else {
                image.hidden = true;
            }
        }
        image.addEventListener('error', recoverImage);
        if (image.complete && image.naturalWidth === 0) { recoverImage(); }
    });

    const shifts = Array.from(form.querySelectorAll('input[name="turno1"], input[name="turno2"], input[name="turno3"]'));
    const notApplicable = form.elements.namedItem('NA');
    notApplicable.addEventListener('change', function () {
        if (notApplicable.checked) { shifts.forEach(function (shift) { shift.checked = false; }); }
    });
    shifts.forEach(function (shift) {
        shift.addEventListener('change', function () {
            if (shift.checked) { notApplicable.checked = false; }
        });
    });

    function scrollToField(element) {
        const pinnedWidth = table.querySelector('.qsb-pinned').getBoundingClientRect().width;
        const left = element.getBoundingClientRect().left - grid.getBoundingClientRect().left + grid.scrollLeft - pinnedWidth;
        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        grid.scrollTo({ left: Math.max(0, left), behavior: reducedMotion ? 'auto' : 'smooth' });
    }
    sectionButtons.forEach(function (button) {
        button.addEventListener('click', function () {
            const section = sections.find(function (item) { return item.dataset.qsbSection === button.dataset.qsbGo; });
            scrollToField(section);
            grid.scrollTop = 0;
        });
    });

    function updateCurrentSection() {
        const pinnedWidth = table.querySelector('.qsb-pinned').getBoundingClientRect().width;
        let current = sections[0].dataset.qsbSection;
        sections.forEach(function (section) {
            if (section.getBoundingClientRect().left - grid.getBoundingClientRect().left <= pinnedWidth + 20) {
                current = section.dataset.qsbSection;
            }
        });
        if (grid.scrollLeft >= grid.scrollWidth - grid.clientWidth - 2) {
            current = sections[sections.length - 1].dataset.qsbSection;
        }
        sectionButtons.forEach(function (button) {
            if (button.dataset.qsbGo === current) { button.setAttribute('aria-current', 'true'); }
            else { button.removeAttribute('aria-current'); }
        });
    }

    topScroll.addEventListener('scroll', function () {
        if (skipTopScroll) { skipTopScroll = false; return; }
        if (Math.abs(grid.scrollLeft - topScroll.scrollLeft) > 1) {
            skipGridScroll = true;
            grid.scrollLeft = topScroll.scrollLeft;
        }
    }, { passive: true });
    grid.addEventListener('scroll', function () {
        if (skipGridScroll) { skipGridScroll = false; }
        else if (Math.abs(topScroll.scrollLeft - grid.scrollLeft) > 1) {
            skipTopScroll = true;
            topScroll.scrollLeft = grid.scrollLeft;
        }
        updateCurrentSection();
    }, { passive: true });
    function resizeScroll() {
        const width = grid.scrollWidth + topScroll.clientWidth - grid.clientWidth;
        document.getElementById('qsb-top-scroll-width').style.width = width + 'px';
        updateCurrentSection();
    }
    new ResizeObserver(resizeScroll).observe(grid);
    resizeScroll();

    form.addEventListener('invalid', function (event) {
        event.target.classList.add('qsb-field-invalid');
        if (validationPending) { return; }
        validationPending = true;
        const label = event.target.getAttribute('aria-label') || 'Local específico';
        errorMessage.textContent = 'Preencha o campo obrigatório: ' + label + '.';
        errorMessage.hidden = false;
        grid.scrollTop = 0;
        scrollToField(event.target.closest('td'));
        setTimeout(function () { validationPending = false; }, 0);
    }, true);

    const dateFilter = document.getElementById('qsb-filter-date');
    const unitFilter = document.getElementById('qsb-filter-unit');
    const typeFilter = document.getElementById('qsb-filter-type');
    const searchFilter = document.getElementById('qsb-filter-search');
    const rows = Array.from(document.querySelectorAll('#qsb-table-entries tr[data-date]'));
    const searchableRows = rows.map(function (row) { return { row: row, text: normalize(row.textContent) }; });

    function normalize(value) {
        return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR');
    }
    function filterRows() {
        const search = normalize(searchFilter.value.trim());
        let count = 0;
        searchableRows.forEach(function (item) {
            const row = item.row;
            row.hidden = Boolean(
                (dateFilter.value && row.dataset.date !== dateFilter.value) ||
                (unitFilter.value && row.dataset.unit !== unitFilter.value) ||
                (typeFilter.value && row.dataset.type !== typeFilter.value) ||
                (search && !item.text.includes(search))
            );
            if (!row.hidden) { count += 1; }
        });
        document.getElementById('qsb-table-empty').hidden = count !== 0;
        document.getElementById('qsb-table-count').textContent = count + ' de ' + rows.length + ' informativo(s)';
    }
    [dateFilter, unitFilter, typeFilter, searchFilter].forEach(function (filter) { filter.addEventListener('input', filterRows); });
    document.getElementById('qsb-clear-filters').addEventListener('click', function () {
        [dateFilter, unitFilter, typeFilter, searchFilter].forEach(function (filter) { filter.value = ''; });
        filterRows();
    });
    filterRows();

    document.querySelectorAll('[data-product-code]').forEach(function (button) {
        button.addEventListener('click', async function () {
            const code = button.dataset.productCode;
            const output = button.parentElement.querySelector('.qsb-description-value');
            button.disabled = true;
            button.textContent = 'Consultando...';
            try {
                if (!descriptions.has(code)) {
                    const values = await lookup('searchProd', code);
                    descriptions.set(code, values[0] || 'Descrição não encontrada.');
                }
                output.textContent = descriptions.get(code);
                button.hidden = true;
            } catch (error) {
                output.textContent = 'Consulta indisponível.';
                button.textContent = 'Tentar novamente';
            } finally {
                button.disabled = false;
                const item = searchableRows.find(function (entry) { return entry.row === button.closest('tr'); });
                item.text = normalize(item.row.textContent);
                filterRows();
            }
        });
    });

    form.addEventListener('reset', function () {
        setTimeout(function () {
            clearTimeout(centerTimer);
            centerVersion += 1;
            setWorkcenters();
            resetProduct();
            window.QsbLocations.setUnit(unit.value);
            ['nok', 'ok'].forEach(renderFiles);
            form.querySelectorAll('.qsb-field-invalid').forEach(function (field) { field.classList.remove('qsb-field-invalid'); });
            errorMessage.hidden = true;
            updateProgress();
            grid.scrollTo({ left: 0, top: 0 });
        }, 0);
    });

    form.addEventListener('submit', function (event) {
        if (submitting) { event.preventDefault(); return; }
        submitting = true;
        submitButtons.forEach(function (button) { button.disabled = true; button.textContent = 'Cadastrando...'; });
    });
    window.addEventListener('pageshow', function () {
        submitting = false;
        submitButtons.forEach(function (button, index) { button.disabled = false; button.textContent = submitLabels[index]; });
        updateProgress();
        ['nok', 'ok'].forEach(renderFiles);
    });
}());
