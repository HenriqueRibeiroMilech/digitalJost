import { requestJson } from '@/shared/api/client'
import { paginationQuery } from '@/shared/api/pagination'
import type {
  AttendanceEntries, AttendanceListDetail, AttendanceListItem, AttendanceLists, AttendanceRegistered,
} from './types'

const listsPath = (eventId: number) => `/api/v1/events/${eventId}/attendance-lists`
const listPath = (eventId: number, listId: number) => `${listsPath(eventId)}/${listId}`

export const attendanceApi = {
  list(eventId: number, page: number, perPage: number) {
    return requestJson<AttendanceLists>(`${listsPath(eventId)}?${paginationQuery(page, perPage)}`)
  },
  create(eventId: number, name: string) {
    return requestJson<AttendanceListItem>(listsPath(eventId), {
      method: 'POST', body: JSON.stringify({ name }),
    })
  },
  get(eventId: number, listId: number) {
    return requestJson<AttendanceListDetail>(listPath(eventId, listId))
  },
  rename(eventId: number, listId: number, name: string) {
    return requestJson<AttendanceListItem>(listPath(eventId, listId), {
      method: 'PUT', body: JSON.stringify({ name }),
    })
  },
  deleteList(eventId: number, listId: number) {
    return requestJson<{ id: number }>(listPath(eventId, listId), { method: 'DELETE' })
  },
  deleteEntry(eventId: number, listId: number, entryId: number) {
    return requestJson<{ id: number }>(`${listPath(eventId, listId)}/entries/${entryId}`, { method: 'DELETE' })
  },
  entries(eventId: number, listId: number, page: number, perPage: number) {
    return requestJson<AttendanceEntries>(`${listPath(eventId, listId)}/entries?${paginationQuery(page, perPage)}`)
  },
  register(eventId: number, listId: number, registration: string) {
    return requestJson<AttendanceRegistered>(`${listPath(eventId, listId)}/entries`, {
      method: 'POST', body: JSON.stringify({ registration }),
    })
  },
}
