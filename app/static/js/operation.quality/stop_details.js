(function () {
    'use strict';
    window.QsbStopDetails = {
        render: function (containers, entries) {
            entries.forEach(function (entry, index) {
                const container = containers[index];
                if (!container) { return; }
                const values = [
                    ['Horário da parada', entry['Horário da parada']],
                    ['Motivo da parada', entry['Motivo da parada']],
                    ['Tempo total de parada', entry['Tempo total de parada'] === null ? '' : Number(entry['Tempo total de parada']).toLocaleString('pt-BR') + ' min'],
                    ['Quantidade de paradas', entry['Quantidade de paradas']],
                    ['Detalhamento do local', entry['Detalhamento do local']],
                ].filter(function (item) { return item[1] !== null && item[1] !== undefined && item[1] !== ''; });
                if (!values.length) { return; }
                const section = document.createElement('section');
                section.className = 'qsb-stop-details';
                const title = document.createElement('h3');
                title.textContent = 'Dados da parada';
                section.appendChild(title);
                const list = document.createElement('dl');
                values.forEach(function (item) {
                    const field = document.createElement('div');
                    const label = document.createElement('dt');
                    const value = document.createElement('dd');
                    label.textContent = item[0];
                    value.textContent = item[1];
                    field.append(label, value);
                    list.appendChild(field);
                });
                section.appendChild(list);
                container.classList.add('qsb-has-stop-details');
                container.insertBefore(section, container.querySelector('.qual_view_img_section'));
            });
        }
    };
}());
