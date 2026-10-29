import { requestJson } from '@/shared/api/client'
import { paginationQuery } from '@/shared/api/pagination'
import type { Contributor, ManagementFilters, RequestDetail, RequestFields, RequestFilters, RequestList, ReviewFields } from './types'

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
  managementList(page: number, perPage: number, filters: ManagementFilters) {
    const query = paginationQuery(page, perPage)
    query.set('search', filters.search)
    query.set('entry_kind', filters.entry_kind)
    query.set('status', filters.status)
    return requestJson<RequestList>(`${base}/management?${query}`, { cache: 'no-store' })
  },
  managementGet(id: number) {
    return requestJson<RequestDetail>(`${base}/management/${id}`, { cache: 'no-store' })
  },
  responsibles() {
    return requestJson<{ items: Contributor[] }>(`${base}/management/responsibles`, { cache: 'no-store' })
  },
  review(id: number, payload: ReviewFields) {
    return requestJson<RequestDetail>(`${base}/management/${id}/review`, { method: 'POST', body: JSON.stringify(payload) })
  },
  attachmentUrl(id: number, attachmentId: number, management = false) {
    return `${base}${management ? '/management' : ''}/${id}/attachments/${attachmentId}`
  },
}
