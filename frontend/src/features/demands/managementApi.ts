import { requestJson } from '@/shared/api/client'
import type { Board, BoardFilters, ManagedDetail, ManagedDemand, ManagementFields, ManagementOptions, Notice } from './managementTypes'

const base = '/api/v1/demand-management'
const json = (method: string, payload: unknown): RequestInit => ({ method, body: JSON.stringify(payload) })
export const managementApi = {
  options: () => requestJson<ManagementOptions>(base + '/options'),
  board(filters: BoardFilters) {
    const query = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => { if (value) query.set(key, value) })
    return requestJson<Board>(`${base}?${query}`, { cache: 'no-store' })
  },
  requests: () => requestJson<{ items: ManagedDemand[] }>(base + '/requests', { cache: 'no-store' }),
  get: (id: number) => requestJson<ManagedDetail>(`${base}/${id}`, { cache: 'no-store' }),
  review: (id: number, payload: Record<string, unknown>) => requestJson<ManagedDetail>(`${base}/${id}/review`, json('POST', payload), 60000),
  action: (id: number, payload: Record<string, unknown>) => requestJson<ManagedDetail>(`${base}/${id}/actions`, json('POST', payload), 60000),
  deadline: (id: number, payload: Record<string, unknown>) => requestJson<ManagedDetail>(`${base}/${id}/deadline`, json('PATCH', payload), 60000),
  update: (id: number, payload: ManagementFields & { row_version: string }) => requestJson<ManagedDetail>(`${base}/${id}`, json('PUT', payload)),
  create(payload: Record<string, unknown>, files: File[]) {
    const body = new FormData(); body.append('payload', JSON.stringify(payload))
    files.forEach(file => body.append('files', file))
    return requestJson<ManagedDetail>(base, { method: 'POST', body }, 60000)
  },
  task: (id: number, payload: Record<string, unknown>, taskId?: number) => requestJson<ManagedDetail>(`${base}/${id}/tasks${taskId ? '/' + taskId : ''}`, json(taskId ? 'PUT' : 'POST', payload)),
  removeTask: (id: number, taskId: number, version: string) => requestJson<ManagedDetail>(`${base}/${id}/tasks/${taskId}`, json('DELETE', { row_version: version })),
  attach(id: number, version: string, files: File[]) {
    const body = new FormData(); body.append('payload', JSON.stringify({ row_version: version }))
    files.forEach(file => body.append('files', file))
    return requestJson<ManagedDetail>(`${base}/${id}/attachments`, { method: 'POST', body }, 60000)
  },
  removeAttachment: (id: number, attachmentId: number, version: string) => requestJson<ManagedDetail>(`${base}/${id}/attachments/${attachmentId}`, json('DELETE', { row_version: version })),
  attachmentUrl: (id: number, attachmentId: number) => `${base}/${id}/attachments/${attachmentId}`,
  notice: (payload: Record<string, unknown>, id?: number) => requestJson<{ saved: boolean }>(`${base}/notices${id ? '/' + id : ''}`, json(id ? 'PUT' : 'POST', payload)),
  finishNotice: (notice: Notice) => requestJson<{ saved: boolean }>(`${base}/notices/${notice.id}`, json('DELETE', { row_version: notice.row_version })),
}
