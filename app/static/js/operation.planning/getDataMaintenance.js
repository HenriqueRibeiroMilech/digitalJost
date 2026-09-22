async function getDataMaintenance() {

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
            .then(response => response.json())
            .then(data => {
                document.getElementById('infoTableBody0').innerHTML = ''
                document.getElementById('infoTableBody1').innerHTML = ''
                document.getElementById('infoTableBody2').innerHTML = ''
                document.getElementById('infoTableBody3').innerHTML = ''
                
                received_data.availability = data.extra
                received_data.month = data.month
                received_data.overall = data.overall
            })
            .catch(error => {
                console.error('Error:', error);
            });
    } else {
        alert("Por favor, preencha ambos os campos.");
    }
}
