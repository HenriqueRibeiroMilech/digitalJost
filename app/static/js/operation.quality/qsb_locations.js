(function () {
    function getElements() {
        return {
            addButton: document.getElementById('qsb_location_add_button'),
            field: document.getElementById('qsb_location_field'),
            freeInput: document.getElementById('op_local_info'),
            label: document.getElementById('qsb_location_label'),
            modal: document.getElementById('qsb_location_modal'),
            modalClose: document.getElementById('qsb_location_modal_close'),
            modalError: document.getElementById('qsb_location_modal_error'),
            modalInput: document.getElementById('qsb_location_name'),
            modalSave: document.getElementById('qsb_location_modal_save'),
            select: document.getElementById('op_local_info_select'),
            unit: document.getElementById('unidade')
        };
    }

    function setUnit(unit, value) {
        const elements = getElements();
        const isCaxias = String(unit) === '0';

        elements.select.disabled = !isCaxias;
        elements.select.style.display = isCaxias ? '' : 'none';
        elements.freeInput.disabled = isCaxias;
        elements.freeInput.style.display = isCaxias ? 'none' : '';
        elements.label.htmlFor = isCaxias ? 'op_local_info_select' : 'op_local_info';

        if (elements.addButton) {
            elements.addButton.style.display = isCaxias ? '' : 'none';
        }

        if (typeof value === 'undefined') {
            elements.select.value = '';
            elements.freeInput.value = '';
        } else if (isCaxias) {
            const matchingOption = Array.from(elements.select.options).find(function (option) {
                return option.value.localeCompare(value, 'pt-BR', { sensitivity: 'base' }) === 0;
            });
            elements.select.value = matchingOption ? matchingOption.value : '';
            elements.freeInput.value = '';
        } else {
            elements.select.value = '';
            elements.freeInput.value = value;
        }

        elements.field.dataset.initialized = 'true';
    }

    function openModal() {
        const elements = getElements();
        elements.modalError.textContent = '';
        elements.modalInput.value = '';
        elements.modal.classList.add('is-open');
        elements.modal.setAttribute('aria-hidden', 'false');
        elements.modalInput.focus();
    }

    function closeModal() {
        const elements = getElements();
        elements.modal.classList.remove('is-open');
        elements.modal.setAttribute('aria-hidden', 'true');
    }

    function addLocationOption(location) {
        const select = getElements().select;
        const option = document.createElement('option');
        option.value = location;
        option.textContent = location;
        select.appendChild(option);

        Array.from(select.options)
            .slice(1)
            .sort(function (left, right) {
                return left.text.localeCompare(right.text, 'pt-BR', { sensitivity: 'base' });
            })
            .forEach(function (sortedOption) {
                select.appendChild(sortedOption);
            });

        select.value = location;
    }

    async function createLocation() {
        const elements = getElements();
        const location = elements.modalInput.value.trim().replace(/\s+/g, ' ');

        if (!location) {
            elements.modalError.textContent = 'Informe o nome do local.';
            return;
        }

        elements.modalSave.disabled = true;
        elements.modalError.textContent = '';

        try {
            const response = await fetch(elements.field.dataset.createUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: location })
            });
            const data = await response.json().catch(function () {
                return {};
            });

            if (!response.ok) {
                throw new Error(data.error || 'Não foi possível cadastrar o local.');
            }

            addLocationOption(data.location);
            closeModal();
        } catch (error) {
            elements.modalError.textContent = error.message;
        } finally {
            elements.modalSave.disabled = false;
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const elements = getElements();

        elements.unit.addEventListener('change', function () {
            setUnit(elements.unit.value);
        });

        if (elements.field.dataset.initialized !== 'true') {
            setUnit(elements.unit.value);
        }

        if (!elements.addButton) {
            return;
        }

        elements.addButton.addEventListener('click', openModal);
        elements.modalClose.addEventListener('click', closeModal);
        elements.modalSave.addEventListener('click', createLocation);
        elements.modalInput.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                createLocation();
            }
        });
        elements.modal.addEventListener('click', function (event) {
            if (event.target === elements.modal) {
                closeModal();
            }
        });
    });

    window.QsbLocations = {
        setUnit: setUnit
    };
}());
