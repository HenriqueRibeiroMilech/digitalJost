import { requestJson } from '@/shared/api/client'
import { paginationQuery } from '@/shared/api/pagination'
import type { Contributor, RequestDetail, RequestFields, RequestFilters, RequestList } from './types'

const base = '/api/v1/demands'

export const demandsApi = {
  list(page: number, perPage: number, filters: RequestFilters) {
    const query = paginationQuery(page, perPage)
    query.set('search', filters.search)
    query.set('entry_kind', filters.entry_kind)
    return requestJson<RequestList>(`${base}?${query}`, { cache: 'no-store' })
  },
  contributors() {
    return requestJson<{ items: Contributor[] }>(`${base}/contributors`)
  },
  get(id: number) {
    return requestJson<RequestDetail>(`${base}/${id}`, { cache: 'no-store' })
  },
  create(payload: RequestFields & { submission_key: string }, files: File[]) {
    const body = new FormData()
    body.append('payload', JSON.stringify(payload))
    files.forEach(file => body.append('files', file))
    return requestJson<RequestDetail>(base, { method: 'POST', body }, 60000)
  },
  update(id: number, payload: RequestFields & { row_version: string }) {
    return requestJson<RequestDetail>(`${base}/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
  },
  attachmentUrl(id: number, attachmentId: number) {
    return `${base}/${id}/attachments/${attachmentId}`
  },
  reply(id: number, payload: { row_version: string; information_id: number; reply: string }, files: File[]) {
    const body = new FormData()
    body.append('payload', JSON.stringify(payload))
    files.forEach(file => body.append('files', file))
    return requestJson<{ saved: boolean; notification_warning?: string }>(`${base}/${id}/information-reply`, { method: 'POST', body }, 60000)
  },
}
