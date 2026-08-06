
function getStatusStyle(status) {
    switch (status) {
        case -2: // CANCELADO
        return { display: 'CANCELADO', color: 'gray' };
        case -1: // RECUSADO
        return { display: 'RECUSADO', color: 'red' };
        case 0: // NÃO INICIADO
        return { display: 'NÃO INICIADO', color: 'black' };
        case 100: // CONCLUÍDO
        return { display: 'CONCLUÍDO', color: 'green' };
        default: // EM ANDAMENTO
        return { display: `${status}%`, color: 'blue' };
    }
}

function displayDeadlines(id, data) {
    const container = document.getElementById(id);
    container.innerHTML = '';

    data.forEach((deadline, index) => {
        const div = document.createElement('div');
        div.style.cursor = 'help'

        // Configurando o texto da data
        if (index === 0) {
            div.innerHTML = `<strong>${deadline}</strong>`;
        } else {
            div.style.textDecoration = "line-through";
            div.innerHTML = `${deadline}`;
        }

        // Adicionando o div ao container
        container.appendChild(div);
    });
}

function phrase(data, column) {

    let dataset;

    if (column == null) {
        dataset = [...new Set(data)];
    } else {
        dataset = [...new Set(data.map(row => row[column]))];
    }


    let phrase_str = '';

    if (dataset.length > 1) {
        const last_data = dataset.pop();
        phrase_str = dataset.join(', ') + ' e ' + last_data;
    } else if (dataset.length == 1) {
        phrase_str = dataset[0];
    } else {
        phrase_str = 'Não definido'
    }
    return phrase_str
}



function loadActionPlan(presentationArea) {

    let tableBody
    let data
    if (motiveId == 5) {
        tableBody = document.querySelector(presentationArea >= 0 ? `#actionPlan${presentationArea} tbody` : `#actionPlanExtra${Math.abs(presentationArea)} tbody`);
        console.log(presentationArea >= 0 ? `#actionPlan${presentationArea} tbody` : `#actionPlanExtra${Math.abs(presentationArea)} tbody`)
        if (presentationArea == 4) {
            data = received_data.oldActionPlan
        } else if (presentationArea == -1) {
            data = received_data.actionPlan.filter(item => item.presentationArea == 1 && item.description.includes('insumo'));
        } else if (presentationArea == -2) {
            data = received_data.actionPlan.filter(item => item.presentationArea == 2 && item.description.includes('setup'));
        } else if (presentationArea == -3) {
            data = received_data.actionPlan.filter(item => item.presentationArea == 3 && item.description.includes('setup'));
        } else {
            data = received_data.actionPlan.filter(item => item.presentationArea == presentationArea && !item.description.includes('insumo') && !item.description.includes('setup'));
        }

    } else {
        tableBody = document.querySelector(`#actionPlan${presentationArea != 4 ? (motiveId == 2 ? presentationArea + 4 : presentationArea) : motiveId == 2 ? 8 : presentationArea} tbody`);
        data = presentationArea == 4 ? received_data.oldActionPlan : received_data.actionPlan.filter(item => item.presentationArea == presentationArea && item.presentationMotive == motiveId);    
    }

    tableBody.innerHTML = '';

    const statusOrder = {
        '0': 1,
        '-2': 3,
        '-1': 4,
        '100': 5
    }
    
    const groupedData = data.reduce((acc, row) => {
        const key = `${row.planId}`;
        if (!acc[key]) {
            acc[key] = { ...row, rows: [] };
        }
        acc[key].rows.push(row);
        return acc;
    }, {});
    
    // Ordena os grupos antes de iterar
    const sortedGroups = Object.values(groupedData).sort((a, b) => {
        const statusA = statusOrder[a.planStatus.toString()] || (a.planStatus >= 1 && a.planStatus <= 99 ? 2 : 6);
        const statusB = statusOrder[b.planStatus.toString()] || (b.planStatus >= 1 && b.planStatus <= 99 ? 2 : 6);
        
        return statusA - statusB;
    });
    
    sortedGroups.forEach(group => {
        const { planId, responsible, description, planStatus, mainDeadline, workcenter, localGroup, relatedEvents, rows } = group;
    
        // Criar uma linha para o cabeçalho do grupo
        const trDescription = document.createElement('tr');
        trDescription.style.borderTop = '5px solid black';
        trDescription.style.backgroundColor = '#f5f5f5'; // Cor de fundo para destaque
    
        // Coluna 1 (Tipo de Ação) - Exibir a descrição do plano
        const tdDescription = trDescription.insertCell();
        tdDescription.textContent = description;
        tdDescription.innerHTML = `
                <strong>Problema:</strong> ${description}<br>
                <strong>Impacto:</strong> Área - ${phrase(JSON.parse(localGroup))} / Centro - ${phrase(JSON.parse(workcenter))} <br>                  
                <strong>Paradas:</strong> ${relatedEvents ? phrase(relatedEvents.split(",")) : 'Não relacionado'}<br>
                <button onclick="window.open('/op/plano/historico/${planId}', '_blank')" style="margin-top: 1vh;">Acessar</button>                   
        `;
        tdDescription.style.width  = '60%'
        tdDescription.style.position = 'relative'

        // Coluna 3 (Responsável) - Vazia para manter alinhamento
        const tdEmpty1 = trDescription.insertCell();
        tdEmpty1.textContent = responsible;
    
        // Coluna 4 (Prazo) - Vazia para manter alinhamento
        const tdEmpty2 = trDescription.insertCell();
        tdEmpty2.id = `deadline${planId}-0`
    
        // Coluna 5 (Status) - Exibir status geral do plano
        const tdStatus = trDescription.insertCell();
        tdStatus.innerHTML = `${getStatusStyle(planStatus).display}`;
        tdStatus.style.color = getStatusStyle(planStatus).color;
        tdStatus.style.fontWeight = 'bold';
    
        // Adicionar a linha de descrição à tabela
        tableBody.appendChild(trDescription);
    
        // Adicionar as linhas da tabela normalmente
        rows.forEach((row, index) => {
            const tr = document.createElement('tr');

            const textCell = tr.insertCell();
            textCell.innerHTML = `<strong>${row.type} ${row.istraining ? '(treinamento)' : '' }:</strong> ${row.text}`
    
            const nameCell = tr.insertCell();
            nameCell.textContent = row.name;
    
            const deadlineCell = tr.insertCell();
            deadlineCell.id = `deadline${planId}-${index + 1}`

            deadlineCell.textContent = row.deadline;
    
            const statusCell = tr.insertCell();
            const statusStyle = getStatusStyle(row.status);
            statusCell.textContent = statusStyle.display;
            statusCell.style.color = statusStyle.color;
            statusCell.style.fontWeight = 'bold';
    
            tableBody.appendChild(tr);
        });

        displayDeadlines(`deadline${planId}-0`, mainDeadline.split(","))

        rows.forEach((row, index) => {
            displayDeadlines(`deadline${planId}-${index + 1}`, row.deadline.split(","))
        });
    });
    

}