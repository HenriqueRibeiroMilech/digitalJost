export class DemandApiError extends Error {
    constructor(message, status) {
        super(message);
        this.name = 'DemandApiError';
        this.status = status;
    }
}

export function createDemandApi(area, csrfToken) {
    const areaQuery = `area=${encodeURIComponent(area)}`;
    const baseUrl = '/demandas/gerenciador/api';

    async function requestJson(url, options = {}) {
        const response = await fetch(url, {
            credentials: 'same-origin',
            headers: {
                Accept: 'application/json',
                'X-CSRF-Token': csrfToken,
                ...(options.body instanceof FormData ? {} : {'Content-Type': 'application/json'}),
                ...(options.headers || {}),
            },
            ...options,
        });

        const contentType = response.headers.get('content-type') || '';
        const payload = contentType.includes('application/json')
            ? await response.json()
            : null;

        if (!response.ok || payload?.ok === false || payload === null) {
            throw new DemandApiError(
                payload?.message || (payload === null
                    ? 'A sessão pode ter expirado. Recarregue a página e tente novamente.'
                    : 'Não foi possível concluir a operação.'),
                response.status,
            );
        }
        return payload;
    }

    return {
        list() {
            return requestJson(`${baseUrl}?${areaQuery}`);
        },
        detail(managementId) {
            return requestJson(`${baseUrl}/${managementId}?${areaQuery}`);
        },
        update(managementId, field, value, version) {
            return requestJson(`${baseUrl}/${managementId}?${areaQuery}`, {
                method: 'PATCH',
                body: JSON.stringify({field, value, version}),
            });
        },
        createTask(managementId, values) {
            return requestJson(`${baseUrl}/${managementId}/tasks?${areaQuery}`, {
                method: 'POST',
                body: JSON.stringify(values),
            });
        },
        updateTask(managementId, taskId, values, version) {
            return requestJson(`${baseUrl}/${managementId}/tasks/${taskId}?${areaQuery}`, {
                method: 'PATCH',
                body: JSON.stringify({...values, version}),
            });
        },
        deleteTask(managementId, taskId, version) {
            return requestJson(`${baseUrl}/${managementId}/tasks/${taskId}?${areaQuery}`, {
                method: 'DELETE',
                body: JSON.stringify({version}),
            });
        },
        uploadAttachment(managementId, file) {
            const formData = new FormData();
            formData.append('file', file);
            return requestJson(`${baseUrl}/${managementId}/attachments?${areaQuery}`, {
                method: 'POST',
                body: formData,
            });
        },
        deleteAttachment(managementId, attachmentId) {
            return requestJson(
                `${baseUrl}/${managementId}/attachments/${encodeURIComponent(attachmentId)}?${areaQuery}`,
                {method: 'DELETE'},
            );
        },
        attachmentUrl(managementId, attachmentId) {
            return `${baseUrl}/${managementId}/attachments/${encodeURIComponent(attachmentId)}?${areaQuery}`;
        },
    };
}
