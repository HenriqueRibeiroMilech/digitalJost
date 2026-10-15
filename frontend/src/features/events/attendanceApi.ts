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
  entries(eventId: number, listId: number, page: number, perPage: number) {
    return requestJson<AttendanceEntries>(`${listPath(eventId, listId)}/entries?${paginationQuery(page, perPage)}`)
  },
  register(eventId: number, listId: number, registration: string) {
    return requestJson<AttendanceRegistered>(`${listPath(eventId, listId)}/entries`, {
      method: 'POST', body: JSON.stringify({ registration }),
    })
  },
}
