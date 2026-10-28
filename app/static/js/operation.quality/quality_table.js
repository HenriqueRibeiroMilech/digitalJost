(function () {
    'use strict';

    const form = document.getElementById('qsb-table-form');
    const unit = document.getElementById('unidade');
    const workcenter = document.getElementById('qsb-workcenter');
    const workcenters = document.getElementById('qsb-workcenters');
    const product = document.getElementById('qsb-product');
    const products = document.getElementById('qsb-products');
    const description = document.getElementById('qsb-product-description');
    const submit = document.getElementById('qsb-table-submit');
    const caxiasCenters = Array.from(workcenters.options, function (option) { return option.value; });
    const campinasCenters = [
        'M101-Montagem Articulação De Onibus',
        'M102-Montagem Trava De Quinta Roda',
        'S101-Solda Robotizada Articulação De Onibus'
    ];
    let centerTimer;
    let productTimer;
    let centerVersion = 0;
    let productVersion = 0;

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
        url.searchParams.set(key, value);
        const response = await fetch(url, { method: 'POST' });
        if (!response.ok || response.redirected) {
            throw new Error('Consulta indisponível.');
        }
        return response.json();
    }

    function resetProduct() {
        clearTimeout(productTimer);
        productVersion += 1;
        product.value = '';
        products.replaceChildren();
        description.textContent = 'Informe o código do produto.';
    }

    unit.addEventListener('change', function () {
        clearTimeout(centerTimer);
        centerVersion += 1;
        workcenter.value = '';
        fillOptions(workcenters, unit.value === '1' ? campinasCenters : caxiasCenters);
        resetProduct();
    });
    fillOptions(workcenters, unit.value === '1' ? campinasCenters : caxiasCenters);

    workcenter.addEventListener('input', function () {
        workcenter.value = workcenter.value.replace(/'/g, '');
        clearTimeout(centerTimer);
        const version = ++centerVersion;
        resetProduct();
        if (!workcenter.value.trim()) { return; }
        centerTimer = setTimeout(async function () {
            try {
                const values = await lookup('searchCt', workcenter.value);
                if (version !== centerVersion) { return; }
                fillOptions(products, values);
            } catch (error) {
                if (version === centerVersion) {
                    description.textContent = 'Não foi possível consultar as sugestões. Informe o código do produto.';
                }
            }
        }, 300);
    });

    product.addEventListener('input', function () {
        product.value = product.value.replace(/'/g, '');
        clearTimeout(productTimer);
        const version = ++productVersion;
        description.textContent = 'Informe o código do produto.';
        if (!product.value.trim()) { return; }
        description.textContent = 'Consultando descrição...';
        productTimer = setTimeout(async function () {
            try {
                const values = await lookup('searchProd', product.value);
                if (version !== productVersion) { return; }
                description.textContent = values[0] || 'Descrição não encontrada.';
            } catch (error) {
                if (version === productVersion) {
                    description.textContent = 'Não foi possível consultar a descrição.';
                }
            }
        }, 300);
    });

    ['nok', 'ok'].forEach(function (category) {
        const input = document.getElementById('qsb-files-' + category);
        const list = document.getElementById('qsb-files-' + category + '-list');
        input.addEventListener('change', function () {
            list.replaceChildren();
            Array.from(input.files).forEach(function (file) {
                const item = document.createElement('li');
                item.textContent = file.name;
                list.appendChild(item);
            });
        });
    });

    const shifts = Array.from(form.querySelectorAll('input[name="turno1"], input[name="turno2"], input[name="turno3"]'));
    const notApplicable = form.elements.namedItem('NA');
    notApplicable.addEventListener('change', function () {
        if (notApplicable.checked) {
            shifts.forEach(function (shift) { shift.checked = false; });
        }
    });
    shifts.forEach(function (shift) {
        shift.addEventListener('change', function () {
            if (shift.checked) { notApplicable.checked = false; }
        });
    });

    const dateFilter = document.getElementById('qsb-filter-date');
    const unitFilter = document.getElementById('qsb-filter-unit');
    const typeFilter = document.getElementById('qsb-filter-type');
    const searchFilter = document.getElementById('qsb-filter-search');
    const rows = Array.from(document.querySelectorAll('#qsb-table-entries tr[data-date]'));
    const searchableRows = rows.map(function (row) {
        return { row: row, text: normalize(row.textContent) };
    });

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
        document.getElementById('qsb-table-count').textContent = count + ' de ' + rows.length + ' informativo(s).';
    }

    [dateFilter, unitFilter, typeFilter, searchFilter].forEach(function (filter) {
        filter.addEventListener('input', filterRows);
    });
    document.getElementById('qsb-clear-filters').addEventListener('click', function () {
        [dateFilter, unitFilter, typeFilter, searchFilter].forEach(function (filter) { filter.value = ''; });
        filterRows();
    });
    filterRows();

    form.addEventListener('submit', function (event) {
        if (submit.disabled) { event.preventDefault(); return; }
        submit.disabled = true;
        submit.textContent = 'Cadastrando...';
    });
    window.addEventListener('pageshow', function () {
        submit.disabled = false;
        submit.textContent = 'Cadastrar';
    });
}());
