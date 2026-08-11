import {
    DIFFICULTY_LABELS,
    STATUS_LABELS,
    TYPE_LABELS,
    groupByResponsible,
    isOverdue,
    state,
} from './state.js';


function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
}

function icon(className) {
    const node = element('i', className);
    node.setAttribute('aria-hidden', 'true');
    return node;
}

function option(value, label, selected = false, disabled = false) {
    const node = element('option', '', label);
    node.value = value;
    node.selected = selected;
    node.disabled = disabled;
    return node;
}

function initials(name) {
    const parts = String(name || '?').trim().split(/\s+/).filter(Boolean);
    return parts.slice(0, 2).map((part) => part[0]).join('').toUpperCase() || '?';
}

function formatHours(value) {
    if (value === null || value === undefined || value === '') return '—';
    return `${Number(value).toLocaleString('pt-BR', {maximumFractionDigits: 2})} h`;
}

function formatDate(value) {
    if (!value) return '—';
    const [year, month, day] = String(value).slice(0, 10).split('-');
    return year && month && day ? `${day}/${month}/${year}` : value;
}

function readableSize(size) {
    const bytes = Number(size || 0);
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function badge(kind, value, label, asButton = false) {
    const node = element(asButton ? 'button' : 'span', asButton ? 'dm-badge-button' : 'dm-badge');
    node.classList.add(`dm-${kind}--${value || 'none'}`);
    node.textContent = label;
    if (asButton) node.type = 'button';
    return node;
}

function demandSelectField(label, demand, field, values, includeEmpty = false) {
    const wrapper = element('label', 'dm-field');
    wrapper.append(element('span', '', label));
    const select = element('select');
    select.dataset.demandField = field;
    select.dataset.managementId = demand.managementId;
    if (includeEmpty) select.append(option('', 'Não definida', !demand[field]));
    values.forEach(([value, text]) => select.append(option(value, text, demand[field] === value)));
    wrapper.append(select);
    return wrapper;
}

function demandInputField(label, demand, field, type, options = {}) {
    const wrapper = element('label', `dm-field${options.wide ? ' dm-field--wide' : ''}`);
    wrapper.append(element('span', '', label));
    const input = options.textarea ? element('textarea') : element('input');
    if (!options.textarea) input.type = type;
    input.value = demand[field] ?? '';
    input.dataset.demandField = field;
    input.dataset.managementId = demand.managementId;
    if (options.step) input.step = options.step;
    if (options.min !== undefined) input.min = options.min;
    if (options.placeholder) input.placeholder = options.placeholder;
    wrapper.append(input);
    return wrapper;
}

function responsibleField(demand, users) {
    const wrapper = element('label', 'dm-field');
    wrapper.append(element('span', '', 'Responsável'));
    const select = element('select');
    select.dataset.demandField = 'responsibleUserId';
    select.dataset.managementId = demand.managementId;
    users.forEach((user) => {
        const current = user.id === demand.responsibleUserId;
        select.append(option(user.id, user.name, current, !user.assignable && !current));
    });
    wrapper.append(select);
    return wrapper;
}

function progressPercent(demand) {
    if (!demand.taskTotal) return 0;
    return Math.round((demand.taskCompleted / demand.taskTotal) * 100);
}

function demandCard(demand, users) {
    const card = element('article', 'dm-card');
    card.dataset.managementId = demand.managementId;
    if (isOverdue(demand)) card.classList.add('dm-card--overdue');

    const header = element('div', 'dm-card__header');
    const typeBadge = badge('type', demand.demandType, TYPE_LABELS[demand.demandType] || 'Melhoria', true);
    typeBadge.dataset.openDemand = demand.managementId;
    typeBadge.dataset.section = 'source';
    typeBadge.title = 'Abrir todos os detalhes';
    header.append(typeBadge);
    header.append(badge('status', demand.status, STATUS_LABELS[demand.status] || demand.status));
    if (demand.difficulty) {
        header.append(badge('difficulty', demand.difficulty, DIFFICULTY_LABELS[demand.difficulty]));
    }
    header.append(element('span', 'dm-card__reference', `#${demand.requestId}`));
    if (isOverdue(demand)) {
        const overdue = element('span', 'dm-overdue-flag');
        overdue.append(icon('fas fa-exclamation-triangle'), document.createTextNode('Atrasada'));
        header.append(overdue);
    }
    card.append(header);

    const intro = element('div', 'dm-card__intro');
    intro.append(element('h3', '', demand.title));
    intro.append(element('p', '', demand.initialDescription || 'Sem descrição inicial.'));
    card.append(intro);

    const fields = element('div', 'dm-card__fields');
    fields.append(
        responsibleField(demand, users),
        demandSelectField('Status', demand, 'status', Object.entries(STATUS_LABELS)),
        demandSelectField('Dificuldade', demand, 'difficulty', Object.entries(DIFFICULTY_LABELS), true),
        demandInputField('Prazo', demand, 'deadline', 'date'),
        demandInputField('Data de início', demand, 'startDate', 'date'),
        demandInputField('Tempo estimado (h)', demand, 'estimatedHours', 'number', {step: '0.25', min: '0'}),
        demandInputField('Tempo diário (h)', demand, 'dailyHours', 'number', {step: '0.25', min: '0'}),
        demandInputField('Tempo realizado (h)', demand, 'actualHours', 'number', {step: '0.25', min: '0'}),
        demandInputField('Observações', demand, 'observations', '', {
            textarea: true,
            wide: true,
            placeholder: 'Registre decisões, bloqueios e contexto operacional…',
        }),
    );
    card.append(fields);

    const footer = element('footer', 'dm-card__footer');
    const taskButton = element('button', 'dm-card-action');
    taskButton.type = 'button';
    taskButton.dataset.openDemand = demand.managementId;
    taskButton.dataset.section = 'tasks';
    taskButton.append(icon('fas fa-check-square'));
    const taskLabel = element('span');
    taskLabel.append(document.createTextNode('Tarefas '));
    taskLabel.append(element('strong', '', `${demand.taskCompleted}/${demand.taskTotal}`));
    taskButton.append(taskLabel);
    const progress = element('span', 'dm-progress');
    const progressFill = element('span');
    progressFill.style.width = `${progressPercent(demand)}%`;
    progress.append(progressFill);
    taskButton.append(progress);

    const attachmentButton = element('button', 'dm-card-action');
    attachmentButton.type = 'button';
    attachmentButton.dataset.openDemand = demand.managementId;
    attachmentButton.dataset.section = 'attachments';
    attachmentButton.append(
        icon('fas fa-paperclip'),
        document.createTextNode(`Anexos `),
        element('strong', '', String(demand.attachmentCount)),
    );
    footer.append(taskButton, attachmentButton);
    card.append(footer);
    return card;
}

function responsibleGroup(group, users) {
    if (!state.initializedGroups.has(group.id)) {
        state.openGroups.add(group.id);
        state.initializedGroups.add(group.id);
    }

    const details = element('details', 'dm-group');
    details.dataset.responsibleId = group.id;
    details.open = state.openGroups.has(group.id);
    const summary = element('summary', 'dm-group__summary');
    summary.append(element('span', 'dm-group__avatar', initials(group.name)));

    const identity = element('span', 'dm-group__name');
    identity.append(
        element('strong', '', group.name),
        element('span', '', `${group.demands.length} ${group.demands.length === 1 ? 'demanda' : 'demandas'}`),
    );
    summary.append(identity);

    const indicators = element('span', 'dm-group__indicators');
    const active = group.demands.filter((demand) => demand.status === 'in_progress').length;
    const overdue = group.demands.filter(isOverdue).length;
    indicators.append(element('span', 'dm-group__counter', `${active} em andamento`));
    if (overdue) indicators.append(element('span', 'dm-group__counter dm-group__counter--danger', `${overdue} atrasada${overdue > 1 ? 's' : ''}`));
    const chevron = element('span', 'dm-group__chevron');
    chevron.append(icon('fas fa-chevron-down'));
    indicators.append(chevron);
    summary.append(indicators);
    details.append(summary);

    const grid = element('div', 'dm-card-grid');
    group.demands.forEach((demand) => grid.append(demandCard(demand, users)));
    details.append(grid);
    return details;
}

export function renderResponsibleFilter(select, users, selectedValue) {
    const current = selectedValue || '';
    select.replaceChildren(option('', 'Todos', !current));
    users.forEach((user) => select.append(option(user.id, user.name, user.id === current)));
}

export function renderDashboard(demands) {
    const groupsContainer = document.getElementById('responsibleGroups');
    const emptyState = document.getElementById('emptyState');
    const groups = groupByResponsible(demands);
    groupsContainer.replaceChildren();
    groups.forEach((group) => groupsContainer.append(responsibleGroup(group, state.users)));
    emptyState.hidden = demands.length !== 0;

    const taskTotal = demands.reduce((sum, demand) => sum + Number(demand.taskTotal || 0), 0);
    const taskCompleted = demands.reduce((sum, demand) => sum + Number(demand.taskCompleted || 0), 0);
    document.getElementById('metricTotal').textContent = demands.length;
    document.getElementById('metricTotalCaption').textContent = `${groups.length} ${groups.length === 1 ? 'responsável' : 'responsáveis'}`;
    document.getElementById('metricInProgress').textContent = demands.filter((demand) => demand.status === 'in_progress').length;
    document.getElementById('metricOverdue').textContent = demands.filter(isOverdue).length;
    document.getElementById('metricTasks').textContent = `${taskCompleted}/${taskTotal}`;
}

function descriptionItem(term, description, wide = false) {
    const wrapper = element('div', wide ? 'dm-description-list__wide' : '');
    wrapper.append(element('dt', '', term), element('dd', '', description || 'Não informado'));
    return wrapper;
}

function sourcePanel(detail) {
    const source = detail.source;
    const panel = element('section', 'dm-panel');
    panel.id = 'source';
    const header = element('header', 'dm-panel__header');
    const heading = element('h3');
    heading.append(icon('fas fa-file-alt'), document.createTextNode('Dados da solicitação'));
    header.append(heading, element('span', 'dm-card__reference', `Solicitação #${source.requestId}`));
    panel.append(header);

    const body = element('div', 'dm-panel__body');
    const list = element('dl', 'dm-description-list');
    list.append(
        descriptionItem('Solicitante', source.requesterName),
        descriptionItem('Solicitada em', formatDate(source.requestDate)),
        descriptionItem('Urgência', source.urgency),
    );
    if (source.demandType === 'erro') {
        list.append(descriptionItem('Descrição completa do problema', source.objective, true));
    } else {
        list.append(
            descriptionItem('Objetivo da demanda', source.objective, true),
            descriptionItem('Premissas da demanda', source.assumptions, true),
            descriptionItem('Problemas atuais', source.actualProblems, true),
            descriptionItem('Ganhos esperados', source.benefits, true),
        );
    }
    body.append(list);
    panel.append(body);
    return panel;
}

function operationalPanel(detail) {
    const demand = detail.demand;
    const panel = element('section', 'dm-panel');
    const header = element('header', 'dm-panel__header');
    const heading = element('h3');
    heading.append(icon('fas fa-sliders-h'), document.createTextNode('Acompanhamento operacional'));
    header.append(heading);
    panel.append(header);
    const body = element('div', 'dm-panel__body');
    const badges = element('div', 'dm-detail-badges');
    badges.append(
        badge('type', demand.demandType, TYPE_LABELS[demand.demandType] || 'Melhoria'),
        badge('status', demand.status, STATUS_LABELS[demand.status] || demand.status),
    );
    if (demand.difficulty) badges.append(badge('difficulty', demand.difficulty, DIFFICULTY_LABELS[demand.difficulty]));
    body.append(badges);
    const list = element('dl', 'dm-description-list');
    list.append(
        descriptionItem('Responsável', demand.responsibleName),
        descriptionItem('Prazo', formatDate(demand.deadline)),
        descriptionItem('Data de início', formatDate(demand.startDate)),
        descriptionItem('Tempo estimado', formatHours(demand.estimatedHours)),
        descriptionItem('Tempo diário', formatHours(demand.dailyHours)),
        descriptionItem('Tempo realizado', formatHours(demand.actualHours)),
        descriptionItem('Observações', demand.observations, true),
    );
    body.append(list);
    panel.append(body);
    return panel;
}

function usersSelect(users, selectedId, allowEmpty = true) {
    const select = element('select');
    if (allowEmpty) select.append(option('', 'Sem responsável', !selectedId));
    users.forEach((user) => {
        const current = user.id === selectedId;
        select.append(option(user.id, user.name, current, !user.assignable && !current));
    });
    return select;
}

function tasksPanel(detail) {
    const panel = element('section', 'dm-panel');
    panel.id = 'tasks';
    const header = element('header', 'dm-panel__header');
    const heading = element('h3');
    heading.append(icon('fas fa-check-square'), document.createTextNode('Tarefas'));
    const completed = detail.tasks.filter((task) => Boolean(task.completed)).length;
    header.append(heading, badge('status', 'in_progress', `${completed}/${detail.tasks.length} concluídas`));
    panel.append(header);

    const body = element('div', 'dm-panel__body');
    const form = element('form', 'dm-task-form');
    form.id = 'taskCreateForm';
    form.dataset.managementId = detail.demand.managementId;
    const descriptionLabel = element('label');
    descriptionLabel.append(element('span', '', 'Nova tarefa'));
    const description = element('input');
    description.name = 'description';
    description.required = true;
    description.maxLength = 2000;
    description.placeholder = 'Descreva uma entrega objetiva';
    descriptionLabel.append(description);

    const responsibleLabel = element('label');
    responsibleLabel.append(element('span', '', 'Responsável'));
    const responsible = usersSelect(detail.users, detail.demand.responsibleUserId);
    responsible.name = 'responsibleUserId';
    responsibleLabel.append(responsible);

    const deadlineLabel = element('label');
    deadlineLabel.append(element('span', '', 'Prazo'));
    const deadline = element('input');
    deadline.type = 'date';
    deadline.name = 'deadline';
    deadlineLabel.append(deadline);
    const submit = element('button', 'dm-button', 'Adicionar');
    submit.type = 'submit';
    submit.append(icon('fas fa-plus'));
    form.append(descriptionLabel, responsibleLabel, deadlineLabel, submit);
    body.append(form);

    const list = element('div', 'dm-task-list');
    if (!detail.tasks.length) {
        list.append(element('p', 'dm-task-empty', 'Nenhuma tarefa cadastrada. Divida a demanda em entregas menores para acompanhar o progresso.'));
    } else {
        detail.tasks.forEach((task) => {
            const row = element('div', `dm-task-row${task.completed ? ' dm-task-row--completed' : ''}`);
            const checkbox = element('input', 'dm-task-check');
            checkbox.type = 'checkbox';
            checkbox.checked = Boolean(task.completed);
            checkbox.dataset.taskField = 'completed';
            checkbox.dataset.taskId = task.taskId;
            checkbox.setAttribute('aria-label', `Concluir tarefa ${task.description}`);

            const taskDescription = element('input', 'dm-task-description');
            taskDescription.value = task.description;
            taskDescription.maxLength = 2000;
            taskDescription.dataset.taskField = 'description';
            taskDescription.dataset.taskId = task.taskId;

            const assignee = usersSelect(detail.users, task.responsibleUserId);
            assignee.className = 'dm-task-assignee';
            assignee.dataset.taskField = 'responsibleUserId';
            assignee.dataset.taskId = task.taskId;

            const taskDeadline = element('input', 'dm-task-deadline');
            taskDeadline.type = 'date';
            taskDeadline.value = task.deadline || '';
            taskDeadline.dataset.taskField = 'deadline';
            taskDeadline.dataset.taskId = task.taskId;

            const remove = element('button', 'dm-icon-button dm-icon-button--danger');
            remove.type = 'button';
            remove.dataset.deleteTask = task.taskId;
            remove.title = 'Excluir tarefa';
            remove.setAttribute('aria-label', `Excluir tarefa ${task.description}`);
            remove.append(icon('fas fa-trash-alt'));
            row.append(checkbox, taskDescription, assignee, taskDeadline, remove);
            list.append(row);
        });
    }
    body.append(list);
    panel.append(body);
    return panel;
}

function attachmentsPanel(detail, api) {
    const panel = element('section', 'dm-panel');
    panel.id = 'attachments';
    const header = element('header', 'dm-panel__header');
    const heading = element('h3');
    heading.append(icon('fas fa-paperclip'), document.createTextNode('Anexos'));
    header.append(heading, element('span', 'dm-card__reference', `${detail.attachments.length} arquivo${detail.attachments.length === 1 ? '' : 's'}`));
    panel.append(header);
    const body = element('div', 'dm-panel__body');
    const form = element('form', 'dm-attachment-form');
    form.id = 'attachmentForm';
    form.dataset.managementId = detail.demand.managementId;
    const input = element('input');
    input.type = 'file';
    input.name = 'file';
    input.required = true;
    input.accept = '.pdf,.png,.jpg,.jpeg,.gif,.webp,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip';
    const submit = element('button', 'dm-button', 'Anexar arquivo');
    submit.type = 'submit';
    submit.append(icon('fas fa-upload'));
    form.append(input, submit);
    body.append(form);

    const list = element('div', 'dm-attachment-list');
    if (!detail.attachments.length) {
        list.append(element('p', 'dm-attachment-empty', 'Nenhum anexo cadastrado para esta demanda.'));
    } else {
        detail.attachments.forEach((attachment) => {
            const row = element('div', 'dm-attachment-row');
            const fileIcon = element('span', 'dm-file-icon');
            fileIcon.append(icon('fas fa-file'));
            const name = element('span', 'dm-attachment-name');
            name.append(
                element('strong', '', attachment.originalName),
                element('small', '', `${readableSize(attachment.sizeBytes)} · ${attachment.uploadedByName}`),
            );
            const download = element('a', 'dm-download-link', 'Baixar');
            download.href = api.attachmentUrl(detail.demand.managementId, attachment.attachmentId);
            download.append(icon('fas fa-download'));
            const remove = element('button', 'dm-icon-button dm-icon-button--danger');
            remove.type = 'button';
            remove.dataset.deleteAttachment = attachment.attachmentId;
            remove.title = 'Excluir anexo';
            remove.setAttribute('aria-label', `Excluir anexo ${attachment.originalName}`);
            remove.append(icon('fas fa-trash-alt'));
            row.append(fileIcon, name, download, remove);
            list.append(row);
        });
    }
    body.append(list);
    panel.append(body);
    return panel;
}

export function renderDialog(detail, api) {
    document.getElementById('dialogKicker').textContent = `${TYPE_LABELS[detail.source.demandType] || 'Demanda'} · #${detail.source.requestId}`;
    document.getElementById('dialogTitle').textContent = detail.source.title;
    const layout = element('div', 'dm-detail-layout');
    const summary = element('div', 'dm-detail-summary');
    summary.append(sourcePanel(detail), operationalPanel(detail));
    layout.append(summary, tasksPanel(detail), attachmentsPanel(detail, api));
    document.getElementById('dialogBody').replaceChildren(layout);
}

export function renderDialogError(message) {
    const wrapper = element('section', 'dm-empty');
    wrapper.append(
        element('h2', '', 'Não foi possível abrir a demanda'),
        element('p', '', message),
    );
    document.getElementById('dialogBody').replaceChildren(wrapper);
}
