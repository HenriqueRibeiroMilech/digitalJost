export const TYPE_LABELS = {
    melhoria: 'Melhoria',
    projeto: 'Projeto',
    erro: 'Erro / Defeito',
};

export const STATUS_LABELS = {
    todo: 'A fazer',
    in_progress: 'Em andamento',
    paused: 'Pausado',
    completed: 'Concluído',
    cancelled: 'Cancelado',
};

export const DIFFICULTY_LABELS = {
    low: 'Baixa',
    medium: 'Média',
    high: 'Alta',
};

export const state = {
    demands: [],
    users: [],
    openGroups: new Set(),
    initializedGroups: new Set(),
    filters: {
        search: '',
        responsible: '',
        type: '',
        status: '',
        difficulty: '',
    },
    currentDetail: null,
};

export function normalizeSearch(value) {
    return String(value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .trim();
}

export function isOverdue(demand) {
    if (!demand.deadline || ['completed', 'cancelled'].includes(demand.status)) {
        return false;
    }
    const today = new Date();
    const todayIso = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, '0'),
        String(today.getDate()).padStart(2, '0'),
    ].join('-');
    return demand.deadline < todayIso;
}

export function getVisibleDemands() {
    const search = normalizeSearch(state.filters.search);
    return state.demands.filter((demand) => {
        return (!search || normalizeSearch(demand.title).includes(search))
            && (!state.filters.responsible || demand.responsibleUserId === state.filters.responsible)
            && (!state.filters.type || demand.demandType === state.filters.type)
            && (!state.filters.status || demand.status === state.filters.status)
            && (!state.filters.difficulty || demand.difficulty === state.filters.difficulty);
    });
}

export function groupByResponsible(demands) {
    const grouped = new Map();
    demands.forEach((demand) => {
        const key = demand.responsibleUserId;
        if (!grouped.has(key)) {
            grouped.set(key, {
                id: key,
                name: demand.responsibleName || key,
                demands: [],
            });
        }
        grouped.get(key).demands.push(demand);
    });

    return [...grouped.values()]
        .map((group) => ({
            ...group,
            demands: group.demands.sort((a, b) => {
                if (isOverdue(a) !== isOverdue(b)) return isOverdue(a) ? -1 : 1;
                return String(a.title).localeCompare(String(b.title), 'pt-BR');
            }),
        }))
        .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
}

export function replaceDemand(updatedDemand) {
    state.demands = state.demands.map((demand) => (
        demand.managementId === updatedDemand.managementId ? updatedDemand : demand
    ));
    state.openGroups.add(updatedDemand.responsibleUserId);
}

export function updateTaskSummary(managementId, tasks) {
    const demand = state.demands.find((item) => item.managementId === managementId);
    if (!demand) return;
    demand.taskTotal = tasks.length;
    demand.taskCompleted = tasks.filter((task) => Boolean(task.completed)).length;
}

export function updateAttachmentSummary(managementId, attachments) {
    const demand = state.demands.find((item) => item.managementId === managementId);
    if (demand) demand.attachmentCount = attachments.length;
}
