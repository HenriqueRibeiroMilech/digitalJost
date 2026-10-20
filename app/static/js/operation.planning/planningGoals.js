let editingSpecificGoal = null;

function openSpecificGoal(row = null) {
    const form = document.getElementById('specific-goal-form');
    form.reset();
    editingSpecificGoal = row ? {
        type: String(Number(row.type)),
        event: String(Number(row.event)),
        workcenter: String(Number(row.workcenter)),
        goal: String(row.goal),
        revision: row.revision
    } : null;

    if (editingSpecificGoal) {
        document.getElementById('specific-type').value = editingSpecificGoal.type;
        document.getElementById('specific-event').value = editingSpecificGoal.event;
        document.getElementById('specific-workcenter').value = editingSpecificGoal.workcenter;
        document.getElementById('specific-goal').value = editingSpecificGoal.goal;
    }

    document.getElementById('specificGoalTitle').textContent = row
        ? 'Editar Meta Específica' : 'Adicionar Meta Específica';
    document.getElementById('addSpecificGoalForm').textContent = row
        ? 'Salvar alterações' : 'Adicionar';
    openModal('modalAddSpecificGoal');
}

document.getElementById('specific-goal-form').addEventListener('submit', async function (event) {
    event.preventDefault();
    const button = document.getElementById('addSpecificGoalForm');
    if (button.disabled) return;
    button.disabled = true;
    button.style.opacity = '0.7';

    const data = {
        type: document.getElementById('specific-type').value,
        event: document.getElementById('specific-event').value,
        workcenter: document.getElementById('specific-workcenter').value,
        goal: document.getElementById('specific-goal').value
    };
    if (editingSpecificGoal) data.original = { ...editingSpecificGoal };
    const url = new URL(planningGoalsConfig.saveUrl, window.location.origin);
    url.searchParams.set('type', editingSpecificGoal ? 'edit_specific' : 'specific');

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(result.error || 'Não foi possível salvar a meta.');
        }
        window.location.href = planningGoalsConfig.saveUrl;
    } catch (error) {
        infoAlert(error.message || 'Não foi possível salvar a meta. Tente novamente.');
    } finally {
        button.disabled = false;
        button.style.opacity = '1';
    }
});
