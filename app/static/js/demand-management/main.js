import {createDemandApi} from './api.js';
import {
    getVisibleDemands,
    replaceDemand,
    state,
    updateAttachmentSummary,
    updateTaskSummary,
} from './state.js';
import {
    renderDashboard,
    renderDialog,
    renderDialogError,
    renderResponsibleFilter,
} from './render.js';


const app = document.getElementById('demandManagementApp');
const area = app.dataset.area;
const api = createDemandApi(area, app.dataset.csrfToken);
const groupsContainer = document.getElementById('responsibleGroups');
const dialog = document.getElementById('demandDialog');
const dialogBody = document.getElementById('dialogBody');
const feedback = document.getElementById('pageFeedback');
const toastRegion = document.getElementById('toastRegion');
let detailRequestSequence = 0;


function setFeedback(message, tone = '') {
    feedback.textContent = message;
    if (tone) feedback.dataset.tone = tone;
    else delete feedback.dataset.tone;
}

function toast(message, tone = 'success') {
    const node = document.createElement('div');
    node.className = `dm-toast${tone === 'error' ? ' dm-toast--error' : ''}`;
    const icon = document.createElement('i');
    icon.className = tone === 'error' ? 'fas fa-exclamation-circle' : 'fas fa-check-circle';
    icon.setAttribute('aria-hidden', 'true');
    node.append(icon, document.createTextNode(message));
    toastRegion.append(node);
    window.setTimeout(() => node.remove(), 4200);
}

function render() {
    const visible = getVisibleDemands();
    renderDashboard(visible);
    setFeedback(`${visible.length} de ${state.demands.length} demandas exibidas.`);
}

function setInitialData(payload) {
    state.demands = payload.demands;
    state.users = payload.users;
    renderResponsibleFilter(
        document.getElementById('filterResponsible'),
        state.users,
        state.filters.responsible,
    );
    render();
}

async function loadData({quiet = false} = {}) {
    if (!quiet) {
        app.setAttribute('aria-busy', 'true');
        setFeedback('Carregando demandas…');
    }
    try {
        setInitialData(await api.list());
    } catch (error) {
        setFeedback(error.message, 'error');
        groupsContainer.replaceChildren();
        document.getElementById('emptyState').hidden = false;
        toast(error.message, 'error');
    } finally {
        app.setAttribute('aria-busy', 'false');
    }
}

function readDemandValue(control) {
    if (control.type === 'number') return control.value === '' ? null : control.value;
    return control.value;
}

async function updateDemandControl(control) {
    const managementId = Number(control.dataset.managementId);
    const demand = state.demands.find((item) => item.managementId === managementId);
    if (!demand || control.disabled) return;

    const field = control.dataset.demandField;
    const value = readDemandValue(control);
    const currentValue = demand[field] ?? '';
    if (String(value ?? '') === String(currentValue)) return;

    const card = control.closest('.dm-card');
    const cardControls = [...card.querySelectorAll('[data-demand-field]')];
    card.setAttribute('aria-busy', 'true');
    card.dataset.saving = 'true';
    cardControls.forEach((item) => { item.disabled = true; });
    control.dataset.state = 'saving';
    setFeedback(`Salvando “${demand.title}”…`);
    try {
        const payload = await api.update(managementId, field, value, demand.version);
        replaceDemand(payload.demand);
        render();
        toast(field === 'responsibleUserId'
            ? `Demanda movida para ${payload.demand.responsibleName}.`
            : 'Alteração salva.');
    } catch (error) {
        control.dataset.state = 'error';
        card.removeAttribute('aria-busy');
        delete card.dataset.saving;
        cardControls.forEach((item) => { item.disabled = false; });
        setFeedback(error.message, 'error');
        toast(error.message, 'error');
        if (error.status === 409) await loadData({quiet: true});
    }
}

function openNativeDialog() {
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
}

function closeNativeDialog() {
    detailRequestSequence += 1;
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
    state.currentDetail = null;
}

async function openDemand(managementId, section = 'source') {
    const requestSequence = ++detailRequestSequence;
    document.getElementById('dialogKicker').textContent = 'Detalhes da demanda';
    document.getElementById('dialogTitle').textContent = 'Carregando…';
    dialogBody.replaceChildren();
    const loading = document.createElement('div');
    loading.className = 'dm-dialog-loading';
    for (let index = 0; index < 3; index += 1) loading.append(document.createElement('span'));
    loading.append(document.createTextNode('Buscando detalhes da demanda…'));
    dialogBody.append(loading);
    if (!dialog.open) openNativeDialog();

    try {
        const detail = await api.detail(managementId);
        if (requestSequence !== detailRequestSequence) return;
        state.currentDetail = detail;
        renderDialog(detail, api);
        window.requestAnimationFrame(() => {
            document.getElementById(section)?.scrollIntoView({behavior: 'smooth', block: 'start'});
        });
    } catch (error) {
        if (requestSequence !== detailRequestSequence) return;
        renderDialogError(error.message);
    }
}

function rerenderCurrentDetail() {
    if (!state.currentDetail) return;
    const scrollTop = dialogBody.scrollTop;
    renderDialog(state.currentDetail, api);
    window.requestAnimationFrame(() => { dialogBody.scrollTop = scrollTop; });
}

function applyTasks(managementId, tasks) {
    updateTaskSummary(managementId, tasks);
    if (state.currentDetail?.demand.managementId === managementId) {
        state.currentDetail.tasks = tasks;
        rerenderCurrentDetail();
    }
    render();
}

function applyAttachments(managementId, attachments) {
    updateAttachmentSummary(managementId, attachments);
    if (state.currentDetail?.demand.managementId === managementId) {
        state.currentDetail.attachments = attachments;
        rerenderCurrentDetail();
    }
    render();
}

async function createTask(form) {
    const managementId = Number(form.dataset.managementId);
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    const values = Object.fromEntries(new FormData(form).entries());
    try {
        const payload = await api.createTask(managementId, values);
        applyTasks(managementId, payload.tasks);
        toast('Tarefa adicionada.');
    } catch (error) {
        submit.disabled = false;
        toast(error.message, 'error');
    }
}

async function updateTaskControl(control) {
    if (!state.currentDetail || control.disabled) return;
    const managementId = state.currentDetail.demand.managementId;
    const taskId = Number(control.dataset.taskId);
    const task = state.currentDetail.tasks.find((item) => item.taskId === taskId);
    if (!task) return;
    const field = control.dataset.taskField;
    const value = control.type === 'checkbox' ? control.checked : control.value;
    const row = control.closest('.dm-task-row');
    const rowControls = [...row.querySelectorAll('input, select, button')];
    row.setAttribute('aria-busy', 'true');
    rowControls.forEach((item) => { item.disabled = true; });
    try {
        const payload = await api.updateTask(managementId, taskId, {[field]: value}, task.version);
        applyTasks(managementId, payload.tasks);
        toast('Tarefa atualizada.');
    } catch (error) {
        row.removeAttribute('aria-busy');
        rowControls.forEach((item) => { item.disabled = false; });
        toast(error.message, 'error');
        if (error.status === 409) openDemand(managementId, 'tasks');
    }
}

async function deleteTask(taskId) {
    if (!state.currentDetail) return;
    if (!window.confirm('Excluir esta tarefa? Esta ação não poderá ser desfeita.')) return;
    const managementId = state.currentDetail.demand.managementId;
    const task = state.currentDetail.tasks.find((item) => item.taskId === taskId);
    if (!task) return;
    try {
        const payload = await api.deleteTask(managementId, taskId, task.version);
        applyTasks(managementId, payload.tasks);
        toast('Tarefa excluída.');
    } catch (error) {
        toast(error.message, 'error');
        if (error.status === 409) openDemand(managementId, 'tasks');
    }
}

async function uploadAttachment(form) {
    const input = form.querySelector('input[type="file"]');
    const submit = form.querySelector('button[type="submit"]');
    if (!input.files.length) return;
    submit.disabled = true;
    try {
        const managementId = Number(form.dataset.managementId);
        const payload = await api.uploadAttachment(managementId, input.files[0]);
        applyAttachments(managementId, payload.attachments);
        toast('Anexo enviado com segurança.');
    } catch (error) {
        submit.disabled = false;
        toast(error.message, 'error');
    }
}

async function deleteAttachment(attachmentId) {
    if (!state.currentDetail) return;
    if (!window.confirm('Excluir este anexo? Esta ação não poderá ser desfeita.')) return;
    const managementId = state.currentDetail.demand.managementId;
    try {
        const payload = await api.deleteAttachment(managementId, attachmentId);
        applyAttachments(managementId, payload.attachments);
        toast(payload.warning || 'Anexo excluído.', payload.warning ? 'error' : 'success');
    } catch (error) {
        toast(error.message, 'error');
    }
}

document.querySelectorAll('#filterSearch, #filterResponsible, #filterType, #filterStatus, #filterDifficulty')
    .forEach((control) => {
        const eventName = control.type === 'search' ? 'input' : 'change';
        control.addEventListener(eventName, () => {
            const mapping = {
                filterSearch: 'search',
                filterResponsible: 'responsible',
                filterType: 'type',
                filterStatus: 'status',
                filterDifficulty: 'difficulty',
            };
            state.filters[mapping[control.id]] = control.value;
            render();
        });
    });

document.getElementById('clearFilters').addEventListener('click', () => {
    Object.keys(state.filters).forEach((key) => { state.filters[key] = ''; });
    document.getElementById('filterSearch').value = '';
    document.getElementById('filterResponsible').value = '';
    document.getElementById('filterType').value = '';
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterDifficulty').value = '';
    render();
});

groupsContainer.addEventListener('change', (event) => {
    const control = event.target.closest('[data-demand-field]');
    if (control) updateDemandControl(control);
});

groupsContainer.addEventListener('toggle', (event) => {
    const group = event.target.closest('details[data-responsible-id]');
    if (!group) return;
    if (group.open) state.openGroups.add(group.dataset.responsibleId);
    else state.openGroups.delete(group.dataset.responsibleId);
}, true);

groupsContainer.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-demand]');
    if (trigger) openDemand(Number(trigger.dataset.openDemand), trigger.dataset.section);
});

dialogBody.addEventListener('submit', (event) => {
    event.preventDefault();
    if (event.target.id === 'taskCreateForm') createTask(event.target);
    if (event.target.id === 'attachmentForm') uploadAttachment(event.target);
});

dialogBody.addEventListener('change', (event) => {
    const taskControl = event.target.closest('[data-task-field]');
    if (taskControl) updateTaskControl(taskControl);
});

dialogBody.addEventListener('click', (event) => {
    const deleteTaskButton = event.target.closest('[data-delete-task]');
    if (deleteTaskButton) deleteTask(Number(deleteTaskButton.dataset.deleteTask));
    const deleteAttachmentButton = event.target.closest('[data-delete-attachment]');
    if (deleteAttachmentButton) deleteAttachment(deleteAttachmentButton.dataset.deleteAttachment);
});

document.getElementById('closeDialog').addEventListener('click', closeNativeDialog);
dialog.addEventListener('close', () => {
    detailRequestSequence += 1;
    state.currentDetail = null;
});
dialog.addEventListener('click', (event) => {
    if (event.target === dialog) closeNativeDialog();
});

document.addEventListener('keydown', (event) => {
    if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey) return;
    const activeTag = document.activeElement?.tagName;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(activeTag)) return;
    event.preventDefault();
    document.getElementById('filterSearch').focus();
});

loadData();
