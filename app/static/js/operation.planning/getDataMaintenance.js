async function getDataMaintenance() {
    // Não reutiliza o percentual do filtro anterior se a nova consulta falhar.
    delete received_data.availability;
    received_data.overall = null;
    document.getElementById('overall').textContent = 'Consultando...';

    document.getElementById('infoTableBody0').innerHTML = '</h1><div class="loader"></div>'
    document.getElementById('infoTableBody1').innerHTML = '</h1><div class="loader"></div>'
    document.getElementById('infoTableBody2').innerHTML = '</h1><div class="loader"></div>'
    document.getElementById('infoTableBody3').innerHTML = '</h1><div class="loader"></div>'

    const year = document.getElementById('yearInput').value;
    const week = document.getElementById('weekInput').value;

    if (year && week) {

        const diagnostic = new URLSearchParams(window.location.search).get('diagnostic') === '1';
        const url = `/op/plano/area/3?type=maintenance&year=${year}&week=${week}${diagnostic ? '&diagnostic=1' : ''}`;

        fetch(url, { method: 'POST' })
            .then(response => {
                if (!response.ok) throw new Error('Falha ao consultar disponibilidade.');
                return response.json();
            })
            .then(data => {
                document.getElementById('infoTableBody0').innerHTML = ''
                document.getElementById('infoTableBody1').innerHTML = ''
                document.getElementById('infoTableBody2').innerHTML = ''
                document.getElementById('infoTableBody3').innerHTML = ''
                
                received_data.availability = data.extra
                received_data.month = data.month
                received_data.overall = data.overall
                if (planningDataAvailable && currentSlide === 5) showData();
            })
            .catch(error => {
                console.error('Error:', error);
                for (let area = 0; area < 4; area++) {
                    document.getElementById(`infoTableBody${area}`).innerHTML =
                        '<tr><td colspan="2">Não foi possível consultar a disponibilidade.</td></tr>';
                }
                document.getElementById('overall').textContent = 'Não disponível';
            });
    } else {
        alert("Por favor, preencha ambos os campos.");
    }
}
