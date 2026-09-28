let gettingData = false
let planningDataAvailable = false;

function submitWeek(areaId) {


    if (Object.keys(received_data).length > 0) {
        currentSlide = 0
        showSlide(currentSlide);
    }

    gettingData = true;
    planningDataAvailable = false;
    document.getElementById('getDataButton').disabled = true;
    document.getElementById('prevBtn').disabled = true;
    document.getElementById('nextBtn').disabled = true;

    if (areaId == 3) {
        getDataMaintenance()
    }

    

    document.getElementById('stopped1').style.display = 'none'
    document.getElementById('stopped2').style.display = 'none'
    document.getElementById('stopped3').style.display = 'none'

    const chartsContainer = document.getElementById('charts-container1');
    chartsContainer.innerHTML = '<div class="loader"></div>';

    const year = document.getElementById('yearInput').value;
    const week = document.getElementById('weekInput').value;

    if (year && week) {

        const url = `/op/plano/area/${areaId}?type=graph&year=${year}&week=${week}`;

        fetch(url, { method: 'POST' })
            .then(response => {
                if (!response.ok) throw new Error('Falha ao consultar indicadores.');
                return response.json();
            })
            .then(data => {

                if (areaId == "2") {
                    received_data.area.barchart13 = data.area.barchart1
                    received_data.area.barchart14 = data.area.barchart2
                    received_data.area.barchart15 = data.area.barchart3

                    received_data.area.barchart16 = data.area.barchart4
                    received_data.area.barchart17 = data.area.barchart5
                    received_data.area.barchart18 = data.area.barchart6

                    received_data.area.barchart19 = data.area.barchart7
                    received_data.area.barchart20 = data.area.barchart8
                    received_data.area.barchart21 = data.area.barchart9

                    received_data.area.barchart22 = data.area.barchart10
                    received_data.area.barchart23 = data.area.barchart11
                    received_data.area.barchart24 = data.area.barchart12

                    received_data.area.totals4 = data.area.totals0
                    received_data.area.totals5 = data.area.totals1
                    received_data.area.totals6 = data.area.totals2
                    received_data.area.totals7 = data.area.totals3

                    received_data.totals.count = parseFloat(received_data.totals.count) + parseFloat(data.totals.count)
                    received_data.totals.sum = parseFloat(received_data.totals.sum) + parseFloat(data.totals.sum)

                    received_data.actionPlan.push(...data.actionPlan)
                    received_data.oldActionPlan.push(...data.oldActionPlan)

                } else if (areaId == "1") {
                    Object.assign(received_data, data);
                    submitWeek("2")
                    return
                } else {
                    Object.assign(received_data, data);
                }

                planningDataAvailable = true;
                currentSlide = 0
                showSlide(currentSlide);

                gettingData = false
                document.getElementById('getDataButton').disabled = false;
                document.getElementById('prevBtn').disabled = false;
                document.getElementById('nextBtn').disabled = false;
            })
            .catch(error => {
                console.error('Error:', error);
                gettingData = false;
                planningDataAvailable = false;
                document.getElementById('getDataButton').disabled = false;
                // A navegação permanece bloqueada para não exibir gráficos antigos.
                chartsContainer.textContent = 'Não foi possível consultar os indicadores. Tente pesquisar novamente.';
            });
    } else {
        alert("Por favor, preencha ambos os campos.");
    }
}
